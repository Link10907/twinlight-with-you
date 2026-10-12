#!/usr/bin/env python3
"""Check card-free V10 UI. Injected diagnostics never count as offline file-open."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

def verify(html: Path,out: Path,browser: str,load_mode: str='file') -> dict:
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True,exist_ok=True);checks=[];errors=[];webgl=[];net=[]
    raw=html.read_text(encoding='utf-8')
    result={'version':'galaxy-browser-1','html_sha256':hashlib.sha256(html.read_bytes()).hexdigest(),
            'load_mode':load_mode,'offline_file_open':'unverified','webgl':'unverified',
            'real_time_fusion_verified':False,'checks':checks,'page_errors':errors,
            'scope':'Card-free UI, layout and deterministic ending/return; not native image or GPU artistic acceptance.'}
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path=browser,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        try:
            for label,width,height in [('desktop',1440,1000),('mobile',390,844)]:
                page=b.new_page(viewport={'width':width,'height':height})
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:net.append(r.url) if r.url.startswith(('http:','https:')) else None)
                page.route('http://**',lambda r:r.abort());page.route('https://**',lambda r:r.abort())
                if load_mode=='file':
                    try:page.goto(html.resolve().as_uri(),wait_until='load',timeout=15000)
                    except Exception as e:
                        result.update(status='unavailable',offline_file_open='unavailable',reason=str(e).splitlines()[0])
                        return result
                    result['offline_file_open']='passed'
                else:page.set_content(raw,wait_until='load',timeout=15000)
                page.wait_for_function('!!window.galaxyDebug && state.ready',timeout=15000)
                page.wait_for_timeout(1300)
                def test(name,value):checks.append({'name':label+':'+name,'passed':bool(value)})
                st=page.evaluate('window.twinlightSkill.getState()');test('card_feature_disabled',st['cardEnabled'] is False)
                test('no_card_dom',page.locator('#identityScene,#cardExportReview,#v8CardShortcut').count()==0)
                test('no_horizontal_overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                webgl.append(page.evaluate('window.galaxyDebug.getState().webgl'))
                page.screenshot(path=str(out/(label+'-home.png')))
                page.evaluate('window.galaxyDebug.go(0);window.galaxyDebug.finish()')
                test('chapter_navigation',page.evaluate('window.galaxyDebug.getState().active===0'))
                # Use V10's own inspection hook; this is not real-time GPU proof.
                page.evaluate('window.twinlightV10.seek(14)')
                test('ending_reachable',page.evaluate('window.twinlightV10.getState().time===14 && !document.querySelector("#galaxyEndActions").hidden'))
                page.screenshot(path=str(out/(label+'-ending.png')))
                page.locator('#galaxyReturn').click(timeout=5000)
                test('return_to_galaxy',page.evaluate('window.galaxyDebug.getState().mode==="personal" && document.querySelector("#encounterCinema").hidden'))
                page.evaluate('location.hash="card"');page.wait_for_timeout(100)
                test('card_hash_does_not_reveal_card',page.evaluate('location.hash==="#galaxy" && !document.querySelector("#identityScene")'))
                page.close()
        finally:b.close()
    checks.append({'name':'no_uncaught_js_errors','passed':not errors})
    checks.append({'name':'no_remote_runtime_requests','passed':not net})
    result['webgl']='passed' if webgl and all(webgl) else 'unavailable'
    result['status']='failed' if errors or not all(c['passed'] for c in checks) else ('passed' if load_mode=='file' and all(webgl) else 'limited')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--html',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--browser',default='/usr/bin/chromium');p.add_argument('--load-mode',choices=['file','injected'],default='file');a=p.parse_args()
    try:r=verify(a.html,a.out,a.browser,a.load_mode)
    except Exception as e:r={'status':'failed','error':str(e),'scope':'No successful validation is implied.'}
    a.out.mkdir(parents=True,exist_ok=True);(a.out/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False,indent=2));return 2 if r['status']=='failed' else 0
if __name__=='__main__':raise SystemExit(main())
