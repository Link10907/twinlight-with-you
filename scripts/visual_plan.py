#!/usr/bin/env python3
"""Compile concrete per-layer prompts and register actual host image outputs."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from twinlight_core.visual_contract import catalog,default_style,validate_design,visual_keywords,subject_prompt,_json
from twinlight_core.generation_plan import write_plan,register_image,bind_composite,bind_review,repair_plan,revalidate_image

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('styles')
    q=sub.add_parser('check');q.add_argument('design',type=Path);q.add_argument('--persona-digest')
    q=sub.add_parser('compile');q.add_argument('design',type=Path);q.add_argument('--out',type=Path,required=True)
    q.add_argument('--phase',choices=['prototype','layers'],default='prototype');q.add_argument('--canvas',nargs=2,type=int);q.add_argument('--capabilities',type=Path)
    q=sub.add_parser('dispatch');q.add_argument('plan',type=Path);q.add_argument('--role',choices=['prototype','background','subject','effects'],required=True)
    q.add_argument('--workspace',type=Path,required=True);q.add_argument('--host-capabilities',type=Path,required=True);q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('record');q.add_argument('plan',type=Path);q.add_argument('--role',choices=['prototype','background','subject','effects'],required=True)
    q.add_argument('--dispatch',type=Path,required=True)
    for name in ['image','raw-response']:q.add_argument('--'+name,type=Path,required=True)
    for name in ['tool','call-id','artifact-id']:q.add_argument('--'+name,required=True)
    q=sub.add_parser('repair');q.add_argument('plan',type=Path)
    q.add_argument('--role',choices=['prototype','background','subject','effects'],required=True)
    instructions=q.add_mutually_exclusive_group(required=True)
    instructions.add_argument('--instruction');instructions.add_argument('--instruction-file',type=Path)
    q=sub.add_parser('revalidate');q.add_argument('plan',type=Path);q.add_argument('--attempt-key',required=True)
    for name in ['tool','call-id','artifact-id']:q.add_argument('--'+name,required=True)
    q=sub.add_parser('bind-composite');q.add_argument('--layers',type=Path,required=True);q.add_argument('--image',type=Path,required=True)
    q=sub.add_parser('bind-review');q.add_argument('--layers',type=Path,required=True);q.add_argument('--review',type=Path,required=True)
    q.add_argument('--front',type=Path);q.add_argument('--preview',type=Path)
    a=p.parse_args(argv)
    try:
        if a.cmd=='styles':result={'styles':[{k:x[k] for k in ('id','name','version','sha256')} for x in catalog()],'default_style':default_style()['id'],'default_subject':None,'default_typography':default_style()['typography_default']}
        elif a.cmd=='check':
            d=validate_design(_json(a.design),a.persona_digest);result={'ok':True,'visual_keywords':visual_keywords(d),'subject_prompt':subject_prompt(d),'image_generation_performed':False}
        elif a.cmd=='compile':
            caps=_json(a.capabilities) if a.capabilities else None
            if caps and caps.get('version')=='host-capabilities-2':
                from twinlight_core.host_contract import assess
                h=assess(caps,'card')
                if not h['ok']:raise ValueError('Actual host capabilities are not ready: '+', '.join(h['gaps']))
                caps=caps['image']
            canvas=a.canvas
            if canvas is None and caps and caps.get('canvas_selection')!='prompt_only':
                candidates=[size for size in caps.get('native_canvases',[]) if min(size)>=256 and size[0]*size[1]<=16000000 and abs(size[0]/size[1]-.75)<.01]
                canvas=max(candidates,key=lambda s:s[0]*s[1]) if candidates else None
            result=write_plan(a.design,a.out,phase=a.phase,canvas=canvas or (1080,1440),capabilities=caps)
        elif a.cmd=='dispatch':
            from twinlight_core.image_dispatch import dispatch
            result=dispatch(a.plan,a.role,a.workspace,a.host_capabilities,a.out)
        elif a.cmd=='bind-composite':result=bind_composite(a.layers,a.image)
        elif a.cmd=='bind-review':result=bind_review(a.layers,a.review,front=a.front,preview=a.preview)
        elif a.cmd=='repair':result=repair_plan(a.plan,a.role,a.instruction_file.read_text(encoding='utf-8') if a.instruction_file else a.instruction)
        elif a.cmd=='revalidate':result=revalidate_image(a.plan,a.attempt_key,tool=a.tool,call_id=a.call_id,artifact_id=a.artifact_id)
        else:result=register_image(a.plan,a.role,a.image,a.raw_response,tool=a.tool,call_id=a.call_id,artifact_id=a.artifact_id,dispatch_path=a.dispatch)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result.get('ok',True) else 2
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'ok':False,'code':getattr(exc,'code','invalid_input'),'error':str(exc)},ensure_ascii=False),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
