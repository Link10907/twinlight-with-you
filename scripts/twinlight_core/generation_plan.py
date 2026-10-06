"""Auditable host handoff. Never calls a provider, cuts an image, or approves art."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image

from .visual_contract import (VERSION, VisualContractError, validate_design, style_binding,
                              subject_prompt, visual_keywords, layer_prompt, style_for,
                              style_references, _json, sha256)
from .canvas_mapping import native_dimensions_allowed,rounding_diagnostic,compose_layers,POLICY

IMAGE_ROLES = ('prototype', 'background', 'subject', 'effects')
MAX_BYTES = 24 * 1024 * 1024


def _task_scope(role: str) -> dict:
    """One image-tool deliverable, distinct from the host's complete product."""
    return {'version':'image-task-scope-1','output_count':1,'role':role,
            'artifact_kind':'single_scene_illustration' if role == 'prototype' else 'native_layer',
            'host_renderer_only':['website_ui','card_frame','typography','foil_animation']}


def _task_instruction(design: dict, role: str, canvas: tuple[int, int]) -> str:
    """Put the current output first; keep the evidenced base prompt unchanged."""
    if role == 'prototype':
        subject = design['subject']
        lines = ['本次唯一产物：一张占满画布的无字连续场景插画。'
                 '画布本身就是作品；一个主角、一个清楚动作。',
                 f'原生画布：{canvas[0]}×{canvas[1]}，竖版 3:4；主体按下述构图保留边距。',
                 '当前主角：' + subject['species'] + '；当前动作：' + subject['pose'] + '。']
    else:
        lines = ['本次唯一产物：一张 ' + role + ' 原生编辑图层。只处理当前已通过原型的这一层，'
                 '保持原型完整画布与原坐标，执行下述具体保留/删除任务。']
    lines.append('本次图像调用的职责到这张图为止。Twinlight 网页、卡框、中文排字与动态镭射由宿主程序组装；图像输出只包含当前插画或图层。')
    return '\n'.join(lines)


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
    prompt_only = value.get('canvas_selection') == 'prompt_only'
    if not isinstance(canvases,list) or (not prompt_only and list(canvas) not in canvases):
        raise VisualContractError('native_canvas_unavailable', 'Selected native canvas is not in the observed supported sizes; do not fix it by image processing')
    for size in canvases:
        if not isinstance(size,list) or len(size)!=2 or any(type(n) is not int or n<1 for n in size):
            raise VisualContractError('capability_canvas', 'Invalid capability canvas list')
    return value


def _ownership_instruction(design: dict, role: str) -> str:
    """Explicit object ownership; append to the stable, evidenced edit contract."""
    foreground = json.dumps(design['scene']['foreground'], ensure_ascii=False)
    subject = design['subject']['species']
    prop = design['subject']['main_prop']
    kept = subject + ('; attached prop: ' + prop if prop else '; no attached prop')
    tasks = {
        'subject': 'KEEP ONLY the existing subject and attached prop: ' + kept + '. DELETE the entire environment AND DELETE EACH foreground item listed here: ' + foreground + '. These foreground objects are NOT part of the subject, even when they overlap its clothes or the lower canvas. Make every deleted region transparent, locally complete covered clothing only. Delete the named foreground even when it is out of focus, but never confuse it with similarly colored clothing or the explicitly retained subject/prop.',
        'background': 'DELETE the subject and attached prop: ' + kept + '. ALSO DELETE EACH independently layered foreground item listed here: ' + foreground + '. Reconstruct the medium/distant environment behind these removed objects. None of the named foreground objects may remain here; keep distant environmental objects that are not on this foreground list.',
        'effects': 'KEEP ONLY EACH of these exact original foreground objects at its original coordinates: ' + foreground + '. DELETE the subject and attached prop (' + kept + ') AND DELETE all medium/distant environment. Every other pixel must be transparent. Do not introduce extra foreground or a complete scene.'}
    return 'EXPLICIT LAYER OWNERSHIP — ' + tasks[role] + ' Preserve the full original canvas, framing and pixel coordinates.'


def repair_plan(plan_path: Path, role: str, instruction: str) -> dict:
    """Append observed host feedback without changing identity or erasing attempts."""
    plan_path = Path(plan_path).resolve(); root = plan_path.parent
    plan = _json(plan_path)
    if plan.get('version') != 'generation-plan-2' or plan.get('phase') != 'layers' or role not in ('background','subject','effects'):
        raise VisualContractError('repair_phase', 'Repair an existing native layer job in the layers phase')
    if not isinstance(instruction, str) or not 8 <= len(instruction.strip()) <= 2500 or '\x00' in instruction:
        raise VisualContractError('repair_instruction', 'Supply 8–2500 characters of actual observed visual feedback and a concrete correction')
    instruction = instruction.strip()
    jobs = [job for job in plan.get('jobs', []) if job.get('role') == role]
    if len(jobs) != 1:
        raise VisualContractError('repair_role', 'The current plan must contain exactly one matching layer job')
    job = jobs[0]
    target = (root / plan['design']['file']).resolve()
    if not target.is_relative_to(root) or not target.is_file() or sha256(target) != plan['design']['sha256']:
        raise VisualContractError('design_changed', 'Do not repair a plan after its person or visual design changed')
    design = validate_design(_json(target), plan['persona_digest'])
    if style_binding(design) != plan['style_binding'] or job['style_binding'] != plan['style_binding']:
        raise VisualContractError('style_drift', 'A repair cannot change the selected style or its references')
    prototype = plan.get('prototype')
    if not prototype:
        raise VisualContractError('prototype_missing', 'Repair the layer against its approved prototype')
    proto_path = (root / prototype['file']).resolve()
    if not proto_path.is_relative_to(root) or not proto_path.is_file() or sha256(proto_path) != prototype['sha256']:
        raise VisualContractError('prototype_changed', 'The approved prototype changed before the repair')
    if (job.get('operation') != 'image_edit' or job.get('reference_images') != [{**prototype, 'purpose':'composition'}]
            or job.get('edit_base') != prototype or job.get('coordinate_policy') != 'preserve_full_canvas'):
        raise VisualContractError('edit_reference', 'Compile the sole-prototype native-edit plan before repairing it')
    prompt = (root / job['prompt']['file']).resolve()
    if not prompt.is_relative_to(root) or not prompt.is_file() or sha256(prompt) != job['prompt']['sha256']:
        raise VisualContractError('prompt_changed', 'The previous compiled prompt must remain intact before adding feedback')
    evidence_path = root / 'art-evidence.json'
    evidence = _json(evidence_path) if evidence_path.exists() else {}
    if evidence and (evidence.get('persona_digest') != plan['persona_digest'] or evidence.get('design') != plan['design']):
        raise VisualContractError('wrong_persona', 'A repair cannot use image attempts from another person or design')
    attempts = evidence.get('attempts', [])
    used = sum(attempt.get('role') == role for attempt in attempts)
    if used >= 3:
        raise VisualContractError('retry_limit', 'Three returns are already recorded for this role; repair must not reset the attempt limit')
    previous = job['prompt']
    text = prompt.read_text(encoding='utf-8')
    ownership = job.get('ownership_instruction') or _ownership_instruction(design, role)
    if ownership not in text:
        text = ownership + '\n\n' + text
    text = 'LATEST OBSERVED FAILURE AND REQUIRED REPAIR — highest-priority corrections to this same approved Image1, preserving its full canvas:\n' + instruction + '\n\n' + text
    prompt.write_text(text, encoding='utf-8')
    job['prompt'] = _ref(prompt, root)
    job['ownership_instruction'] = ownership
    job['repair_instruction'] = instruction
    job.setdefault('repair_history', []).append({'instruction':instruction,'previous_prompt_sha256':previous['sha256'],
                                               'prompt_sha256':job['prompt']['sha256'],'attempts_already_recorded':used})
    _save(plan_path, plan)
    return {'ok':True,'role':role,'prompt':job['prompt'],'repair_instruction':instruction,
            'attempts_used':used,'attempts_remaining':3-used,'design_unchanged':True,
            'style_unchanged':True,'prototype_unchanged':True,'image_generation_performed':False}


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
    # Brand examples travel as real tool inputs, separately from user likeness consent.
    style_refs = []
    for index, ref in enumerate(style_references(style_for(design['style']['id'], design['style']['version']))):
        source = Path(ref['file'])
        copied = out / 'references' / (design['style']['id'] + '-' + str(index + 1) + source.suffix.lower())
        copied.parent.mkdir(exist_ok=True)
        if copied.exists() and sha256(copied) != ref['sha256']:
            raise VisualContractError('style_reference_changed', 'Do not overwrite a previously staged style reference')
        if source != copied:
            shutil.copyfile(source, copied)
        style_refs.append({**_ref(copied, out), 'purpose': 'style_only'})
    # A generation plan is an instruction, not proof that a tool call happened.
    jobs=[]
    roles=('prototype',) if phase=='prototype' else ('background','subject','effects')
    prompt_dir=out/'prompts';prompt_dir.mkdir(exist_ok=True)
    for role in roles:
        path=prompt_dir/(role+'.txt')
        ownership = _ownership_instruction(design, role) if prototype_ref else None
        path.write_text((ownership+'\n\n' if ownership else '')+_task_instruction(design,role,canvas)+'\n\n'+layer_prompt(design,role,canvas)+'\n',encoding='utf-8')
        refs = ([{**prototype_ref, 'purpose': 'composition'}] if prototype_ref else style_refs + [
            {**x, 'purpose': 'user_reference'} for x in design['references']])
        jobs.append({'role':role,'prompt':_ref(path,out),'requested_canvas':list(canvas),
                     'task_scope':_task_scope(role),
                     'transparent':role in ('subject','effects'),
                     'operation':'image_edit' if prototype_ref else 'image_generation',
                     'edit_base':prototype_ref,
                     'coordinate_policy':'preserve_full_canvas' if prototype_ref else 'establish_composition',
                     'ownership_instruction':ownership,
                     'reference_images':refs,
                     'referenced_image_paths':[str((out / ref['file']).resolve()) for ref in refs],
                     'reference_sha256':[ref['sha256'] for ref in refs],
                     'style_binding':style,'status':'not_called'})
    plan={'version':'generation-plan-2','phase':phase,'persona_digest':design['persona_digest'],
          'design':_ref(target,out),'style_binding':style,'canvas':list(canvas),
          'prototype':prototype_ref,'jobs':jobs,'capabilities':capabilities,
          'canvas_policy':'observe_native_prototype_then_freeze' if capabilities and capabilities.get('canvas_selection') == 'prompt_only' else 'declared_native_canvas',
          'layer_strategy':'prototype_native_edit_v1',
          'ready_for_image_call':capabilities is not None,
          'required_artwork':'native_layered','subject_count':1,'main_prop_limit':1,
          'spirit':'empty_same_canvas_no_image_call','independent_typography':True,
          'image_generation_performed':False,'requires_host_tool_call':True,
          'next_action':'call_prototype_image_tool' if phase=='prototype' else 'call_native_layer_image_tools',
          'limits':['This is a host handoff, not an authenticated provider call.',
                    'Send exactly one current job.prompt text per image call. Its task_scope is the image deliverable; the complete website, card assembly and delivery request stay with the host.',
                    'Pass each job.referenced_image_paths to the actual image tool; a prompt mentioning a reference is not an image reference.',
                    'For image_edit jobs, the only input is this approved prototype. Preserve its full canvas and coordinates; do not append style examples or create a recentered character sheet.',
                    'If canvas_selection is prompt_only, requested_canvas is a prompt preference, not a provider size parameter. Inspect native dimensions after the call; never resample.',
                    'Do not send personal history, narrative keywords or the whole skill manual to the image tool.']}
    (out/'subject-description.txt').write_text(subject_prompt(design)+'\n',encoding='utf-8')
    _save(out/'visual-keywords.json',{'visual_keywords':visual_keywords(design),'derived_from':'subject_fields_only'})
    _save(out/'generation-plan.json',plan)
    return plan


def register_image(plan_path: Path, role: str, image_path: Path, raw_response: Path, *,
                   tool: str, call_id: str, artifact_id: str, _revalidate_attempt: str|None=None) -> dict:
    """Copy original output bytes and register an observed response. No synthetic calls."""
    plan_path=Path(plan_path).resolve();root=plan_path.parent
    plan=_json(plan_path)
    if plan.get('version')!='generation-plan-2' or plan.get('ready_for_image_call') is not True:
        raise VisualContractError('plan_not_ready','Validate real image capabilities before using this plan')
    jobs=[j for j in plan.get('jobs',[]) if j.get('role')==role]
    if role not in IMAGE_ROLES or len(jobs)!=1:
        raise VisualContractError('wrong_phase','This phase does not permit that image role')
    job=jobs[0];design_path=(root/plan['design']['file']).resolve()
    if 'task_scope' in job and job['task_scope'] != _task_scope(role):
        raise VisualContractError('image_task_scope', 'The current image job must deliver one illustration or one native layer; recompile its scope before calling the tool')
    if not design_path.is_relative_to(root) or sha256(design_path)!=plan['design']['sha256']:
        raise VisualContractError('design_changed','Design changed after prompt compilation')
    design=validate_design(_json(design_path),plan['persona_digest'])
    if style_binding(design)!=plan['style_binding'] or job['style_binding']!=plan['style_binding']:
        raise VisualContractError('style_drift','Style changed after prompt compilation')
    prompt=(root/job['prompt']['file']).resolve()
    if not prompt.is_relative_to(root) or sha256(prompt)!=job['prompt']['sha256']:
        raise VisualContractError('prompt_changed','Prompt changed after compilation')
    references = job.get('reference_images', [])
    if plan.get('layer_strategy') == 'prototype_native_edit_v1':
        expected_operation = 'image_generation' if role == 'prototype' else 'image_edit'
        if job.get('operation') != expected_operation:
            raise VisualContractError('image_operation', 'This plan requires the declared prototype generation or native layer editing operation')
    if 'reference_images' in job and [ref['sha256'] for ref in references] != job['reference_sha256']:
        raise VisualContractError('reference_changed', 'Image reference list changed after compilation')
    for ref in references:
        path = (root / ref['file']).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha256(path) != ref['sha256']:
            raise VisualContractError('reference_changed', 'A compiled image reference is missing or changed')
    required_style_hashes = set(plan['style_binding'].get('reference_sha256', [])) if role == 'prototype' else set()
    if not required_style_hashes.issubset({r['sha256'] for r in references if r.get('purpose') == 'style_only'}):
        raise VisualContractError('style_reference_missing', 'The collector image call must bind its actual style reference images')
    if job.get('operation') == 'image_edit':
        expected = plan.get('prototype')
        if (not expected or job.get('edit_base') != expected
                or job.get('coordinate_policy') != 'preserve_full_canvas'
                or references != [{**expected, 'purpose': 'composition'}]):
            raise VisualContractError('edit_reference', 'Native layer editing requires only the current prototype and its complete original canvas')
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
    previous_attempt=next((x for x in evidence.get('attempts',[]) if x.get('key')==attempt_key),None)
    if previous_attempt and _revalidate_attempt is None:
        raise VisualContractError('duplicate_tool_output','This call/artifact was already registered; do not count it as a new attempt')
    if _revalidate_attempt is not None:
        if (not previous_attempt or _revalidate_attempt != attempt_key or previous_attempt.get('role') != role
                or previous_attempt.get('status') != 'rejected'
                or not (previous_attempt.get('error_code') == 'canvas_mismatch'
                        or previous_attempt.get('error') == 'Regenerate mismatched layers; never crop, scale or reposition')):
            raise VisualContractError('revalidation_source','Only an existing canvas-mismatch rejection may be revalidated without a new call')
        if previous_attempt.get('revalidations'):
            raise VisualContractError('revalidation_duplicate','This failed return was already revalidated; do not reset its history')
        for candidate,stored in ((image_path,previous_attempt['image']),(raw_response,previous_attempt['raw_response'])):
            if candidate != (root/stored['file']).resolve() or sha256(candidate) != stored['sha256']:
                raise VisualContractError('revalidation_source','Revalidation must use the exact immutable original return and response')
    if _revalidate_attempt is None and sum(x['role']==role for x in evidence.get('attempts',[]))>=3:
        raise VisualContractError('retry_limit','Three returned attempts already recorded for this role; preserve the failure and stop')
    # Immutable originals preserve successful and failed attempts. Only selected roles are copied below.
    originals=root/'evidence'/'originals';originals.mkdir(parents=True,exist_ok=True)
    raw_copy=originals/(attempt_key+'-response.txt')
    native_copy=originals/(attempt_key+'-image'+image_path.suffix.lower())
    prompt_copy=originals/(attempt_key+'-prompt.txt')
    if _revalidate_attempt is None:
        shutil.copyfile(raw_response,raw_copy);shutil.copyfile(image_path,native_copy);shutil.copyfile(prompt,prompt_copy)
    elif not prompt_copy.is_file() or sha256(prompt_copy)!=job['prompt']['sha256']:
        raise VisualContractError('revalidation_prompt','The frozen failed request does not match the current plan; do not invent a replacement request')
    attempt={'key':attempt_key,'role':role,'image':_ref(native_copy,root),'raw_response':_ref(raw_copy,root),
             'registered_at':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'rejected'}
    attempt['tool_identifiers']={'tool':tool,'call_id':call_id,'artifact_id':artifact_id}
    attempt['prompt']=_ref(prompt_copy,root)
    error=None;actual_canvas=None;fmt=None
    try:
        with Image.open(native_copy) as image:
            if image.format not in ('PNG','WEBP','JPEG'): raise VisualContractError('image_format','Use a native raster output')
            actual_canvas=_canvas(image.size);fmt=image.format
            native_edit=job.get('operation')=='image_edit' and job.get('coordinate_policy')=='preserve_full_canvas'
            if role!='prototype' and not native_dimensions_allowed(actual_canvas,canvas,native_edit=native_edit):
                raise VisualContractError('canvas_mismatch','Native layer differs by more than the explicit one-pixel rounding policy, or was not a native image edit')
            if _revalidate_attempt and (actual_canvas==canvas or not native_edit):
                raise VisualContractError('revalidation_source','This policy revalidation applies only to a one-pixel native image-edit return')
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
        error=str(exc);attempt['error']=error;attempt['error_code']=getattr(exc,'code','invalid_native_output')
    if actual_canvas is not None:attempt['returned_canvas']=list(actual_canvas)
    if _revalidate_attempt is None:evidence.setdefault('attempts',[]).append(attempt)
    if error:
        _save(evidence_path,evidence)
        return {'ok':False,'status':'art_rejected','role':role,'error':error,'error_code':attempt.get('error_code'),
                'attempt_key':attempt_key,'requested_canvas':list(canvas),'returned_canvas':list(actual_canvas) if actual_canvas else None,
                'originals_preserved':True,'attempts_used':sum(x['role']==role for x in evidence['attempts'])}
    ext={'PNG':'.png','WEBP':'.webp','JPEG':'.jpg'}[fmt]
    target=root/(role+ext);shutil.copyfile(native_copy,target)
    call={'version':'image-call-1','kind':'image_tool','tool':tool,'call_id':call_id,'run_id':evidence['run_id'],
          'capabilities':{k:plan['capabilities'][k] for k in ('image_generation','reference_images','native_transparency')},
          'request':{'role':role,'canvas':list(canvas),'transparent':job['transparent'],
                     'prompt':_ref(prompt_copy,root),'design_sha256':plan['design']['sha256'],
                     'style_binding':plan['style_binding'],'reference_sha256':job['reference_sha256'],
                     'reference_images':references,
                     'operation':job.get('operation','legacy_image_request'),
                     'edit_base':job.get('edit_base'),
                     'coordinate_policy':job.get('coordinate_policy'),
                     'task_scope':job.get('task_scope'),
                     'ownership_instruction':job.get('ownership_instruction'),
                     'repair_instruction':job.get('repair_instruction'),
                     'prompt_transport':'host_instruction_record_not_provider_authentication'},
          'response':{'artifact_id':artifact_id,'sha256':sha256(target),'canvas':list(actual_canvas)},
          'raw_response':_ref(raw_copy,root)}
    if role!='prototype' and actual_canvas!=canvas:
        call['response']['canvas_mapping']=rounding_diagnostic(actual_canvas,canvas)
    call_path=originals/(attempt_key+'-call.json');_save(call_path,call)
    evidence['images'][role]={**_ref(target,root),'mode':'generated','call':_ref(call_path,root)}
    if _revalidate_attempt:
        previous_attempt.setdefault('revalidations',[]).append({'policy':POLICY,'status':'registered_not_reviewed',
            'at':dt.datetime.now(dt.timezone.utc).isoformat(),'call':_ref(call_path,root),
            'original_rejection_preserved':True,'new_image_call':False})
    else:attempt['status']='registered'
    manifest_path=root/'layers.json'
    manifest=_json(manifest_path) if manifest_path.exists() else {
        'schema_version':'1.0','persona_digest':plan['persona_digest'],'art_status':'generated',
        'reference_consent':design['reference_consent'],
        'assets':{k:k+'.png' for k in ('background','subject','spirit','effects','text','lineart')},
        'depths':{'background':-.25,'subject':.4,'effects':.5,'text':0},
        'notes':'Incomplete until all native layers, typography, reviews and browser checks pass.'}
    if role!='prototype': manifest['assets'][role]=target.name
    if role!='prototype' and actual_canvas!=canvas:
        mapping=manifest.setdefault('canvas_mapping',{'version':POLICY,'canvas':list(canvas),'sampling':'full_uv_bilinear','native_edit_roles':[]})
        if mapping['canvas']!=list(canvas):raise VisualContractError('canvas_mapping','Manifest already declares another logical canvas')
        mapping['native_edit_roles']=sorted(set(mapping['native_edit_roles'])|{role})
    _save(manifest_path,manifest);_save(evidence_path,evidence)
    return {'ok':True,'status':'image_registered_not_reviewed','role':role,'image':str(target),
            'attempt_key':attempt_key,
            'requested_canvas':list(canvas),'returned_canvas':list(actual_canvas),
            'canvas_mapping':rounding_diagnostic(actual_canvas,canvas) if role!='prototype' and actual_canvas!=canvas else None,
            'new_image_call':False if _revalidate_attempt else None,
            'generation_provenance_verified':False,'art_approved':False}


def revalidate_image(plan_path: Path, attempt_key: str, *, tool: str, call_id: str, artifact_id: str) -> dict:
    """Reconsider preserved one-pixel returns without another call or another attempt."""
    plan_path=Path(plan_path).resolve();root=plan_path.parent
    evidence=_json(root/'art-evidence.json')
    attempt=next((a for a in evidence.get('attempts',[]) if a.get('key')==attempt_key),None)
    if not attempt:raise VisualContractError('revalidation_source','No immutable original attempt matches this key')
    return register_image(plan_path,attempt['role'],root/attempt['image']['file'],root/attempt['raw_response']['file'],
                          tool=tool,call_id=call_id,artifact_id=artifact_id,_revalidate_attempt=attempt_key)


def bind_composite(manifest_path: Path, composite_path: Path) -> dict:
    """Register only the real unlettered alpha composite; never generate art here."""
    from .art_quality import read_json, _manifest_assets, pixel_digest
    manifest_path=Path(manifest_path).resolve();root=manifest_path.parent
    evidence=read_json(root/'art-evidence.json');manifest=read_json(manifest_path)
    if evidence.get('persona_digest')!=manifest.get('persona_digest'):
        raise VisualContractError('wrong_persona','Composite belongs to another person')
    _,images=_manifest_assets(root,manifest)
    merged=compose_layers(manifest,images)
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
