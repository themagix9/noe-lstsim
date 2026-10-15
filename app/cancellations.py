"""Dispatcher-initiated radio contact and per-unit SDS/ESApp cancellation."""
import uuid

class Cancellations:
    def contact_resource(self,data):
        j=self.get('jobs',data['job']);v=self.get('vehicles',data['vehicle'])
        if v.get('job')!=j['id'] or v['status'] not in ('assigned','standby','acknowledged','enroute','scene'):raise ValueError('Storno nur für zugebuchte Ressourcen vor Patiententransport.')
        if any(c['vehicle']==v['id'] and c['kind']=='Storno' and c['state']!='closed' for c in self.state['radio_calls']):return
        call={'id':uuid.uuid4().hex[:12],'job':j['id'],'vehicle':v['id'],'kind':'Storno','state':'calling','created':self.state['clock'],'reason':'Weitere Kräfte nicht mehr erforderlich.'}
        self.state['radio_calls'].append(call);self.log(f'{self.radio_name(v)} von LEO, kommen.','Funk')

    def cancellation_action(self,data):
        j=self.get('jobs',data['job']);call=next((c for c in self.state['radio_calls'] if c['id']==data.get('call') and c['job']==j['id'] and c['kind']=='Storno'),None)
        if not call or call['state']=='closed':raise ValueError('Kein offenes Stornogespräch.')
        v=self.get('vehicles',call['vehicle'])
        if v.get('job')!=j['id'] or v['status'] not in ('assigned','standby','acknowledged','enroute','scene'):raise ValueError('Ressource ist inzwischen gebunden oder transportiert; Storno nicht mehr möglich.')
        if data.get('step')=='answer' and call['state']=='calling':
            self.log(f'LEO von {self.radio_name(v)}, hört.','Funk');call['state']='awaiting_cancel';return
        if data.get('step')!='cancel' or call['state']!='awaiting_cancel':raise ValueError('Zuerst Mannschaft anfunken und Antwort abwarten.')
        reason=str(data.get('reason') or call['reason']).strip()
        if len(reason)>250:raise ValueError('Stornogrund maximal 250 Zeichen.')
        text=f'EINSATZSTORNO {j["incident_number"]} · {j.get("code","")} · {j["address"]}. {reason}'
        for channel in ('SDS','ESApp'):
            self.state['messages'].append({'job':j['id'],'vehicle':v['id'],'channel':channel,'time':self.state['clock'],'text':text});self.log(f'{v["callsign"]}: '+text,channel)
        self.state['messages']=self.state['messages'][-250:]
        self.log(f'{self.radio_name(v)} von LEO, Einsatz {j["incident_number"]} für Sie storniert. {reason} Kommen.','Funk')
        self.log(f'LEO von {self.radio_name(v)}, Einsatzstorno verstanden.','Funk');self.log('LEO Ende.','Funk')
        previous=v['status'];self.detach(v);j['vehicles']=[id for id in j['vehicles'] if id!=v['id']]
        v.pop('assessment_due',None);v['ack_deadline']=None
        for c in self.state['radio_calls']:
            if c['vehicle']==v['id'] and c['job']==j['id']:c['state']='closed'
        if j.get('reinforcement_waiting')==v['id']:j.pop('reinforcement_waiting',None);j.pop('reinforcement_arrived',None)
        j.setdefault('cancellations',[]).append({'vehicle':v['id'],'callsign':v['callsign'],'time':self.state['clock'],'reason':reason})
        from engine import distance
        if previous in ('assigned','standby','acknowledged') and distance(v,self.home(v))<.03:v.update(status=self.idle_status(v),phase_due=None,leg=None)
        else:self.drive(v,self.home(v),'radio')
        self.log(f'{v["callsign"]}: '+('Status 1: frei auf Wache.' if v['status']=='ready' else 'Status 6: frei über Funk.'),'Status')
        if not j['vehicles']:j.update(status='done',completed=self.state['clock'],bed_state='none')
