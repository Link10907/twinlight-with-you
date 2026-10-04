/* Local-only viewer. Native images retain their original canvas and pixels. */
(function(){
'use strict';
const $=id=>document.getElementById(id),B=JSON.parse($('bundle').textContent),L=window.TwinlightLite;
const ROLES=['background','spirit','subject','effects','text','lineart'];
const TOKENS=/__(PROFILE|CARD_DATA|CARD_LAYERS|V9_CARD_IMAGE|DEPTH_BG|DEPTH_SUBJECT|DEPTH_EFFECTS)__/g;
const state={check:null,art:null,artError:null,html:null,data:null,url:null,revision:0};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safe=v=>JSON.stringify(v).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
let toastTimer,timer;
function toast(msg){$('toast').textContent=msg;$('toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('show'),1800);}
async function copyText(text){try{await navigator.clipboard.writeText(text);}catch(_){const a=document.createElement('textarea');a.value=text;a.style.position='fixed';a.style.opacity='0';document.body.append(a);a.select();document.execCommand('copy');a.remove();}toast('已复制');}
document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=()=>copyText($(b.dataset.copy).textContent));
$('copyPrompt').onclick=()=>copyText(B.prompt);
$('copyCardPrompt').onclick=()=>copyText(B.cardPrompt);
function invalidate(){state.revision++;state.html=null;$('confirmCheck').checked=false;$('buildPanel').hidden=true;sync();}
function currentDigest(){return state.check?.ok?L.toProfile(state.check.data,{generatedAt:'2000-01-01T00:00:00Z'}).persona.persona_digest:null;}
function artChoice(){return state.art&&!state.artError?state.art.mode:'placeholder';}
function sync(){$('generate').disabled=!(state.check?.ok&&$('confirmCheck').checked&&!state.artError);}
function artStatus(){
 if(state.art&&state.art.personaDigest!==currentDigest())state.artError='卡图属于另一份人物设定。请清空卡图，或导入与当前结果匹配的新卡图。';
 const el=$('artStatus'),mode=artChoice();
 if(state.artError)el.innerHTML='<span class="pill bad">卡图未通过</span> '+esc(state.artError);
 else el.innerHTML=mode==='layered'?'<span class="pill ok">独立分层</span> 原生透明图层已就绪。请检查构图和文字。':mode==='static'?'<span class="pill warn">静态原型</span> 原图预览，分层尚未完成。':'<span class="pill dim">占位卡</span> 可以先看星系，再让 AI 完成专属卡图。';
 $('artThumb').hidden=!state.art||!!state.artError;if(state.art&&!state.artError)$('artThumb').src=state.art.preview;
 sync();
}
function runCheck(){
 const text=$('jsonInput').value,panel=$('checkPanel');
 if(!text.trim()){state.check=null;panel.hidden=true;$('contentDetails').hidden=true;$('artPromptBox').hidden=true;artStatus();return;}
 const r=L.checkText(text,B.schema);state.check=r;panel.hidden=false;panel.className='panel '+(r.ok?'ok':'bad');
 const warn=r.warnings.length?'<p class="warnings">已修正：'+r.warnings.map(esc).join('；')+'</p>':'';
 if(r.ok)panel.innerHTML='<span class="pill ok">已读入</span> '+r.stats.themes+' 个主题 · '+r.stats.topics+' 颗行星'+warn;
 else{panel.innerHTML='<span class="pill bad">'+r.errors.length+' 处需要修正</span><ul class="errors">'+r.errors.map(e=>'<li><code>'+esc(e.path)+'</code>'+esc(e.message)+'</li>').join('')+'</ul><button id="copyRepair">复制修复提示给 AI</button>'+warn;$('copyRepair').onclick=()=>copyText(L.repairPrompt(r.errors));}
 renderPreview(r.ok?r.data:null);artStatus();
}
function renderPreview(d){
 $('contentDetails').hidden=!d;$('artPromptBox').hidden=!d;if(!d)return;
 $('contentPreview').innerHTML='<div class="panel"><p class="hint">'+esc(d.name)+' · 总结者 '+esc(d.summarizer)+'</p>'+d.themes.map(t=>'<div class="preview-theme"><h3>'+esc(t.label)+'<small>'+esc(t.english)+'</small></h3><p><b>'+esc(t.headline)+'</b></p>'+t.story.map(s=>'<p>'+esc(s)+'</p>').join('')+'<p class="hint">'+esc(t.reflection)+'</p><ul>'+t.topics.map(p=>'<li>'+esc(p.label)+' <span class="basis">'+esc(L.BASIS[p.basis][0])+'</span> '+esc(p.summary)+'</li>').join('')+'</ul></div>').join('')+'<div class="preview-card"><div><div class="title">'+esc(d.card.title)+'</div><p>'+esc(d.card.english_title)+'</p><p>'+d.card.keywords.map(esc).join(' · ')+'</p><p>'+esc(d.card.tagline)+'</p><p class="hint">'+esc(d.card.reflection)+'</p></div></div></div>';
 $('promptRows').replaceChildren();
 const cardInput={twinlight:'card-1',name:d.name,summarizer:d.summarizer,card:d.card};
 const instruction=B.cardPrompt+'\n\n当前内容作为只读输入，请按实际确认情况核对，不改变人物绑定：\n'+JSON.stringify(cardInput,null,2);
 const row=document.createElement('div');row.className='copy-row';const code=document.createElement('code');code.textContent=instruction;const btn=document.createElement('button');btn.textContent='复制闪卡说明与当前内容';btn.onclick=()=>copyText(instruction);row.append(code,btn);$('promptRows').append(row);
}
$('jsonInput').oninput=()=>{invalidate();clearTimeout(timer);timer=setTimeout(runCheck,200);};
$('jsonFile').onchange=async e=>{const f=e.target.files[0];e.target.value='';if(!f)return;if(f.size>1024*1024){toast('数据文件不能超过 1 MB');return;}invalidate();$('jsonInput').value=await f.text();runCheck();};
$('loadExample').onclick=()=>{invalidate();state.art=null;state.artError=null;$('jsonInput').value=B.example;runCheck();toast('已加载纯虚构示例');};
function loadImage(src){return new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>resolve(i);i.onerror=()=>reject(Error('图片无法读取'));i.src=src;});}
function readURI(file){return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(Error('文件无法读取'));r.readAsDataURL(file);});}
async function inspectImage(src,name,{keepAlpha=false}={}){
 if(typeof src!=='string'||!/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(src))throw Error(name+'：只接受本地 PNG / JPG / WebP 图层');
 if(src.length>34*1024*1024)throw Error(name+'：图片超过 24 MB');
 const im=await loadImage(src),w=im.naturalWidth,h=im.naturalHeight;
 if(w*h>16000000||Math.min(w,h)<256||Math.abs(w/h-.75)>=.01)throw Error(name+'：需要同一完整 3:4 画布，短边至少 256 像素');
 const c=document.createElement('canvas');c.width=w;c.height=h;const g=c.getContext('2d',{willReadFrequently:true});g.drawImage(im,0,0);
 const px=g.getImageData(0,0,w,h).data,alpha=keepAlpha?new Uint8Array(w*h):null;let transparent=0,occupied=0,opaque=0,lo=255,hi=0;
 for(let i=0;i<px.length;i+=4){const a=px[i+3];if(alpha)alpha[i/4]=a;if(a<16)transparent++;else occupied++;if(a===255)opaque++;const v=(px[i]*299+px[i+1]*587+px[i+2]*114)/1000;lo=Math.min(lo,v);hi=Math.max(hi,v);}
 return {im,w,h,transparent:transparent/(w*h),occupied:occupied/(w*h),opaque:opaque===w*h,lo,hi,...(alpha?{alpha}:{})};
}
function validateComposition(lock,personaDigest,images){
 const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k),object=o=>!!o&&typeof o==='object'&&!Array.isArray(o);
 const fields=['version','persona_digest','canvas','source_prototype_sha256','subject_bounds','subject_center_region','text_safe_regions','max_text_overlap'];
 if(!object(lock)||Object.keys(lock).some(k=>!fields.includes(k))||lock.version!=='1.0'||typeof lock.persona_digest!=='string'||!/^[a-f0-9]{64}$/.test(lock.persona_digest))throw Error('composition：构图锁格式不正确');
 if(lock.persona_digest!==personaDigest)throw Error('composition：构图锁属于另一份人物设定');
 const canvas=lock.canvas,w=images.subject.w,h=images.subject.h;
 if(!object(canvas)||Object.keys(canvas).some(k=>!['width','height'].includes(k))||!Number.isInteger(canvas.width)||!Number.isInteger(canvas.height)||canvas.width<256||canvas.height<256||canvas.width!==w||canvas.height!==h)throw Error('composition.canvas：必须等于图层的实际画布，不会裁切或重摆');
 if(own(lock,'source_prototype_sha256')&&(typeof lock.source_prototype_sha256!=='string'||!/^[a-f0-9]{64}$/.test(lock.source_prototype_sha256)))throw Error('composition.source_prototype_sha256：需要有效的原型哈希');
 const rectangle=(r,name)=>{if(!Array.isArray(r)||r.length!==4||r.some(v=>typeof v!=='number'||!Number.isFinite(v)||v<0||v>1)||!(r[0]<r[2]&&r[1]<r[3]))throw Error('composition.'+name+'：需要有效的归一化正矩形');};
 for(const name of ['subject_bounds','subject_center_region'])if(own(lock,name))rectangle(lock[name],name);
 if(own(lock,'text_safe_regions')){if(!Array.isArray(lock.text_safe_regions)||lock.text_safe_regions.length<1||lock.text_safe_regions.length>8)throw Error('composition.text_safe_regions：需要 1–8 个明确留白区域');lock.text_safe_regions.forEach((r,i)=>rectangle(r,'text_safe_regions['+i+']'));}
 if(own(lock,'max_text_overlap')&&(!own(lock,'text_safe_regions')||typeof lock.max_text_overlap!=='number'||!Number.isFinite(lock.max_text_overlap)||lock.max_text_overlap<0||lock.max_text_overlap>.25))throw Error('composition.max_text_overlap：需要明确留白区域及 0–0.25 的占用上限');
 const alpha=images.subject.alpha;let left=w,top=h,right=0,bottom=0,mass=0,xMass=0,yMass=0;
 for(let i=0;i<alpha.length;i++){const a=alpha[i];if(a<16)continue;const x=i%w,y=Math.floor(i/w);left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x+1);bottom=Math.max(bottom,y+1);mass+=a;xMass+=(x+.5)*a;yMass+=(y+.5)*a;}
 if(!mass)throw Error('composition.subject：无法检查空主体');
 const bounds=[left/w,top/h,right/w,bottom/h],report={provided:true,canvas:[w,h],subject_bounds:bounds,quality_verified:false};
 if(own(lock,'subject_bounds')){const r=lock.subject_bounds;if(!(bounds[0]>=r[0]&&bounds[1]>=r[1]&&bounds[2]<=r[2]&&bounds[3]<=r[3]))throw Error('composition.subject_bounds：主体超出锁定范围，请参考原型重生成主体');}
 if(own(lock,'subject_center_region')){const center=[xMass/mass/w,yMass/mass/h],r=lock.subject_center_region;if(!(center[0]>=r[0]&&center[0]<=r[2]&&center[1]>=r[1]&&center[1]<=r[3]))throw Error('composition.subject_center_region：主体 alpha 中心超出锁定范围');report.subject_alpha_center=center;}
 if(own(lock,'text_safe_regions')){report.text_safe_regions=[];const spirit=images.spirit.alpha,effects=images.effects.alpha;for(const [i,r] of lock.text_safe_regions.entries()){const x0=Math.floor(r[0]*w),y0=Math.floor(r[1]*h),x1=Math.ceil(r[2]*w),y1=Math.ceil(r[3]*h);let occupied=0;for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++){const p=y*w+x;if(alpha[p]>=16||spirit[p]>=16||effects[p]>=16)occupied++;}const overlap=occupied/((x1-x0)*(y1-y0));if(overlap>(lock.max_text_overlap??.05))throw Error('composition.text_safe_regions['+i+']：主体或前景占据文字留白，请重生成对应图层');report.text_safe_regions.push({region:r,occupied_fraction:overlap});}}
 if(own(lock,'source_prototype_sha256')){report.source_prototype_sha256=lock.source_prototype_sha256;report.prototype_hash_verified_by_layer_validator=false;}
 return report;
}
async function validateCard(card){
 if(!['generated','approved','placeholder'].includes(card.art_status)||card.twinlight_card!=='layers-1')throw Error('这不是有效的 Twinlight 分层卡');
 if(card.persona_digest!==currentDigest())throw Error('卡图属于另一份人物设定，请让 AI 为当前用户重新生成。');
 const d=card.depths;if(!d||!(d.background>=-.4&&d.background<=-.05&&d.subject>=.1&&d.subject<=.6&&d.effects>=.15&&d.effects<=.7&&d.subject<d.effects&&d.text===0))throw Error('图层景深设置不正确');
 const hasLock=Object.prototype.hasOwnProperty.call(card,'composition'),images={};for(const role of ROLES){const x=await inspectImage(card.layers?.[role],role,{keepAlpha:hasLock&&['subject','spirit','effects'].includes(role)});images[role]=x;if(role==='background'&&!x.opaque)throw Error('背景层必须完整且不透明');if(['subject','effects','text'].includes(role)&&(x.transparent<=.01||x.occupied<=.0005))throw Error(role+'：需要真实 alpha 透明图层；不会自动抠图。');if(role==='lineart'&&!(x.lo<128&&x.hi>200))throw Error('线稿需要与主体对应的深色轮廓和白底');}
 const first=images.background;if(ROLES.some(k=>images[k].w!==first.w||images[k].h!==first.h)||!Array.isArray(card.canvas)||card.canvas[0]!==first.w||card.canvas[1]!==first.h)throw Error('所有图层必须保留完全相同的画布尺寸与坐标');
 const compositionChecks=hasLock?validateComposition(card.composition,card.persona_digest,images):null;
 const flat=document.createElement('canvas');flat.width=first.w;flat.height=first.h;const g=flat.getContext('2d');for(const role of ROLES.filter(k=>k!=='lineart'))g.drawImage(images[role].im,0,0);
 return {mode:card.art_status==='placeholder'?'placeholder':'layered',status:card.art_status,personaDigest:card.persona_digest,layers:card.layers,depths:d,preview:flat.toDataURL('image/jpeg',.92),...(hasLock?{composition:card.composition,compositionChecks}:{})};
}
async function importLayers(files){
 invalidate();const revision=state.revision;state.art=null;state.artError=null;
 try{
  if(!state.check?.ok)throw Error('请先放入有效的 AI 结果');
  if(files.reduce((n,f)=>n+f.size,0)>160*1024*1024)throw Error('卡片包不能超过 160 MB');
  const jsons=files.filter(f=>f.name.toLowerCase().endsWith('.json'));if(jsons.length!==1)throw Error('请选择一个卡片包，或一个图层清单和它的六张图片');
  const input=JSON.parse(await jsons[0].text());let card=input;
  if(input.twinlight_card!=='layers-1'){
   if(input.schema_version!=='1.0'||!input.assets)throw Error('找不到有效的图层清单');
   const layers={};for(const role of ROLES){const path=input.assets[role];if(typeof path!=='string'||path.split(/[\\/]/).includes('..')||/^(?:[a-z]+:|[\\/])/i.test(path))throw Error('图层路径只能指向本次本地文件');const name=path.split(/[\\/]/).pop(),matches=files.filter(f=>f.name===name);if(matches.length!==1)throw Error('缺少或重名图层：'+name);if(matches[0].size>24*1024*1024)throw Error(name+' 超过 24 MB');layers[role]=await readURI(matches[0]);}
   const bg=await loadImage(layers.background);card={twinlight_card:'layers-1',persona_digest:input.persona_digest,art_status:input.art_status,layers,depths:input.depths,canvas:[bg.naturalWidth,bg.naturalHeight],...(Object.prototype.hasOwnProperty.call(input,'composition')?{composition:input.composition}:{})};
  }
  const art=await validateCard(card);if(revision!==state.revision)return;state.art=art;
 }catch(e){if(revision!==state.revision)return;state.artError=e.message;}
 artStatus();
}
$('layerFiles').onchange=e=>{const files=Array.from(e.target.files);e.target.value='';if(files.length)importLayers(files);};
$('prototypeFile').onchange=async e=>{
 const file=e.target.files[0];e.target.value='';if(!file)return;invalidate();const revision=state.revision;state.art=null;state.artError=null;
 try{if(!state.check?.ok)throw Error('请先放入有效的 AI 结果');if(file.size>20*1024*1024)throw Error('原型超过 20 MB');const src=await readURI(file),x=await inspectImage(src,'静态原型');if(Math.min(x.w,x.h)<512)throw Error('静态原型短边至少 512 像素');if(revision!==state.revision)return;state.art={mode:'static',status:'static',personaDigest:currentDigest(),layers:{background:src,subject:B.clear,spirit:B.clear,effects:B.clear,lineart:'auto',text:'auto'},depths:B.depths.static,preview:src};}catch(err){if(revision!==state.revision)return;state.artError=err.message;}artStatus();
};
$('clearArt').onclick=()=>{invalidate();state.art=null;state.artError=null;artStatus();};
function composeArt(){if(state.artError)throw Error(state.artError);if(state.art)return state.art;return {mode:'placeholder',status:'placeholder',layers:{background:'auto',subject:B.placeholder.subject,spirit:B.clear,effects:'auto',lineart:'auto',text:'auto'},depths:B.depths.layered,preview:'auto'};}
$('confirmCheck').onchange=sync;
$('generate').onclick=async()=>{
 const btn=$('generate');btn.disabled=true;$('genStatus').textContent='正在打开…';
 try{if(!state.check?.ok||!$('confirmCheck').checked)throw Error('请先检查并确认当前内容');artStatus();const art=composeArt(),data=state.check.data,profile=L.toProfile(data,{generatedAt:new Date().toISOString().replace(/\.\d{3}Z$/,'Z'),artStatus:art.status,artMode:art.mode,confirmed:true,aiHistory:B.aiHistory});
  const values={PROFILE:safe(profile),CARD_DATA:safe(profile.persona),CARD_LAYERS:safe(art.layers),V9_CARD_IMAGE:art.mode==='layered'?art.preview:'auto',DEPTH_BG:String(art.depths.background),DEPTH_SUBJECT:String(art.depths.subject),DEPTH_EFFECTS:String(art.depths.effects)};
  state.html=B.template.replace(TOKENS,(m,k)=>values[k]);state.data=data;$('buildPanel').hidden=false;$('buildPanel').className='panel ok';$('buildPanel').innerHTML='<p>'+data.themes.length+' 个主题 · '+profile.layout.topics.length+' 颗行星 · '+({layered:'独立分层卡',static:'静态原型',placeholder:'占位卡'})[art.mode]+'</p><button id="reopen">再次观看</button>';$('reopen').onclick=openPreview;$('genStatus').textContent='';openPreview();
 }catch(e){$('genStatus').textContent=e.message;}finally{sync();}
};
function fileName(ext){return 'Twinlight-'+String(state.data.name).replace(/[\\/:*?"<>|\s]+/g,'_').slice(0,32)+ext;}
function save(blob,name){const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),2000);}
function openPreview(){if(state.url)URL.revokeObjectURL(state.url);state.url=URL.createObjectURL(new Blob([state.html],{type:'text/html'}));$('previewTitle').textContent=state.data.name+' 的星系';$('previewFrame').src=state.url;$('previewLayer').hidden=false;document.body.style.overflow='hidden';}
$('closePreview').onclick=()=>{$('previewLayer').hidden=true;$('previewFrame').src='about:blank';document.body.style.overflow='';};
$('downloadHtml').onclick=()=>save(new Blob([state.html],{type:'text/html'}),fileName('.html'));
$('downloadJson').onclick=()=>save(new Blob([JSON.stringify(state.data,null,2)+'\n'],{type:'application/json'}),fileName('.json'));
artStatus();
window.twinlightViewer={getState:()=>({ok:!!state.check?.ok,errors:state.check?.errors||[],warnings:state.check?.warnings||[],art:artChoice(),artError:state.artError,built:!!state.html,htmlBytes:state.html?state.html.length:0,composition:state.art?.composition||null,compositionChecks:state.art?.compositionChecks||null}),html:()=>state.html,check:runCheck};
})();
