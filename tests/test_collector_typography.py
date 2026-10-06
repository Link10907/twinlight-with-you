"""Measured collector geometry only; visual quality still requires real review."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from twinlight_core.art_typography import typeset
from twinlight_core.visual_contract import default_style


class CollectorTypographyTests(unittest.TestCase):
    def setUp(self):
        self.font = next((p for p in (
            Path('/System/Library/Fonts/Supplemental/Songti.ttc'),
            Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'),
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        ) if p.is_file()), None)
        if self.font is None:
            self.skipTest('No local typography test font')
        self.data = {'summarizer':'GPT','card':{'title':'拾光者','english_title':'THE LIGHT KEEPER',
                     'keywords':['观察','创造','共鸣'],'tagline':'把微小的光，留给正在生长的世界。'}}
        self.theme = default_style()['typography_default']

    def test_collector_layout_preserves_native_canvas_and_frozen_wording(self):
        before = copy.deepcopy(self.data)
        for size in ((300,400),(600,800),(1086,1448)):
            image, report = typeset(self.data,size,self.font,self.theme)
            self.assertEqual(image.size,size);self.assertEqual(self.data,before)
            self.assertFalse(report['overlap']);self.assertEqual(report['layout_profile'],'collector-v10-hierarchy')
            fields = {b['field']:b['box'] for b in report['boxes']}
            self.assertEqual(set(fields),{'rarity','summarizer','title','english_title','keywords','tagline','edition'})
            self.assertGreater(fields['title'][3]-fields['title'][1],2*(fields['english_title'][3]-fields['english_title'][1]))
            self.assertGreater(fields['edition'][1],size[1]*.92)
            self.assertLess(fields['rarity'][3],size[1]*.15)

    def test_light_explicit_alternative_keeps_its_theme(self):
        theme={**self.theme,'layout':'measured','frame':'none','accent_color':'#245949','text_color':'#172521','scrim_color':'#FFFFFF'}
        _,report=typeset(self.data,(600,800),self.font,theme)
        self.assertEqual(report['layout_profile'],'measured');self.assertEqual(report['theme'],theme)


if __name__ == '__main__':
    unittest.main()
