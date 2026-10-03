"""Strict-mode helpers: collect-all verify, quote anchoring, per-chunk validation. Fictional demo data."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from twinlight_core.common import ROOT, ContractError, load, save, schema_errors
from twinlight_core.evidence import verify, anchor_document
from twinlight_core.extraction import validate_chunk, merge_chunks
from twinlight_core.history import make_chunks, normalize


class Strict(unittest.TestCase):
    def setUp(self):
        self.h = load(ROOT / 'examples/demo/history.json')
        self.a = load(ROOT / 'examples/demo/analysis.json')
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.p = Path(self.tmp.name)

    def both(self, a):
        with self.assertRaises(ContractError):
            verify(self.h, a)
        r = verify(self.h, a, collect=True)
        self.assertFalse(r['ok'])
        return r['errors']

    def test_collect_mode_clean_demo(self):
        r = verify(self.h, self.a, collect=True)
        self.assertTrue(r['ok']); self.assertEqual(r['errors'], [])
        self.assertNotIn('errors', verify(self.h, self.a))

    def test_collect_reports_every_problem_with_paths(self):
        a = copy.deepcopy(self.a)
        a['facts'][0]['evidence'][0]['text_sha256'] = '0' * 64
        a['facts'][1]['evidence'][0]['quote'] += '多'
        a['summary_meta']['display_name'] = 'Somebody'
        a['summary_meta']['provider'] = 'unknown'
        paths = [e['path'] for e in self.both(a)]
        self.assertIn('facts[0].evidence[0].text_sha256', paths)
        self.assertTrue(any(p.startswith('facts[1].evidence[0]') for p in paths))
        self.assertIn('summary_meta.display_name', paths)

    def test_cycle_is_reported_not_recursed(self):
        a = copy.deepcopy(self.a)
        x, y = a['facts'][0], a['facts'][1]
        x['supersedes'] = [y['id']]; y['supersedes'] = [x['id']]
        msgs = [e['message'] for e in self.both(a)]
        self.assertIn('Cycle in supersedes graph', msgs)

    def test_schema_problems_stop_before_semantics(self):
        a = copy.deepcopy(self.a)
        del a['facts'][0]['kind']
        a['facts'][1]['review'] = 'maybe'
        r = verify(self.h, a, collect=True)
        self.assertEqual(r['stage'], 'schema')
        self.assertEqual({e['path'] for e in r['errors']}, {'facts[0]', 'facts[1].review'})
        self.assertTrue(all(a['facts'][1]['evidence'][0]['quote'] not in e['message'] for e in r['errors']))

    def test_anchor_restores_offsets_from_quotes(self):
        a = copy.deepcopy(self.a)
        for f in a['facts']:
            for ref in f['evidence']:
                ref.pop('start'); ref.pop('end'); ref.pop('text_sha256')
        r = anchor_document(self.h, a)
        self.assertTrue(r['ok'], r['errors'])
        self.assertEqual(r['document'], self.a)
        self.assertEqual(r['changed'], r['evidence_refs'])

    def mini(self):
        save(self.p / 'in.json', {'messages': [
            {'id': 'u1', 'conversation_id': 'c', 'role': 'user', 'text': '我每天 散步。晚上也散步。', 'timestamp': None, 'platform': 'fixture'},
            {'id': 'a1', 'conversation_id': 'c', 'role': 'assistant', 'text': '你是散步大师。', 'timestamp': None, 'platform': 'fixture'}]})
        h = normalize(self.p / 'in.json', 'generic', scope='provided_subset')
        return h, {m['native_id']: m['id'] for m in h['messages']}

    def test_anchor_reports_all_failures(self):
        h, ids = self.mini()
        a = {'facts': [{'evidence': [{'message_id': ids['u1'], 'quote': '我每天散步'}]},
                       {'evidence': [{'message_id': ids['a1'], 'quote': '散步大师'}]},
                       {'evidence': [{'message_id': 'nope', 'quote': 'x'}, {'message_id': ids['u1']}]}]}
        r = anchor_document(h, a)
        self.assertFalse(r['ok']); self.assertIsNone(r['document'])
        self.assertEqual([e['path'] for e in r['errors']],
                         ['facts[0].evidence[0].quote', 'facts[1].evidence[0].message_id', 'facts[2].evidence[0].message_id', 'facts[2].evidence[1]'])
        self.assertIn('removing whitespace', r['errors'][0]['message'])

    def test_anchor_ambiguous_quote_needs_occurrence(self):
        h, ids = self.mini()
        a = {'facts': [{'evidence': [{'message_id': ids['u1'], 'quote': '散步'}]}]}
        self.assertIn('occurs 2 times', anchor_document(h, a)['errors'][0]['message'])
        a['facts'][0]['evidence'][0]['occurrence'] = 1
        r = anchor_document(h, a)
        self.assertTrue(r['ok'])
        ref = r['document']['facts'][0]['evidence'][0]
        self.assertEqual((ref['start'], ref['end'], 'occurrence' in ref), (10, 12, False))
        a['facts'][0]['evidence'][0]['occurrence'] = 5
        self.assertIn('occurrence', anchor_document(h, a)['errors'][0]['path'])

    def chunk(self):
        chunks = self.p / 'chunks'; m = make_chunks(self.h, chunks, 1000); e = m['chunks'][0]
        return chunks / 'manifest.json', {'chunk_path': e['path'], 'chunk_sha256': e['sha256'], 'history_digest': self.h['history_digest'],
                                          'facts': copy.deepcopy(self.a['facts']), 'message_dispositions': copy.deepcopy(self.a['message_dispositions'])}

    def test_validate_chunk_ok_and_merge_agree(self):
        manifest, result = self.chunk()
        r = validate_chunk(self.h, manifest, result)
        self.assertTrue(r['ok'], r['errors'])
        res = self.p / 'results'; res.mkdir(); save(res / 'one.json', result)
        self.assertEqual(len(merge_chunks(self.h, self.a, manifest, res)['facts']), len(self.a['facts']))

    def test_validate_chunk_collects(self):
        manifest, result = self.chunk()
        result['facts'][0]['evidence'][0]['start'] += 1
        result['message_dispositions'] = result['message_dispositions'][1:]
        r = validate_chunk(self.h, manifest, result)
        self.assertFalse(r['ok'])
        paths = {e['path'] for e in r['errors']}
        self.assertIn('message_dispositions', paths)
        self.assertTrue(any(p.startswith('facts[0].evidence') for p in paths))
        res = self.p / 'results'; res.mkdir(); save(res / 'one.json', result)
        with self.assertRaises(ContractError):
            merge_chunks(self.h, self.a, manifest, res)

    def test_chunk_schema_reuses_analysis_definitions(self):
        manifest, result = self.chunk()
        result['facts'][0]['kind'] = 'skill'
        result['extra'] = 1
        paths = {e['path'] for e in schema_errors(result, 'chunk-result.schema.json')}
        self.assertEqual(paths, {'$', 'facts[0].kind'})
        self.assertFalse(validate_chunk(self.h, manifest, result)['ok'])


if __name__ == '__main__':
    unittest.main()
