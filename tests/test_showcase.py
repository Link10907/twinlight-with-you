"""Optional local legacy fixtures retain their content without implying permission to publish."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from twinlight_core.common import load  # noqa: E402
from twinlight_core.showcase import LAYER_FILES, NODES, SHOWCASE, orbit, showcase_profile  # noqa: E402


@unittest.skipUnless((SHOWCASE / 'profile.json').is_file(), 'Private legacy assets are intentionally not distributed')
class Showcase(unittest.TestCase):
    def setUp(self):
        self.p = showcase_profile()

    def test_every_v10_star_planet_and_line_survives(self):
        src = load(SHOWCASE / 'profile.json')
        self.assertEqual(len(self.p['chapters']), 5)
        self.assertEqual(len(self.p['layout']['topics']), 40)
        for a, b in zip(src['chapters'], self.p['chapters']):
            self.assertEqual(a['story'], b['story'])
            self.assertEqual([t['body'] for t in a['topics']], [t['body'] for t in b['topics']])
        self.assertEqual(self.p['persona']['title'], load(SHOWCASE / 'persona-card.json')['title'])
        self.assertTrue(all((SHOWCASE / 'card' / f).is_file() for f in LAYER_FILES.values()))

    def test_layout_matches_v10_and_template_limits(self):
        stars = self.p['layout']['stars']
        self.assertEqual([s['position'] for s in stars], NODES)
        self.assertEqual([s['material'] for s in stars], [0, 1, 2, 3, 4])
        ids = set()
        for i, c in enumerate(self.p['chapters']):
            for j, t in enumerate(c['topics']):
                spec = next(s for s in self.p['layout']['topics'] if s['parent_id'] == c['id'] and s['id'] == t['id'])
                self.assertEqual({k: spec[k] for k in orbit(i, j)}, orbit(i, j))
                self.assertTrue(.5 <= spec['radius'] <= 6 and 8 <= spec['orbitRadius'] <= 80 and abs(spec['eccentricity']) <= .5)
                ids.add((c['id'], t['id']))
        self.assertEqual(len(ids), 40)

    def test_local_review_does_not_imply_public_release(self):
        self.assertEqual(self.p['release'], {'draft': True, 'share_allowed': False})
        self.assertEqual(self.p['persona']['art_status'], 'approved')
        self.assertNotIn('layout', load(SHOWCASE / 'profile.json'))


if __name__ == '__main__':
    unittest.main()
