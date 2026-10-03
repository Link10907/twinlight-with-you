"""Native card layers retain pixels, ownership and truthful static/placeholder status."""
import base64
import copy
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from twinlight_core import lite, state as fsm  # noqa: E402
from twinlight_core.cardgen import art_prompts, card_spec  # noqa: E402
from twinlight_core.common import ContractError, load, save  # noqa: E402
from twinlight_core.site import lite_layers, build_lite  # noqa: E402

AT = '2026-10-03T00:00:00Z'
FIXTURE = ROOT / 'tests/fixtures/lite/valid.json'
NODE = shutil.which('node')


def native_fixture(root, persona_digest, size=(600, 800)):
    """Procedural test shapes stand in for independent image-generator outputs."""
    root.mkdir(parents=True, exist_ok=True)
    W, H = size
    Image.new('RGB', size, (10, 25, 35)).save(root / 'background.png')
    subject = Image.new('RGBA', size)
    ImageDraw.Draw(subject).ellipse((W // 5, H // 4, W * 3 // 5, H * 4 // 5), fill=(70, 150, 130, 255))
    subject.putpixel((W // 5, H // 4), (220, 110, 35, 128))
    subject.save(root / 'subject.png')
    effects = Image.new('RGBA', size)
    ImageDraw.Draw(effects).ellipse((W * 4 // 5 - 15, 40, W * 4 // 5 + 15, 70), fill=(230, 210, 120, 240))
    effects.save(root / 'effects.png')
    Image.new('RGBA', size).save(root / 'spirit.png')
    text = Image.new('RGBA', size)
    ImageDraw.Draw(text).rectangle((10, 10, W - 10, H - 10), outline=(220, 190, 100, 255), width=3)
    ImageDraw.Draw(text).text((30, 25), 'SSR', fill=(220, 190, 100, 255))
    text.save(root / 'text.png')
    lineart = Image.new('RGB', size, 'white')
    ImageDraw.Draw(lineart).ellipse((W // 5, H // 4, W * 3 // 5, H * 4 // 5), outline='black', width=2)
    lineart.save(root / 'lineart.png')
    manifest = {'schema_version': '1.0', 'persona_digest': persona_digest, 'art_status': 'generated', 'reference_consent': False,
                'assets': {k: k + '.png' for k in ('background', 'subject', 'spirit', 'effects', 'text', 'lineart')},
                'depths': {'background': -.25, 'subject': .4, 'effects': .5, 'text': 0},
                'notes': 'Independent procedural test layers, no poster segmentation.'}
    save(root / 'layers.json', manifest)
    return root / 'layers.json'


def decode(uri):
    return Image.open(io.BytesIO(base64.b64decode(uri.split(',', 1)[1]))).convert('RGBA')


class NativeLayers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = load(FIXTURE)
        self.persona = lite.to_profile(self.data, generated_at=AT)['persona']['persona_digest']
        self.manifest = native_fixture(self.root / 'card', self.persona)

    def test_full_canvas_subject_is_kept_byte_for_byte(self):
        layers = lite_layers(layers=self.manifest, expected_persona=self.persona)
        original = Image.open(self.root / 'card/subject.png').convert('RGBA')
        rendered = decode(layers['layers']['subject'])
        self.assertEqual(rendered.size, original.size)
        self.assertEqual(rendered.tobytes(), original.tobytes())
        self.assertEqual(layers['art_mode'], 'layered')
        self.assertEqual(layers['binding'], 'persona_digest')
        self.assertNotIn('matte', layers)

    def test_native_pair_is_registered_and_no_template_scene_is_substituted(self):
        layers = lite_layers(character=self.root / 'card/subject.png', background=self.root / 'card/background.png')
        self.assertEqual(decode(layers['layers']['subject']).tobytes(), Image.open(self.root / 'card/subject.png').convert('RGBA').tobytes())
        self.assertEqual(decode(layers['layers']['background']).tobytes(), Image.open(self.root / 'card/background.png').convert('RGBA').tobytes())
        with self.assertRaisesRegex(ContractError, '完整背景'):
            lite_layers(character=self.root / 'card/subject.png')
        Image.new('RGB', (900, 1200), 'navy').save(self.root / 'card/wrong-background.png')
        with self.assertRaisesRegex(ContractError, '相同的画布'):
            lite_layers(character=self.root / 'card/subject.png', background=self.root / 'card/wrong-background.png')

    def test_opaque_green_or_checkerboard_are_not_accepted_as_alpha(self):
        W, H = 600, 800
        for kind in ('green', 'checker'):
            im = Image.new('RGB', (W, H), (0, 255, 0))
            if kind == 'checker':
                d = ImageDraw.Draw(im)
                for y in range(0, H, 25):
                    for x in range(0, W, 25):
                        d.rectangle((x, y, x+24, y+24), fill='white' if (x//25+y//25)%2 else 'grey')
            ImageDraw.Draw(im).ellipse((150, 150, 450, 650), fill=(70, 100, 120))
            path = self.root / (kind + '.png'); im.save(path)
            with self.subTest(kind), self.assertRaisesRegex(ContractError, '真实 alpha'):
                lite_layers(character=path, background=self.root / 'card/background.png')

    def test_manifest_owner_and_dimensions_must_match(self):
        with self.assertRaisesRegex(ContractError, 'different persona'):
            lite_layers(layers=self.manifest, expected_persona='f' * 64)
        with self.assertRaisesRegex(ContractError, 'persona_digest'):
            lite_layers(layers=self.manifest)
        Image.new('RGBA', (300, 400)).save(self.root / 'card/spirit.png')
        with self.assertRaisesRegex(ContractError, 'same canvas'):
            lite_layers(layers=self.manifest, expected_persona=self.persona)

    def test_static_prototype_has_zero_internal_parallax_and_truthful_release(self):
        prototype = self.root / 'prototype.png'
        Image.new('RGB', (600, 800), (180, 35, 70)).save(prototype)
        art = lite_layers(prototype=prototype)
        self.assertEqual((art['art_status'], art['art_mode']), ('static', 'static'))
        self.assertEqual(set(art['depths'].values()), {0})
        self.assertEqual(decode(art['layers']['background']).tobytes(), Image.open(prototype).convert('RGBA').tobytes())
        report = build_lite(self.data, self.root / 'static', generated_at=AT, prototype=prototype, confirmed=True)
        profile = load(self.root / 'static/profile.json')
        self.assertEqual(report['art_status'], 'static')
        self.assertEqual(profile['persona']['art_status'], 'static')
        self.assertEqual(profile['persona']['art_mode'], 'static')
        self.assertIn('尚未完成独立分层', profile['persona']['art_type'])
        self.assertTrue(profile['release']['share_allowed'])

    def test_prototype_is_reference_only_not_an_extra_texture(self):
        Image.new('RGB', (600, 800), (255, 0, 0)).save(self.root / 'card/prototype.png')
        art = lite_layers(layers=self.manifest, expected_persona=self.persona)
        self.assertEqual(set(art['layers']), {'background', 'subject', 'spirit', 'effects', 'text', 'lineart'})
        self.assertNotIn('prototype', art['layers'])
        with self.assertRaisesRegex(ContractError, '不能同时'):
            lite_layers(layers=self.manifest, expected_persona=self.persona, prototype=self.root / 'card/prototype.png')

    def test_build_manifest_is_reusable_across_dates_but_not_card_changes(self):
        report = build_lite(self.data, self.root / 'site', generated_at='2026-10-04T10:00:00Z', layers=self.manifest)
        self.assertEqual(report['persona_digest'], self.persona)
        self.assertEqual(report['art_mode'], 'layered')
        changed = copy.deepcopy(self.data); changed['card']['art_prompt'] = '一枚在雪地中慢慢转动的木质罗盘，浅银与暖木色。'
        with self.assertRaisesRegex(ContractError, 'different persona'):
            build_lite(changed, self.root / 'other', generated_at=AT, layers=self.manifest)

    def test_cli_card_spec_and_layers_build_use_the_same_binding(self):
        cli = [sys.executable, str(ROOT / 'scripts/twinlight.py')]
        spec_path = self.root / 'spec.json'
        r = subprocess.run(cli + ['card-spec', str(FIXTURE), '--out', str(spec_path)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(load(spec_path)['persona_digest'], self.persona)
        r = subprocess.run(cli + ['lite-build', str(FIXTURE), '--layers', str(self.manifest), '--out', str(self.root / 'cli')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['art_binding'], 'persona_digest')

    def test_workflow_reopens_art_when_a_referenced_layer_changes(self):
        ws = self.root / 'run'; fsm.start(ws)
        save(ws / 'twinlight.json', self.data); fsm.check_stage(ws); fsm.confirm(ws, '可以在本地生成')
        native_fixture(ws / 'card', self.persona)
        Image.new('RGB', (600, 800), 'red').save(ws / 'card/prototype.png')
        r = fsm.check_stage(ws)
        self.assertEqual((r['status'], r['next']['stage']), ('passed', 'build'))
        fsm.check_stage(ws)
        Image.new('RGBA', (600, 800)).save(ws / 'card/spirit.png')
        # Change encoded pixels without touching layers.json.
        spirit = Image.open(ws / 'card/spirit.png'); spirit.putpixel((0, 0), (50, 80, 90, 80)); spirit.save(ws / 'card/spirit.png')
        status = fsm.status(ws)
        self.assertEqual(status['current'], 'art')
        self.assertIn('卡图已修改', ' '.join(status['notes']))


class Prompts(unittest.TestCase):
    def test_each_layer_uses_the_current_concept_and_native_transparency(self):
        card = {'art_prompt': '一位鹿形林地守护灵，青苔毛色，陪伴幼苗，水彩风格。'}
        prompts = art_prompts(card)
        self.assertEqual(set(prompts), {'prototype', 'subject', 'character', 'background', 'effects', 'spirit', 'text'})
        for kind in ('prototype', 'subject', 'background', 'effects', 'spirit'):
            self.assertIn(card['art_prompt'], prompts[kind])
        self.assertEqual(prompts['character'], prompts['subject'])
        self.assertIn('真实 alpha', prompts['subject'])
        self.assertIn('只作为共同参考', prompts['prototype'])
        self.assertIn('不要画人物', prompts['background'])
        self.assertNotIn('#00FF00', '\n'.join(prompts.values()))
        self.assertNotIn('纯绿色', '\n'.join(prompts.values()))
        self.assertIn('独立 text 层', prompts['text'])

    def test_spec_binds_this_card_and_excludes_examples(self):
        data = load(FIXTURE)
        spec = card_spec(data, generated_at=AT)
        self.assertEqual(spec['persona_digest'], lite.to_profile(data, generated_at=AT)['persona']['persona_digest'])
        self.assertEqual(spec['manifest_template']['persona_digest'], spec['persona_digest'])
        self.assertFalse(spec['prototype']['included_in_final_layers'])
        self.assertEqual(spec['canvas']['width'], 1080)
        self.assertEqual(spec['canvas']['height'], 1440)
        self.assertEqual(spec['typography']['title'], data['card']['title'])
        self.assertNotIn('showcase', json.dumps(spec, ensure_ascii=False))

    @unittest.skipUnless(NODE, 'node not installed')
    def test_browser_twin_builds_identical_prompts(self):
        card = {'art_prompt': '  一枚陪伴栽种幼苗的林地罗盘。 '}
        js = subprocess.run([NODE, '-e', 'const L=require(process.argv[1]);process.stdout.write(JSON.stringify(L.artPrompts(JSON.parse(process.argv[2]))))',
                             str(ROOT / 'assets/lite/lite.js'), json.dumps(card)], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(js.stdout), art_prompts(card))


if __name__ == '__main__':
    unittest.main()
