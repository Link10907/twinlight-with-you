#!/usr/bin/env python3
"""Exercise legal text limits in the fixed renderer; synthetic data, no personal claims."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from twinlight_core.common import ROOT, save
from twinlight_core.lite import schema, validate
from twinlight_core.site import build_lite


def extreme_input(character: str) -> dict:
    """Use the current schema's actual limits, including unbroken long words."""
    properties = schema()['properties']
    theme = properties['themes']['items']['properties']
    topic = theme['topics']['items']['properties']
    card = properties['card']['properties']
    longest = lambda fields, key, char=character: char * fields[key]['maxLength']
    themes = []
    for i in range(properties['themes']['maxItems']):
        themes.append({
            'label': longest(theme, 'label')[:-1] + str(i),
            'english': longest(theme, 'english', 'W')[:-1] + str(i),
            'headline': longest(theme, 'headline'),
            'story': [character * theme['story']['items']['maxLength']] * theme['story']['maxItems'],
            'reflection': longest(theme, 'reflection'),
            'topics': [{
                'label': longest(topic, 'label')[:-1] + str(j),
                'summary': longest(topic, 'summary'), 'basis': 'often',
            } for j in range(theme['topics']['maxItems'])],
        })
    return {
        'twinlight': 'lite-1', 'name': longest(properties, 'name'),
        'summarizer': longest(properties, 'summarizer'), 'intro': longest(properties, 'intro'),
        'themes': themes,
        'card': {
            'title': longest(card, 'title'), 'english_title': longest(card, 'english_title', 'W'),
            'keywords': [character * (card['keywords']['items']['maxLength'] - 1) + str(i)
                         for i in range(card['keywords']['maxItems'])],
            'tagline': longest(card, 'tagline'), 'reflection': longest(card, 'reflection'),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browser', help='Installed Chrome/Chromium executable; otherwise use the browser verifier discovery.')
    parser.add_argument('--skip-continuous', action='store_true', help='Use when a normal artifact has already passed real-time playback in the same verification run.')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    checks = []
    for index, (name, char) in enumerate([('max-ascii', 'W'), ('max-cjk', '光')]):
        data = extreme_input(char)
        errors = validate(data)
        if errors:
            checks.append({'name': name, 'passed': False, 'input_errors': errors})
            break
        save(args.out / (name + '.json'), data)
        build_lite(data, args.out / name, generated_at='2026-10-04T00:00:00Z')
        command = [sys.executable, str(ROOT / 'scripts/verify_browser.py'),
                   '--html', str(args.out / name / 'index.html'), '--out', str(args.out / (name + '-browser'))]
        if index or args.skip_continuous:
            command.append('--skip-continuous')
        if args.browser:
            command += ['--browser', args.browser]
        start = time.monotonic()
        result = subprocess.run(command, check=False)
        report = args.out / (name + '-browser/report.json')
        checks.append({'name': name, 'passed': result.returncode == 0,
                       'elapsed_seconds': round(time.monotonic() - start, 2), 'report': str(report)})
        if result.returncode:
            break
    ok = len(checks) == 2 and all(check['passed'] for check in checks)
    save(args.out / 'layout-report.json', {
        'ok': ok, 'checks': checks,
        'scope': 'Schema-valid maximum-length ASCII and Chinese text in headless Chrome, desktop and 390px emulated touch.',
        'continuous_finale': not args.skip_continuous,
        'not_tested': ['Physical phone', 'Safari', 'personal semantic accuracy', 'newly generated native card artwork'] +
                      (['Real-time finale playback (explicitly skipped)'] if args.skip_continuous else []),
    })
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
