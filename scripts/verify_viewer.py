#!/usr/bin/env python3
"""Exercise the local viewer with native layers, ownership checks and truthful static previews."""
from __future__ import annotations
import argparse
import base64
import copy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from threading import Thread
from urllib.parse import quote, urlsplit
from PIL import Image, ImageChops, ImageDraw
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from twinlight_core import lite  # noqa: E402
from twinlight_core.common import load, save  # noqa: E402
from test_card_art import native_fixture  # noqa: E402
from preview_card import preview as build_card_preview  # noqa: E402

FIX = ROOT / 'tests/fixtures/lite'
AT = '2026-10-03T00:00:00Z'
p = argparse.ArgumentParser()
p.add_argument('--viewer', type=Path, default=ROOT / 'outputs/viewer/index.html')
p.add_argument('--out', type=Path, required=True)
p.add_argument('--browser')
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
checks, errors, network = [], [], []
report = {'viewer': str(a.viewer), 'checks': checks, 'errors': errors, 'external_requests': network,
          'not_tested': ['real-history semantic accuracy', 'actual image-model output', 'Safari', 'physical phone']}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def record(name, ok, detail=None):
    checks.append({'name': name, 'passed': bool(ok), 'detail': detail})
    print(('PASS ' if ok else 'FAIL ') + name, flush=True)
    if not ok:
        raise AssertionError(name)


def launch(pw):
    binary = a.browser or os.environ.get('TWINLIGHT_BROWSER')
    flags = ['--no-sandbox', '--ignore-gpu-blocklist', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']
    try:
        return pw.chromium.launch(executable_path=binary, headless=True, args=flags)
    except Exception:
        system = [x for x in ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Chromium.app/Contents/MacOS/Chromium',
                              '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'] if Path(x).exists()]
        if binary or not system:
            raise
        report['browser'] = system[0]
        return pw.chromium.launch(executable_path=system[0], headless=True, args=flags)


def fixture_images(tmp):
    prototype = Image.new('RGB', (600, 800), (20, 35, 75))
    d = ImageDraw.Draw(prototype)
    d.ellipse([180, 160, 420, 680], fill=(70, 150, 130))
    prototype.save(tmp / 'prototype.png')
    Image.new('RGB', (300, 400), 'gray').save(tmp / 'small.png')
    Image.new('RGB', (700, 800), 'navy').save(tmp / 'wrong-ratio.png')
    green = Image.new('RGB', (600, 800), (0, 255, 0))
    ImageDraw.Draw(green).ellipse([180, 160, 420, 680], fill=(70, 150, 130))
    green.save(tmp / 'green.png')


def state(q):
    return q.evaluate('()=>twinlightViewer.getState()')


def paste(q, text):
    q.fill('#jsonInput', text)
    q.evaluate('()=>twinlightViewer.check()')


def manifest_files(folder):
    manifest = load(folder / 'layers.json')
    return [str(folder / 'layers.json')] + [str(folder / fn) for fn in manifest['assets'].values()]


def import_layers(q, files, expected='layered'):
    q.set_input_files('#layerFiles', files)
    if expected == 'layered':
        q.wait_for_function('()=>twinlightViewer.getState().art==="layered"', timeout=15000)
    else:
        q.wait_for_function('()=>typeof twinlightViewer.getState().artError==="string"&&twinlightViewer.getState().artError.length>0', timeout=15000)


def clear_art(q):
    q.click('#clearArt')
    q.wait_for_function('()=>twinlightViewer.getState().art==="placeholder"')


def generate(q):
    q.check('#confirmCheck')
    q.click('#generate')
    q.wait_for_function('()=>!document.getElementById("previewLayer").hidden&&twinlightViewer.getState().built', timeout=20000)
    frame = q.locator('#previewFrame').element_handle().content_frame()
    frame.wait_for_function('()=>typeof state!=="undefined"&&state.ready&&document.getElementById("loading").hidden===true', timeout=30000)
    return frame


def close_preview(q):
    q.click('#closePreview')
    q.wait_for_function('()=>document.getElementById("previewLayer").hidden')


def decoded(uri):
    return Image.open(io.BytesIO(base64.b64decode(uri.split(',', 1)[1]))).convert('RGBA')


def portable_card(folder):
    manifest = load(folder / 'layers.json')
    layers = {k: 'data:image/png;base64,' + base64.b64encode((folder / fn).read_bytes()).decode('ascii')
              for k, fn in manifest['assets'].items()}
    with Image.open(folder / manifest['assets']['background']) as im:
        canvas = list(im.size)
    card = {'twinlight_card': 'layers-1', 'persona_digest': manifest['persona_digest'], 'canvas': canvas,
            'layers': layers, 'depths': manifest['depths'], 'art_status': manifest['art_status']}
    if 'composition' in manifest:
        card['composition'] = copy.deepcopy(manifest['composition'])
    return card


def composition_fixtures(tmp, persona_digest):
    """Native test shapes, with explicit locks rather than any person's artwork."""
    lock = {'version': '1.0', 'persona_digest': persona_digest, 'canvas': {'width': 600, 'height': 800},
            'subject_bounds': [.19, .24, .61, .81], 'subject_center_region': [.35, .45, .45, .6],
            'text_safe_regions': [[.04, .03, .65, .14], [.05, .87, .95, .97]],
            'source_prototype_sha256': 'f' * 64}
    cases = []
    for name, field, value in [('valid', None, None), ('other-person', 'persona_digest', '0' * 64),
                               ('wrong-canvas', 'canvas', {'width': 300, 'height': 400}),
                               ('shifted-bounds', 'subject_bounds', [.6, .24, .95, .81]),
                               ('shifted-center', 'subject_center_region', [.05, .05, .15, .15]),
                               ('text-occupied', None, None)]:
        folder = tmp / ('composition-' + name)
        native_fixture(folder, persona_digest)
        manifest = load(folder / 'layers.json')
        manifest['composition'] = copy.deepcopy(lock)
        if field:
            manifest['composition'][field] = value
        if name == 'text-occupied':
            with Image.open(folder / 'effects.png') as im:
                effects = im.convert('RGBA')
            ImageDraw.Draw(effects).rectangle([30, 24, 390, 112], fill=(230, 210, 120, 255))
            effects.save(folder / 'effects.png')
        save(folder / 'layers.json', manifest)
        portable = tmp / ('composition-' + name + '.json')
        save(portable, portable_card(folder))
        cases.append((name, folder, portable))
    return cases


status, server = 0, None
with tempfile.TemporaryDirectory() as t:
    tmp = Path(t)
    fixture_images(tmp)
    data = lite.check_text((FIX / 'fenced.txt').read_text(encoding='utf-8'))['data']
    persona_digest = lite.to_profile(data, generated_at=AT)['persona']['persona_digest']
    native_fixture(tmp / 'native', persona_digest)
    native_fixture(tmp / 'green-layer', persona_digest)
    (tmp / 'green-layer/subject.png').write_bytes((tmp / 'green.png').read_bytes())
    native_fixture(tmp / 'wrong-size', persona_digest)
    Image.new('RGBA', (300, 400)).save(tmp / 'wrong-size/spirit.png')
    native_fixture(tmp / 'other-person', 'f' * 64)
    save(tmp / 'card.json', portable_card(tmp / 'native'))
    locked_cases = composition_fixtures(tmp, persona_digest)
    try:
        public = tmp / 'public'; public.mkdir()
        shutil.copyfile(a.viewer, public / a.viewer.name)
        card_input = tmp / 'card-input.json'
        save(card_input, {'twinlight': 'card-1', 'name': data['name'], 'summarizer': data['summarizer'], 'card': data['card']})
        build_card_preview(tmp / 'native/layers.json', public / 'card-preview.html', card_input)
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(public)))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f'http://127.0.0.1:{server.server_port}'
        report['local_url'] = origin + '/' + quote(a.viewer.name)
        with sync_playwright() as pw:
            b = launch(pw)
            q = b.new_page(viewport={'width': 1280, 'height': 900})
            q.on('pageerror', lambda e: errors.append(str(e)))
            q.on('request', lambda r: network.append(r.url) if r.url.startswith(('http:', 'https:')) and
                 (urlsplit(r.url).hostname != '127.0.0.1' or urlsplit(r.url).port != server.server_port) else None)
            q.goto(origin + '/card-preview.html', wait_until='load')
            q.wait_for_function('()=>window.__holo&&(__holo.ready||document.querySelector(".holo-fallback-on"))', timeout=20000)
            record('Standalone card boots without galaxy content or scripts', q.locator('#cardTitle').inner_text() == data['card']['title'] and q.locator('canvas').count() == 1 and not errors, errors)
            record('Standalone card uses the shared WebGL renderer', q.evaluate('()=>__holo.ready&&!__holo.getState().fallback'))
            q.evaluate('()=>{holo.foil=0;holo.depth=1;__holo.setView(0,-.45)}')
            left = decoded(q.evaluate('()=>document.getElementById("holoCanvas").toDataURL()')).convert('RGB')
            q.evaluate('()=>__holo.setView(0,.45)')
            right = decoded(q.evaluate('()=>document.getElementById("holoCanvas").toDataURL()')).convert('RGB')
            change = sum(ImageChops.difference(left, right).convert('L').getdata()) / (left.width * left.height)
            record('Standalone card has real internal parallax with foil off', change > .5, round(change, 3))
            q.click('#holoSettings'); q.click('[data-finish="3"]'); q.click('#cardFlip')
            record('Standalone card material and flip controls work', q.evaluate('()=>__holo.getState().finish===3&&__holo.getState().flipped'))
            q.click('#holoReset')
            record('Standalone card resets to the front', q.evaluate('()=>!__holo.getState().flipped'))
            q.screenshot(path=str(a.out / 'standalone-card.png'))
            q.goto(report['local_url'], wait_until='load')
            record('Viewer boots over localhost without script errors', q.evaluate('()=>!!window.twinlightViewer&&!!window.TwinlightLite') and not errors, errors)
            # If an obsolete helper survives, any accidental invocation becomes a visible test failure.
            q.evaluate('()=>{window.__matteCalls=0;if(typeof TwinlightLite.matte==="function")TwinlightLite.matte=()=>{window.__matteCalls++;throw Error("Automatic matting is forbidden")}}')
            one = q.locator('#oneLiner').inner_text()
            record('One-liner points at the published prompt source', 'prompt.md' in one.lower() and '__' not in one, one)
            record('Default entry uses real GitHub source URLs',
                   'https://raw.githubusercontent.com/Link10907/twinlight-with-you/main/PROMPT.md' in one and
                   'link10907.github.io' not in one, one)
            card_one = q.locator('#cardLiner').text_content()
            record('HTML and card entries specify separate deliverables', 'HTML' in one and 'CARD.md' in card_one and '卡片包' in card_one)
            record('No green-screen upload flow remains', q.locator('#characterFile').count() == 0 and q.locator('#portraitFile').count() == 0)
            q.screenshot(path=str(a.out / 'viewer-home.png'), full_page=True)

            bad = (FIX / 'too_long.json').read_text(encoding='utf-8')
            paste(q, bad)
            js, py = state(q), lite.check_text(bad)
            record('Invalid JSON is rejected with every error listed', not js['ok'] and js['errors'] == py['errors'] and q.locator('#checkPanel .errors li').count() == len(py['errors']), len(py['errors']))
            record('Repair prompt offered', q.locator('#copyRepair').is_visible())
            record('Generate locked while JSON is invalid', q.locator('#generate').is_disabled())
            q.locator('#step2').screenshot(path=str(a.out / 'viewer-errors.png'))

            good = (FIX / 'fenced.txt').read_text(encoding='utf-8')
            paste(q, good)
            js, py = state(q), lite.check_text(good)
            record('Fenced AI reply accepted, same verdict as Python', js['ok'] and py['ok'] and js['warnings'] == py['warnings'], js['warnings'])
            record('Content preview shows every theme', q.locator('#contentPreview .preview-theme').count() == len(data['themes']))
            record('Generate still locked until user confirms', q.locator('#generate').is_disabled())
            browser_digest = q.evaluate('(d)=>TwinlightLite.personaDigest(d)', data)
            record('Python and browser agree on the stable persona digest', browser_digest == persona_digest, browser_digest)
            q.locator('#step2').screenshot(path=str(a.out / 'viewer-valid.png'))
            q.locator('#artDetails > summary').click()

            q.set_input_files('#prototypeFile', str(tmp / 'small.png'))
            q.wait_for_function('()=>/512|小/.test(twinlightViewer.getState().artError||"")')
            record('Too-small prototype rejected', state(q)['art'] == 'placeholder')
            q.set_input_files('#prototypeFile', str(tmp / 'wrong-ratio.png'))
            q.wait_for_function('()=>/3:4|比例/.test(twinlightViewer.getState().artError||"")')
            record('Prototype with wrong aspect ratio rejected', state(q)['art'] == 'placeholder')
            import_layers(q, manifest_files(tmp / 'green-layer'), expected='error')
            record('Opaque green-screen subject is rejected without matting', state(q)['art'] == 'placeholder' and q.evaluate('()=>window.__matteCalls===0'))
            import_layers(q, manifest_files(tmp / 'wrong-size'), expected='error')
            record('Layer dimensions must match exactly', state(q)['art'] == 'placeholder')
            import_layers(q, manifest_files(tmp / 'other-person'), expected='error')
            record('Artwork from another persona is rejected', state(q)['art'] == 'placeholder')

            for kind in ('manifest', 'portable'):
                for name, folder, portable in locked_cases:
                    files = manifest_files(folder) if kind == 'manifest' else str(portable)
                    import_layers(q, files, expected='layered' if name == 'valid' else 'error')
                    got = state(q)
                    if name == 'valid':
                        record(f'{kind}: current-person composition lock is accepted and retained',
                               got['art'] == 'layered' and got['composition'] == load(folder / 'layers.json')['composition'])
                        checks_report = got['compositionChecks']
                        record(f'{kind}: alpha geometry never claims prototype or visual approval',
                               checks_report['prototype_hash_verified_by_layer_validator'] is False and
                               checks_report['quality_verified'] is False and
                               checks_report['canvas'] == [600, 800])
                    else:
                        record(f'{kind}: composition {name} is rejected',
                               got['art'] == 'placeholder' and 'composition' in got['artError'])

            clear_art(q)
            frame = generate(q)
            placeholder_html = q.evaluate('()=>twinlightViewer.html()')
            record('Placeholder build is labelled honestly', state(q)['htmlBytes'] > 100000 and frame.evaluate('()=>DEFAULT_PROFILE.persona.art_status==="placeholder"'))
            close_preview(q)
            q.click('#loadExample')
            example = lite.check_text((ROOT / 'examples/lite/example.json').read_text(encoding='utf-8'))['data']
            record('Example loads fictional text without borrowing artwork', state(q)['ok'] and state(q)['art'] == 'placeholder' and example['name'] != 'Link' and example['card']['title'] != '筑星者')
            record('Loading an example revokes earlier confirmation', not q.is_checked('#confirmCheck') and q.locator('#generate').is_disabled())
            frame = generate(q)
            got = frame.evaluate('()=>twinlightSkill.getState()')
            topics = sum(len(theme['topics']) for theme in example['themes'])
            record('Every fictional example star and planet is built', got['stars'] == len(example['themes']) and got['planets'] == topics, got)
            record('Generated fictional example does not contain the author biography', '筑星者' not in q.evaluate('()=>twinlightViewer.html()') and frame.evaluate('()=>DEFAULT_PROFILE.name') == example['name'])
            close_preview(q)

            paste(q, good)
            q.set_input_files('#prototypeFile', str(tmp / 'prototype.png'))
            q.wait_for_function('()=>twinlightViewer.getState().art==="static"')
            record('A lone prototype is reported as a static card', state(q)['art'] == 'static')
            frame = generate(q)
            record('Static preview retains truthful status', frame.evaluate('()=>DEFAULT_PROFILE.persona.art_status==="static"&&DEFAULT_PROFILE.persona.art_mode==="static"'))
            frame.evaluate('()=>twinlightV10.showCard()')
            frame.wait_for_function('()=>holo.ready||holo.failed', timeout=20000)
            record('Zero-depth static preview compiles in WebGL', frame.evaluate('()=>holo.ready&&!holo.failed'))
            static_pixels = frame.evaluate('()=>HOLO_LAYERS.background')
            record('Static prototype is kept without cropping', decoded(static_pixels).tobytes() == Image.open(tmp / 'prototype.png').convert('RGBA').tobytes())
            q.screenshot(path=str(a.out / 'viewer-static-card.png'))
            static_html = q.evaluate('()=>twinlightViewer.html()')
            record('Static template has zero signed depths', all(token in static_html for token in ['bu=parallax(uv,float(0)*uDepth)', 'su=parallax(uv,float(0)*uDepth)', 'eu=parallax(uv,float(0)*uDepth)']))
            close_preview(q)

            import_layers(q, manifest_files(tmp / 'native'))
            record('Native layers require renewed confirmation', not q.is_checked('#confirmCheck') and q.locator('#generate').is_disabled())
            frame = generate(q)
            frame.evaluate('()=>twinlightV10.showCard()')
            frame.wait_for_function('()=>holo.ready||holo.failed', timeout=20000)
            record('Native layer card preserves current binding', frame.evaluate('()=>DEFAULT_PROFILE.persona.persona_digest') == persona_digest)
            sub_uri = frame.evaluate('()=>HOLO_LAYERS.subject')
            original = Image.open(tmp / 'native/subject.png').convert('RGBA')
            record('Subject pixels and full-canvas coordinates are unchanged', decoded(sub_uri).size == original.size and decoded(sub_uri).tobytes() == original.tobytes())
            q.screenshot(path=str(a.out / 'viewer-native-card.png'))
            layered_html = q.evaluate('()=>twinlightViewer.html()')
            close_preview(q)

            changed = copy.deepcopy(data); changed['intro'] = '经过本人检查的新开场白。'
            paste(q, json.dumps(changed, ensure_ascii=False))
            record('Editing any public copy revokes confirmation', not q.is_checked('#confirmCheck') and q.locator('#generate').is_disabled())
            changed['name'] = '另一个人'
            paste(q, json.dumps(changed, ensure_ascii=False))
            record('Changing persona drops the old artwork', state(q)['ok'] and state(q)['art'] == 'placeholder')
            import_layers(q, manifest_files(tmp / 'native'), expected='error')
            record('Old artwork cannot be attached to the new person', state(q)['art'] == 'placeholder')

            paste(q, good)
            import_layers(q, str(tmp / 'card.json'))
            record('Portable card imports the same validated native layers', state(q)['art'] == 'layered')
            frame = generate(q)
            record('Portable card keeps the original persona binding', frame.evaluate('()=>DEFAULT_PROFILE.persona.persona_digest') == persona_digest)
            close_preview(q)
            record('No matting helper was called', q.evaluate('()=>window.__matteCalls===0'))
            record('No template tokens remain', not any(f'__{key}__' in layered_html for key in ['PROFILE', 'CARD_DATA', 'CARD_LAYERS', 'V9_CARD_IMAGE', 'DEPTH_BG', 'DEPTH_SUBJECT', 'DEPTH_EFFECTS']))
            record('Viewer made no external requests', not network, network)
            record('No page errors', not errors, errors)
            b.close()

        for name, html in [('generated', layered_html), ('generated-placeholder', placeholder_html), ('generated-static', static_html)]:
            gen = a.out / (name + '.html'); gen.write_text(html, encoding='utf-8')
            cmd = [sys.executable, str(ROOT / 'scripts/verify_browser.py'), '--html', str(gen), '--out', str(a.out / name)]
            if a.browser: cmd += ['--browser', a.browser]
            result = subprocess.run(cmd, capture_output=True, text=True)
            record(name + ' output passes verify_browser.py', result.returncode == 0, (result.stdout + result.stderr)[-1800:])
    except Exception as exc:
        status = 1
        report['failure'] = f'{type(exc).__name__}: {exc}'
        print('ERROR', report['failure'], file=sys.stderr)
    finally:
        if server is not None:
            server.shutdown(); server.server_close()
            thread.join(timeout=2)
report['ok'] = status == 0
(a.out / 'viewer-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'ok': status == 0, 'checks': len(checks), 'out': str(a.out)}, ensure_ascii=False))
raise SystemExit(status)
