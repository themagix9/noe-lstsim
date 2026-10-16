'use strict';
// One manual ad per page. Google CMP supplies consent; never invent consent here.
window.LandingAds=(()=>{
 const aside=document.getElementById('landing-ad'),layout=document.querySelector('.landing-layout'),slot=document.getElementById('landing-ad-slot'),privacy=document.getElementById('ad-privacy');
 let config=null,loaded=false,allowed=false,subscribed=false,requested=false,revoked=false,attempts=0,timer=null;
 const queue=()=>window.adsbygoogle=window.adsbygoogle||[];
 const lobbyVisible=()=>document.body.classList.contains('lobby-open')&&!document.hidden;
 function pause(){if(loaded)queue().pauseAdRequests=1}
 function consent(data,success){
  if(!success||data?.cmpStatus!=='loaded'||!['tcloaded','useractioncomplete'].includes(data.eventStatus)){allowed=false;pause();return}
  allowed=data.gdprApplies===false||(data.gdprApplies===true&&typeof data.tcString==='string'&&!!data.tcString&&data.purpose?.consents?.[1]===true&&data.vendor?.consents?.[755]===true);
  if(!allowed&&requested){revoked=true;slot.replaceChildren()}
  update();
 }
 function subscribe(){
  if(subscribed||!loaded)return;
  if(typeof window.__tcfapi==='function'){
   try{window.__tcfapi('addEventListener',2,consent);subscribed=true;return}catch{/* CMP may still be loading. */}
  }
  if(++attempts<240){clearTimeout(timer);timer=setTimeout(subscribe,500)}
 }
 function ready(){
  privacy.hidden=typeof window.googlefc?.showRevocationMessage!=='function';
  subscribe();
 }
 function load(){
  if(loaded)return;loaded=true;queue().pauseAdRequests=1;
  window.googlefc=window.googlefc||{};window.googlefc.controlledMessagingFunction=message=>message.proceed(!!config?.enabled&&lobbyVisible());window.googlefc.callbackQueue=window.googlefc.callbackQueue||[];
  window.googlefc.callbackQueue.push({CONSENT_API_READY:ready});
  const script=document.createElement('script');script.id='adsense-loader';script.async=true;script.crossOrigin='anonymous';
  script.src='https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='+encodeURIComponent(config.publisher);
  script.onload=()=>{ready();subscribe()};script.onerror=()=>{pause();aside.dataset.state='unavailable'};
  document.head.append(script);subscribe();
 }
 function update(){
  const enabled=!!config?.enabled&&location.protocol==='https:';
  aside.hidden=!enabled;layout.classList.toggle('has-ad',enabled);
  if(!enabled||!lobbyVisible()){pause();return}
  load();if(!allowed||revoked){pause();return}
  queue().pauseAdRequests=0;
  if(requested||slot.getBoundingClientRect().width<1)return;
  const ad=document.createElement('ins');ad.className='adsbygoogle';ad.style.display='block';ad.dataset.adClient=config.publisher;ad.dataset.adSlot=config.slot;ad.dataset.adFormat=matchMedia('(min-width:1250px)').matches?'vertical':'horizontal';ad.dataset.fullWidthResponsive='true';
  slot.append(ad);requested=true;
  try{queue().push({});aside.dataset.state='requested'}catch{aside.dataset.state='unavailable';pause()}
 }
 function configure(value){
  if(!value||value.publisher!=='ca-pub-2546389460875165'||value.slot!=='7480335427')return;
  config=value;requestAnimationFrame(update);
 }
 privacy.onclick=()=>{allowed=false;pause();window.googlefc?.callbackQueue?.push({CONSENT_API_READY:()=>{window.googlefc.showRevocationMessage()}})};
 new MutationObserver(update).observe(document.body,{attributes:true,attributeFilter:['class']});
 document.addEventListener('visibilitychange',update);
 return {configure};
})();
