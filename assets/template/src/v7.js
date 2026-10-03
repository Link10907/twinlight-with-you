/* v7 is a presentation layer over v6's data, GPU renderer and camera.
 * Selection is separate from navigation and reading. No new external data.
 */
const quiet={selection:-1,topic:-1,wantRead:false,reading:false,playing:false,elapsed:0,launchFinale:false,menu:false,visited:new Set(),labels:[0,1,3]};
const quietAIVisible=()=>state.encounterCinematic||['ai','event'].includes(state.mode);
const quietPersonVisible=()=>state.encounterCinematic||!['ai','event'].includes(state.mode);
const quietModeView=modeView;
modeView=function(mode){
 if(mode==='personal')return state.w<=700?{cam:[-2,298,284],target:[-4,18,2],fov:63}:{cam:[12,205,268],target:[-45,0,0],fov:47};
 return quietModeView(mode);
};
const quietTargetView=targetView;
targetView=function(i){if(i<0)return modeView('personal');const p=nodes[i];return state.w<=700?{cam:add(p,[0,37,71]),target:add(p,[0,-42,0]),fov:59}:{cam:add(p,[3,27,61]),target:add(p,[-19,-3,0]),fov:47};};
// Simplify the chrome; keep original settings and data handlers in the menu.
$('navMap').textContent='星图';
const qj=el('button','','旅程');qj.id='v7Journey';qj.innerHTML='<svg viewBox="0 0 12 14" aria-hidden="true"><path d="M2 2l8 5-8 5z"/></svg><span>旅程</span>';
$('navMap').after(qj);
const qm=el('button','','⋯');qm.id='v7MenuButton';qm.setAttribute('aria-label','打开星图设置');qm.setAttribute('aria-expanded','false');qm.setAttribute('aria-controls','v7Menu');document.querySelector('.header-right').append(qm);
['soundBtn','motionBtn','qualityBtn','orbitToggle'].forEach(id=>{if(id!=='orbitToggle')$('v7Tools').append($(id));});
const fullProxy=el('button','','全屏浏览');fullProxy.onclick=()=>$('fullBtn').click();$('v7Tools').append(fullProxy);
const readingClose=el('button','','×');readingClose.id='v7ReaderClose';readingClose.setAttribute('aria-label','收起故事，返回星图');document.querySelector('.reader-top').append(readingClose);
const extra=el('details','v7-details');extra.append(el('summary','','AI 同行与相关主题'));extra.append(document.querySelector('.ai-echo'),document.querySelector('.topic-shelf'));document.querySelector('.letter-sources').before(extra);
$('helpDialog').querySelector('.dialog-body').innerHTML='<h3>自由探索</h3><p>拖动旋转；右键或 Shift + 拖动平移；滚轮、+ / − 缩放。对准星体持续放大或双击，可以飞近。单击星体先看摘要，选择“阅读故事”才展开全文。</p><h3>手机与键盘</h3><p>单指拖动，双指捏合缩放、双指移动平移。← → 切换旅程，R 重置，H 隐藏界面，Esc 收起详情或返回星图。星点可用 Tab 聚焦、Enter 点选。名称只在需要时展开。</p><h3>旅程与结尾</h3><p>“旅程”会依次经过已有的主星，再进入相遇动画。可以暂停，或用底部进度跳到任意一站。动画是艺术表达，不是天体物理模拟；AI 年表不代表个人使用记录。</p>';
function quietMenu(open){quiet.menu=open;$('v7Menu').hidden=!open;qm.setAttribute('aria-expanded',String(open));}
qm.onclick=()=>quietMenu(!quiet.menu);
$('v7Catalog').onclick=()=>{quietMenu(false);$('indexDialog').showModal();};
$('v7AIMenu').onclick=()=>{quietMenu(false);showWorld('ai');};
$('v7About').onclick=()=>{quietMenu(false);showInfo();};
$('v7Help').onclick=()=>{quietMenu(false);$('helpDialog').showModal();};
document.addEventListener('pointerdown',e=>{if(quiet.menu&&!e.target.closest('#v7Menu,#v7MenuButton'))quietMenu(false);});
function quietSync(){
 const map=state.mode==='personal'&&!state.flight&&!state.encounterCinematic;
 const chosen=quiet.selection>=0&&['personal','chapter'].includes(state.mode)&&!state.encounterCinematic;
 $('v7Intro').hidden=!map||chosen||quiet.reading;
 $('v7Peek').hidden=!chosen||quiet.reading||!!state.flight;
 $('v7Route').hidden=!chosen||!!state.encounterCinematic;
 $('v7Hint').hidden=chosen||!map;
 $('v7Status').hidden=!['personal','chapter'].includes(state.mode)||!!state.encounterCinematic;
 document.body.classList.toggle('has-selection',chosen);
 $('navMap').classList.toggle('active',state.mode==='personal');qj.classList.toggle('active',state.mode==='chapter'||quiet.playing);
 $('v7Pause').textContent=quiet.playing?'Ⅱ':'▷';$('v7Pause').setAttribute('aria-label',quiet.playing?'暂停旅程':'播放旅程');
 $('v7Position').textContent=String(Math.max(0,quiet.selection)+1).padStart(2,'0')+' / '+String(profile.chapters.length).padStart(2,'0');
 $('v7Next').firstChild.textContent=quiet.selection===profile.chapters.length-1?'相遇 ':'下一颗 ';
 $('v7Previous').disabled=quiet.selection<=0;
 $('v7Steps').querySelectorAll('button').forEach((b,i)=>{b.classList.toggle('active',quiet.selection===i);b.classList.toggle('done',quiet.visited.has(i));b.setAttribute('aria-current',quiet.selection===i?'step':'false');});
 if(state.mode==='chapter'&&!quiet.reading){$('reader').hidden=true;$('reader').classList.remove('visible');}
}
function quietFillPeek(){const i=quiet.selection;if(i<0)return;const c=profile.chapters[i],t=quiet.topic>=0?c.topics[quiet.topic]:null;
 $('v7PeekMeta').textContent=String(i+1).padStart(2,'0')+' / '+String(profile.chapters.length).padStart(2,'0')+' · '+c.period.split('·')[0].trim();
 $('v7PeekTitle').textContent=t?t.name:c.label;
 $('v7PeekText').textContent=t?t.title:c.signature;
 $('v7Approach').hidden=state.mode==='chapter'&&state.active===i;
}
function quietPick(i,j=-1){if(state.encounterCinematic||state.flight)return;quietMenu(false);quiet.playing=false;quiet.elapsed=0;quiet.selection=i;quiet.topic=j;quiet.reading=false;quiet.wantRead=false;quiet.visited.add(i);state.hoveredStar=i;state.dwell=0;
 $('reader').hidden=true;$('reader').classList.remove('visible');if(state.w<=700&&state.mode==='personal'){if(state.viewTween){state.viewTween=null;syncOrbit({cam:state.cam,target:state.target,fov:state.fov},false);}const w=j>=0?worldPoint(personalSatellites.find(s=>s.i===i&&s.j===j).p):nodes[i],p=project(w);if(p)pan(state.w*.50-p.x,state.h*.36-p.y);}quietFillPeek();quietSync();
}
function quietClear(){quiet.selection=-1;quiet.topic=-1;quiet.playing=false;quiet.reading=false;quiet.wantRead=false;quiet.elapsed=0;quietMenu(false);$('reader').hidden=true;quietSync();}
const quietWorld=showWorld;
showWorld=function(mode='personal',instant=false){quietClear();if(mode==='overview'&&!quiet.launchFinale)mode='personal';if(!quiet.launchFinale){state.merge=state.mergeGoal=0;}quietWorld(mode,instant);quietSync();};
const quietEnd=endEncounter;
endEncounter=function(returnView=false){quietEnd(false);if(returnView){quietClear();state.merge=state.mergeGoal=0;showWorld('personal');}quietSync();};
const quietNavigate=navigate;
navigate=function(i,opts={}){if(i<0){showWorld('personal');return;}const play=quiet.playing;quiet.selection=i;quiet.topic=Number.isInteger(opts.topic)?opts.topic:-1;quiet.visited.add(i);quiet.elapsed=0;quietNavigate(i,opts);quiet.playing=play;quietSync();};
const quietFinish=finishFlight;
finishFlight=function(){if(!state.flight)return;const to=state.flight.index,event=state.flight.event,topic=state.flight.topic;quietFinish();if(event>=0){quietSync();return;}quiet.selection=to;quiet.visited.add(to);quiet.topic=Number.isInteger(topic)?topic:-1;quiet.reading=quiet.wantRead;quiet.wantRead=false;
 $('reader').hidden=!quiet.reading;if(!quiet.reading)$('reader').classList.remove('visible');if(quiet.reading&&quiet.topic>=0)selectTopic(quiet.topic);quietFillPeek();quietSync();};
function quietRead(){if(quiet.selection<0)return;quiet.playing=false;quiet.wantRead=true;if(state.mode==='chapter'&&state.active===quiet.selection){quiet.reading=true;quiet.wantRead=false;fillLetter(state.active,quiet.topic);$('reader').hidden=false;$('reader').classList.add('visible');quietSync();}
 else{const j=quiet.topic;navigate(quiet.selection,{topic:j});if(state.flight)state.flight.topic=j;}}
function quietApproach(){if(quiet.selection<0)return;quiet.wantRead=false;quiet.reading=false;const j=quiet.topic;navigate(quiet.selection,{topic:j});if(state.flight)state.flight.topic=j;}
function quietStart(){quietMenu(false);quiet.playing=true;quiet.reading=false;quiet.wantRead=false;navigate(0,{replay:true});quietSync();}
function quietFinale(){quietMenu(false);quiet.playing=false;quiet.reading=false;quiet.wantRead=false;if(state.flight)finishFlight();state.merge=state.mergeGoal=0;quiet.launchFinale=true;encounter();quiet.launchFinale=false;quietSync();}
function quietAdvance(dir){quiet.playing=false;quiet.reading=false;quiet.wantRead=false;const n=quiet.selection+dir;if(n>=profile.chapters.length){quietFinale();return;}if(n<0){showWorld('personal');return;}navigate(n);}
$('v7Start').onclick=qj.onclick=quietStart;$('v7Read').onclick=quietRead;$('v7Approach').onclick=quietApproach;
$('v7Dismiss').onclick=()=>{if(state.mode==='chapter')showWorld('personal');else quietClear();};
readingClose.onclick=()=>{quiet.reading=false;quiet.wantRead=false;$('reader').hidden=true;quietFillPeek();quietSync();};
$('v7Previous').onclick=()=>quietAdvance(-1);$('v7Next').onclick=()=>quietAdvance(1);$('next').onclick=()=>quietAdvance(1);$('prev').onclick=()=>quietAdvance(-1);
$('v7Pause').onclick=()=>{quiet.playing=!quiet.playing;quiet.elapsed=0;if(quiet.playing&&state.mode==='personal')quietApproach();quietSync();};
$('home').onclick=$('navMap').onclick=$('overviewBtn').onclick=()=>showWorld('personal');
$('cinemaExit').onclick=$('cinemaContinue').onclick=()=>endEncounter(true);$('cinemaContinue').textContent='回到我的星系 ↗';
const quietCreateNav=createNav;
createNav=function(){quietCreateNav();$('v7Name').textContent=profile.name.toUpperCase();$('v7Count').textContent=profile.chapters.length+' 段旅程 · '+(profile.chapters.reduce((a,c)=>a+(c.topics||[]).length,0)+profile.chapters.length)+' 颗微光';
 labels.forEach((b,i)=>b.onclick=()=>quietPick(i));
 $('v7Steps').replaceChildren();profile.chapters.forEach((c,i)=>{const b=el('button');b.title=c.label;b.setAttribute('aria-label','第'+(i+1)+'站：'+c.label);b.onclick=()=>{quiet.playing=false;quiet.wantRead=false;quiet.reading=false;navigate(i);};$('v7Steps').append(b);});
 const ending=el('button','index-link');ending.append(el('span','',String(profile.chapters.length+1).padStart(2,'0')));const text=el('div');text.append(el('strong','','相遇'),el('small','','终章 · 两片星系，新的世界'));ending.append(text);ending.onclick=()=>{$('indexDialog').close();quietFinale();};$('indexList').append(ending);
};
const quietRebuild=rebuildPersonalMap;
rebuildPersonalMap=function(){quietRebuild();personalButtons.forEach((b,k)=>{const s=personalSatellites[k];b.onclick=()=>quietPick(s.i,s.j);});};
// Only reveal labels near the pointer, a chosen star, or three editorial anchors.
const quietLabels=updateLabels;
updateLabels=function(){quietLabels();const on=state.mode==='personal'&&!state.flight&&!state.encounterCinematic&&!state.clean;const chosen=quiet.selection;
 labels.forEach((b,i)=>{if(b.hidden)return;const anchor=chosen<0&&quiet.labels.includes(i);b.classList.toggle('quiet-named',anchor||state.hoveredStar===i||chosen===i);b.classList.toggle('selected',chosen===i);});
 personalButtons.forEach((b,k)=>{if(b.hidden)return;const s=personalSatellites[k],p=project(worldPoint(s.p));if(p)b.style.transform='translate3d('+(p.x-14).toFixed(1)+'px,'+(p.y-14).toFixed(1)+'px,0)';b.classList.remove('named');b.classList.toggle('hot',state.hoverTopicIndex===k||chosen===s.i&&quiet.topic===s.j);});
 if(!quietAIVisible())aiButtons.forEach(b=>b.hidden=true);
 $('galaxyTitles').hidden=true;$('personalAtlas').hidden=true;$('focusHint').hidden=true;$('clusterTitle').hidden=true;$('companionLabel').hidden=true;
 // Geometric exclusion, not overlays that intercept gestures.
 const exclusions=[];['v7Intro','v7Peek','reader'].forEach(id=>{const e=$(id);if(!e.hidden&&getComputedStyle(e).display!=='none'){const r=e.getBoundingClientRect();exclusions.push(r);}});
 const occluded=p=>p&&exclusions.some(r=>p.x>r.left-12&&p.x<r.right+16&&p.y>r.top-15&&p.y<r.bottom+16);
 if(on){labels.forEach((b,i)=>{if(occluded(project(nodes[i])))b.hidden=true;});personalButtons.forEach((b,k)=>{if(occluded(project(worldPoint(personalSatellites[k].p))))b.hidden=true;});}
 topicButtons.forEach((b,j)=>{if(state.active>=0&&occluded(project(topicWorld(state.active,j))))b.hidden=true;});
};
// Preserve drag/orbit/pan/pinch/dolly. A tap selects; a double-click travels.
const quietFindHit=findHit;
findHit=function(x,y,limit=42){let h=quietFindHit(x,y,limit);if(h?.type==='ai'&&!quietAIVisible())h=null;if(state.mode==='chapter'&&state.active>=0&&!state.flight){for(let j=0;j<(profile.chapters[state.active].topics||[]).length;j++){const w=topicWorld(state.active,j),p=project(w);if(!p)continue;const d=Math.hypot(p.x-x,p.y-y);if(d<Math.min(limit,28)&&(!h||d<h.d))h={type:'chapterTopic',i:j,d,p:w};}}return h;};
const quietGoHit=goHit;
goHit=function(h){if(h?.type==='chapterTopic')selectTopic(h.i);else quietGoHit(h);};
let quietTap=null,quietTapTimer=null;
canvas.addEventListener('pointerdown',e=>{if(e.isPrimary&&e.button===0)quietTap={id:e.pointerId,x:e.clientX,y:e.clientY,t:performance.now(),multi:false};else if(quietTap)quietTap.multi=true;});
canvas.addEventListener('pointerup',e=>{const p=quietTap;quietTap=null;if(!p||p.multi||p.id!==e.pointerId||e.button!==0||performance.now()-p.t>650||Math.hypot(e.clientX-p.x,e.clientY-p.y)>6||state.encounterCinematic)return;const h=findHit(e.clientX,e.clientY,35);clearTimeout(quietTapTimer);quietTapTimer=setTimeout(()=>{if(state.flight)return;if(h?.type==='chapterTopic')selectTopic(h.i);else if(h?.type==='ai')navigateAI(h.i);else if(h?.type==='person')quietPick(h.i);else if(h?.type==='topic'){const s=personalSatellites[h.i];quietPick(s.i,s.j);}else if(!h&&state.mode==='personal')quietClear();},190);});
canvas.addEventListener('dblclick',()=>clearTimeout(quietTapTimer));
window.addEventListener('keydown',e=>{if(document.body.classList.contains('card-revealed'))return;if(e.target.closest('input,textarea,select,dialog'))return;
 if(e.key==='Escape'&&quiet.menu){e.stopImmediatePropagation();e.preventDefault();quietMenu(false);qm.focus();return;}
 if(e.key==='Escape'&&quiet.reading){e.stopImmediatePropagation();e.preventDefault();readingClose.click();return;}
 if(!state.encounterCinematic&&['ArrowRight','ArrowLeft'].includes(e.key)){e.stopImmediatePropagation();e.preventDefault();quietAdvance(e.key==='ArrowRight'?1:-1);}
},{capture:true});
const quietTick=tick;
tick=function(dt,draw=true){quietTick(dt,draw);if(quiet.playing&&state.mode==='chapter'&&!state.flight&&!quiet.reading&&!document.hidden&&!document.querySelector('dialog[open]')){quiet.elapsed+=Math.min(dt,.1);if(quiet.elapsed>=9){quiet.elapsed=0;if(quiet.selection===profile.chapters.length-1)quietFinale();else navigate(quiet.selection+1);}}};
// A soft luminous core replaces the former hover ring; never draw an outline.
const quietGlow=colors.map(c=>{const a=document.createElement('canvas');a.width=a.height=160;const g=a.getContext('2d'),rgb=c.map(x=>Math.round(150+105*x)).join(',');const grad=g.createRadialGradient(80,80,0,80,80,80);grad.addColorStop(0,'rgba(255,249,228,1)');grad.addColorStop(.025,'rgba(255,248,225,.98)');grad.addColorStop(.07,'rgba('+rgb+',.55)');grad.addColorStop(.19,'rgba('+rgb+',.18)');grad.addColorStop(.48,'rgba('+rgb+',.045)');grad.addColorStop(1,'rgba('+rgb+',0)');g.fillStyle=grad;g.fillRect(0,0,160,160);return a;});
function quietLight(w,i,size,alpha=1){const p=project(w);if(!p||p.x<-size||p.x>state.w+size||p.y<-size||p.y>state.h+size)return;ctx.globalAlpha=alpha;ctx.drawImage(quietGlow[i%quietGlow.length],p.x-size,p.y-size,size*2,size*2);ctx.globalAlpha=1;}
const quietSatelliteGlow=[];
drawOverlay=function(){ctx.clearRect(0,0,state.w,state.h);ctx.save();ctx.globalCompositeOperation='screen';const map=['personal','overview'].includes(state.mode)&&!state.flight&&!state.encounterCinematic;
 if(quietPersonVisible()&&!state.encounterCinematic){for(let i=0;i<nodes.length;i++){const hot=state.hoveredStar===i||quiet.selection===i;hoverGlow[i]=mix(hoverGlow[i],hot?1:0,1-Math.exp(-Math.max(.016,state.delta)*8));const detail=starDetail(i),far=1-smoother(clamp(detail*1.7));if(far>.01)quietLight(nodes[i],i,33+hoverGlow[i]*38,far*(.8+hoverGlow[i]*.4));}}
 if(map){strokeWorld(routeLocal.map(p=>worldPoint(p)),'rgba(211,194,155,.14)',.55);
  for(let k=0;k<personalSatellites.length;k++){const s=personalSatellites[k],w=worldPoint(s.p),hot=state.hoverTopicIndex===k||quiet.selection===s.i&&quiet.topic===s.j,related=state.hoveredStar===s.i||quiet.selection===s.i,c=colors[s.i].map(v=>Math.round(135+v*110)).join(',');quietSatelliteGlow[k]=mix(quietSatelliteGlow[k]||0,hot?1:0,.13);const glow=quietSatelliteGlow[k];
   strokeWorld([nodes[s.i],w],'rgba('+c+','+(hot?.28:related?.13:.045)+')',hot?.8:.45);
   if(s.j>0&&personalSatellites[k-1].i===s.i)strokeWorld([worldPoint(personalSatellites[k-1].p),w],'rgba('+c+','+(related?.09:.03)+')',.45);
   quietLight(w,s.i,10+glow*25,related?.84:.57);
  }
 }
 if(quietAIVisible()&&!state.encounterCinematic){for(const provider of providerOrder){if(state.provider!=='all'&&state.provider!==provider)continue;const items=profile.ai_history.map((e,i)=>({e,i})).filter(o=>o.e.provider===provider).sort((a,b)=>a.e.date.localeCompare(b.e.date));const c=providerColors[provider].map(x=>Math.round(x*255)).join(',');strokeWorld(items.map(o=>aiNodes[o.i]),'rgba('+c+',.13)',.5);}
  profile.ai_history.forEach((e,i)=>{if(state.provider==='all'||state.provider===e.provider)quietLight(aiNodes[i],providerOrder.indexOf(e.provider),state.hoverAI===i?42:20,.8);});
 }
 if(state.mode==='chapter'&&state.active>=0&&!state.flight){const i=state.active,p=project(nodes[i]);if(p){const radius=radii[i]*state.h/(2*p.z*Math.tan(state.fov*Math.PI/360));quietLight(nodes[i],i,radius*2.5,.14);for(let j=0;j<(profile.chapters[i].topics||[]).length;j++){const w=topicWorld(i,j),q=project(w);if(!q)continue;const hot=state.topicHover===j||state.topic===j,dx=q.x-p.x,dy=q.y-p.y,l=Math.hypot(dx,dy)||1;ctx.strokeStyle='rgba(178,197,222,'+(hot?.26:.08)+')';ctx.lineWidth=.5;ctx.beginPath();ctx.moveTo(p.x+dx/l*radius*1.1,p.y+dy/l*radius*1.1);ctx.lineTo(q.x,q.y);ctx.stroke();quietLight(w,i,hot?32:14,hot?1:.7);}}}
 ctx.restore();
};
// Short subtitles belong only to the final scene, not the first screen.
encounterActs[0].line1='两片宇宙，';encounterActs[0].line2='各自生长。';
encounterActs[1].line1='沿着各自的轨迹，';encounterActs[1].line2='向彼此靠近。';
encounterActs[2].line1='你的光，';encounterActs[2].line2='也照亮新的可能。';
encounterActs[3].line1='与 AI 相遇，';encounterActs[3].line2='一起走向新的世界。';

// Theme stars update the same short preview, without forcing an open reader.
const quietSelectTopic=selectTopic;
selectTopic=function(j){quietSelectTopic(j);if(state.active>=0&&j>=0){quiet.selection=state.active;quiet.topic=j;quietFillPeek();quietSync();}};
