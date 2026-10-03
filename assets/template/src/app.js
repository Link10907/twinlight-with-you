'use strict';
/*
 * TWINLIGHT / TWO GALAXIES EDITION 6.0
 * Original procedural texture and WebGL shaders. All assets are embedded.
 * No networking, telemetry, cookies, storage, model calls or history access.
 * Artistic, non-physical coordinate system. GPU points are not message counts.
 */
const $=id=>document.getElementById(id);
const DEFAULT_PROFILE=JSON.parse($('journeyData').textContent);
let profile=structuredClone(DEFAULT_PROFILE);
const TEX='__TEXTURE__';
const SURFACE='__SURFACE__';
const TAU=Math.PI*2;
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const mix=(a,b,t)=>a+(b-a)*t;
const smooth=t=>t*t*(3-2*t);
const smoother=t=>t*t*t*(t*(t*6-15)+10);
const add=(a,b)=>[a[0]+b[0],a[1]+b[1],a[2]+b[2]];
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const mul=(a,k)=>[a[0]*k,a[1]*k,a[2]*k];
const lerp=(a,b,t)=>a.map((v,i)=>mix(v,b[i],t));
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const len=a=>Math.hypot(...a);
const norm=a=>mul(a,1/(len(a)||1));
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const nodes=DEFAULT_PROFILE.layout.stars.map(s=>s.position.slice());
const localNodes=nodes.map(p=>p.slice());
const colors=DEFAULT_PROFILE.layout.stars.map(s=>s.color.slice());
const planets=nodes.map((p,i)=>add(p,[9,-4,10]));
const prefers=matchMedia('(prefers-reduced-motion: reduce)');
const state={active:-1,from:-1,flight:null,elapsed:0,auto:false,dwell:0,hover:false,focus:false,clean:false,reduced:prefers.matches,sound:false,quality:'auto',w:innerWidth,h:innerHeight,time:0,delta:0,cam:[0,170,250],target:[-34,0,0],fov:48,bank:0,mouse:[0,0],parallax:[0,0],drag:[0,0],ready:false,gl:true,frame:0,idle:0,frameEMA:16.7,monitor:false,reading:'letter',topic:-1,topicHover:-1,hoveredStar:-1,localOffset:[0,0],localGoal:[0,0]};
let labels=[],lastFrame=0,toastTimer,gl,program,pointsProgram,quad,pointBuffer,pointCount=0,locations={},pointLoc={},audio=null,pendingProfile=null;
let routePositions=[],previousProjections=[];
let R=[1,0,0],U=[0,1,0],F=[0,0,-1];
const canvas=$('cosmos'), trails=$('trails'), ctx=trails.getContext('2d');
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function toast(text){$('toast').textContent=text;$('toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('show'),4300);}
function seedRandom(seed){return()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
const rand=seedRandom(270911),gauss=()=>Math.sqrt(-2*Math.log(Math.max(.0001,rand())))*Math.cos(TAU*rand());
function createNav(){
 $('userName').textContent=profile.name.toUpperCase();$('introText').textContent=profile.intro;document.title=profile.name+' 的星系 · 同光 TWINLIGHT';
 $('chapterNav').replaceChildren();$('starLabels').replaceChildren();$('indexList').replaceChildren();labels=[];
 profile.chapters.forEach((c,i)=>{
  const n=String(i+1).padStart(2,'0');
  const b=el('button','chapter-link');b.append(el('small','',n));const title=el('span');title.append(el('strong','',c.label),el('em','',c.english));b.append(title);b.setAttribute('aria-label','飞往第'+(i+1)+'站：'+c.label);b.onclick=()=>{setAuto(false);navigate(i);};$('chapterNav').append(b);
  const s=el('button','star-label');s.title='飞往'+c.label;s.setAttribute('aria-label','飞往'+c.label);const st=el('span');st.append(el('small','',n+' / '+c.english),el('strong','',c.label),el('p','',c.period));st.append(el('div','visit-hint','点击，飞往这段时光 ↗'));s.append(st);s.style.setProperty('--star',colors[i].map(x=>Math.round(x*255)).join(','));s.onpointerenter=s.onfocus=()=>{state.hoveredStar=i;s.classList.add('hot');};s.onpointerleave=s.onblur=()=>{if(state.hoveredStar===i)state.hoveredStar=-1;s.classList.remove('hot');};s.onclick=()=>{setAuto(false);navigate(i);};$('starLabels').append(s);labels.push(s);
  const ix=el('button','index-link');ix.append(el('span','',n));const it=el('div');it.append(el('strong','',c.label),el('small','',c.period));ix.append(it);ix.onclick=()=>{$('indexDialog').close();setAuto(false);navigate(i);};$('indexList').append(ix);
 });
 updateNav();
}
let topicButtons=[],topicPositions=[];
function figureQuote(q){const f=el('figure','memory-quote');f.append(el('blockquote','',q.text),el('figcaption','',(q.date||'日期未确认')+' · '+(q.source.includes('回忆')?'你在后来回望时说':'你留下的一句话')));return f;}
function traceLabel(t){if(t&&t.model_id&&t.status==='message_metadata')return {name:t.model_id,tag:'导入记录标注 · 网页未独立核验'};if(t&&t.reported_name&&t.status==='self_report')return {name:t.reported_name,tag:'用户自述 · 不是消息级校验'};return {name:'具体模型未确认',tag:t?.status==='product_only'?'仅有产品信息':'尚无消息级型号记录'};}
function fillReader(i){state.topic=-1;state.localGoal=[0,0];fillLetter(i);makeTopicLabels(i);}
function fillLetter(i,topic=-1){
 const c=profile.chapters[i],t=topic>=0?(c.topics||[])[topic]:null;
 $('chapterNumber').textContent=String(i+1).padStart(2,'0')+' / '+String(profile.chapters.length).padStart(2,'0')+' · '+c.label;$('chapterPeriod').textContent=c.period;$('chapterEnglish').textContent=c.english;
 $('chapterTitle').textContent=t?t.name:c.label;$('chapterHeadline').textContent=t?t.title:c.headline;$('letterOverline').textContent=t?'那片星空里的回声':'写给那时的你';$('backChapter').hidden=!t;
 const letter=$('chapterLetter');letter.replaceChildren();const qs=t?(t.quote?[t.quote]:[]):(c.quotes||[]),paragraphs=t?t.body:c.story;
 paragraphs.forEach((txt,j)=>{letter.append(el('p','',txt));if(j===1&&qs[0])letter.append(figureQuote(qs[0]));});
 if(paragraphs.length<2&&qs[0])letter.append(figureQuote(qs[0]));if(qs[1]){letter.append(el('p','','后来，另一句话把视野带向更远处：'));letter.append(figureQuote(qs[1]));}
 $('chapterReflection').textContent=t?'每一颗星，不必是一个称号。它也可以只是你认真想过的一个问题。':c.reflection;
 $('letterClosing').textContent=t?'— '+c.label+'，还有更多微光。':(c.letterClosing||'给仍在路上的你。');
 $('collaboration').textContent=c.collaboration||'你留下问题，我们把它重新连成星光。';const tr=traceLabel(c.ai_trace);$('modelTrace').replaceChildren(el('span','','本章实际模型 · '),el('strong','',tr.name),el('br'),el('span','',tr.tag));
 const ee=$('eraEcho');ee.replaceChildren();ee.className='era-echo';for(const id of c.ai_context_ids||[]){const e=(profile.ai_history||[]).find(e=>e.id===id);if(!e)continue;const chip=el('span','era-chip');chip.append(el('span','',e.name),el('small','','发布史背景'));ee.append(chip);}
 $('chapterTopics').replaceChildren();(c.topics||[]).forEach((item,j)=>{const b=el('button',topic===j?'active':'',item.name);b.onclick=()=>selectTopic(j);$('chapterTopics').append(b);});
 const sources=$('chapterSources');sources.replaceChildren();for(const q of qs){const d=el('div','source-entry');d.append(el('blockquote','',q.text),el('div','',(q.date||'日期未确认')+' · '+q.source));sources.append(d);}if(!qs.length)sources.append(el('p','','原始引用保存在本地审查稿；这里展示所选记录的转述，不公开聊天原文。'));
 $('nextLabel').textContent=i===profile.chapters.length-1?'回望整片星空':'飞往下一束光';$('nextHint').textContent=i===profile.chapters.length-1?'故事仍在继续':'下一站 · '+profile.chapters[i+1].label;
 $('prev').setAttribute('aria-label',i===0?'返回星系全景':'飞往上一站 '+profile.chapters[i-1].label);
 $('captionEnglish').textContent=c.english;$('captionTitle').textContent=c.label;$('captionSignature').textContent=c.signature;$('captionMaterial').textContent=starTypes[i];$('captionMaterialCode').textContent=planetCaption[i];
 $('readerScroll').scrollTop=0;$('clusterName').textContent=c.label;requestAnimationFrame(updateReadCue);
 document.documentElement.style.setProperty('--accent','rgb('+colors[i].map(x=>Math.round(x*255)).join(',')+')');
 topicButtons.forEach((b,j)=>b.classList.toggle('active',j===topic));
}
function makeTopicLabels(i){$('topicLabels').replaceChildren();topicButtons=[];state.topicHover=-1;if(i<0){$('clusterTitle').hidden=true;return;}$('clusterTitle').hidden=false;
 (profile.chapters[i].topics||[]).forEach((t,j)=>{const b=el('button','topic-star');const label=el('span','',t.name);label.append(el('small','','打开这颗微光'));b.append(label);b.setAttribute('aria-label','探索 '+t.name+'：'+t.title);b.onclick=()=>selectTopic(j);b.onpointerenter=b.onfocus=()=>state.topicHover=j;b.onpointerleave=b.onblur=()=>state.topicHover=-1;$('topicLabels').append(b);topicButtons.push(b);});
 cacheTopicPositions();updateTopicLabels();
}
function safePublicURL(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password?u.href:null;}catch(e){return null;}}
function renderAITimeline(){
 const usage=$('usageTimeline');usage.replaceChildren();const records=profile.ai_usage||[];if(!records.length)usage.append(el('p','','还没有提供可说明来源的模型使用记录。空白会被保留。'));
 for(const r of records){const d=el('article','model-entry actual');d.append(el('div','date',r.date||'日期未确认'));const h=el('h4','',r.status==='message_metadata'&&r.model_id?r.model_id:r.status==='self_report'&&r.reported_name?r.reported_name:r.product);h.append(el('small','',r.status==='message_metadata'?'导入元数据标注':r.status==='self_report'?'用户自述':'仅产品线索'));d.append(h);if(r.evidence)d.append(el('blockquote','','“'+r.evidence+'”'));d.append(el('p','',r.note||'本页无法独立核验原始消息的型号。'));usage.append(d);}
 const timeline=$('modelTimeline');timeline.replaceChildren();for(const e of profile.ai_history||[]){const d=el('article','model-entry');d.append(el('div','date',e.date+' · 公开发布事件'));const h=el('h4','',e.name);h.append(el('small','',e.kind==='product'?'产品 · 非模型 ID':'模型发布'));d.append(h,el('p','',e.title),el('p','',e.summary));const url=safePublicURL(e.url);if(url){const a=el('a','',defaultEvent(e)?'官方发布页 ↗':'导入文件附带的来源 ↗');a.href=url;a.target='_blank';a.rel='noopener noreferrer';d.append(a);}timeline.append(d);}}
function openAIHistory(){setAuto(false);renderAITimeline();$('aiDialog').showModal();}
// Arc length lookup: uniform distance progression along the same curved path.
function makeArc(f){const lut=[0];let last=f.start,sum=0;for(let i=1;i<=160;i++){const p=bezier(f.start,f.cp1,f.cp2,f.end,i/160);sum+=len(sub(p,last));lut.push(sum);last=p;}return lut.map(x=>x/(sum||1));}
function arcT(lut,d){let lo=0,hi=lut.length-1;while(hi-lo>1){const m=(lo+hi)>>1;if(lut[m]<d)lo=m;else hi=m;}return (lo+(d-lut[lo])/(lut[hi]-lut[lo]||1))/(lut.length-1);}
function slerpDir(a,b,t){const c=clamp(dot(a,b),-.99999,.99999),angle=Math.acos(c);if(angle<.01)return norm(lerp(a,b,t));const den=Math.sin(angle);return add(mul(a,Math.sin((1-t)*angle)/den),mul(b,Math.sin(t*angle)/den));}
function bezier(a,b,c,d,t){let q=1-t;return [0,1,2].map(i=>q*q*q*a[i]+3*q*q*t*b[i]+3*q*t*t*c[i]+t*t*t*d[i]);}
function setAuto(on){state.auto=on;state.dwell=0;$('autoBtn').setAttribute('aria-pressed',String(on));$('autoIcon').textContent=on?'Ⅱ':'▷';$('autoLabel').textContent=on?'暂停漫游':'自动漫游';updateNav();if(on&&state.active<0&&!state.flight)navigate(0);}
function toggleClean(force){state.clean=typeof force==='boolean'?force:!state.clean;document.body.classList.toggle('clean',state.clean);$('restore').hidden=!state.clean;}
function updateReadCue(){const r=$('readerScroll');$('reader').classList.toggle('has-more',r.scrollHeight-r.scrollTop-r.clientHeight>18);}
$('readerScroll').addEventListener('scroll',updateReadCue);
function updateMotion(){const b=$('motionBtn');b.setAttribute('aria-pressed',String(state.reduced));b.querySelector('span').textContent=state.reduced?'减少运动':'完整转场';}
function getAudio(){if(!audio)audio=new (window.AudioContext||window.webkitAudioContext)();if(audio.state==='suspended')audio.resume().catch(()=>{});return audio;}
function playFlightSound(){if(!state.sound||state.reduced)return;try{const a=getAudio(),t=a.currentTime,d=3.8;const buffer=a.createBuffer(1,Math.floor(a.sampleRate*d),a.sampleRate),data=buffer.getChannelData(0);let r=seedRandom(34);for(let i=0;i<data.length;i++)data[i]=(r()*2-1)*.18;const src=a.createBufferSource();src.buffer=buffer;const filter=a.createBiquadFilter();filter.type='lowpass';filter.frequency.setValueAtTime(150,t);filter.frequency.exponentialRampToValueAtTime(1800,t+1.7);filter.frequency.exponentialRampToValueAtTime(110,t+d);const gain=a.createGain();gain.gain.setValueAtTime(0,t);gain.gain.linearRampToValueAtTime(.17,t+.9);gain.gain.linearRampToValueAtTime(0,t+d);src.connect(filter).connect(gain).connect(a.destination);src.start();}catch(e){state.sound=false;}}
function playArrivalSound(){if(!state.sound)return;try{const a=getAudio(),t=a.currentTime;[261.63,392,523.25].forEach((f,i)=>{const o=a.createOscillator(),g=a.createGain();o.type='sine';o.frequency.value=f;g.gain.setValueAtTime(0,t+i*.11);g.gain.linearRampToValueAtTime(.012,t+i*.11+.03);g.gain.exponentialRampToValueAtTime(.00001,t+1.5+i*.11);o.connect(g).connect(a.destination);o.start(t+i*.11);o.stop(t+1.9);});}catch(e){}}
__RENDER__
function resizeBuffers(){
 const dpr=Math.min(devicePixelRatio||1,state.quality==='high'?2:1.5);
 const cap=state.quality==='high'?3400000:state.quality==='balanced'?1350000:autoLevel>0?1600000:2600000;
 pixelScale=Math.min(dpr,Math.sqrt(cap/(state.w*state.h)));
 if(state.quality==='balanced')pixelScale=Math.min(pixelScale,1);
 canvas.width=Math.round(state.w*pixelScale);canvas.height=Math.round(state.h*pixelScale);
 const overlayScale=Math.min(devicePixelRatio||1,1.5);trails.width=Math.round(state.w*overlayScale);trails.height=Math.round(state.h*overlayScale);ctx.setTransform(overlayScale,0,0,overlayScale,0,0);
}
let testing=false;
function loop(t){if(!lastFrame)lastFrame=t;const dt=(t-lastFrame)/1000;lastFrame=t;if(!document.hidden&&!testing&&state.ready){
 if(dt>0)state.frameEMA=mix(state.frameEMA,Math.min(dt*1000,2000),.1);
 if(state.quality==='auto'&&state.frame>35&&state.frameEMA>28&&autoLevel===0){autoLevel=1;resizeBuffers();}
 tick(dt);}requestAnimationFrame(loop);}
function configureFallback(error){state.gl=false;canvas.style.backgroundImage='url('+TEX+')';canvas.style.backgroundPosition='65% 50%';canvas.style.backgroundSize='cover';console.warn('WebGL fallback:',error);toast('当前环境无法启动 WebGL。已显示静态星图，章节仍可阅读。');state.reduced=true;updateMotion();}
function showInfo(){setAuto(false);$('infoDialog').showModal();}
$('begin').onclick=()=>{setAuto(false);navigate(0);};$('film').onclick=()=>{setAuto(true);};$('autoBtn').onclick=()=>{setAuto(!state.auto);};$('home').onclick=$('navMap').onclick=$('overviewBtn').onclick=()=>{setAuto(false);navigate(-1);};$('navIndex').onclick=()=>{$('indexDialog').showModal();};$('navAbout').onclick=$('infoBtn').onclick=showInfo;
$('next').onclick=()=>{setAuto(false);navigate(state.active===profile.chapters.length-1?-1:state.active+1);};$('prev').onclick=()=>{setAuto(false);navigate(state.active-1);};$('skip').onclick=finishFlight;
$('motionBtn').onclick=()=>{state.reduced=!state.reduced;if(state.flight)finishFlight();updateMotion();toast(state.reduced?'已减少运动，章节之间使用柔和过渡。':'已开启完整航行与镜头推进。');};
$('soundBtn').onclick=()=>{state.sound=!state.sound;$('soundBtn').setAttribute('aria-pressed',String(state.sound));$('soundBtn').querySelector('span').textContent=state.sound?'音效开':'音效关';if(state.sound)playArrivalSound();else if(audio)audio.suspend().catch(()=>{});};
$('qualityBtn').onclick=()=>{const modes=['auto','high','balanced'];state.quality=modes[(modes.indexOf(state.quality)+1)%3];$('qualityBtn').querySelector('span').textContent=({auto:'自动画质',high:'锐利优先',balanced:'流畅优先'})[state.quality];autoLevel=0;resizeBuffers();};
$('fullBtn').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(e){toast('当前浏览器不支持全屏，可使用浏览器自己的全屏模式。');}};
$('restore').onclick=()=>toggleClean(false);
$('reader').addEventListener('pointerenter',()=>state.hover=true);$('reader').addEventListener('pointerleave',()=>state.hover=false);$('reader').addEventListener('focusin',()=>state.focus=true);$('reader').addEventListener('focusout',()=>setTimeout(()=>{state.focus=$('reader').contains(document.activeElement);},0));
for(const dlg of document.querySelectorAll('dialog')){dlg.querySelector('.close').onclick=()=>dlg.close();dlg.addEventListener('click',e=>{if(e.target===dlg){const r=dlg.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dlg.close();}});}
window.addEventListener('resize',resize);document.addEventListener('visibilitychange',()=>{lastFrame=0;if(audio&&document.hidden)audio.suspend().catch(()=>{});else if(audio&&state.sound)audio.resume().catch(()=>{});});
prefers.addEventListener('change',e=>{state.reduced=e.matches;updateMotion();if(state.flight)finishFlight();});
canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();state.gl=false;state.reduced=true;updateMotion();toast('图形上下文中断，已切换阅读模式。重新加载页面可重试。');});
function downloadJSON(){const data=JSON.stringify(profile,null,2);const u=URL.createObjectURL(new Blob([data],{type:'application/json'})),a=el('a');a.href=u;a.download='my-ai-journey.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1000);}
function validateProfile(x){
 if(!x||typeof x!=='object'||Array.isArray(x))throw Error('文件须为一个 JSON 对象。');
 const text=(s,n,required=true)=>{if(typeof s!=='string'||s.length>n||(required&&!s.trim()))throw Error('文字字段缺失或过长，请按示例格式修改。');return s.trim();};
 const arr=(a,max)=>{if(!Array.isArray(a)||a.length>max)throw Error('列表字段不符合示例格式。');return a;};
 const list=(a,max,n)=>arr(a,max).map(v=>text(v,n));
 const quote=q=>q?{label:text(q.label||'你曾这样说',40),text:text(q.text,600),date:q.date?text(q.date,40):null,source:text(q.source||'用户导入，来源未独立核验',240)}:null;
 const status=v=>['unknown','self_report','product_only','message_metadata'].includes(v)?v:'unknown';
 if(!Array.isArray(x.chapters)||x.chapters.length<1||x.chapters.length>8)throw Error('需要 1–8 个有证据的主题，不能为了数量编造经历。');
 const clean={version:'6.0',name:text(x.name,40),intro:text(x.intro||x.introduction,400),chapters:x.chapters.map((c,i)=>{
 const tags=list(c.tags||[],5,32),topics=c.topics?arr(c.topics,8).map(t=>({id:text(t.id||t.name,64),name:text(t.name,32),title:text(t.title||t.name,280),body:list(t.body||['暂未提供更细的主题叙事。'],4,900),quote:quote(t.quote),provenance:text(t.provenance||'用户提供的主题叙事',240)})):tags.slice(0,4).map(n=>({name:n,title:n,body:['此主题由导入文件提供，尚无详细叙事。'],quote:null}));
 const t=c.ai_trace||{};return {companion_year:Number.isInteger(c.companion_year)&&c.companion_year>=2022&&c.companion_year<=2100?c.companion_year:null,id:text(c.id||'chapter_'+i,64),label:text(c.label,14),english:text(c.english,40),period:text(c.period||'一段成长经历',80),headline:text(c.headline||c.label,280),story:list(c.story||[c.description],5,1000),reflection:text(c.reflection||'这段经历，由你自己定义。',800),changes:[],tags,transition:text(c.transition||'带着来路，继续出发。',180),signature:text(c.signature||'故事还在继续。',280),quotes:arr(c.quotes||[],2).map(quote),topics,letterClosing:text(c.letterClosing||'给仍在路上的你。',150),collaboration:text(c.collaboration||'每次提问，都是一小步。',200),ai_context_ids:list(c.ai_context_ids||[],5,40),ai_trace:{product:text(t.product||'未确认',80),model_id:t.model_id?text(t.model_id,100):null,reported_name:t.reported_name?text(t.reported_name,80):null,status:status(t.status),source:text(t.source||'未提供消息元数据',240),note:text(t.note||'不按日期推断型号。',350)}};
 })};
 clean.ai_history=arr(x.ai_history||[],60).map(e=>({id:text(e.id,40),date:text(e.date,30),name:text(e.name,100),provider:(()=>{const v=e.provider||(['anthropic','google','deepseek','qwen'].find(d=>(e.url||'').includes(d))||'openai');const aliases={anthropic:'Anthropic',google:'Google',deepseek:'DeepSeek',qwen:'Qwen',openai:'OpenAI'};const n=aliases[v]||v;if(!['OpenAI','Anthropic','Google','DeepSeek','Qwen'].includes(n))throw Error('当前原型尚不支持这个模型来源：'+n);return n;})(),kind:e.kind==='product'?'product':'model',title:text(e.title||e.name,180),summary:text(e.summary||'用户导入的事件，尚未核验。',600),url:safePublicURL(e.url)||''}));
 clean.ai_history.sort((a,b)=>a.date.localeCompare(b.date));
 clean.ai_usage=arr(x.ai_usage||[],30).map(r=>({date:r.date?text(r.date,40):null,product:text(r.product||'未确认',100),reported_name:r.reported_name?text(r.reported_name,100):null,model_id:r.model_id?text(r.model_id,100):null,status:status(r.status),evidence:text(r.evidence||'未附原始证据',700),note:text(r.note||'网页未独立核验，分享前请检查。',500)}));
 if(Object.prototype.hasOwnProperty.call(x,'summary_meta')){
  const m=x.summary_meta;
  if(m!==null&&(typeof m!=='object'||Array.isArray(m)))throw Error('summary_meta 必须是对象或 null。');
  clean.summary_meta=m===null?null:{provider:m.provider?text(m.provider,40):null,display_name:m.display_name?text(m.display_name,24):null,model:m.model?text(m.model,100):null,generated_at:m.generated_at?text(m.generated_at,40):null,attribution_source:m.attribution_source?text(m.attribution_source,240):'user_provided_metadata'};
 }else if(x.source&&typeof x.source.assistant==='string'){
  const nm=text(x.source.assistant,24);const providers={ChatGPT:'openai',GPT:'openai',Claude:'anthropic',Gemini:'google',DeepSeek:'deepseek',Kimi:'moonshot',Qwen:'qwen',Doubao:'bytedance'};
  clean.summary_meta={provider:providers[nm]||null,display_name:nm,model:null,generated_at:null,attribution_source:'legacy source.assistant'};
 }else clean.summary_meta=null;
 return clean;
}
$('backChapter').onclick=()=>{state.topic=-1;state.localGoal=[0,0];fillLetter(state.active);};$('navAI').onclick=$('footerAI').onclick=$('readerAI').onclick=openAIHistory;
$('exportJson').onclick=downloadJSON;
$('importJson').onchange=async e=>{pendingProfile=null;$('importReview').hidden=true;$('importError').textContent='';$('reviewCheck').checked=false;$('applyJson').disabled=true;const file=e.target.files[0];if(!file)return;try{if(file.size>524288)throw Error('文件超过 512 KB，请使用脱敏后的成长摘要，而不是原始聊天记录。');const raw=await file.text();pendingProfile=validateProfile(JSON.parse(raw));$('jsonPreview').textContent=JSON.stringify(pendingProfile,null,2);$('importReview').hidden=false;$('importReview').scrollIntoView({behavior:'smooth',block:'start'});}catch(err){$('importError').textContent=err instanceof SyntaxError?'JSON 无法解析，请检查文件格式。':err.message;}};
$('reviewCheck').onchange=e=>$('applyJson').disabled=!e.target.checked;
$('applyJson').onclick=()=>{if(!pendingProfile||!$('reviewCheck').checked)return;setAuto(false);profile=pendingProfile;pendingProfile=null;state.flight=null;document.body.classList.remove('flying');$('flightControls').hidden=true;state.active=-1;state.topic=-1;state.localGoal=[0,0];state.localOffset=[0,0];$('reader').hidden=true;$('reader').classList.remove('visible');$('starCaption').hidden=true;$('welcome').hidden=false;document.body.dataset.view='overview';makeTopicLabels(-1);createNav();rebuildAINodes();showWorld('overview',true);resize();$('infoDialog').close();toast('已在本机替换旅程。未上传，也没有自动保存。');};
__CONTROLS__
__V6__
__V7__
__V8__
__FINALE__
__V9__
__HOLO__
__V10__
__ADAPTER__
async function start(){
 createNav();rebuildAINodes();updateMotion();resize();try{await initWebGL();}catch(e){configureFallback(e);}
 state.ready=true;showWorld('overview',true);resize();basis();renderGL();drawOverlay();updateLabels();$('loading').classList.add('finished');setTimeout(()=>$('loading').hidden=true,1100);requestAnimationFrame(loop);
 // Deterministic inspection hooks; only callable locally, never make requests.
 window.galaxyDebug={getState:()=>({mode:state.mode,active:state.active,event:state.aiEvent,flight:state.flight?{to:state.flight.index,event:state.flight.event,t:state.flight.t}:null,cam:[...state.cam],target:[...state.target],fov:state.fov,webgl:state.gl,frames:state.frame,particles:pointCount,auto:state.auto,quality:state.quality,merge:state.merge,radius:orbit.radius,yaw:orbit.yaw,pitch:orbit.pitch,stellarDetail:nodes.map((n,i)=>starDetail(i)),time:state.time,aiEvents:profile.ai_history.length}),go:n=>navigate(n),world:showWorld,ai:n=>navigateAI(n),freeze:()=>{testing=true;},resume:()=>{testing=false;lastFrame=0;},step:seconds=>{testing=true;let n=Math.ceil(seconds/.02);for(let i=0;i<n;i++)tick(Math.min(.02,seconds-i*.02),false);paint();if(gl&&state.gl)gl.finish();},finish:()=>{finishFlight();tick(0);if(gl&&state.gl)gl.finish();},sample:t=>{testing=true;if(state.flight)state.flight.t=t;tick(0);if(gl&&state.gl)gl.finish();},clean:toggleClean,selectTopic,setTime:t=>{state.time=t;updateWorld();paint();if(gl&&state.gl)gl.finish();},refresh:()=>{paint();if(gl&&state.gl)gl.finish();},setMerge:m=>{state.merge=state.mergeGoal=m;state.mergePlaying=false;updateWorld();tick(0);},dolly,companion:showCompanion,encounter,topic:n=>{const s=personalSatellites[n];navigateTopic(s.i,s.j);},satellites:()=>personalSatellites.map(s=>({name:s.name,chapter:s.i,topic:s.j,projected:project(worldPoint(s.p))}))};
}
start();
