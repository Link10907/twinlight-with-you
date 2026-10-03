/* V6 · forty navigable theme stars, an editable public-release chronology,
 * and a reversible, 12-second, explicitly artistic tidal encounter.
 * Data remain in page memory. No external fetches, no storage, no tracking.
 */
const encounterDuration=14;
Object.assign(state,{hoverTopicIndex:-1,encounterCinematic:false,encounterElapsed:0,encounterRewind:false,encounterScrubbing:false});
let personalSatellites=[],personalButtons=[],companionYear=2023,lastPoem=-1;
const rangeEase=(a,b,x)=>smoother(clamp((x-a)/(b-a)));
// Same radial shear in CPU navigation coordinates and GPU particle positions.
function tideLocal(p,g){const m=rangeEase(.08,.93,state.merge);if(m===0)return p.slice();const r=Math.hypot(p[0],p[2]),outer=smooth(clamp((r-15)/125)),ang=Math.atan2(p[2],p[0]),twist=(g?-.58:.68)*m*outer;const a=ang+twist,rr=r*(1+.17*m*outer*Math.cos(ang*2+.6+g));return [Math.cos(a)*rr,p[1]+m*outer*7*Math.sin(a*2+g),Math.sin(a)*rr];}
function worldPoint(p,g=0){const f=galaxyFrames[g];return add(f.origin,mul(mv(f.matrix,tideLocal(p,g)),f.scale));}
function updateWorld(){
 const p=clamp(state.merge),m=smoother(p),tt=state.time;
 const mid=[111,22.5,-72.5],off=[111,22.5,-72.5],a=m*1.12,c=Math.cos(a),s=Math.sin(a),shrink=1-.88*m;
 const d=[(off[0]*c+off[2]*s)*shrink,off[1]*(1-.92*m),(-off[0]*s+off[2]*c)*shrink];
 galaxyFrames[0].origin=sub(mid,d);galaxyFrames[1].origin=add(mid,d);
 galaxyFrames[0].matrix=mat3YawTilt(.10+tt*.0023+m*.48,.055+m*.12);
 galaxyFrames[1].matrix=mat3YawTilt(-.60-tt*.003+m*.44,.32-m*.10);
 for(let i=0;i<nodes.length;i++)nodes[i]=worldPoint(localNodes[i]);
 aiNodes=aiLocal.map(p=>worldPoint(p,1));
}
function rebuildPersonalMap(){
 personalSatellites=[];personalButtons=[];$('personalLabels').replaceChildren();
 const rr=seedRandom(673112);
 profile.chapters.forEach((c,i)=>(c.topics||[]).forEach((t,j)=>{
  const a=-1.05+j*TAU/c.topics.length+i*.38,rad=22+(j%3)*4.2;
  const n=localNodes[i],p=add(n,[Math.cos(a)*rad,2.8+rr()*4,Math.sin(a)*rad*.83]);
  const idx=personalSatellites.length,b=el('button','personal-star'),rgb=colors[i].map(v=>Math.round(110+v*130)).join(',');b.style.setProperty('--topiccolor',rgb);
  b.setAttribute('aria-label','探索 '+t.name+' · '+c.label);b.dataset.chapter=i;b.dataset.topic=j;b.append(el('i'));
  const label=el('span','',t.name);label.append(el('small','',c.label));b.append(label);
  b.onpointerenter=b.onfocus=()=>{state.hoverTopicIndex=idx;state.hoveredStar=-1;state.hoverAI=-1;};
  b.onpointerleave=b.onblur=()=>{if(state.hoverTopicIndex===idx)state.hoverTopicIndex=-1;};
  b.onclick=()=>navigateTopic(i,j);$('personalLabels').append(b);personalButtons.push(b);personalSatellites.push({p,i,j,name:t.name});
 }));
 $('personalCount').textContent=profile.chapters.length+personalSatellites.length;
 $('personalCountNote').textContent=profile.chapters.length+' 段来路 · '+personalSatellites.length+' 颗主题星';
}
function navigateTopic(i,j){setAuto(false);state.hoverTopicIndex=-1;if(state.mode==='chapter'&&state.active===i&&!state.flight){selectTopic(j);return;}navigate(i);if(state.flight)state.flight.topic=j;}
const oldFinishFlight=finishFlight;
finishFlight=function(){const j=state.flight?.topic;oldFinishFlight();if(Number.isInteger(j)&&j>=0&&state.active>=0)selectTopic(j);};
const oldShowWorld=showWorld;
showWorld=function(mode='overview',instant=false){
 state.mergePlaying=false;state.encounterRewind=false;state.encounterCinematic=false;document.body.classList.remove('encounter-cinema');$('encounterCinema').hidden=true;state.hoverTopicIndex=-1;
 oldShowWorld(mode,instant);updateEncounterUI();
};
const oldNav=navigate,oldNavAI=navigateAI;
navigate=function(i,opts={}){endEncounter(false);oldNav(i,opts);};
navigateAI=function(i){endEncounter(false);oldNavAI(i);};
function endEncounter(returnView=false){state.encounterCinematic=false;state.mergePlaying=false;state.encounterRewind=false;document.body.classList.remove('encounter-cinema');$('encounterCinema').hidden=true;updateEncounterUI();if(returnView)animateView(modeView('overview'),1.5);}
function cacheTopicPositions(){
 topicPositions=localNodes.map((n,i)=>{const p=nodes[i],v=targetView(i),f=norm(sub(v.target,v.cam)),r=norm(cross(f,[0,1,0])),u=norm(cross(r,f)),depth=dot(sub(p,v.cam),f),tan=Math.tan(v.fov*Math.PI/360);
 const xy=state.w<900?[[.13,.15],[.39,.105],[.74,.115],[.87,.195],[.13,.255],[.35,.292],[.67,.295],[.86,.272]]:[[.50,.35],[.59,.23],[.77,.215],[.92,.34],[.945,.53],[.84,.70],[.67,.73],[.53,.58]];
 return (profile.chapters[i].topics||[]).map((t,j)=>{const q=xy[j%8],w=add(add(add(v.cam,mul(f,depth)),mul(r,(q[0]*2-1)*tan*state.w/state.h*depth)),mul(u,(1-q[1]*2)*tan*depth));return sub(w,p);});});
}
function updatePersonalMap(){
 const on=['overview','personal'].includes(state.mode)&&!state.flight&&!state.clean&&!state.encounterCinematic;
 const taken=[];labels.forEach((b,i)=>{if(!b.hidden){const p=project(nodes[i]);if(p)taken.push({x:p.x+55,y:p.y-5,w:90,h:27});}});
 const projections=personalSatellites.map((s,k)=>{const p=on?project(worldPoint(s.p)):null;return {s,k,p};});
 projections.sort((a,b)=>(b.k===state.hoverTopicIndex?1:0)-(a.k===state.hoverTopicIndex?1:0));
 for(const {s,k,p}of projections){const b=personalButtons[k],ok=on&&p&&p.x>25&&p.x<state.w-30&&p.y>102&&p.y<state.h-144;b.hidden=!ok;if(!ok)continue;
 b.style.transform='translate3d('+(p.x-10).toFixed(1)+'px,'+(p.y-10).toFixed(1)+'px,0)';
 const hot=k===state.hoverTopicIndex||state.hoveredStar===s.i,sz=state.w<900?65:92,cx=p.x+sz*.5+12;
 let labelled=hot||(!taken.some(q=>Math.abs(q.x-cx)<(q.w+sz)*.5&&Math.abs(q.y-p.y)<27)&&(state.mode==='personal'||s.j%2===0));
 if(labelled)taken.push({x:cx,y:p.y,w:sz,h:24});b.classList.toggle('named',labelled);b.classList.toggle('hot',k===state.hoverTopicIndex);b.classList.toggle('left',p.x>state.w-150);
 }
 $('personalAtlas').hidden=state.mode!=='personal'||state.flight||state.clean||state.encounterCinematic;
}
const oldUpdateLabels=updateLabels;
updateLabels=function(){oldUpdateLabels();updatePersonalMap();if(state.encounterCinematic){$('galaxyTitles').hidden=true;$('focusHint').hidden=true;labels.forEach(b=>b.hidden=true);aiButtons.forEach(b=>b.hidden=true);}
 else if(state.hoverTopicIndex>=0&&!state.flight&&!state.clean){const s=personalSatellites[state.hoverTopicIndex];if(s){$('focusHint').hidden=false;$('focusName').textContent=s.name;$('focusHint').style.left=clamp(state.pointer[0]+20,20,state.w-240)+'px';$('focusHint').style.top=clamp(state.pointer[1]+25,105,state.h-220)+'px';}}
};
function findHit(x,y,limit=42){let best=null;const consider=(p,type,i,l=limit)=>{const q=project(p);if(!q)return;const d=Math.hypot(q.x-x,q.y-y);if(d<l&&(!best||d<best.d))best={type,i,d,p};};if(state.encounterCinematic)return null;
 if(state.mode!=='ai')nodes.forEach((p,i)=>consider(p,'person',i));
 if(['overview','personal'].includes(state.mode))personalSatellites.forEach((s,i)=>consider(worldPoint(s.p),'topic',i,Math.min(24,limit)));
 if(state.mode!=='personal')aiNodes.forEach((p,i)=>{if(state.provider==='all'||profile.ai_history[i].provider===state.provider)consider(p,'ai',i);});return best;
}
function goHit(hit){if(!hit)return;if(hit.type==='topic'){const s=personalSatellites[hit.i];navigateTopic(s.i,s.j);}else if(hit.type==='person')navigate(hit.i);else navigateAI(hit.i);}
canvas.addEventListener('pointermove',e=>{if(activePointers.size||state.flight)return;const hit=findHit(e.clientX,e.clientY);state.hoverTopicIndex=hit?.type==='topic'?hit.i:-1;});
// Version chronology is an explicit editorial layer, independent of personal-use evidence.
function companionYears(){return [...new Set(profile.ai_history.map(e=>e.date.slice(0,4)))].filter(y=>Number(y)>=2023).sort();}
function showCompanion(){if(state.active<0)return;companionOpen=!companionOpen;$('companionCard').hidden=!companionOpen;if(!companionOpen)return;const c=profile.chapters[state.active];companionYear=String(c.companion_year||'');renderCompanion();}
function renderCompanion(){
 const c=profile.chapters[state.active];$('companionName').textContent='那时，AI 也在向前。';$('companionText').textContent='沿着年份，看看与你的成长并行的版本与产品。';
 $('companionYears').replaceChildren();companionYears().forEach(y=>{const b=el('button',y===String(companionYear)?'active':'',y);b.setAttribute('aria-pressed',String(y===String(companionYear)));b.onclick=()=>{companionYear=y;renderCompanion();};$('companionYears').append(b);});
 const list=$('companionVersions');list.replaceChildren();const entries=profile.ai_history.filter(e=>e.date.startsWith(String(companionYear))).sort((a,b)=>a.date.localeCompare(b.date));
 for(const e of entries){const row=el('article','version-row');row.style.setProperty('--vcolor',providerColors[e.provider].map(x=>Math.round(x*255)).join(','));row.append(el('i'),el('time','',e.date.slice(5).replace('-','.')));
 const content=el('div');content.append(el('small','',e.provider),el('b','',e.name),el('p','',e.title));row.append(content);
 const b=el('button','version-fly','↗');b.setAttribute('aria-label','飞往 '+e.name+' 的公开发布事件');b.onclick=()=>navigateAI(profile.ai_history.indexOf(e));row.append(b);list.append(row);}
 $('companionTrace').replaceChildren();const evidence=el('details');evidence.append(el('summary','','关于这段时间，你实际使用的记录'));
 const tr=traceLabel(c.ai_trace);evidence.append(el('p','',tr.name+' · '+tr.tag));const relevant=(profile.ai_usage||[]).filter(e=>(e.date||'').startsWith(String(companionYear)));
 relevant.forEach(e=>{const d=el('p','usage-note');d.textContent=(e.date||'')+' · '+(e.reported_name||e.product)+' · '+(e.status==='self_report'?'用户自述':'产品线索');evidence.append(d);});
 evidence.append(el('p','fine','版本年表是公开历史，不表示你使用过其中的每个模型。章节与年份是浏览入口，不是精确的个人起止日期。'));$('companionTrace').append(evidence);
 $('companionVersionCount').textContent=entries.length+' 个精选节点 · 按公开时间排序';
}
const oldFillLetter=fillLetter;
fillLetter=function(i,j=-1){oldFillLetter(i,j);const c=profile.chapters[i],year=String(c.companion_year||[2023,2024,2025,2026,2026][i]);
 const entries=profile.ai_history.filter(e=>e.date.startsWith(year));$('modelTrace').replaceChildren(el('span','','与这段旅程并行的 AI 年份 · '),el('strong','',year));
 const echo=$('eraEcho');echo.replaceChildren();entries.slice(0,6).forEach(e=>{const chip=el('button','era-chip');chip.append(el('span','',e.name),el('small','',e.date.slice(5)+' · 发布'));chip.onclick=()=>{companionOpen=false;showCompanion();};echo.append(chip);});
 if(entries.length>6){const b=el('button','era-chip','还有 '+(entries.length-6)+' 个版本 ↗');b.onclick=()=>{companionOpen=false;showCompanion();};echo.append(b);}
};
const encounterActs=[
 {start:0,end:.25,code:'01 / 引力 · GRAVITY',line1:'就像银河系与仙女座星系，',line2:'向彼此靠近。',sub:'一片宇宙，装着你的来路。另一片，记录 AI 的成长。'},
 {start:.25,end:.51,code:'02 / 相遇 · ENCOUNTER',line1:'我们也将',line2:'与 AI 相聚。',sub:'问题成为引力，答案带来回声。两条轨迹开始靠近。'},
 {start:.51,end:.78,code:'03 / 交织 · INTERWEAVE',line1:'带着各自的来路，',line2:'点亮彼此的可能。',sub:'不是抹去你的星光，而是在相遇中，继续成为自己。'},
 {start:.78,end:1,code:'04 / 同光 · A SHARED WORLD',line1:'一起，',line2:'组成新的世界。',sub:'AI 在进化，其实你也是。'}
];
function updateEncounterUI(){
 $('encounterPlay').textContent=state.mergePlaying?'Ⅱ 暂停':state.merge>.998?'↺ 重看':'▷ 相遇';
 $('cinemaPause').textContent=state.mergePlaying?'Ⅱ 暂停':'▷ 继续';
 const act=encounterActs.findIndex((a,i)=>state.merge>=a.start&&(state.merge<a.end||i===3));
 $('encounterCaption').textContent=['各自生长','引力相遇','旋臂交织','新的世界'][Math.max(0,act)];
 if(state.encounterCinematic){$('encounterCinema').hidden=false;document.body.classList.add('encounter-cinema');
  const a=encounterActs[Math.max(0,act)],local=clamp((state.merge-a.start)/(a.end-a.start));
  if(lastPoem!==act){lastPoem=act;$('poemCode').textContent=a.code;$('poemLine1').textContent=a.line1;$('poemLine2').textContent=a.line2;$('poemSub').textContent=a.sub;}
  const fade=state.reduced?1:Math.min(rangeEase(0,.12,local),act===3?1:1-rangeEase(.90,1,local));
  $('encounterPoem').style.opacity=String(fade);$('encounterPoem').style.transform='translateY('+((1-fade)*14).toFixed(2)+'px)';
  $('cinemaRange').value=String(Math.round(state.merge*1000));$('cinemaTime').textContent=String(Math.round(state.merge*encounterDuration)).padStart(2,'0')+' / '+encounterDuration+' s';
  $('cinemaContinue').hidden=state.merge<.97;$('cinemaPause').hidden=state.merge>=.998;
  document.querySelectorAll('#cinemaChapters i').forEach((el,i)=>el.classList.toggle('active',i===act));
 }
}
function encounter(){
 if(!state.encounterCinematic){if(state.mode!=='overview')showWorld('overview');setAuto(false);state.encounterCinematic=true;state.exploring=false;document.body.classList.remove('exploring');state.orbiting=false;
  animateView(state.w<900?{cam:[111,720,490],target:[111,-34,-72],fov:62}:{cam:[124,301,410],target:[111,-32,-72],fov:51},2.1);
  lastPoem=-1;
 }
 if(state.mergePlaying){state.mergePlaying=false;state.mergeGoal=state.merge;}else if(state.merge>.985){state.mergePlaying=false;state.encounterRewind=true;state.mergeGoal=0;}else{state.encounterRewind=false;state.mergePlaying=true;state.mergeGoal=1;}
 updateEncounterUI();
}
function advanceEncounter(dt){
 if(state.encounterRewind){state.merge=Math.max(0,state.merge-dt/2.6);if(state.merge===0){state.encounterRewind=false;state.mergePlaying=true;state.mergeGoal=1;}}
 else if(state.mergePlaying&&!state.reduced){state.merge=Math.min(1,state.merge+dt/encounterDuration);if(state.merge>1-1e-7)state.merge=1;state.mergeGoal=state.merge;if(state.merge===1){state.mergePlaying=false;}}
 else if(!state.mergePlaying){state.merge=mix(state.merge,state.mergeGoal,1-Math.exp(-dt*5));if(Math.abs(state.merge-state.mergeGoal)<.00002)state.merge=state.mergeGoal;}
 if(state.reduced&&state.mergePlaying){state.mergePlaying=false;state.mergeGoal=state.merge;toast('减少运动已开启：可用下方滑杆静态浏览四幕。');}
 updateEncounterUI();
}
function scrubEncounter(v){state.mergePlaying=false;state.encounterRewind=false;state.mergeGoal=clamp(v);updateEncounterUI();}
$('meetHero').onclick=$('encounterPlay').onclick=$('cinemaPause').onclick=encounter;
$('cinemaReplay').onclick=()=>{state.encounterRewind=true;state.mergePlaying=false;state.mergeGoal=0;updateEncounterUI();};
$('cinemaExit').onclick=$('cinemaContinue').onclick=()=>endEncounter(true);
$('cinemaRange').oninput=e=>scrubEncounter(Number(e.target.value)/1000);
$('encounterRange').oninput=e=>{if(state.mode!=='overview')showWorld('overview');scrubEncounter(Number(e.target.value)/100);};
$('companionLabel').onclick=showCompanion;
$('companionExplore').onclick=()=>showWorld('ai');
$('home').onclick=$('navMap').onclick=$('overviewBtn').onclick=()=>showWorld('overview');
$('navPersonal').onclick=$('humanGalaxyTitle').onclick=()=>showWorld('personal');
$('navAI').onclick=$('footerAI').onclick=$('aiGalaxyTitle').onclick=$('readerAI').onclick=()=>showWorld('ai');
$('begin').onclick=()=>navigate(0);$('skip').onclick=()=>finishFlight();
window.addEventListener('keydown',e=>{if(document.querySelector('dialog[open]'))return;if(e.key==='Escape'&&state.encounterCinematic){e.stopImmediatePropagation();endEncounter(true);}},{capture:true});
const oldRebuildAI=rebuildAINodes;
rebuildAINodes=function(){oldRebuildAI();rebuildPersonalMap();};
// The additional map layer is small; the galaxy itself remains GPU-batched.
function drawPersonalMap(){if(!['overview','personal'].includes(state.mode)||state.flight||state.encounterCinematic)return;
 const show=state.mode==='personal';for(let k=0;k<personalSatellites.length;k++){const s=personalSatellites[k],w=worldPoint(s.p),p=project(w);if(!p)continue;
 const hot=state.hoverTopicIndex===k||state.hoveredStar===s.i,c=colors[s.i].map(v=>Math.round(135+v*110)).join(',');
 if(show||hot||s.j%2===0)strokeWorld([nodes[s.i],w],'rgba('+c+','+(hot?.35:show?.11:.065)+')',hot?.8:.5);
 if(s.j>0){const prev=personalSatellites[k-1];if(prev.i===s.i)strokeWorld([worldPoint(prev.p),w],'rgba('+c+','+(hot?.28:.085)+')',.45);}
 glint(w,s.i,hot?26:11,hot?1:.67);ctx.fillStyle='rgba('+c+','+(hot?1:.78)+')';ctx.fillRect(p.x-.85,p.y-.85,1.7,1.7);
 }
}
const oldDrawOverlay=drawOverlay;
drawOverlay=function(){oldDrawOverlay();drawPersonalMap();};
