"""Per-resource simulated special-signal instructions and continuous journey timing."""
import uuid

SIGNAL_STATES=('assigned','standby','acknowledged','enroute','scene','transport')

class SignalOps:
    def signal_for(self,v,j):
        override=v.get('signal')
        return override if j and v.get('job')==j['id'] and isinstance(override,bool) else bool(j and j.get('signal'))

    def job_signal(self,data):
        j=self.get('jobs',data['job'])
        if j['status']=='done':raise ValueError('Einsatz bereits abgeschlossen.')
        if not isinstance(data.get('signal'),bool):raise ValueError('Signalfahrt ein- oder ausschalten.')
        for unit in self.state['vehicles']:
            if unit.get('job')==j['id'] and not isinstance(unit.get('signal'),bool):unit['signal']=bool(j.get('signal'))
        j['signal']=data['signal']
        self.log(f'Einsatz {j["incident_number"]}: neue Alarmierungen '+('mit' if j['signal'] else 'ohne')+' Sondersignal. Bereits alarmierte Kräfte über Funk umstellen.','System')

    def signal_contact(self,data):
        j=self.get('jobs',data['job']);v=self.get('vehicles',data['vehicle'])
        if not isinstance(data.get('signal'),bool):raise ValueError('Gewünschte Signalfahrt auswählen.')
        if v.get('job')!=j['id'] or v['status'] not in SIGNAL_STATES or v['type'] in ('NAH','FR','BEL'):raise ValueError('Signalfahrt nur bei einer zugebuchten Bodenressource vor Übergabe ändern.')
        if any(c['vehicle']==v['id'] and c['kind']=='Signalfahrt' and c['state']!='closed' for c in self.state['radio_calls']):raise ValueError('Signalfahrt-Gespräch ist bereits offen.')
        call={'id':uuid.uuid4().hex[:12],'job':j['id'],'vehicle':v['id'],'kind':'Signalfahrt','signal':data['signal'],'state':'calling','created':self.state['clock']}
        self.state['radio_calls'].append(call);self.log(f'{self.radio_name(v)} von LEO, kommen.','Funk')

    def set_unit_signal(self,v,j,enabled):
        old_factor=self.response_factor(v,j);v['signal']=enabled;factor=self.response_factor(v,j)
        leg=v.get('leg')
        if not leg or v['status'] not in ('enroute','transport'):return
        if leg.get('waiting'):leg['time_factor']=factor;return
        duration=leg['end']-leg['start']
        if duration<=0:return
        now=self.state['clock'];fraction=max(0,min(1,(now-leg['start'])/duration))
        if leg.get('geometry'):
            from routing import position
            v.update(position(leg,fraction))
        else:
            v.update(lat=leg['lat']+(leg['target_lat']-leg['lat'])*fraction,lon=leg['lon']+(leg['target_lon']-leg['lon'])*fraction)
        duration*=factor/leg.get('time_factor',old_factor)
        leg.update(start=now-fraction*duration,end=now+(1-fraction)*duration,time_factor=factor)
        v['phase_due']=leg['end']

    def signal_action(self,data):
        j=self.get('jobs',data['job'])
        call=next((c for c in self.state['radio_calls'] if c['id']==data.get('call') and c['job']==j['id'] and c['kind']=='Signalfahrt' and c['state']!='closed'),None)
        if not call:raise ValueError('Kein offenes Signalfahrt-Gespräch.')
        v=self.get('vehicles',call['vehicle']);step=data.get('step')
        if step=='cancel':call['state']='closed';self.log('LEO Ende.','Funk');return
        if v.get('job')!=j['id'] or v['status'] not in SIGNAL_STATES:raise ValueError('Ressource ist nicht mehr für diese Anweisung verfügbar.')
        if step=='answer' and call['state']=='calling':
            self.log(f'Hier {self.radio_name(v)}, hört.','Funk');call['state']='awaiting_instruction';return
        if step!='confirm' or call['state']!='awaiting_instruction':raise ValueError('Zuerst die Antwort der Mannschaft abwarten.')
        enabled=call['signal'];mode='mit Sondersignal' if enabled else 'ohne Sondersignal'
        self.log(f'{self.radio_name(v)} von LEO, weitere Fahrt {mode} durchführen. Kommen.','Funk')
        # Keep an accompanying NEF and its carrier in the same driving mode.
        leader=v.get('escort_of') or v['id']
        convoy=[u for u in self.state['vehicles'] if u.get('job')==j['id'] and u['status'] in SIGNAL_STATES and (u['id']==v['id'] or u['id']==leader or u.get('escort_of')==leader)]
        for unit in convoy:
            self.set_unit_signal(unit,j,enabled)
            text=f'Einsatz {j["incident_number"]}: weitere Fahrt {mode}. Anweisung der Leitstelle.'
            for channel in ('SDS','ESApp'):
                self.state['messages'].append({'job':j['id'],'vehicle':unit['id'],'channel':channel,'time':self.state['clock'],'text':text});self.log(f'{unit["callsign"]}: '+text,channel)
        self.state['messages']=self.state['messages'][-250:]
        self.log(f'Hier {self.radio_name(v)}, weitere Fahrt {mode}, verstanden.','Funk');self.log('LEO Ende.','Funk');call['state']='closed'
        call['applied']=self.state['clock']
