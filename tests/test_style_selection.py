"""Style routing and reference isolation, separate from actual image-quality trials."""
import json
import tempfile
import unittest
from pathlib import Path

from visual_v2_fixtures import design, save
from twinlight_core.generation_plan import write_plan
from twinlight_core.visual_contract import default_style, style_for, style_references


class StyleSelectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.caps = {'version':'image-capabilities-1','image_generation':True,
                     'reference_images':True,'native_transparency':True,
                     'canvas_selection':'prompt_only','native_canvases':[],
                     'source':'Synthetic compiler fixture, not an actual image provider invocation.'}

    def compile(self, style_id, kind):
        selected = style_for(style_id)
        content = design(kind, style_id)
        content['typography'] = selected['typography_default']
        out = self.root / (style_id + '-' + kind)
        out.mkdir()
        save(out / 'design.json', content)
        plan = write_plan(out / 'design.json', out, capabilities=self.caps)
        prompt = (out / plan['jobs'][0]['prompt']['file']).read_text()
        return content, plan, prompt

    def test_forest_and_eastern_do_not_change_global_default(self):
        self.compile('forest-fantasy', 'human')
        self.compile('eastern-fantasy-scroll', 'animal')
        self.assertEqual(default_style()['id'], 'twinlight-collector')

    def test_forest_subject_is_not_inferred_from_its_deer_reference(self):
        for kind in ('human', 'animal', 'object'):
            content, plan, prompt = self.compile('forest-fantasy', kind)
            persisted = json.loads((self.root / ('forest-fantasy-' + kind) / 'art-direction.json').read_text())
            self.assertEqual(persisted['subject'], content['subject'])
            self.assertIn(content['subject']['species'], prompt)
            self.assertEqual(plan['style_binding']['id'], 'forest-fantasy')

    def test_selected_references_do_not_import_collector_human_style(self):
        collector_hashes = {ref['sha256'] for ref in style_references(default_style())}
        forest_hashes = {ref['sha256'] for ref in style_references(style_for('forest-fantasy'))}
        human_hashes = collector_hashes - forest_hashes
        self.assertTrue(human_hashes)
        for style_id in ('forest-fantasy', 'eastern-fantasy-scroll'):
            _, plan, _ = self.compile(style_id, 'human')
            actual = {r['sha256'] for r in plan['jobs'][0]['reference_images']}
            expected = {r['sha256'] for r in style_references(style_for(style_id))}
            self.assertEqual(actual, expected)
            self.assertFalse(actual & human_hashes)

    def test_compiled_drawing_instructions_come_from_selected_style(self):
        for style_id in ('forest-fantasy', 'eastern-fantasy-scroll'):
            style = style_for(style_id)
            content, plan, prompt = self.compile(style_id, 'human')
            self.assertEqual(content['typography'], style['typography_default'])
            for field in ('visual_language', 'materials_and_light', 'palette'):
                self.assertIn(style[field], prompt)
            self.assertEqual(plan['style_binding']['sha256'], style['sha256'])


if __name__ == '__main__':
    unittest.main()
