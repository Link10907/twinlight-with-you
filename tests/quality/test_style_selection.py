"""SYNTHETIC upstream selection tests; no image calls or aesthetic approvals."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quality_fixtures import ROOT, design
from split_fixtures import person
from test_portable import caps
from twinlight_core import portable, style_selection as ss
from twinlight_core.common import load, save, digest
from twinlight_core.card_context import image_input, render_prompt, preset, validate_input
from twinlight_core.visual_contract import catalog, default_style, style_for, style_references


def request(**kwargs):
    x = image_input(design(style='twinlight-collector'))
    x.pop('style'); x['version'] = ss.REQUEST_VERSION
    return x | kwargs


class SelectionTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.root = Path(t.name); self.w = self.root / 'work'
    def test_default_is_subject_random_over_six(self):
        r = ss.select(self.w, request()); self.assertEqual(r['mode'], 'subject_random')
        self.assertEqual(len(r['candidates']), 6); self.assertFalse(r['image_generation_performed'])
    def test_status_does_not_choose_or_create_files(self):
        r = ss.selection_status(self.w); self.assertEqual(r['default_mode'], 'subject_random')
        self.assertFalse(self.w.exists()); self.assertNotIn('selected_style', r)
    def test_legacy_default_function_remains_unchanged(self):
        self.assertEqual(default_style()['id'], 'twinlight-collector')
    def test_explicit_selection_for_every_installed_style(self):
        for s in catalog():
            with self.subTest(style=s['id']):
                r = ss.select(self.w / s['id'], request(style={k:s[k] for k in ('id','version')}))
                self.assertEqual(r['selected_style']['id'], s['id']); self.assertEqual(r['mode'], 'explicit')
    def test_explicit_beats_random_default(self):
        r = ss.select(self.w, request(mode='random', style={'id':'paper-craft-story','version':'1.0.0'}))
        self.assertEqual(r['selected_style']['id'], 'paper-craft-story'); self.assertEqual(r['mode'], 'explicit')
    def test_explicit_conflicting_constraints_rejected(self):
        with self.assertRaises(ValueError):
            ss.select(self.w, request(style={'id':'paper-craft-story','version':'1.0.0'}, candidates=['forest-fantasy']))
    def test_explicit_requires_style(self):
        with self.assertRaises(ValueError): ss.select(self.w, request(mode='explicit'))
    def test_unknown_style_does_not_fallback(self):
        with self.assertRaises(ValueError): ss.select(self.w, request(style={'id':'ink-wash','version':'1.0.0'}))
        self.assertFalse(self.w.exists())
    def test_version_mismatch_does_not_fallback(self):
        with self.assertRaises(ValueError): ss.select(self.w, request(style={'id':'forest-fantasy','version':'99.0.0'}))
    def test_filtered_random_stays_inside_candidates(self):
        choices=['forest-fantasy','paper-craft-story']
        for i in range(12):
            r=ss.select(self.w/str(i),request(mode='subject_random',candidates=choices,reason='SYNTHETIC visual compatibility.',seed=str(i)))
            self.assertIn(r['selected_style']['id'],choices)
    def test_random_with_no_filter_uses_six(self):
        self.assertEqual(len(ss.select(self.w,request(mode='random'))['candidates']),6)
    def test_all_six_reachable_for_deterministic_test_seeds(self):
        choices=sorted(s['id'] for s in catalog())
        seen={ss._choice(choices,str(i)) for i in range(120)}
        self.assertEqual(seen,set(choices))
    def test_candidate_order_does_not_change_choice(self):
        q=request(candidates=['paper-craft-story','forest-fantasy'],reason='SYNTHETIC candidates.',seed='test')
        a=ss.select(self.w,q);q['candidates'].reverse();b=ss.select(self.w,q)
        self.assertEqual(a['selected_style'],b['selected_style']);self.assertTrue(b['reused'])
    def test_duplicate_candidates_rejected(self):
        with self.assertRaises(ValueError):ss.select(self.w,request(candidates=['forest-fantasy']*2,reason='test'))
    def test_empty_candidates_rejected(self):
        with self.assertRaises(ValueError):ss.select(self.w,request(candidates=[]))
    def test_unknown_candidate_rejected(self):
        with self.assertRaises(ValueError):ss.select(self.w,request(candidates=['forest-fantasy','ink-wash'],reason='test'))
    def test_single_subject_candidate_requires_explicit_mode(self):
        with self.assertRaises(ValueError):ss.select(self.w,request(candidates=['forest-fantasy'],reason='test'))
    def test_filtered_subject_choice_requires_reason(self):
        with self.assertRaises(ValueError):ss.select(self.w,request(candidates=['forest-fantasy','paper-craft-story']))
    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):ss.select(self.w,request(mode='guess'))
    def test_bad_seed_rejected(self):
        for seed in ('',123,True,'a'*129):
            with self.subTest(seed=seed),self.assertRaises(ValueError):ss.select(self.w,request(seed=seed))
    def test_unknown_request_fields_rejected(self):
        with self.assertRaises(ValueError):ss.select(self.w,request(biography='SYNTHETIC private material'))
    def test_visible_field_validation_is_still_used(self):
        q=request();q['subject']['clothing']='HTML 首页网页布局'
        with self.assertRaises(ValueError):ss.select(self.w,q)
    def test_plain_request_has_no_extra_drawing_metadata(self):
        q=request(mode='random',reason='PRIVATE_REASON_SENTINEL',seed='PRIVATE_SEED_SENTINEL')
        ss.select(self.w,q);x=load(self.w/ss.DRAWING)
        self.assertEqual(set(x),{'version','style','subject','scene'});validate_input(x)
        text=render_prompt(x,'prototype',(600,800))
        self.assertNotIn('PRIVATE_REASON_SENTINEL',text);self.assertNotIn('PRIVATE_SEED_SENTINEL',text)
    def test_subject_scene_are_not_rewritten(self):
        q=request();ss.select(self.w,q);x=load(self.w/ss.DRAWING)
        self.assertEqual(x['subject'],q['subject']);self.assertEqual(x['scene'],q['scene'])
    def test_request_object_is_not_mutated(self):
        q=request();before=copy.deepcopy(q);ss.select(self.w,q);self.assertEqual(q,before)
    def test_existing_style_prompts_are_used_without_extra_prose(self):
        for s in catalog():
            w=self.w/s['id'];ss.select(w,request(style={'id':s['id'],'version':s['version']}))
            x=load(w/ss.DRAWING);original=image_input(design(style=s['id']))
            for role in ('prototype','background','subject','effects','spirit'):
                self.assertEqual(render_prompt(x,role,(600,800)),render_prompt(original,role,(600,800)))
    def test_only_selected_reference_images_are_returned(self):
        for s in catalog():
            r=ss.select(self.w/s['id'],request(style={'id':s['id'],'version':s['version']}))
            self.assertEqual(r['style_reference_images'],style_references(s))
    def test_text_only_style_does_not_get_collector_images(self):
        r=ss.select(self.w,request(style={'id':'paper-craft-story','version':'1.0.0'}))
        self.assertEqual(r['style_reference_images'],[])
    def test_resume_does_not_draw_another_seed_or_rewrite_bytes(self):
        q=request();a=ss.select(self.w,q);before={f.name:f.read_bytes() for f in self.w.iterdir()}
        with patch.object(ss.secrets,'token_hex',side_effect=AssertionError('must not redraw')):
            b=ss.select(self.w,q)
        self.assertEqual(a['selected_style'],b['selected_style']);self.assertTrue(b['reused'])
        self.assertEqual(before,{f.name:f.read_bytes() for f in self.w.iterdir()})
    def test_new_works_use_fresh_entropy_by_default(self):
        with patch.object(ss.secrets,'token_hex',side_effect=['one','two']) as gen:
            ss.select(self.w/'a',request());ss.select(self.w/'b',request())
        self.assertEqual(gen.call_count,2)
        self.assertNotEqual(load(self.w/'a'/ss.RECORD)['seed'],load(self.w/'b'/ss.RECORD)['seed'])
    def test_same_seed_and_pool_reproduce_selection(self):
        q=request(seed='repeat');a=ss.select(self.w/'a',q);b=ss.select(self.w/'b',q)
        self.assertEqual(a['selected_style'],b['selected_style'])
    def test_changed_request_cannot_overwrite_existing(self):
        q=request(seed='before');ss.select(self.w,q);before=(self.w/ss.RECORD).read_bytes()
        for change in ('subject','seed','candidates','style'):
            other=copy.deepcopy(q)
            if change=='subject':other['subject']['clothing']='深色棉质衬衫'
            if change=='seed':other['seed']='after'
            if change=='candidates':other.update(candidates=['forest-fantasy','paper-craft-story'],reason='test')
            if change=='style':other['style']={'id':'futuristic-clean','version':'1.0.0'}
            with self.subTest(change=change),self.assertRaises(ValueError):ss.select(self.w,other)
        self.assertEqual(before,(self.w/ss.RECORD).read_bytes())
    def test_changed_drawing_rejected_without_overwrite(self):
        q=request();ss.select(self.w,q);x=load(self.w/ss.DRAWING);x['subject']['clothing']='深色棉质衬衫';save(self.w/ss.DRAWING,x)
        with self.assertRaises(ValueError):ss.select(self.w,q)
        self.assertEqual(load(self.w/ss.DRAWING),x)
    def test_missing_drawing_restored_from_frozen_record(self):
        q=request();ss.select(self.w,q);old=(self.w/ss.DRAWING).read_bytes();(self.w/ss.DRAWING).unlink()
        with patch.object(ss.secrets,'token_hex',side_effect=AssertionError('must not redraw')):ss.select(self.w,q)
        self.assertEqual(old,(self.w/ss.DRAWING).read_bytes())
    def test_tampered_record_rejected(self):
        ss.select(self.w,request());r=load(self.w/ss.RECORD);r['seed']='changed';save(self.w/ss.RECORD,r)
        with self.assertRaises(ValueError):ss.selection_status(self.w)
    def test_rehashed_wrong_selection_still_rejected(self):
        ss.select(self.w,request(mode='random',seed='test'));r=load(self.w/ss.RECORD)
        other=next(s['id'] for s in catalog() if s['id']!=r['selected_style']['id']);r['selected_style']['id']=other
        r['record_sha256']=digest({k:v for k,v in r.items() if k!='record_sha256'});save(self.w/ss.RECORD,r)
        with self.assertRaises(ValueError):ss.selection_status(self.w)
    def test_style_binding_change_rejected(self):
        ss.select(self.w,request())
        with patch.object(ss,'_binding',return_value={'changed':True}),self.assertRaises(ValueError):ss.selection_status(self.w)
    def test_changed_frozen_content_binding_rejected(self):
        save(self.w/'portable-state.json',{'input_sha256':'before'});ss.select(self.w,request())
        save(self.w/'portable-state.json',{'input_sha256':'after'})
        with self.assertRaises(ValueError):ss.selection_status(self.w)
    def test_old_art_is_not_reselected(self):
        for name in ('generation.json','image-attempts.json','art-direction.json','generation-plan.json'):
            w=self.w/name;save(w/name,{})
            self.assertEqual(ss.selection_status(w)['status'],'reuse_existing_artwork')
            with self.assertRaises(ValueError):ss.select(w,request())
    def test_old_card_directory_is_not_reselected(self):
        save(self.w/'card-task/custom-plan.json',{'existing':True})
        with self.assertRaises(ValueError):ss.select(self.w,request())
    def test_existing_conflicting_input_not_overwritten(self):
        save(self.w/ss.DRAWING,{'existing':True})
        with self.assertRaises(ValueError):ss.select(self.w,request())
        self.assertEqual(load(self.w/ss.DRAWING),{'existing':True});self.assertFalse((self.w/ss.RECORD).exists())
    def test_symlink_outputs_rejected(self):
        self.w.mkdir();target=self.root/'private.json';save(target,{'private':True})
        (self.w/ss.RECORD).symlink_to(target)
        with self.assertRaises(ValueError):ss.select(self.w,request())
        self.assertEqual(load(target),{'private':True})
    def test_private_outputs_are_created_with_restricted_permissions(self):
        ss.select(self.w,request())
        for name in (ss.RECORD,ss.DRAWING):self.assertEqual((self.w/name).stat().st_mode & 0o077,0)


class UpstreamIntegrationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);self.w=self.root/'work'
        self.source=self.root/'person.json';save(self.source,person())
    def test_new_portable_run_exposes_selection_before_images(self):
        r=portable.run(self.source,self.w,caps())
        self.assertEqual(r['style_selection']['status'],'selection_required')
        self.assertEqual(r['image_calls_performed_by_cli'],0);self.assertFalse((self.w/'site-task').exists())
    def test_resumed_portable_run_exposes_same_selection(self):
        portable.run(self.source,self.w,caps());s=ss.select(self.w,request())
        r=portable.run(self.source,self.w,caps())
        self.assertEqual(r['style_selection']['selected_style'],s['selected_style']);self.assertTrue(r['style_selection']['reused'])
    def test_no_card_route_does_not_call_selector(self):
        with patch.object(ss,'selection_status',side_effect=AssertionError('No card means no selection')):
            r=portable.run(self.source,self.w,caps('unavailable'))
        self.assertNotIn('style_selection',r);self.assertFalse((self.w/ss.RECORD).exists())
    def test_cli_select_and_status(self):
        q=self.root/'request.json';save(q,request())
        for args in (['select-style',str(q),'--workspace',str(self.w)],['style-status','--workspace',str(self.w)]):
            result=subprocess.run([sys.executable,str(ROOT/'scripts/portable.py'),*args],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'],'frozen')
    def test_cli_unknown_style_reports_error_without_files(self):
        q=self.root/'request.json';save(q,request(style={'id':'ink-wash','version':'1.0.0'}))
        result=subprocess.run([sys.executable,str(ROOT/'scripts/portable.py'),'select-style',str(q),'--workspace',str(self.w)],capture_output=True,text=True)
        self.assertEqual(result.returncode,2);self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertFalse(self.w.exists())


if __name__ == '__main__': unittest.main()
