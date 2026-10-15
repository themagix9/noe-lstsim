"""Gameplay helicopter queries for critical patients with long ground transfers."""
import math

class AirTransport:
    def maybe_request_transport_heli(self,j,v,target=None):
        if j.get('no_patient') or j['kind']!='emergency' or v.get('job')!=j['id'] or v['status']!='scene' or v['type'] not in ('KTW','RTW','RTW-C','NEF'):return False
        if v.get('assessment_due',0)>self.state['clock'] or self.agency_gate(j):return False
        if self.is_manv(j) and (not self.triage_finished(j) or self.ensure_triage_leader(j)!=v):return False
        p=(j['patients'][v['patient_index']] if v.get('patient_index') is not None else min(self.scene_patients(j),key=lambda p:p['percent'],default={})) if j.get('patients') else j.get('patient_condition') or {}
        if not 0<p.get('percent',100)<45:return False
        if 'NAH' in j.get('request_denials',{}):return False
        if any(u.get('job')==j['id'] and u['type']=='NAH' for u in self.state['vehicles']):return False
        existing=next((c for c in self.state['radio_calls'] if c['job']==j['id'] and c['kind']=='NAH' and c['state']!='closed'),None)
        if existing:return bool(j.get('air_transport_request',{}).get('call')==existing['id'])
        from hospital_specialties import choose_target
        try:
            h=target or (self.get('hospitals',j['crew_target']) if j.get('crew_target') else choose_target(self,j,v))
            if not h.get('helipad'):h=choose_target(self,j,{**v,'type':'NAH'})
        except ValueError:return False
        origin={'id':'heli-ground-'+j['id'],'lat':j['lat'],'lon':j['lon']}
        estimate=self.router.cached_eta(origin,h)
        if not estimate or estimate.get('status')!='ready':
            if self.router.enabled:self.router.estimates([origin],h)
            from engine import distance
            seconds=distance(origin,h)*1.25/45*3600;approximate=True
        else:seconds=estimate['seconds'];approximate=False
        seconds*=self.response_factor(v,j)
        if seconds<35*60:return False
        minutes=math.ceil(seconds/60)
        call=self.raise_radio(j,v,'NAH',f'Patient kritisch. Bodentransport zum {h["name"]} '+('geschätzt ' if approximate else 'voraussichtlich ')+f'{minutes} Minuten. Ist ein Notarzthubschrauber für den Patiententransport verfügbar?',reason_initial=True)
        if not call:return False
        call['transport_query']=True
        j['air_transport_request']={'call':call['id'],'vehicle':v['id'],'patient_number':p.get('number'),'target':h['id'],'ground_seconds':seconds,'approximate':approximate,'requested_at':self.state['clock']}
        v['phase_due']=None
        return True

    def confirm_transport_heli(self,j,call,unit):
        request=j.get('air_transport_request')
        if not request or request['call']!=call['id']:return
        request['unit']=unit['id']
        if not j.get('patients'):j.update(carrier=unit['id'],crew_target=request['target'])

    def update_transport_heli(self,j):
        request=j.get('air_transport_request')
        if not request:return
        unit=next((u for u in self.state['vehicles'] if u['id']==request.get('unit') and u.get('job')==j['id']),None)
        if unit and unit['status']=='scene' and request.get('patient_number') and not request.get('transferred'):
            p=next((p for p in self.scene_patients(j) if p['number']==request['patient_number']),None)
            if p:
                previous=next((v for v in self.state['vehicles'] if v['id']==p.get('carrier')),None)
                if previous:previous.pop('patient_index',None)
                # An aircraft might already have a different reserved patient.
                for other in j['patients']:
                    if other is not p and other.get('carrier')==unit['id']:other['carrier']=None
                p['carrier']=unit['id'];unit['patient_index']=p['number']-1;request['transferred']=True
                self.assign_patients(j)

    def awaiting_transport_heli(self,j,v):
        request=j.get('air_transport_request')
        if not request:return False
        patient=next((p for p in self.scene_patients(j) if p['number']==request.get('patient_number')),None)
        if request['vehicle']!=v['id'] and (not patient or patient.get('carrier')!=v['id']):return False
        call=next((c for c in self.state['radio_calls'] if c['id']==request['call']),None)
        if call and call['state']!='closed':return True
        unit=next((u for u in self.state['vehicles'] if u['id']==request.get('unit') and u.get('job')==j['id']),None)
        if unit and unit['status'] in ('assigned','standby','acknowledged','enroute'):return True
        return False
