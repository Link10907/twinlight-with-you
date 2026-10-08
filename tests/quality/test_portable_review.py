"""SYNTHETIC regressions for the reported v2 host failure. No model calls.

The fixture has an independent visual-task facility but no platform IDs and no
OS-enforced read-only permissions. These tests are NOT a real artwork review.
"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from quality_fixtures import ROOT, PERSONA, host, save, ref, release, design
from PIL import Image
from twinlight_core.art_quality import ArtEvidenceError, sha256, check_evidence
from twinlight_core.host_contract import assess
from twinlight_core.independent_review import check_handoff, check_release
from twinlight_core.review_exchange import packet, import_response, activate_release
from twinlight_core.generation_plan import write_plan, register_image, bind_review
from twinlight_core.image_dispatch import dispatch, check_recorded_dispatch
from twinlight_core.run import run


def portable_host():
    h = host()
    h.pop('producer_session_id', None)
    h['reviewer'].update(read_only_inputs=False, runtime_evidence=None)
    h['runtime']['webgl'] = None
    return h


class PortableHostTests(unittest.TestCase):
    def test_reported_host_can_start_without_platform_ids_or_os_read_only(self):
        result = assess(portable_host())
        self.assertTrue(result['ok']); self.assertTrue(result['may_start_image_calls'])
        self.assertIn('audit.producer_session_id_unavailable', result['warnings'])
        self.assertIn('audit.os_read_only_not_enforced_use_packet_hash_checks', result['warnings'])
        self.assertFalse(result['release_authorized'])
        self.assertFalse(result['host_identity_authenticated'])

    def test_webgl_unknown_waits_for_actual_preview_not_first_image(self):
        result = assess(portable_host())
        self.assertTrue(result['ok'])
        self.assertIn('runtime.webgl_probe_at_preview', result['deferred_checks'])

    def test_known_missing_webgl_is_not_claimed_available(self):
        h = portable_host(); h['runtime']['webgl'] = False
        self.assertFalse(assess(h)['ok'])

    def test_fake_isolation_still_blocks(self):
        h = portable_host(); h['reviewer']['isolated_session'] = False
        self.assertFalse(assess(h)['may_start_image_calls'])

    def test_text_only_reviewer_still_blocks(self):
        h = portable_host(); h['reviewer']['visual_inputs'] = False
        self.assertFalse(assess(h)['ok'])

    def test_empty_capability_template_not_approved(self):
        self.assertFalse(assess({})['ok'])


class TempTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.hp = self.root / 'host.json'; save(self.hp, portable_host())


class PortableReviewTests(TempTest):
    def candidate(self, decision='accept'):
        outputs, old = release(self.root, 'card')
        raw = {k:v for k,v in old.items() if k != 'handoff'}
        raw['decision'] = decision
        if decision != 'accept':
            raw['blockers'] = [{'object':'subject','location':'top edge',
                               'evidence':'SYNTHETIC missing head pixels','repair':'Redo only the subject layer'}]
        draft = copy.deepcopy(raw); draft['decision'] = 'pending'; draft['blockers'] = []
        draft['checks'] = {key: {'passed':False, 'observation':''} for key in draft['checks']}
        tp = self.root/'pending.json'; save(tp,draft)
        packet(tp, {str(Path(x)):sha256(Path(x)) for x in outputs.values()}, self.root/'reviewer-packet')
        rawp = self.root/'actual-task-return.json'; save(rawp,raw)
        # "actual" here names a synthetic fixture path, never a real tool call.
        return outputs, rawp

    def import_candidate(self, rawp):
        out=self.root/'history/imported.json'
        r=import_response(self.root,rawp,None,out,packet_path=self.root/'reviewer-packet',host_path=self.hp)
        return r,out

    def test_import_no_trace_no_ids_no_read_only(self):
        outputs,rawp=self.candidate();before=rawp.read_bytes();result,out=self.import_candidate(rawp)
        self.assertTrue(result['ok']);self.assertEqual(before,rawp.read_bytes())
        imported=json.loads(out.read_text());h=imported['handoff']
        self.assertIsNone(h['producer_session_id']);self.assertIsNone(h['reviewer_session_id'])
        self.assertIsNone(h['invocation_id']);self.assertFalse(h['read_only_artifacts'])
        self.assertFalse(result['agent_invoked']);self.assertFalse(result['reviewer_identity_authenticated'])
        check_handoff(self.root,imported,{})

    def test_hash_bound_portable_review_can_pass_same_existing_release_checks(self):
        outputs,rawp=self.candidate();_,out=self.import_candidate(rawp)
        save(self.root/'run-report.json',{'mode':'card','outputs':outputs})
        activate_release(self.root,out)
        self.assertTrue(check_release(self.root,outputs,'card')['ok'])

    def test_missing_raw_return_cannot_create_review(self):
        self.candidate()
        with self.assertRaises((OSError, ValueError)):
            self.import_candidate(self.root/'missing.json')

    def test_no_packet_cannot_invent_evidence(self):
        _,rawp=self.candidate()
        with self.assertRaises(ValueError):
            import_response(self.root,rawp,None,self.root/'o.json',host_path=self.hp)

    def test_changed_original_input_rejected(self):
        outputs,rawp=self.candidate();Path(outputs['card_preview']).write_text('CHANGED AFTER DISPATCH')
        with self.assertRaisesRegex(ArtEvidenceError,'changed'): self.import_candidate(rawp)

    def test_changed_packet_copy_rejected(self):
        _,rawp=self.candidate();m=json.loads((self.root/'reviewer-packet/packet.json').read_text())
        (self.root/'reviewer-packet'/m['attachments'][0]['file']).write_bytes(b'CHANGED')
        with self.assertRaisesRegex(ArtEvidenceError,'changed'): self.import_candidate(rawp)

    def test_changed_pending_criteria_rejected(self):
        _,rawp=self.candidate();(self.root/'reviewer-packet/review-template.json').write_text('{}')
        with self.assertRaisesRegex(ArtEvidenceError,'changed'): self.import_candidate(rawp)

    def test_stage_cannot_be_swapped(self):
        _,rawp=self.candidate();raw=json.loads(rawp.read_text());raw['stage']='prototype';save(rawp,raw)
        with self.assertRaises(ArtEvidenceError): self.import_candidate(rawp)

    def test_original_cannot_change_after_import(self):
        outputs,rawp=self.candidate();_,out=self.import_candidate(rawp)
        Path(outputs['card_preview']).write_text('CHANGED AFTER IMPORT')
        with self.assertRaises(ArtEvidenceError):check_handoff(self.root,json.loads(out.read_text()),{})

    def test_rewritten_verdict_after_import_rejected(self):
        _,rawp=self.candidate();_,out=self.import_candidate(rawp);r=json.loads(out.read_text())
        r['checks']['complete_subject']['observation']='PRODUCER REWROTE THE OBSERVATION'
        with self.assertRaises(ArtEvidenceError):check_handoff(self.root,r,{})

    def test_roleplay_cannot_import_as_independent(self):
        _,rawp=self.candidate();h=portable_host();h['reviewer']['isolated_session']=False;save(self.hp,h)
        with self.assertRaises(ValueError): self.import_candidate(rawp)

    def test_revise_still_blocks_release(self):
        outputs,rawp=self.candidate('revise');_,out=self.import_candidate(rawp)
        save(self.root/'run-report.json',{'mode':'card','outputs':outputs});activate_release(self.root,out)
        result=check_release(self.root,outputs,'card')
        self.assertFalse(result['ok']);self.assertEqual(result['status'],'release_rejected')

    def test_blocked_still_blocks_release(self):
        outputs,rawp=self.candidate('blocked');_,out=self.import_candidate(rawp)
        save(self.root/'run-report.json',{'mode':'card','outputs':outputs});activate_release(self.root,out)
        self.assertFalse(check_release(self.root,outputs,'card')['ok'])

    def test_importer_never_approves_pending(self):
        _,rawp=self.candidate();r=json.loads(rawp.read_text());r['decision']='pending';save(rawp,r)
        with self.assertRaises(ValueError):self.import_candidate(rawp)

    def test_fallback_is_not_holographic_pass(self):
        outputs,rawp=self.candidate();r=json.loads(rawp.read_text());r['runtime'].update(backend='css',fallback=True,webgl_ready=False);save(rawp,r)
        _,out=self.import_candidate(rawp);save(self.root/'run-report.json',{'mode':'card','outputs':outputs});activate_release(self.root,out)
        self.assertFalse(check_release(self.root,outputs,'card')['ok'])

    def test_foil_noop_still_rejected(self):
        outputs,rawp=self.candidate();r=json.loads(rawp.read_text());r['effect_frames']['foil_on']['image']=r['effect_frames']['foil_off']['image'];save(rawp,r)
        _,out=self.import_candidate(rawp);save(self.root/'run-report.json',{'mode':'card','outputs':outputs});activate_release(self.root,out)
        self.assertFalse(check_release(self.root,outputs,'card')['ok'])

    def test_cli_import_works_without_trace_flag(self):
        _,rawp=self.candidate()
        cmd=[sys.executable,str(ROOT/'scripts/reviewer.py'),'import','--root',str(self.root),'--response',str(rawp),
             '--packet',str(self.root/'reviewer-packet'),'--host-capabilities',str(self.hp),'--out',str(self.root/'cli-out.json')]
        done=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
        self.assertEqual(done.returncode,0,done.stdout+done.stderr)
        self.assertEqual(json.loads(done.stdout)['evidence_mode'],'artifact_bound')


class PortableProductionTests(TempTest):
    def prepare(self):
        folder=self.root/'run';folder.mkdir();card=folder/'card';card.mkdir()
        save(folder/'run-state.json',{'mode':'both','persona_digest':PERSONA})
        save(card/'design.json',design(style='twinlight-collector'))
        write_plan(card/'design.json',card,canvas=(600,800),capabilities=portable_host()['image'])
        return folder,card,card/'generation-plan.json'

    def test_real_compile_and_dispatch_continue_in_reported_host_shape(self):
        folder,card,plan=self.prepare();d=card/'dispatch/one.json'
        result=dispatch(plan,'prototype',folder,self.hp,d)
        self.assertTrue(result['ok']);self.assertIsNone(json.loads(d.read_text())['producer_session_id'])
        self.assertEqual(result['attempts_used'],1)

    def test_output_without_provider_ids_uses_honest_local_bindings(self):
        folder,card,plan=self.prepare();d=card/'dispatch/one.json';dispatch(plan,'prototype',folder,self.hp,d)
        img=card/'returned.png';Image.new('RGB',(600,800),(30,40,50)).save(img)
        raw=card/'returned.txt';raw.write_text('SYNTHETIC tool returned an attachment at returned.png, no provider IDs exposed.')
        result=register_image(plan,'prototype',img,raw,tool='SYNTHETIC_IMAGE_TOOL',dispatch_path=d)
        self.assertTrue(result['ok']);self.assertFalse(result['art_approved'])
        ev=json.loads((card/'art-evidence.json').read_text());call=json.loads((card/ev['images']['prototype']['call']['file']).read_text())
        self.assertTrue(call['call_id'].startswith('local-call:'));self.assertIsNone(call['provider_call_id'])
        self.assertEqual(call['response']['artifact_id'],'local-artifact:'+sha256(img))
        self.assertIsNone(call['response']['provider_artifact_id']);check_recorded_dispatch(card,call,{})
        # Evidence registration is not an aesthetic pass.
        gate=check_evidence(card/'layers.json',PERSONA,stage='prototype')
        self.assertFalse(gate['ok']);self.assertEqual(gate['status'],'needs_art_review',gate)

    def test_empty_return_not_replaced_with_fabricated_receipt(self):
        folder,card,plan=self.prepare();d=card/'dispatch/one.json';dispatch(plan,'prototype',folder,self.hp,d)
        img=card/'returned.png';Image.new('RGB',(600,800),(30,40,50)).save(img)
        raw=card/'returned.txt';raw.write_text('')
        with self.assertRaises(ValueError):register_image(plan,'prototype',img,raw,tool='SYNTHETIC_IMAGE_TOOL',dispatch_path=d)


    def approved_synthetic_prototype(self):
        folder,card,plan=self.prepare();d=card/'dispatch/one.json';dispatch(plan,'prototype',folder,self.hp,d)
        img=card/'returned.png';Image.new('RGB',(600,800),(30,40,50)).save(img)
        raw=card/'returned.txt';raw.write_text('SYNTHETIC image tool attachment; no platform IDs provided.')
        register_image(plan,'prototype',img,raw,tool='SYNTHETIC_IMAGE_TOOL',dispatch_path=d)
        packetdir=card/'reviewer-input/prototype-1'
        done=subprocess.run([sys.executable,str(ROOT/'scripts/reviewer.py'),'packet','--stage','prototype',
             '--layers',str(card/'layers.json'),'--out',str(packetdir)],capture_output=True,text=True,timeout=15)
        self.assertEqual(done.returncode,0,done.stdout+done.stderr)
        review=json.loads((packetdir/'review-template.json').read_text())
        review.update(decision='accept',observer='SYNTHETIC_REVIEW_TASK',observed_at='2000-01-01T00:00:00+00:00',
                      capture=ref(card,card/'prototype.png'),blockers=[])
        for value in review['checks'].values():value.update(passed=True,observation='SYNTHETIC pipeline fixture; not a real aesthetic judgement.')
        rp=card/'reviewer-return.json';save(rp,review);out=card/'review-history/imported.json'
        import_response(card,rp,None,out,packet_path=packetdir,host_path=self.hp)
        result=bind_review(card/'layers.json',out)
        self.assertTrue(result['ok'],result)
        return folder,card,plan

    def test_full_prototype_registration_packet_import_binding_without_platform_ids(self):
        folder,card,plan=self.approved_synthetic_prototype()
        gate=check_evidence(card/'layers.json',PERSONA,stage='prototype')
        self.assertTrue(gate['ok'],gate)
        result=write_plan(card/'art-direction.json',card,phase='layers',capabilities=portable_host()['image'])
        self.assertEqual(result['phase'],'layers')
        self.assertTrue(check_evidence(card/'layers.json',PERSONA,stage='prototype')['ok'])

    def test_normal_future_layer_metadata_does_not_revoke_prototype(self):
        _,card,_=self.approved_synthetic_prototype()
        manifest=json.loads((card/'layers.json').read_text())
        manifest['notes']='SYNTHETIC downstream registration; prototype/design/style unchanged'
        manifest['assets']['subject']='subject.webp';save(card/'layers.json',manifest)
        gate=check_evidence(card/'layers.json',PERSONA,stage='prototype')
        self.assertTrue(gate['ok'],gate)

    def test_actual_prototype_change_still_revokes_approval(self):
        _,card,_=self.approved_synthetic_prototype()
        Image.new('RGB',(600,800),(100,60,20)).save(card/'prototype.png')
        self.assertFalse(check_evidence(card/'layers.json',PERSONA,stage='prototype')['ok'])

    def test_actual_public_controller_reaches_art_step_not_capability_blocked(self):
        data={'twinlight':'card-1','name':'测试','summarizer':'SYNTHETIC',
              'card':{'title':'测试卡','english_title':'TEST CARD','keywords':['合成','测试','隔离'],
                      'tagline':'仅用于程序测试','reflection':'这是合成测试材料，不是个人定义。'}}
        inp=self.root/'input.json';save(inp,data)
        r=run(inp,self.root/'public-run',mode='card',no_browser=True,host_capabilities=self.hp)
        self.assertEqual(r['status'],'needs_card');self.assertFalse(r['complete'])
        self.assertTrue(r['host_contract']['ok'])


if __name__ == '__main__': unittest.main()
