"""Distribution and cross-person isolation tests; no real user records."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from package_skill import package
from twinlight_core.common import ROOT, ContractError, load, save
from twinlight_core.history import normalize
from twinlight_core.evidence import anchor
from twinlight_core.compiler import compile_profile


def fictional_case(folder, owner, statement):
    """An independent source and minimal analysis, with no demo-derived content."""
    raw = folder / (owner + '-input.json')
    save(raw, {'messages': [{'id': owner + '-message', 'conversation_id': owner,
                            'role': 'user', 'text': statement, 'timestamp': None}]})
    history = normalize(raw, 'generic', scope='provided_subset')
    fact_id = owner + '-fact'
    linked = {'text': statement, 'fact_ids': [fact_id]}
    analysis = {
        'schema_version': '1.0', 'owner': {'id': owner, 'display_name': owner},
        'history_digest': history['history_digest'],
        'summary_meta': {'provider': 'unknown', 'display_name': None, 'model': None,
                         'generated_at': '2026-10-03T00:00:00Z', 'attribution_source': 'unknown'},
        'facts': [{'id': fact_id, 'statement': statement, 'kind': 'practice',
                   'speech_context': 'autobiographical', 'status': 'current',
                   'evidence': [anchor(history['messages'][0], statement)],
                   'sensitivity': 'personal', 'review': 'accepted',
                   'supersedes': [], 'conflict_key': None}],
        'message_dispositions': [{'message_id': history['messages'][0]['id'],
                                  'fact_ids': [fact_id], 'reason': 'extracted'}],
        'themes': [{'id': owner + '-theme', 'label': '本次记录', 'english': 'THIS RECORD',
                    'fact_ids': [fact_id], 'headline': copy.deepcopy(linked),
                    'paragraphs': [copy.deepcopy(linked)], 'reflection': copy.deepcopy(linked),
                    'topics': []}], 'card': None,
    }
    return history, analysis


class Isolation(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)

    def cli(self, root, *args):
        return subprocess.run([sys.executable, str(root / 'scripts/twinlight.py'), *map(str, args)],
                              cwd=self.folder, capture_output=True, text=True)

    def test_default_archive_excludes_personal_examples_and_answers(self):
        out = self.folder / 'core.zip'
        package(ROOT, out)
        with ZipFile(out) as archive:
            names = archive.namelist()
            self.assertFalse(any('/examples/demo/' in n or '/examples/smoke/' in n for n in names))
            self.assertNotIn('twinlight-with-you/prompts/06-smoke-test.txt', names)
            self.assertFalse(any('/private/' in n or '/verification/' in n or '/.git/' in n for n in names))
            manifest = json.loads(archive.read('twinlight-with-you/package-manifest.json'))
            self.assertEqual(manifest['mode'], 'personal_use')
            self.assertFalse(manifest['contains_fictional_history'])
            for name, expected in manifest['files_sha256'].items():
                self.assertEqual(hashlib.sha256(archive.read('twinlight-with-you/' + name)).hexdigest(), expected)

    def test_demo_is_opt_in_and_has_no_grading_answer(self):
        out = self.folder / 'demo.zip'
        package(ROOT, out, include_demo=True)
        with ZipFile(out) as archive:
            names = archive.namelist()
            self.assertIn('twinlight-with-you/examples/demo/history.json', names)
            self.assertIn('twinlight-with-you/prompts/06-smoke-test.txt', names)
            self.assertNotIn('twinlight-with-you/examples/smoke/expected.txt', names)
            self.assertTrue(json.loads(archive.read('twinlight-with-you/package-manifest.json'))['contains_fictional_history'])

    def test_two_distinct_people_do_not_inherit_demo_or_each_other(self):
        ha, aa = fictional_case(self.folder, 'fictional-baker', '我每周练习烤面包。')
        hb, ab = fictional_case(self.folder, 'fictional-runner', '我每天练习慢跑。')
        pa, la, _ = compile_profile(ha, aa)
        pb, _, _ = compile_profile(hb, ab)
        self.assertIn('烤面包', json.dumps(pa, ensure_ascii=False))
        public_b = json.dumps(pb, ensure_ascii=False)
        self.assertIn('慢跑', public_b)
        for forbidden in ('烤面包', 'fictional-baker', '小岚', '月亮照片', '整理照片', '观察手记'):
            self.assertNotIn(forbidden, public_b)
        with self.assertRaises(ContractError):
            compile_profile(hb, ab, previous=la)
        with self.assertRaises(ContractError):
            compile_profile(hb, aa)

    def test_core_package_builds_from_new_sources_without_demo(self):
        out = self.folder / 'core.zip'
        package(ROOT, out)
        with ZipFile(out) as archive:
            archive.extractall(self.folder / 'unpacked')
        root = self.folder / 'unpacked/twinlight-with-you'
        h, a = fictional_case(self.folder, 'fictional-baker', '我每周练习烤面包。')
        save(self.folder / 'history.json', h)
        save(self.folder / 'analysis.json', a)
        draft = self.folder / 'empty.json'
        result = self.cli(root, 'init-analysis', self.folder / 'history.json',
                          '--owner-id', 'fictional-baker', '--name', '虚构烘焙者', '--out', draft)
        self.assertEqual(result.returncode, 0, result.stderr)
        scaffold = load(draft)
        self.assertEqual(scaffold['facts'], [])
        self.assertEqual(scaffold['themes'], [])
        self.assertIsNone(scaffold['card'])
        result = self.cli(root, 'build', self.folder / 'history.json', self.folder / 'analysis.json',
                          '--out', self.folder / 'site')
        self.assertEqual(result.returncode, 0, result.stderr)
        html = (self.folder / 'site/index.html').read_text()
        self.assertIn('烤面包', html)
        self.assertNotIn('小岚', html)
        self.assertNotIn('整理照片', html)
        demo = self.cli(root, 'demo', '--out', self.folder / 'unexpected-demo')
        self.assertEqual(demo.returncode, 2)
        self.assertIn('no fictional demo', demo.stderr)
        self.assertFalse((self.folder / 'unexpected-demo').exists())


if __name__ == '__main__':
    unittest.main()
