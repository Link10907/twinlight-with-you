"""SYNTHETIC pixels test native-return rounding policy, never aesthetic approval."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image,ImageDraw
from visual_v2_fixtures import dossier,sha256,save,PERSONA,ROOT
from twinlight_core.canvas_mapping import native_dimensions_allowed,mapping_for,logical_canvas,render_layers,compose_layers
from twinlight_core.generation_plan import write_plan,register_image,revalidate_image
from twinlight_core.visual_contract import VisualContractError

CAPS={'version':'image-capabilities-1','image_generation':True,'reference_images':True,'native_transparency':True,
      'source':'SYNTHETIC native rounding tests only','native_canvases':[[600,800]]}


class RoundingPolicyTests(unittest.TestCase):
    def test_only_explicit_native_edit_allows_one_pixel(self):
        self.assertTrue(native_dimensions_allowed((600,800),(600,800)))
        self.assertFalse(native_dimensions_allowed((601,799),(600,800)))
        self.assertTrue(native_dimensions_allowed((601,799),(600,800),native_edit=True))
        self.assertFalse(native_dimensions_allowed((602,800),(600,800),native_edit=True))
        self.assertFalse(native_dimensions_allowed((True,800),(600,800),native_edit=True))

    def test_display_sampling_preserves_original_pixels_and_full_frame(self):
        images={name:Image.new('RGBA',(600,800)) for name in ('background','subject','effects','spirit','text','lineart')}
        images['background']=Image.new('RGBA',(600,800),(40,40,50,255))
        images['subject']=Image.new('RGBA',(601,799),(200,50,80,200))
        images['lineart']=Image.new('RGBA',(601,799),'white')
        before={name:(im.size,im.tobytes()) for name,im in images.items()}
        mapping=mapping_for((600,800),images,['subject']);manifest={'canvas_mapping':mapping}
        self.assertEqual(logical_canvas(manifest,images),(600,800))
        displayed=render_layers(manifest,images)
        self.assertTrue(all(im.size==(600,800) for im in displayed.values()))
        self.assertEqual(compose_layers(manifest,images,include_text=True).size,(600,800))
        self.assertEqual(before,{name:(im.size,im.tobytes()) for name,im in images.items()})
        with self.assertRaises(ValueError):logical_canvas({},images)
        with self.assertRaises(ValueError):mapping_for((600,800),images,['effects'])
        images['subject']=Image.new('RGBA',(602,800))
        with self.assertRaises(ValueError):logical_canvas(manifest,images)


class NativeReturnTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name).resolve()
        dossier(self.root)
        self.plan=self.root/'generation-plan.json'
        write_plan(self.root/'art-direction.json',self.root,phase='layers',capabilities=CAPS)
        self.raw=self.root/'synthetic-response.txt';self.raw.write_text('SYNTHETIC returned artifact rounding-one')
        self.image=self.root/'returned.png';im=Image.new('RGBA',(601,799));ImageDraw.Draw(im).ellipse((100,150,500,700),fill=(180,120,90,255));im.save(self.image)

    def register(self):
        return register_image(self.plan,'subject',self.image,self.raw,tool='SYNTHETIC-TEST-ADAPTER',call_id='rounding1',artifact_id='rounding-one')

    def test_one_pixel_native_return_records_true_size_and_preserves_bytes(self):
        original=self.image.read_bytes();r=self.register();self.assertTrue(r['ok'],r)
        self.assertEqual(r['returned_canvas'],[601,799]);self.assertEqual(r['requested_canvas'],[600,800])
        self.assertEqual((self.root/'subject.png').read_bytes(),original)
        e=json.loads((self.root/'art-evidence.json').read_text());call=json.loads((self.root/e['images']['subject']['call']['file']).read_text())
        self.assertEqual(call['response']['canvas'],[601,799]);self.assertFalse(call['response']['canvas_mapping']['source_pixels_modified'])
        self.assertEqual(json.loads((self.root/'layers.json').read_text())['canvas_mapping']['native_edit_roles'],['subject'])

    def test_more_than_one_pixel_stays_rejected_and_preserved(self):
        im=Image.new('RGBA',(602,800));ImageDraw.Draw(im).ellipse((100,150,500,700),fill='white');im.save(self.image)
        r=self.register();self.assertFalse(r['ok']);self.assertEqual(r['error_code'],'canvas_mismatch')
        self.assertEqual(r['returned_canvas'],[602,800])
        e=json.loads((self.root/'art-evidence.json').read_text());attempt=e['attempts'][-1]
        self.assertEqual((self.root/attempt['image']['file']).read_bytes(),self.image.read_bytes())
        with self.assertRaises(VisualContractError):
            revalidate_image(self.plan,attempt['key'],tool='wrong-tool',call_id='rounding1',artifact_id='rounding-one')

    def test_policy_revalidation_preserves_original_rejection_and_attempt_count(self):
        with patch('twinlight_core.generation_plan.native_dimensions_allowed',return_value=False):
            r=self.register()
        self.assertFalse(r['ok']);e=json.loads((self.root/'art-evidence.json').read_text());before=e['attempts'][-1].copy()
        result=revalidate_image(self.plan,before['key'],tool='SYNTHETIC-TEST-ADAPTER',call_id='rounding1',artifact_id='rounding-one')
        self.assertTrue(result['ok'],result);self.assertFalse(result['new_image_call'])
        e=json.loads((self.root/'art-evidence.json').read_text());self.assertEqual(len(e['attempts']),1)
        for key,value in before.items():self.assertEqual(e['attempts'][0][key],value)
        self.assertTrue(e['attempts'][0]['revalidations'][0]['original_rejection_preserved'])
        self.assertEqual((self.root/'subject.png').read_bytes(),self.image.read_bytes())
        with self.assertRaises(VisualContractError):
            revalidate_image(self.plan,before['key'],tool='SYNTHETIC-TEST-ADAPTER',call_id='rounding1',artifact_id='rounding-one')

    def test_assembly_preserves_native_bytes_and_renders_only_logical_canvas(self):
        from prepare_card_layers import prepare
        from twinlight_core.site import render_card_preview
        font=next((p for p in (Path('/System/Library/Fonts/Supplemental/Songti.ttc'),
                              Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc')) if p.is_file()),None)
        if font is None:self.skipTest('No local Chinese typography font')
        self.assertTrue(self.register()['ok'])
        before={role:(self.root/(role+'.png')).read_bytes() for role in ('subject','background','effects')}
        data=json.loads((ROOT/'tests/fixtures/lite/valid.json').read_text())
        design=(self.root/'art-direction.json').read_text()
        with patch('twinlight_core.lite.persona_digest',return_value=PERSONA):
            report=prepare(data,self.root/'background.png',self.root/'subject.png',self.root/'effects.png',
                           self.root,font,prototype=self.root/'prototype.png',art_prompt=design)
            self.assertEqual(report['size'],[600,800])
            render_card_preview(data,self.root/'rendered-front.png',layers=self.root/'layers.json')
        for role,original in before.items():self.assertEqual((self.root/(role+'.png')).read_bytes(),original)
        with Image.open(self.root/'subject.png') as im:self.assertEqual(im.size,(601,799))
        with Image.open(self.root/'lineart.png') as im:self.assertEqual(im.size,(601,799))
        with Image.open(self.root/'text.png') as im:self.assertEqual(im.size,(600,800))
        with Image.open(self.root/'rendered-front.png') as im:self.assertEqual(im.size,(600,800))


if __name__=='__main__':unittest.main()
