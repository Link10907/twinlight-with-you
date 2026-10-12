#!/usr/bin/env python3
"""One user instruction, host-driven native tool loop. No external API is required."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from twinlight_core.common import load,ContractError
from twinlight_core import portable
from twinlight_core.portable_layers import layer_plan, record_attempt

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 q=sub.add_parser('plan');q.add_argument('--capabilities',type=Path,required=True)
 q=sub.add_parser('select-style');q.add_argument('request',type=Path);q.add_argument('--workspace',type=Path,required=True)
 q=sub.add_parser('style-status');q.add_argument('--workspace',type=Path,required=True)
 q=sub.add_parser('layers-plan');q.add_argument('--capabilities',type=Path,required=True);q.add_argument('--workspace',type=Path,required=True)
 q=sub.add_parser('record-image-attempt');q.add_argument('--workspace',type=Path,required=True);q.add_argument('--role',choices=('background','subject','effects'),required=True);q.add_argument('--outcome',choices=('success','failure','reference_mismatch'),required=True);q.add_argument('--reason',required=True);q.add_argument('--prototype',type=Path,required=True);q.add_argument('--output',type=Path)
 q=sub.add_parser('run');q.add_argument('input',type=Path);q.add_argument('--workspace',type=Path,required=True);q.add_argument('--capabilities',type=Path,required=True);q.add_argument('--layers',type=Path)
 q=sub.add_parser('deliver');q.add_argument('--workspace',type=Path,required=True);q.add_argument('--out',type=Path,required=True)
 a=p.parse_args()
 try:
  if a.command=='plan':r=portable.route(load(a.capabilities))
  elif a.command=='select-style':
   from twinlight_core.style_selection import select
   r=select(a.workspace,load(a.request,max_bytes=32*1024))
  elif a.command=='style-status':
   from twinlight_core.style_selection import selection_status
   r=selection_status(a.workspace)
  elif a.command=='layers-plan':
   hp=a.workspace/'image-attempts.json';r=layer_plan(load(a.capabilities),load(hp) if hp.exists() else None)
  elif a.command=='record-image-attempt':r=record_attempt(a.workspace,a.role,a.outcome,a.reason,a.prototype,a.output)
  elif a.command=='run':r=portable.run(a.input,a.workspace,load(a.capabilities),layers=a.layers)
  else:r=portable.deliver(a.workspace,a.out)
  print(json.dumps(r,ensure_ascii=False,indent=2));return 0
 except (OSError,ValueError,KeyError) as e:
  print(json.dumps({'ok':False,'complete':False,'error':str(e)},ensure_ascii=False));return 2
if __name__=='__main__':raise SystemExit(main())
