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
if(typeof window!=='undefined'){
 let context=null,pending=false;
 let prefs={enabled:true,volume:25};
 try{prefs={...prefs,...JSON.parse(localStorage.getItem('noe-sound-settings')||'{}')}}catch{}
 prefs.volume=Math.max(0,Math.min(100,Number(prefs.volume)||0));
 const enabled=document.getElementById('transport-gong-enabled'),volume=document.getElementById('sound-volume');
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
  try{context=context||new Audio();context.resume().then(()=>{if(pending)gong()}).catch(()=>{})}catch{}
 }
 document.addEventListener('pointerdown',unlock,{passive:true});document.addEventListener('keydown',unlock);
 function save(){prefs.enabled=enabled.checked;prefs.volume=Number(volume.value);localStorage.setItem('noe-sound-settings',JSON.stringify(prefs));if(!prefs.enabled)pending=false}
 enabled.onchange=save;volume.oninput=save;
 document.getElementById('test-transport-gong').onclick=()=>{unlock();gong()};
 window.TransportReminders=createTransportReminders(sessionStorage,jobs=>{
  gong();if(typeof toast==='function')toast(jobs.length===1?'Transport abholbereit: '+jobs[0].address+' · Abholung '+time(jobs[0].due).slice(0,5):jobs.length+' Transportaufträge erreichen die 30-Minuten-Marke.');
 });
}
if(typeof module!=='undefined')module.exports={createTransportReminders};
