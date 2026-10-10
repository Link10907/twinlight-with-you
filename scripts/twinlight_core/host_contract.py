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
# Product requirements, not operating-system access-control requirements.
REVIEW_FLAGS = ('isolated_session', 'visual_inputs')
REVIEW_AUDIT_FLAGS = ('read_only_inputs', 'runtime_evidence')


def template() -> dict:
    return {'version': VERSION, 'host': '', 'producer_session_id': None,
            'image': {'version': 'image-capabilities-1', 'tool': '', 'source': '',
                      **{k: None for k in IMAGE_FLAGS}, 'prompt_transport': 'unknown',
                      'reference_transport': 'unknown', 'native_canvases': [],
                      'canvas_selection': 'unknown'},
            'reviewer': {'tool': '', 'source': '', **{k: None for k in REVIEW_FLAGS + REVIEW_AUDIT_FLAGS}},
            'runtime': {'browser': None, 'webgl': None, 'source': ''},
            'in_chat_preview': {'available': None, 'source': ''}}


def _source(value: dict) -> bool:
    return isinstance(value.get('source'), str) and bool(value['source'].strip())


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
    if mode not in ('html', 'card', 'both', 'integrate'): raise ValueError('Unknown production mode')
    value = value if isinstance(value, dict) else {}
    gaps = []
    if value.get('version') != VERSION: gaps.append('host.version')
    for key in ('host',):
        if not isinstance(value.get(key), str) or len(value[key].strip()) < 2: gaps.append('host.' + key)
    reviewer = value.get('reviewer') if isinstance(value.get('reviewer'), dict) else {}
    for key in REVIEW_FLAGS:
        if reviewer.get(key) is not True: gaps.append('reviewer.' + key)
    if not isinstance(reviewer.get('tool'), str) or not reviewer['tool'].strip(): gaps.append('reviewer.tool')
    if not _source(reviewer): gaps.append('reviewer.source')
    runtime = value.get('runtime') if isinstance(value.get('runtime'), dict) else {}
    if runtime.get('browser') is not True: gaps.append('runtime.browser')
    if not _source(runtime): gaps.append('runtime.source')
    warnings = []
    deferred = []
    if not value.get('producer_session_id'):
        warnings.append('audit.producer_session_id_unavailable')
    if reviewer.get('read_only_inputs') is not True:
        warnings.append('audit.os_read_only_not_enforced_use_packet_hash_checks')
    if reviewer.get('runtime_evidence') is not True:
        deferred.append('review.actual_runtime_evidence')
    if mode != 'html':
        if mode != 'integrate':
            gaps.extend(image_gaps(value.get('image')))
        if runtime.get('webgl') is False: gaps.append('runtime.webgl')
        elif runtime.get('webgl') is not True: deferred.append('runtime.webgl_probe_at_preview')
    ok = not gaps
    return {'version': 'host-preflight-2', 'ok': ok, 'status': 'ready' if ok else 'capability_blocked',
            'mode': mode, 'gaps': gaps, 'warnings': warnings, 'deferred_checks': deferred,
            'review_policy': 'artifact_bound_independent_task',
            'release_authorized': False, 'may_start_image_calls': ok and mode in ('card', 'both'),
            'may_build_local_candidates': True, 'agent_invoked': False,
            'host_identity_authenticated': False,
            'scope': 'Production capability routing only. Platform IDs and enforced read-only access are optional audit metadata. Real independent visual review and runtime checks still gate release; this assessment does not authenticate a provider or authorize delivery.'}


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
