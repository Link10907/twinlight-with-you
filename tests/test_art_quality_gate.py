"""Synthetic TEST DOUBLES exercise evidence contracts, never fresh image quality.

The fake image adapter, inspection records and view captures below are deliberately
not presented as actual image-model runs or browser/visual acceptance evidence.
"""
from __future__ import annotations
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from twinlight_core.art_quality import (REVIEW_CHECKS, check_evidence, compile_visual_brief, read_json, sha256,
                                       snapshot, validate_design, ArtEvidenceError)
from twinlight_core.art_typography import typeset, validate_theme

PERSONA = 'a' * 64


def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def ref(path):
    return {'file': Path(path).name, 'sha256': sha256(Path(path))}


def design_fixture():
    return {
        'version': 'art-direction-1', 'persona_digest': PERSONA,
        'preferences': {'keep': ['A clear subject with restrained decorative details'], 'avoid': ['Dense technical dashboard symbols'],
                        'basis': 'Synthetic preference text for contract tests only.', 'rejected_asset_sha256': []},
        'scene': {'style': 'Quiet editorial watercolor illustration', 'subject': 'One small original paper sculpture',
                  'action': 'A folded arch resting on its broad base', 'setting': 'An uncluttered pale tabletop',
                  'materials': 'Soft paper fibers with visible watercolor grain', 'palette': 'Off-white, desaturated teal and charcoal',
                  'lighting': 'Broad soft side light from upper left', 'composition': 'One central focal subject, generous top and bottom text space'},
        'decision': {'considered': [{'name': 'paper', 'rationale': 'Paper folds express careful construction without technical logos.'},
                                    {'name': 'wood', 'rationale': 'Wood grain gives a tactile interpretation but would be less airy.'}],
                     'selected': 'paper', 'rationale': 'The paper silhouette provides one clear focal point and coherent material.'},
        'references': [], 'reference_basis': 'text_only',
        'typography': {'text_color': '#20303A', 'accent_color': '#396D72', 'scrim_color': '#FFFFFF',
                       'scrim_opacity': 0, 'frame': 'none', 'footer_top': .74},
    }


def synthetic_dossier(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    size = (300, 400)
    bg = Image.new('RGBA', size, (30, 45, 70, 255))
    subject = Image.new('RGBA', size)
    ImageDraw.Draw(subject).ellipse((85, 105, 200, 275), fill=(220, 165, 90, 255))
    effects = Image.new('RGBA', size)
    ImageDraw.Draw(effects).rectangle((210, 130, 225, 155), fill=(140, 190, 230, 160))
    spirit = Image.new('RGBA', size)
    text = Image.new('RGBA', size)
    ImageDraw.Draw(text).rectangle((70, 335, 230, 355), fill=(230, 230, 220, 255))
    alpha = subject.getchannel('A')
    line = ImageOps.invert(ImageChops.difference(alpha.filter(ImageFilter.MaxFilter(5)), alpha.filter(ImageFilter.MinFilter(5)))).convert('RGBA')
    layers = {'background': bg, 'subject': subject, 'effects': effects, 'spirit': spirit, 'text': text, 'lineart': line}
    for role, im in layers.items():
        im.save(root / (role + '.png'))
    raw = Image.alpha_composite(Image.alpha_composite(bg, subject), effects)
    raw.save(root / 'prototype.png'); raw.save(root / 'composite.png')
    Image.alpha_composite(raw, text).save(root / 'front.png')
    (root / 'preview.html').write_text('<!doctype html><p>Test-double preview, not a browser validation</p>', encoding='utf-8')
    manifest = {'schema_version': '1.0', 'persona_digest': PERSONA, 'art_status': 'generated', 'reference_consent': False,
                'assets': {r: r + '.png' for r in layers}, 'depths': {'background': -.25, 'subject': .4, 'effects': .5, 'text': 0}}
    save(root / 'layers.json', manifest)
    design = design_fixture(); save(root / 'art-direction.json', design)
    evidence = {'version': 'art-evidence-1', 'persona_digest': PERSONA, 'run_id': 'TEST-RUN',
                'design': ref(root / 'art-direction.json'), 'images': {}, 'composite': ref(root / 'composite.png'), 'reviews': {}}
    visual = compile_visual_brief(json.dumps(design))
    prototype_hash = sha256(root / 'prototype.png')
    for role in ('prototype', 'background', 'subject', 'effects'):
        (root / (role + '-prompt.txt')).write_text(visual + '\nRender role: ' + role, encoding='utf-8')
        artifact = 'TEST-ARTIFACT-' + role
        (root / (role + '-return.txt')).write_text('TEST DOUBLE, NOT A REAL TOOL RESPONSE: ' + artifact, encoding='utf-8')
        call = {'version': 'image-call-1', 'kind': 'image_tool', 'tool': 'TEST-IMAGE-ADAPTER', 'call_id': 'TEST-CALL-' + role,
                'run_id': 'TEST-RUN', 'capabilities': {'image_generation': True, 'native_transparency': True, 'reference_images': True},
                'request': {'canvas': list(size), 'transparent': role in ('subject', 'effects'),
                            'prompt': ref(root / (role + '-prompt.txt')), 'design_sha256': sha256(root / 'art-direction.json'),
                            'reference_sha256': [] if role == 'prototype' else [prototype_hash]},
                'response': {'artifact_id': artifact, 'sha256': sha256(root / (role + '.png'))},
                'raw_response': ref(root / (role + '-return.txt'))}
        save(root / (role + '-call.json'), call)
        evidence['images'][role] = {**ref(root / (role + '.png')), 'mode': 'generated', 'call': ref(root / (role + '-call.json'))}
    save(root / 'art-evidence.json', evidence)
    targets, *_ = snapshot(root / 'layers.json', PERSONA, front=root / 'front.png', preview=root / 'preview.html')
    for index, name in enumerate(('left', 'right', 'mobile')):
        view = raw.copy(); view.putpixel((10, 10), (20 + index * 60, 90, 150, 255)); view.save(root / (name + '.png'))
    for stage, criteria in REVIEW_CHECKS.items():
        (root / (stage + '-inspection.txt')).write_text('TEST DOUBLE visual inspection capture, not an actual visual acceptance.', encoding='utf-8')
        review = {'stage': stage, 'targets': targets[stage], 'observer': 'TEST-REVIEWER', 'observed_at': '2026-10-04T12:00:00Z',
                  'decision': 'accept', 'checks': {c: {'passed': True, 'observation': 'Synthetic assertion for the specific test criterion: ' + c} for c in criteria},
                  'capture': ref(root / (stage + '-inspection.txt'))}
        if stage == 'final':
            review['views'] = {name: ref(root / (name + '.png')) for name in ('left', 'right', 'mobile')}
        save(root / (stage + '-review.json'), review)
        evidence['reviews'][stage] = ref(root / (stage + '-review.json'))
    save(root / 'art-evidence.json', evidence)
    return root / 'layers.json'


class ArtQualityGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'art'; self.manifest = synthetic_dossier(self.root)

    def check(self, stage='final'):
        return check_evidence(self.manifest, PERSONA, stage=stage, front=self.root / 'front.png', preview=self.root / 'preview.html')

    def evidence(self):
        return read_json(self.root / 'art-evidence.json')

    def mutate_call(self, role, mutate):
        p = self.root / (role + '-call.json'); doc = read_json(p); mutate(doc); save(p, doc)
        e = self.evidence(); e['images'][role]['call'] = ref(p); save(self.root / 'art-evidence.json', e)

    def mutate_review(self, stage, mutate):
        p = self.root / (stage + '-review.json'); doc = read_json(p); mutate(doc); save(p, doc)
        e = self.evidence(); e['reviews'][stage] = ref(p); save(self.root / 'art-evidence.json', e)

    def rejected(self, code=None):
        report = self.check(); self.assertFalse(report['ok'], report)
        if code:
            self.assertEqual(report['errors'][0]['code'], code, report)
        return report

    def test_pending_template_without_observer_is_pending_not_rejected(self):
        def pending(review):
            review.update(decision='pending', observer=None, observed_at=None, capture=None)
        self.mutate_review('prototype', pending)
        report = self.check('prototype')
        self.assertEqual(report['status'], 'needs_art_review')
        self.assertEqual(report['errors'][0]['code'], 'pending_review')

    def test_unlettered_composite_bytes_are_bound_in_final_recheck(self):
        report = self.check()
        self.assertEqual(report['inputs_sha256'][str(self.root / 'composite.png')], sha256(self.root / 'composite.png'))

    def test_full_prototype_cannot_masquerade_as_opaque_background(self):
        (self.root / 'background.png').write_bytes((self.root / 'prototype.png').read_bytes())
        self.rejected('poster_reused')

    def test_consistent_dossier_is_traceable_not_certified(self):
        r = self.check(); self.assertTrue(r['ok'], r)
        self.assertTrue(r['host_visual_review_recorded'])
        self.assertFalse(r['quality_verified']); self.assertFalse(r['generation_provenance_verified'])
        self.assertEqual(r['reused_roles'], [])

    def test_missing_evidence_blocks_completion(self):
        (self.root / 'art-evidence.json').unlink()
        self.assertEqual(self.rejected()['status'], 'needs_art_evidence')

    def test_generated_manifest_alone_does_not_establish_source(self):
        e = self.evidence(); e['images'].pop('subject'); save(self.root / 'art-evidence.json', e)
        self.rejected('source_missing')

    def test_old_call_cannot_be_claimed_new(self):
        self.mutate_call('subject', lambda x: x.update(run_id='OLD-RUN')); self.rejected('old_call_as_new')

    def test_same_owner_reuse_is_explicit_and_reported(self):
        self.mutate_call('subject', lambda x: x.update(run_id='OLD-RUN'))
        e = self.evidence(); e['images']['subject'].update(mode='reused', reuse={'declared': True, 'persona_digest': PERSONA,
                       'reason': 'Explicit same-owner reuse of a currently reviewed test asset.'})
        save(self.root / 'art-evidence.json', e)
        r = self.check(); self.assertTrue(r['ok'], r); self.assertEqual(r['reused_roles'], ['subject'])

    def test_undeclared_reuse_is_blocked(self):
        e = self.evidence(); e['images']['subject']['mode'] = 'reused'; save(self.root / 'art-evidence.json', e)
        self.rejected('undeclared_reuse')

    def test_wrong_owner_reuse_is_blocked(self):
        e = self.evidence(); e['images']['subject'].update(mode='reused', reuse={'declared': True, 'persona_digest': 'b' * 64, 'reason': 'Not this person'})
        save(self.root / 'art-evidence.json', e); self.rejected('undeclared_reuse')

    def test_absent_native_transparency_is_blocked(self):
        self.mutate_call('subject', lambda x: x['request'].update(transparent=False)); self.rejected('native_alpha_missing')

    def test_missing_image_tool_capability_is_blocked(self):
        self.mutate_call('subject', lambda x: x['capabilities'].update(image_generation=False)); self.rejected('image_tool_unavailable')

    def test_procedural_drawing_is_not_a_native_image_call(self):
        self.mutate_call('subject', lambda x: x.update(tool='Pillow')); self.rejected('procedural_source')

    def test_unsupported_source_mode_is_blocked(self):
        e = self.evidence(); e['images']['subject']['mode'] = 'placeholder'; save(self.root / 'art-evidence.json', e)
        self.rejected('unsupported_source')

    def test_tool_return_must_bind_actual_image(self):
        self.mutate_call('subject', lambda x: x['response'].update(sha256='b' * 64)); self.rejected('tool_output_mismatch')

    def test_tool_response_capture_is_not_optional(self):
        self.mutate_call('subject', lambda x: x['response'].update(artifact_id='NONEXISTENT-ARTIFACT')); self.rejected('uncaptured_response')

    def test_reference_to_selected_prototype_is_required(self):
        self.mutate_call('subject', lambda x: x['request'].update(reference_sha256=[])); self.rejected('prototype_reference_missing')

    def test_canvas_is_actual_not_just_claimed(self):
        self.mutate_call('subject', lambda x: x['request'].update(canvas=[1080, 1440])); self.rejected('canvas_mismatch')

    def test_actual_prompt_must_bind_current_design(self):
        self.mutate_call('subject', lambda x: x['request'].update(design_sha256='b' * 64)); self.rejected('wrong_prompt_design')

    def test_actual_prompt_contains_concrete_visual_decisions(self):
        p = self.root / 'subject-prompt.txt'; p.write_text('Make a nice premium card.', encoding='utf-8')
        self.mutate_call('subject', lambda x: x['request'].update(prompt=ref(p))); self.rejected('visual_brief_missing')

    def test_invalid_background_cannot_pass_as_private_draft(self):
        p = self.root / 'background.png'; im = Image.open(p).convert('RGBA'); im.putpixel((0, 0), (0, 0, 0, 3)); im.save(p)
        self.rejected('background_alpha')

    def test_bogus_constant_lineart_is_rejected(self):
        Image.new('RGBA', (300, 400), (180, 180, 180, 180)).save(self.root / 'lineart.png')
        self.rejected('unregistered_lineart')

    def test_lineart_must_come_from_same_subject_pixels(self):
        p = self.root / 'lineart.png'; im = Image.open(p).convert('RGBA'); im.putpixel((2, 2), (10, 10, 10, 255)); im.save(p)
        self.rejected('unregistered_lineart')

    def test_raw_composite_must_match_registered_layers(self):
        p = self.root / 'composite.png'; im = Image.open(p).convert('RGBA'); im.putpixel((2, 2), (255, 0, 0, 255)); im.save(p)
        e = self.evidence(); e['composite'] = ref(p); save(self.root / 'art-evidence.json', e); self.rejected('wrong_composite')

    def test_front_must_be_actual_current_card(self):
        p = self.root / 'front.png'; im = Image.open(p).convert('RGBA'); im.putpixel((2, 2), (255, 0, 0, 255)); im.save(p)
        self.rejected('wrong_front')

    def test_missing_review_cannot_be_silently_accepted(self):
        e = self.evidence(); e['reviews'].pop('prototype'); save(self.root / 'art-evidence.json', e)
        self.assertEqual(self.rejected()['status'], 'needs_art_review')

    def test_explicit_negative_review_blocks(self):
        self.mutate_review('prototype', lambda x: x.update(decision='revise')); self.rejected('review_rejected')

    def test_pending_review_template_never_passes(self):
        self.mutate_review('prototype', lambda x: x.update(decision='pending'))
        self.assertEqual(self.rejected()['status'], 'needs_art_review')

    def test_a_failed_check_overrides_overall_accept(self):
        self.mutate_review('prototype', lambda x: x['checks']['composition'].update(passed=False)); self.rejected('failed_visual_check')

    def test_empty_visual_comment_does_not_count_as_review(self):
        self.mutate_review('prototype', lambda x: x['checks']['composition'].update(observation='ok')); self.rejected('invalid_text')

    def test_renaming_card_requires_current_persona(self):
        e = self.evidence(); e['persona_digest'] = 'b' * 64; save(self.root / 'art-evidence.json', e); self.rejected('wrong_persona')

    def test_changed_preview_invalidates_final_review(self):
        (self.root / 'preview.html').write_text('<p>A changed renderer</p>', encoding='utf-8'); self.rejected('stale_review')

    def test_review_targets_cannot_be_stale(self):
        self.mutate_review('prototype', lambda x: x['targets'].update(prototype_sha256='b' * 64)); self.rejected('stale_review')

    def test_left_right_captures_must_not_be_identical(self):
        self.mutate_review('final', lambda x: x['views'].update(right=x['views']['left'])); self.rejected('duplicate_views')

    def test_review_requires_timezone(self):
        self.mutate_review('prototype', lambda x: x.update(observed_at='2026-10-04T12:00:00')); self.rejected('review_time')

    def test_rejected_art_cannot_be_recycled(self):
        d = read_json(self.root / 'art-direction.json'); d['preferences']['rejected_asset_sha256'] = [sha256(self.root / 'prototype.png')]
        save(self.root / 'art-direction.json', d)
        e = self.evidence(); e['design'] = ref(self.root / 'art-direction.json'); save(self.root / 'art-evidence.json', e)
        self.rejected('rejected_asset_reused')

    def test_path_traversal_rejected_before_read(self):
        e = self.evidence(); e['design']['file'] = '../outside.json'; save(self.root / 'art-evidence.json', e); self.rejected('unsafe_path')

    def test_external_symlink_rejected_before_read(self):
        outside = self.root.parent / 'outside.json'; outside.write_text('{}')
        link = self.root / 'external.json'; link.symlink_to(outside)
        e = self.evidence(); e['design'] = {'file': link.name, 'sha256': sha256(outside)}; save(self.root / 'art-evidence.json', e)
        self.rejected('unsafe_path')

    def test_duplicate_json_fields_rejected(self):
        (self.root / 'art-evidence.json').write_text('{"version":"x","version":"y"}')
        self.rejected('duplicate_key')

    def test_nonfinite_json_rejected(self):
        (self.root / 'art-evidence.json').write_text('{"x":NaN}')
        self.rejected('nonfinite_number')

    def test_nonobject_evidence_rejected(self):
        (self.root / 'art-evidence.json').write_text('[]')
        self.rejected('object_required')

    def test_oversized_evidence_rejected(self):
        (self.root / 'art-evidence.json').write_text(' ' * (2 * 1024 * 1024 + 1))
        self.rejected('record_too_large')

    def test_prototype_gate_does_not_require_later_layers(self):
        for name in ('background', 'subject', 'effects', 'spirit', 'lineart', 'text'):
            (self.root / (name + '.png')).unlink()
        r = self.check('prototype'); self.assertTrue(r['ok'], r)

    def test_claimed_visual_reference_requires_actual_files(self):
        d = design_fixture(); d['reference_basis'] = 'visible_images'
        with self.assertRaises(ArtEvidenceError): validate_design(d)

    def test_brief_compiler_emits_visual_decisions_not_workflow_manual(self):
        text = compile_visual_brief(json.dumps(design_fixture()))
        self.assertIn('folded arch', text); self.assertIn('watercolor', text)
        for term in ('persona_digest', 'run-state', 'card-pack.json', 'TEST-RUN'):
            self.assertNotIn(term, text)

    def test_review_template_cli_defaults_to_unapproved(self):
        out = self.root / 'pending-review.json'
        p = subprocess.run([sys.executable, str(ROOT / 'scripts/art_quality.py'), 'review-template', '--layers', str(self.manifest),
                            '--persona-digest', PERSONA, '--stage', 'prototype', '--out', str(out)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        r = read_json(out); self.assertEqual(r['decision'], 'pending'); self.assertIsNone(r['observer'])
        self.assertTrue(all(v['passed'] is False for v in r['checks'].values()))

    def test_composite_cli_never_overwrites_sources(self):
        p = subprocess.run([sys.executable, str(ROOT / 'scripts/art_quality.py'), 'composite', '--layers', str(self.manifest),
                            '--persona-digest', PERSONA, '--out', str(self.root / 'subject.png')], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertTrue(self.check()['ok'])


class ThemeTypographyTests(unittest.TestCase):
    def setUp(self):
        fonts = (Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'),
                 Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
                 Path('/System/Library/Fonts/STHeiti Light.ttc'),
                 Path('C:/Windows/Fonts/msyh.ttc'))
        self.font = next((p for p in fonts if p.is_file()), None)
        if self.font is None: self.skipTest('No test font available')
        self.data = {'summarizer': 'GPT', 'card': {'title': 'PAPER MAKER', 'english_title': 'THE CAREFUL BUILDER',
            'keywords': ['Curiosity', 'Practice', 'Patience'], 'tagline': 'Make one small thing work well.'}}
        self.theme = design_fixture()['typography']

    def test_theme_has_no_forced_gold_frame(self):
        im, r = typeset(self.data, (1080, 1440), self.font, self.theme)
        self.assertEqual(im.getpixel((30, 30))[3], 0)
        self.assertEqual(r['theme']['accent_color'], '#396D72'); self.assertFalse(r['overlap'])

    def test_all_text_fields_are_measured_without_mutating_content(self):
        before = copy.deepcopy(self.data)
        _, r = typeset(self.data, (1080, 1440), self.font, self.theme)
        self.assertEqual(self.data, before)
        self.assertEqual({x['field'] for x in r['boxes']}, {'rarity', 'summarizer', 'title', 'english_title', 'keywords', 'tagline', 'edition'})

    def test_three_frame_modes_fit_actual_native_canvas(self):
        for frame in ('none', 'single', 'double'):
            theme = {**self.theme, 'frame': frame}
            im, r = typeset(self.data, (600, 800), self.font, theme)
            self.assertEqual(im.size, (600, 800)); self.assertFalse(r['overlap'])

    def test_impossibly_long_text_errors_instead_of_clipping(self):
        self.data['card']['title'] = 'A' * 2000
        with self.assertRaises(ValueError): typeset(self.data, (1080, 1440), self.font, self.theme)

    def test_invalid_theme_rejected(self):
        for bad in ({'frame': 'rainbow'}, {'scrim_opacity': True}, {'scrim_opacity': 999}, {'text_color': 'gold'}, {'footer_top': float('nan')}):
            with self.assertRaises(ValueError): validate_theme({**self.theme, **bad})

    def test_no_native_image_resizing(self):
        with self.assertRaises(ValueError): typeset(self.data, (1080, 1080), self.font, self.theme)


if __name__ == '__main__':
    unittest.main()
