"""Portable-only layer production. The six-layer renderer/strict contracts stay unchanged.

This module validates pixels and local process records, not an image provider or
an aesthetic judgement. Assisted extraction never claims to be native alpha.
"""
from __future__ import annotations
import hashlib
import shutil
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageOps
from .common import check, load, save, local_asset

METHODS = ('native_layers', 'assisted_layers')
ROLES = ('background', 'subject', 'effects')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def layer_plan(capabilities: dict, history: dict | None = None) -> dict:
    """A failed reference edit is NOT absent image generation; stop wrong-scene loops."""
    edit = capabilities.get('image_edit', {})
    processing = capabilities.get('layer_processing', {})
    attempts = (history or {}).get('attempts', [])
    check(isinstance(attempts, list) and all(isinstance(a, dict) for a in attempts),
          'image-attempts.json needs an attempts array of actual calls')
    statuses = {'available', 'unavailable', 'unknown', 'temporarily_blocked'}
    for key in ('status', 'reference_binding', 'transparent_output'):
        check(edit.get(key, 'unknown') in statuses, 'Invalid image_edit.' + key)
    check(processing.get('status', 'unknown') in statuses, 'Invalid layer_processing.status')
    drift = any(a.get('outcome') == 'reference_mismatch' for a in attempts)
    exhausted = any(sum(a.get('role') == role for a in attempts) >= 3 and
                    not any(a.get('role') == role and a.get('outcome') == 'success' for a in attempts)
                    for role in ROLES)
    restricted = any(edit.get(k) in ('unavailable', 'temporarily_blocked')
                     for k in ('status', 'reference_binding', 'transparent_output'))
    base = {'scope': 'Observed current-session abilities; not a provider guarantee.',
            'same_prototype_required': True, 'interactive_html_required': True,
            'static_or_cardless_fallback': False, 'max_attempts_per_role': 3}
    if drift or exhausted or restricted:
        why = ('A reference edit returned another subject/scene.' if drift else
               'Native layer attempt budget exhausted.' if exhausted else
               'Reference-bound native transparent editing is unavailable or blocked.')
        if processing.get('status') == 'available':
            return base | {'status': 'ready', 'method': 'assisted_layers', 'reason': why,
                           'next_action': 'Keep the accepted prototype and successful layers. Use real silhouette masks/clean-background repair via prepare_assisted_layers.py; review edges and occlusion. Do not repeat the wrong-scene edit.'}
        return base | {'status': 'inspect_layer_processing' if processing.get('status', 'unknown') == 'unknown' else 'layer_capability_blocked',
                       'method': None, 'reason': why,
                       'next_action': 'Check actual local segmentation/repair tools. A missing mask or clean background is a precise layer limitation, not permission for a flat PNG, fake layers, or HTML-only.'}
    if all(edit.get(k) == 'available' for k in ('status', 'reference_binding', 'transparent_output')):
        return base | {'status': 'ready', 'method': 'native_layers',
                       'next_action': 'Use the real accepted prototype with the supported edit interface; inspect the first returned layer before requesting the rest.'}
    return base | {'status': 'inspect_layer_capabilities', 'method': None,
                   'next_action': 'Check reference binding and transparent output separately from text-to-image. One real bound edit may establish capability; record its actual outcome. Unknown is not unavailable.'}


def record_attempt(workspace: Path, role: str, outcome: str, reason: str, prototype: Path,
                   output: Path | None = None) -> dict:
    """Record an already executed image call, never issue a call or fabricate a receipt."""
    check(role in ROLES, 'Invalid layer role')
    check(outcome in ('success', 'failure', 'reference_mismatch'), 'Invalid actual outcome')
    check(bool(reason.strip()), 'Record the observed result, not a generic pass')
    root = workspace.resolve()
    state = root / 'portable-state.json'
    check(not state.exists() or not load(state).get('image_task_contract'),
          'Tracked portable run: reserve-image before calling, then record-image-result; do not backfill the old attempt log')
    check(prototype.is_file() and prototype.resolve().is_relative_to(root), 'Keep the actual prototype inside the workspace')
    path = root / 'image-attempts.json'
    history = load(path) if path.exists() else {'version': 'portable-attempts-1', 'attempts': []}
    check(isinstance(history.get('attempts'), list), 'Invalid attempt history')
    fingerprint = sha(prototype)
    check(all(a.get('prototype_sha256') == fingerprint for a in history['attempts']),
          'Prototype changed; version the work instead of silently resetting attempts')
    check(sum(a.get('role') == role for a in history['attempts']) < 3,
          'Native attempt budget reached; preserve work and use assisted layers or report the limitation')
    check(not any(a.get('outcome') == 'reference_mismatch' for a in history['attempts']),
          'Reference binding already failed; stop the wrong-scene loop and inspect the assisted route')
    item = {'role': role, 'outcome': outcome, 'reason': reason, 'prototype_sha256': fingerprint}
    if output is not None:
        check(output.is_file() and output.resolve().is_relative_to(root), 'Missing actual returned image')
        item.update(output_file=output.resolve().relative_to(root).as_posix(), output_sha256=sha(output))
    check(outcome != 'success' or output is not None, 'Success requires actual returned bytes')
    history['attempts'].append(item)
    save(path, history)
    return {'ok': True, 'attempts_used': sum(a['role'] == role for a in history['attempts']),
            'scope': 'Local record of an actual observed call; not provider authentication.'}


def _image(path: Path) -> Image.Image:
    check(path.is_file() and path.stat().st_size <= 24 * 1024 * 1024, 'Missing/oversized image')
    with Image.open(path) as im:
        check(im.format in ('PNG', 'JPEG', 'WEBP') and im.width * im.height <= 16_000_000,
              'Expected a supported raster image, at most 16 million pixels')
        return im.convert('RGBA')


def extract(prototype: Path, mask: Path) -> Image.Image:
    """Apply an observed semantic mask; do not infer silhouettes from rectangular crops."""
    original = _image(prototype)
    with Image.open(mask) as im:
        check(im.format == 'PNG' and im.mode in ('1', 'L'), 'Mask must be a real grayscale PNG, not a painted checkerboard/RGB picture')
        check(im.size == original.size, 'Mask must retain prototype canvas and coordinates; no resize/reposition')
        alpha = im.convert('L')
    histogram = alpha.histogram(); total = alpha.width * alpha.height
    check(sum(histogram[:16]) / total > .01 and sum(histogram[16:]) / total > .0005,
          'Mask is empty or a full opaque poster')
    result = original.copy(); result.putalpha(alpha)
    return result


def prepare_assisted(data: dict, prototype: Path, background: Path, out: Path, font: Path, *,
                     subject: Path | None = None, subject_mask: Path | None = None,
                     effects: Path | None = None, effects_mask: Path | None = None,
                     composition: dict | None = None) -> dict:
    """Keep the original RGB; supply a reviewed clean background and real masks/layers.

    It does not download a segmentation model, create a semantic mask, repair a
    missing background, or auto-approve the resulting artwork.
    """
    check(bool(subject) != bool(subject_mask), 'Provide exactly one subject layer or subject mask')
    check(bool(effects) != bool(effects_mask), 'Provide exactly one effects layer or foreground mask')
    check(subject_mask is not None or effects_mask is not None, 'Use native preparation when no extraction is needed')
    original, bg = _image(prototype), _image(background)
    check(min(original.size) >= 512 and abs(original.width / original.height - .75) < .01,
          'Keep a native 3:4 prototype, short side at least 512 pixels')
    check(original.getchannel('A').getextrema() == (255, 255), 'Prototype must be a complete opaque scene')
    check(bg.size == original.size and bg.getchannel('A').getextrema() == (255, 255),
          'Clean background must be opaque and preserve the entire prototype canvas')
    check(ImageChops.difference(original.convert('RGB'), bg.convert('RGB')).getbbox() is not None,
          'The prototype is not a clean background: it would leave a duplicate subject')
    check(not out.exists() or not any(out.iterdir()), 'Use a new layer revision; never overwrite accepted source assets')
    outputs = {'subject': extract(prototype, subject_mask) if subject_mask else _image(subject),
               'effects': extract(prototype, effects_mask) if effects_mask else _image(effects)}
    check(all(im.size == original.size for im in outputs.values()), 'Every layer must retain the same canvas')
    out.mkdir(parents=True, exist_ok=True); sources = out / 'sources'; sources.mkdir()
    inputs = {}
    for role, path in [('prototype', prototype), ('background', background), ('subject', subject),
                       ('subject_mask', subject_mask), ('effects', effects), ('effects_mask', effects_mask)]:
        if path is None: continue
        dest = sources / (role + path.suffix.lower()); shutil.copyfile(path, dest)
        inputs[role] = {'file': dest.relative_to(out).as_posix(), 'sha256': sha(dest)}
    # Keep the established six-layer interface. Native supplied layers keep their bytes.
    for role in ('subject', 'effects'):
        if role + '_mask' in inputs:
            path = sources / (role + '-extracted.png'); outputs[role].save(path)
        else:
            path = local_asset(out, inputs[role]['file'])
        inputs[role + '_assembled'] = {'file': path.relative_to(out).as_posix(), 'sha256': sha(path)}
    # Reuse the existing typesetter, depth contract and validator, but do not
    # re-enter the strict art-prompt compiler after pictures already exist.
    from prepare_card_layers import typography
    from .cardgen import DEPTHS
    from .lite import persona_digest
    from .art import validate_layers, validate_composition
    persona = persona_digest(data)
    if composition:
        validate_composition(composition, persona, original.size)
        if composition.get('source_prototype_sha256'):
            check(composition['source_prototype_sha256'] == sha(prototype), 'Composition belongs to another prototype')
    typography(data, original.size, font, composition).save(out / 'text.png')
    paths = {}
    for role in ROLES:
        source = local_asset(out, inputs['background' if role == 'background' else role + '_assembled']['file'])
        target = out / (role + source.suffix.lower()); shutil.copyfile(source, target); paths[role] = target.name
    Image.new('RGBA', original.size).save(out / 'spirit.png')
    alpha = outputs['subject'].getchannel('A')
    edge = ImageChops.difference(alpha.filter(ImageFilter.MaxFilter(5)), alpha.filter(ImageFilter.MinFilter(5)))
    ImageOps.invert(edge).convert('RGB').save(out / 'lineart.png')
    manifest = {'schema_version':'1.0', 'persona_digest':persona, 'art_status':'generated',
                'reference_consent':False, 'depths':dict(DEPTHS),
                'assets':paths | {'text':'text.png','spirit':'spirit.png','lineart':'lineart.png'},
                'notes':'assisted_layers: native illustration with registered mask extraction/clean background. Not native transparent generation. Actual visual and motion review still required.'}
    if composition: manifest['composition'] = composition
    save(out / 'layers.json', manifest)
    result = validate_layers(out / 'layers.json', persona)
    record = {'version': 'portable-layer-process-1', 'method': 'assisted_layers',
              'inputs': inputs, 'prototype_sha256': sha(prototype),
              'outputs_sha256': {r: sha(local_asset(out, manifest['assets'][r])) for r in ROLES},
              'extracted_roles': [r for r in ('subject', 'effects') if r + '_mask' in inputs],
              'automatic_approval': False, 'semantic_mask_reviewed_by_script': False,
              'scope': 'Pixel-preserving alpha application and assembly only. Clean-background quality and silhouette accuracy require actual visual review.'}
    save(out / 'layer-process.json', record)
    return result | {'layer_method': 'assisted_layers', 'process_record': str(out / 'layer-process.json'),
                     'native_transparency_claimed': False, 'quality_verified': False}


def verify_process(path: Path, layers: Path, prototype_sha256: str) -> dict:
    check(path.resolve().parent == layers.resolve().parent, 'Layer process must belong to this layer revision')
    r = load(path); root = path.parent; m = load(layers)
    check(r.get('version') == 'portable-layer-process-1' and r.get('method') == 'assisted_layers', 'Invalid assisted process record')
    check(r.get('prototype_sha256') == prototype_sha256, 'Assisted layers reference another prototype')
    inputs = r.get('inputs', {})
    for role, item in inputs.items():
        check(sha(local_asset(root, item['file'])) == item['sha256'], 'Assisted input changed: ' + role)
    check(inputs.get('prototype', {}).get('sha256') == prototype_sha256, 'Missing frozen prototype')
    expected_roles = [role for role in ('subject', 'effects') if role + '_mask' in inputs]
    check(expected_roles and sorted(r.get('extracted_roles', [])) == sorted(expected_roles), 'Missing or changed extraction roles')
    for role in ROLES:
        target = local_asset(layers.parent, m['assets'][role])
        check(sha(target) == r.get('outputs_sha256', {}).get(role), 'Assisted output changed: ' + role)
        if role in expected_roles:
            wanted = extract(local_asset(root, inputs['prototype']['file']), local_asset(root, inputs[role + '_mask']['file']))
            actual = _image(target)
            check(wanted.size == actual.size and wanted.tobytes() == actual.tobytes(), 'Extracted pixels/alpha no longer match the frozen original: ' + role)
        else:
            check(sha(target) == inputs[role]['sha256'], 'Supplied layer was modified: ' + role)
    return {'method': 'assisted_layers', 'record_sha256': sha(path),
            'extracted_roles': expected_roles, 'native_transparency_claimed': False}
