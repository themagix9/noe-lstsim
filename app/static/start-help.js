'use strict';
// Detect missing start controls, not blocked ad requests: no consent or ad wall.
(()=>{
 const help=document.getElementById('start-help'),lobby=document.getElementById('lobby'),card=document.querySelector('.lobby-card');
 let missingSince=0,dismissed=false;
 function visible(element){
  if(!element||!element.getClientRects().length)return false;
  for(let node=element;node;node=node.parentElement){
   const style=getComputedStyle(node);
   if(style.display==='none'||style.visibility==='hidden'||style.visibility==='collapse'||Number(style.opacity)===0)return false;
  }
  return element.getBoundingClientRect().height>0;
 }
 function check(){
  const expected=document.body.classList.contains('lobby-open')&&!lobby.classList.contains('hidden')&&!document.hidden;
  if(!expected||visible(card)){missingSince=0;help.hidden=true;return}
  if(!missingSince)missingSince=Date.now();
  help.hidden=dismissed||Date.now()-missingSince<1500;
 }
 document.getElementById('start-help-reload').onclick=()=>location.reload();
 document.getElementById('start-help-close').onclick=()=>{dismissed=true;help.hidden=true};
 setInterval(check,1000);
})();
