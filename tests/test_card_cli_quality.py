"""CLI and assembler integration uses native synthetic artwork, never biographies."""
from __future__ import annotations
import copy
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from PIL import Image, ImageDraw
from prepare_card_layers import prepare
from test_card_art import native_fixture
from test_workflow_reliability import DATA
from twinlight_core.common import ContractError, load, save
from twinlight_core.lite import to_profile


class CardCliQuality(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = copy.deepcopy(DATA)
        self.data_path = self.root / 'person.json'; save(self.data_path, self.data)
        self.owner = to_profile(self.data, generated_at='2000-01-01T00:00:00Z')['persona']['persona_digest']
        self.size = (1086, 1448)
        self.native = self.root / 'native'; native_fixture(self.native, self.owner, self.size)
        # The reused fixture has a fixed-size decoration; retain adequate native alpha
        # occupancy at this larger actual canvas without touching any tested originals.
        effects = Image.new('RGBA', self.size)
        ImageDraw.Draw(effects).ellipse((760, 200, 820, 260), fill=(230, 210, 120, 240))
        effects.save(self.native / 'effects.png')
        self.prototype = self.root / 'prototype.png'
        Image.new('RGB', self.size, (25, 40, 65)).save(self.prototype)
        self.composition = {'version': '1.0', 'persona_digest': self.owner,
                            'canvas': {'width': self.size[0], 'height': self.size[1]},
                            'source_prototype_sha256': hashlib.sha256(self.prototype.read_bytes()).hexdigest(),
                            'subject_bounds': [.19, .24, .61, .81],
                            'text_safe_regions': [[.05, .03, .9, .1]], 'max_text_overlap': 0}
        self.composition_path = self.root / 'composition.json'; save(self.composition_path, self.composition)
        self.paths = {role: self.native / (role + '.png') for role in ('background', 'subject', 'effects')}

    def cli(self, out, *, composition=None, prototype=None):
        args = [sys.executable, str(ROOT / 'scripts/twinlight.py'), 'card-spec', str(self.data_path), '--out', str(out)]
        if prototype is not None: args += ['--prototype', str(prototype)]
        if composition is not None: args += ['--composition', str(composition)]
        return subprocess.run(args, capture_output=True, text=True, timeout=30)

    def font(self):
        candidates = [Path('/System/Library/Fonts/Supplemental/Songti.ttc'),
                      Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'),
                      Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
                      Path('C:/Windows/Fonts/msyh.ttc')]
        font = next((p for p in candidates if p.is_file()), None)
        if font is None: self.skipTest('This assembly test requires a local raster font')
        return font

    def assemble(self, out, *, composition=None, prototype=None, font=None):
        return prepare(self.data, self.paths['background'], self.paths['subject'], self.paths['effects'], out,
                       font or Path('unused-before-copy-validation.ttf'), composition=composition, prototype=prototype)

    def test_cli_reads_prototype_actual_canvas_without_modifying_image(self):
        original = self.prototype.read_bytes(); out = self.root / 'native-spec.json'
        result = self.cli(out, prototype=self.prototype)
        self.assertEqual(result.returncode, 0, result.stderr)
        spec = load(out)
        self.assertEqual((spec['canvas']['width'], spec['canvas']['height']), self.size)
        for prompt in spec['prompts'].values(): self.assertIn('1086×1448', prompt)
        self.assertEqual(self.prototype.read_bytes(), original)

    def test_cli_keeps_same_person_lock_and_native_canvas(self):
        out = self.root / 'locked-spec.json'
        result = self.cli(out, prototype=self.prototype, composition=self.composition_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        spec = load(out)
        self.assertEqual(spec['composition'], self.composition)
        self.assertEqual(spec['manifest_template']['composition'], self.composition)
        self.assertEqual(spec['persona_digest'], self.owner)
        self.assertEqual((spec['canvas']['width'], spec['canvas']['height']), self.size)

    def test_cli_rejects_foreign_owner_canvas_and_prototype_hash_without_writing_output(self):
        cases = [('owner', {'persona_digest': 'f' * 64}, 'different persona'),
                 ('canvas', {'canvas': {'width': 1080, 'height': 1440}}, 'Composition canvas'),
                 ('hash', {'source_prototype_sha256': 'f' * 64}, '另一张原型')]
        for name, updates, message in cases:
            with self.subTest(name=name):
                invalid = copy.deepcopy(self.composition); invalid.update(updates)
                path = self.root / (name + '-lock.json'); save(path, invalid)
                out = self.root / (name + '-spec.json')
                result = self.cli(out, prototype=self.prototype, composition=path)
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)
                self.assertFalse(out.exists())

    def test_prepare_preserves_original_bytes_and_outputs_actual_canvas_spec(self):
        originals = {role: path.read_bytes() for role, path in self.paths.items()}
        prototype_bytes = self.prototype.read_bytes(); out = self.root / 'assembled'
        report = self.assemble(out, composition=self.composition, prototype=self.prototype, font=self.font())
        self.assertTrue(report['ok']); self.assertEqual(report['size'], list(self.size))
        spec = load(out / 'card-spec.json'); manifest = load(out / 'layers.json')
        self.assertEqual((spec['canvas']['width'], spec['canvas']['height']), self.size)
        self.assertEqual(spec['composition'], self.composition)
        self.assertEqual(manifest['composition'], self.composition)
        for role, original in originals.items():
            self.assertEqual((out / manifest['assets'][role]).read_bytes(), original)
            self.assertEqual(self.paths[role].read_bytes(), original)
        self.assertEqual(self.prototype.read_bytes(), prototype_bytes)

    def test_prepare_rejects_wrong_prototype_size_and_hash_before_overwriting_files(self):
        for name, size in [('size', (1080, 1440)), ('hash', self.size)]:
            with self.subTest(name=name):
                wrong = self.root / (name + '-prototype.png'); Image.new('RGB', size, 'red').save(wrong)
                out = self.root / ('existing-' + name); out.mkdir()
                sentinel = out / 'background.png'; sentinel.write_bytes(b'existing-artwork-to-preserve')
                with self.assertRaises(ContractError):
                    self.assemble(out, composition=self.composition, prototype=wrong)
                self.assertEqual(sentinel.read_bytes(), b'existing-artwork-to-preserve')
                self.assertFalse((out / 'subject.png').exists())
                self.assertFalse((out / 'layers.json').exists())

    def test_prepare_requires_prototype_when_lock_contains_its_hash(self):
        out = self.root / 'no-prototype'
        with self.assertRaisesRegex(ContractError, '提供同一张参考图'):
            self.assemble(out, composition=self.composition)
        self.assertFalse(out.exists())

    def test_footer_text_respects_later_safe_region_without_moving_native_art(self):
        composition = copy.deepcopy(self.composition)
        composition['text_safe_regions'] = [[.25, .83, .95, 1]]
        originals = {role: path.read_bytes() for role, path in self.paths.items()}
        out = self.root / 'later-footer'
        self.assemble(out, composition=composition, prototype=self.prototype, font=self.font())
        text = Image.open(out / 'text.png').convert('RGBA')
        width, height = text.size
        # Exclude the outer frame and header, and find actual light lettering,
        # rather than the translucent dark scrim beneath the text.
        region = text.crop((int(width*.06), int(height*.2), int(width*.94), int(height*.95)))
        light = Image.new('L', region.size)
        light.putdata([255 if r > 160 and g > 160 and b > 120 and a > 220 else 0
                       for r, g, b, a in region.getdata()])
        bounds = light.getbbox()
        self.assertIsNotNone(bounds, 'footer lettering must remain readable')
        self.assertGreaterEqual(bounds[1] + int(height*.2), int(height*.83))
        self.assertGreaterEqual(bounds[0] + int(width*.06), int(width*.25) - 3)
        self.assertLessEqual(bounds[2] + int(width*.06), int(width*.95) + 3)
        for role, original in originals.items():
            self.assertEqual((out / (role + '.png')).read_bytes(), original)

    def test_prepare_rejects_foreign_owner_and_canvas_lock_before_copying(self):
        for name, updates in [('owner', {'persona_digest': 'f' * 64}),
                              ('canvas', {'canvas': {'width': 1080, 'height': 1440}})]:
            with self.subTest(name=name):
                invalid = copy.deepcopy(self.composition); invalid.update(updates)
                out = self.root / ('wrong-' + name)
                with self.assertRaises(ContractError):
                    self.assemble(out, composition=invalid, prototype=self.prototype)
                self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
