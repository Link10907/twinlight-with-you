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
            "choice": ws / "card" / "choice.json", "art_brief": ws / "card" / "art-brief.txt",
            "card_preview": ws / "card" / "front.png",
            "site": ws / "site", "html": ws / "site" / "index.html",
            "visual": ws / "visual", "report": ws / "report.html"}


def cmd(*args: str) -> str:
    return " ".join(shlex.quote(a) for a in [sys.executable, str(CLI), *args])


def _blank(stage: str) -> dict:
    return {"status": "pending", "attempts": 0, "updated_at": None, "errors": [], "warnings": [], "detail": {}, "log": []}


def start(ws: Path, preview_only: bool = False) -> dict:
    p = paths(ws)
    check(not p["state"].exists(), f"工作目录已存在运行记录：{p['state']}。继续请直接运行 next；重新开始请换一个目录。")
    p["card"].mkdir(parents=True, exist_ok=True)
    state = {"version": "1", "mode": "lite", "preview_only": bool(preview_only), "created_at": now(),
             "stages": {s: _blank(s) for s in STAGES}, "events": []}
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
    choice = load(p["choice"]) if p["choice"].is_file() else {}
    mode = choice.get("mode") or ("placeholder" if choice.get("placeholder") is True else None)
    check(mode in (None, "static", "placeholder"), "卡图选择只能是 static 或 placeholder；恢复独立图层时清除 choice.json")
    if mode == "placeholder":
        return {}
    if mode == "static":
        for role in ("prototype", "portrait"):
            hits = [p["card"] / (role + ext) for ext in IMAGE_EXT if (p["card"] / (role + ext)).is_file()]
            check(len(hits) <= 1, f"card/ 里有多个 {role} 图片，只保留一个")
            if hits:
                return {role: hits[0]}
        raise ContractError("静态降级需要现有 card/prototype 或 portrait 图片；请先保存原型，或明确选择 placeholder")
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
        return {"files": files, "choice": sha(p["choice"]), "art_brief": sha(p["art_brief"])}
    except (ContractError, OSError, ValueError, TypeError, KeyError):
        # A malformed/deleted resource also invalidates the accepted art stage.
        return {"invalid_inputs": True, "manifest": sha(p["card"] / "layers.json"), "choice": sha(p["choice"]),
                "art_brief": sha(p["art_brief"])}


def _art_kwargs(found: dict) -> dict:
    if "layers" in found: return {"layers": found["layers"]}
    return {k: v for k, v in found.items() if k in ("prototype", "portrait", "character", "background")}


def integrity(state: dict, p: dict) -> list[str]:
    notes = []
    st = state["stages"]
    if st["profile"]["status"] == "passed" and sha(p["profile"]) != st["profile"]["detail"].get("sha256"):
        _reopen(state, "profile", "twinlight.json 在通过校验后被修改"); notes.append("twinlight.json 已修改，需重新校验并重新确认")
    if st["art"]["status"] == "passed" and (
            _art_fingerprint(p) != st["art"]["detail"].get("fingerprint")
            or not p["card_preview"].is_file()
            or sha(p["card_preview"]) != st["art"]["detail"].get("card_preview_sha256")):
        _reopen(state, "art", "卡图或卡片预览在通过检查后被修改"); notes.append("卡图已修改或卡片预览已变动，需重新检查并重新构建")
    if st["build"]["status"] == "passed" and sha(p["html"]) != st["build"]["detail"].get("html_sha256"):
        _reopen(state, "build", "site/index.html 在构建后被修改"); notes.append("HTML 被改动，需重新构建")
    return notes


def _pass(state: dict, stage: str, detail: dict, warnings: list | None = None, status: str = "passed") -> None:
    s = state["stages"][stage]
    s.update({"status": status, "updated_at": now(), "errors": [], "warnings": warnings or [], "detail": detail})
    s["log"].append({"at": now(), "result": status, "errors": 0})
    message = "通过" if status == "passed" else "跳过（未验证）"
    if stage == "review" and detail.get("reason") == "local_preview":
        message = "本地草稿，文案尚未由本人确认"
    _event(state, stage, message)


def _local_preview_review(state: dict) -> bool:
    """A deferred local review is permission to render, never text approval."""
    profile, review = state["stages"]["profile"], state["stages"]["review"]
    return bool(state.get("preview_only") and profile["status"] == "passed"
                and review["status"] == "skipped" and review["detail"].get("reason") == "local_preview"
                and review["detail"].get("confirmed") is False
                and review["detail"].get("profile_sha256") == profile["detail"].get("sha256"))


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
        result["message"] = "此阶段已连续失败 3 次。按 next 查明原因并修复或选择实际可交付模式，再继续后续阶段。"
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
        if state.get("preview_only"):
            _pass(state, stage, {"profile_sha256": state["stages"]["profile"]["detail"]["sha256"],
                                 "reason": "local_preview", "confirmed": False}, status="skipped")
            result["message"] = "继续生成本地未确认草稿；未记录本人确认，也未开启应用导出。"
        else:
            result["message"] = "这一步只能由用户确认。把 next 输出里的 preview 全文展示给用户，用户明确同意后运行 confirm。"
    elif stage == "art":
        try:
            found = art_inputs(p)
            if not found:
                choice = load(p["choice"]) if p["choice"].is_file() else {}
                check(choice.get("mode") == "placeholder" or choice.get("placeholder") is True,
                      "card/ 里没有图片，也没有选择占位卡（art --placeholder）")
            from .site import lite_layers, render_card_preview
            data = _profile_data(p)
            art = lite_layers(**_art_kwargs(found), expected_persona=lite.persona_digest(data))
            preview = render_card_preview(data, p["card_preview"], **_art_kwargs(found))
            check(p["card_preview"].is_file() and sha(p["card_preview"]) == preview["sha256"], "本次卡片预览缺失或内容不匹配")
            _pass(state, stage, {"fingerprint": _art_fingerprint(p), "art_status": art["art_status"], "art_mode": art["art_mode"],
                                 "binding": art["binding"], "native_full_canvas": art["native_full_canvas"],
                                 "card_preview": str(p["card_preview"]), "card_preview_sha256": preview["sha256"],
                                 "card_preview_kind": preview["preview_kind"],
                                 "files": {k: str(v) for k, v in found.items()}})
        except (ContractError, OSError, ValueError, TypeError, KeyError) as exc:
            _fail(state, stage, [{"path": "card/", "code": "art", "message": str(exc)}])
    elif stage == "build":
        from .site import build_lite
        try:
            found = art_inputs(p)
            report = build_lite(_profile_data(p), p["site"], generated_at=state["created_at"],
                                confirmed=state["stages"]["review"]["status"] == "passed",
                                **_art_kwargs(found))
            _pass(state, stage, {**report, "html_sha256": sha(p["html"])})
        except (ContractError, OSError, ValueError, TypeError, KeyError) as exc:
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
    out = p["visual"]
    rep = out / "report.json"
    try:
        out.mkdir(parents=True, exist_ok=True)
        # A report must come from this invocation, even after a rebuild or retry.
        rep.unlink(missing_ok=True)
    except OSError as exc:
        _fail(state, "visual", [{"path": "visual/", "code": "io", "message": str(exc)}]); return
    try:
        import playwright  # noqa: F401
    except ImportError:
        _pass(state, "visual", {"verified": False, "reason": "当前环境没有 Playwright，无法做浏览器检查"}, status="skipped"); return
    try:
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_browser.py"), "--html", str(p["html"]), "--out", str(out)],
                              capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        _fail(state, "visual", [{"path": "visual/", "code": "timeout", "message": "浏览器检查超过 10 分钟"}]); return
    except OSError as exc:
        _fail(state, "visual", [{"path": "visual/", "code": "browser", "message": str(exc)}]); return
    if not rep.is_file():
        message = "本次浏览器检查没有生成报告"
        if proc.stderr.strip():
            message += "：" + proc.stderr.strip().splitlines()[-1][:300]
        _fail(state, "visual", [{"path": "visual/report.json", "code": "missing_report", "message": message}]); return
    try:
        report = load(rep)
        check(isinstance(report, dict) and isinstance(report.get("checks"), list), "本次浏览器检查报告格式不正确")
        detail = {"verified": True, "webgl": report.get("webgl"), "checks": len(report["checks"]),
                  "failed": [c["name"] for c in report["checks"] if not c["passed"]],
                  "screenshots": sorted(x.name for x in out.glob("*.png")), "html_sha256": sha(p["html"])}
    except (ContractError, OSError, ValueError, TypeError, KeyError) as exc:
        _fail(state, "visual", [{"path": "visual/report.json", "code": "invalid_report", "message": str(exc)}]); return
    failure = str(report.get("failure", ""))
    unavailable_browser = not report["checks"] and any(x in failure.lower() for x in (
        "executable doesn't exist", "executable does not exist", "browser executable not found",
        "host system is missing dependencies to run browsers", "error while loading shared libraries"))
    if unavailable_browser:
        _pass(state, "visual", {"verified": False, "reason": "浏览器无法启动：" + str(report.get("failure"))[:300]}, status="skipped"); return
    if proc.returncode == 0 and report.get("ok") is True and report["checks"] and not detail["failed"] and not failure:
        _pass(state, "visual", detail)
    else:
        _fail(state, "visual", [{"path": "visual/", "code": "browser", "message": failure or f"本次浏览器检查未通过（退出码 {proc.returncode}）"}])


def confirm(ws: Path, user_reply: str) -> dict:
    p = paths(ws); state = _load(ws)
    if integrity(state, p): save(p["state"], state)
    stage = current(state)
    deferred = _local_preview_review(state) and stage in ("art", "build", "visual", "report", "done")
    check(stage == "review" or deferred, f"现在不是确认阶段（当前：{STAGE_CN.get(stage)}）")
    reply = user_reply.strip()
    check(len(reply) >= 1, "--user-reply 需要填写用户确认时的原话")
    _pass(state, "review", {"user_reply": reply[:500], "confirmed": True,
                            "profile_sha256": state["stages"]["profile"]["detail"]["sha256"]})
    if deferred:
        _reopen(state, "art", "本人明确确认当前草稿文案，重新检查卡片并构建页面")
    save(p["state"], state)
    return {"ok": True, "next": next_action(ws)}


def choose_art(ws: Path, mode: str) -> dict:
    p = paths(ws); state = _load(ws)
    if integrity(state, p): save(p["state"], state)
    check(current(state) in ("art", "build", "visual", "report", "done")
          and (state["stages"]["review"]["status"] == "passed" or _local_preview_review(state)),
          f"卡图模式需要当前文案已确认，或已校验的本地草稿流程（当前：{STAGE_CN.get(current(state))}）")
    check(mode in ("static", "placeholder", "layered"), "卡图模式只能是 static、placeholder 或 layered")
    if mode == "static":
        # Validate the selection before replacing an existing choice.
        for role in ("prototype", "portrait"):
            hits = [p["card"] / (role + ext) for ext in IMAGE_EXT if (p["card"] / (role + ext)).is_file()]
            check(len(hits) <= 1, f"card/ 里有多个 {role} 图片，只保留一个")
            if hits:
                from .site import lite_layers
                lite_layers(**{role: hits[0]})
                break
        else:
            raise ContractError("静态降级需要现有 card/prototype 或 portrait 图片；请先保存原型，或明确选择 placeholder")
    if mode == "layered":
        p["choice"].unlink(missing_ok=True)
    else:
        save(p["choice"], {"mode": mode, "placeholder": mode == "placeholder", "at": now()})
    _reopen(state, "art", "明确选择卡图模式：" + mode + "；保留现有图片")
    save(p["state"], state)
    return check_stage(ws)


def choose_placeholder(ws: Path) -> dict:
    return choose_art(ws, "placeholder")


def unblock(ws: Path, note: str) -> dict:
    p = paths(ws); state = _load(ws)
    stage = current(state)
    check(stage != "done" and state["stages"][stage]["status"] == "blocked", "当前阶段没有被阻塞")
    check(len(note.strip()) >= 1, "--note 需要写明实际技术修复、降级或用户决定；不能伪造本人确认")
    state["stages"][stage].update({"status": "pending", "attempts": 0})
    _event(state, stage, "解除技术阻塞：" + note.strip()[:300])
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
    out: dict = {"stage": stage, "name": STAGE_CN[stage], "notes": notes,
                 "preview_only": bool(state.get("preview_only")),
                 "text_confirmed": state["stages"]["review"]["status"] == "passed"}
    if stage != "done":
        s = state["stages"][stage]
        out.update({"status": s["status"], "attempts": s["attempts"], "max_attempts": MAX_ATTEMPTS})
        if s["status"] == "blocked":
            out["do"] = ["相同流程已连续 3 次没有通过，先根据 errors 查明原因，不重复无变化的检查。",
                         "格式、文件、图层和浏览器等技术问题由你修复；仅缺少本人资料或需要新内容决定时询问用户。",
                         f"实际修复后运行：{cmd('unblock', '--workspace', w, '--note', '<实际技术修复或用户决定>')}，然后重新运行 check。unblock 不替代本人文案确认。"]
            if stage == "art":
                out["do"].append(f"独立图层仍不合格时保留全部素材，用 {cmd('art', '--workspace', w, '--static')} 选择现有原型；无合格原型则用 {cmd('art', '--workspace', w, '--placeholder')}。明确降级可恢复检查。")
            out["errors"] = s["errors"]
            return out
    if stage == "profile":
        out.update({"read": [str(ROOT / "PROMPT.md"), str(ROOT / "references" / "lite-content.md")],
            "write": str(p["profile"]), "schema": str(ROOT / "schemas" / "lite.schema.json"),
            "do": ["按 PROMPT.md 的规则，根据你对用户的了解（你的记忆 + 本次对话）写出 Twinlight JSON，保存到 write 指定的路径。",
                   "对用户了解很少时，先问 2–3 个简短问题再写；不要编造经历或读入示例来补全。",
                   "只写文件，不要让用户手工编辑 JSON。"],
            "then": cmd("check", "--workspace", w)})
        if state["stages"]["profile"]["errors"]:
            out["errors"] = state["stages"]["profile"]["errors"]
            out["repair_prompt"] = lite.repair_prompt(state["stages"]["profile"]["errors"])
            out["do"] = ["上一次校验没通过。只修改 errors 列出的位置，其余内容不变，保存后再运行 then。"]
    elif stage == "review":
        out["preview"] = lite.preview_markdown(_profile_data(p))
        if state.get("preview_only"):
            out.update({"do": ["这是本地未确认草稿流程，运行 then 记录延后审阅并自动继续卡片与 HTML；不要代本人 confirm。",
                               "卡片与页面完成后一起展示；真实确认可稍后记录，未确认时应用导出保持关闭。"],
                        "then": cmd("check", "--workspace", w)})
        else:
            out.update({"do": ["把 preview 的全文原样展示给用户（不要删减），问：这些内容放到你的星系里可以吗？有没有想改或不想公开的？",
                                "用户要修改：直接改 twinlight.json，然后运行 check（会重新校验，再回到这一步）。",
                                "用户明确同意后，把用户的原话填进 --user-reply 运行 then。不能替用户同意。"],
                        "then": cmd("confirm", "--workspace", w, "--user-reply", "<用户同意时的原话>")})
    elif stage == "art":
        from .cardgen import card_spec
        data = _profile_data(p)
        try:
            art_prompt = p["art_brief"].read_text(encoding="utf-8") if p["art_brief"].is_file() else None
            spec = card_spec(data, generated_at=state["created_at"], art_prompt=art_prompt)
        except (ContractError, OSError, UnicodeError) as exc:
            out.update({"read": [str(ROOT / "CARD.md"), str(ROOT / "prompts" / "card-generation.md"),
                                  str(ROOT / "references" / "art-direction.md")],
                        "write": str(p["art_brief"]), "art_brief": str(p["art_brief"]), "brief_required": True,
                        "errors": [{"path": "card/art-brief.txt", "code": "art_brief", "message": str(exc)}],
                        "do": ["在 write 路径写入本次独立美术 brief（20–1500 字），使用本次授权资料、明确偏好与最新反馈；未指定的设计由你自主选择。",
                               "不要为了画风或生图补写 card.art_prompt 到 twinlight.json，也不要修改已核对文案、人物绑定或确认记录。",
                               "写好后运行 then 取得卡片规格；已有绑定合格的成品图层可直接运行 check 消费，渲染不需要新增生图提示。"],
                        "then": cmd("next", "--workspace", w)})
            return out
        existing_art = {"validated": False, "source": None, "files": {}}
        asset_errors = []
        selected_mode = None
        try:
            found = art_inputs(p)
            if p["choice"].is_file():
                choice = load(p["choice"])
                selected_mode = choice.get("mode") or ("placeholder" if choice.get("placeholder") is True else None)
            if found:
                composition = None
                if "layers" in found:
                    from .art import validate_layers
                    validation = validate_layers(found["layers"], spec["persona_digest"])
                    canvas = validation["size"]
                    manifest = load(found["layers"])
                    composition = manifest.get("composition")
                    source, binding = "layers", "persona_digest"
                else:
                    from .site import lite_layers, open_card_image
                    art = lite_layers(**_art_kwargs(found), expected_persona=spec["persona_digest"])
                    if art["art_validation"]:
                        canvas = art["art_validation"]["size"]
                        source = "native_pair"
                    else:
                        source = "prototype" if "prototype" in found else "portrait"
                        canvas = open_card_image(found[source]).size
                    binding = art["binding"]
                spec = card_spec(data, generated_at=state["created_at"], canvas=canvas, composition=composition,
                                 art_prompt=art_prompt)
                existing_art = {"validated": True, "source": source, "canvas": list(canvas), "binding": binding,
                                "files": {k: str(v) for k, v in _art_kwargs(found).items()}}
        except (ContractError, OSError, ValueError, TypeError, KeyError) as exc:
            # `next` must remain readable when supplied artwork needs repair.
            # A failed binding or malformed asset never selects its canvas.
            asset_errors = [{"path": "card/", "code": "art", "message": str(exc)}]
        existing_art["selected_mode"] = selected_mode
        prompts = spec["prompts"]
        card = str(p["card"])
        prototype_action = f"仅在没有已校验的本次原型或完整图层时，按 prototype_prompt 生成无字原型并保存为 {card}/prototype.png；后续调用复用同一参考，不因读取 next 重生成。"
        if existing_art["validated"] and existing_art["source"] in ("prototype", "portrait"):
            prototype_action = "复用 existing_art 中已校验的本次原型，按它的实际画布生成缺少的原生图层；不要重新生成或裁切原型。"
        out.update({"read": [str(ROOT / "prompts" / "card-generation.md"), str(ROOT / "references" / "art-direction.md")],
            "card_spec": spec, "existing_art": existing_art,
            "art_brief": str(p["art_brief"]),
            "manifest": str(p["card"] / "layers.json"), "card_preview": str(p["card_preview"]),
            "prototype_prompt": prompts["prototype"], "subject_prompt": prompts["subject"],
            "character_prompt": prompts["character"], "background_prompt": prompts["background"],
            "effects_prompt": prompts["effects"], "spirit_prompt": prompts["spirit"], "text_instructions": prompts["text"],
            "do": ["先检查 existing_art 与 errors，优先复用已校验的本次素材；素材缺少时再检查生图工具，只修复失败层，保持当前文案不变。不要让用户查工具、写 JSON 或操作命令。",
                   prototype_action,
                   "参考这张原型，按 subject/background/effects/spirit 提示分别原生生成真实独立层，保持完整 3:4 画布和同一坐标。禁止抠图、去背景、裁切主体、重新摆位或多层重复完整海报。",
                   "SSR、卡框和当前称号在独立 text 层排版；lineart 从最终 subject 的原像素推导，不重新画。unused spirit 交付同尺寸透明 PNG。",
                   f"保存全部层文件，并按 card_spec.manifest_template 写 {card}/layers.json；绑定本次 persona_digest，未视觉审查时 art_status=generated。",
                   "若工具只能生成一张原型，保留为 static 静态预览、景深为0，不宣称分层完成。若没有生图工具，使用明确 placeholder。",
                   f"已有失败图层时不删除素材：静态降级运行 {cmd('art', '--workspace', w, '--static')}；占位运行 {cmd('art', '--workspace', w, '--placeholder')}。恢复原生图层可运行 {cmd('art', '--workspace', w, '--layered')} 清除降级选择。",
                   "降级选择会优先于现有图层；默认保留该选择，不因目录里的其他素材自动改模式。生成好当前选择的原型或图层后运行 then。",
                   "then 会生成卡片预览；卡片完成或诚实降级后，自动继续构建 HTML、检查与报告直到 done，不能只交卡片或 JSON 后停止。"],
            "then": cmd("check", "--workspace", w)})
        if not asset_errors and ((existing_art["validated"] and existing_art["source"] in ("layers", "native_pair"))
                                 or selected_mode in ("static", "placeholder")):
            out["do"] = ["复用 existing_art 中已校验的本次素材与实际画布；已有完整图层或明确选择的静态/占位模式时，直接继续，不再生成原型或重生成通过的图层。",
                         "检查本次图像的构图、透明度与文字是否合格；机械校验不代替目视审查。需要修复时只改失败素材，保持当前文案不变。",
                         "运行 then 生成卡片预览，自动继续构建 HTML、检查与报告直到 done；不能只交卡片或 JSON 后停止。"]
            if selected_mode == "placeholder":
                out["do"][0] = "已明确选择占位模式，保留现有素材，不生成原型，也不因目录里的失败图层自动恢复分层；直接继续占位预览和 HTML。"
            elif existing_art["source"] == "native_pair":
                out["do"][0] = "按 native_pair 路线复用已校验的同画布原生主体与背景，不重生成原型；这两层尚未包含准确文字和完整六层卡片，展示时如实说明。"
                out["do"][1] = "目视检查主体/背景配准、真实透明度与场景，不把机械校验或 native_pair 预览称为已完成完整六层 SSR；保持当前文案不变。"
        if asset_errors:
            out["do"].insert(0, "现有素材尚未通过校验，先按 errors 修复；未通过的绑定和画布不可复用，不能按默认尺寸覆盖原文件。")
        errors = list(state["stages"]["art"]["errors"])
        errors.extend(issue for issue in asset_errors if issue not in errors)
        if errors: out["errors"] = errors
    elif stage in ("build", "visual", "report"):
        what = {"build": "用固定模板构建单文件 HTML", "visual": "用浏览器打开页面做自动检查并截图（没有浏览器会标记为未验证）",
                "report": "生成可视化运行报告 report.html"}[stage]
        out.update({"do": [f"运行 then：{what}。", "完成后继续读取 next 并执行，直到 done；用户一次请求需要卡片预览和实际 HTML 两项产物。"],
                    "then": cmd("check", "--workspace", w), "card_preview": str(p["card_preview"])})
        if stage == "build":
            out["read"] = [str(ROOT / "prompts" / "html-build.md"), str(ROOT / "references" / "preview.md")]
        if state["stages"][stage]["errors"]: out["errors"] = state["stages"][stage]["errors"]
    else:
        st = state["stages"]
        out.update({"card_preview": str(p["card_preview"]), "html": str(p["html"]), "report": str(p["report"]),
            "art_status": st["art"]["detail"].get("art_status"), "visual_verified": st["visual"]["detail"].get("verified"),
            "art_mode": st["art"]["detail"].get("art_mode"), "card_preview_kind": st["art"]["detail"].get("card_preview_kind"),
            "do": ["先展示 card_preview，再打开实际 html；两项一起交付，不让用户再请求一次 HTML。",
                   "如果当前聊天支持 HTML/Artifact 预览，直接打开 html 给用户看；否则提供同一 html 文件（单文件、浏览器离线可用）。",
                   "说明：卡图是分层、静态还是占位；文案是否本人确认；浏览器检查是否真的运行（visual_verified）。report 留作可选附件。",
                   "内容来自 AI 印象，不是逐条核对的聊天记录；页面不会自动公开，分享由用户自己决定。"]})
    return out
