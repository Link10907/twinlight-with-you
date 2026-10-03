/* Twinlight V8. Source-specific SSR card + physically shaded topic planets.
 * No inference service, network, storage, unique-token claim or live Skill call.
 * Only the supplied profile and this audited, editable persona are used.
 */
const v8={cardOpen:false,flipped:false,encounterElapsed:0,anchor:0,base:0,running:false,needPaint:false,returnFocus:null,exportSide:'front',exporting:false};
const CARD_ART=__CARD_ART__;
const CARD_PERSONA=__CARD_DATA__;
const v8Baseline=JSON.stringify(DEFAULT_PROFILE.chapters);
const v8xml=s=>String(s??'').replace(/[<>&"']/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&apos;'}[c]));
const v8URI=svg=>'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
const solarPalette=[[.68,.51,.38],[.29,.58,.73],[.69,.43,.27],[.69,.72,.59],[.79,.67,.49],[.46,.72,.79],[.59,.64,.79],[.72,.61,.82]];
const solarRadius=[1.00,1.24,1.12,1.54,2.16,1.92,1.62,2.36];
const solarMaterials=[0,1,0,0,4,2,3,4];
let solarLookup=[];
function orbitalPosition(s,a){
 const r=s.orbitRadius,e=s.eccentricity;
 const x=r*(Math.cos(a)-e),z=r*Math.sqrt(1-e*e)*Math.sin(a);
 const pos=mv(mat3YawTilt(s.nodeAngle,s.inclination),[x,0,z]);
 return add(localNodes[s.i],pos);
}
const v8Rebuild=rebuildPersonalMap;
rebuildPersonalMap=function(){v8Rebuild();solarLookup=profile.chapters.map(()=>[]);
 personalSatellites.forEach((s,k)=>{const j=s.j;const spec=profile.layout.topics.find(p=>p.parent_id===profile.chapters[s.i].id&&p.id===profile.chapters[s.i].topics[s.j].id);if(!spec)throw Error('行星布局缺失');Object.assign(s,{k,...spec});
 s.p=orbitalPosition(s,s.phase);solarLookup[s.i][j]=s;
 const b=personalButtons[k];b.title='';b.setAttribute('aria-label','探索行星 '+s.name+' · '+profile.chapters[s.i].label);
 });
};
const v8WorldUpdate=updateWorld;
updateWorld=function(){v8WorldUpdate();for(const s of personalSatellites){s.p=orbitalPosition(s,s.phase+(state.reduced?0:state.time*.065*Math.pow(11.8/s.orbitRadius,1.5)));}};
// One set of 3D positions for map, fly-in, picking and orbit geometry.
cacheTopicPositions=function(){};
topicWorld=function(i,j){const s=solarLookup[i]?.[j];return s?worldPoint(s.p):nodes[i];};
const v8Target=targetView;
targetView=function(i){if(i<0)return v8Target(i);const p=nodes[i];return state.w<=700?{cam:add(p,[5,99,116]),target:add(p,[-2,-33,0]),fov:59}:{cam:add(p,[8,66,94]),target:add(p,[-24,-7,0]),fov:52};};
function solarOccluded(s){const w=worldPoint(s.p),q=project(w);if(!q)return true;for(let i=0;i<nodes.length;i++){const p=project(nodes[i]);if(!p||p.z>=q.z)continue;const r=mix(2.5,radii[i],starDetail(i))*state.h/(2*p.z*Math.tan(state.fov*Math.PI/360));if(Math.hypot(q.x-p.x,q.y-p.y)<r*.9)return true;}return false;}
const v8Labels=updateLabels;
updateLabels=function(){v8Labels();personalButtons.forEach((b,k)=>{const s=personalSatellites[k];if(b.hidden)return;if(solarOccluded(s)){b.hidden=true;return;}const p=project(worldPoint(s.p));if(p)b.style.transform=`translate3d(${(p.x-22).toFixed(1)}px,${(p.y-22).toFixed(1)}px,0)`;});
 topicButtons.forEach((b,j)=>{const s=solarLookup[state.active]?.[j];if(s&&solarOccluded(s))b.hidden=true;});
 if(v8.cardOpen){labels.forEach(b=>b.hidden=true);personalButtons.forEach(b=>b.hidden=true);topicButtons.forEach(b=>b.hidden=true);}
};
const v8Hit=findHit;
findHit=function(x,y,limit=42){if(v8.cardOpen||state.encounterCinematic)return null;let h=v8Hit(x,y,limit);if(h?.type==='topic'&&solarOccluded(personalSatellites[h.i]))h=null;if(h?.type==='chapterTopic'&&solarOccluded(solarLookup[state.active][h.i]))h=null;return h;};
// Quiet elliptical tracks, not spoke diagrams. Only a few tracks in the map;
// in a focused system all evidenced tracks become discoverable, with depth cues.
function drawSolarTracks(){if(state.encounterCinematic||state.flight||v8.cardOpen||!quietPersonVisible())return;
 const close=state.mode==='chapter'&&state.active>=0,map=['personal','overview'].includes(state.mode);if(!close&&!map)return;
 for(const s of personalSatellites){if(close&&s.i!==state.active)continue;const related=close||quiet.selection===s.i||state.hoveredStar===s.i;
 const hot=(close&&(state.topicHover===s.j||state.topic===s.j))||state.hoverTopicIndex===s.k||quiet.selection===s.i&&quiet.topic===s.j;
 if(!related&&s.j!==1&&s.j!==5)continue;
 const pts=[];for(let k=0;k<=84;k++)pts.push(worldPoint(orbitalPosition(s,k*TAU/84)));
 const rgb=s.color.map(x=>Math.round(x*255)).join(',');
 ctx.strokeStyle=`rgba(${rgb},${hot?.28:close?.105:related?.085:.032})`;ctx.lineWidth=hot?.8:.55;ctx.beginPath();let pen=false;
 for(const w of pts){const q=project(w),p=project(nodes[s.i]);if(!q||!p){pen=false;continue;}const sr=mix(2.5,radii[s.i],starDetail(s.i))*state.h/(2*p.z*Math.tan(state.fov*Math.PI/360));if(Math.hypot(q.x-p.x,q.y-p.y)<sr*1.04){pen=false;continue;}if(pen)ctx.lineTo(q.x,q.y);else ctx.moveTo(q.x,q.y);pen=true;}ctx.stroke();
 }
}
drawOverlay=function(){ctx.clearRect(0,0,state.w,state.h);if(v8.cardOpen)return;ctx.save();ctx.globalCompositeOperation='screen';
 if(quietPersonVisible()&&!state.encounterCinematic){for(let i=0;i<nodes.length;i++){const hot=state.hoveredStar===i||quiet.selection===i;hoverGlow[i]=mix(hoverGlow[i],hot?1:0,1-Math.exp(-Math.max(.016,state.delta)*8));const p=project(nodes[i]);if(!p)continue;const r=mix(2.5,radii[i],starDetail(i))*state.h/(2*p.z*Math.tan(state.fov*Math.PI/360));quietLight(nodes[i],i,Math.max(18,r*2.6)+hoverGlow[i]*15,.14+hoverGlow[i]*.17);}}
 if(quietAIVisible()&&!state.encounterCinematic){for(const provider of providerOrder){if(state.provider!=='all'&&state.provider!==provider)continue;const items=profile.ai_history.map((e,i)=>({e,i})).filter(o=>o.e.provider===provider).sort((a,b)=>a.e.date.localeCompare(b.e.date));const c=providerColors[provider].map(x=>Math.round(x*255)).join(',');strokeWorld(items.map(o=>aiNodes[o.i]),'rgba('+c+',.13)',.5);}profile.ai_history.forEach((e,i)=>{if(state.provider==='all'||state.provider===e.provider)quietLight(aiNodes[i],providerOrder.indexOf(e.provider),state.hoverAI===i?42:20,.8);});}
 if(['personal','overview'].includes(state.mode)&&!state.flight&&!state.encounterCinematic)strokeWorld(routeLocal.map(p=>worldPoint(p)),'rgba(211,194,155,.11)',.5);
 drawSolarTracks();ctx.restore();
};
// Art and typography are separate assets; every card receives the same SSR
// treatment. For an imported different journey we don't reuse the previous owner's verdict.
function currentPersona(){
 const bound=profile.owner_id===DEFAULT_PROFILE.owner_id && JSON.stringify(profile.chapters)===JSON.stringify(DEFAULT_PROFILE.chapters) && JSON.stringify(profile.summary_meta)===JSON.stringify(DEFAULT_PROFILE.summary_meta);
 const p=bound?CARD_PERSONA:{name:profile.name,rarity:'SSR',title:'星旅者',english_title:'A JOURNEY IN LIGHT',edition:'',keywords:['记录'],line:'这是一段新的旅程。',reflection:'请根据新资料重新生成并审查卡片，不能沿用另一位用户的形象。',evidence:[]};
 return {...p,ready:bound&&!!p.content_ready,artReady:bound&&p.art_status==='approved',shareAllowed:bound&&profile.release?.share_allowed===true};
}
function wrapCard(s,n=25){const lines=[];let line='',units=0;for(const c of String(s)){const u=c.charCodeAt(0)>255?1:.55;if(units+u>n){lines.push(line);line='';units=0;}line+=c;units+=u;}if(line)lines.push(line);return lines;}
function svgTextLines(lines,x,y,size,color,lh=1.8){return lines.map((s,i)=>`<text x="${x}" y="${y+i*size*lh}" fill="${color}" font-size="${size}">${v8xml(s)}</text>`).join('');}
function buildCardSVG(side='front'){
 const d=currentPersona(),rnd=seedRandom(2864);let stars='';for(let i=0;i<75;i++){const x=30+rnd()*540,y=95+rnd()*570;stars+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(.3+rnd()*.8).toFixed(1)}" fill="#d1d9e5" opacity="${(.1+rnd()*.42).toFixed(2)}"/>`;}
 const defs=`<defs><linearGradient id="cardBorder" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e8cf9e"/><stop offset=".25" stop-color="#839dbb"/><stop offset=".5" stop-color="#ba9fce"/><stop offset=".76" stop-color="#cbdace"/><stop offset="1" stop-color="#b98b5d"/></linearGradient><radialGradient id="cbg" cx=".57" cy=".4" r=".76"><stop stop-color="#1b2b40"/><stop offset=".65" stop-color="#0c1523"/><stop offset="1" stop-color="#070d16"/></radialGradient><linearGradient id="bottom" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#0a121e" stop-opacity="0"/><stop offset=".5" stop-color="#0a121e" stop-opacity=".9"/><stop offset="1" stop-color="#080e18"/></linearGradient><linearGradient id="ssr" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f5e4b9"/><stop offset=".5" stop-color="#dfc18b"/><stop offset="1" stop-color="#adc8d4"/></linearGradient><clipPath id="cardClip"><rect x="9" y="9" width="582" height="782" rx="24"/></clipPath></defs>`;
 const shell=`<rect x="1" y="1" width="598" height="798" rx="30" fill="#101827" stroke="url(#cardBorder)" stroke-width="2"/><rect x="9" y="9" width="582" height="782" rx="24" fill="url(#cbg)" stroke="url(#cardBorder)" stroke-opacity=".43"/><path d="M29 124V48Q29 29 48 29H138M462 29h89q20 0 20 20v75M29 685v67q0 19 19 19h96M456 771h95q20 0 20-20v-66" stroke="url(#cardBorder)" fill="none" stroke-width="1.1" opacity=".6"/>`;
 const badge=`<g transform="translate(454 35)"><rect width="110" height="53" rx="11" fill="#e6c68b" fill-opacity=".08" stroke="#e6cb99" stroke-opacity=".42"/><text x="55" y="29" text-anchor="middle" font-family="Georgia,serif" font-size="26" letter-spacing="5" fill="url(#ssr)">SSR</text><text x="55" y="44" text-anchor="middle" font-size="6.5" letter-spacing="1.1" fill="#b9ae94">UNIQUE PERSONA</text></g>`;
 let body='';if(side==='front'){
 body=`${stars}<svg x="0" y="73" width="600" height="584" viewBox="0 0 600 680" fill="none">${CARD_ART.replace(/^[\s\S]*?<svg[^>]*>/,'').replace(/<\/svg>\s*$/,'')}</svg><rect x="10" y="560" width="580" height="230" fill="url(#bottom)"/>
 <text x="39" y="54" font-size="10" letter-spacing="3.4" fill="#b4c1d2">AI'S VIEW</text><text x="39" y="82" font-size="17" letter-spacing="1.4" fill="#ede5d6">${v8xml(d.name)}</text>${badge}
 <text x="300" y="627" text-anchor="middle" font-family="'Songti SC','Noto Serif CJK SC',serif" font-size="38" letter-spacing="9" fill="#f0dfbf">${v8xml(d.title)}</text><text x="300" y="654" text-anchor="middle" font-size="10" letter-spacing="4.3" fill="#8eabc1">${v8xml(d.english_title)}</text>
 <path d="M119 680h65M416 680h65" stroke="#d5bd93" stroke-opacity=".28"/>
 <text x="300" y="685" text-anchor="middle" font-size="12" letter-spacing="4" fill="#b7c0c6">${v8xml(d.keywords.join(' · '))}</text>
 <text x="300" y="727" text-anchor="middle" font-size="16" letter-spacing="1.2" fill="#d7c9ae">${v8xml(d.line)}</text>
 <text x="39" y="768" font-size="8" letter-spacing="2.3" fill="#8292a6">TWINLIGHT</text><text x="562" y="768" text-anchor="end" font-size="8" letter-spacing="1.2" fill="#8292a6">AI IMPRESSION · ${v8xml(d.edition)}</text>`;
 }else{
 body=`${stars}<text x="39" y="55" font-size="10" letter-spacing="2.8" fill="#aabbcb">THE OTHER SIDE</text><text x="39" y="82" font-size="16" fill="#e5dccb">${v8xml(d.name)} / ${v8xml(summarizerInfo().name? summarizerInfo().name+' 眼中的你':'成长印象')}</text>${badge}
 <text x="43" y="151" font-family="'Songti SC','Noto Serif CJK SC',serif" font-size="26" letter-spacing="1.5" fill="#ead7b2">我看见的，不止是结果。</text>
 ${svgTextLines(wrapCard(d.reflection,25),44,190,15,'#abb9c8',1.85)}
 <path d="M43 300h514" stroke="#c4b88b" stroke-opacity=".23"/>`;
 d.evidence.forEach((e,i)=>{const y=345+i*113;body+=`<text x="45" y="${y}" font-size="12" fill="#b9a579" letter-spacing="2">0${i+1}</text><text x="86" y="${y+1}" font-size="18" fill="#e0d3b7" letter-spacing="1">${v8xml(e.title)}</text>${svgTextLines(wrapCard(e.text,23),86,y+32,14,'#94a5b9',1.7)}`;});
 body+=`<path d="M43 679h514" stroke="#c4b88b" stroke-opacity=".2"/><text x="44" y="710" font-size="11" fill="#9da8b7">基于成长资料 · ${v8xml(summarizerInfo().name||'来源未标注')} 印象，非人格测评</text><text x="44" y="735" font-size="10" fill="#76889e">SSR 表示每个人独特的经历，不表示能力排名。</text><text x="44" y="768" font-size="8" letter-spacing="2.3" fill="#8292a6">TWINLIGHT / AI'S VIEW</text><text x="557" y="768" text-anchor="end" font-size="8" letter-spacing="1.1" fill="#8292a6">${v8xml(d.edition)}</text>`;
 }
 return `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1440" viewBox="0 0 600 800"><style>text{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Noto Sans CJK SC','Microsoft YaHei',sans-serif;font-weight:400}</style>${defs}${shell}<g clip-path="url(#cardClip)">${body}</g></svg>`;
}
function refreshIdentity(){const d=currentPersona();$('cardFront').src=v8URI(buildCardSVG('front'));$('cardBack').src=v8URI(buildCardSVG('back'));$('identityCard').setAttribute('aria-label','SSR '+d.title+'闪卡，点击翻面');document.querySelector('.identity-caption span').textContent='给 '+d.name+' 的一张卡';$('identityHeading').innerHTML=d.ready?'原来，<br>你一直在<span>造自己的星。</span>':'新的旅程，<br><span>等待被看见。</span>';$('cardSave').disabled=!d.ready;document.querySelector('.identity-message').innerHTML=d.ready?'那些问过的问题、走通的路，<br>慢慢组成了我眼中的你。':'这份新资料尚未生成对应的 AI 印象。<br>当前只显示通用模板，不沿用原卡判断。';}
function flipIdentity(force){v8.flipped=typeof force==='boolean'?force:!v8.flipped;$('identityCard').classList.toggle('flipped',v8.flipped);$('identityCard').setAttribute('aria-pressed',String(v8.flipped));$('cardFlip').innerHTML=(v8.flipped?'翻回正面':'翻到背面')+' <span>↻</span>';}
function setCardTilt(x=0,y=0){const c=$('identityCard');c.style.setProperty('--rx',(-y*9).toFixed(2)+'deg');c.style.setProperty('--ry',(x*12-3).toFixed(2)+'deg');c.style.setProperty('--mx',(50+x*38).toFixed(1)+'%');c.style.setProperty('--my',(45+y*38).toFixed(1)+'%');}
function showIdentityCard(){if(v8.cardOpen)return;v8.returnFocus=document.activeElement;v8.running=false;quiet.playing=false;state.merge=state.mergeGoal=1;endEncounter(false);quiet.reading=false;hideReading();v8.cardOpen=true;v8.needPaint=true;refreshIdentity();flipIdentity(false);setCardTilt(-.22,-.08);$('identityScene').hidden=false;document.body.classList.add('card-revealed');
 document.querySelectorAll('body > *').forEach(e=>{if(!['identityScene','cardExportReview','toast'].includes(e.id)&&!['SCRIPT','STYLE'].includes(e.tagName)){e.dataset.v8WasInert=e.inert?'1':'0';e.inert=true;}});
 $('identityCard').focus({preventScroll:true});
}
function hideIdentityCard(){if(!v8.cardOpen)return;v8.cardOpen=false;$('identityScene').hidden=true;document.body.classList.remove('card-revealed');document.querySelectorAll('[data-v8-was-inert]').forEach(e=>{e.inert=e.dataset.v8WasInert==='1';delete e.dataset.v8WasInert;});if($('cardExportReview').open)$('cardExportReview').close();}
const v8ShowWorld=showWorld;
showWorld=function(mode='personal',instant=false){hideIdentityCard();v8.running=false;v8.encounterElapsed=0;v8ShowWorld(mode,instant);};
$('identityClose').onclick=()=>{const previous=v8.returnFocus;hideIdentityCard();showWorld('personal');if(previous&&previous.isConnected&&!previous.hidden)previous.focus({preventScroll:true});else $('home').focus();};
$('identityCard').onclick=()=>flipIdentity();$('cardFlip').onclick=()=>flipIdentity();
$('identityCard').onpointermove=e=>{if(state.reduced)return;const r=e.currentTarget.getBoundingClientRect();setCardTilt(clamp((e.clientX-r.left)/r.width*2-1,-1,1),clamp((e.clientY-r.top)/r.height*2-1,-1,1));};
$('identityCard').onpointerleave=()=>setCardTilt(-.22,-.08);
$('identityCard').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();flipIdentity();}};
$('cardSideHint').textContent=matchMedia('(pointer:coarse)').matches?'轻触翻面 · 正反两面都能保存':'移动看流光 · 点击翻面';
window.addEventListener('keydown',e=>{if(!v8.cardOpen||document.querySelector('dialog[open]'))return;if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();$('identityClose').click();return;}if(e.key==='Tab'){const list=[...$('identityScene').querySelectorAll('button:not([disabled]),[tabindex="0"]')].filter(el=>!el.hidden);const first=list[0],last=list.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}},{capture:true});
// All entry paths use the same twelve-second active timeline; pause and tab
// visibility are explicit. The camera transition is inside those 12 seconds.
encounterActs.splice(0,4,
 {start:0,end:.25,code:'01 / 各自生长',line1:'不同的来路，',line2:'同样的好奇。',sub:''},
 {start:.25,end:.58,code:'02 / 向光而行',line1:'问题与回声，',line2:'让两片宇宙靠近。',sub:''},
 {start:.58,end:.86,code:'03 / 交织',line1:'新的世界，',line2:'也有你的一束光。',sub:''},
 {start:.86,end:1,code:'04 / AI\'S VIEW',line1:'而在 AI 眼里，',line2:'你是什么样的人？',sub:''});
const v8Encounter=encounter;
encounter=function(){const was=state.encounterCinematic,playing=state.mergePlaying;v8Encounter();if(!was){v8.encounterElapsed=state.merge*encounterDuration;v8.base=v8.encounterElapsed;v8.anchor=performance.now();if(state.viewTween)state.viewTween.duration=state.reduced?.2:1.05;}
 if(state.encounterRewind){state.encounterRewind=false;state.merge=state.mergeGoal=0;v8.encounterElapsed=0;state.mergePlaying=true;}
 v8.running=state.mergePlaying;v8.base=state.merge*encounterDuration;v8.encounterElapsed=v8.base;v8.anchor=performance.now();
 if(state.reduced){state.mergePlaying=false;v8.running=false;showIdentityCard();}updateEncounterUI();
};
advanceEncounter=function(dt){
 if(!state.encounterCinematic){v8.running=false;return;}
 if(state.mergePlaying){if(!v8.running){v8.running=true;v8.base=state.merge*encounterDuration;v8.anchor=performance.now();v8.encounterElapsed=v8.base;}
 v8.encounterElapsed=testing?v8.encounterElapsed+dt:v8.base+(performance.now()-v8.anchor)/1000;
 state.merge=state.mergeGoal=clamp(v8.encounterElapsed/encounterDuration);
 if(state.merge>=1-1e-7){state.merge=state.mergeGoal=1;state.mergePlaying=false;v8.running=false;updateEncounterUI();showIdentityCard();return;}
 }else{v8.running=false;state.merge=mix(state.merge,state.mergeGoal,1-Math.exp(-dt*8));if(Math.abs(state.merge-state.mergeGoal)<.00002)state.merge=state.mergeGoal;if(state.mergeGoal===1&&state.merge>.999)showIdentityCard();}
 updateEncounterUI();
};
scrubEncounter=function(v){state.mergePlaying=false;state.encounterRewind=false;v8.running=false;state.merge=state.mergeGoal=clamp(v);v8.encounterElapsed=state.merge*encounterDuration;updateEncounterUI();if(state.merge>=1)showIdentityCard();};
const v8EncounterUI=updateEncounterUI;
updateEncounterUI=function(){v8EncounterUI();if(state.encounterCinematic)$('cinemaTime').textContent=Math.min(12,Math.floor(state.merge*12)).toString().padStart(2,'0')+' / 12s';};
$('meetHero').onclick=$('encounterPlay').onclick=$('cinemaPause').onclick=()=>encounter();
const skipCard=el('button','','直接看闪卡 →');skipCard.id='cinemaSkip';skipCard.onclick=showIdentityCard;document.querySelector('.cinema-player').append(skipCard);
$('cinemaContinue').onclick=showIdentityCard;
function replayIdentity(){hideIdentityCard();endEncounter(false);quietFinale();}
$('cardReplay').onclick=$('cinemaReplay').onclick=replayIdentity;
$('cinemaRange').oninput=e=>scrubEncounter(Number(e.target.value)/1000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&state.encounterCinematic&&state.mergePlaying){v8.anchor=performance.now();v8.base=state.merge*encounterDuration;}});
const v8Tick=tick;
tick=function(dt,draw=true){if(v8.cardOpen){if(draw&&v8.needPaint){updateWorld();paint();v8.needPaint=false;}return;}v8Tick(dt,draw);};
const v8Motion=updateMotion;
updateMotion=function(){v8Motion();document.body.classList.toggle('reduced-motion',state.reduced);if(state.reduced&&state.encounterCinematic)showIdentityCard();};
const v8Nav=createNav;
createNav=function(){v8Nav();$('v7Count').textContent=profile.chapters.length+' 颗主星 · '+profile.chapters.reduce((a,c)=>a+c.topics.length,0)+' 颗行星';const last=$('indexList').lastElementChild;if(last)last.querySelector('small').textContent='终章 · 12 秒交融，然后领取 SSR 闪卡';};
const finaleShortcut=el('button','','终章 · 12 秒交融');finaleShortcut.id='v8FinaleShortcut';finaleShortcut.append(el('span','','↗'));finaleShortcut.onclick=()=>{quietMenu(false);quietFinale();};$('v7Catalog').after(finaleShortcut);
const cardShortcut=el('button','','我的 SSR 闪卡');cardShortcut.id='v8CardShortcut';cardShortcut.append(el('span','','✧'));cardShortcut.onclick=()=>{quietMenu(false);if(state.flight)finishFlight();showIdentityCard();};finaleShortcut.after(cardShortcut);
// Explicit opt-in export. The page never uploads images or attaches raw chats.
function imageReady(src){return new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>resolve(i);i.onerror=()=>reject(new Error('卡面图片未能载入。'));i.src=src;});}
async function exportCardBlob(side){const image=await imageReady(v8URI(buildCardSVG(side))),cv=document.createElement('canvas');cv.width=1080;cv.height=1440;const c=cv.getContext('2d');c.drawImage(image,0,0,1080,1440);return new Promise((resolve,reject)=>{try{cv.toBlob(b=>b?resolve(b):reject(new Error('图片导出失败，请重试。')),'image/png');}catch(e){reject(e);}});}
$('cardSave').onclick=()=>{if(!currentPersona().ready)return;v8.exportSide=v8.flipped?'back':'front';$('cardReviewCheck').checked=false;$('cardDownload').disabled=true;$('cardNativeShare').disabled=true;$('cardExportStatus').textContent=(v8.flipped?'背面':'正面')+' · 1080 × 1440 PNG · 静态图片不包含互动流光';$('cardNativeShare').hidden=!(navigator.share&&navigator.canShare);$('cardExportReview').showModal();};
$('cardExportClose').onclick=()=>$('cardExportReview').close();
$('cardReviewCheck').onchange=()=>{$('cardDownload').disabled=$('cardNativeShare').disabled=!$('cardReviewCheck').checked||v8.exporting;};
function saveBlob(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);}
async function cardExport(native=false){if(!$('cardReviewCheck').checked||v8.exporting||!currentPersona().ready)return;v8.exporting=true;$('cardDownload').disabled=$('cardNativeShare').disabled=true;$('cardExportStatus').textContent='正在生成卡面图片…';try{const blob=await exportCardBlob(v8.exportSide),fileName='Twinlight-SSR-'+(v8.exportSide==='front'?'front':'back')+'.png';if(native){const file=new File([blob],fileName,{type:'image/png'});if(navigator.canShare?.({files:[file]})){await navigator.share({files:[file],title:(summarizerInfo().name||'成长记录')+' 眼中的我 · SSR '+currentPersona().title});$('cardExportStatus').textContent='已交给系统分享面板。';}else{saveBlob(blob,fileName);$('cardExportStatus').textContent='此浏览器不支持图片分享，已改为保存 PNG。';}}else{saveBlob(blob,fileName);$('cardExportStatus').textContent='已生成 PNG，并请求浏览器保存。';}}catch(e){$('cardExportStatus').textContent=e.name==='AbortError'?'已取消分享。':'导出未完成：'+e.message;}finally{v8.exporting=false;$('cardDownload').disabled=$('cardNativeShare').disabled=!$('cardReviewCheck').checked;}}
$('cardDownload').onclick=()=>cardExport(false);$('cardNativeShare').onclick=()=>cardExport(true);
refreshIdentity();
window.twinlightV8={showCard:showIdentityCard,flip:flipIdentity,finale:quietFinale,cardSVG:buildCardSVG,exportPNG:exportCardBlob,getState:()=>({cardOpen:v8.cardOpen,flipped:v8.flipped,duration:encounterDuration,elapsed:v8.encounterElapsed,planets:personalSatellites.length,ready:currentPersona().ready})};
