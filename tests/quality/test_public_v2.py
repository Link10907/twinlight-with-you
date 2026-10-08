"""SYNTHETIC public-controller/packaging regressions; no providers are invoked."""
import copy,json,tempfile,unittest,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from quality_fixtures import ROOT,PERSONA,host,save,ref,sign,release
from twinlight_core.host_contract import load_assessment
from twinlight_core.art_quality import sha256
from twinlight_core.delivery import deliver
from twinlight_core.export_delivery import export
from twinlight_core.review_exchange import activate_release
from twinlight_core.generation_plan import bind_review
from twinlight_core.run import run
from package_skill import resource_files


class PublicTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name).resolve()
        self.hp=self.root/'host.json';save(self.hp,host())
    def fake_core(self,input_path,workspace,**kwargs):
        workspace.mkdir(exist_ok=True)
        out=workspace/'html.html';out.write_text('SYNTHETIC CANDIDATE')
        if not (workspace/'run-state.json').exists():save(workspace/'run-state.json',{'stages':{}})
        return {'mode':'html','status':'files_ready','ok':True,'stages':{},'outputs':{'html':str(out)},
                'dynamic_verified':True,'next_action':None}
    def test_no_host_stops_public_completion(self):
        inp=self.root/'input.json';save(inp,{});w=self.root/'run'
        r=deliver(self.fake_core,inp,w,mode='html')
        self.assertFalse(r['complete']);self.assertEqual(r['status'],'capability_blocked');self.assertTrue(r['files_built'])
    def test_known_host_still_needs_real_release(self):
        inp=self.root/'input.json';save(inp,{});w=self.root/'run'
        r=deliver(self.fake_core,inp,w,mode='html',host_capabilities=self.hp)
        self.assertFalse(r['complete']);self.assertEqual(r['status'],'needs_release_review')
        self.assertIn('--host-capabilities',r['next_action']['resume'])
    def test_host_requirement_survives_resume(self):
        inp=self.root/'input.json';save(inp,{});w=self.root/'run'
        deliver(self.fake_core,inp,w,mode='html',host_capabilities=self.hp)
        r=deliver(self.fake_core,inp,w,mode='html')
        self.assertTrue(r['host_contract']['ok']);self.assertEqual(r['host_contract']['source'],str(self.hp))
    def test_host_downgrade_blocks_resume(self):
        inp=self.root/'input.json';save(inp,{});w=self.root/'run'
        deliver(self.fake_core,inp,w,mode='html',host_capabilities=self.hp)
        v=host();v['reviewer']['isolated_session']=False;save(self.hp,v)
        self.assertEqual(deliver(self.fake_core,inp,w,mode='html')['status'],'capability_blocked')
    def test_inchat_requirement_survives_resume(self):
        inp=self.root/'input.json';save(inp,{});w=self.root/'run'
        deliver(self.fake_core,inp,w,mode='html',host_capabilities=self.hp,require_in_chat_preview=True)
        r=deliver(self.fake_core,inp,w,mode='html')
        self.assertTrue(r['delivery_requirements']['in_chat_preview']);self.assertFalse(r['request_satisfied'])
    def test_missing_host_does_not_remove_candidate(self):
        inp=self.root/'input.json';save(inp,{});w=self.root/'run'
        r=deliver(self.fake_core,inp,w,mode='html')
        self.assertTrue(Path(r['outputs']['html']).is_file());self.assertFalse(r['complete'])
    def prepare_export(self):
        w=self.root/'run';w.mkdir();outputs,_=release(w,'card')
        c=load_assessment(self.hp,'card');primary=outputs['card_preview']
        r={'mode':'card','status':'files_ready','complete':True,'dynamic_verified':True,'outputs':outputs,'primary_output':primary,
           'host_contract':c,'delivery_requirements':{'in_chat_preview':False},'host_preview':{'status':'not_tested'}}
        receipt={**r,'draft':True,'share_allowed':False,'outputs_sha256':{k:sha256(Path(p)) for k,p in outputs.items()}}
        save(w/'run-report.json',r);save(w/'delivery-report.json',receipt)
        save(w/'run-state.json',{'layers_source':str(w/'layers.json'),'persona_digest':PERSONA})
        return w
    def test_export_rechecks_revoked_upstream(self):
        w=self.prepare_export()
        with patch('twinlight_core.art_quality.check_evidence',return_value={'ok':False}):
            with self.assertRaisesRegex(ValueError,'Upstream artwork review'):export(w,self.root/'export')
        self.assertFalse((self.root/'export').exists())
    def test_export_rechecks_changed_capability_source(self):
        w=self.prepare_export();v=host();v['runtime']['webgl']=False;save(self.hp,v)
        with self.assertRaisesRegex(ValueError,'Host capability'):export(w,self.root/'export')
    def test_activate_preserves_replaced_verdict(self):
        w=self.root/'run';w.mkdir();outputs,r=release(w,'card');save(w/'run-report.json',{'mode':'card','outputs':outputs})
        before=(w/'release-review.json').read_bytes()
        r.update(decision='revise',blockers=[{'object':'subject','location':'left edge','evidence':'SYNTHETIC defect','repair':'Repair one layer'}]);r=sign(w,r,'second');save(w/'next.json',r)
        result=activate_release(w,w/'next.json');self.assertFalse(result['complete'])
        self.assertEqual(json.loads((w/'release-review.json').read_text())['decision'],'revise')
        self.assertTrue(any(p.read_bytes()==before for p in (w/'review-history').glob('*.json')))
    def test_blocked_art_review_replaces_old_pass(self):
        w=self.root/'card';w.mkdir();save(w/'layers.json',{'persona_digest':PERSONA})
        targets={'prototype':{'persona_digest':PERSONA}};ev={'reviews':{'prototype':{'file':'old.json','sha256':'a'*64}}}
        r={'stage':'prototype','targets':targets['prototype'],'decision':'blocked','blockers':[{'object':'viewer','location':'review host','evidence':'No live image viewer','repair':'Use actual visual reviewer'}]}
        r=sign(w,r);save(w/'new-review.json',r)
        with patch('twinlight_core.art_quality.snapshot',return_value=(targets,ev,{},{})):
            result=bind_review(w/'layers.json',w/'new-review.json')
        self.assertFalse(result['ok']);self.assertTrue(result['bound']);self.assertEqual(result['status'],'reviewer_blocked')
        self.assertEqual(json.loads((w/'art-evidence.json').read_text())['reviews']['prototype']['file'],'new-review.json')
    def test_packager_includes_reviewer_and_reproducible_tests(self):
        names={p.relative_to(ROOT).as_posix() for p in resource_files(ROOT)}
        for n in ('REVIEWER.md','scripts/preflight.py','scripts/verify_skill.py','tests/quality/test_public_v2.py'):
            self.assertIn(n,names)
        self.assertFalse(any(n.endswith(('.ttf','.otf','.ttc','.woff','.woff2')) for n in names))
    def test_real_public_card_candidate_does_not_complete(self):
        data={'twinlight':'card-1','name':'测试','summarizer':'SYNTHETIC',
              'card':{'title':'测试卡','english_title':'TEST CARD','keywords':['合成','测试','隔离'],
                      'tagline':'仅用于程序测试','reflection':'这是隔离的合成测试材料，不是个人定义。'}}
        inp=self.root/'card.json';save(inp,data)
        result=run(inp,self.root/'actual-run',mode='card',no_browser=True,host_capabilities=self.hp)
        self.assertFalse(result['complete']);self.assertEqual(result['status'],'needs_card')
        self.assertTrue((self.root/'actual-run'/'run-state.json').is_file())


if __name__=='__main__':unittest.main()
