'use strict';
window.TelemedicineUI=(()=>{
 function resource(j){const t=j.telenotarzt;return t?`<span class="job-resource tna-resource"><span class="unit-doctor">Telenotarzt</span><span>☎ ${esc(t.phone)}</span></span>`:''}
 function cards(j,disabled){
  const t=j.telenotarzt,pool=state.telenotarzt_pool||{total:10,available:10},request=(state.radio_calls||[]).find(c=>c.job===j.id&&c.kind==='Telenotarzt'&&c.state!=='closed');
  let html=`<div class="destination-card tna-card"><b>Telenotarzt · ${pool.available}/${pool.total} frei</b><p>Ärztliche Einschätzung und Anleitung per Telefon. Kein Notarzt vor Ort und keine Transportbegleitung.</p>`;
  if(t)html+=`<p><strong>Telenotarzt zugebucht</strong> · ☎ <span data-tna-phone>${esc(t.phone)}</span><br>Fiktive Simulationsnummer · per SDS und ESApp an die Mannschaft gesendet.</p><button data-tna-release ${disabled?'disabled':''}>Telefonische Beratung beenden</button>`;
  else if(request?.state==='awaiting_dispatch')html+=`<button data-tna-book="${esc(request.id)}" ${disabled||!pool.available?'disabled':''}>Telenotarzt zubuchen · Telefonnummer senden</button>${!pool.available?'<p>Alle Telenotärzte sind gebunden. Anfrage im Funk ablehnen oder warten lassen.</p>':''}`;
  else if(request)html+='<p>Mannschaft hat einen Sprechwunsch. Anfrage zunächst im Funk abfragen.</p><button data-reinforcement-radio>Zum Funkgespräch</button>';
  else html+='<p>Wird auf Wunsch der Mannschaft über das Funkgespräch zugebucht.</p>';
  html+='</div>';
  const air=j.air_transport_request;
  if(air){const c=(state.radio_calls||[]).find(c=>c.id===air.call),u=state.vehicles.find(v=>v.id===air.unit);html+=`<div class="destination-card"><b>Heli für kritischen Patiententransport</b><p>Bodentransport ${Math.ceil(air.ground_seconds/60)} min${air.approximate?' · vorläufige Schätzung':''} · ${esc(state.hospitals.find(h=>h.id===air.target)?.name||'Zielkrankenhaus')}</p><p>${u?esc(resourceName(u))+' zugebucht':c?.declined?'Negativ · derzeit kein Heli verfügbar':c?.state==='closed'?'Funkgespräch beendet':'Verfügbarkeit beim Disponenten angefragt'}</p>${c&&c.state!=='closed'?'<button data-reinforcement-radio>Heli-Anfrage beantworten</button>':''}</div>`}
  return html;
 }
 function bind(j){
  document.querySelectorAll('[data-tna-book]').forEach(b=>b.onclick=async()=>{if(await command('radio',{job:j.id,call:b.dataset.tnaBook,step:'confirm'}))toast('Telenotarzt zugebucht · Telefonnummer per SDS und ESApp gesendet.')});
  document.querySelectorAll('[data-tna-release]').forEach(b=>b.onclick=()=>command('telenotarzt_release',{job:j.id}));
 }
 return {resource,cards,bind};
})();
