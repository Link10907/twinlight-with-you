/* Skill 1.0 data adapter. Renderer stays fixed; evidence/compiler owns content. */
const nativeValidate=validateProfile;
validateProfile=function(x){
 const clean=nativeValidate(x);
 if(x.version!=='1.0'||!x.layout||!Array.isArray(x.layout.stars)||x.layout.stars.length!==clean.chapters.length)throw Error('请导入由本 Skill 编译的 profile.json。旧版 JSON 请先迁移，不要自动凑五章。');
 const vec=(v,n,min=-1000,max=1000)=>Array.isArray(v)&&v.length===n&&v.every(x=>typeof x==='number'&&Number.isFinite(x)&&x>=min&&x<=max);
 if(!x.owner_id||typeof x.owner_id!=='string'||x.owner_id.length>64)throw Error('缺少稳定 owner_id');
 if(new Set(clean.chapters.map(c=>c.id)).size!==clean.chapters.length)throw Error('重复主星 ID');
 const stars=x.layout.stars.map((s,i)=>{if(s.id!==clean.chapters[i].id||!vec(s.position,3)||!vec(s.color,3,0,1)||!Number.isInteger(s.material)||s.material<0||s.material>4)throw Error('主星布局无效');return {id:s.id,position:s.position.slice(),color:s.color.slice(),material:s.material};});
 if(!Array.isArray(x.layout.topics)||x.layout.topics.length>64)throw Error('行星数量无效');
 const topics=x.layout.topics.map(s=>{for(const k of ['radius','orbitRadius','eccentricity','inclination','nodeAngle','phase','material'])if(typeof s[k]!=='number'||!Number.isFinite(s[k]))throw Error('行星布局缺少数值');if(s.radius<.5||s.radius>6||s.orbitRadius<8||s.orbitRadius>80||Math.abs(s.eccentricity)>.5||!vec(s.color,3,0,1)||!Number.isInteger(s.material)||s.material<0||s.material>4)throw Error('行星布局超出范围');return {id:String(s.id),parent_id:String(s.parent_id),radius:s.radius,orbitRadius:s.orbitRadius,eccentricity:s.eccentricity,inclination:s.inclination,nodeAngle:s.nodeAngle,phase:s.phase,material:s.material,color:s.color.slice()};});
 if(topics.length!==clean.chapters.reduce((n,c)=>n+c.topics.length,0))throw Error('布局含无对应内容的行星');
 for(const c of clean.chapters)for(const t of c.topics)if(topics.filter(s=>s.parent_id===c.id&&s.id===t.id).length!==1)throw Error('主题与行星不一一对应');
 clean.version='1.0';clean.owner_id=String(x.owner_id||'');clean.layout={version:'1.0',stars,topics};
 // Runtime import never receives the old owner's artwork or approval.
 clean.release={draft:true,share_allowed:false};clean.persona=null;clean.content_digest=null;
 return clean;
};
function adoptLayout(){
 const starList=profile.layout.stars;
 nodes.splice(0,nodes.length,...starList.map(s=>s.position.slice()));
 localNodes.splice(0,localNodes.length,...starList.map(s=>s.position.slice()));
 colors.splice(0,colors.length,...starList.map(s=>s.color.slice()));
 radii.splice(0,radii.length,...starList.map(s=>[5.8,4.5,6.2,4.8,5.15][s.material]));
 hoverGlow.splice(0,hoverGlow.length,...nodes.map(()=>0));
 starTypes.splice(0,starTypes.length,...starList.map(s=>STAR_TYPES[s.material]));
 planetCaption.splice(0,planetCaption.length,...starList.map(s=>STAR_CAPTIONS[s.material]));
 routeLocal.length=0;
 for(let i=0;i<localNodes.length-1;i++)for(let j=0;j<=28;j++){const t=j/28,p=lerp(localNodes[i],localNodes[i+1],t);p[1]+=Math.sin(t*Math.PI)*9;routeLocal.push(p);}
 document.documentElement.style.setProperty('--chapter-count',String(nodes.length));
}
// A registered native layer set belongs to the current person. Only layers
// explicitly marked 'auto' receive the reusable template's procedural treatment.
const liteMode=DEFAULT_PROFILE.mode==='lite';
const skillCurrentPersona=currentPersona;
currentPersona=function(){
 const d=skillCurrentPersona(),staticArt=d.art_status==='static'||d.art_mode==='static';
 return {...d,artReady:d.ready&&!staticArt&&(liteMode?d.art_mode==='layered'&&['generated','approved'].includes(d.art_status):d.art_status==='approved')};
};
const LITE_W=1080,LITE_H=1440;
const LITE_GOLD='<linearGradient id="lg" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#fff7dc"/><stop offset=".42" stop-color="#f1d28e"/><stop offset=".7" stop-color="#b98a45"/><stop offset="1" stop-color="#f6e0a8"/></linearGradient><linearGradient id="lf" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f3dca6"/><stop offset=".3" stop-color="#a8865a"/><stop offset=".55" stop-color="#f8e7bd"/><stop offset=".8" stop-color="#9c7a4c"/><stop offset="1" stop-color="#ecd29a"/></linearGradient>';
function liteCanvas(w=LITE_W,h=LITE_H){const c=document.createElement('canvas');c.width=w;c.height=h;return c;}
function liteRandom(){const d=currentPersona();let h=2166136261;for(const ch of String(d.title)+'|'+String(d.name)){h^=ch.codePointAt(0);h=Math.imul(h,16777619);}return seedRandom(h>>>0);}
function liteStar4(x,cx,cy,r,thin=.18){const t=r*thin;x.beginPath();x.moveTo(cx,cy-r);x.quadraticCurveTo(cx+t,cy-t,cx+r,cy);x.quadraticCurveTo(cx+t,cy+t,cx,cy+r);x.quadraticCurveTo(cx-t,cy+t,cx-r,cy);x.quadraticCurveTo(cx-t,cy-t,cx,cy-r);x.closePath();}
function liteStar4Path(cx,cy,r){const t=r*.18,f=v=>v.toFixed(1);return `M${f(cx)} ${f(cy-r)}Q${f(cx+t)} ${f(cy-t)} ${f(cx+r)} ${f(cy)}Q${f(cx+t)} ${f(cy+t)} ${f(cx)} ${f(cy+r)}Q${f(cx-t)} ${f(cy+t)} ${f(cx-r)} ${f(cy)}Q${f(cx-t)} ${f(cy-t)} ${f(cx)} ${f(cy-r)}Z`;}
function liteBackdrop(rnd){
 const c=liteCanvas(),x=c.getContext('2d'),W=LITE_W,H=LITE_H;
 let g=x.createLinearGradient(0,0,0,H);[[0,'#0d1a38'],[.42,'#172a52'],[.78,'#0b152c'],[1,'#060b18']].forEach(([o,s])=>g.addColorStop(o,s));x.fillStyle=g;x.fillRect(0,0,W,H);
 x.globalCompositeOperation='screen';
 for(const [cx,cy,r,col] of [[.12,.18,.55,'74,92,170'],[.9,.5,.5,'110,76,150'],[.2,.72,.45,'40,110,150'],[.75,.08,.4,'150,120,80'],[.5,.95,.5,'60,70,140']]){
  g=x.createRadialGradient(cx*W,cy*H,0,cx*W,cy*H,r*W);g.addColorStop(0,`rgba(${col},.32)`);g.addColorStop(1,`rgba(${col},0)`);x.fillStyle=g;x.fillRect(0,0,W,H);}
 const mx=W*(.64+rnd()*.14),my=H*.16,mr=W*.085;
 g=x.createRadialGradient(mx,my,mr*.6,mx,my,mr*4);g.addColorStop(0,'rgba(255,236,200,.42)');g.addColorStop(1,'rgba(255,236,200,0)');x.fillStyle=g;x.fillRect(0,0,W,H);
 for(let i=0;i<9;i++){const a=Math.PI*(.35+rnd()*.5),s=.02+rnd()*.03;x.beginPath();x.moveTo(mx,my);x.lineTo(mx+Math.cos(a-s)*H*1.3,my+Math.sin(a-s)*H*1.3);x.lineTo(mx+Math.cos(a+s)*H*1.3,my+Math.sin(a+s)*H*1.3);x.closePath();x.fillStyle=`rgba(255,230,190,${(.025+rnd()*.03).toFixed(3)})`;x.fill();}
 x.globalCompositeOperation='source-over';
 x.shadowColor='rgba(255,236,200,.9)';x.shadowBlur=60;
 g=x.createRadialGradient(mx-mr*.3,my-mr*.3,mr*.1,mx,my,mr);g.addColorStop(0,'#fffdf6');g.addColorStop(.75,'#f7ecd2');g.addColorStop(1,'#e8d3a6');x.fillStyle=g;x.beginPath();x.arc(mx,my,mr,0,Math.PI*2);x.fill();x.shadowBlur=0;
 for(let i=0;i<1100;i++){const sx=rnd()*W,sy=Math.pow(rnd(),1.35)*H,r=.5+Math.pow(rnd(),3)*1.8;x.fillStyle=`rgba(${rnd()<.2?'255,230,190':'220,232,255'},${(.18+rnd()*.7).toFixed(2)})`;x.beginPath();x.arc(sx,sy,r,0,Math.PI*2);x.fill();}
 for(let i=0;i<26;i++){const sx=rnd()*W,sy=Math.pow(rnd(),1.2)*H*.8,r=5+rnd()*11;x.fillStyle='rgba(255,246,222,.85)';liteStar4(x,sx,sy,r);x.fill();}
 x.strokeStyle='rgba(232,208,150,.28)';x.lineWidth=1.4;x.fillStyle='rgba(255,240,205,.8)';
 for(const [ox,oy] of [[.08,.1],[.7,.38],[.06,.5]]){const pts=[];let px=ox*W,py=oy*H;for(let i=0;i<5;i++){pts.push([px,py]);px+=40+rnd()*90;py+=(rnd()-.4)*90;}
  x.beginPath();pts.forEach(([a,b],i)=>i?x.lineTo(a,b):x.moveTo(a,b));x.stroke();pts.forEach(([a,b])=>{x.beginPath();x.arc(a,b,3,0,Math.PI*2);x.fill();});}
 x.globalCompositeOperation='screen';
 for(let i=0;i<10;i++){const cx=rnd()*W,cy=H*(.82+rnd()*.2),rx=W*(.25+rnd()*.3);g=x.createRadialGradient(cx,cy,0,cx,cy,rx);g.addColorStop(0,'rgba(120,140,200,.12)');g.addColorStop(1,'rgba(120,140,200,0)');x.fillStyle=g;x.fillRect(0,0,W,H);}
 x.globalCompositeOperation='source-over';
 g=x.createRadialGradient(W/2,H*.45,W*.35,W/2,H*.5,H*.75);g.addColorStop(0,'rgba(3,6,14,0)');g.addColorStop(1,'rgba(3,6,14,.62)');x.fillStyle=g;x.fillRect(0,0,W,H);
 return c.toDataURL('image/jpeg',.92);
}
function liteSparkles(rnd){
 const c=liteCanvas(),x=c.getContext('2d'),W=LITE_W,H=LITE_H;let placed=0,tries=0;
 while(placed<14&&tries++<400){const u=.05+rnd()*.9,v=.06+rnd()*.82;
  // Keep the face clear: sparkles sit around the figure, not on it.
  if(((u-.5)/.27)**2+((v-.34)/.2)**2<1)continue;
  const cx=u*W,cy=v*H,r=10+Math.pow(rnd(),2)*30;
  let g=x.createRadialGradient(cx,cy,0,cx,cy,r*1.6);g.addColorStop(0,'rgba(255,236,190,.55)');g.addColorStop(1,'rgba(255,220,150,0)');x.fillStyle=g;x.fillRect(cx-r*2,cy-r*2,r*4,r*4);
  g=x.createRadialGradient(cx,cy,0,cx,cy,r);g.addColorStop(0,'#fffef8');g.addColorStop(.35,'#ffe9b0');g.addColorStop(1,'rgba(230,180,90,.0)');x.fillStyle=g;liteStar4(x,cx,cy,r,.12);x.fill();
  if(r>22){x.save();x.globalAlpha=.55;x.fillStyle='#fff3d0';x.translate(cx,cy);x.rotate(Math.PI/4);liteStar4(x,0,0,r*.5,.14);x.fill();x.restore();}
  placed++;}
 for(let i=0;i<46;i++){const cx=rnd()*W,cy=H*(.05+rnd()*.9);if(((cx/W-.5)/.27)**2+((cy/H-.34)/.2)**2<1)continue;const r=1.5+rnd()*5;
  const g=x.createRadialGradient(cx,cy,0,cx,cy,r*2.2);g.addColorStop(0,`rgba(255,226,160,${(.25+rnd()*.4).toFixed(2)})`);g.addColorStop(1,'rgba(255,226,160,0)');x.fillStyle=g;x.beginPath();x.arc(cx,cy,r*2.2,0,Math.PI*2);x.fill();}
 return c.toDataURL('image/png');
}
async function liteLineart(src){
 // Line art comes from the subject's own edges (Sobel), so the foil glints follow the drawing.
 const w=540,h=720,c=liteCanvas(w,h),x=c.getContext('2d',{willReadFrequently:true});
 x.drawImage(await imageReady(src),0,0,w,h);const s=x.getImageData(0,0,w,h).data,out=x.createImageData(w,h),o=out.data,lum=new Float32Array(w*h);
 for(let p=0;p<w*h;p++)lum[p]=(s[p*4]*.299+s[p*4+1]*.587+s[p*4+2]*.114)*s[p*4+3]/255;
 o.fill(255);
 for(let y=1;y<h-1;y++)for(let X=1;X<w-1;X++){const p=y*w+X;if(s[p*4+3]<128)continue;
  const gx=lum[p-w+1]+2*lum[p+1]+lum[p+w+1]-lum[p-w-1]-2*lum[p-1]-lum[p+w-1],gy=lum[p+w-1]+2*lum[p+w]+lum[p+w+1]-lum[p-w-1]-2*lum[p-w]-lum[p-w+1];
  const m=Math.hypot(gx,gy),v=m<70?255:Math.max(0,255-(m-70)*2.2);o[p*4]=o[p*4+1]=o[p*4+2]=v;}
 x.putImageData(out,0,0);const big=liteCanvas();big.getContext('2d').drawImage(c,0,0,LITE_W,LITE_H);return big.toDataURL('image/png');
}
async function liteFlatten(keys){const c=liteCanvas(),x=c.getContext('2d');for(const k of keys)x.drawImage(await imageReady(HOLO_LAYERS[k]),0,0,LITE_W,LITE_H);return c.toDataURL('image/jpeg',.92);}
const liteUnits=s=>[...String(s)].reduce((n,ch)=>n+(ch.charCodeAt(0)>255?1:.58),0);
function liteTextSVG(d,artHref){
 const X=v8xml,who=(typeof summarizerInfo==='function'&&summarizerInfo().name)||'AI';
 const art=artHref?`<image href="${artHref}" x="0" y="0" width="600" height="800" preserveAspectRatio="xMidYMid slice"/>`:'';
 const tl=[...d.title].length,ts=tl<=3?66:tl===4?58:tl===5?50:tl===6?44:38,tw=liteUnits(d.title)*ts*1.14;
 // Tagline column: break after punctuation first, then wrap long pieces at 8 characters.
 const tag=String(d.line).split(/(?<=[，。、；：！？,.;:!?])/).flatMap(s=>wrapCard(s.trim(),8)).filter(Boolean).slice(0,6),tagW=Math.max(...tag.map(liteUnits))*12.5+22;
 const kws=d.keywords.slice(0,4);while(kws.length>2&&kws.reduce((n,k)=>n+liteUnits(k)*11+26,0)+(kws.length-1)*16>500)kws.pop();
 const pw=kws.map(k=>liteUnits(k)*11+26),total=pw.reduce((a,b)=>a+b,0)+(kws.length-1)*16;let px=300-total/2,pills='';
 kws.forEach((k,i)=>{pills+=`<rect x="${px.toFixed(1)}" y="683" width="${pw[i].toFixed(1)}" height="21" rx="10.5" fill="#0a1222" fill-opacity=".55" stroke="url(#lf)" stroke-width=".9"/><text x="${(px+pw[i]/2).toFixed(1)}" y="697.5" text-anchor="middle" font-size="10.5" letter-spacing="1" fill="#efe2c4">${X(k)}</text>`;px+=pw[i];if(i<kws.length-1){pills+=`<path d="M${(px+8).toFixed(1)} 690l3 3.5-3 3.5-3-3.5z" fill="#e6c886"/>`;px+=16;}});
 const corner=`<path d="M14 64V30q0-16 16-16h34" fill="none" stroke="url(#lf)" stroke-width="1.6"/><path d="M22 52V36q0-14 14-14h16" fill="none" stroke="url(#lf)" stroke-width=".8" opacity=".8"/><path d="M14 14l5 5-5 5-5-5z" fill="#f2d79c"/><circle cx="64" cy="14" r="1.8" fill="#f2d79c"/><circle cx="14" cy="64" r="1.8" fill="#f2d79c"/>`;
 const moons=y=>`<circle cx="0" cy="${y-22}" r="3.2" fill="#f1d9a0" opacity=".9"/><circle cx="0" cy="${y}" r="4.4" fill="none" stroke="#f1d9a0" stroke-width="1.2"/><circle cx="0" cy="${y+22}" r="3.2" fill="#f1d9a0" opacity=".55"/>`;
 return `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1440" viewBox="0 0 600 800"><style>text{font-family:'Songti SC','Noto Serif CJK SC','Source Han Serif SC','STSong','SimSun',serif}.k{font-family:'STKaiti','Kaiti SC','KaiTi','Songti SC','Noto Serif CJK SC','SimSun',serif}.e{font-family:'Didot','Bodoni 72','Bodoni MT','Playfair Display',Georgia,'Times New Roman',serif}</style>
<defs>${LITE_GOLD}<linearGradient id="lt" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#050a16" stop-opacity=".6"/><stop offset="1" stop-color="#050a16" stop-opacity="0"/></linearGradient>
<linearGradient id="lbot" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#060c1a" stop-opacity="0"/><stop offset=".4" stop-color="#060c1a" stop-opacity=".62"/><stop offset="1" stop-color="#050913" stop-opacity=".9"/></linearGradient>
<filter id="glow" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur in="SourceAlpha" stdDeviation="5" result="b"/><feFlood flood-color="#ffd890" flood-opacity=".45"/><feComposite in2="b" operator="in" result="g"/><feMerge><feMergeNode in="g"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="soft"><feGaussianBlur stdDeviation="1.4"/></filter><clipPath id="lc"><rect x="6" y="6" width="588" height="788" rx="16"/></clipPath></defs>
<g clip-path="url(#lc)">${art}<rect width="600" height="160" fill="url(#lt)"/><rect y="470" width="600" height="330" fill="url(#lbot)"/></g>
<rect x="4" y="4" width="592" height="792" rx="18" fill="none" stroke="url(#lf)" stroke-width="2.4"/><rect x="12" y="12" width="576" height="776" rx="12" fill="none" stroke="url(#lf)" stroke-width=".8" opacity=".75"/>
${corner}<g transform="translate(600 0) scale(-1 1)">${corner}</g><g transform="translate(0 800) scale(1 -1)">${corner}</g><g transform="translate(600 800) scale(-1 -1)">${corner}</g>
<g transform="translate(12 0)">${moons(400)}</g><g transform="translate(588 0)">${moons(400)}</g>
<path d="M266 12h26M308 12h26" stroke="#f1d9a0" stroke-width="1"/><path d="${liteStar4Path(300,12,8)}" fill="#fff1c8"/>
<g filter="url(#glow)"><text class="e" x="30" y="84" font-size="58" font-weight="700" fill="url(#lg)" stroke="#3b2a10" stroke-width=".7" paint-order="stroke">SSR</text></g>
<path d="M32 98h10M120 98h10" stroke="#e8cd92" stroke-width=".8"/><text class="e" x="81" y="101" text-anchor="middle" font-size="7.5" letter-spacing="3.6" fill="#e8d7ae">TWINLIGHT</text>
<rect x="24" y="122" width="${tagW.toFixed(1)}" height="${(tag.length*19+18).toFixed(1)}" rx="3" fill="#0a1222" fill-opacity=".45"/><path d="M28 128v${(tag.length*19+6).toFixed(1)}" stroke="url(#lf)" stroke-width="1"/>
${tag.map((s,i)=>`<text x="36" y="${142+i*19}" font-size="11.5" letter-spacing="1.5" fill="#f2e7cf">${X(s)}</text>`).join('')}
<rect x="${(574-liteUnits(who+' 眼中的你')*11-18).toFixed(1)}" y="24" width="${(liteUnits(who+' 眼中的你')*11+18).toFixed(1)}" height="22" rx="3" fill="#0a1222" fill-opacity=".6" stroke="url(#lf)" stroke-width=".7"/><text x="${(574-9).toFixed(1)}" y="39" text-anchor="end" font-size="11" letter-spacing="1" fill="#f2e7cf">${X(who)} 眼中的你</text>
<text class="e" transform="translate(577 250) rotate(90)" font-size="7.5" letter-spacing="3" fill="#e8d7ae" opacity=".8">UNIQUE PERSONA · ${X(d.name)}</text>
<path d="M296 525a17 17 0 1 0 16 25a13.5 13.5 0 1 1-16-25z" fill="url(#lg)" filter="url(#glow)"/><path d="${liteStar4Path(322,530,6)}" fill="#fff1c8"/><path d="${liteStar4Path(276,548,4)}" fill="#fff1c8"/>
<path d="M${(300-tw/2-40).toFixed(1)} 612q${(tw/2+40).toFixed(1)} -46 ${(tw+80).toFixed(1)} 0" fill="none" stroke="#f1d9a0" stroke-width=".9" opacity=".55"/>
<g filter="url(#glow)"><text class="k" x="300" y="${(600+ts*.32).toFixed(1)}" text-anchor="middle" font-size="${ts}" letter-spacing="${(ts*.12).toFixed(1)}" fill="url(#lg)" stroke="#2a1c0a" stroke-width="1" paint-order="stroke">${X(d.title)}</text></g>
<path d="${liteStar4Path(300-tw/2-24,598,11)}" fill="#fff4d2"/><path d="${liteStar4Path(300+tw/2+24,590,14)}" fill="#fff4d2"/>
<text class="e" x="300" y="646" text-anchor="middle" font-size="11.5" letter-spacing="5.5" fill="#efe2c4">${X(String(d.english_title).toUpperCase())}</text>
<path d="M200 667h46M354 667h46" stroke="#e8cd92" stroke-width=".8"/><text x="300" y="671" text-anchor="middle" font-size="10.5" letter-spacing="3" fill="#e8d7ae">${X(who)} 眼中的你</text>
${pills}
<text class="e" x="300" y="731" text-anchor="middle" font-size="8.5" letter-spacing="3" fill="#e2cf9f">SSR · 1/1</text>
<path d="M232 746h52M316 746h52" stroke="#e8cd92" stroke-width=".7"/><path d="${liteStar4Path(300,746,7)}" fill="#fff1c8"/>
<text class="e" x="300" y="766" text-anchor="middle" font-size="7.5" letter-spacing="5" fill="#e8d7ae">TWINLIGHT</text><text class="e" x="300" y="778" text-anchor="middle" font-size="6" letter-spacing="2.4" fill="#cdbb92" opacity=".75">AI IMPRESSION · ${X(d.edition)}</text></svg>`;
}
let liteArtReady=Promise.resolve(),liteCardImage=V9_CARD_IMAGE==='auto'?'':V9_CARD_IMAGE;
if(liteMode){
 const auto=k=>HOLO_LAYERS[k]==='auto';
 const setLayer=(k,src)=>{HOLO_LAYERS[k]=src;const im=holoFallback.querySelector(`img[data-layer="${k}"]`);if(im)im.src=src;};
 const rnd=liteRandom(),staticArt=currentPersona().art_mode==='static'||currentPersona().art_status==='static';
 if(auto('background'))setLayer('background',liteBackdrop(rnd));
 if(auto('effects'))setLayer('effects',staticArt?liteCanvas().toDataURL('image/png'):liteSparkles(rnd));
 if(auto('text'))setLayer('text',v8URI(liteTextSVG(currentPersona())));
 liteArtReady=(async()=>{
  if(auto('lineart'))HOLO_LAYERS.lineart=await liteLineart(HOLO_LAYERS.subject);
  // Rasterize once so WebGL never depends on SVG-texture support.
  if(HOLO_LAYERS.text.startsWith('data:image/svg')){const c=liteCanvas();c.getContext('2d').drawImage(await imageReady(HOLO_LAYERS.text),0,0,LITE_W,LITE_H);HOLO_LAYERS.text=c.toDataURL('image/png');}
  if(!liteCardImage){liteCardImage=await liteFlatten(['background','spirit','subject','effects','text']);refreshIdentity();}
 })().catch(e=>console.warn('Lite card layers:',String(e)));
 const liteInit=initHolo;initHolo=async function(){await liteArtReady;return liteInit();};
}
// The flattened front already contains its one text layer. Wrapping it must
// never paint the default title or frame a second time over supplied artwork.
const skillCardSVG=buildCardSVG;
buildCardSVG=function(side='front'){
 const d=currentPersona();if(side!=='front'||!d.ready)return skillCardSVG(side);
 const src=liteMode?liteCardImage||HOLO_LAYERS.background:V9_CARD_IMAGE;
 return `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1440" viewBox="0 0 600 800"><title>${v8xml('SSR · '+d.title+' · '+d.name)}</title><image href="${v8xml(src)}" x="0" y="0" width="600" height="800" preserveAspectRatio="none"/></svg>`;
};
const skillCreateNav=createNav;
createNav=function(){adoptLayout();skillCreateNav();};
const skillRefresh=refreshIdentity;
refreshIdentity=function(){skillRefresh();const d=currentPersona();
 $('cardSave').disabled=!d.shareAllowed;$('cardNativeShare').disabled=!d.shareAllowed;
 const staticArt=d.ready&&(d.art_mode==='static'||d.art_status==='static'),pendingArt=d.ready&&!staticArt&&!d.artReady&&d.art_status==='generated';
 $('cardFront').alt=d.artReady?'SSR '+d.title+'，'+d.name+' 的独立分层闪卡':staticArt?'SSR '+d.title+'，'+d.name+' 的静态原型；分层尚未完成':pendingArt?'SSR '+d.title+'，'+d.name+' 的分层插画；待审查':'SSR 图层示意；专属插画尚待生成和审查';
 let notice=$('skillArtNotice');if(!notice){notice=el('p','skill-art-notice');notice.id='skillArtNotice';$('identityHeading').after(notice);}notice.hidden=d.artReady;notice.textContent=staticArt?'静态原型，分层尚未完成':pendingArt?'分层插画 · 待审查':liteMode?'占位卡面 · 还没有放入你的插画':'分层示意 · 专属插画待生成与审查';
 if(staticArt)document.querySelector('.identity-message').textContent=d.line||'你的卡面原型。';
 else if(pendingArt)document.querySelector('.identity-message').textContent=(d.line||'')+' · 卡面待审查。';
 else if(!d.artReady)document.querySelector('.identity-message').textContent=(d.line||'')+(liteMode?' · 当前为占位卡面。':' · 当前为分层示意素材，专属卡面待生成与审查。');
};
const skillExport=exportCardBlob;
exportCardBlob=async function(side){if(!currentPersona().shareAllowed)throw Error('当前资料/图层尚未取得分享审查许可。');return skillExport(side);};
const originalApply=$('applyJson').onclick;
$('applyJson').onclick=function(){originalApply();refreshIdentity();};
const draft=el('span','skill-draft');draft.textContent='本地预览 · 待审查';draft.hidden=!profile.release.draft;document.body.append(draft);
const originalImportApply=$('applyJson').onclick;$('applyJson').onclick=()=>{originalImportApply();draft.hidden=false;};
const sourcesBody=$('infoDialog').querySelector('.dialog-body');
const coverageLine=el('p');coverageLine.textContent='材料范围：'+(profile.coverage?.description||'本次导入摘要；并非完整账户历史')+(liteMode?'':' 原始引用、排除项和冲突处理见本地 review.md。');sourcesBody.prepend(coverageLine);
refreshIdentity();
window.twinlightSkill={getState:()=>({version:'1.0',stars:nodes.length,planets:personalSatellites.length,owner:profile.owner_id,shareAllowed:currentPersona().shareAllowed,artReady:currentPersona().artReady,artStatus:currentPersona().art_status,artMode:currentPersona().art_mode,layout:profile.layout}),validate:validateProfile};
