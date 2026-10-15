"""Fictional telephone advice and a room-local pool; never an on-scene doctor."""
POOL_SIZE=10

class Telemedicine:
    def tna_free_slots(self):
        used={j['telenotarzt']['slot'] for j in self.state['jobs'] if j.get('telenotarzt') and j['status']!='done'}
        return [n for n in range(1,POOL_SIZE+1) if n not in used]

    def tna_patient(self,j):
        t=j.get('telenotarzt') or {}
        if j.get('patients'):
            return next((p for p in j['patients'] if p['number']==t.get('patient_number') and self.patient_phase(j,p)=='scene'),None)
        return j.get('patient_condition')

    def tna_active(self,j):
        t=j.get('telenotarzt');unit=next((u for u in self.state['vehicles'] if t and u['id']==t['vehicle']),None)
        return bool(t and t.get('connected_at') is not None and unit and unit.get('job')==j['id'] and unit['status']=='scene' and self.tna_patient(j) and not self.agency_gate(j))

    def allocate_telenotarzt(self,j,v):
        if j.get('telenotarzt'):raise ValueError('Für diesen Einsatz ist bereits ein Telenotarzt zugebucht.')
        if j['status']=='done' or v.get('job')!=j['id'] or v['status']!='scene' or v['type'] in ('NEF','NAH','FR','BEL'):raise ValueError('Eine versorgende Rettungsmannschaft am Berufungsort benötigt.')
        if v.get('assessment_due',0)>self.state['clock'] or j.get('no_patient') or self.triage_unit(j,v):raise ValueError('Zuerst die Lage vor Ort erheben.')
        if any(u.get('job')==j['id'] and u['type'] in ('NEF','NAH') and u['status']=='scene' and u.get('assessment_due',0)<=self.state['clock'] for u in self.state['vehicles']):raise ValueError('Ein Notarzt vor Ort hat die Versorgung bereits übernommen.')
        slots=self.tna_free_slots()
        if not slots:raise ValueError('Alle zehn Telenotärzte sind derzeit gebunden.')
        slot=slots[0];now=self.state['clock'];patient_number=None
        if j.get('patients'):
            patient=next((p for p in self.scene_patients(j) if p.get('carrier')==v['id']),None)
            if not patient:raise ValueError('Die Mannschaft muss einen Patienten zur telefonischen Beratung übernommen haben.')
            patient_number=patient['number']
        t={'id':f'tna-{slot:02d}','slot':slot,'name':'Telenotarzt','phone':f'SIM-000-000-{slot:02d}','virtual':True,'vehicle':v['id'],'patient_number':patient_number,'assigned_at':now,'call_due':now+30,'connected_at':None,'care_due':None}
        j['telenotarzt']=t
        text=f'Einsatz {j["incident_number"]} | Telenotarzt zugebucht | Telefonnummer: {t["phone"]} (fiktive Simulationsnummer) | Bitte telefonisch Kontakt aufnehmen.'
        for channel in ('SDS','ESApp'):
            self.state['messages'].append({'job':j['id'],'vehicle':v['id'],'channel':channel,'time':now,'text':text});self.log(f'{v["callsign"]} ← {text}',channel)
        self.state['messages']=self.state['messages'][-250:]
        return t

    def release_telenotarzt(self,j,reason='Telefonische Beratung beendet.'):
        t=j.pop('telenotarzt',None)
        if not t:return
        self.log(f'Telenotarzt · Einsatz {j["incident_number"]}: {reason}','Telefon')
        j.setdefault('telenotarzt_history',[]).append({'assigned_at':t['assigned_at'],'ended_at':self.state['clock'],'reason':reason})

    def sync_telenotarzt(self):
        for j in self.state['jobs']:
            t=j.get('telenotarzt')
            if not t:continue
            v=next((u for u in self.state['vehicles'] if u['id']==t['vehicle']),None)
            doctor=any(u.get('job')==j['id'] and u['type'] in ('NEF','NAH') and u['status']=='scene' and u.get('assessment_due',0)<=self.state['clock'] and not self.triage_unit(j,u) for u in self.state['vehicles'])
            if j['status']=='done' or not v or v.get('job')!=j['id'] or v['status']!='scene' or j.get('no_patient') or doctor:
                self.release_telenotarzt(j,'Notarzt vor Ort übernimmt.' if doctor else 'Mannschaft hat die Versorgung am Berufungsort beendet.')

    def maybe_telenotarzt_request(self,j,v):
        if j.get('telenotarzt') or j.get('tna_considered') or j['kind']!='emergency' or v['type'] not in ('RTW','RTW-C','KTW'):return
        if j.get('patients') or j.get('no_patient') or not j.get('scene_report'):return
        c=j.get('patient_condition') or {}
        if not 45<=c.get('percent',100)<=75:return
        if any(u.get('job')==j['id'] and u['type'] in ('NEF','NAH') for u in self.state['vehicles']):return
        if any(c['job']==j['id'] and c['state']!='closed' for c in self.state['radio_calls']):return
        import random
        j['tna_considered']=True
        if random.random()<.4:self.raise_radio(j,v,'Telenotarzt','Wir benötigen eine ärztliche Einschätzung und telefonische Anleitung zur weiteren Versorgung.',reason_initial=True)

    def update_telenotarzt(self,now):
        self.sync_telenotarzt()
        for j in self.state['jobs']:
            t=j.get('telenotarzt')
            if not t:continue
            v=self.get('vehicles',t['vehicle'])
            if t['connected_at'] is None and now>=t['call_due']:
                t.update(connected_at=now,care_due=now+60)
                self.log(f'{self.radio_name(v)} ruft den Telenotarzt unter {t["phone"]} an. Ärztliche Einschätzung und telefonische Anleitung beginnen.','Telefon')
            if not self.tna_active(j):continue
            patient=self.tna_patient(j)
            # No revival, physical care or transport accompaniment is invented.
            if now>=(t.get('care_due') or now+60):
                if __import__('os').environ.get('PATIENT_EVOLUTION','1')!='0' and 0<patient['percent']<85:
                    patient['percent']=min(85,patient['percent']+3)
                    if j.get('patients'):
                        from multiple_patients import triage
                        patient['triage']=triage(patient['percent'])
                    else:patient['notarzt_required']=patient['percent']<45
                t['care_due']=now+60
            if patient['percent']<45 and not t.get('escalated'):
                t['escalated']=True
                self.log(f'Telenotarzt → {self.radio_name(v)}: Für diesen Patienten ist ein Notarzt vor Ort erforderlich. Bitte über LEO nachfordern.','Telefon')
                if not self.maybe_request_transport_heli(j,v):
                    doctors=any(u.get('job')==j['id'] and u['type'] in ('NEF','NAH') for u in self.state['vehicles'])
                    if not doctors:self.raise_radio(j,v,'NEF','Nach telefonischer Rücksprache mit dem Telenotarzt benötigen wir einen Notarzt vor Ort.',reason_initial=True)
