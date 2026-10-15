'use strict';
(()=>{
 const menu=document.createElement('div');menu.className='vehicle-menu';menu.id='vehicle-menu';menu.hidden=true;menu.setAttribute('role','menu');menu.setAttribute('aria-label','Fahrzeugaktionen');document.body.append(menu);
 let current=null,ring=null,ringTimer=null;
 const close=()=>{menu.hidden=true;current=null};
 function positionVehicle(v){
  if(!leafletMap||!Number.isFinite(v.lat)||!Number.isFinite(v.lon)){toast('Keine Kartenposition vorhanden.');return}
  leafletMap.setView([v.lat,v.lon],14,{animate:false});
  if(ring)ring.remove();clearTimeout(ringTimer);ring=L.circleMarker([v.lat,v.lon],{radius:16,color:'#2563eb',weight:3,fillOpacity:.12,interactive:false}).addTo(leafletMap);ringTimer=setTimeout(()=>{ring?.remove();ring=null},5000);
  const key=mapVisible(v)?'vehicle:'+v.id:v.status==='scene'&&v.job?'job:'+v.job:'station:'+v.station;mapObjects.get(key)?.layer.openPopup();
  $('map-note').textContent=v.type+' '+resourceName(v)+' · '+statusName(v)+(v.holding?' · Standort halten':'');
 }
 function show(v,event){
  current=v.id;const allowed=!v.job&&!v.support_request&&!v.fueling&&['radio','duty'].includes(v.status)&&!(splitWorkflow()&&state.session.role!=='dispatcher');
  menu.innerHTML=`<b>${esc(v.type+' '+resourceName(v))}</b><span>${esc(statusName(v))}${v.holding?' · Standort halten':''}</span><button role="menuitem" data-vehicle-menu-action="position">Position auf Karte anzeigen</button><button role="menuitem" data-vehicle-menu-action="return" ${allowed?'':'disabled'}>Per Funk: Zur Wache einrücken</button><button role="menuitem" data-vehicle-menu-action="hold" ${allowed?'':'disabled'}>Per Funk: Standort halten</button>${v.job?`<button role="menuitem" data-vehicle-menu-action="job">Einsatz öffnen / Storno</button>`:''}<p>${v.job?'Einsatzbindung zuerst über Storno aufheben.':'Bewegungsaufträge für freie Fahrzeuge in Status 6 oder 7.'}</p>`;
  menu.hidden=false;const row=event.target.closest('[data-fleet-vehicle]').getBoundingClientRect(),x=event.clientX||row.left,y=event.clientY||row.bottom;menu.style.left=Math.max(8,Math.min(x,innerWidth-menu.offsetWidth-8))+'px';menu.style.top=Math.max(8,Math.min(y,innerHeight-menu.offsetHeight-8))+'px';menu.querySelector('button').focus();
 }
 document.addEventListener('click',event=>{if(menu.contains(event.target))return;const row=event.target.closest('#fleet-table [data-fleet-vehicle]');if(row&&!event.target.closest('button,input,select')){const v=state?.vehicles.find(v=>v.id===row.dataset.fleetVehicle);if(v)show(v,event)}else close()});
 document.addEventListener('contextmenu',event=>{const row=event.target.closest('#fleet-table [data-fleet-vehicle]');if(!row)return;event.preventDefault();const v=state?.vehicles.find(v=>v.id===row.dataset.fleetVehicle);if(v)show(v,event)});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'){close();return}if(['Enter',' '].includes(event.key)&&event.target.matches('#fleet-table [data-fleet-vehicle]')){event.preventDefault();const v=state?.vehicles.find(v=>v.id===event.target.dataset.fleetVehicle);if(v)show(v,event)}else if(!menu.hidden&&['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();const buttons=[...menu.querySelectorAll('button:not(:disabled)')],i=buttons.indexOf(document.activeElement);buttons[(i+(event.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus()}});
 menu.onclick=async event=>{const button=event.target.closest('[data-vehicle-menu-action]');if(!button)return;const v=state?.vehicles.find(v=>v.id===current),action=button.dataset.vehicleMenuAction;close();if(!v)return;if(action==='position')positionVehicle(v);else if(action==='job'&&v.job)openDispatch(v.job);else await command('vehicle_order',{vehicle:v.id,order:action})};
 window.addEventListener('resize',close);
})();
