#!/usr/bin/env python3
"""Check actual browser state/frames. Explicitly separates WebGL and CSS fallback."""
import argparse
import base64
import io
import json
import os
import platform
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
from playwright.sync_api import sync_playwright

p=argparse.ArgumentParser();p.add_argument('--html',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
p.add_argument('--require-webgl',action='store_true');p.add_argument('--browser');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];warnings=[];network=[]
report={'environment':f'{platform.system()} {platform.machine()} · headless Chromium desktop + emulated touch. No Safari/real-device performance claim.','checks':checks,'errors':errors,'warnings':warnings,'external_requests':network,'webgl':None}
SETTLE='()=>document.fonts.ready.then(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))'
def record(name,ok,detail=None):
 checks.append({'name':name,'passed':bool(ok),'detail':detail});print(('PASS ' if ok else 'FAIL ')+name,flush=True)
 if not ok:raise AssertionError(name)
def shot(page,name):page.screenshot(path=str(a.out/(name+'.png')))
def load_page(page):
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('console',lambda m:warnings.append(m.text) if m.type in ['warning','error'] else None)
 page.on('request',lambda r:network.append(r.url) if r.url.startswith(('http:','https:')) else None)
 page.set_content(a.html.read_text(encoding='utf-8'),wait_until='load');page.wait_for_function('()=>state.ready&&window.twinlightSkill')
 # The loading veil fades for 1.1 s after ready; screenshots before that show the veil, not the page.
 page.wait_for_function('()=>document.getElementById("loading").hidden===true',timeout=15000);page.evaluate(SETTLE)
 page.evaluate('()=>galaxyDebug.freeze()')
def image(page):
 s=page.evaluate('()=>holoCanvas.toDataURL("image/png").split(",")[1]')
 return Image.open(io.BytesIO(base64.b64decode(s))).convert('RGB')
def diff(a,b):
 if a.size!=b.size:raise AssertionError(f'Card frame dimensions changed during comparison: {a.size} -> {b.size}')
 return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3
status=0
try:
 with sync_playwright() as pw:
  binary=a.browser or os.environ.get('TWINLIGHT_BROWSER')
  if not binary and Path('/usr/lib/chromium/chromium').exists():binary='/usr/lib/chromium/chromium'
  flags=['--no-sandbox','--disable-gpu-sandbox','--ignore-gpu-blocklist','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']
  try:b=pw.chromium.launch(executable_path=binary,headless=True,args=flags)
  except Exception as exc:
   # Playwright's bundled build may be missing or mismatched; an installed Chrome/Chromium is an equivalent engine.
   system=[x for x in ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Chromium.app/Contents/MacOS/Chromium',
     '/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser',r'C:\Program Files\Google\Chrome\Application\chrome.exe'] if Path(x).exists()]
   if binary or not system:raise exc
   b=pw.chromium.launch(executable_path=system[0],headless=True,args=flags);report['browser']=system[0]
  q=b.new_page(viewport={'width':1440,'height':900});load_page(q)
  st=q.evaluate('()=>twinlightSkill.getState()');report['webgl']=q.evaluate('()=>state.gl')
  static_art=st.get('artMode')=='static' or st.get('artStatus')=='static'
  report['card_art']={'mode':st.get('artMode'),'status':st.get('artStatus'),'layered_ready':st['artReady']}
  record('Data-derived star/planet count',1<=st['stars']<=8 and st['planets']<=64,st['stars'])
  record('Browser accepts compiled profile',q.evaluate('()=>validateProfile(DEFAULT_PROFILE).chapters.length===nodes.length'))
  record('Unknown author is never guessed',q.evaluate('()=>{const old=profile.summary_meta;profile.summary_meta=null;const ok=summarizerInfo().name===null;profile.summary_meta=old;return ok}'))
  record('Overview uses point LOD',q.evaluate('()=>nodes.every((_,i)=>v9BodyBlend(i)===0)'))
  shot(q,'home')
  q.evaluate('()=>{navigate(0);galaxyDebug.finish()}');record('Focus only shows selected star detail',q.evaluate('()=>v9BodyBlend(0)>0&&nodes.every((_,i)=>i===0||v9BodyBlend(i)===0)'));shot(q,'detail')
  q.evaluate('()=>twinlightV10.seek(2)');record('AI galaxy has an introduction',q.locator('.v10-born-caption').is_visible());shot(q,'ai-birth')
  q.evaluate('()=>twinlightV10.seek(12)');name=q.evaluate('()=>summarizerInfo().name');record('Question names actual summary author',name in q.locator('#v10Question').inner_text() if name else '这个 AI' not in q.locator('#v10Question').inner_text());shot(q,'question')
  record('Question precedes card',not q.evaluate('()=>v8.cardOpen'))
  q.evaluate('()=>twinlightV10.showCard()');q.wait_for_function('()=>holo.ready||holo.failed');q.wait_for_timeout(300);q.evaluate(SETTLE)
  record('Unapproved exports disabled',q.locator('#cardSave').is_disabled() if not st['shareAllowed'] else not q.locator('#cardSave').is_disabled())
  if static_art:
   record('Static prototype is labelled as unfinished layers',not st['artReady'] and '分层尚未完成' in q.locator('#skillArtNotice').inner_text())
   record('Static depth and foil controls are disabled',q.locator('#holoDepth').is_disabled() and q.locator('#holoFoil').is_disabled())
   q.evaluate('()=>{holo.depth=1;holo.foil=.5;holo.finish=3;__holo.setView(0,-.45)}')
   appearance=q.evaluate('()=>__holo.getState()')
   record('Static prototype cannot enable depth or rainbow foil',appearance['depth']==0 and appearance['foil']==0 and appearance['finish']==2 and appearance['layers']==1,appearance)
  if q.evaluate('()=>holo.ready'):
   record('Card WebGL compiles',q.evaluate('()=>holo.gl.getError()===0'))
   if static_art:
    im1=image(q);q.evaluate('()=>__holo.setView(0,.45)');im2=image(q)
    record('Static prototype pixels stay fixed across view angles',diff(im1,im2)<.15,round(diff(im1,im2),3))
   else:
    q.evaluate('()=>{holo.foil=0;holo.depth=1;__holo.setView(0,-.45)}');im1=image(q)
    q.evaluate('()=>__holo.setView(0,.45)');im2=image(q);record('Internal layer pixels move with foil OFF',diff(im1,im2)>.5,round(diff(im1,im2),3))
    q.evaluate('()=>{holo.depth=0;__holo.setView(0,-.45)}');im1=image(q);q.evaluate('()=>__holo.setView(0,.45)');im2=image(q)
    record('Depth zero eliminates parallax',diff(im1,im2)<.15,round(diff(im1,im2),3))
    q.evaluate('()=>{holo.depth=1;holo.foil=.5}')
  else:
   report['webgl_unverified']='Both shader compilation and GPU particle rendering unverified in this environment.'
   record('CSS fallback shows registered card images' if static_art else 'CSS fallback has independent real layers',q.locator('.holo-fallback img').count()==5 and q.locator('.holo-fallback').is_visible())
   q.evaluate('()=>__holo.setView(0,-.45)')
   l=q.locator('.holo-fallback img').evaluate_all('(images)=>images.map(e=>e.style.transform)')
   q.evaluate('()=>__holo.setView(0,.45)')
   r=q.locator('.holo-fallback img').evaluate_all('(images)=>images.map(e=>e.style.transform)')
   record('Fallback static image positions stay fixed' if static_art else 'Fallback layer transform responds',l==r if static_art else l!=r)
  q.evaluate('()=>__holo.setView(-.05,-.15)');shot(q,'card')
  box=q.locator('#identityCard').bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
  q.mouse.move(x,y);q.mouse.down();q.mouse.move(x+40,y-8,steps=4);q.mouse.up()
  record('Drag changes angle without accidental flip',q.evaluate('()=>holo.ty>0&&!v8.flipped'))
  q.locator('#cardFlip').click();q.wait_for_timeout(350);record('Flip works',q.evaluate('()=>v8.flipped'))
  record('No horizontal overflow desktop',q.evaluate('()=>document.documentElement.scrollWidth<=innerWidth'))
  q.close()
  ctx=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);m=ctx.new_page();load_page(m)
  record('No horizontal overflow mobile',m.evaluate('()=>document.documentElement.scrollWidth<=innerWidth'));shot(m,'mobile-home')
  m.evaluate('()=>twinlightV10.showCard()');m.wait_for_function('()=>holo.ready||holo.failed');m.wait_for_timeout(300);m.evaluate(SETTLE);shot(m,'mobile-card')
  bb=m.locator('#identityCard').bounding_box();record('Mobile card remains within viewport',bb['y']>=0 and bb['y']+bb['height']<=844)
  m.locator('#cardFlip').tap();record('Touch flip works',m.evaluate('()=>v8.flipped'));ctx.close()
  ctx=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce');r=ctx.new_page();load_page(r)
  r.evaluate('()=>quietFinale()');r.wait_for_timeout(100);record('Reduced-motion manual reveal',r.locator('#v10RevealNow').is_visible());r.locator('#v10RevealNow').click();record('Reduced motion stops card sway',r.evaluate('()=>!holo.auto'));ctx.close();b.close()
  record('No page exceptions',not errors,errors);record('No external requests',not network,network)
  if a.require_webgl:record('WebGL required by invocation',report['webgl'] is True and 'webgl_unverified' not in report)
except Exception as exc:
 status=1;report['failure']=str(exc)
finally:
 report['ok']=status==0;report['not_tested']=['Safari','physical phone','real-history semantic accuracy','sustained device performance'];(a.out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
raise SystemExit(status)
