"""Validate a release-local template lock; never update it during a personal run.

This is reproducibility metadata, not a signature or an authenticated release.
Kept stdlib-only so URL bootstrap can check it before installing dependencies.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

LOCK_NAME = 'template-lock.json'
LOCK_SCHEMA = 'template-lock-1'


def verify_lock(template: Path, sources: dict[str, str], *,
                assembled_sha256: str | None = None,
                builder_version: str | None = None) -> dict:
    errors = []
    try:
        path = template / LOCK_NAME
        if path.is_symlink() or not path.resolve().is_relative_to(template.resolve()):
            raise ValueError('unsafe lock path')
        lock = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(lock, dict):
            raise ValueError('invalid lock object')
    except (OSError, ValueError, TypeError):
        return {'ok': False, 'errors': [{'path': LOCK_NAME, 'code': 'missing_or_invalid_template_lock'}],
                'scope': 'Release-local reproducibility; not a signed release.'}
    if lock.get('schema_version') != LOCK_SCHEMA:
        errors.append({'path': LOCK_NAME, 'code': 'unsupported_template_lock'})
    approved = lock.get('source_files_sha256')
    if not isinstance(approved, dict) or set(approved) != set(sources):
        errors.append({'path': LOCK_NAME, 'code': 'locked_source_set_mismatch'})
    for name, sha in sources.items():
        if not isinstance(approved, dict) or approved.get(name) != sha:
            errors.append({'path': name, 'code': 'locked_template_source_changed'})
    expected = lock.get('assembled_template_sha256')
    if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
        errors.append({'path': LOCK_NAME, 'code': 'invalid_locked_template_hash'})
    elif assembled_sha256 is not None and expected != assembled_sha256:
        errors.append({'path': LOCK_NAME, 'code': 'locked_assembly_changed'})
    if not isinstance(lock.get('builder_version'), str) or (
            builder_version is not None and lock['builder_version'] != builder_version):
        errors.append({'path': LOCK_NAME, 'code': 'locked_builder_version_mismatch'})
    return {'ok': not errors, 'errors': errors,
            'template_sha256': expected, 'builder_version': lock.get('builder_version'),
            'scope': 'Release-local reproducibility; not a signed release.'}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
