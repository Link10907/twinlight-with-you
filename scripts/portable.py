#!/usr/bin/env python3
"""One user instruction, host-driven native tool loop. No external API is required."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from twinlight_core.common import load,ContractError
from twinlight_core import portable

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 q=sub.add_parser('plan');q.add_argument('--capabilities',type=Path,required=True)
 q=sub.add_parser('run');q.add_argument('input',type=Path);q.add_argument('--workspace',type=Path,required=True);q.add_argument('--capabilities',type=Path,required=True);q.add_argument('--layers',type=Path)
 q=sub.add_parser('deliver');q.add_argument('--workspace',type=Path,required=True);q.add_argument('--out',type=Path,required=True)
 a=p.parse_args()
 try:
  if a.command=='plan':r=portable.route(load(a.capabilities))
  elif a.command=='run':r=portable.run(a.input,a.workspace,load(a.capabilities),layers=a.layers)
  else:r=portable.deliver(a.workspace,a.out)
  print(json.dumps(r,ensure_ascii=False,indent=2));return 0
 except (OSError,ValueError,KeyError) as e:
  print(json.dumps({'ok':False,'complete':False,'error':str(e)},ensure_ascii=False));return 2
if __name__=='__main__':raise SystemExit(main())
