#!/usr/bin/env python3
"""Exercise the additive V10 navigator on the ACTUAL supplied HTML.

The default copies only index.html into an empty temporary directory and opens
file:// while offline. --load-mode injected is a development-only DOM check:
it can never authorize offline/file delivery or replace WebGL/full-story checks.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path


def verify(html: Path, out: Path, *, browser: str | None = None, load_mode: str = 'file') -> dict:
    from playwright.sync_api import sync_playwright
    from twinlight_core.run import _browser_binary
    raw=html.read_bytes()
    report={'version':'navigation-browser-1','html_sha256':hashlib.sha256(raw).hexdigest(),
            'ok':False,'load_mode':load_mode,'checks':[], 'page_errors':[], 'resource_requests':[],
            'file_open_verified':False,'offline_self_contained_verified':False,
            'webgl_verified':False,'full_finale_replay_verified':False,
            'independent_visual_review_performed':False,
            'not_tested':['Art quality','Real device performance','Full 14-second finale (separate integration gate)',
                          'Chat attachment viewer','Visual foil/depth (separate WebGL gate)'],
            'scope':'Actual DOM/navigation checks; injected mode is not local-file or final-release verification.'}
    out.mkdir(parents=True,exist_ok=True)
    def save():
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def record(name, passed, detail=None):
        report['checks'].append({'name':name,'passed':bool(passed),'detail':detail});save()
        if not passed:raise AssertionError(name)
    def wait(page, view):
        page.wait_for_function('(v)=>window.twinlightNavigation?.getState().ready && !twinlightNavigation.getState().pending && twinlightNavigation.getState().view===v',arg=view,timeout=20000)
    def go(page, view):
        page.evaluate('(v)=>twinlightNavigation.go(v)',view);wait(page,view)
    try:
        with tempfile.TemporaryDirectory(prefix='twinlight-single-file-') as folder, sync_playwright() as pw:
            isolated=Path(folder)/'index.html';isolated.write_bytes(raw)
            binary=_browser_binary(browser)
            b=pw.chromium.launch(executable_path=binary,headless=True,args=['--no-sandbox'])
            report['browser_version']=b.version
            context=b.new_context(viewport={'width':1440,'height':900},offline=True,reduced_motion='no-preference')
            def open_page(fragment='galaxy'):
                page=context.new_page()
                page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                page.on('request',lambda r:report['resource_requests'].append(r.url) if r.url.startswith(('http:','https:')) else None)
                if load_mode=='file':
                    page.goto(isolated.as_uri()+'#'+fragment,wait_until='load',timeout=15000)
                else:
                    page.evaluate('(h)=>history.replaceState(null,"",h)','#'+fragment)
                    page.set_content(raw.decode('utf-8'),wait_until='load')
                wait(page,'card' if fragment=='card' else 'galaxy')
                page.wait_for_function('()=>document.getElementById("loading").hidden',timeout=15000)
                return page
            q=open_page()
            record('Current navigator initialized',q.evaluate('()=>twinlightNavigation.version')=='navigation-1.0.0')
            # Freeze only in the test harness for exact restoration comparison;
            # production navigation never freezes the galaxy render loop.
            q.evaluate('()=>{galaxyDebug.freeze();quietPick(0);quietRead();if(state.flight)finishFlight();}')
            q.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
            q.evaluate('()=>{$("reader").scrollTop=60;window.__savedAudio=bgm;}')
            snapshot='()=>({mode:state.mode,active:state.active,topic:state.topic,cam:state.cam,target:state.target,fov:state.fov,orbit,selection:quiet.selection,reading:quiet.reading,readerHidden:$("reader").hidden,scroll:$("reader").scrollTop})'
            before=q.evaluate(snapshot)
            go(q,'card')
            record('Quick entry opens the original card',q.evaluate('()=>v8.cardOpen && document.querySelectorAll("#identityCard").length===1 && document.querySelectorAll("#holoCanvas").length===1'))
            report['card_runtime']=q.evaluate('()=>__holo.getState()')
            q.screenshot(path=str(out/'card-desktop.png'))
            q.locator('#identityClose').click();wait(q,'galaxy')
            after=q.evaluate(snapshot)
            record('Return restores camera, selected star and reader state',before==after,{'before':before,'after':after})
            go(q,'card');q.evaluate('()=>history.back()');wait(q,'galaxy')
            q.evaluate('()=>history.forward()');wait(q,'card')
            record('Browser back/forward updates the view',q.evaluate('()=>location.hash==="#card" && v8.cardOpen'))
            go(q,'galaxy')
            q.evaluate('()=>{twinlightNavigation.go("card");twinlightNavigation.go("galaxy");twinlightNavigation.go("card");twinlightNavigation.go("galaxy");}')
            wait(q,'galaxy')
            record('Rapid navigation cancels stale transitions',q.evaluate('()=>!v8.cardOpen && twinlightNavigation.getState().target==="galaxy"'))
            go(q,'finale')
            record('Legacy finale route starts the retained story',q.evaluate('()=>state.encounterCinematic && v10.total===14') if q.evaluate('()=>"total" in v10') else q.evaluate('()=>state.encounterCinematic && twinlightV10.getState().total===14'))
            # Abort mid-story; no completion claim from this seek-free route check.
            go(q,'galaxy')
            record('Leaving finale cancels story and returns to saved galaxy',q.evaluate('()=>!state.encounterCinematic && !v10.playing && !v8.cardOpen'))
            go(q,'card');q.keyboard.press('Escape');wait(q,'galaxy')
            record('Escape uses the same return controller',q.evaluate('()=>!v8.cardOpen'))
            record('Repeated navigation keeps one card renderer and audio instance',q.evaluate('()=>document.querySelectorAll("#identityCard").length===1 && document.querySelectorAll("#holoCanvas").length===1 && bgm===window.__savedAudio'))
            q.screenshot(path=str(out/'galaxy-desktop.png'))
            q.close()
            direct=open_page('card')
            # Wait past the old core's 1300-ms boot timer: it must not reopen or replay.
            count=direct.evaluate('()=>twinlightNavigation.getState().transitions')
            direct.wait_for_timeout(1500)
            record('Initial #card waits for readiness and suppresses the legacy timer',direct.evaluate('()=>twinlightNavigation.getState().transitions')==count and direct.evaluate('()=>v8.cardOpen'))
            go(direct,'galaxy');direct.close()
            q=open_page();q.set_viewport_size({'width':390,'height':844})
            q.wait_for_timeout(250)
            record('Mobile view has no horizontal document overflow',q.evaluate('()=>document.documentElement.scrollWidth<=innerWidth+1'))
            boxes=q.locator('.header .brand,.header nav,.header-right').evaluate_all('(es)=>es.filter(e=>e.getClientRects().length).map(e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom}})')
            record('Mobile header controls fit without clipping or overlap',all(x['left']>=-1 and x['right']<=391 for x in boxes) and all(x['right']<=y['left']+2 for x,y in zip(boxes,boxes[1:])),boxes)
            q.locator('#twinlightNavCard').click();wait(q,'card')
            record('Mobile quick entry and close are visible',q.locator('#identityClose').is_visible())
            q.screenshot(path=str(out/'card-mobile.png'))
            q.locator('#identityClose').click();wait(q,'galaxy')
            q.screenshot(path=str(out/'galaxy-mobile.png'))
            record('No page exceptions',not report['page_errors'],report['page_errors'])
            record('No HTTP resource requests from the self-contained page',not report['resource_requests'])
            record('Source HTML unchanged during verification',hashlib.sha256(html.read_bytes()).hexdigest()==report['html_sha256'])
            report['file_open_verified']=load_mode=='file'
            report['offline_self_contained_verified']=load_mode=='file'
            report['ok']=True;report['status']='navigation_passed' if load_mode=='file' else 'injected_navigation_only'
            b.close()
    except Exception as exc:
        report['failure']=str(exc)[:2500]
        unavailable=any(x in str(exc).lower() for x in ('err_blocked_by_administrator',"executable doesn't exist",'browsertype.launch','operation not permitted'))
        report['capability_unavailable']=unavailable
        report['status']='capability_unavailable' if unavailable else 'navigation_failed'
    report['delivery_eligible']=report['ok'] and report['offline_self_contained_verified']
    save();return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--html',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--browser');p.add_argument('--load-mode',choices=('file','injected'),default='file')
    a=p.parse_args()
    r=verify(a.html,a.out,browser=a.browser,load_mode=a.load_mode)
    print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['ok'] else 2

if __name__=='__main__':raise SystemExit(main())
