"""Per-room automatic incident rates, measured in simulation hours."""
import math,random

class EventGeneration:
    def event_settings(self):
        split=self.state['setup'].get('workflow')=='split'
        defaults=dict(emergency_per_hour=6 if split else 3,transport_per_hour=6 if split else 4,transports_enabled=True)
        return {**defaults,**self.state['setup'].get('events',{})}

    def event_interval(self,rate):return 3600/rate*random.uniform(.6,1.4)

    def configure_events(self,data):
        settings=self.event_settings()
        for field in ('emergency_per_hour','transport_per_hour'):
            value=data.get(field,settings[field])
            if isinstance(value,bool):raise ValueError('Einsatzfrequenz zwischen 0 und 120 pro Simulationsstunde eingeben.')
            try:value=float(value)
            except (ValueError,TypeError):raise ValueError('Einsatzfrequenz zwischen 0 und 120 pro Simulationsstunde eingeben.')
            if not math.isfinite(value) or not 0<=value<=120:raise ValueError('Einsatzfrequenz zwischen 0 und 120 pro Simulationsstunde eingeben.')
            settings[field]=value
        enabled=data.get('transports_enabled',settings['transports_enabled'])
        if not isinstance(enabled,bool):raise ValueError('Automatische Krankentransporte ein- oder ausschalten.')
        settings['transports_enabled']=enabled;self.state['setup']['events']=settings
        for kind in ('emergency','transport'):
            rate=settings[kind+'_per_hour'] if kind!='transport' or enabled else 0
            self.state['next_'+kind]=self.state['clock']+self.event_interval(rate) if rate else None
        self.log(f'Einsatzfrequenz geändert: {settings["emergency_per_hour"]:g} Notrufe/h, '+(f'{settings["transport_per_hour"]:g} Transportaufträge/h.' if enabled else 'automatische Krankentransporte ausgeschaltet.'),'System')

    def generate_events(self,now):
        if self.state['setup']['dispo']!='05' or not any(s.get('dispo')=='05' for s in self.state['stations']):return
        settings=self.event_settings()
        for kind in ('emergency','transport'):
            rate=settings[kind+'_per_hour'] if kind!='transport' or settings['transports_enabled'] else 0
            key='next_'+kind;due=self.state.get(key)
            if not rate:self.state[key]=None;continue
            if due is not None and now>=due:self.new_job(kind)
            if due is None or now>=due:self.state[key]=now+self.event_interval(rate)
