'use strict';
// Draw along the server's route between live snapshots, without rendering forms.
(function(root){
 const moving=new Set(['enroute','transport','radio','duty']);
 function position(leg,fraction){
  const f=Math.max(0,Math.min(1,fraction)),coords=leg.geometry,weights=leg.cumulative;
  if(coords?.length>=2&&weights?.length===coords.length&&weights.at(-1)>0){
   const distance=f*weights.at(-1);let low=0,high=weights.length-1;
   while(low+1<high){const middle=(low+high)>>1;if(weights[middle]<=distance)low=middle;else high=middle}
   const width=weights[low+1]-weights[low],part=width>0?(distance-weights[low])/width:0;
   return [coords[low][0]+(coords[low+1][0]-coords[low][0])*part,coords[low][1]+(coords[low+1][1]-coords[low][1])*part];
  }
  return [leg.lat+(leg.target_lat-leg.lat)*f,leg.lon+(leg.target_lon-leg.lon)*f];
 }
 function create(options={}){
  const now=options.now||(()=>performance.now()),request=options.requestFrame||(cb=>requestAnimationFrame(cb)),cancel=options.cancelFrame||(id=>cancelAnimationFrame(id));
  const tracks=new Map();let anchor={clock:0,speed:1,paused:true,received:now()},frameId=null,room=null;
  function clock(){return anchor.clock+(anchor.paused?0:Math.max(0,Math.min(3,(now()-anchor.received)/1000))*anchor.speed)}
  const signature=v=>[v.job,v.status,v.leg?.start,v.leg?.end,v.leg?.target_lat,v.leg?.target_lon].join('|');
  function point(v){
   const leg=v.leg;if(!moving.has(v.status)||!leg||leg.waiting||!(leg.end>leg.start))return [v.lat,v.lon];
   const key=signature(v),track=tracks.get(v.id),previous=track?.key===key?track.fraction:0;
   const fraction=Math.max(previous,Math.max(0,Math.min(1,(clock()-leg.start)/(leg.end-leg.start))));
   if(track&&track.key===key)track.fraction=fraction;
   return position(leg,fraction);
  }
  function draw(){frameId=null;if(anchor.paused)return;
   for(const track of tracks.values()){const next=point(track.vehicle),current=track.layer.getLatLng();if(current.lat!==next[0]||current.lng!==next[1])track.layer.setLatLng(next)}
   start();
  }
  function start(){if(frameId===null&&!anchor.paused&&tracks.size)frameId=request(draw)}
  function sync(snapshot){
   const nextRoom=snapshot.session?.me||null;
   if(nextRoom!==room||snapshot.clock<anchor.clock){tracks.clear();room=nextRoom}
   anchor={clock:snapshot.clock,speed:snapshot.speed,paused:snapshot.paused,received:now()};
   if(anchor.paused&&frameId!==null){cancel(frameId);frameId=null}
   start();
  }
  function attach(v,layer){
   if(!moving.has(v.status)||!v.leg||v.leg.waiting||!(v.leg.end>v.leg.start)){tracks.delete(v.id);return}
   const key=signature(v),old=tracks.get(v.id);
   tracks.set(v.id,{key,vehicle:v,layer,fraction:old?.key===key?old.fraction:0});
   layer.setLatLng(point(v));start();
  }
  function retain(ids){for(const id of tracks.keys())if(!ids.has(id))tracks.delete(id);if(!tracks.size&&frameId!==null){cancel(frameId);frameId=null}}
  function clear(){tracks.clear();if(frameId!==null)cancel(frameId);frameId=null}
  return {sync,point,attach,retain,clear};
 }
 root.ResourceMotion={create,position};
})(typeof window==='undefined'?globalThis:window);
