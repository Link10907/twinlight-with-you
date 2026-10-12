"""A card-free projection of locked V10; no placeholder or card asset is created.

Original source files and their lock stay unchanged. Projection rules below are
versioned separately and fail closed when source anchors no longer match.
"""
from __future__ import annotations
import copy, hashlib, json, re
from pathlib import Path
from .common import ROOT, VERSION, check, load, save, safe_script_json
from . import lite
from .site import TEMPLATE, TEMPLATE_MODULES, TEMPLATE_CSS, TEMPLATE_MEDIA, uri, template_parts, template_source_hashes
from .template_lock import verify_lock, sha256

PROJECTION_VERSION = 'galaxy-only-1'

def one(s: str, old: str, new: str) -> str:
    check(s.count(old) == 1, 'V10 projection anchor changed: ' + old[:70])
    return s.replace(old, new, 1)

def before(s: str, anchor: str) -> str:
    check(s.count(anchor) == 1, 'V10 projection boundary changed: ' + anchor)
    return s.split(anchor, 1)[0]

def validate_content(data: dict) -> dict:
    """No card/persona is required or synthesized for a galaxy-only run."""
    check(isinstance(data, dict), 'Expected a content object')
    clean = lite.normalize(copy.deepcopy(data)); clean.pop('card', None)
    sch = copy.deepcopy(lite.schema()); sch['required'].remove('card'); sch['properties'].pop('card', None)
    errors = []; lite._walk(clean, sch, '', 'Twinlight galaxy', errors); lite._semantic(clean, errors)
    check(not errors, 'Invalid galaxy content: ' + '; '.join(e['path'] + ': ' + e['message'] for e in errors[:8]))
    return clean

def assemble(profile: dict) -> tuple[str,str,dict]:
    original, _ = template_parts(); sources = template_source_hashes()
    locked = verify_lock(TEMPLATE, sources, assembled_sha256=sha256(original.encode()), builder_version=VERSION)
    check(locked['ok'], 'Original V10 template lock failed')
    src = TEMPLATE/'src'; modules = {k:(src/(v+'.js')).read_text() for k,v in TEMPLATE_MODULES.items()}
    v8 = before(modules['V8'], '// Art and typography are separate assets;')
    v8 = re.sub(r'^const (?:CARD_ART|CARD_PERSONA|v8Baseline|v8xml|v8URI)=.*\n', '', v8, flags=re.M)
    # V8 planet geometry and V9 point-map motion are retained verbatim.
    modules['V8'] = v8 + '\n' + (ROOT/'assets/galaxy-only/before-finale.js').read_text()
    modules['V9'] = before(modules['V9'], '// The compiler supplies the current person')
    modules['HOLO'] = ''
    v10 = before(modules['V10'], 'const providerRefresh=refreshIdentity;')
    v10 = one(v10, "newMusicButton($('encounterCinema'));const topSound=el('div');topSound.style.display='flex';topSound.style.alignItems='center';$('identityClose').before(topSound);newMusicButton(topSound,true);topSound.append($('identityClose'));", "newMusicButton($('encounterCinema'));")
    v10 = one(v10, ' if(v8.cardOpen)hideIdentityCard();\n', '')
    v10 = one(v10, "$('cinemaReplay').onclick=$('cardReplay').onclick=", "$('cinemaReplay').onclick=")
    v10 = one(v10, ";$('v8CardShortcut').onclick=()=>{quietMenu(false);if(state.flight)finishFlight();showIdentityCard();};", ';')
    old="if(question){const name=summarizerInfo().name;$('v10Question').replaceChildren(document.createTextNode(name?'在 '+name+' 眼中，':'从你的成长轨迹里，'),document.createElement('br'));const s=el('span','','你是什么样的？');$('v10Question').append(s);}"
    new="if(question){$('v10Question').replaceChildren(document.createTextNode('我们与 AI 相聚，'),document.createElement('br'));$('v10Question').append(el('span','','故事仍在继续。'));}"
    v10=one(v10,old,new)
    v10=v10.replace('你留下的提问与尝试，<br>在另一束光里，成为了一幅画像。','走过的路与未完的探索，<br>都在这片星空里，留下自己的光。')
    v10=v10.replace("question?(summarizerInfo().name? summarizerInfo().name+' 眼中的你':'成长画像揭晓')", "question?'故事仍在继续'")
    v10=v10.replace('showIdentityCard','finishGalaxyFinale').replace('hideIdentityCard','closeGalaxyEnding')
    v10=v10.replace('揭晓我的闪卡','返回我的星系').replace('跳到揭晓 →','跳到终章 →').replace("v10.phase='card'","v10.phase='finished'").replace("?'question':'card'","?'ending':'finished'")
    v10=v10.replace("b.onclick=()=>finishGalaxyFinale();", "b.onclick=()=>closeGalaxyEnding();")
    modules['V10']=v10+'\n'+(ROOT/'assets/galaxy-only/after-finale.js').read_text()
    adapter=before(modules['ADAPTER'], '// A registered native layer set belongs')
    modules['ADAPTER']=adapter+'\n'+(ROOT/'assets/galaxy-only/adapter.js').read_text()
    js=(src/'app.js').read_text()
    for token, contents in modules.items():js=js.replace('__'+token+'__',contents)
    for token,filename in TEMPLATE_MEDIA:js=js.replace(token,uri(TEMPLATE/'assets'/filename))
    css='\n'.join((src/(name+'.css')).read_text() for name in TEMPLATE_CSS)
    css+='\n'+(ROOT/'assets/galaxy-only/style.css').read_text()
    page=(src/'page.html').read_text()
    page,n=re.subn(r'<section id="identityScene"[\s\S]*?</section>\s*<dialog id="cardExportReview"[\s\S]*?</dialog>', '', page, count=1)
    check(n==1,'Card DOM projection boundary changed')
    page=page.replace('<html ', '<html data-twinlight-mode="galaxy-only" ',1)
    page=page.replace('__CSS__',css).replace('__JS__',js).replace('__PROFILE__',safe_script_json(profile))
    check(not re.search(r'__[A-Z][A-Z0-9_]+__',page),'Unexpanded card-free template token')
    check('id="identityScene"' not in page and 'id="cardExportReview"' not in page,'Unexpected card DOM')
    receipt={'projection':PROJECTION_VERSION,'base_template_lock':locked,'base_sources_sha256':sources,
             'projection_sources_sha256':projection_hashes(),'html_sha256':sha256(page.encode()),
             'card_enabled':False,'card_assets_created':False,
             'scope':'Card-free V10 projection, not full-card template equivalence or visual acceptance.'}
    return page,js,receipt

def projection_hashes() -> dict:
    paths=[Path(__file__)]+sorted((ROOT/'assets/galaxy-only').glob('*'))
    return {p.relative_to(ROOT).as_posix():sha256(p.read_bytes()) for p in paths if p.is_file()}

def build(data: dict, out: Path, *, generated_at: str) -> dict:
    clean=validate_content(data)
    profile=lite.to_profile(clean,generated_at=generated_at,include_card=False)
    profile['features']={'card':False}; profile['persona']=None
    profile['release']={'draft':True,'share_allowed':False,'scope':'private_generated_work'}
    html,js,receipt=assemble(profile);out.mkdir(parents=True,exist_ok=True)
    (out/'index.html').write_text(html,encoding='utf-8');(out/'app.js').write_text(js,encoding='utf-8')
    save(out/'profile.json',profile);save(out/'galaxy-receipt.json',receipt)
    report={'ok':True,'mode':'html-only','card_enabled':False,'card_assets_created':False,
            'files_built':True,'visual_review':'not_performed','browser_validation':'not_performed',
            'html_sha256':receipt['html_sha256'],'stars':len(profile['chapters']),
            'planets':len(profile['layout']['topics']),'out':str(out/'index.html')}
    save(out/'build-report.json',report);return report

def verify(out: Path) -> dict:
    receipt=load(out/'galaxy-receipt.json');profile=load(out/'profile.json')
    expected,_,_=assemble(profile)
    check(receipt['projection']==PROJECTION_VERSION,'Wrong projection version')
    check(receipt['projection_sources_sha256']==projection_hashes(),'Projection source changed')
    check((out/'index.html').read_text()==expected,'Card-free page differs from current V10 projection')
    check(receipt['html_sha256']==sha256(expected.encode()),'Card-free HTML fingerprint changed')
    return {'ok':True,'card_enabled':False,'html_sha256':receipt['html_sha256']}
