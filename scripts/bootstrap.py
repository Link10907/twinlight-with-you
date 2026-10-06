#!/usr/bin/env python3
"""Acquire a complete pinned resource tree, or check a local one. No model calls."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import importlib.util
import io
import json
import os
import re
import stat
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

REPOSITORY = 'Link10907/twinlight-with-you'
MAX_ARCHIVE = 40 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024
REQUIRED = (
    'SKILL.md', 'AGENT.md', 'PROMPT.md', 'CARD.md', 'requirements.txt', 'scripts/bootstrap.py',
    'prompts/html-build.md', 'prompts/card-generation.md',
    'scripts/art_quality.py', 'references/quality-workflow.md', 'references/art-evidence-format.md',
    'references/lite-content.md', 'references/art-direction.md', 'references/preview.md',
    'references/privacy.md', 'references/workflow.md', 'references/extraction.md',
    'references/layout.md', 'references/sources.md', 'references/quickstart.md',
    'references/fresh-generation-eval.md',
    'references/platform-adapters.md', 'assets/template/template-lock.json',
    'scripts/lock_template.py',
    'scripts/twinlight.py', 'scripts/prepare_card_layers.py',
    'scripts/package_card.py', 'scripts/preview_card.py', 'scripts/verify_browser.py',
    'requirements-dev.txt', 'assets/lite/lite.js',
    'assets/ai-history.json', 'assets/card-preview/page.html', 'assets/card-preview/style.css',
    'assets/card-preview/bootstrap.js',
)
CORE = ('__init__', 'art', 'cardgen', 'common', 'compiler', 'evidence', 'extraction',
        'history', 'layout', 'lite', 'report', 'showcase', 'site', 'state', 'template_origin', 'template_lock', 'run', 'art_quality', 'art_typography', 'delivery')
SCHEMAS = ('analysis', 'approval', 'art-direction', 'card-composition', 'card-input',
           'chunk-result', 'evidence-reference', 'history', 'layer-manifest', 'layout', 'lite')
TEMPLATE = ('adapter.css', 'adapter.js', 'app.js', 'card-art.svg', 'controls.js',
            'finale.js', 'holo-card.js', 'page.html', 'render.js', 'style.css',
            'v10.css', 'v10.js', 'v6.js', 'v7.css', 'v7.js', 'v8.css', 'v8.js', 'v9.css', 'v9.js')
REQUIRED += tuple('scripts/twinlight_core/' + name + '.py' for name in CORE)
REQUIRED += tuple('schemas/' + name + '.schema.json' for name in SCHEMAS)
REQUIRED += tuple('prompts/' + name + '.md' for name in ('00-intake', '01-extract', '02-reconcile', '03-narrative', '04-character-card', '05-review'))
REQUIRED += tuple('assets/template/src/' + name for name in TEMPLATE)
REQUIRED += tuple('assets/template/assets/' + name for name in ('another-light.mp3', 'dust-disc.jpg', 'stellar-atlas.jpg'))

# V2 visual-subject contract is part of the complete release, not optional prompts.
REQUIRED += (
    'schemas/art-direction-v2.schema.json', 'references/visual-contract.md', 'references/delivery-v2.md',
    'scripts/visual_plan.py', 'scripts/deliver_artifacts.py', 'scripts/verify_card_browser.py',
    'assets/art-styles/catalog.json',
)
REQUIRED += tuple('assets/art-styles/' + name + '.json' for name in
                  ('twinlight-collector', 'forest-fantasy', 'real-life-cinematic', 'eastern-fantasy-scroll', 'futuristic-clean', 'paper-craft-story'))
REQUIRED += ('assets/art-references/twinlight-collector/prototype.png',
             'assets/art-references/twinlight-collector/human-prototype.png',
             'assets/art-references/twinlight-collector/manifest.json',
             'assets/art-references/forest-fantasy.json')
REQUIRED += tuple('scripts/twinlight_core/' + name + '.py' for name in
                  ('visual_contract', 'generation_plan', 'embedded_card', 'export_delivery', 'canvas_mapping'))


def fetch(url: str, limit: int) -> bytes:
    request = urllib.request.Request(url, headers={'User-Agent': 'Twinlight-resource-bootstrap',
                                                  'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError('Resource response exceeds the size limit')
    return payload


def resolve_revision(revision: str | None) -> str:
    if revision is not None:
        if not re.fullmatch(r'[a-fA-F0-9]{40}', revision):
            raise ValueError('--revision requires a complete 40-character commit SHA')
        return revision.lower()
    result = json.loads(fetch('https://api.github.com/repos/' + REPOSITORY + '/commits/main', 1024 * 1024))
    return resolve_revision(result.get('sha', ''))


def unpack(payload: bytes, out: Path, revision: str) -> None:
    """Validate the entire archive before writing any file. Never overwrite a run."""
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError('Resource destination must be a new or empty directory')
    prefix = 'twinlight-with-you-' + revision + '/'
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        infos = archive.infolist()
        if len(infos) > 2000 or sum(entry.file_size for entry in infos) > MAX_EXPANDED:
            raise ValueError('Resource archive exceeds the expanded size limit')
        planned = []
        names = set()
        for entry in infos:
            if not entry.filename.startswith(prefix):
                raise ValueError('Archive does not match the requested revision')
            relative = entry.filename[len(prefix):]
            if not relative:
                continue
            path = PurePosixPath(relative)
            if '\\' in relative or path.is_absolute() or any(part in ('..', '.') for part in relative.split('/') if part):
                raise ValueError('Unsafe resource archive path')
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('Resource archive cannot contain symlinks')
            if not entry.is_dir():
                if relative in names:
                    raise ValueError('Duplicate resource archive path')
                names.add(relative)
                planned.append((entry, out.joinpath(*path.parts)))
        missing = set(REQUIRED) - names
        if missing:
            raise ValueError('Incomplete resource archive: ' + ', '.join(sorted(missing)))
        # Read and check CRCs before mutating the destination.
        contents = [(target, archive.read(entry)) for entry, target in planned]
    out.mkdir(parents=True, exist_ok=True)
    for target, content in contents:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def check_root(root: Path) -> dict:
    root = root.resolve()
    missing, hashes = [], {}
    for relative in REQUIRED:
        path = root / relative
        if not path.is_file() or not path.resolve().is_relative_to(root):
            missing.append(relative)
        else:
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    dependencies, unavailable = {}, []
    for module_name in ('jsonschema', 'PIL', 'playwright'):
        try:
            importlib.import_module(module_name)
            try:
                dependencies[module_name] = importlib.metadata.version('Pillow' if module_name == 'PIL' else module_name)
            except importlib.metadata.PackageNotFoundError:
                dependencies[module_name] = 'available'
        except ImportError:
            unavailable.append(module_name)
    runtime_ok = sys.version_info >= (3, 10) and not unavailable
    manifest = root / 'package-manifest.json'
    package_verified = None
    if manifest.exists():
        files = json.loads(manifest.read_text(encoding='utf-8'))['files_sha256']
        package_verified = bool(files) and all(
            (root / relative).resolve().is_relative_to(root) and (root / relative).is_file()
            and hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
            for relative, expected in files.items())
    locked = {'ok': False, 'errors': [{'code': 'template_lock_unavailable'}]}
    verifier = root / 'scripts/twinlight_core/template_lock.py'
    if verifier.is_file():
        try:
            spec = importlib.util.spec_from_file_location('twinlight_bootstrap_lock', verifier)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            sources = {name: value for name, value in hashes.items()
                       if name.startswith('assets/template/') and name != 'assets/template/template-lock.json'}
            locked = module.verify_lock(root / 'assets/template', sources)
        except (OSError, ValueError, TypeError, AttributeError, ImportError, SyntaxError):
            pass
    browser = browser_preflight()
    return {'ok': not missing and runtime_ok and package_verified is not False and locked['ok'],
            'resource_complete': not missing, 'resource_root': str(root),
            'required_files_sha256': hashes, 'missing_resources': missing,
            'package_manifest_verified': package_verified,
            'template_lock': locked,
            'runtime': {'python': sys.version.split()[0], 'minimum_python': '3.10',
                        'dependencies': dependencies, 'missing_dependencies': unavailable, 'ok': runtime_ok},
            'browser': browser,
            'ready_for_local_browser_checks': runtime_ok and browser['executable_available'],
            'scope': 'Resource/runtime and release-local template lock only; no HTML build, model analysis, image generation or visual verification.'}


def browser_preflight() -> dict:
    """Locate an existing browser without launching or downloading one."""
    configured = os.environ.get('TWINLIGHT_BROWSER')
    choices = ([configured] if configured else [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
        '/usr/lib/chromium/chromium', '/usr/bin/google-chrome',
        '/usr/bin/chromium', '/usr/bin/chromium-browser',
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    ])
    binary = next((str(Path(p).resolve()) for p in choices if Path(p).is_file()), None)
    if binary is None and not configured:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                cached = Path(playwright.chromium.executable_path)
                if cached.is_file():
                    binary = str(cached.resolve())
        except (ImportError, OSError, RuntimeError):
            pass
    return {'executable_available': binary is not None, 'executable': binary,
            'status': 'located_not_launched' if binary else 'unavailable',
            'next': None if binary else 'Host must locate an existing browser and pass --browser, or install the browser runtime when allowed before final validation.',
            'scope': 'Read-only capability preflight; no rendering, WebGL, sandbox or image-generation capability is implied.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--root', type=Path, help='Read-only check of an existing resource tree')
    choice.add_argument('--out', type=Path, help='Acquire into a new or empty resource directory')
    parser.add_argument('--revision', help='Immutable commit SHA; default resolves main once')
    args = parser.parse_args()
    try:
        if args.root:
            if args.revision:
                raise ValueError('--revision is only used with --out')
            report = check_root(args.root)
        else:
            revision = resolve_revision(args.revision)
            payload = fetch('https://codeload.github.com/' + REPOSITORY + '/zip/' + revision, MAX_ARCHIVE)
            unpack(payload, args.out, revision)
            report = check_root(args.out)
            report.update(repository=REPOSITORY, revision=revision,
                          archive_sha256=hashlib.sha256(payload).hexdigest())
            (args.out / 'resource-receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['ok'] else 2
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        print(json.dumps({'ok': False, 'error': str(exc), 'scope': 'Resource acquisition incomplete; do not substitute a rewritten HTML.'}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
