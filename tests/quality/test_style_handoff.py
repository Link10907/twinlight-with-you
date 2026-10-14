"""SYNTHETIC handoff checks only. No image generation or visual acceptance."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from quality_fixtures import ROOT, design
from split_fixtures import person
from test_portable import caps
from test_style_selection import request
from twinlight_core import portable, style_selection as ss
from twinlight_core.card_context import image_input, render_prompt
from twinlight_core.common import load, save
from twinlight_core.visual_contract import catalog, style_references


class HandoffBoundaryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); self.w = self.root/'work'
        self.q = request(mode='random', seed='PRIVATE_SEED_SENTINEL',
                         reason='PRIVATE_EXPLANATION_SENTINEL')
        self.keys = {'ok', 'status', 'reused', 'selected_style',
                     'drawing_input', 'style_reference_images'}

    def test_selected_result_has_only_resolved_input_fields(self):
        r = ss.select(self.w, self.q)
        self.assertEqual(set(r), self.keys)

    def test_frozen_status_has_same_minimal_boundary(self):
        ss.select(self.w, self.q)
        self.assertEqual(set(ss.selection_status(self.w)), self.keys)

    def test_decisions_remain_in_private_record_not_output(self):
        r = ss.select(self.w, self.q); private = load(self.w/ss.RECORD)
        self.assertEqual(private['request']['reason'], self.q['reason'])
        self.assertEqual(private['seed'], self.q['seed'])
        for hidden in ('mode','candidates','reason','seed','record','scope','instruction'):
            self.assertNotIn(hidden, r)
        self.assertNotIn(self.q['reason'], json.dumps(r))
        self.assertNotIn(self.q['seed'], json.dumps(r))

    def test_cli_does_not_echo_selection_metadata(self):
        p = self.root/'request.json'; save(p, self.q)
        for args in (['select-style',str(p),'--workspace',str(self.w)],
                     ['style-status','--workspace',str(self.w)]):
            r = subprocess.run([sys.executable,str(ROOT/'scripts/portable.py'),*args],
                               capture_output=True,text=True,check=True)
            self.assertEqual(set(json.loads(r.stdout)), self.keys)
            self.assertNotIn(self.q['reason'],r.stdout+r.stderr)
            self.assertNotIn(self.q['seed'],r.stdout+r.stderr)

    def test_all_styles_keep_subject_scene_and_existing_prompt_bytes(self):
        for style in catalog():
            q = request(style={k:style[k] for k in ('id','version')},reason=self.q['reason'])
            w = self.w/style['id']; r = ss.select(w,q); x = load(Path(r['drawing_input']))
            original = image_input(design(style=style['id']))
            self.assertEqual(set(x), {'version','style','subject','scene'})
            self.assertEqual(x['subject'], q['subject']); self.assertEqual(x['scene'],q['scene'])
            for role in ('prototype','background','subject','effects','spirit'):
                with self.subTest(style=style['id'],role=role):
                    prompt = render_prompt(x,role,(600,800))
                    self.assertEqual(prompt, render_prompt(original,role,(600,800)))
                    self.assertNotIn(self.q['reason'],prompt)

    def test_different_selection_reasons_have_identical_art_input(self):
        a = request(style={'id':'paper-craft-story','version':'1.0.0'},reason='PRIVATE_A')
        b = copy.deepcopy(a); b['reason'] = 'PRIVATE_B'
        ra=ss.select(self.w/'a',a); rb=ss.select(self.w/'b',b)
        self.assertEqual(Path(ra['drawing_input']).read_bytes(),Path(rb['drawing_input']).read_bytes())

    def test_all_style_references_still_match_selected_style(self):
        for s in catalog():
            r=ss.select(self.w/s['id'],request(style={k:s[k] for k in ('id','version')}))
            self.assertEqual(r['style_reference_images'],style_references(s))

    def test_resumed_portable_action_does_not_explain_style_choice(self):
        p=self.root/'person.json';save(p,person());portable.run(p,self.w,caps())
        ss.select(self.w,self.q);r=portable.run(p,self.w,caps())
        self.assertEqual(set(r['style_selection']),self.keys)
        self.assertNotIn('style_selection',r['next_action'])
        self.assertNotIn('style-selection.md',r['next_action'])
        self.assertNotIn(self.q['reason'],json.dumps(r))

    def test_new_host_still_receives_selection_instructions(self):
        r=ss.selection_status(self.w)
        self.assertEqual(r['status'],'selection_required')
        self.assertEqual(len(r['styles']),5)
        self.assertTrue(Path(r['guide']).is_file())
        self.assertFalse(self.w.exists())

    def test_art_guides_no_longer_route_back_to_selector(self):
        for name in ('CARD.md','prompts/card-generation.md','references/art-direction.md',
                     'references/visual-contract.md','references/card-input-contract.md',
                     'references/quality-workflow.md'):
            text=(ROOT/name).read_text()
            with self.subTest(file=name):
                for selector in ('style-selection.md','select-style','subject_random'):
                    self.assertNotIn(selector,text)

    def test_host_guide_keeps_selection_private(self):
        text=(ROOT/'AGENT.md').read_text()
        self.assertIn('references/style-selection.md',text)
        self.assertIn('选择是宿主内部步骤',text)
        self.assertIn('只有 card-image-input.json',text)

    def test_private_record_and_input_bytes_unchanged_on_resume(self):
        ss.select(self.w,self.q)
        before={f.name:f.read_bytes() for f in self.w.iterdir()}
        result=ss.select(self.w,self.q)
        self.assertTrue(result['reused'])
        self.assertEqual(before,{f.name:f.read_bytes() for f in self.w.iterdir()})


if __name__=='__main__': unittest.main()
