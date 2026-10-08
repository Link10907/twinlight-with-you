#!/usr/bin/env python3
"""Prepare a pending host contract or check facts reported by the actual host."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from twinlight_core.host_contract import template, load_assessment


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('template','check'))
    p.add_argument('--capabilities', type=Path)
    p.add_argument('--mode', choices=('html','card','both'), default='both')
    p.add_argument('--out',type=Path)
    a=p.parse_args(argv)
    try:
        if a.command=='template':
            if a.out is None: p.error('--out is required')
            a.out.parent.mkdir(parents=True,exist_ok=True)
            with a.out.open('x',encoding='utf-8') as f:
                json.dump(template(),f,ensure_ascii=False,indent=2)
            r={'ok':True,'status':'pending','out':str(a.out),'agent_invoked':False}
        else:
            r=load_assessment(a.capabilities,a.mode)
            if a.out:
                a.out.parent.mkdir(parents=True,exist_ok=True)
                with a.out.open('x',encoding='utf-8') as f: json.dump(r,f,ensure_ascii=False,indent=2)
        print(json.dumps(r,ensure_ascii=False,indent=2)); return 0 if r['ok'] else 2
    except (OSError, ValueError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False)); return 2

if __name__=='__main__': raise SystemExit(main())
