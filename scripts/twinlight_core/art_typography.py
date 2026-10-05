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
    inset = max(3, round(w * .027))
    if theme["frame"] != "none":
        draw.rounded_rectangle((inset, inset, w - inset, h - inset), radius=max(3, round(w * .018)),
                               outline=accent, width=max(1, round(2 * scale)))
        if theme["frame"] == "double":
            delta = max(2, round(8 * scale))
            draw.rounded_rectangle((inset + delta, inset + delta, w - inset - delta, h - inset - delta),
                                   radius=max(2, round(w * .014)), outline=accent, width=1)
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
            draw.text((left, y), line, font=f, anchor="lt", fill=color)
            actual = draw.textbbox((left, y), line, font=f, anchor="lt")
            if not (inset <= actual[0] and actual[2] <= w - inset and inset <= actual[1] and actual[3] <= h - inset):
                raise ValueError("Typography would leave the safe canvas: " + field)
            boxes.append({"field": field, "box": [round(v, 2) for v in actual]})
            step = line_height + max(2, round(5 * scale))
            y += step; height += step
        return height

    # Header columns are measured independently: long author names shrink rather than collide with SSR.
    header_y = h * .045
    place("rarity", ["SSR"], face(62), w * .06, header_y, accent, False)
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
    bottom = .955
    if bottom - top < .11:
        raise ValueError("Actual composition leaves too little space for the unchanged card text")
    scrim_start = max(.62, top - .06)
    for y in range(round(h * scrim_start), h - inset):
        amount = (y / h - scrim_start) / (1 - scrim_start)
        opacity = max(0, min(theme["scrim_opacity"], round(amount * theme["scrim_opacity"])))
        draw.line((inset + 2, y, w - inset - 2, y), fill=_rgb(theme["scrim_color"], opacity))
    card = data["card"]
    fields = [
        ("title", card["title"], 68, 2, accent),
        ("english_title", card["english_title"], 24, 2, accent),
        ("keywords", " · ".join(card["keywords"]), 24, 2, ink),
        ("tagline", card["tagline"], 23, 2, ink),
        ("edition", "T W I N L I G H T  ·  1 / 1", 17, 1, accent),
    ]
    measured = None
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
            if total <= (bottom - top) * h:
                measured = rows; break
    if measured is None:
        raise ValueError("Current title/tagline cannot fit safely; change the composition, not the frozen wording")
    y = top * h
    for name, lines, f, color, step in measured:
        place(name, lines, f, w / 2, y, color)
        y += step
    for index, a in enumerate(boxes):
        for b in boxes[index + 1:]:
            l, t, r, bot = a["box"]; x, yy, xx, y2 = b["box"]
            if min(r, xx) > max(l, x) and min(bot, y2) > max(t, yy):
                raise ValueError("Text overlaps: " + a["field"] + " / " + b["field"])
    return overlay, {"canvas": [w, h], "theme": theme, "boxes": boxes, "overlap": False,
                     "scope": "Measured text geometry only; visual readability still needs inspection."}
