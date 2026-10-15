"""One first-arriving vehicle coordinates MANV triage, with patient care after the initial triage."""
class ManvCoordination:
    def is_manv(self,j):return bool(j.get('manv') or j.get('_scenario',{}).get('manv'))

    def triage_finished(self,j):return j.get('triage_completed_at') is not None or bool(j.get('patients') and j.get('scene_report'))

    def triage_unit(self,j,v):return self.is_manv(j) and j.get('triage_leader')==v['id'] and not self.triage_finished(j)

    def ensure_triage_leader(self,j):
        if not self.is_manv(j) or j['status']=='done':return None
        units=[self.get('vehicles',id) for id in j['vehicles']]
        candidates=[v for v in units if v.get('job')==j['id'] and v['status']=='scene' and v['type'] not in ('FR','BEL')]
        if not candidates:
            j['triage_leader']=None
            for unit in units:unit.pop('manv_role',None)
            return None
        candidate=min(candidates,key=lambda v:v.get('scene_arrived_at',0))
        current=next((v for v in candidates if v['id']==j.get('triage_leader')),None)
        leader=current if current and current.get('scene_arrived_at',0)<=candidate.get('scene_arrived_at',0) else candidate
        changed=j.get('triage_leader')!=leader['id'];j['triage_leader']=leader['id']
        # Existing sessions with an assessed patient list have finished triage.
        finished=self.triage_finished(j)
        if finished:
            j.setdefault('triage_completed_at',(j.get('scene_report') or {}).get('time',self.state['clock']))
            self.assign_patients(j)
        else:self.release_patient_carrier(j,leader)
        for unit in units:
            if unit['id']==leader['id']:unit['manv_role']='Koordination · Sichtung abgeschlossen' if finished else 'Sichtung / Koordination'
            else:unit.pop('manv_role',None)
        for call in self.state['radio_calls']:
            if call['job']==j['id'] and call['state']!='closed' and call['kind'] in ('Lagemeldung','NEF','NAH','RTW','RTW-C'):
                if call['vehicle']==leader['id'] and call['kind']=='Lagemeldung':call['manv']=True
                if call['vehicle']!=leader['id'] or call['kind']!='Lagemeldung':call.update(state='closed',ended=self.state['clock'],end_reason='MANV-Koordination über Sichtungsfahrzeug')
        if changed:self.log(f'{self.radio_name(leader)} übernimmt MANV-Koordination'+(' nach abgeschlossener Sichtung.' if finished else ' und die erste Sichtung; Patientenübernahme nach Abschluss möglich.'),'System')
        return leader

    def manv_needs(self,j):
        units=[v for v in self.state['vehicles'] if v.get('job')==j['id'] and not self.triage_unit(j,v) and v['status'] in ('assigned','standby','acknowledged','enroute','scene')]
        return dict(RTW=max(0,len(self.scene_patients(j))-sum(v['type'] in ('KTW','KTW-B','RTW','RTW-C','NAH') for v in units)),NEF=max(0,self.doctor_demand(j)-sum(v['type'] in ('NEF','NAH') for v in units)))

    def manv_request(self,j,v):
        leader=self.ensure_triage_leader(j)
        if not leader or leader['id']!=v['id'] or v.get('assessment_due',0)>self.state['clock']:return
        needs=self.manv_needs(j);previous=j.get('manv_reported_needs',{})
        force=any(count>previous.get(kind,0) and kind not in j.get('request_denials',{}) for kind,count in needs.items())
        self.raise_scene_radio(j,leader,force=force)

    def manv_report_text(self,j):
        patients=self.scene_patients(j);needs=self.manv_needs(j)
        text=f'Sichtung abgeschlossen. {len(patients)} Patienten noch am Berufungsort, davon {sum(p["percent"]<45 for p in patients)} kritisch.'
        parts=[]
        if needs['NEF']:parts.append(f'{needs["NEF"]} weitere Notarztmittel')
        if needs['RTW']:parts.append(f'{needs["RTW"]} weitere transportierende Rettungsmittel')
        return text+(' Benötigen '+ ' und '.join(parts)+'.' if parts else ' Derzeit ausreichend Rettungs- und Notarztmittel disponiert.')
