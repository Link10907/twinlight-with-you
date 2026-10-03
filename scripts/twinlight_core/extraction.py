"""Merge host-produced chunk results without an implicit semantic overwrite."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from .common import check, load, digest, local_asset
from .evidence import verify


def merge_chunks(history: dict, draft: dict, manifest_path: Path, results_dir: Path) -> dict:
    manifest=load(manifest_path)
    check(manifest['history_digest']==history['history_digest']==draft['history_digest'],'Chunk batch belongs to another history')
    expected={entry['path']:entry for entry in manifest['chunks']}
    results=[load(p) for p in sorted(results_dir.glob('*.json'))]
    check(len(results)==len(expected),'Each chunk must have exactly one result JSON')
    seen=set();facts={};dispositions={}
    for result in results:
        check(set(result)=={'chunk_path','chunk_sha256','history_digest','facts','message_dispositions'},'Unexpected extraction result shape')
        name=result['chunk_path'];check(name in expected and name not in seen,'Unknown/duplicate extraction chunk')
        seen.add(name);entry=expected[name]
        chunk=load(local_asset(manifest_path.parent,name))
        check(result['chunk_sha256']==entry['sha256']==digest(chunk),'Chunk hash mismatch')
        check(result['history_digest']==history['history_digest'],'Stale chunk extraction')
        segment_users={s['message_id'] for s in chunk['segments'] if s['role']=='user'}
        check({d['message_id'] for d in result['message_dispositions']}==segment_users,'Each user segment needs a disposition')
        for fact in result['facts']:
            check(all(any(seg['message_id']==ref['message_id'] and seg['start']<=ref['start']<ref['end']<=seg['end'] for seg in chunk['segments']) for ref in fact['evidence']), 'Map citation falls outside its assigned source segments')
            check(all(r['message_id'] in segment_users for r in fact['evidence']),'Map-stage facts may cite only user messages in this chunk')
            fid=fact['id']
            if fid in facts:
                check({k:v for k,v in fact.items() if k!='evidence'}=={k:v for k,v in facts[fid].items() if k!='evidence'},'Same fact ID has conflicting meaning; reconcile explicitly')
                refs={digest(r):r for r in facts[fid]['evidence']+fact['evidence']}
                facts[fid]['evidence']=[refs[k] for k in sorted(refs)]
            else:facts[fid]=deepcopy(fact)
        for item in result['message_dispositions']:
            mid=item['message_id']
            if mid not in dispositions:dispositions[mid]=deepcopy(item);continue
            old=dispositions[mid]
            if old['reason']==item['reason']=='extracted':old['fact_ids']=sorted(set(old['fact_ids']+item['fact_ids']))
            elif old==item:pass
            elif old['reason']=='insufficient_context':dispositions[mid]=deepcopy(item)
            elif item['reason']=='insufficient_context':pass
            else:raise ValueError('Conflicting message dispositions across chunks; reconcile, do not silently discard')
    output=deepcopy(draft);output['facts']=[facts[k] for k in sorted(facts)];output['message_dispositions']=[dispositions[k] for k in sorted(dispositions)]
    # Narrative and persona MUST be generated after reconciliation, not inherited.
    output['themes']=[];output['card']=None
    verify(history,output)
    return output
