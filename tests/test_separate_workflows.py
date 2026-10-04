"""HTML builds without art; native cards build without galaxy data and import explicitly."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from twinlight_core import lite
from twinlight_core.cardgen import card_spec, read_card_data
from twinlight_core.common import ContractError, load, save
from twinlight_core.site import build_lite
from twinlight_core.site import build as build_strict
from twinlight_core.compiler import art_brief, compile_profile
from prepare_card_layers import prepare
from package_card import package
from preview_card import preview
from test_card_art import native_fixture

AT = '2026-10-03T00:00:00Z'
BRIEF = '原创纸本版画风格，一枚有明确造型的折纸罗盘，低饱和蓝绿与细金线，留出上下文字安全区。'


class SeparateWorkflows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = load(ROOT / 'tests/fixtures/lite/valid.json')
        self.data['card'].pop('art_prompt', None)
        self.input = self.root / 'content.json'; save(self.input, self.data)
        self.card_data = {'twinlight': 'card-1', 'name': self.data['name'],
                          'summarizer': self.data['summarizer'], 'card': copy.deepcopy(self.data['card'])}
        self.card_input = self.root / 'card-input.json'; save(self.card_input, self.card_data)

    def test_html_finishes_without_an_art_prompt_or_card_assets(self):
        self.assertTrue(lite.check_text(self.input.read_text())['ok'])
        report = build_lite(self.data, self.root / 'site', generated_at=AT, confirmed=True)
        html = (self.root / 'site/index.html').read_text()
        self.assertTrue(report['ok'])
        self.assertIn(self.data['name'], html)
        self.assertEqual(report['art_mode'], 'placeholder')
        self.assertFalse((self.root / 'card').exists())

    def test_standalone_card_spec_needs_no_themes_or_html_and_keeps_user_brief(self):
        brief = self.root / 'art-brief.txt'; brief.write_text(BRIEF)
        output = self.root / 'card/spec.json'
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/twinlight.py'),
                                 'card-spec', str(self.card_input), '--art-prompt-file', str(brief),
                                 '--out', str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        spec = load(output)
        self.assertEqual(spec['persona_digest'], lite.persona_digest(self.data))
        for role in ['prototype', 'background', 'subject', 'effects']:
            self.assertIn(BRIEF, spec['prompts'][role])
        self.assertFalse(list(self.root.rglob('*.html')))
        self.assertNotIn('themes', read_card_data(self.card_input))

    def test_card_package_and_explicit_import_preserve_existing_html_and_content(self):
        fonts = [Path('/System/Library/Fonts/Supplemental/Songti.ttc'),
                 Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
        font = next((p for p in fonts if p.is_file()), None)
        if font is None: self.skipTest('A local font is required for independent typography')
        build_lite(self.data, self.root / 'site', generated_at=AT, confirmed=True)
        before = (self.root / 'site/index.html').read_bytes()
        original_input = self.input.read_bytes()
        native_fixture(self.root / 'native', lite.persona_digest(self.card_data))
        assembled = self.root / 'assembled'
        prepare(self.card_data, self.root / 'native/background.png', self.root / 'native/subject.png',
                self.root / 'native/effects.png', assembled, font, art_prompt=BRIEF)
        package(assembled / 'layers.json', self.root / 'card.json', self.card_input)
        self.assertEqual(load(self.root / 'card.json')['persona_digest'], lite.persona_digest(self.data))
        revised = card_spec(self.card_data, generated_at=AT, art_prompt=BRIEF + '改用克制的珍珠光。')
        self.assertEqual(revised['persona_digest'], lite.persona_digest(self.data))
        self.assertEqual((self.root / 'site/index.html').read_bytes(), before)
        self.assertEqual(self.input.read_bytes(), original_input)
        report = build_lite(self.data, self.root / 'site-with-card', generated_at=AT, confirmed=True,
                            layers=assembled / 'layers.json')
        self.assertEqual(report['art_mode'], 'layered')
        self.assertEqual((self.root / 'site/index.html').read_bytes(), before)
        other = copy.deepcopy(self.data); other['name'] = '另一测试者'
        with self.assertRaises(ContractError):
            build_lite(other, self.root / 'foreign', generated_at=AT, layers=assembled / 'layers.json')

    def test_card_schema_rejects_galaxy_fields_and_missing_visual_brief(self):
        mixed = dict(self.card_data, themes=self.data['themes']); save(self.card_input, mixed)
        with self.assertRaises(ContractError): read_card_data(self.card_input)
        with self.assertRaises(ContractError): card_spec(self.card_data, generated_at=AT)

    def test_card_preview_needs_no_galaxy_and_preserves_native_assets(self):
        native_fixture(self.root / 'native', lite.persona_digest(self.card_data))
        manifest = self.root / 'native/layers.json'
        before = {p.name: p.read_bytes() for p in manifest.parent.iterdir()}
        report = preview(manifest, self.root / 'card/preview.html', self.card_input)
        html = (self.root / 'card/preview.html').read_text()
        self.assertTrue(report['ok'])
        self.assertFalse(report['browser_verified'])
        self.assertIn('const HOLO_LAYERS=', html)
        self.assertIn('tBackground,tSubject,tSpirit,tEffects,tText,tLine', html)
        self.assertIn(self.card_data['card']['title'], html)
        self.assertNotIn('__DEPTH_', html)
        self.assertNotIn('__CARD_DATA__', html)
        self.assertNotIn(self.data['themes'][0]['label'], html)
        self.assertEqual({p.name: p.read_bytes() for p in manifest.parent.iterdir()}, before)
        with self.assertRaises(ContractError): preview(manifest, self.card_input, self.card_input)
        other = copy.deepcopy(self.card_data); other['name'] = '另一测试者'
        save(self.card_input, other)
        with self.assertRaises(ContractError): preview(manifest, self.root / 'wrong.html', self.card_input)

    def strict_content(self):
        history = load(ROOT / 'examples/demo/history.json')
        analysis = load(ROOT / 'examples/demo/analysis.json')
        for field in ['symbols', 'visual_style', 'portrait_mode', 'reference_consent']:
            analysis['card'].pop(field, None)
        return history, analysis

    def test_strict_html_also_finishes_without_art_settings(self):
        history, analysis = self.strict_content()
        report = build_strict(history, analysis, self.root / 'strict-html')
        self.assertTrue(report['ok'])
        self.assertTrue((self.root / 'strict-html/index.html').is_file())
        profile, _, _ = compile_profile(history, analysis)
        native_fixture(self.root / 'strict-native', profile['persona']['persona_digest'])
        report = build_strict(history, analysis, self.root / 'strict-with-card', layers=self.root / 'strict-native/layers.json')
        self.assertTrue(report['ok'])

    def test_strict_card_design_does_not_change_reviewed_content_or_binding(self):
        history, analysis = self.strict_content()
        original = copy.deepcopy(analysis)
        profile, _, _ = compile_profile(history, analysis)
        binding = profile['persona']['persona_digest']
        with self.assertRaises(ContractError): art_brief(analysis, binding)
        direction = {'visual_style': BRIEF, 'symbols': ['折纸罗盘']}
        brief = art_brief(analysis, binding, direction)
        self.assertEqual(brief['visual_style'], BRIEF)
        self.assertEqual(brief['persona_digest'], binding)
        self.assertEqual(analysis, original)
        save(self.root / 'history.json', history); save(self.root / 'analysis.json', analysis)
        save(self.root / 'art-direction.json', direction)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/twinlight.py'), 'art-brief',
                                 str(self.root / 'history.json'), str(self.root / 'analysis.json'),
                                 '--art-direction-file', str(self.root / 'art-direction.json'),
                                 '--out', str(self.root / 'strict-brief.json')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(load(self.root / 'strict-brief.json'), brief)
        self.assertEqual(load(self.root / 'analysis.json'), original)
        with self.assertRaises(ContractError):
            art_brief(analysis, binding, dict(direction, portrait_mode='user_reference'))


if __name__ == '__main__':
    unittest.main()
