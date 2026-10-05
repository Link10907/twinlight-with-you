"""Test the real controller/delivery glue with explicit renderer/browser test doubles.

These tests exercise admission, resumption and invalidation. They do NOT establish
fixed-template rendering, real browser/WebGL behavior or real image quality.
"""
from __future__ import annotations
import copy
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from twinlight_core import run as controller
import twinlight_core
from twinlight_core.common import load, save
from visual_v2_fixtures import PERSONA, ref, dossier as synthetic_dossier, minimal_embedded


class DeliveryQualityGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve(); self.work = self.root / 'run'
        self.manifest = synthetic_dossier(self.root / 'art')
        self.data = {'twinlight': 'lite-1', 'name': 'TEST PERSON', 'summarizer': 'TEST', 'card': {}}
        self.input = self.root / 'person.json'; save(self.input, self.data)
        self.built = []
        self.browser_hook = None
        self.template_ok = True
        def build_lite(data, out, **kwargs):
            out.mkdir(parents=True, exist_ok=True); self.built.append(out.name)
            for name in ('index.html', 'compiled-check.js'):
                (out / name).write_text('TEST DOUBLE: ' + name, encoding='utf-8')
            if kwargs.get('layers'):
                # Real native bytes under a controlled HTML builder; still not a V10 browser test.
                shutil.copyfile(minimal_embedded(self.manifest.parent), out / 'index.html')
            for name in ('profile.json', 'render-inputs.json', 'template-receipt.json', 'build-report.json'):
                save(out / name, {'release': {'draft': True, 'share_allowed': False}})
            return {'ok': True}
        def render_card_preview(data, out, **kwargs):
            out.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(self.manifest.parent / 'front.png', out)
            return {'ok': True}
        def preview(layers, out, content):
            shutil.copyfile(self.manifest.parent / 'preview.html', out); return {'ok': True}
        def package(layers, out, content):
            save(out, {'test_fixture_only': True}); return {'ok': True}
        modules = {}
        def module(name, **functions):
            m = types.ModuleType(name)
            for k, v in functions.items(): setattr(m, k, v)
            modules[name] = m
            return m
        package_names = {
            'lite': module('twinlight_core.lite', persona_digest=lambda d: PERSONA),
            'site': module('twinlight_core.site', build_lite=build_lite, render_card_preview=render_card_preview),
            'art': module('twinlight_core.art', validate_layers=lambda *args: {'art_status': 'generated'}),
            'cardgen': module('twinlight_core.cardgen', read_card_data=load, card_spec=lambda *a, **k: {}),
            'template_origin': module('twinlight_core.template_origin', verify_site=lambda *a: {'ok': self.template_ok}),
        }
        module('package_card', package=package); module('preview_card', preview=preview)
        self.mock_modules = mock.patch.dict(sys.modules, modules); self.mock_modules.start(); self.addCleanup(self.mock_modules.stop)
        for name, m in package_names.items():
            patch = mock.patch.object(twinlight_core, name, m, create=True); patch.start(); self.addCleanup(patch.stop)
        def browser(state, workspace, key, html, **kwargs):
            if self.browser_hook:
                self.browser_hook(key)
            result = {'status': 'skipped' if kwargs.get('disabled') else 'passed', 'attempts': 0, 'test_double': True}
            state['stages'][key] = result
            return result
        patch = mock.patch.object(controller, '_browser', side_effect=browser); patch.start(); self.addCleanup(patch.stop)

    def execute(self, **kwargs):
        return controller.run(self.input, self.work, **kwargs)

    def test_public_route_blocks_source_less_layers_before_html_integration(self):
        (self.manifest.parent / 'art-evidence.json').unlink()
        r = self.execute(layers=self.manifest)
        self.assertEqual(r['status'], 'needs_art_evidence'); self.assertFalse(r['complete'])
        self.assertEqual(self.built, ['site']); self.assertNotIn('html_with_card', r['outputs'])
        self.assertNotIn('card_pack', r['outputs']); self.assertIn('card_preview', r['candidate_outputs'])
        self.assertTrue(Path(r['outputs']['html']).is_file())
        self.assertFalse(r['dynamic_verified'])

    def test_rejected_card_does_not_integrate(self):
        p = self.manifest.parent / 'prototype-review.json'; review = load(p); review['decision'] = 'revise'; save(p, review)
        epath = self.manifest.parent / 'art-evidence.json'; e = load(epath); e['reviews']['prototype'] = ref(p); save(epath, e)
        r = self.execute(layers=self.manifest)
        self.assertEqual(r['status'], 'art_rejected'); self.assertFalse(r['ok']); self.assertFalse(r['complete'])
        self.assertEqual(self.built, ['site']); self.assertEqual(r['next_action']['type'], 'repair_art')

    def test_accepted_bound_reviews_allow_integration_not_aesthetic_certification(self):
        r = self.execute(layers=self.manifest)
        self.assertTrue(r['complete']); self.assertEqual(r['status'], 'files_ready')
        self.assertEqual(self.built, ['site', 'site-with-card'])
        self.assertTrue(r['art_reviewed_by_host']); self.assertTrue(r['generation_evidence_checked'])
        self.assertFalse(r['quality_verified']); self.assertFalse(r['generation_provenance_verified'])
        self.assertFalse(r['text_confirmed'])

    def test_no_browser_does_not_become_complete(self):
        r = self.execute(layers=self.manifest, no_browser=True)
        self.assertEqual(r['status'], 'dynamic_unverified'); self.assertFalse(r['complete'])
        self.assertTrue(r['art_reviewed_by_host'])

    def test_resuming_preserves_verified_base_html(self):
        first = self.execute(); path = Path(first['outputs']['html']); before = (path.read_bytes(), path.stat().st_mtime_ns)
        r = self.execute(layers=self.manifest)
        self.assertTrue(r['complete']); self.assertTrue(r['stages']['html']['reused'])
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_later_missing_review_invalidates_previously_ready_delivery(self):
        self.assertTrue(self.execute(layers=self.manifest)['complete'])
        p = self.manifest.parent / 'art-evidence.json'; e = load(p); del e['reviews']['final']; save(p, e)
        r = self.execute()
        self.assertEqual(r['status'], 'needs_art_review'); self.assertFalse(r['complete'])
        self.assertNotIn('html_with_card', r['outputs'])
        self.assertTrue(r['stages']['card']['reused'])

    def test_evidence_removed_during_integration_cannot_inherit_approval(self):
        def hook(key):
            if key == 'integration_browser':
                (self.manifest.parent / 'art-evidence.json').unlink()
        self.browser_hook = hook
        r = self.execute(layers=self.manifest)
        self.assertFalse(r['complete']); self.assertNotIn('html_with_card', r['outputs'])
        self.assertEqual(r['status'], 'needs_art_evidence')
        self.assertFalse(load(self.work / 'delivery-report.json')['complete'])

    def test_missing_art_action_starts_with_prototype_gate(self):
        r = self.execute()
        self.assertEqual(r['status'], 'needs_card'); self.assertEqual(r['next_action']['type'], 'prepare_and_review_prototype')
        self.assertFalse(r['complete']); self.assertEqual(len(r['next_action']['read']), 1)

    def test_pending_evidence_keeps_exact_resume_options(self):
        (self.manifest.parent / 'art-evidence.json').unlink()
        r = self.execute(layers=self.manifest, no_browser=True)
        resume = r['next_action']['resume']
        self.assertIn('--no-browser', resume); self.assertIn(str(self.manifest), resume)
        self.assertIn(str(self.input.resolve()), resume); self.assertIn(str(self.work), resume)
        self.assertFalse(r['next_action']['user_confirmation_required'])

    def test_html_only_does_not_require_any_art_evidence(self):
        r = self.execute(mode='html')
        self.assertEqual(r['status'], 'files_ready'); self.assertTrue(r['complete']); self.assertFalse(r['art_reviewed_by_host'])
        self.assertEqual(self.built, ['site']); self.assertNotIn('art_quality', r['stages'])

    def test_card_only_does_not_build_galaxy(self):
        r = self.execute(mode='card', layers=self.manifest)
        self.assertTrue(r['complete']); self.assertEqual(self.built, [])
        self.assertNotIn('html', r['outputs']); self.assertIn('card_front', r['outputs'])

    def test_template_failure_stays_failure_even_when_art_is_reviewed(self):
        self.template_ok = False
        r = self.execute(layers=self.manifest)
        self.assertFalse(r['complete']); self.assertFalse(r['ok'])
        self.assertIn(r['status'], ('failed', 'partial_success'))

    def test_private_mechanical_engine_never_claims_complete(self):
        r = controller._run_mechanical(self.input, self.work, layers=self.manifest)
        self.assertTrue(r['mechanical_only']); self.assertFalse(r['complete'])

    def test_delivery_receipt_binds_current_artifacts(self):
        r = self.execute(layers=self.manifest)
        receipt = load(self.work / 'delivery-report.json')
        self.assertEqual(receipt['outputs_sha256'], {k: controller._sha(Path(v)) for k, v in r['outputs'].items()})
        self.assertTrue(receipt['draft']); self.assertFalse(receipt['share_allowed'])
        self.assertFalse(receipt['quality_verified'])

    def test_deleted_output_is_not_presented_as_complete(self):
        def hook(key):
            if key == 'integration_browser': (self.work / 'card/front.png').unlink()
        self.browser_hook = hook
        r = self.execute(layers=self.manifest)
        self.assertFalse(r['complete']); self.assertNotIn('card_front', r['outputs'])


if __name__ == '__main__':
    unittest.main()
