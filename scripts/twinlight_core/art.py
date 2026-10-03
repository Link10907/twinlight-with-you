"""Check genuine image layers without uploading them anywhere."""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from .common import check, local_asset, load, schema_check


def validate_composition(composition: dict, persona_digest: str, canvas: tuple[int, int]) -> None:
    """Validate explicit geometry, without guessing a face or a person's meaning."""
    schema_check(composition, "card-composition.schema.json")
    check(composition["persona_digest"] == persona_digest,
          "Composition belongs to a different persona; do not reuse another person's prototype lock")
    locked = composition["canvas"]
    check((locked["width"], locked["height"]) == tuple(canvas),
          "Composition canvas differs from the native layer canvas; regenerate the layer instead of cropping, resizing or repositioning")
    width, height = canvas
    check(width * height <= 16_000_000 and abs(width / height - .75) < .01,
          "Composition requires a native 3:4 canvas, at most 16 million pixels")
    rectangles = [(name, composition[name]) for name in ("subject_bounds", "subject_center_region") if name in composition]
    rectangles += [(f"text_safe_regions[{i}]", rect) for i, rect in enumerate(composition.get("text_safe_regions", []))]
    for name, rect in rectangles:
        check(rect[0] < rect[2] and rect[1] < rect[3], f"{name}: rectangle must have positive width and height")
    check("max_text_overlap" not in composition or "text_safe_regions" in composition,
          "max_text_overlap requires explicit text_safe_regions")


def _alpha_center(alpha: Image.Image) -> list[float]:
    """Exact alpha-weighted centroid, used only for an explicitly requested check."""
    width, height = alpha.size
    total = ImageStat.Stat(alpha).sum[0]
    check(total > 0, "subject: cannot measure the center of an empty layer")
    def mass(region):
        return ImageStat.Stat(region).sum[0]
    x = sum((i + .5) * mass(alpha.crop((i, 0, i + 1, height))) for i in range(width)) / total / width
    y = sum((i + .5) * mass(alpha.crop((0, i, width, i + 1))) for i in range(height)) / total / height
    return [x, y]


def _check_registered_composition(composition: dict, images: dict) -> dict:
    """Measure native alpha geometry; no source pixels are modified or saved."""
    alpha = images["subject"].getchannel("A")
    width, height = alpha.size
    alpha = alpha.point(lambda v: v if v >= 16 else 0)
    box = alpha.getbbox()
    check(box is not None, "subject: layer is empty")
    bounds = [box[0] / width, box[1] / height, box[2] / width, box[3] / height]
    result = {"provided": True, "canvas": [width, height], "subject_bounds": [round(v, 6) for v in bounds]}
    if "subject_bounds" in composition:
        allowed = composition["subject_bounds"]
        check(bounds[0] >= allowed[0] and bounds[1] >= allowed[1] and bounds[2] <= allowed[2] and bounds[3] <= allowed[3],
              "Subject extends outside the locked subject_bounds; regenerate against the selected prototype, do not reposition the layer")
    if "subject_center_region" in composition:
        center = _alpha_center(alpha)
        allowed = composition["subject_center_region"]
        check(allowed[0] <= center[0] <= allowed[2] and allowed[1] <= center[1] <= allowed[3],
              "Subject alpha center is outside the locked subject_center_region; regenerate, then visually compare the actual focal feature")
        result["subject_alpha_center"] = [round(v, 6) for v in center]
    if "text_safe_regions" in composition:
        foreground = alpha
        for role in ("spirit", "effects"):
            foreground = ImageChops.lighter(foreground, images[role].getchannel("A"))
        occupied = foreground.point(lambda v: 255 if v >= 16 else 0)
        checked = []
        for i, rect in enumerate(composition["text_safe_regions"]):
            pixels = (math.floor(rect[0] * width), math.floor(rect[1] * height),
                      math.ceil(rect[2] * width), math.ceil(rect[3] * height))
            crop = occupied.crop(pixels)
            overlap = crop.histogram()[255] / (crop.width * crop.height)
            check(overlap <= composition.get("max_text_overlap", .05),
                  f"text_safe_regions[{i}]: subject/spirit/effects occupy the locked text space; regenerate the offending foreground layer")
            checked.append({"region": rect, "occupied_fraction": round(overlap, 6)})
        result["text_safe_regions"] = checked
    if "source_prototype_sha256" in composition:
        result["source_prototype_sha256"] = composition["source_prototype_sha256"]
        result["prototype_hash_verified_by_layer_validator"] = False
    result["quality_verified"] = False
    return result


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
    if "composition" in manifest:
        validate_composition(manifest["composition"], manifest["persona_digest"], (w,h))
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
    # Mechanical checks cannot prove visual quality, likeness, or personal meaning.
    report = {"ok":True,"size":[w,h],"art_status":manifest["art_status"],"layers":checks,
              "quality_verified":False,"automatic_approval":False,
              "visual_review_required":["same current-person concept and symbols as the selected prototype",
                                        "complete background with no repeated or ghost subject",
                                        "no missing scenery revealed at +/-25 degrees",
                                        "clean native alpha edges for the actual subject and foreground",
                                        "face or main symbol remains readable; text stays aligned",
                                        "real figure likeness if authorized"]}
    if "composition" in manifest:
        report["composition"] = _check_registered_composition(manifest["composition"], images)
    return report


def asset_digest(manifest_path: Path) -> str:
    import hashlib
    from .common import digest
    manifest=load(manifest_path)
    validate_layers(manifest_path)
    files={k:hashlib.sha256(local_asset(manifest_path.parent,v).read_bytes()).hexdigest() for k,v in manifest['assets'].items()}
    return digest({'manifest':manifest,'files':files})
