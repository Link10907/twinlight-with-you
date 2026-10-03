"""Self-contained visual run report. Local only: it contains the person's text."""
from __future__ import annotations
import base64
import html
import io
from pathlib import Path
from PIL import Image
from .common import load
from . import lite
from .state import STAGES, STAGE_CN, paths, art_inputs

STATUS = {"passed": ("通过", "ok"), "skipped": ("未验证", "warn"), "failed": ("未通过", "bad"),
          "blocked": ("已阻塞", "bad"), "pending": ("未开始", "idle")}
SHOTS = [("home", "桌面 · 首页"), ("detail", "桌面 · 主题详情"), ("card", "桌面 · SSR 卡"),
         ("mobile-home", "手机 · 首页"), ("mobile-card", "手机 · SSR 卡")]
CSS = """
:root{color-scheme:dark;--bg:#0b111b;--panel:#121b29;--line:#26344a;--text:#e8e2d4;--dim:#93a1b5;--ok:#5fd39a;--warn:#e8c46a;--bad:#ff7b72;--idle:#6b7a90;--gold:#e6cb99}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.7 -apple-system,BlinkMacSystemFont,'PingFang SC','Noto Sans CJK SC','Microsoft YaHei',sans-serif}
main{max-width:1080px;margin:0 auto;padding:32px 20px 80px}h1{font-size:26px;margin:0 0 4px;letter-spacing:1px}h2{font-size:17px;margin:36px 0 12px;color:var(--gold);letter-spacing:1px}
.sub{color:var(--dim);margin:0 0 20px}.badge{display:inline-block;padding:2px 10px;border-radius:99px;font-size:12px;font-weight:600}
.ok{background:#173a2a;color:var(--ok)}.warn{background:#3b3115;color:var(--warn)}.bad{background:#3e1b1b;color:var(--bad)}.idle{background:#1b2332;color:var(--idle)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:10px 0}
.timeline{display:grid;grid-template-columns:repeat(6,1fr);gap:8px}.step{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px}
.step b{display:block;font-size:13px;margin:6px 0 2px}.step small{color:var(--dim);display:block}.step.ok{border-color:#2d6b4c}.step.warn{border-color:#7a6326}.step.bad{border-color:#7b3434}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{border-bottom:1px solid var(--line);padding:7px 6px;text-align:left;vertical-align:top}th{color:var(--dim);font-weight:500}
code{background:#0a0f17;border:1px solid var(--line);border-radius:6px;padding:1px 5px;font-size:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}figure{margin:0}figure img{width:100%;border-radius:10px;border:1px solid var(--line);display:block}
figcaption{color:var(--dim);font-size:12px;margin-top:6px}.card{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap}.card img{width:240px;border-radius:14px;border:1px solid var(--line)}
.err{color:var(--bad)}.dim{color:var(--dim)}ul{margin:6px 0;padding-left:20px}.basis{font-size:11px;color:var(--dim);border:1px solid var(--line);border-radius:6px;padding:0 5px;margin-left:6px}
@media(max-width:760px){.timeline{grid-template-columns:repeat(2,1fr)}}
"""


def _thumb(path: Path, width: int) -> str:
    with Image.open(path) as im:
        im = im.convert("RGB"); im.thumbnail((width, width * 3))
        s = io.BytesIO(); im.save(s, format="JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(s.getvalue()).decode("ascii")


def e(x) -> str:
    return html.escape(str(x), quote=True)


def write_report(ws: Path, state: dict | None = None) -> Path:
    p = paths(ws)
    state = state or load(p["state"])
    st = state["stages"]
    statuses = [st[s]["status"] for s in STAGES if s != "report"]
    if all(x == "passed" for x in statuses): overall = ("全部通过", "ok")
    elif all(x in ("passed", "skipped") for x in statuses): overall = ("通过，含未验证项", "warn")
    elif any(x in ("failed", "blocked") for x in statuses): overall = ("有未通过的阶段", "bad")
    else: overall = ("尚未完成", "idle")
    out = [f"<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
           f"<title>Twinlight 运行报告</title><style>{CSS}</style><main>",
           f"<h1>Twinlight 运行报告 <span class='badge {overall[1]}'>{overall[0]}</span></h1>",
           f"<p class='sub'>工作目录 <code>{e(p['ws'])}</code> · 创建于 {e(state['created_at'])} · 本报告含个人文案，只保存在本地。</p>"]

    out.append("<h2>流程门禁</h2><div class='timeline'>")
    for s in STAGES:
        info = st[s]; label, cls = STATUS.get(info["status"], (info["status"], "idle"))
        if s == "report" and info["status"] == "pending": label, cls = "本报告", "ok"
        tries = len(info.get("log", []))
        out.append(f"<div class='step {cls}'><span class='badge {cls}'>{label}</span><b>{e(STAGE_CN[s])}</b>"
                   f"<small>检查 {tries} 次{' · ' + e(info['updated_at']) if info['updated_at'] else ''}</small></div>")
    out.append("</div>")

    log = st["profile"].get("log", [])
    out.append("<h2>JSON 校验与修复过程</h2><div class='panel'>")
    if log:
        out.append("<table><tr><th>第几次</th><th>时间</th><th>结果</th></tr>")
        for i, item in enumerate(log, 1):
            res = "通过" if item["result"] == "passed" else f"<span class='err'>{item['errors']} 处问题</span>"
            out.append(f"<tr><td>{i}</td><td>{e(item['at'])}</td><td>{res}</td></tr>")
        out.append("</table>")
    else:
        out.append("<p class='dim'>还没有校验记录。</p>")
    if st["profile"]["errors"]:
        out.append("<p class='err'>当前未解决的问题：</p><ul>" + "".join(f"<li><code>{e(x['path'])}</code> {e(x['message'])}</li>" for x in st["profile"]["errors"]) + "</ul>")
    if st["profile"]["warnings"]:
        out.append("<p class='dim'>自动修正：" + "；".join(e(w) for w in st["profile"]["warnings"]) + "</p>")
    out.append("</div>")

    if st["profile"]["status"] == "passed" and p["profile"].is_file():
        data = lite.check_text(p["profile"].read_text(encoding="utf-8"))["data"]
        if data:
            stats = st["profile"]["detail"].get("stats", {})
            out.append(f"<h2>内容预览 <span class='dim' style='font-size:13px'>{stats.get('themes')} 个主题 · {stats.get('topics')} 颗行星 · 总结者：{e(data['summarizer'])}</span></h2>")
            review = st["review"]
            if review["status"] == "passed":
                out.append(f"<div class='panel'>用户确认：<b>“{e(review['detail'].get('user_reply'))}”</b> <span class='dim'>{e(review['updated_at'])}</span></div>")
            else:
                out.append("<div class='panel err'>用户尚未确认这些文案。</div>")
            out.append("<div class='panel'><table><tr><th style='width:22%'>主题</th><th>标题与话题</th></tr>")
            for t in data["themes"]:
                topics = "".join(f"<li>{e(x['label'])}<span class='basis'>{e(lite.BASIS[x['basis']][0])}</span> {e(x['summary'])}</li>" for x in t["topics"])
                out.append(f"<tr><td><b>{e(t['label'])}</b><br><span class='dim'>{e(t['english'])}</span></td><td>{e(t['headline'])}<ul>{topics}</ul></td></tr>")
            out.append("</table></div>")
            c = data["card"]
            art = st["art"]["detail"]
            found = art_inputs(p) if st["art"]["status"] == "passed" else {}
            img = next((found[k] for k in ("portrait", "character") if k in found), None)
            out.append("<h2>SSR 卡片</h2><div class='panel card'>")
            if img: out.append(f"<img alt='卡图' src='{_thumb(img, 480)}'>")
            out.append(f"<div><p><b style='font-size:20px'>{e(c['title'])}</b> <span class='dim'>{e(c['english_title'])}</span></p>"
                       f"<p>{' · '.join(e(k) for k in c['keywords'])}</p><p>{e(c['tagline'])}</p><p class='dim'>{e(c['reflection'])}</p>"
                       f"<p>卡图状态：<span class='badge {'ok' if art.get('art_status') == 'generated' else 'warn'}'>{'已放入插画' if art.get('art_status') == 'generated' else '占位卡面' if art.get('art_status') else '未检查'}</span></p></div></div>")

    b = st["build"]["detail"]
    if b:
        out.append(f"<h2>构建结果</h2><div class='panel'><table><tr><th>文件</th><td><code>{e(b.get('out'))}</code></td></tr>"
                   f"<tr><th>大小</th><td>{b.get('html_bytes', 0) / 1024 / 1024:.2f} MB（单文件，离线可打开）</td></tr>"
                   f"<tr><th>星系</th><td>{b.get('stars')} 颗主星 · {b.get('planets')} 颗行星</td></tr>"
                   f"<tr><th>SHA-256</th><td><code>{e(b.get('html_sha256'))}</code></td></tr></table></div>")

    v = st["visual"]
    out.append("<h2>浏览器视觉检查</h2>")
    if v["status"] == "skipped":
        out.append(f"<div class='panel'><span class='badge warn'>未验证</span> {e(v['detail'].get('reason'))}</div>")
    elif v["detail"].get("verified") or v["errors"]:
        rep_path = p["visual"] / "report.json"
        rep = load(rep_path) if rep_path.is_file() else {}
        webgl = "WebGL 已启用" if rep.get("webgl") else "WebGL 不可用（降级渲染）"
        out.append(f"<div class='panel'><p>{e(webgl)} · 外部请求 {len(rep.get('external_requests', []))} 个 · 页面异常 {len(rep.get('errors', []))} 个</p><table>")
        for c in rep.get("checks", []):
            pill = "<span class='badge ok'>通过</span>" if c["passed"] else "<span class='badge bad'>失败</span>"
            detail = c.get("detail") if c.get("detail") is not None else ""
            out.append(f"<tr><td>{pill}</td><td>{e(c['name'])}</td><td class='dim'>{e(detail)}</td></tr>")
        out.append("</table>")
        if rep.get("failure"): out.append(f"<p class='err'>{e(rep['failure'])}</p>")
        out.append("</div><div class='grid'>")
        for name, caption in SHOTS:
            f = p["visual"] / (name + ".png")
            if f.is_file(): out.append(f"<figure><img alt='{e(caption)}' src='{_thumb(f, 900)}'><figcaption>{e(caption)}</figcaption></figure>")
        out.append("</div>")
    else:
        out.append("<div class='panel dim'>尚未运行。</div>")

    out.append("<h2>边界</h2><div class='panel dim'><ul><li>精简模式的内容来自 AI 对你的印象（记忆与对话），没有逐条核对原始聊天记录。</li>"
               "<li>浏览器检查在本机无头浏览器中进行，不代表 Safari 或真机效果。</li><li>页面不会自动公开；是否分享由你决定。</li></ul></div>")
    out.append("</main></html>")
    p["report"].write_text("\n".join(out), encoding="utf-8")
    return p["report"]
