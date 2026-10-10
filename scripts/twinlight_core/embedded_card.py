"""Independent check of the actual delivered HTML, not just a source manifest.

Compare decoded embedded bytes with all six selected native assets and bind both
persona copies. This does not replace template-origin or real browser checks.
"""
from __future__ import annotations
import base64
import hashlib
import io
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageOps
from .canvas_mapping import logical_canvas, compose_layers

ROLES=('background','spirit','subject','effects','text','lineart')
MAX_HTML=128*1024*1024
MAX_ASSET=24*1024*1024


class EmbeddingError(ValueError):
    def __init__(self, code, message): super().__init__(message);self.code=code


def require(value, code, message):
    if not value: raise EmbeddingError(code,message)


def _json(text):
    def pairs(xs):
        out={}
        for k,v in xs:
            require(k not in out,'duplicate_json_key','Duplicate key in embedded data: '+k);out[k]=v
        return out
    def bad(v): raise EmbeddingError('nonfinite_json','Non-finite embedded value: '+v)
    return json.JSONDecoder(object_pairs_hook=pairs,parse_constant=bad)


class Scripts(HTMLParser):
    def __init__(self): super().__init__(convert_charrefs=False);self.current=None;self.items=[]
    def handle_starttag(self,tag,attrs):
        if tag=='script':self.current=[dict(attrs),[]]
    def handle_data(self,data):
        if self.current is not None:self.current[1].append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.current is not None:
            self.items.append((self.current[0],''.join(self.current[1])));self.current=None


def _constant(script,name):
    found=list(re.finditer(r'^\s*const\s+'+re.escape(name)+r'\s*=\s*',script,re.M))
    require(len(found)==1,'embedded_binding_count','Expected exactly one '+name+' constant')
    tail=script[found[0].end():]
    try:value,end=_json(tail).raw_decode(tail)
    except (ValueError,TypeError) as exc:raise EmbeddingError('embedded_json','Invalid '+name+' JSON') from exc
    require(tail[end:].lstrip().startswith(';'),'embedded_expression','Embedded card data must be a literal JSON value')
    return value


def _image(payload):
    require(len(payload)<=MAX_ASSET,'asset_size','Embedded artwork exceeds 24 MiB')
    with Image.open(io.BytesIO(payload)) as im:
        require(im.format in ('PNG','JPEG','WEBP'),'asset_format','Unsupported embedded image format')
        require(0<im.width*im.height<=16_000_000,'image_size','Embedded image exceeds size limit')
        return im.convert('RGBA')


def _data_uri(value):
    require(isinstance(value,str) and len(value)<=MAX_ASSET*4//3+100,'data_uri','Missing or oversized embedded asset')
    match=re.fullmatch(r'data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)',value)
    require(match is not None,'not_self_contained','Every layer must be a local embedded image, not auto, a URL or a file path')
    try:return base64.b64decode(match[2],validate=True)
    except ValueError as exc:raise EmbeddingError('invalid_base64','Invalid embedded layer bytes') from exc


def _source_assets(manifest_path):
    root=manifest_path.resolve().parent
    require(manifest_path.stat().st_size<=2*1024*1024,'manifest_size','Manifest too large')
    manifest=_json('').decode(manifest_path.read_text(encoding='utf-8'))
    require(manifest.get('art_status') in ('generated','approved'),'native_art_required','Static and placeholder cards cannot satisfy a native-card request')
    require(set(manifest.get('assets',{}))==set(ROLES),'layer_roles','All six distinct layer roles are required')
    assets={};images={};resolved=set()
    for role,name in manifest['assets'].items():
        require(isinstance(name,str) and name and not Path(name).is_absolute() and '..' not in Path(name).parts and ':' not in name,
                'asset_path','Native layer paths must be relative to the card directory')
        path=(root/name).resolve()
        require(path.is_relative_to(root) and path.is_file(),'asset_path','Missing or escaping native layer path')
        require(path not in resolved,'duplicate_layer_file','One file cannot fill multiple layer roles');resolved.add(path)
        require(path.stat().st_size<=MAX_ASSET,'asset_size','Native asset exceeds size limit')
        assets[role]=path.read_bytes();images[role]=_image(assets[role])
    try:
        w,h=logical_canvas(manifest,images)
    except ValueError as exc:
        raise EmbeddingError('canvas_mismatch',str(exc)) from exc
    require(min(w,h)>=256 and abs(w/h-.75)<.01,'canvas_ratio','All original layers must share one native 3:4 canvas')
    require(images['background'].getchannel('A').getextrema()==(255,255),'background_alpha','Background must be fully opaque')
    for role in ('subject','effects','text'):
        hist=images[role].getchannel('A').histogram();total=images[role].width*images[role].height
        require(sum(hist[:16])/total>.01 and sum(hist[16:])/total>.0005,
                'empty_or_flat_layer',role+' needs visible content and genuine transparent regions')
    alpha=images['subject'].getchannel('A')
    edge=ImageChops.difference(alpha.filter(ImageFilter.MaxFilter(5)),alpha.filter(ImageFilter.MinFilter(5)))
    registered=ImageOps.invert(edge).convert('RGBA')
    require(images['lineart'].size==registered.size and images['lineart'].tobytes()==registered.tobytes(),
            'unregistered_lineart','Lineart must follow the final subject alpha at the same native pixels')
    d=manifest.get('depths',{})
    require(all(type(d.get(k)) in (int,float) for k in ('background','subject','effects','text')),
            'layer_depths','Missing layer depths')
    require(d['background']<0<d['subject']<d['effects'] and d['text']==0,
            'layer_depths','Keep real separated depths and fixed text')
    return manifest,assets,images


def audit_embedding(html_path: Path, manifest_path: Path, expected_persona: str, *, strict_renderer: bool = False) -> dict:
    report={'ok':False,'status':'embedding_failed','errors':[],
            'scope':'Actual embedded bytes and identity bindings only; not a browser or aesthetic certificate.',
            'native_layers_embedded':False,'dynamic_verified':False}
    try:
        html_path,manifest_path=Path(html_path),Path(manifest_path)
        require(html_path.is_file() and html_path.stat().st_size<=MAX_HTML,'html_file','HTML is missing or exceeds size limit')
        raw=html_path.read_bytes();text=raw.decode('utf-8')
        manifest,assets,images=_source_assets(manifest_path)
        require(manifest.get('persona_digest')==expected_persona,'wrong_persona','Native manifest belongs to another person')
        parser=Scripts();parser.feed(text)
        profiles=[t for a,t in parser.items if a.get('id')=='journeyData']
        require(len(profiles)==1,'profile_count','Expected one embedded personal profile')
        profile=_json('').decode(profiles[0]);persona=profile.get('persona',{})
        scripts='\n'.join(t for a,t in parser.items if a.get('type')!='application/json')
        card=_constant(scripts,'CARD_PERSONA');layers=_constant(scripts,'HOLO_LAYERS')
        require(persona==card,'persona_copies_diverged','Page and card identity data disagree')
        require(persona.get('persona_digest')==expected_persona and persona.get('content_ready') is True,
                'wrong_persona','Embedded identity is missing, unready or belongs to another person')
        require(persona.get('art_mode')=='layered' and persona.get('art_status') in ('generated','approved'),
                'static_card_not_native','Static/placeholder mode disables the requested native effect')
        require(set(layers)==set(ROLES),'embedded_roles','HTML is missing native layer roles')
        fingerprints={}
        for role in ROLES:
            payload=_data_uri(layers[role]);_image(payload)
            actual=hashlib.sha256(payload).hexdigest();expected=hashlib.sha256(assets[role]).hexdigest()
            require(actual==expected,'embedded_layer_mismatch','HTML contains stale or substituted '+role+' bytes')
            fingerprints[role]=actual
        match=re.findall(r'^\s*const\s+V9_CARD_IMAGE\s*=\s*([\'\"])(.*?)\1\s*;',scripts,re.M)
        require(len(match)==1,'flat_preview_missing','Expected the embedded flattened preview of the same native card')
        flat=_data_uri(match[0][1]);image=compose_layers(manifest,images,include_text=True)
        buffer=io.BytesIO();image.convert('RGB').save(buffer,format='JPEG',quality=92)
        require(hashlib.sha256(flat).digest()==hashlib.sha256(buffer.getvalue()).digest(),
                'flat_preview_mismatch','Flattened preview is not this exact assembled native card')
        if strict_renderer:
            rendering = audit_renderer(html_path, manifest_path)
            require(rendering.get('ok'), 'shared_renderer_mismatch', 'Embedded renderer or depth configuration differs')
            report['rendering'] = rendering
        report.update(ok=True,status='native_card_embedded',native_layers_embedded=True,
                      html_sha256=hashlib.sha256(raw).hexdigest(),persona_digest=expected_persona,
                      canvas=list(image.size),layers_sha256=fingerprints,flat_preview_verified=True)
    except (EmbeddingError,OSError,ValueError,TypeError,KeyError,AttributeError,Image.DecompressionBombError) as exc:
        report['errors']=[{'code':getattr(exc,'code','invalid_embedding'),'message':str(exc)[:1000]}]
    return report


def audit_renderer(html_path: Path, manifest_path: Path) -> dict:
    """Exact shared renderer bytes after token expansion, including native depths.

    This is reproducibility, not a WebGL or aesthetic certificate.
    """
    from .common import ROOT, load, local_asset, safe_script_json
    from .site import fill, uri
    from .card_handoff import renderer_contract
    try:
        manifest = load(manifest_path)
        values = {'CARD_LAYERS': safe_script_json({k: uri(local_asset(manifest_path.parent, v))
                  for k, v in manifest['assets'].items()}),
                  **{'DEPTH_' + token: str(manifest['depths'][role]) for role, token in
                     [('background', 'BG'), ('subject', 'SUBJECT'), ('effects', 'EFFECTS')]}}
        expected = fill((ROOT / 'assets/template/src/holo-card.js').read_text(), values)
        text = Path(html_path).read_text(encoding='utf-8')
        require(text.count(expected) == 1, 'shared_renderer_mismatch',
                'HTML must contain exactly the current shared renderer with the same native depths and layer bytes')
        return {'ok': True, 'renderer': renderer_contract(), 'depths': manifest['depths'],
                'scope': 'Shared rendering bytes/configuration only, not runtime or aesthetic review.'}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {'ok': False, 'errors': [{'code': getattr(exc, 'code', 'renderer_invalid'), 'message': str(exc)}]}
