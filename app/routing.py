"""Cached OSRM road routing; one background worker shared by all sessions.
Public FOSSGIS endpoint is for small private exercises only (max 1 request/s).
ROUTING_URL can point to a self-hosted OSRM service without a code change.
"""
import copy
import json
import math
import os
from pathlib import Path
import queue
import sqlite3
import threading
import time
import urllib.request
import urllib.error
import urllib.parse

PUBLIC='https://routing.openstreetmap.de/routed-car'
_registry={};_registry_lock=threading.Lock()

class RoadRouteError(ValueError):pass

def point(p):return [round(float(p['lon']),5),round(float(p['lat']),5)]
def key(a,b):return json.dumps([point(a),point(b)],separators=(',',':'))
def cumulative(coords):
    sums=[0.0]
    for a,b in zip(coords,coords[1:]):
        lat=math.radians((a[0]+b[0])/2)
        sums.append(sums[-1]+math.hypot((b[0]-a[0])*111200,(b[1]-a[1])*111200*math.cos(lat)))
    return sums

def position(leg,fraction):
    coords=leg['geometry'];weights=leg['cumulative'];target=max(0,min(1,fraction))*weights[-1]
    import bisect
    i=min(len(coords)-2,max(0,bisect.bisect_right(weights,target)-1))
    f=(target-weights[i])/(weights[i+1]-weights[i]) if weights[i+1]>weights[i] else 0
    return {name:coords[i][n]+(coords[i+1][n]-coords[i][n])*f for n,name in enumerate(('lat','lon'))}

class Router:
    def __init__(self,path,url=None,enabled=None,fetcher=None):
        self.url=(url or os.environ.get('ROUTING_URL',PUBLIC)).rstrip('/')
        self.enabled=(os.environ.get('ROUTING_ENABLED','1')!='0') if enabled is None else enabled
        self.fetcher=fetcher;self.lock=threading.RLock();self.items={};self.pending=set();self.tasks=queue.PriorityQueue();self.sequence=0;self.next_call=0
        self.path=str(path);self.db=sqlite3.connect(self.path,check_same_thread=False);self.db.execute('PRAGMA busy_timeout=5000')
        self.db.execute('CREATE TABLE IF NOT EXISTS routes (key TEXT PRIMARY KEY, value TEXT NOT NULL, stored REAL NOT NULL)')
        for k,value in self.db.execute('SELECT key,value FROM routes WHERE stored>?',(time.time()-7*86400,)):
            self.items[k]=json.loads(value)
        if self.enabled:threading.Thread(target=self.worker,daemon=True,name='road-routing').start()
    def cachekey(self,a,b):return self.url+'|'+key(a,b)
    def save(self,k,result):
        with self.lock:
            self.items[k]=result
            if result['status']=='ready':
                self.db.execute('INSERT OR REPLACE INTO routes VALUES (?,?,?)',(k,json.dumps(result),time.time()));self.db.commit()
    def enqueue(self,k,priority,fn):
        with self.lock:
            if k in self.pending or len(self.pending)>=200:return
            self.pending.add(k);self.sequence+=1;self.tasks.put((priority,self.sequence,k,fn))
    def worker(self):
        while True:
            _,_,k,fn=self.tasks.get()
            try:fn()
            except Exception as error:
                with self.lock:self.items[k]={'status':'error','retry_at':time.time()+60,'error':'Keine erreichbare Straßenverbindung nach Straßen-Fallback' if isinstance(error,RoadRouteError) else 'Routenserver nicht erreichbar'}
            finally:
                with self.lock:self.pending.discard(k)
                self.tasks.task_done()
    def request(self,path):
        # Global to this server/process, including matrix and individual route requests.
        time.sleep(max(0,self.next_call-time.monotonic()));self.next_call=time.monotonic()+1.1
        if self.fetcher:return self.fetcher(path)
        request=urllib.request.Request(self.url+path,headers={'User-Agent':'NOe-Dispo/0.5 (https://github.com/themagix9/noe-lstsim)','Accept':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=8) as response:raw=response.read(8_000_001)
        except urllib.error.HTTPError as error:
            # OSRM returns NoSegment with HTTP 400. Keep this distinct from an
            # unavailable server so a valid nearest-road recovery can run.
            if error.code!=400:raise
            raw=error.read(8_000_001)
            data=json.loads(raw)
            if data.get('code') not in ('NoSegment','NoRoute'):raise
            return data
        if len(raw)>8_000_000:raise ValueError('Routing response too large')
        return json.loads(raw)
    def route(self,a,b):
        if not self.enabled:return {'status':'disabled'}
        k='route|'+self.cachekey(a,b)
        with self.lock:result=copy.deepcopy(self.items.get(k,{'status':'pending'}))
        if result['status']=='ready' or result.get('retry_at',0)>time.time():return result
        self.enqueue(k,0,lambda:self.fetch_route(k,a.copy(),b.copy()))
        return {'status':'pending'}
    def road_route(self,a,b,hints=None):
        coords=';'.join(','.join(map(str,point(p))) for p in (a,b))
        options='overview=full&geometries=geojson&steps=false'
        if hints:options+='&'+urllib.parse.urlencode({'hints':';'.join(hints)})
        return self.request('/route/v1/driving/'+coords+'?'+options)

    def nearest_roads(self,p):
        coords=','.join(map(str,point(p)))
        data=self.request('/nearest/v1/driving/'+coords+'?number=4')
        if data.get('code')!='Ok':return []
        result=[];seen=set()
        for match in data.get('waypoints',[]):
            lon,lat=map(float,match['location']);distance=float(match.get('distance',0))
            if not all(map(math.isfinite,(lat,lon,distance))) or not -90<=lat<=90 or not -180<=lon<=180 or not 0<=distance<=2000:continue
            fingerprint=(round(lat,7),round(lon,7),match.get('hint',''))
            if fingerprint in seen:continue
            seen.add(fingerprint);result.append(dict(lat=lat,lon=lon,distance_m=distance,hint=match.get('hint','')))
        return result

    def fetch_route(self,k,a,b):
        data=self.road_route(a,b);snap=None
        if data.get('code') in ('NoRoute','NoSegment') or data.get('code')=='Ok' and not data.get('routes'):
            starts=self.nearest_roads(a);ends=self.nearest_roads(b)
            pairs=sorted(((x,y) for x in starts for y in ends),key=lambda pair:pair[0]['distance_m']+pair[1]['distance_m'])
            for x,y in pairs[:8]:
                candidate=self.road_route(x,y,[x['hint'],y['hint']])
                if candidate.get('code')=='Ok' and candidate.get('routes'):
                    data=candidate;snap=dict(origin=x,destination=y);break
        if data.get('code')!='Ok' or not data.get('routes'):raise RoadRouteError('No road route')
        r=data['routes'][0];geometry=[[float(lat),float(lon)] for lon,lat in r['geometry']['coordinates']]
        if not 2<=len(geometry)<=100000 or any(not -90<=a<=90 or not -180<=b<=180 for a,b in geometry):raise ValueError('Invalid route geometry')
        if not math.isfinite(r['duration']) or r['duration']<0 or not math.isfinite(r['distance']) or r['distance']<0:raise ValueError('Invalid route estimate')
        record={'status':'ready','seconds':max(1,r['duration']),'distance_m':r['distance'],'geometry':geometry,'cumulative':cumulative(geometry),'source':'OSRM · OpenStreetMap'}
        if snap:record.update(recovered=True,snap=snap,source='OSRM · OpenStreetMap · Straßen-Fallback')
        self.save(k,record)
        # An unreachable matrix entry may have started this recovery. Replace its
        # provisional ETA when the actual drivable route has been found.
        self.save('eta|'+self.cachekey(a,b),{name:value for name,value in record.items() if name not in ('geometry','cumulative')})
    def estimates(self,origins,target):
        if not self.enabled:return {v['id']:{'status':'disabled'} for v in origins}
        unique={self.cachekey(v,target):v.copy() for v in origins}
        missing=[];result={};now=time.time()
        with self.lock:
            for k,v in unique.items():
                cache='eta|'+k;record=self.items.get(cache)
                if record and record['status']=='pending' and now-record.get('started_at',now)>12:
                    record={'status':'error','retry_at':now+60,'error':'Routenberechnung dauert zu lange'};self.items[cache]=record
                if not record or record['status']=='pending' or record['status']=='error' and record.get('retry_at',0)<=now:
                    if not record or record['status']=='error':self.items[cache]={'status':'pending','started_at':now}
                    missing.append(v)
            for v in origins:result[v['id']]=copy.deepcopy(self.items.get('eta|'+self.cachekey(v,target),{'status':'pending'}))
        for start in range(0,len(missing),60):
            batch=missing[start:start+60];k='matrix|'+self.url+'|'+json.dumps([point(v) for v in batch]+[point(target)])
            with self.lock:failed=self.items.get(k,{}).get('retry_at',0)>time.time()
            if not failed:self.enqueue(k,10,lambda batch=batch:self.fetch_matrix(batch,target.copy()))
        return result
    def fetch_matrix(self,origins,target):
        try:self._fetch_matrix(origins,target)
        except Exception:
            for v in origins:self.save('eta|'+self.cachekey(v,target),{'status':'error','retry_at':time.time()+60,'error':'Routenserver nicht erreichbar'})
            raise
    def _fetch_matrix(self,origins,target):
        points=origins+[target];coords=';'.join(','.join(map(str,point(p))) for p in points)
        path='/table/v1/driving/'+coords+'?sources='+ ';'.join(str(i) for i in range(len(origins)))+'&destinations='+str(len(origins))+'&annotations=duration,distance'
        data=self.request(path)
        if data.get('code')!='Ok':raise ValueError('No road matrix')
        for i,v in enumerate(origins):
            duration=data['durations'][i][0];distance=data.get('distances',[[None]]*len(origins))[i][0]
            if duration is not None and (not math.isfinite(duration) or duration<0):raise ValueError('Invalid matrix duration')
            record={'status':'ready','seconds':duration,'distance_m':distance,'source':'OSRM · OpenStreetMap'} if duration is not None else {'status':'error','retry_at':time.time()+60,'error':'Keine Straßenroute; Straßenanschluss wird geprüft'}
            if duration is None:
                # A failed target can affect the entire fleet. Do not enqueue
                # hundreds of recovery routes from one ETA matrix: only an
                # actual journey starts recovery, at driving priority.
                with self.lock:road=self.items.get('route|'+self.cachekey(v,target),{})
                if road.get('status')=='ready':record={name:value for name,value in road.items() if name not in ('geometry','cumulative')}
            self.save('eta|'+self.cachekey(v,target),record)
    def cached_eta(self,v,j):
        with self.lock:return self.items.get('eta|'+self.cachekey(v,j))

def router_for(path):
    path=str(Path(path).resolve().parent/'routing.sqlite3')
    with _registry_lock:
        if path not in _registry:_registry[path]=Router(path)
        return _registry[path]
