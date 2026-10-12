"""SYNTHETIC ONLY: layer/motion contract tests. No personal artwork is approved."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw
from split_fixtures import person, native
from prepare_card_layers import font_path
from twinlight_core.common import load, save
from twinlight_core.lite import persona_digest
from twinlight_core import portable
from twinlight_core.portable_layers import layer_plan, record_attempt, extract, prepare_assisted, verify_process, sha
from twinlight_core.portable_motion import motion_check, REQUIRED
from test_portable import caps


class LayerPlanTests(unittest.TestCase):
    def ready(self):
        return {'image_edit': {'status':'available','reference_binding':'available','transparent_output':'available'},
                'layer_processing':{'status':'available'}}
    def test_separate_capabilities_are_not_assumed(self):
        self.assertEqual(layer_plan(caps())['status'],'inspect_layer_capabilities')
    def test_explicit_native_capabilities_use_existing_route(self):
        self.assertEqual(layer_plan(self.ready())['method'],'native_layers')
    def test_native_alpha_absence_uses_assisted_not_no_card(self):
        c=self.ready();c['image_edit']['transparent_output']='unavailable';r=layer_plan(c)
        self.assertEqual(r['method'],'assisted_layers');self.assertFalse(r['static_or_cardless_fallback'])
    def test_first_reference_mismatch_stops_native_loop(self):
        self.assertEqual(layer_plan(self.ready(),{'attempts':[{'role':'subject','outcome':'reference_mismatch'}]})['method'],'assisted_layers')
    def test_three_failures_exhaust_native_role(self):
        r=layer_plan(self.ready(),{'attempts':[{'role':'subject','outcome':'failure'}]*3})
        self.assertEqual(r['method'],'assisted_layers')
    def test_successful_layers_are_reused(self):
        r=layer_plan(self.ready(),{'attempts':[{'role':'subject','outcome':'failure'}]*2+[{'role':'subject','outcome':'success'}]})
        self.assertEqual(r['method'],'native_layers')
    def test_unknown_processing_is_inspected(self):
        c=self.ready();c['layer_processing']['status']='unknown';c['image_edit']['reference_binding']='unavailable'
        self.assertEqual(layer_plan(c)['status'],'inspect_layer_processing')
    def test_missing_processing_is_precise_layer_block(self):
        c=self.ready();c['layer_processing']['status']='unavailable';c['image_edit']['reference_binding']='unavailable'
        r=layer_plan(c);self.assertEqual(r['status'],'layer_capability_blocked');self.assertFalse(r['static_or_cardless_fallback'])
    def test_temporary_alpha_limit_never_changes_image_mode(self):
        c=caps()|self.ready();c['image_edit']['transparent_output']='temporarily_blocked'
        self.assertEqual(layer_plan(c)['method'],'assisted_layers');self.assertEqual(portable.route(c)['mode'],'full')
    def test_bad_capability_typo_rejected(self):
        c=self.ready();c['image_edit']['reference_binding']='yes'
        with self.assertRaises(ValueError):layer_plan(c)


class AttemptTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
        self.p=self.root/'prototype.png';Image.new('RGB',(8,8),'red').save(self.p)
    def test_three_actual_failures_are_capped(self):
        for _ in range(3):record_attempt(self.root,'subject','failure','SYNTHETIC failed return',self.p)
        with self.assertRaises(ValueError):record_attempt(self.root,'subject','failure','SYNTHETIC fourth',self.p)
    def test_reference_mismatch_stops_repeated_calls(self):
        record_attempt(self.root,'subject','reference_mismatch','SYNTHETIC wrong scene',self.p)
        with self.assertRaises(ValueError):record_attempt(self.root,'effects','failure','SYNTHETIC repeated chain',self.p)
    def test_success_without_bytes_rejected(self):
        with self.assertRaises(ValueError):record_attempt(self.root,'subject','success','SYNTHETIC no output',self.p)
    def test_real_byte_record_not_a_provider_id(self):
        r=record_attempt(self.root,'background','success','SYNTHETIC bytes only',self.p,self.p)
        self.assertEqual(r['attempts_used'],1)
        item=load(self.root/'image-attempts.json')['attempts'][0]
        self.assertEqual(item['output_sha256'],sha(self.p));self.assertNotIn('provider_id',item)
    def test_changed_original_cannot_reset_counter(self):
        record_attempt(self.root,'subject','failure','SYNTHETIC failure',self.p)
        Image.new('RGB',(8,8),'blue').save(self.p)
        with self.assertRaises(ValueError):record_attempt(self.root,'subject','failure','SYNTHETIC changed image',self.p)


class AssistedTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
        self.p=self.root/'prototype.png';self.bg=self.root/'background.png';self.sm=self.root/'subject-mask.png';self.fm=self.root/'effects-mask.png'
        size=(600,800);bg=Image.new('RGB',size,(20,30,50));bg.save(self.bg)
        sm=Image.new('L',size);d=ImageDraw.Draw(sm);d.ellipse((180,120,420,600),fill=255);sm.save(self.sm)
        fm=Image.new('L',size);ImageDraw.Draw(fm).ellipse((450,570,505,625),fill=230);fm.save(self.fm)
        original=bg.copy();ImageDraw.Draw(original).ellipse((180,120,420,600),fill=(150,175,210));ImageDraw.Draw(original).ellipse((450,570,505,625),fill=(240,220,155));original.save(self.p)
        self.out=self.root/'layers'
    def prepare(self,**extra):
        kw={'subject_mask':self.sm,'effects_mask':self.fm};kw.update(extra)
        return prepare_assisted(person(),self.p,self.bg,self.out,font_path(None),**kw)
    def generation(self):
        m=load(self.out/'layers.json');r={'origin':'native_image_tool','tool':'SYNTHETIC fixture, NOT a real tool invocation',
            'prototype_file':'prototype.png','prototype_sha256':sha(self.p),
            'prototype_review':'self','prototype_verdict':'accept','prototype_observations':'SYNTHETIC test flag only; no actual artwork approval.',
            'layer_method':'assisted_layers','assembly_record_file':'layers/layer-process.json',
            'layers_sha256':{k:sha(self.out/m['assets'][k]) for k in ('background','subject','effects')},
            'context_isolation':'contextual_native_tool','verdict':'accept','layer_observations':'SYNTHETIC test only; not production approval.'}
        path=self.root/'generation.json';save(path,r);return path
    def test_rgb_pixels_and_alpha_match_frozen_original(self):
        result=extract(self.p,self.sm)
        self.assertEqual(result.convert('RGB').tobytes(),Image.open(self.p).convert('RGB').tobytes())
        self.assertEqual(result.getchannel('A').tobytes(),Image.open(self.sm).tobytes())
    def test_six_layers_use_existing_schema_and_depths(self):
        r=self.prepare();self.assertTrue(r['ok']);self.assertFalse(r['native_transparency_claimed'])
        m=load(self.out/'layers.json');self.assertEqual(len(m['assets']),6);self.assertEqual(m['depths']['text'],0)
        self.assertLess(m['depths']['background'],0);self.assertGreater(m['depths']['effects'],m['depths']['subject'])
    def test_clean_background_required_not_original_again(self):
        self.bg.write_bytes(self.p.read_bytes())
        with self.assertRaises(ValueError):self.prepare()
    def test_complete_opaque_background_required(self):
        im=Image.open(self.bg).convert('RGBA');im.putalpha(254);im.save(self.bg)
        with self.assertRaises(ValueError):self.prepare()
    def test_painted_rgb_mask_rejected(self):
        Image.open(self.sm).convert('RGB').save(self.sm)
        with self.assertRaises(ValueError):extract(self.p,self.sm)
    def test_empty_mask_rejected(self):
        Image.new('L',(600,800)).save(self.sm)
        with self.assertRaises(ValueError):extract(self.p,self.sm)
    def test_opaque_poster_mask_rejected(self):
        Image.new('L',(600,800),255).save(self.sm)
        with self.assertRaises(ValueError):extract(self.p,self.sm)
    def test_wrong_canvas_mask_not_resized(self):
        Image.new('L',(512,512),128).save(self.sm)
        with self.assertRaises(ValueError):extract(self.p,self.sm)
    def test_accepted_native_effects_bytes_reused(self):
        fx=self.root/'native-effects.png';extract(self.p,self.fm).save(fx)
        self.prepare(effects=fx,effects_mask=None)
        m=load(self.out/'layers.json');self.assertEqual(sha(fx),sha(self.out/m['assets']['effects']))
        self.assertTrue(verify_process(self.out/'layer-process.json',self.out/'layers.json',sha(self.p)))
    def test_input_revision_never_overwritten(self):
        self.prepare()
        with self.assertRaises(ValueError):self.prepare()
    def test_changed_source_mask_revokes_record(self):
        self.prepare();r=load(self.out/'layer-process.json');p=self.out/r['inputs']['subject_mask']['file'];p.write_bytes(b'changed')
        with self.assertRaises(ValueError):verify_process(self.out/'layer-process.json',self.out/'layers.json',sha(self.p))
    def test_changed_output_revokes_record(self):
        self.prepare();Image.new('RGBA',(600,800)).save(self.out/'subject.png')
        with self.assertRaises(ValueError):verify_process(self.out/'layer-process.json',self.out/'layers.json',sha(self.p))
    def test_pixels_still_checked_after_rewriting_output_hash(self):
        self.prepare();im=Image.open(self.out/'subject.png').convert('RGBA');im.putpixel((250,250),(255,0,0,255));im.save(self.out/'subject.png')
        r=load(self.out/'layer-process.json');r['outputs_sha256']['subject']=sha(self.out/'subject.png');save(self.out/'layer-process.json',r)
        with self.assertRaises(ValueError):verify_process(self.out/'layer-process.json',self.out/'layers.json',sha(self.p))
    def test_wrong_original_revokes_assisted_record(self):
        self.prepare()
        with self.assertRaises(ValueError):verify_process(self.out/'layer-process.json',self.out/'layers.json','0'*64)
    def test_assisted_cannot_claim_native_transparency(self):
        self.prepare();p=self.generation();r=load(p);r.pop('layer_method');save(p,r)
        with self.assertRaises(ValueError):portable.generation_check(p,self.out/'layers.json')
    def test_assisted_record_is_accepted_as_assisted_only(self):
        self.prepare();r=portable.generation_check(self.generation(),self.out/'layers.json')
        self.assertEqual(r['layer_method'],'assisted_layers');self.assertFalse(r['native_transparency_claimed'])
    def test_assisted_review_has_truthful_check_name(self):
        p=self.root/'review.json';save(p,{'stage':'card','target_sha256':'x','method':'self','verdict':'accept',
            'checks':{k:True for k in portable.CHECKS['card-assisted']},'observations':'SYNTHETIC contract test; not a visual approval.'})
        self.assertTrue(portable.review_check(p,'card','x','self',layer_method='assisted_layers')['ok'])
        with self.assertRaises(ValueError):portable.review_check(p,'card','x','self')
    def test_same_assisted_card_embeds_without_second_generation(self):
        self.prepare();self.generation();src=self.root/'person.json';save(src,person())
        fake={'ok':True,'method':'self','status':'accepted','SYNTHETIC':True}
        with patch.object(portable,'review_check',return_value=fake):r=portable.run(src,self.root,caps(),layers=self.out/'layers.json')
        self.assertTrue(r['complete']);self.assertEqual(r['layer_method'],'assisted_layers');self.assertEqual(r['card_artifact'],'interactive_html')
        self.assertFalse(r['all_checks_passed']);self.assertFalse(r['card_motion']['interaction_verified'])
        with patch.object(portable,'review_check',return_value=fake):again=portable.run(src,self.root,caps())
        self.assertEqual(r['card_digest'],again['card_digest'])
        self.assertEqual(r['html_sha256'],again['html_sha256'])


class MotionEvidenceTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
        self.html=self.root/'card.html';self.html.write_text('SYNTHETIC html fixture, no actual artwork')
        self.path=self.root/'card-runtime.json'
    def report(self):
        images={}
        for key,color in [('left','red'),('right','blue'),('foil_off','black'),('foil_on','white')]:
            p=self.root/(key+'.png');Image.new('RGB',(16,16),color).save(p);images[key]={'file':p.name,'sha256':sha(p)}
        return {'version':'portable-card-motion-1','status':'passed','html_sha256':sha(self.html),
            'backend':'webgl','load_mode':'file','offline_file_open':'passed','foil_verified':True,
            **{k:True for k in REQUIRED},'checks':[{'name':'SYNTHETIC contract fixture, not browser execution','passed':True}],
            'frames':images}
    def test_no_browser_is_unverified_not_static_completion(self):
        r=motion_check(self.path,self.html);self.assertEqual(r['status'],'unavailable');self.assertFalse(r['interaction_verified'])
    def test_bound_motion_report_validates(self):
        save(self.path,self.report());self.assertEqual(motion_check(self.path,self.html)['status'],'passed')
    def test_stale_html_invalidates_runtime(self):
        save(self.path,self.report());self.html.write_text('changed')
        with self.assertRaises(ValueError):motion_check(self.path,self.html)
    def test_png_alone_is_not_runtime_evidence(self):
        save(self.path,{'html_sha256':sha(self.html),'status':'passed','image':'left.png'})
        with self.assertRaises(ValueError):motion_check(self.path,self.html)
    def test_known_motion_failure_blocks(self):
        r=self.report();r['status']='failed';save(self.path,r)
        with self.assertRaises(ValueError):motion_check(self.path,self.html)
    def test_false_check_blocks_even_when_summary_passed(self):
        r=self.report();r['checks'][0]['passed']=False;save(self.path,r)
        with self.assertRaises(ValueError):motion_check(self.path,self.html)
    def test_no_internal_parallax_not_accepted_as_dynamic(self):
        r=self.report();r['parallax_verified']=False;save(self.path,r)
        with self.assertRaises(ValueError):motion_check(self.path,self.html)
    def test_identical_frames_not_evidence(self):
        r=self.report();r['frames']['right']=r['frames']['left'];save(self.path,r)
        with self.assertRaises(ValueError):motion_check(self.path,self.html)
    def test_changed_screenshot_revokes_binding(self):
        save(self.path,self.report());(self.root/'left.png').write_bytes(b'changed')
        with self.assertRaises(ValueError):motion_check(self.path,self.html)
    def test_css_motion_is_limited_not_webgl_foil(self):
        r=self.report();r.update(status='limited',backend='css-layered',foil_verified=False);save(self.path,r)
        self.assertEqual(motion_check(self.path,self.html)['status'],'limited')
    def test_css_cannot_claim_foil_verified(self):
        r=self.report();r.update(status='limited',backend='css-layered');save(self.path,r)
        with self.assertRaises(ValueError):motion_check(self.path,self.html)
    def test_injected_not_offline_pass(self):
        r=self.report();r.update(load_mode='injected');save(self.path,r)
        with self.assertRaises(ValueError):motion_check(self.path,self.html)
    def test_injected_complete_function_checks_are_limited(self):
        r=self.report();r.update(status='limited',load_mode='injected',offline_file_open='unverified');save(self.path,r)
        self.assertEqual(motion_check(self.path,self.html)['status'],'limited')
    def test_unavailable_cannot_claim_motion_verified(self):
        r=self.report();r.update(status='unavailable',reason='SYNTHETIC no browser');r['checks']=[];save(self.path,r)
        with self.assertRaises(ValueError):motion_check(self.path,self.html)

if __name__=='__main__':unittest.main()
