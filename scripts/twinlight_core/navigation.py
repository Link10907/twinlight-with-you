"""Versioned additive navigation over an UNCHANGED, independently locked V10 core."""
from __future__ import annotations
import hashlib
from .common import ROOT, check, load

DIRECTORY=ROOT/'assets/navigation'
FILES=('before-core.js','after-core.js','style.css')
VERSION='navigation-1.0.0'


def manifest(directory=None) -> dict:
    directory = DIRECTORY if directory is None else directory
    actual={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in FILES}
    locked=load(directory/'extension-lock.json')
    check(locked.get('version')==VERSION and locked.get('files_sha256')==actual,
          'Navigation extension changed; restore the release resources, do not relock during a personal run')
    return {'version':VERSION,'files_sha256':actual,
            'scope':'Additive navigation adapter; original V10 core remains independently locked.'}


def compose(html: str, js: str) -> tuple[str,str,dict]:
    extension=manifest()
    before=(DIRECTORY/'before-core.js').read_text()
    after=(DIRECTORY/'after-core.js').read_text()
    css=(DIRECTORY/'style.css').read_text()
    check('</script' not in (before+after).lower() and '</style' not in css.lower(), 'Invalid navigation resource')
    combined=before+'\n'+js+'\n'+after
    old='<script>'+js+'</script>'
    check(html.count(old)==1, 'Expected exactly one retained V10 script')
    html=html.replace(old,'<script>'+combined+'</script>')
    html=html.replace('</style>', '\n'+css+'\n</style>',1)
    return html,combined,extension


def audit_runtime(workspace, html) -> dict:
    """Recheck the runner's actual offline navigation report for task B.

    Neither an injected-page diagnostic nor a hand-edited passed flag is enough.
    This is evidence consistency; it does not authenticate the browser provider.
    """
    from pathlib import Path
    root=Path(workspace).resolve();html=Path(html).resolve()
    state=load(root/'run-state.json')
    stage=state.get('stages',{}).get('navigation_browser',{})
    fingerprint=hashlib.sha256(html.read_bytes()).hexdigest()
    check(stage.get('status')=='passed' and stage.get('invoked_by_runner') is True
          and stage.get('report_input_bound') is True and stage.get('input_html_sha256')==fingerprint,
          'Task B requires the current runner-bound offline navigation check')
    path=Path(stage.get('report','')).resolve()
    check(path.is_relative_to(root) and path.is_file(), 'Missing task B navigation report')
    relative=path.relative_to(root).as_posix();sha=hashlib.sha256(path.read_bytes()).hexdigest()
    check(stage.get('files_sha256',{}).get(relative)==sha,'Task B navigation evidence changed')
    report=load(path);checks=report.get('checks')
    check(report.get('version')=='navigation-browser-1' and report.get('html_sha256')==fingerprint
          and report.get('ok') is True and report.get('load_mode')=='file'
          and report.get('file_open_verified') is True and report.get('offline_self_contained_verified') is True
          and report.get('delivery_eligible') is True and isinstance(checks,list) and bool(checks)
          and all(isinstance(c,dict) and c.get('passed') is True for c in checks),
          'Injected/failed/unbound navigation checks cannot approve the single-file delivery')
    return {'file':relative,'sha256':sha,'html_sha256':fingerprint,'scope':'offline-navigation'}
