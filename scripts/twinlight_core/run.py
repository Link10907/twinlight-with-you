"""Portable one-request orchestration; content and native art are authored by the host.

The runner owns mechanical gates, retries and artifact invalidation. It cannot
authenticate the host, certify personal facts, or certify image quality/provenance.
All outputs are private, unconfirmed drafts. State is local traceability, not a
signed receipt. No external image service, installation or network is invoked.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from .common import ROOT, VERSION, ContractError, check, digest, load, save

STATE_VERSION = "controlled-run-1"
MAX_ATTEMPTS = 3


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resources() -> str:
    """Invalidate outputs when a renderer, contract, gate or its approval changes."""
    paths = []
    for directory in (ROOT / "assets/template", ROOT / "assets/card-preview",
                      ROOT / "schemas", ROOT / "scripts/twinlight_core"):
        paths.extend(p for p in directory.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    paths.extend(ROOT / "scripts" / name for name in
                 ("verify_browser.py", "package_card.py", "preview_card.py", "prepare_card_layers.py", "lock_template.py"))
    return digest({str(p.relative_to(ROOT)): _sha(p) for p in sorted(set(paths)) if p.is_file()})


def _art_dependency(path: Path) -> str:
    """Hash real source bytes even when validation will fail, enabling repaired retries."""
    from .common import local_asset
    files = {"manifest": _sha(path)}
    try:
        manifest = load(path)
        assets = manifest.get("assets", {}) if isinstance(manifest, dict) else {}
        for role, filename in (assets.items() if isinstance(assets, dict) else []):
            try:
                files[role] = _sha(local_asset(path.parent, filename))
            except (OSError, ValueError, TypeError):
                files[role] = "missing_or_invalid"
    except (OSError, ValueError, TypeError):
        pass
    return digest(files)


def _fingerprints(workspace: Path, relative_paths: list[str]) -> dict:
    return {name: _sha(workspace / name) for name in relative_paths}


def _intact(workspace: Path, stage: dict) -> bool:
    files = stage.get("files_sha256", {})
    if not files:
        return False
    try:
        # Use only fixed relative artifacts written by this runner, never a path
        # selected by an external browser report or content field.
        return all(Path(name).is_relative_to(Path(".")) and not Path(name).is_absolute()
                   and ".." not in Path(name).parts and _sha(workspace / name) == sha
                   for name, sha in files.items())
    except (OSError, ValueError, TypeError):
        return False


def _stage(state: dict, workspace: Path, key: str, dependency: str, action,
           artifacts: list[str], *, validate=None) -> dict:
    old = state["stages"].get(key, {})
    unchanged = old.get("dependency") == dependency
    if unchanged and old.get("status") == "files_ready" and _intact(workspace, old):
        gate = validate() if validate else {"ok": True}
        if gate.get("ok"):
            old["reused"] = True
            return old
    attempts = old.get("attempts", 0) if unchanged else 0
    if attempts >= MAX_ATTEMPTS:
        result = {**old, "status": "blocked", "reused": False,
                  "error": "Three actual failures with unchanged inputs/resources; repair the reported dependency before resuming."}
    else:
        try:
            detail = action()
            gate = validate() if validate else {"ok": True}
            check(gate.get("ok"), "Independent artifact verification failed: " +
                  json.dumps(gate.get("errors", []), ensure_ascii=False)[:1500])
            result = {"status": "files_ready", "dependency": dependency, "attempts": attempts,
                      "reused": False, "detail": detail, "verification": gate,
                      "files_sha256": _fingerprints(workspace, artifacts)}
        except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
            result = {"status": "failed", "dependency": dependency, "attempts": attempts + 1,
                      "reused": False, "error": str(exc)[:2000], "files_sha256": {}}
    state["stages"][key] = result
    save(workspace / "run-state.json", state)
    return result


_CARD_BROWSER = r'''
import base64, hashlib, io, json, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright
html, out, binary = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3] or None
out.mkdir(parents=True, exist_ok=True)
html_bytes=html.read_bytes();html_text=html_bytes.decode('utf-8')
report={"ok":False,"html_sha256":hashlib.sha256(html_bytes).hexdigest(),"checks":[],"webgl":False,"interaction_verified":False,"scope":"Independent card preview; real drag/flip, layer motion, desktop and emulated mobile. Art quality unverified."}
def check(name, condition):
 report["checks"].append({"name":name,"passed":bool(condition)})
 if not condition: raise AssertionError(name)
def frame(page):
 encoded=page.evaluate('()=>holoCanvas.toDataURL("image/png").split(",")[1]')
 return Image.open(io.BytesIO(base64.b64decode(encoded))).convert('RGB')
def diff(a,b):
 if a.size!=b.size: raise AssertionError('Card frame dimensions changed')
 return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3
try:
 with sync_playwright() as pw:
  flags=['--no-sandbox','--disable-gpu-sandbox','--ignore-gpu-blocklist','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']
  b=pw.chromium.launch(executable_path=binary,headless=True,args=flags)
  errors=[]
  for width,height in ((1440,900),(390,844)):
   page=b.new_page(viewport={"width":width,"height":height},is_mobile=width==390,has_touch=width==390)
   page.on('pageerror',lambda error:errors.append(str(error)))
   page.set_content(html_text,wait_until='load')
   page.wait_for_function('()=>holo.ready||holo.failed',timeout=20000)
   check('Renderer initialized '+str(width),page.evaluate('()=>holo.ready||holo.failed'))
   report['webgl']=report['webgl'] or page.evaluate('()=>holo.ready')
   check('No horizontal overflow '+str(width),page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth'))
   check('Real native layers '+str(width),page.evaluate('()=>__holo.getState().layers>=5'))
   page.evaluate('()=>{holo.foil=0;holo.depth=1;__holo.setView(0,-.45)}')
   if page.evaluate('()=>holo.ready'):
    left=frame(page);page.evaluate('()=>__holo.setView(0,.45)');right=frame(page)
    check('Real internal pixels move with foil off '+str(width),diff(left,right)>.5)
    page.evaluate('()=>{holo.depth=0;__holo.setView(0,-.45)}');left=frame(page)
    page.evaluate('()=>__holo.setView(0,.45)');right=frame(page)
    check('Depth zero removes parallax '+str(width),diff(left,right)<.15)
    check('No WebGL errors '+str(width),page.evaluate('()=>holo.gl.getError()===0'))
   else:
    left=page.locator('.holo-fallback img').evaluate_all('(images)=>images.map(e=>e.style.transform)')
    page.evaluate('()=>__holo.setView(0,.45)')
    right=page.locator('.holo-fallback img').evaluate_all('(images)=>images.map(e=>e.style.transform)')
    check('CSS fallback independent layers respond '+str(width),len(right)==5 and left!=right)
   page.evaluate('()=>{holo.depth=1;holo.foil=.5;__holo.setView(-.05,-.15)}')
   box=page.locator('#identityCard').bounding_box()
   check('Card is within viewport '+str(width),box['x']>=0 and box['x']+box['width']<=width and box['y']>=0 and box['y']+box['height']<=height)
   x,y=box['x']+box['width']/2,box['y']+box['height']/2
   page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+40,y-8,steps=4);page.mouse.up()
   check('Actual drag rotates without flip '+str(width),page.evaluate('()=>holo.ty>0&&!v8.flipped'))
   if width==390: page.locator('#cardFlip').tap()
   else: page.locator('#cardFlip').click()
   check('Actual flip control '+str(width),page.evaluate('()=>v8.flipped'))
   page.screenshot(path=str(out/(str(width)+'.png')))
   page.close()
  check('No page exceptions',not errors)
  b.close()
 report['ok']=True;report['interaction_verified']=True
except Exception as exc: report['failure']=str(exc)
finally: (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
raise SystemExit(0 if report['ok'] else 1)
'''


def _browser_binary(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    if os.environ.get("TWINLIGHT_BROWSER"):
        return os.environ["TWINLIGHT_BROWSER"]
    choices = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
               "/Applications/Chromium.app/Contents/MacOS/Chromium", "/usr/lib/chromium/chromium",
               "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
               r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    return next((p for p in choices if Path(p).is_file()), None)


def _font_preflight(explicit: Path | None) -> dict:
    """Only preflight pending typography; completed native text needs no local font."""
    try:
        from prepare_card_layers import font_path
        from PIL import ImageFont
        path = font_path(explicit)
        ImageFont.truetype(str(path), 24)
        return {"status": "available", "path": str(path.resolve()), "readable": True,
                "cjk_coverage_verified": False,
                "scope": "Font can be loaded; typeset current Chinese text and inspect glyphs before delivery."}
    except (OSError, ValueError, TypeError, ImportError) as exc:
        return {"status": "unavailable", "readable": False, "reason": str(exc),
                "next": "Host AI must locate a usable licensed Chinese font and pass --font; do not ask the user to run installation commands or draw text with an image model."}


def _execute_browser(command: list[str], *, timeout: int = 180):
    """Bound only the browser processes launched by this runner, including timeout cleanup."""
    options = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True}
    if os.name == "posix":
        options["start_new_session"] = True
    elif os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    process = subprocess.Popen(command, **options)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            elif os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=10, check=False)
            else:
                process.kill()
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        raise


def _browser(state: dict, workspace: Path, key: str, html: Path, *, browser: str | None,
             disabled: bool, card_only: bool = False) -> dict:
    binary = _browser_binary(browser)
    html_before = _sha(html)
    dependency = digest({"html": html_before, "resources": _resources(),
                         "binary": binary, "binary_stat": [Path(binary).stat().st_size, Path(binary).stat().st_mtime_ns] if binary and Path(binary).is_file() else None,
                         "python": sys.executable, "disabled": disabled})
    old = state["stages"].get(key, {})
    if disabled:
        result = {"status": "skipped", "reason": "Browser checks explicitly disabled; dynamic rendering is unverified.", "attempts": 0}
    elif importlib.util.find_spec("playwright") is None:
        result = {"status": "unavailable", "reason": "Playwright is unavailable in this Python environment.", "attempts": 0}
    elif binary and not Path(binary).is_file():
        result = {"status": "unavailable", "reason": "Requested browser executable is unavailable.", "attempts": 0}
    elif old.get("dependency") == dependency and old.get("status") == "passed" and old.get("input_html_sha256") == html_before and old.get("report_input_bound") is True and _intact(workspace, old):
        old["reused"] = True
        return old
    else:
        attempts = old.get("attempts", 0) if old.get("dependency") == dependency else 0
        if attempts >= MAX_ATTEMPTS:
            result = {**old, "status": "blocked", "reused": False}
        else:
            out = workspace / "browser" / key
            out.mkdir(parents=True, exist_ok=True)
            report_path = out / "report.json"
            # Discard any earlier or externally placed report before executing.
            report_path.unlink(missing_ok=True)
            command = ([sys.executable, "-c", _CARD_BROWSER, str(html), str(out), binary or ""] if card_only else
                       [sys.executable, str(ROOT / "scripts/verify_browser.py"), "--html", str(html), "--out", str(out)] +
                       (["--browser", binary] if binary else []))
            try:
                process = _execute_browser(command)
                report = load(report_path) if report_path.is_file() else {}
                checks = report.get("checks", [])
                input_unchanged = html.is_file() and _sha(html) == html_before
                report_input_bound = report.get("html_sha256") == html_before
                passed = input_unchanged and report_input_bound and process.returncode == 0 and report.get("ok") is True and bool(checks) and all(
                    isinstance(item, dict) and item.get("passed") is True for item in checks)
                failure = str(report.get("failure", "") or process.stderr[-1800:] or process.stdout[-1800:])
                if not input_unchanged:
                    failure = "HTML changed during browser execution; this report cannot verify the current output."
                elif process.returncode == 0 and report.get("ok") is True and not report_input_bound:
                    failure = "Browser report is missing or mismatches the actual input HTML hash."
                unavailable = not checks and any(message in failure.lower() for message in (
                    "executable doesn't exist", "executable does not exist", "browser executable not found",
                    "missing dependencies", "error while loading shared libraries", "operation not permitted",
                    "permission denied", "no module named 'playwright'", "browsertype.launch", "kill eperm"))
                result = {"status": "passed" if passed else "unavailable" if unavailable else "failed",
                          "attempts": attempts if passed or unavailable else attempts + 1, "reused": False,
                          "input_html_sha256": html_before, "input_unchanged": input_unchanged, "invoked_by_runner": True,
                          "report_input_bound": report_input_bound,
                          "exit_code": process.returncode, "report": str(report_path), "checks": checks,
                          "webgl_verified": passed and report.get("webgl") is True,
                          "interaction_verified": passed and (report.get("interaction_verified") is True if card_only else True),
                          "scope": report.get("scope", "Fixed HTML browser script; desktop and emulated mobile only."),
                          "limits": report.get("not_tested", ["Visual art quality", "generation provenance", "real-device performance"])}
                if not passed:
                    result["reason"] = failure[:2000]
                if report_path.is_file():
                    result["files_sha256"] = _fingerprints(workspace, [str(report_path.relative_to(workspace))])
            except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as exc:
                result = {"status": "failed", "attempts": attempts + 1, "reused": False, "reason": str(exc)[:2000]}
    result["dependency"] = dependency
    state["stages"][key] = result
    save(workspace / "run-state.json", state)
    return result


def _run_mechanical(input_path: Path, workspace: Path, *, mode: str = "both", layers: Path | None = None,
        art_prompt_file: Path | None = None, browser: str | None = None, no_browser: bool = False,
        font: Path | None = None, _review_gate=None) -> dict:
    """Internal mechanical checks only; use run() for production delivery. Build/verify independent modules, then integrate only current-person native art."""
    from . import lite, site
    from .art import validate_layers
    from .cardgen import card_spec, read_card_data
    from .template_origin import verify_site

    check(mode in ("html", "card", "both"), "Unsupported run mode")
    input_path, workspace = input_path.resolve(), workspace.resolve()
    check(input_path.is_file(), "Current-person input file is missing")
    raw = input_path.read_bytes()
    input_sha = hashlib.sha256(raw).hexdigest()
    state_file = workspace / "run-state.json"
    if state_file.exists():
        state = load(state_file)
        check(isinstance(state, dict) and state.get("schema_version") == STATE_VERSION, "Unsupported run state")
        check(state.get("mode") == mode, "This workspace belongs to another requested mode; use a new workspace.")
        check(state.get("input_sha256") == input_sha, "This workspace belongs to another input revision; use a new workspace.")
        check((workspace / "content.json").is_file() and _sha(workspace / "content.json") == input_sha,
              "Read-only content.json was changed; use a new workspace and the intended source.")
    else:
        check(not workspace.exists() or not any(workspace.iterdir()), "New run workspace must be empty")
        workspace.mkdir(parents=True, exist_ok=True)
        state = {"schema_version": STATE_VERSION, "version": VERSION, "mode": mode, "input_sha256": input_sha,
                 "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                 "stages": {}}
        (workspace / "content.json").write_bytes(raw)
        save(state_file, state)
    content = workspace / "content.json"
    data = read_card_data(content)
    if mode != "card":
        check(data.get("twinlight") == "lite-1", "HTML mode requires Lite content with current-person themes")
    state["mode"] = mode
    state["version"] = VERSION
    state["persona_digest"] = lite.persona_digest(data)
    resources = _resources()
    dep = digest({"input": input_sha, "resources": resources, "generated_at": state["created_at"]})
    outputs, selected, dynamic = {}, [], []
    resume = [sys.executable, str(ROOT / "scripts/twinlight.py"), "run", str(input_path),
              "--workspace", str(workspace), "--mode", mode]
    if browser:
        resume += ["--browser", browser]
    if no_browser:
        resume += ["--no-browser"]
    if art_prompt_file:
        resume += ["--art-prompt-file", str(art_prompt_file.resolve())]
    if font:
        resume += ["--font", str(font.resolve())]
    next_action = None

    def build_html(folder: str, native: Path | None = None):
        if native is not None:
            require_sources()
        report = site.build_lite(data, workspace / folder, generated_at=state["created_at"], layers=native, confirmed=False)
        if native is not None:
            require_sources()
        return report

    def site_files(folder: str) -> list[str]:
        return [folder + "/" + name for name in ("index.html", "compiled-check.js", "profile.json", "render-inputs.json", "template-receipt.json", "build-report.json")]

    if mode != "card":
        html = _stage(state, workspace, "html", dep, lambda: build_html("site"), site_files("site"),
                      validate=lambda: verify_site(workspace / "site"))
        selected.append(html)
        if html["status"] == "files_ready":
            outputs["html"] = str(workspace / "site/index.html")
            dynamic.append(_browser(state, workspace, "html_browser", workspace / "site/index.html", browser=browser, disabled=no_browser))

    native = None
    if mode != "html":
        if layers is None and state.get("layers_source"):
            layers = Path(state["layers_source"])
        if layers is not None:
            layers = layers.resolve()
            state["layers_source"] = str(layers)
            art_source = _art_dependency(layers) if layers.is_file() else "missing"
            art_dep = digest({"run": dep, "art": art_source})

            def sources_unchanged():
                try:
                    return layers.is_file() and _art_dependency(layers) == art_source
                except (OSError, ValueError, TypeError):
                    return False

            def require_sources():
                check(sources_unchanged(), "Native source layers changed during this run; card and integration must be rebuilt from one stable input revision.")

            def source_gate():
                unchanged = sources_unchanged()
                return {"ok": unchanged, "errors": [] if unchanged else [{"code": "native_source_changed"}]}

            def make_card():
                from package_card import package
                from preview_card import preview
                require_sources()
                report = validate_layers(layers, state["persona_digest"])
                check(report["art_status"] in ("generated", "approved"), "Placeholder or static art cannot complete a native card")
                rendered = site.render_card_preview(data, workspace / "card/front.png", layers=layers)
                viewed = preview(layers, workspace / "card/preview.html", content)
                packed = package(layers, workspace / "card/card-pack.json", content)
                require_sources()
                return {"render": rendered, "preview": viewed, "package": packed, "art_validation": report,
                        "native_source_sha256": art_source}

            card = _stage(state, workspace, "card", art_dep, make_card,
                          ["card/front.png", "card/preview.html", "card/card-pack.json"], validate=source_gate)
            selected.append(card)
            if card["status"] == "files_ready":
                native = layers
                outputs.update(card_preview=str(workspace / "card/preview.html"), card_front=str(workspace / "card/front.png"),
                               card_pack=str(workspace / "card/card-pack.json"))
                dynamic.append(_browser(state, workspace, "card_browser", workspace / "card/preview.html", browser=browser,
                                        disabled=no_browser, card_only=True))
                if _review_gate is not None:
                    art_review = _review_gate(content, layers, workspace, state["persona_digest"])
                    state["stages"]["art_quality"] = art_review
                    if art_review.get("ok") is not True:
                        # Keep inspectable candidates, but never integrate unreviewed artwork.
                        native = None
        else:
            (workspace / "card").mkdir(exist_ok=True)
            typography = _font_preflight(font)
            state["stages"]["typography_preflight"] = {**typography, "attempts": 0}
            if art_prompt_file is not None or data["card"].get("art_prompt"):
                brief_dep = digest({"run": dep, "brief": _sha(art_prompt_file) if art_prompt_file and art_prompt_file.is_file()
                                    else "missing" if art_prompt_file else data["card"].get("art_prompt")})

                def make_brief():
                    prompt = art_prompt_file.read_text(encoding="utf-8") if art_prompt_file else data["card"].get("art_prompt")
                    spec = card_spec(data, generated_at=state["created_at"], art_prompt=prompt)
                    save(workspace / "card/card-spec.json", spec)
                    save(workspace / "card/manifest-template.json", spec["manifest_template"])
                    return {"persona_digest": spec["persona_digest"], "generation_status": "brief_only"}

                brief = _stage(state, workspace, "card_brief", brief_dep, make_brief,
                               ["card/card-spec.json", "card/manifest-template.json"])
                if brief["status"] == "files_ready":
                    next_action = {"type": "generate_native_layers", "card_spec": str(workspace / "card/card-spec.json"),
                                   "typography_font": typography, "image_capability": "unknown_required",
                                   "manifest_template": str(workspace / "card/manifest-template.json"),
                                   "read": [str(ROOT / "CARD.md"), str(ROOT / "prompts/card-generation.md")],
                                   "resume": resume + ["--layers", str(workspace / "card/layers.json")],
                                   "constraints": ["Use actual image tools and one current-person prototype.",
                                                   "No cutout, crop, resize or duplicate poster layers.",
                                                   "Do not treat the template manifest or a placeholder as generated art."]}
                else:
                    selected.append(brief)
            else:
                next_action = {"type": "prepare_art_direction", "out": str(workspace / "card/art-direction.txt"),
                               "typography_font": typography, "image_capability": "unknown_required",
                               "read": [str(ROOT / "references/art-direction.md")],
                               "resume": resume + ["--art-prompt-file", str(workspace / "card/art-direction.txt")],
                               "constraints": ["Author an independent 20–1500 character brief from current authorized content and preferences."]}
            state["stages"]["card"] = {"status": "needs_card", "attempts": 0,
                                       "reason": "Native current-person image layers have not been supplied."}
            selected.append(state["stages"]["card"])

    if mode == "both" and native is not None:
        def verify_integration():
            gate = verify_site(workspace / "site-with-card")
            if not sources_unchanged():
                gate["ok"] = False
                gate.setdefault("errors", []).append({"code": "native_source_changed"})
            return gate

        joined = _stage(state, workspace, "integration", art_dep, lambda: build_html("site-with-card", native),
                        site_files("site-with-card"), validate=verify_integration)
        selected.append(joined)
        if joined["status"] == "files_ready":
            outputs["html_with_card"] = str(workspace / "site-with-card/index.html")
            dynamic.append(_browser(state, workspace, "integration_browser", workspace / "site-with-card/index.html",
                                    browser=browser, disabled=no_browser))
    # Browser/image tools run after builds. Recheck the final files before
    # reporting links, so a mid-check rewrite cannot inherit an earlier gate.
    owners = {"html": "html", "card_preview": "card", "card_front": "card", "card_pack": "card",
              "html_with_card": "integration"}
    for key, folder in (("html", "site"), ("card", None), ("integration", "site-with-card")):
        item = state["stages"].get(key)
        if item is None or item.get("status") != "files_ready" or not any(item is entry for entry in selected):
            continue
        gate = verify_site(workspace / folder) if folder else {"ok": True}
        if key in ("card", "integration") and not sources_unchanged():
            gate["ok"] = False
            gate.setdefault("errors", []).append({"code": "native_source_changed"})
        if not _intact(workspace, item) or not gate.get("ok"):
            item.update(status="failed", attempts=item.get("attempts", 0) + 1,
                        error="Final artifact changed or failed independent verification after execution.",
                        files_sha256={}, verification=gate)
            outputs = {name: path for name, path in outputs.items() if owners.get(name) != key}
    failures = [item for item in selected + dynamic if item["status"] in ("failed", "blocked")]
    ready = any(item["status"] == "files_ready" for item in selected)
    if failures:
        status = "partial_success" if ready else "failed"
        pending_actions = [next_action] if next_action else []
        current_stages = {id(item) for item in selected + dynamic}
        next_action = {"type": "repair", "failed_stages": [name for name, value in state["stages"].items()
                       if id(value) in current_stages and value.get("status") in ("failed", "blocked")], "resume": resume,
                       "pending_actions": pending_actions, "continue_independent_modules": True,
                       "constraints": ["Repair the actual error; do not write passed into state or fabricate browser reports."]}
    elif any(item["status"] == "needs_card" for item in selected):
        status = "needs_card"
    elif any(item["status"] != "passed" for item in dynamic):
        status = "dynamic_unverified"
        next_action = {"type": "review_browser", "resume": [arg for arg in resume if arg != "--no-browser"],
                       "constraints": ["Use actual browser execution; do not claim WebGL or interaction validation from file hashes."]}
    else:
        status = "files_ready"
    result = {"ok": not failures, "status": status, "mode": mode, "workspace": str(workspace), "outputs": outputs,
              "next_action": next_action, "stages": state["stages"], "text_confirmed": False,
              "dynamic_verified": not failures and bool(dynamic) and all(item["status"] == "passed" for item in dynamic),
              "quality_verified": False, "generation_provenance_verified": False,
              "limits": ["Host authors personal content and performs actual native image generation.",
                         "Mechanical checks do not establish factual accuracy, art quality or image-generation provenance.",
                         "Browser evidence covers this local run only; other AI websites and physical devices are unverified.",
                         "Files remain private, unconfirmed drafts; no publishing or share approval is inferred."]}
    result["complete"] = False  # Only the public delivery gate may mark a request complete.
    result["mechanical_only"] = _review_gate is None
    save(state_file, state)
    save(workspace / "run-report.json", result)
    return result


def run(input_path: Path, workspace: Path, *, mode: str = "both", layers: Path | None = None,
        art_prompt_file: Path | None = None, browser: str | None = None, no_browser: bool = False,
        font: Path | None = None) -> dict:
    """Default production route: mechanical files, source evidence and visual review gates."""
    from .delivery import deliver
    return deliver(_run_mechanical, input_path, workspace, mode=mode, layers=layers,
                   art_prompt_file=art_prompt_file, browser=browser, no_browser=no_browser, font=font)
