'use strict';
// Fixed incident window: only the resource table scrolls. Long documents use pages.
window.DispatchLayout=(()=>{
 const pages=new Map();let scheduled=false;
 function resetList(){const list=document.querySelector('#detail .resource-list');if(list)list.scrollTop=0}
 function fit(){
  scheduled=false;const dialog=document.getElementById('dispatch-dialog');
  if(!dialog?.open)return;
  const panel=dialog.querySelector('[role="tabpanel"]:not([hidden])');if(!panel)return;
  if(panel.id==='detail-panel-disposition'||panel.matches('.call-panel'))return;
  const key=(document.getElementById('detail').dataset.job||'')+':'+panel.id;
  panel.querySelectorAll('.dispatch-page-hidden').forEach(e=>e.classList.remove('dispatch-page-hidden'));
  let nav=panel.querySelector(':scope > .dispatch-page-nav');nav?.remove();
  const capacity=Math.max(80,panel.clientHeight-40);
  function items(e){
   if(e.hidden||!e.getBoundingClientRect().height)return [];
   const children=[...e.children];
   const structural=e.matches('.job-fields,.alarm-document,[data-key="support-card"]');
   const oversized=e.getBoundingClientRect().height>capacity&&children.length>1&&!e.matches('label,button,p,input,select,textarea');
   return structural||oversized?children.flatMap(items):[e];
  }
  const units=[...panel.children].flatMap(items);
  const groups=[];
  for(const e of units){const rect=e.getBoundingClientRect(),last=groups.at(-1);if(last&&Math.abs(last.top-rect.top)<3){last.elements.push(e);last.bottom=Math.max(last.bottom,rect.bottom)}else groups.push({top:rect.top,bottom:rect.bottom,elements:[e]})}
  let used=0;const chunks=[[]];
  for(const group of groups){const height=group.bottom-group.top+8;if(used+height>capacity&&chunks.at(-1).length){chunks.push([]);used=0}chunks.at(-1).push(...group.elements);used+=height}
  if(chunks.length<=1){pages.set(key,0);return}
  let current=Math.min(pages.get(key)||0,chunks.length-1);
  const focused=document.activeElement,focusedPage=chunks.findIndex(items=>items.some(e=>e===focused||e.contains(focused)));
  if(focusedPage>=0)current=focusedPage;
  pages.set(key,current);
  chunks.forEach((items,i)=>items.forEach(e=>e.classList.toggle('dispatch-page-hidden',i!==current)));
  nav=document.createElement('div');nav.className='dispatch-page-nav';
  nav.innerHTML=`<button type="button" ${current===0?'disabled':''} aria-label="Vorige Seite">← Zurück</button><span>Seite ${current+1} / ${chunks.length}</span><button type="button" ${current===chunks.length-1?'disabled':''} aria-label="Nächste Seite">Weiter →</button>`;
  nav.firstElementChild.onclick=()=>{pages.set(key,current-1);nav.firstElementChild.blur();fit()};nav.lastElementChild.onclick=()=>{pages.set(key,current+1);nav.lastElementChild.blur();fit()};panel.append(nav);
 }
 function sync(){if(scheduled)return;scheduled=true;requestAnimationFrame(fit)}
 window.addEventListener('resize',sync);
 new ResizeObserver(sync).observe(document.getElementById('dispatch-dialog'));
 return {sync,resetList};
})();
