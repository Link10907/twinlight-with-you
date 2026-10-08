#!/usr/bin/env python3
"""Exercise the real shared card renderer. This does not certify illustration quality."""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from twinlight_core.browser_runtime import launch_flags


def verify(html: Path, out: Path, binary: str | None = None, *, gpu_mode: str = "auto", headed: bool = False, channel: str | None = None) -> dict:
    from playwright.sync_api import sync_playwright
    html, out = html.resolve(), out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    content = html.read_bytes()
    report = {'ok': False, 'html_sha256': hashlib.sha256(content).hexdigest(), 'checks': [],
              'requested_runtime': {'gpu_mode':gpu_mode,'headed':headed,'channel':channel},
              'release_authorized':False, 'webgl': False, 'interaction_verified': False, 'foil_verified': False,
              'fixed_text_verified': False, 'touch_verified': False, 'reduced_motion_verified': False,
              'scope': 'Real shared card renderer; desktop and emulated mobile, native pixel motion, view-dependent foil, fixed text, drag, flip, keyboard and reduced motion.',
              'not_tested': ['Illustration quality and subject likeness', 'External generation provenance',
                             'Physical mobile devices', 'Chat-host inline HTML preview']}
    def check(name, condition):
        report['checks'].append({'name': name, 'passed': bool(condition)})
        if not condition: raise AssertionError(name)
    def pixels(page, expression='()=>holoCanvas.toDataURL("image/png").split(",")[1]'):
        return Image.open(io.BytesIO(base64.b64decode(page.evaluate(expression)))).convert('RGB')
    def diff(a, b, mask=None):
        if a.size != b.size: raise AssertionError('Card canvas changed dimensions')
        return sum(ImageStat.Stat(ImageChops.difference(a, b), mask).mean) / 3
    browser = None
    try:
        with sync_playwright() as pw:
            if binary and channel: raise ValueError('--browser and --channel are mutually exclusive')
            browser = pw.chromium.launch(executable_path=binary, channel=channel,
                                         headless=not headed, args=launch_flags(gpu_mode))
            report['browser_version']=browser.version
            errors = []
            for width, height in ((1440, 900), (390, 844)):
                context = browser.new_context(viewport={'width': width, 'height': height},
                                              is_mobile=width == 390, has_touch=width == 390)
                page = context.new_page()
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.set_content(content.decode('utf-8'), wait_until='load')
                page.wait_for_function('()=>holo.ready||holo.failed', timeout=20000)
                check('Renderer initialized ' + str(width), page.evaluate('()=>holo.ready||holo.failed'))
                # CSS fallback is useful, but cannot establish the requested foil effect.
                report['capability_unavailable'] = not page.evaluate('()=>holo.ready&&!holo.failed')
                if report['capability_unavailable']:
                    page.screenshot(path=str(out / f'{width}-fallback.png'))
                check('Native WebGL foil renderer available ' + str(width), not report['capability_unavailable'])
                check('Native card mode ' + str(width), page.evaluate('()=>__holo.getState().layers>=5&&!holoStaticArt()&&currentPersona().art_status!=="placeholder"'))
                check('No horizontal overflow ' + str(width), page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth'))
                page.evaluate('()=>{holo.elapsed=0;holo.finish=0;holo.foil=0;holo.depth=1;__holo.setView(0,-.45)}')
                left = pixels(page)
                page.screenshot(path=str(out / f'{width}-left.png'))
                page.evaluate('()=>__holo.setView(0,.45)')
                right = pixels(page)
                page.screenshot(path=str(out / f'{width}-right.png'))
                check('Internal parallax with foil disabled ' + str(width), diff(left, right) > .5)
                # Compare opaque text pixels in FBO space, with foil off. Eroding
                # the resized mask would discard thin serif strokes and narrow frames.
                mask = pixels(page, '''()=>{const c=document.createElement('canvas');c.width=holoCanvas.width;c.height=holoCanvas.height;const x=c.getContext('2d');x.drawImage(holo.images.text,0,0,c.width,c.height);const d=x.getImageData(0,0,c.width,c.height);for(let i=0;i<d.data.length;i+=4){const v=d.data[i+3]===255?255:0;d.data[i]=d.data[i+1]=d.data[i+2]=v;d.data[i+3]=255;}x.putImageData(d,0,0);return c.toDataURL('image/png').split(',')[1];}''').convert('L')
                check('Text provides opaque pixels for motion comparison ' + str(width), mask.histogram()[255] >= 20)
                check('Text stays fixed while art moves ' + str(width), diff(left, right, mask) < .5)
                page.evaluate('()=>{holo.depth=0;__holo.setView(0,-.45)}')
                zero_left = pixels(page)
                page.evaluate('()=>__holo.setView(0,.45)')
                zero_right = pixels(page)
                check('Zero depth removes parallax ' + str(width), diff(zero_left, zero_right) < .15)
                page.evaluate('()=>{holo.foil=.6;holo.elapsed=0;__holo.setView(0,-.45)}')
                foil_left = pixels(page)
                page.evaluate('()=>{holo.elapsed=0;__holo.setView(0,.45)}')
                foil_right = pixels(page)
                check('Foil appears independently of depth ' + str(width), diff(foil_right, zero_right) > .25)
                check('Foil responds to view, not time ' + str(width), diff(foil_left, foil_right) > .25)
                page.screenshot(path=str(out / f'{width}-foil.png'))
                check('WebGL has no errors ' + str(width), page.evaluate('()=>holo.gl.getError()===0'))
                page.evaluate('()=>{holo.depth=1;holo.foil=.5;__holo.setView(-.05,-.15)}')
                box = page.locator('#identityCard').bounding_box()
                check('Card visible and reachable ' + str(width), box is not None and box['x'] >= 0 and box['x'] + box['width'] <= width + 1 and box['y'] >= 0 and box['y'] + box['height'] <= height + 1)
                x, y = box['x'] + box['width']/2, box['y'] + box['height']/2
                if width == 390:
                    session = context.new_cdp_session(page)
                    session.send('Input.dispatchTouchEvent', {'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
                    for delta in (10,20,30,40):
                        session.send('Input.dispatchTouchEvent', {'type':'touchMove','touchPoints':[{'x':x+delta,'y':y-8}]})
                    session.send('Input.dispatchTouchEvent', {'type':'touchEnd','touchPoints':[]})
                else:
                    page.mouse.move(x,y); page.mouse.down(); page.mouse.move(x+40,y-8,steps=4); page.mouse.up()
                check(('Touch' if width==390 else 'Mouse') + ' drag rotates without flipping', page.evaluate('()=>holo.ty>0&&!v8.flipped'))
                (page.locator('#cardFlip').tap if width == 390 else page.locator('#cardFlip').click)()
                check('Flip control ' + str(width), page.evaluate('()=>v8.flipped'))
                page.locator('#identityCard').focus()
                page.keyboard.press('Home')
                page.keyboard.press('ArrowRight')
                check('Keyboard changes view ' + str(width), page.evaluate('()=>holo.ty>-.14&&!v8.flipped'))
                page.keyboard.press('Enter')
                check('Keyboard flips card ' + str(width), page.evaluate('()=>v8.flipped'))
                page.keyboard.press('Home')
                page.screenshot(path=str(out / f'{width}.png'))
                context.close()
            context = browser.new_context(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
            page = context.new_page(); page.on('pageerror', lambda e: errors.append(str(e)))
            page.set_content(content.decode('utf-8'), wait_until='load')
            page.wait_for_function('()=>holo.ready||holo.failed', timeout=20000)
            check('Reduced-motion disables automatic sway', page.evaluate('()=>state.reduced&&!holo.auto'))
            before = page.evaluate('()=>[holo.elapsed,holo.x,holo.y]')
            page.wait_for_timeout(250)
            after = page.evaluate('()=>[holo.elapsed,holo.x,holo.y]')
            check('Reduced-motion view remains stable', all(abs(a-b)<.001 for a,b in zip(before,after)))
            page.locator('#cardFlip').click()
            check('Reduced-motion still permits explicit flip', page.evaluate('()=>v8.flipped'))
            context.close()
            check('No page exceptions', not errors)
            check('HTML unchanged by inspection', hashlib.sha256(html.read_bytes()).hexdigest() == report['html_sha256'])
            browser.close(); browser = None
            report.update(ok=True, webgl=True, interaction_verified=True, foil_verified=True,
                          fixed_text_verified=True, touch_verified=True, reduced_motion_verified=True)
    except Exception as exc:
        report['failure'] = str(exc)
    finally:
        report['screenshots_sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.png')}
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--browser')
    parser.add_argument('--gpu-mode',choices=('auto','swiftshader'),default='auto')
    parser.add_argument('--headed',action='store_true')
    parser.add_argument('--channel')
    args=parser.parse_args()
    try:
        result=verify(args.html,args.out,args.browser,gpu_mode=args.gpu_mode,headed=args.headed,channel=args.channel)
    except (OSError,ValueError,ImportError) as exc:
        result={'ok':False,'failure':str(exc),'checks':[]}
        args.out.mkdir(parents=True,exist_ok=True)
        (args.out/'report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['ok'] else 2

if __name__=='__main__': raise SystemExit(main())
