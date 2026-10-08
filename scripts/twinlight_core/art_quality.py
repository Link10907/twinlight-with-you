"""Fail-closed artwork evidence gates. Local records are NOT authenticated tool receipts.

This module checks files, bindings, and recorded reviews. It neither generates
images nor judges beauty. Even an accepted dossier keeps quality_verified and
generation_provenance_verified false: its observations belong to the named host.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageFilter, ImageOps

MAX_JSON = 2 * 1024 * 1024
MAX_ASSET = 24 * 1024 * 1024
MAX_PIXELS = 16_000_000
ROLES = ("background", "spirit", "subject", "effects", "text", "lineart")
SCENE_FIELDS = ("style", "subject", "action", "setting", "materials", "palette", "lighting", "composition")
REVIEW_CHECKS = {
    "prototype": ("subject_clarity", "composition", "materials", "lighting", "preference_fit", "distinctiveness", "text_space"),
    "composite": ("registration", "complete_background", "clean_edges", "single_ownership", "prototype_fidelity"),
    "final": ("typography", "visual_hierarchy", "preference_fit", "parallax", "foil", "mobile_readability"),
}


class ArtEvidenceError(ValueError):
    def __init__(self, code: str, message: str, *, status: str = "art_rejected"):
        super().__init__(message)
        self.code, self.status = code, status


def require(condition: bool, code: str, message: str, *, status: str = "art_rejected") -> None:
    if not condition:
        raise ArtEvidenceError(code, message, status=status)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_key", "Duplicate JSON field: " + key)
        result[key] = value
    return result


def parse_json(text: str) -> Any:
    def bad_number(value):
        raise ArtEvidenceError("nonfinite_number", "Non-finite JSON number")
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=bad_number)


def read_json(path: Path) -> dict:
    require(path.is_file(), "missing_file", "Missing evidence file: " + path.name, status="needs_art_evidence")
    require(path.stat().st_size <= MAX_JSON, "record_too_large", "Evidence JSON exceeds 2 MiB")
    data = parse_json(path.read_text(encoding="utf-8-sig"))
    require(isinstance(data, dict), "object_required", "Evidence must be a JSON object")
    return data


def _string(value, field: str, minimum: int = 1, maximum: int = 2000):
    require(isinstance(value, str) and minimum <= len(value.strip()) <= maximum,
            "invalid_text", field + " requires a specific, bounded description")
    return value.strip()


def _strings(value, field: str, minimum: int = 0):
    require(isinstance(value, list) and minimum <= len(value) <= 32, "invalid_list", field + " must be a bounded list")
    return [_string(item, field, maximum=500) for item in value]


def _digest(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            "invalid_hash", "Expected a lowercase SHA-256 digest")
    return value


def checked_ref(root: Path, ref: dict, *, limit: int = MAX_ASSET) -> Path:
    require(isinstance(ref, dict), "invalid_ref", "A file reference must contain file and sha256")
    name = _string(ref.get("file"), "file", maximum=500)
    relative = Path(name)
    require(not relative.is_absolute() and ".." not in relative.parts and ":" not in name,
            "unsafe_path", "Evidence references must be relative, local paths within the card directory")
    target = (root / relative).resolve()
    require(target.is_relative_to(root.resolve()), "unsafe_path", "Evidence symlink escapes the card directory")
    require(target.is_file(), "missing_file", "Missing evidence asset: " + name, status="needs_art_evidence")
    require(target.stat().st_size <= limit, "asset_too_large", "Evidence asset exceeds its size limit")
    require(sha256(target) == _digest(ref.get("sha256")), "hash_mismatch", "Evidence asset changed: " + name)
    return target


def image(path: Path) -> Image.Image:
    require(path.stat().st_size <= MAX_ASSET, "asset_too_large", "Image exceeds 24 MiB")
    with Image.open(path) as im:
        require(im.format in ("PNG", "WEBP", "JPEG"), "image_format", "Evidence image must be raster artwork")
        require(0 < im.width * im.height <= MAX_PIXELS, "image_size", "Evidence image exceeds pixel limit")
        return im.convert("RGBA")


def pixel_digest(im: Image.Image) -> str:
    return hashlib.sha256(str(im.size).encode("ascii") + im.convert("RGBA").tobytes()).hexdigest()


def validate_design(design: dict, persona: str | None = None) -> dict:
    if isinstance(design, dict) and design.get("version") == "art-direction-2":
        from .visual_contract import validate_design as validate_v2, VisualContractError
        try:
            return validate_v2(design, persona)
        except VisualContractError as exc:
            raise ArtEvidenceError(exc.code, str(exc), status="needs_art_direction") from exc
    require(isinstance(design, dict) and design.get("version") == "art-direction-1",
            "design_version", "A structured art-direction-1 brief is required", status="needs_art_direction")
    _digest(design.get("persona_digest"))
    if persona is not None:
        require(design["persona_digest"] == persona, "wrong_persona", "Design belongs to another persona")
    preferences = design.get("preferences")
    require(isinstance(preferences, dict), "preferences_missing", "Capture the current user's preferences and rejections")
    for field in ("keep", "avoid"):
        _strings(preferences.get(field), "preferences." + field)
    _string(preferences.get("basis"), "preferences.basis", 8)
    rejected = _strings(preferences.get("rejected_asset_sha256", []), "rejected_asset_sha256")
    for value in rejected:
        _digest(value)
    scene = design.get("scene")
    require(isinstance(scene, dict), "scene_missing", "Choose one concrete scene before image generation")
    for field in SCENE_FIELDS:
        _string(scene.get(field), "scene." + field, 4, 500)
    decision = design.get("decision")
    require(isinstance(decision, dict), "decision_missing", "Record the art-direction choice, not a personality score")
    candidates = decision.get("considered")
    require(isinstance(candidates, list) and 2 <= len(candidates) <= 3,
            "design_candidates", "Internally compare two or three design directions")
    names = []
    for item in candidates:
        require(isinstance(item, dict), "design_candidate", "Each direction needs a name and fit rationale")
        names.append(_string(item.get("name"), "candidate.name", maximum=80))
        _string(item.get("rationale"), "candidate.rationale", 8, 500)
    require(len(set(names)) == len(names) and decision.get("selected") in names,
            "design_selection", "Select one of the distinct candidate directions")
    _string(decision.get("rationale"), "decision.rationale", 12, 500)
    references = design.get("references", [])
    require(isinstance(references, list) and len(references) <= 5,
            "design_references", "References must be a bounded list of actual image files")
    require(design.get("reference_basis") in ("visible_images", "text_only"),
            "reference_basis", "State whether actual reference images were available")
    require(bool(references) == (design["reference_basis"] == "visible_images"),
            "reference_basis", "Do not claim to have seen absent reference images")
    from .art_typography import validate_theme
    validate_theme(design.get("typography"))
    return design


def compile_visual_brief(text: str, role: str = "prototype") -> str:
    """Only concrete visual decisions go to the image model, not the execution manual."""
    design = validate_design(parse_json(text))
    if design.get("version") == "art-direction-2":
        from .visual_contract import visual_brief
        return visual_brief(design, role)
    labels = ("画风", "主体", "动作或结构记忆点", "场景", "材质与笔触", "配色", "光线", "构图与留白")
    lines = [f"{label}：{design['scene'][field]}" for field, label in zip(SCENE_FIELDS, labels)]
    if design["preferences"]["keep"]:
        lines.append("保留：" + "；".join(design["preferences"]["keep"]))
    if design["preferences"]["avoid"]:
        lines.append("本次明确排除：" + "；".join(design["preferences"]["avoid"]))
    return "\n".join(lines)


def _source(root: Path, entry: dict, role: str, prototype_hash: str, canvas: tuple,
            run_id: str, persona: str, rejected: set[str], records: dict, inputs: dict, design: dict, design_hash: str,
            canvas_mapping: dict | None = None) -> None:
    path = checked_ref(root, entry)
    digest = sha256(path)
    require(digest not in rejected, "rejected_asset_reused", "A previously rejected asset was selected: " + role)
    require(entry.get("mode") in ("generated", "reused"), "unsupported_source",
            "Only image-tool outputs or explicitly declared same-owner reuse can supply artwork")
    if entry["mode"] == "reused":
        reuse = entry.get("reuse", {})
        require(isinstance(reuse, dict) and reuse.get("persona_digest") == persona and reuse.get("declared") is True,
                "undeclared_reuse", "Reuse requires the same persona and an explicit reuse declaration")
        _string(reuse.get("reason"), "reuse.reason", 12)
    call_path = checked_ref(root, entry.get("call"), limit=MAX_JSON)
    call = read_json(call_path)
    inputs[str(call_path)] = sha256(call_path)
    inputs[str(path)] = digest
    require(call.get("version") == "image-call-1" and call.get("kind") == "image_tool",
            "call_kind", "Code drawings or model summaries are not image-tool calls")
    tool = _string(call.get("tool"), "tool", maximum=120)
    require(tool.casefold() not in {"python", "pillow", "svg", "canvas", "placeholder"},
            "procedural_source", "Procedural geometry cannot masquerade as generated illustration")
    call_id = _string(call.get("call_id"), "call_id", maximum=500)
    if entry["mode"] == "generated":
        require(call.get("run_id") == run_id, "old_call_as_new", "An old invocation cannot be labelled newly generated")
    else:
        _string(call.get("run_id"), "previous run_id", maximum=200)
    caps = call.get("capabilities", {})
    require(isinstance(caps, dict) and caps.get("image_generation") is True,
            "image_tool_unavailable", "No image-generation capability was recorded")
    request = call.get("request", {})
    v2 = design.get("version") == "art-direction-2"
    require(isinstance(request, dict), "invalid_request", "Capture the actual image request")
    if v2 and role == "prototype":
        requested = request.get("canvas")
        require(isinstance(requested, list) and len(requested) == 2
                and all(type(n) is int and n >= 256 for n in requested)
                and requested[0] * requested[1] <= MAX_PIXELS and abs(requested[0] / requested[1] - .75) < .01,
                "canvas_mismatch", "Record requested native prototype dimensions separately from actual returned dimensions")
    else:
        require(request.get("canvas") == list(canvas),
                "canvas_mismatch", "Independent layer request must use the selected prototype canvas")
    if v2:
        from .visual_contract import style_binding
        require(request.get("style_binding") == style_binding(design),
                "style_drift", "The image request did not use the current versioned style")
        require(request.get("role") == role, "wrong_layer_request", "The recorded request belongs to another layer")
    prompt = checked_ref(root, request.get("prompt"), limit=MAX_JSON)
    require(prompt.stat().st_size > 0, "empty_prompt", "An actual per-layer image prompt is required")
    inputs[str(prompt)] = sha256(prompt)
    if entry["mode"] == "generated":
        require(request.get("design_sha256") == design_hash, "wrong_prompt_design", "The invocation must bind the current art direction")
        if v2 and request.get("operation") == "image_edit":
            from .visual_contract import layer_prompt
            require(role != "prototype", "edit_phase", "Select a generated prototype before editing native layers")
            base = checked_ref(root, request.get("edit_base"))
            require(sha256(base) == prototype_hash and request.get("coordinate_policy") == "preserve_full_canvas",
                    "edit_base_mismatch", "Native layer editing must retain the current approved prototype canvas")
            inputs[str(base)] = sha256(base)
            visual = layer_prompt(design, role, tuple(canvas))
        else:
            visual = compile_visual_brief(json.dumps(design, ensure_ascii=False), role=role)
        require(visual in prompt.read_text(encoding="utf-8"), "visual_brief_missing", "Actual prompt must include the current concrete visual brief")
    if role in ("subject", "effects", "spirit"):
        require(caps.get("native_transparency") is True and request.get("transparent") is True,
                "native_alpha_missing", "The image invocation must request actual native transparency")
    if role == "background":
        require(request.get("transparent") is False, "opaque_background_request", "Request an opaque background")
    references = request.get("reference_sha256", [])
    require(isinstance(references, list), "invalid_references", "Reference hashes must be a list")
    if v2:
        from .visual_contract import style_for, style_references
        anchors = style_references(style_for(design["style"]["id"], design["style"]["version"]))
        if anchors:
            require(digest not in {anchor["sha256"] for anchor in anchors}, "style_reference_reused",
                    "A bundled style reference is not newly generated personal artwork")
        if anchors and role == "prototype":
            attached = request.get("reference_images", [])
            require(isinstance(attached, list), "style_reference_missing", "Record actual style reference image attachments")
            staged = {}
            for reference in attached:
                p = checked_ref(root, reference)
                image(p)
                inputs[str(p)] = sha256(p)
                staged[sha256(p)] = reference.get("purpose")
            for anchor in anchors:
                require(anchor["sha256"] in references and staged.get(anchor["sha256"]) == "style_only"
                        and caps.get("reference_images") is True,
                        "style_reference_missing", "The actual image request must attach the installed visual quality reference as style_only")
    if role != "prototype":
        require(caps.get("reference_images") is True and prototype_hash in references,
                "prototype_reference_missing", "Every independent layer must reference the selected prototype")
        if v2 and anchors:
            attached = request.get("reference_images", [])
            require(isinstance(attached, list) and len(attached) == 1
                    and attached[0].get("sha256") == prototype_hash
                    and attached[0].get("purpose") == "composition",
                    "composition_reference_missing", "Native layer editing must use only the approved prototype as its composition authority")
            p = checked_ref(root, attached[0])
            image(p)
            inputs[str(p)] = sha256(p)
    response = call.get("response", {})
    require(isinstance(response, dict) and response.get("sha256") == digest,
            "tool_output_mismatch", "Returned image bytes do not match the registered layer")
    im = image(path)
    if v2:
        require(response.get("canvas") == list(im.size), "returned_canvas", "Record actual returned image dimensions, including native rounding")
    artifact = _string(response.get("artifact_id"), "artifact_id", maximum=500)
    raw = checked_ref(root, call.get("raw_response"), limit=MAX_JSON)
    if v2:
        from .image_dispatch import check_recorded_dispatch
        check_recorded_dispatch(root, call, inputs)
    raw_text = raw.read_text(encoding="utf-8")
    inputs[str(raw)] = sha256(raw)
    require(bool(raw_text.strip()), "uncaptured_response", "Preserve the actual returned message or attachment record")
    if response.get("artifact_id_origin") == "local_binding":
        require(artifact == "local-artifact:" + digest and response.get("provider_artifact_id") is None,
                "local_artifact_mismatch", "A local artifact key is a file hash, not a provider ID")
    else:
        require(artifact in raw_text, "uncaptured_response", "The recorded artifact is absent from the captured tool response")
    if call.get("call_id_origin") == "local_binding":
        dispatched = checked_ref(root, request.get("dispatch"))
        require(call_id == "local-call:" + sha256(dispatched) and call.get("provider_call_id") is None,
                "local_call_mismatch", "A local invocation key binds the pre-call dispatch, not a platform receipt")
    # Track call/artifact pairs rather than allowing one returned image to fill several roles.
    key = tool + "\0" + call_id + "\0" + artifact
    require(key not in records, "duplicate_tool_output", "One returned image cannot fill multiple independent roles")
    records[key] = digest
    from .canvas_mapping import native_dimensions_allowed
    explicit_native_edit = bool(canvas_mapping and role in canvas_mapping.get("native_edit_roles", [])
                                and v2 and request.get("operation") == "image_edit"
                                and request.get("coordinate_policy") == "preserve_full_canvas")
    require(native_dimensions_allowed(im.size, canvas, native_edit=explicit_native_edit),
            "canvas_mismatch", "Only explicitly mapped native image edits may differ by one pixel; preserve original bytes")


def _manifest_assets(root: Path, manifest: dict) -> tuple[dict, dict]:
    entries = manifest.get("assets", {})
    require(isinstance(entries, dict) and set(entries) == set(ROLES), "layer_roles", "The six layer roles are required")
    paths, images = {}, {}
    for role in ROLES:
        name = _string(entries[role], role + ".file", maximum=500)
        require(not Path(name).is_absolute() and ".." not in Path(name).parts and ":" not in name,
                "unsafe_path", "Layer paths must stay inside the card directory")
        p = (root / name).resolve()
        require(p.is_relative_to(root.resolve()), "unsafe_path", "Layer symlink escapes the card directory")
        require(p.is_file(), "missing_layer", "Missing layer: " + role, status="needs_card")
        paths[role], images[role] = p, image(p)
    return paths, images


def _review(root: Path, evidence: dict, stage: str, targets: dict, inputs: dict, required_checks=None) -> dict:
    entry = evidence.get("reviews", {}).get(stage)
    require(entry is not None, "missing_review", "Actual " + stage + " review is required", status="needs_art_review")
    path = checked_ref(root, entry, limit=MAX_JSON)
    data = read_json(path)
    inputs[str(path)] = sha256(path)
    require(data.get("stage") == stage and data.get("targets") == targets,
            "stale_review", "Review is not bound to the current " + stage + " artwork")
    require(data.get("decision") in ("accept", "revise", "pending", "blocked"), "review_decision", "Invalid review decision")
    require(data.get("decision") != "blocked", "reviewer_blocked", "Reviewer could not inspect actual evidence", status="reviewer_blocked")
    require(data["decision"] != "pending", "pending_review", "Review has not been performed", status="needs_art_review")
    require(data["decision"] == "accept", "review_rejected", "The observer rejected this artwork")
    _string(data.get("observer"), "observer", 2, 120)
    observed = dt.datetime.fromisoformat(_string(data.get("observed_at"), "observed_at", maximum=80).replace("Z", "+00:00"))
    require(observed.tzinfo is not None, "review_time", "Review timestamp must include a timezone")
    checks = data.get("checks", {})
    require(isinstance(checks, dict) and set(required_checks or REVIEW_CHECKS[stage]).issubset(checks),
            "incomplete_review", "Every required visual criterion needs a concrete observation", status="needs_art_review")
    for name, item in checks.items():
        require(isinstance(item, dict) and item.get("passed") is True, "failed_visual_check", "Visual criterion failed: " + name)
        _string(item.get("observation"), name + ".observation", 12, 1500)
    capture = checked_ref(root, data.get("capture"), limit=MAX_JSON)
    require(capture.stat().st_size > 0, "empty_review_capture", "Keep the actual visual inspection record")
    inputs[str(capture)] = sha256(capture)
    if stage == "final":
        views = data.get("views", {})
        require(isinstance(views, dict) and {"left", "right", "mobile"}.issubset(views),
                "missing_view", "Final review needs actual left/right and mobile captures", status="needs_art_review")
        signatures = []
        for name in ("left", "right", "mobile"):
            p = checked_ref(root, views[name])
            signatures.append(pixel_digest(image(p)))
            inputs[str(p)] = sha256(p)
        require(signatures[0] != signatures[1], "duplicate_views", "Left and right views cannot be the same pixels")
    from .independent_review import check_handoff
    check_handoff(root, data, inputs)
    return data


def snapshot(manifest_path: Path, persona: str, *, stage: str = "final", front: Path | None = None,
             preview: Path | None = None) -> tuple[dict, dict, dict, dict]:
    """Compute review targets; this function never creates an accepted review."""
    require(stage in REVIEW_CHECKS, "invalid_stage", "Unknown art review stage")
    root = manifest_path.resolve().parent
    evidence_path = root / "art-evidence.json"
    require(evidence_path.resolve().is_relative_to(root), "unsafe_path", "Evidence file escapes the card directory")
    manifest, evidence = read_json(manifest_path), read_json(evidence_path)
    require(manifest.get("persona_digest") == persona and evidence.get("persona_digest") == persona,
            "wrong_persona", "Manifest/evidence belong to another persona")
    require(evidence.get("version") == "art-evidence-1", "evidence_version", "Unsupported artwork evidence version")
    brief_path = checked_ref(root, evidence.get("design"), limit=MAX_JSON)
    design = validate_design(read_json(brief_path), persona)
    reference_inputs = {}
    if design.get("version") == "art-direction-2":
        from .visual_contract import style_for, style_references, STYLE_DIR
        style = style_for(design["style"]["id"], design["style"]["version"])
        reference_inputs[style["path"]] = style["sha256"]
        reference_inputs[str(STYLE_DIR / "catalog.json")] = sha256(STYLE_DIR / "catalog.json")
        for anchor in style_references(style):
            reference_inputs[anchor["file"]] = anchor["sha256"]
    for ref in design.get("references", []):
        reference_path = checked_ref(root, ref)
        image(reference_path)
        reference_inputs[str(reference_path)] = sha256(reference_path)
    images = evidence.get("images", {})
    require(isinstance(images, dict) and isinstance(images.get("prototype"), dict),
            "prototype_missing", "A selected, wordless prototype is required", status="needs_art_evidence")
    prototype = checked_ref(root, images["prototype"])
    im = image(prototype)
    require(im.width >= 256 and im.height >= 256 and abs(im.width / im.height - .75) < .01,
            "prototype_canvas", "Prototype must be a native 3:4 image, at least 256px")
    base = {"persona_digest": persona, "design_sha256": sha256(brief_path), "prototype_sha256": sha256(prototype)}
    if design.get("version") == "art-direction-2":
        from .visual_contract import style_binding
        base["style_binding"] = style_binding(design)
    targets = {"prototype": base}
    inputs = {str(manifest_path.resolve()): sha256(manifest_path), str(root / "art-evidence.json"): sha256(root / "art-evidence.json"),
              str(brief_path): sha256(brief_path), str(prototype): sha256(prototype)}
    inputs.update(reference_inputs)
    if stage != "prototype":
        paths, layers = _manifest_assets(root, manifest)
        from .canvas_mapping import logical_canvas, compose_layers
        require(logical_canvas(manifest, layers) == im.size, "canvas_mismatch", "The display canvas must remain the approved prototype canvas")
        require(layers["background"].getchannel("A").getextrema() == (255, 255),
                "background_alpha", "Background must be completely opaque; draft is not an exemption")
        for role in ("subject", "effects", "text"):
            hist = layers[role].getchannel("A").histogram()
            count = layers[role].width * layers[role].height
            require(sum(hist[:16]) / count > .01 and sum(hist[16:]) / count > .0005,
                    "layer_alpha", role + " must contain real transparent and occupied regions")
        alpha = layers["subject"].getchannel("A")
        edge = ImageChops.difference(alpha.filter(ImageFilter.MaxFilter(5)), alpha.filter(ImageFilter.MinFilter(5)))
        expected = ImageOps.invert(edge).convert("RGBA")
        require(pixel_digest(expected) == pixel_digest(layers["lineart"]),
                "unregistered_lineart", "Lineart must be derived from the final subject's exact alpha pixels")
        fingerprints = {role: sha256(p) for role, p in paths.items()}
        for role in ("background", "subject", "effects", "spirit"):
            require(pixel_digest(layers[role]) != pixel_digest(im), "poster_reused", "Prototype cannot be reused as a layer")
        raw = compose_layers(manifest, layers)
        composite_targets = {**base, "manifest_sha256": sha256(manifest_path), "layers_sha256": fingerprints,
                             "composite_pixels_sha256": pixel_digest(raw)}
        targets["composite"] = composite_targets
        composite_path = checked_ref(root, evidence.get("composite"))
        inputs[str(composite_path)] = sha256(composite_path)
        composite = image(composite_path)
        require(pixel_digest(composite) == pixel_digest(raw), "wrong_composite", "Review the actual unlettered assembled image")
        inputs.update({str(p): sha256(p) for p in paths.values()})
        if stage == "final":
            require(front is not None and preview is not None and front.is_file() and preview.is_file(),
                    "final_preview_missing", "Generate the real front and interactive preview before final review", status="needs_art_review")
            expected_front = Image.alpha_composite(raw, layers["text"])
            require(pixel_digest(image(front)) == pixel_digest(expected_front), "wrong_front", "Final front is not the current assembled card")
            targets["final"] = {**composite_targets, "front_sha256": sha256(front), "preview_sha256": sha256(preview)}
            inputs[str(front.resolve())], inputs[str(preview.resolve())] = sha256(front), sha256(preview)
    return targets, evidence, design, inputs


def check_evidence(manifest_path: Path, persona: str, *, stage: str = "final", front: Path | None = None,
                   preview: Path | None = None) -> dict:
    report = {"ok": False, "status": "needs_art_evidence", "stage": stage, "errors": [],
              "evidence_checked": False, "host_visual_review_recorded": False,
              "quality_verified": False, "generation_provenance_verified": False,
              "scope": "File bindings and host-recorded observations only; no authenticated provider receipt or automatic beauty judgment."}
    try:
        targets, evidence, design, inputs = snapshot(manifest_path, persona, stage=stage, front=front, preview=preview)
        root = manifest_path.resolve().parent
        run_id = _string(evidence.get("run_id"), "run_id", maximum=200)
        rejected = set(design["preferences"].get("rejected_asset_sha256", []))
        images = evidence["images"]
        prototype_hash = targets["prototype"]["prototype_sha256"]
        canvas = image(checked_ref(root, images["prototype"])).size
        records, reused = {}, []
        roles = ["prototype"]
        manifest = read_json(manifest_path)
        if stage != "prototype":
            roles += ["background", "subject", "effects"]
            spirit_path = root / manifest["assets"]["spirit"]
            if image(spirit_path).getchannel("A").getbbox() is not None:
                roles.append("spirit")
        for role in roles:
            entry = images.get(role)
            require(isinstance(entry, dict), "source_missing", "Missing actual image-tool evidence for " + role, status="needs_art_evidence")
            if role != "prototype":
                require(entry.get("file") == manifest["assets"][role], "source_path_mismatch", "Evidence points to another " + role + " asset")
            _source(root, entry, role, prototype_hash, canvas, run_id, persona, rejected, records, inputs, design,
                    targets["prototype"]["design_sha256"], manifest.get("canvas_mapping"))
            if entry["mode"] == "reused":
                reused.append(role)
        report["evidence_checked"] = True
        observers = {}
        for current in REVIEW_CHECKS:
            from .visual_contract import review_checks
            review = _review(root, evidence, current, targets[current], inputs,
                             review_checks(design, current, REVIEW_CHECKS[current]))
            observers[current] = review["observer"]
            if current == stage:
                break
        # Catch any changed evidence/input after read/verification instead of inheriting a stale review.
        require(all(Path(p).is_file() and sha256(Path(p)) == h for p, h in inputs.items()),
                "changed_during_review", "An artwork or review file changed during verification")
        report.update(ok=True, status="art_review_recorded", host_visual_review_recorded=True,
                      observers=observers, reused_roles=reused, targets=targets, inputs_sha256=inputs)
    except ArtEvidenceError as exc:
        report.update(status=exc.status, errors=[{"code": exc.code, "message": str(exc)}])
    except (OSError, ValueError, TypeError, KeyError, AttributeError, Image.DecompressionBombError) as exc:
        report.update(status="art_rejected", errors=[{"code": "invalid_evidence", "message": str(exc)[:800]}])
    return report
