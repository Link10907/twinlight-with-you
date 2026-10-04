"""Standalone card previews preserve registered art without building a site."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from twinlight_core import lite, site  # noqa: E402
from twinlight_core.common import ContractError, load  # noqa: E402
from test_card_art import AT, FIXTURE, native_fixture  # noqa: E402


def compose_registered(manifest_path):
    """Independent pixel oracle; lineart and any browser foil are excluded."""
    manifest = load(manifest_path)
    canvas = None
    for role in ('background', 'spirit', 'subject', 'effects', 'text'):
        with Image.open(manifest_path.parent / manifest['assets'][role]) as source:
            layer = source.convert('RGBA')
        canvas = layer.copy() if canvas is None else Image.alpha_composite(canvas, layer)
    return canvas


class CardPreview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = load(FIXTURE)
        self.persona = lite.to_profile(self.data, generated_at=AT)['persona']['persona_digest']
        self.manifest = native_fixture(self.root / 'card', self.persona)

    def assert_png(self, path):
        with Image.open(path) as image:
            self.assertEqual(image.format, 'PNG')
            return image.convert('RGBA')

    def assert_metadata(self, report, out, mode, status, kind):
        self.assertEqual(Path(report['out']).resolve(), out.resolve())
        self.assertEqual(report['sha256'], hashlib.sha256(out.read_bytes()).hexdigest())
        self.assertEqual(report['persona_digest'], self.persona)
        self.assertEqual((report['art_mode'], report['art_status'], report['preview_kind']),
                         (mode, status, kind))

    def source_bytes(self):
        manifest = load(self.manifest)
        paths = [self.manifest] + [self.manifest.parent / relative for relative in manifest['assets'].values()]
        return {path: path.read_bytes() for path in paths}

    def test_registered_preview_composites_current_text_without_any_html_stage(self):
        # All translucent roles overlap, so the oracle also verifies their order.
        for role, color in [('spirit', (50, 80, 220, 130)), ('effects', (220, 80, 40, 140))]:
            with Image.open(self.root / 'card' / (role + '.png')) as source:
                layer = source.convert('RGBA')
            ImageDraw.Draw(layer).rectangle((190, 290, 270, 370), fill=color)
            layer.save(self.root / 'card' / (role + '.png'))
        with Image.open(self.root / 'card/text.png') as source:
            text = source.convert('RGBA')
        draw = ImageDraw.Draw(text)
        draw.rectangle((210, 310, 250, 350), fill=(245, 205, 45, 180))
        draw.text((25, 75), 'CURRENT CARD TEXT', fill=(20, 240, 210, 255))
        text.save(self.root / 'card/text.png')
        expected = compose_registered(self.manifest)
        out = self.root / 'standalone/current-card.png'
        with mock.patch.object(site, 'write_site', side_effect=AssertionError('HTML build is not needed')), \
                mock.patch.object(site, 'template_parts', side_effect=AssertionError('HTML template is not needed')):
            report = site.render_card_preview(self.data, out, layers=self.manifest)
        actual = self.assert_png(out)
        self.assertEqual(actual.size, expected.size)
        self.assertEqual(actual.tobytes(), expected.tobytes())
        self.assertEqual(actual.getpixel((230, 330)), expected.getpixel((230, 330)))
        self.assert_metadata(report, out, 'layered', 'generated', 'registered_layers')
        self.assertEqual(list(self.root.rglob('*.html')), [])

    def test_changed_card_or_other_owner_is_rejected_before_output_is_written(self):
        changed_card = copy.deepcopy(self.data)
        changed_card['card']['art_prompt'] = '一枚浅银与暖木色的罗盘，在雪地中缓慢转动。'
        other_owner = copy.deepcopy(self.data)
        other_owner['name'] = '另一位完全虚构的人物'
        for label, data in [('changed-card', changed_card), ('other-owner', other_owner)]:
            with self.subTest(label=label):
                out = self.root / label / 'preview.png'
                with self.assertRaisesRegex(ContractError, 'different persona'):
                    site.render_card_preview(data, out, layers=self.manifest)
                self.assertFalse(out.exists())

    def test_original_bytes_are_preserved_and_repeated_inputs_keep_identical_pixels(self):
        before = self.source_bytes()
        input_before = copy.deepcopy(self.data)
        first = self.root / 'first.png'
        second = self.root / 'second.png'
        first_report = site.render_card_preview(self.data, first, layers=self.manifest)
        second_report = site.render_card_preview(self.data, second, layers=self.manifest)
        self.assertEqual(self.source_bytes(), before)
        self.assertEqual(self.data, input_before)
        self.assertEqual(self.assert_png(first).tobytes(), self.assert_png(second).tobytes())
        for report, out in [(first_report, first), (second_report, second)]:
            self.assert_metadata(report, out, 'layered', 'generated', 'registered_layers')

    def test_static_preview_keeps_native_canvas_and_modes_are_explicit(self):
        prototype = self.root / 'prototype.png'
        image = Image.new('RGBA', (768, 1024), (170, 35, 70, 255))
        for point, color in [((0, 0), (5, 15, 25, 255)), ((767, 0), (45, 55, 65, 255)),
                             ((0, 1023), (85, 95, 105, 255)), ((767, 1023), (125, 135, 145, 255))]:
            image.putpixel(point, color)
        image.save(prototype)
        before = prototype.read_bytes()
        out = self.root / 'static.png'
        report = site.render_card_preview(self.data, out, prototype=prototype)
        actual = self.assert_png(out)
        self.assertEqual(actual.size, image.size)
        self.assertEqual(actual.tobytes(), image.tobytes())
        for point in [(0, 0), (767, 0), (0, 1023), (767, 1023)]:
            self.assertEqual(actual.getpixel(point), image.getpixel(point))
        self.assert_metadata(report, out, 'static', 'static', 'static_prototype')
        self.assertEqual(prototype.read_bytes(), before)
        malformed = self.root / 'wrong-ratio.png'
        Image.new('RGB', (768, 1000), 'navy').save(malformed)
        rejected_out = self.root / 'wrong-ratio-preview.png'
        with self.assertRaises(ContractError):
            site.render_card_preview(self.data, rejected_out, prototype=malformed)
        self.assertFalse(rejected_out.exists())
        placeholder = self.root / 'placeholder.png'
        report = site.render_card_preview(self.data, placeholder)
        self.assert_png(placeholder)
        self.assert_metadata(report, placeholder, 'placeholder', 'placeholder', 'placeholder')

    def test_output_cannot_overwrite_any_registered_or_direct_image_source(self):
        before = self.source_bytes()
        for source in before:
            with self.subTest(source=source.name), self.assertRaises(ContractError):
                site.render_card_preview(self.data, source, layers=self.manifest)
        self.assertEqual(self.source_bytes(), before)
        prototype = self.root / 'prototype.png'
        Image.new('RGB', (600, 800), (170, 35, 70)).save(prototype)
        prototype_bytes = prototype.read_bytes()
        with self.assertRaises(ContractError):
            site.render_card_preview(self.data, prototype, prototype=prototype)
        self.assertEqual(prototype.read_bytes(), prototype_bytes)
        for role in ('subject', 'background'):
            with self.subTest(direct_source=role), self.assertRaises(ContractError):
                site.render_card_preview(self.data, self.root / 'card' / (role + '.png'),
                                         character=self.root / 'card/subject.png',
                                         background=self.root / 'card/background.png')
        alias = self.root / 'source-alias.png'
        alias.symlink_to(self.root / 'card/subject.png')
        with self.assertRaises(ContractError):
            site.render_card_preview(self.data, alias, layers=self.manifest)
        hardlink = self.root / 'source-hardlink.png'
        hardlink.hardlink_to(self.root / 'card/subject.png')
        with self.assertRaises(ContractError):
            site.render_card_preview(self.data, hardlink, layers=self.manifest)
        self.assertEqual(self.source_bytes(), before)

    def test_real_cli_generates_png_without_html_or_confirmation_artifacts(self):
        input_path = self.root / 'input.json'
        input_path.write_bytes(FIXTURE.read_bytes())
        original_input = input_path.read_bytes()
        out = self.root / 'cli/card-preview.png'
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/twinlight.py'), 'render-card',
                                 str(input_path), '--layers', str(self.manifest), '--out', str(out)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_metadata(json.loads(result.stdout), out, 'layered', 'generated', 'registered_layers')
        self.assertEqual(self.assert_png(out).tobytes(), compose_registered(self.manifest).tobytes())
        self.assertEqual(input_path.read_bytes(), original_input)
        self.assertEqual(list(out.parent.rglob('*.html')), [])
        self.assertFalse((out.parent / 'state.json').exists())
        self.assertFalse((out.parent / 'profile.json').exists())
        self.assertFalse((out.parent / 'confirmation.json').exists())
        alias = out.parent / 'input-alias.png'
        alias.hardlink_to(input_path)
        rejected = subprocess.run([sys.executable, str(ROOT / 'scripts/twinlight.py'), 'render-card',
                                   str(input_path), '--layers', str(self.manifest), '--out', str(alias)],
                                  capture_output=True, text=True, timeout=30)
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertEqual(input_path.read_bytes(), original_input)


if __name__ == '__main__':
    unittest.main()
