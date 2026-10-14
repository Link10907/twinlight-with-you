"""Upstream-only style choice. Never redraw, layer, render, or rewrite art prompts.

New works default to a uniform draw from all installed styles. Explicit choices
win; a user-requested filtered draw remains available. This module validates the
request, draws once, and projects the existing drawing-only input.
A frozen selection is reused on resume; it is not an aesthetic approval.
"""
from __future__ import annotations

import copy
import json
import os
import secrets
import tempfile
from pathlib import Path

from .common import ROOT, check, digest, load
from .card_context import validate_input, preset
from .visual_contract import catalog, style_for, style_references, sha256

REQUEST_VERSION = 'style-selection-request-1'
VERSION = 'style-selection-1'
ALGORITHM = 'sha256-rejection-v1'
MODES = ('explicit', 'random', 'subject_random')
RECORD = 'style-selection.json'
DRAWING = 'card-image-input.json'


def _normalize(request: dict, *, frozen: bool = False) -> dict:
    check(isinstance(request, dict), 'Style request must be an object')
    allowed = {'version', 'mode', 'style', 'candidates', 'reason', 'seed', 'subject', 'scene'}
    check(not set(request) - allowed, 'Unknown upstream style request field')
    check(request.get('version') == REQUEST_VERSION, 'Unsupported upstream style request version')
    mode = request.get('mode', 'random')
    check(mode in MODES, 'Use explicit, random or subject_random')
    selected = request.get('style')
    # An explicitly supplied versioned style takes precedence over random defaults.
    if selected is not None:
        check(isinstance(selected, dict) and set(selected) == {'id', 'version'}, 'Explicit style needs id and version only')
        style_for(selected['id'], selected['version'])
        mode = 'explicit'
    check(mode != 'explicit' or selected is not None, 'Explicit mode requires a versioned style')
    installed = {s['id']: s for s in catalog()}
    supplied = request.get('candidates')
    candidates = supplied if supplied is not None else sorted(installed)
    check(isinstance(candidates, list) and bool(candidates), 'Candidates must be a nonempty list')
    check(all(isinstance(s, str) and s in installed for s in candidates), 'Unknown candidate; do not silently fall back to collector')
    check(len(candidates) == len(set(candidates)), 'Candidates must not repeat')
    if selected is not None:
        check(supplied is None or selected['id'] in candidates, 'Explicit style conflicts with the supplied candidate constraints')
        candidates = [selected['id']]
    elif mode == 'random':
        check(frozen or set(candidates) == set(installed),
              'Random mode uses all installed styles; use explicit subject_random for a user-requested subset')
    elif mode == 'subject_random':
        check(len(candidates) >= 2, 'Keep at least two subject-compatible styles; use explicit mode for a single choice')
    reason = request.get('reason', '')
    check(isinstance(reason, str) and len(reason) <= 600, 'Selection reason must be a short private string')
    if mode == 'subject_random' and supplied is None and not reason.strip():
        reason = 'No narrower visual constraints supplied; all installed styles remain eligible.'
    if mode == 'subject_random' and supplied is not None:
        check(bool(reason.strip()), 'The host must explain its subject-based candidate selection')
    seed = request.get('seed')
    check(seed is None or isinstance(seed, str) and bool(seed.strip()) and len(seed) <= 128,
          'Optional seed must be a nonempty string of at most 128 characters')
    subject, scene = request.get('subject'), request.get('scene')
    validation_style = installed[candidates[0]]
    validate_input({'version': 'card-image-input-1',
                    'style': {k: validation_style[k] for k in ('id', 'version')},
                    'subject': subject, 'scene': scene})
    return copy.deepcopy({'version': REQUEST_VERSION, 'mode': mode, 'style': selected,
                          'candidates': sorted(candidates), 'reason': reason,
                          'seed': seed, 'subject': subject, 'scene': scene})


def _choice(candidates: list[str], seed: str) -> str:
    """Deterministic draw, with rejection to avoid modulo bias."""
    limit = (1 << 256) - (1 << 256) % len(candidates)
    counter = 0
    while True:
        value = int(digest({'algorithm': ALGORITHM, 'seed': seed,
                            'candidates': candidates, 'counter': counter}), 16)
        if value < limit:
            return candidates[value % len(candidates)]
        counter += 1


def _resolve(request: dict, seed: str) -> dict:
    if request['mode'] == 'explicit':
        return copy.deepcopy(request['style'])
    s = style_for(_choice(request['candidates'], seed))
    return {k: s[k] for k in ('id', 'version')}


def _drawing(request: dict, selected: dict) -> dict:
    return validate_input({'version': 'card-image-input-1', 'style': copy.deepcopy(selected),
                           'subject': copy.deepcopy(request['subject']), 'scene': copy.deepcopy(request['scene'])})


def _binding(selected: dict) -> dict:
    s = style_for(selected['id'], selected['version'])
    preset(selected)  # A name alone is not an installed, maintained drawing preset.
    refs = style_references(s)
    return {'style_sha256': s['sha256'],
            'presets_sha256': sha256(ROOT / 'assets/art-styles/image-presets.json'),
            'reference_sha256': [r['sha256'] for r in refs]}


def _content_binding(workspace: Path) -> str | None:
    state = workspace / 'portable-state.json'
    return load(state).get('input_sha256') if state.is_file() else None


def _legacy_art_started(workspace: Path) -> bool:
    for name in ('generation.json', 'image-attempts.json', 'art-direction.json', 'generation-plan.json'):
        if (workspace / name).exists():
            return True
    card = workspace / 'card-task'
    if card.exists() and any(p.is_file() for p in card.rglob('*')):
        return True
    state = workspace / 'portable-state.json'
    return bool(load(state).get('layers_path')) if state.is_file() else False


def _write_once(path: Path, value: dict) -> None:
    """Publish complete bytes exclusively; concurrent callers cannot overwrite."""
    check(not path.is_symlink(), 'Refuse a symlink in the frozen style outputs')
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='.style-', delete=False) as stream:
        tmp = Path(stream.name)
        try:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        os.link(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _ensure_drawing(workspace: Path, drawing: dict, *, restore: bool) -> None:
    path = workspace / DRAWING
    check(not path.is_symlink(), 'Refuse a symlink in the frozen drawing input')
    if not path.exists() and restore:
        try:
            _write_once(path, drawing)
        except FileExistsError:
            pass
    check(path.is_file(), 'Frozen drawing input missing; rerun select-style to restore the same choice')
    check(load(path) == drawing, 'Frozen drawing input changed; do not reselect or overwrite an existing card')


def _read(workspace: Path, *, restore: bool = False) -> dict:
    path = workspace / RECORD
    check(not path.is_symlink(), 'Refuse a symlink in the style selection record')
    r = load(path, max_bytes=32 * 1024)
    check(isinstance(r, dict) and r.get('version') == VERSION and r.get('algorithm') == ALGORITHM,
          'Invalid frozen style selection')
    check(r.get('record_sha256') == digest({k: v for k, v in r.items() if k != 'record_sha256'}),
          'Style record changed; preserve the original run')
    request = _normalize(r['request'], frozen=True)
    check(request == r['request'] and digest(request) == r['request_sha256'], 'Frozen style request changed')
    seed = r.get('seed')
    check(isinstance(seed, str) and 0 < len(seed) <= 128, 'Invalid frozen seed')
    check(request['seed'] is None or request['seed'] == seed, 'Frozen seed differs from the requested seed')
    selected = _resolve(request, seed)
    check(selected == r['selected_style'], 'Frozen random result or explicit style changed')
    check(_binding(selected) == r['style_binding'], 'Selected style/preset/reference changed; do not silently substitute resources')
    if r.get('content_sha256') is not None:
        check(_content_binding(workspace) == r['content_sha256'], 'Selection belongs to a different frozen content run')
    drawing = _drawing(request, selected)
    check(digest(drawing) == r['drawing_sha256'], 'Frozen drawing binding changed')
    _ensure_drawing(workspace, drawing, restore=restore)
    return r


def _summary(workspace: Path, r: dict, reused: bool) -> dict:
    # Return resolved inputs only. Selection policy and history stay in RECORD.
    return {'ok': True, 'status': 'frozen', 'reused': reused,
            'selected_style': copy.deepcopy(r['selected_style']),
            'drawing_input': str(workspace / DRAWING),
            'style_reference_images': style_references(style_for(r['selected_style']['id'], r['selected_style']['version']))}


def select(workspace: Path, request: dict) -> dict:
    """Freeze once or reuse; never mutate a prior image, layer or drawing input."""
    workspace = Path(workspace)
    if (workspace / RECORD).exists() or (workspace / RECORD).is_symlink():
        r = _read(workspace, restore=True)
        # An omitted mode must not migrate an older frozen default on resume.
        if isinstance(request, dict) and 'mode' not in request and request.get('style') is None:
            request = {**request, 'mode': r['request']['mode']}
        normalized = _normalize(request, frozen=True)
        check(digest(normalized) == r['request_sha256'],
              'Selection is frozen; changed subject, candidates, seed or style requires a new workspace')
        return _summary(workspace, r, True)
    normalized = _normalize(request)
    check(not _legacy_art_started(workspace), 'Artwork already started without this selector; resume its original style, do not retrofit random selection')
    seed = normalized['seed'] if normalized['seed'] is not None else secrets.token_hex(16)
    selected = _resolve(normalized, seed)
    drawing = _drawing(normalized, selected)
    r = {'version': VERSION, 'algorithm': ALGORITHM, 'request': normalized,
         'request_sha256': digest(normalized), 'seed': seed, 'selected_style': selected,
         'drawing_sha256': digest(drawing), 'style_binding': _binding(selected),
         'content_sha256': _content_binding(workspace)}
    r['record_sha256'] = digest(r)
    path = workspace / DRAWING
    check(not path.is_symlink(), 'Refuse a symlink in the frozen drawing input')
    if path.exists():
        check(load(path) == drawing, 'Existing drawing input has another style/subject; do not overwrite it')
    try:
        _write_once(workspace / RECORD, r)
    except FileExistsError:
        return select(workspace, request)
    _ensure_drawing(workspace, drawing, restore=True)
    return _summary(workspace, r, False)


def selection_status(workspace: Path) -> dict:
    """A host instruction, not another drawing prompt or a forced art migration."""
    workspace = Path(workspace)
    if (workspace / RECORD).exists() or (workspace / RECORD).is_symlink():
        return _summary(workspace, _read(workspace), True)
    if _legacy_art_started(workspace):
        return {'status': 'reuse_existing_artwork', 'reselect': False,
                'instruction': 'Keep the existing design/prototype style. Do not restart accepted work to add a selection record.'}
    return {'status': 'selection_required', 'default_mode': 'random',
            'styles': [{k: s[k] for k in ('id', 'name', 'version')} for s in catalog()],
            'guide': str(ROOT / 'references/style-selection.md'),
            'instruction': 'Honor an explicit installed style first. Otherwise draw once uniformly from all installed styles with portable.py select-style; do not filter by biography or subject. Use subject_random only for a user-requested narrower pool. Reuse the frozen drawing input for every repair; do not send selection metadata to the image tool.'}
