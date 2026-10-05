"""SYNTHETIC test data, images and records. Not provider calls or aesthetic approval."""
from __future__ import annotations
import base64,json,io,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps,ImageChops,ImageFilter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from twinlight_core.art_quality import sha256,snapshot,REVIEW_CHECKS
from twinlight_core.visual_contract import visual_brief,style_binding,review_checks
PERSONA='a'*64

def save(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def ref(p,root=None):
    p=Path(p);return {'file':p.relative_to(root).as_posix() if root else p.name,'sha256':sha256(p)}

def design(kind='human',style='eastern-fantasy-scroll'):
    s={'kind':kind,'species':'人类','gender_presentation':'female','age_impression':'年轻成年人',
       'appearance':[{'part':'hair','description':'黑色齐耳短发'},{'part':'eyes','description':'深棕眼睛，视线向下'}],
       'clothing':'素白窄袖衬衫','expression':'眉眼放松，嘴角微微上扬','pose':'双手在胸前轻托纸鹤',
       'main_prop':'一只折叠纸鹤','representation':'original_concept',
       'selection_basis':'这是隔离的合成测试形象，不是任何真实用户资料。'}
    if kind in ('animal','anthropomorphic'):
        s.update(species='赤狐',gender_presentation='male',age_impression='成年小型动物',
                 appearance=[{'part':'fur','description':'赤褐毛发，白色胸口'},{'part':'ears','description':'尖耳直立，耳尖深棕'}],
                 clothing='没有衣服和配饰',expression='双眼睁开，鼻尖朝左',pose='前爪并拢坐在石面上',main_prop=None)
    if kind=='object':
        s.update(species='陶瓷小碗',gender_presentation='not_applicable',age_impression='新制完整器物',
                 appearance=[{'part':'surface','description':'青白釉面，细小窑变斑点'},{'part':'shape','description':'圆口浅腹，底足矮而宽'}],
                 clothing='表面没有包布或附件',expression='内壁弧面圆润',pose='平稳放在水平石面上',main_prop=None)
    return {'version':'art-direction-2','persona_digest':PERSONA,'style':{'id':style,'version':'1.0.0'},
            'subject':s,'scene':{'setting':'只有一面浅灰墙和低矮石台','lighting':'左上方柔和散射光，右侧浅阴影',
            'composition':'主体在中央，上方百分之十二和底部百分之二十留白，轮廓完整，不触碰边缘',
            'foreground':['右下角两片小而清晰的叶子']},
            'preferences':{'keep':['轮廓清楚，背景简洁'],'avoid':['网页界面和职业符号'],
            'basis':'Synthetic preferences for contract tests only, not personal data.','rejected_asset_sha256':[]},
            'selection_reason':'Only a synthetic subject for testing four independently versioned drawing templates.',
            'reference_basis':'text_only','references':[],'reference_consent':False,
            'typography':{'text_color':'#FFFFFF','accent_color':'#CCDDEE','scrim_color':'#112233','scrim_opacity':180,'frame':'single','footer_top':.75}}

def images(root,size=(600,800)):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);w,h=size
    bg=Image.new('RGBA',size,(24,38,58,255));d=ImageDraw.Draw(bg)
    for y in range(0,h,20):d.rectangle((0,y,w,y+8),fill=(50+y%90,65+y%60,84,255))
    sub=Image.new('RGBA',size);d=ImageDraw.Draw(sub);d.ellipse((w*.27,h*.22,w*.65,h*.69),fill=(180,124,95,255))
    d.rectangle((w*.4,h*.4,w*.75,h*.56),fill=(110,172,151,255))
    fx=Image.new('RGBA',size);ImageDraw.Draw(fx).ellipse((w*.7,h*.64,w*.78,h*.7),fill=(100,165,224,230))
    spirit=Image.new('RGBA',size);text=Image.new('RGBA',size);d=ImageDraw.Draw(text)
    d.rectangle((w*.18,h*.79,w*.82,h*.84),fill=(235,240,230,255))
    d.text((w*.2,h*.8),'SYNTHETIC TEST ONLY',fill=(12,22,32,255))
    alpha=sub.getchannel('A');line=ImageOps.invert(ImageChops.difference(alpha.filter(ImageFilter.MaxFilter(5)),alpha.filter(ImageFilter.MinFilter(5)))).convert('RGBA')
    ims=dict(background=bg,subject=sub,effects=fx,spirit=spirit,text=text,lineart=line)
    for r,im in ims.items():im.save(root/(r+'.png'))
    merged=bg.copy()
    for r in ('spirit','subject','effects'):merged=Image.alpha_composite(merged,ims[r])
    merged.save(root/'prototype.png');merged.save(root/'composite.png');Image.alpha_composite(merged,text).save(root/'front.png')
    m={'schema_version':'1.0','persona_digest':PERSONA,'art_status':'generated','reference_consent':False,
       'assets':{r:r+'.png' for r in ims},'depths':{'background':-.25,'subject':.4,'effects':.5,'text':0}}
    save(root/'layers.json',m);return m

def uri(p):return 'data:image/png;base64,'+base64.b64encode(Path(p).read_bytes()).decode()

def minimal_embedded(root):
    root=Path(root);m=json.loads((root/'layers.json').read_text());p={'persona_digest':PERSONA,'content_ready':True,'art_mode':'layered','art_status':'generated'}
    layers={r:uri(root/f) for r,f in m['assets'].items()};merged=Image.open(root/'front.png').convert('RGB');buf=io.BytesIO();merged.save(buf,format='JPEG',quality=92)
    flat='data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()
    h='<!doctype html><script id="journeyData" type="application/json">'+json.dumps({'persona':p})+'</script>\n<script>\nconst CARD_PERSONA='+json.dumps(p)+';\nconst HOLO_LAYERS='+json.dumps(layers)+';\nconst V9_CARD_IMAGE='+json.dumps(flat)+';\n</script>'
    (root/'embedded.html').write_text(h,encoding='utf-8');return root/'embedded.html'

def preview(root):
    root=Path(root);m=json.loads((root/'layers.json').read_text());persona={'ready':True,'content_ready':True,'name':'SYNTHETIC TEST','title':'RENDERER FIXTURE','reflection':'No real person or generated artwork is represented.','summarizer':'TEST','art_status':'generated','art_mode':'layered'}
    renderer=(ROOT/'assets/template/src/holo-card.js').read_text();renderer=renderer.replace('__CARD_LAYERS__',json.dumps({r:uri(root/f) for r,f in m['assets'].items()}))
    for k,v in [('BG',-.25),('SUBJECT',.4),('EFFECTS',.5)]:renderer=renderer.replace('__DEPTH_'+k+'__',str(v))
    b=(ROOT/'assets/card-preview/bootstrap.js').read_text().replace('__CARD_DATA__',json.dumps(persona))
    h=(ROOT/'assets/card-preview/page.html').read_text().replace('__STYLE__',(ROOT/'assets/card-preview/style.css').read_text()).replace('__BOOTSTRAP__',b).replace('__RENDERER__',renderer)
    (root/'preview.html').write_text(h,encoding='utf-8');return root/'preview.html'

def dossier(root):
    root=Path(root);images(root);preview(root);d=design();save(root/'art-direction.json',d)
    e={'version':'art-evidence-1','persona_digest':PERSONA,'run_id':'SYNTHETIC-TEST','design':ref(root/'art-direction.json'),
       'images':{},'composite':ref(root/'composite.png'),'reviews':{}}
    for role in ('prototype','background','subject','effects'):
        p=root/(role+'-prompt.txt');p.write_text(visual_brief(d,role),encoding='utf-8');a='SYNTHETIC-ARTIFACT-'+role
        raw=root/(role+'-response.txt');raw.write_text('SYNTHETIC TEST RESPONSE ONLY: '+a)
        call={'version':'image-call-1','kind':'image_tool','tool':'SYNTHETIC-TEST-ADAPTER','call_id':'TEST-'+role,'run_id':e['run_id'],
              'capabilities':{'image_generation':True,'native_transparency':True,'reference_images':True},
              'request':{'role':role,'canvas':[600,800],'transparent':role in ('subject','effects'),'prompt':ref(p),
                         'design_sha256':e['design']['sha256'],'style_binding':style_binding(d),'reference_sha256':[] if role=='prototype' else [sha256(root/'prototype.png')]},
              'response':{'artifact_id':a,'canvas':[600,800],'sha256':sha256(root/(role+'.png'))},'raw_response':ref(raw)}
        c=root/(role+'-call.json');save(c,call);e['images'][role]={**ref(root/(role+'.png')),'mode':'generated','call':ref(c)}
    save(root/'art-evidence.json',e)
    targets,*_=snapshot(root/'layers.json',PERSONA,front=root/'front.png',preview=root/'preview.html')
    for i,n in enumerate(('left','right','mobile')):
        im=Image.open(root/'prototype.png').convert('RGBA');im.putpixel((2,2),(20+i*70,20,80,255));im.save(root/(n+'.png'))
    for st,base in REVIEW_CHECKS.items():
        capture=root/(st+'-observations.txt');capture.write_text('SYNTHETIC REVIEW RECORD FOR UNIT TESTS ONLY. NOT REAL AESTHETIC APPROVAL.')
        r={'stage':st,'targets':targets[st],'observer':'SYNTHETIC TEST','observed_at':'2026-10-05T10:00:00Z','decision':'accept',
           'checks':{k:{'passed':True,'observation':'Synthetic test assertion for '+k} for k in review_checks(d,st,base)},'capture':ref(capture)}
        if st=='final':r['views']={n:ref(root/(n+'.png')) for n in ('left','right','mobile')}
        rp=root/(st+'-review.json');save(rp,r);e['reviews'][st]=ref(rp)
    save(root/'art-evidence.json',e);return root/'layers.json'
