"""Portable cards preserve original raster files and their owner binding."""
import base64
import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from package_card import package
from prepare_card_layers import prepare
from twinlight_core.common import ContractError, load, save
from twinlight_core.lite import to_profile
from test_card_art import native_fixture


class CardPackage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = load(ROOT / 'tests/fixtures/lite/valid.json')
        self.owner = to_profile(self.data, generated_at='2026-10-03T00:00:00Z')['persona']['persona_digest']
        self.manifest = native_fixture(self.root / 'native', self.owner)

    def test_portable_keeps_all_original_files_and_refuses_another_owner(self):
        manifest = load(self.manifest)
        manifest['composition'] = {'version': '1.0', 'persona_digest': self.owner,
                                   'canvas': {'width': 600, 'height': 800},
                                   'subject_bounds': [.19, .24, .62, .82]}
        save(self.manifest, manifest)
        save(self.root / 'data.json', self.data)
        package(self.manifest, self.root / 'card.json', self.root / 'data.json')
        card = load(self.root / 'card.json')
        self.assertEqual(card['canvas'], [600, 800])
        self.assertEqual(card['composition'], manifest['composition'])
        for role, uri in card['layers'].items():
            self.assertEqual(base64.b64decode(uri.split(',', 1)[1]), (self.root / 'native' / (role+'.png')).read_bytes())
        other = copy.deepcopy(self.data)
        other['name'] = '另一个人'
        save(self.root / 'other.json', other)
        with self.assertRaises(ContractError):
            package(self.manifest, self.root / 'wrong.json', self.root / 'other.json')
        self.assertFalse((self.root / 'wrong.json').exists())

    def test_prepare_copies_source_bytes_and_keeps_registered_canvas(self):
        candidates = [Path('/System/Library/Fonts/Supplemental/Songti.ttc'),
                      Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
        font = next((p for p in candidates if p.is_file()), None)
        if font is None:
            self.skipTest('This test requires a local raster font')
        paths = {k: self.root / 'native' / (k+'.png') for k in ['subject', 'effects', 'background']}
        report = prepare(self.data, paths['background'], paths['subject'], paths['effects'], self.root / 'assembled', font)
        self.assertTrue(report['ok'])
        self.assertEqual(report['size'], [600, 800])
        self.assertEqual(load(self.root / 'assembled/layers.json')['persona_digest'], self.owner)
        for role, source in paths.items():
            self.assertEqual((self.root / 'assembled' / (role+'.png')).read_bytes(), source.read_bytes())


if __name__ == '__main__':
    unittest.main()
