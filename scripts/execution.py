#!/usr/bin/env python3
"""Execute image generation or a real independent review. Paid/remote calls are opt-in."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from twinlight_core.execution_bridge import doctor, probe_reviewer, write_host, invoke_image, invoke_review


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('doctor','probe-reviewer','host','image','review'):
        q=sub.add_parser(name);q.add_argument('--config',type=Path,required=True)
        if name!='doctor': q.add_argument('--out',type=Path,required=True)
        else: q.add_argument('--out',type=Path)
        if name in ('probe-reviewer','image','review'):q.add_argument('--allow-provider-calls',action='store_true')
        if name=='probe-reviewer':q.add_argument('--image',type=Path,required=True)
        if name=='host':
            q.add_argument('--probe',type=Path,required=True);q.add_argument('--browser-probe',type=Path,required=True)
        if name=='image':
            q.add_argument('--plan',type=Path,required=True);q.add_argument('--role',choices=('prototype','background','subject','effects'),required=True)
            q.add_argument('--workspace',type=Path,required=True);q.add_argument('--host-capabilities',type=Path,required=True)
        if name=='review':
            q.add_argument('--packet',type=Path,required=True);q.add_argument('--root',type=Path,required=True)
            q.add_argument('--host-capabilities',type=Path,required=True)
            q.add_argument('--layers',type=Path);q.add_argument('--front',type=Path);q.add_argument('--preview',type=Path)
            q.add_argument('--activate',action='store_true')
    a=p.parse_args(argv)
    try:
        if a.command=='doctor':
            r=doctor(a.config)
            if a.out:
                from twinlight_core.provider_runtime import save_new
                save_new(a.out,r)
        elif a.command=='probe-reviewer':r=probe_reviewer(a.config,a.image,a.out,allowed=a.allow_provider_calls)
        elif a.command=='host':r=write_host(a.config,a.probe,a.browser_probe,a.out)
        elif a.command=='image':r=invoke_image(a.config,a.plan,a.role,a.workspace,a.host_capabilities,a.out,allowed=a.allow_provider_calls)
        else:r=invoke_review(a.config,a.packet,a.root,a.host_capabilities,a.out,allowed=a.allow_provider_calls,layers=a.layers,front=a.front,preview=a.preview,activate=a.activate)
        print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r.get('ok') else 2
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'ok':False,'code':getattr(exc,'code','invalid_input'),'error':str(exc),'release_authorized':False},ensure_ascii=False,indent=2));return 2

if __name__=='__main__':raise SystemExit(main())
