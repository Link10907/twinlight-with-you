"""The collector quality anchor must reach the recorded image request, not just a prompt."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from visual_v2_fixtures import PERSONA, dossier, ref, save
from twinlight_core.art_quality import check_evidence, REVIEW_CHECKS, snapshot
from twinlight_core.visual_contract import default_style, review_checks, style_binding, style_for, style_references, visual_brief


class StyleReferenceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.layers = dossier(self.root)
        design = json.loads((self.root / 'art-direction.json').read_text())
        design['style'] = {'id': 'twinlight-collector', 'version': '1.0.0'}
        design['typography'] = default_style()['typography_default']
        save(self.root / 'art-direction.json', design)
        evidence = json.loads((self.root / 'art-evidence.json').read_text())
        evidence['design'] = ref(self.root / 'art-direction.json')
        prompt = self.root / 'prototype-prompt.txt'
        prompt.write_text(visual_brief(design, 'prototype'))
        call = json.loads((self.root / 'prototype-call.json').read_text())
        call['request'].update(prompt=ref(prompt), design_sha256=evidence['design']['sha256'],
                               style_binding=style_binding(design))
        references = []
        for index, anchor in enumerate(style_references(style_for('twinlight-collector'))):
            path = self.root / ('style-' + str(index) + '.png')
            shutil.copyfile(anchor['file'], path)
            references.append({**ref(path), 'purpose': 'style_only'})
        call['request']['reference_images'] = references
        call['request']['reference_sha256'] = [r['sha256'] for r in references]
        save(self.root / 'prototype-call.json', call)
        evidence['images']['prototype']['call'] = ref(self.root / 'prototype-call.json')
        save(self.root / 'art-evidence.json', evidence)
        targets, *_ = snapshot(self.layers, PERSONA, stage='prototype')
        review = json.loads((self.root / 'prototype-review.json').read_text())
        review['targets'] = targets['prototype']
        review['checks'] = {key: {'passed': True, 'observation': 'SYNTHETIC contract assertion only: ' + key}
                            for key in review_checks(design, 'prototype', REVIEW_CHECKS['prototype'])}
        save(self.root / 'prototype-review.json', review)
        evidence['reviews']['prototype'] = ref(self.root / 'prototype-review.json')
        save(self.root / 'art-evidence.json', evidence)

    def update_call(self, change):
        path = self.root / 'prototype-call.json'
        call = json.loads(path.read_text())
        change(call['request'])
        save(path, call)
        evidence = json.loads((self.root / 'art-evidence.json').read_text())
        evidence['images']['prototype']['call'] = ref(path)
        save(self.root / 'art-evidence.json', evidence)

    def test_actual_reference_attachments_are_checked(self):
        report = check_evidence(self.layers, PERSONA, stage='prototype')
        self.assertTrue(report['ok'], report)
        self.assertTrue(any('style-0.png' in key for key in report['inputs_sha256']))

    def test_hash_mentions_without_image_attachments_do_not_pass(self):
        self.update_call(lambda request: request.pop('reference_images'))
        report = check_evidence(self.layers, PERSONA, stage='prototype')
        self.assertFalse(report['ok'])
        self.assertEqual(report['errors'][0]['code'], 'style_reference_missing')

    def test_reference_cannot_be_recorded_as_persona_or_composition(self):
        self.update_call(lambda request: request['reference_images'][0].update(purpose='composition'))
        report = check_evidence(self.layers, PERSONA, stage='prototype')
        self.assertFalse(report['ok'])
        self.assertEqual(report['errors'][0]['code'], 'style_reference_missing')

    def test_replaced_staged_reference_invalidates_the_request(self):
        (self.root / 'style-0.png').write_bytes((self.root / 'prototype.png').read_bytes())
        self.assertFalse(check_evidence(self.layers, PERSONA, stage='prototype')['ok'])

    def test_style_example_cannot_be_delivered_as_new_personal_art(self):
        path = self.root / 'prototype.png'
        shutil.copyfile(self.root / 'style-0.png', path)
        evidence = json.loads((self.root / 'art-evidence.json').read_text())
        evidence['images']['prototype'].update(ref(path))
        save(self.root / 'art-evidence.json', evidence)
        report = check_evidence(self.layers, PERSONA, stage='prototype')
        self.assertFalse(report['ok'])
        self.assertEqual(report['errors'][0]['code'], 'style_reference_reused')


if __name__ == '__main__':
    unittest.main()
