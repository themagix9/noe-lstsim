"""Individual fictional patients, triage, care and transport bookkeeping."""
import os
import random

TRANSPORTERS=('KTW','KTW-B','BKTW','RTW','RTW-C','NAH')

def triage(score):
    return 'I' if score<45 else 'II' if score<70 else 'III'

class MultiplePatients:
    def discover_patients(self,j):
        truth=j.get('_scenario',{})
        count=truth.get('patient_count',1)
        if count<2 or j.get('patients'):return
        scores=truth.get('patient_scores',[70,80])
        j['patient_count']=count;j['manv']=bool(truth.get('manv',count>=5))
        j['patients']=[{'number':i+1,'name':'Übungspatient '+str(i+1),'percent':scores[i%len(scores)],'triage':triage(scores[i%len(scores)]),'carrier':None,'doctor':None,'delivered':False,'phase':'scene','requires_doctor':scores[i%len(scores)]<45} for i in range(count)]
        j['patients_next_change']=self.state['clock']+60
        self.assign_patients(j)

    def patient_phase(self,j,p):
        if p['delivered']:return 'delivered'
        v=next((v for v in self.state['vehicles'] if v['id']==p.get('carrier') and v.get('job')==j['id']),None)
        return v['status'] if v and v['status'] in ('transport','hospital') else 'scene'

    def scene_patients(self,j):
        return [p for p in j.get('patients',[]) if self.patient_phase(j,p)=='scene']

    def doctor_needed_at_scene(self,j):
        if j.get('patients'):return bool(self.scene_patients(j))
        return any(v.get('job')==j['id'] and v['type'] in TRANSPORTERS and v['status'] in ('assigned','acknowledged','enroute','scene') for v in self.state['vehicles'])

    def assign_patients(self,j):
        if not j.get('patients'):return
        for id in j['vehicles']:
            v=self.get('vehicles',id)
            if v['job']!=j['id'] or v['type'] not in TRANSPORTERS:continue
            if any(p['carrier']==id for p in j['patients']):continue
            patient=min((p for p in j['patients'] if not p['delivered'] and not p['carrier']),key=lambda p:(p['percent'],p['number']),default=None)
            if patient:patient['carrier']=id;v['patient_index']=patient['number']-1

    def assign_doctors(self,j):
        patients=[p for p in j.get('patients',[]) if self.patient_phase(j,p)=='scene']
        doctors=[v for v in self.state['vehicles'] if v.get('job')==j['id'] and v['type'] in ('NEF','NAH') and v['status']=='scene' and v.get('assessment_due',0)<=self.state['clock']]
        for p in j.get('patients',[]):
            if self.patient_phase(j,p)=='scene':p['doctor']=None
        for v in doctors:
            v.pop('treating_patient',None)
            p=min((p for p in patients if not p['doctor']),key=lambda p:(p['percent'],p['number']),default=None)
            if p:p['doctor']=v['id'];v['treating_patient']=p['number']

    def missing_carriers(self,j):
        if not j.get('patients'):return 0
        self.assign_patients(j)
        return sum(not p['delivered'] and not p['carrier'] for p in j['patients'])

    def request_manv_resources(self,j,v):
        if not j.get('patients') or v['status']!='scene' or v.get('assessment_due',0)>self.state['clock']:return
        if os.environ.get('REINFORCEMENTS_AUTO','1')=='0':return
        scene=[p for p in j['patients'] if self.patient_phase(j,p)=='scene']
        doctors=[u for u in self.state['vehicles'] if u.get('job')==j['id'] and u['type'] in ('NEF','NAH') and u['status'] not in ('transport','hospital','radio','out')]
        critical=sum(p['percent']<45 for p in scene)
        if critical>len(doctors):self.raise_radio(j,v,'NEF',f'{critical} kritische Patienten am Berufungsort, {len(doctors)} Notarztmittel gebunden oder auf Anfahrt. Bitte ein weiteres Notarztmittel.',reason_initial=True)
        missing=self.missing_carriers(j)
        if missing:self.raise_radio(j,v,'RTW',f'{len(scene)} Patienten noch am Berufungsort. Es fehlen {missing} transportierende Rettungsmittel.',reason_initial=True)

    def update_multiple_patients(self,j,now):
        self.assign_patients(j);self.assign_doctors(j)
        scene=[p for p in j['patients'] if self.patient_phase(j,p)=='scene']
        for p in j['patients']:p['phase']=self.patient_phase(j,p);p.setdefault('triage',triage(p['percent']))
        if os.environ.get('PATIENT_EVOLUTION','1')!='0' and now>=j.get('patients_next_change',now+60):
            transport_care=[p for p in j['patients'] if self.patient_phase(j,p)=='transport' and any(v['id']==p.get('doctor') and v.get('job')==j['id'] and v['status']=='transport' for v in self.state['vehicles'])]
            for p in scene+transport_care:
                unit=next((u for u in self.state['vehicles'] if u['id']==p.get('carrier') and u.get('job')==j['id'] and u['status']=='scene' and u.get('assessment_due',0)<=now),None)
                delta=random.randint(4,8) if p.get('doctor') else random.randint(-2,1) if unit else random.randint(-4,0)
                p['percent']=max(0,min(100,p['percent']+delta));p['triage']=triage(p['percent'])
                if p['percent']>=60:p['requires_doctor']=False
                elif p['percent']<45:p['requires_doctor']=True
            j['patients_next_change']=now+60
            self.assign_doctors(j)
        c=j.get('patient_condition')
        if scene and c:
            c.update(percent=min(p['percent'] for p in scene),notarzt_required=any(p['percent']<45 for p in scene))
        reporter=next((v for v in self.state['vehicles'] if v.get('job')==j['id'] and v['status']=='scene' and v.get('assessment_due',0)<=now and v['type'] in ('NEF','NAH')),None)
        if reporter:self.request_manv_resources(j,reporter)

    def delivered_patient(self,j,v):
        index=v.get('patient_index')
        if index is not None and j.get('patients'):
            j['patients'][index].update(delivered=True,phase='delivered',doctor=None)
            j['patient_delivered']=all(p['delivered'] for p in j['patients'])
        elif v['type'] in TRANSPORTERS:j['patient_delivered']=True

    def release_patient_carrier(self,j,v):
        if j.get('patients') and v.get('patient_index') is not None:
            p=j['patients'][v['patient_index']]
            if not p['delivered']:p['carrier']=None
        for p in j.get('patients',[]):
            if p.get('doctor')==v['id']:p['doctor']=None
        v.pop('patient_index',None);v.pop('treating_patient',None);v.pop('escort_of',None)
