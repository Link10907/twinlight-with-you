/* Twinlight V9 · point-first overview, readable close-ups, continuous motion.
 * Semantic LOD is explicit: zooming the overview alone never draws a sphere.
 * Ambient motion is local, deterministic and independent of cinematic timing.
 */
const v9={motion:true,flow:0,phase:0,pace:1,pointer:[0,0],look:[0,0],velocity:[0,0],drag:null,coasting:false};
const v9IsMap=()=>['personal','overview'].includes(state.mode)&&!state.encounterCinematic&&!v8.cardOpen;
function v9BodyBlend(i){
 if(!quietPersonVisible()||state.encounterCinematic||v8.cardOpen)return 0;
 const f=state.flight;
 if(f){if(f.event>=0)return 0;if(f.index===i)return rangeEase(.58,.94,f.t);if(state.from===i)return 1-rangeEase(0,.30,f.t);return 0;}
 return state.mode==='chapter'&&state.active===i?1:0;
}
const v9OldDetail=starDetail;
starDetail=function(i){return v9BodyBlend(i)*v9OldDetail(i);};
const v9OldOcclusion=solarOccluded;
solarOccluded=function(s){return !!s&&v9BodyBlend(s.i)>.4?v9OldOcclusion(s):false;};
const v9OldTracks=drawSolarTracks;
drawSolarTracks=function(){if(state.mode==='chapter'&&state.active>=0&&!state.flight)v9OldTracks();};
// Shared forward angular warp. The dust shader applies its analytic inverse.
const v9OldTide=tideLocal;
tideLocal=function(p,g=0){const q=v9OldTide(p,g);if(g!==0)return q;const a=.026*Math.sin(v9.flow*.27+Math.hypot(q[0],q[2])*.035),c=Math.cos(a),s=Math.sin(a);return[q[0]*c-q[2]*s,q[1],q[0]*s+q[2]*c];};
const v9OldWorld=updateWorld;
updateWorld=function(){v9OldWorld();if(!state.encounterCinematic&&state.merge<.001){
 galaxyFrames[0].matrix=mat3YawTilt(.10+v9.phase,.055+.015*Math.sin(v9.flow*.12));
 for(let i=0;i<localNodes.length;i++)nodes[i]=worldPoint(localNodes[i]);
 }};
// Keep read mode stable; a global map rotation must not carry the chosen sun away.
const v9OldShow=showWorld;
showWorld=function(mode='personal',instant=false){v9.velocity=[0,0];v9.coasting=false;v9.look=[0,0];v9OldShow(mode,instant);};
const v9OldNav=navigate;
navigate=function(i,opts={}){v9.velocity=[0,0];v9.coasting=false;v9.look=[0,0];return v9OldNav(i,opts);};
const v9OldAINav=navigateAI;
navigateAI=function(i){v9.velocity=[0,0];v9.coasting=false;return v9OldAINav(i);};
// A light point has a small, untextured core and a feathered glow, never a rim.
function v9Point(w,i,core,spread,alpha=1){const p=project(w);if(!p||p.x<-80||p.y<-80||p.x>state.w+80||p.y>state.h+80)return;
 quietLight(w,i,spread,alpha);ctx.globalAlpha=alpha;ctx.fillStyle='#f5eee3';ctx.beginPath();ctx.arc(p.x,p.y,core,0,TAU);ctx.fill();ctx.globalAlpha=1;
}
const v9Random=seedRandom(911029);
const v9Tracers=Array.from({length:84},(_,i)=>({seed:v9Random(),speed:.48+v9Random()*.86,arm:i%2,scatter:(v9Random()-.5)*.30,height:(v9Random()-.5)*3,hue:i%5}));
function v9TracerPoint(s,u){const r=24+u*118,a=s.arm*Math.PI+2.30*Math.log(r/155+.06)+s.scatter;return worldPoint([Math.cos(a)*r,s.height,Math.sin(a)*r]);}
function drawV9Flow(){
 const count=state.w<701?44:state.quality==='balanced'?54:v9Tracers.length;
 for(let k=0;k<count;k++){const s=v9Tracers[k],u=(s.seed+v9.flow*.017*s.speed)%1,fade=Math.sin(u*Math.PI);if(fade<.09)continue;
  const points=[];for(let j=0;j<=4;j++)points.push(v9TracerPoint(s,Math.max(0,u-j*.0033)));
  const warm=k%3===0,c=warm?'232,201,155':'169,195,231';
  strokeWorld(points,'rgba('+c+','+(fade*.14).toFixed(3)+')',.65);
  quietLight(points[0],s.hue,5.5,fade*.23);
 }
}
const v9OldOverlay=drawOverlay;
drawOverlay=function(){
 if(v8.cardOpen||state.encounterCinematic){v9OldOverlay();return;}
 const map=v9IsMap();
 if(!map&&!state.flight){v9OldOverlay();return;}
 ctx.clearRect(0,0,state.w,state.h);ctx.save();ctx.globalCompositeOperation='screen';
 if(quietPersonVisible()){
  if(map&&!state.flight)drawV9Flow();
  for(let i=0;i<nodes.length;i++){
   const hot=state.hoveredStar===i||quiet.selection===i;
   hoverGlow[i]=mix(hoverGlow[i],hot?1:0,1-Math.exp(-Math.max(.001,state.delta)*8));
   const fade=(1-v9BodyBlend(i))*(state.flight&&state.flight.index!==i?1-rangeEase(.05,.76,state.flight.t):1);
   if(fade<.001)continue;
   const pulse=.92+.08*Math.sin(v9.flow*.92+i*1.79),h=hoverGlow[i];
   v9Point(nodes[i],i,1.55+h*.55,35+h*25,fade*pulse*(.79+h*.21));
  }
  for(const s of personalSatellites){
   const hot=state.hoverTopicIndex===s.k||quiet.selection===s.i&&quiet.topic===s.j,related=state.hoveredStar===s.i||quiet.selection===s.i;
   const fade=(1-v9BodyBlend(s.i))*(state.flight&&state.flight.index!==s.i?1-rangeEase(0,.60,state.flight.t):1);
   if(fade<.001)continue;
   quietSatelliteGlow[s.k]=mix(quietSatelliteGlow[s.k]||0,hot?1:0,1-Math.exp(-Math.max(.001,state.delta)*9));
   const glow=quietSatelliteGlow[s.k],twinkle=.90+.10*Math.sin(v9.flow*1.07+s.k*2.17);
   v9Point(worldPoint(s.p),s.i,.68+glow*.4,10+(related?3:0)+glow*13,fade*twinkle*(related?.76:.58));
  }
 }
 ctx.restore();
};
// The close system retains V8's radii, inclinations, materials and interactions.
const v9OldLabels=updateLabels;
updateLabels=function(){v9OldLabels();document.body.classList.toggle('v9-point-map',v9IsMap());
 labels.forEach((b,i)=>{if(b.hidden)return;const p=project(nodes[i]),name=b.firstElementChild;if(!p||!name)return;const left=p.x>state.w-125;
 name.style.setProperty('left',left?'auto':'36px','important');name.style.setProperty('right',left?'36px':'auto','important');name.style.setProperty('top','16px','important');name.style.setProperty('text-align',left?'right':'left','important');});
};
const v9OldHit=findHit;
findHit=function(x,y,limit=42){if(v9IsMap()&&!state.flight){for(let i=0;i<nodes.length;i++){const p=project(nodes[i]);if(!p)continue;const d=Math.hypot(p.x-x,p.y-y);if(d<Math.min(10,limit))return{type:'person',i,d,p:nodes[i]};}}return v9OldHit(x,y,limit);};
const v9OldCreate=createNav;
createNav=function(){v9OldCreate();labels.forEach((b,i)=>{b.title='';b.setAttribute('aria-label','查看 '+profile.chapters[i].label+' 的成长摘要');});$('v7Count').textContent=profile.chapters.length+' 颗主星 · '+profile.chapters.reduce((a,c)=>a+c.topics.length,0)+' 颗微光';};
const v9MotionButton=el('button');v9MotionButton.id='v9Motion';v9MotionButton.setAttribute('aria-label','暂停星系动效');
function v9SyncMotion(){v9MotionButton.textContent=v9.motion?'暂停星系动效 Ⅱ':'恢复星系动效 ▷';v9MotionButton.setAttribute('aria-pressed',String(!v9.motion));v9MotionButton.setAttribute('aria-label',v9.motion?'暂停星系动效':'恢复星系动效');document.body.classList.toggle('v9-motion-paused',!v9.motion);}
v9MotionButton.onclick=()=>{v9.motion=!v9.motion;v9.velocity=[0,0];v9.coasting=false;v9SyncMotion();};$('v7Tools').prepend(v9MotionButton);v9SyncMotion();
// Finite angular momentum after a deliberate single-pointer orbit gesture.
// A tap, pan, pinch, cancellation, or held finger never injects momentum.
canvas.addEventListener('pointerdown',e=>{v9.velocity=[0,0];v9.coasting=false;
 if(activePointers.size===1&&e.button===0&&!e.shiftKey&&!state.flight&&!state.encounterCinematic)v9.drag={id:e.pointerId,x:e.clientX,y:e.clientY,t:performance.now(),distance:0,v:[0,0]};else v9.drag=null;
});
canvas.addEventListener('pointermove',e=>{const d=v9.drag;if(!d||e.pointerId!==d.id)return;
 if(activePointers.size!==1||e.shiftKey||gesture?.pan){v9.drag=null;return;}
 const t=performance.now(),dt=Math.max(.012,(t-d.t)/1000),dx=e.clientX-d.x,dy=e.clientY-d.y;
 d.distance+=Math.hypot(dx,dy);d.v=[mix(d.v[0],clamp(-dx*.005/dt,-1.4,1.4),.40),mix(d.v[1],clamp(dy*.004/dt,-.9,.9),.40)];d.x=e.clientX;d.y=e.clientY;d.t=t;
});
canvas.addEventListener('pointerup',e=>{const d=v9.drag;v9.drag=null;if(!d||d.id!==e.pointerId||activePointers.size||state.reduced||!v9.motion)return;
 if(d.distance>10&&performance.now()-d.t<110){v9.velocity=d.v.map(x=>x*.72);v9.coasting=true;}
});
canvas.addEventListener('pointercancel',()=>{v9.drag=null;v9.velocity=[0,0];v9.coasting=false;});
canvas.addEventListener('wheel',()=>{v9.velocity=[0,0];v9.coasting=false;},{passive:true});
window.addEventListener('pointermove',e=>{if(e.pointerType==='mouse')v9.pointer=[clamp(e.clientX/state.w*2-1,-1,1),clamp(e.clientY/state.h*2-1,-1,1)];});
document.documentElement.addEventListener('pointerleave',()=>{v9.pointer=[0,0];});
window.addEventListener('blur',()=>{v9.drag=null;v9.velocity=[0,0];v9.coasting=false;v9.pointer=[0,0];});
const v9OldTick=tick;
tick=function(dt,draw=true){
 if(v8.cardOpen){v9OldTick(dt,draw);return;}
 const motionDt=clamp(dt,0,.25),step=clamp(dt,0,.1),modal=!!document.querySelector('dialog[open]');
 const move=v9.motion&&!state.reduced&&!state.paused&&!document.hidden&&!modal;
 const map=v9IsMap()&&!state.flight;
 const hover=state.hoveredStar>=0||state.hoverTopicIndex>=0;
 const desired=map?(activePointers.size?.20:hover?.16:quiet.selection>=0?.40:1):0;
 v9.pace=mix(v9.pace,desired,1-Math.exp(-motionDt*3.8));
 if(move&&map){v9.flow+=motionDt*v9.pace;v9.phase+=motionDt*v9.pace*.023;}
 if(v9.coasting&&!activePointers.size&&!state.flight&&!state.viewTween&&!state.encounterCinematic&&move){
  orbit.goalYaw+=v9.velocity[0]*motionDt;orbit.goalPitch=clamp(orbit.goalPitch+v9.velocity[1]*motionDt,-.25,1.48);
  const decay=Math.exp(-motionDt*5.3);v9.velocity=v9.velocity.map(x=>x*decay);if(Math.hypot(...v9.velocity)<.004){v9.coasting=false;v9.velocity=[0,0];}
 }
 const wasPaused=state.paused;if(!move&&!state.encounterCinematic)state.paused=true;
 v9OldTick(step,false);state.paused=wasPaused;
 // Offset the computed camera only. Do not accumulate parallax into orbit state.
 if(v9IsMap()&&!state.flight&&!state.viewTween){
  const enable=move&&!activePointers.size&&!hover&&quiet.selection<0;
  const target=enable?v9.pointer:[0,0],ease=1-Math.exp(-step*3.2);
  v9.look=v9.look.map((x,i)=>mix(x,target[i],ease));basis();
  const sway=enable?Math.sin(v9.flow*.24)*.48:0;
  state.cam=add(state.cam,add(mul(R,v9.look[0]*4.4+sway),mul(U,-v9.look[1]*2.3)));
 }
 if(draw){paint();if(state.monitor&&state.frame%15===0)$('performance').textContent=Math.round(1000/state.frameEMA)+' FPS · '+canvas.width+' × '+canvas.height+' · '+(v9IsMap()?'光点全景':'行星近景');}
};
// Reuse the illustrated artwork generated in this conversation. It is a fantasy
// persona, not a claim of photographic likeness or a freshly executed Skill.
const V9_CARD_IMAGE='__V9_CARD_IMAGE__';
const v9OldCardSVG=buildCardSVG;
buildCardSVG=function(side='front'){
 if(side!=='front'||!currentPersona().ready)return v9OldCardSVG(side);
 return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 800" width="600" height="800"><title>SSR · 筑星者 · AI 眼中的你</title><image href="${V9_CARD_IMAGE}" x="0" y="0" width="600" height="800" preserveAspectRatio="xMidYMid slice"/></svg>`;
};
refreshIdentity();window.twinlightV8.cardSVG=buildCardSVG;
window.twinlightV9={getState:()=>({view:v9IsMap()?'points':state.mode,flow:v9.flow,phase:v9.phase,motion:v9.motion,reduced:state.reduced,coasting:v9.coasting,bodyBlends:nodes.map((_,i)=>v9BodyBlend(i)),renderedBodies:renderObjects.length,cardArt:'independently-bound-layers',look:[...v9.look]}),pause:()=>{v9.motion=false;v9SyncMotion();},resume:()=>{v9.motion=true;v9SyncMotion();}};
