"""Simulation of crew reports, reservations and the Vienna bed coordinator."""
import random
import uuid

STATUS_LABELS = {'ready':'1 · Frei auf Wache','enroute':'2 · Zum Berufungsort','scene':'3 · Am Berufungsort','transport':'4 · Zum Zielort','hospital':'5 · Am Zielort','radio':'6 · Frei über Funk','duty':'7 · Dienstfahrt','standby':'8 · Bereitschaft','acknowledged':'9 · Alarmiert und Quittiert','out':'0 · Außer Betrieb','fr_ready':'Bereitschaft · zuhause'}
JOB_ACTIONS = ('accept','ask','dispatch','reserve','unreserve','bed_request','send_case','edit_job','carrier','ask_cpr','radio','radio_generate','call_question','call_finish')

class Operations:
    def migrate_operations(self):
        for h in self.state['hospitals']:
            h.setdefault('region','Wien' if h['id'].startswith('kh-donaustadt') else 'NÖ')
        for h in self.state['hospitals']:h.setdefault('helipad',True)
        if not any(h['id']=='kh-akh-ecpr' for h in self.state['hospitals']):self.state['hospitals'].append({'id':'kh-akh-ecpr','name':'AKH Wien · eCPR (Übungsziel)','region':'Wien','lat':48.220,'lon':16.347,'helipad':True,'ecpr':True,'source':'eCPR-Zentrum MedUni Wien; Annahme/Verfügbarkeit simuliert'})
        from catalog import RULES
        self.state.setdefault('rules',__import__('copy').deepcopy(RULES))
        self.state.setdefault('setup',{'centre':'Mödling','dispo':'05'})
        for station in self.state['stations']:station.setdefault('dispo','05' if station['zone']=='Bruck/Leitha' else '')
        self.state.setdefault('messages',[])
        self.state.setdefault('radio_calls',[])
        self.state.setdefault('incident_counter',0)
        for j in self.state['jobs']:
            self.ensure_alarm_identity(j)
            j.setdefault('code',next((r['code'] for r in self.state['rules'] if r['title']==j['title']),'SIM-KT' if j['kind']=='transport' else 'RD-17B1'));j.setdefault('signal',j['priority']=='hoch');j.setdefault('additional','');j.setdefault('police',False);j.setdefault('fire',False)
            j.setdefault('reserved',None); j.setdefault('bed_state','none');j.setdefault('case_number',None)
            j.setdefault('requested_destination',None);j.setdefault('bed_due',None)
            if j['kind']=='emergency' and j['status']=='new':j['destination']=None
        for v in self.state['vehicles']:
            if v['status']=='return':v['status']='radio'
            elif v['status']=='clean':v['status']='out';v['out_reason']='Fahrzeugaufbereitung'
            v.setdefault('rtwc_capable',v['type']=='RTW-C');v.setdefault('rtwc_fixed',False);v.setdefault('daylight',False);v.setdefault('nfs',False)
            if v['type']=='RTW-C':v['nfs']=True
            v.setdefault('turnout',60);v.setdefault('organization','RK')
            v.setdefault('alarm_from','ready');v.setdefault('ack_deadline',None)
            v.setdefault('reservation',None);v.setdefault('manual_out',False);v.setdefault('leg',None)

    def ensure_alarm_identity(self,j):
        if not j.get('incident_number'):
            self.state['incident_counter']=self.state.get('incident_counter',0)+1
            serial=self.state['incident_counter']
            year=str(self.state.get('start_date','2026'))[:4]
            j['incident_number']=year+f'{serial:07d}'
            j['billing_number']=f'SIM-{serial:07d}'
        j.setdefault('patient',{'name':'Übungspatient '+j['incident_number'][-7:],'fictitious':True})
        j.setdefault('event_title',j['title'])

    def eligible(self,v,j):
        if j.get('code')=='KTx-96K5':return v['type'] in ('RTW','RTW-C')
        return v['type'] in (('KTW','KTW-B','BKTW','RTW','RTW-C') if j['kind']=='transport' else ('KTW','RTW','RTW-C','NEF','NAH','FR'))

    def sendable(self,v,j):
        # Hospital handover can finish while the next transport is transmitted.
        return self.in_shift(v) and v['status'] in (('ready','radio','hospital','fr_ready') if j['kind']=='transport' else ('ready','radio','fr_ready')) and self.eligible(v,j) and (not v.get('reservation') or v['reservation']==j['id'])

    def reserve(self,data):
        j=self.get('jobs',data['job']);v=self.get('vehicles',data['vehicle'])
        if j['kind']!='transport' or j['vehicles'] or j['status']=='done':raise ValueError('Nur offene Transportaufträge können vordisponiert werden.')
        if not self.eligible(v,j):raise ValueError('Eine transportierende Ressource wählen.')
        if v.get('reservation') and v['reservation']!=j['id']:raise ValueError('Ressource bereits für einen anderen Auftrag reserviert.')
        old=j.get('reserved')
        if old and old!=v['id']:self.get('vehicles',old)['reservation']=None
        v['reservation']=j['id'];j['reserved']=v['id']
        self.log(f'{v["callsign"]} für Transport {j["id"]} vordisponiert. Noch nicht an die Mannschaft gesendet.','Aufträge')

    def unreserve(self,data):
        j=self.get('jobs',data['job'])
        if j.get('reserved'):self.get('vehicles',j['reserved'])['reservation']=None
        j['reserved']=None

    def detach(self,v):
        if not v['job']:return
        old=self.get('jobs',v['job'])
        if v['status']=='hospital' and v['type'] not in ('NEF','FR'):old['patient_delivered']=True
        v['job']=None
        if all(self.get('vehicles',id)['job']!=old['id'] for id in old['vehicles']):
            old['status']='done' if old.get('patient_delivered') else 'assigned'

    def drive(self,v,target,status,minimum=120):
        from engine import distance
        now=self.state['clock']
        if v['type']=='NAH' or not self.router.enabled:
            duration=max(60 if v['type']=='NAH' else minimum,distance(v,target)*(1 if v['type']=='NAH' else 1.25)/(v.get('flight_speed',220) if v['type']=='NAH' else 45)*3600)
            v.update(status=status,route_state='flight' if v['type']=='NAH' else 'disabled',phase_due=now+duration,leg={'start':now,'end':now+duration,'lat':v['lat'],'lon':v['lon'],'target_lat':target['lat'],'target_lon':target['lon']})
            return
        v.update(status=status,route_state='pending',phase_due=None,leg={'waiting':True,'lat':v['lat'],'lon':v['lon'],'target_lat':target['lat'],'target_lon':target['lon']})
        self.resolve_route(v)

    def resolve_route(self,v):
        leg=v['leg'];origin={'lat':leg['lat'],'lon':leg['lon']};target={'lat':leg['target_lat'],'lon':leg['target_lon']}
        route=self.router.route(origin,target);v['route_state']=route['status']
        if route['status']!='ready':return
        now=self.state['clock'];duration=route['seconds']
        v.update(phase_due=now+duration,leg={**leg,'waiting':False,'start':now,'end':now+duration,'geometry':route['geometry'],'cumulative':route['cumulative'],'distance_m':route['distance_m']})

    def dispatch(self,data):
        j=self.get('jobs',data['job']);ids=data.get('vehicles',[])
        if not j['accepted']:raise ValueError('Zuerst den Notruf annehmen.')
        if j['status']=='done' or not ids:raise ValueError('Offenen Auftrag und Fahrzeuge auswählen.')
        if len(ids)!=len(set(ids)):raise ValueError('Fahrzeug mehrfach ausgewählt.')
        if j['kind']=='transport' and (len(ids)!=1 or j['vehicles']):raise ValueError('Ein Transportauftrag hat genau eine Ressource.')
        if data.get('destination') and data['destination']!=j.get('destination'):raise ValueError('Das Transportziel wird von der Mannschaft bzw. dem Transportauftrag gemeldet.')
        selected=[self.get('vehicles',id) for id in ids]
        for v in selected:
            if not self.sendable(v,j):raise ValueError(f'{v["callsign"]} kann den Auftrag noch nicht erhalten (Status 1, 5 oder 6 erforderlich).')
            if v['status']=='hospital' and j['kind']!='transport':raise ValueError('Während der Übergabe nur Transportaufträge senden.')
        if j.get('call',{}).get('state')=='connected':raise ValueError('Notruf zuerst vollständig abfragen.')
        if j.get('call',{}).get('state')=='ready':self.finish_call({'job':j['id']})
        if j['kind']=='transport' and j.get('reserved'):
            self.unreserve({'job':j['id']})
        if j.get('code')=='RD-9E1' and any(v['type']=='NAH' for v in selected) and j['status'] in ('transport','hospital'):raise ValueError('eCPR-Flug vor Beginn des Patiententransports abstimmen.')
        if j.get('code')=='RD-9E1':
            j['police']=True;self.log('Polizei: simulierte Alarmierung für 9E1.','System')
            if any(v['type']=='NAH' for v in selected):
                if j['status'] in ('transport','hospital'):raise ValueError('eCPR-Flug vor Beginn des Patiententransports abstimmen.')
                j['carrier']=next(v['id'] for v in selected if v['type']=='NAH');self.ecpr_precall(j)
        for v in selected:
            self.ensure_alarm_identity(j)
            text=f'Einsatz {j["incident_number"]} | {j["code"]} – {j["title"]} | {j.get("category") or "Transportauftrag"} | {j["address"]} | {j["detail"]} | Zusatz: {j.get("additional") or "—"} | Signalfahrt: '+('ja' if j.get('signal') else 'nein')+f' | Ressource: {v["type"]} {v["callsign"]} | Verrechnung: {j["billing_number"]}'
            for channel in ('SDS','ESApp'):
                self.state['messages'].append({'job':j['id'],'vehicle':v['id'],'channel':channel,'text':text,'time':self.state['clock'],'incident_number':j['incident_number'],'code':j['code']})
                self.log(f'{v["type"]} {v["callsign"]} ← '+text,channel)
            self.state['messages']=self.state['messages'][-250:]
            previous=v['status'];handover=v.get('phase_due') if previous=='hospital' else None
            self.detach(v)
            v.update(status='standby' if data.get('standby') else 'assigned',alarm_from=previous,job=j['id'],phase_due=self.state['clock']+random.randint(20,45),ack_deadline=self.state['clock']+600,handover_due=handover,leg=None,manual_out=False)
            j['vehicles'].append(v['id'])
            if v.get('reservation')==j['id']:v['reservation']=None;j['reserved']=None
            self.log(f'{v["type"]} {v["callsign"]}: '+('Bereitschaft' if data.get('standby') else 'Alarmiert auf Wache' if previous=='ready' else 'Alarmiert über Funk')+'.','Status')
        if j.get('ecpr_state') in ('awaiting_question','question_sent'):j['status']='awaiting_cpr'
        elif j['bed_state'] in ('requested','calling','allocated'):j['status']='awaiting_bed'
        elif j['status'] not in ('scene','transport','hospital'):j['status']='assigned'
        return j

    def acknowledge(self,v,direct=False):
        if v['status'] not in ('assigned','standby'):raise ValueError('Es liegt keine offene Alarmierung vor.')
        v['ack_deadline']=None
        if direct:self.depart(v)
        else:
            v.update(status='acknowledged',phase_due=max(self.state['clock']+15,v.get('handover_due') or 0))
            self.log(f'{v["callsign"]}, Status 9: alarmiert und quittiert.')

    def depart(self,v):
        if v.get('handover_due') and self.state['clock']<v['handover_due']:
            v.update(status='acknowledged',phase_due=v['handover_due']);return
        j=self.get('jobs',v['job']);self.drive(v,j,'enroute')
        self.log(f'{v["callsign"]}, Status 2: zum Berufungsort {j["place"]}.')

    def crew_destination(self,v):
        j=self.get('jobs',v['job'])
        waiting=j.get('reinforcement_waiting')
        if waiting and not j.get('reinforcement_arrived'):
            unit=self.get('vehicles',waiting)
            if unit['job']==j['id'] and unit['status']!='scene':v['phase_due']=self.state['clock']+30;return
        carrier=self.patient_carrier(j)
        if carrier and v['id']!=carrier['id']:
            if carrier['status'] in ('transport','hospital') or j.get('patient_delivered'):self.detach(v);self.drive(v,self.home(v),'radio')
            else:v['phase_due']=None
            return
        if j.get('ecpr_state') in ('prealerted','awaiting_question','question_sent'):
            j['ecpr_state']='awaiting_question' if j['ecpr_state']=='prealerted' else j['ecpr_state'];j['status']='awaiting_cpr';v['phase_due']=None;return
        if j['kind']=='transport':
            self.start_transport(v);return
        if j['bed_state']!='none':
            if j['bed_state'] in ('crew_selected','sent') and j.get('destination'):
                if j['bed_state']=='sent':
                    self.log(f'{v["callsign"]}: bestehende Zielinformation mit Kasusnummer {j["case_number"]} per {j["case_channel"]} erhalten.',j['case_channel'])
                self.start_transport(v)
            else:v['phase_due']=None
            return
        h=self.get('hospitals',j['crew_target']) if j.get('crew_target') else random.choice([h for h in self.state['hospitals'] if not h.get('ecpr') and (v['type']!='NAH' or h.get('helipad'))]);j['requested_destination']=h['id']
        if h['region']=='Wien':
            j['destination']=None;j['bed_state']='requested';j['status']='awaiting_bed';v['phase_due']=None
            self.log(f'{v["callsign"]} an Leitstelle: Patient transportbereit, benötigen ein Ziel in Wien, Wunsch {h["name"]}. Bitte Bettenmann verständigen.')
        else:
            j['destination']=h['id'];j['bed_state']='crew_selected'
            self.log(f'{v["callsign"]} an Leitstelle: Transportziel {h["name"]}, von der Mannschaft vor Ort festgelegt.')
            self.start_transport(v)

    def start_transport(self,v):
        j=self.get('jobs',v['job']);h=self.get('hospitals',j['destination'])
        if v['type']=='NAH' and not h.get('helipad'):raise ValueError('Hubschrauberziel benötigt einen Landeplatz.')
        if j.get('cpr_confirmed') and (v['type']!='NAH' or not h.get('ecpr') or j.get('ecpr_state')!='confirmed'):raise ValueError('eCPR-Flug erst nach Mannschaftsrückmeldung und Zielbestätigung.')
        for id in j['vehicles']:
            other=self.get('vehicles',id)
            if other['id']!=v['id'] and other['job']==j['id'] and other['status']=='scene':self.detach(other);self.drive(other,self.home(other),'radio')
        self.drive(v,h,'transport',180);j['status']='transport'
        self.log(f'{v["callsign"]}, Status 4: Patient übernommen, zum Zielort {h["name"]}.')

    def request_bed(self,data):
        j=self.get('jobs',data['job']);h=self.get('hospitals',data['hospital'])
        if j['bed_state']!='requested':raise ValueError('Zuerst muss die Mannschaft ein Wiener Ziel anfordern.')
        if j.get('cpr_confirmed') and (not h.get('ecpr') or not h.get('helipad')):raise ValueError('Bestätigter Reanimationstransport benötigt eCPR-Ziel mit Heli-Landeplatz.')
        if h['region']!='Wien':raise ValueError('Beim Wiener Bettenmann ein Wiener Krankenhaus wählen.')
        j.update(destination=h['id'],bed_state='calling',bed_due=self.state['clock']+30)
        self.log(f'Leitstelle NÖ an Bettenmann Wien: Zielanfrage {h["name"]}, Einsatz {j["id"]}, {j["title"]}.','Bettenmann')

    def send_case(self,data):
        j=self.get('jobs',data['job']);channel=data.get('channel')
        if j['bed_state']!='allocated' or not j['case_number']:raise ValueError('Noch keine Kasusnummer vom Bettenmann vorhanden.')
        if channel not in ('SDS','ESApp'):raise ValueError('SDS oder ESApp wählen.')
        carrier=self.patient_carrier(j);targets=[carrier] if carrier else []
        if not targets or any(v['status']!='scene' for v in targets):raise ValueError('Keine wartende Mannschaft am Berufungsort.')
        h=self.get('hospitals',j['destination']);j['bed_state']='sent';j['case_channel']=channel
        for v in targets:
            text=f'Ziel {h["name"]}; Kasusnummer {j["case_number"]}. Bei der Aufnahme angeben.'
            self.state['messages'].append({'job':j['id'],'vehicle':v['id'],'channel':channel,'text':text,'time':self.state['clock']})
            self.log(f'Leitstelle → {v["callsign"]}: {text}',channel)
            self.log(f'{v["callsign"]}, {channel} erhalten, Kasusnummer {j["case_number"]} verstanden.')
            self.start_transport(v)
        self.state['messages']=self.state['messages'][-250:]

    def update_operations(self,now):
        for j in self.state['jobs']:
            if j['bed_state']=='calling' and now>=j['bed_due']:
                j['case_number']='SIM-W-'+uuid.uuid4().hex[:8].upper();j['bed_state']='allocated';j['bed_due']=None
                self.log(f'Bettenmann Wien: {self.get("hospitals",j["destination"])["name"]}, Kasusnummer {j["case_number"]}.','Bettenmann')
        for v in self.state['vehicles']:
            leg=v.get('leg')
            if v['status']=='transport' and v.get('job') and not leg:
                # Recover older persisted transports which lost their active route.
                j=self.get('jobs',v['job']);h=self.get('hospitals',j['destination'])
                from engine import distance
                if distance(v,h)>.02:self.drive(v,h,'transport',180);leg=v.get('leg')
            if leg and self.router.enabled and v['type']!='NAH' and not leg.get('geometry') and not leg.get('waiting'):
                # Resume persisted journeys from older versions on a road route.
                self.drive(v,{'lat':leg['target_lat'],'lon':leg['target_lon']},v['status'])
                leg=v['leg']
            if leg and leg.get('waiting'):
                self.resolve_route(v);leg=v['leg']
            if leg and not leg.get('waiting'):
                fraction=min(1,max(0,(now-leg['start'])/(leg['end']-leg['start'])))
                if leg.get('geometry'):
                    from routing import position
                    v.update(position(leg,fraction))
                else:
                    v['lat']=leg['lat']+(leg['target_lat']-leg['lat'])*fraction;v['lon']=leg['lon']+(leg['target_lon']-leg['lon'])*fraction
            if v.get('ack_deadline') and now>=v['ack_deadline']:
                self.log(f'{v["callsign"]}: Quittierungsfrist von 10 Minuten überschritten. Mannschaft nachfragen.','System');v['ack_deadline']=None

    def advance(self,v):
        now=self.state['clock'];home=self.home(v);status=v['status'];v['leg']=None
        if status in ('assigned','standby'):self.acknowledge(v,direct=status=='assigned' and random.random()<.25);return
        if status=='acknowledged':self.depart(v);return
        if status=='enroute':
            j=self.get('jobs',v['job']);v.update(status='scene',phase_due=now+(600 if j['kind']=='transport' else 900),lat=j['lat'],lon=j['lon'])
            if j.get('reinforcement_waiting')==v['id']:j['reinforcement_arrived']=True
            if v['type'] not in ('NEF','NAH','FR'):self.patient_report(j,v)
            self.maybe_reinforcement(j,v)
            if j.get('ecpr_state') in ('awaiting_question','question_sent'):j['status']='awaiting_cpr'
            elif j['bed_state'] in ('requested','calling','allocated'):j['status']='awaiting_bed'
            elif j['status'] not in ('transport','hospital'):j['status']='scene'
            self.log(f'{v["callsign"]}, Status 3: am Berufungsort.','Status');return
        if status=='scene' and any(c['vehicle']==v['id'] and c['state']!='closed' for c in self.state['radio_calls']):v['phase_due']=None;return
        if status=='scene':
            if v['type'] in ('NEF','FR'):self.detach(v);self.drive(v,home,'radio');self.log(f'{v["callsign"]}, Status 6: Versorgung beendet, frei über Funk, Rückfahrt.')
            else:self.crew_destination(v)
            return
        if status=='transport':
            j=self.get('jobs',v['job']);h=self.get('hospitals',j['destination']);v.update(status='hospital',phase_due=now+600,lat=h['lat'],lon=h['lon']);j['status']='hospital'
            self.log(f'{v["callsign"]}, Status 5: am Zielort, Patientenübergabe.'+(f' Aufnahme mit Kasusnummer {j["case_number"]}.' if j.get('case_number') else ''));return
        if status=='hospital':
            self.detach(v);self.drive(v,home,'radio');self.log(f'{v["callsign"]}, Übergabe abgeschlossen, Status 6: frei über Funk.');return
        if status in ('radio','duty'):
            v.update(status=self.idle_status(v),phase_due=None,lat=home['lat'],lon=home['lon']);self.log(f'{v["callsign"]}, '+('Status 1: frei auf Wache.' if v['status']=='ready' else 'Status 0: außer Betrieb.'));return
        if status=='out' and v['job']:
            self.detach(v);v.update(status=self.idle_status(v),phase_due=None);return
        v['phase_due']=None

    def vehicle_status(self,data):
        v=self.get('vehicles',data['vehicle']);code=str(data.get('status'))
        if code in ('9','2'):
            if not v['job']:raise ValueError('Kein alarmierter Auftrag vorhanden.')
            if code=='9':self.acknowledge(v)
            elif v['status'] in ('assigned','standby','acknowledged'):self.depart(v)
            else:raise ValueError('Status 2 nur nach Alarmierung oder Quittierung.')
            return
        if v['job']:raise ValueError('Eine laufende Versorgung kann nicht mit einem freien Status beendet werden.')
        if v['type']=='FR' and code=='1':raise ValueError('First Responder haben keine Wache; Bereitschaft zuhause verwenden.')
        if v['type']=='FR' and code=='8':
            v.update(status='fr_ready',phase_due=None,ack_deadline=None,manual_out=False);return
        mapping={'0':'out','1':'ready','6':'radio','7':'duty','8':'standby'}
        if code not in mapping:raise ValueError('Ungültiger Statuswechsel.')
        if code!='0' and not self.in_shift(v):raise ValueError('Fahrzeug außerhalb der Dienstzeit oder unbesetzt.')
        v.update(status=mapping[code],phase_due=None,leg=None,manual_out=code=='0',ack_deadline=self.state['clock']+600 if code=='8' else None)
        if code=='1':home=self.station(v['station']);v.update(lat=home['lat'],lon=home['lon'])
        self.log(f'{v["callsign"]}, Statusmeldung {STATUS_LABELS[v["status"]]}.')

    def recommendation(self,j):
        from aao import recommend
        return recommend(self,j)

    def rule(self,code):
        from aao import code_rule
        return next((r for r in self.state['rules'] if r['code']==code),None) or code_rule(code)

    def edit_job(self,data):
        j=self.get('jobs',data['job'])
        if j['status']!='new' or j['vehicles']:raise ValueError('Einsatzdaten nur vor der ersten Alarmierung ändern.')
        rule=self.rule(data.get('code',j.get('code')))
        if rule and rule['kind']!=j['kind']:rule=None
        if not rule:raise ValueError('Passendes Übungsstichwort wählen.')
        additional=str(data.get('additional',j.get('additional',''))).strip()
        if len(additional)>500:raise ValueError('Zusatztext maximal 500 Zeichen.')
        if j['kind']=='transport' and 'due' in data:
            due=float(data['due'])
            if not __import__('math').isfinite(due) or due<0 or due%1800:raise ValueError('Abholzeit muss auf :00 oder :30 liegen.')
            j['due']=due
        j.update(code=rule['code'],title=rule['title'],priority=rule['priority'],needs=rule['needs'][:],category=rule.get('category'),signal=bool(data.get('signal',rule['signal'])),additional=additional,fire=bool(data.get('fire',False)),police=bool(data.get('police',False)),secondary_unavailable=bool(data.get('secondary_unavailable',False)))
        j['code_confirmed']=True
        if j['code']=='RD-9E1':j.update(needs=['RTW-C','NEF'],police=True)
        self.ensure_patient_condition(j,replace=not j.get('vehicles'))
        for name in ('fire','police'):
            if j[name]:self.log(('Feuerwehr' if name=='fire' else 'Polizei')+f': simulierte Unterstützungsanforderung zu Einsatz {j["id"]}.','System')

    def create_job(self,data):
        kind=data.get('kind','emergency');code=data.get('code','')
        if not self.rule(code) or self.rule(code)['kind']!=kind:raise ValueError('Ungültiges Übungsstichwort.')
        address=str(data.get('address','')).strip();lat=float(data.get('lat',0));lon=float(data.get('lon',0));due=float(data.get('due',__import__('math').ceil(self.state['clock']/1800)*1800 if kind=='transport' else self.state['clock']))
        if kind=='transport' and (not __import__('math').isfinite(due) or due<0 or due%1800):raise ValueError('Abholzeit muss auf :00 oder :30 liegen.')
        from locations import ADDRESSES
        address_point=next((a for a in ADDRESSES if a['address'].casefold()==address.casefold()),None)
        if address_point:lat,lon=address_point['lat'],address_point['lon']
        if not address or len(address)>200 or not -90<=lat<=90 or not -180<=lon<=180 or not __import__('math').isfinite(due) or due<0:raise ValueError('Einsatzort, Koordinaten und Abholzeit prüfen.')
        additional=str(data.get('additional','')).strip()
        if len(additional)>500:raise ValueError('Zusatztext maximal 500 Zeichen.')
        destination=data.get('destination')
        if kind=='transport':self.get('hospitals',destination)
        elif destination:raise ValueError('Notfallziel wird durch die Mannschaft gemeldet.')
        place=address.split(',')[-1].strip();place=__import__('re').sub(r'^\d{4}\s+','',place)
        j=self.new_job(kind,manual=True);j.update(address=address,place=place,lat=lat,lon=lon,due=due,caller='Vom Disponenten erstellter Auftrag',accepted=True,asked=True)
        if kind=='emergency':j.update(event_title=self.rule(code)['title'],detail=additional or 'Manuell angelegter Auftrag; Patientenzustand wird durch die Mannschaft gemeldet.',scene='Mannschaft vor Ort, Versorgung läuft.')
        j['address_point']=address_point.copy() if address_point else None;j['address_source']='OpenStreetMap' if address_point else 'Manuelle Adresse / Koordinaten'
        if address_point:j['place']=address_point['city']
        if kind=='transport':j['destination']=destination
        self.edit_job({**data,'job':j['id'],'code':code});return j

    def edit_rules(self,data):
        rows=data.get('rules')
        if not isinstance(rows,list) or not 1<=len(rows)<=40:raise ValueError('1–40 Übungs-AAO-Regeln erforderlich.')
        clean=[];seen=set()
        for r in rows:
            if not isinstance(r,dict):raise ValueError('Ungültige Regel.')
            code=str(r.get('code',''));title=str(r.get('title',''));needs=r.get('needs')
            if not code.startswith('SIM-') or len(code)>40 or code in seen or not 1<=len(title)<=80 or r.get('kind') not in ('emergency','transport') or r.get('priority') not in ('hoch','mittel','geplant') or not isinstance(needs,list) or not 1<=len(needs)<=4 or any(n not in ('RTW','NEF','KTW') for n in needs):raise ValueError('Code SIM-…, Titel, Art, Priorität und Ressourcenbedarf prüfen.')
            if r['kind']=='transport' and needs!=['KTW']:raise ValueError('Transportregel benötigt genau einen KTW.')
            seen.add(code);clean.append({'code':code,'title':title,'kind':r['kind'],'priority':r['priority'],'needs':needs,'signal':bool(r.get('signal'))})
        self.state['rules']=clean;self.log('Übungs-AAO aktualisiert.','System')
