'use strict';
(()=>{
 const notice=document.getElementById('site-notice');if(!notice)return;
 const key='stratosi-privacy-notice-v1';let dismissed=false;
 try{dismissed=sessionStorage.getItem(key)==='seen'}catch{/* Storage can be disabled. */}
 function update(){
  const playing=notice.dataset.scope==='simulator'&&!document.body.classList.contains('lobby-open');
  notice.hidden=dismissed||playing;
  document.documentElement.style.setProperty('--site-notice-height',notice.hidden?'0px':notice.offsetHeight+'px');
 }
 notice.querySelector('button').onclick=()=>{dismissed=true;try{sessionStorage.setItem(key,'seen')}catch{}update()};
 new MutationObserver(update).observe(document.body,{attributes:true,attributeFilter:['class']});
 if(typeof ResizeObserver==='function')new ResizeObserver(update).observe(notice);
 window.addEventListener('resize',update);update();
})();
