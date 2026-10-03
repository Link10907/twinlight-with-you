"""Lite contract, gated workflow, and Python/JS parity. Fixtures are fictional."""
import base64
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from twinlight_core.common import ROOT, ContractError, load
from twinlight_core import lite, state as fsm
from twinlight_core.site import lite_layers, build_lite, PERSONAL_TOKENS
from PIL import Image, ImageDraw

FIX = ROOT / 'tests' / 'fixtures' / 'lite'
CASES = load(FIX / 'cases.json')
EXAMPLE = ROOT / 'examples' / 'lite' / 'example.json'
AT = '2026-10-03T00:00:00Z'


def text(name):
    return (FIX / name).read_text(encoding='utf-8')


class Contract(unittest.TestCase):
    def test_fixture_expectations(self):
        for case in CASES:
            with self.subTest(case['file']):
                r = lite.check_text(text(case['file']))
                self.assertEqual(r['ok'], case['expect_ok'], r['errors'])
                self.assertEqual(sorted(e['code'] for e in r['errors']), sorted(case['expect_codes']))
                self.assertEqual(len(r['warnings']), case['expect_warnings'], r['warnings'])
                self.assertEqual(r['data'] is not None, r['ok'])

    def test_errors_are_complete_and_readable(self):
        for case in CASES:
            for e in lite.check_text(text(case['file']))['errors']:
                self.assertEqual(set(e), {'path', 'code', 'message'})
                self.assertRegex(e['message'], r'[\u4e00-\u9fff]')

    def test_reports_all_errors_not_first(self):
        data = json.loads(EXAMPLE.read_text(encoding='utf-8'))
        data['card']['title'] = '一二三四五六七八九'
        data['themes'][0]['english'] = '中文'
        data['themes'][1]['topics'][0]['basis'] = 'always'
        del data['summarizer']
        codes = sorted(e['code'] for e in lite.validate(lite.normalize(data)))
        self.assertEqual(codes, ['bad_format', 'bad_value', 'missing', 'too_long'])

    def test_repair_prompt_lists_every_path(self):
        errors = lite.check_text(text('too_long.json'))['errors']
        prompt = lite.repair_prompt(errors)
        for e in errors:
            self.assertIn(e['path'], prompt)
        self.assertIn('```json', prompt)

    def test_example_is_valid(self):
        self.assertTrue(lite.check_text(EXAMPLE.read_text(encoding='utf-8'))['ok'])

    def test_smart_quote_hint(self):
        msg = lite.check_text(text('smart_quotes.txt'))['errors'][0]['message']
        self.assertIn('引号', msg)

    def test_code_points_not_utf16(self):
        self.assertTrue(lite.check_text(text('emoji_length.json'))['ok'])

    def test_profile_contract(self):
        data = lite.check_text(EXAMPLE.read_text(encoding='utf-8'))['data']
        draft = lite.to_profile(data, generated_at=AT)
        self.assertTrue(draft['release']['draft'])
        self.assertFalse(draft['release']['share_allowed'])
        p = lite.to_profile(data, generated_at=AT, confirmed=True, art_status='generated')
        self.assertEqual(p['mode'], 'lite')
        self.assertEqual(len(p['chapters']), len(data['themes']))
        self.assertEqual(len(p['layout']['topics']), sum(len(t['topics']) for t in data['themes']))
        self.assertEqual(p['summary_meta']['attribution_source'], 'ai_self_reported')
        self.assertEqual(p['coverage']['scope'], 'ai_impression')
        self.assertEqual(lite.to_profile(data, generated_at=AT, confirmed=True, art_status='generated'), p)

    def test_unknown_summarizer_not_guessed(self):
        self.assertEqual(lite.provider_of('不确定'), ('unknown', None))
        self.assertEqual(lite.provider_of('Claude Opus')[0], 'anthropic')


class Art(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.p = Path(self.tmp.name)

    def img(self, name, size, mode='RGB', transparent=False):
        im = Image.new(mode, size, (0, 0, 0, 0) if transparent else 'navy')
        if transparent:
            ImageDraw.Draw(im).ellipse([size[0] // 4, size[1] // 4, size[0] * 3 // 4, size[1]], fill=(240, 200, 150, 255))
        im.save(self.p / name); return self.p / name

    def test_modes(self):
        self.assertEqual(lite_layers()['art_status'], 'placeholder')
        r = lite_layers(prototype=self.img('p.jpg', (900, 1200)))
        self.assertEqual((r['art_status'], r['art_mode']), ('static', 'static'))
        self.assertEqual(set(r['depths'].values()), {0})
        original = self.img('c.png', (600, 800), 'RGBA', True)
        r = lite_layers(character=original, background=self.img('bg.jpg', (600, 800)))
        self.assertEqual((r['art_status'], r['art_mode'], r['layers']['text']), ('generated', 'layered', 'auto'))
        self.assertTrue(r['native_full_canvas'])
        self.assertTrue(r['layers']['background'].startswith('data:image/png'))
        sub = Image.open(io.BytesIO(base64.b64decode(r['layers']['subject'].split(',', 1)[1])))
        self.assertEqual(sub.size, (600, 800))
        self.assertEqual(sub.tobytes(), Image.open(original).convert('RGBA').tobytes(), 'native coordinates and pixels stay untouched')

    def test_rejects(self):
        for kwargs in [{'portrait': self.img('s.png', (300, 300))},
                       {'character': self.img('o.png', (800, 1000))},
                       {'portrait': self.img('a.png', (800, 1000)), 'character': self.img('b.png', (800, 1000), 'RGBA', True)},
                       {'background': self.img('bg.png', (800, 1000))}]:
            with self.subTest(list(kwargs)), self.assertRaises(ContractError):
                lite_layers(**kwargs)
        (self.p / 'fake.png').write_text('not an image')
        with self.assertRaises(Exception):
            lite_layers(portrait=self.p / 'fake.png')

    def test_build_fills_every_token(self):
        data = lite.check_text(EXAMPLE.read_text(encoding='utf-8'))['data']
        rep = build_lite(data, self.p / 'site', generated_at=AT, confirmed=True)
        html = (self.p / 'site' / 'index.html').read_text(encoding='utf-8')
        self.assertFalse([t for t in PERSONAL_TOKENS if f'__{t}__' in html])
        self.assertTrue(rep['share_allowed'])
        self.assertEqual(load(self.p / 'site' / 'profile.json')['name'], data['name'])
        self.assertIn(json.dumps(data['card']['title'], ensure_ascii=False).strip('"'), html)


@mock.patch.object(fsm, '_visual', lambda state, p: fsm._pass(state, 'visual', {'verified': False, 'reason': 'test'}, status='skipped'))
class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.ws = Path(self.tmp.name) / 'run'
        self.first = fsm.start(self.ws)

    def write(self, src):
        shutil.copyfile(src, self.ws / 'twinlight.json')

    def test_full_run(self):
        self.assertEqual(self.first['stage'], 'profile')
        self.write(FIX / 'fenced.txt')
        r = fsm.check_stage(self.ws)
        self.assertEqual((r['status'], r['next']['stage']), ('passed', 'review'))
        self.assertTrue(lite.check_text((self.ws / 'twinlight.json').read_text(encoding='utf-8'))['ok'])
        self.assertIn('preview', r['next'])
        self.assertEqual(fsm.check_stage(self.ws)['stage'], 'review')
        self.assertEqual(fsm.confirm(self.ws, '可以')['next']['stage'], 'art')
        nxt = fsm.next_action(self.ws)
        self.assertIn('真实 alpha', nxt['subject_prompt'])
        self.assertIn('card_spec', nxt)
        self.assertIn('prototype_prompt', nxt)
        self.assertIn('不要画人物', nxt['background_prompt'])
        self.assertEqual(fsm.choose_placeholder(self.ws)['next']['stage'], 'build')
        for stage in ('build', 'visual', 'report'):
            self.assertEqual(fsm.check_stage(self.ws)['stage'], stage)
        done = fsm.next_action(self.ws)
        self.assertEqual((done['stage'], done['art_status'], done['visual_verified']), ('done', 'placeholder', False))
        self.assertTrue((self.ws / 'report.html').is_file())
        self.assertIn('未验证', (self.ws / 'report.html').read_text(encoding='utf-8'))

    def test_edit_after_pass_reopens_everything_after(self):
        self.write(EXAMPLE); fsm.check_stage(self.ws); fsm.confirm(self.ws, '好的')
        data = json.loads((self.ws / 'twinlight.json').read_text(encoding='utf-8'))
        data['card']['tagline'] = '改过的一句话。'
        (self.ws / 'twinlight.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        st = fsm.status(self.ws)
        self.assertEqual(st['current'], 'profile')
        self.assertTrue(st['notes'])
        self.assertEqual({s['status'] for s in st['stages']}, {'pending'})

    def test_art_change_reopens_build(self):
        self.write(EXAMPLE); fsm.check_stage(self.ws); fsm.confirm(self.ws, '好的'); fsm.choose_placeholder(self.ws)
        fsm.check_stage(self.ws)
        self.assertEqual(fsm.status(self.ws)['current'], 'visual')
        Image.new('RGB', (900, 1200), 'teal').save(self.ws / 'card' / 'portrait.png')
        self.assertEqual(fsm.status(self.ws)['current'], 'visual')
        chosen = fsm.choose_art(self.ws, 'static')
        self.assertEqual(chosen['next']['stage'], 'build')
        self.assertEqual(load(self.ws / 'card' / 'choice.json')['mode'], 'static')
        self.assertEqual(load(self.ws / 'state.json')['stages']['art']['detail']['art_mode'], 'static')

    def test_opaque_character_fails_and_native_layers_pass(self):
        self.write(EXAMPLE); fsm.check_stage(self.ws); fsm.confirm(self.ws, '好的')
        (self.ws / 'card').mkdir(exist_ok=True)
        noise = Image.effect_noise((600, 800), 80).convert('RGB')
        noise.save(self.ws / 'card' / 'subject.png')
        r = fsm.check_stage(self.ws)
        self.assertEqual((r['stage'], r['status']), ('art', 'failed'))
        msg = fsm.next_action(self.ws)['errors'][0]['message']
        self.assertIn('原生真实 alpha', msg)
        self.assertNotIn('#00FF00', msg)
        subject = Image.new('RGBA', (600, 800))
        ImageDraw.Draw(subject).ellipse([150, 150, 450, 750], fill=(60, 70, 120, 255))
        subject.save(self.ws / 'card' / 'subject.png')
        Image.new('RGB', (600, 800), 'navy').save(self.ws / 'card' / 'background.png')
        r = fsm.check_stage(self.ws)
        self.assertEqual((r['stage'], r['status']), ('art', 'passed'))
        self.assertEqual(fsm.next_action(self.ws)['stage'], 'build')

    def test_three_failures_block(self):
        self.write(FIX / 'too_long.json')
        for i in range(1, 4):
            r = fsm.check_stage(self.ws)
            self.assertEqual(r['attempts'], i)
            self.assertIn('repair_prompt', r)
        self.assertEqual(r['status'], 'blocked')
        nxt = fsm.next_action(self.ws)
        self.assertIn('unblock', ' '.join(nxt['do']))
        self.write(EXAMPLE)
        self.assertEqual(fsm.check_stage(self.ws)['status'], 'blocked')
        with self.assertRaises(ContractError):
            fsm.unblock(self.ws, ' ')
        fsm.unblock(self.ws, '用户说把称号缩短')
        self.assertEqual(fsm.check_stage(self.ws)['status'], 'passed')

    def test_confirm_guards(self):
        with self.assertRaises(ContractError):
            fsm.confirm(self.ws, '可以')
        self.write(EXAMPLE); fsm.check_stage(self.ws)
        with self.assertRaises(ContractError):
            fsm.confirm(self.ws, '   ')
        with self.assertRaises(ContractError):
            fsm.choose_placeholder(self.ws)

    def test_missing_file_and_restart(self):
        self.assertEqual(fsm.check_stage(self.ws)['errors'][0]['code'], 'missing_file')
        with self.assertRaises(ContractError):
            fsm.start(self.ws)

    def test_cli_exit_codes(self):
        cli = [sys.executable, str(ROOT / 'scripts' / 'twinlight.py')]
        self.assertEqual(subprocess.run(cli + ['lite-check', str(FIX / 'too_long.json')], capture_output=True).returncode, 1)
        self.assertEqual(subprocess.run(cli + ['lite-check', str(EXAMPLE)], capture_output=True).returncode, 0)
        self.write(FIX / 'too_long.json')
        self.assertEqual(subprocess.run(cli + ['check', '--workspace', str(self.ws)], capture_output=True).returncode, 1)


NODE = shutil.which('node')
JS = r'''
const L=require(process.argv[1]);const fs=require('fs');
const inp=JSON.parse(fs.readFileSync(0,'utf8'));
const out=inp.cases.map(t=>{const r=L.checkText(t,inp.schema);
 return {ok:r.ok,errors:r.errors,warnings:r.warnings,data:r.data,stats:r.stats,repair:r.ok?null:L.repairPrompt(r.errors),
  profile:r.ok?L.toProfile(r.data,{generatedAt:inp.at,artStatus:'generated',confirmed:true,aiHistory:inp.history}):null};});
process.stdout.write(JSON.stringify({out,hash:L.sha256(inp.hashme),providers:inp.summ.map(L.providerOf)}));
'''


@unittest.skipUnless(NODE, 'node not installed')
class Parity(unittest.TestCase):
    def test_python_and_browser_agree(self):
        texts = [text(c['file']) for c in CASES] + [EXAMPLE.read_text(encoding='utf-8')]
        history = load(ROOT / 'assets' / 'ai-history.json')['events']
        hashme = '小满 ✨ 𝒳 Twinlight'
        summ = ['Claude', 'GPT-5', '豆包', 'Kimi', '不确定', 'AI 助手', 'Unknown', '我自己']
        payload = json.dumps({'cases': texts, 'schema': lite.schema(), 'at': AT, 'history': history, 'hashme': hashme, 'summ': summ}, ensure_ascii=False)
        r = subprocess.run([NODE, '-e', JS, str(ROOT / 'assets' / 'lite' / 'lite.js')], input=payload, capture_output=True, text=True, encoding='utf-8', check=True)
        js = json.loads(r.stdout)
        self.assertEqual(js['hash'], __import__('hashlib').sha256(hashme.encode()).hexdigest())
        self.assertEqual([tuple(x) for x in js['providers']], [lite.provider_of(s) for s in summ])
        for t, got in zip(texts, js['out']):
            py = lite.check_text(t)
            with self.subTest(t[:40]):
                self.assertEqual(got['errors'], py['errors'])
                self.assertEqual(got['warnings'], py['warnings'])
                self.assertEqual(got['data'], py['data'])
                self.assertEqual(got['stats'], py['stats'])
                if py['ok']:
                    self.assertEqual(got['profile'], lite.to_profile(py['data'], generated_at=AT, art_status='generated', confirmed=True, ai_history=history))
                else:
                    self.assertEqual(got['repair'], lite.repair_prompt(py['errors']))

    def test_viewer_tokens_match_python(self):
        viewer = (ROOT / 'assets' / 'viewer' / 'viewer.js').read_text(encoding='utf-8')
        tokens = re.search(r'TOKENS=/__\(([A-Z0-9_|]+)\)__/g', viewer).group(1).split('|')
        self.assertEqual(sorted(tokens), sorted(PERSONAL_TOKENS))


if __name__ == '__main__':
    unittest.main()
