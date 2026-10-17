"""SYNTHETIC task/return/accounting regressions; no real provider or art approval."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from quality_fixtures import ROOT
from image_task_fixtures import start,accepted,native,layers,generation,capabilities,reserve,picture,TOOL,NOTE
from split_fixtures import person
from twinlight_core import portable,portable_images as jobs,style_selection
from twinlight_core.common import load,save,digest
from twinlight_core.card_context import render_prompt
from twinlight_core.portable_layers import record_attempt,prepare_assisted,sha
from prepare_card_layers import font_path


class ImageTaskTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);self.w=self.root/'work'
        self.src=start(self.w)
    def plan(self):return jobs.next_task(self.w,load(self.w/'capabilities.json'))
    def result(self,task,reserved,**extra):
        p=Path(reserved['output_directory'])/'return.png';picture(p,task['role'],tuple(task['canvas']))
        return {'task_id':task['task_id'],'outcome':'success','disposition':'accepted','reason':NOTE,
                'review_method':'self','output':p.relative_to(self.w).as_posix()}|extra
    def test_new_full_has_tracked_contract(self):
        self.assertEqual(load(self.w/'portable-state.json')['image_task_contract'],jobs.CONTRACT)
    def test_run_exposes_only_one_prototype_task(self):
        r=portable.run(self.src,self.w,capabilities());self.assertEqual(r['image_task']['role'],'prototype')
        self.assertEqual(r['image_calls_performed_by_cli'],0);self.assertFalse((self.w/jobs.LEDGER).exists())
    def test_repeated_plans_do_not_reserve(self):
        a=self.plan();b=self.plan();self.assertEqual(a,b);self.assertFalse((self.w/jobs.LEDGER).exists())
    def test_reservation_counts_before_actual_call(self):
        task,r=reserve(self.w);ledger=load(self.w/jobs.LEDGER)
        self.assertEqual(len(ledger['attempts']),1);self.assertNotIn('result',ledger['attempts'][0])
        self.assertEqual(r['image_calls_performed_by_cli'],0);self.assertEqual(task['number'],1)
    def test_pending_does_not_issue_a_second_call(self):
        task,r=reserve(self.w);before=(self.w/jobs.LEDGER).read_bytes()
        self.assertEqual(self.plan()['status'],'awaiting_image_result')
        with self.assertRaises(ValueError):jobs.reserve(self.w,task['task_id'],TOOL)
        self.assertEqual(before,(self.w/jobs.LEDGER).read_bytes())
    def test_stale_task_id_rejected(self):
        with self.assertRaises(ValueError):jobs.reserve(self.w,'not-this-task',TOOL)
        self.assertFalse((self.w/jobs.LEDGER).exists())
    def test_result_without_reservation_rejected(self):
        with self.assertRaises(ValueError):jobs.record(self.w,{'task_id':'unknown','outcome':'failure','disposition':'discarded','reason':NOTE})
    def test_result_replay_rejected(self):
        task,r=reserve(self.w);v=self.result(task,r);jobs.record(self.w,v)
        with self.assertRaises(ValueError):jobs.record(self.w,v)
    def test_payload_uses_unchanged_short_compiler(self):
        task,r=reserve(self.w);v=load(Path(r['drawing_payload']));drawing=load(self.w/'card-image-input.json')
        self.assertEqual(v['prompt_text'],render_prompt(drawing,'prototype',(600,800)))
        for key in ('task_id','reason','persona_digest','input_sha256','tool','scope'):self.assertNotIn(key,v)
        self.assertNotIn(person()['name'],v['prompt_text']);self.assertEqual(v['reference_images'],[])
    def test_only_selected_style_references_are_used(self):
        w=self.root/'collector';start(w,style='twinlight-collector');task,r=reserve(w);v=load(Path(r['drawing_payload']))
        selected=style_selection.selection_status(w)['style_reference_images']
        self.assertEqual(v['reference_images'],[x['file'] for x in selected])
    def test_layer_edit_binds_exact_frozen_prototype(self):
        prototype=accepted(self.w);task,r=reserve(self.w);v=load(Path(r['drawing_payload']))
        self.assertEqual(task['role'],'background');self.assertEqual(v['operation'],'image_edit')
        self.assertEqual(v['reference_images'],[str(prototype)])
        self.assertEqual(load(self.w/jobs.LEDGER)['attempts'][-1]['request']['prototype_sha256'],sha(prototype))
    def test_prototype_compatible_actual_canvas_is_frozen(self):
        task,r=reserve(self.w);v=self.result(task,r);picture(self.w/v['output'],'prototype',(768,1024))
        jobs.record(self.w,v);self.assertEqual(self.plan()['canvas'],[768,1024])
    def test_layer_canvas_mismatch_cannot_be_accepted(self):
        accepted(self.w);task,r=reserve(self.w);v=self.result(task,r);picture(self.w/v['output'],'background',(768,1024))
        with self.assertRaises(ValueError):jobs.record(self.w,v)
        v['disposition']='discarded';jobs.record(self.w,v);self.assertEqual(self.plan()['number'],2)
    def test_transparent_layer_must_have_actual_alpha(self):
        accepted(self.w);accepted(self.w);task,r=reserve(self.w);v=self.result(task,r)
        Image.new('RGB',(600,800),'red').save(self.w/v['output'])
        with self.assertRaises(ValueError):jobs.record(self.w,v)
    def test_nonimage_bytes_cannot_be_recorded_as_art(self):
        task,r=reserve(self.w);v=self.result(task,r);(self.w/v['output']).write_bytes(b'not a PNG')
        with self.assertRaises((ValueError,OSError)):jobs.record(self.w,v)
    def test_corrupt_return_can_be_preserved_as_technical_failure(self):
        task,r=reserve(self.w);v=self.result(task,r,outcome='failure',disposition='discarded');v.pop('review_method')
        (self.w/v['output']).write_bytes(b'SYNTHETIC corrupt image return')
        jobs.record(self.w,v);self.assertEqual(self.plan()['number'],2)
        entry=load(self.w/jobs.LEDGER)['attempts'][0]['result']['outputs'][0]
        self.assertFalse(entry['readable_image']);self.assertIsNone(entry['canvas'])
        m,g=native(self.w);report=jobs.audit(self.w,m,g)
        self.assertEqual((report['returned_files'],report['returned_images'],report['unreadable_returns']),(5,4,1))
    def test_context_boundary_cannot_be_upgraded_in_generation_record(self):
        m,g=native(self.w);x=load(self.w/'generation.json');x['context_isolation']='explicit_narrow_task';save(self.w/'generation.json',x)
        with self.assertRaises(ValueError):jobs.audit(self.w,m,portable.generation_check(self.w/'generation.json',m))
    def test_changed_return_revokes_binding(self):
        p=accepted(self.w);p.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.plan()
    def test_changed_payload_is_rejected(self):
        task,r=reserve(self.w);p=Path(r['drawing_payload']);v=load(p);v['prompt_text']='Unplanned second scene';save(p,v)
        with self.assertRaises(ValueError):self.plan()
    def test_changed_payload_rehashed_still_fails_compiler_check(self):
        task,r=reserve(self.w);p=Path(r['drawing_payload']);v=load(p);v['prompt_text']='Unplanned second scene';save(p,v)
        ledger=load(self.w/jobs.LEDGER);a=ledger['attempts'][0];a['request']['drawing_file_sha256']=sha(p)
        a['request_sha256']=digest(a['request']);jobs._save(self.w,ledger)
        with self.assertRaises(ValueError):self.plan()
    def test_changed_content_blocks_new_call(self):
        p=person();p['name']='另一位测试角色';save(self.src,p)
        with self.assertRaises(ValueError):self.plan()
    def test_success_without_bytes_is_not_success(self):
        task,r=reserve(self.w)
        with self.assertRaises(ValueError):jobs.record(self.w,{'task_id':task['task_id'],'outcome':'success','disposition':'accepted','reason':NOTE})
    def test_wrong_scene_is_discarded_and_stops_native_chain(self):
        accepted(self.w);task,r=reserve(self.w);v=self.result(task,r,outcome='reference_mismatch',disposition='discarded')
        jobs.record(self.w,v);n=self.plan();self.assertEqual(n['status'],'assisted_layers_required')
        with self.assertRaises(ValueError):jobs.reserve(self.w,task['task_id'],TOOL)
        self.assertEqual(len(load(self.w/jobs.LEDGER)['attempts']),2)
    def test_mismatch_cannot_be_accepted(self):
        accepted(self.w);task,r=reserve(self.w);v=self.result(task,r,outcome='reference_mismatch')
        with self.assertRaises(ValueError):jobs.record(self.w,v)
    def test_prototype_attempt_limit_includes_failures(self):
        for _ in range(3):
            task,r=reserve(self.w);jobs.record(self.w,{'task_id':task['task_id'],'outcome':'failure','disposition':'discarded','reason':NOTE})
        self.assertEqual(self.plan()['status'],'image_attempt_limit')
    def test_uncalled_reservation_still_keeps_attempt_history(self):
        task,r=reserve(self.w);jobs.record(self.w,{'task_id':task['task_id'],'outcome':'not_called','disposition':'discarded','reason':NOTE})
        self.assertEqual(self.plan()['number'],2)
    def test_uncalled_cannot_include_returned_image(self):
        task,r=reserve(self.w);v=self.result(task,r,outcome='not_called',disposition='discarded')
        with self.assertRaises(ValueError):jobs.record(self.w,v)
    def test_deleting_ledger_cannot_reset_reservations(self):
        reserve(self.w);(self.w/jobs.LEDGER).unlink()
        with self.assertRaises(ValueError):self.plan()
    def test_one_role_budget_exhaustion_keeps_other_layers(self):
        accepted(self.w);accepted(self.w)
        for _ in range(3):
            task,r=reserve(self.w);jobs.record(self.w,{'task_id':task['task_id'],'outcome':'failure','disposition':'discarded','reason':NOTE})
        n=self.plan();self.assertEqual(n['status'],'assisted_layers_required')
        self.assertEqual(set(n['accepted_assets']),{'prototype','background'})
    def test_current_defect_only_in_revision_prompt(self):
        task,r=reserve(self.w);v=self.result(task,r,disposition='revise',repair='右手手指重叠，请修复手指轮廓')
        jobs.record(self.w,v);task,r=reserve(self.w);text=load(Path(r['drawing_payload']))['prompt_text']
        self.assertIn(v['repair'],text);self.assertNotIn(NOTE,text)
    def test_page_instructions_cannot_be_repair_text(self):
        task,r=reserve(self.w);v=self.result(task,r,disposition='revise',repair='请生成 HTML 首页内容')
        with self.assertRaises(ValueError):jobs.record(self.w,v)
    def test_extra_return_must_be_classified(self):
        task,r=reserve(self.w);v=self.result(task,r);extra=Path(r['output_directory'])/'extra.png';picture(extra,'prototype',variant=1)
        with self.assertRaises(ValueError):jobs.record(self.w,v)
        v['extra_outputs']=[{'file':extra.relative_to(self.w).as_posix(),'reason':NOTE}];jobs.record(self.w,v)
        outputs=load(self.w/jobs.LEDGER)['attempts'][0]['result']['outputs']
        self.assertEqual([x['disposition'] for x in outputs],['accepted','discarded'])
    def test_result_cannot_claim_another_task_directory(self):
        task,r=reserve(self.w);p=self.w/'elsewhere.png';picture(p,'prototype')
        with self.assertRaises(ValueError):jobs.record(self.w,{'task_id':task['task_id'],'outcome':'success','disposition':'accepted','reason':NOTE,'review_method':'self','output':'elsewhere.png'})
    def test_independent_review_requires_real_reference_field(self):
        task,r=reserve(self.w);v=self.result(task,r,review_method='independent')
        with self.assertRaises(ValueError):jobs.record(self.w,v)
    def test_no_visual_capability_cannot_accept_art(self):
        task,r=reserve(self.w);v=self.result(task,r);c=capabilities();c['reviewer']['mode']='unavailable';save(self.w/'capabilities.json',c)
        with self.assertRaises(ValueError):jobs.record(self.w,v)
    def test_missing_edit_capability_routes_assisted_not_cardless(self):
        accepted(self.w);c=capabilities();c['image_edit']['reference_binding']='unavailable';save(self.w/'capabilities.json',c)
        self.assertEqual(self.plan()['status'],'assisted_layers_required');self.assertEqual(load(self.w/'portable-state.json')['mode'],'full')
    def test_unknown_edit_capability_allows_one_bound_trial(self):
        accepted(self.w);c=capabilities();c.pop('image_edit');save(self.w/'capabilities.json',c)
        self.assertEqual(self.plan()['role'],'background');task,r=reserve(self.w)
        self.assertTrue(load(Path(r['drawing_payload']))['reference_images'])
    def test_old_after_call_command_cannot_bypass_reservation(self):
        p=accepted(self.w)
        with self.assertRaises(ValueError):record_attempt(self.w,'background','success',NOTE,p,p)
    def test_symlink_return_is_rejected(self):
        task,r=reserve(self.w);external=self.root/'external.png';picture(external,'prototype')
        p=Path(r['output_directory'])/'return.png';p.symlink_to(external)
        with self.assertRaises(ValueError):jobs.record(self.w,{'task_id':task['task_id'],'outcome':'success','disposition':'accepted','reason':NOTE,'review_method':'self','output':p.relative_to(self.w).as_posix()})
    def test_layer_payload_contains_no_second_style_references(self):
        accepted(self.w);accepted(self.w);task,r=reserve(self.w);v=load(Path(r['drawing_payload']))
        self.assertEqual(task['role'],'subject');self.assertEqual(len(v['reference_images']),1);self.assertTrue(v['transparent'])
    def test_all_native_roles_finish_without_new_prototype(self):
        m,g=native(self.w);n=self.plan();self.assertEqual(n['status'],'assemble_layers')
        self.assertEqual([a['request']['role'] for a in load(self.w/jobs.LEDGER)['attempts']],list(jobs.ROLES))
        self.assertTrue(jobs.audit(self.w,m,g)['ok'])
    def test_accepted_prototype_cannot_be_withdrawn(self):
        accepted(self.w)
        with self.assertRaises(ValueError):jobs.withdraw(self.w,'prototype','SYNTHETIC change request for accepted prototype')
    def test_one_layer_repair_reuses_others_and_preserves_budget(self):
        m,g=native(self.w);before=jobs._accepted(jobs._read(self.w)[1]);save(self.w/'review-card.json',{'SYNTHETIC':'old'})
        jobs.withdraw(self.w,'subject','SYNTHETIC subject silhouette edge is visibly broken')
        n=self.plan();self.assertEqual((n['role'],n['number']),('subject',2));self.assertFalse((self.w/'review-card.json').exists())
        self.assertTrue(list((self.w/'card-task/image-review-history').glob('*.json')))
        accepted(self.w,variant=1);after=jobs._accepted(jobs._read(self.w)[1])
        for role in ('prototype','background','effects'):self.assertEqual(before[role],after[role])
        m=layers(self.w);r=jobs.audit(self.w,m,generation(self.w,m));self.assertEqual(r['unused_images'],1)
    def test_reuse_of_prior_return_not_counted_as_new_accepted_call(self):
        p=accepted(self.w);task,r=reserve(self.w);v=self.result(task,r);shutil.copyfile(p,self.w/v['output'])
        with self.assertRaises(ValueError):jobs.record(self.w,v)
    def test_close_prevents_image_calls_from_task_b(self):
        m,g=native(self.w);jobs.audit(self.w,m,g,close=True)
        self.assertEqual(self.plan()['status'],'image_tasks_closed')
        with self.assertRaises(ValueError):jobs.reserve(self.w,'any',TOOL)
        with self.assertRaises(ValueError):jobs.withdraw(self.w,'subject','SYNTHETIC later defect must not restart image generation')
    def test_pending_return_blocks_accounting(self):
        m,g=native(self.w);jobs.withdraw(self.w,'effects','SYNTHETIC effects have an incorrect cutout edge');reserve(self.w)
        with self.assertRaises(ValueError):jobs.audit(self.w,m,g)
    def test_unknown_return_file_blocks_accounting(self):
        m,g=native(self.w);picture(self.w/jobs.OUTPUTS/'untracked.png','prototype',variant=1)
        with self.assertRaises(ValueError):jobs.audit(self.w,m,g)
    def test_changed_final_layer_cannot_pass_accounting(self):
        m,g=native(self.w);picture(m.parent/'subject.png','subject',variant=1)
        g=generation(self.w,m)
        with self.assertRaises(ValueError):jobs.audit(self.w,m,g)
    def test_tool_name_cannot_change_in_generation_record(self):
        m,g=native(self.w);x=load(self.w/'generation.json');x['tool']='another tool';save(self.w/'generation.json',x)
        with self.assertRaises(ValueError):jobs.audit(self.w,m,portable.generation_check(self.w/'generation.json',m))
    def test_unused_image_is_accounted_not_forced_into_layers(self):
        task,r=reserve(self.w);v=self.result(task,r,disposition='discarded');jobs.record(self.w,v)
        accepted(self.w,variant=1)
        for _ in range(3):accepted(self.w)
        m=layers(self.w);r=jobs.audit(self.w,m,generation(self.w,m))
        self.assertEqual((r['returned_images'],r['used_images'],r['unused_images']),(5,4,1))
        self.assertEqual(load(self.w/'image-usage.json')['items'][0]['usage'],'not_used')
    def test_audit_returns_only_nonprivate_totals(self):
        m,g=native(self.w);r=jobs.audit(self.w,m,g)
        self.assertNotIn('items',r);self.assertNotIn(str(self.w),json.dumps(r));self.assertNotIn(NOTE,json.dumps(r))
    def test_cli_reserve_and_record_preserve_task(self):
        task=self.plan();cmd=[sys.executable,str(ROOT/'scripts/portable.py')]
        r=subprocess.run(cmd+['reserve-image','--workspace',str(self.w),'--task-id',task['task_id'],'--tool',TOOL],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr);reserved=json.loads(r.stdout);v=self.result(task,reserved)
        path=self.root/'result.json';save(path,v)
        r=subprocess.run(cmd+['record-image-result',str(path),'--workspace',str(self.w)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(self.plan()['role'],'background')
    def test_cli_layers_plan_uses_new_mismatch_history(self):
        accepted(self.w);task,r=reserve(self.w);v=self.result(task,r,outcome='reference_mismatch',disposition='discarded');jobs.record(self.w,v)
        r=subprocess.run([sys.executable,str(ROOT/'scripts/portable.py'),'layers-plan','--workspace',str(self.w),'--capabilities',str(self.w/'capabilities.json')],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(json.loads(r.stdout)['method'],'assisted_layers')
    def test_tracked_full_cannot_assemble_unregistered_native_assets(self):
        from split_fixtures import native as untracked
        from twinlight_core.lite import persona_digest
        m=untracked(self.w/'old-assets',persona_digest(person()))
        with patch.object(portable,'generation_check',return_value={'SYNTHETIC':True}),self.assertRaises(ValueError):
            portable.run(self.src,self.w,capabilities(),layers=m)
        self.assertFalse((self.w/'site-task').exists())
    def test_assisted_processing_uses_same_registered_prototype(self):
        p=accepted(self.w);c=capabilities();c['image_edit']['reference_binding']='unavailable';save(self.w/'capabilities.json',c)
        bg=self.w/'clean-background.png';picture(bg,'background');sm=self.w/'subject-mask.png';fm=self.w/'effects-mask.png'
        from PIL import ImageDraw
        for path,box in ((sm,(180,96,420,600)),(fm,(468,544,522,616))):
            im=Image.new('L',(600,800));ImageDraw.Draw(im).ellipse(box,fill=255);im.save(path)
        out=self.w/'assisted';prepare_assisted(person(),p,bg,out,font_path(None),subject_mask=sm,effects_mask=fm)
        m=out/'layers.json';r=jobs.audit(self.w,m,generation(self.w,m,'assisted_layers'))
        self.assertEqual(r['observed_calls'],1);self.assertTrue(r['ok'])
    def test_real_file_assembly_and_delivery_never_reserve_more_images(self):
        m,g=native(self.w)
        with patch.object(jobs,'reserve',side_effect=AssertionError('Task B cannot generate')):
            r=portable.run(self.src,self.w,capabilities(),layers=m);self.assertEqual(r['status'],'review_required')
            save(self.w/'review-card.json',{'stage':'card','target_sha256':r['card_review']['target_sha256'],'method':'self','verdict':'accept',
                 'checks':{k:True for k in portable.CHECKS['card']},'observations':NOTE})
            r=portable.run(self.src,self.w,capabilities());self.assertEqual(r['site_review']['status'],'review_required')
            save(self.w/'review-site.json',{'stage':'site','target_sha256':r['html_sha256'],'method':'self','verdict':'accept',
                 'checks':{k:True for k in portable.CHECKS['site']},'observations':NOTE})
            r=portable.run(self.src,self.w,capabilities());self.assertTrue(r['complete']);self.assertFalse(r['all_checks_passed'])
            d=portable.deliver(self.w,self.root/'delivery')
        self.assertEqual(len(load(self.w/jobs.LEDGER)['attempts']),4)
        self.assertEqual(load(self.root/'delivery/delivery.json')['image_accounting']['returned_images'],4)
        import zipfile
        with zipfile.ZipFile(d['zip']) as z:
            for forbidden in ('image-tasks','image-usage','image-outputs','drawing.json','generation.json'):
                self.assertFalse(any(forbidden in name for name in z.namelist()))
        picture(self.w/jobs.OUTPUTS/'orphan.png','prototype',variant=1)
        with self.assertRaises(ValueError):portable.deliver(self.w,self.root/'invalid-delivery')
        self.assertFalse((self.root/'invalid-delivery').exists())


class ImageRouteBoundaryTests(unittest.TestCase):
    def test_no_card_does_not_create_or_call_image_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'person.json';save(src,person());w=root/'work';c=capabilities();c['image']['status']='unavailable';c['image']['reason']=NOTE
            with patch.object(jobs,'next_task',side_effect=AssertionError('No image plan for no-card')):
                r=portable.run(src,w,c)
            self.assertEqual(r['mode'],'html-only');self.assertNotIn('image_task_contract',load(w/'portable-state.json'))
            self.assertFalse((w/jobs.LEDGER).exists());self.assertFalse((w/'card-task').exists())
    def test_old_state_is_not_retroactively_given_reservations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);w=root/'work';src=start(w);s=load(w/'portable-state.json');s.pop('image_task_contract');s['version']='v10-portable-1.2.1';save(w/'portable-state.json',s)
            r=portable.run(src,w,capabilities());self.assertEqual(r['image_accounting']['status'],'legacy_untracked')
            self.assertNotIn('image_task_contract',load(w/'portable-state.json'));self.assertFalse((w/jobs.LEDGER).exists())
            with self.assertRaises(ValueError):jobs.reserve(w,'fake',TOOL)
    def test_unknown_contract_is_not_silently_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp)/'w';src=start(w);s=load(w/'portable-state.json');s['image_task_contract']='unknown-version';save(w/'portable-state.json',s)
            with self.assertRaises(ValueError):portable.run(src,w,capabilities())

if __name__=='__main__':unittest.main()
