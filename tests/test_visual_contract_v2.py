"""Contract tests only. Synthetic fixtures are not image-model performance claims."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from visual_v2_fixtures import design,images,dossier,save,ref,ROOT,PERSONA
from twinlight_core.visual_contract import *
from twinlight_core.generation_plan import write_plan,register_image,check_capabilities,bind_review,bind_composite,repair_plan
from twinlight_core.art_quality import check_evidence,snapshot

CAPS={'version':'image-capabilities-1','image_generation':True,'reference_images':True,'native_transparency':True,
      'source':'SYNTHETIC capability fixture for unit tests only.','native_canvases':[[600,800],[300,400]]}

class VisualContractTests(unittest.TestCase):
    def test_distinct_versioned_styles_include_collector_default(self):
        styles=catalog();self.assertGreaterEqual(len(styles),5);self.assertEqual(len({s['visual_language'] for s in styles}),len(styles));self.assertEqual(default_style()['id'],DEFAULT_STYLE)
    def test_every_style_resolves(self):
        for s in catalog():self.assertEqual(style_for(s['id'],'1.0.0')['sha256'],s['sha256'])
    def test_default_style_does_not_select_gender_or_subject(self):
        self.assertEqual(json.loads((STYLE_DIR/'catalog.json').read_text())['default_style'],DEFAULT_STYLE)
        self.assertNotIn('subject',default_style());self.assertNotIn('gender',default_style())
    def test_reject_unknown_style(self):
        with self.assertRaises(VisualContractError):style_for('arbitrary-space-gold')
    def test_reject_style_version_drift(self):
        with self.assertRaises(VisualContractError):style_for('paper-craft-story','2.0.0')
    def test_human_female_concrete(self):
        d=design();self.assertIn('女性呈现',subject_prompt(d));self.assertIn('黑色齐耳短发',subject_prompt(d))
    def test_human_male_concrete(self):
        d=design();d['subject']['gender_presentation']='male';self.assertIn('男性呈现',subject_prompt(d))
    def test_neutral_does_not_infer_gender(self):
        d=design();d['subject']['gender_presentation']='unspecified';self.assertIn('不强调性别',subject_prompt(d))
    def test_animal_species_and_sex_are_explicit(self):
        p=subject_prompt(design('animal'));self.assertIn('赤狐',p);self.assertIn('雄性',p)
    def test_object_has_no_assumed_person(self):
        d=design('object');self.assertIn('陶瓷小碗',subject_prompt(d));self.assertIsNone(d['subject']['main_prop'])
    def test_animal_cannot_be_generic_animal(self):
        d=design('animal');d['subject']['species']='动物'
        with self.assertRaises(VisualContractError):validate_design(d)
    def test_human_cannot_be_animal(self):
        d=design();d['subject']['species']='赤狐'
        with self.assertRaises(VisualContractError):validate_design(d)
    def test_object_cannot_have_gender(self):
        d=design('object');d['subject']['gender_presentation']='male'
        with self.assertRaises(VisualContractError):validate_design(d)
    def test_object_cannot_have_extra_prop(self):
        d=design('object');d['subject']['main_prop']='一个电脑'
        with self.assertRaises(VisualContractError):validate_design(d)
    def test_abstract_label_not_appearance(self):
        for word in ('构建','共创','拆解 / 验证 / 迭代'):
            d=design();d['subject']['appearance'][0]['description']=word
            with self.assertRaises(VisualContractError):validate_design(d)
    def test_unresolved_choice_is_rejected(self):
        for text in ('黑发或白发二选一','{{发型}}','TODO hair'):
            d=design();d['subject']['appearance'][0]['description']=text
            with self.assertRaises(VisualContractError):validate_design(d)
    def test_one_prop_not_list(self):
        for prop in ('电脑/吉他','电脑、足球','电脑或者吉他'):
            d=design();d['subject']['main_prop']=prop
            with self.assertRaises(VisualContractError):validate_design(d)
    def test_trait_budget(self):
        d=design();d['subject']['appearance']*=3
        with self.assertRaises(VisualContractError):validate_design(d)
    def test_duplicate_part_rejected(self):
        d=design();d['subject']['appearance'][1]['part']='hair'
        with self.assertRaises(VisualContractError):validate_design(d)
    def test_freeform_keywords_not_allowed(self):
        d=design();d['visual_keywords']=['共创']
        with self.assertRaises(VisualContractError):validate_design(d)
    def test_keywords_derive_only_visible_subject(self):
        d=design();d['selection_reason']='INTERNAL_PRIVATE_PROSE that must not reach the drawing model.'
        d['subject']['selection_basis']='INTERNAL_PRIVATE_BASIS for a synthetic fixture only.'
        self.assertNotIn('INTERNAL_PRIVATE',str(visual_keywords(d)));self.assertNotIn('INTERNAL_PRIVATE',subject_prompt(d))
    def test_background_excludes_subject_and_prop(self):
        d=design();p=visual_brief(d,'background');self.assertNotIn('齐耳',p);self.assertNotIn('纸鹤',p);self.assertNotIn('女性',p)
    def test_effects_exclude_subject_setting(self):
        d=design();p=visual_brief(d,'effects');self.assertNotIn('纸鹤',p);self.assertNotIn('石台',p);self.assertIn('两片',p)
    def test_subject_excludes_whole_scene(self):
        p=visual_brief(design(),'subject');self.assertNotIn('浅灰墙',p);self.assertIn('齐耳',p)
    def test_title_identity_prose_never_compiled(self):
        d=design();p=layer_prompt(d,'prototype',(600,800));self.assertNotIn('系统织星者',p);self.assertNotIn(d['subject']['selection_basis'],p)
    def test_plain_wordless_prototype(self):
        p=layer_prompt(design(),'prototype',(600,800));self.assertIn('600',p);self.assertIn('不要',p);self.assertIn('文字',p)
    def test_no_crop_to_fake_canvas(self):
        with self.assertRaises(VisualContractError):layer_prompt(design(),'prototype',(1024,1536))
    def test_missing_photo_not_a_likeness(self):
        d=design();d['subject']['representation']='user_reference'
        with self.assertRaises(VisualContractError):validate_design(d)
    def test_wrong_persona_rejected(self):
        with self.assertRaises(VisualContractError):validate_design(design(),'b'*64)
    def test_no_mutation_of_subject(self):
        d=design();before=copy.deepcopy(d);layer_prompt(d,'subject',(600,800));self.assertEqual(d,before)
    def test_collector_uses_visible_hashed_style_examples_without_identity(self):
        refs=style_references(default_style());self.assertTrue(refs)
        for ref in refs:
            self.assertEqual(ref['purpose'],'style_only');self.assertEqual(sha256(Path(ref['file'])),ref['sha256'])
        d=design(style=DEFAULT_STYLE)
        self.assertEqual(style_binding(d)['reference_sha256'],[r['sha256'] for r in refs])
        self.assertEqual(d['reference_basis'],'text_only');self.assertFalse(d['reference_consent'])
    def test_collector_all_drawing_roles_keep_quality_and_geometry(self):
        d=design(style=DEFAULT_STYLE)
        for role in ('prototype','background','subject','effects'):
            p=layer_prompt(d,role,(600,800))
            self.assertIn('典藏卡共同几何约束',p);self.assertIn('精绘',p);self.assertIn('style_only',p)
            if role != 'prototype':self.assertIn('composition',p);self.assertIn('不得重新设计',p)
    def test_native_layer_edits_preserve_canvas_and_assign_foreground_once(self):
        d=design(style=DEFAULT_STYLE)
        background=layer_prompt(d,'background',(600,800));subject=layer_prompt(d,'subject',(600,800))
        effects=layer_prompt(d,'effects',(600,800))
        for text in (background,subject,effects):
            self.assertIn('唯一输入 Image1',text);self.assertIn('原生编辑',text)
            self.assertIn('禁止自动紧边裁切',text);self.assertIn('右下角两片',text)
            self.assertNotIn('黑色齐耳短发',text)
        self.assertIn('同时删除',background);self.assertIn('不得重复保留 effects 前景',background)
        self.assertIn('头顶到上缘',subject);self.assertIn('只保留原图中的主体',subject)
        self.assertIn('严格保持每块元素的原位置',effects)
    def test_collector_requires_quality_parity_reviews(self):
        for stage in ('prototype','composite','final'):
            checks=review_checks(design(style=DEFAULT_STYLE),stage,())
            self.assertTrue({'material_finish','spatial_depth','reference_quality_parity'}.issubset(checks))
    def test_collector_cannot_silently_use_compact_text_profile(self):
        d=design(style=DEFAULT_STYLE);d['typography'].pop('layout')
        with self.assertRaises(VisualContractError):validate_design(d)

class PlanTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);self.src=self.root/'sources';images(self.src)
        self.d=self.root/'design.json';save(self.d,design());self.out=self.root/'art'
    def make(self):
        return write_plan(self.d,self.out,canvas=(600,800),capabilities=CAPS)
    def record(self,role='prototype',file=None,ident='one'):
        raw=self.root/(ident+'.txt');raw.write_text('SYNTHETIC response artifact '+ident)
        return register_image(self.out/'generation-plan.json',role,file or self.src/(role+'.png'),raw,tool='SYNTHETIC-TEST-ADAPTER',call_id='TEST-'+ident,artifact_id=ident)
    def test_plan_without_capabilities_is_not_ready(self):
        p=write_plan(self.d,self.out);self.assertFalse(p['ready_for_image_call']);self.assertFalse(p['image_generation_performed'])
    def test_only_prototype_job_initially(self):
        p=self.make();self.assertEqual([j['role'] for j in p['jobs']],['prototype'])
    def test_layers_require_actual_prototype_review(self):
        self.make();self.record()
        with self.assertRaises(VisualContractError):write_plan(self.d,self.out,phase='layers',capabilities=CAPS)
    def test_false_capability_blocks(self):
        c={**CAPS,'native_transparency':False}
        with self.assertRaises(VisualContractError):write_plan(self.d,self.out,canvas=(600,800),capabilities=c)
    def test_unsupported_native_canvas_blocks(self):
        with self.assertRaises(VisualContractError):write_plan(self.d,self.out,canvas=(900,1200),capabilities=CAPS)
    def test_real_bytes_preserved_not_resampled(self):
        self.make();r=self.record();self.assertTrue(r['ok']);self.assertEqual((self.out/'prototype.png').read_bytes(),(self.src/'prototype.png').read_bytes())
        self.assertFalse(r['art_approved']);self.assertFalse(r['generation_provenance_verified'])
    def test_wrong_phase_rejected(self):
        self.make()
        with self.assertRaises(VisualContractError):self.record('subject')
    def test_actual_different_native_prototype_canvas_is_recorded(self):
        self.make();image=self.src/'smaller.png';Image.new('RGB',(300,400)).save(image);r=self.record(file=image)
        self.assertEqual(r['returned_canvas'],[300,400]);self.assertEqual(r['requested_canvas'],[600,800])
    def test_wrong_ratio_preserved_as_failure(self):
        self.make();image=self.src/'bad.png';Image.new('RGB',(1024,1536)).save(image);r=self.record(file=image)
        self.assertFalse(r['ok']);self.assertTrue(r['originals_preserved']);self.assertFalse((self.out/'prototype.png').exists())
    def test_three_attempt_limit(self):
        self.make();image=self.src/'bad.png';Image.new('RGB',(10,10)).save(image)
        for i in range(3):self.assertFalse(self.record(file=image,ident=str(i))['ok'])
        with self.assertRaises(VisualContractError):self.record(file=image,ident='four')
    def test_duplicate_call_not_new_attempt(self):
        self.make();self.record()
        with self.assertRaises(VisualContractError):self.record()
    def test_prompt_mutation_rejected(self):
        self.make();(self.out/'prompts/prototype.txt').write_text('Changed')
        with self.assertRaises(VisualContractError):self.record()
    def test_design_mutation_rejected(self):
        self.make();d=design();d['subject']['expression']='皱眉闭眼';save(self.out/'art-direction.json',d)
        with self.assertRaises(VisualContractError):self.record()
    def test_no_python_drawings_as_image_tool(self):
        self.make();raw=self.root/'raw';raw.write_text('artifact')
        with self.assertRaises(VisualContractError):register_image(self.out/'generation-plan.json','prototype',self.src/'prototype.png',raw,tool='Pillow',call_id='x',artifact_id='artifact')
    def test_record_missing_response_id_rejected(self):
        self.make();raw=self.root/'raw';raw.write_text('different')
        with self.assertRaises(VisualContractError):register_image(self.out/'generation-plan.json','prototype',self.src/'prototype.png',raw,tool='TEST',call_id='x',artifact_id='absent')
    def test_default_style_reference_is_copied_and_passed_as_tool_argument(self):
        save(self.d,design(style=DEFAULT_STYLE));p=self.make();j=p['jobs'][0]
        self.assertTrue(j['reference_images']);self.assertEqual(len(j['reference_images']),len(j['referenced_image_paths']))
        for ref,path in zip(j['reference_images'],j['referenced_image_paths']):
            self.assertEqual(ref['purpose'],'style_only');self.assertEqual(sha256(Path(path)),ref['sha256'])
            self.assertEqual((self.out/ref['file']).resolve(),Path(path));self.assertIn(ref['sha256'],j['reference_sha256'])
        self.record()
        evidence=json.loads((self.out/'art-evidence.json').read_text())
        call=json.loads((self.out/evidence['images']['prototype']['call']['file']).read_text())
        self.assertEqual(call['request']['reference_images'],j['reference_images'])
    def test_missing_default_style_image_cannot_be_registered(self):
        save(self.d,design(style=DEFAULT_STYLE));p=self.make()
        (self.out/p['jobs'][0]['reference_images'][0]['file']).unlink()
        with self.assertRaises(VisualContractError):self.record()
    def test_removed_default_style_binding_cannot_be_registered(self):
        save(self.d,design(style=DEFAULT_STYLE));p=self.make()
        p['jobs'][0]['reference_images']=[];p['jobs'][0]['reference_sha256']=[];save(self.out/'generation-plan.json',p)
        with self.assertRaises(VisualContractError):self.record()
    def test_prompt_only_canvas_records_native_output_without_invented_size_support(self):
        caps={**CAPS,'native_canvases':[],'canvas_selection':'prompt_only'}
        p=write_plan(self.d,self.out,capabilities=caps)
        self.assertTrue(p['ready_for_image_call']);self.assertEqual(p['canvas_policy'],'observe_native_prototype_then_freeze')
        r=self.record();self.assertEqual(r['returned_canvas'],[600,800]);self.assertEqual(r['requested_canvas'],[1080,1440])

class EvidenceV2Tests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)/'art';self.manifest=dossier(self.root)
    def check(self):return check_evidence(self.manifest,PERSONA,front=self.root/'front.png',preview=self.root/'preview.html')
    def test_v2_synthetic_dossier_passes_contract_not_certification(self):
        r=self.check();self.assertTrue(r['ok'],r);self.assertFalse(r['quality_verified']);self.assertFalse(r['generation_provenance_verified'])
    def test_style_change_invalidates_review(self):
        d=json.loads((self.root/'art-direction.json').read_text());d['style']['id']='paper-craft-story';save(self.root/'art-direction.json',d);self.assertFalse(self.check()['ok'])
    def test_missing_specific_subject_review_blocks(self):
        p=self.root/'prototype-review.json';r=json.loads(p.read_text());del r['checks']['concrete_subject'];save(p,r)
        e=json.loads((self.root/'art-evidence.json').read_text());e['reviews']['prototype']=ref(p);save(self.root/'art-evidence.json',e)
        self.assertFalse(self.check()['ok'])
    def test_compile_layers_after_bound_prototype_review(self):
        p=write_plan(self.root/'art-direction.json',self.root,phase='layers',capabilities=CAPS)
        self.assertEqual([j['role'] for j in p['jobs']],['background','subject','effects']);self.assertTrue(p['prototype'])
        for job in p['jobs']:
            self.assertEqual(job['operation'],'image_edit');self.assertEqual(job['edit_base'],p['prototype'])
            self.assertEqual(job['coordinate_policy'],'preserve_full_canvas')
            self.assertEqual(job['reference_images'],[{**p['prototype'],'purpose':'composition'}])
            self.assertEqual(job['referenced_image_paths'],[str((self.root/'prototype.png').resolve())])
            self.assertTrue((self.root/job['prompt']['file']).read_text().startswith('EXPLICIT LAYER OWNERSHIP'))
            self.assertIn('右下角两片',job['ownership_instruction'])
    def test_native_layer_call_binds_current_prototype_edit_intent(self):
        write_plan(self.root/'art-direction.json',self.root,phase='layers',capabilities=CAPS)
        raw=self.root/'returned.txt';raw.write_text('SYNTHETIC returned edit artifact edit-one')
        r=register_image(self.root/'generation-plan.json','subject',self.root/'subject.png',raw,tool='SYNTHETIC-TEST-ADAPTER',call_id='edit1',artifact_id='edit-one')
        self.assertTrue(r['ok'],r)
        e=json.loads((self.root/'art-evidence.json').read_text())
        call=json.loads((self.root/e['images']['subject']['call']['file']).read_text())
        self.assertEqual(call['request']['operation'],'image_edit')
        self.assertEqual(call['request']['edit_base'],ref(self.root/'prototype.png'))
        self.assertEqual(call['request']['coordinate_policy'],'preserve_full_canvas')
        # The source/evidence validator must accept the compiled native-edit brief,
        # not demand the earlier verbose prompt that redesigned the whole scene.
        result=check_evidence(self.manifest,PERSONA,stage='composite')
        self.assertTrue(result['ok'],result)
    def test_layer_edit_rejects_extra_style_reference_before_registering_output(self):
        p=write_plan(self.root/'art-direction.json',self.root,phase='layers',capabilities=CAPS)
        job=p['jobs'][0];job['reference_images'].append({**p['prototype'],'purpose':'style_only'})
        job['reference_sha256'].append(p['prototype']['sha256']);save(self.root/'generation-plan.json',p)
        raw=self.root/'returned.txt';raw.write_text('SYNTHETIC extra reference')
        with self.assertRaises(VisualContractError) as failure:
            register_image(self.root/'generation-plan.json','background',self.root/'background.png',raw,tool='SYNTHETIC-TEST-ADAPTER',call_id='extra',artifact_id='reference')
        self.assertEqual(failure.exception.code,'edit_reference')
    def test_repair_preserves_identity_history_other_layers_and_valid_base_prompt(self):
        plan=write_plan(self.root/'art-direction.json',self.root,phase='layers',capabilities=CAPS)
        e=json.loads((self.root/'art-evidence.json').read_text())
        e['attempts']=[{'role':'subject','key':'TEST-rejected-1','status':'rejected'},
                       {'role':'subject','key':'TEST-rejected-2','status':'rejected'}]
        save(self.root/'art-evidence.json',e);evidence_before=(self.root/'art-evidence.json').read_bytes()
        instruction='Observed retained foreground: remove both right-corner leaves entirely; preserve the shirt, hands and paper crane at their original positions.'
        result=repair_plan(self.root/'generation-plan.json','subject',instruction)
        self.assertEqual(result['attempts_used'],2);self.assertEqual(result['attempts_remaining'],1)
        current=json.loads((self.root/'generation-plan.json').read_text())
        for key in ('persona_digest','design','style_binding','prototype','canvas'):
            self.assertEqual(current[key],plan[key])
        self.assertEqual((self.root/'art-evidence.json').read_bytes(),evidence_before)
        self.assertEqual(current['jobs'][0],plan['jobs'][0]);self.assertEqual(current['jobs'][2],plan['jobs'][2])
        subject=current['jobs'][1];text=(self.root/subject['prompt']['file']).read_text()
        self.assertTrue(text.startswith('LATEST OBSERVED FAILURE'));self.assertIn(instruction,text)
        self.assertIn(layer_prompt(design(),'subject',(600,800)),text)
        self.assertNotEqual(subject['prompt']['sha256'],plan['jobs'][1]['prompt']['sha256'])
        raw=self.root/'repair-return.txt';raw.write_text('SYNTHETIC third artifact repair-final')
        r=register_image(self.root/'generation-plan.json','subject',self.root/'subject.png',raw,tool='SYNTHETIC-TEST-ADAPTER',call_id='repair3',artifact_id='repair-final')
        self.assertTrue(r['ok'],r)
        e=json.loads((self.root/'art-evidence.json').read_text())
        call=json.loads((self.root/e['images']['subject']['call']['file']).read_text())
        self.assertEqual(call['request']['repair_instruction'],instruction)
        snapshot(self.manifest,PERSONA,stage='composite')
        with self.assertRaises(VisualContractError) as failure:
            repair_plan(self.root/'generation-plan.json','subject',instruction)
        self.assertEqual(failure.exception.code,'retry_limit')
    def test_repair_rejects_prompt_tampering_and_wrong_phase(self):
        plan=write_plan(self.root/'art-direction.json',self.root,phase='layers',capabilities=CAPS)
        prompt=self.root/plan['jobs'][1]['prompt']['file'];prompt.write_text('Unregistered prompt mutation')
        with self.assertRaises(VisualContractError) as failure:
            repair_plan(self.root/'generation-plan.json','subject','Remove only the retained foreground objects.')
        self.assertEqual(failure.exception.code,'prompt_changed')
        with self.assertRaises(VisualContractError) as failure:
            repair_plan(self.root/'generation-plan.json','prototype','This must never turn a layer repair into a new prototype.')
        self.assertEqual(failure.exception.code,'repair_phase')
    def test_repair_requires_bounded_actual_feedback(self):
        write_plan(self.root/'art-direction.json',self.root,phase='layers',capabilities=CAPS)
        for bad in ('', 'fix', 'x'*2501, 'remove\x00foreground'):
            with self.assertRaises(VisualContractError) as failure:
                repair_plan(self.root/'generation-plan.json','subject',bad)
            self.assertEqual(failure.exception.code,'repair_instruction')
    def test_composite_binding_rejects_lettered_front(self):
        with self.assertRaises(VisualContractError):bind_composite(self.manifest,self.root/'front.png')
    def test_composite_binding_matches_actual_pixels(self):
        r=bind_composite(self.manifest,self.root/'composite.png');self.assertTrue(r['ok']);self.assertFalse(r['reviewed'])
    def test_pending_review_cannot_be_bound(self):
        p=self.root/'prototype-review.json';r=json.loads(p.read_text());r['decision']='pending';save(p,r)
        with self.assertRaises(ValueError):bind_review(self.manifest,p)
    def test_final_review_requires_specific_actual_front(self):
        r=bind_review(self.manifest,self.root/'final-review.json',front=self.root/'front.png',preview=self.root/'preview.html');self.assertTrue(r['ok'],r)

if __name__=='__main__':unittest.main()
