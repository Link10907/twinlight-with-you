#!/usr/bin/env python3
"""Export a completed, verified run to a clean private delivery directory."""
import argparse
import json
from pathlib import Path
from twinlight_core.export_delivery import export


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--link-style',choices=('local','sandbox'),default='local',help='Use sandbox only for actual ChatGPT artifact files exported under /mnt/data')
    args=p.parse_args()
    try:
        result=export(args.workspace,args.out,link_style=args.link_style)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,TypeError,KeyError) as exc:
        print(json.dumps({'ok':False,'error':str(exc),'complete':False},ensure_ascii=False));return 2

if __name__=='__main__': raise SystemExit(main())
