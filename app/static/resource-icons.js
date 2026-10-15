'use strict';
// Keep an unsaved icon choice stable while live simulation updates arrive.
window.ResourceIcons=(()=>{
 let selected='',draft='',signature='',voiceAudio=null,voiceUrl=null;
 const vehicleSelect=document.getElementById('icon-resource');
 const graphicSelect=document.getElementById('icon-graphic');
 const search=document.getElementById('icon-resource-search');
 const save=document.getElementById('save-resource-icon');
 const upload=document.getElementById('settings-upload-graphic');
 function render(){
  if(!state)return;
  const query=search.value.toLocaleLowerCase('de');
  const candidates=state.vehicles.filter(v=>(v.callsign+' '+v.type+' '+(station(v.station)?.name||'')).toLocaleLowerCase('de').includes(query)).sort((a,b)=>a.callsign.localeCompare(b.callsign,'de',{numeric:true}));
  if(!candidates.some(v=>v.id===selected)){selected=candidates[0]?.id||'';draft=state.vehicles.find(v=>v.id===selected)?.graphic||''}
  const next=JSON.stringify([candidates.map(v=>[v.id,v.callsign,v.type,v.station]),state.graphics.map(g=>[g.id,g.name])]);
  if(signature!==next){
   vehicleSelect.innerHTML=candidates.map(v=>`<option value="${esc(v.id)}">${esc(v.type+' '+resourceName(v)+' · '+station(v.station)?.name)}</option>`).join('');
   graphicSelect.innerHTML=state.graphics.map(g=>`<option value="${esc(g.id)}">${esc(g.name)}</option>`).join('');signature=next;
  }
  vehicleSelect.value=selected;graphicSelect.value=draft;
  const graphic=state.graphics.find(g=>g.id===draft),preview=document.getElementById('resource-icon-preview');
  preview.hidden=!graphic;if(graphic){preview.src=graphic.url;preview.alt=graphic.name}
  const v=state.vehicles.find(v=>v.id===selected);
  document.getElementById('resource-icon-info').textContent=graphic?graphic.name+' · '+graphic.author+' · '+graphic.license:'Keine passende Ressource gefunden.';
  document.getElementById('resource-voice-info').textContent=v?.voice_profile?'Feste Sprecherstimme '+(v.voice_profile.speaker_id+1)+' · bleibt bei Statuswechsel und Neustart erhalten.':'';
  document.getElementById('preview-resource-voice').disabled=!v;
  save.disabled=!v||!graphic||!state.session.host||v.graphic===draft;
  graphicSelect.disabled=!state.session.host;upload.disabled=!state.session.host;
 }
 document.getElementById('preview-resource-voice').onclick=async()=>{
  const button=document.getElementById('preview-resource-voice');button.disabled=true;
  try{if(voiceAudio)voiceAudio.pause();if(voiceUrl)URL.revokeObjectURL(voiceUrl);const response=await fetch('/api/resource_voice?vehicle='+encodeURIComponent(selected),{headers:authHeaders()});if(!response.ok)throw Error('Stimme derzeit nicht verfügbar.');voiceUrl=URL.createObjectURL(await response.blob());voiceAudio=new Audio(voiceUrl);voiceAudio.playbackRate=1;await voiceAudio.play()}catch(error){toast(error.message)}finally{button.disabled=false}
 };
 search.oninput=render;
 vehicleSelect.onchange=()=>{selected=vehicleSelect.value;draft=state.vehicles.find(v=>v.id===selected)?.graphic||'';render()};
 graphicSelect.onchange=()=>{draft=graphicSelect.value;render()};
 save.onclick=async()=>{if(await command('vehicle_graphic',{vehicle:selected,graphic:draft})){render();toast('Ressourcen-Icon gespeichert.')}};
 upload.onclick=()=>document.getElementById('graphic-dialog').showModal();
 return {render};
})();
