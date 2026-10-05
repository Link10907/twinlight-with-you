"""Public delivery gate around the existing fixed-template mechanical controller."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from .art_quality import check_evidence, read_json, sha256, checked_ref
from .embedded_card import audit_embedding


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
        if decision.get("ok"):
            evidence = read_json(layers.parent / "art-evidence.json")
            design = read_json(checked_ref(layers.parent, evidence["design"]))
            if design.get("version") != "art-direction-2":
                decision = {**decision, "ok": False, "status": "needs_art_direction", "errors": [
                    {"code": "versioned_visual_subject_required",
                     "message": "Public native-card delivery requires art-direction-2: one versioned style and an explicit visual subject. Legacy free-form briefs remain diagnostics only."}]}
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
        action["schema"] = str(Path(__file__).resolve().parents[2] / "schemas/art-direction-v2.schema.json")
        action["style_catalog"] = str(Path(__file__).resolve().parents[2] / "assets/art-styles/catalog.json")
        action["steps"] = ["Select one versioned art style; describe one concrete human/animal/object, its appearance and one action. Never use identity keywords as drawing input.",
                           "Check actual image-generation, reference-image and native-alpha capabilities.",
                           "Generate and inspect a wordless prototype; do not generate layers before prototype review passes.",
                           "Create native independent layers, inspect the unlettered composite, then inspect final typography and foil.",
                           "Keep actual invocation outputs and hash-bound reviews in art-evidence.json; resume the same run."]
    missing_outputs = [name for name, path in result.get("outputs", {}).items() if not Path(path).is_file()]
    for name in missing_outputs:
        result["outputs"].pop(name)
    if missing_outputs:
        result["status"] = "partial_success" if result["outputs"] else "failed"
        result["ok"] = False
        result["missing_outputs"] = missing_outputs
    mode = result.get("mode", kwargs.get("mode", "both"))
    card_ok = mode == "html" or bool(decision and decision["ok"])
    embedding = {"ok": mode != "both", "status": "not_required" if mode != "both" else "not_run"}
    if mode == "both" and card_ok and result["outputs"].get("html_with_card"):
        embedding = audit_embedding(Path(result["outputs"]["html_with_card"]), manifest, persona)
        if not embedding["ok"]:
            result.setdefault("candidate_outputs", {})["html_with_card"] = result["outputs"].pop("html_with_card")
            result["status"] = "partial_success" if result["outputs"] else "failed"
            result["ok"] = False
            old = result.get("next_action") or {}
            resume = [sys.executable, str(Path(__file__).resolve().parents[1] / "twinlight.py"), "run",
                      str(Path(input_path).resolve()), "--workspace", str(workspace), "--mode", mode,
                      "--layers", str(manifest)]
            for name in ("browser", "font", "art_prompt_file"):
                if kwargs.get(name) is not None:
                    resume += ["--" + name.replace("_", "-"), str(kwargs[name])]
            if kwargs.get("no_browser"): resume.append("--no-browser")
            result["next_action"] = {"type": "repair_embedding", "errors": embedding["errors"],
                                     "resume": old.get("resume", resume), "user_confirmation_required": False,
                                     "constraints": ["Rebuild from the verified native manifest. Never patch a data URI into the old HTML or select the base HTML as the finished both-mode result."]}
    result["stages"]["embedded_card"] = embedding
    result["embedded_card_verified"] = mode == "both" and embedding.get("ok") is True
    required = {"html": ("html",), "card": ("card_front", "card_preview", "card_pack"),
                "both": ("html_with_card", "card_front", "card_preview", "card_pack")}[mode]
    outputs_ready = all(k in result["outputs"] and Path(result["outputs"][k]).is_file() for k in required)
    if result.get("status") == "files_ready" and not outputs_ready:
        result["status"] = "partial_success" if result["outputs"] else "failed"
        result["ok"] = False
    if not card_ok or not embedding.get("ok"):
        result["candidate_dynamic_verified"] = result.get("dynamic_verified", False)
        result["dynamic_verified"] = False
    result["complete"] = (result.get("status") == "files_ready" and card_ok and outputs_ready
                          and embedding.get("ok") is True and result.get("dynamic_verified") is True)
    # Never hand the unillustrated base site to the host as the finished both-mode result.
    primary_key = {"both": "html_with_card", "html": "html", "card": "card_preview"}[mode]
    result["primary_output"] = result["outputs"].get(primary_key)
    result["delivery_files"] = {k: result["outputs"][k] for k in required if k in result["outputs"]}
    result["host_preview"] = {"status": "not_tested", "html_sha256": None,
                              "note": "A file attachment and a local browser check do not establish in-chat HTML execution."}
    result["in_chat_preview_verified"] = False
    # An optional real host-preview observation must bind this exact HTML; never infer it from account/model names.
    host_path = workspace / "host-preview.json"
    if host_path.is_file() and result["primary_output"]:
        try:
            observed = read_json(host_path)
            target_sha = sha256(Path(result["primary_output"]))
            if (observed.get("version") == "host-preview-1" and observed.get("html_sha256") == target_sha
                    and observed.get("status") in ("available", "unsupported", "blocked")
                    and isinstance(observed.get("observation"), str) and len(observed["observation"]) >= 12):
                result["host_preview"] = observed
                result["in_chat_preview_verified"] = observed["status"] == "available"
        except (ValueError, OSError, TypeError):
            pass
    result["art_reviewed_by_host"] = bool(decision and decision.get("host_visual_review_recorded") and decision.get("ok"))
    result["generation_evidence_checked"] = bool(decision and decision.get("evidence_checked"))
    result["quality_verified"] = False
    result["generation_provenance_verified"] = False
    result["completion_scope"] = "complete means requested files, versioned visual-subject evidence, actual embedded native bytes and local browser effects passed. In-chat preview is a separate observed capability; no independent aesthetic or provider authentication is claimed."
    result["text_confirmed"] = False
    # Save the public result last; do not edit the maintained template lock or weaken asset validation.
    state_path = workspace / "run-state.json"
    if state_path.is_file():
        state = read_json(state_path)
        if decision is not None:
            state["stages"]["art_quality"] = decision
        state["stages"]["embedded_card"] = embedding
        _save(state_path, state)
    _save(workspace / "run-report.json", result)
    _save(workspace / "delivery-report.json", {
        "complete": result["complete"], "status": result["status"], "mode": mode,
        "input_sha256": sha256(Path(input_path)),
        "outputs_sha256": {name: sha256(Path(path)) for name, path in result["outputs"].items()},
        "art_reviewed_by_host": result["art_reviewed_by_host"],
        "generation_evidence_checked": result["generation_evidence_checked"],
        "dynamic_verified": result.get("dynamic_verified", False),
        "embedded_card_verified": result["embedded_card_verified"],
        "primary_output": result["primary_output"],
        "delivery_files": result["delivery_files"],
        "host_preview": result["host_preview"],
        "in_chat_preview_verified": result["in_chat_preview_verified"],
        "quality_verified": False, "generation_provenance_verified": False,
        "draft": True, "share_allowed": False,
    })
    return result
