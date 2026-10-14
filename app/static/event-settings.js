'use strict';
window.EventSettings=(()=>{
 const form=document.getElementById('event-settings'),emergency=document.getElementById('emergency-rate'),transport=document.getElementById('transport-rate'),enabled=document.getElementById('transports-enabled'),save=document.getElementById('save-event-settings'),only=document.getElementById('only-emergencies'),note=document.getElementById('event-settings-note');
 let dirty=false,room=null,signature=null,host=false;
 function controls(){emergency.disabled=!host;enabled.disabled=!host;transport.disabled=!host||!enabled.checked;save.disabled=!host;only.disabled=!host}
 form.addEventListener('input',()=>{dirty=true;controls()});
 function render(snapshot){const settings=snapshot.event_settings;if(!settings)return;host=!!snapshot.session.host;if(room!==snapshot.session.me){room=snapshot.session.me;dirty=false;signature=null}const next=JSON.stringify(settings);if(!dirty&&next!==signature){emergency.value=settings.emergency_per_hour;transport.value=settings.transport_per_hour;enabled.checked=settings.transports_enabled;signature=next}controls();note.textContent=host?'Gilt für die gesamte Sitzung. Änderungen starten die Wartezeit für neue Aufträge neu.':'Die Einsatzfrequenz wird vom Sitzungsleiter festgelegt.'}
 async function submit(){if(!form.reportValidity())return;const data={emergency_per_hour:Number(emergency.value),transport_per_hour:Number(transport.value),transports_enabled:enabled.checked};if(await command('event_settings',data)){dirty=false;render(state);toast('Einsatzfrequenz gespeichert.')}}
 form.onsubmit=event=>{event.preventDefault();submit()};only.onclick=()=>{enabled.checked=false;if(Number(emergency.value)===0)emergency.value=3;dirty=true;controls();submit()};
 return {render};
})();
