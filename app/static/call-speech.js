'use strict';
// Audio and server text share a single acknowledged line cursor. Closing the
// floating window suspends this AudioContext, preserving the exact playback point.
window.CallSpeech=(()=>{
 let ctx=null,jobId=null,room=null,line=-1,node=null,epoch=0,busy=false,finished=false,control='',timer=null;
 let enabled=localStorage.getItem('noe-call-voice')!=='0',telephone=localStorage.getItem('noe-call-telephone')!=='0';
 let volume=Number(localStorage.getItem('noe-call-volume')??65)/100;
 let status='',commands=Promise.resolve();
 function unlock(){if(!ctx){const Audio=window.AudioContext||window.webkitAudioContext;if(Audio)ctx=new Audio()}if(ctx?.state==='suspended'&&document.getElementById('dispatch-dialog').open)void ctx.resume().catch(()=>{});sync()}
 function reset(){epoch++;clearTimeout(timer);if(node){node.onended=null;try{node.stop()}catch{}node.disconnect()}node=null;line=-1;busy=false;finished=false;control=''}
 function send(mode,job=jobId,index=line){if(!job)return Promise.resolve(false);commands=commands.then(()=>command('call_playback',{job,mode,line:index}));return commands}
 function active(){const j=state?.jobs.find(j=>j.id===selected);return j?.call?.automatic&&j.owner===state.session.me&&j.accepted?j:null}
 function label(text){status=text;const el=document.getElementById('call-audio-status');if(el)el.textContent=text}
 function complete(token){if(token!==epoch)return;finished=true;busy=false;node=null;timer=setTimeout(()=>{if(token===epoch&&document.getElementById('dispatch-dialog').open){finished=false;send('done');}},250)}
 async function speak(j,index){
  const token=++epoch;busy=true;finished=false;line=index;label('Sprachausgabe wird vorbereitet …');
  try{
   const response=await fetch('/api/call_audio?job='+encodeURIComponent(j.id)+'&line='+index,{headers:authHeaders(),signal:AbortSignal.timeout(18000)});
   if(!response.ok)throw Error('Sprachmodell nicht erreichbar');
   const buffer=await ctx.decodeAudioData(await response.arrayBuffer());if(token!==epoch)return;
   const row=j.call.transcript[index];node=ctx.createBufferSource();node.buffer=buffer;
   // Original synthesized voice at its native speed and pitch, for every line.
   node.playbackRate.value=1;node.detune.value=0;
   const gain=ctx.createGain();gain.gain.value=volume;
   if(telephone&&row.speaker==='Anrufer'){
    const high=ctx.createBiquadFilter(),low=ctx.createBiquadFilter(),compress=ctx.createDynamicsCompressor();
    high.type='highpass';high.frequency.value=300;low.type='lowpass';low.frequency.value=3400;
    compress.threshold.value=-24;compress.ratio.value=4;node.connect(high).connect(low).connect(compress).connect(gain);
   }else node.connect(gain);
   gain.connect(ctx.destination);node.onended=()=>complete(token);node.start();
   if(!document.getElementById('dispatch-dialog').open||j.call.paused)await ctx.suspend();
   label(row.speaker==='Anrufer'&&telephone?'Anrufer · Telefonklang':'Sprachausgabe · '+row.speaker);
  }catch(error){if(token!==epoch)return;busy=false;control='text';label('Keine Sprachausgabe verfügbar · Textdialog läuft weiter.');send('resume')}
 }
 function sync(){
  const j=active(),open=document.getElementById('dispatch-dialog')?.open;
  if(!j){if(jobId){if(state?.session?.me===room)send('pause');reset();jobId=null}return}
  if(jobId!==j.id||room!==state.session.me){if(jobId)send('pause');reset();jobId=j.id;room=state.session.me}
  if(j.call.state!=='connected'){if(j.call.state==='ended')label('Telefonat beendet.');return}
  if(!open){if(control!=='pause'){control='pause';send('pause');if(ctx)void ctx.suspend()}return}
  const speech=enabled&&!!ctx&&control!=='text';
  const mode=speech?'speech':'resume';
  if(control==='pause'||!control){control=speech?'speech':'text';send(mode);if(ctx)void ctx.resume().catch(()=>{});if(speech&&finished){finished=false;send('done')}}
  if(j.call.paused)return;
  const index=j.call.transcript.length-1;
  if(speech&&index>=0&&index!==line&&!busy)speak(j,index);
  if(!speech&&!status)label(enabled?'Für Sprachausgabe einmal ins Fenster klicken.':'Sprachausgabe ausgeschaltet.');
 }
 document.addEventListener('pointerdown',unlock,{passive:true});
 document.addEventListener('keydown',unlock);
 document.addEventListener('click',unlock);
 document.addEventListener('DOMContentLoaded',()=>{
  const dialog=document.getElementById('dispatch-dialog');dialog.addEventListener('close',sync);
  new MutationObserver(sync).observe(dialog,{attributes:true,attributeFilter:['open']});
  for(const [id,value] of [['call-voice-enabled',enabled],['call-telephone-enabled',telephone]])document.getElementById(id).checked=value;
  document.getElementById('call-voice-volume').value=Math.round(volume*100);
  document.getElementById('call-voice-enabled').onchange=e=>{enabled=e.target.checked;localStorage.setItem('noe-call-voice',enabled?'1':'0');reset();sync()};
  document.getElementById('call-telephone-enabled').onchange=e=>{telephone=e.target.checked;localStorage.setItem('noe-call-telephone',telephone?'1':'0')};
  document.getElementById('call-voice-volume').oninput=e=>{volume=Number(e.target.value)/100;localStorage.setItem('noe-call-volume',Math.round(volume*100))};
 });
 return {sync,get status(){return status}};
})();
