"""Two-patient incidents with separate carriers and delivery bookkeeping."""
class MultiplePatients:
    def discover_patients(self,j):
        truth=j.get('_scenario',{})
        if truth.get('patient_count',1)<2 or j.get('patients'):return
        j['patient_count']=2
        j['patients']=[{'number':i+1,'name':'Übungspatient '+str(i+1),'percent':score,'carrier':None,'delivered':False} for i,score in enumerate(truth.get('patient_scores',[70,80]))]
        self.assign_patients(j)

    def assign_patients(self,j):
        if not j.get('patients'):return
        for id in j['vehicles']:
            v=self.get('vehicles',id)
            if v['job']!=j['id'] or v['type'] not in ('KTW','RTW','RTW-C','NAH'):continue
            if any(p['carrier']==id for p in j['patients']):continue
            patient=next((p for p in j['patients'] if not p['delivered'] and not p['carrier']),None)
            if patient:patient['carrier']=id;v['patient_index']=patient['number']-1

    def missing_carriers(self,j):
        if not j.get('patients'):return 0
        self.assign_patients(j)
        return sum(not p['delivered'] and not p['carrier'] for p in j['patients'])

    def delivered_patient(self,j,v):
        index=v.get('patient_index')
        if index is not None and j.get('patients'):
            j['patients'][index]['delivered']=True
            j['patient_delivered']=all(p['delivered'] for p in j['patients'])
        else:j['patient_delivered']=True

    def release_patient_carrier(self,j,v):
        if j.get('patients') and v.get('patient_index') is not None:
            p=j['patients'][v['patient_index']]
            if not p['delivered']:p['carrier']=None
        v.pop('patient_index',None)
