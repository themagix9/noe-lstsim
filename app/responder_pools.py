"""Fictional municipal responder pools; private homes are never real addresses."""
import random

def upgrade(engine):
    from fleet import defaults
    from engine import uid
    stations=[s for s in engine.state['stations'] if s.get('dispo')=='05' and (s['id']=='fr-fischamend' or any(v['station']==s['id'] and v['type'] in ('RTW','RTW-C','KTW') for v in engine.state['vehicles']))]
    for s in stations:
        name='Fischamend' if s['id']=='fr-fischamend' else s['name'].removeprefix('RK ').removeprefix('ASB ').removeprefix('FR ').split(' · ')[0]
        target=15 if s['id']=='fr-fischamend' else 10 if s['id']=='schwechat' else 5
        members=[v for v in engine.state['vehicles'] if v['type']=='FR' and v['station']==s['id'] and not v['callsign'].endswith('-POOL')]
        while len(members)<target:
            call=f'FR-{s["id"].upper()}-{len(members)+1:02}'
            v={'id':uid(),**defaults(call,'FR',s['id']),'status':'fr_ready','job':None,'phase_due':None,'reservation':None,'leg':None,'manual_out':False,'ack_deadline':None,'alarm_from':'fr_ready'}
            engine.state['vehicles'].append(v);members.append(v)
        for v in members:
            v.update(fr_pool=s['id'],fr_name='FR '+name)
            if not v.get('pool_home_version') and not v.get('job'):
                rng=random.Random('noe-fr-'+v['id']);lat=s['lat']+rng.uniform(-.008,.008);lon=s['lon']+rng.uniform(-.012,.012)
                v.update(home_lat=lat,home_lon=lon,lat=lat,lon=lon,home_address='Fiktiver Bereitschaftsort · '+name,pool_home_version=1,status='fr_ready',staffed=True,duty_managed=True,start='00:00',end='00:00',source='Fiktiver Gemeindepool: 10 Schwechat / 15 Fischamend / sonst 5, keine realen Personal- oder Wohnortdaten')

def nearest_responder(self,v,j):
    from engine import distance
    return min((u for u in self.state['vehicles'] if u['type']=='FR' and u.get('fr_pool',u['station'])==v.get('fr_pool',v['station']) and self.sendable(u,j)),key=lambda u:distance(u,j),default=v)

def number_responder(self,v):
    if v['type']!='FR' or not v.get('job') or v.get('fr_number'):return
    used={u.get('fr_number') for u in self.state['vehicles'] if u.get('job')==v['job'] and u.get('fr_pool',u['station'])==v.get('fr_pool',v['station']) and u['id']!=v['id']}
    v['fr_number']=next(n for n in range(1,1000) if n not in used)
