#!/usr/bin/env python3
"""Synthetic renderer capacity tests, not a method for inventing real user themes."""
import copy,json,tempfile,argparse,os
from pathlib import Path
from playwright.sync_api import sync_playwright
from twinlight_core.common import ROOT,load,save
from twinlight_core.site import build
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'verification/capacity.json');a=p.parse_args()
h=load(ROOT/'examples/demo/history.json');base=load(ROOT/'examples/demo/analysis.json');checks=[]
with tempfile.TemporaryDirectory() as td, sync_playwright() as pw:
 binary=os.environ.get('TWINLIGHT_BROWSER') or ('/usr/lib/chromium/chromium' if Path('/usr/lib/chromium/chromium').exists() else None)
 b=pw.chromium.launch(executable_path=binary,headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for count,per in [(1,0),(8,8)]:
  data=copy.deepcopy(base);data['themes']=[]
  for i in range(count):
   t=copy.deepcopy(base['themes'][0]);t['id']=f'theme-{i}';t['label']='测试'+str(i+1);sample=copy.deepcopy(t['topics'][0]);t['topics']=[{**copy.deepcopy(sample),'id':f'planet-{j}'} for j in range(per)];data['themes'].append(t)
  out=Path(td)/str(count);build(h,data,out)
  errors=[];q=b.new_page(viewport={'width':390,'height':844});q.on('pageerror',lambda e:errors.append(str(e)))
  q.set_content((out/'index.html').read_text(),wait_until='load');q.wait_for_function('()=>state.ready&&window.twinlightSkill')
  q.evaluate('()=>{galaxyDebug.freeze();navigate(nodes.length-1);galaxyDebug.finish()}')
  st=q.evaluate('()=>({stars:nodes.length,planets:personalSatellites.length,active:state.active,caption:document.getElementById("chapterTitle").textContent,overflow:document.documentElement.scrollWidth>innerWidth})')
  ok=st['stars']==count and st['planets']==count*per and st['active']==count-1 and not st['overflow'] and not errors
  checks.append({'stars':count,'planets_per_star':per,'passed':ok,'state':st,'errors':errors});q.close()
 b.close()
save(a.out,{'environment':'Chromium 390px layout and JS state, no claim of GPU rendering','ok':all(c['passed'] for c in checks),'checks':checks})
print(json.dumps(checks,ensure_ascii=False,indent=2));raise SystemExit(0 if all(c['passed'] for c in checks) else 1)
