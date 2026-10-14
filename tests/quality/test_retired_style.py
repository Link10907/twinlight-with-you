"""SYNTHETIC retirement regressions; no image calls or visual approvals."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from quality_fixtures import ROOT, design
from test_style_selection import request
from twinlight_core import style_selection as ss
from twinlight_core.card_context import image_input, render_prompt, validate_input
from twinlight_core.common import load, save
from twinlight_core.visual_contract import catalog, style_for, validate_design, VisualContractError
from bootstrap import REQUIRED, check_root
from package_skill import package, resource_files

RETIRED = 'futuristic-clean'
ACTIVE = {'twinlight-collector', 'forest-fantasy', 'real-life-cinematic',
          'eastern-fantasy-scroll', 'paper-craft-story'}


class RetiredStyleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.work = self.root / 'work'

    def test_catalog_and_presets_contain_exactly_five_active_styles(self):
        self.assertEqual({style['id'] for style in catalog()}, ACTIVE)
        presets = load(ROOT / 'assets/art-styles/image-presets.json')['presets']
        self.assertEqual(set(presets), ACTIVE)
        self.assertFalse((ROOT / f'assets/art-styles/{RETIRED}.json').exists())

    def test_selector_status_never_advertises_retired_style(self):
        status = ss.selection_status(self.work)
        self.assertEqual({style['id'] for style in status['styles']}, ACTIVE)
        self.assertEqual(status['default_mode'], 'random')
        self.assertFalse(self.work.exists())

    def test_default_draw_uses_all_five_styles_and_resume_preserves_choice(self):
        result = ss.select(self.work, request(seed='SYNTHETIC_RETIREMENT'))
        record = load(self.work / ss.RECORD)
        self.assertEqual(set(record['request']['candidates']), ACTIVE)
        self.assertIn(result['selected_style']['id'], ACTIVE)
        before = {p.name: p.read_bytes() for p in self.work.iterdir()}
        resumed = ss.select(self.work, request(seed='SYNTHETIC_RETIREMENT'))
        self.assertTrue(resumed['reused'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.work.iterdir()})

    def test_explicit_retired_style_rejected_without_output(self):
        with self.assertRaises(VisualContractError) as error:
            ss.select(self.work, request(style={'id': RETIRED, 'version': '1.0.0'}))
        self.assertEqual(error.exception.code, 'style_unknown')
        self.assertFalse(self.work.exists())

    def test_retired_style_rejected_in_both_candidate_modes(self):
        for mode in ('random', 'subject_random'):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'Unknown candidate'):
                ss.select(self.work, request(mode=mode, candidates=sorted(ACTIVE | {RETIRED}),
                                             reason='SYNTHETIC stale candidate pool'))
            self.assertFalse(self.work.exists())

    def test_direct_lookup_cannot_load_retired_style(self):
        with self.assertRaises(VisualContractError) as error:
            style_for(RETIRED, '1.0.0')
        self.assertEqual(error.exception.code, 'style_unknown')

    def test_direct_drawing_and_full_design_cannot_bypass_catalog(self):
        full = design()
        thin = image_input(full)
        for value, check in ((full, validate_design), (thin, validate_input),
                             (copy.deepcopy(thin), lambda x: render_prompt(x, 'prototype', (600, 800)))):
            value['style'] = {'id': RETIRED, 'version': '1.0.0'}
            with self.assertRaises(VisualContractError) as error:
                check(value)
            self.assertEqual(error.exception.code, 'style_unknown')

    def test_cli_retired_choice_fails_without_creating_workspace(self):
        source = self.root / 'request.json'
        save(source, request(style={'id': RETIRED, 'version': '1.0.0'}))
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/portable.py'),
                                 'select-style', str(source), '--workspace', str(self.work)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertFalse(self.work.exists())

    def test_bootstrap_does_not_require_removed_file(self):
        self.assertNotIn(f'assets/art-styles/{RETIRED}.json', REQUIRED)
        result = check_root(ROOT, profile='portable')
        self.assertTrue(result['resource_complete'], result['missing_resources'])
        self.assertTrue(result['package_manifest_verified'])
        self.assertTrue(result['template_lock']['ok'])

    def test_readme_and_guide_advertise_only_active_options(self):
        for name in ('README.md', 'references/style-selection.md'):
            text = (ROOT / name).read_text()
            self.assertNotIn(RETIRED, text)
            self.assertNotIn('未来极简', text)
            self.assertNotIn('六种', text)
            self.assertIn('五种', text)
        guide = (ROOT / 'references/style-selection.md').read_text()
        for style in ACTIVE:
            self.assertIn(style, guide)

    def test_packaged_skill_cannot_reinstall_removed_preset(self):
        relative = f'assets/art-styles/{RETIRED}.json'
        self.assertNotIn(relative, {p.relative_to(ROOT).as_posix() for p in resource_files(ROOT)})
        archive = self.root / 'skill.zip'
        package(ROOT, archive)
        with ZipFile(archive) as zipped:
            prefix = 'twinlight-with-you/'
            self.assertNotIn(prefix + relative, zipped.namelist())
            presets = json.loads(zipped.read(prefix + 'assets/art-styles/image-presets.json'))
            self.assertEqual(set(presets['presets']), ACTIVE)
            manifest = json.loads(zipped.read(prefix + 'package-manifest.json'))
            self.assertNotIn(relative, manifest['files_sha256'])
            self.assertEqual(manifest['skill_revision'], 'v10-portable-1.2.3')


if __name__ == '__main__':
    unittest.main()
