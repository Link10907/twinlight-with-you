"""Template provenance requires reconstructed bytes, not a self-reported receipt."""
from __future__ import annotations
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from twinlight_core import lite, site
from twinlight_core.common import load, save
from twinlight_core.template_origin import verify_site

AT='2026-10-03T00:00:00Z'
LAYERS={name:'auto' for name in ('background','subject','spirit','effects','text','lineart')}
DEPTHS={'background':-.25,'subject':.4,'effects':.5,'text':0}


class TemplateOrigin(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.out=self.root/'site'
        self.data=load(ROOT/'tests/fixtures/lite/valid.json')
        self.profile=lite.to_profile(self.data,generated_at=AT)
        site.write_site(self.out,self.profile,LAYERS,'auto',DEPTHS)

    def codes(self,result):
        return {entry['code'] for entry in result['errors']}

    def files(self):
        return {p.name:p.read_bytes() for p in self.out.iterdir() if p.is_file()}

    def test_record_adds_no_visual_or_script_changes_and_survives_relocation(self):
        html,js=site.template_parts()
        values=site.personal_values(self.profile,LAYERS,'auto',DEPTHS)
        self.assertEqual((self.out/'index.html').read_bytes(),site.fill(html,values).encode())
        self.assertEqual((self.out/'compiled-check.js').read_bytes(),site.fill(js,values).encode())
        receipt=load(self.out/'template-receipt.json')
        self.assertEqual(receipt['persona_digest'],self.profile['persona']['persona_digest'])
        self.assertEqual(set(receipt['template_source_files_sha256']),set(site.template_source_hashes()))
        self.assertNotIn(self.data['name'],json.dumps(receipt,ensure_ascii=False))
        before=self.files()
        self.assertTrue(verify_site(self.out)['ok'])
        self.assertTrue(verify_site(self.out/'index.html')['ok'])
        self.assertEqual(self.files(),before)
        moved=self.root/'relocated';shutil.copytree(self.out,moved)
        self.assertTrue(verify_site(moved)['ok'])

    def test_forged_output_hash_cannot_approve_rewritten_html(self):
        html=self.out/'index.html'
        html.write_bytes(b'<!doctype html><html><body><script>window.twinlightSkill={};'
                         b'window.twinlightV10={};</script>Custom replacement</body></html>')
        receipt=load(self.out/'template-receipt.json')
        receipt['output_files']['index.html']={'sha256':hashlib.sha256(html.read_bytes()).hexdigest(),
                                             'bytes':html.stat().st_size}
        save(self.out/'template-receipt.json',receipt)
        before=self.files();result=verify_site(self.out)
        self.assertFalse(result['ok'])
        self.assertIn('reconstruction_mismatch',self.codes(result))
        self.assertNotIn('output_changed',self.codes(result))
        self.assertEqual(self.files(),before)

    def test_profile_and_art_input_changes_are_detected_without_echoing_content(self):
        originals=self.files()
        for name in ('profile.json','render-inputs.json'):
            with self.subTest(name=name):
                for file,data in originals.items():(self.out/file).write_bytes(data)
                changed=load(self.out/name)
                marker='PRIVATE_CHANGED_INPUT_DO_NOT_REPORT'
                if name=='profile.json':changed['intro']=marker
                else:changed['layer_uris']['background']=marker
                save(self.out/name,changed)
                before=self.files();result=verify_site(self.out)
                self.assertFalse(result['ok'])
                self.assertIn('input_changed',self.codes(result))
                self.assertIn('render_input_changed',self.codes(result))
                self.assertIn('reconstruction_mismatch',self.codes(result))
                self.assertNotIn(marker,json.dumps(result))
                self.assertEqual(self.files(),before)

    def test_style_script_markup_and_embedded_media_changes_are_detected(self):
        template=self.root/'template';shutil.copytree(site.TEMPLATE,template)
        for relative in ('src/style.css','src/v10.js','src/page.html','assets/dust-disc.jpg'):
            with self.subTest(source=relative),mock.patch.object(site,'TEMPLATE',template):
                source=template/relative;original=source.read_bytes()
                source.write_bytes(original+b'\nchanged template source\n')
                before=self.files();result=verify_site(self.out)
                self.assertFalse(result['ok'])
                self.assertIn('template_source_changed',self.codes(result))
                self.assertIn('template_changed',self.codes(result))
                self.assertIn('reconstruction_mismatch',self.codes(result))
                self.assertEqual(self.files(),before)
                source.write_bytes(original)

    def test_different_people_and_content_remain_valid_under_same_template(self):
        changed=copy.deepcopy(self.data)
        changed['name']='另一位虚构用户'
        changed['themes']=changed['themes'][:1]
        changed['card']['title']='新的定义'
        profile=lite.to_profile(changed,generated_at=AT)
        out=self.root/'another'
        site.write_site(out,profile,LAYERS,'auto',DEPTHS)
        self.assertTrue(verify_site(out)['ok'])
        old=load(self.out/'template-receipt.json');new=load(out/'template-receipt.json')
        self.assertEqual(old['template_sha256'],new['template_sha256'])
        self.assertNotEqual(old['persona_digest'],new['persona_digest'])
        self.assertNotEqual(old['render_inputs_sha256'],new['render_inputs_sha256'])

    def test_lite_and_strict_builds_share_receipt_and_verification(self):
        lite_out=self.root/'lite'
        site.build_lite(self.data,lite_out,generated_at=AT)
        strict_out=self.root/'strict'
        site.build(load(ROOT/'examples/demo/history.json'),load(ROOT/'examples/demo/analysis.json'),strict_out)
        self.assertTrue(verify_site(lite_out)['ok'])
        self.assertTrue(verify_site(strict_out)['ok'])
        self.assertEqual(load(lite_out/'template-receipt.json')['template_sha256'],
                         load(strict_out/'template-receipt.json')['template_sha256'])

    def test_missing_receipt_and_malformed_inputs_fail_read_only(self):
        original=(self.out/'template-receipt.json').read_bytes()
        (self.out/'template-receipt.json').unlink()
        before=self.files();result=verify_site(self.out)
        self.assertFalse(result['ok']);self.assertIn('missing_or_invalid',self.codes(result))
        self.assertEqual(self.files(),before)
        (self.out/'template-receipt.json').write_bytes(original)
        (self.out/'render-inputs.json').write_text('{"schema_version":"template-render-1"}')
        before=self.files();result=verify_site(self.out)
        self.assertFalse(result['ok']);self.assertIn('invalid_render_inputs',self.codes(result))
        self.assertEqual(self.files(),before)

    def test_cli_succeeds_and_failure_does_not_modify_site(self):
        args=[sys.executable,str(ROOT/'scripts/twinlight.py'),'verify-site',str(self.out/'index.html')]
        before=self.files();passed=subprocess.run(args,capture_output=True,text=True,timeout=30)
        self.assertEqual(passed.returncode,0,passed.stderr)
        self.assertTrue(json.loads(passed.stdout)['ok']);self.assertEqual(self.files(),before)
        html=self.out/'index.html';html.write_bytes(html.read_bytes()+b'\nchanged\n')
        before=self.files();failed=subprocess.run(args,capture_output=True,text=True,timeout=30)
        self.assertEqual(failed.returncode,1,failed.stderr)
        self.assertFalse(json.loads(failed.stdout)['ok']);self.assertEqual(self.files(),before)


if __name__=='__main__':unittest.main()
