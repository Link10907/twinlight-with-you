"""Per-person native-layer briefs. This module never cuts out or uploads an image."""
from __future__ import annotations
from copy import deepcopy
from .common import check, digest


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
    """Keep the concept personal; keep registration, transparency and typography explicit."""
    desc = str((card or {}).get("art_prompt") or "").strip()
    concept = "本次卡面设定：" + desc
    style = "遵循本次明确偏好、最新审美反馈与 AI 从当前资料自主选择的美术设定，不询问创意选择。画风与主体由行为、气质和卡面表现力共同决定；人物、动物、拟人角色和寓意物件均可，不固定二次元人像、小鹿或某种画法。统一笔触、材质、色彩和光线，保持主体清楚、比例合理、细节精致、象征克制；轮廓、动作或材质需要有本次设计的记忆点，整幅画面的美术语言应有辨识度，仅换物种、换脸、换衣服或加光球不足以形成特色。虚构形象不代表本人真实身份。不要套用示例人物、月夜、服装、性别、肤色或经历。"
    dimensions = canvas_spec(canvas)
    size = f"{dimensions['width']}×{dimensions['height']}"
    registered_canvas = f"统一 {size}、竖版 3:4 全画布；各层使用同一坐标，保持本次选定原型的构图、比例、姿态与光照。不得裁剪到主体后重新摆位。"
    if composition is not None:
        rules = ["严格沿用本次原型的实际画布和构图锁；坐标是左上角为 (0,0)、右下角为 (1,1) 的归一化坐标。"]
        if "subject_bounds" in composition:
            rules.append(f"主体的完整可见轮廓必须位于 subject_bounds={composition['subject_bounds']}，不能为适配该区域而裁剪或移动原型主体。")
        if "subject_center_region" in composition:
            rules.append(f"保持主体总体轮廓的中心在 subject_center_region={composition['subject_center_region']}；这不是脸部位置，脸和主要象征物仍需对照原型看图检查。")
        if "text_safe_regions" in composition:
            rules.append(f"文字留白区 text_safe_regions={composition['text_safe_regions']} 内不要绘制主体、同伴或前景装饰，文字稍后独立排版。")
        registered_canvas += "\n" + "\n".join(rules)
    alpha = "直接原生生成带真实 alpha 通道的透明 PNG，主体之外透明；不抠图，不去背景，不用纯色幕布，不把灰白棋盘格画成图片。工具不能输出透明层时保留原型为静态预览，并明确分层尚未完成。"
    no_text = "不要画文字、字母、数字、签名、水印、SSR、边框或彩虹镭射；文字与卡框在独立 text 层排版，镭射由渲染器添加。"
    subject = "\n".join([
        "参考同一张本次选定原型，直接生成收藏闪卡的独立 subject 主体层。", concept, style, registered_canvas,
        "只保留本次原型的主体、随身细节和主要物件；主体按本次自主选择的设定，可以是人物、动物、拟人角色或寓意物件。周围的环境归背景层，远景同伴归 spirit 层。",
        alpha, no_text,
    ])
    return {
        "prototype": "\n".join([
            "根据本次用户资料生成一张无字收藏闪卡原型，作为之后原生分层生图的构图参考。", concept, style,
            f"{size}、竖版 3:4；主体是视觉焦点。保留顶部 SSR 和底部称号的排版空间，但不要画出它们。",
            "原型可包含完整主体与环境；它只作为共同参考，不得从这张海报抠出后续图层，也不得将整张图重复贴到多个层。", no_text,
        ]),
        "subject": subject,
        "character": subject,
        "background": "\n".join([
            "参考同一张本次选定原型，直接生成收藏闪卡的独立 background 场景层。", concept, style, registered_canvas,
            "只生成完整场景，不要画主体，不要画人物或主体的影子、替身、残片；主体曾遮住的位置也必须画完整。保持原型的环境、透视与光照，不需要先去掉任何人物。",
            "整张场景必须完全不透明。主体层会单独叠加；不要将完整原型用作背景。", no_text,
        ]),
        "effects": "\n".join([
            "参考同一张本次选定原型，直接生成收藏闪卡的独立 effects 前景效果层。", concept, style, registered_canvas,
            "只绘制本次设定需要的少量前景象征物、光粒或装饰；不要重画主体或场景，不遮住主体的脸及后续文字。", alpha, no_text,
        ]),
        "spirit": "\n".join([
            "参考同一张本次选定原型，直接生成可选的 spirit 中景伴生层。", concept, style, registered_canvas,
            "只有本次设定明确包含同伴或中景象征时才生成，不要为凑层数添加人格含义；不使用时交付同尺寸全透明 PNG。不要重画主角。", alpha, no_text,
        ]),
        "text": "\n".join([
            f"SSR、卡框与文字默认由程序排版为独立 text 层，真实透明、同一 {size} 画布，depth=0。",
            "排版只使用当前卡的 title、english_title、keywords、tagline 与当前总结者署名，不沿用示例文案。",
            "也可独立生图生成 text 层，但必须逐字核对、保持真实 alpha 与同画布坐标；不能把文字烧进 subject 或 background。",
        ]),
    }


def card_spec(data: dict, *, generated_at: str, canvas=None, composition: dict | None = None) -> dict:
    """A brief and safe manifest template bound to this person's current card content."""
    from .lite import to_profile
    profile = to_profile(data, generated_at=generated_at)
    persona_digest = profile["persona"]["persona_digest"]
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
                                    "canvas": actual_canvas, "composition": composition}),
        "canvas": actual_canvas, "prototype": {"file": "prototype.png", "role": "reference_only", "included_in_final_layers": False},
        "layer_order": list(LAYER_ORDER), "depths": dict(DEPTHS),
        "prompts": art_prompts(data["card"], canvas=actual_canvas, composition=composition),
        "typography": {"title": data["card"]["title"], "english_title": data["card"]["english_title"],
                       "keywords": list(data["card"]["keywords"]), "tagline": data["card"]["tagline"],
                       "summarizer": data["summarizer"], "rarity": "SSR"},
        "rules": ["Generate native independent layers from one selected prototype; never cut a poster into layers.",
                  "Subject/effects/text use genuine alpha, all layers retain the full shared canvas and coordinates.",
                  "Background is a complete opaque scene with no repeated subject; unused spirit is transparent.",
                  "Lineart is derived from the final subject's exact pixels; it is not redrawn or segmented.",
                  "A dimension or composition mismatch requires regenerating that layer; do not crop, resize or reposition it.",
                  "Prototype-only output is static, with zero parallax; missing image tools means placeholder.",
                  "Use this person's provided content, explicit preferences and AI-selected art direction; examples are not input."],
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
    if composition is not None:
        spec["composition"] = composition
        spec["manifest_template"]["composition"] = deepcopy(composition)
    return spec
