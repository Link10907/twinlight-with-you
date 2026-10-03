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
 const p=L.artPrompts(d.card);$('promptRows').replaceChildren();
 for(const [key,label] of [['prototype','原型'],['subject','主体'],['background','背景'],['effects','前景'],['text','文字']]){const row=document.createElement('div');row.className='copy-row';const code=document.createElement('code');code.id=key+'Prompt';code.textContent=p[key];const btn=document.createElement('button');btn.textContent='复制'+label;btn.onclick=()=>copyText(p[key]);row.append(code,btn);$('promptRows').append(row);}
}
$('jsonInput').oninput=()=>{invalidate();clearTimeout(timer);timer=setTimeout(runCheck,200);};
$('jsonFile').onchange=async e=>{const f=e.target.files[0];e.target.value='';if(!f)return;if(f.size>1024*1024){toast('数据文件不能超过 1 MB');return;}invalidate();$('jsonInput').value=await f.text();runCheck();};
$('loadExample').onclick=()=>{invalidate();state.art=null;state.artError=null;$('jsonInput').value=B.example;runCheck();toast('已加载纯虚构示例');};
function loadImage(src){return new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>resolve(i);i.onerror=()=>reject(Error('图片无法读取'));i.src=src;});}
function readURI(file){return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(Error('文件无法读取'));r.readAsDataURL(file);});}
async function inspectImage(src,name){
 if(typeof src!=='string'||!/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(src))throw Error(name+'：只接受本地 PNG / JPG / WebP 图层');
 if(src.length>34*1024*1024)throw Error(name+'：图片超过 24 MB');
 const im=await loadImage(src),w=im.naturalWidth,h=im.naturalHeight;
 if(w*h>16000000||Math.min(w,h)<256||Math.abs(w/h-.75)>=.01)throw Error(name+'：需要同一完整 3:4 画布，短边至少 256 像素');
 const c=document.createElement('canvas');c.width=w;c.height=h;const g=c.getContext('2d',{willReadFrequently:true});g.drawImage(im,0,0);
 const px=g.getImageData(0,0,w,h).data;let transparent=0,occupied=0,opaque=0,lo=255,hi=0;
 for(let i=0;i<px.length;i+=4){const a=px[i+3];if(a<16)transparent++;else occupied++;if(a===255)opaque++;const v=(px[i]*299+px[i+1]*587+px[i+2]*114)/1000;lo=Math.min(lo,v);hi=Math.max(hi,v);}
 return {im,w,h,transparent:transparent/(w*h),occupied:occupied/(w*h),opaque:opaque===w*h,lo,hi};
}
async function validateCard(card){
 if(!['generated','approved','placeholder'].includes(card.art_status)||card.twinlight_card!=='layers-1')throw Error('这不是有效的 Twinlight 分层卡');
 if(card.persona_digest!==currentDigest())throw Error('卡图属于另一份人物设定，请让 AI 为当前用户重新生成。');
 const d=card.depths;if(!d||!(d.background>=-.4&&d.background<=-.05&&d.subject>=.1&&d.subject<=.6&&d.effects>=.15&&d.effects<=.7&&d.subject<d.effects&&d.text===0))throw Error('图层景深设置不正确');
 const images={};for(const role of ROLES){const x=await inspectImage(card.layers?.[role],role);images[role]=x;if(role==='background'&&!x.opaque)throw Error('背景层必须完整且不透明');if(['subject','effects','text'].includes(role)&&(x.transparent<=.01||x.occupied<=.0005))throw Error(role+'：需要真实 alpha 透明图层；不会自动抠图。');if(role==='lineart'&&!(x.lo<128&&x.hi>200))throw Error('线稿需要与主体对应的深色轮廓和白底');}
 const first=images.background;if(ROLES.some(k=>images[k].w!==first.w||images[k].h!==first.h)||!Array.isArray(card.canvas)||card.canvas[0]!==first.w||card.canvas[1]!==first.h)throw Error('所有图层必须保留完全相同的画布尺寸与坐标');
 const flat=document.createElement('canvas');flat.width=first.w;flat.height=first.h;const g=flat.getContext('2d');for(const role of ROLES.filter(k=>k!=='lineart'))g.drawImage(images[role].im,0,0);
 return {mode:card.art_status==='placeholder'?'placeholder':'layered',status:card.art_status,personaDigest:card.persona_digest,layers:card.layers,depths:d,preview:flat.toDataURL('image/jpeg',.92)};
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
   const bg=await loadImage(layers.background);card={twinlight_card:'layers-1',persona_digest:input.persona_digest,art_status:input.art_status,layers,depths:input.depths,canvas:[bg.naturalWidth,bg.naturalHeight]};
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
window.twinlightViewer={getState:()=>({ok:!!state.check?.ok,errors:state.check?.errors||[],warnings:state.check?.warnings||[],art:artChoice(),artError:state.artError,built:!!state.html,htmlBytes:state.html?state.html.length:0}),html:()=>state.html,check:runCheck};
})();
