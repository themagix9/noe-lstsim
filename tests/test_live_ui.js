const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={km:(v,j)=>Math.abs(v.lat-j.lat)*111};vm.createContext(context);vm.runInContext(fs.readFileSync('app/static/live-ui.js','utf8'),context);
for(const [type,filter,expected] of [['RTW-C','RTW',true],['RTW-C','RTW-C',true],['BKTW','KTW',true],['KTW','NA',false],['NAH','NA',true],['NEF','NEF',true],['NAH','NEF',false],['FR','FR',true]])assert.equal(context.matchesResourceFilter({type},filter),expected);
const a={id:'a',type:'RTW',callsign:'77/002',status:'enroute',lat:48,station:'s'},b={id:'b',type:'KTW',callsign:'77/003',status:'ready',lat:48.1,station:'s'},j={lat:48,resource_eta:{a:{status:'ready',seconds:300,distance_m:2000},b:{status:'ready',seconds:120,distance_m:5000}}};
assert(context.compareResources(a,b,j,'distance','asc',[])<0);assert(context.compareResources(a,b,j,'eta','asc',[])>0);assert(context.compareResources(a,b,j,'status','asc',[])>0);assert(context.compareResources(a,b,j,'callsign','desc',[])>0);
console.log('Resource filter and sorting tests passed.');
