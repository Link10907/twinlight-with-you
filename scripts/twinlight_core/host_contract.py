"""Bounded host capability declarations. No tool calls or identity attestation.

Null/absent capability is unknown, never an implicit pass. The host obtains
facts from its live tools; the package cannot discover or create those tools.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

VERSION = 'host-capabilities-2'
IMAGE_FLAGS = ('image_generation', 'reference_images', 'native_transparency',
               'native_image_editing', 'post_image_continuation')
REVIEW_FLAGS = ('isolated_session', 'read_only_inputs', 'visual_inputs', 'runtime_evidence')


def template() -> dict:
    return {'version': VERSION, 'host': '', 'producer_session_id': '',
            'image': {'version': 'image-capabilities-1', 'tool': '', 'source': '',
                      **{k: None for k in IMAGE_FLAGS}, 'prompt_transport': 'unknown',
                      'reference_transport': 'unknown', 'native_canvases': [],
                      'canvas_selection': 'unknown'},
            'reviewer': {'tool': '', 'source': '', **{k: None for k in REVIEW_FLAGS}},
            'runtime': {'browser': None, 'webgl': None, 'source': ''},
            'in_chat_preview': {'available': None, 'source': ''}}


def _source(value: dict) -> bool:
    return isinstance(value.get('source'), str) and len(value['source'].strip()) >= 12


def image_gaps(value: dict) -> list[str]:
    if not isinstance(value, dict):
        return ['image.capabilities_missing']
    gaps = ['image.' + k for k in IMAGE_FLAGS if value.get(k) is not True]
    if value.get('version') != 'image-capabilities-1': gaps.append('image.version')
    if value.get('prompt_transport') not in ('explicit_prompt', 'isolated_task_context'):
        gaps.append('image.prompt_transport')
    if value.get('reference_transport') not in ('explicit_attachments', 'isolated_task_context'):
        gaps.append('image.reference_transport')
    if not isinstance(value.get('tool'), str) or not value['tool'].strip(): gaps.append('image.tool')
    if not _source(value): gaps.append('image.source')
    sizes = value.get('native_canvases')
    if not isinstance(sizes, list) or any(not isinstance(s, list) or len(s) != 2 or
        any(type(n) is not int or n < 1 for n in s) for s in sizes):
        gaps.append('image.native_canvases')
    elif value.get('canvas_selection') != 'prompt_only' and not any(
        min(s) >= 256 and abs(s[0] / s[1] - .75) < .01 for s in sizes):
        gaps.append('image.portrait_canvas')
    return gaps


def assess(value: dict, mode: str = 'both') -> dict:
    if mode not in ('html', 'card', 'both'): raise ValueError('Unknown production mode')
    value = value if isinstance(value, dict) else {}
    gaps = []
    if value.get('version') != VERSION: gaps.append('host.version')
    for key in ('host', 'producer_session_id'):
        if not isinstance(value.get(key), str) or len(value[key].strip()) < 2: gaps.append('host.' + key)
    reviewer = value.get('reviewer') if isinstance(value.get('reviewer'), dict) else {}
    for key in REVIEW_FLAGS:
        if reviewer.get(key) is not True: gaps.append('reviewer.' + key)
    if not isinstance(reviewer.get('tool'), str) or not reviewer['tool'].strip(): gaps.append('reviewer.tool')
    if not _source(reviewer): gaps.append('reviewer.source')
    runtime = value.get('runtime') if isinstance(value.get('runtime'), dict) else {}
    if runtime.get('browser') is not True: gaps.append('runtime.browser')
    if not _source(runtime): gaps.append('runtime.source')
    if mode != 'html':
        gaps.extend(image_gaps(value.get('image')))
        if runtime.get('webgl') is not True: gaps.append('runtime.webgl')
    ok = not gaps
    return {'version': 'host-preflight-2', 'ok': ok, 'status': 'ready' if ok else 'capability_blocked',
            'mode': mode, 'gaps': gaps, 'may_start_image_calls': ok and mode != 'html',
            'may_build_local_candidates': True, 'agent_invoked': False,
            'host_identity_authenticated': False,
            'scope': 'Consistency of explicit host declarations; not proof of provider capabilities, permissions or successful artwork.'}


def load_assessment(path: Path | None, mode: str) -> dict:
    from .art_quality import read_json
    if path is None:
        return {**assess({}, mode), 'source': None, 'sha256': None}
    path = Path(path).resolve()
    try:
        data = read_json(path)
        return {**assess(data, mode), 'source': str(path),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    except (OSError, ValueError, TypeError) as exc:
        return {**assess({}, mode), 'source': str(path), 'sha256': None,
                'error': str(exc)}
