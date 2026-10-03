"""Gated lite workflow. The agent only ever does what `next` says.

Each stage records the SHA-256 of what it accepted. Editing an accepted file
re-opens that stage and every later one, so a confirmation or a screenshot can
never silently describe content that has since changed.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path
from .common import ROOT, ContractError, check, load, save, local_asset
from . import lite

STAGES = ["profile", "review", "art", "build", "visual", "report"]
STAGE_CN = {"profile": "写 JSON 并通过校验", "review": "用户确认文案", "art": "卡图", "build": "构建单文件 HTML",
            "visual": "浏览器视觉检查", "report": "生成报告", "done": "完成"}
MAX_ATTEMPTS = 3
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
CLI = ROOT / "scripts" / "twinlight.py"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def paths(ws: Path) -> dict:
    ws = ws.resolve()
    return {"ws": ws, "state": ws / "state.json", "profile": ws / "twinlight.json", "card": ws / "card",
            "choice": ws / "card" / "choice.json", "site": ws / "site", "html": ws / "site" / "index.html",
            "visual": ws / "visual", "report": ws / "report.html"}


def cmd(*args: str) -> str:
    return " ".join(shlex.quote(a) for a in [sys.executable, str(CLI), *args])


def _blank(stage: str) -> dict:
    return {"status": "pending", "attempts": 0, "updated_at": None, "errors": [], "warnings": [], "detail": {}, "log": []}


def start(ws: Path) -> dict:
    p = paths(ws)
    check(not p["state"].exists(), f"工作目录已存在运行记录：{p['state']}。继续请直接运行 next；重新开始请换一个目录。")
    p["card"].mkdir(parents=True, exist_ok=True)
    state = {"version": "1", "mode": "lite", "created_at": now(), "stages": {s: _blank(s) for s in STAGES}, "events": []}
    _event(state, "start", "创建工作目录")
    save(p["state"], state)
    return next_action(ws)


def _load(ws: Path) -> dict:
    p = paths(ws)
    check(p["state"].is_file(), f"没有运行记录：{p['state']}。先运行 {cmd('start', '--workspace', str(p['ws']))}")
    return load(p["state"])


def _event(state: dict, stage: str, text: str) -> None:
    state["events"].append({"at": now(), "stage": stage, "event": text})


def current(state: dict) -> str:
    for s in STAGES:
        if state["stages"][s]["status"] not in ("passed", "skipped"):
            return s
    return "done"


def _reopen(state: dict, stage: str, reason: str) -> None:
    for s in STAGES[STAGES.index(stage):]:
        if state["stages"][s]["status"] != "pending" or state["stages"][s]["attempts"]:
            state["stages"][s].update({"status": "pending", "attempts": 0, "errors": [], "detail": {}})
    _event(state, stage, "重新打开：" + reason)


def art_inputs(p: dict) -> dict:
    found = {}
    manifest = p["card"] / "layers.json"
    if manifest.is_file(): found["layers"] = manifest
    # With a manifest the PNG files are its registered resources, not competing inputs.
    roles = ("prototype",) if "layers" in found else ("prototype", "portrait", "character", "subject", "background")
    for role in roles:
        hits = [p["card"] / (role + ext) for ext in IMAGE_EXT if (p["card"] / (role + ext)).is_file()]
        check(len(hits) <= 1, f"card/ 里有多个 {role} 图片，只保留一个")
        if hits: found[role] = hits[0]
    if "subject" in found:
        check("character" not in found, "card/ 里有 subject 和 character 两份主体，只保留当前原生主体层")
        found["character"] = found.pop("subject")
    return found


def _art_fingerprint(p: dict) -> dict:
    try:
        found = art_inputs(p)
        files = {k: sha(v) for k, v in found.items()}
        if "layers" in found:
            manifest = load(found["layers"])
            files["layer_assets"] = {k: sha(local_asset(p["card"], v)) for k, v in manifest["assets"].items()}
        return {"files": files, "choice": sha(p["choice"])}
    except (ContractError, OSError, ValueError, TypeError, KeyError):
        # A malformed/deleted resource also invalidates the accepted art stage.
        return {"invalid_inputs": True, "manifest": sha(p["card"] / "layers.json"), "choice": sha(p["choice"])}


def _art_kwargs(found: dict) -> dict:
    if "layers" in found: return {"layers": found["layers"]}
    return {k: v for k, v in found.items() if k in ("prototype", "portrait", "character", "background")}


def integrity(state: dict, p: dict) -> list[str]:
    notes = []
    st = state["stages"]
    if st["profile"]["status"] == "passed" and sha(p["profile"]) != st["profile"]["detail"].get("sha256"):
        _reopen(state, "profile", "twinlight.json 在通过校验后被修改"); notes.append("twinlight.json 已修改，需重新校验并重新确认")
    if st["art"]["status"] == "passed" and _art_fingerprint(p) != st["art"]["detail"].get("fingerprint"):
        _reopen(state, "art", "卡图文件在通过检查后被修改"); notes.append("卡图已修改，需重新检查并重新构建")
    if st["build"]["status"] == "passed" and sha(p["html"]) != st["build"]["detail"].get("html_sha256"):
        _reopen(state, "build", "site/index.html 在构建后被修改"); notes.append("HTML 被改动，需重新构建")
    return notes


def _pass(state: dict, stage: str, detail: dict, warnings: list | None = None, status: str = "passed") -> None:
    s = state["stages"][stage]
    s.update({"status": status, "updated_at": now(), "errors": [], "warnings": warnings or [], "detail": detail})
    s["log"].append({"at": now(), "result": status, "errors": 0})
    _event(state, stage, "通过" if status == "passed" else "跳过（未验证）")


def _fail(state: dict, stage: str, errors: list, warnings: list | None = None) -> None:
    s = state["stages"][stage]
    s["attempts"] += 1
    s.update({"status": "blocked" if s["attempts"] >= MAX_ATTEMPTS else "failed", "updated_at": now(),
              "errors": errors, "warnings": warnings or []})
    s["log"].append({"at": now(), "result": "failed", "errors": len(errors)})
    _event(state, stage, f"第 {s['attempts']} 次检查失败：{len(errors)} 处问题")


def _profile_data(p: dict) -> dict:
    report = lite.check_text(p["profile"].read_text(encoding="utf-8"))
    check(report["ok"], "twinlight.json 未通过校验")
    return report["data"]


def check_stage(ws: Path) -> dict:
    p = paths(ws); state = _load(ws)
    notes = integrity(state, p)
    stage = current(state)
    s = state["stages"].get(stage)
    result: dict = {"stage": stage, "notes": notes}
    if stage == "done":
        result["message"] = "全部阶段已完成。"
    elif s["status"] == "blocked":
        result["message"] = "此阶段已连续失败 3 次，已停止。按 next 的说明向用户报告。"
    elif stage == "profile":
        if not p["profile"].is_file():
            _fail(state, stage, [{"path": "$", "code": "missing_file", "message": f"还没有 {p['profile'].name}"}])
        else:
            report = lite.check_text(p["profile"].read_text(encoding="utf-8"))
            if report["ok"]:
                p["profile"].write_text(json.dumps(report["data"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                _pass(state, stage, {"sha256": sha(p["profile"]), "stats": report["stats"]}, report["warnings"])
            else:
                _fail(state, stage, report["errors"], report["warnings"])
                result["repair_prompt"] = lite.repair_prompt(report["errors"])
    elif stage == "review":
        result["message"] = "这一步只能由用户确认。把 next 输出里的 preview 全文展示给用户，用户明确同意后运行 confirm。"
    elif stage == "art":
        try:
            found = art_inputs(p)
            if not found:
                check(p["choice"].is_file() and load(p["choice"]).get("placeholder") is True,
                      "card/ 里没有图片，也没有选择占位卡（art --placeholder）")
            from .site import lite_layers
            profile = lite.to_profile(_profile_data(p), generated_at=state["created_at"])
            art = lite_layers(**_art_kwargs(found), expected_persona=profile["persona"]["persona_digest"])
            _pass(state, stage, {"fingerprint": _art_fingerprint(p), "art_status": art["art_status"], "art_mode": art["art_mode"],
                                 "binding": art["binding"], "native_full_canvas": art["native_full_canvas"],
                                 "files": {k: str(v) for k, v in found.items()}})
        except ContractError as exc:
            _fail(state, stage, [{"path": "card/", "code": "art", "message": str(exc)}])
    elif stage == "build":
        from .site import build_lite
        found = art_inputs(p)
        try:
            report = build_lite(_profile_data(p), p["site"], generated_at=state["created_at"], confirmed=True,
                                **_art_kwargs(found))
            _pass(state, stage, {**report, "html_sha256": sha(p["html"])})
        except ContractError as exc:
            _fail(state, stage, [{"path": "site/", "code": "build", "message": str(exc)}])
    elif stage == "visual":
        _visual(state, p)
    elif stage == "report":
        from .report import write_report
        write_report(ws, state)
        _pass(state, stage, {"report": str(p["report"])})
    if stage in state["stages"]:
        s = state["stages"][stage]
        result.update({"status": s["status"], "attempts": s["attempts"], "errors": s["errors"], "warnings": s["warnings"]})
    save(p["state"], state)
    result["next"] = next_action(ws)
    return result


def _visual(state: dict, p: dict) -> None:
    try:
        import playwright  # noqa: F401
    except ImportError:
        _pass(state, "visual", {"verified": False, "reason": "当前环境没有 Playwright，无法做浏览器检查"}, status="skipped"); return
    out = p["visual"]; out.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_browser.py"), "--html", str(p["html"]), "--out", str(out)],
                              capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        _fail(state, "visual", [{"path": "visual/", "code": "timeout", "message": "浏览器检查超过 10 分钟"}]); return
    rep = out / "report.json"
    if not rep.is_file():
        _pass(state, "visual", {"verified": False, "reason": "浏览器无法启动：" + (proc.stderr.strip().splitlines() or ["未知原因"])[-1][:300]}, status="skipped"); return
    report = load(rep)
    launch_failed = not report.get("checks") and "Executable" in str(report.get("failure", ""))
    if launch_failed:
        _pass(state, "visual", {"verified": False, "reason": "浏览器无法启动：" + str(report.get("failure"))[:300]}, status="skipped"); return
    detail = {"verified": True, "webgl": report.get("webgl"), "checks": len(report.get("checks", [])),
              "failed": [c["name"] for c in report.get("checks", []) if not c["passed"]], "screenshots": sorted(x.name for x in out.glob("*.png"))}
    if report.get("ok"):
        _pass(state, "visual", detail)
    else:
        _fail(state, "visual", [{"path": "visual/", "code": "browser", "message": report.get("failure") or "浏览器检查未通过"}])


def confirm(ws: Path, user_reply: str) -> dict:
    p = paths(ws); state = _load(ws)
    integrity(state, p)
    check(current(state) == "review", f"现在不是确认阶段（当前：{STAGE_CN.get(current(state))}）")
    reply = user_reply.strip()
    check(len(reply) >= 1, "--user-reply 需要填写用户确认时的原话")
    _pass(state, "review", {"user_reply": reply[:500], "profile_sha256": state["stages"]["profile"]["detail"]["sha256"]})
    save(p["state"], state)
    return {"ok": True, "next": next_action(ws)}


def choose_placeholder(ws: Path) -> dict:
    p = paths(ws); state = _load(ws)
    check(current(state) == "art", f"现在不是卡图阶段（当前：{STAGE_CN.get(current(state))}）")
    check(not art_inputs(p), "card/ 里已经有图片；要用占位卡请先删掉这些图片")
    save(p["choice"], {"placeholder": True, "at": now()})
    return check_stage(ws)


def unblock(ws: Path, note: str) -> dict:
    p = paths(ws); state = _load(ws)
    stage = current(state)
    check(stage != "done" and state["stages"][stage]["status"] == "blocked", "当前阶段没有被阻塞")
    check(len(note.strip()) >= 1, "--note 需要写明用户怎么说")
    state["stages"][stage].update({"status": "pending", "attempts": 0})
    _event(state, stage, "用户介入后解除阻塞：" + note.strip()[:300])
    save(p["state"], state)
    return next_action(ws)


def status(ws: Path) -> dict:
    p = paths(ws); state = _load(ws)
    notes = integrity(state, p); save(p["state"], state)
    return {"workspace": str(p["ws"]), "current": current(state), "notes": notes,
            "stages": [{"stage": s, "name": STAGE_CN[s], "status": state["stages"][s]["status"],
                        "attempts": state["stages"][s]["attempts"]} for s in STAGES]}


def next_action(ws: Path) -> dict:
    p = paths(ws); state = _load(ws)
    notes = integrity(state, p); save(p["state"], state)
    stage = current(state); w = str(p["ws"])
    out: dict = {"stage": stage, "name": STAGE_CN[stage], "notes": notes}
    if stage != "done":
        s = state["stages"][stage]
        out.update({"status": s["status"], "attempts": s["attempts"], "max_attempts": MAX_ATTEMPTS})
        if s["status"] == "blocked":
            out["do"] = ["已连续 3 次没有通过，停止自动修复。",
                         "把下面 errors 用通俗中文告诉用户，问用户想怎么处理（例如删掉某个主题、缩短某段话）。",
                         f"按用户意见修改后运行：{cmd('unblock', '--workspace', w, '--note', '<用户的原话>')}，然后重新运行 check。"]
            out["errors"] = s["errors"]
            return out
    if stage == "profile":
        out.update({"read": [str(ROOT / "PROMPT.md")], "write": str(p["profile"]), "schema": str(ROOT / "schemas" / "lite.schema.json"),
            "do": ["按 PROMPT.md 的规则，根据你对用户的了解（你的记忆 + 本次对话）写出 Twinlight JSON，保存到 write 指定的路径。",
                   "对用户了解很少时，先问 2–3 个简短问题再写；不要编造经历或读入示例来补全。",
                   "只写文件，不要让用户手工编辑 JSON。"],
            "then": cmd("check", "--workspace", w)})
        if state["stages"]["profile"]["errors"]:
            out["errors"] = state["stages"]["profile"]["errors"]
            out["repair_prompt"] = lite.repair_prompt(state["stages"]["profile"]["errors"])
            out["do"] = ["上一次校验没通过。只修改 errors 列出的位置，其余内容不变，保存后再运行 then。"]
    elif stage == "review":
        out.update({"preview": lite.preview_markdown(_profile_data(p)),
            "do": ["把 preview 的全文原样展示给用户（不要删减），问：这些内容放到你的星系里可以吗？有没有想改或不想公开的？",
                   "用户要修改：直接改 twinlight.json，然后运行 check（会重新校验，再回到这一步）。",
                   "用户明确同意后，把用户的原话填进 --user-reply 运行 then。不能替用户同意。"],
            "then": cmd("confirm", "--workspace", w, "--user-reply", "<用户同意时的原话>")})
    elif stage == "art":
        from .cardgen import card_spec
        spec = card_spec(_profile_data(p), generated_at=state["created_at"])
        prompts = spec["prompts"]
        card = str(p["card"])
        out.update({"card_spec": spec, "manifest": str(p["card"] / "layers.json"),
            "prototype_prompt": prompts["prototype"], "subject_prompt": prompts["subject"],
            "character_prompt": prompts["character"], "background_prompt": prompts["background"],
            "effects_prompt": prompts["effects"], "spirit_prompt": prompts["spirit"], "text_instructions": prompts["text"],
            "do": ["主动检查已提供的生图工具并使用本次用户资料；不要让用户查工具、写 JSON 或操作命令。",
                   f"先按 prototype_prompt 直接生成无字原型，保存为 {card}/prototype.png，作为同一构图的参考。",
                   "参考这张原型，按 subject/background/effects/spirit 提示分别原生生成真实独立层，保持完整 3:4 画布和同一坐标。禁止抠图、去背景、裁切主体、重新摆位或多层重复完整海报。",
                   "SSR、卡框和当前称号在独立 text 层排版；lineart 从最终 subject 的原像素推导，不重新画。unused spirit 交付同尺寸透明 PNG。",
                   f"保存全部层文件，并按 card_spec.manifest_template 写 {card}/layers.json；绑定本次 persona_digest，未视觉审查时 art_status=generated。",
                   "若工具只能生成一张原型，保留为 static 静态预览、景深为0，不宣称分层完成。若没有生图工具，使用明确 placeholder。",
                   f"无图时运行 {cmd('art', '--workspace', w, '--placeholder')}；生成好原型或图层后运行 then。"],
            "then": cmd("check", "--workspace", w)})
        if state["stages"]["art"]["errors"]: out["errors"] = state["stages"]["art"]["errors"]
    elif stage in ("build", "visual", "report"):
        what = {"build": "用固定模板构建单文件 HTML", "visual": "用浏览器打开页面做自动检查并截图（没有浏览器会标记为未验证）",
                "report": "生成可视化运行报告 report.html"}[stage]
        out.update({"do": [f"运行 then：{what}。"], "then": cmd("check", "--workspace", w)})
        if state["stages"][stage]["errors"]: out["errors"] = state["stages"][stage]["errors"]
    else:
        st = state["stages"]
        out.update({"html": str(p["html"]), "report": str(p["report"]),
            "art_status": st["art"]["detail"].get("art_status"), "visual_verified": st["visual"]["detail"].get("verified"),
            "art_mode": st["art"]["detail"].get("art_mode"),
            "do": ["如果当前聊天支持 HTML/Artifact 预览，直接打开 html 给用户看；否则告诉用户用浏览器打开 html 文件（单文件、离线可用）。",
                   "同时给出 report 路径，说明：卡图是占位还是生成的；浏览器检查是否真的运行（visual_verified）。",
                   "内容来自 AI 印象，不是逐条核对的聊天记录；页面不会自动公开，分享由用户自己决定。"]})
    return out
