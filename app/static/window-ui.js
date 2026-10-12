'use strict';
const dispatchWindow=document.getElementById('dispatch-dialog');
const dispatchTitle=dispatchWindow.querySelector('.panel-head');let windowDrag=null,windowPositioned=false;
function clampDispatchWindow(){
 let r=dispatchWindow.getBoundingClientRect();if(!dispatchWindow.open)return;
 if(!windowPositioned){const top=Math.min(document.getElementById('team-bar').getBoundingClientRect().bottom+8,innerHeight*.4);dispatchWindow.style.top=top+'px';dispatchWindow.style.maxHeight=Math.max(220,innerHeight-top-16)+'px';windowPositioned=true;r=dispatchWindow.getBoundingClientRect()}
 dispatchWindow.style.left=Math.max(8,Math.min(r.left,innerWidth-r.width-8))+'px';
 dispatchWindow.style.top=Math.max(8,Math.min(r.top,innerHeight-80))+'px';
}
dispatchTitle.addEventListener('pointerdown',event=>{
 if(event.target.closest('button,input,select')||event.button!==0)return;
 const r=dispatchWindow.getBoundingClientRect();windowDrag={x:event.clientX,y:event.clientY,left:r.left,top:r.top};
 dispatchWindow.style.right='auto';dispatchWindow.style.margin='0';dispatchWindow.style.left=r.left+'px';dispatchWindow.style.top=r.top+'px';
 dispatchTitle.setPointerCapture(event.pointerId);event.preventDefault();
});
dispatchTitle.addEventListener('pointermove',event=>{
 if(!windowDrag)return;
 const width=dispatchWindow.getBoundingClientRect().width;
 dispatchWindow.style.left=Math.max(8,Math.min(windowDrag.left+event.clientX-windowDrag.x,innerWidth-width-8))+'px';
 dispatchWindow.style.top=Math.max(8,Math.min(windowDrag.top+event.clientY-windowDrag.y,innerHeight-80))+'px';
});
function stopWindowDrag(){windowDrag=null}
dispatchTitle.addEventListener('pointerup',stopWindowDrag);dispatchTitle.addEventListener('pointercancel',stopWindowDrag);
window.addEventListener('resize',clampDispatchWindow);
