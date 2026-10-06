"""Offline V10-derived fixed template builder; never calls an image/model API."""
from __future__ import annotations
import base64
import io
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from .common import ROOT, VERSION, check, load, save, safe_script_json, local_asset, digest
from .compiler import compile_profile, check_approval
from .art import validate_layers, asset_digest
from .canvas_mapping import compose_layers

TEMPLATE=ROOT/'assets/template'
TEMPLATE_MODULES={'RENDER':'render','CONTROLS':'controls','V6':'v6','V7':'v7','V8':'v8','FINALE':'finale','V9':'v9','HOLO':'holo-card','V10':'v10','ADAPTER':'adapter'}
TEMPLATE_CSS=('style','v7','v8','v9','v10','adapter')
TEMPLATE_MEDIA=(('__TEXTURE__','dust-disc.jpg'),('__SURFACE__','stellar-atlas.jpg'),('__V10_MUSIC__','another-light.mp3'))

def uri(path: Path) -> str:
    suffix=path.suffix.lower()
    types={'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp','.mp3':'audio/mpeg'}
    check(suffix in types, 'Unsupported embedded media type')
    return 'data:'+types[suffix]+';base64,'+base64.b64encode(path.read_bytes()).decode('ascii')

def placeholder_layers(out: Path, persona_digest: str) -> Path:
    """A deliberately abstract, labeled depth fixture, NOT an AI portrait."""
    out.mkdir(parents=True,exist_ok=True)
    w,h=600,800
    bg=Image.new('RGB',(w,h)); px=bg.load()
    for y in range(h):
        for x in range(w):
            f=max(0,1-(((x-390)/500)**2+((y-220)/700)**2))
            px[x,y]=(int(7+7*f),int(12+17*f),int(23+27*f))
    d=ImageDraw.Draw(bg)
    for i in range(210):
        u=int(digest(['demo-star',i])[:8],16);x=u%w;y=(u//w)%h;r=1 if i%7 else 2
        d.ellipse((x-r,y-r,x+r,y+r),fill=(85+i%60,103+i%65,135+i%80))
    d.ellipse((315,90,490,265),outline=(113,139,164),width=2)
    bg.save(out/'background.jpg',quality=90)
    # An open, sculptural astrolabe creates clear negative space and separate depth.
    subject=Image.new('RGBA',(w,h));d=ImageDraw.Draw(subject)
    for b in [(122,242,475,550),(176,201,419,587),(101,334,499,457)]:
        d.ellipse(b,outline=(208,185,142,255),width=5)
    d.line((180,562,405,225),fill=(201,183,150,255),width=7)
    d.ellipse((270,350,338,418),fill=(146,181,201,255),outline=(243,221,173,255),width=4)
    d.polygon([(300,310),(317,364),(370,385),(317,402),(300,455),(283,402),(230,385),(283,364)],outline=(241,220,171,255),width=3)
    subject.save(out/'subject.png')
    fx=Image.new('RGBA',(w,h));d=ImageDraw.Draw(fx)
    for x,y,r in [(126,269,11),(440,485,12),(439,216,8),(155,565,8)]:
        d.polygon([(x,y-r),(x+r*.35,y-r*.35),(x+r,y),(x+r*.35,y+r*.35),(x,y+r),(x-r*.35,y+r*.35),(x-r,y),(x-r*.35,y-r*.35)],fill=(229,214,185,230))
    fx.save(out/'effects.png')
    transparent=Image.new('RGBA',(w,h));transparent.save(out/'spirit.png')
    txt=Image.new('RGBA',(w,h));d=ImageDraw.Draw(txt)
    font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font=lambda n:ImageFont.truetype(font_path,n) if Path(font_path).exists() else ImageFont.load_default(size=n)
    d.rounded_rectangle((14,14,586,786),radius=18,outline=(204,185,151,240),width=2)
    d.rounded_rectangle((27,27,573,773),radius=12,outline=(105,132,155,160),width=1)
    d.text((47,53),'SSR',font=font(37),fill=(231,212,174,255))
    for y,text,size in [(638,'LAYERS IN LIGHT',25),(681,'DEMO / NOT A PERSONAL PORTRAIT',13),(723,'T W I N L I G H T',12)]:
        bbox=d.textbbox((0,0),text,font=font(size));d.text(((w-(bbox[2]-bbox[0]))/2,y),text,font=font(size),fill=(219,219,213,255))
    txt.save(out/'text.png')
    # White outside the very same subject contour; no separately redrawn line art.
    alpha=subject.getchannel('A');edge=ImageChops_safe(alpha.filter(ImageFilter.MaxFilter(5)),alpha.filter(ImageFilter.MinFilter(5)))
    ImageOps.invert(edge).convert('RGB').save(out/'lineart.png')
    manifest={'schema_version':'1.0','persona_digest':persona_digest,'art_status':'placeholder','reference_consent':False,
      'assets':{k:k+('.jpg' if k=='background' else '.png') for k in ['background','subject','spirit','effects','text','lineart']},
      'depths':{'background':-.25,'subject':.4,'effects':.5,'text':0},
      'notes':'Procedural abstract fixture. No person is depicted. This is not finished character artwork.'}
    save(out/'layers.json',manifest)
    return out/'layers.json'

def ImageChops_safe(a,b):
    from PIL import ImageChops
    return ImageChops.subtract(a,b)

def flatten_layers(manifest_path: Path) -> bytes:
    m=load(manifest_path);images={k:Image.open(local_asset(manifest_path.parent,p)).convert('RGBA') for k,p in m['assets'].items()}
    im=compose_layers(m,images,include_text=True)
    stream=io.BytesIO();im.convert('RGB').save(stream,format='JPEG',quality=92);return stream.getvalue()

PERSONAL_TOKENS=('PROFILE','CARD_DATA','CARD_LAYERS','V9_CARD_IMAGE','DEPTH_BG','DEPTH_SUBJECT','DEPTH_EFFECTS')
PERSONAL_RE=re.compile(r'__('+'|'.join(PERSONAL_TOKENS)+r')__')

def template_source_hashes() -> dict[str,str]:
    """Hash exactly the maintained files consumed by the fixed template."""
    import hashlib
    paths=[Path('src')/name for name in ('page.html','app.js','card-art.svg')]
    paths += [Path('src')/(name+'.js') for name in TEMPLATE_MODULES.values()]
    paths += [Path('src')/(name+'.css') for name in TEMPLATE_CSS]
    paths += [Path('assets')/name for _,name in TEMPLATE_MEDIA]
    return {'assets/template/'+path.as_posix():hashlib.sha256((TEMPLATE/path).read_bytes()).hexdigest()
            for path in sorted(paths)}

def template_parts() -> tuple[str,str]:
    """Fixed template with only the per-person tokens left. Shared by the CLI and the browser viewer."""
    src=TEMPLATE/'src'; js=(src/'app.js').read_text()
    for token,file in TEMPLATE_MODULES.items():js=js.replace('__'+token+'__',(src/(file+'.js')).read_text())
    for token,fn in TEMPLATE_MEDIA:
        js=js.replace(token,uri(TEMPLATE/'assets'/fn))
    js=js.replace('__CARD_ART__',safe_script_json((src/'card-art.svg').read_text()))
    css='\n'.join((src/(f+'.css')).read_text() for f in TEMPLATE_CSS)
    html=(src/'page.html').read_text().replace('__CSS__',css).replace('__JS__',js)
    left=set(re.findall(r'__([A-Z][A-Z0-9_]+)__',html))
    check(left<=set(PERSONAL_TOKENS), 'Unexpanded template token: '+', '.join(sorted(left-set(PERSONAL_TOKENS))))
    return html,js

def personal_values(profile: dict, layer_uris: dict, card_image_uri: str, depths: dict) -> dict:
    return {'PROFILE':safe_script_json(profile),'CARD_DATA':safe_script_json(profile['persona']),
            'CARD_LAYERS':safe_script_json(layer_uris),'V9_CARD_IMAGE':card_image_uri,
            'DEPTH_BG':str(depths['background']),'DEPTH_SUBJECT':str(depths['subject']),'DEPTH_EFFECTS':str(depths['effects'])}

def fill(template: str, values: dict) -> str:
    # Single pass: substituted personal text is never rescanned for tokens.
    return PERSONAL_RE.sub(lambda m:values[m.group(1)],template)

def write_site(out: Path, profile: dict, layer_uris: dict, card_image_uri: str, depths: dict) -> str:
    from .template_origin import record_site
    from .template_lock import verify_lock, sha256
    html_t,js_t=template_parts()
    sources=template_source_hashes()
    locked=verify_lock(TEMPLATE,sources,assembled_sha256=sha256(html_t.encode('utf-8')),builder_version=VERSION)
    check(locked['ok'], '固定模板版本校验失败；恢复本次完整发布资源，不在个人任务中重新锁定模板：'+
          ', '.join(e['code'] for e in locked['errors']))
    values=personal_values(profile,layer_uris,card_image_uri,depths)
    html=fill(html_t,values)
    out.mkdir(parents=True,exist_ok=True)
    (out/'index.html').write_bytes(html.encode('utf-8'));(out/'compiled-check.js').write_bytes(fill(js_t,values).encode('utf-8'))
    record_site(out,profile,layer_uris,card_image_uri,depths,html_t,sources)
    return html

CARD_SIZE=(1080,1440)
LITE_DEPTHS={'static':{'background':0,'subject':0,'effects':0,'text':0},
             'portrait':{'background':0,'subject':0,'effects':0,'text':0},
             'layered':{'background':-.25,'subject':.4,'effects':.5,'text':0}}


def _png_uri(im: Image.Image) -> str:
    s=io.BytesIO();im.save(s,format='PNG',optimize=True);return 'data:image/png;base64,'+base64.b64encode(s.getvalue()).decode('ascii')


def _jpeg_uri(im: Image.Image) -> str:
    s=io.BytesIO();im.convert('RGB').save(s,format='JPEG',quality=90);return 'data:image/jpeg;base64,'+base64.b64encode(s.getvalue()).decode('ascii')


def open_card_image(path: Path) -> Image.Image:
    check(path.is_file(),f'找不到图片：{path.name}')
    check(path.stat().st_size<=20*1024*1024,f'{path.name} 超过 20 MB')
    with Image.open(path) as im:
        check(im.format in ('PNG','JPEG','WEBP'),f'{path.name} 必须是 PNG / JPG / WebP')
        check(im.width*im.height<=16_000_000,f'{path.name} 尺寸过大')
        check(min(im.size)>=512,f'{path.name} 太小，短边至少 512 像素，现在 {min(im.size)}')
        im=ImageOps.exif_transpose(im).convert('RGBA')
    return im


def native_subject(path: Path) -> Image.Image:
    """Check the original full-canvas subject. No segmentation, crop or relocation."""
    im=open_card_image(path)
    check(abs(im.width/im.height-.75)<.01,f'{path.name}：主体必须使用完整的 3:4 画布，请按原型坐标重新生成')
    hist=im.getchannel('A').histogram(); total=im.width*im.height
    check(sum(hist[:16])/total>.01,f'{path.name}：需要原生真实 alpha 透明层，请用支持透明输出的生图工具重新生成；不会抠图或移除背景')
    check(sum(hist[16:])/total>.0005,f'{path.name}：主体层为空，请按当前卡面设定重新生成')
    return im


def lite_layers(portrait: Path|None=None, character: Path|None=None, background: Path|None=None, *,
                layers: Path|None=None, expected_persona: str|None=None, prototype: Path|None=None) -> dict:
    """Consume registered native layers; a lone prototype remains a zero-depth static card."""
    check(not (portrait and prototype),'prototype 和 portrait 是同一静态预览的两种名称，请只提供一个')
    portrait=prototype or portrait
    check(not layers or not (portrait or character or background),'layers.json 与单图输入不能同时使用')
    check(not (portrait and (character or background)),'静态原型与独立分层输入二选一')
    check(not background or character,'背景图必须和原生主体层一起使用')
    if layers:
        check(bool(expected_persona),'分层 manifest 必须绑定当前用户的 persona_digest')
        report=validate_layers(layers,expected_persona)
        manifest=load(layers)
        return {'layers':{k:uri(local_asset(layers.parent,p)) for k,p in manifest['assets'].items()},
                'card_image':'data:image/jpeg;base64,'+base64.b64encode(flatten_layers(layers)).decode('ascii'),
                'depths':dict(manifest['depths']),'art_status':manifest['art_status'],
                'art_mode':'placeholder' if manifest['art_status']=='placeholder' else 'layered',
                'art_validation':report,'binding':'persona_digest','native_full_canvas':True}
    clear=_png_uri(Image.new('RGBA',(4,4)))
    layer_data={'background':'auto','subject':clear,'spirit':clear,'effects':'auto','lineart':'auto','text':'auto'}
    if portrait:
        # A prototype contains one composited scene; it must never imply independent depth.
        im=open_card_image(portrait)
        check(abs(im.width/im.height-.75)<.01,'静态原型必须使用完整的 3:4 画布，不会自动裁切或拉伸')
        layer_data['background']=_png_uri(im)
        return {'layers':layer_data,'card_image':'auto','depths':dict(LITE_DEPTHS['static']),
                'art_status':'static','art_mode':'static','art_validation':None,
                'binding':'explicit_current_run_input','native_full_canvas':False}
    if character:
        sub=native_subject(character)
        check(background is not None,'独立主体层还需要完整背景层；仅有主体不能声称分层完成。请生成同画布背景或交付静态原型')
        bg=open_card_image(background)
        check(bg.size==sub.size,'主体和背景必须使用完全相同的画布尺寸与坐标，不会自动裁切或重摆')
        check(bg.getchannel('A').getextrema()==(255,255),'背景层必须完全不透明并画完整场景')
        layer_data['subject']=_png_uri(sub);layer_data['background']=_png_uri(bg)
        return {'layers':layer_data,'card_image':'auto','depths':dict(LITE_DEPTHS['layered']),
                'art_status':'generated','art_mode':'layered','art_validation':{'ok':True,'size':list(sub.size),
                    'native_alpha':True,'same_canvas':True,'visual_review_required':['registered composition','complete background without duplicate subject']},
                'binding':'explicit_current_run_inputs','native_full_canvas':True}
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        placeholder_layers(Path(tmp),'0'*64)
        layer_data['subject']=_png_uri(Image.open(Path(tmp)/'subject.png').convert('RGBA'))
    return {'layers':layer_data,'card_image':'auto','depths':dict(LITE_DEPTHS['layered']),
            'art_status':'placeholder','art_mode':'placeholder','art_validation':None,
            'binding':'none','native_full_canvas':False}


def render_card_preview(data: dict, out: Path, *, layers: Path|None=None,
                        prototype: Path|None=None, portrait: Path|None=None,
                        character: Path|None=None, background: Path|None=None) -> dict:
    """Render a registered front independently of HTML; source layers stay untouched."""
    from .lite import persona_digest
    persona = persona_digest(data)
    art = lite_layers(portrait, character, background, layers=layers, prototype=prototype,
                      expected_persona=persona)
    check(out.suffix.lower() == '.png', '卡片预览输出必须是 PNG')
    sources = [p for p in (layers, prototype, portrait, character, background) if p is not None]
    if layers:
        sources += [local_asset(layers.parent, p) for p in load(layers)['assets'].values()]
    check(all(out.resolve() != p.resolve() and not (out.exists() and out.samefile(p)) for p in sources),
          '卡片预览不能覆盖原型、清单或原生图层')
    if layers:
        manifest = load(layers)
        images = {}
        # validate_layers already checked size/format/alpha. Preserve the native
        # registered coordinates, including valid 256px layers and raw EXIF.
        for role, path in manifest['assets'].items():
            with Image.open(local_asset(layers.parent, path)) as original:
                images[role] = original.convert('RGBA')
        image = compose_layers(manifest,images,include_text=True)
        kind = 'registered_layers'
    elif prototype or portrait:
        image = open_card_image(prototype or portrait)
        kind = 'static_prototype'
    elif character:
        image = Image.alpha_composite(open_card_image(background), native_subject(character))
        kind = 'native_pair'
    else:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = placeholder_layers(Path(tmp), persona)
            manifest = load(manifest_path)
            image = open_card_image(local_asset(Path(tmp), manifest['assets']['background']))
            for role in ('spirit', 'subject', 'effects', 'text'):
                image = Image.alpha_composite(image, open_card_image(local_asset(Path(tmp), manifest['assets'][role])))
        kind = 'placeholder'
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format='PNG')
    return {'ok': True, 'out': str(out), 'sha256': __import__('hashlib').sha256(out.read_bytes()).hexdigest(),
            'canvas': list(image.size), 'persona_digest': persona,
            'art_status': art['art_status'], 'art_mode': art['art_mode'], 'preview_kind': kind}


def build_lite(data: dict, out: Path, *, generated_at: str, confirmed: bool=False,
               portrait: Path|None=None, character: Path|None=None, background: Path|None=None,
               layers: Path|None=None, prototype: Path|None=None) -> dict:
    from .lite import to_profile
    provisional=to_profile(data,generated_at=generated_at)
    art=lite_layers(portrait,character,background,layers=layers,prototype=prototype,
                    expected_persona=provisional['persona']['persona_digest'])
    profile=to_profile(data,generated_at=generated_at,art_status=art['art_status'],art_mode=art['art_mode'],confirmed=confirmed)
    html=write_site(out,profile,art['layers'],art['card_image'],art['depths'])
    save(out/'profile.json',profile)
    report={'ok':True,'mode':'lite','stars':len(profile['chapters']),'planets':len(profile['layout']['topics']),
            'persona_digest':profile['persona']['persona_digest'],'art_status':art['art_status'],'art_mode':art['art_mode'],
            'art_binding':art['binding'],'art_validation':art['art_validation'],'native_full_canvas':art['native_full_canvas'],
            'share_allowed':profile['release']['share_allowed'],
            'html_sha256':__import__('hashlib').sha256(html.encode()).hexdigest(),'html_bytes':len(html.encode()),
            'out':str(out/'index.html')}
    save(out/'build-report.json',report)
    return report


def build(history: dict, analysis: dict, out: Path, *, previous: dict|None=None,
          layers: Path|None=None, approval: dict|None=None) -> dict:
    profile,layout,audit=compile_profile(history,analysis,previous)
    out.mkdir(parents=True,exist_ok=True)
    if layers is None:layers=placeholder_layers(out/'artwork-pending',profile['persona']['persona_digest'])
    art_report=validate_layers(layers,profile['persona']['persona_digest'])
    manifest=load(layers)
    if manifest['art_status']!='placeholder' and analysis['card'] and 'reference_consent' in analysis['card']:
        check(manifest['reference_consent']==analysis['card']['reference_consent'],'Artwork reference consent does not match reviewed persona')
    if approval is not None:
        check_approval(analysis,approval)
        if approval['scope']=='share':check(approval['art_digest']==asset_digest(layers),'Artwork changed after approval; review it again')
    may_share=bool(approval and approval['scope']=='share' and manifest['art_status']=='approved' and analysis['card'])
    profile['release']={'draft':not may_share,'share_allowed':may_share}
    profile['persona']['art_status']=manifest['art_status']
    layer_data={k:uri(local_asset(layers.parent,p)) for k,p in manifest['assets'].items()}
    card_image='data:image/jpeg;base64,'+base64.b64encode(flatten_layers(layers)).decode('ascii')
    # No original export, evidence ledger, private quote or reference photo is copied.
    html=write_site(out,profile,layer_data,card_image,manifest['depths'])
    save(out/'profile.json',profile);save(out/'layout.lock.json',layout)
    build_report={'ok':True,'version':VERSION,'analysis_digest':digest(analysis),'persona_digest':profile['persona']['persona_digest'],
      'stars':len(profile['chapters']),'planets':len(layout['topics']),'art_status':manifest['art_status'],'share_allowed':may_share,
      'html_sha256':__import__('hashlib').sha256(html.encode()).hexdigest(),'html_bytes':len(html.encode()),
      'audit':{k:audit[k] for k in ['ok','user_messages','accounted_user_messages','candidate_facts','active_publishable_facts','cited_facts','extraction_coverage_complete','semantic_truth_verified_by_code']},'art_validation':art_report,'warning':'Draft files still contain personal summaries. A share flag is an application guard, not DRM or proof of consent.'}
    save(out/'build-report.json',build_report)
    return build_report
