'use strict';
window.WorkspaceUI=(()=>{
 const stage=document.getElementById('desk'),ids=['window-map','window-resources','window-jobs','window-communication','chat-panel'];
 let lastSize='',gesture=null,front=10;
 const small=()=>stage.clientWidth<800,key=()=>`noe-window-layout-v1-${small()?'small':'large'}-${document.getElementById('chat-panel').classList.contains('hidden')?'single':'multi'}`;
 const visible=()=>ids.filter(id=>!document.getElementById(id).classList.contains('hidden'));
 function defaults(){
  if(small())return {'window-map':[0,0,1,.47],'window-resources':[0,.48,.49,.25],'window-jobs':[.5,.48,.5,.25],'window-communication':visible().includes('chat-panel')?[.5,.74,.5,.26]:[0,.74,1,.26],'chat-panel':[0,.74,.49,.26]};
  const multi=visible().includes('chat-panel');return {'window-map':[0,0,.58,multi?.73:1],'window-resources':[.59,0,.41,.32],'window-jobs':[.59,.33,.41,.34],'window-communication':[.59,.68,.41,.32],'chat-panel':[0,.74,.58,.26]};
 }
 function load(){try{return JSON.parse(localStorage.getItem(key()))||{}}catch{return{}}}
 function apply(id,box){const panel=document.getElementById(id),w=stage.clientWidth,h=stage.clientHeight;
  const width=Math.min(w,Math.max(Math.min(180,w),box[2]*w)),height=Math.min(h,Math.max(Math.min(100,h),box[3]*h));
  const x=Math.max(0,Math.min(box[0]*w,w-width)),y=Math.max(0,Math.min(box[1]*h,h-height));
  Object.assign(panel.style,{left:x+'px',top:y+'px',width:width+'px',height:height+'px'});
 }
 function save(){const w=stage.clientWidth,h=stage.clientHeight;if(!w||!h)return;const boxes=load();visible().forEach(id=>{const p=document.getElementById(id);boxes[id]=[p.offsetLeft/w,p.offsetTop/h,p.offsetWidth/w,p.offsetHeight/h]});try{localStorage.setItem(key(),JSON.stringify(boxes))}catch{}}
 function sync(){const w=stage.clientWidth,h=stage.clientHeight;if(!w||!h)return;const size=`${w},${h},${visible().join(',')}`;if(size===lastSize)return;lastSize=size;const saved=load(),base=defaults();visible().forEach(id=>apply(id,Array.isArray(saved[id])&&saved[id].length===4&&saved[id].every(Number.isFinite)?saved[id]:base[id]));}
 function reset(){try{localStorage.removeItem(key())}catch{}lastSize='';sync()}
 ids.forEach(id=>{const p=document.getElementById(id),head=p.querySelector('.panel-head');p.classList.add('desk-window');
  const handle=document.createElement('button');handle.type='button';handle.className='window-resize';handle.setAttribute('aria-label',head.querySelector('h2').textContent+' vergrößern oder verkleinern');handle.title='An dieser Ecke ziehen';p.append(handle);
  p.addEventListener('pointerdown',()=>p.style.zIndex=++front);
  const begin=(event,resize)=>{if(event.button!==0||!resize&&event.target.closest('button,input,select,a'))return;gesture={id,resize,x:event.clientX,y:event.clientY,left:p.offsetLeft,top:p.offsetTop,width:p.offsetWidth,height:p.offsetHeight};event.currentTarget.setPointerCapture(event.pointerId);event.preventDefault()};
  head.addEventListener('pointerdown',e=>begin(e,false));handle.addEventListener('pointerdown',e=>begin(e,true));
  const move=event=>{if(!gesture||gesture.id!==id)return;const g=gesture,w=stage.clientWidth,h=stage.clientHeight,dx=event.clientX-g.x,dy=event.clientY-g.y;
   const width=g.resize?Math.max(Math.min(180,w),Math.min(w-g.left,g.width+dx)):g.width,height=g.resize?Math.max(Math.min(100,h),Math.min(h-g.top,g.height+dy)):g.height;
   const x=g.resize?g.left:Math.max(0,Math.min(w-width,g.left+dx)),y=g.resize?g.top:Math.max(0,Math.min(h-height,g.top+dy));
   Object.assign(p.style,{left:x+'px',top:y+'px',width:width+'px',height:height+'px'});
  };
  const end=()=>{if(gesture?.id===id){gesture=null;save()}};
  [head,handle].forEach(target=>{target.addEventListener('pointermove',move);target.addEventListener('pointerup',end);target.addEventListener('pointercancel',end)});
  handle.onkeydown=event=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))return;event.preventDefault();const w=stage.clientWidth,h=stage.clientHeight;apply(id,[p.offsetLeft/w,p.offsetTop/h,(p.offsetWidth+(event.key==='ArrowRight'?20:event.key==='ArrowLeft'?-20:0))/w,(p.offsetHeight+(event.key==='ArrowDown'?20:event.key==='ArrowUp'?-20:0))/h]);save()};
 });
 document.getElementById('reset-layout').onclick=()=>{reset();document.getElementById('desk-menu').open=false};
 new ResizeObserver(()=>requestAnimationFrame(sync)).observe(stage);
 new ResizeObserver(()=>requestAnimationFrame(()=>{if(window.leafletMap)window.leafletMap.invalidateSize({pan:false});else if(typeof leafletMap!=='undefined')leafletMap?.invalidateSize({pan:false})})).observe(document.getElementById('map'));
 return {sync,reset};
})();
