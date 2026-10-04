#!/usr/bin/env python3
"""Maintainer-only template lock update after reviewing a release's template.

Personal generation must never use --write to silence a failed template check.
"""
from __future__ import annotations
import argparse
import json
from twinlight_core import site
from twinlight_core.common import VERSION, save
from twinlight_core.template_lock import LOCK_NAME, LOCK_SCHEMA, sha256, verify_lock


def current_lock() -> dict:
    html, _ = site.template_parts()
    return {'schema_version': LOCK_SCHEMA, 'template_name': 'Twinlight V10-derived',
            'builder_version': VERSION,
            'source_files_sha256': site.template_source_hashes(),
            'assembled_template_sha256': sha256(html.encode('utf-8')),
            'scope': 'Maintainer-reviewed local release lock; not a signed attestation.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true',
                        help='Explicit maintainer update after reviewing intentional template changes')
    args = parser.parse_args()
    lock = current_lock()
    if args.write:
        save(site.TEMPLATE / LOCK_NAME, lock)
    report = verify_lock(site.TEMPLATE, lock['source_files_sha256'],
                         assembled_sha256=lock['assembled_template_sha256'], builder_version=VERSION)
    report['lock_written'] = args.write
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
