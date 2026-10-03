"""Merge host-produced chunk results without an implicit semantic overwrite."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from .common import Collector, check, load, digest, local_asset, schema_check, schema_errors
from .evidence import verify, check_ref


def check_result(history: dict, manifest_path: Path, manifest: dict, result: dict, need: Collector, seen: set) -> bool:
    """Contract for ONE chunk result. Shared by validate-chunk (collect) and merge-extractions (raise)."""
    if need.collect:
        shape = schema_errors(result, "chunk-result.schema.json")
        if shape:
            need.errors.extend(shape); return False
    else:
        schema_check(result, "chunk-result.schema.json")
    expected = {entry['path']: entry for entry in manifest['chunks']}
    name = result['chunk_path']
    if not need(name in expected and name not in seen, 'Unknown/duplicate extraction chunk', 'chunk_path'):
        return False
    seen.add(name)
    chunk = load(local_asset(manifest_path.parent, name))
    need(result['chunk_sha256'] == expected[name]['sha256'] == digest(chunk), 'Chunk hash mismatch', 'chunk_sha256')
    need(result['history_digest'] == history['history_digest'], 'Stale chunk extraction', 'history_digest')
    segment_users = {s['message_id'] for s in chunk['segments'] if s['role'] == 'user'}
    given = [d['message_id'] for d in result['message_dispositions']]
    missing, extra = segment_users - set(given), set(given) - segment_users
    need(not missing and not extra and len(given) == len(set(given)),
         f'Each user segment needs exactly one disposition (missing {len(missing)}, outside this chunk {len(extra)}, repeated {len(given)-len(set(given))})',
         'message_dispositions')
    messages = {m['id']: m for m in history['messages']}
    ids = set()
    for i, fact in enumerate(result['facts']):
        fp = f'facts[{i}]'
        need(fact['id'] not in ids, 'Duplicate fact ID in this chunk result', fp + '.id'); ids.add(fact['id'])
        need(all(any(seg['message_id'] == ref['message_id'] and seg['start'] <= ref['start'] < ref['end'] <= seg['end'] for seg in chunk['segments'])
                 for ref in fact['evidence']), 'Map citation falls outside its assigned source segments', fp + '.evidence')
        need(all(r['message_id'] in segment_users for r in fact['evidence']), 'Map-stage facts may cite only user messages in this chunk', fp + '.evidence')
        if need.collect:
            for j, ref in enumerate(fact['evidence']):
                check_ref(need, messages, ref, f'{fp}.evidence[{j}]', fact['id'])
    for k, item in enumerate(result['message_dispositions']):
        dp = f'message_dispositions[{k}]'
        need((item['reason'] == 'extracted') == bool(item['fact_ids']), 'extracted dispositions need facts; exclusions must have none', dp + '.reason')
        for fid in item['fact_ids']:
            need(fid in ids, f'Disposition references a fact not in this result: {fid}', dp + '.fact_ids')
    return True


def validate_chunk(history: dict, manifest_path: Path, result: dict) -> dict:
    need = Collector(collect=True)
    manifest = load(manifest_path)
    need(manifest['history_digest'] == history['history_digest'], 'Chunk batch belongs to another history', 'history_digest')
    check_result(history, manifest_path, manifest, result, need, set())
    count = lambda key: len(result.get(key, [])) if isinstance(result, dict) and isinstance(result.get(key), list) else None
    return {'ok': not need.errors, 'chunk_path': result.get('chunk_path') if isinstance(result, dict) else None,
            'facts': count('facts'), 'dispositions': count('message_dispositions'), 'errors': need.errors}


def merge_chunks(history: dict, draft: dict, manifest_path: Path, results_dir: Path) -> dict:
    manifest=load(manifest_path)
    check(manifest['history_digest']==history['history_digest']==draft['history_digest'],'Chunk batch belongs to another history')
    results=[load(p) for p in sorted(results_dir.glob('*.json'))]
    check(len(results)==len(manifest['chunks']),'Each chunk must have exactly one result JSON')
    need=Collector();seen=set();facts={};dispositions={}
    for result in results:
        check_result(history,manifest_path,manifest,result,need,seen)
        for fact in result['facts']:
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
