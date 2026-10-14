"""Fictional third-party dispatch, finite units, access tasks and road travel.
Origins and identifiers are exercise data, not real police/fire inventories.
"""
import hashlib
import uuid

KINDS={'police':'Polizei','fire':'Feuerwehr'}
TASKS={'police':{'assist':('Absicherung / Erhebungen',240),'safety':('Gefahrenbereich sichern und freigeben',180)},'fire':{'assist':('Tragehilfe / Unterstützung',180),'extrication':('Technische Menschenrettung',420),'fire':('Brandbekämpfung / Zugang freigeben',600)}}
OPEN=('waiting','alarmed','enroute','working','onscene')

class Agencies:
    def upgrade_agencies(self):
        self.state.setdefault('agency_units',[])
        # Shared exercise staging points use existing, positioned local stations.
        # These are deliberately not presented as actual police/fire stations.
        if self.state.get('agency_version')==1:return
        for s in self.state['stations']:
            if s.get('dispo')!='05' or s.get('responder_area'):continue
            if not any(v['station']==s['id'] and v['type'] in ('RTW','RTW-C','KTW') for v in self.state['vehicles']):continue
            area=s['name'].removeprefix('RK ').removeprefix('ASB ').split(' · ')[0]
            for kind,typ in [('police','POL'),('fire','RLF')]:
                id=f'agency-{kind}-{s["id"]}'
                if any(v['id']==id for v in self.state['agency_units']):continue
                self.state['agency_units'].append(dict(id=id,kind=kind,type=typ,callsign=f'{KINDS[kind]} {area} · SIM',station=s['id'],origin='Simulierter Bereitschaftspunkt '+area,lat=s['lat'],lon=s['lon'],job=None,status='ready',leg=None,phase_due=None,signal=False,request=None,graphic='police.svg' if kind=='police' else 'fire.svg'))
        self.state['agency_version']=1

    def agency_request(self,data):
        j=self.get('jobs',data['job']);kind=data.get('kind');task=data.get('task','assist')
        if kind not in KINDS or task not in TASKS[kind]:raise ValueError('Organisation und Aufgabe prüfen.')
        if not j['accepted'] or j['status']=='done':raise ValueError('Einen angenommenen, offenen Einsatz wählen.')
        if not j.get('code_confirmed') and j.get('dispatched_at') is None:raise ValueError('Zuerst das Alarmierungsstichwort speichern.')
        if any(r['kind']==kind and r['status'] in OPEN for r in j.get('agency_requests',[])):raise ValueError('Für diese Organisation läuft bereits eine Unterstützung. Bestehenden Auftrag zuerst beenden.')
        now=self.state['clock'];label,work=TASKS[kind][task]
        r=dict(id=uuid.uuid4().hex[:12],kind=kind,task=task,label=label,status='waiting',created=now,unit=None,work_seconds=work,signal=bool(data.get('signal',True)),reason=str(data.get('reason') or label).strip()[:300])
        if task!='assist':j.setdefault('agency_requirements',{})[task]=dict(label=label,cleared=False)
        j.setdefault('agency_requests',[]).append(r);j[kind]=True;j.setdefault('agency_started',{})[kind]=True
        self.log(f'LEO → {KINDS[kind]}-Leitstelle: Unterstützung zu Einsatz {j["incident_number"]}, {j["address"]}. {r["reason"]}.','Telefon')
        self.allocate_agency(j,r)
        return r

    def allocate_agency(self,j,r):
        from engine import distance
        units=[v for v in self.state['agency_units'] if v['kind']==r['kind'] and not v.get('job') and v['status'] in ('ready','radio')]
        if not units:
            if not r.get('waiting_reported'):
                self.log(f'{KINDS[r["kind"]]}-Leitstelle → LEO: Derzeit keine freie Einheit; Anforderung wartet.','Telefon');r['waiting_reported']=True
            return
        v=min(units,key=lambda u:distance(u,j));now=self.state['clock']
        seed=int(hashlib.sha256((j['id']+v['id']+r['id']).encode()).hexdigest()[:8],16)
        prep=30+seed%31 if r['kind']=='police' else 90+seed%91
        previous=v['status']
        v.update(alarm_from=previous,job=j['id'],request=r['id'],status='assigned',signal=r['signal'],leg=None,phase_due=now+prep)
        r.update(status='alarmed',unit=v['id'],alarmed=now,depart_due=now+prep)
        self.log(f'{KINDS[r["kind"]]}-Leitstelle → LEO: {v["callsign"]} übernimmt {r["label"]}. Ausrücken in etwa {prep} Sekunden.','Telefon')

    def agency_task(self,data):
        j=self.get('jobs',data['job']);r=next((r for r in j.get('agency_requests',[]) if r['id']==data.get('request')),None)
        if not r or r['status'] not in OPEN or r.get('task_completed') is not None:raise ValueError('Keine laufende, unbearbeitete Aufgabe.')
        task=data.get('task')
        if task not in TASKS[r['kind']]:raise ValueError('Aufgabe prüfen.')
        label,work=TASKS[r['kind']][task]
        if task==r['task']:return
        r.update(task=task,label=label,work_seconds=work)
        if r['status']=='working':r['work_due']=self.state['clock']+work
        if task!='assist':j.setdefault('agency_requirements',{})[task]=dict(label=label,cleared=False)
        self.log(f'LEO → {KINDS[r["kind"]]}-Leitstelle: Einsatz {j["incident_number"]}, Aufgabe geändert: {label}.','Telefon')

    def agency_release(self,data):
        j=self.get('jobs',data['job']);r=next((r for r in j.get('agency_requests',[]) if r['id']==data.get('request')),None)
        if not r or r['status'] not in OPEN:raise ValueError('Keine laufende Unterstützung.')
        self.release_agency(j,r,'cancelled','Durch Disposition abbestellt')

    def release_agency(self,j,r,status='released',reason='Rettungsdiensteinsatz beendet'):
        now=self.state['clock'];r.update(status=status,ended=now,end_reason=reason)
        v=next((v for v in self.state['agency_units'] if v['id']==r.get('unit')),None)
        if v and v.get('request')==r['id']:
            v.update(job=None,request=None,signal=False)
            from engine import distance
            if distance(v,self.station(v['station']))<.02:v.update(status='ready',leg=None,phase_due=None)
            else:self.drive(v,self.station(v['station']),'radio')
        self.log(f'LEO → {KINDS[r["kind"]]}-Leitstelle: Einsatz {j["incident_number"]}, {reason}.','Telefon')
        self.resume_after_agency(j)

    def ensure_agency_requests(self,j):
        if j['status']=='done' or j.get('dispatched_at') is None or not j.get('accepted'):return
        for kind in KINDS:
            if j.get(kind) and not j.get('agency_started',{}).get(kind):
                self.agency_request({'job':j['id'],'kind':kind,'task':'assist'})

    def agency_gate(self,j,stage='assessment'):
        for task,requirement in j.get('agency_requirements',{}).items():
            if not requirement['cleared'] and (task in ('safety','fire') or stage=='transport' and task=='extrication'):return requirement['label']
        for r in j.get('agency_requests',[]):
            if r['status'] not in OPEN or r.get('task_completed') is not None:continue
            if r['task'] in ('safety','fire') or stage=='transport' and r['task']=='extrication':return r['label']
        return None

    def resume_after_agency(self,j):
        if self.agency_gate(j):return
        for v in self.state['vehicles']:
            if v.get('job')!=j['id'] or v['status']!='scene':continue
            if v.pop('agency_assessment_wait',False):v['assessment_due']=self.state['clock']+60
            if not self.agency_gate(j,'transport') and v.pop('agency_transport_wait',False):v['phase_due']=max(self.state['clock']+60,v.get('assessment_due') or 0)

    def update_agencies(self,now):
        from routing import position
        for j in self.state['jobs']:
            self.ensure_agency_requests(j)
            for r in j.get('agency_requests',[]):
                if r['status'] not in OPEN:continue
                if j['status']=='done':self.release_agency(j,r);continue
                if r['status']=='waiting':self.allocate_agency(j,r)
                v=next((v for v in self.state['agency_units'] if v['id']==r.get('unit')),None)
                if not v:continue
                if r['status']=='alarmed' and now>=v['phase_due']:
                    due=v['phase_due'];self.state['clock']=due
                    try:self.drive(v,j,'enroute')
                    finally:self.state['clock']=now
                    r.update(status='enroute',departed=due)
                    self.log(f'{KINDS[r["kind"]]}-Leitstelle → LEO: {v["callsign"]} auf Anfahrt.','Telefon')
                if r['status']=='working' and now>=r['work_due']:
                    r.update(status='onscene',task_completed=now,release_due=now+600)
                    self.log(f'{KINDS[r["kind"]]}-Leitstelle → LEO: Einsatz {j["incident_number"]}, {r["label"]} abgeschlossen. '+('Einsatzstelle für Rettungsdienst freigegeben.' if r['task'] in ('safety','fire') else 'Patient zugänglich und für Transport befreit.' if r['task']=='extrication' else 'Unterstützung durchgeführt.'),'Telefon')
                    if r['task'] in j.get('agency_requirements',{}):j['agency_requirements'][r['task']]['cleared']=True
                    self.resume_after_agency(j)
                if r['status']=='onscene' and now>=r['release_due']:self.release_agency(j,r,reason='Aufgabe erledigt, Einheit rückt ein')
        for v in self.state['agency_units']:
            leg=v.get('leg')
            if leg and leg.get('waiting'):self.resolve_route(v);leg=v.get('leg')
            if leg and not leg.get('waiting'):
                fraction=max(0,min(1,(now-leg['start'])/max(1,leg['end']-leg['start'])))
                if leg.get('geometry'):v.update(position(leg,fraction))
                else:v.update(lat=leg['lat']+(leg['target_lat']-leg['lat'])*fraction,lon=leg['lon']+(leg['target_lon']-leg['lon'])*fraction)
                if fraction<1:continue
                v.update(lat=leg['target_lat'],lon=leg['target_lon'],leg=None,phase_due=None)
                if v['status']=='radio':v['status']='ready';continue
                j=next((j for j in self.state['jobs'] if j['id']==v.get('job')),None)
                r=next((r for r in (j or {}).get('agency_requests',[]) if r['id']==v.get('request')),None)
                if not r or r['status'] not in OPEN:continue
                v['status']='scene';r.update(status='working',arrived=now,work_due=now+r['work_seconds'])
                self.log(f'{KINDS[r["kind"]]}-Leitstelle → LEO: {v["callsign"]} am Einsatzort, {r["label"]} beginnt.','Telefon')

    def update_additional(self,data):
        j=self.get('jobs',data['job']);text=data.get('additional')
        if not isinstance(text,str) or len(text)>500:raise ValueError('Zusatztext maximal 500 Zeichen.')
        if 'previous' in data and data['previous']!=j.get('additional',''):raise ValueError('Zusatztext wurde inzwischen geändert. Aktuellen Text prüfen und erneut bearbeiten.')
        text=text.strip()
        if text==j.get('additional',''):return
        j['additional']=text;j['additional_revision']=j.get('additional_revision',0)+1
        j.setdefault('additional_history',[]).append(dict(time=self.state['clock'],text=text,actor=data.get('_actor',{}).get('name','Disponent')))
        j['additional_history']=j['additional_history'][-50:]
        self.log(f'Einsatz {j["incident_number"]}: Zusatztext aktualisiert.','Aufträge')
        if data.get('send',True):
            for v in self.state['vehicles']:
                if v.get('job')!=j['id']:continue
                message=f'EINSATZUPDATE {j["incident_number"]} | Zusatztext: {text or "—"}'
                for channel in ('SDS','ESApp'):
                    self.state['messages'].append(dict(job=j['id'],vehicle=v['id'],channel=channel,time=self.state['clock'],text=message));self.log(f'{v["callsign"]} ← {message}',channel)
            self.state['messages']=self.state['messages'][-250:]
