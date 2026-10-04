/* Twinlight V10 · view-dependent layered card.
 * Parallax / foil equations adapted from HRuiCcc/RuiC-card-skill, MIT (2026).
 * See THIRD-PARTY-NOTICES.md. Canvas-local uView has the same bounded normal
 * and signed depths as the upstream viewer. No copied single-poster tilt.
 * All submitted artwork is validated and bound to its persona digest.
 */
const HOLO_LAYERS=__CARD_LAYERS__;
const holo={ready:false,gl:null,program:null,loc:{},x:-.045,y:-.14,tx:-.045,ty:-.14,auto:true,zoom:1,depth:1,foil:.5,finish:0,drag:null,last:0,elapsed:0,lastInteraction:0,failed:false,drawn:0,images:{}};
const holoCard=$('identityCard'),holoTilt=holoCard.querySelector('.card-tilt'),holoFront=holoCard.querySelector('.card-front');
const holoCanvas=el('canvas');holoCanvas.id='holoCanvas';holoCanvas.setAttribute('aria-hidden','true');holoFront.prepend(holoCanvas);
const holoFallback=el('div','holo-fallback');holoFallback.hidden=true;holoFront.prepend(holoFallback);
for(const k of ['background','spirit','subject','effects','text']){const im=el('img');im.alt='';if(HOLO_LAYERS[k]!=='auto')im.src=HOLO_LAYERS[k];im.dataset.layer=k;holoFallback.append(im);}
// A thin solid card edge, not a group of disconnected transparent posters.
for(let k=0;k<8;k++){const e=el('div','holo-thickness');e.style.transform=`translateZ(${(-2.7+k*.75).toFixed(2)}px)`;holoCard.querySelector('.card-flipper').prepend(e);}
const holoControls=el('div','holo-controls');holoControls.innerHTML=`<div class="holo-control-row"><button id="holoAuto" aria-pressed="true">Ⅱ 暂停轻摇</button><button id="holoReset">归位 ↺</button><button id="holoSettings" aria-expanded="false" aria-controls="holoSettingsPanel">质感与景深 ☷</button></div><div id="holoSettingsPanel" hidden><label>层次景深 <input id="holoDepth" type="range" min="0" max="1.6" step=".05" value="1" aria-label="层次景深"><output id="holoDepthValue">1.00</output></label><label>镭射强度 <input id="holoFoil" type="range" min="0" max="1" step=".05" value=".5" aria-label="镭射强度"><output id="holoFoilValue">0.50</output></label><div class="holo-finishes" aria-label="卡面材质"><button data-finish="0" aria-pressed="true">珠光</button><button data-finish="1" aria-pressed="false">银箔</button><button data-finish="3" aria-pressed="false">烫金</button><button data-finish="2" aria-pressed="false">原画</button></div></div>`;
$('cardSideHint').after(holoControls);$('cardSideHint').textContent='按住拖转 · 滚轮缩放 · 双击归位';
function holoStaticArt(){const d=currentPersona();return d.ready&&(d.art_status==='static'||d.art_mode==='static');}
function holoConstrainAppearance(){
 // A single prototype remains a printed flat image, even if a script changes
 // the controls. Physical card rotation is still available for viewing it.
 if(holoStaticArt()){holo.depth=0;holo.foil=0;holo.finish=2;}
}
const HOLO_VERT=`attribute vec2 a_pos;varying vec2 vUv;void main(){vUv=vec2(a_pos.x*.5+.5,.5-a_pos.y*.5);gl_Position=vec4(a_pos,0.,1.);}`;
const HOLO_FRAG=`precision highp float;
varying vec2 vUv;uniform sampler2D tBackground,tSubject,tSpirit,tEffects,tText,tLine;
uniform vec3 uView;uniform float uTime,uDepth,uFoil,uFinish;
float inside(vec2 p){return step(0.,p.x)*step(0.,p.y)*step(p.x,1.)*step(p.y,1.);}
vec2 parallax(vec2 uv,float depth){return uv+uView.xy/max(abs(uView.z),.4)*depth*.10;}
vec3 spectrum(float p){return .66+.25*cos(6.28318*(p+vec3(0.,.33,.67)));}
vec3 film(vec2 uv){float p=uv.x*.85+uv.y*.55+uView.x*1.5-uView.y*.9;if(uFinish>2.5){float hi=.5+.5*sin(p*6.28318);float glint=.5+.5*cos((p+.25)*6.28318);return mix(vec3(.72,.50,.20),vec3(1.,.90,.60),hi*.7+glint*.3);}vec3 c=spectrum(p);return mix(c,vec3(dot(c,vec3(.2126,.7152,.0722))),step(.5,uFinish));}
float sweep(vec2 uv){return pow(.5+.5*sin((uv.x*.72+uv.y*.45+uView.x*1.2+uView.y*.6)*6.283),10.);}
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
void main(){
 vec2 uv=vUv,bu=parallax(uv,float(__DEPTH_BG__)*uDepth),su=parallax(uv,float(__DEPTH_SUBJECT__)*uDepth),eu=parallax(uv,float(__DEPTH_EFFECTS__)*uDepth),pu=parallax(uv,.10*uDepth);
 vec3 col=texture2D(tBackground,clamp(bu,0.,1.)).rgb;
 vec4 sp=texture2D(tSpirit,clamp(pu,0.,1.));col=mix(col,sp.rgb,sp.a*inside(pu));
 vec4 sub=texture2D(tSubject,clamp(su,0.,1.));col=mix(col,sub.rgb,sub.a*inside(su));
 vec4 fx=texture2D(tEffects,clamp(eu,0.,1.));col=mix(col,fx.rgb,fx.a*inside(eu));
 float amount=abs(uFinish-2.)<.05?0.:uFoil;vec3 foil=film(uv);float band=sweep(uv);float lum=dot(col,vec3(.2126,.7152,.0722));
 if(uFinish>2.5)col=col*vec3(1.02,.95,.78)+vec3(.025,.008,0.);
 col*=1.-amount*.21*(1.-foil)*(.2+band*.8);col+=foil*amount*band*(uFinish>2.5?1.7:1.)*(.065+.11*(1.-lum));
 float line=1.-smoothstep(.06,.25,texture2D(tLine,clamp(su,0.,1.)).r);col+=line*inside(su)*sub.a*band*amount*.055;
 vec4 txt=texture2D(tText,uv);col=mix(col,txt.rgb,txt.a); // Card frame/text NEVER parallax.
 float edge=1.-smoothstep(.014,.035,min(min(uv.x,1.-uv.x),min(uv.y,1.-uv.y)));
 col+=foil*amount*band*(edge*.16+txt.a*.025);
 vec2 cell=floor(uv*vec2(480.,720.));float flake=step(.996,hash(cell))*pow(.5+.5*sin(hash(cell+8.)*30.+uView.x*20.+uTime*.6),10.);
 col+=foil*flake*amount*.10;gl_FragColor=vec4(clamp(col,0.,1.),1.);
}`;
function holoCompile(g,type,code){const s=g.createShader(type);g.shaderSource(s,code);g.compileShader(s);if(!g.getShaderParameter(s,g.COMPILE_STATUS))throw Error(g.getShaderInfoLog(s));return s;}
async function initHolo(){if(holo.ready||holo.failed||holo.loading)return;holo.loading=true;
 try{const g=holoCanvas.getContext('webgl',{alpha:false,antialias:true,preserveDrawingBuffer:true});if(!g)throw Error('WebGL unavailable');holo.gl=g;
 const p=g.createProgram();g.attachShader(p,holoCompile(g,g.VERTEX_SHADER,HOLO_VERT));g.attachShader(p,holoCompile(g,g.FRAGMENT_SHADER,HOLO_FRAG));g.linkProgram(p);if(!g.getProgramParameter(p,g.LINK_STATUS))throw Error(g.getProgramInfoLog(p));holo.program=p;g.useProgram(p);
 const b=g.createBuffer();g.bindBuffer(g.ARRAY_BUFFER,b);g.bufferData(g.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),g.STATIC_DRAW);const loc=g.getAttribLocation(p,'a_pos');g.enableVertexAttribArray(loc);g.vertexAttribPointer(loc,2,g.FLOAT,false,0,0);
 for(const n of ['uView','uTime','uDepth','uFoil','uFinish'])holo.loc[n]=g.getUniformLocation(p,n);
 const pairs=[['background','tBackground'],['subject','tSubject'],['spirit','tSpirit'],['effects','tEffects'],['text','tText'],['lineart','tLine']];
 const images=await Promise.all(pairs.map(([n])=>imageReady(HOLO_LAYERS[n])));
 g.useProgram(p);
 pairs.forEach(([name,key],i)=>{holo.images[name]=images[i];const t=g.createTexture();g.activeTexture(g.TEXTURE0+i);g.bindTexture(g.TEXTURE_2D,t);g.pixelStorei(g.UNPACK_FLIP_Y_WEBGL,false);g.pixelStorei(g.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);g.texImage2D(g.TEXTURE_2D,0,g.RGBA,g.RGBA,g.UNSIGNED_BYTE,images[i]);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_MIN_FILTER,g.LINEAR);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_MAG_FILTER,g.LINEAR);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_WRAP_S,g.CLAMP_TO_EDGE);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_WRAP_T,g.CLAMP_TO_EDGE);g.uniform1i(g.getUniformLocation(p,key),i);});
 holo.ready=true;holo.loading=false;holoCard.classList.add('holo-ready');holoRender();
 }catch(e){holo.loading=false;holo.failed=true;holoCard.classList.add('holo-ready','holo-fallback-on');holoCanvas.hidden=true;holoFallback.hidden=false;console.warn('Layered CSS fallback:',String(e));}}
function holoRender(){
 holoConstrainAppearance();
 if(!v8.cardOpen||!currentPersona().ready)return;
 const cw=holoCard.clientWidth,scale=Math.min(devicePixelRatio||1,2);const width=Math.round(cw*scale);if(width<1)return;
 const vx=-Math.sin(holo.y)*Math.cos(holo.x),vy=Math.sin(holo.x),vz=Math.cos(holo.y)*Math.cos(holo.x);
 if(holo.ready){const g=holo.gl;if(holoCanvas.width!==width){holoCanvas.width=width;holoCanvas.height=Math.round(width*4/3);}g.viewport(0,0,holoCanvas.width,holoCanvas.height);g.useProgram(holo.program);g.uniform3f(holo.loc.uView,vx,vy,vz);g.uniform1f(holo.loc.uTime,holo.elapsed);g.uniform1f(holo.loc.uDepth,holo.depth);g.uniform1f(holo.loc.uFoil,holo.foil);g.uniform1f(holo.loc.uFinish,holo.finish);g.drawArrays(g.TRIANGLES,0,6);holo.drawn++;}
 else if(holo.failed){const ratio=.1/Math.max(Math.abs(vz),.4),d={background:__DEPTH_BG__,spirit:.10,subject:__DEPTH_SUBJECT__,effects:__DEPTH_EFFECTS__,text:0};holoFallback.querySelectorAll('img').forEach(im=>{const dep=d[im.dataset.layer]*holo.depth;im.style.transform=`translate(${-vx*dep*ratio*100}%,${-vy*dep*ratio*100}%)`;});}
}
function holoApply(){holoTilt.style.transform=`rotateX(${holo.x}rad) rotateY(${holo.y}rad) scale(${holo.zoom})`;holoCard.style.setProperty('--mx',(50-Math.sin(holo.y)*35)+'%');holoCard.style.setProperty('--my',(50+Math.sin(holo.x)*35)+'%');holoRender();}
function holoTick(t){requestAnimationFrame(holoTick);if(!holo.last)holo.last=t;const dt=Math.min(.06,(t-holo.last)/1000);holo.last=t;if(!v8.cardOpen||document.hidden||!currentPersona().ready)return;
 const animated=holo.auto&&!state.reduced&&!holo.drag&&!document.querySelector('dialog[open]');if(animated)holo.elapsed+=dt;
 let tx=holo.tx,ty=holo.ty;if(animated){ty+=Math.sin(holo.elapsed*.72)*.32;tx+=Math.sin(holo.elapsed*.53+1)*.095;}
 const ease=state.reduced||holo.drag?1:1-Math.exp(-dt*10);holo.x+=(tx-holo.x)*ease;holo.y+=(ty-holo.y)*ease;holoApply();}
requestAnimationFrame(holoTick);
function holoSync(){
 holoConstrainAppearance();const staticArt=holoStaticArt();
 $('holoAuto').textContent=holo.auto?'Ⅱ 暂停轻摇':'▷ 自动轻摇';$('holoAuto').setAttribute('aria-pressed',String(holo.auto));$('cardFlip').innerHTML=(v8.flipped?'翻回正面':'翻到背面')+' <span>↻</span>';
 $('holoSettings').hidden=staticArt;$('holoSettings').disabled=staticArt;
 if(staticArt){$('holoSettingsPanel').hidden=true;$('holoSettings').setAttribute('aria-expanded','false');}
 for(const [id,value] of [['holoDepth',holo.depth],['holoFoil',holo.foil]]){$(id).disabled=staticArt;$(id).value=String(value);$(id+'Value').textContent=value.toFixed(2);}
 holoControls.querySelectorAll('[data-finish]').forEach(b=>{b.disabled=staticArt;b.setAttribute('aria-pressed',String(Number(b.dataset.finish)===holo.finish));});
 $('cardSideHint').textContent=staticArt?'拖转查看 · 静态原型，分层尚未完成':'按住拖转 · 滚轮缩放 · 双击归位';
}
function holoReset(){holo.tx=-.045;holo.ty=-.14;holo.zoom=1;holo.elapsed=0;v8.flipped=false;holoCard.classList.remove('flipped');holoSync();}
// Replace all old card handlers. A drag never falls through to click-to-flip.
holoCard.onclick=null;holoCard.setAttribute('role','group');holoCard.removeAttribute('aria-pressed');holoCard.onpointermove=null;holoCard.onpointerleave=null;holoCard.onkeydown=null;
holoCard.onpointerdown=e=>{if(e.button!==0)return;e.preventDefault();holo.auto=false;holoSync();holo.drag={id:e.pointerId,x:e.clientX,y:e.clientY,tx:holo.tx,ty:holo.ty};holoCard.setPointerCapture(e.pointerId);};
holoCard.onpointermove=e=>{const d=holo.drag;if(!d||d.id!==e.pointerId)return;holo.ty=d.ty+(e.clientX-d.x)*.008;holo.tx=clamp(d.tx-(e.clientY-d.y)*.006,-.7,.7);holo.x=holo.tx;holo.y=holo.ty;v8.flipped=Math.cos(holo.y)<0;holoSync();holoApply();};
const release=e=>{if(holo.drag?.id!==e.pointerId)return;holo.drag=null;if(holoCard.hasPointerCapture(e.pointerId))holoCard.releasePointerCapture(e.pointerId);};holoCard.onpointerup=release;holoCard.onpointercancel=release;
holoCard.ondblclick=holoReset;holoCard.addEventListener('wheel',e=>{e.preventDefault();holo.zoom=clamp(holo.zoom-e.deltaY*.0007,.72,1.25);holoApply();},{passive:false});
holoCard.onkeydown=e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Enter',' ','Home'].includes(e.key)){e.preventDefault();e.stopPropagation();holo.auto=false;if(e.key==='Home')holoReset();else if(e.key==='Enter'||e.key===' ')flipIdentity();else if(e.key==='ArrowLeft')holo.ty-=.18;else if(e.key==='ArrowRight')holo.ty+=.18;else holo.tx=clamp(holo.tx+(e.key==='ArrowUp'?.12:-.12),-.7,.7);holoSync();}};
flipIdentity=function(force){const target=typeof force==='boolean'?force:!v8.flipped;v8.flipped=target;holo.ty=target?Math.PI-.14:-.14;holo.tx=-.045;holoCard.classList.remove('flipped');holoCard.setAttribute('aria-pressed',String(target));holoSync();};
setCardTilt=function(){}; // All orientation now has a single source of truth.
$('cardFlip').onclick=()=>flipIdentity();$('holoAuto').onclick=()=>{holo.auto=!holo.auto;holoSync();};$('holoReset').onclick=holoReset;
$('holoSettings').onclick=()=>{if(holoStaticArt())return;const panel=$('holoSettingsPanel');panel.hidden=!panel.hidden;$('holoSettings').setAttribute('aria-expanded',String(!panel.hidden));};
$('holoDepth').oninput=e=>{if(!holoStaticArt())holo.depth=Number(e.target.value);holoSync();holoRender();};$('holoFoil').oninput=e=>{if(!holoStaticArt())holo.foil=Number(e.target.value);holoSync();holoRender();};
holoControls.querySelectorAll('[data-finish]').forEach(b=>b.onclick=()=>{if(!holoStaticArt())holo.finish=Number(b.dataset.finish);holoSync();holoRender();});
const holoOldRefresh=refreshIdentity;
refreshIdentity=function(){holoOldRefresh();holoCard.classList.toggle('holo-generic',!currentPersona().ready);holoSync();if(v8.cardOpen){initHolo();holoRender();}};
const holoOldShow=showIdentityCard;
showIdentityCard=function(){if(v8.cardOpen)return;holoOldShow();holoReset();holo.auto=!state.reduced;holoSync();const d=currentPersona();holoCard.setAttribute('aria-label','SSR '+d.title+'，'+d.name+' 的'+(holoStaticArt()?'静态原型，分层尚未完成':'分层闪卡')+'；按住拖动旋转，方向键调整角度，回车翻面');initHolo();};
const holoOldExport=exportCardBlob;
exportCardBlob=async function(side){if(side!=='front'||!holo.ready||!currentPersona().ready)return holoOldExport(side);holoRender();const cv=document.createElement('canvas');cv.width=1080;cv.height=1440;cv.getContext('2d').drawImage(holoCanvas,0,0,1080,1440);return new Promise((resolve,reject)=>cv.toBlob(b=>b?resolve(b):reject(Error('Export failed')),'image/png'));};
window.__holo={get ready(){return holo.ready},getState:()=>{holoConstrainAppearance();return {x:holo.x,y:holo.y,depth:holo.depth,foil:holo.foil,finish:holo.finish,auto:holo.auto,flipped:v8.flipped,drawn:holo.drawn,webgl:!!holo.gl,fallback:holo.failed,layers:holoStaticArt()?1:5,artMode:currentPersona().art_mode,artStatus:currentPersona().art_status};},setView:(x,y)=>{holo.auto=false;holo.x=holo.tx=x;holo.y=holo.ty=y;holoApply();holoSync();},reset:holoReset,flip:()=>flipIdentity(),render:holoRender};
