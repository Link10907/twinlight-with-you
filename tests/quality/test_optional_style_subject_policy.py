"""SYNTHETIC policy regressions; no image generation or visual acceptance."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quality_fixtures import ROOT, design
from test_style_selection import request
from twinlight_core import style_selection as ss
from twinlight_core.common import load
from twinlight_core.card_context import image_input, validate_input, render_prompt
from twinlight_core.visual_contract import catalog, validate_design, VisualContractError


class OptionalStyleTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.w = Path(tmp.name) / 'work'

    def test_default_random_cannot_be_silently_filtered(self):
        for mode in (None, 'random'):
            q = request(candidates=['forest-fantasy', 'paper-craft-story'], reason='Subject preference')
            if mode is not None:
                q['mode'] = mode
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'all installed styles'):
                ss.select(self.w, q)
        self.assertFalse(self.w.exists())

    def test_default_single_candidate_is_not_random(self):
        with self.assertRaises(ValueError):
            ss.select(self.w, request(candidates=['twinlight-collector']))
        self.assertFalse(self.w.exists())

    def test_explicit_style_still_beats_default(self):
        q = request(style={'id': 'real-life-cinematic', 'version': '1.0.0'})
        r = ss.select(self.w, q)
        self.assertEqual(r['selected_style'], q['style'])
        self.assertEqual(load(self.w / ss.RECORD)['request']['mode'], 'explicit')

    def test_all_style_pool_order_is_irrelevant(self):
        choices = [s['id'] for s in catalog()]
        a = ss.select(self.w, request(candidates=choices, seed='SYNTHETIC'))
        b = ss.select(self.w, request(candidates=list(reversed(choices)), seed='SYNTHETIC'))
        self.assertEqual(a['selected_style'], b['selected_style'])
        self.assertTrue(b['reused'])

    def test_legacy_implicit_subject_random_resumes_without_migration(self):
        q = request(mode='subject_random', seed='SYNTHETIC')
        a = ss.select(self.w, q)
        before = {p.name: p.read_bytes() for p in self.w.iterdir()}
        del q['mode']
        with patch.object(ss.secrets, 'token_hex', side_effect=AssertionError('No redraw')):
            b = ss.select(self.w, q)
        self.assertEqual(a['selected_style'], b['selected_style'])
        self.assertTrue(b['reused'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.w.iterdir()})

    def test_legacy_filtered_random_record_is_readable(self):
        q = request(mode='random', candidates=['forest-fantasy', 'paper-craft-story'], seed='SYNTHETIC')
        normalize = ss._normalize
        # Model the old selector, which allowed an explicitly filtered random pool.
        with patch.object(ss, '_normalize', side_effect=lambda value, **kw: normalize(value, frozen=True)):
            a = ss.select(self.w, q)
        b = ss.select(self.w, q)
        self.assertEqual(a['selected_style'], b['selected_style'])
        self.assertTrue(b['reused'])

    def test_changed_explicit_mode_cannot_migrate_old_record(self):
        q = request(mode='subject_random')
        ss.select(self.w, q)
        with self.assertRaisesRegex(ValueError, 'frozen'):
            ss.select(self.w, {**q, 'mode': 'random'})

    def test_catalog_and_host_report_random_default(self):
        cat = json.loads((ROOT / 'assets/art-styles/catalog.json').read_text())
        self.assertEqual(cat['upstream_default_mode'], 'random')
        self.assertEqual(ss.selection_status(self.w)['default_mode'], 'random')

    def test_readme_and_mapping_cover_only_installed_styles(self):
        readme = (ROOT / 'README.md').read_text()
        guide = (ROOT / 'references/style-selection.md').read_text()
        self.assertIn('不选画风就默认随机', readme)
        self.assertIn('可选，放在启动句后', readme)
        for style in catalog():
            self.assertIn(style['name'], readme)
            self.assertIn(style['id'], guide)
        self.assertNotIn('这次用水墨画风。', readme)


class NonAnimalSubjectTests(unittest.TestCase):
    def test_both_schemas_allow_only_human_and_object(self):
        for name in ('card-image-input.schema.json', 'art-direction-v2.schema.json'):
            schema = json.loads((ROOT / 'schemas' / name).read_text())
            fields = schema['properties']['subject']['properties']
            self.assertEqual(fields['kind']['enum'], ['human', 'object'])
            parts = fields['appearance']['items']['properties']['part']['enum']
            self.assertFalse(set(parts) & {'fur', 'feathers', 'scales', 'horns'})

    def test_full_design_rejects_animal_and_anthropomorphic(self):
        for kind in ('animal', 'anthropomorphic'):
            with self.subTest(kind=kind), self.assertRaises(VisualContractError):
                validate_design(design(kind))

    def test_thin_input_and_prompt_reject_animal_and_anthropomorphic(self):
        for kind in ('animal', 'anthropomorphic'):
            value = image_input(design())
            value['subject']['kind'] = kind
            value['subject']['species'] = '赤狐'
            for check in (validate_input, lambda x: render_prompt(x, 'prototype', (600, 800))):
                with self.subTest(kind=kind, check=check), self.assertRaises(VisualContractError):
                    check(value)

    def test_selector_rejects_animal_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = Path(tmp) / 'work'
            q = request()
            q['subject']['kind'] = 'animal'
            with self.assertRaises(VisualContractError):
                ss.select(w, q)
            self.assertFalse(w.exists())

    def test_human_label_cannot_hide_animal_species(self):
        full = design()
        thin = image_input(full)
        for value, check in ((full, validate_design), (thin, validate_input)):
            value['subject']['species'] = '赤狐'
            with self.assertRaisesRegex(VisualContractError, 'Human subject'):
                check(value)

    def test_human_label_cannot_hide_animal_parts(self):
        for part in ('fur', 'feathers', 'scales', 'horns'):
            full = design()
            thin = image_input(full)
            for value, check in ((full, validate_design), (thin, validate_input)):
                value['subject']['appearance'][0]['part'] = part
                with self.subTest(part=part), self.assertRaises(VisualContractError):
                    check(value)

    def test_obvious_hybrid_descriptions_are_rejected(self):
        for description in ('黑发上方长着猫耳', '银色兽尾', 'a pair of fox ears', 'large antlers'):
            full = design()
            thin = image_input(full)
            for value, check in ((full, validate_design), (thin, validate_input)):
                value['subject']['appearance'][0]['description'] = description
                with self.subTest(description=description), self.assertRaisesRegex(VisualContractError, 'Animal features'):
                    check(value)

    def test_valid_human_and_object_work_in_every_style(self):
        for style in catalog():
            for kind in ('human', 'object'):
                value = image_input(design(kind, style=style['id']))
                self.assertEqual(validate_input(value), value)
                prompt = render_prompt(value, 'prototype', (600, 800))
                self.assertIn('不使用动物、拟人动物、兽耳兽尾或动物同伴', prompt)
                self.assertIn('参考图中的动物不进入画面', prompt)
                self.assertEqual(set(value), {'version', 'style', 'subject', 'scene'})

    def test_subject_validation_does_not_rewrite_input(self):
        full = design()
        before = copy.deepcopy(full)
        validate_design(full)
        self.assertEqual(full, before)
        thin = image_input(full)
        before = copy.deepcopy(thin)
        validate_input(thin)
        self.assertEqual(thin, before)

    def test_reviewer_requires_observed_non_animal_subject(self):
        text = (ROOT / 'REVIEWER.md').read_text()
        self.assertIn('无动物、拟人动物、兽耳兽尾或动物同伴', text)
        self.assertIn('不能因为参考图出现动物就放行', text)


if __name__ == '__main__':
    unittest.main()
