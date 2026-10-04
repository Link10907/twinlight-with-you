#!/usr/bin/env python3
"""Twinlight local pipeline. Host AI authors evidence-backed analysis; this CLI verifies and compiles it."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from twinlight_core.common import ROOT, VERSION, ContractError, load, save, digest, check, schema_check
from twinlight_core.history import normalize, make_chunks
from twinlight_core.evidence import verify
from twinlight_core.compiler import compile_profile, review_markdown, art_brief
from twinlight_core.art import validate_layers, asset_digest
from twinlight_core.site import build
from twinlight_core.extraction import merge_chunks


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version',action='version',version=VERSION)
    sub=p.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('ingest',help='Normalize an explicitly supplied JSON export, locally')
    q.add_argument('input',type=Path);q.add_argument('--format',choices=['auto','chatgpt','claude','generic'],default='auto')
    q.add_argument('--branches',choices=['active','all'],default='active')
    q.add_argument('--scope',choices=['provided_export','provided_subset','current_chat','memory_only'],default='provided_export');q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('chunk',help='Deterministic, complete character-budget source chunks')
    q.add_argument('history',type=Path);q.add_argument('--chars',type=int,default=12000);q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('init-analysis',help='Create a draft; does NOT hallucinate extracted facts')
    q.add_argument('history',type=Path);q.add_argument('--owner-id',required=True);q.add_argument('--name',required=True)
    q.add_argument('--provider',choices=['openai','anthropic','google','deepseek','other','unknown'],default='unknown');q.add_argument('--display-name');q.add_argument('--model')
    q.add_argument('--attribution-source',choices=['run_manifest','host_metadata','user_confirmed','unknown'],default='unknown');q.add_argument('--out',type=Path,required=True)
    for cmd in ['verify','review','compile','art-brief','approve','build']:
        q=sub.add_parser(cmd)
        q.add_argument('history',type=Path);q.add_argument('analysis',type=Path)
        if cmd=='verify':
            q.add_argument('--allow-partial',action='store_true');q.add_argument('--out',type=Path)
            q.add_argument('--all-errors',action='store_true',help='Report every problem with its JSON path instead of stopping at the first')
        else:q.add_argument('--out',type=Path,required=True)
        if cmd in ['compile','build']:q.add_argument('--layout-lock',type=Path)
        if cmd=='art-brief':q.add_argument('--art-direction-file',type=Path,help='Independent strict card design; does not modify reviewed HTML content')
        if cmd=='build':q.add_argument('--layers',type=Path);q.add_argument('--approval',type=Path)
        if cmd=='approve':
            q.add_argument('--by',required=True);q.add_argument('--scope',choices=['local_preview','share'],required=True)
            q.add_argument('--layers',type=Path);q.add_argument('--ack-reviewed',action='store_true',help='Human confirmation has actually occurred; never set on behalf of an unasked user')
    q=sub.add_parser('anchor',help='Fill text_sha256/start/end from message_id + quote for an analysis or chunk result')
    q.add_argument('history',type=Path);q.add_argument('input',type=Path);q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('validate-chunk',help='Check ONE chunk result (all errors) before merge-extractions')
    q.add_argument('history',type=Path);q.add_argument('manifest',type=Path);q.add_argument('result',type=Path)
    q=sub.add_parser('merge-extractions');q.add_argument('history',type=Path);q.add_argument('draft',type=Path);q.add_argument('manifest',type=Path);q.add_argument('results',type=Path);q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('validate-art');q.add_argument('manifest',type=Path);q.add_argument('--persona-digest')
    q=sub.add_parser('demo',help='Build a fictional demo through the generic lite pipeline; no live AI calls')
    q.add_argument('--out',type=Path,default=ROOT/'outputs/demo')
    q.add_argument('--pipeline',action='store_true',help='Instead build the small fictional strict-mode fixture')
    q=sub.add_parser('showcase',help='Explicitly build the author\'s archived original showcase')
    q.add_argument('--out',type=Path,default=ROOT/'outputs/showcase')
    # Lite mode: gated state machine. Agents only follow `next`.
    for name,text in [('start','Create a lite workspace'),('next','Print the single next action'),('check','Validate the current stage and advance'),
                      ('status','Show stage gates'),('report','Write report.html for the workspace')]:
        q=sub.add_parser(name,help=text);q.add_argument('--workspace',type=Path,required=True)
    q=sub.add_parser('confirm',help='Record the person\'s explicit approval of the text');q.add_argument('--workspace',type=Path,required=True);q.add_argument('--user-reply',required=True)
    q=sub.add_parser('art',help='Explicitly choose native layers, a static prototype or a placeholder');q.add_argument('--workspace',type=Path,required=True)
    mode=q.add_mutually_exclusive_group(required=True)
    for name in ('layered','static','placeholder'):mode.add_argument('--'+name,action='store_true')
    q=sub.add_parser('unblock',help='Resume a stage after repairing its reported problem');q.add_argument('--workspace',type=Path,required=True);q.add_argument('--note',required=True)
    q=sub.add_parser('lite-check',help='Validate a lite JSON (all errors at once)');q.add_argument('input',type=Path)
    q=sub.add_parser('card-spec',help='Write a per-person native-layer card brief and bound manifest template')
    q.add_argument('input',type=Path);q.add_argument('--out',type=Path,required=True)
    q.add_argument('--prototype',type=Path,help='Use the selected prototype\'s native canvas without resizing')
    q.add_argument('--composition',type=Path,help='Optional current-person composition lock JSON')
    q.add_argument('--art-prompt-file',type=Path,help='Independent card art brief; does not change HTML content or binding')
    q=sub.add_parser('lite-build',help='Build one HTML from a lite JSON without the state machine')
    q.add_argument('input',type=Path);q.add_argument('--out',type=Path,required=True)
    q.add_argument('--portrait',type=Path);q.add_argument('--prototype',type=Path)
    q.add_argument('--character','--subject',dest='character',type=Path);q.add_argument('--background',type=Path)
    q.add_argument('--layers',type=Path,help='A six-layer manifest bound to this person\'s card-spec persona_digest')
    q.add_argument('--confirmed',action='store_true',help='The person has reviewed the text; enables card export')
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        if args.cmd=='ingest':
            h=normalize(args.input,args.format,args.branches,args.scope);save(args.out,h);result={'ok':True,'history_digest':h['history_digest'],'coverage':h['coverage']}
        elif args.cmd=='chunk':result=make_chunks(load(args.history),args.out,args.chars)
        elif args.cmd=='init-analysis':
            h=load(args.history);names={'openai':'GPT','anthropic':'Claude','google':'Gemini','deepseek':'DeepSeek'}
            result={'schema_version':'1.0','owner':{'id':args.owner_id,'display_name':args.name},'history_digest':h['history_digest'],
                'summary_meta':{'provider':args.provider,'display_name':names.get(args.provider,args.display_name),'model':args.model,
                    'generated_at':dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z'),'attribution_source':args.attribution_source},
                'facts':[],'message_dispositions':[],'themes':[],'card':None}
            schema_check(result,'analysis.schema.json');save(args.out,result)
            result={'ok':True,'state':'draft_requires_AI_extraction_and_reconciliation','out':str(args.out)}
        elif args.cmd=='merge-extractions':
            merged=merge_chunks(load(args.history),load(args.draft),args.manifest,args.results);save(args.out,merged);result={'ok':True,'facts':len(merged['facts']),'state':'reconcile_before_narrative'}
        elif args.cmd=='anchor':
            from twinlight_core.evidence import anchor_document
            report=anchor_document(load(args.history),load(args.input));doc=report.pop('document')
            if doc is not None:save(args.out,doc);report['out']=str(args.out)
            print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['ok'] else 1
        elif args.cmd=='validate-chunk':
            from twinlight_core.extraction import validate_chunk
            report=validate_chunk(load(args.history),args.manifest,load(args.result))
            print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['ok'] else 1
        elif args.cmd=='validate-art':result=validate_layers(args.manifest,args.persona_digest)
        elif args.cmd in ('start','next','check','status','report','confirm','art','unblock'):
            from twinlight_core import state as fsm
            if args.cmd=='start':result=fsm.start(args.workspace)
            elif args.cmd=='next':result=fsm.next_action(args.workspace)
            elif args.cmd=='status':result=fsm.status(args.workspace)
            elif args.cmd=='confirm':result=fsm.confirm(args.workspace,args.user_reply)
            elif args.cmd=='art':result=fsm.choose_art(args.workspace,'static' if args.static else 'placeholder' if args.placeholder else 'layered')
            elif args.cmd=='unblock':result=fsm.unblock(args.workspace,args.note)
            elif args.cmd=='report':
                from twinlight_core.report import write_report
                result={'ok':True,'report':str(write_report(args.workspace))}
            else:
                result=fsm.check_stage(args.workspace)
                print(json.dumps(result,ensure_ascii=False,indent=2))
                return 1 if result.get('status') in ('failed','blocked') else 0
        elif args.cmd=='lite-check':
            from twinlight_core import lite
            report=lite.check_text(args.input.read_text(encoding='utf-8'));report.pop('data')
            if not report['ok']:report['repair_prompt']=lite.repair_prompt(report['errors'])
            print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['ok'] else 1
        elif args.cmd=='card-spec':
            from twinlight_core.cardgen import card_spec, read_card_data
            data=read_card_data(args.input)
            canvas=None
            composition=load(args.composition) if args.composition else None
            if args.prototype:
                from twinlight_core.site import open_card_image
                canvas=open_card_image(args.prototype).size
                if composition and composition.get('source_prototype_sha256'):
                    import hashlib
                    check(hashlib.sha256(args.prototype.read_bytes()).hexdigest()==composition['source_prototype_sha256'],
                          '构图锁对应另一张原型；请使用当前选定的原型')
            spec=card_spec(data,generated_at=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),canvas=canvas,composition=composition,
                           art_prompt=args.art_prompt_file.read_text(encoding='utf-8') if args.art_prompt_file else None)
            save(args.out,spec);result={'ok':True,'out':str(args.out),'persona_digest':spec['persona_digest']}
        elif args.cmd=='lite-build':
            from twinlight_core import lite
            from twinlight_core.site import build_lite
            report=lite.check_text(args.input.read_text(encoding='utf-8'))
            check(report['ok'],'JSON 未通过校验，先运行 lite-check：'+'；'.join(f"{e['path']} {e['message']}" for e in report['errors'][:5]))
            result=build_lite(report['data'],args.out,generated_at=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),
                              confirmed=args.confirmed,portrait=args.portrait,prototype=args.prototype,
                              character=args.character,background=args.background,layers=args.layers)
        elif args.cmd=='showcase':
            from twinlight_core.showcase import build_showcase
            result=build_showcase(args.out)
        elif args.cmd=='demo' and not args.pipeline:
            from twinlight_core import lite
            from twinlight_core.site import build_lite
            folder=ROOT/'examples/generated-demo'
            source=folder/'twinlight.json' if (folder/'twinlight.json').is_file() else ROOT/'examples/lite/example.json'
            check(source.is_file(),'这个个人使用包不含虚构示例。请在源码仓库或明确的演示包中运行 demo。')
            report=lite.check_text(source.read_text(encoding='utf-8'))
            check(report['ok'],'虚构示例没有通过通用 lite-check，不能构建')
            manifest=folder/'card/layers.json' if (folder/'card/layers.json').is_file() else None
            result=build_lite(report['data'],args.out,
                generated_at=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),
                layers=manifest,confirmed=True)
        elif args.cmd=='demo':
            check((ROOT/'examples/demo/history.json').is_file() and (ROOT/'examples/demo/analysis.json').is_file(),
                  'This personal-use package has no fictional demo. Use the source repository or the separately packaged --include-demo bundle for an explicit demo run.')
            result=build(load(ROOT/'examples/demo/history.json'),load(ROOT/'examples/demo/analysis.json'),args.out)
        else:
            h,a=load(args.history),load(args.analysis)
            if args.cmd=='verify':
                result=verify(h,a,not args.allow_partial,collect=args.all_errors)
                if args.out:save(args.out,result)
                if not result['ok']:
                    print(json.dumps(result,ensure_ascii=False,indent=2));return 1
            elif args.cmd=='review':
                args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(review_markdown(h,a),encoding='utf-8');result={'ok':True,'private_review':str(args.out)}
            elif args.cmd=='approve':
                check(args.ack_reviewed,'Approval requires actual human review and --ack-reviewed')
                verify(h,a)
                art_hash=None
                if args.scope=='share':
                    check(args.layers is not None,'Share approval must bind reviewed artwork')
                    profile,_,_=compile_profile(h,a)
                    art=validate_layers(args.layers,profile['persona']['persona_digest'])
                    check(art['art_status']=='approved','Artwork is not approved; cannot approve placeholder as a personal card')
                    art_hash=asset_digest(args.layers)
                result={'schema_version':'1.0','analysis_digest':digest(a),'art_digest':art_hash,'approved_by':args.by,'scope':args.scope,
                    'confirmed_at':dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z'),
                    'acknowledgments':{k:True for k in ['reviewed_personal_facts','reviewed_public_copy','understands_source_coverage','permits_selected_output']}}
                schema_check(result,'approval.schema.json');save(args.out,result)
                result={'ok':True,'receipt':str(args.out),'warning':'Receipt records confirmation, not authenticated identity or a legal release.'}
            elif args.cmd in ['compile','art-brief']:
                previous=load(args.layout_lock) if getattr(args,'layout_lock',None) else None
                profile,layout,audit=compile_profile(h,a,previous)
                if args.cmd=='art-brief':
                    save(args.out,art_brief(a,profile['persona']['persona_digest'],load(args.art_direction_file) if args.art_direction_file else None))
                    result={'ok':True,'out':str(args.out)}
                else:
                    save(args.out/'profile.json',profile);save(args.out/'layout.lock.json',layout);save(args.out/'audit.json',audit)
                    result={'ok':True,'stars':len(layout['stars']),'planets':len(layout['topics']),'draft':True}
            elif args.cmd=='build':
                result=build(h,a,args.out,previous=load(args.layout_lock) if args.layout_lock else None,layers=args.layers,
                    approval=load(args.approval) if args.approval else None)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ContractError,ValueError,TypeError,KeyError,OSError) as exc:
        # Do not print traceback or entire source documents on validation errors.
        print('Twinlight: '+str(exc),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
