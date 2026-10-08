"""SYNTHETIC local HTTP/process integration tests. No live model or artwork approval.

The production HTTP/JSON/attachment code really runs against a loopback fixture.
The fixture is explicitly synthetic; it tests wiring, not image/reviewer quality.
"""
from __future__ import annotations
import base64,copy,io,json,os,subprocess,sys,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from quality_fixtures import ROOT,PERSONA,host,design,save,ref
from twinlight_core.art_quality import sha256,check_evidence
from twinlight_core.generation_plan import write_plan
from twinlight_core.provider_runtime import generate,vision,image_input,ExecutionError,endpoint,extract_json_text,model_name
from twinlight_core.execution_bridge import doctor,probe_reviewer,invoke_image,invoke_review,validate_verdict,write_host
from twinlight_core.review_exchange import attach_runtime_evidence


def png(size=(600,800),transparent=False):
    im=Image.new('RGBA',size,(40,60,80,0 if transparent else 255))
    if transparent:im.putpixel((30,30),(80,90,100,255))
    buf=io.BytesIO();im.save(buf,format='PNG');return buf.getvalue()


class HttpFixture:
    def __init__(self):
        self.requests=[];self.image=png();self.verdict='accept';self.http_status=200;self.fault=None
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.requests.append((self.path,dict(self.headers),body))
                if owner.http_status!=200:
                    self.send_response(owner.http_status);self.end_headers();self.wfile.write(b'{"error":"SYNTHETIC FIXTURE"}');return
                if self.path=='/v1/images/edits':res={'created':1,'data':[{'b64_json':base64.b64encode(owner.image).decode()}]}
                else:
                    text=body['input'][0]['content'][0]['text'] if 'input' in body else body['messages'][0]['content'][-1]['text']
                    if 'VISION TRANSPORT probe' in text:
                        verdict={'has_image':True,'description':'SYNTHETIC fixture sees an illustrated scene; this is a transport test, never a real observation.','limitations':[]}
                    else:
                        template=text.split('RESPONSE TEMPLATE (immutable targets/evidence; fill only decision, checks observations/pass, blockers):\n',1)[1]
                        verdict=json.JSONDecoder().raw_decode(template)[0]
                        verdict['decision']=owner.verdict
                        verdict['blockers']=[] if owner.verdict=='accept' else [{'object':'prototype','location':'center','evidence':'SYNTHETIC deliberate rejection','repair':'Redo the synthetic test candidate only'}]
                        for check in verdict['checks'].values():check.update(passed=owner.verdict=='accept',observation='SYNTHETIC TRANSPORT FIXTURE, NOT A REAL AESTHETIC ASSESSMENT.')
                        if owner.fault=='targets':verdict['targets']={}
                        if owner.fault=='runtime':verdict['runtime']={'webgl_ready':True}
                    serialized=json.dumps(verdict,ensure_ascii=False)
                    if self.path=='/v1/messages':res={'stop_reason':'end_turn','content':[{'type':'text','text':serialized}]}
                    else:res={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':serialized}]}]}
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('x-request-id','SYNTHETIC-HTTP-TEST');self.end_headers();self.wfile.write(json.dumps(res).encode())
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    @property
    def url(self):return f'http://127.0.0.1:{self.server.server_port}/v1'
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join()


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.server=HttpFixture()
    @classmethod
    def tearDownClass(cls):cls.server.close()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.server.requests.clear();self.server.image=png();self.server.verdict='accept';self.server.http_status=200;self.server.fault=None
        self.env=patch.dict(os.environ,{'TWINLIGHT_TEST_KEY':'SYNTHETIC_NOT_A_REAL_KEY'});self.env.start();self.addCleanup(self.env.stop)
        common={'base_url':self.server.url,'allow_local_http':True,'model':'SYNTHETIC-MODEL','api_key_env':'TWINLIGHT_TEST_KEY','timeout_seconds':5}
        self.ic={**common,'kind':'openai_images','native_canvas':[600,800]};self.rc={**common,'kind':'openai_responses'}
        self.cfg={'version':'twinlight-execution-1','image':self.ic,'reviewer':self.rc};self.cp=self.root/'execution.json';save(self.cp,self.cfg)
        self.im=self.root/'reference.png';self.im.write_bytes(png());self.hp=self.root/'host.json';save(self.hp,host())
    def callout(self,name='call'):
        out=self.root/name;out.mkdir();return out
    def prepare(self):
        run=self.root/'run';run.mkdir();card=run/'card';card.mkdir();save(run/'run-state.json',{'mode':'both','persona_digest':PERSONA})
        save(card/'design.json',design(style='twinlight-collector'));write_plan(card/'design.json',card,canvas=(600,800),capabilities=host()['image'])
        return run,card,card/'generation-plan.json'
    def produce_and_packet(self):
        run,card,plan=self.prepare();invoke_image(self.cp,plan,'prototype',run,self.hp,card/'calls/image-1',allowed=True)
        packet=card/'packet'
        p=subprocess.run([sys.executable,str(ROOT/'scripts/reviewer.py'),'packet','--stage','prototype','--layers',str(card/'layers.json'),'--out',str(packet)],capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        return run,card,plan,packet
    def test_doctor_never_calls_model(self):
        r=doctor(self.cp);self.assertTrue(r['ok']);self.assertEqual(len(self.server.requests),0);self.assertFalse(r['routes']['reviewer']['live_verified'])
    def test_missing_key_is_precise_and_offline(self):
        self.ic['api_key_env']='SYNTHETIC_ABSENT_KEY';save(self.cp,self.cfg);r=doctor(self.cp)
        self.assertFalse(r['ok']);self.assertIn('environment_variable_missing:SYNTHETIC_ABSENT_KEY',r['routes']['image']['gaps']);self.assertFalse(self.server.requests)
    def test_no_call_without_opt_in(self):
        with self.assertRaisesRegex(ExecutionError,'allow-provider-calls'):generate(self.ic,'SYNTHETIC task',[self.im],[600,800],False,self.callout(),allowed=False)
        self.assertFalse(self.server.requests)
    def test_actual_http_image_prompt_and_reference_bytes(self):
        image,_=generate(self.ic,'ONLY THIS SINGLE IMAGE TASK',[self.im],[600,800],False,self.callout(),allowed=True)
        path,headers,body=self.server.requests[0]
        self.assertEqual(path,'/v1/images/edits');self.assertEqual(body['prompt'],'ONLY THIS SINGLE IMAGE TASK')
        self.assertEqual(base64.b64decode(body['images'][0]['image_url'].split(',')[1]),self.im.read_bytes())
        self.assertNotIn('messages',body);self.assertNotIn('conversation',body);self.assertEqual(image.read_bytes(),self.server.image)
    def test_secret_not_saved_in_request(self):
        out=self.callout();generate(self.ic,'SYNTHETIC TASK',[self.im],[600,800],False,out,allowed=True)
        self.assertNotIn('SYNTHETIC_NOT_A_REAL_KEY',''.join(p.read_text() for p in out.glob('*.json')))
    def test_receipt_keeps_raw_response_hash(self):
        out=self.callout();_,r=generate(self.ic,'SYNTHETIC TASK',[self.im],[600,800],False,out,allowed=True)
        self.assertEqual(r['provider_response']['sha256'],sha256(out/'provider-response.raw.json'));self.assertFalse(r['native_bytes_modified'])
    def test_native_transparent_output(self):
        self.server.image=png(transparent=True);image,_=generate(self.ic,'SYNTHETIC ALPHA',[self.im],[600,800],True,self.callout(),allowed=True)
        self.assertEqual(image.read_bytes(),self.server.image);self.assertEqual(self.server.requests[0][2]['background'],'transparent')
    def test_opaque_subject_rejected(self):
        out=self.callout()
        with self.assertRaisesRegex(ExecutionError,'opaque pixels'):generate(self.ic,'SYNTHETIC ALPHA',[self.im],[600,800],True,out,allowed=True)
        self.assertTrue((out/'returned-image.png').exists())
    def test_wrong_canvas_preserved_not_rescaled(self):
        self.server.image=png((640,800));out=self.callout()
        with self.assertRaisesRegex(ExecutionError,'never rescale'):generate(self.ic,'SYNTHETIC CANVAS',[self.im],[600,800],False,out,allowed=True)
        self.assertEqual((out/'returned-image.png').read_bytes(),self.server.image)
    def test_bad_native_image_keeps_bytes(self):
        self.server.image=b'<html>not artwork</html>';out=self.callout()
        with self.assertRaises(ExecutionError):generate(self.ic,'SYNTHETIC BAD',[self.im],[600,800],False,out,allowed=True)
        self.assertEqual((out/'returned-image.png').read_bytes(),self.server.image)
    def test_http_429_not_retried(self):
        self.server.http_status=429
        with self.assertRaisesRegex(ExecutionError,'429'):generate(self.ic,'SYNTHETIC',[self.im],[600,800],False,self.callout(),allowed=True)
        self.assertEqual(len(self.server.requests),1)
    def test_http_401_not_retried(self):
        self.server.http_status=401
        with self.assertRaisesRegex(ExecutionError,'401'):vision(self.rc,'SYNTHETIC',[self.im],self.callout(),allowed=True)
        self.assertEqual(len(self.server.requests),1)
    def test_openai_vision_request_is_fresh_and_toolless(self):
        probe_reviewer(self.cp,self.im,self.root/'probe',allowed=True);body=self.server.requests[-1][2]
        self.assertNotIn('tools',body);self.assertNotIn('previous_response_id',body);self.assertNotIn('conversation',body);self.assertIs(body['store'],False)
        self.assertTrue(any(x['type']=='input_image' for x in body['input'][0]['content']))
    def test_anthropic_explicit_image_transport(self):
        self.cfg['reviewer']['kind']='anthropic_messages';save(self.cp,self.cfg);r=probe_reviewer(self.cp,self.im,self.root/'probe',allowed=True)
        self.assertTrue(r['ok']);body=self.server.requests[-1][2]
        self.assertNotIn('tools',body);self.assertEqual(body['messages'][0]['content'][1]['type'],'image')
    def test_review_probe_is_not_art_approval(self):
        r=probe_reviewer(self.cp,self.im,self.root/'probe',allowed=True);self.assertTrue(r['independent_call_performed']);self.assertFalse(r['artwork_approved'])
    def test_register_through_executed_http_transport(self):
        run,card,plan=self.prepare();r=invoke_image(self.cp,plan,'prototype',run,self.hp,card/'calls/image-1',allowed=True)
        self.assertTrue(r['ok']);self.assertFalse(r['artwork_approved']);self.assertEqual(read(card/'art-evidence.json')['images']['prototype']['sha256'],sha256(Path(r['image'])))
    def test_complete_prototype_call_review_bind_next_layer_phase(self):
        run,card,plan,packet=self.produce_and_packet()
        r=invoke_review(self.cp,packet,card,self.hp,card/'calls/review-1',allowed=True,layers=card/'layers.json')
        self.assertTrue(r['ok'],r);self.assertTrue(check_evidence(card/'layers.json',PERSONA,stage='prototype')['ok'])
        layered=write_plan(card/'art-direction.json',card,phase='layers',capabilities=host()['image'])
        self.assertEqual(layered['phase'],'layers');self.assertEqual(len(self.server.requests),2)
        self.assertFalse(r['release_authorized'])
    def test_revise_imported_and_blocks_next_stage(self):
        run,card,plan,packet=self.produce_and_packet();self.server.verdict='revise'
        r=invoke_review(self.cp,packet,card,self.hp,card/'calls/review-1',allowed=True,layers=card/'layers.json')
        self.assertFalse(r['ok']);self.assertTrue(r['import_ok']);self.assertEqual(r['decision'],'revise')
        self.assertFalse(check_evidence(card/'layers.json',PERSONA,stage='prototype')['ok'])
        with self.assertRaises(ValueError):write_plan(card/'art-direction.json',card,phase='layers',capabilities=host()['image'])
    def test_blocked_is_not_approved(self):
        run,card,plan,packet=self.produce_and_packet();self.server.verdict='blocked'
        r=invoke_review(self.cp,packet,card,self.hp,card/'calls/review-1',allowed=True,layers=card/'layers.json')
        self.assertEqual(r['decision'],'blocked');self.assertFalse(r['ok'])
    def test_model_cannot_change_targets(self):
        run,card,plan,packet=self.produce_and_packet();self.server.fault='targets'
        with self.assertRaises(ValueError):invoke_review(self.cp,packet,card,self.hp,card/'calls/review-1',allowed=True)
        self.assertTrue((card/'calls/review-1/review-response.json').exists());self.assertFalse((card/'calls/review-1/imported-review.json').exists())
    def test_mutated_packet_prevents_provider_call(self):
        run,card,plan,packet=self.produce_and_packet();entry=read(packet/'packet.json')['attachments'][0];(packet/entry['file']).write_bytes(b'CHANGED')
        before=len(self.server.requests)
        with self.assertRaises(ValueError):invoke_review(self.cp,packet,card,self.hp,card/'calls/review-1',allowed=True)
        self.assertEqual(before,len(self.server.requests))
    def test_duplicate_image_directory_prevents_second_charge(self):
        run,card,plan=self.prepare();out=card/'calls/image-1';invoke_image(self.cp,plan,'prototype',run,self.hp,out,allowed=True)
        with self.assertRaises(ValueError):invoke_image(self.cp,plan,'prototype',run,self.hp,out,allowed=True)
        self.assertEqual(len(self.server.requests),1)
    def test_failed_call_reservation_not_cleared(self):
        run,card,plan=self.prepare();self.server.http_status=429
        with self.assertRaises(ValueError):invoke_image(self.cp,plan,'prototype',run,self.hp,card/'calls/image-1',allowed=True)
        self.assertEqual(len(read(run/'production-attempts.json')['attempts']),1)
    def test_host_requires_actual_probe(self):
        bad=self.root/'bad.json';save(bad,{'ok':False});bp=self.root/'browser.json';save(bp,{'version':'browser-probe-1','browser_started':True,'webgl':True})
        with self.assertRaisesRegex(ValueError,'real independent'):write_host(self.cp,bad,bp,self.root/'out.json')
    def test_host_from_completed_probe_no_platform_ids(self):
        probe_reviewer(self.cp,self.im,self.root/'probe',allowed=True);bp=self.root/'browser.json';save(bp,{'version':'browser-probe-1','browser_started':True,'webgl':True})
        r=write_host(self.cp,self.root/'probe/probe.json',bp,self.root/'observed-host.json')
        self.assertTrue(r['ok']);self.assertFalse(r['image_service_live_verified']);h=read(self.root/'observed-host.json');self.assertIsNone(h['producer_session_id']);self.assertFalse(h['reviewer']['read_only_inputs'])
    def test_modified_probe_not_imported(self):
        probe_reviewer(self.cp,self.im,self.root/'probe',allowed=True);(self.root/'probe/probe-answer.json').write_text('{}')
        bp=self.root/'browser.json';save(bp,{'version':'browser-probe-1','browser_started':True,'webgl':True})
        with self.assertRaisesRegex(ValueError,'changed'):write_host(self.cp,self.root/'probe/probe.json',bp,self.root/'h.json')


def read(p):return json.loads(p.read_text())

class PureTransportTests(unittest.TestCase):
    def test_http_remote_rejected(self):
        with self.assertRaises(ExecutionError):endpoint({'base_url':'http://example.com/v1','allow_local_http':True},'/responses')
    def test_endpoint_credentials_rejected(self):
        with self.assertRaises(ExecutionError):endpoint({'base_url':'https://user:password@example.com/v1'},'')
    def test_loopback_needs_explicit_setting(self):
        with self.assertRaises(ExecutionError):endpoint({'base_url':'http://127.0.0.1:99/v1'},'')
    def test_invalid_json_not_repaired(self):
        with self.assertRaises(ExecutionError):extract_json_text('I approve it, great.')
    def test_fenced_json_is_losslessly_parsed(self):self.assertEqual(extract_json_text('```json\n{"decision":"revise"}\n```'),{'decision':'revise'})
    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ExecutionError):extract_json_text('{"decision":"revise","decision":"accept"}')
    def test_dynamic_accept_without_runtime_rejected(self):
        frozen={'stage':'final','targets':{},'checks':{'foil':{}}};raw={'stage':'final','targets':{},'checks':{'foil':{'passed':True,'observation':'SYNTHETIC observation long enough.'}},'decision':'accept','blockers':[]}
        with self.assertRaisesRegex(ExecutionError,'without actual browser'):validate_verdict(raw,frozen)
    def test_fallback_accept_rejected(self):
        r={'stage':'release','targets':{'mode':'card'},'checks':{'foil':{'passed':True,'observation':'SYNTHETIC observation long enough.'}},'decision':'accept','blockers':[],'runtime':{'webgl_ready':False,'fallback':True}}
        with self.assertRaisesRegex(ExecutionError,'fallback'):validate_verdict(r,r)
    def test_noop_approval_with_failed_check_rejected(self):
        r={'stage':'prototype','targets':{},'checks':{'style':{'passed':False,'observation':'SYNTHETIC no style.'}},'decision':'accept','blockers':[]}
        with self.assertRaisesRegex(ExecutionError,'failed'):validate_verdict(r,r)
    def test_oversized_merger_rejected(self):
        r={'stage':'release','targets':{'mode':'both'},'checks':{'foil':{'passed':True,'observation':'SYNTHETIC long enough observation.'}},'decision':'accept','blockers':[],
           'runtime':{'webgl_ready':True,'fallback':False,'merge_seconds':20}}
        with self.assertRaisesRegex(ExecutionError,'0–15'):validate_verdict(r,r)
    def test_runtime_rewrite_rejected(self):
        f={'stage':'prototype','targets':{},'checks':{'style':{}},'runtime':{'webgl_ready':False}}
        r={'stage':'prototype','targets':{},'checks':{'style':{'passed':False,'observation':'SYNTHETIC'}},'decision':'blocked','blockers':[],'runtime':{'webgl_ready':True}}
        with self.assertRaisesRegex(ExecutionError,'immutable'):validate_verdict(r,f)



class CommandTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.im=self.root/'source.png';self.im.write_bytes(png((600,800)))
    def test_real_independent_command_receives_json_images(self):
        runner=self.root/'reviewer.py'
        runner.write_text('import json,sys\nx=json.load(sys.stdin)\nassert x["task"]=="review"\nassert x["images"][0]["data_url"].startswith("data:image/png;base64,")\nprint(json.dumps({"has_image":True,"description":"SYNTHETIC separate process transport test"}))\n')
        out=self.root/'call';out.mkdir();r=vision({'kind':'command','argv':[sys.executable,str(runner)]},'SINGLE REVIEW',[self.im],out,allowed=True)
        self.assertTrue(r['has_image']);self.assertEqual(read(out/'transport.json')['transport'],'fresh-command')
    def test_command_not_shell_string(self):
        out=self.root/'call';out.mkdir()
        with self.assertRaises(ExecutionError):vision({'kind':'command','argv':'echo fake'},'SINGLE REVIEW',[self.im],out,allowed=True)
    def test_codex_fresh_process_actual_attachment_flags(self):
        runner=self.root/'codex'
        runner.write_text('#!'+sys.executable+'\nimport json,sys,pathlib\na=sys.argv[1:]\nif "--help" in a:\n print("--image --sandbox --output-last-message --skip-git-repo-check --ephemeral");sys.exit(0)\nassert a[0]=="exec" and "resume" not in a and "--last" not in a\nassert a[a.index("--sandbox")+1]=="read-only"\np=pathlib.Path(a[a.index("--image")+1]);assert p.read_bytes().startswith(b"\\x89PNG")\ntext=sys.stdin.read();assert "ONLY TASK" in text\npathlib.Path(a[a.index("--output-last-message")+1]).write_text(json.dumps({"has_image":True,"description":"SYNTHETIC mock CLI independent process transport test"}))\n')
        runner.chmod(0o700);out=self.root/'call';out.mkdir()
        r=vision({'kind':'codex_exec','executable':str(runner)},'ONLY TASK',[self.im],out,allowed=True)
        self.assertTrue(r['has_image']);req=read(out/'request.json');self.assertFalse(req['resume']);self.assertFalse(req['conversation_history_included'])
        self.assertFalse(read(out/'transport.json')['production_working_directory_shared'])
        self.assertIn('fresh system temporary',req['working_directory'])
    def test_codex_help_checked_instead_of_inventing_flags(self):
        runner=self.root/'codex';runner.write_text('#!'+sys.executable+'\nprint("old unsupported CLI")\n');runner.chmod(0o700)
        out=self.root/'call';out.mkdir()
        with self.assertRaisesRegex(ExecutionError,'advertise'):vision({'kind':'codex_exec','executable':str(runner)},'ONLY TASK',[self.im],out,allowed=True)
    def test_command_timeout_not_approval(self):
        runner=self.root/'wait.py';runner.write_text('import time\ntime.sleep(5)\n')
        out=self.root/'call';out.mkdir()
        with self.assertRaisesRegex(ExecutionError,'timed out'):vision({'kind':'command','argv':[sys.executable,str(runner)],'timeout_seconds':.1},'ONLY TASK',[self.im],out,allowed=True)
    def test_dynamic_evidence_wrong_target_rejected(self):
        e=self.root/'review-evidence.json';save(e,{'version':'review-evidence-1','ok':True,'html_sha256':'b'*64})
        draft={'stage':'final','targets':{'preview_sha256':'a'*64}}
        with self.assertRaisesRegex(ValueError,'exact preview'):attach_runtime_evidence(draft,e,self.root)
    def test_final_preview_hash_field_supported(self):
        e=self.root/'review-evidence.json';save(e,{'version':'review-evidence-1','ok':True,'html_sha256':'a'*64,'runtime':{'webgl_ready':False,'fallback':True}})
        d={'stage':'final','targets':{'preview_sha256':'a'*64}}
        r,s=attach_runtime_evidence(d,e,self.root);self.assertFalse(r['runtime']['webgl_ready']);self.assertIn(str(e),s)

if __name__=='__main__':unittest.main()
