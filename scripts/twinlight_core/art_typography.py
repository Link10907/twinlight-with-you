"""Theme-aware, independently typeset card text; never modifies source artwork."""
from __future__ import annotations
import math
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def validate_theme(theme: dict) -> dict:
    if not isinstance(theme, dict):
        raise ValueError("Choose typography colors, frame and scrim to suit this artwork")
    for key in ("text_color", "accent_color", "scrim_color"):
        if not isinstance(theme.get(key), str) or re.fullmatch(r"#[0-9A-Fa-f]{6}", theme[key]) is None:
            raise ValueError(key + " must be #RRGGBB")
    if theme.get("frame") not in ("none", "single", "double"):
        raise ValueError("frame must be none, single or double")
    if theme.get("layout", "measured") not in ("measured", "collector"):
        raise ValueError("layout must be measured or collector")
    opacity = theme.get("scrim_opacity")
    if type(opacity) is not int or not 0 <= opacity <= 220:
        raise ValueError("scrim_opacity must be an integer between 0 and 220")
    top = theme.get("footer_top", .76)
    if type(top) not in (float, int) or not math.isfinite(top) or not .68 <= top <= .84:
        raise ValueError("footer_top must be between 0.68 and 0.84")
    return theme


def _rgb(value: str, opacity: int = 255) -> tuple:
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5)) + (opacity,)


def typeset(data: dict, size: tuple[int, int], font: Path, theme: dict,
            composition: dict | None = None) -> tuple[Image.Image, dict]:
    """Return transparent text and measured boxes. A missing fit is an error, not clipping."""
    validate_theme(theme)
    w, h = size
    if w < 256 or h < 256 or abs(w / h - .75) >= .01:
        raise ValueError("Use the actual native 3:4 canvas")
    scale = w / 1080
    overlay = Image.new("RGBA", size)
    draw = ImageDraw.Draw(overlay)
    ink, accent = _rgb(theme["text_color"]), _rgb(theme["accent_color"])
    collector = theme.get("layout") == "collector"
    inset = max(3, round(w * (.0167 if collector else .027)))
    stroke = max(1, round(scale)) if collector else 0
    # A theme-derived stroke works on both light and dark art; artwork itself stays untouched.
    stroke_ink = _rgb(theme["scrim_color"], 195)
    if theme["frame"] != "none":
        draw.rounded_rectangle((inset, inset, w - inset, h - inset), radius=max(3, round(w * .018)),
                               outline=accent, width=max(1, round(2 * scale)))
        if theme["frame"] == "double":
            delta = max(2, round(8 * scale))
            draw.rounded_rectangle((inset + delta, inset + delta, w - inset - delta, h - inset - delta),
                                   radius=max(2, round(w * .014)), outline=(*accent[:3], 140), width=1)
        if collector:
            # Fine corner engraving is deterministic decoration, never generated image content.
            arm = round(48 * scale)
            for x, sx in ((inset + 7 * scale, 1), (w - inset - 7 * scale, -1)):
                for y, sy in ((inset + 7 * scale, 1), (h - inset - 7 * scale, -1)):
                    draw.line([(x, y + sy * arm), (x, y), (x + sx * arm, y)], fill=accent, width=max(1, round(scale)))
                    draw.line([(x, y + sy * arm), (x + sx * arm, y)], fill=(*accent[:3], 150), width=max(1, round(scale)))
                    cx, cy, r = x + sx * 17 * scale, y + sy * 17 * scale, 5 * scale
                    draw.polygon([(cx, cy-r), (cx+r, cy), (cx, cy+r), (cx-r, cy)], outline=accent)
    boxes = []

    def face(points):
        return ImageFont.truetype(str(font), max(3, round(points * scale)))

    def width(text, f):
        return draw.textlength(text, font=f)

    def wrapped(text, f, maximum):
        lines, line = [], ""
        for char in str(text):
            if char == "\n":
                lines.append(line); line = ""; continue
            if line and width(line + char, f) > maximum:
                lines.append(line); line = char
            else:
                line += char
        if line or not lines:
            lines.append(line)
        return lines

    def place(field, lines, f, x, y, color, centered=True):
        height = 0
        for line in lines:
            bounds = draw.textbbox((0, 0), line or " ", font=f, anchor="lt")
            line_height = max(1, bounds[3] - bounds[1])
            left = x - width(line, f) / 2 if centered else x
            draw.text((left, y), line, font=f, anchor="lt", fill=color,
                      stroke_width=stroke, stroke_fill=stroke_ink)
            actual = draw.textbbox((left, y), line, font=f, anchor="lt", stroke_width=stroke)
            if not (inset <= actual[0] and actual[2] <= w - inset and inset <= actual[1] and actual[3] <= h - inset):
                raise ValueError("Typography would leave the safe canvas: " + field)
            boxes.append({"field": field, "box": [round(v, 2) for v in actual]})
            step = line_height + max(2, round(5 * scale))
            y += step; height += step
        return height

    # Header columns are measured independently: long author names shrink rather than collide with SSR.
    header_y = h * .045
    place("rarity", ["SSR"], face(86 if collector else 62), w * .055, header_y, accent, False)
    author = str(data["summarizer"]) + " 眼中的你"
    points = 23
    while width(author, face(points)) > w * .54 and points > 10:
        points -= 1
    if width(author, face(points)) > w * .54:
        raise ValueError("Summarizer label cannot fit without clipping")
    f = face(points)
    place("summarizer", [author], f, w * .94 - width(author, f), header_y + h * .01, ink, False)

    top = float(theme.get("footer_top", .76))
    regions = [r for r in (composition or {}).get("text_safe_regions", [])
               if r[0] <= .2 and r[2] >= .8 and r[1] >= .6 and r[3] >= .98]
    footer_width = .83
    if regions:
        region = min(regions, key=lambda r: r[1])
        top = max(top, region[1] + .005)
        footer_width = min(footer_width, 2 * min(.5 - region[0], region[2] - .5))
    bottom = .967 if collector else .955
    if bottom - top < .11:
        raise ValueError("Actual composition leaves too little space for the unchanged card text")
    scrim_start = max(.62, top - (.09 if collector else .06))
    for y in range(round(h * scrim_start), h - inset):
        amount = (y / h - scrim_start) / (1 - scrim_start)
        opacity = max(0, min(theme["scrim_opacity"], round(amount * theme["scrim_opacity"])))
        draw.line((inset + 2, y, w - inset - 2, y), fill=_rgb(theme["scrim_color"], opacity))
    card = data["card"]
    fields = [
        ("title", card["title"], 90 if collector else 68, 2, accent),
        ("english_title", card["english_title"], 25 if collector else 24, 2, accent),
        ("keywords", " · ".join(card["keywords"]), 25 if collector else 24, 2, ink),
        ("tagline", card["tagline"], 23, 2, ink),
        ("edition", "T W I N L I G H T  ·  1 / 1", 17, 1, accent),
    ]
    measured = None
    # V10-like collector hierarchy uses spacious, fixed rhythm when wording fits.
    # It may shrink typography for long frozen wording, but never silently edits it.
    collector_offsets = (0, .080, .130, .175, .210)
    collector_height = .232
    for percent in range(100, 44, -2):
        rows, total = [], 0
        for name, text, points, max_lines, color in fields:
            f = face(points * percent / 100)
            lines = wrapped(text, f, w * footer_width)
            if len(lines) > max_lines:
                break
            heights = [max(1, draw.textbbox((0, 0), line or " ", font=f, anchor="lt")[3]) + max(2, round(5 * scale)) for line in lines]
            step = sum(heights) + max(3, round(10 * scale))
            rows.append((name, lines, f, color, step)); total += step
        else:
            if collector:
                rhythm = min(1, (bottom - top) / collector_height)
                fits = True
                for index, row in enumerate(rows):
                    start = collector_offsets[index] * rhythm * h
                    limit = collector_offsets[index + 1] * rhythm * h if index < 4 else (bottom - top) * h
                    actual_height = row[4] - max(3, round(10 * scale))
                    if start + actual_height > limit - max(1, round(2 * scale)):
                        fits = False; break
                if fits:
                    measured = rows; break
            elif total <= (bottom - top) * h:
                measured = rows; break
    if measured is None:
        raise ValueError("Current title/tagline cannot fit safely; change the composition, not the frozen wording")
    y = top * h
    for index, (name, lines, f, color, step) in enumerate(measured):
        if collector:
            y = (top + collector_offsets[index] * rhythm) * h
        labels = [str(x) for x in card['keywords']] if name == 'keywords' and collector and len(lines) == 1 else []
        pill_widths = [width(label, f) + 32 * scale for label in labels]
        gap = 22 * scale
        pill_total = sum(pill_widths) + gap * max(0, len(labels) - 1)
        if labels and pill_total <= w * footer_width:
            left = (w - pill_total) / 2
            for label, pill_width in zip(labels, pill_widths):
                label_height = draw.textbbox((0, 0), label, font=f, anchor='lt')[3]
                draw.rounded_rectangle((left, y - 7*scale, left + pill_width, y + label_height + 7*scale),
                                       radius=12*scale, outline=(*accent[:3], 170),
                                       fill=_rgb(theme['scrim_color'], 80), width=max(1, round(scale)))
                place(name, [label], f, left + pill_width / 2, y, color)
                left += pill_width + gap
        else:
            place(name, lines, f, w / 2, y, color)
        y += step
    if collector:
        # Small flanking ornaments occupy measured gaps, not the title or face.
        title_boxes = [b['box'] for b in boxes if b['field'] == 'title']
        if len(title_boxes) == 1:
            l, t, r, b = title_boxes[0]
            radius = 6 * scale
            for cx in (l - 24 * scale, r + 24 * scale):
                if inset + radius < cx < w - inset - radius:
                    cy = (t + b) / 2
                    draw.polygon([(cx,cy-radius),(cx+radius*.4,cy),(cx,cy+radius),(cx-radius*.4,cy)],fill=accent)
        edition = next(b['box'] for b in boxes if b['field'] == 'edition')
        cy = edition[1] - 12 * scale
        draw.line((w*.33, cy, w*.47, cy), fill=(*accent[:3], 150), width=max(1, round(scale)))
        draw.line((w*.53, cy, w*.67, cy), fill=(*accent[:3], 150), width=max(1, round(scale)))
        r = 6 * scale
        draw.polygon([(w*.5,cy-r),(w*.5+r*.5,cy),(w*.5,cy+r),(w*.5-r*.5,cy)],fill=accent)
    for index, a in enumerate(boxes):
        for b in boxes[index + 1:]:
            l, t, r, bot = a["box"]; x, yy, xx, y2 = b["box"]
            if min(r, xx) > max(l, x) and min(bot, y2) > max(t, yy):
                raise ValueError("Text overlaps: " + a["field"] + " / " + b["field"])
    return overlay, {"canvas": [w, h], "theme": theme, "boxes": boxes, "overlap": False,
                     "layout_profile": "collector-v10-hierarchy" if collector else "measured",
                     "scope": "Measured text geometry only; visual readability still needs inspection."}
