"""Actual byte/receipt audits with synthetic assets; controlled build doubles only."""
import base64,copy,json,shutil,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from visual_v2_fixtures import *
from twinlight_core.embedded_card import audit_embedding
from twinlight_core.delivery import deliver, HOST_CHECKS
from twinlight_core.export_delivery import export

class EmbeddedCardTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);images(self.root)
        self.manifest=self.root/'layers.json';self.html=minimal_embedded(self.root)
    def audit(self):return audit_embedding(self.html,self.manifest,PERSONA)
    def test_exact_embedded_native_bytes_pass(self):self.assertTrue(self.audit()['ok'])
    def test_byte_audit_is_not_browser_proof(self):self.assertFalse(self.audit()['dynamic_verified'])
    def test_wrong_persona_blocked(self):self.assertFalse(audit_embedding(self.html,self.manifest,'b'*64)['ok'])
    def test_static_card_blocked(self):
        self.html.write_text(self.html.read_text().replace('"layered"','"static"'));self.assertEqual(self.audit()['errors'][0]['code'],'static_card_not_native')
    def test_placeholder_manifest_blocked(self):
        m=json.loads(self.manifest.read_text());m['art_status']='placeholder';save(self.manifest,m);self.assertFalse(self.audit()['ok'])
    def test_old_image_in_html_blocked(self):
        old=uri(self.root/'subject.png');bad=uri(self.root/'effects.png');self.html.write_text(self.html.read_text().replace(old,bad));self.assertEqual(self.audit()['errors'][0]['code'],'embedded_layer_mismatch')
    def test_empty_four_pixel_layers_blocked(self):
        Image.new('RGBA',(4,4)).save(self.root/'subject.png');self.assertEqual(self.audit()['errors'][0]['code'],'canvas_mismatch')
    def test_empty_native_size_subject_blocked(self):
        Image.new('RGBA',(600,800)).save(self.root/'subject.png');self.assertEqual(self.audit()['errors'][0]['code'],'empty_or_flat_layer')
    def test_lineart_wrong_pixels_blocked(self):
        Image.new('RGB',(600,800),'white').save(self.root/'lineart.png');self.assertEqual(self.audit()['errors'][0]['code'],'unregistered_lineart')
    def test_zero_depth_blocked(self):
        m=json.loads(self.manifest.read_text());m['depths']['subject']=0;save(self.manifest,m);self.assertEqual(self.audit()['errors'][0]['code'],'layer_depths')
    def test_shared_asset_file_blocked(self):
        m=json.loads(self.manifest.read_text());m['assets']['effects']='subject.png';save(self.manifest,m);self.assertEqual(self.audit()['errors'][0]['code'],'duplicate_layer_file')
    def test_missing_flat_preview_blocked(self):
        s=self.html.read_text();s=s.replace('const V9_CARD_IMAGE','const OLD_IMAGE');self.html.write_text(s);self.assertFalse(self.audit()['ok'])
    def test_flattened_image_must_match_layers(self):
        s=self.html.read_text();i=s.index('const V9_CARD_IMAGE=');s=s[:i]+'const V9_CARD_IMAGE='+json.dumps(uri(self.root/'background.png'))+';\n</script>';self.html.write_text(s);self.assertEqual(self.audit()['errors'][0]['code'],'flat_preview_mismatch')
    def test_duplicate_persona_constant_rejected(self):
        self.html.write_text(self.html.read_text()+'\n<script>\nconst CARD_PERSONA={};</script>');self.assertFalse(self.audit()['ok'])
    def test_remote_uri_rejected(self):
        self.html.write_text(self.html.read_text().replace(uri(self.root/'subject.png'),'https://example.invalid/art.png'));self.assertEqual(self.audit()['errors'][0]['code'],'not_self_contained')
    def test_profile_and_persona_must_agree(self):
        self.html.write_text(self.html.read_text().replace('"content_ready": true','"content_ready": false',1));self.assertEqual(self.audit()['errors'][0]['code'],'persona_copies_diverged')
    def test_directory_traversal_blocked(self):
        m=json.loads(self.manifest.read_text());m['assets']['subject']='../subject.png';save(self.manifest,m);self.assertEqual(self.audit()['errors'][0]['code'],'asset_path')

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);self.art=self.root/'art';self.manifest=dossier(self.art)
        self.ws=self.root/'run';self.input=self.root/'input.json';save(self.input,{'synthetic_test_only':True})
        self.after_gate=None;self.dynamic=True;self.mutate_html=False
    def core(self,input_path,workspace,_review_gate,**kwargs):
        """Build double: no claim that production V10 CLI or image tools ran here."""
        mode=kwargs.get('mode','both');workspace.mkdir(exist_ok=True);shutil.copyfile(input_path,workspace/'content.json')
        save(workspace/'run-state.json',{'stages':{}});outputs={};stages={}
        if mode!='card':
            (workspace/'site').mkdir(exist_ok=True);(workspace/'site/index.html').write_text('BASE HTML TEST DOUBLE')
            outputs['html']=str(workspace/'site/index.html')
        if mode!='html':
            (workspace/'card').mkdir(exist_ok=True)
            for key,file in [('card_front','front.png'),('card_preview','preview.html')]:
                shutil.copyfile(self.art/file,workspace/'card'/file);outputs[key]=str(workspace/'card'/file)
            save(workspace/'card/card-pack.json',{'synthetic_test_only':True});outputs['card_pack']=str(workspace/'card/card-pack.json')
            gate=_review_gate(workspace/'content.json',self.manifest,workspace,PERSONA)
            if mode=='both' and gate['ok']:
                (workspace/'site-with-card').mkdir(exist_ok=True)
                h=minimal_embedded(self.art);shutil.copyfile(h,workspace/'site-with-card/index.html')
                outputs['html_with_card']=str(workspace/'site-with-card/index.html')
                if self.mutate_html:
                    p=Path(outputs['html_with_card']);p.write_text(p.read_text().replace('"layered"','"static"'))
        if self.after_gate:self.after_gate(workspace,outputs)
        return {'mode':mode,'status':'files_ready' if self.dynamic else 'dynamic_unverified','ok':True,'stages':stages,
                'outputs':outputs,'dynamic_verified':self.dynamic,'next_action':None}
    def run_delivery(self,mode='both',**kwargs):
        return deliver(self.core,self.input,self.ws,mode=mode,layers=self.manifest,**kwargs)
    def host_observation(self,result,**overrides):
        observed={'version':'host-preview-2','status':'available','surface':'in_chat',
                  'html_sha256':ref(Path(result['primary_output']))['sha256'],
                  'tool':'synthetic-test-tool','artifact_reference':'synthetic-test-only',
                  'observation':'Synthetic host observation for unit tests only; no real host was opened.',
                  'checks':{key:{'passed':True,'observation':'Synthetic observed interaction for this unit test only.'}
                            for key in HOST_CHECKS[result['mode']]}}
        observed.update(overrides);save(self.ws/'host-preview.json',observed)
        return observed
    def test_native_v2_delivery_complete_with_controlled_browser_status(self):
        r=self.run_delivery();self.assertTrue(r['complete'],r);self.assertTrue(r['embedded_card_verified']);self.assertFalse(r['quality_verified'])
    def test_primary_is_integrated_never_base(self):
        r=self.run_delivery();self.assertEqual(r['primary_output'],r['outputs']['html_with_card']);self.assertNotEqual(r['primary_output'],r['outputs']['html'])
    def test_host_preview_not_inferred_from_local_check(self):
        r=self.run_delivery();self.assertEqual(r['host_preview']['status'],'not_tested');self.assertFalse(r['in_chat_preview_verified'])
        self.assertTrue(r['request_satisfied']);self.assertFalse(r['delivery_requirements']['in_chat_preview'])
    def test_explicit_in_chat_request_keeps_completed_files_but_not_request_success(self):
        r=self.run_delivery(require_in_chat_preview=True)
        self.assertTrue(r['complete']);self.assertFalse(r['request_satisfied'])
        self.assertEqual(r['request_status'],'host_preview_unverified')
        self.assertEqual(r['next_action']['type'],'verify_in_chat_preview')
        self.assertIn('--require-in-chat-preview',r['next_action']['resume'])
        self.assertEqual(r['next_action']['target'],r['outputs']['html_with_card'])
        self.assertTrue(json.loads((self.ws/'run-state.json').read_text())['delivery_requirements']['in_chat_preview'])
    def test_resume_cannot_silently_drop_explicit_chat_requirement(self):
        self.run_delivery(require_in_chat_preview=True)
        r=self.run_delivery()
        self.assertTrue(r['delivery_requirements']['in_chat_preview']);self.assertFalse(r['request_satisfied'])
    def test_current_in_chat_interactions_satisfy_requested_contract(self):
        r=self.run_delivery(require_in_chat_preview=True);self.host_observation(r)
        r=self.run_delivery()
        self.assertTrue(r['request_satisfied']);self.assertTrue(r['in_chat_interaction_verified'])
        self.assertTrue(r['in_chat_preview_verified']);self.assertIsNone(r['next_action'])
        self.assertTrue(json.loads((self.ws/'delivery-report.json').read_text())['request_satisfied'])
    def test_old_available_record_does_not_prove_new_interaction_requirement(self):
        r=self.run_delivery(require_in_chat_preview=True);self.host_observation(r,version='host-preview-1',checks={})
        r=self.run_delivery()
        self.assertTrue(r['in_chat_preview_verified']);self.assertFalse(r['in_chat_interaction_verified'])
        self.assertFalse(r['request_satisfied'])
    def test_local_browser_surface_cannot_be_claimed_as_in_chat_interaction(self):
        r=self.run_delivery(require_in_chat_preview=True);self.host_observation(r,surface='local_browser')
        r=self.run_delivery();self.assertFalse(r['request_satisfied']);self.assertFalse(r['in_chat_interaction_verified'])
    def test_in_chat_check_must_observe_foil_and_not_accept_truthy_strings(self):
        for defect in ('missing','truthy','empty'):
            with self.subTest(defect=defect):
                r=self.run_delivery(require_in_chat_preview=True);observed=self.host_observation(r)
                if defect=='missing':del observed['checks']['foil_angle']
                elif defect=='truthy':observed['checks']['foil_angle']['passed']='true'
                else:observed['checks']['foil_angle']['observation']=''
                save(self.ws/'host-preview.json',observed)
                self.assertFalse(self.run_delivery()['request_satisfied'])
    def test_limited_host_reports_limitation_and_preserves_completed_files(self):
        for status in ('unsupported','blocked'):
            with self.subTest(status=status):
                r=self.run_delivery(require_in_chat_preview=True);self.host_observation(r,status=status,checks={})
                r=self.run_delivery();self.assertTrue(r['complete']);self.assertFalse(r['request_satisfied'])
                self.assertEqual(r['request_status'],'host_preview_'+status)
                self.assertEqual(r['next_action']['type'],'report_host_limitation')
    def test_mode_specific_host_checks_do_not_require_an_absent_module(self):
        for mode in ('card','html'):
            with self.subTest(mode=mode):
                self.ws=self.root/('run-'+mode)
                r=self.run_delivery(mode,require_in_chat_preview=True);self.host_observation(r)
                r=self.run_delivery(mode);self.assertTrue(r['request_satisfied'])
    def test_host_observation_requires_exact_current_hash(self):
        r=self.run_delivery();save(self.ws/'host-preview.json',{'version':'host-preview-1','status':'available','html_sha256':'0'*64,'observation':'Synthetic host observation, deliberately wrong file.'})
        self.assertFalse(self.run_delivery()['in_chat_preview_verified'])
    def test_no_browser_is_not_complete(self):
        self.dynamic=False;r=self.run_delivery();self.assertFalse(r['complete'])
    def test_static_substitution_in_actual_html_blocked(self):
        self.mutate_html=True;r=self.run_delivery();self.assertFalse(r['complete']);self.assertIsNone(r['primary_output']);self.assertEqual(r['next_action']['type'],'repair_embedding')
    def test_missing_final_review_blocks_html_integration(self):
        e=json.loads((self.art/'art-evidence.json').read_text());del e['reviews']['final'];save(self.art/'art-evidence.json',e)
        r=self.run_delivery();self.assertFalse(r['complete']);self.assertNotIn('html_with_card',r['outputs'])
    def test_changed_evidence_cannot_inherit_previous_pass(self):
        self.run_delivery();(self.art/'art-evidence.json').unlink();r=self.run_delivery();self.assertFalse(r['complete'])
    def test_deleted_output_not_hashed_as_complete(self):
        self.after_gate=lambda ws,o:Path(o['card_front']).unlink();r=self.run_delivery();self.assertFalse(r['complete']);self.assertNotIn('card_front',r['outputs'])
    def test_card_only_does_not_require_galaxy_embedding(self):
        r=self.run_delivery('card');self.assertTrue(r['complete'],r);self.assertNotIn('html',r['outputs'])
    def test_html_only_does_not_require_card_evidence(self):
        (self.art/'art-evidence.json').unlink();r=self.run_delivery('html');self.assertTrue(r['complete'],r)
    def test_legacy_v1_cannot_pass_public_delivery(self):
        d=json.loads((self.art/'art-direction.json').read_text());d['version']='art-direction-1';save(self.art/'art-direction.json',d)
        e=json.loads((self.art/'art-evidence.json').read_text());e['design']=ref(self.art/'art-direction.json');save(self.art/'art-evidence.json',e)
        # Only the old evidence checker is stubbed to model a legacy accepted dossier.
        with patch('twinlight_core.delivery.check_evidence',return_value={'ok':True,'inputs_sha256':{},'evidence_checked':True}):r=self.run_delivery()
        self.assertFalse(r['complete']);self.assertEqual(r['status'],'needs_art_direction')
    def test_export_complete_delivery_has_only_public_artifacts(self):
        self.run_delivery();(self.ws/'private.txt').write_text('TEST PRIVATE EXTRA')
        r=export(self.ws,self.root/'export');self.assertEqual(r['primary_file'],'Twinlight.html')
        with zipfile.ZipFile(r['archive']) as z:
            self.assertNotIn('private.txt',z.namelist());self.assertIn('Twinlight.html',z.namelist());self.assertEqual(len(z.namelist()),6)
            self.assertNotIn('handoff.json',z.namelist());self.assertNotIn('delivery-reply.md',z.namelist())
    def test_export_handoff_points_to_every_actual_export_with_current_bytes(self):
        self.run_delivery();r=export(self.ws,self.root/'export with spaces')
        handoff=json.loads(Path(r['handoff_file']).read_text());reply=Path(r['reply_file']).read_text()
        self.assertFalse(handoff['delivery_sent']);self.assertFalse(r['delivery_sent'])
        self.assertEqual(handoff['attachments'][0]['key'],'html_with_card')
        self.assertEqual({a['key'] for a in handoff['attachments']},{'html_with_card','card_front','card_preview','card_pack','archive'})
        for attachment in handoff['attachments']:
            actual=Path(attachment['path']);self.assertTrue(actual.is_file())
            self.assertEqual(attachment['sha256'],ref(actual)['sha256'])
            self.assertEqual(attachment['bytes'],actual.stat().st_size)
            self.assertIn(attachment['markdown'],reply)
            if attachment['key']=='card_front':
                self.assertIn(attachment['preview_markdown'],reply)
                self.assertTrue(attachment['preview_markdown'].startswith('![闪卡正面]'))
        self.assertNotIn(str(self.ws),reply);self.assertIn('export%20with%20spaces',reply)
    def test_single_module_exports_mention_only_existing_files(self):
        for mode in ('card','html'):
            with self.subTest(mode=mode):
                self.ws=self.root/('run-'+mode);self.run_delivery(mode)
                out=self.root/('export-'+mode);r=export(self.ws,out)
                note=(out/'READ-ME.txt').read_text();reply=Path(r['reply_file']).read_text()
                absent='Twinlight.html' if mode=='card' else 'card-preview.html'
                self.assertNotIn(absent,note);self.assertNotIn(absent,reply)
                self.assertEqual(len(r['attachments']),4 if mode=='card' else 2)
    def test_export_preserves_unmet_chat_requirement_in_reply_and_receipt(self):
        self.run_delivery(require_in_chat_preview=True);r=export(self.ws,self.root/'export')
        self.assertTrue(r['complete']);self.assertFalse(r['request_satisfied'])
        self.assertIn('聊天内直接交互尚未完成',Path(r['reply_file']).read_text())
        self.assertFalse(json.loads((self.root/'export/delivery.json').read_text())['request_satisfied'])
    def test_portable_receipt_excludes_host_private_observations_and_paths(self):
        r=self.run_delivery(require_in_chat_preview=True)
        self.host_observation(r,artifact_reference=str(self.ws/'private-host-entry.html'),
                              observation='PRIVATE HOST OBSERVATION FOR THIS SYNTHETIC TEST ONLY')
        self.run_delivery();r=export(self.ws,self.root/'export')
        with zipfile.ZipFile(r['archive']) as archive:
            raw=archive.read('delivery.json').decode('utf-8');receipt=json.loads(raw)
        self.assertTrue(receipt['request_satisfied'])
        self.assertEqual(set(receipt['host_preview']),{'version','status','html_sha256','surface'})
        self.assertNotIn(str(self.ws),raw);self.assertNotIn('PRIVATE HOST OBSERVATION',raw)
        self.assertIn('private-host-entry.html',(self.ws/'delivery-report.json').read_text())
    def test_export_refuses_mismatched_request_receipt(self):
        self.run_delivery(require_in_chat_preview=True)
        receipt=json.loads((self.ws/'delivery-report.json').read_text());receipt['delivery_requirements']['in_chat_preview']=False
        save(self.ws/'delivery-report.json',receipt)
        with self.assertRaisesRegex(ValueError,'Inconsistent delivery requirements'):export(self.ws,self.root/'export')
    def test_export_rechecks_interaction_success_instead_of_trusting_a_boolean(self):
        self.run_delivery(require_in_chat_preview=True)
        for name in ('run-report.json','delivery-report.json'):
            doc=json.loads((self.ws/name).read_text());doc['request_satisfied']=True;save(self.ws/name,doc)
        with self.assertRaisesRegex(ValueError,'Inconsistent request_satisfied'):export(self.ws,self.root/'export')
    def test_sandbox_links_cannot_be_invented_for_local_files(self):
        self.run_delivery()
        with self.assertRaisesRegex(ValueError,'actual exported files under /mnt/data'):
            export(self.ws,self.root/'export',link_style='sandbox')
        self.assertFalse((self.root/'export').exists())
    def test_export_rejects_incomplete(self):
        self.dynamic=False;self.run_delivery()
        with self.assertRaises(ValueError):export(self.ws,self.root/'export')
    def test_export_rejects_modified_html(self):
        r=self.run_delivery();Path(r['primary_output']).write_text('MODIFIED')
        with self.assertRaises(ValueError):export(self.ws,self.root/'export')
    def test_export_refuses_base_as_primary(self):
        r=self.run_delivery();r['primary_output']=r['outputs']['html'];save(self.ws/'run-report.json',r)
        with self.assertRaises(ValueError):export(self.ws,self.root/'export')
    def test_export_will_not_overwrite(self):
        self.run_delivery();out=self.root/'export';out.mkdir();(out/'keep').write_text('keep')
        with self.assertRaises(ValueError):export(self.ws,out)
        self.assertEqual((out/'keep').read_text(),'keep')
    def test_export_will_not_write_inside_working_run(self):
        self.run_delivery()
        with self.assertRaises(ValueError):export(self.ws,self.ws/'export')
    def test_receipt_keeps_private_draft(self):
        self.run_delivery();r=json.loads((self.ws/'delivery-report.json').read_text());self.assertTrue(r['draft']);self.assertFalse(r['share_allowed'])

if __name__=='__main__':unittest.main()
