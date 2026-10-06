"""Synthetic contracts for display sampling; these are not real image-tool results."""
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageOps

from visual_v2_fixtures import PERSONA, dossier, ref, save, minimal_embedded
from twinlight_core.art_quality import check_evidence, snapshot, sha256
from twinlight_core.canvas_mapping import compose_layers
from twinlight_core.embedded_card import audit_embedding
from twinlight_core.visual_contract import layer_prompt, visual_brief


class RoundingEvidenceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.layers = dossier(self.root)
        # Only synthetic test imagery is resized here to simulate provider rounding.
        path = self.root / 'subject.png'
        with Image.open(path) as image:
            subject = image.resize((601, 799))
        subject.save(path)
        alpha = subject.getchannel('A')
        edge = ImageChops.difference(alpha.filter(ImageFilter.MaxFilter(5)), alpha.filter(ImageFilter.MinFilter(5)))
        ImageOps.invert(edge).convert('RGBA').save(self.root / 'lineart.png')
        manifest = self.read('layers.json')
        manifest['canvas_mapping'] = {'version':'native-rounding-1','canvas':[600,800],
                                      'sampling':'full_uv_bilinear','native_edit_roles':['subject']}
        save(self.layers, manifest)
        design = self.read('art-direction.json')
        prompt = self.root / 'subject-prompt.txt'
        prompt.write_text(layer_prompt(design, 'subject', (600, 800)))
        call = self.read('subject-call.json')
        call['request'].update(operation='image_edit', edit_base=ref(self.root / 'prototype.png'),
                               coordinate_policy='preserve_full_canvas', prompt=ref(prompt))
        call['response'].update(canvas=[601,799], sha256=sha256(path))
        save(self.root / 'subject-call.json', call)
        evidence = self.read('art-evidence.json')
        evidence['images']['subject'].update(ref(path), call=ref(self.root / 'subject-call.json'))
        images = {role: Image.open(self.root / filename).convert('RGBA') for role, filename in manifest['assets'].items()}
        compose_layers(manifest, images).save(self.root / 'composite.png')
        compose_layers(manifest, images, include_text=True).save(self.root / 'front.png')
        evidence['composite'] = ref(self.root / 'composite.png')
        save(self.root / 'art-evidence.json', evidence)
        targets, *_ = snapshot(self.layers, PERSONA, front=self.root / 'front.png', preview=self.root / 'preview.html')
        for stage in ('prototype', 'composite', 'final'):
            review = self.read(stage + '-review.json')
            review['targets'] = targets[stage]
            save(self.root / (stage + '-review.json'), review)
            evidence['reviews'][stage] = ref(self.root / (stage + '-review.json'))
        save(self.root / 'art-evidence.json', evidence)

    def read(self, name):
        return json.loads((self.root / name).read_text())

    def gate(self):
        return check_evidence(self.layers, PERSONA, front=self.root / 'front.png', preview=self.root / 'preview.html')

    def update_call(self, call):
        save(self.root / 'subject-call.json', call)
        evidence = self.read('art-evidence.json')
        evidence['images']['subject']['call'] = ref(self.root / 'subject-call.json')
        save(self.root / 'art-evidence.json', evidence)

    def test_full_evidence_and_embedded_bytes_keep_original_native_image(self):
        original = (self.root / 'subject.png').read_bytes()
        self.assertTrue(self.gate()['ok'], self.gate())
        report = audit_embedding(minimal_embedded(self.root), self.layers, PERSONA)
        self.assertTrue(report['ok'], report)
        self.assertEqual((self.root / 'subject.png').read_bytes(), original)
        self.assertEqual(report['canvas'], [600,800])

    def test_actual_response_dimensions_cannot_be_relabeled_as_requested(self):
        call = self.read('subject-call.json')
        call['response']['canvas'] = [600,800]
        self.update_call(call)
        report = self.gate()
        self.assertFalse(report['ok'])
        self.assertEqual(report['errors'][0]['code'], 'returned_canvas')

    def test_rounding_exception_requires_real_native_edit_request(self):
        call = self.read('subject-call.json')
        call['request'].pop('operation')
        prompt = self.root / 'subject-prompt.txt'
        prompt.write_text(visual_brief(self.read('art-direction.json'), 'subject'))
        call['request']['prompt'] = ref(prompt)
        self.update_call(call)
        report = self.gate()
        self.assertFalse(report['ok'])
        self.assertEqual(report['errors'][0]['code'], 'canvas_mismatch')

    def test_without_explicit_mapping_mismatch_still_fails(self):
        manifest = self.read('layers.json')
        manifest.pop('canvas_mapping')
        save(self.layers, manifest)
        self.assertFalse(self.gate()['ok'])


if __name__ == '__main__':
    unittest.main()
