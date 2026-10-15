"""Interactive simulated crew requests, shared and owned with their incident."""
import os
import random
import uuid

class Radio:
    def radio_name(self,v):
        if v['type']=='FR' and v.get('fr_name'):return v['fr_name']+(f' {v["fr_number"]}' if v.get('fr_number') else '')
        if v['type']=='NAH':return {'C3':'Christophorus 3','C9':'Christophorus 9','C15':'Christophorus 15','C16':'Christophorus 16'}.get(v['callsign'],v['callsign'])
        if v['type']=='NEF':return 'NEF '+self.station(v['station'])['name'].removeprefix('RK ').removeprefix('NEF ').split(' · ')[0]
        return v['callsign']
    def radio_text(self,text):
        import re
        from hospitals import spoken_name
        for h in sorted(self.state.get('hospitals',[]),key=lambda h:len(h['name']),reverse=True):
            if h['name'] in str(text):text=str(text).replace(h['name'],spoken_name(h))
        text=re.sub(r'\bLeitstelle(?: NÖ)?\b','LEO',str(text))
        def name(value):
            unit=next((v for v in self.state['vehicles'] if v['callsign']==value),None)
            return self.radio_name(unit) if unit else value
        old=re.match(r'^(.*?) an (LEO|C\d+|[0-9]+/[0-9]+):\s*(.*)$',text)
        if old:text=f'{name(old[2])} von {name(old[1])}, {old[3]}'
        text=re.sub(r'\bC(?:3|9|15|16)\b',lambda match:name(match[0]),text)
        if re.match(r'^.+? von .+?,',text) and not text.lower().endswith(('kommen.','ende.','warten.')):text=text.rstrip() + (' ' if text.endswith(('.', '?', '!')) else '. ')+'Kommen.'
        return text

    def radio_metadata(self,text):
        import re
        match=re.match(r'^(.+?) von (.+?),',text)
        if not match:return {}
        parties={match[1],match[2]}
        unit=next((v for v in self.state['vehicles'] if self.radio_name(v) in parties or v['callsign'] in parties),None)
        if not unit:return {}
        job=next((j for j in self.state['jobs'] if j['id']==unit.get('job')),None)
        return dict(vehicle=unit['id'],job=unit.get('job'),owner=job.get('owner') if job else None)

    def radio_transmit(self,sender,receiver,text='kommen.'):
        sender=self.radio_name(sender) if isinstance(sender,dict) else sender
        receiver=self.radio_name(receiver) if isinstance(receiver,dict) else receiver
        text=text.strip()
        if not text.lower().endswith(('kommen.','ende.')):text=text.rstrip() + (' ' if text.endswith(('.', '?', '!')) else '. ')+'Kommen.'
        self.log(f'{receiver} von {sender}, {text}','Funk')

    def reinforcement_eta(self,unit,j):
        """Remaining simulated response time, including outstanding turnout."""
        import math
        from engine import distance
        from turnout import preparation
        if unit['status']=='scene':return {'seconds':0,'minutes':0,'approximate':False,'arrived':True}
        now=self.state['clock'];leg=unit.get('leg') or {};approximate=False
        if unit['status']=='enroute' and not leg.get('waiting') and leg.get('end') is not None:
            remaining=max(0,leg['end']-now)
        else:
            estimate=self.router.cached_eta(unit,j) if unit['type']!='NAH' else None
            if estimate and estimate.get('status')=='ready':travel=estimate['seconds']
            else:
                approximate=unit['type']!='NAH'
                travel=distance(unit,j)*(1 if unit['type']=='NAH' else 1.25)/(unit.get('flight_speed',220) if unit['type']=='NAH' else 45)*3600
            remaining=travel*self.response_factor(unit,j)
            if unit['status']!='enroute':
                remaining+=max(0,unit['turnout_due']-now) if unit.get('turnout_due') is not None else preparation(self,unit,j)
        minutes=max(1,math.ceil(remaining/60))
        return {'seconds':remaining,'minutes':minutes,'approximate':approximate,'arrived':False}

    def reinforcement_eta_text(self,unit,j):
        eta=self.reinforcement_eta(unit,j)
        if eta['arrived']:return 'Bereits am Berufungsort.'
        minutes=eta['minutes'];approximate=eta['approximate']
        return f'Eintreffzeit ca. {minutes} '+('Minute.' if minutes==1 else 'Minuten.')+(' Vorläufige Schätzung, Straßenroute wird noch ermittelt.' if approximate else '')

    def raise_radio(self,j,v,kind='NEF',reason=None,reason_initial=False,force=False):
        if self.is_manv(j) and kind in ('NEF','RTW','RTW-C'):
            leader=self.ensure_triage_leader(j)
            if leader and leader.get('assessment_due',0)<=self.state['clock']:return self.raise_scene_radio(j,leader,force=force)
            return
        if kind in j.get('request_denials',{}) and not force:return
        if any(c['job']==j['id'] and c['kind']==kind and c['state']!='closed' for c in self.state['radio_calls']):return
        if v['job']!=j['id'] or v['status']!='scene':raise ValueError('Mannschaft muss am Berufungsort sein.')
        if v.get('assessment_due',0)>self.state['clock']:raise ValueError('Mannschaft verschafft sich noch einen Überblick am Berufungsort.')
        if kind not in ('NEF','NAH','RTW-C','RTW','Polizei','Feuerwehr','Telenotarzt'):raise ValueError('Unbekannte Nachforderung.')
        if reason is not None and (not isinstance(reason,str) or len(reason)>300):raise ValueError('Nachforderungsgrund maximal 300 Zeichen.')
        if force:j.setdefault('request_denials',{}).pop(kind,None)
        reason=reason or {'Telenotarzt':'Bitte ärztliche Einschätzung und telefonische Anleitung zur weiteren Versorgung.','NAH':'Patiententransport unter laufender Reanimation, Notarzthubschrauber erforderlich.','NEF':'Patientenzustand verschlechtert, Notarzt erforderlich.','RTW-C':'Notfallsanitäter zur weiteren Versorgung erforderlich.','RTW':'Weiterer Patient am Berufungsort.','Polizei':'Unterstützung zur Absicherung erforderlich.','Feuerwehr':'Technische Unterstützung beim Patiententransport erforderlich.'}[kind]
        call={'id':uuid.uuid4().hex[:12],'job':j['id'],'vehicle':v['id'],'kind':kind,'reason':reason,'reason_initial':reason_initial,'state':'calling','created':self.state['clock'],'assigned':None}
        self.state['radio_calls'].append(call);self.state['radio_calls']=self.state['radio_calls'][-100:]
        self.log(f'LEO von {self.radio_name(v)}, kommen.','Funk');return call

    def maybe_reinforcement(self,j,v):
        if j.get('no_patient') or j.get('_scenario',{}).get('no_patient'):return
        if any(c['job']==j['id'] and c.get('transport_query') and c['state']!='closed' for c in self.state['radio_calls']):return
        if os.environ.get('REINFORCEMENTS_AUTO','1')=='0' and not j.get('exercise_reinforcement'):return
        if j.get('patients'):
            self.request_manv_resources(j,v);return
        if self.missing_carriers(j) and v['type'] not in ('NEF','NAH','FR'):
            self.raise_radio(j,v,'RTW','Zwei Patienten am Berufungsort, bitte ein zweites transportierendes Rettungsmittel.',reason_initial=True);return
        if v['type'] in ('NEF','NAH','FR') or j['kind']!='emergency' or j.get('reinforcement_checked'):return
        j['reinforcement_checked']=True
        protocol=str(j.get('code','')).removeprefix('RD-').split('-')[0]
        roll=random.random()
        if protocol.startswith('29') and not j.get('fire') and roll<.25:
            self.raise_radio(j,v,'Feuerwehr','Patient im Fahrzeug eingeschlossen, technische Rettung erforderlich.',reason_initial=True);return
        if protocol.startswith(('25','27')) and not j.get('police') and roll<.25:
            self.raise_radio(j,v,'Polizei','Gefährdung der Mannschaft, polizeiliche Absicherung erforderlich.',reason_initial=True);return
        if protocol.startswith('29') and roll<.4:
            self.raise_radio(j,v,'RTW','Zweiter Patient vor Ort, bitte ein weiteres Rettungsmittel.',reason_initial=True);return
        if any(self.get('vehicles',id)['job']==j['id'] and self.get('vehicles',id)['type'] in ('NEF','NAH') for id in j['vehicles']):return
        needed=j.get('patient_condition',{}).get('notarzt_required',False) or j.get('exercise_reinforcement')
        if needed:
            reason='Laufende Reanimation.' if (j.get('patient_condition') or {}).get('percent')==0 or j.get('exercise_reinforcement')=='reanimation' else random.choice(['Patientenzustand verschlechtert, deutlich eingeschränktes Bewusstsein.','Zunehmende Atemnot, bitte Notarzt zur weiteren Versorgung.'])
            self.raise_radio(j,v,'NEF',reason,reason_initial=random.random()<.35)

    def radio_action(self,data):
        j=self.get('jobs',data['job']);call=next((c for c in self.state['radio_calls'] if c['id']==data.get('call') and c['job']==j['id']),None)
        if not call:raise ValueError('Funkgespräch nicht gefunden.')
        v=self.get('vehicles',call['vehicle']);step=data.get('step');kind=call['kind']
        if call['state']=='closed':raise ValueError('Funkgespräch bereits beendet.')
        if kind=='Lagemeldung':return self.scene_radio_action(j,call,v,data)
        if step=='end':
            self.radio_transmit('LEO',v,'verstanden. Ende.');call.update(state='closed',ended=self.state['clock'])
            if v.get('job')==j['id'] and v['status']=='scene' and v.get('phase_due') is None:v['phase_due']=self.state['clock']+120
            return
        if not v['job']==j['id'] or v['status']!='scene':raise ValueError('Anfordernde Mannschaft nicht mehr am Berufungsort.')
        if step=='wait' and call['state'] in ('reason_needed','awaiting_dispatch'):
            self.log(f'{self.radio_name(v)} von LEO, warten.','Funk');return
        if step=='repeat' and call['state'] in ('reason_needed','awaiting_dispatch'):
            self.log(f'{self.radio_name(v)} von LEO, wiederholen, kommen.','Funk')
            request=('ein NEF' if kind=='NEF' else 'einen Notarzthubschrauber' if kind=='NAH' else 'einen RTW-C' if kind=='RTW-C' else 'einen weiteren RTW' if kind=='RTW' else 'einen Telenotarzt' if kind=='Telenotarzt' else 'die '+kind)
            self.log(f'LEO von {self.radio_name(v)}, ich wiederhole: Bitte {request} '+('zur telefonischen Beratung. ' if kind=='Telenotarzt' else 'zum Berufungsort. ')+(call['reason']+' ' if call['state']=='awaiting_dispatch' else '')+'Kommen.','Funk');return
        if step=='listen' and call['state']=='calling':
            self.radio_transmit('LEO',v,'hört, kommen.')
            self.log(f'LEO von {self.radio_name(v)}, bitte '+('ein NEF' if kind=='NEF' else 'einen Notarzthubschrauber' if kind=='NAH' else 'einen RTW-C' if kind=='RTW-C' else 'einen weiteren RTW' if kind=='RTW' else 'einen Telenotarzt' if kind=='Telenotarzt' else 'die '+kind)+(' zur telefonischen Beratung. ' if kind=='Telenotarzt' else ' zum Berufungsort. ')+(call['reason']+' ' if call['reason_initial'] else '')+'Kommen.','Funk')
            call['state']='awaiting_dispatch' if call['reason_initial'] else 'reason_needed'
            # Keep the crew at scene until the interactive request has been handled.
            v['phase_due']=None
        elif step=='reason' and call['state']=='reason_needed':
            self.radio_transmit('LEO',v,'Verstanden, Grund der Nachforderung? Kommen.');self.log(f'LEO von {self.radio_name(v)}, {call["reason"]} Kommen.','Funk');call['state']='awaiting_dispatch'
        elif step=='confirm' and call['state']=='awaiting_dispatch':
            if kind=='Telenotarzt':
                self.allocate_telenotarzt(j,v)
                answer='Telenotarzt ist zugebucht. Die Telefonnummer wurde per SDS und ESApp übermittelt.'
            elif kind in ('Polizei','Feuerwehr'):
                agency='police' if kind=='Polizei' else 'fire'
                text=call['reason'].lower()
                task='safety' if agency=='police' and any(t in text for t in ('gefährd','bedroh','gewalt','waffe')) else 'extrication' if agency=='fire' and any(t in text for t in ('eingeschloss','eingeklemm','technische rettung','befrei')) else 'fire' if agency=='fire' and any(t in text for t in ('brand','rauch','feuer')) else 'assist'
                existing=next((r for r in j.get('agency_requests',[]) if r['kind']==agency and r['status'] in ('waiting','alarmed','enroute','working','onscene')),None)
                if existing and task!='assist' and existing['task']!=task and existing.get('task_completed') is None:self.agency_task({'job':j['id'],'request':existing['id'],'task':task})
                request=existing or self.agency_request({'job':j['id'],'kind':agency,'task':task,'reason':call['reason']})
                answer=kind+(' ist angefordert; derzeit keine freie Einheit, Rückmeldung folgt.' if request['status']=='waiting' else ' ist verständigt und kommt zum Berufungsort.')
            else:
                unit=next((self.get('vehicles',id) for id in reversed(j['vehicles']) if (self.get('vehicles',id)['type']==kind or kind=='NEF' and self.get('vehicles',id)['type']=='NAH' or kind=='RTW' and self.get('vehicles',id)['type'] in ('RTW-C','KTW')) and self.get('vehicles',id)['job']==j['id'] and id!=v['id'] and self.get('vehicles',id)['status'] in ('assigned','standby','acknowledged','enroute','scene') and id not in [c.get('assigned') for c in self.state['radio_calls'] if c['job']==j['id'] and c['kind']==kind and c['state']=='closed']),None)
                if not unit:raise ValueError('Benötigtes Rettungsmittel zuerst zum bestehenden Einsatz dazubuchen.')
                self.confirm_transport_heli(j,call,unit)
                call['assigned']=unit['id'];j['reinforcement_waiting']=unit['id'];j['reinforcement_arrived']=unit['status']=='scene';place=self.station(unit['station'])['name'].removeprefix('RK ').split(' · ')[0]
                answer=f'{self.radio_name(unit) if kind in ("NEF","NAH") else kind+" "+place} kommt '+('ab Wache.' if unit.get('alarm_from')=='ready' else 'über Funk zum Berufungsort.')
                if kind in ('NEF','NAH'):
                    if unit['status']=='scene':answer=f'{self.radio_name(unit)} ist bereits am Berufungsort.'
                    else:answer+=' '+self.reinforcement_eta_text(unit,j)
            self.radio_transmit('LEO',v,answer+' Kommen.');self.log(f'LEO von {self.radio_name(v)}, '+('Telenotarzt' if kind=='Telenotarzt' else self.radio_name(unit) if kind in ('NEF','NAH') else answer.split(' kommt ')[0])+', verstanden.','Funk');self.log('LEO Ende.','Funk');call['state']='closed';v['phase_due']=self.state['clock']+120
        elif step=='unavailable' and call['state']=='awaiting_dispatch':
            self.log(f'{self.radio_name(v)} von LEO, '+('Negativ, derzeit kein Notarzthubschrauber verfügbar.' if kind=='NAH' else f'Negativ, derzeit keine weiteren Kräfte ({kind}) verfügbar.')+' Kommen.','Funk')
            self.log(f'LEO von {self.radio_name(v)}, negativ verstanden, Versorgung mit vorhandenen Mitteln. Kommen.','Funk')
            self.log('LEO Ende.','Funk');call.update(state='closed',declined=True)
            j.setdefault('request_denials',{})[kind]={'time':self.state['clock'],'reason':'Keine weiteren Kräfte verfügbar.'}
            if v.get('phase_due') is None:v['phase_due']=self.state['clock']+120
        else:raise ValueError('Dieser Gesprächsschritt ist jetzt nicht möglich.')

    def retry_requests(self,data):
        j=self.get('jobs',data['job']);kind=data.get('kind')
        if kind not in ('NEF','NAH','RTW-C','RTW','Polizei','Feuerwehr','Telenotarzt'):raise ValueError('Unbekannte Nachforderung.')
        j.setdefault('request_denials',{}).pop(kind,None)
        self.log(f'Einsatz {j["incident_number"]}: automatische Nachforderungen {kind} wieder zugelassen.','System')
        if self.is_manv(j) and kind in ('NEF','RTW'):
            leader=self.ensure_triage_leader(j)
            if leader and leader.get('assessment_due',0)<=self.state['clock']:self.raise_scene_radio(j,leader,force=True)
