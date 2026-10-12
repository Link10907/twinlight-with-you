"""SYNTHETIC ONLY: portable routing/build tests, never real artwork approvals."""
import copy,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from split_fixtures import person,native
from twinlight_core.common import load,save
from twinlight_core import portable,galaxy_only,lite
from twinlight_core.site import template_source_hashes
from twinlight_core.host_contract import assess
from quality_fixtures import host
from package_skill import resource_files


def caps(status='available'):
    return {'image':{'status':status,'reason':'SYNTHETIC: actual route behavior fixture, not a live capability observation','context_isolation':'contextual_native_tool'},
            'files':{'status':'available'},'reviewer':{'mode':'self'},'browser':{'status':'unavailable'}}

class PortableRouteTests(unittest.TestCase):
    def test_available_native_without_api_key_routes_full(self):
        r=portable.route(caps());self.assertEqual(r['mode'],'full');self.assertFalse(r['requires_api_key'])
    def test_absent_routes_no_card(self):
        r=portable.route(caps('unavailable'));self.assertEqual(r['mode'],'html-only');self.assertFalse(r['card_enabled'])
    def test_unknown_not_absent(self):self.assertEqual(portable.route(caps('unknown'))['status'],'inspect_image_tools')
    def test_temporary_failure_not_absent(self):self.assertIsNone(portable.route(caps('temporarily_blocked'))['mode'])
    def test_missing_browser_does_not_block_native_image(self):self.assertEqual(portable.route(caps())['status'],'ready')
    def test_self_review_not_reported_independent(self):self.assertEqual(portable.route(caps())['review_mode'],'self')
    def test_absent_needs_observation(self):
        c=caps('unavailable');c['image'].pop('reason')
        with self.assertRaises(ValueError):portable.route(c)
    def test_model_brand_not_used_as_capability(self):
        c=caps();c['provider']='DeepSeek';self.assertEqual(portable.route(c)['mode'],'full')
        c['provider']='ChatGPT';c['image']['status']='unavailable';self.assertEqual(portable.route(c)['mode'],'html-only')
    def test_no_file_capability_precise_block(self):
        c=caps();c['files']['status']='unavailable';self.assertEqual(portable.route(c)['status'],'artifact_capability_blocked')
    def test_strict_independent_gate_unchanged(self):
        c=host();c['reviewer']['isolated_session']=False;self.assertFalse(assess(c,'card')['ok'])

class PortableBuildTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);self.work=self.root/'work'
        self.input=self.root/'person.json';save(self.input,person())
    def test_cardless_accepts_no_card_content(self):
        p=person();p.pop('card');save(self.input,p)
        r=portable.run(self.input,self.work,caps('unavailable'))
        self.assertEqual(r['mode'],'html-only');self.assertEqual(r['status'],'review_required');self.assertFalse(r['complete'])
        prof=load(self.work/'site-task/site/profile.json');self.assertIsNone(prof['persona']);self.assertFalse(prof['features']['card'])
    def test_cardless_does_not_generate_any_card_asset(self):
        with patch('twinlight_core.site.placeholder_layers',side_effect=AssertionError('NO PLACEHOLDERS')):
            portable.run(self.input,self.work,caps('unavailable'))
        self.assertFalse((self.work/'card-task').exists())
        html=(self.work/'site-task/site/index.html').read_text()
        for bad in ('id="identityScene"','id="cardExportReview"','const HOLO_LAYERS','const CARD_PERSONA','const CARD_ART',"id='v8CardShortcut'"):
            self.assertNotIn(bad,html)
        self.assertIn('返回我的星系',html)
    def test_original_template_hashes_unchanged(self):
        before=template_source_hashes();portable.run(self.input,self.work,caps('unavailable'));self.assertEqual(before,template_source_hashes())
    def test_cardless_reconstruction_detects_mutation(self):
        portable.run(self.input,self.work,caps('unavailable'));folder=self.work/'site-task/site'
        self.assertTrue(galaxy_only.verify(folder)['ok']);p=folder/'index.html';p.write_text(p.read_text()+'changed')
        with self.assertRaises(ValueError):galaxy_only.verify(folder)
    def test_full_does_not_build_before_native_images(self):
        r=portable.run(self.input,self.work,caps());self.assertEqual(r['status'],'native_image_generation_required')
        self.assertFalse((self.work/'site-task').exists());self.assertEqual(r['image_calls_performed_by_cli'],0)
    def test_no_silent_mode_change(self):
        portable.run(self.input,self.work,caps())
        with self.assertRaises(ValueError):portable.run(self.input,self.work,caps('unavailable'))
    def test_no_silent_person_change(self):
        portable.run(self.input,self.work,caps('unavailable'));p=person();p['name']='另一个人';save(self.input,p)
        with self.assertRaises(ValueError):portable.run(self.input,self.work,caps('unavailable'))
    def test_review_requires_observations_and_current_target(self):
        r=self.work/'review.json';save(r,{'stage':'site','target_sha256':'old','method':'self'})
        with self.assertRaises(ValueError):portable.review_check(r,'site','new','self')
    def test_synthetic_self_review_separate_from_all_checks(self):
        r=portable.run(self.input,self.work,caps('unavailable'))
        review={'stage':'site','target_sha256':r['html_sha256'],'method':'self','verdict':'accept',
                'checks':{k:True for k in portable.CHECKS['site']},'observations':'SYNTHETIC UNIT TEST ONLY. Not a real visual review.'}
        save(self.work/'review-site.json',review)
        r=portable.run(self.input,self.work,caps('unavailable'))
        self.assertTrue(r['complete']);self.assertFalse(r['all_checks_passed']);self.assertEqual(r['validation_level'],'host_self_review')
        dest=self.root/'delivery';d=portable.deliver(self.work,dest)
        self.assertEqual(set(d['files']),{'index.html','delivery.json','README.txt'})
        with zipfile.ZipFile(d['zip']) as z:self.assertFalse(any('card' in n for n in z.namelist()))
    def test_text_only_cardless_source_review_without_visual_claim(self):
        c=caps('unavailable');c['reviewer']['mode']='unavailable'
        r=portable.run(self.input,self.work,c)
        save(self.work/'review-site.json',{'stage':'site','target_sha256':r['html_sha256'],'method':'source','verdict':'accept',
             'checks':{k:True for k in portable.CHECKS['site-source']},'observations':'SYNTHETIC SOURCE CHECK ONLY. No actual visual approval.'})
        r=portable.run(self.input,self.work,c)
        self.assertTrue(r['complete']);self.assertEqual(r['validation_level'],'source_review_only')
        self.assertFalse(r['all_checks_passed']);self.assertFalse(r['site_review']['visual_review_performed'])
        d=portable.deliver(self.work,self.root/'delivery');self.assertEqual(d['mode'],'html-only')
    def test_source_only_cannot_approve_a_card(self):
        p=self.root/'review.json';save(p,{'stage':'card','target_sha256':'test','method':'source','verdict':'accept',
            'checks':{k:True for k in portable.CHECKS['card']},'observations':'SYNTHETIC SOURCE CHECK ONLY. Not actual card review.'})
        with self.assertRaises(ValueError):portable.review_check(p,'card','test','unavailable',allow_source=True)
    def test_no_export_after_review_is_revoked(self):
        r=portable.run(self.input,self.work,caps('unavailable'))
        rev={'stage':'site','target_sha256':r['html_sha256'],'method':'self','verdict':'accept',
             'checks':{k:True for k in portable.CHECKS['site']},'observations':'SYNTHETIC UNIT TEST ONLY. Not a real visual review.'}
        save(self.work/'review-site.json',rev);portable.run(self.input,self.work,caps('unavailable'))
        rev['verdict']='revise';save(self.work/'review-site.json',rev)
        with self.assertRaises(ValueError):portable.deliver(self.work,self.root/'delivery')
    def test_runtime_known_failure_still_blocks(self):
        r=portable.run(self.input,self.work,caps('unavailable'))
        rev={'stage':'site','target_sha256':r['html_sha256'],'method':'self','verdict':'accept',
             'checks':{k:True for k in portable.CHECKS['site']},'observations':'SYNTHETIC UNIT TEST ONLY. Not a real visual review.'}
        save(self.work/'review-site.json',rev);save(self.work/'runtime-check.json',{'status':'limited','html_sha256':r['html_sha256'],'checks':[{'passed':False}]})
        with self.assertRaises(ValueError):portable.run(self.input,self.work,caps('unavailable'))
    def test_no_full_site_when_card_review_not_accepted(self):
        self.work.mkdir();layers=native(self.work/'card-task/native',lite.persona_digest(person()))
        with patch.object(portable,'generation_check',return_value={'SYNTHETIC':True}):
            r=portable.run(self.input,self.work,caps(),layers=layers)
        self.assertEqual(r['status'],'review_required');self.assertFalse((self.work/'site-task').exists())
    def test_full_embeds_same_bytes_with_mocked_review_only(self):
        self.work.mkdir();layers=native(self.work/'card-task/native',lite.persona_digest(person()))
        fake={'ok':True,'method':'self','status':'accepted','SYNTHETIC':True}
        with patch.object(portable,'generation_check',return_value={'SYNTHETIC':True}),patch.object(portable,'review_check',return_value=fake):
            r=portable.run(self.input,self.work,caps(),layers=layers)
        self.assertTrue(r['complete']);self.assertTrue(r['card_enabled']);self.assertFalse(r['all_checks_passed'])
        self.assertTrue((self.work/'site-task/site/index.html').is_file())

if __name__=='__main__':unittest.main()
