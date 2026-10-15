'use strict';
function viennaAction(job,clock){
 if(!job||job.status==='done'||!['requested','calling','allocated'].includes(job.bed_state))return null;
 const since=job.bed_requested_at??job.scene_report?.time??job.created??clock;
 const minutes=Math.max(0,Math.floor((clock-since)/60)),urgent=minutes>=10;
 return {id:job.id,stage:job.bed_state,minutes,urgent,actionable:job.bed_state!=='calling',label:job.bed_state==='allocated'?'Kasusnummer liegt vor – an Mannschaft senden':job.bed_state==='calling'?'Bettenmann angefragt – Antwort ausständig':'Wiener Ziel – Kasusnummer erforderlich',button:job.bed_state==='allocated'?'Kasusnummer senden':job.bed_state==='calling'?'Zielabklärung öffnen':'Bettenmann anfragen'};
}
function createViennaReminders(storage,onDue){
 let room=null,seen=new Set();
 return {check(state){if(!state?.session)return;const key='noe-vienna-reminders-'+state.session.me;if(room!==key){room=key;try{seen=new Set(JSON.parse(storage.getItem(key)||'[]'))}catch{seen=new Set()}}
 const fresh=[];for(const job of state.jobs){const action=viennaAction(job,state.clock);if(!action?.actionable)continue;const id=job.id+':'+action.stage+':'+(action.urgent?'overdue':'new');if(seen.has(id))continue;seen.add(id);fresh.push({job,action})}
 if(!fresh.length)return;try{storage.setItem(key,JSON.stringify([...seen].slice(-1000)))}catch{}onDue(fresh);
 }};
}
if(typeof window!=='undefined'){
 const box=document.createElement('div');box.id='vienna-alerts';box.className='vienna-alerts';box.hidden=true;box.setAttribute('role','status');box.setAttribute('aria-live','polite');document.getElementById('jobs').before(box);
 const reminder=createViennaReminders(sessionStorage,items=>{window.ViennaSound?.play();toast(items.length===1?items[0].action.label+' · Einsatz '+items[0].job.incident_number:items.length+' Einsätze warten auf Wiener Zielabklärung.');});
 document.addEventListener('click',event=>{const button=event.target.closest('[data-vienna-job]');if(!button)return;event.stopPropagation();openDispatch(button.dataset.viennaJob);switchDetailTab('transport')});
 window.ViennaAlerts={action:viennaAction,render(snapshot){const pending=snapshot.jobs.map(job=>({job,action:viennaAction(job,snapshot.clock)})).filter(x=>x.action).sort((a,b)=>Number(b.action.urgent)-Number(a.action.urgent)||b.action.minutes-a.action.minutes);box.hidden=!pending.length;const html=pending.map(({job,action})=>`<div data-key="vienna-${esc(job.id)}" class="vienna-alert ${action.urgent?'overdue':''}"><b>${esc(action.label)}</b><span>Einsatz ${esc(job.incident_number)} · ${action.minutes} Min. seit Zielanforderung${job.owner?' · '+esc(ownerName(job)):''}</span><button type="button" data-vienna-job="${esc(job.id)}">${esc(action.button)}</button></div>`).join('');if(box.innerHTML!==html)patchHtml(box,html);reminder.check(snapshot)}};
}
if(typeof module!=='undefined')module.exports={viennaAction,createViennaReminders};
