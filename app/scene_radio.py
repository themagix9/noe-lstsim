"""Crew-initiated situation reports and dispatcher-approved excess-unit cancellation."""
import uuid

class SceneRadio:
    def raise_scene_radio(self,j,v,force=False):
        if j.get('no_patient') or v['type']=='FR':return
        if self.is_manv(j):
            leader=self.ensure_triage_leader(j)
            if not leader or leader['id']!=v['id']:return
        if any(c['vehicle']==v['id'] and c['job']==j['id'] and c['kind']=='Lagemeldung' and c['state']!='closed' for c in self.state['radio_calls']):return
        if v['id'] in j.get('lage_reported',[]) and not force:return
        j.setdefault('lage_reported',[]).append(v['id'])
        call=dict(id=uuid.uuid4().hex[:12],job=j['id'],vehicle=v['id'],kind='Lagemeldung',state='calling',created=self.state['clock'])
        if self.is_manv(j):call['manv']=True;j['manv_reported_needs']=self.manv_needs(j)
        self.state['radio_calls'].append(call);self.log(f'LEO von {self.radio_name(v)}, kommen.','Funk')
        return call

    def excess_units(self,j,reporter):
        transporters=('KTW','KTW-B','BKTW','RTW','RTW-C','NAH')
        scene=[v for v in self.state['vehicles'] if v.get('job')==j['id'] and v['status']=='scene' and not self.triage_unit(j,v)]
        patients=max(1,len(self.scene_patients(j))) if j.get('patients') else 1
        doctor_need=self.doctor_demand(j) if j.get('patients') else int(j.get('patient_condition',{}).get('notarzt_required',False))
        enough_transport=sum(v['type'] in transporters for v in scene)>=patients
        enough_doctors=sum(v['type'] in ('NEF','NAH') for v in scene)>=doctor_need
        result=[]
        for v in self.state['vehicles']:
            if v.get('job')!=j['id'] or v['id']==reporter['id'] or v['status'] not in ('assigned','acknowledged','standby','enroute'):continue
            if v['type']=='NAH' and not (enough_transport and enough_doctors):continue
            if v['type']=='NEF' and not enough_doctors:continue
            if v['type'] in transporters and not enough_transport:continue
            if v['type']=='FR' and not (enough_transport and enough_doctors):continue
            result.append(v['id'])
        return result

    def scene_radio_action(self,j,c,v,data):
        step=data.get('step')
        if step=='end':
            self.radio_transmit('LEO',v,'verstanden. Ende.');c['state']='closed'
            if v.get('job')==j['id'] and v['status']=='scene' and v.get('phase_due') is None:v['phase_due']=self.state['clock']+120
            return
        if c.get('manv') and step in ('manv_confirm','manv_unavailable') and c['state']=='awaiting_end':
            needs=self.manv_needs(j)
            if step=='manv_confirm' and any(needs.values()):raise ValueError('Benötigte Kräfte zuerst zuordnen oder negativ bestätigen.')
            if step=='manv_unavailable':
                for kind,count in needs.items():
                    if count:j.setdefault('request_denials',{})[kind]={'time':self.state['clock'],'reason':'Keine weiteren Kräfte verfügbar.'}
            self.log(f'{self.radio_name(v)} von LEO, '+('negativ, derzeit keine weiteren Kräfte verfügbar.' if step=='manv_unavailable' else 'benötigte Kräfte sind disponiert.')+' Kommen.','Funk')
            self.log(f'LEO von {self.radio_name(v)}, verstanden.','Funk');self.log('LEO Ende.','Funk');c['state']='closed';return
        if step=='listen' and c['state']=='calling':
            self.radio_transmit('LEO',v,'hört, kommen.');condition=j.get('patient_condition') or {}
            text='Laufende Reanimation.' if condition.get('percent')==0 or j.get('code')=='RD-9E1' else j.get('scene_report',{}).get('text','')
            if not text or text.startswith('Mannschaft vor Ort'):
                text='Patient kritisch, notärztliche Versorgung läuft.' if condition.get('notarzt_required') and v['type'] in ('NEF','NAH') else 'Patient wird von uns versorgt, Zustand derzeit stabil.' if not condition.get('notarzt_required') else 'Patient kritisch, weitere Versorgung am Berufungsort.'
            if c.get('manv'):text=self.manv_report_text(j);j['manv_reported_needs']=self.manv_needs(j)
            elif j.get('patients'):text+=f' {len(self.scene_patients(j))} Patienten noch am Berufungsort, davon {sum(p["percent"]<45 for p in self.scene_patients(j))} kritisch.'
            present=[self.radio_name(u) for u in self.state['vehicles'] if u.get('job')==j['id'] and u['status']=='scene' and u['id']!=v['id']]
            if present:text+=' '+', '.join(present)+' bereits vor Ort.'
            c['cancel_candidates']=self.excess_units(j,v)
            if c['cancel_candidates']:text+=' Weitere anfahrende Kräfte können storniert werden.'
            c.update(state='awaiting_end',report=text)
            self.log(f'LEO von {self.radio_name(v)}, {text} Kommen.','Funk');return
        if step=='cancel_excess' and c['state']=='awaiting_end':
            ids=data.get('vehicles',[]);allowed=set(self.excess_units(j,v))&set(c.get('cancel_candidates',[]))
            if not ids or not isinstance(ids,list) or any(id not in allowed for id in ids):raise ValueError('Nur aktuell entbehrliche anfahrende Kräfte auswählen.')
            for id in dict.fromkeys(ids):
                unit=self.get('vehicles',id)
                self.contact_resource({'job':j['id'],'vehicle':id});storno=next(x for x in reversed(self.state['radio_calls']) if x['vehicle']==id and x['kind']=='Storno' and x['state']!='closed')
                # The reporting crew and LEO have already clarified that support
                # is not needed; deliver the cancellation to each affected crew.
                storno['state']='awaiting_cancel';self.cancellation_action({'job':j['id'],'call':storno['id'],'step':'cancel','reason':'Laut Lagemeldung vor Ort nicht mehr benötigt.'})
            c['cancel_candidates']=[id for id in c['cancel_candidates'] if id not in ids];return
        raise ValueError('Dieser Gesprächsschritt ist jetzt nicht möglich.')
