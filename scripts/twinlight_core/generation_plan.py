"""Auditable host handoff. Never calls a provider, cuts an image, or approves art."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image

from .visual_contract import (VERSION, VisualContractError, validate_design, style_binding,
                              subject_prompt, visual_keywords, layer_prompt, _json, sha256)

IMAGE_ROLES = ('prototype', 'background', 'subject', 'effects')
MAX_BYTES = 24 * 1024 * 1024


def _save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temp.replace(path)


def _ref(path: Path, root: Path) -> dict:
    if not path.resolve().is_relative_to(root.resolve()):
        raise VisualContractError('evidence_path', 'Evidence must be staged inside this card directory')
    return {'file':path.resolve().relative_to(root.resolve()).as_posix(), 'sha256':sha256(path)}


def _canvas(value) -> tuple[int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 2 or any(type(x) is not int for x in value):
        raise VisualContractError('canvas', 'Canvas must contain two integer dimensions')
    w,h=value
    if min(w,h)<256 or w*h>16_000_000 or abs(w/h-.75)>=.01:
        raise VisualContractError('canvas', 'This renderer requires a native 3:4 portrait. Do not crop, pad, stretch or resample to fake it.')
    return w,h


def check_capabilities(value: dict, canvas) -> dict:
    if not isinstance(value, dict) or value.get('version') != 'image-capabilities-1':
        raise VisualContractError('capabilities_missing', 'Record the actual current host image interface before generation')
    for key in ('image_generation','reference_images','native_transparency'):
        if value.get(key) is not True:
            raise VisualContractError('capability_unavailable', 'Native card generation requires actual ' + key)
    if not isinstance(value.get('source'), str) or len(value['source'].strip())<8:
        raise VisualContractError('capability_source', 'Explain how the currently available tool capability was checked')
    canvases=value.get('native_canvases')
    if not isinstance(canvases,list) or list(canvas) not in canvases:
        raise VisualContractError('native_canvas_unavailable', 'Selected native canvas is not in the observed supported sizes; do not fix it by image processing')
    for size in canvases:
        if not isinstance(size,list) or len(size)!=2 or any(type(n) is not int or n<1 for n in size):
            raise VisualContractError('capability_canvas', 'Invalid capability canvas list')
    return value


def write_plan(design_path: Path, out: Path, *, phase: str='prototype', canvas=(1080,1440),
               capabilities: dict | None=None) -> dict:
    design_path, out = Path(design_path).resolve(), Path(out).resolve()
    design = validate_design(_json(design_path))
    if phase not in ('prototype','layers'): raise VisualContractError('phase','Use prototype or layers')
    canvas = _canvas(canvas)
    prototype_ref = None
    if phase == 'layers':
        from .art_quality import check_evidence, checked_ref, read_json
        evidence = read_json(out/'art-evidence.json')
        if evidence.get('design',{}).get('sha256') != sha256(design_path):
            raise VisualContractError('design_changed','Layer generation cannot inherit approval from another design')
        gate = check_evidence(out/'layers.json', design['persona_digest'], stage='prototype')
        if gate.get('ok') is not True:
            raise VisualContractError('prototype_not_reviewed','Inspect and accept the actual wordless prototype before requesting layers: '+str(gate['errors']))
        proto = checked_ref(out,evidence['images']['prototype'])
        with Image.open(proto) as im: canvas=_canvas(im.size)
        prototype_ref = _ref(proto,out)
    if capabilities is not None: check_capabilities(capabilities,canvas)
    existing=out/'art-evidence.json'
    if existing.exists() and _json(existing).get('design',{}).get('sha256') != sha256(design_path):
        raise VisualContractError('design_changed','Start a new card-art directory for a changed visual design; preserve earlier evidence')
    for ref in design['references']:
        p=(out/ref['file']).resolve()
        if not p.is_relative_to(out) or not p.is_file() or sha256(p)!=ref['sha256']:
            raise VisualContractError('reference_not_staged','Stage actual reference images in the card directory before compiling')
    out.mkdir(parents=True,exist_ok=True)
    target=out/'art-direction.json'
    if target != design_path:
        if target.exists() and target.read_bytes()!=design_path.read_bytes():
            raise VisualContractError('design_conflict','Do not overwrite another visual direction')
        shutil.copyfile(design_path,target)
    style=style_binding(design)
    # A generation plan is an instruction, not proof that a tool call happened.
    jobs=[]
    roles=('prototype',) if phase=='prototype' else ('background','subject','effects')
    prompt_dir=out/'prompts';prompt_dir.mkdir(exist_ok=True)
    for role in roles:
        path=prompt_dir/(role+'.txt')
        path.write_text(layer_prompt(design,role,canvas)+'\n',encoding='utf-8')
        jobs.append({'role':role,'prompt':_ref(path,out),'requested_canvas':list(canvas),
                     'transparent':role in ('subject','effects'),
                     'reference_sha256':([prototype_ref['sha256']] if prototype_ref else [])+
                                         [x['sha256'] for x in design['references']],
                     'style_binding':style,'status':'not_called'})
    plan={'version':'generation-plan-2','phase':phase,'persona_digest':design['persona_digest'],
          'design':_ref(target,out),'style_binding':style,'canvas':list(canvas),
          'prototype':prototype_ref,'jobs':jobs,'capabilities':capabilities,
          'ready_for_image_call':capabilities is not None,
          'required_artwork':'native_layered','subject_count':1,'main_prop_limit':1,
          'spirit':'empty_same_canvas_no_image_call','independent_typography':True,
          'image_generation_performed':False,'requires_host_tool_call':True,
          'next_action':'call_prototype_image_tool' if phase=='prototype' else 'call_native_layer_image_tools',
          'limits':['This is a host handoff, not an authenticated provider call.',
                    'Do not send personal history, narrative keywords or the whole skill manual to the image tool.']}
    (out/'subject-description.txt').write_text(subject_prompt(design)+'\n',encoding='utf-8')
    _save(out/'visual-keywords.json',{'visual_keywords':visual_keywords(design),'derived_from':'subject_fields_only'})
    _save(out/'generation-plan.json',plan)
    return plan


def register_image(plan_path: Path, role: str, image_path: Path, raw_response: Path, *,
                   tool: str, call_id: str, artifact_id: str) -> dict:
    """Copy original output bytes and register an observed response. No synthetic calls."""
    plan_path=Path(plan_path).resolve();root=plan_path.parent
    plan=_json(plan_path)
    if plan.get('version')!='generation-plan-2' or plan.get('ready_for_image_call') is not True:
        raise VisualContractError('plan_not_ready','Validate real image capabilities before using this plan')
    jobs=[j for j in plan.get('jobs',[]) if j.get('role')==role]
    if role not in IMAGE_ROLES or len(jobs)!=1:
        raise VisualContractError('wrong_phase','This phase does not permit that image role')
    job=jobs[0];design_path=(root/plan['design']['file']).resolve()
    if not design_path.is_relative_to(root) or sha256(design_path)!=plan['design']['sha256']:
        raise VisualContractError('design_changed','Design changed after prompt compilation')
    design=validate_design(_json(design_path),plan['persona_digest'])
    if style_binding(design)!=plan['style_binding'] or job['style_binding']!=plan['style_binding']:
        raise VisualContractError('style_drift','Style changed after prompt compilation')
    prompt=(root/job['prompt']['file']).resolve()
    if not prompt.is_relative_to(root) or sha256(prompt)!=job['prompt']['sha256']:
        raise VisualContractError('prompt_changed','Prompt changed after compilation')
    canvas=_canvas(plan['canvas']);check_capabilities(plan['capabilities'],canvas)
    image_path,raw_response=Path(image_path).resolve(),Path(raw_response).resolve()
    if not image_path.is_file() or image_path.stat().st_size>MAX_BYTES:
        raise VisualContractError('image_file','Actual tool output is missing or oversized')
    if not raw_response.is_file() or raw_response.stat().st_size>2*1024*1024:
        raise VisualContractError('response_file','Capture the actual tool response, without credentials')
    if not all(isinstance(s,str) and 1<=len(s)<=500 for s in (tool,call_id,artifact_id)):
        raise VisualContractError('tool_identifiers','Use the actual tool, call and returned artifact identifiers')
    if tool.casefold() in ('python','pillow','svg','canvas','placeholder'):
        raise VisualContractError('not_image_tool','Code drawings are not native image-tool outputs')
    raw_text=raw_response.read_text(encoding='utf-8')
    if artifact_id not in raw_text:
        raise VisualContractError('response_mismatch','Artifact identifier is absent from the captured tool response')
    evidence_path=root/'art-evidence.json'
    evidence=_json(evidence_path) if evidence_path.exists() else {
        'version':'art-evidence-1','run_id':hashlib.sha256(str(root).encode()).hexdigest()[:20],
        'persona_digest':plan['persona_digest'],'design':plan['design'],'images':{},'reviews':{},'attempts':[]}
    if evidence['persona_digest']!=plan['persona_digest'] or evidence['design']!=plan['design']:
        raise VisualContractError('wrong_persona','Existing image evidence belongs to another person/design')
    attempt_key=hashlib.sha256((tool+'\0'+call_id+'\0'+artifact_id).encode()).hexdigest()[:20]
    if any(x.get('key')==attempt_key for x in evidence.get('attempts',[])):
        raise VisualContractError('duplicate_tool_output','This call/artifact was already registered; do not count it as a new attempt')
    if sum(x['role']==role for x in evidence.get('attempts',[]))>=3:
        raise VisualContractError('retry_limit','Three returned attempts already recorded for this role; preserve the failure and stop')
    # Immutable originals preserve successful and failed attempts. Only selected roles are copied below.
    originals=root/'evidence'/'originals';originals.mkdir(parents=True,exist_ok=True)
    raw_copy=originals/(attempt_key+'-response.txt');shutil.copyfile(raw_response,raw_copy)
    native_copy=originals/(attempt_key+'-image'+image_path.suffix.lower());shutil.copyfile(image_path,native_copy)
    prompt_copy=originals/(attempt_key+'-prompt.txt');shutil.copyfile(prompt,prompt_copy)
    attempt={'key':attempt_key,'role':role,'image':_ref(native_copy,root),'raw_response':_ref(raw_copy,root),
             'registered_at':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'rejected'}
    error=None;actual_canvas=None;fmt=None
    try:
        with Image.open(native_copy) as image:
            if image.format not in ('PNG','WEBP','JPEG'): raise VisualContractError('image_format','Use a native raster output')
            actual_canvas=_canvas(image.size);fmt=image.format
            if role!='prototype' and actual_canvas!=canvas:
                raise VisualContractError('canvas_mismatch','Regenerate mismatched layers; never crop, scale or reposition')
            alpha=image.convert('RGBA').getchannel('A');hist=alpha.histogram();total=image.width*image.height
            if role in ('prototype','background') and hist[255]!=total:
                raise VisualContractError('background_alpha','Prototype/background must be fully opaque')
            if role in ('subject','effects') and not (sum(hist[:16])/total>.01 and sum(hist[16:])/total>.0005):
                raise VisualContractError('native_alpha','Subject/effects need nonempty real native transparency')
        if role!='prototype':
            from .art_quality import check_evidence
            gate=check_evidence(root/'layers.json',plan['persona_digest'],stage='prototype')
            if not gate['ok']: raise VisualContractError('prototype_not_reviewed','Prototype approval changed before the independent layer was registered')
            current=evidence['images']['prototype']['sha256']
            if current not in job['reference_sha256']:
                raise VisualContractError('prototype_changed','This layer job referenced another prototype')
    except (ValueError,OSError,Image.DecompressionBombError) as exc:
        error=str(exc);attempt['error']=error
    evidence.setdefault('attempts',[]).append(attempt)
    if error:
        _save(evidence_path,evidence)
        return {'ok':False,'status':'art_rejected','role':role,'error':error,'originals_preserved':True,'attempts_used':sum(x['role']==role for x in evidence['attempts'])}
    ext={'PNG':'.png','WEBP':'.webp','JPEG':'.jpg'}[fmt]
    target=root/(role+ext);shutil.copyfile(native_copy,target)
    call={'version':'image-call-1','kind':'image_tool','tool':tool,'call_id':call_id,'run_id':evidence['run_id'],
          'capabilities':{k:plan['capabilities'][k] for k in ('image_generation','reference_images','native_transparency')},
          'request':{'role':role,'canvas':list(canvas),'transparent':job['transparent'],
                     'prompt':_ref(prompt_copy,root),'design_sha256':plan['design']['sha256'],
                     'style_binding':plan['style_binding'],'reference_sha256':job['reference_sha256'],
                     'prompt_transport':'host_instruction_record_not_provider_authentication'},
          'response':{'artifact_id':artifact_id,'sha256':sha256(target),'canvas':list(actual_canvas)},
          'raw_response':_ref(raw_copy,root)}
    call_path=originals/(attempt_key+'-call.json');_save(call_path,call)
    evidence['images'][role]={**_ref(target,root),'mode':'generated','call':_ref(call_path,root)}
    attempt['status']='registered'
    manifest_path=root/'layers.json'
    manifest=_json(manifest_path) if manifest_path.exists() else {
        'schema_version':'1.0','persona_digest':plan['persona_digest'],'art_status':'generated',
        'reference_consent':design['reference_consent'],
        'assets':{k:k+'.png' for k in ('background','subject','spirit','effects','text','lineart')},
        'depths':{'background':-.25,'subject':.4,'effects':.5,'text':0},
        'notes':'Incomplete until all native layers, typography, reviews and browser checks pass.'}
    if role!='prototype': manifest['assets'][role]=target.name
    _save(manifest_path,manifest);_save(evidence_path,evidence)
    return {'ok':True,'status':'image_registered_not_reviewed','role':role,'image':str(target),
            'requested_canvas':list(canvas),'returned_canvas':list(actual_canvas),
            'generation_provenance_verified':False,'art_approved':False}


def bind_composite(manifest_path: Path, composite_path: Path) -> dict:
    """Register only the real unlettered alpha composite; never generate art here."""
    from .art_quality import read_json, _manifest_assets, pixel_digest
    manifest_path=Path(manifest_path).resolve();root=manifest_path.parent
    evidence=read_json(root/'art-evidence.json');manifest=read_json(manifest_path)
    if evidence.get('persona_digest')!=manifest.get('persona_digest'):
        raise VisualContractError('wrong_persona','Composite belongs to another person')
    _,images=_manifest_assets(root,manifest)
    merged=images['background'].copy()
    for role in ('spirit','subject','effects'):
        merged=Image.alpha_composite(merged,images[role])
    path=Path(composite_path).resolve();ref=_ref(path,root)
    with Image.open(path) as selected:
        if pixel_digest(selected)!=pixel_digest(merged):
            raise VisualContractError('wrong_composite','Register the actual native-layer composite, not another rendered poster')
    evidence['composite']=ref;_save(root/'art-evidence.json',evidence)
    return {'ok':True,'reviewed':False,'composite':ref}


def bind_review(manifest_path: Path, review_path: Path, *, front: Path|None=None, preview: Path|None=None) -> dict:
    """Bind a completed host observation after checking its exact current targets.

    The host must actually inspect the images and fill observations; no default
    acceptance, generated review or automatic aesthetic judgement is provided.
    """
    from .art_quality import read_json,snapshot,_review,REVIEW_CHECKS,check_evidence
    from .visual_contract import review_checks
    manifest_path,review_path=Path(manifest_path).resolve(),Path(review_path).resolve()
    root=manifest_path.parent;review=read_json(review_path);stage=review.get('stage')
    if stage not in REVIEW_CHECKS:raise VisualContractError('review_stage','Unknown review stage')
    manifest=read_json(manifest_path);persona=manifest['persona_digest']
    targets,evidence,design,inputs=snapshot(manifest_path,persona,stage=stage,front=front,preview=preview)
    candidate=json.loads(json.dumps(evidence));candidate.setdefault('reviews',{})[stage]=_ref(review_path,root)
    _review(root,candidate,stage,targets[stage],inputs,required_checks=review_checks(design,stage,REVIEW_CHECKS[stage]))
    _save(root/'art-evidence.json',candidate)
    report=check_evidence(manifest_path,persona,stage=stage,front=front,preview=preview)
    return {'ok':report['ok'],'status':report['status'],'review':candidate['reviews'][stage],
            'errors':report['errors'],'generation_provenance_verified':False,'quality_verified':False}
