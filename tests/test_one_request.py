"""One request produces local card and HTML drafts without fabricating consent."""
from __future__ import annotations
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from PIL import Image, ImageDraw
from twinlight_core import lite, site, state
from twinlight_core.common import ContractError, load, save
from test_card_art import native_fixture


DATA = {
    "twinlight": "lite-1", "name": "合成预览", "summarizer": "未知",
    "themes": [{"label": "技术测试", "english": "TEST", "headline": "仅用于流程测试。",
                "story": ["这些是虚构的测试资料，不描述真实人物。"], "reflection": "仅供测试。", "topics": []}],
    "card": {"title": "预览卡片", "english_title": "PREVIEW CARD", "keywords": ["合成", "校验", "预览"],
             "tagline": "仅用于本地流程测试。", "reflection": "不描述真实人物。",
             "art_prompt": "仅用于技术测试的原创抽象几何插画，蓝色圆形位于完整竖版画布中央，不描述真实人物。"},
}
BRIEF = "本次独立美术设定：原创纸本版画中的折纸罗盘，低饱和蓝绿与细金线，主体清楚，保留上下文字空间。"


class OneRequest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ws = (Path(self.tmp.name) / "run").resolve()

    def start(self, preview=True, data=None):
        state.start(self.ws, preview_only=preview)
        save(self.ws / "twinlight.json", copy.deepcopy(DATA if data is None else data))
        result = state.check_stage(self.ws)
        self.assertEqual(result["next"]["stage"], "review")
        return result["next"]

    def local_review(self):
        result = state.check_stage(self.ws)
        self.assertEqual((result["status"], result["next"]["stage"]), ("skipped", "art"))
        return result["next"]

    def native(self, size=(600, 800)):
        saved = load(self.ws / "state.json")
        data = load(self.ws / "twinlight.json")
        persona = lite.to_profile(data, generated_at=saved["created_at"])["persona"]["persona_digest"]
        manifest = native_fixture(self.ws / "card", persona, size=size)
        if size[0] * size[1] > 600 * 800:
            # The shared fixture's fixed 30px effect is too sparse on a larger
            # canvas. Make a valid independent synthetic effect at native size.
            width, height = size
            effects = self.ws / "card" / "effects.png"
            with Image.open(effects) as image:
                ImageDraw.Draw(image).ellipse((width * 3 // 4, height // 12, width * 7 // 8, height // 6),
                                              fill=(230, 210, 120, 240))
                image.save(effects)
        return manifest

    def static(self):
        image = self.ws / "card" / "prototype.png"
        Image.new("RGB", (600, 800), "navy").save(image)
        result = state.choose_art(self.ws, "static")
        self.assertEqual((result["status"], result["next"]["stage"]), ("passed", "build"))
        return image

    def finish(self):
        # This exercises the real unavailable-browser route, without an external browser.
        with mock.patch.dict(sys.modules, {"playwright": None}):
            for _ in range(8):
                following = state.next_action(self.ws)
                if following["stage"] == "done":
                    return following
                result = state.check_stage(self.ws)
                self.assertNotIn(result.get("status"), ("failed", "blocked"), result)
        self.fail("The workflow did not finish automatically")

    def test_one_request_delivers_card_and_html_without_confirmation(self):
        following = self.start()
        self.assertIn("check", following["then"])
        self.assertNotIn("confirm", following["then"])
        following = self.local_review()
        self.assertIn(str(ROOT / "prompts" / "card-generation.md"), following["read"])
        manifest = self.native()
        inputs = {path: path.read_bytes() for path in (self.ws / "card").glob("*") if path.is_file()}
        calls = []
        render = site.render_card_preview
        build = site.build_lite

        def render_card(*args, **kwargs):
            calls.append("card")
            result = render(*args, **kwargs)
            self.assertTrue((self.ws / "card" / "front.png").is_file())
            self.assertEqual({path: path.read_bytes() for path in inputs}, inputs)
            return result

        def build_html(*args, **kwargs):
            calls.append("html")
            self.assertTrue((self.ws / "card" / "front.png").is_file())
            self.assertFalse(kwargs["confirmed"])
            return build(*args, **kwargs)

        with mock.patch.object(site, "render_card_preview", side_effect=render_card), \
                mock.patch.object(site, "build_lite", side_effect=build_html), \
                mock.patch.object(state, "confirm", side_effect=AssertionError("Must not fabricate consent")):
            checked = state.check_stage(self.ws)
            self.assertEqual(checked["next"]["stage"], "build")
            self.assertIn(str(ROOT / "prompts" / "html-build.md"), checked["next"]["read"])
            following = self.finish()

        self.assertEqual(calls, ["card", "html"])
        self.assertEqual({path: path.read_bytes() for path in inputs}, inputs)
        self.assertTrue(manifest.is_file())
        self.assertEqual(Path(following["card_preview"]), self.ws / "card" / "front.png")
        self.assertEqual(Path(following["html"]), self.ws / "site" / "index.html")
        self.assertTrue(Path(following["card_preview"]).is_file())
        self.assertTrue(Path(following["html"]).is_file())
        self.assertFalse(following["text_confirmed"])
        self.assertEqual(load(self.ws / "site" / "profile.json")["release"], {"draft": True, "share_allowed": False})
        review = load(self.ws / "state.json")["stages"]["review"]
        self.assertEqual(review["status"], "skipped")
        self.assertEqual(review["detail"]["reason"], "local_preview")
        self.assertFalse(review["detail"]["confirmed"])
        self.assertNotIn("user_reply", review["detail"])
        self.assertEqual(review["detail"]["profile_sha256"], state.sha(self.ws / "twinlight.json"))
        report = (self.ws / "report.html").read_text(encoding="utf-8")
        self.assertIn("本地未确认草稿", report)
        self.assertNotIn("用户确认：", report)

    def test_html_retry_keeps_the_accepted_card_and_review(self):
        self.start()
        self.local_review()
        self.native()
        self.assertEqual(state.check_stage(self.ws)["next"]["stage"], "build")
        accepted = load(self.ws / "state.json")["stages"]
        original_card = (self.ws / "card" / "front.png").read_bytes()

        with mock.patch.object(site, "build_lite", side_effect=ContractError("Synthetic HTML build failure")):
            failed = state.check_stage(self.ws)
        self.assertEqual((failed["stage"], failed["status"], failed["next"]["stage"]),
                         ("build", "failed", "build"))
        after_failure = load(self.ws / "state.json")["stages"]
        self.assertEqual(after_failure["art"], accepted["art"])
        self.assertEqual(after_failure["review"], accepted["review"])

        with mock.patch.object(site, "render_card_preview", side_effect=AssertionError("HTML retry must keep accepted card")):
            following = self.finish()
        self.assertEqual(following["stage"], "done")
        self.assertEqual((self.ws / "card" / "front.png").read_bytes(), original_card)
        self.assertTrue(Path(following["html"]).is_file())
        self.assertFalse(following["text_confirmed"])

    def test_legacy_start_still_waits_for_real_confirmation(self):
        following = self.start(preview=False)
        self.assertIn("confirm", following["then"])
        self.assertEqual(state.check_stage(self.ws)["status"], "pending")
        self.assertEqual(state.status(self.ws)["current"], "review")
        with self.assertRaises(ContractError):
            state.choose_placeholder(self.ws)
        self.assertFalse((self.ws / "card" / "front.png").exists())
        state.confirm(self.ws, "这些虚构测试资料可以使用")
        state.choose_placeholder(self.ws)
        following = self.finish()
        self.assertTrue(following["text_confirmed"])

    def test_real_confirmation_upgrades_draft_and_text_edit_invalidates_it(self):
        self.start()
        self.local_review()
        self.static()
        self.finish()
        reply = "我确认本次虚构测试文案"
        following = state.confirm(self.ws, reply)["next"]
        self.assertEqual(following["stage"], "art")
        self.assertTrue(following["text_confirmed"])
        self.finish()
        self.assertEqual(load(self.ws / "site" / "profile.json")["release"], {"draft": False, "share_allowed": True})
        review = load(self.ws / "state.json")["stages"]["review"]
        self.assertEqual(review["detail"]["user_reply"], reply)

        changed = load(self.ws / "twinlight.json")
        changed["card"]["tagline"] = "修改后的虚构测试文字。"
        save(self.ws / "twinlight.json", changed)
        with self.assertRaises(ContractError):
            state.confirm(self.ws, "不能用于新版文字的旧确认")
        stages = load(self.ws / "state.json")["stages"]
        self.assertEqual(stages["profile"]["status"], "pending")
        self.assertEqual(stages["review"]["status"], "pending")
        self.assertNotIn("user_reply", stages["review"]["detail"])
        following = self.finish()
        self.assertFalse(following["text_confirmed"])
        self.assertEqual(load(self.ws / "site" / "profile.json")["release"], {"draft": True, "share_allowed": False})

    def test_preview_review_must_match_current_validated_profile(self):
        self.start()
        with self.assertRaises(ContractError):
            state.choose_placeholder(self.ws)
        self.local_review()
        changed = load(self.ws / "twinlight.json")
        changed["card"]["tagline"] = "这是不同的虚构文案。"
        save(self.ws / "twinlight.json", changed)
        with self.assertRaises(ContractError):
            state.choose_placeholder(self.ws)
        self.assertEqual(state.status(self.ws)["current"], "profile")

    def test_art_changes_reopen_card_and_html_while_preserving_deferred_review(self):
        self.start()
        self.local_review()
        self.native()
        self.finish()
        subject = self.ws / "card" / "subject.png"
        with Image.open(subject) as image:
            image.putpixel((250, 350), (180, 80, 130, 255))
            image.save(subject)
        self.assertEqual(state.status(self.ws)["current"], "art")
        stages = load(self.ws / "state.json")["stages"]
        self.assertEqual(stages["build"]["status"], "pending")
        self.assertEqual(stages["review"]["status"], "skipped")
        self.assertNotIn("user_reply", stages["review"]["detail"])
        self.finish()

    def test_changed_or_missing_card_preview_cannot_leave_run_done(self):
        self.start()
        self.local_review()
        self.static()
        self.finish()
        preview = self.ws / "card" / "front.png"
        preview.write_bytes(b"modified preview")
        self.assertEqual(state.status(self.ws)["current"], "art")
        self.finish()
        preview.unlink()
        self.assertEqual(state.next_action(self.ws)["stage"], "art")

    def test_placeholder_downgrade_still_builds_html(self):
        self.start()
        self.local_review()
        state.choose_placeholder(self.ws)
        following = self.finish()
        self.assertEqual(following["art_mode"], "placeholder")
        self.assertTrue(Path(following["card_preview"]).is_file())
        self.assertTrue(Path(following["html"]).is_file())
        self.assertFalse(following["text_confirmed"])

    def test_provided_layers_lock_actual_canvas_and_typography_without_prototype(self):
        self.start()
        self.local_review()
        manifest = self.native(size=(1086, 1448))
        original = {path: path.read_bytes() for path in (self.ws / "card").glob("*") if path.is_file()}
        text = (self.ws / "twinlight.json").read_bytes()
        self.assertFalse((self.ws / "card" / "prototype.png").exists())
        for _ in range(2):
            following = state.next_action(self.ws)
            spec = following["card_spec"]
            self.assertEqual((spec["canvas"]["width"], spec["canvas"]["height"]), (1086, 1448))
            self.assertEqual(following["existing_art"]["canvas"], [1086, 1448])
            self.assertEqual(following["existing_art"]["source"], "layers")
            self.assertTrue(following["existing_art"]["validated"])
            self.assertEqual(spec["typography"]["title"], DATA["card"]["title"])
            self.assertEqual(spec["typography"]["keywords"], DATA["card"]["keywords"])
            self.assertEqual(spec["typography"]["summarizer"], DATA["summarizer"])
            for prompt in spec["prompts"].values():
                self.assertIn("1086×1448", prompt)
                self.assertNotIn("1080×1440", prompt)
            self.assertIn("不再生成原型", " ".join(following["do"]))
            self.assertEqual({path: path.read_bytes() for path in original}, original)
            self.assertFalse((self.ws / "card" / "front.png").exists())
        following = self.finish()
        with Image.open(following["card_preview"]) as preview:
            self.assertEqual(preview.size, (1086, 1448))
        self.assertTrue(Path(following["html"]).is_file())
        self.assertEqual((self.ws / "twinlight.json").read_bytes(), text)
        self.assertEqual({path: path.read_bytes() for path in original}, original)
        self.assertTrue(manifest.is_file())

    def test_existing_prototype_and_native_pair_select_actual_canvas(self):
        root = self.ws
        for role in ("prototype", "native_pair"):
            with self.subTest(role=role):
                self.ws = root / role
                self.start()
                self.local_review()
                if role == "prototype":
                    Image.new("RGB", (1086, 1448), "navy").save(self.ws / "card" / "prototype.png")
                else:
                    self.native(size=(1086, 1448)).unlink()
                original = {path: path.read_bytes() for path in (self.ws / "card").glob("*") if path.is_file()}
                following = state.next_action(self.ws)
                self.assertEqual(following["existing_art"]["source"], role)
                self.assertTrue(following["existing_art"]["validated"])
                self.assertEqual(following["existing_art"]["canvas"], [1086, 1448])
                for prompt in following["card_spec"]["prompts"].values():
                    self.assertIn("1086×1448", prompt)
                self.assertIn("复用", " ".join(following["do"]))
                self.assertEqual({path: path.read_bytes() for path in original}, original)

    def test_wrong_person_and_malformed_layers_remain_repairable(self):
        self.start()
        self.local_review()
        manifest = self.native(size=(1086, 1448))
        original = load(manifest)
        for failure in ("different persona", "malformed"):
            with self.subTest(failure=failure):
                if failure == "different persona":
                    wrong = copy.deepcopy(original)
                    wrong["persona_digest"] = "f" * 64
                    save(manifest, wrong)
                else:
                    manifest.write_text("not-json", encoding="utf-8")
                corrupted = manifest.read_bytes()
                following = state.next_action(self.ws)
                self.assertEqual(following["stage"], "art")
                self.assertFalse(following["existing_art"]["validated"])
                self.assertTrue(following["errors"])
                self.assertEqual(following["card_spec"]["canvas"]["width"], 1080)
                if failure == "different persona":
                    self.assertIn("different persona", following["errors"][0]["message"])
                checked = state.check_stage(self.ws)
                self.assertEqual(checked["status"], "failed")
                self.assertEqual(checked["next"]["stage"], "art")
                self.assertTrue(checked["next"]["errors"])
                self.assertEqual(manifest.read_bytes(), corrupted)
                self.assertFalse((self.ws / "card" / "front.png").exists())
        save(manifest, original)
        following = state.next_action(self.ws)
        self.assertTrue(following["existing_art"]["validated"])
        self.assertEqual(following["existing_art"]["canvas"], [1086, 1448])
        self.assertEqual(self.finish()["stage"], "done")

    def test_no_assets_keep_nominal_canvas_as_brief_only(self):
        self.start()
        following = self.local_review()
        self.assertFalse(following["existing_art"]["validated"])
        self.assertIsNone(following["existing_art"]["source"])
        self.assertEqual((following["card_spec"]["canvas"]["width"], following["card_spec"]["canvas"]["height"]),
                         (1080, 1440))
        self.assertFalse((self.ws / "card" / "prototype.png").exists())

    def test_optional_art_input_uses_separate_brief_without_changing_html_content(self):
        data = copy.deepcopy(DATA)
        data["card"].pop("art_prompt")
        following = self.start(data=data)
        self.assertNotIn("角色设定（生图用）", following["preview"])
        text = (self.ws / "twinlight.json").read_bytes()
        binding = lite.persona_digest(data)
        following = self.local_review()
        self.assertTrue(following["brief_required"])
        self.assertEqual(following["write"], str(self.ws / "card" / "art-brief.txt"))
        self.assertTrue(following["errors"])
        brief = Path(following["write"])
        brief.write_text("太短", encoding="utf-8")
        self.assertTrue(state.next_action(self.ws)["brief_required"])
        brief.write_text(BRIEF, encoding="utf-8")
        following = state.next_action(self.ws)
        self.assertEqual(following["card_spec"]["persona_digest"], binding)
        self.assertIn(BRIEF, following["prototype_prompt"])
        self.native(size=(1086, 1448))
        following = state.next_action(self.ws)
        self.assertEqual(following["card_spec"]["canvas"]["width"], 1086)
        self.assertIn(BRIEF, following["subject_prompt"])
        following = self.finish()
        self.assertTrue(Path(following["card_preview"]).is_file())
        self.assertTrue(Path(following["html"]).is_file())
        self.assertFalse(following["text_confirmed"])
        self.assertEqual((self.ws / "twinlight.json").read_bytes(), text)
        self.assertNotIn("art_prompt", load(self.ws / "twinlight.json")["card"])
        self.assertEqual(load(self.ws / "site" / "profile.json")["persona"]["persona_digest"], binding)

    def test_independent_brief_revision_preserves_text_binding_and_confirmation(self):
        data = copy.deepcopy(DATA)
        data["card"].pop("art_prompt")
        self.start(data=data)
        self.local_review()
        brief = self.ws / "card" / "art-brief.txt"
        brief.write_text(BRIEF, encoding="utf-8")
        original_spec = state.next_action(self.ws)["card_spec"]
        self.native()
        self.finish()
        state.confirm(self.ws, "我确认这份虚构测试文字")
        self.finish()
        text = (self.ws / "twinlight.json").read_bytes()
        html = (self.ws / "site" / "index.html").read_bytes()
        review = copy.deepcopy(load(self.ws / "state.json")["stages"]["review"])
        updated = BRIEF + "本次只把美术调整为更克制的珍珠光泽，保持已核对的文字。"
        brief.write_text(updated, encoding="utf-8")
        following = state.next_action(self.ws)
        self.assertEqual(following["stage"], "art")
        self.assertTrue(following["text_confirmed"])
        self.assertEqual(following["card_spec"]["persona_digest"], original_spec["persona_digest"])
        self.assertNotEqual(following["card_spec"]["card_spec_digest"], original_spec["card_spec_digest"])
        self.assertIn(updated, following["prototype_prompt"])
        self.assertEqual(load(self.ws / "state.json")["stages"]["review"], review)
        self.finish()
        self.assertEqual((self.ws / "twinlight.json").read_bytes(), text)
        self.assertEqual((self.ws / "site" / "index.html").read_bytes(), html)

    def test_optional_art_input_can_consume_completed_layers_without_new_brief(self):
        data = copy.deepcopy(DATA)
        data["card"].pop("art_prompt")
        self.start(data=data)
        self.local_review()
        self.native()
        following = self.finish()
        self.assertEqual(following["art_mode"], "layered")
        self.assertTrue(Path(following["card_preview"]).is_file())
        self.assertTrue(Path(following["html"]).is_file())
        self.assertFalse((self.ws / "card" / "art-brief.txt").exists())
        self.assertNotIn("art_prompt", load(self.ws / "twinlight.json")["card"])


if __name__ == "__main__":
    unittest.main()
