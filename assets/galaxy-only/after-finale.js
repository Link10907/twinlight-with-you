const galaxyEndActions=el('div','galaxy-end-actions');galaxyEndActions.id='galaxyEndActions';galaxyEndActions.hidden=true;
const galaxyReturn=el('button','','返回我的星系 ↗');galaxyReturn.id='galaxyReturn';galaxyReturn.onclick=closeGalaxyEnding;
const galaxyReplay=el('button','','重看交融');galaxyReplay.id='galaxyReplay';galaxyReplay.onclick=()=>{closeGalaxyEnding();quietFinale();};
galaxyEndActions.append(galaxyReturn,galaxyReplay);questionScene.append(galaxyEndActions);
const galaxyEncounter=encounter;encounter=function(){if(!state.encounterCinematic){galaxyEnding=false;galaxyEndActions.hidden=true;}galaxyEncounter();};
const galaxyOldEnd=endEncounter;endEncounter=function(returnView=false){galaxyEnding=false;galaxyEndActions.hidden=true;v10.playing=false;v10HideOverlays();galaxyOldEnd(returnView);};
$('cinemaExit').onclick=closeGalaxyEnding;
$('encounterCinema').setAttribute('aria-label','十四秒终章：AI 星系发展与交融');
const galaxyCreateNav=createNav;createNav=function(){galaxyCreateNav();const last=$('indexList').lastElementChild;if(last?.querySelector('small'))last.querySelector('small').textContent='认识 AI 星系 · 交融 · 继续探索';};
window.twinlightV10={finale:quietFinale,getState:()=>({time:v10.time,phase:v10.phase,total:14,aiBirth:v10Birth(),mergerProgress:v10MergeProgress(),summarizer:summarizerInfo(),music:state.sound,card:false}),seek:seconds=>{if(!state.encounterCinematic)quietFinale();scrubEncounter(seconds/14);paint();},summarizer:summarizerInfo};
window.twinlightGalaxyOnly={cardEnabled:false,returnToGalaxy:closeGalaxyEnding};
function galaxyHash(){if(location.hash==='#card'){history.replaceState(null,'','#galaxy');return;}if(location.hash==='#finale'){if(state.ready)quietFinale();else setTimeout(galaxyHash,100);}}
window.addEventListener('hashchange',galaxyHash);galaxyHash();
