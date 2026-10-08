"""Synthetic routing tests only; not image or independent review evidence."""
import sys, unittest
from pathlib import Path
from quality_fixtures import ROOT
from twinlight_core.browser_runtime import finale_route, launch_flags
class RuntimeTests(unittest.TestCase):
 def state(self,**kwargs):return dict(webgl=True,reduced=False,hidden=False,testing=False,ready=True,**{})|kwargs
 def test_normal_route(self):self.assertEqual(finale_route(self.state())['route'],'autoplay')
 def test_fallback_route(self):self.assertEqual(finale_route(self.state(webgl=False,reduced=True))['reason'],'webgl_fallback_forces_reduced_motion')
 def test_user_reduced_route(self):self.assertEqual(finale_route(self.state(reduced=True))['reason'],'reduced_motion_active')
 def test_no_webgl_not_reduced(self):self.assertEqual(finale_route(self.state(webgl=False))['route'],'unavailable')
 def test_unknown_not_approved(self):self.assertEqual(finale_route({})['route'],'unavailable')
 def test_frozen_not_approved(self):self.assertEqual(finale_route(self.state(testing=True))['route'],'unavailable')
 def test_hidden_not_approved(self):self.assertEqual(finale_route(self.state(hidden=True))['route'],'unavailable')
 def test_not_ready(self):self.assertEqual(finale_route(self.state(ready=False))['route'],'unavailable')
 def test_route_is_not_proof(self):self.assertFalse(finale_route(self.state())['autoplay_verified'])
 def test_auto_no_swiftshader(self):self.assertFalse(any('swiftshader' in f for f in launch_flags()))
 def test_explicit_swiftshader(self):self.assertIn('--use-angle=swiftshader',launch_flags('swiftshader'))
 def test_unknown_flags_fail(self):
  with self.assertRaises(ValueError):launch_flags('made-up')
if __name__=='__main__':unittest.main()
