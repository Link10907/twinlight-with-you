"""Run reports describe static/layered art honestly and preview only safe local images."""
import base64
import io
import re
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from test_card_art import FIXTURE, native_fixture
from twinlight_core import lite, state as fsm
from twinlight_core.common import load, save
from twinlight_core.report import write_report


class ArtReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ws = self.root / "run"
        fsm.start(self.ws)
        self.data = load(FIXTURE)
        save(self.ws / "twinlight.json", self.data)
        fsm.check_stage(self.ws)
        fsm.confirm(self.ws, "可以使用这些虚构测试资料")
        self.persona = lite.to_profile(self.data, generated_at="2026-10-03T00:00:00Z")["persona"]["persona_digest"]

    def report(self):
        return write_report(self.ws).read_text(encoding="utf-8")

    def native(self, status="generated"):
        manifest = native_fixture(self.ws / "card", self.persona)
        doc = load(manifest)
        doc["art_status"] = status
        save(manifest, doc)
        self.assertEqual(fsm.check_stage(self.ws)["status"], "passed")
        return manifest

    def visual(self, *, status="passed", report=None):
        (self.ws / "site").mkdir(exist_ok=True)
        (self.ws / "site/index.html").write_text("<html>current test page</html>", encoding="utf-8")
        (self.ws / "visual").mkdir(exist_ok=True)
        Image.new("RGB", (600, 400), "navy").save(self.ws / "visual/home.png")
        report = report if report is not None else {"ok": True, "checks": [{"name": "previous visual pass", "passed": True}],
                                                    "webgl": True, "errors": [], "external_requests": []}
        save(self.ws / "visual/report.json", report)
        state = load(self.ws / "state.json")
        state["stages"]["visual"].update({"status": status, "detail": {"verified": True,
                                          "html_sha256": fsm.sha(self.ws / "site/index.html")}})
        if status == "failed":
            state["stages"]["visual"]["errors"] = [{"code": "invalid_report", "message": "本次检查未通过"}]
        save(self.ws / "state.json", state)

    def test_static_prototype_and_legacy_portrait_have_preview_without_layered_claim(self):
        for role in ("prototype", "portrait"):
            with self.subTest(role=role):
                for existing in (self.ws / "card").glob("*.png"):
                    existing.unlink()
                Image.new("RGB", (600, 800), "orange").save(self.ws / "card" / (role + ".png"))
                fsm.choose_art(self.ws, "static")
                html = self.report()
                self.assertIn("静态原型（未分层）", html)
                self.assertIn("静态原型预览", html)
                self.assertIn("data:image/jpeg;base64,", html)
                self.assertNotIn("占位卡面", html)
                self.assertNotIn("已生成独立图层", html)

    def test_native_generated_and_approved_preview_only_the_transparent_subject(self):
        for status, label in (("generated", "已生成独立图层"), ("approved", "已审阅独立图层")):
            with self.subTest(status=status):
                manifest = self.native(status)
                html = self.report()
                self.assertIn(label, html)
                self.assertIn("原生主体层 · 单层预览", html)
                self.assertNotIn("占位卡面", html)
                png = re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", html)
                self.assertIsNotNone(png)
                with Image.open(io.BytesIO(base64.b64decode(png.group(1)))) as preview:
                    self.assertEqual(preview.mode, "RGBA")
                    self.assertEqual(preview.getchannel("A").getextrema(), (0, 255))
                self.assertEqual(load(manifest)["art_status"], status)
                # Start the next accepted-art check without relying on stale state.
                state = load(self.ws / "state.json")
                state["stages"]["art"]["status"] = "pending"
                save(self.ws / "state.json", state)

    def test_placeholder_ignores_existing_prototype(self):
        Image.new("RGB", (600, 800), "orange").save(self.ws / "card/prototype.png")
        fsm.choose_art(self.ws, "placeholder")
        html = self.report()
        self.assertIn("占位卡面", html)
        self.assertNotIn("data:image/", html)

    def test_missing_and_corrupt_preview_do_not_break_report(self):
        prototype = self.ws / "card/prototype.png"
        Image.new("RGB", (600, 800), "orange").save(prototype)
        fsm.choose_art(self.ws, "static")
        prototype.unlink()
        self.assertNotIn("data:image/", self.report())
        prototype.write_text("not a raster image", encoding="utf-8")
        self.assertNotIn("data:image/", self.report())

    def test_manifest_traversal_symlink_and_other_person_are_not_embedded(self):
        manifest = self.native()
        outside = self.root / "outside.png"
        Image.new("RGB", (600, 800), "red").save(outside)
        doc = load(manifest)
        doc["assets"]["subject"] = "../../outside.png"
        save(manifest, doc)
        self.assertNotIn("data:image/", self.report())
        doc["assets"]["subject"] = "subject.png"
        save(manifest, doc)
        subject = self.ws / "card/subject.png"
        subject.unlink()
        subject.symlink_to(outside)
        self.assertNotIn("data:image/", self.report())
        subject.unlink()
        Image.new("RGBA", (600, 800), (0, 0, 0, 0)).save(subject)
        doc["persona_digest"] = "f" * 64
        save(manifest, doc)
        self.assertNotIn("data:image/", self.report())

    def test_unchecked_stage_does_not_reuse_old_generated_status_or_preview(self):
        self.native()
        state = load(self.ws / "state.json")
        state["stages"]["art"]["status"] = "failed"
        save(self.ws / "state.json", state)
        html = self.report()
        self.assertIn("卡图状态：<span class='badge idle'>未检查", html)
        self.assertNotIn("已生成独立图层", html)
        self.assertNotIn("data:image/", html)

    def test_invalid_visual_json_or_shape_still_produces_a_failure_report(self):
        for broken in ('{"checks":', '[]', '{"checks":["bad"],"ok":true}',
                       '{"checks":[{"name":"bad bool","passed":"true"}]}'):
            with self.subTest(broken=broken):
                self.visual(status="failed")
                (self.ws / "visual/report.json").write_text(broken, encoding="utf-8")
                html = self.report()
                self.assertIn("检查报告无法读取或格式不正确", html)
                self.assertIn("本次检查未通过", html)
                self.assertNotIn("已验证", html)
                self.assertNotIn("data:image/", html)

    def test_pending_visual_stage_ignores_old_verified_detail_report_and_screenshot(self):
        self.visual(status="pending")
        html = self.report()
        self.assertIn("尚未运行", html)
        self.assertNotIn("已验证", html)
        self.assertNotIn("previous visual pass", html)
        self.assertNotIn("data:image/", html)

    def test_verified_visual_report_requires_the_current_html_and_valid_success(self):
        self.visual()
        html = self.report()
        self.assertIn("<span class='badge ok'>已验证</span>", html)
        self.assertIn("data:image/jpeg", html)
        (self.ws / "site/index.html").write_text("<html>changed page</html>", encoding="utf-8")
        html = self.report()
        self.assertIn("页面已变更或缺失", html)
        self.assertNotIn("已验证", html)
        self.assertNotIn("previous visual pass", html)
        self.assertNotIn("data:image/", html)

    def test_failed_visual_report_labels_screenshots_as_diagnostics(self):
        self.visual(status="failed", report={"ok": False, "checks": [{"name": "canvas", "passed": True},
                              {"name": "card", "passed": False}], "failure": "卡片检查失败"})
        html = self.report()
        self.assertIn("单项通过", html)
        self.assertIn("卡片检查失败", html)
        self.assertIn("未通过检查，仅供诊断", html)
        self.assertIn("data:image/jpeg", html)
        self.assertNotIn("已验证", html)


if __name__ == "__main__":
    unittest.main()
