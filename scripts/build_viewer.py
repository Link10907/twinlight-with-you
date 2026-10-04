#!/usr/bin/env python3
"""Build the self-contained lite viewer (GitHub Pages entry point). No network at runtime."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twinlight_core.common import ROOT, load  # noqa: E402
from twinlight_core.site import LITE_DEPTHS, template_parts, uri  # noqa: E402

DEFAULT_BASE = "https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/"
VIEWER = ROOT / "assets" / "viewer"


def bundle() -> dict:
    html_t, _ = template_parts()
    # Keep maintained procedural fixtures byte-stable across Pillow/zlib platforms.
    # Neither asset carries a biography or a person's illustration.
    placeholder = {"subject": uri(VIEWER / 'placeholder-subject.png')}
    return {"version": "lite-1", "schema": load(ROOT / "schemas" / "lite.schema.json"), "template": html_t,
            "aiHistory": load(ROOT / "assets" / "ai-history.json")["events"], "placeholder": placeholder,
            "clear": uri(VIEWER / 'clear.png'),
            "depths": {k: v for k, v in LITE_DEPTHS.items()},
            "prompt": instruction_bundle(('PROMPT.md', 'AGENT.md', 'prompts/html-build.md',
                                           'CARD.md', 'prompts/card-generation.md')),
            "cardPrompt": instruction_bundle(('CARD.md', 'prompts/card-generation.md',
                                               'references/art-direction.md')),
            "example": (ROOT / "examples" / "lite" / "example.json").read_text(encoding="utf-8")}


def instruction_bundle(paths: tuple[str, ...]) -> str:
    """Copy the actual module instructions; assets still require the complete package."""
    return '\n\n'.join('<!-- ' + path + ' -->\n' + (ROOT / path).read_text(encoding='utf-8')
                        for path in paths)


def script_json(value) -> str:
    # Not canonical(): validators report errors in schema property order, so key order must survive.
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    for a, b in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        text = text.replace(a, b)
    return text


def build(out: Path, base: str) -> dict:
    if out.exists() and any(p.name not in {'index.html', 'prompt.md', 'card.md', 'agent.md', 'example.json', '.nojekyll'} for p in out.iterdir()):
        raise ValueError('查看器输出目录含其他文件，请选择空目录，避免把旧的私人展示一起发布。')
    base = base if base.endswith("/") else base + "/"
    scripts = {"LITE_JS": (ROOT / "assets" / "lite" / "lite.js").read_text(encoding="utf-8"),
               "VIEWER_JS": (VIEWER / "viewer.js").read_text(encoding="utf-8")}
    for name, code in scripts.items():
        if re.search(r"</script", code, re.I):
            raise ValueError(f"{name} must not contain a closing script tag")
    raw_source = base.startswith('https://raw.githubusercontent.com/')
    values = {**scripts, "VIEWER_CSS": (VIEWER / "viewer.css").read_text(encoding="utf-8"),
              "BUNDLE": script_json(bundle()), "PROMPT_URL": base + ('PROMPT.md' if raw_source else 'prompt.md'),
              "AGENT_URL": base + ('AGENT.md' if raw_source else 'agent.md'),
              "CARD_URL": base + ('CARD.md' if raw_source else 'card.md'),
              }
    shell = (VIEWER / "index.html").read_text(encoding="utf-8")
    html = re.sub(r"__(" + "|".join(values) + r")__", lambda m: values[m.group(1)], shell)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    shutil.copyfile(ROOT / "PROMPT.md", out / "prompt.md")
    shutil.copyfile(ROOT / "CARD.md", out / "card.md")
    shutil.copyfile(ROOT / "AGENT.md", out / "agent.md")
    shutil.copyfile(ROOT / "examples" / "lite" / "example.json", out / "example.json")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    data = html.encode("utf-8")
    return {"ok": True, "out": str(out / "index.html"), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "files": sorted(p.name for p in out.iterdir())}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT / "outputs" / "viewer")
    p.add_argument("--base-url", default=DEFAULT_BASE, help="Public URL where prompt.md / agent.md are served")
    a = p.parse_args()
    print(json.dumps(build(a.out, a.base_url), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
