/* Twinlight lite: browser/Node twin of scripts/twinlight_core/lite.py.
 * Same schema interpretation, same Chinese messages, same layout algorithm.
 * tests/test_lite.py runs both on shared fixtures and compares output.
 * No network, no eval, no dependencies.
 */
(function(root){
'use strict';
const TRIM=/^[ \t\r\n\u00a0\u3000]+|[ \t\r\n\u00a0\u3000]+$/g;
const FENCE=/```[ \t]*(?:json|JSON|json5)?[ \t]*\r?\n([\s\S]*?)\r?\n?```/;
const TYPE_CN={object:'对象 {…}',array:'列表 […]',string:'文字'};
const PRIVACY=[
 ['私钥',/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/],
 ['GitHub 令牌',/\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b/],
 ['API 密钥',/\bsk-[A-Za-z0-9_-]{24,}\b/],
 ['AWS 密钥',/\bAKIA[A-Z0-9]{16}\b/],
 ['邮箱地址',/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/],
 ['手机号',/(?<!\d)(?:\+86[- ]?)?1[3-9]\d{9}(?!\d)/]
];
const BASIS={often:['常聊','你的 AI：你们经常聊到这个。'],once:['提过','你的 AI：你提到过这个。'],inferred:['AI 推测','你的 AI 根据整体印象推测，未必准确。']};
const BASIS_WEIGHT={often:3,once:1,inferred:1};
const PROVIDERS=[['openai',['gpt','chatgpt','openai']],['anthropic',['claude','anthropic']],['google',['gemini','google']],['deepseek',['deepseek']],['qwen',['qwen','通义']],['moonshot',['kimi','moonshot']],['bytedance',['doubao','豆包']]];
const UNKNOWN_AUTHOR=new Set(['','未知','unknown','ai','不知道','不确定','不清楚','n/a','none','ai助手','ai 助手','assistant','ai assistant']);
const COLORS=[[1,.55,.18],[.40,.70,1],[1,.28,.07],[.40,.86,1],[.65,.43,1]];
const PLANET_COLORS=[[.68,.51,.38],[.29,.58,.73],[.69,.43,.27],[.69,.72,.59],[.79,.67,.49],[.46,.72,.79],[.59,.64,.79],[.72,.61,.82]];

// ---- SHA-256 over UTF-8; constants derived like the FIPS definition. ----
const K=[],H0=[];
(function(){let n=2,found=0;const prime=x=>{for(let d=2;d*d<=x;d++)if(x%d===0)return false;return true;};
 while(found<64){if(prime(n)){if(found<8)H0.push((Math.sqrt(n)%1)*4294967296|0);K.push((Math.cbrt(n)%1)*4294967296|0);found++;}n++;}})();
function sha256(str){
 const bytes=new TextEncoder().encode(str),l=bytes.length,size=((l+9+63)>>6)<<6,buf=new Uint8Array(size);buf.set(bytes);buf[l]=0x80;
 const dv=new DataView(buf.buffer),bits=l*8;dv.setUint32(size-4,bits>>>0);dv.setUint32(size-8,Math.floor(bits/4294967296));
 const W=new Int32Array(64);let H=H0.slice();
 for(let o=0;o<size;o+=64){
  for(let i=0;i<16;i++)W[i]=dv.getInt32(o+i*4);
  for(let i=16;i<64;i++){const a=W[i-15],b=W[i-2];W[i]=(W[i-16]+(((a>>>7)|(a<<25))^((a>>>18)|(a<<14))^(a>>>3))+W[i-7]+(((b>>>17)|(b<<15))^((b>>>19)|(b<<13))^(b>>>10)))|0;}
  let [a,b,c,d,e,f,g,h]=H;
  for(let i=0;i<64;i++){const t1=(h+(((e>>>6)|(e<<26))^((e>>>11)|(e<<21))^((e>>>25)|(e<<7)))+((e&f)^(~e&g))+K[i]+W[i])|0;const t2=((((a>>>2)|(a<<30))^((a>>>13)|(a<<19))^((a>>>22)|(a<<10)))+((a&b)^(a&c)^(b&c)))|0;h=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=a;a=(t1+t2)|0;}
  H=[H[0]+a|0,H[1]+b|0,H[2]+c|0,H[3]+d|0,H[4]+e|0,H[5]+f|0,H[6]+g|0,H[7]+h|0];
 }
 return H.map(x=>(x>>>0).toString(16).padStart(8,'0')).join('');
}
function canonical(v){
 if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';
 if(v&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
 return JSON.stringify(v);
}
const digest=v=>sha256(canonical(v));
const cp=s=>[...s].length;
const err=(path,code,message)=>({path:path||'$',code,message});

function stripTrailingCommas(text){
 let out='',inStr=false,esc=false;
 for(let i=0;i<text.length;i++){const c=text[i];
  if(inStr){out+=c;if(esc)esc=false;else if(c==='\\')esc=true;else if(c==='"')inStr=false;}
  else if(c==='"'){inStr=true;out+=c;}
  else if(c===','){let j=i+1;while(j<text.length&&' \t\r\n'.includes(text[j]))j++;if(j>=text.length||!'}]'.includes(text[j]))out+=c;}
  else out+=c;}
 return out;
}
function parse(text){
 const warnings=[];let t=String(text).replace(/^\ufeff+/,'').trim();
 const m=FENCE.exec(t);
 if(m){t=m[1].trim();warnings.push('去掉了 ``` 代码块标记');}
 else if(!t.startsWith('{')&&t.includes('{')&&t.includes('}')){t=t.slice(t.indexOf('{'),t.lastIndexOf('}')+1);warnings.push('去掉了 JSON 前后的说明文字');}
 try{return {data:JSON.parse(t),warnings,errors:[]};}
 catch(first){
  const fixed=stripTrailingCommas(t);
  if(fixed!==t){try{const data=JSON.parse(fixed);warnings.push('去掉了 } 或 ] 前多余的逗号');return {data,warnings,errors:[]};}catch(_){}}
  const hint=/[“”]\s*:|:\s*[“”]/.test(t)?'；检测到中文引号 “ ” 被当作 JSON 引号，请改成英文双引号 "':'';
  let where='';const msg=String(first.message||'');const lc=/line (\d+) column (\d+)/.exec(msg),pos=/position (\d+)/.exec(msg);
  if(lc)where=`（第 ${lc[1]} 行第 ${lc[2]} 列附近）`;else if(pos){const before=t.slice(0,Number(pos[1])).split('\n');where=`（第 ${before.length} 行第 ${before[before.length-1].length+1} 列附近）`;}
  return {data:null,warnings,errors:[err('$','parse_error',`不是有效的 JSON${where}${hint}`)]};
 }
}
function normalize(v){
 if(typeof v==='string')return v.replace(TRIM,'');
 if(Array.isArray(v))return v.map(normalize);
 if(v&&typeof v==='object'){const o={};for(const k of Object.keys(v))o[k]=normalize(v[k]);return o;}
 return v;
}
function typeOk(node,kind){
 if(kind==='object')return !!node&&typeof node==='object'&&!Array.isArray(node);
 if(kind==='array')return Array.isArray(node);
 if(kind==='string')return typeof node==='string';
 return true;
}
function walk(node,sch,path,title,errors){
 if(sch.title!==undefined)title=sch.title;
 if('const' in sch){if(node!==sch.const)errors.push(err(path,'bad_value',`「${title}」应为 "${sch.const}"`));return;}
 if('enum' in sch){if(typeof node!=='string'||!sch.enum.includes(node))errors.push(err(path,'bad_value',`「${title}」只能是 `+sch.enum.join(' / ')));return;}
 const kind=sch.type;
 if(kind&&!typeOk(node,kind)){errors.push(err(path,'wrong_type',`「${title}」应为${TYPE_CN[kind]}`));return;}
 if(kind==='string'){
  const n=cp(node),min=sch.minLength??0;
  if(n<min)errors.push(n===0?err(path,'empty',`「${title}」不能为空`):err(path,'too_short',`「${title}」至少 ${sch.minLength} 字，现在 ${n} 字`));
  else if(sch.maxLength!==undefined&&n>sch.maxLength)errors.push(err(path,'too_long',`「${title}」最多 ${sch.maxLength} 字，现在 ${n} 字`));
  else if(sch.pattern!==undefined&&!new RegExp(sch.pattern).test(node))errors.push(err(path,'bad_format',`「${title}」${sch['x-message']||'格式不对'}`));
 }else if(kind==='array'){
  const n=node.length;
  if(n<(sch.minItems??0))errors.push(err(path,'too_few',`「${title}」至少 ${sch.minItems} 项，现在 ${n} 项`));
  else if(sch.maxItems!==undefined&&n>sch.maxItems)errors.push(err(path,'too_many',`「${title}」最多 ${sch.maxItems} 项，现在 ${n} 项`));
  node.forEach((item,i)=>walk(item,sch.items,`${path}[${i}]`,title,errors));
 }else if(kind==='object'){
  const props=sch.properties||{},prefix=path?path+'.':'';
  for(const key of sch.required||[])if(!Object.prototype.hasOwnProperty.call(node,key))errors.push(err(prefix+key,'missing',`缺少「${props[key].title??key}」`));
  if(sch.additionalProperties===false)for(const key of Object.keys(node))if(!Object.prototype.hasOwnProperty.call(props,key))errors.push(err(prefix+key,'unknown_field',`多了不认识的字段「${key}」，请删除`));
  for(const [key,sub] of Object.entries(props))if(Object.prototype.hasOwnProperty.call(node,key))walk(node[key],sub,prefix+key,sub.title??key,errors);
 }
}
function semantic(data,errors){
 const themes=data.themes;
 if(Array.isArray(themes)){const seen=new Map();
  themes.forEach((theme,i)=>{
   if(!theme||typeof theme!=='object'||Array.isArray(theme))return;
   const label=theme.label;
   if(typeof label==='string'&&label){if(seen.has(label))errors.push(err(`themes[${i}].label`,'duplicate',`「主题名」与 ${seen.get(label)} 重复`));else seen.set(label,`themes[${i}].label`);}
   if(Array.isArray(theme.topics)){const tseen=new Map();
    theme.topics.forEach((topic,j)=>{const tl=topic&&typeof topic==='object'&&!Array.isArray(topic)?topic.label:null;
     if(typeof tl==='string'&&tl){const p=`themes[${i}].topics[${j}].label`;if(tseen.has(tl))errors.push(err(p,'duplicate',`「话题名」与 ${tseen.get(tl)} 重复`));else tseen.set(tl,p);}});}
  });}
 const visit=(x,path)=>{
  if(typeof x==='string'){for(const [kind,re] of PRIVACY)if(re.test(x)){errors.push(err(path,'privacy',`疑似包含${kind}，请删除`));break;}}
  else if(Array.isArray(x))x.forEach((v,i)=>visit(v,`${path}[${i}]`));
  else if(x&&typeof x==='object')for(const k of Object.keys(x))visit(x[k],path?`${path}.${k}`:k);
 };
 visit(data,'');
}
function validate(data,schema){
 const errors=[];walk(data,schema,'','Twinlight JSON',errors);
 if(data&&typeof data==='object'&&!Array.isArray(data))semantic(data,errors);
 return errors;
}
function stats(d){return {themes:d.themes.length,topics:d.themes.reduce((n,t)=>n+t.topics.length,0),keywords:d.card.keywords.length};}
function checkText(text,schema){
 let {data,warnings,errors}=parse(text);
 if(!errors.length){data=normalize(data);errors=validate(data,schema);}
 const ok=!errors.length;
 return {ok,errors,warnings,data:ok?data:null,stats:ok?stats(data):null};
}
function repairPrompt(errors){
 return [`你输出的 Twinlight JSON 有 ${errors.length} 处问题：`,...errors.map((e,i)=>`${i+1}. ${e.path}：${e.message}`),
  '请只修改这些位置，其余内容保持不变。重新输出完整的 JSON，放在一个 ```json 代码块里，代码块外不要写别的内容。'].join('\n');
}
function providerOf(summarizer){
 const s=summarizer.replace(TRIM,''),low=s.toLowerCase();
 if(UNKNOWN_AUTHOR.has(low))return ['unknown',null];
 for(const [p,keys] of PROVIDERS)if(keys.some(k=>low.includes(k)))return [p,s];
 return ['other',s];
}
const ownerId=name=>'lite-'+sha256(name).slice(0,12);
// Bind artwork to this person's current card and its reported author, rather
// than the moment a browser or compiler happened to open the same content.
function personaPayload(data){
 const [provider,display]=providerOf(data.summarizer);
 return {owner:ownerId(data.name),card:data.card,author:{provider,display_name:display,attribution_source:'ai_self_reported'}};
}
async function sha256Canonical(value){
 const source=canonical(value);
 if(root.crypto&&root.crypto.subtle){
  try{
   const bytes=await root.crypto.subtle.digest('SHA-256',new TextEncoder().encode(source));
   return Array.from(new Uint8Array(bytes),x=>x.toString(16).padStart(2,'0')).join('');
  }catch(_){/* Local-file previews may lack SubtleCrypto; the same SHA-256 remains available. */}
 }
 return sha256(source);
}
const personaDigest=async data=>sha256Canonical(personaPayload(data));

// ---- Deterministic layout (twin of layout.layout_from_spec, no lock). ----
const unit=(seed,key)=>parseInt(digest([seed,key]).slice(0,13),16)/4503599627370496;
const round=(x,n)=>{const r=Number(x.toFixed(n));return Object.is(r,-0)?0:r;};
const dist=(p,q)=>Math.sqrt((p[0]-q[0])**2+(p[1]-q[1])**2+(p[2]-q[2])**2);
function layoutFromSpec(owner,spec){
 const seed=digest(['twinlight-layout-v1',owner]);
 const themes=spec.map(([id,topics])=>({id,topics:topics.map(([tid,weight])=>({id:tid,weight}))})).sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0);
 if(themes.length<1||themes.length>8)throw Error('Need 1–8 themes');
 const taken=[],stars=[];
 for(const t of themes){
  const cands=[];
  for(let j=0;j<64;j++){
   const radius=38+(j%3)*29+unit(seed,t.id+`:r:${j}`)*7,angle=j*2.399963229728653+unit(seed,t.id+':angle')*.7;
   cands.push([unit(seed,t.id+`:candidate:${j}`),[round(radius*Math.cos(angle),4),round(4+unit(seed,t.id+':height')*5,4),round(radius*Math.sin(angle),4)]]);
  }
  cands.sort((a,b)=>a[0]-b[0]);
  const hit=cands.find(([,p])=>taken.every(q=>dist(p,q)>=34));
  if(!hit)throw Error('Layout packing failed');
  const material=Math.floor(unit(seed,t.id+':material')*5)%5;
  stars.push({id:t.id,position:hit[1],material,color:COLORS[material]});taken.push(hit[1]);
 }
 const topics=[];
 for(const t of themes){
  let inner=9+3;
  for(const topic of t.topics.slice().sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0)){
   const k=t.id+'/'+topic.id;
   const radius=round(Math.min(2.7,1.2+.36*Math.log2(1+topic.weight))+.22*unit(seed,k+':size'),4);
   const orbitRadius=round(inner+radius,4);inner=orbitRadius+radius+2.7;
   if(orbitRadius>80)throw Error('Orbit slots exhausted');
   topics.push({id:topic.id,parent_id:t.id,radius,orbitRadius,eccentricity:round(.03+.08*unit(seed,k+':ecc'),4),inclination:round(-.12+.42*unit(seed,k+':inc'),4),
    nodeAngle:round(unit(seed,t.id+':node')*Math.PI*2+(unit(seed,k+':node')-.5)*.25,5),phase:round(unit(seed,k+':phase')*Math.PI*2,5),
    material:Math.floor(unit(seed,k+':mat')*5)%5,color:PLANET_COLORS[Math.floor(unit(seed,k+':color')*8)%8]});
  }
 }
 const value={version:'1.0',owner_id:owner,seed,stars,topics};
 value.layout_digest=digest(value);
 return value;
}

function toProfile(data,{generatedAt,artStatus='placeholder',artMode=null,confirmed=false,aiHistory=[]}){
 const oid=ownerId(data.name),chapters=[],spec=[];
 artMode=artMode||(artStatus==='static'?'static':artStatus==='placeholder'?'placeholder':'layered');
 data.themes.forEach((theme,i)=>{
  const tid=`theme-${i+1}`;
  const topics=theme.topics.map((topic,j)=>({id:`topic-${j+1}`,name:topic.label,title:topic.summary,body:[topic.summary],quote:null,status:BASIS[topic.basis][0],provenance:BASIS[topic.basis][1]}));
  spec.push([tid,theme.topics.map((t,j)=>[`topic-${j+1}`,BASIS_WEIGHT[t.basis]])]);
  chapters.push({id:tid,label:theme.label,english:theme.english,period:'AI 印象 · 未标注日期',headline:theme.headline,story:theme.story.slice(),reflection:theme.reflection,changes:[],
   tags:topics.slice(0,5).map(t=>t.name),transition:'循着微光，走向下一段记录。',signature:theme.headline,quotes:[],topics,letterClosing:'这些印象，是来路，不是定论。',
   collaboration:'由你的 AI 根据对你的了解写下。',companion_year:null,ai_context_ids:[],
   ai_trace:{product:'未确认',model_id:null,reported_name:null,status:'unknown',source:'精简模式不绑定消息级模型证据',note:'不由日期、词语或总结者反推历史模型。'}});
 });
 const [provider,display]=providerOf(data.summarizer);
 const meta={provider,display_name:display,model:null,generated_at:generatedAt,attribution_source:'ai_self_reported'};
 const card=data.card;
 const persona={version:'1.0',name:data.name,rarity:'SSR',title:card.title,english_title:card.english_title,edition:generatedAt.slice(0,7).replace('-','.'),
  keywords:card.keywords.slice(),line:card.tagline,reflection:card.reflection,evidence:data.themes.slice(0,3).map(t=>({title:t.label,text:[...t.headline].slice(0,60).join('')})),
  art_type:artStatus==='static'?'静态原型插画：尚未完成独立分层':artStatus!=='placeholder'?'原生独立分层插画':'占位卡面：还没有放入你的插画',
  disclaimer:'本卡是 AI 对你的创作性印象，不是人格诊断或能力排名。每张卡都是 SSR。',summarizer:meta,content_ready:true,art_status:artStatus,art_mode:artMode};
 persona.persona_digest=digest(personaPayload(data));
 const profile={version:'1.0',mode:'lite',name:data.name,owner_id:oid,intro:data.intro||'每一颗微光，都有来处。',chapters,summary_meta:meta,ai_history:aiHistory,ai_usage:[],
  layout:layoutFromSpec(oid,spec),persona,
  coverage:{scope:'ai_impression',start:null,end:null,account_history_complete:false,description:'基于你的 AI 对你的印象（记忆与对话），不是逐条核对的聊天记录。'},
  release:{draft:!confirmed,share_allowed:!!confirmed}};
 profile.content_digest=digest({owner_id:oid,chapters,summary_meta:meta,persona_digest:persona.persona_digest});
 return profile;
}

// ---- Native layers share a selected prototype, never a poster cutout. ----
// Keep this prompt set byte-for-byte equal to scripts/twinlight_core/cardgen.py.
function artPrompts(card){
 const desc=String(card&&card.art_prompt||'').trim();
 const concept='本次卡面设定：'+desc;
 const style='遵循本次明确偏好、最新审美反馈与 AI 从当前资料自主选择的美术设定，不询问创意选择。画风与主体由行为、气质和卡面表现力共同决定；人物、动物、拟人角色和寓意物件均可，不固定二次元人像、小鹿或某种画法。统一笔触、材质、色彩和光线，保持主体清楚、比例合理、细节精致、象征克制；轮廓、动作或材质需要有本次设计的记忆点，整幅画面的美术语言应有辨识度，仅换物种、换脸、换衣服或加光球不足以形成特色。虚构形象不代表本人真实身份。不要套用示例人物、月夜、服装、性别、肤色或经历。';
 const canvas='统一 1080×1440、竖版 3:4 全画布；各层使用同一坐标，保持本次选定原型的构图、比例、姿态与光照。不得裁剪到主体后重新摆位。';
 const alpha='直接原生生成带真实 alpha 通道的透明 PNG，主体之外透明；不抠图，不去背景，不用纯色幕布，不把灰白棋盘格画成图片。工具不能输出透明层时保留原型为静态预览，并明确分层尚未完成。';
 const noText='不要画文字、字母、数字、签名、水印、SSR、边框或彩虹镭射；文字与卡框在独立 text 层排版，镭射由渲染器添加。';
 const subject=['参考同一张本次选定原型，直接生成收藏闪卡的独立 subject 主体层。',concept,style,canvas,
  '只保留本次原型的主体、随身细节和主要物件；主体按本次自主选择的设定，可以是人物、动物、拟人角色或寓意物件。周围的环境归背景层，远景同伴归 spirit 层。',
  alpha,noText].join('\n');
 return {
  prototype:['根据本次用户资料生成一张无字收藏闪卡原型，作为之后原生分层生图的构图参考。',concept,style,
   '1080×1440、竖版 3:4；主体是视觉焦点。保留顶部 SSR 和底部称号的排版空间，但不要画出它们。',
   '原型可包含完整主体与环境；它只作为共同参考，不得从这张海报抠出后续图层，也不得将整张图重复贴到多个层。',noText].join('\n'),
  subject,character:subject,
  background:['参考同一张本次选定原型，直接生成收藏闪卡的独立 background 场景层。',concept,style,canvas,
   '只生成完整场景，不要画主体，不要画人物或主体的影子、替身、残片；主体曾遮住的位置也必须画完整。保持原型的环境、透视与光照，不需要先去掉任何人物。',
   '整张场景必须完全不透明。主体层会单独叠加；不要将完整原型用作背景。',noText].join('\n'),
  effects:['参考同一张本次选定原型，直接生成收藏闪卡的独立 effects 前景效果层。',concept,style,canvas,
   '只绘制本次设定需要的少量前景象征物、光粒或装饰；不要重画主体或场景，不遮住主体的脸及后续文字。',alpha,noText].join('\n'),
  spirit:['参考同一张本次选定原型，直接生成可选的 spirit 中景伴生层。',concept,style,canvas,
   '只有本次设定明确包含同伴或中景象征时才生成，不要为凑层数添加人格含义；不使用时交付同尺寸全透明 PNG。不要重画主角。',alpha,noText].join('\n'),
  text:['SSR、卡框与文字默认由程序排版为独立 text 层，真实透明、同一 1080×1440 画布，depth=0。',
   '排版只使用当前卡的 title、english_title、keywords、tagline 与当前总结者署名，不沿用示例文案。',
   '也可独立生图生成 text 层，但必须逐字核对、保持真实 alpha 与同画布坐标；不能把文字烧进 subject 或 background。'].join('\n')};
}

const api={parse,normalize,validate,checkText,repairPrompt,toProfile,layoutFromSpec,providerOf,ownerId,sha256,digest,canonical,sha256Canonical,personaDigest,stripTrailingCommas,BASIS,artPrompts};
root.TwinlightLite=api;
if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
