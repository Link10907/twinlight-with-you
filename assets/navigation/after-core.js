/* One view controller over the retained V10 scene and the ONE existing card.
 * No iframe, API call, second canvas renderer, audio instance or legacy timer.
 */
(() => {
  'use strict';
  const boot = window.__twinlightNavigationBoot;
  const nav = {view:'galaxy', target:'galaxy', epoch:0, snapshot:null, internal:false,
               ready:false, transitions:0, pending:null, error:null};
  const rawShow = showIdentityCard, rawHide = hideIdentityCard;
  const rawFinale = quietFinale, rawEncounter = encounter, rawEnd = endEncounter;
  const clone = value => JSON.parse(JSON.stringify(value));
  const stateKeys = ['mode','active','from','topic','aiEvent','cam','target','fov','bank',
    'localOffset','localGoal','merge','mergeGoal','orbiting','exploring','reading',
    'auto','zoomIntent','zoomTarget','hoveredStar','hoverAI'];
  const quietKeys = ['selection','topic','wantRead','reading','playing','elapsed'];
  const elementIds = ['reader','starCaption','companionCard','companionLabel','eventReader',
    'clusterTitle','welcome','aiIntro','flightControls'];
  function remember() {
    if (nav.snapshot || nav.view !== 'galaxy') return;
    if (state.flight) finishFlight();
    nav.snapshot = {
      state:Object.fromEntries(stateKeys.filter(k => state[k] !== undefined).map(k => [k,clone(state[k])])),
      orbit:clone(orbit), quiet:Object.fromEntries(quietKeys.map(k => [k,quiet[k]])),
      elements:elementIds.map(id => $(id)).filter(Boolean).map(node =>
        ({node,hidden:node.hidden,classes:node.className,scrollTop:node.scrollTop,scrollLeft:node.scrollLeft})),
      readerScroll:Array.from($('reader').querySelectorAll('*')).filter(n => n.scrollTop || n.scrollLeft)
        .map(node => ({node,top:node.scrollTop,left:node.scrollLeft})),
      bodyClasses:document.body.className, bodyView:document.body.dataset.view,
      bodyMode:document.body.dataset.mode, focus:document.activeElement, scroll:[scrollX,scrollY]
    };
  }
  function setHash(view, replace=false) {
    const hash='#'+view;
    if (location.hash !== hash) history[replace ? 'replaceState' : 'pushState'](history.state,'',hash);
  }
  function sync() {
    document.body.dataset.twinlightView=nav.view;
    for (const b of document.querySelectorAll('button[data-twinlight-view]')) {
      const active=b.dataset.twinlightView===nav.view;
      b.setAttribute('aria-pressed',String(active));
      if (active) b.setAttribute('aria-current','page'); else b.removeAttribute('aria-current');
    }
  }
  function restore() {
    const snapshot=nav.snapshot;
    nav.internal=true;
    try {
      rawHide(); rawEnd(false);
      state.mergePlaying=false; v10.playing=false; v8.running=false;
      state.flight=null; state.viewTween=null;
      if (snapshot) {
        Object.assign(state,clone(snapshot.state)); Object.assign(orbit,clone(snapshot.orbit));
        Object.assign(quiet,snapshot.quiet);
        document.body.className=snapshot.bodyClasses;
        if (snapshot.bodyView === undefined) delete document.body.dataset.view; else document.body.dataset.view=snapshot.bodyView;
        if (snapshot.bodyMode === undefined) delete document.body.dataset.mode; else document.body.dataset.mode=snapshot.bodyMode;
        makeTopicLabels(state.active); updateWorld(); updateNav();
        for (const e of snapshot.elements) {
          e.node.hidden=e.hidden; e.node.className=e.classes;
          e.node.scrollTop=e.scrollTop; e.node.scrollLeft=e.scrollLeft;
        }
        for (const e of snapshot.readerScroll) {e.node.scrollTop=e.top;e.node.scrollLeft=e.left;}
        scrollTo(...snapshot.scroll);
        if (snapshot.focus?.isConnected && !snapshot.focus.inert) snapshot.focus.focus({preventScroll:true});
      } else {
        showWorld('overview',true);
      }
      v10.phase='home'; basis(); paint();
      nav.snapshot=null;
    } finally {nav.internal=false;}
  }
  const ready = new Promise(resolve => {
    const check = () => {
      if (state.ready && window.galaxyDebug) {nav.ready=true;resolve();}
      else requestAnimationFrame(check);
    };
    check();
  });
  async function go(view, options={}) {
    if (!['galaxy','card','finale'].includes(view)) view='galaxy';
    if (nav.target===view && nav.pending) return nav.pending;
    if (nav.ready && nav.view===view && view!=='finale' && !nav.pending) {
      if (!options.fromURL) setHash(view,options.replace); return;
    }
    const token=++nav.epoch; nav.target=view;
    const operation=(async () => {
      if (!nav.ready) await ready;
      if (token!==nav.epoch) return;
      if (view==='card') {
        // Eager preparation uses the SAME retained renderer. Hidden cards do
        // not draw; a fallback remains a fallback, never a WebGL pass.
        if (!holo.ready && !holo.failed) await initHolo();
        if (token!==nav.epoch) return;
        remember();
        nav.internal=true;
        try {quietMenu(false);rawEnd(false);state.mergePlaying=false;v10.playing=false;rawShow();}
        finally {nav.internal=false;}
      } else if (view==='finale') {
        remember();
        nav.internal=true;
        try {rawHide();rawEnd(false);state.mergePlaying=false;v10.playing=false;rawFinale();}
        finally {nav.internal=false;}
      } else restore();
      nav.view=view; nav.transitions++; sync();
      if (!options.fromURL) setHash(view,options.replace);
    })();
    nav.pending=operation;
    try {await operation;} catch (error) {
      nav.error=String(error);console.error('Twinlight navigation:',error);
      toast('此视图未能载入，请返回星系重试。');
    } finally {if (token===nav.epoch) nav.pending=null;}
  }
  // Both narrative completion and shortcut navigation converge here.
  showIdentityCard=function() {
    if (nav.internal) return rawShow();
    return go('card',{replace:nav.view==='finale'});
  };
  quietFinale=function() {if(nav.internal)return rawFinale();return go('finale');};
  encounter=function() {
    if (nav.internal || state.encounterCinematic) return rawEncounter();
    return go('finale');
  };
  const on=(id,view) => {if($(id))$(id).onclick=()=>go(view);};
  on('identityClose','galaxy'); on('cinemaExit','galaxy');
  for(const id of ['cardReplay','cinemaReplay','v8FinaleShortcut','v10HomeFinale'])on(id,'finale');
  on('v8CardShortcut','card');
  $('identityClose').textContent='返回星系';
  $('v8CardShortcut').textContent='我的闪卡 ↗';
  const header=document.querySelector('.header nav');
  const mapButton=$('navMap'), oldMapClick=mapButton.onclick;
  const cardButton=el('button','twinlight-view-link');
  cardButton.type='button';cardButton.id='twinlightNavCard';header.append(cardButton);
  for(const [button,view,title,shortTitle] of [
      [mapButton,'galaxy','我的星系','星系'],[cardButton,'card','我的闪卡','闪卡']]) {
    button.classList.add('twinlight-view-link');button.dataset.twinlightView=view;
    button.setAttribute('aria-label',title);button.replaceChildren();
    for(const [cls,label] of [['nav-full',title],['nav-short',shortTitle]]) {
      const span=document.createElement('span');span.className=cls;span.textContent=label;
      span.setAttribute('aria-hidden','true');button.append(span);
    }
    button.onclick=()=>view==='galaxy' && nav.view==='galaxy' && !nav.pending
      ? oldMapClick?.call(button) : go(view);
  }
  window.twinlightV10.showCard=()=>showIdentityCard();window.twinlightV10.finale=()=>quietFinale();
  window.twinlightV8.showCard=()=>showIdentityCard();window.twinlightV8.finale=()=>quietFinale();
  document.addEventListener('keydown',event => {
    if (event.key==='Escape' && (v8.cardOpen || state.encounterCinematic)
        && !document.querySelector('dialog[open]')) {
      event.preventDefault();event.stopImmediatePropagation();go('galaxy');
    }
  },true);
  window.addEventListener('hashchange',() => {
    const view=location.hash.slice(1);
    if (['galaxy','card','finale'].includes(view)) go(view,{fromURL:true});
    else go('galaxy',{replace:true});
  });
  window.twinlightNavigation={version:boot.version,go,ready,
    getState:()=>({view:nav.view,target:nav.target,ready:nav.ready,pending:!!nav.pending,
      transitions:nav.transitions,error:nav.error,hasSnapshot:!!nav.snapshot,
      cardInstances:document.querySelectorAll('#identityCard').length,
      holoCanvases:document.querySelectorAll('#holoCanvas').length})};
  if(boot.hash)history.replaceState(history.state,'',boot.hash);
  sync();
  go(['#galaxy','#card','#finale'].includes(boot.hash)?boot.hash.slice(1):'galaxy',{replace:true});
})();
