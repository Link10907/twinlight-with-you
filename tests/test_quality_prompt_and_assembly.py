"""Check actual prompt compiler and assembly wiring with synthetic image fixtures."""
from __future__ import annotations
import copy
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock
from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import twinlight_core
from twinlight_core import cardgen
from twinlight_core.art_quality import compile_visual_brief
from twinlight_core.common import ContractError
from test_art_quality_gate import PERSONA, design_fixture, synthetic_dossier, sha256


class StructuredPromptTests(unittest.TestCase):
    def setUp(self):
        self.design = design_fixture()
        self.data = {'name': 'TEST', 'summarizer': 'GPT', 'card': {'title': 'PAPER MAKER', 'english_title': 'A CAREFUL BUILDER',
                      'keywords': ['Curiosity', 'Practice'], 'tagline': 'Build one small thing well.', 'reflection': 'Synthetic content only.'}}
        lite = types.ModuleType('twinlight_core.lite'); lite.persona_digest = lambda data: PERSONA
        p = mock.patch.dict(sys.modules, {'twinlight_core.lite': lite}); p.start(); self.addCleanup(p.stop)
        p = mock.patch.object(twinlight_core, 'lite', lite, create=True); p.start(); self.addCleanup(p.stop)

    def test_per_layer_prompts_include_the_chosen_visual_scene(self):
        text = json.dumps(self.design, ensure_ascii=False)
        prompts = cardgen.art_prompts({'art_prompt': text}, canvas=(300, 400))
        visual = compile_visual_brief(text)
        for role in ('prototype', 'background', 'subject', 'effects', 'spirit'):
            self.assertIn(visual, prompts[role])
            self.assertNotIn('persona_digest', prompts[role])
            self.assertNotIn('不询问创意选择', prompts[role])
        self.assertIn('真实 alpha', prompts['subject'])
        self.assertIn('300×400', prompts['background'])

    def test_structured_brief_does_not_change_persona_content(self):
        before = copy.deepcopy(self.data)
        spec = cardgen.card_spec(self.data, generated_at='2026-10-04T12:00:00Z', art_prompt=json.dumps(self.design))
        self.assertEqual(self.data, before); self.assertEqual(spec['persona_digest'], PERSONA)
        self.assertEqual(spec['generation_status'], 'brief_only')

    def test_wrong_persona_design_cannot_be_used(self):
        self.design['persona_digest'] = 'b' * 64
        with self.assertRaises(ValueError):
            cardgen.card_spec(self.data, generated_at='2026-10-04', art_prompt=json.dumps(self.design))

    def test_legacy_plain_brief_is_still_a_brief_not_a_verified_card(self):
        spec = cardgen.card_spec(self.data, generated_at='2026-10-04', art_prompt='A deliberate handmade paper scene with a calm uncluttered composition.')
        self.assertEqual(spec['generation_status'], 'brief_only')
        self.assertFalse(spec['quality_review']['automatic_approval'])

    def test_structured_json_length_has_a_bound(self):
        self.design['unused'] = 'A' * 6500
        with self.assertRaises(ContractError):
            cardgen.card_spec(self.data, generated_at='2026-10-04', art_prompt=json.dumps(self.design))


class NativeAssemblyTests(unittest.TestCase):
    def setUp(self):
        StructuredPromptTests.setUp(self)
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); synthetic_dossier(self.root / 'source')
        self.out = self.root / 'assembled'; self.source = self.root / 'source'
        fonts = (Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'),
                 Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
                 Path('/System/Library/Fonts/STHeiti Light.ttc'),
                 Path('C:/Windows/Fonts/msyh.ttc'))
        self.font = next((p for p in fonts if p.is_file()), None)
        if self.font is None: self.skipTest('No test font')
        art = types.ModuleType('twinlight_core.art'); art.validate_layers = lambda *a: {'ok': True, 'test_double': True}
        site = types.ModuleType('twinlight_core.site')
        def opened(path):
            with Image.open(path) as im: return im.convert('RGBA')
        site.native_subject = opened; site.open_card_image = opened; site.ImageChops_safe = ImageChops.difference
        p = mock.patch.dict(sys.modules, {'twinlight_core.art': art, 'twinlight_core.site': site}); p.start(); self.addCleanup(p.stop)
        spec = importlib.util.spec_from_file_location('test_prepare_card_layers', ROOT / 'scripts/prepare_card_layers.py')
        self.module = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)

    def prepare(self, **kwargs):
        return self.module.prepare(self.data, self.source / 'background.png', self.source / 'subject.png', self.source / 'effects.png',
                                   self.out, self.font, prototype=self.source / 'prototype.png', art_prompt=json.dumps(self.design), **kwargs)

    def test_actual_assembler_uses_theme_aware_text_and_preserves_raw_bytes(self):
        before = {r: sha256(self.source / (r + '.png')) for r in ('background', 'subject', 'effects')}
        self.prepare()
        for role, digest in before.items():
            self.assertEqual(sha256(self.source / (role + '.png')), digest)
            self.assertEqual(sha256(self.out / (role + '.png')), digest)
        report = json.loads((self.out / 'typography-report.json').read_text())
        self.assertEqual(report['theme']['frame'], 'none'); self.assertFalse(report['overlap'])
        self.assertTrue((self.out / 'art-direction.json').is_file())

    def test_explicit_nonempty_spirit_is_copied_not_erased(self):
        p = self.source / 'companion.png'; im = Image.new('RGBA', (300, 400)); ImageDraw.Draw(im).ellipse((20, 100, 50, 130), fill='white'); im.save(p)
        self.prepare(spirit=p)
        self.assertEqual(sha256(p), sha256(self.out / 'spirit.png'))

    def test_nonempty_existing_spirit_is_not_silently_overwritten(self):
        self.out.mkdir(); p = self.out / 'spirit.png'; Image.new('RGBA', (300, 400), (1, 2, 3, 255)).save(p); before = sha256(p)
        with self.assertRaises(ContractError): self.prepare()
        self.assertEqual(sha256(p), before)

    def test_mismatched_spirit_canvas_is_rejected_without_resizing(self):
        p = self.source / 'companion.png'; Image.new('RGBA', (600, 800)).save(p)
        with self.assertRaises(ContractError): self.prepare(spirit=p)
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
