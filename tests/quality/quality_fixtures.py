"""SYNTHETIC TEST FIXTURES ONLY. No real image provider or reviewer is invoked."""
from pathlib import Path
import sys,json,copy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from PIL import Image
from twinlight_core.host_contract import template
from twinlight_core.visual_contract import default_style,DEFAULT_STYLE
from twinlight_core.art_quality import sha256
from twinlight_core.independent_review import canonical_sha,release_targets,release_checks
PERSONA='a'*64


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def host():
    v=template();v.update(host='SYNTHETIC_TEST_HOST',producer_session_id='SYNTHETIC_PRODUCER')
    v['image'].update(tool='SYNTHETIC_IMAGE_TOOL',source='SYNTHETIC capability declaration for unit tests only.',
        image_generation=True,reference_images=True,native_transparency=True,native_image_editing=True,
        post_image_continuation=True,prompt_transport='explicit_prompt',reference_transport='explicit_attachments',
        native_canvases=[[600,800]],canvas_selection='native_sizes')
    v['reviewer'].update(tool='SYNTHETIC_REVIEW_TOOL',source='SYNTHETIC reviewer declaration; not a deployed agent.',
        isolated_session=True,read_only_inputs=True,visual_inputs=True,runtime_evidence=True)
    v['runtime'].update(browser=True,webgl=True,source='SYNTHETIC runtime; not a real browser check.')
    return v


def ref(root,path):
    return {'file':Path(path).relative_to(root).as_posix(),'sha256':sha256(Path(path))}


def sign(root,review,tag='test'):
    """Make a clearly synthetic consistency fixture, not provider authentication."""
    raw={k:v for k,v in review.items() if k!='handoff'}
    rp=root/(tag+'-raw.json');save(rp,raw)
    trace={'producer_session_id':'SYNTHETIC_PRODUCER','reviewer_session_id':'SYNTHETIC_REVIEWER',
           'invocation_id':'SYNTHETIC_INVOCATION','context':'isolated','read_only_artifacts':True,
           'scope_sha256':canonical_sha(raw['targets']),'raw_response':ref(root,rp)}
    tp=root/(tag+'-trace.json');save(tp,trace)
    return {**raw,'handoff':{**{k:trace[k] for k in ('producer_session_id','reviewer_session_id','invocation_id','context','read_only_artifacts')},
                           'mode':'independent_agent','trace':ref(root,tp)}}


def release(root,mode='card'):
    outputs={}
    keys={'card':('card_front','card_preview','card_pack'),'html':('html',),
          'both':('html_with_card','card_front','card_preview','card_pack')}[mode]
    for k in keys:
        p=root/(k+('.png' if k=='card_front' else '.html' if 'html' in k or k=='card_preview' else '.json'))
        if k=='card_front':Image.new('RGB',(60,80),(40,50,60)).save(p)
        else:p.write_text('SYNTHETIC fixture for '+k)
        outputs[k]=str(p)
    captures={}
    for k,size in [('desktop',(100,80)),('mobile',(50,90))]:
        p=root/(k+'.png');Image.new('RGB',size,(30,40,60)).save(p);captures[k]=ref(root,p)
    primary={'card':'card_preview','both':'html_with_card','html':'html'}[mode]
    r={'stage':'release','targets':release_targets(root,outputs,mode),'decision':'accept','blockers':[],
       'checks':{k:{'passed':True,'observation':'SYNTHETIC condition fixture, not an actual visual inspection.'} for k in release_checks(mode)},
       'captures':captures,'runtime':{'html_sha256':sha256(Path(outputs[primary])),
        'backend':'webgl','webgl_ready':True,'fallback':False,'page_ready':True,'merge_seconds':12},'effect_frames':{}}
    for name in ('foil','depth'):
        for active in (False,True):
            k=name+('_on' if active else '_off');p=root/(k+'.png')
            Image.new('RGB',(60,80),(60,80,90) if active else (20,30,40)).save(p)
            state={'x':.1,'y':.4,'depth':0,'foil':0,'time':0,'finish':0,'viewport':[1440,900], 'paused':True,'region':'card'}
            state[name]=1 if active else 0
            r['effect_frames'][k]={'image':ref(root,p),'state':state}
    r=sign(root,r);save(root/'release-review.json',r)
    return outputs,r


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
            'typography':dict(default_style()['typography_default']) if style == DEFAULT_STYLE else {'text_color':'#FFFFFF','accent_color':'#CCDDEE','scrim_color':'#112233','scrim_opacity':180,'frame':'single','footer_top':.75}}
