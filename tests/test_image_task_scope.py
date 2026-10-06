"""Compiled image handoffs, not image-model quality or browser execution claims."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from visual_v2_fixtures import design, dossier, images, save
from twinlight_core.generation_plan import register_image, repair_plan, write_plan
from twinlight_core.visual_contract import VisualContractError, sha256, style_for, style_references


CAPS = {'version':'image-capabilities-1','image_generation':True,'reference_images':True,
        'native_transparency':True,'native_canvases':[[600,800]],
        'source':'Synthetic compiler fixture; no real image provider was invoked.'}


class ImageTaskScopeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    def compile(self, content, name='card'):
        out = self.root / name
        out.mkdir(exist_ok=True)
        source = out / 'design.json'
        save(source, content)
        plan = write_plan(source, out, canvas=(600,800), capabilities=CAPS)
        job = plan['jobs'][0]
        prompt = out / job['prompt']['file']
        self.assertEqual(job['prompt']['sha256'], sha256(prompt))
        return out, plan, prompt.read_text(encoding='utf-8')

    def test_compiled_prototype_is_one_scene_before_style_and_product_context(self):
        for kind, style_id in (('human','twinlight-collector'), ('animal','forest-fantasy'),
                               ('object','eastern-fantasy-scroll')):
            with self.subTest(kind=kind, style=style_id):
                content = design(kind, style_id)
                original = copy.deepcopy(content)
                out, plan, prompt = self.compile(content, kind)
                self.assertEqual(content, original)
                self.assertEqual(len(plan['jobs']), 1)
                job = plan['jobs'][0]
                self.assertEqual(job['operation'], 'image_generation')
                self.assertFalse(job['transparent'])
                self.assertIsNone(job['edit_base'])
                self.assertEqual(job['requested_canvas'], [600,800])
                self.assertEqual(job['task_scope']['output_count'], 1)
                self.assertEqual(job['task_scope']['artifact_kind'], 'single_scene_illustration')
                self.assertEqual(job['task_scope']['role'], 'prototype')
                self.assertEqual(job['task_scope']['host_renderer_only'],
                                 ['website_ui','card_frame','typography','foil_animation'])
                # The provider's actual hashed prompt establishes its deliverable,
                # dimensions and current subject before the longer style brief.
                front = prompt.split('固定画风：', 1)[0]
                for value in ('连续场景插画', '600×800', content['subject']['species'],
                              content['subject']['pose'], '宿主程序组装'):
                    self.assertIn(value, front)
                style = style_for(style_id)
                for field in ('visual_language','materials_and_light','palette'):
                    self.assertIn(style[field], prompt)
                for trait in content['subject']['appearance']:
                    self.assertIn(trait['description'], prompt)
                self.assertIn(content['scene']['setting'], prompt)
                self.assertEqual(json.loads((out/'art-direction.json').read_text()), original)

    def test_product_and_personal_reasoning_do_not_enter_provider_prompt(self):
        content = design()
        content['selection_reason'] = 'HOST_ONLY: deliver HTML and a complete interactive website in this turn.'
        content['subject']['selection_basis'] = 'PERSON_ONLY: a long private biography belongs to the host.'
        content['preferences']['basis'] = 'HOST_REASON_ONLY: why the complete product should render in chat.'
        _, _, prompt = self.compile(content)
        for value in (content['selection_reason'], content['subject']['selection_basis'],
                      content['preferences']['basis'], content['persona_digest']):
            self.assertNotIn(value, prompt)

    def test_prototype_references_keep_style_and_user_purposes_with_actual_bytes(self):
        content = design(style='twinlight-collector')
        out = self.root/'card'
        images(out)
        supplied = out/'prototype.png'
        content['references'] = [{'file':supplied.name,'sha256':sha256(supplied)}]
        content['reference_basis'] = 'visible_images'
        content['reference_consent'] = True
        content['subject']['representation'] = 'user_reference'
        _, plan, _ = self.compile(content)
        job = plan['jobs'][0]
        expected_style = {r['sha256'] for r in style_references(style_for('twinlight-collector'))}
        self.assertEqual({r['sha256'] for r in job['reference_images'] if r['purpose']=='style_only'}, expected_style)
        self.assertEqual([r for r in job['reference_images'] if r['purpose']=='user_reference'],
                         [{**content['references'][0], 'purpose':'user_reference'}])
        self.assertEqual(len(job['reference_images']), len(job['referenced_image_paths']))
        for ref, actual in zip(job['reference_images'], job['referenced_image_paths']):
            self.assertEqual(Path(actual), out/ref['file'])
            self.assertEqual(sha256(Path(actual)), ref['sha256'])

    def test_native_layer_tasks_have_one_composition_input_and_distinct_alpha(self):
        out = self.root/'layers'
        dossier(out)
        plan = write_plan(out/'art-direction.json', out, phase='layers', capabilities=CAPS)
        self.assertEqual([j['role'] for j in plan['jobs']], ['background','subject','effects'])
        for job in plan['jobs']:
            with self.subTest(role=job['role']):
                self.assertEqual(job['task_scope']['artifact_kind'], 'native_layer')
                self.assertEqual(job['task_scope']['output_count'], 1)
                self.assertEqual(job['task_scope']['role'], job['role'])
                self.assertEqual(job['operation'], 'image_edit')
                self.assertEqual(job['edit_base'], plan['prototype'])
                self.assertEqual(job['coordinate_policy'], 'preserve_full_canvas')
                self.assertEqual(job['requested_canvas'], [600,800])
                self.assertEqual(job['reference_images'], [{**plan['prototype'],'purpose':'composition'}])
                self.assertEqual(job['referenced_image_paths'], [str(out/'prototype.png')])
                self.assertEqual(job['transparent'], job['role'] in ('subject','effects'))
                prompt = (out/job['prompt']['file']).read_text()
                self.assertIn(job['ownership_instruction'], prompt)
                self.assertIn('600×800', prompt)
                self.assertIn('Image1', prompt)

    def test_record_keeps_scoped_request_without_claiming_visual_approval(self):
        out, plan, _ = self.compile(design())
        source = self.root/'native-return'
        images(source)
        raw = source/'response.txt'
        raw.write_text('SYNTHETIC TEST ONLY artifact synthetic-prototype')
        result = register_image(out/'generation-plan.json', 'prototype', source/'prototype.png', raw,
                                tool='SYNTHETIC-TEST-ADAPTER', call_id='synthetic-call', artifact_id='synthetic-prototype')
        self.assertTrue(result['ok'], result)
        self.assertFalse(result['art_approved'])
        self.assertFalse(result['generation_provenance_verified'])
        evidence = json.loads((out/'art-evidence.json').read_text())
        call = json.loads((out/evidence['images']['prototype']['call']['file']).read_text())
        self.assertEqual(call['request']['task_scope'], plan['jobs'][0]['task_scope'])
        self.assertEqual(call['request']['reference_images'], plan['jobs'][0]['reference_images'])
        frozen_prompt = out/call['request']['prompt']['file']
        self.assertEqual(sha256(frozen_prompt), plan['jobs'][0]['prompt']['sha256'])

    def test_changed_output_scope_cannot_register_as_the_compiled_image_job(self):
        out, plan, _ = self.compile(design())
        plan['jobs'][0]['task_scope']['artifact_kind'] = 'website_mockup'
        save(out/'generation-plan.json', plan)
        with self.assertRaises(VisualContractError) as failure:
            register_image(out/'generation-plan.json', 'prototype', out/'absent.png', out/'absent-response.txt',
                           tool='SYNTHETIC-TEST-ADAPTER', call_id='not-called', artifact_id='not-produced')
        self.assertEqual(failure.exception.code, 'image_task_scope')
        self.assertFalse((out/'art-evidence.json').exists())

    def test_local_repair_preserves_scope_and_native_edit_inputs(self):
        out = self.root/'layers'
        dossier(out)
        before = write_plan(out/'art-direction.json', out, phase='layers', capabilities=CAPS)
        repair_plan(out/'generation-plan.json', 'subject',
                    'Remove the retained right-corner leaves; keep the hands and paper crane at their existing coordinates.')
        after = json.loads((out/'generation-plan.json').read_text())
        for old, new in zip(before['jobs'], after['jobs']):
            for field in ('task_scope','operation','reference_images','edit_base','requested_canvas','coordinate_policy'):
                self.assertEqual(old[field], new[field])
            if old['role'] != 'subject':
                self.assertEqual(old, new)


if __name__ == '__main__':
    unittest.main()
