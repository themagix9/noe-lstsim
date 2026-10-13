'use strict';
// One reminder per incident and pickup time, measured in shared simulation time.
function createTransportReminders(storage,onDue){
 let room=null,seen=new Set();
 return {check(state){
  if(!state?.session)return;
  const key='noe-transport-reminders-'+state.session.me;
  if(room!==key){room=key;try{seen=new Set(JSON.parse(storage.getItem(key)||'[]'))}catch{seen=new Set()}}
  if(state.paused)return;
  const due=state.jobs.filter(j=>j.kind==='transport'&&j.status==='new'&&!j.vehicles.length&&Number.isFinite(j.due)&&j.due-state.clock<=1800&&!seen.has(j.id+':'+j.due));
  if(!due.length)return;
  due.forEach(j=>seen.add(j.id+':'+j.due));
  try{storage.setItem(key,JSON.stringify([...seen].slice(-1000)))}catch{}
  onDue(due);
 }};
}
function createRadioReminders(onIncoming){
 let room=null,seen=new Set();
 return {check(state){
  if(!state?.session)return;
  const incoming=(state.logs||[]).filter(l=>l.channel==='Funk'&&/^(LEO von |Hier )/.test(l.text));
  const keys=incoming.map(l=>l.time+':'+l.text);
  if(room!==state.session.me){room=state.session.me;seen=new Set(keys);return}
  const fresh=keys.filter(k=>!seen.has(k));keys.forEach(k=>seen.add(k));
  if(seen.size>1000)seen=new Set(keys);
  if(fresh.length)onIncoming();
 }};
}
if(typeof window!=='undefined'){
 let context=null,pending=false,pendingRadio=false;
 let prefs={enabled:true,radioEnabled:true,volume:25};
 try{prefs={...prefs,...JSON.parse(localStorage.getItem('noe-sound-settings')||'{}')}}catch{}
 prefs.volume=Math.max(0,Math.min(100,Number(prefs.volume)||0));
 const enabled=document.getElementById('transport-gong-enabled'),volume=document.getElementById('sound-volume'),radioEnabled=document.getElementById('radio-sound-enabled');
 radioEnabled.checked=!!prefs.radioEnabled;
 enabled.checked=!!prefs.enabled;volume.value=prefs.volume;
 function gong(){
  if(!prefs.enabled||!prefs.volume){pending=false;return}
  if(!context||context.state!=='running'){pending=true;return}
  pending=false;
  // Original bell synthesized locally; no external audio assets.
  const start=context.currentTime;
  [[523.25,1],[1046.5,.35],[1574,.15]].forEach(([frequency,level])=>{
   const oscillator=context.createOscillator(),gain=context.createGain();
   oscillator.type='sine';oscillator.frequency.value=frequency;
   gain.gain.setValueAtTime(.0001,start);gain.gain.exponentialRampToValueAtTime(prefs.volume/100*.3*level,start+.015);gain.gain.exponentialRampToValueAtTime(.0001,start+1.8);
   oscillator.connect(gain);gain.connect(context.destination);oscillator.start(start);oscillator.stop(start+1.9);
   oscillator.onended=()=>{oscillator.disconnect();gain.disconnect()};
  });
 }
 function unlock(){
  const Audio=window.AudioContext||window.webkitAudioContext;if(!Audio)return;
  try{context=context||new Audio();context.resume().then(()=>{if(pending)gong();if(pendingRadio)radioTone()}).catch(()=>{})}catch{}
 }
 function radioTone(){
  if(!prefs.radioEnabled||!prefs.volume){pendingRadio=false;return}
  if(!context||context.state!=='running'){pendingRadio=true;return}
  pendingRadio=false;
  const ownTone=()=>{[1400,1800].forEach((frequency,i)=>{const o=context.createOscillator(),g=context.createGain(),start=context.currentTime+i*.09;o.type='sine';o.frequency.value=frequency;g.gain.setValueAtTime(.0001,start);g.gain.exponentialRampToValueAtTime(prefs.volume/100*.2,start+.008);g.gain.exponentialRampToValueAtTime(.0001,start+.075);o.connect(g);g.connect(context.destination);o.start(start);o.stop(start+.08);o.onended=()=>{o.disconnect();g.disconnect()}})};
  const custom=localStorage.getItem('noe-radio-custom-sound');
  if(custom&&custom.startsWith('data:audio/')){const audio=new window.Audio(custom);audio.volume=prefs.volume/100;audio.play().then(()=>setTimeout(()=>audio.pause(),5000)).catch(ownTone)}else ownTone();
 }
 document.addEventListener('pointerdown',unlock,{passive:true});document.addEventListener('keydown',unlock);
 function save(){prefs.enabled=enabled.checked;prefs.radioEnabled=radioEnabled.checked;prefs.volume=Number(volume.value);localStorage.setItem('noe-sound-settings',JSON.stringify(prefs));if(!prefs.enabled)pending=false;if(!prefs.radioEnabled)pendingRadio=false}
 enabled.onchange=save;volume.oninput=save;radioEnabled.onchange=save;
 document.getElementById('test-radio-sound').onclick=()=>{unlock();radioTone()};
 document.getElementById('radio-sound-file').onchange=event=>{const file=event.target.files[0];if(!file)return;if(file.size>1024*1024||!file.type.startsWith('audio/')){if(typeof toast==='function')toast('Audiodatei bis 1 MB auswählen.');return}const reader=new FileReader();reader.onload=()=>{try{localStorage.setItem('noe-radio-custom-sound',reader.result);if(typeof toast==='function')toast('Eigener Funkton lokal gespeichert.')}catch{if(typeof toast==='function')toast('Funkton konnte nicht gespeichert werden.')}};reader.readAsDataURL(file)};
 document.getElementById('reset-radio-sound').onclick=()=>{localStorage.removeItem('noe-radio-custom-sound');document.getElementById('radio-sound-file').value='';if(typeof toast==='function')toast('Eigener Standard-Funkton aktiv.')};
 document.getElementById('test-transport-gong').onclick=()=>{unlock();gong()};
 window.TransportReminders=createTransportReminders(sessionStorage,jobs=>{
  gong();if(typeof toast==='function')toast(jobs.length===1?'Transport abholbereit: '+jobs[0].address+' · Abholung '+time(jobs[0].due).slice(0,5):jobs.length+' Transportaufträge erreichen die 30-Minuten-Marke.');
 });
 window.RadioNotifications=createRadioReminders(radioTone);
}
if(typeof module!=='undefined')module.exports={createTransportReminders,createRadioReminders};
