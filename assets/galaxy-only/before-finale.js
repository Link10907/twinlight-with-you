// No card stubs, card images, card DOM or generated placeholder artwork.
const galaxySkip=el('button','','跳到终章 →');galaxySkip.id='cinemaSkip';document.querySelector('.cinema-player').append(galaxySkip);
const galaxyFinaleShortcut=el('button','','终章 · AI 星系与我 ↗');galaxyFinaleShortcut.id='v8FinaleShortcut';$('v7Catalog').after(galaxyFinaleShortcut);
let galaxyEnding=false;
function finishGalaxyFinale(){
 if(galaxyEnding)return;galaxyEnding=true;state.mergePlaying=false;v10.playing=false;v10.time=14;v10.phase='finished';
 updateEncounterUI();$('v10RevealNow')?.remove();questionScene.hidden=false;$('galaxyEndActions').hidden=false;$('cinemaSkip').hidden=true;$('cinemaPause').hidden=true;
}
function closeGalaxyEnding(){galaxyEnding=false;endEncounter(false);showWorld('personal',true);$('galaxyEndActions').hidden=true;history.replaceState(null,'','#galaxy');$('home').focus({preventScroll:true});}
