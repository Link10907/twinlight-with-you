"""Per-person native-layer briefs. This module never cuts out or uploads an image."""
from __future__ import annotations
from copy import deepcopy
from .common import check, digest, schema_check


def read_card_data(path) -> dict:
    """Accept standalone card content or existing Lite content without inventing themes."""
    from . import lite
    data, _, errors = lite.parse(path.read_text(encoding='utf-8'))
    check(not errors, '闪卡输入不是有效 JSON')
    data = lite.normalize(data)
    if isinstance(data, dict) and data.get('twinlight') == 'lite-1':
        errors = lite.validate(data)
    else:
        schema_check(data, 'card-input.schema.json')
        errors = []
        lite._semantic(data, errors)
    check(not errors, '闪卡内容未通过校验：' + '；'.join(e['path'] + ' ' + e['message'] for e in errors))
    return data


LAYER_ORDER = ("background", "spirit", "subject", "effects", "text")
CANVAS = {"width": 1080, "height": 1440, "ratio": "3:4", "same_coordinates_for_all_layers": True}
DEPTHS = {"background": -.25, "subject": .4, "effects": .5, "text": 0}


def canvas_spec(canvas=None) -> dict:
    """Retain a generator's native canvas instead of forcing a nominal export size."""
    if canvas is None:
        return dict(CANVAS)
    if isinstance(canvas, dict):
        width, height = canvas.get("width"), canvas.get("height")
    else:
        check(isinstance(canvas, (list, tuple)) and len(canvas) == 2, "Canvas must contain width and height")
        width, height = canvas
    check(type(width) is int and type(height) is int and width >= 256 and height >= 256,
          "Canvas dimensions must be integer pixels, at least 256")
    check(width * height <= 16_000_000 and abs(width / height - .75) < .01,
          "Canvas must be a native 3:4 portrait image, at most 16 million pixels; regenerate instead of cropping")
    return {**CANVAS, "width": width, "height": height}


def art_prompts(card: dict, *, canvas=None, composition: dict | None = None) -> dict:
    """All supported drawing routes use the same bounded visual compiler."""
    from .art_quality import parse_json
    from .visual_contract import layer_prompt
    from .card_context import image_input
    desc = str((card or {}).get("art_prompt") or "").strip()
    check(desc.startswith("{"), "Free-text art prompts are not a drawing input. Use card-image-input-1 and visual_plan.py init.")
    design = parse_json(desc)
    check(isinstance(design, dict) and design.get("version") == "art-direction-2",
          "Legacy broad briefs are archival only. Compile a bounded card-image-input-1 first.")
    image_input(design)  # Validate the same whitelist before emitting any prompt.
    dimensions = canvas_spec(canvas)
    native = (dimensions["width"], dimensions["height"])
    prompts = {role: layer_prompt(design, role, native, composition)
               for role in ("prototype", "background", "subject", "effects", "spirit")}
    prompts["character"] = prompts["subject"]
    prompts["text"] = "程序独立排版当前 SSR、称号、关键词、标语与实际总结者；同画布透明文字层，depth=0；不调用图像模型画字。"
    return prompts


def card_spec(data: dict, *, generated_at: str, canvas=None, composition: dict | None = None,
              art_prompt: str | None = None) -> dict:
    """A brief and safe manifest template bound to this person's current card content."""
    from .lite import persona_digest as content_digest
    persona_digest = content_digest(data)
    visual_card = dict(data['card'])
    if art_prompt is not None:
        limit = 6000 if isinstance(art_prompt, str) and art_prompt.lstrip().startswith("{") else 1500
        if isinstance(art_prompt, str) and art_prompt.lstrip().startswith("{"):
            from .art_quality import parse_json
            if parse_json(art_prompt).get("version") == "art-direction-2":
                limit = 12000
        check(isinstance(art_prompt, str) and 20 <= len(art_prompt.strip()) <= limit,
              '独立美术提示超出大小限制；v2 使用有界形象字段，不拼入个人历史')
        if art_prompt.lstrip().startswith("{"):
            from .art_quality import parse_json, validate_design
            validate_design(parse_json(art_prompt), persona_digest)
        visual_card['art_prompt'] = art_prompt.strip()
    check(bool(visual_card.get('art_prompt')), '闪卡流程需要美术提示；使用 --art-prompt-file，不必修改 HTML 内容')
    check(composition is None or isinstance(composition, dict), "Composition lock must be an object")
    if canvas is None and composition is not None:
        canvas = composition.get("canvas")
    actual_canvas = canvas_spec(canvas)
    if composition is not None:
        from .art import validate_composition
        composition = deepcopy(composition)
        validate_composition(composition, persona_digest, (actual_canvas["width"], actual_canvas["height"]))
    spec = {
        "version": "1.0", "generation_status": "brief_only", "persona_digest": persona_digest,
        "card_spec_digest": digest({"name": data["name"], "summarizer": data["summarizer"], "card": data["card"],
                                    "art_prompt": visual_card['art_prompt'], "canvas": actual_canvas, "composition": composition}),
        "canvas": actual_canvas, "prototype": {"file": "prototype.png", "role": "reference_only", "included_in_final_layers": False},
        "layer_order": list(LAYER_ORDER), "depths": dict(DEPTHS),
        "prompts": art_prompts(visual_card, canvas=actual_canvas, composition=composition),
        "typography": {"title": data["card"]["title"], "english_title": data["card"]["english_title"],
                       "keywords": list(data["card"]["keywords"]), "tagline": data["card"]["tagline"],
                       "summarizer": data["summarizer"], "rarity": "SSR"},
        "rules": ["Generate native independent layers from one selected prototype; never cut a poster into layers.",
                  "Subject/effects/text use genuine alpha, all layers retain the full shared canvas and coordinates.",
                  "Background is a complete opaque scene with no repeated subject; unused spirit is transparent.",
                  "Lineart is derived from the final subject's exact pixels; it is not redrawn or segmented.",
                  "A dimension or composition mismatch requires regenerating that layer; do not crop, resize or reposition it.",
                  "Missing native artwork blocks the requested card delivery; do not substitute placeholder HTML.",
                  "Send only one compiled role prompt and its whitelisted images; no host content, manuals or full card-spec."],
        "quality_review": {"required": True, "automatic_approval": False,
                           "checks": ["Same current-person concept, visual style and symbol across independent layers",
                                      "Same native canvas, pose, perspective and light as the selected prototype",
                                      "Complete background with no duplicated subject; clean native alpha edges",
                                      "Face or main symbol and title remain readable when tilted",
                                      "No example character, object, biography or text carried into this card"]},
        "manifest_template": {
            "schema_version": "1.0", "persona_digest": persona_digest, "art_status": "generated", "reference_consent": False,
            "assets": {"background": "background.png", "subject": "subject.png", "spirit": "spirit.png",
                       "effects": "effects.png", "text": "text.png", "lineart": "lineart.png"},
            "depths": dict(DEPTHS), "notes": "Template only: fill with this card's actually generated native independent layers; prototype is reference only.",
        },
    }
    if visual_card['art_prompt'].lstrip().startswith("{"):
        from .art_quality import parse_json
        design = parse_json(visual_card['art_prompt'])
        if design.get("version") == "art-direction-2":
            from .visual_contract import style_binding, subject_prompt, visual_keywords
            spec["visual_contract"] = {"version": "art-direction-2", "style": style_binding(design),
                                       "subject_prompt": subject_prompt(design),
                                       "visual_keywords": visual_keywords(design),
                                       "identity_keywords_used_for_drawing": False,
                                       "subject_count": 1, "main_prop_limit": 1}
    if composition is not None:
        spec["composition"] = composition
        spec["manifest_template"]["composition"] = deepcopy(composition)
    return spec
