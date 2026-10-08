"""Freeze one image-only job before a host call; count attempts across card dirs.

This is a transport handoff, NOT an authenticated provider request. The producer
cannot obtain a second-agent capability by editing these records. Hosts must
actually isolate image tasks and enforce writer separation.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
from .art_quality import read_json, sha256, checked_ref
from .host_contract import assess
from .visual_contract import VisualContractError


def _fail(code, message): raise VisualContractError(code,message)


def _save(path: Path, value: dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temp.replace(path)


def dispatch(plan_path: Path, role: str, workspace: Path, host_path: Path, out: Path) -> dict:
    from .generation_plan import IMAGE_ROLES, check_capabilities, _task_scope
    plan_path,workspace,host_path,out=(Path(p).resolve() for p in (plan_path,workspace,host_path,out))
    root=plan_path.parent
    if not out.is_relative_to(root) or out.exists(): _fail('dispatch_path','Use a new dispatch file inside the card directory')
    plan=read_json(plan_path);host=read_json(host_path);state=read_json(workspace/'run-state.json')
    report=assess(host,state.get('mode','both'))
    if not report['may_start_image_calls']: _fail('capability_blocked','Resolve actual host capability gaps before image generation: '+', '.join(report['gaps']))
    if state.get('persona_digest')!=plan.get('persona_digest'): _fail('wrong_persona','Dispatch belongs to another current-person run')
    if plan.get('ready_for_image_call') is not True: _fail('plan_not_ready','Compile with checked image capabilities first')
    if plan.get('capabilities') != host.get('image'): _fail('capabilities_changed','Recompile using the current host.image contract')
    check_capabilities(plan['capabilities'], plan['canvas'])
    jobs=[j for j in plan.get('jobs',[]) if j.get('role')==role]
    if role not in IMAGE_ROLES or len(jobs)!=1: _fail('wrong_phase','This plan does not contain the selected role')
    job=jobs[0]
    if job.get('task_scope')!=_task_scope(role): _fail('image_task_scope','Exactly one image-only deliverable is required')
    prompt=checked_ref(root,job['prompt']);checked_ref(root,plan['design'])
    for ref in job['reference_images']: checked_ref(root,ref)
    if role!='prototype':
        from .art_quality import check_evidence
        gate=check_evidence(root/'layers.json',plan['persona_digest'],stage='prototype')
        if not gate['ok']: _fail('prototype_not_reviewed','Do not dispatch native layers before independent prototype approval')
    # A run-scoped ledger survives prompt recompilation or changing CARD directories.
    ledger_path=workspace/'production-attempts.json'; lock=workspace/'.production-attempts.lock'
    try: fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError: _fail('dispatch_busy','Another dispatch owns the run lock; inspect it, never start a parallel duplicate call')
    os.close(fd)
    try:
        ledger=read_json(ledger_path) if ledger_path.exists() else {'version':'production-attempts-1','persona_digest':plan['persona_digest'],'attempts':[]}
        if ledger.get('persona_digest')!=plan['persona_digest']: _fail('wrong_persona','Attempt ledger belongs to another person')
        used=sum(a.get('role')==role for a in ledger['attempts'])
        if used>=3: _fail('retry_limit','Three call reservations already exist for this role in the same run; preserve partial results')
        payload={'version':'image-dispatch-1','role':role,'persona_digest':plan['persona_digest'],
                 'producer_session_id':host['producer_session_id'],'workspace':str(workspace),
                 'plan_sha256':sha256(plan_path),'design':plan['design'],
                 'prompt':job['prompt'],'prompt_text':prompt.read_text(encoding='utf-8'),
                 'reference_images':job['reference_images'],'task_scope':job['task_scope'],
                 'operation':job['operation'],'transparent':job['transparent'],
                 'canvas':plan['canvas'],'prompt_transport':host['image']['prompt_transport'],
                 'reference_transport':host['image']['reference_transport'],
                 'host_capabilities_sha256':sha256(host_path),'host_capabilities_source':str(host_path),
                 'attempt_number':used+1,'created_at':dt.datetime.now(dt.timezone.utc).isoformat(),
                 'provider_input_verified':False,'agent_invoked':False,
                 'tool_instruction':'Pass only prompt_text, the actual listed images and supported image parameters. Do not attach this whole JSON, website instructions or conversation history.'}
        _save(out,payload)
        ledger['attempts'].append({'role':role,'number':used+1,'dispatch':str(out),
                                  'sha256':sha256(out),'status':'reserved_not_observed'})
        _save(ledger_path,ledger)
        return {'ok':True,'dispatch':str(out),'attempts_used':used+1,'attempts_remaining':2-used,
                'agent_invoked':False,'provider_input_verified':False}
    finally: lock.unlink(missing_ok=True)


def verify_dispatch(plan_path: Path, role: str, path: Path | None, *, call_id: str | None=None) -> dict:
    if path is None: _fail('dispatch_missing','Create a run-scoped image dispatch before calling the tool; registration cannot invent a dispatch afterward')
    plan_path=Path(plan_path).resolve();root=plan_path.parent;path=Path(path).resolve()
    if not path.is_relative_to(root): _fail('dispatch_path','Dispatch must be stored inside the card directory')
    value=read_json(path);plan=read_json(plan_path)
    if value.get('version')!='image-dispatch-1' or value.get('role')!=role or value.get('plan_sha256')!=sha256(plan_path):
        _fail('stale_dispatch','The actual call must use the current immutable plan')
    jobs=[j for j in plan.get('jobs',[]) if j.get('role')==role]
    if len(jobs)!=1: _fail('wrong_phase','Missing unique job')
    job=jobs[0]
    for k in ('prompt','reference_images','task_scope','operation','transparent'):
        if value.get(k)!=job.get(k): _fail('dispatch_changed','Dispatch and compiled job disagree: '+k)
    prompt=checked_ref(root,job['prompt'])
    if value.get('prompt_text')!=prompt.read_text(encoding='utf-8'): _fail('dispatch_changed','Dispatch prompt bytes changed')
    host_path=Path(value['host_capabilities_source']);workspace=Path(value['workspace'])
    host=read_json(host_path);state=read_json(workspace/'run-state.json')
    if sha256(host_path)!=value['host_capabilities_sha256'] or not assess(host,state['mode'])['may_start_image_calls']:
        _fail('capabilities_changed','Host contract changed after dispatch')
    if state.get('persona_digest')!=plan['persona_digest']: _fail('wrong_persona','Run binding changed')
    ledger=read_json(workspace/'production-attempts.json')
    matches=[a for a in ledger['attempts'] if a.get('dispatch')==str(path) and a.get('sha256')==sha256(path)]
    if len(matches)!=1 or matches[0].get('status')!='reserved_not_observed': _fail('dispatch_reused','Use a fresh recorded invocation; a consumed reservation cannot be replayed')
    if call_id and any(a.get('call_id')==call_id for a in ledger['attempts']): _fail('call_replayed','This actual image call was already registered')
    return value


def consume_dispatch(path: Path, call_id: str, response_path: Path):
    path=Path(path).resolve();value=read_json(path)
    ledger_path=Path(value['workspace'])/'production-attempts.json';ledger=read_json(ledger_path)
    for a in ledger['attempts']:
        if a.get('dispatch')==str(path) and a.get('sha256')==sha256(path):
            if a['status']!='reserved_not_observed': _fail('dispatch_reused','Invocation already consumed')
            a.update(status='return_observed',call_id=call_id,raw_response_sha256=sha256(response_path))
            _save(ledger_path,ledger);return
    _fail('dispatch_missing','Reservation missing from the current run ledger')


def check_recorded_dispatch(root: Path, call: dict, inputs: dict) -> None:
    """Recheck consumed image evidence without requiring the plan's old phase."""
    from .art_quality import require
    request=call.get('request',{})
    dispatch_path=checked_ref(root,request.get('dispatch'))
    value=read_json(dispatch_path);inputs[str(dispatch_path)]=sha256(dispatch_path)
    require(value.get('version')=='image-dispatch-1','dispatch_missing','Native artwork must retain its pre-call dispatch')
    for key in ('role','canvas','transparent','operation','reference_images','task_scope'):
        require(value.get(key)==request.get(key),'dispatch_changed','Recorded dispatch differs from returned image request: '+key)
    require(value.get('prompt',{}).get('sha256')==request.get('prompt',{}).get('sha256'),
            'dispatch_prompt_changed','Provider-task record must retain the compiled prompt bytes')
    prompt=checked_ref(root,request['prompt'])
    require(value.get('prompt_text')==prompt.read_text(encoding='utf-8'),'dispatch_prompt_changed','The frozen prompt text changed')
    ledger_path=Path(value['workspace'])/'production-attempts.json'
    ledger=read_json(ledger_path)
    matches=[a for a in ledger.get('attempts',[]) if a.get('dispatch')==str(dispatch_path) and a.get('sha256')==sha256(dispatch_path)]
    require(len(matches)==1 and matches[0].get('status')=='return_observed' and matches[0].get('call_id')==call.get('call_id'),
            'dispatch_not_observed','This role needs its own consumed, actual-call record')
    raw=checked_ref(root,call['raw_response'])
    require(matches[0].get('raw_response_sha256')==sha256(raw),'dispatch_response_changed','The run ledger refers to another response')
    # Ledger may grow for other roles; include current bytes in this pass's stability snapshot.
    inputs[str(ledger_path)]=sha256(ledger_path)
