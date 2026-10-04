"""Behavioral checks for independent modules, real gates and resumable execution."""
from __future__ import annotations
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from twinlight_core import lite, run as controlled, site
from twinlight_core.common import ContractError, load, save
from twinlight_core.template_origin import verify_site
from test_card_art import native_fixture


class ControlledRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.ws = self.folder / "run"
        self.input = self.folder / "person.json"
        self.data = load(ROOT / "tests/fixtures/lite/valid.json")
        save(self.input, self.data)
        self.original = self.input.read_bytes()

    def execute(self, **kwargs):
        return controlled.run(self.input, self.ws, no_browser=True, **kwargs)

    def art(self):
        return native_fixture(self.folder / "art", lite.persona_digest(self.data))

    def test_missing_native_card_keeps_actual_verified_html_and_requests_real_generation(self):
        result = self.execute()
        self.assertEqual(result["status"], "needs_card")
        self.assertEqual(result["next_action"]["type"], "generate_native_layers")
        self.assertTrue(Path(result["outputs"]["html"]).is_file())
        self.assertTrue(verify_site(Path(result["outputs"]["html"]))["ok"])
        self.assertNotIn("card_front", result["outputs"])
        self.assertFalse(result["dynamic_verified"])
        self.assertFalse(result["quality_verified"])
        self.assertFalse(result["text_confirmed"])
        self.assertEqual(result["stages"]["card"]["attempts"], 0)
        self.assertEqual(self.input.read_bytes(), self.original)
        self.assertEqual((self.ws / "content.json").read_bytes(), self.original)
        self.assertEqual(load(self.ws / "site/profile.json")["release"], {"draft": True, "share_allowed": False})

    def test_html_only_does_not_request_or_execute_card_module(self):
        self.data["card"].pop("art_prompt")
        save(self.input, self.data)
        with mock.patch("twinlight_core.cardgen.card_spec", side_effect=AssertionError("No card generation")):
            result = self.execute(mode="html")
        self.assertEqual(result["status"], "dynamic_unverified")
        self.assertNotIn("card", result["stages"])
        self.assertFalse((self.ws / "card").exists())

    def test_card_only_accepts_independent_card_content_without_galaxy(self):
        card = {key: self.data[key] for key in ("name", "summarizer", "card")}
        card["twinlight"] = "card-1"
        save(self.input, card)
        layers = self.art()
        with mock.patch.object(site, "build_lite", side_effect=AssertionError("No HTML module")):
            result = self.execute(mode="card", layers=layers)
        self.assertEqual(result["status"], "dynamic_unverified")
        self.assertTrue(Path(result["outputs"]["card_front"]).is_file())
        self.assertTrue(Path(result["outputs"]["card_preview"]).is_file())
        self.assertTrue(Path(result["outputs"]["card_pack"]).is_file())
        self.assertFalse((self.ws / "site").exists())
        self.assertNotIn("integration", result["stages"])

    def test_native_layers_resume_auto_integrates_without_rebuilding_basic_html(self):
        first = self.execute()
        base = Path(first["outputs"]["html"])
        base_before = (base.read_bytes(), base.stat().st_mtime_ns)
        manifest = self.art()
        source_bytes = {p.name: p.read_bytes() for p in manifest.parent.iterdir() if p.is_file()}
        result = self.execute(layers=manifest)
        self.assertEqual(result["status"], "dynamic_unverified")
        self.assertTrue(result["stages"]["html"]["reused"])
        self.assertEqual((base.read_bytes(), base.stat().st_mtime_ns), base_before)
        self.assertTrue(verify_site(Path(result["outputs"]["html_with_card"]))["ok"])
        self.assertEqual(load(self.ws / "site-with-card/profile.json")["persona"]["art_mode"], "layered")
        self.assertFalse(result["quality_verified"])
        self.assertEqual({p.name: p.read_bytes() for p in manifest.parent.iterdir() if p.is_file()}, source_bytes)
        again = self.execute()
        self.assertTrue(again["stages"]["card"]["reused"])
        self.assertTrue(again["stages"]["integration"]["reused"])
        self.assertEqual(self.input.read_bytes(), self.original)

    def test_native_source_change_during_card_browser_invalidates_card_and_integration(self):
        manifest = self.art()
        initial_source = (manifest.parent / "subject.png").read_bytes()

        def checked(state, workspace, key, html, **kwargs):
            if key == "card_browser":
                path = manifest.parent / "subject.png"
                with Image.open(path) as original:
                    image = original.copy()
                image.putpixel((image.width // 2, image.height // 2), (255, 0, 0, 255))
                image.save(path)
            return {"status": "passed", "checks": [{"passed": True}], "input_html_sha256": controlled._sha(html)}

        with mock.patch.object(controlled, "_browser", side_effect=checked):
            result = self.execute(layers=manifest)
        self.assertEqual(result["status"], "partial_success")
        self.assertFalse(result["ok"])
        self.assertFalse(result["dynamic_verified"])
        self.assertEqual(result["next_action"]["type"], "repair")
        self.assertEqual(result["stages"]["card"]["status"], "failed")
        self.assertEqual(result["stages"]["integration"]["status"], "failed")
        self.assertTrue(Path(result["outputs"]["html"]).is_file())
        self.assertNotIn("card_pack", result["outputs"])
        self.assertNotIn("html_with_card", result["outputs"])
        modified_source = (manifest.parent / "subject.png").read_bytes()
        self.assertNotEqual(initial_source, modified_source)
        repaired = self.execute()
        self.assertEqual(repaired["status"], "dynamic_unverified")
        self.assertEqual(repaired["stages"]["card"]["status"], "files_ready")
        self.assertEqual(repaired["stages"]["integration"]["status"], "files_ready")
        self.assertEqual(load(self.ws / "card/card-pack.json")["layers"]["subject"],
                         load(self.ws / "site-with-card/render-inputs.json")["layer_uris"]["subject"])
        self.assertEqual((manifest.parent / "subject.png").read_bytes(), modified_source)

    def test_native_source_change_during_integration_browser_invalidates_both_final_gates(self):
        manifest = self.art()

        def checked(state, workspace, key, html, **kwargs):
            if key == "integration_browser":
                path = manifest.parent / "effects.png"
                with Image.open(path) as original:
                    image = original.copy()
                image.putpixel((image.width // 2, image.height // 2), (255, 0, 0, 255))
                image.save(path)
            return {"status": "passed", "checks": [{"passed": True}], "input_html_sha256": controlled._sha(html)}

        with mock.patch.object(controlled, "_browser", side_effect=checked):
            result = self.execute(layers=manifest)
        self.assertEqual(result["status"], "partial_success")
        self.assertEqual(result["stages"]["card"]["status"], "failed")
        self.assertEqual(result["stages"]["integration"]["status"], "failed")
        self.assertFalse(result["dynamic_verified"])
        self.assertEqual(set(result["outputs"]), {"html"})

    def test_invalid_card_does_not_discard_html_and_actual_retries_are_bounded(self):
        manifest = self.art()
        wrong = load(manifest)
        wrong["persona_digest"] = "0" * 64
        save(manifest, wrong)
        for attempt in (1, 2, 3):
            result = self.execute(layers=manifest)
            self.assertEqual(result["status"], "partial_success")
            self.assertEqual(result["stages"]["card"]["attempts"], attempt)
            self.assertTrue(Path(result["outputs"]["html"]).is_file())
            self.assertNotIn("card_front", result["outputs"])
        result = self.execute()
        self.assertEqual(result["stages"]["card"]["status"], "blocked")
        self.assertEqual(result["stages"]["card"]["attempts"], 3)
        wrong["persona_digest"] = lite.persona_digest(self.data)
        save(manifest, wrong)
        repaired = self.execute()
        self.assertEqual(repaired["stages"]["card"]["status"], "files_ready")
        self.assertEqual(repaired["stages"]["card"]["attempts"], 0)

    def test_malformed_manifest_does_not_abort_independent_html(self):
        manifest = self.folder / "broken-layers.json"
        save(manifest, {"assets": []})
        result = self.execute(layers=manifest)
        self.assertEqual(result["status"], "partial_success")
        self.assertEqual(result["stages"]["card"]["status"], "failed")
        self.assertTrue(Path(result["outputs"]["html"]).is_file())

    def test_html_failure_keeps_independent_card(self):
        manifest = self.art()
        with mock.patch.object(site, "build_lite", side_effect=ContractError("Test HTML renderer failure")):
            result = self.execute(layers=manifest)
        self.assertEqual(result["status"], "partial_success")
        self.assertTrue(Path(result["outputs"]["card_front"]).is_file())
        self.assertNotIn("html", result["outputs"])
        self.assertNotIn("html_with_card", result["outputs"])
        self.assertEqual(result["stages"]["card"]["status"], "files_ready")

    def test_html_failure_keeps_pending_card_action(self):
        with mock.patch.object(site, "build_lite", side_effect=ContractError("Test HTML renderer failure")):
            result = self.execute()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["next_action"]["pending_actions"][0]["type"], "generate_native_layers")
        self.assertTrue(result["next_action"]["continue_independent_modules"])

    def test_font_preflight_does_not_require_font_for_completed_native_layers(self):
        with mock.patch.object(controlled, "_font_preflight", return_value={"status": "unavailable", "reason": "Test missing font"}):
            pending = self.execute()
        self.assertEqual(pending["status"], "needs_card")
        self.assertEqual(pending["next_action"]["image_capability"], "unknown_required")
        self.assertEqual(pending["next_action"]["typography_font"]["status"], "unavailable")
        with mock.patch.object(controlled, "_font_preflight", side_effect=AssertionError("Completed text needs no local font")):
            complete = self.execute(layers=self.art(), font=self.folder / "missing-font.ttf")
        self.assertEqual(complete["stages"]["card"]["status"], "files_ready")

    def test_output_tamper_or_deleted_receipt_cannot_reuse_success(self):
        first = self.execute(mode="html")
        original_html = Path(first["outputs"]["html"]).read_bytes()
        Path(first["outputs"]["html"]).write_text("<html>replaced output</html>")
        second = self.execute(mode="html")
        self.assertFalse(second["stages"]["html"]["reused"])
        self.assertEqual(Path(second["outputs"]["html"]).read_bytes(), original_html)
        (self.ws / "site/template-receipt.json").unlink()
        third = self.execute(mode="html")
        self.assertFalse(third["stages"]["html"]["reused"])
        self.assertTrue(verify_site(Path(third["outputs"]["html"]))["ok"])

    def test_person_or_private_content_changes_require_new_workspace(self):
        self.execute(mode="html")
        changed = copy.deepcopy(self.data)
        changed["name"] = "另一人"
        save(self.input, changed)
        with self.assertRaisesRegex(ContractError, "another input revision"):
            self.execute(mode="html")
        self.input.write_bytes(self.original)
        (self.ws / "content.json").write_text("{}")
        with self.assertRaisesRegex(ContractError, "Read-only content"):
            self.execute(mode="html")

    def test_mode_changes_require_a_new_workspace(self):
        self.execute()
        with self.assertRaisesRegex(ContractError, "another requested mode"):
            self.execute(mode="html")

    def test_missing_art_brief_returns_action_after_successful_html(self):
        self.data["card"].pop("art_prompt")
        save(self.input, self.data)
        result = self.execute()
        self.assertEqual(result["status"], "needs_card")
        self.assertEqual(result["next_action"]["type"], "prepare_art_direction")
        self.assertTrue(Path(result["outputs"]["html"]).is_file())
        self.assertEqual(result["stages"]["card"]["attempts"], 0)

    def test_invalid_independent_brief_does_not_discard_html(self):
        brief = self.folder / "art-direction.txt"
        brief.write_text("短", encoding="utf-8")
        result = self.execute(art_prompt_file=brief)
        self.assertEqual(result["status"], "partial_success")
        self.assertEqual(result["stages"]["card_brief"]["status"], "failed")
        self.assertTrue(Path(result["outputs"]["html"]).is_file())
        self.assertEqual(self.input.read_bytes(), self.original)
        brief.write_text("本次独立美术设定：原创纸本版画中的折纸罗盘，低饱和蓝绿与细金线，主体清楚，保留上下文字空间。", encoding="utf-8")
        repaired = self.execute(art_prompt_file=brief)
        self.assertEqual(repaired["status"], "needs_card")
        self.assertEqual(repaired["next_action"]["type"], "generate_native_layers")

    def test_missing_tools_and_waiting_art_do_not_consume_retry_budget(self):
        for _ in range(4):
            with mock.patch.object(controlled.importlib.util, "find_spec", return_value=None):
                result = controlled.run(self.input, self.ws)
            self.assertEqual(result["status"], "needs_card")
            self.assertEqual(result["stages"]["html_browser"]["status"], "unavailable")
            self.assertEqual(result["stages"]["html_browser"]["attempts"], 0)
            self.assertEqual(result["stages"]["card"]["attempts"], 0)

    def test_current_template_gate_failure_invalidates_cached_success(self):
        self.execute(mode="html")
        with mock.patch("twinlight_core.template_origin.verify_site", return_value={
                "ok": False, "errors": [{"code": "approved_template_changed"}]}):
            result = self.execute(mode="html")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["stages"]["html"]["status"], "failed")
        self.assertNotIn("html", result["outputs"])

    def test_supplied_fake_browser_report_is_discarded_before_real_invocation(self):
        self.execute(mode="html")
        report_path = self.ws / "browser/html_browser/report.json"
        save(report_path, {"ok": True, "checks": [{"passed": True}]})

        def actual_failure(command, **kwargs):
            self.assertFalse(report_path.exists())
            save(report_path, {"ok": False, "checks": [{"name": "Actual failed check", "passed": False}],
                               "failure": "Actual failed check", "html_sha256": controlled._sha(self.ws / "site/index.html")})
            return type("Process", (), {"returncode": 1, "stderr": "", "stdout": ""})()

        with mock.patch.object(controlled.importlib.util, "find_spec", return_value=object()), \
                mock.patch.object(controlled, "_execute_browser", side_effect=actual_failure):
            result = controlled.run(self.input, self.ws, mode="html", browser=sys.executable)
        self.assertEqual(result["status"], "partial_success")
        self.assertEqual(result["stages"]["html_browser"]["status"], "failed")
        self.assertFalse(result["dynamic_verified"])

    def test_html_changed_during_browser_check_cannot_pass(self):
        self.execute(mode="html")
        report_path = self.ws / "browser/html_browser/report.json"

        def changed_input(command, **kwargs):
            save(report_path, {"ok": True, "html_sha256": controlled._sha(self.ws / "site/index.html"),
                               "checks": [{"name": "Read older HTML", "passed": True}]})
            (self.ws / "site/index.html").write_text("Changed while browser was running")
            return type("Process", (), {"returncode": 0, "stderr": "", "stdout": ""})()

        with mock.patch.object(controlled.importlib.util, "find_spec", return_value=object()), \
                mock.patch.object(controlled, "_execute_browser", side_effect=changed_input):
            result = controlled.run(self.input, self.ws, mode="html", browser=sys.executable)
        self.assertEqual(result["stages"]["html_browser"]["status"], "failed")
        self.assertFalse(result["stages"]["html_browser"]["input_unchanged"])
        self.assertFalse(result["dynamic_verified"])
        self.assertEqual(result["stages"]["html"]["status"], "failed")
        self.assertNotIn("html", result["outputs"])

    def test_browser_report_missing_or_wrong_input_hash_cannot_pass(self):
        for reported_hash in (None, "0" * 64):
            with self.subTest(reported_hash=reported_hash):
                self.ws = self.folder / ("missing-hash" if reported_hash is None else "wrong-hash")
                self.execute(mode="html")
                report_path = self.ws / "browser/html_browser/report.json"

                def wrong_receipt(command, **kwargs):
                    report = {"ok": True, "checks": [{"name": "Mocked browser check", "passed": True}]}
                    if reported_hash is not None:
                        report["html_sha256"] = reported_hash
                    save(report_path, report)
                    return type("Process", (), {"returncode": 0, "stderr": "", "stdout": ""})()

                with mock.patch.object(controlled.importlib.util, "find_spec", return_value=object()), \
                        mock.patch.object(controlled, "_execute_browser", side_effect=wrong_receipt):
                    result = controlled.run(self.input, self.ws, mode="html", browser=sys.executable)
                self.assertEqual(result["stages"]["html_browser"]["status"], "failed")
                self.assertFalse(result["stages"]["html_browser"]["report_input_bound"])
                self.assertFalse(result["dynamic_verified"])
                self.assertIn("hash", result["stages"]["html_browser"]["reason"])

    def test_correctly_bound_browser_receipt_can_pass_and_reuse(self):
        self.execute(mode="html")
        report_path = self.ws / "browser/html_browser/report.json"

        def matching_receipt(command, **kwargs):
            save(report_path, {"ok": True, "html_sha256": controlled._sha(self.ws / "site/index.html"),
                               "checks": [{"name": "Mocked browser check", "passed": True}], "webgl": True})
            return type("Process", (), {"returncode": 0, "stderr": "", "stdout": ""})()

        with mock.patch.object(controlled.importlib.util, "find_spec", return_value=object()), \
                mock.patch.object(controlled, "_execute_browser", side_effect=matching_receipt) as executed:
            first = controlled.run(self.input, self.ws, mode="html", browser=sys.executable)
            second = controlled.run(self.input, self.ws, mode="html", browser=sys.executable)
        self.assertEqual(first["status"], "files_ready")
        self.assertTrue(first["stages"]["html_browser"]["report_input_bound"])
        self.assertTrue(second["stages"]["html_browser"]["reused"])
        self.assertEqual(executed.call_count, 1)

    @unittest.skipUnless(controlled.os.name == "posix", "POSIX process group cleanup")
    def test_browser_timeout_kills_only_spawned_process_group(self):
        child = mock.Mock(pid=123456)
        child.communicate.side_effect = [controlled.subprocess.TimeoutExpired("browser", 1), ("", "")]
        with mock.patch.object(controlled.subprocess, "Popen", return_value=child) as launched, \
                mock.patch.object(controlled.os, "killpg") as kill_group:
            with self.assertRaises(controlled.subprocess.TimeoutExpired):
                controlled._execute_browser(["python", "local-browser-check"], timeout=1)
        self.assertTrue(launched.call_args.kwargs["start_new_session"])
        kill_group.assert_called_once_with(child.pid, controlled.signal.SIGKILL)


if __name__ == "__main__":
    unittest.main()
