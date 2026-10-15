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
            if v['job']!=j['id'] or v['type'] not in TRANSPORTERS or self.triage_unit(j,v):continue
            if any(p['carrier']==id for p in j['patients']):continue
            patient=min((p for p in j['patients'] if not p['delivered'] and not p['carrier']),key=lambda p:(p['percent'],p['number']),default=None)
            if patient:patient['carrier']=id;v['patient_index']=patient['number']-1

    def assign_doctors(self,j):
        patients=self.scene_patients(j);now=self.state['clock']
        doctors=[v for v in self.state['vehicles'] if v.get('job')==j['id'] and v['type'] in ('NEF','NAH') and v['status']=='scene' and v.get('assessment_due',0)<=now and not self.triage_unit(j,v)]
        for p in patients:p['doctor']=None
        for v in doctors:
            options=[p for p in patients if not p['doctor']]
            current=next((p for p in options if p['number']==v.get('treating_patient')),None)
            worst=min(options,key=lambda p:(p['percent'],p['number']),default=None)
            if not worst:v.pop('treating_patient',None);continue
            if current and now<v.get('care_switch_due',0) and worst['percent']+10>=current['percent']:chosen=current
            else:
                # Rotate between similarly urgent patients; a much worse patient
                # always has priority over the rotation.
                alternatives=[p for p in options if p is not current and p['percent']<=worst['percent']+15]
                chosen=min(alternatives,key=lambda p:(p['percent'],p['number']),default=worst)
                v['care_switch_due']=now+30
            chosen['doctor']=v['id'];v['treating_patient']=chosen['number']

    def doctor_demand(self,j):
        scene=self.scene_patients(j);critical=sum(p['percent']<45 for p in scene)
        # Shared care in this game: never one doctor resource per patient.
        return min((len(scene)+5)//6,(critical+2)//3) if critical else 0

    def missing_carriers(self,j):
        if not j.get('patients'):return 0
        self.assign_patients(j)
        return sum(not p['delivered'] and not p['carrier'] for p in j['patients'])

    def request_manv_resources(self,j,v):
        if self.is_manv(j):
            if os.environ.get('REINFORCEMENTS_AUTO','1')!='0':self.manv_request(j,v)
            return
        if not j.get('patients') or v['status']!='scene' or v.get('assessment_due',0)>self.state['clock']:return
        if os.environ.get('REINFORCEMENTS_AUTO','1')=='0':return
        scene=[p for p in j['patients'] if self.patient_phase(j,p)=='scene']
        doctors=[u for u in self.state['vehicles'] if u.get('job')==j['id'] and u['type'] in ('NEF','NAH') and u['status'] not in ('transport','hospital','radio','out')]
        critical=sum(p['percent']<45 for p in scene)
        if self.doctor_demand(j)>len(doctors):self.raise_radio(j,v,'NEF',f'{len(scene)} Patienten am Berufungsort, davon {critical} kritisch. Bitte ein weiteres Notarztmittel zur gemeinsamen Versorgung.',reason_initial=True)
        missing=self.missing_carriers(j)
        if missing:self.raise_radio(j,v,'RTW',f'{len(scene)} Patienten noch am Berufungsort. Es fehlen {missing} transportierende Rettungsmittel.',reason_initial=True)

    def update_multiple_patients(self,j,now):
        self.assign_patients(j);self.assign_doctors(j)
        scene=[p for p in j['patients'] if self.patient_phase(j,p)=='scene']
        for p in j['patients']:p['phase']=self.patient_phase(j,p);p.setdefault('triage',triage(p['percent']))
        if os.environ.get('PATIENT_EVOLUTION','1')!='0' and now>=j.get('patients_next_change',now+60):
            transport_care=[p for p in j['patients'] if self.patient_phase(j,p)=='transport' and any(v['id']==p.get('doctor') and v.get('job')==j['id'] and v['status']=='transport' for v in self.state['vehicles'])]
            present=[v for v in self.state['vehicles'] if v.get('job')==j['id'] and v['type'] in ('NEF','NAH') and v['status']=='scene' and not self.triage_unit(j,v)]
            qualified=[v for v in present if v.get('assessment_due',0)<=now]
            shared_rate=max(1,18*len(qualified)//max(1,len(scene))) if qualified else 0
            for p in scene+transport_care:
                unit=next((u for u in self.state['vehicles'] if u['id']==p.get('carrier') and u.get('job')==j['id'] and u['status']=='scene' and u.get('assessment_due',0)<=now),None)
                if p in transport_care:delta=random.randint(4,8)
                elif self.agency_gate(j):delta=0
                elif qualified:delta=shared_rate+(2 if p.get('doctor') else 0)
                elif present:delta=0
                else:delta=random.randint(-2,1) if unit else random.randint(-4,0)
                if self.tna_active(j) and self.tna_patient(j) is p:delta=max(0,delta)
                p['percent']=max(0,min(100,p['percent']+delta));p['triage']=triage(p['percent'])
                if p['percent']>=60:p['requires_doctor']=False
                elif p['percent']<45:p['requires_doctor']=True
            j['patients_next_change']=now+60
            self.assign_doctors(j)
        c=j.get('patient_condition')
        if scene and c:
            c.update(percent=min(p['percent'] for p in scene),notarzt_required=any(p['percent']<45 for p in scene))
        if self.is_manv(j):
            leader=self.ensure_triage_leader(j)
            if leader:self.request_manv_resources(j,leader)
            return
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
        v.pop('patient_index',None);v.pop('treating_patient',None);v.pop('care_switch_due',None);v.pop('escort_of',None)
