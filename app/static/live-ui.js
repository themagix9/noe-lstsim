'use strict';
// Reconcile nodes instead of replacing forms. Keyed controls keep focus and caret.
function patchHtml(root,html){
 const template=document.createElement('template');template.innerHTML=html;
 const key=n=>n.nodeType===1?(n.id||n.getAttribute('data-key')||''):'';
 const compatible=(a,b)=>a&&a.nodeType===b.nodeType&&(a.nodeType!==1||a.tagName===b.tagName)&&key(a)===key(b);
 function patch(old,fresh){
  if(old.nodeType===3||old.nodeType===8){if(old.nodeValue!==fresh.nodeValue)old.nodeValue=fresh.nodeValue;return}
  const focused=old===document.activeElement;
  for(const a of [...old.attributes])if(!fresh.hasAttribute(a.name)&&!(focused&&a.name==='value'))old.removeAttribute(a.name);
  for(const a of [...fresh.attributes])if(!(focused&&a.name==='value')&&old.getAttribute(a.name)!==a.value)old.setAttribute(a.name,a.value);
  if(old.tagName==='INPUT'){
   if(!focused&&old.value!==fresh.value)old.value=fresh.value;
   if(['checkbox','radio'].includes(old.type))old.checked=fresh.checked;
   return;
  }
  if(focused&&['SELECT','TEXTAREA'].includes(old.tagName))return;
  children(old,fresh);
 }
 function children(old,fresh){
  const previous=[...old.childNodes],used=new Set();let index=0;
  for(const next of [...fresh.childNodes]){
   let current=key(next)?previous.find(n=>!used.has(n)&&key(n)===key(next)):old.childNodes[index];
   if(!compatible(current,next)||used.has(current))current=previous.find(n=>!used.has(n)&&!key(n)&&compatible(n,next));
   if(!current||!compatible(current,next)){current=next.cloneNode(true);old.insertBefore(current,old.childNodes[index]||null)}
   else{if(old.childNodes[index]!==current)old.insertBefore(current,old.childNodes[index]||null);patch(current,next)}
   used.add(current);index++;
  }
  for(const n of previous)if(!used.has(n)&&n.parentNode===old)old.removeChild(n);
 }
 children(root,template.content);
}

function matchesResourceFilter(vehicle,filter){
 if(!filter)return true;
 if(filter==='KTW')return ['KTW','KTW-B','BKTW'].includes(vehicle.type);
 if(filter==='RTW')return ['RTW','RTW-C'].includes(vehicle.type);
 if(filter==='NA')return ['NEF','NAH'].includes(vehicle.type);
 return vehicle.type===filter;
}
function resourceSortValue(vehicle,job,sort,stations){
 const estimate=job.resource_eta?.[vehicle.id],distance=estimate?.distance_m??km(vehicle,job)*1000;
 if(sort==='distance')return distance;
 if(sort==='eta')return estimate?.status==='ready'?estimate.seconds:Number.POSITIVE_INFINITY;
 if(sort==='status')return ({out:0,ready:1,enroute:2,scene:3,transport:4,hospital:5,radio:6,fr_ready:6,duty:7,standby:8,assigned:8.5,acknowledged:9})[vehicle.status]??99;
 if(sort==='type')return vehicle.type;
 if(sort==='station')return stations.find(s=>s.id===vehicle.station)?.name||'';
 return vehicle.callsign;
}
function compareResources(a,b,job,sort,direction,stations){
 const av=resourceSortValue(a,job,sort,stations),bv=resourceSortValue(b,job,sort,stations);
 const order=typeof av==='number'?(av===bv?0:av<bv?-1:1):String(av).localeCompare(String(bv),'de',{numeric:true});
 return order*(direction==='desc'?-1:1)||a.callsign.localeCompare(b.callsign,'de',{numeric:true});
}
