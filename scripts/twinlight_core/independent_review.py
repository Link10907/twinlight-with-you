"""Fail-closed review contracts; local records are NOT authenticated agent identities.

The host must create the actual isolated reviewer invocation. This module never
calls a model, invents observations, or approves images. Host-level read/write
separation is needed to prevent a producer from forging review records.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

RELEASE_KEYS = {
    "html": ("html",),
    "card": ("card_front", "card_preview", "card_pack"),
    "both": ("html_with_card", "card_front", "card_preview", "card_pack"),
}
CARD_CHECKS = ("reference_style_match", "complete_subject", "clean_layer_ownership",
               "genuine_layer_parallax", "view_dependent_foil", "fixed_typography",
               "mobile_readable", "same_card_as_approved")
SITE_CHECKS = ("galaxy_navigation", "galaxy_merge", "question_transition",
               "card_reveal", "return_navigation")


def canonical_sha(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _require(condition: bool, code: str, message: str, status="needs_independent_review"):
    from .art_quality import ArtEvidenceError
    if not condition:
        raise ArtEvidenceError(code, message, status=status)


def check_handoff(root: Path, review: dict, inputs: dict) -> None:
    """Check trace binding and declared separation, not provider authentication."""
    from .art_quality import checked_ref, read_json, sha256
    h = review.get("handoff")
    _require(isinstance(h, dict), "reviewer_missing", "A real isolated reviewer invocation is required; producer self-review cannot approve.")
    _require(h.get("mode") == "independent_agent", "reviewer_not_independent", "A renamed role in the producer conversation is not an independent reviewer.")
    for key in ("producer_session_id", "reviewer_session_id", "invocation_id"):
        _require(isinstance(h.get(key), str) and len(h[key].strip()) >= 2,
                 "reviewer_identity_missing", "Keep the actual host-issued " + key)
    _require(h["producer_session_id"].strip() != h["reviewer_session_id"].strip(), "self_review", "Producer and reviewer session must differ.")
    _require(h.get("context") == "isolated" and h.get("read_only_artifacts") is True,
             "reviewer_context", "Reviewer needs an isolated context and read-only source artifacts.")
    trace_path = checked_ref(root, h.get("trace"))
    trace = read_json(trace_path)
    inputs[str(trace_path)] = sha256(trace_path)
    expected = {key: h[key] for key in ("producer_session_id", "reviewer_session_id", "invocation_id")}
    expected.update(scope_sha256=canonical_sha(review["targets"]), context="isolated", read_only_artifacts=True)
    _require(all(trace.get(k) == v for k, v in expected.items()), "reviewer_trace_mismatch",
             "The host trace must bind this exact review scope and isolated invocation.")
    response_path = checked_ref(root, trace.get("raw_response"))
    response = read_json(response_path)
    inputs[str(response_path)] = sha256(response_path)
    # No recursive hash: the raw reviewer response contains verdict/checks, not its own trace reference.
    original = {k: v for k, v in review.items() if k != "handoff"}
    _require(response == original, "reviewer_response_changed",
             "Do not rewrite the reviewer's verdict or checks when importing the response.")
    _require(isinstance(review.get("blockers"), list), "reviewer_blockers_missing", "Record concrete blockers, or an empty list after a real pass.")
    blockers=review["blockers"]
    _require(len(blockers) <= 3, "reviewer_blocker_count", "Report at most three prioritized root defects.")
    if review.get("decision") in ("revise","blocked"):
        _require(bool(blockers), "reviewer_reason_missing", "Rejection or capability blocking needs a concrete reason.")
        for item in blockers:
            _require(isinstance(item,dict) and all(isinstance(item.get(k),str) and len(item[k].strip())>=2
                     for k in ("object","location","evidence","repair")),
                     "reviewer_blocker_detail", "Each blocker needs object, location, evidence and repair.")
    if review.get("decision") == "accept":
        _require(not review["blockers"], "reviewer_blockers", "A blocking defect cannot be averaged away by other successful checks.", "art_rejected")


def release_targets(workspace: Path, outputs: dict, mode: str) -> dict:
    from .art_quality import sha256
    _require(mode in RELEASE_KEYS, "review_mode", "Unknown review mode.")
    root = Path(workspace).resolve()
    result = {}
    for key in RELEASE_KEYS[mode]:
        value = outputs.get(key)
        _require(isinstance(value, str), "review_output_missing", "Missing release candidate: " + key)
        path = Path(value).resolve()
        _require(path.is_relative_to(root) and path.is_file(), "review_output_path", "Review only existing files inside this run workspace.")
        result[key] = {"file": path.relative_to(root).as_posix(), "sha256": sha256(path)}
    return {"mode": mode, "outputs": result}


def _frame(root: Path, value: dict, inputs: dict):
    from .art_quality import checked_ref, image, sha256
    _require(isinstance(value, dict), "missing_effect_frame", "Keep an actual frozen card-region capture and its render state.")
    path = checked_ref(root, value.get("image"))
    inputs[str(path)] = sha256(path)
    state = value.get("state")
    _require(isinstance(state, dict) and state.get("paused") is True and state.get("region") == "card",
             "effect_frame_state", "Pause animation; capture only the card region with actual render state.")
    for key in ("x", "y", "depth", "foil", "time", "finish"):
        _require(type(state.get(key)) in (int, float) and math.isfinite(state[key]), "effect_frame_state", "Missing numeric render state: " + key)
    _require(isinstance(state.get("viewport"), list) and len(state["viewport"]) == 2 and all(type(v) is int and 1 <= v <= 16384 for v in state["viewport"]),
             "effect_frame_state", "Keep the tested viewport.")
    return image(path).convert("RGB"), state


def _pair(root: Path, frames: dict, name: str, inputs: dict):
    a, sa = _frame(root, frames.get(name + "_off"), inputs)
    b, sb = _frame(root, frames.get(name + "_on"), inputs)
    for key in ("x", "y", "time", "finish", "depth", "foil", "viewport"):
        if key != name:
            _require(sa[key] == sb[key], "effect_controls_changed", "A/B controls must stay fixed except " + name)
    _require(sa[name] == 0 and sb[name] > 0, "effect_not_toggled", "A/B comparison must toggle " + name + " from zero.")
    if name == "depth":
        _require(sa["foil"] == 0 and (abs(sa["x"]) + abs(sa["y"])) > .02,
                 "depth_control", "Check relative motion with foil disabled and a nonzero viewing angle.")
    _require(a.size == b.size, "effect_frame_size", "A/B screenshots need identical card-region dimensions.")
    diff = ImageChops.difference(a, b)
    mean = sum(ImageStat.Stat(diff).mean) / 3
    _require(mean > .25, "effect_not_visible", "The " + name + " control has no measurable card-region effect.", "release_rejected")
    return {"mean_channel_difference": mean, "note": "Pixel difference detects no-op controls; it does not certify correct depth or aesthetics."}


def check_release(workspace: Path, outputs: dict, mode: str) -> dict:
    from .art_quality import ArtEvidenceError, read_json, checked_ref, sha256, image
    root = Path(workspace).resolve()
    result = {"ok": False, "status": "needs_release_review", "errors": [],
              "independent_review_recorded": False, "reviewer_identity_authenticated": False,
              "scope": "Hash-bound host records plus effect no-op checks; not agent identity authentication or automatic aesthetic certification."}
    try:
        report_path = root / "release-review.json"
        _require(report_path.is_file(), "release_review_missing", "The integrated candidate needs an independent release review.", "needs_release_review")
        review = read_json(report_path)
        targets = release_targets(root, outputs, mode)
        _require(review.get("stage") == "release" and review.get("targets") == targets,
                 "stale_release_review", "Review the current final HTML and card bytes, not a previous build.", "needs_release_review")
        decision = review.get("decision")
        _require(decision in ("pending", "accept", "revise", "blocked"), "release_decision", "Unknown release review decision.")
        _require(decision == "accept", "release_not_accepted", "Release is not approved: " + str(decision),
                 "release_rejected" if decision == "revise" else "reviewer_blocked" if decision == "blocked" else "needs_release_review")
        inputs = {str(report_path): sha256(report_path)}
        check_handoff(root, review, inputs)
        criteria = release_checks(mode)
        checks = review.get("checks", {})
        for key in criteria:
            item = checks.get(key, {})
            _require(isinstance(item, dict) and item.get("passed") is True
                     and isinstance(item.get("observation"), str) and len(item["observation"].strip()) >= 12,
                     "release_check_failed", "An actual observation is required: " + key, "release_rejected")
        captures = review.get("captures", {})
        for name in ("desktop", "mobile"):
            path = checked_ref(root, captures.get(name)); image(path)
            inputs[str(path)] = sha256(path)
        runtime = review.get("runtime", {})
        primary = {"both":"html_with_card","card":"card_preview","html":"html"}[mode]
        _require(runtime.get("html_sha256") == targets["outputs"][primary]["sha256"],
                 "release_runtime_target", "Browser evidence must target the same final HTML.")
        if mode != "html":
            _require(runtime.get("backend") == "webgl" and runtime.get("webgl_ready") is True
                     and runtime.get("fallback") is False,
                     "foil_backend_unverified", "The retained V10 CSS fallback does not verify foil; test real WebGL or remain incomplete.", "reviewer_blocked")
        else:
            _require(runtime.get("page_ready") is True, "page_unverified", "Inspect the actual standalone galaxy page")
        if mode in ("html", "both"):
            seconds = runtime.get("merge_seconds")
            _require(type(seconds) in (int, float) and 0 < seconds <= 15,
                     "merge_duration", "Observe the continuous V10 merge and keep it within 15 seconds.", "release_rejected")
        frames = review.get("effect_frames", {})
        metrics = {name: _pair(root, frames, name, inputs) for name in ("foil", "depth")} if mode != "html" else {}
        _require(all(Path(p).is_file() and sha256(Path(p)) == h for p, h in inputs.items()),
                 "release_changed_during_review", "Review evidence changed during verification.")
        # Recheck actual candidate bytes after evaluating images and records.
        _require(release_targets(root, outputs, mode) == targets, "release_candidate_changed", "Candidate changed during release review.")
        result.update(ok=True, status="independent_release_recorded", independent_review_recorded=True,
                      review_sha256=sha256(report_path), inputs_sha256=inputs, metrics=metrics)
    except ArtEvidenceError as exc:
        result.update(status=exc.status, errors=[{"code": exc.code, "message": str(exc)}])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result.update(status="needs_release_review", errors=[{"code": "invalid_release_evidence", "message": str(exc)[:800]}])
    return result


def release_checks(mode: str) -> tuple:
    if mode == "html": return tuple(k for k in SITE_CHECKS if k != "card_reveal") + ("mobile_readable",)
    if mode not in ("both","card"): raise ValueError("Unknown release mode")
    return CARD_CHECKS + (SITE_CHECKS if mode == "both" else ())
