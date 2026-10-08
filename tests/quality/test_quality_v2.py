"""SYNTHETIC contracts/regressions only; these tests do not approve any real card."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from quality_fixtures import ROOT,PERSONA,host,save,ref,sign,release,design
from PIL import Image
from twinlight_core.host_contract import template,assess,load_assessment,IMAGE_FLAGS,REVIEW_FLAGS
from twinlight_core.generation_plan import write_plan,repair_plan,register_image,check_capabilities,bind_review
from twinlight_core.image_dispatch import dispatch,verify_dispatch,consume_dispatch,check_recorded_dispatch
from twinlight_core.independent_review import check_release,check_handoff,_pair,release_checks
from twinlight_core.review_exchange import packet,import_response
from twinlight_core.art_quality import sha256,ArtEvidenceError
from twinlight_core.visual_contract import VisualContractError


class TempTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()


class CapabilityTests(TempTest):
    def test_pending_never_ready(self):self.assertFalse(assess(template())['ok'])
    def test_valid_declaration_not_authenticated(self):
        r=assess(host());self.assertTrue(r['ok']);self.assertFalse(r['host_identity_authenticated']);self.assertFalse(r['agent_invoked'])
    def test_each_image_flag_required(self):
        for k in IMAGE_FLAGS:
            with self.subTest(k=k):
                v=host();v['image'][k]=False;self.assertFalse(assess(v)['ok'])
    def test_each_review_flag_required(self):
        for k in REVIEW_FLAGS:
            with self.subTest(k=k):
                v=host();v['reviewer'][k]=None;self.assertFalse(assess(v)['ok'])
    def test_string_true_is_not_true(self):
        v=host();v['reviewer']['isolated_session']='true';self.assertFalse(assess(v)['ok'])
    def test_shared_prompt_context_blocked(self):
        v=host();v['image']['prompt_transport']='shared_context';self.assertFalse(assess(v)['may_start_image_calls'])
    def test_isolated_context_allowed(self):
        v=host();v['image'].update(prompt_transport='isolated_task_context',reference_transport='isolated_task_context');self.assertTrue(assess(v)['ok'])
    def test_implicit_reference_rejected(self):
        v=host();v['image']['reference_transport']='automatic_unknown';self.assertFalse(assess(v)['ok'])
    def test_html_needs_review_not_image(self):
        v=host();v['image']={};v['runtime']['webgl']=False
        self.assertTrue(assess(v,'html')['ok']);v['reviewer']['isolated_session']=False;self.assertFalse(assess(v,'html')['ok'])
    def test_no_webgl_does_not_release_card(self):
        v=host();v['runtime']['webgl']=False;self.assertFalse(assess(v)['ok'])
    def test_missing_and_invalid_file_block(self):
        self.assertFalse(load_assessment(None,'both')['ok']);p=self.root/'invalid.json';p.write_text('{');self.assertFalse(load_assessment(p,'both')['ok'])
    def test_nonportrait_native_sizes_block(self):
        v=host();v['image']['native_canvases']=[[800,600]];self.assertFalse(assess(v)['ok'])
    def test_prompt_only_is_preference_not_native_guarantee(self):
        v=host();v['image'].update(native_canvases=[],canvas_selection='prompt_only');self.assertTrue(assess(v)['ok'])
    def test_no_capability_source_blocks(self):
        for area in ('image','reviewer','runtime'):
            with self.subTest(area=area):
                v=host();v[area]['source']='';self.assertFalse(assess(v)['ok'])


class DispatchTests(TempTest):
    def setUp(self):
        super().setUp();self.run=self.root/'run';self.run.mkdir();self.hp=self.root/'host.json';save(self.hp,host())
        save(self.run/'run-state.json',{'mode':'both','persona_digest':PERSONA})
        self.card,self.plan=self.compile('card')
    def compile(self,name):
        c=self.root/name;c.mkdir();save(c/'design.json',design(style='twinlight-collector'))
        write_plan(c/'design.json',c,canvas=(600,800),capabilities=host()['image']);return c,c/'generation-plan.json'
    def reserve(self,n=1):
        p=self.card/'dispatch'/f'{n}.json';r=dispatch(self.plan,'prototype',self.run,self.hp,p);return p,r
    def test_pure_image_prompt(self):
        p,r=self.reserve();v=json.loads(p.read_text());self.assertFalse(v['agent_invoked']);self.assertNotIn('selection_basis',v['prompt_text'])
        self.assertEqual(v['task_scope']['output_count'],1);self.assertTrue(v['reference_images'])
    def test_pending_plan_not_callable(self):
        v=json.loads(self.plan.read_text());v['ready_for_image_call']=False;save(self.plan,v)
        with self.assertRaises(VisualContractError):self.reserve()
    def test_missing_dispatch_not_registerable(self):
        with self.assertRaises(VisualContractError):verify_dispatch(self.plan,'prototype',None)
    def test_compiler_rejects_unknown_transport(self):
        v=host()['image'];v['prompt_transport']='unknown'
        with self.assertRaises(VisualContractError):check_capabilities(v,(600,800))
    def test_frozen_plan_changed(self):
        p,_=self.reserve();v=json.loads(self.plan.read_text());v['new_field']='changed';save(self.plan,v)
        with self.assertRaises(VisualContractError):verify_dispatch(self.plan,'prototype',p)
    def test_changed_reference_blocks_dispatch(self):
        v=json.loads(self.plan.read_text());(self.card/v['jobs'][0]['reference_images'][0]['file']).write_bytes(b'changed')
        with self.assertRaises((VisualContractError,ArtEvidenceError)):self.reserve()
    def test_host_changed_after_dispatch(self):
        p,_=self.reserve();v=host();v['image']['source']+=' changed';save(self.hp,v)
        with self.assertRaises(VisualContractError):verify_dispatch(self.plan,'prototype',p)
    def test_wrong_persona_blocked(self):
        save(self.run/'run-state.json',{'mode':'both','persona_digest':'b'*64})
        with self.assertRaises(VisualContractError):self.reserve()
    def test_wrong_role_blocked(self):
        with self.assertRaises(VisualContractError):dispatch(self.plan,'subject',self.run,self.hp,self.card/'d.json')
    def test_output_must_be_new(self):
        self.reserve()
        with self.assertRaises(VisualContractError):self.reserve()
    def test_dispatch_cannot_escape_card_root(self):
        with self.assertRaises(VisualContractError):dispatch(self.plan,'prototype',self.run,self.hp,self.root/'escaped.json')
    def test_budget_persists_across_card_dirs(self):
        self.reserve(1);self.reserve(2);self.reserve(3)
        c,plan=self.compile('other-card')
        with self.assertRaisesRegex(VisualContractError,'Three call'):dispatch(plan,'prototype',self.run,self.hp,c/'fourth.json')
    def test_consumed_dispatch_not_replayable(self):
        p,_=self.reserve();raw=self.card/'raw.txt';raw.write_text('SYNTHETIC raw')
        consume_dispatch(p,'SYNTHETIC_CALL',raw)
        with self.assertRaises(VisualContractError):verify_dispatch(self.plan,'prototype',p)
    def test_same_call_not_reusable(self):
        p,_=self.reserve();raw=self.card/'raw.txt';raw.write_text('SYNTHETIC raw');consume_dispatch(p,'SAME_CALL',raw)
        q,_=self.reserve(2)
        with self.assertRaises(VisualContractError):verify_dispatch(self.plan,'prototype',q,call_id='SAME_CALL')
    def test_prototype_repair_preserves_design(self):
        before=sha256(self.card/'art-direction.json');r=repair_plan(self.plan,'prototype','SYNTHETIC failure: output is a website. Produce one standalone illustration only.')
        self.assertTrue(r['design_unchanged']);self.assertEqual(before,sha256(self.card/'art-direction.json'));self.assertEqual(r['attempts_used'],0)
    def test_repair_invalidates_old_dispatch(self):
        p,_=self.reserve();repair_plan(self.plan,'prototype','SYNTHETIC correction: use the exact one-scene portrait canvas.')
        with self.assertRaises(VisualContractError):verify_dispatch(self.plan,'prototype',p)
    def test_register_actual_bytes_requires_dispatch(self):
        img=self.card/'return.png';Image.new('RGB',(600,800),(36,50,61)).save(img);raw=self.card/'raw.txt';raw.write_text('SYNTHETIC_ARTIFACT')
        with self.assertRaisesRegex(VisualContractError,'dispatch'):register_image(self.plan,'prototype',img,raw,tool='SYNTHETIC_PROVIDER',call_id='call1',artifact_id='SYNTHETIC_ARTIFACT')
    def test_valid_return_registered_not_approved(self):
        d,_=self.reserve();img=self.card/'return.png';Image.new('RGB',(600,800),(36,50,61)).save(img);raw=self.card/'raw.txt';raw.write_text('SYNTHETIC_ARTIFACT')
        r=register_image(self.plan,'prototype',img,raw,tool='SYNTHETIC_PROVIDER',call_id='call1',artifact_id='SYNTHETIC_ARTIFACT',dispatch_path=d)
        self.assertTrue(r['ok']);self.assertFalse(r['art_approved']);self.assertFalse(r['generation_provenance_verified'])
        ev=json.loads((self.card/'art-evidence.json').read_text());call=json.loads((self.card/ev['images']['prototype']['call']['file']).read_text());check_recorded_dispatch(self.card,call,{})
    def test_landscape_rejection_keeps_original(self):
        d,_=self.reserve();img=self.card/'return.png';Image.new('RGB',(800,600),(36,50,61)).save(img);raw=self.card/'raw.txt';raw.write_text('SYNTHETIC_ARTIFACT')
        r=register_image(self.plan,'prototype',img,raw,tool='SYNTHETIC_PROVIDER',call_id='call1',artifact_id='SYNTHETIC_ARTIFACT',dispatch_path=d)
        self.assertFalse(r['ok']);self.assertTrue(r['originals_preserved']);self.assertEqual(r['attempts_used'],1)
    def test_art_attempt_budget_cannot_reset_by_recompile(self):
        for n in (1,2,3):self.reserve(n)
        write_plan(self.card/'design.json',self.card,canvas=(600,800),capabilities=host()['image'])
        with self.assertRaises(VisualContractError):self.reserve(4)


class ReviewTests(TempTest):
    def check(self,mode='card',change=None):
        outputs,r=release(self.root,mode)
        if change:
            change(r);r=sign(self.root,r);save(self.root/'release-review.json',r)
        return check_release(self.root,outputs,mode)
    def test_good_synthetic_card_contract(self):
        r=self.check();self.assertTrue(r['ok']);self.assertFalse(r['reviewer_identity_authenticated'])
    def test_good_synthetic_both_contract(self):self.assertTrue(self.check('both')['ok'])
    def test_good_synthetic_html_contract(self):self.assertTrue(self.check('html')['ok'])
    def test_html_cannot_bypass_release(self):self.assertFalse(check_release(self.root,{},'html')['ok'])
    def test_html_not_required_to_have_card_foil(self):
        r=self.check('html',lambda r:r['runtime'].update(backend='canvas2d',webgl_ready=False,fallback=True));self.assertTrue(r['ok'])
    def test_pending_blocks(self):self.assertFalse(self.check(change=lambda r:r.update(decision='pending'))['ok'])
    def test_blocked_blocks(self):self.assertEqual(self.check(change=lambda r:r.update(decision='blocked'))['status'],'reviewer_blocked')
    def test_revise_blocks(self):self.assertEqual(self.check(change=lambda r:r.update(decision='revise'))['status'],'release_rejected')
    def test_css_fallback_does_not_pass_foil(self):self.assertFalse(self.check(change=lambda r:r['runtime'].update(fallback=True))['ok'])
    def test_silent_webgl_failure_blocks(self):self.assertFalse(self.check(change=lambda r:r['runtime'].update(webgl_ready=False))['ok'])
    def test_merge_over_15_rejected(self):self.assertFalse(self.check('both',lambda r:r['runtime'].update(merge_seconds=15.1))['ok'])
    def test_html_merge_over_15_rejected(self):self.assertFalse(self.check('html',lambda r:r['runtime'].update(merge_seconds=16))['ok'])
    def test_one_failed_criterion_cannot_average_away(self):self.assertFalse(self.check(change=lambda r:r['checks']['complete_subject'].update(passed=False))['ok'])
    def test_empty_observation_rejected(self):self.assertFalse(self.check(change=lambda r:r['checks']['complete_subject'].update(observation=''))['ok'])
    def test_accept_with_blocker_rejected(self):self.assertFalse(self.check(change=lambda r:r.update(blockers=[{'object':'subject'}]))['ok'])
    def test_actual_html_change_invalidates_release(self):
        outputs,_=release(self.root);Path(outputs['card_preview']).write_text('changed');self.assertFalse(check_release(self.root,outputs,'card')['ok'])
    def test_same_session_cannot_self_approve(self):
        _,r=release(self.root);r['handoff']['reviewer_session_id']='SYNTHETIC_PRODUCER'
        with self.assertRaises(ArtEvidenceError):check_handoff(self.root,r,{})
    def test_whitespace_cannot_disguise_self_review(self):
        _,r=release(self.root);r['handoff']['reviewer_session_id']=' SYNTHETIC_PRODUCER '
        with self.assertRaises(ArtEvidenceError):check_handoff(self.root,r,{})
    def test_producer_cannot_rewrite_raw_decision(self):
        outputs,r=release(self.root);r['checks']['complete_subject']['observation']='A different invented producer observation.';save(self.root/'release-review.json',r)
        self.assertFalse(check_release(self.root,outputs,'card')['ok'])
    def test_foil_no_op_detected(self):
        def change(r):r['effect_frames']['foil_on']['image']=r['effect_frames']['foil_off']['image']
        self.assertFalse(self.check(change=change)['ok'])
    def test_depth_no_op_detected(self):
        def change(r):r['effect_frames']['depth_on']['image']=r['effect_frames']['depth_off']['image']
        self.assertFalse(self.check(change=change)['ok'])
    def test_time_drift_is_not_foil(self):
        def change(r):r['effect_frames']['foil_on']['state']['time']=1
        self.assertFalse(self.check(change=change)['ok'])
    def test_view_drift_is_not_depth(self):
        def change(r):r['effect_frames']['depth_on']['state']['y']=.5
        self.assertFalse(self.check(change=change)['ok'])
    def test_viewport_boolean_rejected(self):
        def change(r):r['effect_frames']['foil_off']['state']['viewport']=[True,900]
        self.assertFalse(self.check(change=change)['ok'])
    def test_fullscreen_slider_is_not_card_region(self):
        def change(r):r['effect_frames']['foil_off']['state']['region']='full_screen'
        self.assertFalse(self.check(change=change)['ok'])
    def test_depth_test_requires_nonzero_angle(self):
        def change(r):
            for n in ('depth_off','depth_on'):r['effect_frames'][n]['state'].update(x=0,y=0)
        self.assertFalse(self.check(change=change)['ok'])
    def test_import_preserves_original_response(self):
        _,r=release(self.root);raw=self.root/'test-raw.json';before=raw.read_bytes();out=self.root/'history'/'import.json'
        result=import_response(self.root,raw,self.root/'test-trace.json',out);self.assertTrue(result['ok']);self.assertEqual(before,raw.read_bytes());self.assertEqual(json.loads(out.read_text()),r)
    def test_import_cannot_overwrite(self):
        release(self.root);out=self.root/'used.json';out.write_text('{}')
        with self.assertRaises(ValueError):import_response(self.root,self.root/'test-raw.json',self.root/'test-trace.json',out)
    def test_import_cannot_escape_stage_root(self):
        release(self.root)
        with self.assertRaises(ValueError):import_response(self.root,self.root/'test-raw.json',self.root/'test-trace.json',self.root.parent/'outside.json')
    def test_blocked_requires_actual_reason(self):
        _,r=release(self.root);r['decision']='blocked';r=sign(self.root,r)
        with self.assertRaises(ArtEvidenceError):check_handoff(self.root,r,{})
    def test_detailed_rejection_importable(self):
        _,r=release(self.root);r.update(decision='revise',blockers=[{'object':'subject','location':'top left','evidence':'SYNTHETIC missing pixels','repair':'Regenerate the failed subject layer only','preserve':['background']}]);sign(self.root,r)
        self.assertEqual(import_response(self.root,self.root/'test-raw.json',self.root/'test-trace.json',self.root/'rejected.json')['decision'],'revise')
    def test_packet_not_a_review(self):
        _,r=release(self.root);r['decision']='pending';p=self.root/'pending.json';save(p,r)
        source=self.root/'desktop.png';out=self.root/'packet';x=packet(p,{str(source):sha256(source)},out)
        self.assertFalse(x['agent_invoked']);self.assertEqual(json.loads((out/'review-template.json').read_text())['decision'],'pending')
    def test_packet_excludes_producer_report(self):
        _,r=release(self.root);r['decision']='pending';p=self.root/'pending.json';save(p,r)
        source=self.root/'run-report.json';save(source,{'claim':'THIS IS EXCELLENT'})
        out=self.root/'packet';packet(p,{str(source):sha256(source)},out)
        self.assertEqual(json.loads((out/'packet.json').read_text())['attachments'],[])
    def test_packet_refuses_font_distribution(self):
        p=self.root/'pending.json';save(p,{'stage':'prototype','decision':'pending','targets':{}})
        f=self.root/'test.ttf';f.write_text('SYNTHETIC FONT EXTENSION')
        with self.assertRaises(ValueError):packet(p,{str(f):sha256(f)},self.root/'packet')


if __name__=='__main__':unittest.main()
