#!/usr/bin/env python3
"""Check actual browser state/frames. Explicitly separates WebGL and CSS fallback."""
import argparse
import base64
import hashlib
import io
import json
import os
import platform
import signal
import subprocess
import sys
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
from playwright.sync_api import sync_playwright
from twinlight_core.browser_runtime import launch_flags, finale_route, runtime_snapshot

p=argparse.ArgumentParser();p.add_argument('--html',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
p.add_argument('--require-webgl',action='store_true');p.add_argument('--browser')
p.add_argument('--gpu-mode',choices=('auto','swiftshader'),default='auto',help='Use the normal browser backend by default; explicitly select swiftshader for a separate software-rendering probe.')
p.add_argument('--headed',action='store_true',help='Use an available desktop display. Never inferred from an absent WebGL context.')
p.add_argument('--channel',help='Installed Playwright browser channel, e.g. chrome; cannot be combined with --browser.')
p.add_argument('--skip-continuous',action='store_true',help='Skip the real-time finale when checking additional layout variants. The normal invocation plays it once.')
p.add_argument('--timeout',type=int,default=120,help='Maximum seconds for the browser worker, including cleanup. Timeout keeps partial checks and reports failure.')
p.add_argument('--browser-worker',action='store_true',help=argparse.SUPPRESS)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
if a.timeout<=0:p.error('--timeout must be positive')
if a.channel and a.browser:p.error('--channel and --browser are mutually exclusive')
html_bytes=a.html.read_bytes();html_text=html_bytes.decode('utf-8')
checks=[];errors=[];warnings=[];network=[];unverified=[]
report={'environment':f'{platform.system()} {platform.machine()} · headless Chromium desktop + emulated touch. No Safari/real-device performance claim.',
 'html':str(a.html.resolve()),'html_sha256':hashlib.sha256(html_bytes).hexdigest(),
 'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'checks':checks,'errors':errors,'warnings':warnings,'external_requests':network,'webgl':None,'ok':False,'status':'unverified','stage':'browser_launch',
 'release_authorized':False,'checks_ok':False,'continuous_verified':False,'full_effects_verified':False,
 'requested_runtime':{'gpu_mode':a.gpu_mode,'headed':a.headed,'channel':a.channel},
 'not_tested':['Safari','physical phone','real-history semantic accuracy','sustained device performance']}
def save_report():
 pending=a.out/'report.pending.json';pending.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');pending.replace(a.out/'report.json')
save_report()
if not a.browser_worker:
 # A library cleanup call can stall after the last check. Isolate its process
 # group so a bounded failure cannot interrupt a user's existing browser.
 worker=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:],'--browser-worker'],start_new_session=os.name!='nt')
 try:
  exit_code=worker.wait(timeout=a.timeout)
  if exit_code:
   try:report=json.loads((a.out/'report.json').read_text(encoding='utf-8'))
   except (OSError,ValueError):pass
   report['ok']=False
   if 'failure' not in report:report.update(status='unverified',failure=f'Browser worker exited with code {exit_code} before completing verification')
   save_report()
  raise SystemExit(exit_code if exit_code>=0 else 1)
 except subprocess.TimeoutExpired:
  cleanup_error=None
  try:
   if os.name=='nt':
    subprocess.run(['taskkill','/PID',str(worker.pid),'/T','/F'],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
   else:
    try:os.killpg(worker.pid,signal.SIGTERM)
    except ProcessLookupError:pass
   try:worker.wait(timeout=3)
   except subprocess.TimeoutExpired:
    if os.name=='nt':worker.kill()
    else:
     try:os.killpg(worker.pid,signal.SIGKILL)
     except ProcessLookupError:pass
    worker.wait(timeout=5)
  except (OSError,subprocess.TimeoutExpired) as exc:cleanup_error=str(exc)
  try:report=json.loads((a.out/'report.json').read_text(encoding='utf-8'))
  except (OSError,ValueError):pass
  report.update(ok=False,status='unverified',timed_out=True,failure=f'Browser verification timed out after {a.timeout}s during '+report.get('stage','unknown'))
  if cleanup_error:report['cleanup_error']=cleanup_error
  save_report();print('FAIL '+report['failure'],flush=True);raise SystemExit(1)
SETTLE='()=>document.fonts.ready.then(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))'
def record(name,ok,detail=None):
 checks.append({'name':name,'passed':bool(ok),'detail':detail});print(('PASS ' if ok else 'FAIL ')+name,flush=True)
 save_report()
 if not ok:raise AssertionError(name)
def shot(page,name):page.screenshot(path=str(a.out/(name+'.png')))
def load_page(page):
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('console',lambda m:warnings.append(m.text) if m.type in ['warning','error'] else None)
 page.on('request',lambda r:network.append(r.url) if r.url.startswith(('http:','https:')) else None)
 page.set_content(html_text,wait_until='load');page.wait_for_function('()=>state.ready&&window.twinlightSkill')
 # The loading veil fades for 1.1 s after ready; screenshots before that show the veil, not the page.
 page.wait_for_function('()=>document.getElementById("loading").hidden===true',timeout=15000);page.evaluate(SETTLE)
 page.evaluate('()=>galaxyDebug.freeze()')
def image(page):
 s=page.evaluate('()=>holoCanvas.toDataURL("image/png").split(",")[1]')
 return Image.open(io.BytesIO(base64.b64decode(s))).convert('RGB')
def diff(a,b):
 if a.size!=b.size:raise AssertionError(f'Card frame dimensions changed during comparison: {a.size} -> {b.size}')
 return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3
def text_layout(page,selector,blockers=()):
 """Inspect painted text lines, not only an overflow-hidden document's width."""
 return page.evaluate('''({selector,blockers})=>{
  const e=document.querySelector(selector),box=e.getBoundingClientRect(),rects=[];
  const walker=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);let node;
  while(node=walker.nextNode()){
   if(!node.textContent.trim())continue;
   const s=getComputedStyle(node.parentElement);if(s.visibility==='hidden'||s.display==='none')continue;
   const range=document.createRange();range.selectNodeContents(node);
   for(const r of range.getClientRects())if(r.width&&r.height)rects.push({x:r.x,y:r.y,right:r.right,bottom:r.bottom});
  }
  const obstacles=blockers.map(s=>document.querySelector(s)).filter(e=>e&&e.getClientRects().length)
   .map(e=>({selector:e.id||e.className,box:e.getBoundingClientRect()}));
  const failures=[];
  for(const r of rects){
   if(r.x<-2||r.right>innerWidth+2||r.y<-2||r.bottom>innerHeight+2)failures.push('viewport');
   if(r.x<box.left-2||r.right>box.right+2||r.y<box.top-2||r.bottom>box.bottom+2)failures.push('text-container');
   for(const o of obstacles)if(r.right>o.box.left+2&&r.x<o.box.right-2&&r.bottom>o.box.top+2&&r.y<o.box.bottom-2)failures.push('obscured-by:'+o.selector);
  }
  return {ok:rects.length>0&&!failures.length,text:e.textContent,rects,failures};
 }''',{'selector':selector,'blockers':list(blockers)})
def check_text(page,name,selector,blockers=()):
 layout=text_layout(page,selector,blockers);record(name,layout['ok'],layout)
def check_mobile_navigation(page):
 selectors=['#navMap','#v7Journey','#v10HomeFinale'];lines=[text_layout(page,s) for s in selectors]
 single_line=all(x['ok'] and max(r['y'] for r in x['rects'])-min(r['y'] for r in x['rects'])<2 for x in lines)
 boxes=page.locator('.header .brand,.header nav,.header-right').evaluate_all('(es)=>es.map(e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right}})')
 nonoverlap=all(x['right']<=y['left']+2 for x,y in zip(boxes,boxes[1:]))
 record('Mobile navigation keeps readable single-line labels',single_line and nonoverlap,{'lines':lines,'boxes':boxes})
status=0
try:
 with sync_playwright() as pw:
  binary=a.browser or os.environ.get('TWINLIGHT_BROWSER')
  if not binary and Path('/usr/lib/chromium/chromium').exists():binary='/usr/lib/chromium/chromium'
  if a.channel:binary=None
  flags=launch_flags(a.gpu_mode)
  try:b=pw.chromium.launch(executable_path=binary,channel=a.channel,headless=not a.headed,args=flags)
  except Exception as exc:
   # Playwright's bundled build may be missing or mismatched; an installed Chrome/Chromium is an equivalent engine.
   system=[x for x in ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Chromium.app/Contents/MacOS/Chromium',
     '/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser',r'C:\Program Files\Google\Chrome\Application\chrome.exe'] if Path(x).exists()]
   if binary or a.channel or not system:raise exc
   b=pw.chromium.launch(executable_path=system[0],headless=not a.headed,args=flags);report['browser']=system[0]
  report['browser_version']=b.version
  report['stage']='desktop_checks';q=b.new_page(viewport={'width':1440,'height':900},reduced_motion='no-preference');load_page(q)
  report['initial_runtime']=runtime_snapshot(q);save_report()
  st=q.evaluate('()=>twinlightSkill.getState()');report['webgl']=q.evaluate('()=>state.gl')
  static_art=st.get('artMode')=='static' or st.get('artStatus')=='static'
  report['card_art']={'mode':st.get('artMode'),'status':st.get('artStatus'),'layered_ready':st['artReady']}
  record('Data-derived star/planet count',1<=st['stars']<=8 and st['planets']<=64,st['stars'])
  record('Browser accepts compiled profile',q.evaluate('()=>validateProfile(DEFAULT_PROFILE).chapters.length===nodes.length'))
  record('Unknown author is never guessed',q.evaluate('()=>{const old=profile.summary_meta;profile.summary_meta=null;const ok=summarizerInfo().name===null;profile.summary_meta=old;return ok}'))
  record('Overview uses point LOD',q.evaluate('()=>nodes.every((_,i)=>v9BodyBlend(i)===0)'))
  shot(q,'home')
  q.evaluate('()=>{navigate(0);galaxyDebug.finish()}');record('Focus only shows selected star detail',q.evaluate('()=>v9BodyBlend(0)>0&&nodes.every((_,i)=>i===0||v9BodyBlend(i)===0)'));shot(q,'detail')
  check_text(q,'Desktop theme headline fits its preview','#v7PeekText',['.header','#v7Route'])
  q.evaluate('()=>twinlightV10.seek(.7)');record('Tidal approach begins during AI introduction',q.evaluate('()=>v10.phase==="ai-birth"&&v10MergeProgress()>.01&&fx.ready') if report['webgl'] else q.evaluate('()=>v10.phase==="ai-birth"&&v10MergeProgress()>.01'));shot(q,'early-tide')
  motion=q.evaluate('()=>{const saved=v10.time,values=[];for(let i=0;i<=1060;i++){v10.time=i/100;values.push(v10MergeProgress())}const at=t=>{v10.time=t;return v10MergeProgress()},left=(at(3.2)-at(3.199))/.001,right=(at(3.201)-at(3.2))/.001;v10.time=saved;return {monotonic:values.every((p,i)=>p>=0&&p<=1&&(!i||p>=values[i-1])),left,right,settled:values[values.length-1]}}')
  record('Introduction joins merging with continuous speed',motion['monotonic'] and abs(motion['left']-motion['right'])<.001 and abs(motion['settled']-.995)<.00001,motion)
  q.evaluate('()=>twinlightV10.seek(2)');record('AI galaxy is introduced before first crossing',q.locator('.v10-born-caption').is_visible() and q.evaluate('()=>v10MergeProgress()<.26&&v10Birth()>.5'));shot(q,'ai-birth')
  q.evaluate('()=>twinlightV10.seek(4.5)');record('Full merger follows AI introduction',not q.locator('.v10-born-caption').is_visible() and q.evaluate('()=>v10.phase==="merge"'));shot(q,'first-passage')
  q.evaluate('()=>twinlightV10.seek(12)');name=q.evaluate('()=>summarizerInfo().name');record('Question names actual summary author',name in q.locator('#v10Question').inner_text() if name else '这个 AI' not in q.locator('#v10Question').inner_text());shot(q,'question')
  check_text(q,'Desktop question text fits without control overlap','#v10Question',['.cinema-heading','.cinema-player','#encounterCinema>.v10-audio'])
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
   report['card_webgl']=True
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
   report['card_webgl']=False
   report['webgl_unverified']='The card WebGL renderer is unavailable in this tested configuration; this is not a statement about other browser configurations.'
   report['capability_unavailable']=True
   unverified.append('card WebGL parallax and view-dependent foil')
   record('CSS fallback shows registered card images' if static_art else 'CSS fallback has independent real layers',q.locator('.holo-fallback img').count()==5 and q.locator('.holo-fallback').is_visible())
   q.evaluate('()=>__holo.setView(0,-.45)')
   l=q.locator('.holo-fallback img').evaluate_all('(images)=>images.map(e=>e.style.transform)')
   q.evaluate('()=>__holo.setView(0,.45)')
   r=q.locator('.holo-fallback img').evaluate_all('(images)=>images.map(e=>e.style.transform)')
   record('Fallback static image positions stay fixed' if static_art else 'Fallback layer transform responds',l==r if static_art else l!=r)
  q.evaluate('()=>__holo.setView(-.05,-.15)');shot(q,'card')
  check_text(q,'Desktop reveal title is fully readable','#identityHeading',['.identity-top','.identity-actions'])
  box=q.locator('#identityCard').bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
  q.mouse.move(x,y);q.mouse.down();q.mouse.move(x+40,y-8,steps=4);q.mouse.up()
  record('Drag changes angle without accidental flip',q.evaluate('()=>holo.ty>0&&!v8.flipped'))
  q.locator('#cardFlip').click();q.wait_for_timeout(350);record('Flip works',q.evaluate('()=>v8.flipped'))
  record('No horizontal overflow desktop',q.evaluate('()=>document.documentElement.scrollWidth<=innerWidth'))
  if not a.skip_continuous:
   report['stage']='finale_runtime_route';save_report()
   q.locator('#identityClose').click();q.bring_to_front()
   return_view=q.evaluate('()=>window.twinlightNavigation?{mode:state.mode,active:state.active,topic:state.topic}:null')
   q.evaluate('()=>{v10.musicChosen=true;galaxyDebug.resume()}')
   before=runtime_snapshot(q);report['finale']={'before':before,**finale_route(before)};save_report()
   if report['finale']['route']=='autoplay':
    report['stage']='real_time_finale';save_report()
    # A passive click/rAF observer measures the existing animation. It never seeks,
    # edits the timeline or changes reduced motion/WebGL state to obtain a pass.
    q.evaluate('''()=>{window.__twFinaleProbe={start:null,end:null,frames:0};
     document.getElementById('v10HomeFinale').addEventListener('click',()=>{
      const p=window.__twFinaleProbe;p.start=performance.now();
      const observe=()=>{p.frames++;if(v8.cardOpen){p.end=performance.now();return;}
       if(performance.now()-p.start<25000)requestAnimationFrame(observe);};requestAnimationFrame(observe);
     },{capture:true,once:true});}''')
    q.locator('#v10HomeFinale').click()
    q.wait_for_function('()=>v10.time>3.3&&v10.phase==="merge"&&!testing',timeout=10000,polling=100)
    record('Real-time finale advances beyond AI introduction',q.evaluate('()=>v10.playing&&state.mergePlaying&&!v8.cardOpen'))
    q.wait_for_function('()=>v8.cardOpen&&v10.time===14&&window.__twFinaleProbe.end!==null',timeout=20000,polling=100)
    measured=q.evaluate('()=>window.__twFinaleProbe');report['finale']['measurement']=measured
    elapsed=(measured['end']-measured['start'])/1000;report['finale']['wall_seconds']=elapsed
    record('Real-time finale automatically reveals the card',q.locator('#identityScene').is_visible())
    record('Real-time finale finishes within the 15 second limit',0<elapsed<=15,elapsed)
    report['continuous_verified']=True;report['finale'].update(status='verified',autoplay_verified=True)
   elif report['finale']['route']=='manual_reduced_motion':
    # WebGL failure intentionally sets state.reduced in the locked V10 renderer.
    # That mode waits for a manual reveal, so an autoplay wait is invalid.
    report['stage']='fallback_manual_reveal';report['capability_unavailable']=True
    unverified.append('real-time full galaxy merger: '+report['finale']['reason']);save_report()
    q.locator('#v10HomeFinale').click()
    q.wait_for_function('()=>document.getElementById("v10RevealNow")&&!document.getElementById("v10RevealNow").hidden',timeout=5000,polling=100)
    report['finale']['after_start']=runtime_snapshot(q);save_report()
    record('Fallback explicitly waits for manual reveal, not automatic playback',q.evaluate('()=>state.reduced&&!state.mergePlaying&&!v8.cardOpen'))
    q.locator('#v10RevealNow').click()
    record('Fallback manual reveal remains usable',q.locator('#identityScene').is_visible())
   else:
    report['capability_unavailable']=True
    unverified.append('real-time full galaxy merger: '+report['finale']['reason']);save_report()
   if q.evaluate('()=>v8.cardOpen'):
    q.locator('#identityClose').click();q.evaluate(SETTLE)
    if return_view is not None:
     # Split-task navigation restores the saved view, not an unrelated overview.
     # The dedicated navigation verifier separately compares exact camera/reader state.
     restored=q.evaluate('()=>({mode:state.mode,active:state.active,topic:state.topic})')
     record('Return button restores the previously selected interactive galaxy',
       restored==return_view and q.evaluate('()=>!v8.cardOpen&&!state.encounterCinematic&&!document.querySelector("[inert]")&&twinlightNavigation.getState().view==="galaxy"')
       and q.locator('#v10HomeFinale').is_visible(),{'before':return_view,'after':restored})
    else:
     record('Return button restores interactive personal galaxy',q.evaluate('()=>!v8.cardOpen&&!state.encounterCinematic&&state.mode==="personal"&&!document.querySelector("[inert]")') and q.locator('#v10HomeFinale').is_visible())
   report['finale']['after']=runtime_snapshot(q);save_report()
   q.evaluate('()=>galaxyDebug.freeze()')
  else:
   report['finale']={'route':'explicit_skip','status':'not_tested','reason':'Caller requested a layout-only variant. Not evidence of real-time playback.'}
  q.close()
  report['stage']='mobile_checks'
  ctx=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);m=ctx.new_page();load_page(m)
  record('No horizontal overflow mobile',m.evaluate('()=>document.documentElement.scrollWidth<=innerWidth'));shot(m,'mobile-home')
  check_mobile_navigation(m)
  m.evaluate('()=>{navigate(0);galaxyDebug.finish()}');m.evaluate(SETTLE)
  check_text(m,'Mobile theme headline fits its preview','#v7PeekText',['.header','#v7Route','#exploreToolbar'])
  if m.evaluate('()=>profile.chapters[0].topics.length>0'):
   m.evaluate('()=>quietPick(0,0)');m.evaluate(SETTLE)
   check_text(m,'Mobile topic summary fits its preview','#v7PeekText',['.header','#v7Route','#exploreToolbar'])
  m.evaluate('()=>{quietPick(0);quietRead()}');m.evaluate(SETTLE)
  check_text(m,'Mobile theme title stays inside the reader','#chapterTitle',['.header','#v7ReaderClose'])
  reader=m.evaluate('()=>{const e=$("readerScroll"),r=e.getBoundingClientRect(),text=$("chapterLetter").textContent;let cursor=0;const preserved=profile.chapters[0].story.every(s=>{const at=text.indexOf(s,cursor);if(at<0)return false;cursor=at+s.length;return true});return {width:e.clientWidth,scrollWidth:e.scrollWidth,preserved,paragraphs:profile.chapters[0].story.length,box:{x:r.x,right:r.right,y:r.y,bottom:r.bottom}}}')
  record('Mobile story preserves paragraphs and has no horizontal clipping',reader['preserved'] and reader['scrollWidth']<=reader['width']+1,reader);shot(m,'mobile-theme')
  check_text(m,'Mobile journey controls remain inside the viewport','#v7Route',['#exploreToolbar'])
  m.locator('#readerScroll').evaluate('e=>e.scrollTo({top:e.scrollHeight,behavior:"instant"})')
  m.wait_for_function('()=>{const e=$("readerScroll");return e.scrollHeight-e.clientHeight-e.scrollTop<=2}',timeout=3000)
  record('Mobile long story can scroll to its end',m.locator('#readerScroll').evaluate('e=>e.scrollHeight-e.clientHeight-e.scrollTop<=2'));shot(m,'mobile-theme-bottom')
  m.evaluate('()=>twinlightV10.seek(12)');m.evaluate(SETTLE)
  check_text(m,'Mobile question text fits without control overlap','#v10Question',['.cinema-heading','.cinema-player','#encounterCinema>.v10-audio']);shot(m,'mobile-question')
  m.evaluate('()=>twinlightV10.showCard()');m.wait_for_function('()=>holo.ready||holo.failed');m.wait_for_timeout(300);m.evaluate(SETTLE);shot(m,'mobile-card')
  check_text(m,'Mobile reveal title is fully readable','#identityHeading',['.identity-top','.identity-actions'])
  bb=m.locator('#identityCard').bounding_box();record('Mobile card remains within viewport',bb['y']>=0 and bb['y']+bb['height']<=844)
  m.locator('#cardFlip').tap();record('Touch flip works',m.evaluate('()=>v8.flipped'));ctx.close()
  report['stage']='reduced_motion_checks';ctx=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce');r=ctx.new_page();load_page(r)
  r.evaluate('()=>quietFinale()');r.wait_for_timeout(100);record('Reduced-motion manual reveal',r.locator('#v10RevealNow').is_visible());r.locator('#v10RevealNow').click();record('Reduced motion stops card sway',r.evaluate('()=>!holo.auto'))
  report['stage']='browser_cleanup';save_report();ctx.close();b.close()
  record('No page exceptions',not errors,errors);record('No external requests',not network,network)
  if a.require_webgl:record('WebGL required by invocation',report['webgl'] is True and 'webgl_unverified' not in report)
except Exception as exc:
 status=1;report['failure']=str(exc);report['failed_stage']=report.get('stage')
 try:
  if 'q' in locals() and not q.is_closed():report['failure_runtime']=runtime_snapshot(q)
 except Exception:pass
finally:
 report['checks_ok']=status==0
 report['not_tested']=['Safari','physical phone','real-history semantic accuracy','sustained device performance']+unverified
 if a.skip_continuous:report['not_tested'].append('real-time finale playback (skipped for this additional variant)')
 # This verifier does not perform the standalone card's complete foil comparison.
 report['full_effects_verified']=False
 report['effects_scope']='Timeline and UI diagnostics only; full card foil validation and independent release review are separate.'
 if status==0 and unverified:
  status=2;report['status']='capability_unavailable';report['stage']='completed_partial_checks'
  report['failure']='Partial interaction checks completed; requested effects remain unverified: '+'; '.join(unverified)
 else:
  report['status']='passed' if status==0 else 'failed';report['stage']='complete' if status==0 else 'failed'
 report['ok']=status==0;save_report()
raise SystemExit(status)
