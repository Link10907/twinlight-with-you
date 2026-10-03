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
 starTypes.splice(0,starTypes.length,...nodes.map(()=> '恒星 · 艺术化表面'));
 planetCaption.splice(0,planetCaption.length,...nodes.map(()=> 'STELLAR LIGHT'));
 routeLocal.length=0;
 for(let i=0;i<localNodes.length-1;i++)for(let j=0;j<=28;j++){const t=j/28,p=lerp(localNodes[i],localNodes[i+1],t);p[1]+=Math.sin(t*Math.PI)*9;routeLocal.push(p);}
 document.documentElement.style.setProperty('--chapter-count',String(nodes.length));
}
const skillCreateNav=createNav;
createNav=function(){adoptLayout();skillCreateNav();};
const skillRefresh=refreshIdentity;
refreshIdentity=function(){skillRefresh();const d=currentPersona();
 $('cardSave').disabled=!d.shareAllowed;$('cardNativeShare').disabled=!d.shareAllowed;
 $('cardFront').alt=d.artReady?'SSR '+d.title+'，独立分层角色卡':'SSR 图层示意；专属角色插画尚待生成和审查';
 let notice=$('skillArtNotice');if(!notice){notice=el('p','skill-art-notice');notice.id='skillArtNotice';$('identityHeading').after(notice);}notice.hidden=d.artReady;notice.textContent='分层示意 · 专属人物插画待生成与审查';
 if(!d.artReady)document.querySelector('.identity-message').textContent=(d.line||'')+' · 当前为分层占位素材，不是专属人物成品。';
};
const skillExport=exportCardBlob;
exportCardBlob=async function(side){if(!currentPersona().shareAllowed)throw Error('当前资料/图层尚未取得分享审查许可。');return skillExport(side);};
const originalApply=$('applyJson').onclick;
$('applyJson').onclick=function(){originalApply();refreshIdentity();};
const draft=el('span','skill-draft');draft.textContent='本地预览 · 待审查';draft.hidden=!profile.release.draft;document.body.append(draft);
const originalImportApply=$('applyJson').onclick;$('applyJson').onclick=()=>{originalImportApply();draft.hidden=false;};
const sourcesBody=$('infoDialog').querySelector('.dialog-body');
const coverageLine=el('p');coverageLine.textContent='材料范围：'+(profile.coverage?.description||'本次导入摘要；并非完整账户历史')+' 原始引用、排除项和冲突处理见本地 review.md。';sourcesBody.prepend(coverageLine);
refreshIdentity();
window.twinlightSkill={getState:()=>({version:'1.0',stars:nodes.length,planets:personalSatellites.length,owner:profile.owner_id,shareAllowed:currentPersona().shareAllowed,artReady:currentPersona().artReady,layout:profile.layout}),validate:validateProfile};
