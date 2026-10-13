"""Fictional 0–100 gameplay stability; no clinical score or treatment guidance."""
import os
import random

class Patients:
    def update_assessments(self,now):
        for v in self.state['vehicles']:
            due=v.get('assessment_due')
            if due is None or now<due:continue
            v.pop('assessment_due',None)
            if v['status']!='scene' or not v.get('job'):continue
            j=self.get('jobs',v['job'])
            self.patient_report(j,v)
            self.maybe_reinforcement(j,v)

    def ensure_patient_condition(self,j,replace=False):
        if j.get('patient_condition') and not replace:return
        score=0 if j.get('code')=='RD-9E1' else random.randint(15,40) if 'NEF' in j.get('needs',[]) else random.randint(85,100) if j['kind']=='transport' else random.randint(55,90)
        j['patient_condition']={'percent':score,'reported':False,'notarzt_required':score<45,'last_report':None,'next_change':self.state['clock']+300,'model':'Fiktiver Spielwert – keine medizinische Bewertung'}

    def patient_report(self,j,v,force=False):
        if v.get('assessment_due',0)>self.state['clock']:return
        self.ensure_patient_condition(j);c=j['patient_condition']
        if c['reported'] and not force:return
        c.update(reported=True,last_report=self.state['clock'],next_change=self.state['clock']+300)
        present=any(self.get('vehicles',id)['job']==j['id'] and self.get('vehicles',id)['type'] in ('NEF','NAH') for id in j['vehicles'])
        if c['notarzt_required'] and not present:
            reason='Laufende Reanimation.' if j.get('code')=='RD-9E1' else 'Patientenzustand verschlechtert, Notarzt zur weiteren Versorgung erforderlich.'
            if os.environ.get('REINFORCEMENTS_AUTO','1')!='0':self.raise_radio(j,v,'NEF',reason,reason_initial=True)
        else:self.log(f'Hier {self.radio_name(v)}, '+('Notarztversorgung erforderlich, Notarztmittel bereits disponiert.' if c['notarzt_required'] else 'Patient aktuell stabil, kein Notarztmittel nachgefordert.')+' Kommen.','Funk')

    def update_patients(self,now):
        if os.environ.get('PATIENT_EVOLUTION','1')=='0':return
        for j in self.state['jobs']:
            self.ensure_patient_condition(j);c=j['patient_condition']
            if not c['reported'] or j['status']!='scene' or now<c['next_change']:continue
            units=[self.get('vehicles',id) for id in j['vehicles'] if self.get('vehicles',id)['job']==j['id']]
            carrier=next((v for v in units if v['type'] in ('KTW','KTW-B','BKTW','RTW','RTW-C','NAH')),None)
            if not carrier:continue
            doctor=any(v['type'] in ('NEF','NAH') and v['status']=='scene' for v in units)
            previous=c['notarzt_required'];delta=random.randint(1,6) if doctor else random.randint(-12,4)
            if j.get('code')!='RD-9E1':c['percent']=max(0,min(100,c['percent']+delta))
            c['notarzt_required']=c['percent']<45;c['next_change']=now+300
            if previous!=c['notarzt_required'] and carrier['status']=='scene':self.patient_report(j,carrier,force=True)
