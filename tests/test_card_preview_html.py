"""The independent interactive preview must preserve every accepted source."""
from __future__ import annotations
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from twinlight_core import lite
from twinlight_core.common import ContractError, load, save
from preview_card import preview
from test_card_art import native_fixture


class InteractiveCardPreview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        data = load(ROOT / 'tests/fixtures/lite/valid.json')
        data['card'].pop('art_prompt', None)
        self.data = {'twinlight': 'card-1', 'name': data['name'],
                     'summarizer': data['summarizer'], 'card': data['card']}
        self.input = self.root / 'card-input.json'
        save(self.input, self.data)
        self.manifest = native_fixture(self.root / 'native', lite.persona_digest(self.data))
        self.sources = [self.input, self.manifest] + [self.manifest.parent / path
                        for path in load(self.manifest)['assets'].values()]

    def source_bytes(self):
        return {path: path.read_bytes() for path in self.sources}

    def test_output_rejects_direct_symlink_and_hardlink_aliases_of_every_source(self):
        before = self.source_bytes()
        for i, source in enumerate(self.sources):
            for kind in ('direct', 'symlink', 'hardlink'):
                with self.subTest(source=source.name, alias=kind):
                    out = source if kind == 'direct' else self.root / f'{i}-{kind}.html'
                    if kind == 'symlink':
                        out.symlink_to(source)
                    elif kind == 'hardlink':
                        out.hardlink_to(source)
                    with self.assertRaises(ContractError):
                        preview(self.manifest, out, self.input)
                    self.assertEqual(self.source_bytes(), before)

    def test_rebuilding_only_the_preview_keeps_source_bytes_and_identity(self):
        before = self.source_bytes()
        out = self.root / 'card/index.html'
        first = preview(self.manifest, out, self.input)
        expected = out.read_bytes()
        out.write_text('stale preview', encoding='utf-8')
        second = preview(self.manifest, out, self.input)
        self.assertEqual(out.read_bytes(), expected)
        self.assertEqual(self.source_bytes(), before)
        for report in (first, second):
            self.assertEqual(report['persona_digest'], lite.persona_digest(self.data))
            self.assertEqual(report['canvas'], [600, 800])
            self.assertFalse(report['browser_verified'])
        self.assertIn(self.data['card']['title'], out.read_text(encoding='utf-8'))

    def test_cli_rejects_hardlink_to_card_content(self):
        before = self.source_bytes()
        out = self.root / 'content-alias.html'
        out.hardlink_to(self.input)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/preview_card.py'),
                                 '--layers', str(self.manifest), '--data', str(self.input),
                                 '--out', str(out)], capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Preview cannot replace card content', result.stderr)
        self.assertEqual(self.source_bytes(), before)


if __name__ == '__main__':
    unittest.main()
