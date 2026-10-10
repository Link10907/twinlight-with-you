"""Two-task regressions. ALL approval/provider fixtures below are SYNTHETIC.

Mocked accepted results test code paths, never actual artwork/reviewer quality.
"""
import base64,copy,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from quality_fixtures import ROOT,host,save
from split_fixtures import person,native,card_workspace
from twinlight_core.common import load
from twinlight_core.lite import persona_digest
from twinlight_core.cardgen import read_card_data
from twinlight_core.host_contract import assess
from twinlight_core.execution_bridge import doctor,config,invoke_image
from twinlight_core.tasks import freeze_card_input,site as task_site,card as task_card
from twinlight_core.card_handoff import seal,validate,audit_pack,inspect_card_workspace,renderer_contract
from twinlight_core.art_quality import sha256
from twinlight_core.navigation import manifest,audit_runtime
from twinlight_core.independent_review import release_checks
from twinlight_core.site import build_lite
from twinlight_core.template_origin import verify_site
from twinlight_core.embedded_card import audit_embedding,audit_renderer
from twinlight_core.run import _run_mechanical
from twinlight_core.export_delivery import export
from package_card import package
from package_skill import resource_files


class SplitRoutingTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name).resolve()
        self.input=self.root/'person.json';save(self.input,person())
    def test_integrate_needs_no_image_capabilities(self):
        h=host();h.pop('image');r=assess(h,'integrate')
        self.assertTrue(r['ok']);self.assertFalse(r['may_start_image_calls'])
    def test_card_still_needs_actual_image_capabilities(self):
        h=host();h.pop('image');self.assertFalse(assess(h,'card')['ok'])
    def test_integrate_still_requires_independent_vision(self):
        h=host();h['reviewer']['isolated_session']=False
        self.assertFalse(assess(h,'integrate')['ok'])
    def test_integrate_known_webgl_failure_blocks(self):
        h=host();h['runtime']['webgl']=False;self.assertFalse(assess(h,'integrate')['ok'])
    def test_reviewer_only_doctor_is_offline(self):
        p=self.root/'execution.json';save(p,{'version':'twinlight-execution-1','reviewer':{'kind':'command','argv':[sys.executable]}})
        with patch('twinlight_core.execution_bridge.vision',side_effect=AssertionError('MUST NOT CALL')):
            r=doctor(p,'integrate')
        self.assertTrue(r['ok']);self.assertEqual(set(r['routes']),{'reviewer'});self.assertEqual(r['provider_calls'],0)
    def test_reviewer_only_not_accepted_for_card(self):
        p=self.root/'execution.json';save(p,{'version':'twinlight-execution-1','reviewer':{'kind':'command','argv':[sys.executable]}})
        with self.assertRaises(ValueError):doctor(p,'card')
    def test_site_scoped_host_rejects_image_before_provider_or_config(self):
        hp=self.root/'host.json';save(hp,{'execution_scope':'integrate'})
        with patch('twinlight_core.execution_bridge.generate',side_effect=AssertionError('MUST NOT CALL')):
            with self.assertRaisesRegex(ValueError,'forbidden'):
                invoke_image(self.root/'absent-config',self.root/'absent-plan','prototype',self.root,hp,self.root/'out',allowed=True)
        self.assertFalse((self.root/'out').exists())
    def test_freeze_projects_same_persona_without_galaxy(self):
        p=self.root/'card-input.json';r=freeze_card_input(self.input,p)
        self.assertNotIn('themes',load(p));self.assertEqual(r['persona_digest'],persona_digest(person()))
        self.assertEqual(read_card_data(p)['card'],person()['card'])
    def test_frozen_card_input_cannot_be_silently_replaced(self):
        p=self.root/'card-input.json';freeze_card_input(self.input,p)
        changed=person();changed['card']['title']='新称号';save(self.input,changed)
        with self.assertRaisesRegex(ValueError,'Frozen'):freeze_card_input(self.input,p)
    def test_galaxy_only_edit_keeps_persona(self):
        a=person();b=copy.deepcopy(a);b['themes'][0]['headline']='仅更改星系文章。'
        self.assertEqual(persona_digest(a),persona_digest(b))
    def test_card_text_edit_changes_persona(self):
        a=person();b=copy.deepcopy(a);b['card']['tagline']='修改了卡面内容。'
        self.assertNotEqual(persona_digest(a),persona_digest(b))
    def test_task_b_missing_handoff_does_not_start_runner(self):
        with patch('twinlight_core.run.run',side_effect=AssertionError('MUST NOT START')):
            r=task_site(self.input,self.root/'B')
        self.assertEqual(r['status'],'card_handoff_blocked');self.assertFalse(r['complete']);self.assertEqual(r['image_calls_performed'],0)
    def test_task_b_unapproved_flag_is_not_a_handoff(self):
        p=self.root/'card-handoff.json';save(p,{'approved':True,'complete':True})
        r=task_site(self.input,self.root/'B',card_handoff=p)
        self.assertFalse(r['complete']);self.assertEqual(r['image_calls_performed'],0)
    def test_task_a_does_not_build_site_or_fabricate_seal(self):
        r=task_card(self.input,self.root/'A',no_browser=True)
        self.assertFalse(r['complete']);self.assertFalse((self.root/'A/site').exists())
        self.assertFalse((self.root/'A/card-handoff.json').exists())
    def test_site_review_receives_bound_navigation_not_arbitrary_reports(self):
        from twinlight_core.execution_bridge import _review_inputs
        p=self.root/'report.json';save(p,{'version':'navigation-browser-1','SYNTHETIC':True})
        image=self.root/'capture.png';image.write_bytes(b'SYNTHETIC image ref; not an actual review')
        unknown=self.root/'unknown-report.json';save(unknown,{'private':'must not preload'})
        draft={'stage':'release','targets':{'task':'site','navigation':{'sha256':sha256(p)}}}
        save(self.root/'review-template.json',draft)
        refs={'attachments':[{'file':f.name,'source':str(f),'sha256':sha256(f)} for f in (p,image,unknown)]}
        with patch('twinlight_core.review_exchange.validate_packet',return_value=refs):
            _,_,images,texts=_review_inputs(self.root)
        self.assertEqual(len(images),1);self.assertEqual(len(texts),1)
        self.assertIn('navigation-browser-1',texts[0]);self.assertNotIn('must not preload',texts[0])

    def test_site_extra_visual_review_criteria_are_not_added_to_legacy(self):
        self.assertEqual(len(release_checks('both','site')),len(release_checks('both'))+4)
        self.assertNotIn('single_file_offline',release_checks('card'))
    def test_skill_package_contains_both_tasks_and_no_fonts(self):
        names={p.relative_to(ROOT).as_posix() for p in resource_files(ROOT)}
        for name in ('HTML.md','references/card-handoff.md','scripts/verify_navigation.py','assets/navigation/extension-lock.json','tests/quality/test_split_tasks.py','tests/quality/split_fixtures.py'):
            self.assertIn(name,names)
        self.assertFalse(any(n.endswith(('.woff','.woff2','.ttf','.otf','.ttc')) for n in names))


class HandoffTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name).resolve();self.A=self.root/'A'
        self.data,self.layers,self.outputs=card_workspace(self.A)
    def mocks(self):
        # Test-only protocol success: no actual review is represented here.
        from contextlib import ExitStack
        stack=ExitStack();stack.enter_context(patch('twinlight_core.art_quality.check_evidence',return_value={'ok':True,'inputs_sha256':{}}))
        stack.enter_context(patch('twinlight_core.independent_review.check_release',return_value={'ok':True,'inputs_sha256':{}}))
        return stack
    def test_unmocked_synthetic_approvals_cannot_seal(self):
        with self.assertRaises(ValueError):seal(self.A)
        self.assertFalse((self.A/'card-handoff.json').exists())
    def test_current_handoff_roundtrip_with_explicit_mocked_gates(self):
        with self.mocks():
            r=seal(self.A);v=validate(Path(r['handoff']),persona_digest(self.data))
        self.assertTrue(v['ok']);self.assertEqual(v['image_calls_performed'],0)
    def test_wrong_owner_rejected_even_when_gate_mocks_pass(self):
        with self.mocks():
            seal(self.A)
            with self.assertRaisesRegex(ValueError,'does not match'):validate(self.A/'card-handoff.json','b'*64)
    def test_changed_card_bytes_cannot_inherit_handoff(self):
        with self.mocks():
            seal(self.A);Path(self.outputs['card_front']).write_bytes(b'SYNTHETIC changed')
            with self.assertRaises(ValueError):validate(self.A/'card-handoff.json')
    def test_changed_source_layer_is_detected(self):
        with self.mocks():
            seal(self.A);p=self.layers.parent/'subject.png';p.write_bytes((self.layers.parent/'effects.png').read_bytes())
            with self.assertRaises(ValueError):validate(self.A/'card-handoff.json')
    def test_revoked_art_review_blocks_prior_handoff(self):
        with self.mocks():seal(self.A)
        with patch('twinlight_core.art_quality.check_evidence',return_value={'ok':False,'errors':[{'code':'SYNTHETIC_REVOKED'}]}):
            with self.assertRaisesRegex(ValueError,'artwork review'):validate(self.A/'card-handoff.json')
    def test_revoked_release_blocks_prior_handoff(self):
        with self.mocks():
            seal(self.A)
            with patch('twinlight_core.independent_review.check_release',return_value={'ok':False}):
                with self.assertRaisesRegex(ValueError,'release'):validate(self.A/'card-handoff.json')
    def test_changed_browser_report_is_rejected(self):
        with self.mocks():
            seal(self.A);p=self.A/'browser/card_browser/report.json';r=load(p);r['foil_verified']=False;save(p,r)
            with self.assertRaisesRegex(ValueError,'browser'):validate(self.A/'card-handoff.json')
    def test_complete_boolean_without_runtime_does_not_pass(self):
        p=self.A/'run-state.json';s=load(p);s['stages']['card_browser']['invoked_by_runner']=False;save(p,s)
        with self.mocks():
            with self.assertRaisesRegex(ValueError,'browser'):seal(self.A)
    def test_pack_depth_tampering_is_rejected(self):
        p=Path(self.outputs['card_pack']);r=load(p);r['depths']['subject']=.8;save(p,r)
        with self.assertRaisesRegex(ValueError,'depth'):audit_pack(p,self.layers,persona_digest(self.data))
    def test_pack_renderer_tampering_is_rejected(self):
        p=Path(self.outputs['card_pack']);r=load(p);r['renderer']['fingerprint']='f'*64;save(p,r)
        with self.assertRaisesRegex(ValueError,'renderer'):audit_pack(p,self.layers,persona_digest(self.data))
    def test_external_pack_layer_is_rejected(self):
        p=Path(self.outputs['card_pack']);r=load(p);r['layers']['subject']='https://invalid.example/subject.png';save(p,r)
        with self.assertRaisesRegex(ValueError,'external'):audit_pack(p,self.layers,persona_digest(self.data))
    def test_direct_preview_contains_exact_shared_renderer(self):
        self.assertTrue(audit_renderer(Path(self.outputs['card_preview']),self.layers)['ok'])
        self.assertIn('index.html#galaxy',Path(self.outputs['card_preview']).read_text())
    def test_task_b_copies_card_without_image_edit_or_repack(self):
        inp=self.root/'person.json';save(inp,person());hp=self.root/'host-B.json';h=host();h.pop('image');save(hp,h)
        with self.mocks():
            seal(self.A)
            with patch('package_card.package',side_effect=AssertionError('B must not repackage A')), \
                 patch('preview_card.preview',side_effect=AssertionError('B must not rebuild A preview')), \
                 patch('twinlight_core.execution_bridge.invoke_image',side_effect=AssertionError('B must not generate')):
                r=task_site(inp,self.root/'B',card_handoff=self.A/'card-handoff.json',no_browser=True,host_capabilities=hp)
        self.assertTrue(r['host_contract']['ok']);self.assertFalse(r['complete'])
        self.assertEqual(r['image_calls_performed'],0)
        self.assertEqual(r['stages']['navigation_browser']['status'],'skipped')
        for key,p in self.outputs.items():self.assertEqual(Path(r['outputs'][key]).read_bytes(),Path(p).read_bytes())
        self.assertTrue(audit_embedding(Path(r['outputs']['html_with_card']),self.layers,persona_digest(self.data),strict_renderer=True)['ok'])
        self.assertTrue(verify_site(self.root/'B/site-with-card')['ok'])
        cmd=r['next_action']['resume'];self.assertIn('--card-handoff',cmd);self.assertNotIn('--layers',cmd)
    def test_installed_reviewer_and_style_refs_can_be_bound(self):
        refs={str(ROOT/'REVIEWER.md'):sha256(ROOT/'REVIEWER.md'),
              str(ROOT/'assets/art-styles/twinlight-collector.json'):sha256(ROOT/'assets/art-styles/twinlight-collector.json')}
        with self.mocks():
            with patch('twinlight_core.art_quality.check_evidence',return_value={'ok':True,'inputs_sha256':refs}):
                seal(self.A);v=validate(self.A/'card-handoff.json')
        self.assertTrue(v['ok']);self.assertEqual(set(load(self.A/'card-handoff.json')['resource_files_sha256']),{'REVIEWER.md','assets/art-styles/twinlight-collector.json'})
    def test_arbitrary_external_review_dependency_is_not_allowed(self):
        p=self.root/'outside.json';save(p,{'SYNTHETIC':'untracked external file'})
        with self.mocks():
            with patch('twinlight_core.art_quality.check_evidence',return_value={'ok':True,'inputs_sha256':{str(p):sha256(p)}}):
                with self.assertRaisesRegex(ValueError,'not an installed'):seal(self.A)
    def test_export_same_package_names_and_rechecks_handoff(self):
        # Export wiring ONLY. Mocked release is not a real art/browser approval.
        inp=self.root/'person.json';save(inp,person());hp=self.root/'host-B.json';h=host();h.pop('image');save(hp,h)
        B=self.root/'B'
        with self.mocks():
            seal(self.A)
            r=task_site(inp,B,card_handoff=self.A/'card-handoff.json',no_browser=True,host_capabilities=hp)
            r.update(complete=True,status='files_ready',dynamic_verified=True,embedded_card_verified=True,
                     draft=True,share_allowed=False,primary_output=r['outputs']['html_with_card'])
            for key in ('request_status','request_satisfied','in_chat_interaction_verified'):r.pop(key,None)
            receipt=dict(r,outputs_sha256={k:sha256(Path(v)) for k,v in r['outputs'].items()})
            save(B/'run-report.json',r);save(B/'delivery-report.json',receipt)
            result=export(B,self.root/'delivery')
            with zipfile.ZipFile(result['archive']) as z:
                self.assertEqual(set(z.namelist()),{'index.html','card-preview.html','card-front.png','card-pack.json','README.txt','delivery.json'})
                self.assertEqual(z.read('card-preview.html'),Path(self.outputs['card_preview']).read_bytes())
                self.assertEqual(z.read('index.html'),Path(r['outputs']['html_with_card']).read_bytes())
                self.assertNotIn(str(self.A).encode(),z.read('delivery.json'))
            with patch('twinlight_core.card_handoff.validate',side_effect=ValueError('SYNTHETIC revoked')):
                with self.assertRaisesRegex(ValueError,'revoked'):export(B,self.root/'rejected-export')
            self.assertFalse((self.root/'rejected-export').exists())

    def test_task_b_refuses_nested_workspaces(self):
        inp=self.root/'person.json';save(inp,person())
        with self.mocks():
            seal(self.A);r=task_site(inp,self.A/'B',card_handoff=self.A/'card-handoff.json')
        self.assertEqual(r['status'],'card_handoff_blocked')


class NavigationBindingTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name).resolve()
        self.html=self.root/'index.html';self.html.write_text('SYNTHETIC HTML, not a browser-rendered page')
        self.rp=self.root/'browser/navigation_browser/report.json'
    def fixture(self,load_mode='file'):
        r={'version':'navigation-browser-1','ok':True,'html_sha256':sha256(self.html),'load_mode':load_mode,
           'file_open_verified':True,'offline_self_contained_verified':True,'delivery_eligible':True,
           'checks':[{'name':'SYNTHETIC NAVIGATION','passed':True}]}
        save(self.rp,r)
        stage={'status':'passed','invoked_by_runner':True,'report_input_bound':True,'input_html_sha256':sha256(self.html),
          'report':str(self.rp),'files_sha256':{self.rp.relative_to(self.root).as_posix():sha256(self.rp)}}
        save(self.root/'run-state.json',{'task':'site','stages':{'navigation_browser':stage}})
    def test_injected_report_cannot_authorize_file_delivery(self):
        self.fixture('injected')
        with self.assertRaisesRegex(ValueError,'Injected'):audit_runtime(self.root,self.html)
    def test_hash_binding_roundtrip_synthetic_only(self):
        self.fixture();self.assertEqual(audit_runtime(self.root,self.html)['sha256'],sha256(self.rp))
    def test_navigation_report_edit_revokes_binding(self):
        self.fixture();r=load(self.rp);r['note']='modified';save(self.rp,r)
        with self.assertRaisesRegex(ValueError,'changed'):audit_runtime(self.root,self.html)
    def test_navigation_html_edit_revokes_binding(self):
        self.fixture();self.html.write_text('changed')
        with self.assertRaisesRegex(ValueError,'current'):audit_runtime(self.root,self.html)
    def test_failed_navigation_check_is_never_accepted(self):
        self.fixture();r=load(self.rp);r['checks'][0]['passed']=False;save(self.rp,r)
        st=load(self.root/'run-state.json');st['stages']['navigation_browser']['files_sha256'][self.rp.relative_to(self.root).as_posix()]=sha256(self.rp);save(self.root/'run-state.json',st)
        with self.assertRaises(ValueError):audit_runtime(self.root,self.html)
    def test_versioned_additive_extension_lock_is_valid(self):
        self.assertEqual(manifest()['version'],'navigation-1.0.0')
    def test_navigation_tamper_cannot_be_silently_relocked(self):
        from twinlight_core.navigation import DIRECTORY,FILES
        for name in (*FILES,'extension-lock.json'):(self.root/name).write_bytes((DIRECTORY/name).read_bytes())
        (self.root/'after-core.js').write_text('CHANGED')
        with patch('twinlight_core.navigation.DIRECTORY',self.root):
            with self.assertRaisesRegex(ValueError,'changed'):manifest()


if __name__=='__main__':unittest.main()
