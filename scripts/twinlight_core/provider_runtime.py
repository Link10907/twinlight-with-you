"""Real, opt-in image and independent-vision transports. No implicit paid calls.

A request contains a single task and explicit image bytes. No history, previous
response ID, private credential files, shell interpolation, or production tools
are supplied to the vision API. Model names/endpoints are deployment settings.
"""
from __future__ import annotations
import base64
import hashlib
import io
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from PIL import Image
from .art_quality import parse_json, read_json, sha256

MAX_IMAGE = 24 * 1024 * 1024
MAX_RESPONSE = 80 * 1024 * 1024
IMAGE_KINDS = {'openai_images', 'command'}
REVIEW_KINDS = {'openai_responses', 'anthropic_messages', 'codex_exec', 'command'}


class ExecutionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str):
    raise ExecutionError(code, message)


def save_new(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    try: path.chmod(0o600)
    except OSError: pass


def model_name(cfg: dict) -> str:
    result = os.environ.get(cfg.get('model_env', ''), '') or cfg.get('model', '')
    if not isinstance(result, str) or not result.strip():
        fail('model_not_configured', 'Set a model in the local config or its named model_env; do not guess account access.')
    return result.strip()


def endpoint(cfg: dict, suffix: str) -> str:
    base = cfg.get('base_url', 'https://api.openai.com/v1').rstrip('/')
    p = urllib.parse.urlsplit(base)
    local = p.hostname in ('localhost', '127.0.0.1', '::1')
    if p.username or p.password or p.query or p.fragment or not p.hostname:
        fail('unsafe_endpoint', 'Use a clean provider base URL without credentials, query or fragment.')
    if p.scheme != 'https' and not (p.scheme == 'http' and local and cfg.get('allow_local_http') is True):
        fail('unsafe_endpoint', 'HTTPS is required; a loopback development server needs explicit allow_local_http.')
    return base + suffix


def image_input(path: Path) -> dict:
    path = Path(path).resolve()
    if not path.is_file() or not (0 < path.stat().st_size <= MAX_IMAGE):
        fail('image_size', 'Missing/oversized image: ' + path.name)
    data = path.read_bytes()
    with Image.open(io.BytesIO(data)) as im:
        if im.format not in ('PNG', 'JPEG', 'WEBP') or im.width * im.height > 16_000_000:
            fail('image_format', 'Use an actual PNG, JPEG or WebP with at most 16 million pixels.')
        mime = {'PNG':'image/png', 'JPEG':'image/jpeg', 'WEBP':'image/webp'}[im.format]
        im.verify()
    return {'name': path.name, 'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(),
            'mime_type': mime, 'data_url': 'data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii')}


def authorize(allowed: bool):
    if not allowed:
        fail('provider_calls_not_authorized', 'No model was called. Add --allow-provider-calls only for an already authorized provider/account; calls may consume quota or incur cost.')


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fail('provider_redirect', 'Provider redirected the request; configure the intended endpoint explicitly instead of forwarding credentials.')


def post_json(cfg: dict, suffix: str, body: dict, out: Path, *, allowed: bool) -> dict:
    authorize(allowed)
    url = endpoint(cfg, suffix)
    key_env = cfg.get('api_key_env', 'OPENAI_API_KEY')
    if not isinstance(key_env, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key_env):
        fail('key_env', 'api_key_env must name an environment variable, not contain a credential.')
    token = os.environ.get(key_env)
    if not token:
        fail('credential_missing', 'Set ' + key_env + ' in the execution environment. No credential file is read.')
    headers = {'Content-Type':'application/json', 'Accept':'application/json'}
    if cfg['kind'] == 'anthropic_messages':
        headers.update({'x-api-key':token, 'anthropic-version':'2023-06-01'})
    else:
        headers['Authorization'] = 'Bearer ' + token
    payload = json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
    request_file = out/'request.json'
    save_new(request_file, body)  # private per-call directory; never packaged in Skill artifacts
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        # No automatic HTTP retry: ambiguous timeouts must not cause duplicate image charges.
        with opener.open(urllib.request.Request(url, payload, headers, method='POST'),
                         timeout=float(cfg.get('timeout_seconds', 180))) as response:
            raw = response.read(MAX_RESPONSE + 1)
            request_id = response.headers.get('x-request-id') or response.headers.get('request-id')
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read(8192)
        # Keep a small sanitized receipt, not an echoed private request or authorization header.
        save_new(out/'transport-error.json', {'http_status':exc.code, 'body_sha256':hashlib.sha256(raw).hexdigest(),
                 'request_id':exc.headers.get('x-request-id'), 'automatic_retry':False})
        code = {401:'provider_authentication',403:'provider_access_denied',429:'provider_rate_limit'}.get(exc.code, 'provider_http_error')
        fail(code, f'Provider returned HTTP {exc.code}; no fallback purchase or retry was attempted. Check the configured account/model.')
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        save_new(out/'transport-error.json', {'error_type':type(exc).__name__, 'automatic_retry':False,
                  'outcome':'unknown; inspect provider usage before retrying'})
        fail('provider_connection', 'Provider connection failed/timed out. Outcome may be unknown; do not silently repeat the image call.')
    if len(raw) > MAX_RESPONSE:
        fail('response_too_large', 'Provider response exceeds the configured safety limit; it was not treated as artwork.')
    (out/'provider-response.raw.json').write_bytes(raw)
    try: result = parse_json(raw.decode('utf-8'))
    except (ValueError, UnicodeError): fail('provider_bad_json', 'Provider did not return valid JSON; raw bytes were retained.')
    if not isinstance(result, dict): fail('provider_bad_json', 'Expected a provider response object.')
    save_new(out/'transport.json', {'transport':'https' if url.startswith('https:') else 'loopback-http',
             'provider_kind':cfg['kind'], 'endpoint':url, 'http_status':status, 'request_id':request_id,
             'request_sha256':sha256(request_file), 'response_sha256':hashlib.sha256(raw).hexdigest(),
             'automatic_retry':False, 'provider_identity_authenticated':False})
    return result


def extract_json_text(text: str) -> dict:
    text = text.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == '```': text = '\n'.join(lines[1:-1])
    try: result = parse_json(text)
    except ValueError: fail('invalid_model_json', 'The independent task did not return a single JSON object. Do not repair its decision into a pass.')
    if not isinstance(result, dict): fail('invalid_model_json', 'Expected an independent JSON object.')
    return result


def _run(argv: list[str], payload: str, cwd: Path, timeout: float) -> tuple[str, str]:
    if not argv or not all(isinstance(x, str) for x in argv): fail('command_config', 'Command must be an argv array, never a shell string.')
    try:
        p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding='utf-8', cwd=str(cwd), start_new_session=os.name!='nt')
        try: stdout, stderr = p.communicate(payload, timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name != 'nt':
                try: os.killpg(p.pid, signal.SIGTERM)
                except ProcessLookupError: pass
            else: p.terminate()
            try: p.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                if os.name != 'nt':
                    try: os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                else: p.kill()
                p.communicate(timeout=5)
            fail('command_timeout', 'Independent provider process timed out. It was not retried or approved.')
    except FileNotFoundError:
        fail('command_not_installed', 'Configured executable is not installed: ' + argv[0])
    if p.returncode:
        # Do not print potentially sensitive provider stderr by default.
        fail('command_failed', f'Independent process exited {p.returncode}; no approval was imported. Check the selected executable/account.')
    if len(stdout.encode()) > MAX_RESPONSE: fail('response_too_large', 'Independent command output is too large.')
    return stdout, stderr


def command_call(cfg: dict, task: dict, out: Path, allowed: bool) -> dict:
    authorize(allowed)
    argv = cfg.get('argv')
    if not isinstance(argv, list) or not argv: fail('command_config', 'Provide the argv of an actual existing JSON-stdin provider.')
    save_new(out/'request.json', task)
    # This is a fresh process in a fresh directory. Never --resume or inherited chat history.
    stdout, stderr = _run(argv, json.dumps(task,ensure_ascii=False)+'\n', out, float(cfg.get('timeout_seconds',180)))
    (out/'provider-response.raw.json').write_text(stdout, encoding='utf-8')
    save_new(out/'transport.json', {'transport':'fresh-command','argv':argv,'stderr_sha256':hashlib.sha256(stderr.encode()).hexdigest(),
             'request_sha256':sha256(out/'request.json'),'response_sha256':sha256(out/'provider-response.raw.json'),
             'provider_identity_authenticated':False,'automatic_retry':False})
    return extract_json_text(stdout)


def generate(cfg: dict, prompt: str, paths: list[Path], canvas: list[int], transparent: bool,
             out: Path, *, allowed: bool) -> tuple[Path, dict]:
    authorize(allowed)
    images = [image_input(p) for p in paths]
    if not 1 <= len(images) <= 16: fail('reference_count', 'Send the actual 1–16 task reference images; no blank or fake references.')
    if not prompt.strip() or len(prompt) > 32000: fail('image_prompt', 'Single image prompt is empty or too long.')
    if len(canvas) != 2 or any(type(n) is not int or n < 256 for n in canvas): fail('canvas','Invalid native canvas.')
    if cfg['kind'] == 'openai_images':
        body = {'model':model_name(cfg), 'prompt':prompt,
                'images':[{'image_url':i['data_url']} for i in images],
                'size':f'{canvas[0]}x{canvas[1]}', 'background':'transparent' if transparent else 'opaque',
                'output_format':'png', 'n':1, 'quality':cfg.get('quality','high')}
        if cfg.get('input_fidelity') is not None: body['input_fidelity'] = cfg['input_fidelity']
        response = post_json(cfg, '/images/edits', body, out, allowed=allowed)
        data = response.get('data', [])
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0],dict) or not data[0].get('b64_json'):
            fail('image_response', 'Expected one base64 PNG, not a URL, webpage, contact sheet or text-only reply.')
        try: raw = base64.b64decode(data[0]['b64_json'], validate=True)
        except (ValueError, TypeError): fail('image_response', 'Invalid image base64; original response retained.')
    elif cfg['kind'] == 'command':
        task = {'version':'twinlight-provider-task-1','task':'image','prompt':prompt,
                'images':images,'canvas':canvas,'transparent':transparent,'output_directory':str(out)}
        response = command_call(cfg, task, out, allowed)
        path = Path(response.get('image_file',''))
        if not path.is_absolute(): path=out/path
        path=path.resolve()
        if not path.is_relative_to(out.resolve()) or not path.is_file(): fail('image_output_path', 'Command must return a new image_file inside this call directory.')
        raw=path.read_bytes()
    else: fail('image_backend', 'Unsupported image provider kind.')
    if not 0 < len(raw) <= MAX_IMAGE: fail('image_size', 'Returned artwork exceeds native image size limits.')
    original = out/'returned-image.png'
    # Keep rejected original bytes as evidence; no crop, scale, alpha repair or background painting.
    if original.exists():
        if original.read_bytes()!=raw: fail('image_output_collision','Returned image collides with another file.')
    else:
        with original.open('xb') as stream: stream.write(raw)
    try:
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            if im.format != 'PNG': fail('native_png', 'Provider must return a native PNG for the layer pipeline.')
            if any(abs(a-b)>1 for a,b in zip(im.size, canvas)): fail('native_canvas_mismatch', f'Returned {im.size}, requested {canvas}. Repair the native edit; never rescale to fake registration.')
            alpha=im.getchannel('A') if 'A' in im.getbands() else None
            if transparent and (alpha is None or alpha.getextrema()[0] == 255): fail('native_alpha_missing','Transparent layer request returned opaque pixels only; original retained, not approved.')
            if transparent and alpha.getextrema()[1] == 0: fail('empty_native_layer','Layer is fully transparent; not registered as completed artwork.')
            if not transparent and alpha is not None and alpha.getextrema()[0] != 255: fail('background_not_opaque','The background/prototype must be complete and opaque.')
            actual=list(im.size)
    except (OSError, Image.DecompressionBombError): fail('image_decode','Provider return is not a decodable native image.')
    receipt={'version':'executed-image-return-1','record_origin':'local_transport_receipt',
             'image':{'file':original.name,'sha256':sha256(original),'canvas':actual},
             'provider_response':{'file':'provider-response.raw.json','sha256':sha256(out/'provider-response.raw.json')},
             'request':{'file':'request.json','sha256':sha256(out/'request.json')},
             'tool':cfg['kind'],'native_bytes_modified':False,'provider_identity_authenticated':False}
    save_new(out/'image-receipt.json',receipt)
    return original, receipt


def vision(cfg: dict, instructions: str, paths: list[Path], out: Path, *, allowed: bool) -> dict:
    authorize(allowed)
    if not paths: fail('review_images_missing','A visual reviewer must receive actual image bytes, not just filenames.')
    if len(paths)>int(cfg.get('max_images',40)): fail('review_image_limit','Too many review images; make a focused evidence packet. No images were silently dropped.')
    images=[image_input(p) for p in paths]
    kind=cfg['kind']
    if kind=='openai_responses':
        content=[{'type':'input_text','text':instructions}]
        for im in images:
            content.extend([{'type':'input_text','text':'IMAGE '+im['name']+' SHA256 '+im['sha256']},
                            {'type':'input_image','image_url':im['data_url'],'detail':'high'}])
        body={'model':model_name(cfg),'store':False,'input':[{'role':'user','content':content}],
              'max_output_tokens':int(cfg.get('max_output_tokens',12000))}
        response=post_json(cfg,'/responses',body,out,allowed=allowed)
        if response.get('status') not in (None,'completed'): fail('incomplete_review','Independent model response is incomplete; no verdict imported.')
        texts=[]
        for item in response.get('output',[]):
            if item.get('type')=='message':
                for part in item.get('content',[]):
                    if part.get('type')=='refusal': fail('review_refused','Independent model declined this review.')
                    if part.get('type')=='output_text': texts.append(part['text'])
        return extract_json_text('\n'.join(texts))
    if kind=='anthropic_messages':
        content=[]
        for im in images:
            content.extend([{'type':'text','text':'IMAGE '+im['name']+' SHA256 '+im['sha256']},
                {'type':'image','source':{'type':'base64','media_type':im['mime_type'],'data':im['data_url'].split(',',1)[1]}}])
        content.append({'type':'text','text':instructions})
        response=post_json(cfg,'/messages',{'model':model_name(cfg),'max_tokens':int(cfg.get('max_output_tokens',12000)),
                 'messages':[{'role':'user','content':content}]},out,allowed=allowed)
        if response.get('stop_reason') not in ('end_turn','stop_sequence'): fail('incomplete_review','Independent review stopped before completing a verdict.')
        return extract_json_text('\n'.join(x['text'] for x in response.get('content',[]) if x.get('type')=='text'))
    if kind=='codex_exec':
        binary=cfg.get('executable','codex')
        exe=shutil.which(binary)
        if not exe: fail('reviewer_not_installed','No Codex executable found; configure an existing vision API or install/sign in explicitly.')
        try:
            help_run=subprocess.run([exe,'exec','--help'],capture_output=True,text=True,timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            fail('codex_cli_probe_failed','Could not inspect the installed Codex command; no review was attempted.')
        help_text=help_run.stdout+help_run.stderr
        for flag in ('--image','--sandbox','--output-last-message','--skip-git-repo-check'):
            if flag not in help_text: fail('codex_cli_incompatible','Installed Codex exec does not advertise '+flag+'; do not guess flags.')
        # Outside the production project: do not discover its AGENTS.md, Git tree,
        # producer sessions, or history through a shared working directory.
        with tempfile.TemporaryDirectory(prefix='twinlight-visual-review-') as temporary:
            isolated=Path(temporary).resolve()
            result_path=isolated/'model-result.txt'
            argv=[exe,'exec','--sandbox','read-only','--skip-git-repo-check','--output-last-message',str(result_path)]
            if '--ephemeral' in help_text: argv.append('--ephemeral')
            if cfg.get('ignore_user_config',False) and '--ignore-user-config' in help_text: argv.append('--ignore-user-config')
            if cfg.get('model') or os.environ.get(cfg.get('model_env',''), ''): argv.extend(['--model',model_name(cfg)])
            for i,im in enumerate(images):
                suffix={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}[im['mime_type']]
                target=isolated/f'input-{i:03d}{suffix}'
                shutil.copyfile(im['path'],target);argv.extend(['--image',str(target)])
            argv.append('-')
            save_new(out/'request.json',{'task':instructions,'images':[{k:v for k,v in im.items() if k!='data_url'} for im in images],
                     'argv':argv,'conversation_history_included':False,'resume':False,
                     'working_directory':'fresh system temporary directory outside production project'})
            stdout,stderr=_run(argv,instructions,isolated,float(cfg.get('timeout_seconds',180)))
            if not result_path.is_file(): fail('review_result_missing','Fresh Codex task returned no final-message file.')
            raw=result_path.read_text(encoding='utf-8')
            (out/'model-result.txt').write_text(raw,encoding='utf-8')
        save_new(out/'provider-response.raw.json',{'final_text':raw,'stdout':stdout,
                 'stderr_sha256':hashlib.sha256(stderr.encode()).hexdigest()})
        save_new(out/'transport.json',{'transport':'fresh-codex-exec','resume':False,'requested_sandbox':'read-only',
                 'provider_identity_authenticated':False,'argv':argv,'automatic_retry':False,
                 'production_working_directory_shared':False})
        return extract_json_text(raw)
    if kind=='command':
        return command_call(cfg,{'version':'twinlight-provider-task-1','task':'review','prompt':instructions,
                    'images':images,'output_directory':str(out),'conversation_history_included':False},out,allowed)
    fail('review_backend','Unsupported independent visual reviewer kind.')
