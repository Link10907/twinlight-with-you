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
        if cmd=='verify':q.add_argument('--allow-partial',action='store_true');q.add_argument('--out',type=Path)
        else:q.add_argument('--out',type=Path,required=True)
        if cmd in ['compile','build']:q.add_argument('--layout-lock',type=Path)
        if cmd=='build':q.add_argument('--layers',type=Path);q.add_argument('--approval',type=Path)
        if cmd=='approve':
            q.add_argument('--by',required=True);q.add_argument('--scope',choices=['local_preview','share'],required=True)
            q.add_argument('--layers',type=Path);q.add_argument('--ack-reviewed',action='store_true',help='Human confirmation has actually occurred; never set on behalf of an unasked user')
    q=sub.add_parser('merge-extractions');q.add_argument('history',type=Path);q.add_argument('draft',type=Path);q.add_argument('manifest',type=Path);q.add_argument('results',type=Path);q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('validate-art');q.add_argument('manifest',type=Path);q.add_argument('--persona-digest')
    q=sub.add_parser('demo',help='Build the explicitly fictional example; no live AI calls')
    q.add_argument('--out',type=Path,default=ROOT/'outputs/demo')
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
        elif args.cmd=='validate-art':result=validate_layers(args.manifest,args.persona_digest)
        elif args.cmd=='demo':
            check((ROOT/'examples/demo/history.json').is_file() and (ROOT/'examples/demo/analysis.json').is_file(),
                  'This personal-use package has no fictional demo. Use the source repository or the separately packaged --include-demo bundle for an explicit demo run.')
            result=build(load(ROOT/'examples/demo/history.json'),load(ROOT/'examples/demo/analysis.json'),args.out)
        else:
            h,a=load(args.history),load(args.analysis)
            if args.cmd=='verify':
                result=verify(h,a,not args.allow_partial)
                if args.out:save(args.out,result)
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
                if args.cmd=='art-brief':save(args.out,art_brief(a,profile['persona']['persona_digest']));result={'ok':True,'out':str(args.out)}
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
