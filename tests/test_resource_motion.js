const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={};vm.createContext(context);vm.runInContext(fs.readFileSync('app/static/resource-motion.js','utf8'),context);
const {position,create}=context.ResourceMotion;
const leg={start:100,end:110,lat:0,lon:0,target_lat:10,target_lon:10,geometry:[[0,0],[0,10],[10,10]],cumulative:[0,10,20]};
const point=f=>Array.from(position(leg,f));
assert.deepEqual(point(.25),[0,5]);assert.deepEqual(point(.75),[5,10]);assert.deepEqual(point(-1),[0,0]);assert.deepEqual(point(2),[10,10]);
assert.deepEqual(Array.from(position({...leg,geometry:null,cumulative:null},.5)),[5,5]);
let now=0,nextId=0,callbacks=new Map(),drawn=[0,0],moves=0;
const motion=create({now:()=>now,requestFrame:cb=>{callbacks.set(++nextId,cb);return nextId},cancelFrame:id=>callbacks.delete(id)});
const layer={setLatLng:p=>{drawn=Array.from(p);moves++},getLatLng:()=>({lat:drawn[0],lng:drawn[1]})};
const vehicle={id:'v',status:'enroute',job:'j',lat:0,lon:0,leg};
motion.sync({clock:100,speed:1,paused:false,session:{me:'one'}});motion.attach(vehicle,layer);
function frame(ms){now=ms;const entry=callbacks.entries().next().value;assert(entry);callbacks.delete(entry[0]);entry[1]()}
frame(100);frame(200);frame(500);assert.deepEqual(drawn,[0,1]);assert(moves>=4);assert.equal(vehicle.lat,0);
// An older server position must not move the marker backwards on the same leg.
motion.sync({clock:100.4,speed:1,paused:false,session:{me:'one'}});frame(550);assert(drawn[1]>=1);
motion.sync({clock:100.5,speed:1,paused:true,session:{me:'one'}});assert.equal(callbacks.size,0);
const paused=[...drawn];now=9000;assert.deepEqual(drawn,paused);
motion.sync({clock:101,speed:1,paused:false,session:{me:'one'}});motion.attach(vehicle,layer);motion.retain(new Set());assert.equal(callbacks.size,0);
motion.attach(vehicle,layer);motion.clear();assert.equal(callbacks.size,0);
console.log('Smooth route motion: street geometry, frames, pause, monotonic progress and cleanup passed.');
