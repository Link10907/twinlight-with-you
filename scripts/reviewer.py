#!/usr/bin/env python3
"""Prepare isolated review inputs, import actual responses, or verify release. Never invokes an agent."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from twinlight_core.independent_review import release_targets,check_release,release_checks
from twinlight_core.art_quality import ArtEvidenceError,read_json,sha256,snapshot,REVIEW_CHECKS


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('template','check','packet','import','activate'))
    p.add_argument('--workspace',type=Path)
    p.add_argument('--root',type=Path,help='For import: card directory for art stages, run directory for release')
    p.add_argument('--stage',choices=('prototype','composite','final','release'),default='release')
    p.add_argument('--layers',type=Path);p.add_argument('--front',type=Path);p.add_argument('--preview',type=Path)
    p.add_argument('--packet',type=Path,help='Pre-task reviewer packet (portable import, no provider trace required)')
    p.add_argument('--host-capabilities',type=Path,help='Actual independent reviewer capability source')
    p.add_argument('--evidence',type=Path,help='Actual capture_review.py output for dynamic review; never a producer verdict')
    p.add_argument('--response',type=Path);p.add_argument('--trace',type=Path);p.add_argument('--out',type=Path)
    a=p.parse_args(argv)
    try:
        if a.command=='activate':
            if not a.workspace or not a.response:p.error('activate needs --workspace and --response')
            from twinlight_core.review_exchange import activate_release
            r=activate_release(a.workspace,a.response)
        elif a.command=='import':
            if not all((a.root,a.response,a.out)): p.error('import needs --root, --response and --out')
            if not a.trace and not all((a.packet,a.host_capabilities)): p.error('Use --packet and --host-capabilities, or an existing real --trace')
            from twinlight_core.review_exchange import import_response
            r=import_response(a.root,a.response,a.trace,a.out,packet_path=a.packet,host_path=a.host_capabilities)
        elif a.command=='check':
            if not a.workspace:p.error('--workspace is required')
            run=read_json(a.workspace/'run-report.json');r=check_release(a.workspace,run.get('outputs',{}),run['mode'])
        else:
            if not a.out:p.error('--out is required')
            if a.out.exists(): raise ValueError('Do not overwrite a previous reviewer response or packet')
            if a.stage=='release':
                if not a.workspace:p.error('--workspace is required for release')
                run=read_json(a.workspace/'run-report.json');mode=run['mode'];targets=release_targets(a.workspace,run['outputs'],mode)
                r={'stage':'release','targets':targets,'decision':'pending','handoff':None,'blockers':[],
                   'checks':{k:{'passed':False,'observation':''} for k in release_checks(mode)},
                   'captures':{'desktop':None,'mobile':None},'runtime':None}
                if mode!='html':r['effect_frames']={k:None for k in ('foil_off','foil_on','depth_off','depth_on')}
                sources={str((a.workspace/ref['file']).resolve()):ref['sha256'] for ref in targets['outputs'].values()}
                if a.command=='packet' and mode!='html':
                    state=read_json(a.workspace/'run-state.json')
                    layers=Path(state['layers_source'])
                    _,_,_,art_sources=snapshot(layers,state['persona_digest'],stage='final',
                        front=Path(run['outputs']['card_front']),preview=Path(run['outputs']['card_preview']))
                    sources.update(art_sources)
                content=a.workspace/'content.json'
                if content.is_file():sources[str(content.resolve())]=sha256(content)

            else:
                if not a.layers:p.error('--layers is required for art review')
                manifest=read_json(a.layers)
                targets,_,design,sources=snapshot(a.layers,manifest['persona_digest'],stage=a.stage,front=a.front,preview=a.preview)
                if a.stage=='prototype':
                    # Downstream asset registration legitimately changes the manifest.
                    # Prototype approval binds persona/design/prototype/style, not future layers.
                    sources.pop(str(a.layers.resolve()),None)
                from twinlight_core.visual_contract import review_checks
                r={'stage':a.stage,'targets':targets[a.stage],'observer':None,'observed_at':None,'decision':'pending',
                   'checks':{k:{'passed':False,'observation':''} for k in review_checks(design,a.stage,REVIEW_CHECKS[a.stage])},
                   'capture':None,'handoff':None,'blockers':[]}
                if a.stage=='final':r['views']={'left':None,'right':None,'mobile':None}
            if a.evidence:
                from twinlight_core.review_exchange import attach_runtime_evidence
                evidence_root = a.workspace if a.stage=='release' else a.layers.parent
                r,extra=attach_runtime_evidence(r,a.evidence,evidence_root)
                sources.update(extra)
            if a.command=='packet':
                from twinlight_core.review_exchange import packet
                # Temporary pending template is not a review and is removed after packet assembly.
                import tempfile
                with tempfile.TemporaryDirectory() as folder:
                    t=Path(folder)/'pending.json';t.write_text(json.dumps(r,ensure_ascii=False),encoding='utf-8')
                    root=Path(__file__).resolve().parents[1]
                    for file in ('REVIEWER.md','references/quality-workflow.md'):
                        sources[str(root/file)]=sha256(root/file)
                    r=packet(t,sources,a.out)
            else:
                a.out.parent.mkdir(parents=True,exist_ok=True)
                with a.out.open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
                r={'ok':True,'out':str(a.out),'decision':'pending','agent_invoked':False}
        print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r.get('ok') else 2
    except (ArtEvidenceError,OSError,ValueError,KeyError,TypeError) as e:
        print(json.dumps({'ok':False,'error':str(e)},ensure_ascii=False));return 2

if __name__=='__main__':raise SystemExit(main())
