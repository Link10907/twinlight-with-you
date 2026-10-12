const galaxyLayoutNav=createNav;createNav=function(){adoptLayout();galaxyLayoutNav();};
const galaxyCoverage=el('p');galaxyCoverage.textContent='材料范围：'+(profile.coverage?.description||'当前授权资料')+' 本页为无闪卡的完整星系版。';$('infoDialog').querySelector('.dialog-body').prepend(galaxyCoverage);
const galaxyPrivacy=el('span','skill-draft');galaxyPrivacy.textContent='私人作品 · 分享前请检查内容';document.body.append(galaxyPrivacy);
window.twinlightSkill={getState:()=>({version:'galaxy-only-1',stars:nodes.length,planets:personalSatellites.length,owner:profile.owner_id,shareAllowed:false,artReady:false,artStatus:'not_applicable',artMode:'none',cardEnabled:false,layout:profile.layout}),validate:validateProfile};
