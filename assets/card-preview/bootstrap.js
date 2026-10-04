/* Card-only host for the shared layered renderer; no galaxy profile or narrative. */
const PERSONA=__CARD_DATA__;
const $=id=>document.getElementById(id),el=(tag,cls)=>{const node=document.createElement(tag);if(cls)node.className=cls;return node;};
const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));
const state={reduced:matchMedia('(prefers-reduced-motion: reduce)').matches};
const v8={cardOpen:false,flipped:false};
function currentPersona(){return PERSONA;}
function imageReady(src){return new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>reject(Error('图层载入失败'));im.src=src;});}
function refreshIdentity(){
  $('cardTitle').textContent=PERSONA.title;
  $('cardOwner').textContent=PERSONA.name||'';
  $('backTitle').textContent=PERSONA.title;
  $('backReflection').textContent=PERSONA.reflection||'';
  $('backAuthor').textContent=PERSONA.summarizer||'';
}
function showIdentityCard(){v8.cardOpen=true;refreshIdentity();}
function flipIdentity(){}
function setCardTilt(){}
async function exportCardBlob(){throw Error('没有可导出的原生卡面');}
