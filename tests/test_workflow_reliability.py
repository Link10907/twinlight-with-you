"""Synthetic workflow regressions: downgrade recovery and current browser proof."""
from __future__ import annotations
import copy
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from PIL import Image, ImageDraw
from twinlight_core import state
from twinlight_core.cardgen import card_spec
from twinlight_core.common import ContractError, load, save

DATA = {
    'twinlight': 'lite-1', 'name': '合成测试', 'summarizer': '未知',
    'themes': [{'label': '合成主题', 'english': 'TEST', 'headline': '仅用于校验的合成内容。',
                'story': ['这是程序测试，不描述任何真实人物。'], 'reflection': '仅用于测试。', 'topics': []}],
    'card': {'title': '测试卡片', 'english_title': 'TEST CARD', 'keywords': ['测试', '合成', '复现'],
             'tagline': '仅用于程序复现。', 'reflection': '不描述真实人物。',
             'art_prompt': '一张仅用于技术测试的原创抽象几何卡面，蓝色圆形在完整竖版画布中央。'},
}


class ArtRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name) / 'run'
        state.start(self.ws)
        save(self.ws / 'twinlight.json', DATA)
        state.check_stage(self.ws)
        state.confirm(self.ws, '合成测试中的模拟同意')

    def image(self, role, color='navy'):
        path = self.ws / 'card' / (role + '.png')
        Image.new('RGB', (600, 800), color).save(path)
        return path

    def test_static_recovers_blocked_art_and_keeps_failed_subject(self):
        subject = self.image('subject')
        original = subject.read_bytes()
        for _ in range(3): result = state.check_stage(self.ws)
        self.assertEqual(result['status'], 'blocked')
        prototype = self.image('prototype')
        result = state.choose_art(self.ws, 'static')
        self.assertEqual((result['status'], result['next']['stage']), ('passed', 'build'))
        self.assertEqual(load(self.ws / 'state.json')['stages']['art']['detail']['art_mode'], 'static')
        self.assertEqual(subject.read_bytes(), original)
        self.assertEqual(state.art_inputs(state.paths(self.ws)), {'prototype': prototype.resolve()})
        self.image('subject', 'teal')
        self.assertEqual(state.status(self.ws)['current'], 'build')
        self.image('prototype', 'teal')
        self.assertEqual(state.status(self.ws)['current'], 'art')

    def test_placeholder_recovers_with_invalid_manifest_and_keeps_assets(self):
        manifest = self.ws / 'card/layers.json'
        manifest.write_text('invalid-json', encoding='utf-8')
        subject = self.image('subject')
        for _ in range(3): result = state.check_stage(self.ws)
        self.assertEqual(result['status'], 'blocked')
        result = state.choose_placeholder(self.ws)
        self.assertEqual((result['status'], result['next']['stage']), ('passed', 'build'))
        detail = load(self.ws / 'state.json')['stages']['art']['detail']
        self.assertEqual(detail['art_mode'], 'placeholder')
        self.assertEqual(detail['fingerprint']['files'], {})
        self.assertEqual(manifest.read_text(), 'invalid-json')
        self.assertTrue(subject.is_file())

    def test_static_requires_valid_prototype_before_replacing_choice(self):
        choice_path = self.ws / 'card/choice.json'
        choice = {'mode': 'placeholder', 'placeholder': True}
        save(choice_path, choice)
        with self.assertRaises(ContractError): state.choose_art(self.ws, 'static')
        self.assertEqual(load(choice_path), choice)
        self.image('prototype').write_bytes(b'broken-image')
        with self.assertRaises(OSError): state.choose_art(self.ws, 'static')
        self.assertEqual(load(choice_path), choice)

    def test_static_accepts_portrait_alias(self):
        portrait = self.image('portrait')
        self.image('subject')
        result = state.choose_art(self.ws, 'static')
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(state.art_inputs(state.paths(self.ws)), {'portrait': portrait.resolve()})

    def test_reselect_layered_clears_choice_without_deleting_images(self):
        prototype = self.image('prototype')
        save(self.ws / 'card/choice.json', {'mode': 'static'})
        result = state.choose_art(self.ws, 'layered')
        self.assertEqual(result['status'], 'passed')
        self.assertFalse((self.ws / 'card/choice.json').exists())
        self.assertTrue(prototype.is_file())

    def test_switch_from_build_to_layered_reopens_art_without_deleting_images(self):
        prototype = self.image('prototype')
        state.choose_art(self.ws, 'static')
        self.assertEqual(state.status(self.ws)['current'], 'build')
        card = self.ws / 'card'
        self.image('background')
        for role in ('subject', 'effects', 'text'):
            im = Image.new('RGBA', (600, 800))
            ImageDraw.Draw(im).rectangle((100, 100, 300, 600), fill=(25, 60, 120, 255))
            im.save(card / (role + '.png'))
        Image.new('RGBA', (600, 800)).save(card / 'spirit.png')
        lineart = Image.new('RGB', (600, 800), 'white')
        ImageDraw.Draw(lineart).rectangle((100, 100, 300, 600), outline='black', width=3)
        lineart.save(card / 'lineart.png')
        save(card / 'layers.json', card_spec(DATA, generated_at='2000-01-01T00:00:00Z')['manifest_template'])
        original = {path.name: path.read_bytes() for path in card.glob('*.png')}
        result = state.choose_art(self.ws, 'layered')
        self.assertEqual((result['status'], result['next']['stage']), ('passed', 'build'))
        self.assertEqual(load(self.ws / 'state.json')['stages']['art']['detail']['art_mode'], 'layered')
        self.assertFalse((card / 'choice.json').exists())
        self.assertTrue(prototype.is_file())
        self.assertEqual({path.name: path.read_bytes() for path in card.glob('*.png')}, original)

    def test_switch_after_build_reopens_build_and_visual(self):
        self.image('prototype')
        state.choose_art(self.ws, 'static')
        state.check_stage(self.ws)
        self.assertEqual(state.status(self.ws)['current'], 'visual')
        result = state.choose_art(self.ws, 'placeholder')
        self.assertEqual((result['status'], result['next']['stage']), ('passed', 'build'))
        stages = load(self.ws / 'state.json')['stages']
        self.assertEqual(stages['build']['status'], 'pending')
        self.assertEqual(stages['visual']['status'], 'pending')
        self.assertEqual(stages['review']['status'], 'passed')

    def test_downgrade_cannot_skip_text_review(self):
        data = copy.deepcopy(DATA); data['card']['tagline'] = '修改后的文案。'
        save(self.ws / 'twinlight.json', data)
        with self.assertRaises(ContractError): state.choose_art(self.ws, 'placeholder')
        self.assertEqual(state.status(self.ws)['current'], 'profile')
        state.check_stage(self.ws)
        with self.assertRaises(ContractError): state.choose_art(self.ws, 'placeholder')
        self.assertEqual(state.status(self.ws)['current'], 'review')

    def test_corrupted_download_records_failed_attempt(self):
        (self.ws / 'card/prototype.png').write_bytes(b'broken-image')
        result = state.check_stage(self.ws)
        self.assertEqual((result['stage'], result['status'], result['attempts']), ('art', 'failed', 1))
        self.assertIn('cannot identify image', result['errors'][0]['message'])

    def test_unblock_records_technical_reason_and_keeps_review_gate(self):
        (self.ws / 'card/prototype.png').write_bytes(b'broken-image')
        for _ in range(3): state.check_stage(self.ws)
        self.image('prototype')
        result = state.unblock(self.ws, '重新下载了损坏的原型文件')
        self.assertEqual(result['stage'], 'art')
        saved = load(self.ws / 'state.json')
        self.assertEqual(saved['stages']['review']['status'], 'passed')
        self.assertIn('解除技术阻塞', saved['events'][-1]['event'])
        self.assertEqual(state.check_stage(self.ws)['status'], 'passed')


class CurrentVisualReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p = state.paths(Path(self.tmp.name))
        self.p['visual'].mkdir(); self.p['site'].mkdir()
        self.p['html'].write_text('<html>current-page</html>', encoding='utf-8')
        self.s = {'stages': {k: state._blank(k) for k in state.STAGES}, 'events': []}
        self.good = {'ok': True, 'webgl': True, 'checks': [{'name': 'current check', 'passed': True}]}

    def run_visual(self, *, code=0, report=None, stderr=''):
        def run(*args, **kwargs):
            if isinstance(report, str):
                (self.p['visual'] / 'report.json').write_text(report, encoding='utf-8')
            elif report is not None:
                save(self.p['visual'] / 'report.json', report)
            return subprocess.CompletedProcess(args=args, returncode=code, stdout='', stderr=stderr)
        with mock.patch.dict(sys.modules, {'playwright': types.ModuleType('playwright')}), mock.patch.object(state.subprocess, 'run', side_effect=run):
            state._visual(self.s, self.p)
        return self.s['stages']['visual']

    def test_stale_success_cannot_pass_when_current_run_writes_no_report(self):
        save(self.p['visual'] / 'report.json', self.good)
        result = self.run_visual(code=2, stderr='current invocation failed')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['errors'][0]['code'], 'missing_report')
        self.assertFalse((self.p['visual'] / 'report.json').exists())

    def test_nonzero_process_cannot_pass_even_with_fresh_ok_report(self):
        self.assertEqual(self.run_visual(code=2, report=self.good)['status'], 'failed')

    def test_success_requires_current_report_and_records_html_binding(self):
        result = self.run_visual(report=self.good)
        self.assertEqual(result['status'], 'passed')
        self.assertTrue(result['detail']['verified'])
        self.assertEqual(result['detail']['html_sha256'], state.sha(self.p['html']))

    def test_success_process_without_report_is_failure(self):
        self.assertEqual(self.run_visual()['status'], 'failed')

    def test_invalid_report_is_failure(self):
        result = self.run_visual(report='not-json')
        self.assertEqual((result['status'], result['errors'][0]['code']), ('failed', 'invalid_report'))

    def test_missing_browser_is_skipped_and_runtime_exception_is_failed(self):
        report = {'ok': False, 'checks': [], 'failure': "BrowserType.launch: Executable doesn't exist at /missing/chromium"}
        result = self.run_visual(code=1, report=report)
        self.assertEqual(result['status'], 'skipped')
        self.assertFalse(result['detail']['verified'])
        self.s = {'stages': {k: state._blank(k) for k in state.STAGES}, 'events': []}
        report['failure'] = 'page script raised an unexpected exception'
        self.assertEqual(self.run_visual(code=1, report=report)['status'], 'failed')

    def test_empty_or_failed_checks_cannot_claim_verification(self):
        report = {'ok': True, 'checks': []}
        self.assertEqual(self.run_visual(report=report)['status'], 'failed')
        self.s = {'stages': {k: state._blank(k) for k in state.STAGES}, 'events': []}
        report['checks'] = [{'name': 'failed', 'passed': False}]
        self.assertEqual(self.run_visual(report=report)['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
