"""Offline V10-derived fixed template builder; never calls an image/model API."""
from __future__ import annotations
import base64
import io
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from .common import ROOT, check, load, save, safe_script_json, local_asset, digest
from .compiler import compile_profile, check_approval
from .art import validate_layers, asset_digest

TEMPLATE=ROOT/'assets/template'

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
    im=images['background'].copy()
    for k in ['spirit','subject','effects','text']:im=Image.alpha_composite(im,images[k])
    stream=io.BytesIO();im.convert('RGB').save(stream,format='JPEG',quality=92);return stream.getvalue()

def build(history: dict, analysis: dict, out: Path, *, previous: dict|None=None,
          layers: Path|None=None, approval: dict|None=None) -> dict:
    profile,layout,audit=compile_profile(history,analysis,previous)
    out.mkdir(parents=True,exist_ok=True)
    if layers is None:layers=placeholder_layers(out/'artwork-pending',profile['persona']['persona_digest'])
    art_report=validate_layers(layers,profile['persona']['persona_digest'])
    manifest=load(layers)
    if manifest['art_status']!='placeholder' and analysis['card']:
        check(manifest['reference_consent']==analysis['card']['reference_consent'],'Artwork reference consent does not match reviewed persona')
    if approval is not None:
        check_approval(analysis,approval)
        if approval['scope']=='share':check(approval['art_digest']==asset_digest(layers),'Artwork changed after approval; review it again')
    may_share=bool(approval and approval['scope']=='share' and manifest['art_status']=='approved' and analysis['card'])
    profile['release']={'draft':not may_share,'share_allowed':may_share}
    profile['persona']['art_status']=manifest['art_status']
    src=TEMPLATE/'src'; js=(src/'app.js').read_text()
    modules={'RENDER':'render','CONTROLS':'controls','V6':'v6','V7':'v7','V8':'v8','FINALE':'finale','V9':'v9','HOLO':'holo-card','V10':'v10','ADAPTER':'adapter'}
    for token,file in modules.items():js=js.replace('__'+token+'__',(src/(file+'.js')).read_text())
    for token,fn in [('__TEXTURE__','dust-disc.jpg'),('__SURFACE__','stellar-atlas.jpg'),('__V10_MUSIC__','another-light.mp3')]:
        js=js.replace(token,uri(TEMPLATE/'assets'/fn))
    js=js.replace('__CARD_ART__',safe_script_json((src/'card-art.svg').read_text()))
    js=js.replace('__CARD_DATA__',safe_script_json(profile['persona']))
    js=js.replace('__V9_CARD_IMAGE__','data:image/jpeg;base64,'+base64.b64encode(flatten_layers(layers)).decode('ascii'))
    layer_data={k:uri(local_asset(layers.parent,p)) for k,p in manifest['assets'].items()}
    js=js.replace('__CARD_LAYERS__',safe_script_json(layer_data))
    for token,key in [('BG','background'),('SUBJECT','subject'),('EFFECTS','effects')]:js=js.replace('__DEPTH_'+token+'__',str(manifest['depths'][key]))
    css='\n'.join((src/(f+'.css')).read_text() for f in ['style','v7','v8','v9','v10','adapter'])
    html=(src/'page.html').read_text().replace('__CSS__',css).replace('__PROFILE__',safe_script_json(profile)).replace('__JS__',js)
    check(not re.findall(r'__[A-Z][A-Z_]+__',html), 'Unexpanded template token')
    # No original export, evidence ledger, private quote or reference photo is copied.
    (out/'index.html').write_text(html,encoding='utf-8');(out/'compiled-check.js').write_text(js,encoding='utf-8')
    save(out/'profile.json',profile);save(out/'layout.lock.json',layout)
    build_report={'ok':True,'version':'1.0.0','analysis_digest':digest(analysis),'persona_digest':profile['persona']['persona_digest'],
      'stars':len(profile['chapters']),'planets':len(layout['topics']),'art_status':manifest['art_status'],'share_allowed':may_share,
      'html_sha256':__import__('hashlib').sha256(html.encode()).hexdigest(),'html_bytes':len(html.encode()),
      'audit':{k:audit[k] for k in ['ok','user_messages','accounted_user_messages','candidate_facts','active_publishable_facts','cited_facts','extraction_coverage_complete','semantic_truth_verified_by_code']},'art_validation':art_report,'warning':'Draft files still contain personal summaries. A share flag is an application guard, not DRM or proof of consent.'}
    save(out/'build-report.json',build_report)
    return build_report
