"""Occasional crew fuel requests; dispatcher approval gates a simulated five-minute pause."""
import os
import random
import uuid

class Fuel:
    def request_fuel(self,v):
        if v['type'] in ('FR','NAH','BEL') or v['status']!='radio' or v.get('job') or v.get('reservation'):raise ValueError('Tankwunsch nur für freie bodengebundene Ressourcen im Status 6.')
        if any(c['vehicle']==v['id'] and c['kind']=='Tanken' and c['state']!='closed' for c in self.state['radio_calls']):return
        call={'id':uuid.uuid4().hex[:12],'job':None,'vehicle':v['id'],'kind':'Tanken','state':'calling','created':self.state['clock'],'owner':None}
        self.state['radio_calls'].append(call);self.log(f'LEO von {self.radio_name(v)}, kommen.','Funk');return call

    def fuel_action(self,data):
        call=next((c for c in self.state['radio_calls'] if c['id']==data.get('call') and c['kind']=='Tanken'),None)
        if not call or call['state']=='closed':raise ValueError('Kein offener Tankwunsch.')
        actor=data.get('_actor',{}).get('id')
        if call.get('owner') and actor and actor!=call['owner']:raise ValueError('Funkgespräch wird von einem anderen Disponenten geführt.')
        v=self.get('vehicles',call['vehicle']);step=data.get('step')
        if v['status']!='radio' or v.get('job') or v.get('reservation'):
            call['state']='closed';raise ValueError('Ressource ist inzwischen gebunden; Tankwunsch entfällt.')
        if step=='listen' and call['state']=='calling':
            call.update(state='awaiting_permission',owner=actor);self.radio_transmit('LEO',v,'hört, kommen.')
            self.log(f'LEO von {self.radio_name(v)}, wir müssen tanken. Ist das möglich? Kommen.','Funk')
        elif step=='repeat' and call['state']=='awaiting_permission':
            self.log(f'{self.radio_name(v)} von LEO, wiederholen, kommen.','Funk');self.log(f'LEO von {self.radio_name(v)}, wir bitten um Freigabe zum Tanken. Kommen.','Funk')
        elif step in ('allow','deny') and call['state']=='awaiting_permission':
            allowed=step=='allow';self.log(f'{self.radio_name(v)} von LEO, '+('Tanken zugelassen, melden Sie sich anschließend frei.' if allowed else 'Derzeit nicht möglich, bitte einsatzbereit bleiben.')+' Kommen.','Funk')
            self.log(f'LEO von {self.radio_name(v)}, verstanden.','Funk');self.log('LEO Ende.','Funk');call['state']='closed';v['next_fuel_check']=self.state['clock']+3600
            if allowed:
                v.update(status='duty',leg=None,phase_due=self.state['clock']+300,fueling=True)
                self.log(f'{v["callsign"]}, Status 7: simulierte Tankpause (5 Minuten).','Status')
        else:raise ValueError('Dieser Gesprächsschritt ist jetzt nicht möglich.')

    def update_fuel(self,now):
        for v in self.state['vehicles']:
            if v.get('fueling') and v.get('phase_due') is not None and now>=v['phase_due']:
                v.update(fueling=False,status='radio' if self.in_shift(v) else 'out',phase_due=None)
                self.log(f'{v["callsign"]}, Tankpause beendet, '+('Status 6: frei über Funk.' if v['status']=='radio' else 'Status 0: außer Betrieb.'),'Status')
            for call in self.state['radio_calls']:
                if call['vehicle']==v['id'] and call['kind']=='Tanken' and call['state']!='closed' and (v['status']!='radio' or v.get('job') or v.get('reservation')):call['state']='closed'
            if os.environ.get('FUEL_REQUESTS_AUTO','1')=='0' or v['type'] in ('FR','NAH','BEL'):continue
            v.setdefault('next_fuel_check',now+1200)
            if now<v['next_fuel_check']:continue
            v['next_fuel_check']=now+1200
            if v['status']=='radio' and not v.get('job') and not v.get('reservation') and random.random()<.08:self.request_fuel(v)
