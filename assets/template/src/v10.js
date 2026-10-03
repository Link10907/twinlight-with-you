/* V10 narrative: identify AI, illuminate its history, merge, ask, reveal.
 * Summarizer attribution comes from exported metadata, NEVER a selector or
 * guesses based on which model names occur in someone's history.
 */
const v10={time:0,duration:14,anchor:0,base:0,playing:false,phase:'home',birth:0,question:false,trigger:null,musicChosen:false};
// Attribution describes the author of THIS summary, never the models mentioned
// in the user's history. Missing metadata does not silently become GPT or AI.
function summarizerInfo(){
 const m=profile.summary_meta;
 if(!m||typeof m!=='object')return {provider:null,name:null,model:null};
 const provider=String(m.provider||'').trim().toLowerCase();
 const names={openai:'GPT',anthropic:'Claude',google:'Gemini',deepseek:'DeepSeek',qwen:'Qwen',moonshot:'Kimi',bytedance:'豆包'};
 const display=typeof m.display_name==='string'?m.display_name.trim().slice(0,24):'';
 const aliases={gpt:'GPT',chatgpt:'GPT',claude:'Claude',gemini:'Gemini',deepseek:'DeepSeek',kimi:'Kimi',qwen:'Qwen',doubao:'豆包'};
 const displayName=aliases[display.toLowerCase()]||display;
 const name=names[provider]||(!['','AI','这个 AI','人工智能','Other','unknown'].includes(displayName)?displayName:null);
 return {provider:provider||null,name,model:typeof m.model==='string'?m.model.slice(0,80):null};
}
const bornCaption=el('div','v10-born-caption');bornCaption.innerHTML='<small>THE AI GALAXY</small><h2>AI 星系，正在点亮。</h2><p>模型与工具的演进，在这里化作星光。</p>';bornCaption.hidden=true;
const personalLabel=el('div','v10-galaxy-label');personalLabel.innerHTML='<small>YOUR GALAXY</small><b>你的星系</b>';personalLabel.hidden=true;
const aiLabel=el('div','v10-galaxy-label ai');aiLabel.innerHTML='<small>AN EVOLVING UNIVERSE</small><b>AI 星系</b>';aiLabel.hidden=true;
const sceneDim=el('div','v10-scene-dim');
const questionScene=el('div','v10-question');questionScene.hidden=true;questionScene.innerHTML='<small>ANOTHER LIGHT · ANOTHER VIEW</small><h2 id="v10Question"></h2><p>你留下的提问与尝试，<br>在另一束光里，成为了一幅画像。</p><i class="v10-line"></i>';
$('encounterCinema').append(sceneDim,bornCaption,personalLabel,aiLabel,questionScene);$('encounterPoem').classList.add('v10-poem');
const bgm=new Audio('__V10_MUSIC__');bgm.loop=true;bgm.volume=.26;bgm.preload='none';
const soundControls=[];
function newMusicButton(parent,inline=false){const b=el('button','v10-audio'+(inline?' inline':''));b.type='button';b.setAttribute('aria-label','开启原创深空背景音乐');b.setAttribute('aria-pressed','false');b.innerHTML='<i>♫</i>开启深空音乐';b.onclick=()=>musicToggle(!state.sound);parent.append(b);soundControls.push(b);return b;}
newMusicButton($('encounterCinema'));const topSound=el('div');topSound.style.display='flex';topSound.style.alignItems='center';$('identityClose').before(topSound);newMusicButton(topSound,true);topSound.append($('identityClose'));
function musicSync(){soundControls.forEach(b=>{b.setAttribute('aria-pressed',String(state.sound));b.setAttribute('aria-label',state.sound?'关闭背景音乐':'开启原创深空背景音乐');b.innerHTML='<i>'+(state.sound?'♫':'♪')+'</i>'+(state.sound?'深空音乐 · 开':'深空音乐 · 关');});$('soundBtn').setAttribute('aria-pressed',String(state.sound));$('soundBtn').innerHTML=state.sound?'♫ 深空音乐 · 开':'♪ 深空音乐 · 关';}
async function musicToggle(on){v10.musicChosen=true;state.sound=on;if(on){try{if(audio)await audio.resume();await bgm.play();}catch(e){state.sound=false;toast('点一下音乐按钮，即可开始播放。');}}else{bgm.pause();if(audio)audio.suspend().catch(()=>{});}musicSync();}
$('soundBtn').onclick=()=>musicToggle(!state.sound);musicSync();
document.addEventListener('visibilitychange',()=>{if(document.hidden){bgm.pause();if(state.encounterCinematic){v10.base=v10.time;v10.anchor=performance.now();}}else{v10.anchor=performance.now();v10.base=v10.time;if(state.sound)bgm.play().catch(()=>{});}});
function v10MergeProgress(){const t=v10.time;if(t<3.2)return rangeEase(0,3.2,t)*.018;return mix(.018,.995,rangeEase(3.2,10.6,t));}
function v10Birth(){return rangeEase(.25,3.1,v10.time);}
function v10GalaxyPoint(g=1,offset=[0,0,0]){
 const p=v10MergeProgress(),mobile=state.w<701?1:0;
 const approach=rangeEase(0,.32,p),pass=rangeEase(.26,.53,p),ret=rangeEase(.53,.84,p),end=rangeEase(.82,1,p);let sep=Math.max(0,mix(149,32,approach)+42*pass-72*ret);
 const turn=-.38+.8*approach+1.78*pass+2.45*ret+end*.75,sgn=g?1:-1;
 const core=[Math.cos(turn)*sep*sgn,12*Math.sin(turn)*sep/100*sgn,Math.sin(turn)*sep*.65*sgn];
 const dist=(570-94*Math.sin(Math.PI*rangeEase(0,.54,p))+85*rangeEase(.4,.68,p)-77*rangeEase(.75,1,p))*mix(1,1.65,mobile),az=.06+p*.31;
 const eye=[Math.sin(az)*dist,dist*.65,Math.cos(az)*dist*.65],target=[0,mix(5,-9,mobile),0],fw=norm(sub(target,eye)),right=norm(cross(fw,[0,1,0])),up=cross(right,fw),d=sub(add(core,offset),eye),z=dot(d,fw);
 return{x:(dot(d,right)/(.49*state.w/state.h*z)*.5+.5)*state.w,y:(.5-(dot(d,up)/(.49*z)+mix(.11,.23,mobile))*.5)*state.h};
}
function v10Dots(){
 if(!state.encounterCinematic||v10.time>4.8)return;
 const fade=1-rangeEase(3.4,4.8,v10.time),birth=v10Birth();ctx.save();ctx.globalCompositeOperation='screen';
 // Dots are a rapid visual chronology, not fabricated dates or user messages.
 const n=Math.min(24,profile.ai_history.length||18),points=[];
 for(let i=0;i<n;i++){const a=i*2.39996,r=17+Math.sqrt(i/n)*100,off=[Math.cos(a)*r,Math.sin(a)*r*.35,Math.sin(a)*r*.45];points.push(v10GalaxyPoint(1,off));}
 for(let i=0;i<n;i++){const v=clamp((birth-i/n)*n),q=points[i];if(v<=0)continue;const flash=Math.sin(Math.min(1,v)*Math.PI);if(i&&points[i-1]){ctx.beginPath();ctx.moveTo(points[i-1].x,points[i-1].y);ctx.lineTo(q.x,q.y);ctx.lineWidth=.55;ctx.strokeStyle=`rgba(116,171,238,${.11*fade*Math.min(v,1)})`;ctx.stroke();}
 const radius=(8+flash*22)*(state.w<701?.7:1),gr=ctx.createRadialGradient(q.x,q.y,0,q.x,q.y,radius);gr.addColorStop(0,`rgba(230,242,255,${(.3+flash*.5)*fade})`);gr.addColorStop(.15,`rgba(110,176,255,${(.25+flash*.3)*fade})`);gr.addColorStop(1,'rgba(72,123,246,0)');ctx.fillStyle=gr;ctx.fillRect(q.x-radius,q.y-radius,radius*2,radius*2);ctx.fillStyle=`rgba(223,239,255,${.85*fade})`;ctx.beginPath();ctx.arc(q.x,q.y,1+flash*.8,0,TAU);ctx.fill();}
 ctx.restore();
}
const v10OldOverlay=drawOverlay;drawOverlay=function(){v10OldOverlay();v10Dots();};
function v10HideOverlays(){bornCaption.hidden=true;personalLabel.hidden=true;aiLabel.hidden=true;questionScene.hidden=true;sceneDim.style.opacity='0';document.body.classList.remove('v10-question-active');}
function v10Phase(){return v10.time<3.2?'ai-birth':v10.time<10.6?'merge':v10.time<14?'question':'card';}
updateEncounterUI=function(){
 $('encounterPlay').textContent=state.mergePlaying?'Ⅱ 暂停':'▷ 相遇';$('cinemaPause').textContent=state.mergePlaying?'Ⅱ 暂停':'▷ 继续';
 if(!state.encounterCinematic){v10HideOverlays();return;}
 $('encounterCinema').hidden=false;document.body.classList.add('encounter-cinema');const t=v10.time,phase=v10Phase();v10.phase=phase;
 $('cinemaRange').value=String(Math.round(t/14*1000));$('cinemaTime').textContent=Math.min(14,Math.floor(t)).toString().padStart(2,'0')+' / 14s';$('cinemaPause').hidden=false;
 $('cinemaSkip').hidden=state.reduced;$('cinemaSkip').textContent='跳到揭晓 →';
 bornCaption.hidden=t>=3.6;bornCaption.style.opacity=String(1-rangeEase(2.9,3.6,t));
 const labelsOn=t<4.8;personalLabel.hidden=aiLabel.hidden=!labelsOn;
 if(labelsOn){const p=v10GalaxyPoint(0),a=v10GalaxyPoint(1);for(const [node,q] of [[personalLabel,p],[aiLabel,a]]){node.style.left=q.x+'px';node.style.top=(q.y+(state.w<701?40:78))+'px';node.style.opacity=String(1-rangeEase(3.3,4.8,t));}}
 const intro=t<3.2,question=t>=10.6;
 $('encounterPoem').hidden=intro||question;
 if(!intro&&!question){let code,line1,line2,begin,end;
 if(t<5.8){code='MILKY WAY × ANDROMEDA';line1='就像银河系与仙女座，';line2='正在彼此靠近。';begin=3.2;end=5.8;}
 else if(t<8.25){code='A POSSIBLE FUTURE';line1='或许在遥远的未来，';line2='它们会相撞、交融。';begin=5.8;end=8.25;}
 else{code='YOU × AI';line1='我们也将和 AI 相聚，';line2='组成新的世界。';begin=8.25;end=10.6;}
 $('poemCode').textContent=code;$('poemLine1').textContent=line1;$('poemLine2').textContent=line2;const fade=Math.min(rangeEase(begin,begin+.25,t),1-rangeEase(end-.22,end,t));$('encounterPoem').style.opacity=String(state.reduced?1:fade);$('encounterPoem').style.transform=`translateY(${(1-fade)*9}px)`;
 }
 questionScene.hidden=!question;const q=rangeEase(10.6,11.2,t);sceneDim.style.opacity=String(q*.63);questionScene.style.opacity=String(q);
 if(question){const name=summarizerInfo().name;$('v10Question').replaceChildren(document.createTextNode(name?'在 '+name+' 眼中，':'从你的成长轨迹里，'),document.createElement('br'));const s=el('span','','你是什么样的？');$('v10Question').append(s);}
 $('encounterCaption').textContent=intro?'AI 星系逐步点亮':question?(summarizerInfo().name? summarizerInfo().name+' 眼中的你':'成长画像揭晓'):'两片星系交融';
};
encounter=function(){
 if(v8.cardOpen)hideIdentityCard();
 if(!state.encounterCinematic){v10.trigger=document.activeElement;showWorld('overview',true);setAuto(false);state.encounterCinematic=true;state.exploring=false;state.orbiting=false;document.body.classList.remove('exploring');v10.time=0;state.merge=state.mergeGoal=0;v10.base=0;v10.anchor=performance.now();v10.playing=true;state.mergePlaying=true;v8.running=false;state.viewTween=null;
  if(!v10.musicChosen)musicToggle(true);else if(state.sound)bgm.play().catch(()=>{});
 }else{state.mergePlaying=!state.mergePlaying;v10.playing=state.mergePlaying;v10.base=v10.time;v10.anchor=performance.now();}
 if(state.reduced){v10.time=11.7;v10.base=v10.time;state.merge=state.mergeGoal=v10.time/14;state.mergePlaying=false;v10.playing=false;questionScene.classList.add('v10-question-reduced');if(!$('v10RevealNow')){const b=el('button','','揭晓我的闪卡');b.id='v10RevealNow';b.onclick=()=>showIdentityCard();questionScene.append(b);}}
 else{questionScene.classList.remove('v10-question-reduced');if($('v10RevealNow'))$('v10RevealNow').remove();}
 updateEncounterUI();
};
advanceEncounter=function(dt){if(!state.encounterCinematic)return;
 if(state.mergePlaying&&!document.hidden){if(!v10.playing){v10.playing=true;v10.base=v10.time;v10.anchor=performance.now();}v10.time=testing?v10.time+dt:v10.base+(performance.now()-v10.anchor)/1000;}
 else{v10.playing=false;v10.base=v10.time;v10.anchor=performance.now();}
 v10.time=clamp(v10.time,0,14);state.merge=state.mergeGoal=v10.time/14;v8.encounterElapsed=v10.time;
 if(v10.time>=14){state.mergePlaying=false;v10.playing=false;v10.phase='card';showIdentityCard();return;}
 updateEncounterUI();
};
scrubEncounter=function(p){v10.time=clamp(p)*14;v10.base=v10.time;v10.anchor=performance.now();state.merge=state.mergeGoal=p;state.mergePlaying=false;v10.playing=false;if(p>=1)showIdentityCard();else updateEncounterUI();};
function v10Skip(){v10.time=10.6;v10.base=v10.time;v10.anchor=performance.now();state.merge=state.mergeGoal=v10.time/14;state.mergePlaying=true;v10.playing=true;updateEncounterUI();}
$('cinemaSkip').onclick=v10Skip;$('cinemaContinue').onclick=()=>showIdentityCard();$('meetHero').onclick=$('encounterPlay').onclick=$('cinemaPause').onclick=()=>encounter();
$('cinemaRange').oninput=e=>scrubEncounter(Number(e.target.value)/1000);$('cinemaReplay').onclick=$('cardReplay').onclick=()=>{hideIdentityCard();endEncounter(false);quietFinale();};
$('v8FinaleShortcut').textContent='终章 · AI 星系与我 ↗';$('v8FinaleShortcut').onclick=()=>{quietMenu(false);quietFinale();};$('v8CardShortcut').onclick=()=>{quietMenu(false);if(state.flight)finishFlight();showIdentityCard();};
// A small explicit finale entry, not another block of homepage copy.
const endLink=el('button','v10-home-end','AI 星系与我 ↗');endLink.id='v10HomeFinale';endLink.onclick=quietFinale;document.querySelector('.header nav').append(endLink);
const providerRefresh=refreshIdentity;
refreshIdentity=function(){
 providerRefresh();const ai=summarizerInfo(),d=currentPersona();
 document.querySelector('.identity-kicker').textContent=ai.name?ai.name.toUpperCase()+"'S VIEW":"YOUR STORY";
 $('identityHeading').replaceChildren(document.createTextNode(ai.name?'在 '+ai.name+' 眼中，':'你的故事，'),document.createElement('br'));
 const s=el('span','',d.ready?'你是「'+d.title+'」。':'还在生长。');$('identityHeading').append(s);
 document.querySelector('.identity-message').textContent=d.ready?d.line:'当前旅程还没有对应的模型印象，不沿用上一位用户的卡片。';
 document.querySelector('.identity-caption span').textContent=ai.name?'基于本次成长总结 · '+ai.name:'总结来源未标注';
 $('cardBack').src=v8URI(buildCardSVG('back'));
};
const narrativeShowCard=showIdentityCard;
showIdentityCard=function(){if(v8.cardOpen)return;state.mergePlaying=false;v10.playing=false;v10.phase='card';v10HideOverlays();narrativeShowCard();refreshIdentity();if(!v10.keyboardInput)$('identityCard').classList.add('pointer-focus');};
const v10OldEnd=endEncounter;endEncounter=function(returnView=false){v10.playing=false;v10HideOverlays();v10OldEnd(returnView);};
$('cinemaExit').onclick=()=>{endEncounter(false);showWorld('personal');};
$('cardFront').alt='SSR 人物卡，原创月下幻想人物插画；非真人肖像';document.querySelector('#cardReplay small').textContent='14s';$('encounterCinema').setAttribute('aria-label','十四秒终章：AI 星系发展、交融与身份卡揭晓');
const oldV10Nav=createNav;createNav=function(){oldV10Nav();const last=$('indexList').lastElementChild;if(last?.querySelector('small'))last.querySelector('small').textContent='认识 AI 星系 · 快速交融 · 揭晓 SSR 闪卡';};
document.addEventListener('keydown',e=>{if(e.key==='Tab'){v10.keyboardInput=true;$('identityCard').classList.remove('pointer-focus');}},true);
document.addEventListener('pointerdown',()=>{v10.keyboardInput=false;$('identityCard').classList.add('pointer-focus');},true);
refreshIdentity();
window.twinlightV10={finale:quietFinale,showCard:()=>showIdentityCard(),getState:()=>({time:v10.time,phase:v10.phase,total:14,aiBirth:v10Birth(),mergerProgress:v10MergeProgress(),summarizer:summarizerInfo(),question:$('v10Question').textContent,music:state.sound,card:v8.cardOpen}),seek:seconds=>{if(!state.encounterCinematic){quietFinale();}scrubEncounter(seconds/14);paint();},summarizer:summarizerInfo};
window.twinlightV8.showCard=()=>showIdentityCard();window.twinlightV8.finale=quietFinale;
if(location.hash==='#card')setTimeout(()=>showIdentityCard(),1300);else if(location.hash==='#finale')setTimeout(()=>quietFinale(),1300);
