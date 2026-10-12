"""Honest motion evidence for the portable card. PNG files never prove interactivity."""
from __future__ import annotations
from pathlib import Path
from .common import check, load, local_asset
from .portable_layers import sha

REQUIRED = ('interaction_verified', 'parallax_verified', 'fixed_text_verified',
            'flip_verified', 'touch_verified', 'reduced_motion_verified')


def motion_check(path: Path, html: Path) -> dict:
    """Missing browser is unverified; known broken movement blocks delivery.

    A report is a local execution record, not cryptographic provider proof.
    A CSS parallax fallback is not claimed to have the WebGL foil effect.
    """
    if not path.exists():
        return {'status': 'unavailable', 'backend': 'unverified', 'interaction_verified': False,
                'parallax_verified': False, 'foil_verified': False, 'offline_file_open': 'unverified',
                'reason': 'No card browser execution recorded; shared renderer/byte checks are not a motion test.'}
    r = load(path)
    check(r.get('html_sha256') == sha(html), 'Card motion report targets stale or different HTML')
    check(r.get('version') == 'portable-card-motion-1', 'Use the portable motion runner, not a PNG/visual review as a runtime report')
    status = r.get('status')
    check(status in ('passed', 'limited', 'unavailable'), 'Known card interaction failure blocks delivery')
    checks = r.get('checks', [])
    check(isinstance(checks, list) and not any(c.get('passed') is False for c in checks if isinstance(c, dict)),
          'Known card motion/JS failure blocks delivery')
    if status == 'unavailable':
        check(bool(r.get('reason')) and not any(r.get(k) is True for k in (*REQUIRED, 'foil_verified')),
              'Unavailable runtime cannot claim verified interaction')
        return r
    check(checks and all(isinstance(c, dict) and c.get('passed') is True for c in checks), 'Missing actual motion assertions')
    check(all(r.get(k) is True for k in REQUIRED), 'Card must rotate, show internal parallax, keep text fixed, flip, support touch and reduced motion')
    check(r.get('backend') in ('webgl', 'css-layered'), 'Unknown card rendering backend')
    check(r.get('load_mode') in ('file', 'injected'), 'Record actual browser load mode')
    check(r.get('offline_file_open') == ('passed' if r['load_mode'] == 'file' else 'unverified'), 'Injected diagnostics are not offline file validation')
    if r['backend'] == 'webgl':
        check(r.get('foil_verified') is True, 'WebGL path must actually change its foil under view changes')
    else:
        check(status == 'limited' and r.get('foil_verified') is False, 'CSS fallback is not a WebGL foil pass')
    if status == 'passed':
        check(r['backend'] == 'webgl' and r['load_mode'] == 'file', 'Full motion pass requires actual file opening and WebGL')
    frames = r.get('frames', {})
    check(all(k in frames for k in ('left', 'right')), 'Missing actual angle captures')
    if r['backend'] == 'webgl':
        check(all(k in frames for k in ('foil_off', 'foil_on')), 'Missing actual foil comparison frames')
    for item in frames.values():
        check(sha(local_asset(path.parent, item['file'])) == item['sha256'], 'Card evidence frame changed or missing')
    check(frames['left']['sha256'] != frames['right']['sha256'], 'Identical angle images cannot establish parallax')
    return {**r, 'record_sha256': sha(path)}
