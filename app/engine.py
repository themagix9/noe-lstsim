"""Independent dispatch simulation. No live service or operational data connection."""
import copy
import datetime as dt
import json
import math
import random
import re
import sqlite3
import threading
import uuid
from operations import Operations, STATUS_LABELS, JOB_ACTIONS
from fleet import Fleet, upgrade
from daylight import window
from staffing import Staffing
from air_ops import AirOps
from routing import router_for
from radio import Radio
from patients import Patients
from calls import Calls
from locations import ADDRESSES,ADDRESS_CITIES,upgrade_locations

GRAPHICS = [
    {'id':'helicopter','name':'Notarzthubschrauber · schematisch','url':'/graphics/helicopter.svg','author':'NÖ Dispo','source':'Eigene schematische SVG-Grafik','license':'Projektgrafik'},
    {'id':'responder','name':'First Responder · schematisch','url':'/graphics/responder.svg','author':'NÖ Dispo','source':'Eigene schematische SVG-Grafik','license':'Projektgrafik'},
    {'id':'van','name':'Rettungswagen · Kastenwagen','url':'/graphics/van.svg','author':'NÖ Dispo','source':'Eigene schematische SVG-Grafik','license':'Projektgrafik'},
    {'id':'box','name':'Rettungswagen · Kofferaufbau','url':'/graphics/box.svg','author':'NÖ Dispo','source':'Eigene schematische SVG-Grafik','license':'Projektgrafik'},
    {'id':'car','name':'Notarzteinsatzfahrzeug · SUV','url':'/graphics/car.svg','author':'NÖ Dispo','source':'Eigene schematische SVG-Grafik','license':'Projektgrafik'},
    {'id':'command','name':'Führungsfahrzeug · Bus','url':'/graphics/command.svg','author':'NÖ Dispo','source':'Eigene schematische SVG-Grafik','license':'Projektgrafik'},
]
DEFAULT_GRAPHIC = {'KTW':'van','KTW-B':'van','RTW':'van','RTW-C':'box','NEF':'car','BEL':'command','BKTW':'van','FR':'responder','NAH':'helicopter'}

TYPES = ['KTW', 'KTW-B', 'BKTW', 'RTW', 'RTW-C', 'NEF', 'NAH', 'FR', 'BEL']
STATUSES = STATUS_LABELS
SCENARIOS = [
    {'title': 'Atemnot', 'caller': 'Mein Vater bekommt schlecht Luft. Er sitzt am Sofa und kann kaum einen ganzen Satz sagen.', 'detail': 'Männlich, 68 Jahre, wach, Atmung vorhanden, zunehmende Atemnot seit etwa 20 Minuten.', 'priority': 'hoch', 'needs': ['RTW', 'NEF'], 'scene': 'Patient wach, ausgeprägte Atemnot. Notarzt erforderlich; Transport nach Versorgung.'},
    {'title': 'Sturz in Wohnung', 'caller': 'Meine Mutter ist im Badezimmer gestürzt. Sie liegt noch am Boden und kommt nicht alleine hoch.', 'detail': 'Weiblich, 79 Jahre, ansprechbar, normale Atmung. Schmerzen im Hüftbereich, keine sichtbare Blutung.', 'priority': 'mittel', 'needs': ['RTW'], 'scene': 'Patientin ansprechbar, Schmerzen im Hüftbereich. Liegendtransport zur Abklärung.'},
    {'title': 'Bewusstlose Person', 'caller': 'Da liegt jemand bei der Bushaltestelle. Er reagiert nicht, wenn ich ihn anspreche.', 'detail': 'Erwachsene Person, keine Reaktion. Atmung lässt sich telefonisch nicht sicher beurteilen.', 'priority': 'hoch', 'needs': ['RTW', 'NEF'], 'scene': 'Patient bewusstlos, Atmung vorhanden. Notarzt nachgefordert bzw. erwartet.'},
    {'title': 'Verkehrsunfall', 'caller': 'Hier sind zwei Autos zusammengestoßen. Ein Fahrer hat Schmerzen, er ist aber schon ausgestiegen.', 'detail': 'Eine verletzte Person, ansprechbar, normale Atmung. Unfallstelle laut Anrufer abgesichert.', 'priority': 'mittel', 'needs': ['RTW'], 'scene': 'Eine verletzte Person, kreislaufstabil. Transport zur weiteren Abklärung.'},
]
PLACES = [('Schwechat', 48.141, 16.478), ('Himberg', 48.082, 16.437), ('Bruck/Leitha', 48.023, 16.779), ('Hainburg/Donau', 48.147, 16.945), ('Götzendorf/Leitha', 48.017, 16.582), ('Maria Lanzendorf', 48.100, 16.419)]
HOSPITALS = [{'id':'kh-hainburg','name':'Landesklinikum Hainburg','lat':48.144,'lon':16.953}, {'id':'kh-moedling','name':'Landesklinikum Mödling','lat':48.087,'lon':16.286}, {'id':'kh-donaustadt','name':'Klinik Donaustadt','lat':48.220,'lon':16.462}]

def uid():
    return uuid.uuid4().hex[:12]

def distance(a, b):
    lat = math.radians((a['lat'] + b['lat']) / 2)
    return math.hypot((a['lat']-b['lat'])*111.2, (a['lon']-b['lon'])*111.2*math.cos(lat))

def seed():
    stations = [{'id':'bruck','name':'RK Bruck/Leitha','zone':'Bruck/Leitha','lat':48.023,'lon':16.779}, {'id':'hainburg','name':'RK Hainburg','zone':'Bruck/Leitha','lat':48.147,'lon':16.945}, {'id':'schwechat','name':'RK Schwechat','zone':'Bruck/Leitha','lat':48.141,'lon':16.478}]
    rows = [('53/002','RTW-C','bruck'),('53/022','BEL','bruck'),('53/601','RTW-C','hainburg'),('53/602','RTW','hainburg'),('53/699','NEF','hainburg'),('77/001','RTW-C','schwechat'),('77/002','RTW','schwechat'),('77/004','RTW','schwechat'),('77/006','RTW','schwechat'),('77/015','KTW','schwechat'),('77/030','RTW-C','schwechat'),('77/060','RTW','schwechat'),('77/099','NEF','schwechat'),('77/900','BEL','schwechat')]
    vehicles=[]
    for call, typ, station in rows:
        s=next(x for x in stations if x['id']==station)
        vehicles.append({'id':uid(),'callsign':call,'type':typ,'station':station,'start':'00:00','end':'00:00','staffed':True,'status':'ready','lat':s['lat'],'lon':s['lon'],'job':None,'phase_due':None,'source':'Kennung/Typ: Nutzerfoto 11.10.2026; Stammdienststelle und Dienstzeit: ungeprüfte Startkonfiguration'})
    return {'clock':8*3600,'speed':1,'paused':True,'stations':stations,'vehicles':vehicles,'jobs':[],'logs':[],'hospitals':HOSPITALS,'next_emergency':8*3600+180,'next_transport':8*3600+60}

class Engine(Operations, Fleet, Staffing, AirOps, Radio, Patients, Calls):
    def __init__(self, path, room_id='legacy'):
        self.lock=threading.RLock()
        self.db=sqlite3.connect(path, check_same_thread=False)
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS room_states (room_id TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.room_id=room_id
        self.router=router_for(path)
        row=self.db.execute('SELECT value FROM room_states WHERE room_id=?',(room_id,)).fetchone()
        # Preserve the v0.1 state on migration; first host can explicitly adopt it.
        if not row and room_id=='legacy':
            old=self.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='state'").fetchone()
            row=self.db.execute('SELECT value FROM state WHERE id=1').fetchone() if old else None
        self.state=json.loads(row[0]) if row else seed()
        self.state.setdefault('graphics',copy.deepcopy(GRAPHICS))
        self.state.setdefault('chat',[])
        for v in self.state['vehicles']: v.setdefault('graphic',DEFAULT_GRAPHIC[v['type']])
        for j in self.state['jobs']: j.setdefault('owner',None)
        self.migrate_operations()
        for j in self.state['jobs']:self.ensure_patient_condition(j)
        for g in GRAPHICS:
            if not any(item['id']==g['id'] for item in self.state['graphics']):self.state['graphics'].append(copy.deepcopy(g))
        upgrade(self)
        self.upgrade_staffing()
        upgrade_locations(self)
        self.save()

    def save(self):
        self.db.execute('INSERT OR REPLACE INTO room_states VALUES (?, ?)', (self.room_id,json.dumps(self.state,ensure_ascii=False)))
        self.db.commit()

    def snapshot(self):
        with self.lock:
            result=copy.deepcopy(self.state)
            for v in result['vehicles']:
                v['in_shift']=self.in_shift(v);v['crew_shift']='Tagmannschaft 06–18' if 21600<=self.state['clock']%86400<64800 else 'Nachtmannschaft 18–06';v['capabilities']={'transport':v['type'] in ('KTW','KTW-B','BKTW','RTW','RTW-C','NAH'),'emergency':v['type'] in ('KTW','RTW','RTW-C'),'notarzt':v['type'] in ('NEF','NAH'),'rtwc':bool(v.get('rtwc_capable'))}
                if v.get('daylight'):v['duty_window']=list(self.daylight_window(v))
            for j in result['jobs']:
                if j['accepted'] and j['status']!='done':
                    origins=[v for v in self.state['vehicles'] if v['type']!='NAH' and self.sendable(v,j)]
                    estimates=self.router.estimates(origins,j)
                    for v in self.state['vehicles']:
                        if v['type']=='NAH' and self.sendable(v,j):estimates[v['id']]={'status':'ready','seconds':distance(v,j)/v.get('flight_speed',220)*3600,'distance_m':distance(v,j)*1000,'source':'Flugzeit · Luftlinie'}
                        eta=estimates.get(v['id'])
                        if eta and eta['status']=='ready':
                            eta['seconds']+=float(v.get('turnout',60))+max(0,(v.get('phase_due') or 0)-self.state['clock'] if v['status']=='hospital' else 0)
                            eta['arrival']=self.state['clock']+eta['seconds']
                    j['resource_eta']=estimates;j['aao']=self.recommendation(j)
            for v in result['vehicles']:
                v['eta_seconds']=max(0,v['phase_due']-self.state['clock']) if v.get('leg') and v.get('phase_due') else None
            result['routing']={'enabled':self.router.enabled,'source':'OSRM · OpenStreetMap','mode':'external' if self.router.url.startswith('https://') else 'self-hosted'}
            return result

    def log(self, text, channel='Funk'):
        if channel=='Funk' and re.search(r'Status\s*(?:\d|meldung)',text,re.I):channel='Status'
        self.state['logs'].insert(0, {'time':self.state['clock'],'text':text,'channel':channel})
        self.state['logs']=self.state['logs'][:250]

    def station(self, id):
        return next(s for s in self.state['stations'] if s['id']==id)

    def get(self, collection, id):
        found=next((v for v in self.state[collection] if v['id']==id),None)
        if not found:
            raise ValueError('Datensatz nicht gefunden.')
        return found

    def daylight_window(self,v):
        date=dt.date.fromisoformat(self.state['start_date'])+dt.timedelta(days=int(self.state['clock']//86400))
        home=self.station(v['station']);return window(date.isoformat(),home['lat'],home['lon'])

    def in_shift(self,v):
        if v['type']=='FR':return v['staffed']
        if v.get('duty_managed') and not v.get('daylight'):return self.managed_shift(v)
        if v.get('daylight'):
            a,b=self.daylight_window(v);return v['staffed'] and a<=self.state['clock']//60%1440<b
        minute=int(self.state['clock']//60)%1440
        a,b=[int(x[:2])*60+int(x[3:]) for x in (v['start'],v['end'])]
        return v['staffed'] and (a==b or (a<=minute<b if a<b else minute>=a or minute<b))

    def new_job(self, kind, manual=False):
        city=random.choice(ADDRESS_CITIES)
        address_point=random.choice([a for a in ADDRESSES if a['city']==city])
        place,lat,lon=address_point['city'],address_point['lat'],address_point['lon']
        clock=self.state['clock']
        job={'id':uid(),'kind':kind,'place':place,'lat':lat,'lon':lon,'address':address_point['address'],'address_point':address_point.copy(),'address_source':'OpenStreetMap','created':clock,'vehicles':[],'owner':None,'status':'new','accepted':False,'asked':False,'destination':random.choice([h for h in self.state['hospitals'] if h['region']=='NÖ'])['id'] if kind=='transport' else None,'reserved':None,'bed_state':'none','case_number':None,'requested_destination':None,'bed_due':None}
        if kind=='emergency':
            scenario=copy.deepcopy(random.choice(SCENARIOS)); job.update(scenario)
            job['due']=clock
            if not manual:self.log('Neuer 144-Anruf wartet auf Annahme.','Telefon')
        elif kind=='transport':
            job.update({'title':random.choice(['Entlassung','Ambulanztermin','Dialysefahrt']), 'caller':'Elektronischer Transportauftrag', 'detail':random.choice(['Liegend, zwei Sanitäter erforderlich; keine akute Verschlechterung gemeldet.','Sitzend, Unterstützung beim Umsetzen erforderlich; keine akute Verschlechterung gemeldet.']), 'priority':'geplant','needs':['KTW'],'scene':'Patient übernommen; Transport gemäß Auftrag.','due':clock+random.choice([900,1800,2700]),'accepted':True,'asked':True})
            self.log(f'Neuer Transportauftrag: {job["title"]}, {place}.','Aufträge')
            job['due']=math.ceil(job['due']/1800)*1800
        else:
            raise ValueError('Unbekannte Auftragsart.')
        code={'Atemnot':'RD-6D2','Sturz in Wohnung':'RD-17B1','Bewusstlose Person':'RD-31D3','Verkehrsunfall':'RD-29A1','Entlassung':random.choice(['KTR-95K2','KTR-95K3']),'Ambulanztermin':random.choice(['KTR-90K2','KTR-90K3']),'Dialysefahrt':random.choice(['KTR-93Y1','KTR-93Y2'])}.get(job['title'],'SIM-KT')
        rule=self.rule(code)
        job.update(code=code,category=rule.get('category') if rule else None,signal=rule['signal'] if rule else False,additional='',fire=False,police=False,organization='RK')
        job['event_title']=job['title']
        if rule:job.update(title=rule['title'],needs=rule['needs'][:],priority=rule['priority'])
        self.ensure_patient_condition(job)
        if kind=='emergency' and not manual:self.prepare_call(job)
        self.ensure_alarm_identity(job)
        self.state['jobs'].append(job)
        return job

    def tick(self, real_seconds=1):
        with self.lock:
            if self.state['paused']: return
            self.state['clock']+=real_seconds*self.state['speed']
            now=self.state['clock']
            period='Tagmannschaft 06–18' if 21600<=now%86400<64800 else 'Nachtmannschaft 18–06'
            if self.state.get('crew_period')!=period:self.state['crew_period']=period;self.log(f'Mannschaftswechsel: {period}. Laufende Einsätze werden beendet; Besetzung nach Nachtvorhaltung.','System')
            upgrade(self)
            self.upgrade_staffing()
            self.update_operations(now)
            self.update_air(now)
            self.update_patients(now)
            for v in self.state['vehicles']:
                if v['phase_due'] is not None and now>=v['phase_due']: self.advance(v)
                elif v['job']: pass
                elif self.in_shift(v) and v['status']=='out' and not v.get('manual_out'): v['status']=self.idle_status(v)
                elif not self.in_shift(v) and not v.get('leg') and v['status'] in ('ready','radio','fr_ready'): v['status']='out'
            auto_enabled=any(s.get('dispo')==self.state['setup']['dispo'] for s in self.state['stations']) and self.state['setup']['dispo']=='05'
            if auto_enabled and now>=self.state['next_transport']:
                self.new_job('transport'); self.state['next_transport']=now+random.randint(600,1500)
            if auto_enabled and now>=self.state['next_emergency']:
                self.new_job('emergency'); self.state['next_emergency']=now+random.randint(900,1800)
            if len(self.state['jobs'])>150:
                completed=[j for j in self.state['jobs'] if j['status']=='done']
                for j in completed[:len(self.state['jobs'])-150]: self.state['jobs'].remove(j)
            self.save()

    def command(self, action, data):
        with self.lock:
            actor=data.get('_actor')
            if actor and action in JOB_ACTIONS:
                j=self.get('jobs',data.get('job') if action not in ('accept','ask') else data.get('id'))
                if j.get('owner') and j['owner']!=actor['id']:
                    raise ValueError('Dieser Einsatz wird bereits von einem anderen Disponenten betreut.')
                # Claim only after a successful operation below.
            if actor and action=='vehicle_status':
                vehicle=self.get('vehicles',data.get('vehicle'))
                if vehicle['job']:
                    job=self.get('jobs',vehicle['job'])
                    if job.get('owner') and job['owner']!=actor['id']:raise ValueError('Einsatz wird von einem anderen Disponenten betreut.')
            if action=='claim':
                j=self.get('jobs',data['id'])
                if not actor: raise ValueError('Spieler benötigt.')
                if j['status']=='done': raise ValueError('Einsatz bereits abgeschlossen.')
                if j.get('owner') and j['owner']!=actor['id']: raise ValueError('Einsatz bereits übernommen.')
                j['owner']=actor['id']; self.log(f"{actor['name']} übernimmt Einsatz {j['id']}.",'System')
            elif action=='release':
                j=self.get('jobs',data['id'])
                if not actor or (j.get('owner')!=actor['id'] and not actor.get('host')): raise ValueError('Nur der Betreuer oder Sitzungsleiter kann den Einsatz freigeben.')
                j['owner']=None; self.log(f"{actor['name']} gibt Einsatz {j['id']} zur Übergabe frei.",'System')
            elif action=='chat':
                text=str(data.get('text','')).strip()
                if not actor or not text or len(text)>500: raise ValueError('Nachricht mit 1–500 Zeichen erforderlich.')
                self.state['chat'].append({'id':uid(),'time':self.state['clock'],'player':actor['id'],'name':actor['name'],'text':text})
                self.state['chat']=self.state['chat'][-100:]
            elif action=='control':
                speed=data.get('speed',self.state['speed'])
                if speed not in (1,5,15,60): raise ValueError('Ungültige Geschwindigkeit.')
                self.state['speed']=speed; self.state['paused']=bool(data.get('paused',self.state['paused']))
            elif action=='radio':self.radio_action(data)
            elif action=='radio_generate':
                j=self.get('jobs',data['job']);v=self.get('vehicles',data['vehicle'])
                self.raise_radio(j,v,data.get('kind','NEF'),data.get('reason'),bool(data.get('reason_initial')))
            elif action=='carrier':self.choose_carrier(data)
            elif action=='ask_cpr':self.ask_cpr(data)
            elif action=='rtwc':self.configure_rtwc(data)
            elif action=='generate':
                target=data.get('crew_target')
                if target:
                    if data.get('kind','emergency')!='emergency':raise ValueError('Übungsziel nur für Notruf-Szenarien.')
                    self.get('hospitals',target)
                generated=self.new_job(data.get('kind','emergency'))
                if target:generated['crew_target']=target
            elif action=='accept':
                j=self.get('jobs',data['id'])
                if j['accepted']: raise ValueError('Anruf bereits angenommen.')
                self.accept_call(j)
            elif action=='call_question':self.question_call(data)
            elif action=='call_finish':self.finish_call(data)
            elif action=='ask':
                j=self.get('jobs',data['id'])
                if not j['accepted']: raise ValueError('Anruf zuerst annehmen.')
                if not j['asked']: self.log('Abfrage: Bewusstsein, Atmung und nähere Umstände. '+j['detail'],'Telefon')
                j['asked']=True;j['asked_at']=self.state['clock']
            elif action=='dispatch': self.dispatch(data)
            elif action=='reserve': self.reserve(data)
            elif action=='unreserve': self.unreserve(data)
            elif action=='bed_request': self.request_bed(data)
            elif action=='send_case': self.send_case(data)
            elif action=='vehicle_status': self.vehicle_status(data)
            elif action=='edit_job': self.edit_job(data)
            elif action=='create_job':
                created=self.create_job(data)
                if actor:created['owner']=actor['id']
            elif action=='rules': self.edit_rules(data)
            elif action=='vehicle': self.edit_vehicle(data)
            elif action=='station': self.edit_station(data)
            elif action=='delete_vehicle':
                v=self.get('vehicles',data['id'])
                if v['job'] or v.get('reservation'): raise ValueError('Fahrzeug ist im Einsatz oder vordisponiert.')
                self.state['vehicles'].remove(v)
            elif action=='import':
                if any(v['job'] or v.get('reservation') for v in self.state['vehicles']): raise ValueError('Import erst nach Abschluss aller Einsätze möglich.')
                config=data.get('config',{})
                if not isinstance(config.get('stations'),list) or not isinstance(config.get('vehicles'),list): raise ValueError('Import benötigt stations und vehicles.')
                for collection in ('stations','vehicles'):
                    ids=[item.get('id') for item in config[collection] if isinstance(item,dict) and item.get('id')]
                    if len(ids)!=len(set(ids)): raise ValueError('Doppelte IDs im Import.')
                old=copy.deepcopy(self.state)
                try:
                    self.state['stations']=[]; self.state['vehicles']=[]
                    if not config['stations']: raise ValueError('Mindestens eine Dienststelle benötigt.')
                    for s in config['stations']: self.edit_station(s)
                    for v in config['vehicles']: self.edit_vehicle(v)
                except (ValueError,KeyError,TypeError,StopIteration):
                    self.state=old; raise ValueError('Ungültiger Import; bisherige Konfiguration bleibt erhalten.')
                self.log('Dienststellen- und Fahrzeugkonfiguration importiert.','System')
            elif action=='reset':
                incident_counter=self.state.get('incident_counter',0);location_version=self.state.get('location_version');vehicles=copy.deepcopy(self.state['vehicles']); stations=self.state['stations']; hospitals=self.state['hospitals'];graphics=self.state['graphics']; staffing_version=self.state.get('staffing_version');start_date=self.state['start_date'];fleet_version=self.state.get('fleet_version',0); rules=self.state['rules']; setup=self.state['setup']
                self.state=seed();self.state.update(incident_counter=incident_counter,location_version=location_version,start_date=start_date,fleet_version=fleet_version,staffing_version=staffing_version); self.state['rules']=rules; self.state['setup']=setup; self.state['graphics']=graphics; self.state['chat']=[]; self.state['stations']=stations;self.state['hospitals']=hospitals; self.state['vehicles']=vehicles
                for v in vehicles:
                    s=self.home(v); v.update(job=None,phase_due=None,status=self.idle_status(v),lat=s['lat'],lon=s['lon'],reservation=None,ack_deadline=None,manual_out=False,leg=None)
                self.migrate_operations()
            else: raise ValueError('Unbekannte Aktion.')
            if actor and action in JOB_ACTIONS: j['owner']=actor['id']
            self.save()
            return self.snapshot()

    def edit_station(self,d):
        name=str(d.get('name','')).strip(); zone=str(d.get('zone','')).strip()
        lat=float(d.get('lat',0)); lon=float(d.get('lon',0))
        if not name or len(name)>100 or not zone or not -90<=lat<=90 or not -180<=lon<=180: raise ValueError('Name, Zone und gültige Koordinaten erforderlich.')
        existing=next((s for s in self.state['stations'] if s['id']==d.get('id')),None)
        record_id=existing['id'] if existing else str(d.get('id') or uid())
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',record_id): raise ValueError('Ungültige Dienststellen-ID.')
        dispo=str(d.get('dispo',existing.get('dispo','05') if existing else '05'))
        if dispo not in ('01','02','03','04','05','06'):raise ValueError('Dispozone 01–06 wählen.')
        s={'id':record_id,'name':name,'zone':zone,'dispo':dispo,'lat':lat,'lon':lon,'external':bool(d.get('external',existing.get('external',False) if existing else False)),'address':str(d.get('address',existing.get('address','') if existing else ''))[:250],'source':str(d.get('source',existing.get('source','Manuell gepflegt') if existing else 'Manuell gepflegt'))[:500]}
        if existing: existing.update(s)
        else: self.state['stations'].append(s)
        for v in self.state['vehicles']:
            if v['station']==s['id'] and not v['job']: v.update(lat=lat,lon=lon)

    def edit_vehicle(self,d):
        call=str(d.get('callsign','')).strip(); typ=d.get('type'); station=d.get('station')
        if not call or len(call)>40 or typ not in TYPES: raise ValueError('Kennung und Fahrzeugtyp prüfen.')
        home=self.station(station)
        existing=next((v for v in self.state['vehicles'] if v['id']==d.get('id')),None)
        if existing and (existing['job'] or existing.get('reservation')): raise ValueError('Fahrzeug im Einsatz kann nicht bearbeitet werden.')
        if any(v['callsign']==call and v is not existing for v in self.state['vehicles']): raise ValueError('Kennung bereits vorhanden.')
        start=d.get('start','00:00'); end=d.get('end','00:00')
        for time in (start,end):
            try: dt.datetime.strptime(time,'%H:%M')
            except (ValueError,TypeError): raise ValueError('Dienstzeiten als HH:MM eingeben.')
        record_id=existing['id'] if existing else str(d.get('id') or uid())
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',record_id): raise ValueError('Ungültige Fahrzeug-ID.')
        graphic=d.get('graphic',existing.get('graphic') if existing else DEFAULT_GRAPHIC[typ])
        if graphic not in {g['id'] for g in self.state['graphics']}: raise ValueError('Unbekannte Fahrzeuggrafik.')
        turnout=float(d.get('turnout',existing.get('turnout',60) if existing else 60))
        organization=str(d.get('organization',existing.get('organization','RK') if existing else 'RK'))
        if not 0<=turnout<=1800 or organization not in ('RK','ASB','JUH','ÖAMTC','FR Fischamend','Sonstige'):raise ValueError('Ausrückzeit 0–1800 Sekunden und Organisation prüfen.')
        v={'nfs':bool(d.get('nfs',existing.get('nfs',False) if existing else False)),'turnout':turnout,'organization':organization,'graphic':graphic,'id':record_id,'callsign':call,'type':typ,'station':station,'start':start,'end':end,'staffed':bool(d.get('staffed',True)),'status':'ready','lat':home['lat'],'lon':home['lon'],'job':None,'phase_due':None,'source':str(d.get('source','Manuell gepflegt'))[:300],'reservation':None,'alarm_from':'ready','ack_deadline':None,'manual_out':False,'leg':None}
        v.update(rtwc_capable=bool(d.get('rtwc_capable',existing.get('rtwc_capable',False) if existing else typ=='RTW-C')),rtwc_fixed=call=='77/030' or bool(existing and existing.get('rtwc_fixed')),daylight=bool(d.get('daylight',existing.get('daylight',False) if existing else typ=='NAH')),flight_speed=220 if typ=='NAH' else 0)
        if typ=='RTW-C' and (not v['rtwc_capable'] or not v['nfs']):raise ValueError('RTW-C braucht Fahrzeugfähigkeit und bestätigte NFS-Besetzung.')
        if typ=='RTW-C' and any(u['station']==station and u['type']=='RTW-C' and u is not existing for u in self.state['vehicles']):raise ValueError('Pro Dienststelle ist nur ein RTW-C erlaubt. RTW-C-Besetzung wechseln verwenden.')
        if v['rtwc_fixed'] and (typ!='RTW-C' or station!='goetzendorf' or call!='77/030'):raise ValueError('77/030 bleibt RTW-C in Götzendorf.')
        for key in ('duty_managed','home_lat','home_lon','home_address'):
            if key in d:v[key]=d[key]
            elif existing and key in existing:v[key]=existing[key]
        v['status']=self.idle_status(v)
        if typ=='FR':
            origin=self.home(v);v.update(lat=origin['lat'],lon=origin['lon'])
        if existing: existing.update(v)
        else: self.state['vehicles'].append(v)
