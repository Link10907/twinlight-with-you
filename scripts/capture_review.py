#!/usr/bin/env python3
"""Capture actual V10 card-region A/B states for an independent visual reviewer.

Screenshots/evidence only. Does not certify aesthetics, repair alpha, change the
HTML, or mark release passed. Site continuity comes from verify_browser.py.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from twinlight_core.art_quality import sha256,read_json
from twinlight_core.provider_runtime import save_new
from twinlight_core.browser_runtime import launch_flags
from playwright.sync_api import sync_playwright


def capture(html:Path,root:Path,out:Path,*,mode='both',site_report:Path|None=None,browser=None,channel=None,headed=False,gpu_mode='auto'):
    html,root,out=[p.resolve() for p in (html,root,out)]
    if not html.is_relative_to(root) or not out.is_relative_to(root) or out.exists():raise ValueError('Use current HTML and a new evidence directory inside the review root.')
    out.mkdir(parents=True,mode=0o700);before=sha256(html)
    r={'version':'review-evidence-1','html_sha256':before,'runtime':None,'captures':{},'views':{},'effect_frames':{},'release_authorized':False}
    def ref(p):return {'file':p.relative_to(root).as_posix(),'sha256':sha256(p)}
    def shot(page,name,region=False):
        path=out/(name+'.png')
        if region: page.locator('#identityCard').screenshot(path=str(path),animations='disabled')
        else: page.screenshot(path=str(path),animations='disabled')
        return ref(path)
    try:
        with sync_playwright() as pw:
            b=pw.chromium.launch(executable_path=browser,channel=channel,headless=not headed,args=launch_flags(gpu_mode),timeout=20000)
            for label,(width,height) in [('desktop',(1440,900)),('mobile',(390,844))]:
                ctx=b.new_context(viewport={'width':width,'height':height},reduced_motion='no-preference',is_mobile=label=='mobile',has_touch=label=='mobile')
                page=ctx.new_page();page.set_content(html.read_text(encoding='utf-8'),wait_until='load')
                if mode!='card':
                    page.wait_for_function('()=>state.ready&&window.twinlightSkill',timeout=25000)
                    page.wait_for_function('()=>document.getElementById("loading").hidden',timeout=15000)
                    if label=='desktop': r['home_capture']=shot(page,'home')
                    if mode=='both':page.evaluate('()=>twinlightV10.showCard()')
                if mode=='html':
                    r['captures'][label]=shot(page,label)
                    if label=='desktop':r['runtime']={'html_sha256':before,'page_ready':True,'backend':'webgl' if page.evaluate('()=>state.gl') else 'fallback','merge_seconds':None}
                else:
                    page.wait_for_function('()=>holo.ready||holo.failed',timeout=25000)
                    ready=page.evaluate('()=>holo.ready&&!holo.failed')
                    if label=='desktop':r['runtime']={'html_sha256':before,'page_ready':True,'backend':'webgl' if ready else 'css_fallback','webgl_ready':ready,'fallback':not ready,'merge_seconds':None,'browser_version':b.version}
                    # __holo.setView pauses auto and sets x/y without relying on pointer location.
                    page.evaluate('()=>{holo.auto=false;holo.elapsed=0;holo.finish=0;holo.depth=1;holo.foil=.5;__holo.setView(-.06,.38)}')
                    page.wait_for_timeout(400)
                    r['captures'][label]=shot(page,label)
                    if label=='mobile':r['views']['mobile']=r['captures'][label]
                    if label=='desktop':
                        for side,y in [('left',-.38),('right',.38)]:
                            page.evaluate('(y)=>{holo.auto=false;holo.elapsed=0;holo.depth=1;holo.foil=0;__holo.setView(-.06,y)}',y)
                            r['views'][side]=shot(page,side)
                        for name,depth,foil in [('foil_off',1,0),('foil_on',1,.7),('depth_off',0,0),('depth_on',1,0)]:
                            page.evaluate('([d,f])=>{holo.auto=false;holo.elapsed=0;holo.finish=0;holo.depth=d;holo.foil=f;__holo.setView(-.06,.38)}',[depth,foil])
                            state=page.evaluate('()=>({x:holo.x,y:holo.y,depth:holo.depth,foil:holo.foil,time:holo.elapsed,finish:holo.finish,viewport:[innerWidth,innerHeight],paused:!holo.auto,region:"card"})')
                            r['effect_frames'][name]={'image':shot(page,name,True),'state':state}
                ctx.close()
            b.close()
        if site_report:
            s=read_json(site_report)
            if s.get('html_sha256')!=before:raise ValueError('Site browser report belongs to different HTML bytes.')
            # Store a copy as current evidence, no edits to its actual checks/measurements.
            copied=out/'site-browser-report.json';copied.write_bytes(site_report.read_bytes());r['site_report']=ref(copied)
            if s.get('continuous_verified') is True and s.get('finale',{}).get('autoplay_verified') is True:
                r['runtime']['merge_seconds']=s['finale'].get('wall_seconds')
        if sha256(html)!=before:raise ValueError('HTML changed while collecting evidence.')
        r['ok']=True
    except Exception as exc:r.update(ok=False,error=str(exc))
    save_new(out/'review-evidence.json',r)
    return r


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('html','root','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--mode',choices=('both','card','html'),default='both');p.add_argument('--site-report',type=Path)
    p.add_argument('--browser');p.add_argument('--channel');p.add_argument('--headed',action='store_true');p.add_argument('--gpu-mode',choices=('auto','swiftshader'),default='auto')
    a=p.parse_args();r=capture(a.html,a.root,a.out,mode=a.mode,site_report=a.site_report,browser=a.browser,channel=a.channel,headed=a.headed,gpu_mode=a.gpu_mode)
    print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r.get('ok') else 2
if __name__=='__main__':raise SystemExit(main())
