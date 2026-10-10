"""SYNTHETIC contract fixtures. NEVER production review or artwork evidence."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps
from quality_fixtures import save, ref
from twinlight_core.art_quality import sha256
from twinlight_core.lite import persona_digest
from twinlight_core.site import render_card_preview
from preview_card import preview
from package_card import package


def person():
    return {'twinlight':'lite-1','name':'合成测试角色','summarizer':'GPT', 'intro':'仅用于程序测试，不代表真实人物。',
        'themes':[{'label':'测试星体','english':'SYNTHETIC STAR','headline':'这是隔离的测试输入。',
          'story':['这是为了校验装配过程而写的虚构内容。'],'reflection':'不从测试数据推断任何真实身份。',
          'topics':[{'label':'测试事件','summary':'合成示例，仅用于检查。','basis':'once'}]}],
        'card':{'title':'测试卡','english_title':'TEST CARD','keywords':['合成','测试','隔离'],
                'tagline':'这是程序测试，不是实际作品。','reflection':'没有调用真实生图服务或独立视觉审查者。'}}


def native(root, digest):
    root.mkdir(parents=True,exist_ok=True);size=(300,400)
    images={'background':Image.new('RGBA',size,(22,33,44,255))}
    for role in ('subject','effects','text','spirit'):
        images[role]=Image.new('RGBA',size)
    ImageDraw.Draw(images['subject']).rectangle((100,110,210,280),fill=(100,120,140,255))
    ImageDraw.Draw(images['effects']).ellipse((225,275,260,310),fill=(210,200,140,255))
    ImageDraw.Draw(images['text']).rectangle((35,340,260,355),fill=(240,230,210,255))
    alpha=images['subject'].getchannel('A')
    edge=ImageChops.difference(alpha.filter(ImageFilter.MaxFilter(5)),alpha.filter(ImageFilter.MinFilter(5)))
    images['lineart']=ImageOps.invert(edge).convert('RGBA')
    for k,im in images.items():im.save(root/(k+'.png'))
    m={'schema_version':'1.0','persona_digest':digest,'art_status':'generated','reference_consent':False,
       'assets':{k:k+'.png' for k in images},'depths':{'background':-.25,'subject':.4,'effects':.5,'text':0},
       'notes':'SYNTHETIC rectangles; not model-generated art. Used only with mocked gates in tests.'}
    save(root/'layers.json',m);return root/'layers.json'


def card_workspace(root):
    """Build real file bytes, but SYNTHETIC pass flags require mocked art/release gates.

    Without those explicit unittest mocks this fixture must be rejected.
    """
    root.mkdir(parents=True,exist_ok=True)
    data=person();data={k:data[k] for k in ('name','summarizer','card')}|{'twinlight':'card-1'}
    source=root/'content.json';save(source,data);d=persona_digest(data)
    layers=native(root/'card/native',d)
    c=root/'card';render_card_preview(data,c/'front.png',layers=layers)
    preview(layers,c/'preview.html',source);package(layers,c/'card-pack.json',source)
    outputs={k:str(c/name) for k,name in (('card_front','front.png'),('card_preview','preview.html'),('card_pack','card-pack.json'))}
    design=layers.parent/'art-direction.json';save(design,{'version':'art-direction-2','note':'SYNTHETIC stub; cannot pass unmocked design validation.'})
    save(layers.parent/'art-evidence.json',{'design':ref(layers.parent,design)})
    report=root/'browser/card_browser/report.json'
    r={'ok':True,'html_sha256':sha256(c/'preview.html'),
       'checks':[{'name':'SYNTHETIC_BROWSER_FIXTURE','passed':True}],
       'foil_verified':True,'fixed_text_verified':True,'touch_verified':True,'reduced_motion_verified':True,
       'webgl':True,'scope':'SYNTHETIC only. No browser called by this fixture.'}
    save(report,r)
    stage={'status':'passed','invoked_by_runner':True,'report_input_bound':True,
           'input_html_sha256':sha256(c/'preview.html'),'report':str(report),
           'files_sha256':{report.relative_to(root).as_posix():sha256(report)},
           'scope':'SYNTHETIC flags for gate-isolation tests only.'}
    state={'mode':'card','persona_digest':d,'input_sha256':sha256(source),'layers_source':str(layers),
           'stages':{'card_browser':stage}}
    run={'mode':'card','status':'files_ready','complete':True,'dynamic_verified':True,'outputs':outputs,
         'scope':'SYNTHETIC contract test only'}
    receipt={**run,'input_sha256':sha256(source),'draft':True,'share_allowed':False,
             'outputs_sha256':{k:sha256(Path(v)) for k,v in outputs.items()}}
    for name,value in [('run-state',state),('run-report',run),('delivery-report',receipt)]:save(root/(name+'.json'),value)
    return data,layers,outputs
