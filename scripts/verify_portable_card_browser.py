#!/usr/bin/env python3
"""Execute the unchanged V10 card: parallax, foil, mouse/touch, flip and reduced motion.

File opening is the default; --load-mode injected is explicitly limited. This
runner checks behavior using actual DOM/canvas pixels, not illustration quality.
"""
from __future__ import annotations
import argparse
import base64
import io
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from twinlight_core.portable_layers import sha
from twinlight_core.common import save
from twinlight_core.browser_runtime import launch_flags


def verify(html: Path, out: Path, *, browser: str | None = None, load_mode: str = 'file',
           gpu_mode: str = 'auto', force_css: bool = False, report_path: Path | None = None) -> dict:
    html = html.resolve(); out = out.resolve(); out.mkdir(parents=True, exist_ok=True)
    report_path = (report_path or out / 'report.json').resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if not out.is_relative_to(report_path.parent):
        raise ValueError('Evidence directory must be inside the report directory')
    r = {'version': 'portable-card-motion-1', 'status': 'unavailable', 'html_sha256': sha(html),
         'backend': 'unverified', 'load_mode': load_mode, 'offline_file_open': 'unverified',
         'interaction_verified': False, 'parallax_verified': False, 'foil_verified': False,
         'fixed_text_verified': False, 'flip_verified': False, 'touch_verified': False,
         'reduced_motion_verified': False, 'checks': [], 'frames': {},
         'forced_css': force_css, 'artwork_review_performed': False,
         'not_tested': ['Art quality/likeness', 'Provider provenance', 'Physical phones', 'Galaxy finale'],
         'scope': 'Actual card runtime only; geometric fixtures are not approved personal artwork.'}
    stage = 'launch'
    def check(name, yes):
        r['checks'].append({'name': name, 'passed': bool(yes)})
        if not yes: raise AssertionError(name)
    def frame(name, image):
        p = out / (name + '.png'); image.save(p)
        r['frames'][name] = {'file': p.relative_to(report_path.parent).as_posix(), 'sha256': sha(p)}
    def capture(page):
        if r['backend'] == 'webgl':
            data = page.evaluate('()=>holoCanvas.toDataURL("image/png").split(",")[1]')
            return Image.open(io.BytesIO(base64.b64decode(data))).convert('RGB')
        # Remove physical outer tilt only during a local-art capture. It remains
        # exercised by the real mouse/touch checks below.
        style = page.add_style_tag(content='.card-tilt{transform:none!important}')
        try:
            return Image.open(io.BytesIO(page.locator('.holo-fallback').screenshot())).convert('RGB')
        finally:
            style.evaluate('(node)=>node.remove()')
    def diff(a, b, mask=None):
        if a.size != b.size: raise AssertionError('Changed card capture dimensions')
        return sum(ImageStat.Stat(ImageChops.difference(a, b), mask).mean) / 3
    override = """(()=>{const base=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(t,...args){return /^webgl|experimental-webgl/.test(t)?null:base.call(this,t,...args)}})()"""
    def open_page(context):
        page = context.new_page(); page.on('pageerror', lambda e: errors.append(str(e)))
        if force_css:
            page.add_init_script(override)
            if load_mode == 'injected': page.evaluate(override)
        if load_mode == 'file': page.goto(html.as_uri(), wait_until='load', timeout=20000)
        else: page.set_content(html.read_text(), wait_until='load', timeout=20000)
        # Same runner can inspect the integrated page, not merely an auxiliary PNG.
        page.wait_for_function('()=>typeof showIdentityCard==="function"', timeout=10000)
        page.evaluate('()=>{if(!v8.cardOpen)showIdentityCard()}')
        page.wait_for_function('()=>holo.ready||holo.failed', timeout=20000)
        page.wait_for_function('()=>Array.from(holoFallback.querySelectorAll("img")).every(i=>i.complete&&i.naturalWidth>0)', timeout=10000)
        page.wait_for_timeout(100)
        return page
    errors = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch(executable_path=browser, headless=True, args=launch_flags(gpu_mode))
            try:
                r['browser_version'] = b.version
                backends = []
                for width, height in ((1440, 900), (390, 844)):
                    context = b.new_context(viewport={'width': width, 'height': height},
                                            is_mobile=width == 390, has_touch=width == 390)
                    stage = 'open'; page = open_page(context); stage = 'checks'
                    backend = page.evaluate('()=>holo.ready&&!holo.failed?"webgl":"css-layered"')
                    r['backend'] = backend; backends.append(backend)
                    check('Actual independent image layers ' + str(width), page.evaluate('()=>__holo.getState().layers>=5&&!holoStaticArt()'))
                    check('No horizontal overflow ' + str(width), page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth'))
                    page.evaluate('()=>{holo.depth=1;holo.foil=0;holo.finish=0;holo.elapsed=0;__holo.setView(0,-.4)}')
                    a = capture(page)
                    text_left = page.evaluate("()=>getComputedStyle(holoFallback.querySelector('[data-layer=text]')).transform")
                    page.evaluate('()=>__holo.setView(0,.4)'); right = capture(page)
                    check('Internal layer parallax, foil disabled ' + str(width), diff(a, right) > .3)
                    if width == 1440: frame('left', a); frame('right', right)
                    if backend == 'webgl':
                        encoded = page.evaluate('''()=>{const c=document.createElement('canvas');c.width=holoCanvas.width;c.height=holoCanvas.height;const x=c.getContext('2d');x.drawImage(holo.images.text,0,0,c.width,c.height);const d=x.getImageData(0,0,c.width,c.height);for(let i=0;i<d.data.length;i+=4){const v=d.data[i+3]===255?255:0;d.data[i]=d.data[i+1]=d.data[i+2]=v;d.data[i+3]=255;}x.putImageData(d,0,0);return c.toDataURL().split(',')[1]}''')
                        mask = Image.open(io.BytesIO(base64.b64decode(encoded))).convert('L')
                        check('Opaque text available for comparison ' + str(width), mask.histogram()[255] >= 20)
                        check('Text stays fixed while artwork moves ' + str(width), diff(a, right, mask) < .5)
                    else:
                        check('Text stays fixed while artwork moves ' + str(width), text_left == page.evaluate("()=>getComputedStyle(holoFallback.querySelector('[data-layer=text]')).transform"))
                    page.evaluate('()=>{holo.depth=0;__holo.setView(0,-.4)}'); zleft = capture(page)
                    page.evaluate('()=>__holo.setView(0,.4)'); zright = capture(page)
                    check('Zero depth removes internal parallax ' + str(width), diff(zleft, zright) < .2)
                    if backend == 'webgl':
                        page.evaluate('()=>{holo.foil=.7;holo.elapsed=0;__holo.setView(0,-.4)}'); fleft = capture(page)
                        page.evaluate('()=>{holo.elapsed=0;__holo.setView(0,.4)}'); fright = capture(page)
                        check('Foil visible without parallax ' + str(width), diff(zright, fright) > .2)
                        check('Foil changes with viewing angle ' + str(width), diff(fleft, fright) > .2)
                        if width == 1440: frame('foil_off', zright); frame('foil_on', fright)
                        check('No WebGL errors ' + str(width), page.evaluate('()=>holo.gl.getError()===0'))
                    page.evaluate('()=>{holo.depth=1;holo.foil=.5;__holo.setView(-.045,-.14)}')
                    # Auto motion is tested as elapsed renderer/view state, not a still screenshot.
                    page.locator('#holoAuto').click(); before = page.evaluate('()=>[holo.x,holo.y]')
                    page.wait_for_timeout(220); after = page.evaluate('()=>[holo.x,holo.y]')
                    check('Automatic sway actually moves ' + str(width), any(abs(x-y) > .002 for x, y in zip(before, after)))
                    page.locator('#holoAuto').click()
                    page.locator('#identityCard').scroll_into_view_if_needed()
                    box = page.locator('#identityCard').bounding_box()
                    check('Card reachable ' + str(width), bool(box) and box['width'] > 100)
                    x, y = box['x'] + box['width']/2, box['y'] + box['height']/2
                    page.evaluate('()=>__holo.setView(0,-.14)')
                    if width == 390:
                        session = context.new_cdp_session(page)
                        session.send('Input.dispatchTouchEvent', {'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
                        for d in (10,20,30,40):
                            session.send('Input.dispatchTouchEvent', {'type':'touchMove','touchPoints':[{'x':x+d,'y':y-8}]})
                        session.send('Input.dispatchTouchEvent', {'type':'touchEnd','touchPoints':[]})
                        # The next control tap is a separate human gesture, not
                        # an immediate synthetic continuation of the drag.
                        page.wait_for_timeout(400)
                    else:
                        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+40,y-8,steps=4);page.mouse.up()
                    check(('Touch' if width==390 else 'Mouse')+' drag without accidental flip', page.evaluate('()=>holo.ty>0&&!v8.flipped&&holo.drag===null'))
                    (page.locator('#cardFlip').tap if width==390 else page.locator('#cardFlip').click)()
                    page.wait_for_function('()=>v8.flipped',timeout=2500)
                    check('Explicit front/back flip '+str(width), page.evaluate('()=>v8.flipped'))
                    page.locator('#identityCard').focus();page.keyboard.press('Home');page.keyboard.press('ArrowRight')
                    check('Keyboard view control '+str(width),page.evaluate('()=>holo.ty>-.14&&!v8.flipped'))
                    page.keyboard.press('Enter');check('Keyboard flip '+str(width),page.evaluate('()=>v8.flipped'))
                    page.keyboard.press('Home');check('Reset restores front '+str(width),page.evaluate('()=>!v8.flipped&&Math.abs(holo.ty+.14)<.001'))
                    context.close()
                check('Consistent desktop/mobile backend',len(set(backends))==1)
                context=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
                page=open_page(context)
                check('Reduced motion disables automatic sway',page.evaluate('()=>state.reduced&&!holo.auto'))
                before=page.evaluate('()=>[holo.elapsed,holo.x,holo.y]');page.wait_for_timeout(220);after=page.evaluate('()=>[holo.elapsed,holo.x,holo.y]')
                check('Reduced motion remains stable',all(abs(x-y)<.001 for x,y in zip(before,after)))
                page.locator('#cardFlip').click();check('Reduced motion retains manual flip',page.evaluate('()=>v8.flipped'))
                context.close();check('No JavaScript exceptions',not errors)
                check('Inspection did not rewrite HTML',sha(html)==r['html_sha256'])
                r.update(status='passed' if load_mode=='file' and r['backend']=='webgl' else 'limited',
                         offline_file_open='passed' if load_mode=='file' else 'unverified',
                         interaction_verified=True,parallax_verified=True,fixed_text_verified=True,
                         flip_verified=True,touch_verified=True,reduced_motion_verified=True,
                         foil_verified=r['backend']=='webgl')
            finally: b.close()
    except Exception as exc:
        # Browser launch/policy limits are not image-tool absence. Once execution
        # starts, assertion/JS/asset failures are real failures and block delivery.
        unavailable=stage=='launch' or (stage=='open' and (any(code in str(exc) for code in ('ERR_ACCESS_DENIED','ERR_BLOCKED_BY_ADMINISTRATOR','Not allowed to load local resource'))))
        r.update(status='unavailable' if unavailable else 'failed',reason=str(exc))
    save(report_path,r)
    return r


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--html',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--report',type=Path);p.add_argument('--browser')
    p.add_argument('--load-mode',choices=('file','injected'),default='file')
    p.add_argument('--gpu-mode',choices=('auto','swiftshader'),default='auto')
    p.add_argument('--force-css',action='store_true',help='Test real no-WebGL fallback; never call it a foil pass')
    a=p.parse_args()
    r=verify(a.html,a.out,browser=a.browser,load_mode=a.load_mode,gpu_mode=a.gpu_mode,force_css=a.force_css,report_path=a.report)
    print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['status'] in ('passed','limited') else 2

if __name__=='__main__':raise SystemExit(main())
