"""Portable image tasks: reserve a specific call, inspect its return, audit its use.

The host still invokes its native tool. Local records are not provider receipts
and cannot intercept calls made outside this workflow. Strict dispatch is unchanged.
"""
from __future__ import annotations
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from PIL import Image
from .common import ROOT, check, digest, load, local_asset
from .card_context import render_prompt, validate_input, image_input, visible_text
from .portable_layers import layer_plan, sha, verify_process
from .style_selection import selection_status
from .visual_contract import style_for, style_references, validate_design

CONTRACT = 'portable-image-tasks-1'
LEDGER = 'image-tasks.json'
OUTPUTS = Path('card-task/image-outputs')
ROLES = ('prototype', 'background', 'subject', 'effects')
LIMIT = 3


def _safe(workspace: Path, relative: str) -> Path:
    check(isinstance(relative, str) and relative and not Path(relative).is_absolute()
          and '..' not in Path(relative).parts, 'Use a workspace-relative image path')
    path = workspace / relative
    check(path.resolve().is_relative_to(workspace.resolve()) and
          not any(p.is_symlink() for p in (path, *path.parents)), 'Image paths must not escape or use symlinks')
    return path


def _write(path: Path, value: dict) -> None:
    """Private, atomic writes; a partial reservation must not authorize another call."""
    import json
    check(not any(p.is_symlink() for p in (path, *path.parents)), 'Image record path uses a symlink')
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='.image-', delete=False) as f:
        tmp = Path(f.name)
        try:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write('\n'); f.flush(); os.fsync(f.fileno()); os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)


@contextmanager
def _lock(workspace: Path):
    lock = _safe(workspace, '.image-tasks.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('An image-task update is active or interrupted; inspect it before retrying') from None
    os.close(fd)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def _state(workspace: Path) -> dict:
    s = load(_safe(workspace, 'portable-state.json'))
    check(s.get('mode') == 'full', 'No image tasks in the no-card route')
    check(s.get('image_task_contract') == CONTRACT,
          'Untracked workspace: use its pinned Skill; do not invent earlier reservations')
    check(sha(Path(s['input_path'])) == s['input_sha256'], 'Frozen personal content changed')
    return s


def _image(path: Path) -> tuple[list[int], bool, bool]:
    check(path.is_file() and path.stat().st_size <= 24 * 1024 * 1024, 'Missing or oversized returned image')
    with Image.open(path) as im:
        check(im.format in ('PNG', 'JPEG', 'WEBP') and im.width*im.height <= 16_000_000,
              'Expected actual supported raster image bytes')
        canvas = list(im.size); lo, hi = im.convert('RGBA').getchannel('A').getextrema()
        return canvas, lo == hi == 255, lo < 16 and hi > 16


def _inputs(workspace: Path) -> tuple[dict, dict, list[dict]]:
    s = _state(workspace)
    check(selection_status(workspace)['status'] == 'frozen', 'Freeze the drawing input before reserving an image')
    value = validate_input(load(_safe(workspace, 'card-image-input.json')))
    style = style_for(value['style']['id'], value['style']['version'])
    refs = [{'file': Path(x['file']).relative_to(ROOT).as_posix(), 'sha256': x['sha256'], 'purpose': 'style_only'}
            for x in style_references(style)]
    if value['subject']['representation'] == 'user_reference':
        from .lite import persona_digest
        design = validate_design(load(_safe(workspace, 'art-direction.json')), persona_digest(load(Path(s['input_path']))))
        check(image_input(design) == value, 'Authorized likeness design differs from drawing input')
        for ref in design['references']:
            path = _safe(workspace, ref['file']); _image(path)
            check(sha(path) == ref['sha256'], 'Authorized likeness reference changed')
            refs.append({**ref, 'purpose': 'user_reference'})
    return value, {'content_sha256': s['input_sha256'], 'drawing_sha256': digest(value),
                   'style_sha256': style['sha256'], 'presets_sha256': sha(ROOT/'assets/art-styles/image-presets.json'),
                   'prototype_references': refs}, refs


def _payload(workspace: Path, value: dict, q: dict) -> dict:
    return {'prompt_text': render_prompt(value, q['role'], tuple(q['canvas']), repair=q['repair']),
            'reference_images': [str((ROOT if x['purpose'] == 'style_only' else workspace)/x['file']) for x in q['references']],
            'canvas': q['canvas'], 'transparent': q['role'] in ('subject', 'effects'), 'operation': q['operation']}


def _read(workspace: Path) -> tuple[dict, dict]:
    value, binding, refs = _inputs(workspace)
    p = _safe(workspace, LEDGER)
    if not p.exists():
        check(not (workspace/'card-task/image-jobs').exists(), 'Image ledger missing; preserve the existing job records')
        return value, {'version': CONTRACT, 'binding': binding, 'attempts': [], 'closed': False}
    r = load(p, max_bytes=512 * 1024)
    check(r.get('version') == CONTRACT and r.get('binding') == binding, 'Image-task input binding changed')
    check(r.get('record_sha256') == digest({k:v for k,v in r.items() if k != 'record_sha256'}), 'Image-task record changed')
    check(isinstance(r.get('attempts'), list) and len(r['attempts']) <= LIMIT*len(ROLES), 'Invalid image attempts')
    ids = set()
    for a in r['attempts']:
        q = a['request']; task_id = q['task_id']
        check(task_id not in ids and q['role'] in ROLES, 'Duplicate or unknown image task'); ids.add(task_id)
        check(digest(q) == a['request_sha256'], 'Reserved image task changed')
        path = _safe(workspace, q['drawing_file'])
        check(sha(path) == q['drawing_file_sha256'] and load(path) == _payload(workspace,value,q), 'Reserved drawing payload changed')
        check(q['operation'] == ('image_generation' if q['role'] == 'prototype' else 'image_edit'), 'Image operation changed')
        if q['role'] == 'prototype':
            check(q['references'] == refs, 'Prototype reference scope changed')
        else:
            check(len(q['references']) == 1 and q['references'][0]['purpose'] == 'composition'
                  and q['references'][0]['sha256'] == q['prototype_sha256'], 'Layer reference scope changed')
        for ref in q['references']:
            path = (ROOT/ref['file']) if ref['purpose'] == 'style_only' else _safe(workspace,ref['file'])
            check(path.is_file() and sha(path) == ref['sha256'], 'Reserved image reference changed')
        if a.get('result'):
            result = a['result']
            check(a.get('result_sha256') == digest(result), 'Recorded image result changed')
            for output in result['outputs']:
                check(sha(_safe(workspace,output['file'])) == output['sha256'], 'Returned image bytes changed or are missing')
    check(sum(not a.get('result') for a in r['attempts']) <= 1, 'Multiple pending reservations')
    return value, r


def _save(workspace: Path, r: dict) -> None:
    r['record_sha256'] = digest({k:v for k,v in r.items() if k != 'record_sha256'})
    _write(workspace/LEDGER, r)


def _accepted(r: dict) -> dict:
    return {a['request']['role']: a for a in r['attempts']
            if a.get('result', {}).get('disposition') == 'accepted' and not a.get('withdrawal')}


def _primary(a: dict) -> dict:
    return next(x for x in a['result']['outputs'] if x['disposition'] == 'accepted')


def _history(r: dict) -> dict:
    accepted = [a['request']['task_id'] for a in _accepted(r).values()]
    return {'attempts': [{'role': a['request']['role'],
                         'outcome': ('reference_mismatch' if a.get('result',{}).get('outcome') == 'reference_mismatch'
                                     else 'success' if a['request']['task_id'] in accepted else 'failure')}
                        for a in r['attempts']]}


def history(workspace: Path) -> dict | None:
    workspace = Path(workspace).resolve()
    if (workspace/LEDGER).exists(): return _history(_read(workspace)[1])
    p = workspace/'image-attempts.json'
    return load(p) if p.exists() else None


def _planned(workspace: Path, caps: dict, r: dict) -> dict:
    if r['closed'] or _state(workspace).get('card_target') or (workspace/'site-task/site/index.html').exists():
        return {'status': 'image_tasks_closed', 'next_action': 'Task B embeds the accepted card; no new image call is authorized.'}
    pending = next((a for a in r['attempts'] if not a.get('result')), None)
    if pending:
        return {'status': 'awaiting_image_result', 'task_id': pending['request']['task_id'], 'role': pending['request']['role'],
                'next_action': 'Inspect the prior native call and record its result; do not call again or assume an uncertain call was not_called.'}
    accepted = _accepted(r)
    if set(accepted) == set(ROLES):
        return {'status': 'assemble_layers', 'accepted_assets': {k:_primary(v) for k,v in accepted.items()},
                'next_action': 'Prepare the six-layer manifest from accepted files, then run with --layers. No additional image is needed.'}
    role = next(role for role in ROLES if role not in accepted)
    if role != 'prototype':
        plan = layer_plan(caps, _history(r))
        if plan['method'] == 'assisted_layers' or plan['status'] in ('inspect_layer_processing','layer_capability_blocked'):
            return {'status': 'assisted_layers_required' if plan['method'] else plan['status'], 'layer_plan': plan,
                    'accepted_assets': {k:_primary(v) for k,v in accepted.items()}, 'next_action': plan['next_action']}
    number = sum(a['request']['role'] == role for a in r['attempts']) + 1
    if number > LIMIT:
        return {'status': 'image_attempt_limit', 'role': role, 'next_action': 'Preserve the work and report the actual limitation; do not reset attempts.'}
    if caps.get('image',{}).get('status') != 'available':
        return {'status': 'image_capability_unavailable', 'next_action': 'Inspect the actual image capability; do not substitute a card-free result.'}
    p = _primary(accepted['prototype']) if 'prototype' in accepted else None
    canvas = p['canvas'] if p else caps.get('image',{}).get('canvas',[1080,1440])
    check(isinstance(canvas,(list,tuple)) and len(canvas)==2 and all(type(n) is int for n in canvas)
          and min(canvas)>=512 and canvas[0]*canvas[1]<=16_000_000 and abs(canvas[0]/canvas[1]-.75)<.01,
          'Use a supported native 3:4 canvas, short side at least 512')
    previous = next((a for a in reversed(r['attempts']) if a['request']['role']==role), {})
    repair = previous.get('withdrawal',{}).get('repair') or previous.get('result',{}).get('repair')
    key = {'binding':r['binding'], 'role':role, 'number':number, 'prototype_sha256':p['sha256'] if p else None,
           'canvas':list(canvas), 'repair':repair}
    return {'status':'ready', 'task_id':'image-'+digest(key)[:20], **key,
            'operation':'image_generation' if role=='prototype' else 'image_edit',
            'next_action':'Reserve this one task with reserve-image; invoke the native tool using only its drawing payload and actual references.'}


def next_task(workspace: Path, caps: dict) -> dict:
    """Read-only: repeated run/status calls never consume another attempt."""
    workspace = Path(workspace).resolve(); _state(workspace)
    if selection_status(workspace)['status'] != 'frozen':
        return {'status':'selection_required', 'next_action':'Freeze the style and drawing input first; no image call is ready.'}
    return _planned(workspace,caps,_read(workspace)[1])


def reserve(workspace: Path, task_id: str, tool: str) -> dict:
    """Reserve before the native call. A pending reservation is never reissued."""
    workspace=Path(workspace).resolve()
    check(isinstance(tool,str) and 0<len(tool.strip())<=160,'Name the actually available image tool')
    with _lock(workspace):
        value,r=_read(workspace); caps=load(_safe(workspace,'capabilities.json')); task=_planned(workspace,caps,r)
        check(task['status']=='ready' and task.get('task_id')==task_id,'No matching ready task; inspect the pending result instead of making a duplicate call')
        q={k:task[k] for k in ('task_id','role','operation','number','canvas','prototype_sha256','repair')}
        if q['role']=='prototype': refs=r['binding']['prototype_references']
        else:
            p=_primary(_accepted(r)['prototype']); refs=[{k:p[k] for k in ('file','sha256')}|{'purpose':'composition'}]
        q.update(tool=tool.strip(),references=refs,context_isolation=caps.get('image',{}).get('context_isolation','unknown'),drawing_file=f'card-task/image-jobs/{task_id}/drawing.json',
                 output_directory=(OUTPUTS/task_id).as_posix())
        dest=_safe(workspace,q['drawing_file']); out=_safe(workspace,q['output_directory'])
        check(not dest.exists() and not out.exists(),'Reserved image output already exists')
        _write(dest,_payload(workspace,value,q)); q['drawing_file_sha256']=sha(dest)
        r['attempts'].append({'request':q,'request_sha256':digest(q)})
        _save(workspace,r); out.mkdir(parents=True,exist_ok=False)
    return {'ok':True,'status':'reserved','task_id':task_id,'drawing_payload':str(dest),'output_directory':str(out),
            'attempts_used':q['number'],'image_calls_performed_by_cli':0,
            'instruction':'Pass only the drawing payload through supported native tool fields, not this envelope. Stage ALL returned images in output_directory and record their actual dispositions.'}


def record(workspace: Path, result: dict) -> dict:
    """Observe actual images before accepting, revising or discarding them."""
    workspace=Path(workspace).resolve()
    allowed={'task_id','outcome','disposition','reason','review_method','execution_ref','output','extra_outputs','repair'}
    check(isinstance(result,dict) and not set(result)-allowed,'Unknown image result fields')
    outcome,decision=result.get('outcome'),result.get('disposition'); reason=result.get('reason','')
    check(outcome in ('success','failure','reference_mismatch','not_called'),'Invalid image outcome')
    check(decision in ('accepted','revise','discarded'),'Invalid image disposition')
    check(isinstance(reason,str) and 12<=len(reason.strip())<=240,'Record specific observations, 12–240 characters')
    repair=visible_text(result.get('repair'),'repair',240) if decision=='revise' else None
    check(decision=='revise' or 'repair' not in result,'Only a visual revision supplies a drawing defect')
    with _lock(workspace):
        _,r=_read(workspace); a=next((a for a in r['attempts'] if not a.get('result')),None)
        check(a is not None and a['request']['task_id']==result.get('task_id'),'No matching pending reservation; do not backfill or replay a result')
        q=a['request']; outputs=[]
        if result.get('output'): outputs.append({'file':result['output'],'disposition':decision,'reason':reason})
        extras=result.get('extra_outputs',[])
        check(isinstance(extras,list) and len(extras)<=8,'Invalid extra image results')
        for x in extras:
            check(isinstance(x,dict) and set(x)=={'file','reason'} and isinstance(x['reason'],str)
                  and 12<=len(x['reason'].strip())<=240,'Unused extras require their file and a specific reason')
            outputs.append({**x,'disposition':'discarded'})
        check(all(isinstance(x['file'],str) for x in outputs) and len({x['file'] for x in outputs})==len(outputs),'Duplicate or invalid returned file')
        check(outcome!='not_called' or not outputs,'A not-called reservation cannot have returned images')
        check(outcome!='success' or result.get('output'),'Successful return requires actual image bytes')
        check(decision not in ('accepted','revise') or (outcome=='success' and result.get('output')),'Accept/revise requires a successfully returned image')
        review=result.get('review_method')
        prior={x['sha256'] for other in r['attempts'] if other.get('result') for x in other['result']['outputs']}
        for x in outputs:
            path=_safe(workspace,x['file']); check(path.is_relative_to(workspace/q['output_directory']),'Stage each return under its actual reserved task')
            check(path.is_file() and path.stat().st_size<=24*1024*1024,'Missing or oversized returned file')
            try:
                canvas,opaque,transparent=_image(path); readable=True
            except (OSError,ValueError):
                check(outcome=='failure' and x['disposition']=='discarded',
                      'Unreadable returned bytes may only be kept as a discarded technical failure')
                canvas=None; readable=False
            x.update(sha256=sha(path),canvas=canvas,readable_image=readable)
            if x['disposition']=='accepted':
                check(x['sha256'] not in prior,'Do not reuse a previous returned image as a new accepted call')
                check(min(canvas)>=512 and abs(canvas[0]/canvas[1]-.75)<.01,'Accepted art needs its actual native 3:4 canvas')
                if q['role']=='prototype': check(opaque,'The original scene must be opaque')
                else:
                    check(canvas==q['canvas'],'Layer canvas differs from the frozen prototype; do not rescale it')
                    check(opaque if q['role']=='background' else transparent,'Layer alpha does not match its role')
        if any(x['readable_image'] for x in outputs):
            check(review in ('self','independent') and load(_safe(workspace,'capabilities.json')).get('reviewer',{}).get('mode','self')!='unavailable',
                  'Actual visual observation is required to classify returned images')
        else:
            check(review is None,'Do not claim visual review when no readable image was returned')
        check(review!='independent' or (isinstance(result.get('execution_ref'),str) and result['execution_ref'].strip()),
              'Record the real independent review task reference')
        staged={p.relative_to(workspace).as_posix() for p in _safe(workspace,q['output_directory']).rglob('*') if p.is_file()}
        check(staged=={x['file'] for x in outputs},'Classify every staged return, including unused extras')
        registered={'outcome':outcome,'disposition':decision,'reason':reason,'review_method':review,'outputs':outputs}
        if review=='independent': registered['execution_ref']=result['execution_ref']
        if repair: registered['repair']=repair
        a['result']=registered; a['result_sha256']=digest(registered); _save(workspace,r)
    return {'ok':True,'task_id':q['task_id'],'disposition':decision,
            'next_action':'Run again to obtain the next task; do not start an unplanned image.'}


def withdraw(workspace: Path, role: str, reason: str) -> dict:
    """Reopen only a defective layer during A; preserve its prototype and attempt count."""
    workspace=Path(workspace).resolve()
    check(role in ROLES[1:],'The accepted prototype is frozen; only a defective layer can be withdrawn')
    check(isinstance(reason,str) and 12<=len(reason.strip())<=240,'Give the specific layer defect')
    repair=visible_text(reason,'repair',240)
    with _lock(workspace):
        _,r=_read(workspace); state=_state(workspace)
        check(not r['closed'] and not state.get('card_target'),'Task B cannot dispatch image repairs')
        check(all(a.get('result') for a in r['attempts']),'Resolve the pending return before withdrawing a layer')
        accepted=_accepted(r); check(role in accepted,'No accepted layer with that role')
        accepted[role]['withdrawal']={'reason':reason,'repair':repair}; _save(workspace,r)
        state['layers_path']=None; state['status']='started'; _write(workspace/'portable-state.json',state)
        for name in ('review-card.json','card-runtime.json'):
            old=_safe(workspace,name)
            if old.exists():
                archive=_safe(workspace,'card-task/image-review-history/'+old.stem+'-'+sha(old)+'.json')
                archive.parent.mkdir(parents=True,exist_ok=True); old.replace(archive)
    return {'ok':True,'role':role,'next_action':'Run again; reuse the other accepted layers and retain this role\'s attempt budget.'}


def audit(workspace: Path, layers: Path, generation: dict, *, close: bool=False) -> dict:
    """Reconcile accepted sources and all registered returns before B and delivery."""
    workspace=Path(workspace).resolve(); layers=Path(layers).resolve()
    with _lock(workspace):
        _,r=_read(workspace)
        check(r['attempts'] and all(a.get('result') for a in r['attempts']),'Image returns are missing or pending')
        accepted=_accepted(r); check('prototype' in accepted,'No reserved, accepted original illustration')
        prototype=_primary(accepted['prototype']); check(prototype['sha256']==generation.get('prototype_sha256'),'Final prototype differs from the frozen accepted result')
        g=load(_safe(workspace,'generation.json')); check(sha(workspace/'generation.json')==generation.get('record_sha256'),'Generation record changed after validation')
        check(g.get('tool')==accepted['prototype']['request']['tool'] and g.get('prototype_review')==accepted['prototype']['result']['review_method'],
              'Prototype tool/review attribution differs from its recorded call')
        context=accepted['prototype']['request'].get('context_isolation','unknown')
        check(context=='unknown' or context==g.get('context_isolation'),'Prototype context boundary differs from the recorded task')
        m=load(layers); actual={role:sha(local_asset(layers.parent,m['assets'][role])) for role in ROLES[1:]}
        check(actual==generation.get('layers_sha256'),'Layer output bytes changed after validation')
        if generation.get('layer_method')=='assisted_layers': verify_process(layers.parent/'layer-process.json',layers,prototype['sha256'])
        else: check(set(accepted)==set(ROLES),'Native layers need their own recorded image results')
        for role,a in accepted.items():
            if role!='prototype': check(_primary(a)['sha256']==actual[role],'Accepted layer is unused or replaced without withdrawal: '+role)
        known=set(); items=[]
        for a in r['attempts']:
            for x in a['result']['outputs']:
                known.add(x['file']); used=x['disposition']=='accepted' and not a.get('withdrawal'); role=a['request']['role']
                items.append({'task_id':a['request']['task_id'],'role':role,'file':x['file'],'sha256':x['sha256'],'used':used,
                              'readable_image':x['readable_image'],
                              'usage':('frozen_layer_source' if role=='prototype' else 'embedded_'+role) if used else 'not_used',
                              'reason':a.get('withdrawal',{}).get('reason',x['reason'])})
        for p in (workspace/OUTPUTS).rglob('*'):
            check(not p.is_symlink(),'Managed image returns cannot contain symlinks')
            if p.is_file(): check(p.relative_to(workspace).as_posix() in known,'Unregistered returned file; classify it under its real task')
        summary={'ok':True,'contract':CONTRACT,'reservations':len(r['attempts']),
                 'observed_calls':sum(a['result']['outcome']!='not_called' for a in r['attempts']),
                 'returned_files':len(items),'returned_images':sum(x['readable_image'] for x in items),'used_images':sum(x['used'] for x in items),'unused_images':sum(x['readable_image'] and not x['used'] for x in items),
                 'unreadable_returns':sum(not x['readable_image'] for x in items),
                 'scope':'Registered calls and managed returns only; unregistered host calls outside this workflow are not observable or prevented.'}
        if close and not r['closed']: r['closed']=True; _save(workspace,r)
        _write(workspace/'image-usage.json',{**summary,'items':items})
    return summary
