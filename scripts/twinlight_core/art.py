"""Check genuine image layers without uploading them anywhere."""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from .common import check, local_asset, load, schema_check


def validate_layers(manifest_path: Path, expected_persona: str | None = None) -> dict:
    manifest=load(manifest_path)
    schema_check(manifest,"layer-manifest.schema.json")
    if expected_persona: check(manifest["persona_digest"]==expected_persona,"Artwork belongs to a different persona; do not reuse it silently")
    root=manifest_path.parent
    images={}
    for name, relative in manifest["assets"].items():
        path=local_asset(root,relative)
        check(path.stat().st_size<=24*1024*1024,"Layer file exceeds 24 MiB")
        with Image.open(path) as im:
            check(im.format in ("PNG","JPEG","WEBP"),"Layers must be raster PNG/JPEG/WebP, not SVG/code")
            check(im.width*im.height<=16_000_000,"Layer dimensions too large")
            images[name]=im.convert("RGBA")
    sizes={im.size for im in images.values()}
    check(len(sizes)==1,"All layers must use exactly the same canvas/coordinates")
    w,h=next(iter(sizes))
    check(w>=256 and h>=256 and abs(w/h-.75)<.01,"Expected a 3:4 portrait canvas, at least 256 pixels")
    checks={}
    for name,im in images.items():
        hist=im.getchannel("A").histogram(); total=w*h
        transparent=sum(hist[:16])/total; occupied=sum(hist[16:])/total
        if name in ("subject","effects","text"):
            check(transparent>.01,f"{name}: no genuine transparent region (painted checkerboards are not alpha)")
            check(occupied>.0005,f"{name}: layer is empty")
        if name=="background":check(hist[255]==total,"Background must be fully opaque")
        if name=="lineart":
            grey=im.convert("L"); lo,hi=grey.getextrema()
            check(lo<128 and hi>200,"Lineart must contain dark registered contours on white")
        checks[name]={"transparent_fraction":round(transparent,4),"occupied_fraction":round(occupied,4)}
    depths=manifest["depths"]
    check(depths["background"]<0<depths["subject"]<depths["effects"],"Keep negative background depth and separated positive subject/effects depths")
    # Alpha cannot prove subject segmentation/background inpainting quality.
    return {"ok":True,"size":[w,h],"art_status":manifest["art_status"],"layers":checks,
            "visual_review_required":["ghost subject behind foreground", "holes revealed at +/-25 degrees", "hair and sleeve matte edges", "text stays aligned", "real figure likeness if authorized"]}


def asset_digest(manifest_path: Path) -> str:
    import hashlib
    from .common import digest
    manifest=load(manifest_path)
    validate_layers(manifest_path)
    files={k:hashlib.sha256(local_asset(manifest_path.parent,v).read_bytes()).hexdigest() for k,v in manifest['assets'].items()}
    return digest({'manifest':manifest,'files':files})
