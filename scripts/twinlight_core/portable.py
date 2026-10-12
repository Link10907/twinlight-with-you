"""Native-host-first orchestration; a local CLI never impersonates the host's AI tools.

The host follows next_action until the artifact is delivered. Tool absence is
separate from failed calls, failed art, optional review infrastructure and API
credentials. Strict task-card/task-site contracts remain unchanged elsewhere.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from .common import check, load, save, digest, local_asset, ROOT
from . import galaxy_only, lite
from .art import validate_layers, asset_digest
from .site import build_lite, render_card_preview

VERSION='v10-portable-1.0'
STATUSES={'available','unavailable','unknown','temporarily_blocked'}
CHECKS={
 'card':('subject_and_style','prototype_consistency','native_layers_and_alpha','typography_and_attribution','composition_and_depth'),
 'site':('content_and_privacy','galaxy_navigation','ending_and_return','same_card_or_no_card','layout_and_readability'),
 'site-source':('content_and_privacy','template_and_assets','navigation_code','ending_code','card_feature_absent')}

def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def route(capabilities: dict) -> dict:
    check(isinstance(capabilities,dict),'Capabilities must be an object')
    image=capabilities.get('image',{});status=image.get('status','unknown')
    check(status in STATUSES,'Invalid image capability state')
    files=capabilities.get('files',{}).get('status','unknown')
    reviewer=capabilities.get('reviewer',{}).get('mode','self')
    check(reviewer in ('independent','self','unavailable'),'Invalid reviewer mode')
    base={'version':VERSION,'policy':'portable','image_status':status,'review_mode':reviewer,
          'image_route':'native_host_tool','requires_api_key':False,
          'strict_independent_review':False,'browser_is_generation_prerequisite':False,
          'context_isolation':image.get('context_isolation','unknown'),
          'scope':'Host-declared available tools, not proof of tool execution.'}
    if files=='unavailable':
        return base|{'mode':None,'status':'artifact_capability_blocked','next_action':'Use a genuinely available artifact/code execution tool; do not claim file delivery or substitute a fake download.'}
    if status=='unknown':
        return base|{'mode':None,'status':'inspect_image_tools','next_action':'Inspect native image tool availability in this session. Do not infer absence from brand or missing API credentials; do not ask the user to configure an API.'}
    if status=='temporarily_blocked':
        return base|{'mode':None,'status':'image_temporarily_blocked','next_action':'Report the actual quota/permission/transient restriction. This is not no-image capability; do not silently switch to HTML-only.'}
    if status=='unavailable':
        check(bool(str(image.get('reason','')).strip()),'Unavailable image capability requires an observed reason')
        return base|{'mode':'html-only','status':'ready','card_enabled':False,'next_action':'Build the card-free V10 galaxy; do not load CARD.md or create any card assets.'}
    return base|{'mode':'full','status':'ready','card_enabled':True,'next_action':'Host runs native image generation and review for task A, then embeds the same card in task B without per-step confirmation.'}

def review_check(path: Path, stage: str, target: str, preferred: str, *, allow_source: bool=False) -> dict:
    if not path.is_file():return {'ok':False,'status':'review_required','stage':stage,'target_sha256':target}
    r=load(path)
    check(r.get('stage')==stage and r.get('target_sha256')==target,'Review is stale or targets another artifact')
    method=r.get('method');source_only=allow_source and stage=='site' and method=='source'
    check(method in ('independent','self') or source_only,'Source-only review is permitted only for the no-card site; card work requires actual visual observation')
    if preferred=='unavailable' and not source_only:check(False,'No visual review capability was available; do not fabricate an assessment')
    if method=='independent':check(bool(r.get('execution_ref')),'Independent review needs an actual task reference; unavailable platform IDs may be described truthfully')
    check(isinstance(r.get('observations'),str) and len(r['observations'].strip())>=12,'Review needs actual visual observations')
    keys=CHECKS['site-source'] if source_only else CHECKS[stage]
    checks=r.get('checks',{});check(all(k in checks for k in keys),'Incomplete review checklist')
    check(r.get('verdict') in ('accept','revise','blocked'),'Invalid review verdict')
    accepted=r['verdict']=='accept' and all(checks[k] is True for k in keys)
    return {'ok':accepted,'status':'accepted' if accepted else r['verdict'],'stage':stage,
            'method':method,'independent_review_performed':method=='independent','visual_review_performed':not source_only,
            'target_sha256':target,'receipt_sha256':fingerprint(path),
            'scope':('Source/structure assessment only; no visual approval.' if source_only else 'Recorded visual assessment; hash binding is not provider authentication.')}

def generation_check(path: Path, layers: Path) -> dict:
    check(path.is_file(),'Native generation record is missing; no generated image call can be inferred from files alone')
    r=load(path);check(r.get('origin')=='native_image_tool','Only actual native image-tool outputs are accepted')
    check(isinstance(r.get('tool'),str) and r['tool'].strip(),'Record the actually used tool')
    check(r.get('prototype_review') in ('independent','self'),'The original prototype must actually have been visually reviewed')
    check(r.get('prototype_verdict')=='accept','Prototype has not passed visual review')
    check(bool(r.get('prototype_observations')),'Missing observations of the original prototype')
    prototype=local_asset(path.parent,r.get('prototype_file',''))
    check(prototype.is_file() and fingerprint(prototype)==r.get('prototype_sha256'),'Original prototype bytes missing or changed')
    m=load(layers);actual={role:fingerprint(local_asset(layers.parent,m['assets'][role])) for role in ('background','subject','effects')}
    check(r.get('layers_sha256')==actual,'Generated layers differ from native tool record')
    check(r.get('context_isolation') in ('explicit_narrow_task','contextual_native_tool'),'Record the real image context boundary')
    check(r.get('verdict')=='accept','Native layers have not passed visual comparison with the prototype')
    check(bool(r.get('layer_observations')),'Missing native-layer visual observations')
    return {'ok':True,'record_sha256':fingerprint(path),'prototype_sha256':fingerprint(prototype),
            'layers_sha256':actual,'context_isolation':r['context_isolation'],
            'scope':'Host-recorded native calls and byte consistency; no synthetic provider IDs or cryptographic origin claim.'}

def _state(workspace: Path, source: Path, chosen: dict) -> dict:
    workspace.mkdir(parents=True,exist_ok=True);path=workspace/'portable-state.json';input_hash=fingerprint(source)
    if path.exists():
        state=load(path);check(state['input_sha256']==input_hash,'Frozen content changed; keep the old run and create a new version')
        check(state['mode']==chosen['mode'],'Do not silently change a running full task into HTML-only')
        return state
    state={'version':VERSION,'mode':chosen['mode'],'input_sha256':input_hash,
           'created_at':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'started','input_path':str(source.resolve())}
    save(path,state);return state

def run(source: Path, workspace: Path, capabilities: dict, *, layers: Path|None=None) -> dict:
    chosen=route(capabilities)
    if chosen['status']!='ready':return chosen|{'complete':False}
    state=_state(workspace,source,chosen);mode=chosen['mode'];data=load(source)
    save(workspace/'capabilities.json',capabilities)
    state['layers_path']=str(layers.resolve()) if layers else None
    save(workspace/'portable-state.json',state)
    result={'version':VERSION,'mode':mode,'card_enabled':mode=='full','complete':False,
            'route':chosen,'image_calls_performed_by_cli':0,'private_by_default':True}
    if mode=='html-only':
        folder=workspace/'site-task/site';html=folder/'index.html'
        if not html.is_file():galaxy_only.build(data,folder,generated_at=state['created_at'])
        galaxy_only.verify(folder)
    else:
        checked=lite.check_text(json.dumps(data,ensure_ascii=False));check(checked['ok'],'Full mode needs valid lite content including card text')
        data=checked['data']
        if layers is None:
            result.update(status='native_image_generation_required',next_action='Read CARD.md. The host must call its native image tool, inspect the prototype and native layers, then resume with --layers. Do not call execution.py doctor or require an API key in portable mode.')
            save(workspace/'portable-report.json',result);return result
        check(layers.resolve().is_relative_to(workspace.resolve()),'Keep A assets inside this private workspace')
        validation=validate_layers(layers,lite.persona_digest(data))
        check(validation['art_status'] in ('generated','approved'),'Static art, examples and placeholders are not finished cards')
        generation=generation_check(workspace/'generation.json',layers)
        from preview_card import preview
        from package_card import package
        card=workspace/'card-task/card';card.mkdir(parents=True,exist_ok=True)
        # Deterministic packaging preserves the native image bytes.
        render_card_preview(data,card/'front.png',layers=layers)
        preview(layers,card/'preview.html',source);package(layers,card/'card-pack.json',source)
        card_target=digest({'art':asset_digest(layers),'preview':fingerprint(card/'preview.html'),'front':fingerprint(card/'front.png'),'pack':fingerprint(card/'card-pack.json'),'generation':generation})
        reviewed=review_check(workspace/'review-card.json','card',card_target,chosen['review_mode'])
        result['card_review']=reviewed
        if not reviewed['ok']:
            result.update(status=reviewed['status'],next_action='Visually inspect A front/layers and available interactive preview; write the real review-card.json for the displayed target. Revise failed assets, not the acceptance rules.')
            save(workspace/'portable-report.json',result);return result
        folder=workspace/'site-task/site';html=folder/'index.html'
        cached=state.get('card_target')
        if not html.is_file() or cached!=card_target:
            build_lite(data,folder,generated_at=state['created_at'],layers=layers,navigation=True)
            state['card_target']=card_target;save(workspace/'portable-state.json',state)
        from .template_origin import verify_site
        check(verify_site(folder)['ok'],'Full V10 template verification failed')
        from .embedded_card import audit_embedding,audit_renderer
        pack=load(card/'card-pack.json')
        check(audit_embedding(html,layers,lite.persona_digest(data))['ok'],'Embedded card bytes changed')
        check(audit_renderer(html,layers)['ok'],'Embedded card renderer changed')
        result['card_digest']=card_target
    site_target=fingerprint(html);reviewed=review_check(workspace/'review-site.json','site',site_target,chosen['review_mode'],allow_source=mode=='html-only')
    result.update(site_review=reviewed,html_sha256=site_target,files_built=True)
    if not reviewed['ok']:
        result.update(status=reviewed['status'],next_action='Check the actual site and all available runtime/visual checks, then record review-site.json. No card is expected in html-only mode; if visual tools are absent, use the documented source-only site checklist and do not claim visual approval. Self review is not independent review.')
        save(workspace/'portable-report.json',result);return result
    # Runtime evidence is reported separately. Missing WebGL cannot turn into a
    # successful GPU test, and a known functional failure cannot be released.
    runtime=load(workspace/'runtime-check.json') if (workspace/'runtime-check.json').is_file() else {'status':'unavailable','reason':'No runtime check was recorded','webgl':'unverified','offline_file_open':'unverified'}
    check(runtime.get('status') in ('passed','limited','unavailable'),'Known runtime failure blocks release; fix it first')
    check(not any(c.get('passed') is False for c in runtime.get('checks',[]) if isinstance(c,dict)), 'Known functional check failure blocks release')
    if runtime.get('status')!='unavailable':check(runtime.get('html_sha256')==site_target,'Runtime check targets stale HTML')
    result.update(runtime=runtime,status='ready_for_delivery',complete=True,
                  all_checks_passed=(reviewed['method']!='source' and runtime.get('status')=='passed' and runtime.get('webgl')=='passed' and runtime.get('offline_file_open')=='passed'),
                  validation_level='independent_visual' if reviewed['method']=='independent' else ('source_review_only' if reviewed['method']=='source' else 'host_self_review'),
                  next_action='Use portable.py deliver to export only this released HTML and its same-card artifacts. State any unverified browser/WebGL capability accurately.')
    state['status']='ready_for_delivery';save(workspace/'portable-state.json',state);save(workspace/'portable-report.json',result)
    return result

def deliver(workspace: Path, out: Path) -> dict:
    previous=load(workspace/'portable-report.json');check(previous.get('complete') is True,'Current portable run is not ready for delivery')
    state=load(workspace/'portable-state.json')
    r=run(Path(state['input_path']),workspace,load(workspace/'capabilities.json'),layers=Path(state['layers_path']) if state.get('layers_path') else None)
    check(r.get('complete') is True,'Current artifact no longer passes portable gates')
    src=workspace/'site-task/site/index.html';check(fingerprint(src)==r['html_sha256'],'Site changed after review')
    check(review_check(workspace/'review-site.json','site',r['html_sha256'],r['route']['review_mode'],allow_source=r['mode']=='html-only')['ok'],'Site review is not accepted')
    check(not out.exists() or not any(out.iterdir()),'Delivery directory must be new or empty')
    out.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,out/'index.html')
    files=['index.html']
    if r['mode']=='full':
        c=workspace/'card-task/card'
        for source,target in [('preview.html','card-preview.html'),('front.png','card-front.png'),('card-pack.json','card-pack.json')]:
            shutil.copyfile(c/source,out/target);files.append(target)
    summary={'version':VERSION,'mode':r['mode'],'card_enabled':r['card_enabled'],'validation_level':r['validation_level'],
             'all_checks_passed':r['all_checks_passed'],'webgl':r['runtime'].get('webgl','unverified'),
             'offline_file_open':r['runtime'].get('offline_file_open','unverified'),
             'files_sha256':{name:fingerprint(out/name) for name in files},'share_authorized':False}
    save(out/'delivery.json',summary)
    (out/'README.txt').write_text('Twinlight 私人作品\n打开 index.html。主文件不依赖旁边资源。\n'+('本次是完整无卡星系版，没有闪卡，也没有待生成卡位。\n' if r['mode']=='html-only' else '主 HTML 内嵌本次已审查同一卡片。\n')+'审查范围和未验证项见 delivery.json；分享前请检查个人内容。\n',encoding='utf-8')
    files+=['delivery.json','README.txt'];zip_path=out.parent/(out.name+'.zip')
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        for name in files:z.write(out/name,name)
    return {'ok':True,'mode':r['mode'],'html':str(out/'index.html'),'zip':str(zip_path),'files':files}
