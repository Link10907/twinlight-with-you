"""Public delivery gate around the existing fixed-template mechanical controller."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from .art_quality import check_evidence, read_json, sha256


def _save(path: Path, value: dict):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def deliver(core, input_path: Path, workspace: Path, **kwargs) -> dict:
    """No CLI switch disables this gate. Low-level render/build commands remain diagnostics."""
    workspace = Path(workspace).resolve()
    decisions = []

    def review_gate(content, layers, folder, persona):
        decision = check_evidence(layers, persona, front=folder / "card/front.png", preview=folder / "card/preview.html")
        decisions.append((layers, persona, decision))
        return decision

    result = core(input_path, workspace, _review_gate=review_gate, **kwargs)
    decision = None
    if decisions:
        manifest, persona, initial = decisions[-1]
        # Always re-read evidence after the integration/browser stage. Cached state cannot approve new pixels.
        decision = review_gate(workspace / "content.json", manifest, workspace, persona)
        if initial.get("ok") and decision.get("ok") and initial.get("inputs_sha256") != decision.get("inputs_sha256"):
            decision = {**decision, "ok": False, "status": "art_rejected", "errors": [
                {"code": "evidence_changed_during_run", "message": "Evidence changed after the integration gate; resume with stable files."}]}
        result["stages"]["art_quality"] = decision
        if not decision["ok"]:
            candidates = {}
            for name in ("card_front", "card_preview", "card_pack"):
                if name in result["outputs"]:
                    candidates[name] = result["outputs"].pop(name)
            result["outputs"].pop("html_with_card", None)
            result["candidate_outputs"] = candidates
            action = {"type": "repair_art" if decision["status"] == "art_rejected" else "complete_art_evidence",
                      "manifest": str(manifest), "evidence": str(manifest.parent / "art-evidence.json"),
                      "read": [str(Path(__file__).resolve().parents[2] / "references/quality-workflow.md")],
                      "errors": decision["errors"], "user_confirmation_required": False}
            old_action = result.get("next_action") or {}
            # Art resumption preserves the caller's browser policy. A browser-retry action
            # may intentionally remove --no-browser, so it is not the right resume source.
            action["resume"] = [sys.executable, str(Path(__file__).resolve().parents[1] / "twinlight.py"), "run",
                                str(Path(input_path).resolve()), "--workspace", str(workspace), "--mode", kwargs.get("mode", "both"),
                                "--layers", str(manifest)]
            for name in ("browser", "font", "art_prompt_file"):
                if kwargs.get(name) is not None:
                    action["resume"] += ["--" + name.replace("_", "-"), str(kwargs[name])]
            if kwargs.get("no_browser"):
                action["resume"].append("--no-browser")
            if result["status"] in ("failed", "partial_success"):
                old_action.setdefault("pending_actions", []).append(action)
                result["next_action"] = old_action
            else:
                result["status"] = decision["status"]
                result["next_action"] = action
            if decision["status"] == "art_rejected":
                result["ok"] = False
    action = result.get("next_action")
    if isinstance(action, dict) and action.get("type") in ("generate_native_layers", "prepare_art_direction"):
        # Never treat "generate all layers" as permission to skip prototype selection.
        action["type"] = "prepare_and_review_prototype"
        action["read"] = [str(Path(__file__).resolve().parents[2] / "references/quality-workflow.md")]
        action["steps"] = ["Capture current preferences and rejected directions in a structured visual brief.",
                           "Check actual image-generation, reference-image and native-alpha capabilities.",
                           "Generate and inspect a wordless prototype; do not generate layers before prototype review passes.",
                           "Create native independent layers, inspect the unlettered composite, then inspect final typography and foil.",
                           "Keep actual invocation outputs and hash-bound reviews in art-evidence.json; resume the same run."]
    mode = result.get("mode", kwargs.get("mode", "both"))
    card_ok = mode == "html" or bool(decision and decision["ok"])
    if not card_ok:
        result["candidate_dynamic_verified"] = result.get("dynamic_verified", False)
        result["dynamic_verified"] = False
    result["complete"] = result.get("status") == "files_ready" and card_ok and result.get("dynamic_verified") is True
    result["art_reviewed_by_host"] = bool(decision and decision.get("host_visual_review_recorded") and decision.get("ok"))
    result["generation_evidence_checked"] = bool(decision and decision.get("evidence_checked"))
    result["quality_verified"] = False
    result["generation_provenance_verified"] = False
    result["completion_scope"] = "complete requires fixed-template/asset checks, current hash-bound host art reviews, recorded image outputs and actual browser checks; this is not independent aesthetic certification."
    result["text_confirmed"] = False
    # Save the public result last; do not edit the maintained template lock or weaken asset validation.
    state_path = workspace / "run-state.json"
    if state_path.is_file():
        state = read_json(state_path)
        if decision is not None:
            state["stages"]["art_quality"] = decision
        _save(state_path, state)
    _save(workspace / "run-report.json", result)
    _save(workspace / "delivery-report.json", {
        "complete": result["complete"], "status": result["status"], "mode": mode,
        "input_sha256": sha256(Path(input_path)),
        "outputs_sha256": {name: sha256(Path(path)) for name, path in result["outputs"].items()},
        "art_reviewed_by_host": result["art_reviewed_by_host"],
        "generation_evidence_checked": result["generation_evidence_checked"],
        "dynamic_verified": result.get("dynamic_verified", False),
        "quality_verified": False, "generation_provenance_verified": False,
        "draft": True, "share_allowed": False,
    })
    return result
