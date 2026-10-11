"""Persistent simulated night rosters and fictional responder homes."""
import datetime as dt
import hashlib
import random

class Staffing:
    def staff_plan(self):
        clock=self.state['clock'];day=dt.date.fromisoformat(self.state['start_date'])+dt.timedelta(days=int(clock//86400)-(1 if clock%86400<21600 else 0))
        key=day.isoformat();plans=self.state.setdefault('night_rosters',{})
        if key not in plans:
            rng=random.Random(hashlib.sha256((self.room_id+key).encode()).digest());ids=[]
            for station in self.state['stations']:
                group=[v for v in self.state['vehicles'] if v['station']==station['id'] and v.get('duty_managed') and v['staffed'] and v['type'] not in ('FR','NAH','BEL')]
                always=[v for v in group if v['type'] in ('NEF','RTW-C')];optional=[v for v in group if v not in always];rng.shuffle(optional)
                selected=always[:]
                if station['id']=='schwechat':selected+=optional[:max(0,3-len(always))]
                elif station['id'] not in ('himberg','leopoldsdorf'):selected += optional[:1] if optional else []
                elif optional and rng.random()<.4:selected+=optional[:1]
                for v in optional:
                    if v not in selected and v['type'] in ('KTW','RTW') and rng.random()<.15:selected.append(v)
                ids.extend(v['id'] for v in selected)
            plans.clear();plans[key]=ids
        return plans[key]

    def managed_shift(self,v):
        if not v['staffed']:return False
        if v['type']=='FR':return True
        if v['type'] in ('NEF','RTW-C'):return True
        if 21600<=self.state['clock']%86400<64800:return True
        return v['id'] in self.staff_plan()

    def upgrade_staffing(self):
        if self.state.get('staffing_version')==1:return
        from fleet import defaults
        from engine import uid
        pending=False
        pool=next((v for v in self.state['vehicles'] if v['callsign']=='FR-FISCHAMEND-POOL'),None)
        if pool and not pool['job']:self.state['vehicles'].remove(pool)
        for n in range(1,16):
            call=f'FR-FIS-{n:02}'
            if not any(v['callsign']==call for v in self.state['vehicles']):
                home=self.station('fr-fischamend');v={'id':uid(),**defaults(call,'FR','fr-fischamend'),'status':'fr_ready','lat':home['lat'],'lon':home['lon'],'job':None,'phase_due':None,'reservation':None,'leg':None,'manual_out':False,'ack_deadline':None,'alarm_from':'fr_ready'};self.state['vehicles'].append(v)
        self.station('fr-fischamend')['responder_area']=True
        for v in self.state['vehicles']:
            v.setdefault('duty_managed',v.get('source','').startswith(('Nutzerbestätigung','Kennung/Typ: Nutzerfoto','C3/C9:')))
            if v.get('duty_managed') and v['type'] not in ('NAH','FR'):
                v['start']='06:00';v['end']='18:00';v['source']='Nutzerbestätigung 11.10.2026; simulierte Tag-/Nachtbesetzung, keine echten Dienstpläne'
            if v['type']=='FR':
                if 'home_lat' in v:continue
                if v.get('job') or v.get('reservation'):pending=True;continue
                rng=random.Random(hashlib.sha256((self.room_id+v['id']).encode()).digest())
                if v['station']=='fr-fischamend':lat,lon=48.116+rng.uniform(-.006,.006),16.612+rng.uniform(-.009,.009)
                else:
                    lat,lon=rng.choice([(48.141,16.478),(48.082,16.437),(48.10,16.419),(48.017,16.582)])
                    lat+=rng.uniform(-.005,.005);lon+=rng.uniform(-.005,.005)
                v.update(home_lat=lat,home_lon=lon,home_address=f'Fiktiver Wohnort {v["callsign"]} · keine echte Privatadresse',lat=lat,lon=lon,status='fr_ready',phase_due=None,ack_deadline=None,staffed=True,duty_managed=True,source='Fiktive FR-Wohnorte; 10 Schwechat / 15 Fischamend laut Nutzervorgabe')
        if not pending:self.state['staffing_version']=1

    def home(self,v):
        return {'lat':v['home_lat'],'lon':v['home_lon'],'name':v['home_address']} if v['type']=='FR' and 'home_lat' in v else self.station(v['station'])

    def idle_status(self,v):
        return ('fr_ready' if v['type']=='FR' else 'ready') if self.in_shift(v) else 'out'
