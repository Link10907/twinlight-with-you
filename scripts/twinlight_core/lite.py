"""Lite mode: one small JSON per person, rendered by the fixed template.

The validator interprets schemas/lite.schema.json with the same rules and the
same Chinese messages as assets/lite/lite.js, so an agent CLI and the browser
viewer report identical (path, code, message) triples. tests/test_lite_parity.py
holds both implementations to that.
"""
from __future__ import annotations
import json
import re
from typing import Any
from .common import ROOT, digest, load, text_hash
from .layout import layout_from_spec

FORMAT = "lite-1"
SCHEMA_PATH = ROOT / "schemas" / "lite.schema.json"
TRIM = re.compile(r"^[ \t\r\n\u00a0\u3000]+|[ \t\r\n\u00a0\u3000]+$")
FENCE = re.compile(r"```[ \t]*(?:json|JSON|json5)?[ \t]*\r?\n([\s\S]*?)\r?\n?```")
TYPE_CN = {"object": "对象 {…}", "array": "列表 […]", "string": "文字"}
PRIVACY = [
    ("私钥", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.ASCII)),
    ("GitHub 令牌", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b", re.ASCII)),
    ("API 密钥", re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b", re.ASCII)),
    ("AWS 密钥", re.compile(r"\bAKIA[A-Z0-9]{16}\b", re.ASCII)),
    ("邮箱地址", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.ASCII)),
    ("手机号", re.compile(r"(?<!\d)(?:\+86[- ]?)?1[3-9]\d{9}(?!\d)", re.ASCII)),
]
BASIS = {
    "often": ("常聊", "你的 AI：你们经常聊到这个。"),
    "once": ("提过", "你的 AI：你提到过这个。"),
    "inferred": ("AI 推测", "你的 AI 根据整体印象推测，未必准确。"),
}
BASIS_WEIGHT = {"often": 3, "once": 1, "inferred": 1}
PROVIDERS = [("openai", ("gpt", "chatgpt", "openai")), ("anthropic", ("claude", "anthropic")),
             ("google", ("gemini", "google")), ("deepseek", ("deepseek",)), ("qwen", ("qwen", "通义")),
             ("moonshot", ("kimi", "moonshot")), ("bytedance", ("doubao", "豆包"))]
UNKNOWN_AUTHOR = {"", "未知", "unknown", "ai", "不知道", "不确定", "不清楚", "n/a", "none", "ai助手", "ai 助手", "assistant", "ai assistant"}


def schema() -> dict:
    return load(SCHEMA_PATH)


def _err(path: str, code: str, message: str) -> dict:
    return {"path": path or "$", "code": code, "message": message}


def strip_trailing_commas(text: str) -> str:
    out, in_str, esc, i = [], False, False, 0
    while i < len(text):
        c = text[i]
        if in_str:
            out.append(c)
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': in_str = False
        elif c == '"':
            in_str = True; out.append(c)
        elif c == ",":
            j = i + 1
            while j < len(text) and text[j] in " \t\r\n": j += 1
            if j >= len(text) or text[j] not in "}]": out.append(c)
        else:
            out.append(c)
        i += 1
    return "".join(out)


def parse(text: str) -> tuple[Any, list[str], list[dict]]:
    """Lenient only for wrappers chat models add; never guesses content."""
    warnings: list[str] = []
    t = text.lstrip("\ufeff").strip()
    m = FENCE.search(t)
    if m:
        t = m.group(1).strip(); warnings.append("去掉了 ``` 代码块标记")
    elif not t.startswith("{") and "{" in t and "}" in t:
        t = t[t.index("{"):t.rindex("}") + 1]; warnings.append("去掉了 JSON 前后的说明文字")
    def reject_constant(c):
        raise ValueError(c)
    def loads(s):
        return json.loads(s, parse_constant=reject_constant)
    try:
        return loads(t), warnings, []
    except ValueError as first:
        fixed = strip_trailing_commas(t)
        if fixed != t:
            try:
                data = loads(fixed); warnings.append("去掉了 } 或 ] 前多余的逗号")
                return data, warnings, []
            except ValueError:
                pass
        hint = "；检测到中文引号 “ ” 被当作 JSON 引号，请改成英文双引号 \"" if re.search(r"[“”]\s*:|:\s*[“”]", t) else ""
        where = f"（第 {first.lineno} 行第 {first.colno} 列附近）" if hasattr(first, "lineno") else ""
        return None, warnings, [_err("$", "parse_error", f"不是有效的 JSON{where}{hint}")]


def normalize(value: Any) -> Any:
    if isinstance(value, str): return TRIM.sub("", value)
    if isinstance(value, list): return [normalize(v) for v in value]
    if isinstance(value, dict): return {k: normalize(v) for k, v in value.items()}
    return value


def _type_ok(node: Any, kind: str) -> bool:
    if kind == "object": return isinstance(node, dict)
    if kind == "array": return isinstance(node, list)
    if kind == "string": return isinstance(node, str)
    return True


def _walk(node: Any, sch: dict, path: str, title: str, errors: list[dict]) -> None:
    title = sch.get("title", title)
    if "const" in sch:
        if node != sch["const"] or not isinstance(node, type(sch["const"])):
            errors.append(_err(path, "bad_value", f"「{title}」应为 \"{sch['const']}\""))
        return
    if "enum" in sch:
        if not isinstance(node, str) or node not in sch["enum"]:
            errors.append(_err(path, "bad_value", f"「{title}」只能是 " + " / ".join(sch["enum"])))
        return
    kind = sch.get("type")
    if kind and not _type_ok(node, kind):
        errors.append(_err(path, "wrong_type", f"「{title}」应为{TYPE_CN[kind]}")); return
    if kind == "string":
        n = len(node)
        if n < sch.get("minLength", 0):
            errors.append(_err(path, "empty", f"「{title}」不能为空") if n == 0 else
                          _err(path, "too_short", f"「{title}」至少 {sch['minLength']} 字，现在 {n} 字"))
        elif n > sch.get("maxLength", n):
            errors.append(_err(path, "too_long", f"「{title}」最多 {sch['maxLength']} 字，现在 {n} 字"))
        elif "pattern" in sch and not re.search(sch["pattern"], node):
            errors.append(_err(path, "bad_format", f"「{title}」{sch.get('x-message', '格式不对')}"))
    elif kind == "array":
        n = len(node)
        if n < sch.get("minItems", 0):
            errors.append(_err(path, "too_few", f"「{title}」至少 {sch['minItems']} 项，现在 {n} 项"))
        elif n > sch.get("maxItems", n):
            errors.append(_err(path, "too_many", f"「{title}」最多 {sch['maxItems']} 项，现在 {n} 项"))
        for i, item in enumerate(node):
            _walk(item, sch["items"], f"{path}[{i}]", title, errors)
    elif kind == "object":
        props = sch.get("properties", {})
        prefix = path + "." if path else ""
        for key in sch.get("required", []):
            if key not in node:
                errors.append(_err(prefix + key, "missing", f"缺少「{props[key].get('title', key)}」"))
        if sch.get("additionalProperties") is False:
            for key in node:
                if key not in props:
                    errors.append(_err(prefix + key, "unknown_field", f"多了不认识的字段「{key}」，请删除"))
        for key, sub in props.items():
            if key in node:
                _walk(node[key], sub, prefix + key, sub.get("title", key), errors)


def _semantic(data: dict, errors: list[dict]) -> None:
    themes = data.get("themes")
    if isinstance(themes, list):
        seen: dict[str, str] = {}
        for i, theme in enumerate(themes):
            if not isinstance(theme, dict): continue
            label = theme.get("label")
            if isinstance(label, str) and label:
                if label in seen:
                    errors.append(_err(f"themes[{i}].label", "duplicate", f"「主题名」与 {seen[label]} 重复"))
                else:
                    seen[label] = f"themes[{i}].label"
            topics = theme.get("topics")
            if isinstance(topics, list):
                tseen: dict[str, str] = {}
                for j, topic in enumerate(topics):
                    tl = topic.get("label") if isinstance(topic, dict) else None
                    if isinstance(tl, str) and tl:
                        p = f"themes[{i}].topics[{j}].label"
                        if tl in tseen: errors.append(_err(p, "duplicate", f"「话题名」与 {tseen[tl]} 重复"))
                        else: tseen[tl] = p
    def walk(x, path):
        if isinstance(x, str):
            for kind, pattern in PRIVACY:
                if pattern.search(x):
                    errors.append(_err(path, "privacy", f"疑似包含{kind}，请删除")); break
        elif isinstance(x, list):
            for i, v in enumerate(x): walk(v, f"{path}[{i}]")
        elif isinstance(x, dict):
            for k, v in x.items(): walk(v, f"{path}.{k}" if path else k)
    walk(data, "")


def validate(data: Any) -> list[dict]:
    errors: list[dict] = []
    _walk(data, schema(), "", "Twinlight JSON", errors)
    if isinstance(data, dict): _semantic(data, errors)
    return errors


def check_text(text: str) -> dict:
    """Parse + normalize + validate. Returns a report; `data` is set only when valid."""
    data, warnings, errors = parse(text)
    if not errors:
        data = normalize(data)
        errors = validate(data)
    ok = not errors
    return {"ok": ok, "errors": errors, "warnings": warnings, "data": data if ok else None,
            "stats": stats(data) if ok else None}


def stats(data: dict) -> dict:
    return {"themes": len(data["themes"]), "topics": sum(len(t["topics"]) for t in data["themes"]),
            "keywords": len(data["card"]["keywords"])}


def repair_prompt(errors: list[dict]) -> str:
    lines = [f"你输出的 Twinlight JSON 有 {len(errors)} 处问题："]
    lines += [f"{i}. {e['path']}：{e['message']}" for i, e in enumerate(errors, 1)]
    lines += ["请只修改这些位置，其余内容保持不变。重新输出完整的 JSON，放在一个 ```json 代码块里，代码块外不要写别的内容。"]
    return "\n".join(lines)


def provider_of(summarizer: str) -> tuple[str, str | None]:
    s = summarizer.strip()
    if s.lower() in UNKNOWN_AUTHOR: return "unknown", None
    low = s.lower()
    for provider, keys in PROVIDERS:
        if any(k in low for k in keys): return provider, s
    return "other", s


def owner_id(name: str) -> str:
    return "lite-" + text_hash(name)[:12]


def persona_digest(data: dict) -> str:
    """Shared card/content binding; independent of galaxy fields and timestamps."""
    provider, display = provider_of(data["summarizer"])
    author = {"provider": provider, "display_name": display, "attribution_source": "ai_self_reported"}
    return digest({"owner": owner_id(data["name"]), "card": data["card"], "author": author})


def to_profile(data: dict, *, generated_at: str, art_status: str = "placeholder", confirmed: bool = False,
               ai_history: list | None = None, art_mode: str | None = None) -> dict:
    """Map a VALID lite JSON to the fixed template's profile contract."""
    oid = owner_id(data["name"])
    art_mode = art_mode or ("static" if art_status == "static" else "placeholder" if art_status == "placeholder" else "layered")
    chapters, spec = [], []
    for i, theme in enumerate(data["themes"], 1):
        tid = f"theme-{i}"
        topics = []
        for j, topic in enumerate(theme["topics"], 1):
            status, provenance = BASIS[topic["basis"]]
            topics.append({"id": f"topic-{j}", "name": topic["label"], "title": topic["summary"],
                           "body": [topic["summary"]], "quote": None, "status": status, "provenance": provenance})
        spec.append((tid, [(f"topic-{j}", BASIS_WEIGHT[t["basis"]]) for j, t in enumerate(theme["topics"], 1)]))
        chapters.append({"id": tid, "label": theme["label"], "english": theme["english"], "period": "AI 印象 · 未标注日期",
            "headline": theme["headline"], "story": list(theme["story"]), "reflection": theme["reflection"], "changes": [],
            "tags": [t["name"] for t in topics[:5]], "transition": "循着微光，走向下一段记录。", "signature": theme["headline"],
            "quotes": [], "topics": topics, "letterClosing": "这些印象，是来路，不是定论。",
            "collaboration": "由你的 AI 根据对你的了解写下。", "companion_year": None, "ai_context_ids": [],
            "ai_trace": {"product": "未确认", "model_id": None, "reported_name": None, "status": "unknown",
                         "source": "精简模式不绑定消息级模型证据", "note": "不由日期、词语或总结者反推历史模型。"}})
    provider, display = provider_of(data["summarizer"])
    meta = {"provider": provider, "display_name": display, "model": None, "generated_at": generated_at,
            "attribution_source": "ai_self_reported"}
    card = data["card"]
    persona = {"version": "1.0", "name": data["name"], "rarity": "SSR", "title": card["title"],
               "english_title": card["english_title"], "edition": generated_at[:7].replace("-", "."),
               "keywords": list(card["keywords"]), "line": card["tagline"], "reflection": card["reflection"],
               "evidence": [{"title": t["label"], "text": t["headline"][:60]} for t in data["themes"][:3]],
               "art_type": ("静态原型插画：尚未完成独立分层" if art_status == "static" else
                            "原生独立分层插画" if art_status != "placeholder" else "占位卡面：还没有放入你的插画"),
               "disclaimer": "本卡是 AI 对你的创作性印象，不是人格诊断或能力排名。每张卡都是 SSR。",
               "summarizer": meta, "content_ready": True, "art_status": art_status, "art_mode": art_mode}
    # Binding describes the actual person/card, independent of build timestamps.
    persona["persona_digest"] = persona_digest(data)
    layout = layout_from_spec(oid, spec)
    profile = {"version": "1.0", "mode": "lite", "name": data["name"], "owner_id": oid,
               "intro": data.get("intro") or "每一颗微光，都有来处。", "chapters": chapters, "summary_meta": meta,
               "ai_history": ai_history if ai_history is not None else load(ROOT / "assets/ai-history.json")["events"],
               "ai_usage": [], "layout": layout, "persona": persona,
               "coverage": {"scope": "ai_impression", "start": None, "end": None, "account_history_complete": False,
                            "description": "基于你的 AI 对你的印象（记忆与对话），不是逐条核对的聊天记录。"},
               "release": {"draft": not confirmed, "share_allowed": bool(confirmed)}}
    profile["content_digest"] = digest({"owner_id": oid, "chapters": chapters, "summary_meta": meta,
                                        "persona_digest": persona["persona_digest"]})
    return profile


def preview_markdown(data: dict) -> str:
    """Everything that will appear on the page, for the person's review."""
    out = [f"# {data['name']} 的 Twinlight（待你确认）", "", f"总结者：{data['summarizer']}", ""]
    if data.get("intro"): out += [f"开场白：{data['intro']}", ""]
    for i, t in enumerate(data["themes"], 1):
        out += [f"## 主题 {i} · {t['label']}（{t['english']}）", f"**{t['headline']}**", "", *t["story"], "", f"> {t['reflection']}", ""]
        for p in t["topics"]:
            out.append(f"- {p['label']}【{BASIS[p['basis']][0]}】：{p['summary']}")
        out.append("")
    c = data["card"]
    out += [f"## SSR 卡片 · {c['title']}（{c['english_title']}）", f"关键词：{' · '.join(c['keywords'])}",
            f"标语：{c['tagline']}", f"背面寄语：{c['reflection']}", ""]
    if c.get("art_prompt"):
        out += [f"角色设定（生图用）：{c['art_prompt']}", ""]
    return "\n".join(out)


# Native-layer prompts live with the reusable per-person card specification.
# Kept as a public alias for the CLI and browser contract.
from .cardgen import art_prompts  # noqa: E402,F401
