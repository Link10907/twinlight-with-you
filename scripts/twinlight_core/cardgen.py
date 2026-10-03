"""Per-person native-layer briefs. This module never cuts out or uploads an image."""
from __future__ import annotations
from .common import digest


LAYER_ORDER = ("background", "spirit", "subject", "effects", "text")
CANVAS = {"width": 1080, "height": 1440, "ratio": "3:4", "same_coordinates_for_all_layers": True}
DEPTHS = {"background": -.25, "subject": .4, "effects": .5, "text": 0}


def art_prompts(card: dict) -> dict:
    """Keep the concept personal; keep registration, transparency and typography explicit."""
    desc = str((card or {}).get("art_prompt") or "").strip()
    concept = "本次卡面设定：" + desc
    style = "遵循本次用户确认的视觉风格、主体与象征物；没有指定时采用细腻原创插画。不要套用示例人物、月夜、服装、性别、肤色或经历。"
    canvas = "统一 1080×1440、竖版 3:4 全画布；各层使用同一坐标，保持已确认原型的构图、比例、姿态与光照。不得裁剪到主体后重新摆位。"
    alpha = "直接原生生成带真实 alpha 通道的透明 PNG，主体之外透明；不抠图，不去背景，不用纯色幕布，不把灰白棋盘格画成图片。工具不能输出透明层时保留原型为静态预览，并明确分层尚未完成。"
    no_text = "不要画文字、字母、数字、签名、水印、SSR、边框或彩虹镭射；文字与卡框在独立 text 层排版，镭射由渲染器添加。"
    subject = "\n".join([
        "参考同一张已确认原型，直接生成收藏闪卡的独立 subject 主体层。", concept, style, canvas,
        "只保留本次原型的主体、服饰和主要手持物；主体可以是人物，也可以是用户选择的物件或抽象象征。周围的环境归背景层，远景同伴归 spirit 层。",
        alpha, no_text,
    ])
    return {
        "prototype": "\n".join([
            "根据本次用户资料生成一张无字收藏闪卡原型，作为之后原生分层生图的构图参考。", concept, style,
            "1080×1440、竖版 3:4；主体是视觉焦点。保留顶部 SSR 和底部称号的排版空间，但不要画出它们。",
            "原型可包含完整主体与环境；它只作为共同参考，不得从这张海报抠出后续图层，也不得将整张图重复贴到多个层。", no_text,
        ]),
        "subject": subject,
        "character": subject,
        "background": "\n".join([
            "参考同一张已确认原型，直接生成收藏闪卡的独立 background 场景层。", concept, style, canvas,
            "只生成完整场景，不要画主体，不要画人物或主体的影子、替身、残片；主体曾遮住的位置也必须画完整。保持原型的环境、透视与光照，不需要先去掉任何人物。",
            "整张场景必须完全不透明。主体层会单独叠加；不要将完整原型用作背景。", no_text,
        ]),
        "effects": "\n".join([
            "参考同一张已确认原型，直接生成收藏闪卡的独立 effects 前景效果层。", concept, style, canvas,
            "只绘制本次设定需要的少量前景象征物、光粒或装饰；不要重画主体或场景，不遮住主体的脸及后续文字。", alpha, no_text,
        ]),
        "spirit": "\n".join([
            "参考同一张已确认原型，直接生成可选的 spirit 中景伴生层。", concept, style, canvas,
            "只有本次设定明确包含同伴或中景象征时才生成，不要为凑层数添加人格含义；不使用时交付同尺寸全透明 PNG。不要重画主角。", alpha, no_text,
        ]),
        "text": "\n".join([
            "SSR、卡框与文字默认由程序排版为独立 text 层，真实透明、同一 1080×1440 画布，depth=0。",
            "排版只使用当前卡的 title、english_title、keywords、tagline 与当前总结者署名，不沿用示例文案。",
            "也可独立生图生成 text 层，但必须逐字核对、保持真实 alpha 与同画布坐标；不能把文字烧进 subject 或 background。",
        ]),
    }


def card_spec(data: dict, *, generated_at: str) -> dict:
    """A brief and safe manifest template bound to this person's current card content."""
    from .lite import to_profile
    profile = to_profile(data, generated_at=generated_at)
    persona_digest = profile["persona"]["persona_digest"]
    return {
        "version": "1.0", "persona_digest": persona_digest,
        "card_spec_digest": digest({"name": data["name"], "summarizer": data["summarizer"], "card": data["card"]}),
        "canvas": dict(CANVAS), "prototype": {"file": "prototype.png", "role": "reference_only", "included_in_final_layers": False},
        "layer_order": list(LAYER_ORDER), "depths": dict(DEPTHS), "prompts": art_prompts(data["card"]),
        "typography": {"title": data["card"]["title"], "english_title": data["card"]["english_title"],
                       "keywords": list(data["card"]["keywords"]), "tagline": data["card"]["tagline"],
                       "summarizer": data["summarizer"], "rarity": "SSR"},
        "rules": ["Generate native independent layers from one confirmed prototype; never cut a poster into layers.",
                  "Subject/effects/text use genuine alpha, all layers retain the full shared canvas and coordinates.",
                  "Background is a complete opaque scene with no repeated subject; unused spirit is transparent.",
                  "Lineart is derived from the final subject's exact pixels; it is not redrawn or segmented.",
                  "Prototype-only output is static, with zero parallax; missing image tools means placeholder.",
                  "Only this person's provided content and confirmed style may define the image; examples are not input."],
        "manifest_template": {
            "schema_version": "1.0", "persona_digest": persona_digest, "art_status": "generated", "reference_consent": False,
            "assets": {"background": "background.png", "subject": "subject.png", "spirit": "spirit.png",
                       "effects": "effects.png", "text": "text.png", "lineart": "lineart.png"},
            "depths": dict(DEPTHS), "notes": "Native independent layers generated for this card; prototype is reference only.",
        },
    }
