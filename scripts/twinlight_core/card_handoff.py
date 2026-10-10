"""Private, fail-closed A -> B handoff. Hashes bind files, not provider identity.

No model/API calls, no producer-authored approval, no font or private-evidence
export. The original A workspace remains the source of truth and is rechecked
at import, after integration and at final export. Moving a workspace requires
re-binding its paths and reissuing the handoff, not editing a success flag.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from .common import ROOT, check, load, save, local_asset, digest

VERSION = 'card-handoff-1'
OUTPUTS = {'card_front': 'card/front.png', 'card_preview': 'card/preview.html',
           'card_pack': 'card/card-pack.json'}
RENDER_FILES = ('assets/template/src/holo-card.js',
                'assets/card-preview/bootstrap.js', 'assets/card-preview/page.html',
                'assets/card-preview/style.css', 'scripts/preview_card.py',
                'scripts/package_card.py', 'scripts/twinlight_core/canvas_mapping.py')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def renderer_contract() -> dict:
    files = {name: sha(ROOT / name) for name in RENDER_FILES}
    return {'version': 'shared-card-renderer-1', 'files_sha256': files,
            'fingerprint': digest(files)}


def _inside(root: Path, value: str | Path) -> Path:
    path = Path(value)
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    check(path.is_relative_to(root) and path.is_file(), 'Handoff source missing or outside task A: ' + str(path))
    return path


def _checks_ok(report: dict) -> bool:
    checks = report.get('checks')
    return (report.get('ok') is True and isinstance(checks, list) and bool(checks)
            and all(isinstance(c, dict) and c.get('passed') is True for c in checks))


def audit_pack(pack: Path, layers: Path, expected_persona: str) -> dict:
    """Compare actual decoded native bytes, depths, layout and renderer version."""
    from .art import validate_layers
    native = validate_layers(layers, expected_persona)
    manifest, payload = load(layers), load(pack)
    check(payload.get('twinlight_card') == 'layers-1', 'Unsupported card pack')
    check(payload.get('persona_digest') == expected_persona, 'Wrong card owner/content')
    check(payload.get('canvas') == native['size'], 'Card pack canvas changed')
    check(payload.get('depths') == manifest['depths'], 'Card pack depth configuration changed')
    check(payload.get('canvas_mapping') == manifest.get('canvas_mapping'), 'Card pack canvas mapping changed')
    check(payload.get('composition') == manifest.get('composition'), 'Card pack composition changed')
    check(payload.get('art_status') == manifest['art_status'], 'Card pack art status changed')
    check(payload.get('renderer') == renderer_contract(), 'Card renderer changed; revalidate task A')
    check(set(payload.get('layers', {})) == set(manifest['assets']), 'Card pack layer roles changed')
    fingerprints = {}
    for role, name in manifest['assets'].items():
        uri = payload['layers'][role]
        check(isinstance(uri, str) and uri.startswith('data:image/') and ';base64,' in uri,
              'Card pack contains an external or invalid layer')
        raw = base64.b64decode(uri.split(';base64,', 1)[1], validate=True)
        expected = sha(local_asset(layers.parent, name))
        check(hashlib.sha256(raw).hexdigest() == expected, 'Card pack layer changed: ' + role)
        fingerprints[role] = expected
    return {'ok': True, 'layers_sha256': fingerprints, 'depths': manifest['depths'],
            'composition': manifest.get('composition'), 'renderer': payload['renderer']}


def inspect_card_workspace(workspace: Path, expected_persona: str | None = None) -> dict:
    """Reread real gates, never trust complete=true or a cached handoff alone."""
    from .art_quality import check_evidence
    from .independent_review import check_release
    from .cardgen import read_card_data
    from .lite import persona_digest
    from .embedded_card import audit_renderer

    root = Path(workspace).resolve()
    run, receipt, state = (load(root / name) for name in
                           ('run-report.json', 'delivery-report.json', 'run-state.json'))
    content = _inside(root, 'content.json')
    persona = persona_digest(read_card_data(content))
    check(expected_persona is None or expected_persona == persona, 'Task A card does not match this person/card text/summarizer')
    check(state.get('mode') == 'card' and state.get('persona_digest') == persona, 'Handoff must originate from a standalone card run')
    check(state.get('input_sha256') == sha(content) == receipt.get('input_sha256'), 'Task A frozen input changed')
    for record in (run, receipt):
        check(record.get('mode') == 'card' and record.get('complete') is True
              and record.get('status') == 'files_ready' and record.get('dynamic_verified') is True,
              'Task A is not currently complete; finish actual card checks and independent release first')
    check(receipt.get('draft') is True and receipt.get('share_allowed') is False,
          'Private card handoff is not permission to publish')
    outputs, files, resources = {}, {}, {}
    for key, relative in OUTPUTS.items():
        path = _inside(root, relative)
        check(Path(run.get('outputs', {}).get(key, '')).resolve() == path, 'Unexpected A output: ' + key)
        fingerprint = sha(path)
        check(receipt.get('outputs_sha256', {}).get(key) == fingerprint, 'A output changed after release: ' + key)
        outputs[key] = str(path)
        files[relative] = fingerprint
    layers = _inside(root, state.get('layers_source', ''))
    art = check_evidence(layers, persona, front=Path(outputs['card_front']), preview=Path(outputs['card_preview']))
    check(art.get('ok') is True, 'Task A artwork review missing, rejected or stale: ' + json.dumps(art.get('errors', []), ensure_ascii=False))
    evidence = load(layers.parent / 'art-evidence.json')
    from .art_quality import checked_ref
    check(load(checked_ref(layers.parent, evidence['design'])).get('version') == 'art-direction-2',
          'Task A requires the versioned art-direction-2 contract')
    release = check_release(root, outputs, 'card')
    check(release.get('ok') is True, 'Task A independent release missing, rejected or stale: ' + json.dumps(release.get('errors', []), ensure_ascii=False))
    browser = state.get('stages', {}).get('card_browser', {})
    check(browser.get('status') == 'passed' and browser.get('invoked_by_runner') is True
          and browser.get('report_input_bound') is True
          and browser.get('input_html_sha256') == files[OUTPUTS['card_preview']], 'Task A browser evidence is missing or stale')
    browser_path = _inside(root, browser.get('report', ''))
    browser_record = load(browser_path)
    check(_checks_ok(browser_record) and browser_record.get('html_sha256') == files[OUTPUTS['card_preview']]
          and all(browser_record.get(k) is True for k in ('foil_verified', 'fixed_text_verified', 'touch_verified', 'reduced_motion_verified')),
          'Task A current browser report does not pass native-card checks')
    browser_relative = browser_path.relative_to(root).as_posix()
    check(browser.get('files_sha256', {}).get(browser_relative) == sha(browser_path), 'Task A browser report changed')
    pack = audit_pack(Path(outputs['card_pack']), layers, persona)
    render = audit_renderer(Path(outputs['card_preview']), layers)
    check(render.get('ok') is True, 'Task A preview renderer/depth parameters differ from the shared renderer')
    # Hash every file actually consumed by the gates, not just their verdicts.
    tracked = [content, layers, browser_path, root / 'run-report.json', root / 'delivery-report.json', root / 'run-state.json']
    tracked += [local_asset(layers.parent, p) for p in load(layers)['assets'].values()]
    for gate in (art, release):
        tracked += [Path(p) for p in gate.get('inputs_sha256', {})]
    # A real reviewer packet also binds installed style art/criteria. Those
    # are maintained package resources, not missing private files in A.
    from package_skill import resource_files
    allowed_resources={p.resolve() for p in resource_files(ROOT)}
    for path in tracked:
        p=Path(path).resolve()
        if p.is_relative_to(root):
            p=_inside(root,p);files[p.relative_to(root).as_posix()]=sha(p)
        else:
            check(p in allowed_resources, 'Review dependency outside task A is not an installed skill resource: '+str(p))
            resources[p.relative_to(ROOT).as_posix()]=sha(p)
    return {'version': VERSION, 'persona_digest': persona,
            'layers_file': layers.relative_to(root).as_posix(), 'outputs': dict(OUTPUTS),
            'files_sha256': dict(sorted(files.items())), 'resource_files_sha256':dict(sorted(resources.items())),
            'renderer': renderer_contract(),
            'native_card': pack, 'scope': 'Local byte-bound review evidence, not authenticated provider identity.'}


def seal(workspace: Path) -> dict:
    root = Path(workspace).resolve()
    binding = inspect_card_workspace(root)
    path = root / 'card-handoff.json'
    value = {**binding, 'binding_sha256': digest(binding), 'private': True,
             'approval_inferred_from_flags': False}
    if not path.exists() or load(path) != value:
        save(path, value)
    return {'ok': True, 'handoff': str(path), 'persona_digest': binding['persona_digest'],
            'binding_sha256': value['binding_sha256'], 'private': True}


def validate(handoff: Path, expected_persona: str | None = None) -> dict:
    """Import a private A handoff. No image calls and no model-generated approval."""
    path = Path(handoff).resolve()
    check(path.name == 'card-handoff.json' and path.is_file(), 'Expected task A/card-handoff.json')
    saved = load(path)
    check(saved.get('version') == VERSION and saved.get('private') is True, 'Invalid private card handoff')
    current = inspect_card_workspace(path.parent, expected_persona)
    check(saved.get('binding_sha256') == digest(current)
          and all(saved.get(k) == v for k, v in current.items()),
          'Task A handoff is stale; revalidate and seal the current card workspace')
    # Recheck tracked bytes at end to reject concurrent edits during import.
    check(all(sha(_inside(path.parent, p)) == h for p, h in current['files_sha256'].items()),
          'Task A changed during import; retry only after the files are stable')
    check(all(sha(ROOT/p)==h for p,h in current['resource_files_sha256'].items()),
          'Installed reviewer/style resource changed during import')
    return {'ok': True, 'status': 'accepted_card_import', 'source_workspace': str(path.parent),
            'handoff': str(path), 'handoff_sha256': sha(path),
            'layers': str(path.parent / current['layers_file']),
            'outputs': {k: str(path.parent / p) for k, p in current['outputs'].items()},
            'persona_digest': current['persona_digest'], 'renderer': current['renderer'],
            'inputs_sha256': {**{str(path.parent / p): h for p, h in current['files_sha256'].items()},
                              **{str(ROOT / p): h for p, h in current['resource_files_sha256'].items()}},
            'evidence_checked': True, 'host_visual_review_recorded': True,
            'image_calls_performed': 0, 'reviewer_identity_authenticated': False}
