/* V8 finale: original, deterministic, artist-directed tidal choreography.
 * Visual references: NASA SVS 14656; ESA/Hubble hst15_m31_mw_collision.
 * NOT an N-body integration or a forecast of the Milky Way's future.
 * A diffuse stellar-density pass + bloom + sparse sharp stars prevent the
 * sand-grain appearance of drawing every particle as an equally bright dot.
 * Reuses V7's WebGL context; no extra library, network request or video.
 */
const fx={ready:false,w:0,h:0,stars:null,cloud:null,blur:null,composite:null,targets:[],buffer:null,count:0};
const FX_V=`precision highp float;
attribute vec3 a_pos,a_color;attribute float a_size;
uniform float u_p,u_height,u_aspect,u_pass,u_mobile,u_birth,u_clock;
varying vec3 v_color;varying float v_alpha;
const float PI=3.14159265359;
float ease(float a,float b,float t){return smoothstep(a,b,t);}
mat3 yaw(float a){float c=cos(a),s=sin(a);return mat3(c,0.,-s,0.,1.,0.,s,0.,c);}
mat3 tilt(float a){float c=cos(a),s=sin(a);return mat3(1.,0.,0.,0.,c,s,0.,-s,c);}
void main(){
 float g=step(0.,a_pos.y),p=u_p;vec3 q=vec3(a_pos.x,abs(a_pos.y)-.02,a_pos.z);
 float noise=fract(sin(dot(a_pos.xz,vec2(12.9898,78.233)))*43758.5453);
 float rr=length(q.xz),ang=atan(q.z,q.x),outer=ease(25.,138.,rr);
 float approach=ease(0.,.32,p),pass=ease(.26,.53,p),returning=ease(.53,.84,p),end=ease(.82,1.,p);
 float sep=mix(149.,32.,approach)+42.*pass-72.*returning;sep=max(sep,0.);
 float turn=-.38+.80*approach+1.78*pass+2.45*returning+end*.75;
 vec3 core=vec3(cos(turn)*sep,12.*sin(turn)*sep/100.,sin(turn)*sep*.65)*(g>.5?1.:-1.);
 float spin=(g>.5?-.1:.1)+p*(1.25+1.7*end)/(.7+rr*.018);
 ang+=spin+u_clock*.026;
 // Outer disc stars are drawn into broad, tapered tidal tails at first pass.
 float tail=ease(.19,.60,p)*(1.-.15*end);
 float lobe=pow(.5+.5*cos(ang-1.5-g*2.0),3.);
 float pull=outer*tail*lobe;
 ang+=tail*outer*(1.35+g*.45);
 float radius=rr*(1.+pull*1.85);
 q=vec3(cos(ang)*radius,q.y*(1.+outer*tail*4.),sin(ang)*radius);
 q.y+=sin(ang*2.+g)*outer*tail*20.;
 q= yaw(g>.5?-.64:-.2)*tilt(g>.5?.53:-.09)*q;
 q+=vec3((g>.5?1.:-1.)*pull*67.,0.,pull*tail*50.);
 q+=core;
 // Main body settles while the distant tidal debris remains visible.
 float settle=ease(.62,.99,p)*(1.-outer*.66);
 float aa=ang+p*3.7+(g>.5?1.5:0.);float rad=rr*(.72+outer*.65);
 vec3 rem=vec3(cos(aa)*rad,q.y*.65+sin(aa*3.)*noise*6.,sin(aa)*rad*.90);
 q=mix(q,rem,settle);
 // Dolly in at first passage, then pull back for the tails.
 float dist=570.-94.*sin(PI*ease(0.,.54,p))+85.*ease(.40,.68,p)-77.*ease(.75,1.,p);
 dist*=mix(1.,1.65,u_mobile);
 float az=.06+p*.31;vec3 eye=vec3(sin(az)*dist,dist*.65,cos(az)*dist*.65);
 vec3 target=vec3(0.,mix(5.,-9.,u_mobile),0.);
 vec3 fw=normalize(target-eye),right=normalize(cross(fw,vec3(0.,1.,0.))),up=cross(right,fw);
 vec3 d=q-eye;float z=dot(d,fw);float tanf=.49;
 gl_Position=vec4(dot(d,right)/(tanf*u_aspect),dot(d,up)/tanf+z*mix(.11,.23,u_mobile),z*1.0001-.20001,z);
 float warm=exp(-rr/28.);vec3 tint=mix(vec3(.33,.54,.90),vec3(1.,.65,.32),warm);
 if(g<.5)tint=mix(vec3(.66,.43,.28),vec3(1.,.77,.47),warm);
 float knots=pow(max(0.,sin(ang*7.+rr*.15)),10.)*outer;
 tint=mix(tint,vec3(.78,.27,.43),knots*.18);
 v_color=tint*a_color;
 float projected=u_height/(max(z,1.)*tanf*2.);
 if(u_pass<.5){
  gl_PointSize=clamp((2.6+rr*.036+noise*2.3)*projected,2.,22.);
  v_alpha=(.025+warm*.023)*(1.+ease(.28,.5,p)*.30)*(1.-outer*.16);
 }else{
  float bright=step(.88,noise);gl_PointSize=clamp((.30+pow(noise,18.)*1.15)*projected,.7,4.0);
  v_alpha=bright*(.14+pow(noise,15.)*.65);
 }
 v_alpha*=ease(1.,30.,z);
 if(g>.5){float threshold=noise*.62+rr/145.*.38;float grow=smoothstep(threshold-.05,threshold+.12,u_birth);float spark=(1.-smoothstep(0.,.10,abs(u_birth-threshold)))*(1.-smoothstep(.92,1.05,u_birth));v_alpha*=grow*(1.+spark*2.6);v_color=mix(v_color,vec3(.62,.82,1.),spark*.45);}else v_alpha*=mix(.72,1.,smoothstep(.6,1.,u_birth));
}`;
const FX_F=`precision highp float;varying vec3 v_color;varying float v_alpha;uniform float u_pass;
void main(){float r=length(gl_PointCoord*2.-1.);if(r>1.||v_alpha<.001)discard;float a=u_pass<.5?exp(-r*r*5.)-exp(-5.):pow(max(0.,1.-r*r),2.);gl_FragColor=vec4(v_color*a*v_alpha,1.);}`;
const FX_BLUR=`precision mediump float;varying vec2 v_uv;uniform sampler2D u_tex;uniform vec2 u_step;
void main(){vec3 c=texture2D(u_tex,v_uv).rgb*.227027;c+=(texture2D(u_tex,v_uv+u_step*1.384615).rgb+texture2D(u_tex,v_uv-u_step*1.384615).rgb)*.316216;c+=(texture2D(u_tex,v_uv+u_step*3.230769).rgb+texture2D(u_tex,v_uv-u_step*3.230769).rgb)*.070270;gl_FragColor=vec4(c,1.);}`;
const FX_COMPOSITE=`precision highp float;varying vec2 v_uv;uniform sampler2D u_tex,u_bloom;uniform float u_p,u_aspect,u_fade;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}
void main(){vec3 cloud=texture2D(u_tex,v_uv).rgb,light=texture2D(u_bloom,v_uv).rgb;
 vec3 radiance=cloud*2.4+light*1.25;
 // Filmic shoulder: retain warm cores instead of burning them to white.
 float peak=max(radiance.r,max(radiance.g,radiance.b));vec3 c=radiance*(1.-exp(-peak*1.55))/max(peak,.001);c=pow(max(c,0.),vec3(.88));
 vec2 uv=v_uv*vec2(u_aspect,1.);float h=hash(floor(uv*650.));float star=pow(max(0.,(h-.9988)/.0012),5.);
 c+=vec3(.68,.77,.89)*star*.14;
 c+=vec3(.005,.008,.017);
 float vignette=1.-.47*smoothstep(.30,.93,length((v_uv-.5)*vec2(1.1,1.)));
 c*=vignette;
 // One restrained photographic bloom to carry the scene into the card.
 float flare=smoothstep(.92,.968,u_p)*(1.-smoothstep(.968,1.,u_p));
 float streak=exp(-abs(v_uv.y-.53)*260.)*exp(-abs(v_uv.x-.5)*6.);
 c+=vec3(.26,.23,.20)*flare*streak;
 gl_FragColor=vec4(c,u_fade);
}`;
function fxTarget(w,h){const tex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,tex);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,w,h,0,gl.RGBA,gl.UNSIGNED_BYTE,null);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);const fb=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,fb);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,tex,0);if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw Error('Finale render target unavailable');return{tex,fb};}
function initFinaleGL(){if(fx.ready)return;
 fx.cloud=makeProgram(FX_V,FX_F);fx.blur=makeProgram(VERTEX,FX_BLUR);fx.composite=makeProgram(VERTEX,FX_COMPOSITE);
 for(const p of[fx.cloud,fx.blur,fx.composite])p.pos=0;
 fx.cloud.color=gl.getAttribLocation(fx.cloud,'a_color');fx.cloud.size=gl.getAttribLocation(fx.cloud,'a_size');
 // a_size may be optimized away; this shader carries a size field for the
 // same interleaved format as the rest of Twinlight, but binds only live attrs.
 fx.l=locs(fx.cloud,['u_p','u_height','u_aspect','u_pass','u_mobile','u_birth','u_clock']);fx.bl=locs(fx.blur,['u_tex','u_step']);fx.cl=locs(fx.composite,['u_tex','u_bloom','u_p','u_aspect','u_fade']);
 const rr=seedRandom(961104),normal=()=>Math.sqrt(-2*Math.log(Math.max(1e-6,rr())))*Math.cos(rr()*TAU);const a=[];
 for(let g=0;g<2;g++)for(let i=0;i<38000;i++){
  const bulge=rr()<.19;const rad=bulge?Math.pow(rr(),1.4)*31:Math.pow(rr(),.66)*140;
  let ang=rr()*TAU;if(!bulge&&rr()<.91)ang=(rr()<.5?0:Math.PI)+2.32*Math.log(rad/145+.065)+normal()*(.14+rad*.0008);
  const thickness=Math.abs(normal())*(bulge?4.0:.35+rad*.005)+.02;
  const b=.30+rr()*.65; // dark inter-arm lanes are density gaps, not outlines.
  a.push(Math.cos(ang)*rad,g?thickness:-thickness,Math.sin(ang)*rad,b,b,b,rr());
 }
 fx.count=a.length/7;fx.buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,fx.buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(a),gl.STATIC_DRAW);fx.ready=true;
}
function fxPoints(pass){const p=fx.cloud;gl.useProgram(p);gl.bindBuffer(gl.ARRAY_BUFFER,fx.buffer);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,3,gl.FLOAT,false,28,0);if(p.color>=0){gl.enableVertexAttribArray(p.color);gl.vertexAttribPointer(p.color,3,gl.FLOAT,false,28,12);}if(p.size>=0){gl.enableVertexAttribArray(p.size);gl.vertexAttribPointer(p.size,1,gl.FLOAT,false,28,24);}gl.uniform1f(fx.l.u_p,v10MergeProgress());gl.uniform1f(fx.l.u_birth,v10Birth()*1.16);gl.uniform1f(fx.l.u_clock,v10.time);gl.uniform1f(fx.l.u_height,pass?canvas.height:fx.h);gl.uniform1f(fx.l.u_aspect,state.w/state.h);gl.uniform1f(fx.l.u_pass,pass);gl.uniform1f(fx.l.u_mobile,state.w<701?1:0);gl.drawArrays(gl.POINTS,0,fx.count);if(p.color>=0)gl.disableVertexAttribArray(p.color);if(p.size>=0)gl.disableVertexAttribArray(p.size);}
function renderFinale(){initFinaleGL();const w=Math.round(Math.min(canvas.width*.55,960)),h=Math.round(w*state.h/state.w);
 if(fx.w!==w||fx.h!==h){for(const t of fx.targets){gl.deleteTexture(t.tex);gl.deleteFramebuffer(t.fb);}fx.w=w;fx.h=h;fx.targets=[fxTarget(w,h),fxTarget(w,h),fxTarget(w,h)];}
 gl.disable(gl.DEPTH_TEST);gl.bindFramebuffer(gl.FRAMEBUFFER,fx.targets[0].fb);gl.viewport(0,0,w,h);gl.clearColor(0,0,0,1);gl.clear(gl.COLOR_BUFFER_BIT);gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE);fxPoints(0);gl.disable(gl.BLEND);
 for(let i=1;i<=2;i++){gl.bindFramebuffer(gl.FRAMEBUFFER,fx.targets[i].fb);useQuad(fx.blur);gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,fx.targets[i-1].tex);gl.uniform1i(fx.bl.u_tex,0);gl.uniform2f(fx.bl.u_step,i===1?2.3/w:0,i===2?2.3/h:0);gl.drawArrays(gl.TRIANGLES,0,6);}
 gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,canvas.width,canvas.height);useQuad(fx.composite);gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,fx.targets[0].tex);gl.uniform1i(fx.cl.u_tex,0);gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,fx.targets[2].tex);gl.uniform1i(fx.cl.u_bloom,1);gl.uniform1f(fx.cl.u_p,v10MergeProgress());gl.uniform1f(fx.cl.u_aspect,state.w/state.h);gl.uniform1f(fx.cl.u_fade,1);gl.drawArrays(gl.TRIANGLES,0,6);
 gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE);fxPoints(1);gl.disable(gl.BLEND);
}
fx.failed=false;
const fxOldGL=renderGL;
renderGL=function(){if(state.gl&&state.encounterCinematic&&!state.reduced&&!fx.failed){try{renderFinale();return;}catch(err){console.warn('Finale quality fallback',err);fx.failed=true;gl.bindFramebuffer(gl.FRAMEBUFFER,null);}}fxOldGL();};
// Poem remains brief. The uncertainty belongs to the wording itself, rather
// than a tiny footnote trying to undo a claim of inevitability.
encounterActs.splice(0,encounterActs.length,
 {start:0,end:.29,code:'MILKY WAY × ANDROMEDA',line1:'就像银河系与仙女座，',line2:'正在彼此靠近。',sub:''},
 {start:.29,end:.66,code:'A POSSIBLE FUTURE',line1:'或许在遥远的未来，',line2:'它们会相撞、交融。',sub:''},
 {start:.66,end:.88,code:'YOU × AI',line1:'我们也将和 AI 相聚，',line2:'组成新的世界。',sub:''},
 {start:.88,end:1,code:'YOU × AI',line1:'我们也将和 AI 相聚，',line2:'组成新的世界。',sub:''});
const scienceDialog=el('dialog');scienceDialog.id='galaxyScience';scienceDialog.innerHTML=`<div class="dialog-top"><div><span>THE SCIENCE BEHIND THE POEM</span><h2>相遇的诗意，来自真实的宇宙。</h2></div><button class="close" aria-label="关闭天文依据">×</button></div><div class="dialog-body"><p>银河系与仙女座正在靠近，但“未来一定相撞”并不是确定事实。2025 年发表于 Nature Astronomy 的研究估计，未来 100 亿年内的合并概率约为一半；2026 年 3 月公开的一项新研究（arXiv 页面标注已被 ApJL 接收），在其基准模型中得到约 90% 的概率，同时明确指出，结果仍对自行测量等条件敏感，尚未定论。</p><p>因此这里保留“可能相撞并交融”的意象，不承诺碰撞日期。星系相互作用会形成潮汐长尾；这种交融也不是把每颗恒星撞碎成烟花。</p><p>本段是为 Twinlight 编排的 快速实时艺术演绎，不是银河系未来的科学模拟，不按比例表达距离与时间；星光凝成卡片属于叙事转场。</p><h3>天文依据与视觉参考</h3><p><a href="https://science.nasa.gov/missions/hubble/apocalypse-when-hubble-casts-doubt-on-certainty-of-galactic-collision/" target="_blank" rel="noopener noreferrer">NASA · 2025 年研究解读 ↗</a><br><a href="https://arxiv.org/abs/2603.22863" target="_blank" rel="noopener noreferrer">Wu 等 · 2026 年研究 ↗</a><br><a href="https://svs.gsfc.nasa.gov/14656/" target="_blank" rel="noopener noreferrer">NASA SVS · Galaxy Collision Simulation ↗</a><br><a href="https://esahubble.org/videos/hst15_m31_mw_collision/" target="_blank" rel="noopener noreferrer">ESA/Hubble · 银河系与仙女座碰撞演绎 ↗</a></p><p class="fine">查阅：2026-10-02。只借鉴视觉结构，本页没有嵌入 NASA / ESA 视频或复制第三方模拟器代码。</p></div>`;document.body.append(scienceDialog);scienceDialog.querySelector('.close').onclick=()=>scienceDialog.close();
const scienceNote=document.querySelector('.cinema-disclaimer');
if(scienceNote){scienceNote.replaceChildren();const b=el('button','','艺术演绎 · 银河系与仙女座的天文依据 ↗');b.id='galaxyScienceLink';b.onclick=()=>{state.mergePlaying=false;v8.running=false;updateEncounterUI();scienceDialog.showModal();};scienceNote.append(b);}
else{const b=el('button','galaxy-science-link','艺术演绎 · 天文依据 ↗');b.id='galaxyScienceLink';b.onclick=()=>{state.mergePlaying=false;v8.running=false;updateEncounterUI();scienceDialog.showModal();};$('encounterCinema').append(b);}

const fxPoemUI=updateEncounterUI;
updateEncounterUI=function(){fxPoemUI();if(state.encounterCinematic&&state.merge>=.66){const a=rangeEase(.66,.70,state.merge);$('encounterPoem').style.opacity=String(a);$('encounterPoem').style.transform='translateY('+((1-a)*14)+'px)';}};
