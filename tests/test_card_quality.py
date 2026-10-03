"""Native-canvas locks catch ownership and registration failures, not visual meaning."""
import copy
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from test_card_art import AT, FIXTURE, native_fixture
from twinlight_core import lite
from twinlight_core.art import validate_layers
from twinlight_core.cardgen import card_spec
from twinlight_core.common import ContractError, load, save


class CompositionLock(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = load(FIXTURE)
        self.persona = lite.to_profile(self.data, generated_at=AT)["persona"]["persona_digest"]
        self.manifest = native_fixture(self.root / "card", self.persona)
        self.lock = {"version": "1.0", "persona_digest": self.persona,
                     "canvas": {"width": 600, "height": 800}}

    def attach(self, **regions):
        manifest = load(self.manifest)
        manifest["composition"] = {**copy.deepcopy(self.lock), **regions}
        save(self.manifest, manifest)

    def test_spec_uses_actual_generator_canvas_in_every_image_and_text_brief(self):
        lock = {**self.lock, "canvas": {"width": 1086, "height": 1448},
                "subject_bounds": [.12, .10, .9, .80]}
        spec = card_spec(self.data, generated_at=AT, canvas=(1086, 1448), composition=lock)
        self.assertEqual((spec["canvas"]["width"], spec["canvas"]["height"]), (1086, 1448))
        self.assertEqual(spec["manifest_template"]["composition"], lock)
        for role, prompt in spec["prompts"].items():
            with self.subTest(role=role):
                self.assertIn("1086×1448", prompt)
                self.assertNotIn("1080×1440", prompt)
        self.assertEqual(spec["persona_digest"], self.persona)
        self.assertTrue(spec["quality_review"]["required"])
        self.assertFalse(spec["quality_review"]["automatic_approval"])
        lock["subject_bounds"][0] = .4
        self.assertEqual(spec["composition"]["subject_bounds"][0], .12)

    def test_owner_bound_lock_cannot_follow_a_different_person_or_changed_concept(self):
        for change in ("name", "card"):
            other = copy.deepcopy(self.data)
            if change == "name":
                other["name"] = "不同的人"
            else:
                other["card"]["art_prompt"] = "一艘象征独立旅行的纸舟，暖色晨光。"
            with self.subTest(change=change), self.assertRaisesRegex(ContractError, "different persona"):
                card_spec(other, generated_at=AT, composition=self.lock)
        self.attach(persona_digest="f" * 64)
        with self.assertRaisesRegex(ContractError, "different persona"):
            validate_layers(self.manifest, self.persona)

    def test_layers_keep_full_native_canvas_and_reject_a_different_locked_size(self):
        self.attach(canvas={"width": 900, "height": 1200})
        with self.assertRaisesRegex(ContractError, "regenerate.*cropping"):
            validate_layers(self.manifest, self.persona)
        with Image.open(self.root / "card/subject.png") as original:
            self.assertEqual(original.size, (600, 800))
        with self.assertRaisesRegex(ContractError, "native layer canvas"):
            card_spec(self.data, generated_at=AT, canvas=(600, 800),
                      composition={**self.lock, "canvas": {"width": 900, "height": 1200}})

    def test_explicit_bounds_and_center_accept_registered_subject_but_not_shifted_one(self):
        self.attach(subject_bounds=[.19, .24, .62, .82], subject_center_region=[.35, .48, .45, .57])
        report = validate_layers(self.manifest, self.persona)
        self.assertTrue(report["ok"])
        self.assertAlmostEqual(report["composition"]["subject_alpha_center"][0], .4, delta=.01)
        shifted = Image.new("RGBA", (600, 800))
        ImageDraw.Draw(shifted).ellipse((330, 200, 570, 640), fill=(50, 120, 110, 255))
        shifted.save(self.root / "card/subject.png")
        with self.assertRaisesRegex(ContractError, "subject_bounds"):
            validate_layers(self.manifest, self.persona)
        self.attach(subject_center_region=[.35, .48, .45, .57])
        with self.assertRaisesRegex(ContractError, "subject_center_region"):
            validate_layers(self.manifest, self.persona)

    def test_only_explicit_text_space_blocks_foreground_over_title(self):
        self.attach(text_safe_regions=[[.02, .02, .15, .12]])
        self.assertTrue(validate_layers(self.manifest, self.persona)["ok"])
        effects = Image.open(self.root / "card/effects.png").convert("RGBA")
        ImageDraw.Draw(effects).rectangle((12, 16, 90, 96), fill=(210, 170, 90, 255))
        effects.save(self.root / "card/effects.png")
        with self.assertRaisesRegex(ContractError, "locked text space"):
            validate_layers(self.manifest, self.persona)
        # With no selected safe region, the validator must not invent one.
        self.attach()
        report = validate_layers(self.manifest, self.persona)
        self.assertTrue(report["ok"])
        self.assertNotIn("text_safe_regions", report["composition"])
        self.assertFalse(report["quality_verified"])

    def test_legacy_manifest_remains_compatible_and_never_auto_approves(self):
        report = validate_layers(self.manifest, self.persona)
        self.assertTrue(report["ok"])
        self.assertNotIn("composition", report)
        self.assertEqual(report["art_status"], "generated")
        self.assertFalse(report["automatic_approval"])
        self.assertFalse(report["quality_verified"])
        self.assertGreater(len(report["visual_review_required"]), 0)
        self.assertEqual(load(self.manifest)["art_status"], "generated")

    def test_geometry_is_explicit_and_prototype_hash_is_traceability_not_fake_verification(self):
        self.attach(subject_bounds=[.7, .2, .3, .8])
        with self.assertRaisesRegex(ContractError, "positive width"):
            validate_layers(self.manifest, self.persona)
        self.attach(source_prototype_sha256="a" * 64)
        report = validate_layers(self.manifest, self.persona)
        self.assertEqual(report["composition"]["source_prototype_sha256"], "a" * 64)
        self.assertFalse(report["composition"]["prototype_hash_verified_by_layer_validator"])


if __name__ == "__main__":
    unittest.main()
