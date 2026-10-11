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

GRAPHICS = [
    {'id':'van','name':'Rettungswagen · Kastenwagen','url':'/graphics/van.svg','author':'NÖ Dispo','source':'Eigene schematische SVG-Grafik','license':'Projektgrafik'},
    {'id':'box','name':'Rettungswagen · Kofferaufbau','url':'/graphics/box.svg','author':'NÖ Dispo','source':'Eigene schematische SVG-Grafik','license':'Projektgrafik'},
    {'id':'car','name':'Notarzteinsatzfahrzeug · SUV','url':'/graphics/car.svg','author':'NÖ Dispo','source':'Eigene schematische SVG-Grafik','license':'Projektgrafik'},
    {'id':'command','name':'Führungsfahrzeug · Bus','url':'/graphics/command.svg','author':'NÖ Dispo','source':'Eigene schematische SVG-Grafik','license':'Projektgrafik'},
]
DEFAULT_GRAPHIC = {'KTW':'van','KTW-B':'van','RTW':'van','RTW-C':'box','NEF':'car','BEL':'command'}

TYPES = ['KTW', 'KTW-B', 'RTW', 'RTW-C', 'NEF', 'BEL']
STATUSES = {'ready': 'Frei auf Wache', 'radio': 'Frei über Funk', 'out': 'Außer Dienst', 'assigned': 'Alarmiert', 'enroute': 'Zum Berufungsort', 'scene': 'Am Berufungsort', 'transport': 'Zum Zielort', 'hospital': 'Am Zielort', 'return': 'Rückfahrt', 'clean': 'Desinfektion'}
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

class Engine:
    def __init__(self, path, room_id='legacy'):
        self.lock=threading.RLock()
        self.db=sqlite3.connect(path, check_same_thread=False)
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS room_states (room_id TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.room_id=room_id
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
        self.save()

    def save(self):
        self.db.execute('INSERT OR REPLACE INTO room_states VALUES (?, ?)', (self.room_id,json.dumps(self.state,ensure_ascii=False)))
        self.db.commit()

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.state)

    def log(self, text, channel='Funk'):
        self.state['logs'].insert(0, {'time':self.state['clock'],'text':text,'channel':channel})
        self.state['logs']=self.state['logs'][:250]

    def station(self, id):
        return next(s for s in self.state['stations'] if s['id']==id)

    def get(self, collection, id):
        found=next((v for v in self.state[collection] if v['id']==id),None)
        if not found:
            raise ValueError('Datensatz nicht gefunden.')
        return found

    def in_shift(self,v):
        minute=int(self.state['clock']//60)%1440
        a,b=[int(x[:2])*60+int(x[3:]) for x in (v['start'],v['end'])]
        return v['staffed'] and (a==b or (a<=minute<b if a<b else minute>=a or minute<b))

    def new_job(self, kind):
        place, lat, lon=random.choice(PLACES)
        clock=self.state['clock']
        job={'id':uid(),'kind':kind,'place':place,'lat':lat+random.uniform(-.008,.008),'lon':lon+random.uniform(-.008,.008),'address':f'{place}, Beispieladresse {random.randint(1,40)}','created':clock,'vehicles':[],'owner':None,'status':'new','accepted':False,'asked':False,'destination':random.choice(self.state['hospitals'])['id']}
        if kind=='emergency':
            scenario=copy.deepcopy(random.choice(SCENARIOS)); job.update(scenario)
            job['due']=clock
            self.log('Neuer 144-Anruf wartet auf Annahme.','Telefon')
        elif kind=='transport':
            job.update({'title':random.choice(['Entlassung','Ambulanztermin','Dialysefahrt']), 'caller':'Elektronischer Transportauftrag', 'detail':random.choice(['Liegend, zwei Sanitäter erforderlich; keine akute Verschlechterung gemeldet.','Sitzend, Unterstützung beim Umsetzen erforderlich; keine akute Verschlechterung gemeldet.']), 'priority':'geplant','needs':['KTW'],'scene':'Patient übernommen; Transport gemäß Auftrag.','due':clock+random.choice([900,1800,2700]),'accepted':True,'asked':True})
            self.log(f'Neuer Transportauftrag: {job["title"]}, {place}.','Aufträge')
        else:
            raise ValueError('Unbekannte Auftragsart.')
        self.state['jobs'].append(job)
        return job

    def tick(self, real_seconds=1):
        with self.lock:
            if self.state['paused']: return
            self.state['clock']+=real_seconds*self.state['speed']
            now=self.state['clock']
            for v in self.state['vehicles']:
                if v['job']:
                    if v['phase_due'] is not None and now>=v['phase_due']: self.advance(v)
                elif self.in_shift(v) and v['status']=='out': v['status']='ready'
                elif not self.in_shift(v) and v['status'] in ('ready','radio'): v['status']='out'
            if now>=self.state['next_transport']:
                self.new_job('transport'); self.state['next_transport']=now+random.randint(600,1500)
            if now>=self.state['next_emergency']:
                self.new_job('emergency'); self.state['next_emergency']=now+random.randint(900,1800)
            if len(self.state['jobs'])>150:
                completed=[j for j in self.state['jobs'] if j['status']=='done']
                for j in completed[:len(self.state['jobs'])-150]: self.state['jobs'].remove(j)
            self.save()

    def advance(self,v):
        j=self.get('jobs',v['job']); now=self.state['clock']; home=self.station(v['station'])
        hospital=self.get('hospitals',j['destination'])
        if v['status']=='assigned':
            status='enroute'; seconds=max(120,distance(v,j)*1.25/45*3600)
            text=f'{v["callsign"]} verstanden, wir übernehmen und fahren nach {j["place"]}.'
        elif v['status']=='enroute':
            status='scene'; seconds=600 if j['kind']=='transport' else 900
            v['lat'],v['lon']=j['lat'],j['lon']; j['status']='scene'
            text=f'Hier {v["callsign"]}, am Berufungsort.'
            if v['type']!='NEF': text+=' '+j['scene']
        elif v['status']=='scene':
            if v['type']=='NEF':
                status='return'; seconds=max(120,distance(v,home)*1.25/45*3600)
                text=f'{v["callsign"]}, Versorgung beendet, ohne Begleitung wieder frei über Funk, Rückfahrt.'
            else:
                status='transport'; seconds=max(180,distance(v,hospital)*1.25/45*3600)
                text=f'{v["callsign"]}, Patient übernommen. Transport zum {hospital["name"]}.'
        elif v['status']=='transport':
            status='hospital'; seconds=600; v['lat'],v['lon']=hospital['lat'],hospital['lon']
            text=f'{v["callsign"]}, am Zielort, Patientenübergabe.'
        elif v['status']=='hospital':
            status='return'; seconds=max(120,distance(v,home)*1.25/45*3600)
            text=f'{v["callsign"]}, Übergabe abgeschlossen, Rückfahrt zur Dienststelle.'
        elif v['status']=='return':
            status='clean'; seconds=300; v['lat'],v['lon']=home['lat'],home['lon']
            text=f'{v["callsign"]}, auf Wache, Fahrzeug wird aufbereitet.'
        else:
            status='ready' if self.in_shift(v) else 'out'; seconds=None
            text=f'{v["callsign"]}, wieder einsatzbereit.' if status=='ready' else f'{v["callsign"]}, Dienstende.'
            v['job']=None
        v['status']=status; v['phase_due']=now+seconds if seconds is not None else None
        self.log(text)
        if all(self.get('vehicles',id)['job']!=j['id'] for id in j['vehicles']): j['status']='done'

    def dispatch(self,data):
        j=self.get('jobs',data['job']); ids=data.get('vehicles',[])
        if not j['accepted']: raise ValueError('Zuerst den Notruf annehmen.')
        if j['status']=='done' or not ids: raise ValueError('Offenen Auftrag und Fahrzeuge auswählen.')
        if len(ids)!=len(set(ids)): raise ValueError('Fahrzeug mehrfach ausgewählt.')
        selected=[self.get('vehicles',id) for id in ids]
        for v in selected:
            if v['job'] or v['status'] not in ('ready','radio') or not self.in_shift(v): raise ValueError(f'{v["callsign"]} ist nicht verfügbar.')
            if v['type']=='BEL': raise ValueError('BEL wird in dieser Version nicht für Patienteneinsätze disponiert.')
            if j['kind']=='emergency' and v['type'] not in ('RTW','RTW-C','NEF'): raise ValueError('Für diesen Notfall RTW/RTW-C bzw. NEF wählen.')
            if j['kind']=='transport' and v['type'] not in ('KTW','KTW-B','RTW','RTW-C'): raise ValueError('Für den Transport ein transportierendes Fahrzeug wählen.')
        destination=data.get('destination',j['destination']); self.get('hospitals',destination)
        if j['vehicles'] and destination!=j['destination']: raise ValueError('Transportziel nach Alarmierung in dieser Version nicht veränderbar.')
        j['destination']=destination
        for v in selected:
            v.update(status='assigned',job=j['id'],phase_due=self.state['clock']+30)
            j['vehicles'].append(v['id'])
            self.log(f'Leitstelle an {v["callsign"]}: {j["title"]}, {j["address"]}. '+('Mit Sondersignal.' if j['priority']=='hoch' else 'Ohne Sondersignal.'))
        j['status']='assigned'
        return j

    def command(self, action, data):
        with self.lock:
            actor=data.get('_actor')
            if actor and action in ('accept','ask','dispatch'):
                j=self.get('jobs',data.get('job') if action=='dispatch' else data.get('id'))
                if j.get('owner') and j['owner']!=actor['id']:
                    raise ValueError('Dieser Einsatz wird bereits von einem anderen Disponenten betreut.')
                # Claim only after a successful operation below.
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
            elif action=='generate': self.new_job(data.get('kind','emergency'))
            elif action=='accept':
                j=self.get('jobs',data['id'])
                if j['accepted']: raise ValueError('Anruf bereits angenommen.')
                j['accepted']=True; self.log('144 Notruf, wo genau ist der Notfall? '+j['caller'],'Telefon')
            elif action=='ask':
                j=self.get('jobs',data['id'])
                if not j['accepted']: raise ValueError('Anruf zuerst annehmen.')
                if not j['asked']: self.log('Abfrage: Bewusstsein, Atmung und nähere Umstände. '+j['detail'],'Telefon')
                j['asked']=True
            elif action=='dispatch': self.dispatch(data)
            elif action=='vehicle': self.edit_vehicle(data)
            elif action=='station': self.edit_station(data)
            elif action=='delete_vehicle':
                v=self.get('vehicles',data['id'])
                if v['job']: raise ValueError('Fahrzeug ist im Einsatz.')
                self.state['vehicles'].remove(v)
            elif action=='import':
                if any(v['job'] for v in self.state['vehicles']): raise ValueError('Import erst nach Abschluss aller Einsätze möglich.')
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
                vehicles=copy.deepcopy(self.state['vehicles']); stations=self.state['stations']; graphics=self.state['graphics']
                self.state=seed(); self.state['graphics']=graphics; self.state['chat']=[]; self.state['stations']=stations; self.state['vehicles']=vehicles
                for v in vehicles:
                    s=self.station(v['station']); v.update(job=None,phase_due=None,status='ready' if self.in_shift(v) else 'out',lat=s['lat'],lon=s['lon'])
            else: raise ValueError('Unbekannte Aktion.')
            if actor and action in ('accept','ask','dispatch'): j['owner']=actor['id']
            self.save()
            return self.snapshot()

    def edit_station(self,d):
        name=str(d.get('name','')).strip(); zone=str(d.get('zone','')).strip()
        lat=float(d.get('lat',0)); lon=float(d.get('lon',0))
        if not name or len(name)>100 or not zone or not -90<=lat<=90 or not -180<=lon<=180: raise ValueError('Name, Zone und gültige Koordinaten erforderlich.')
        existing=next((s for s in self.state['stations'] if s['id']==d.get('id')),None)
        record_id=existing['id'] if existing else str(d.get('id') or uid())
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',record_id): raise ValueError('Ungültige Dienststellen-ID.')
        s={'id':record_id,'name':name,'zone':zone,'lat':lat,'lon':lon}
        if existing: existing.update(s)
        else: self.state['stations'].append(s)
        for v in self.state['vehicles']:
            if v['station']==s['id'] and not v['job']: v.update(lat=lat,lon=lon)

    def edit_vehicle(self,d):
        call=str(d.get('callsign','')).strip(); typ=d.get('type'); station=d.get('station')
        if not call or len(call)>40 or typ not in TYPES: raise ValueError('Kennung und Fahrzeugtyp prüfen.')
        home=self.station(station)
        existing=next((v for v in self.state['vehicles'] if v['id']==d.get('id')),None)
        if existing and existing['job']: raise ValueError('Fahrzeug im Einsatz kann nicht bearbeitet werden.')
        if any(v['callsign']==call and v is not existing for v in self.state['vehicles']): raise ValueError('Kennung bereits vorhanden.')
        start=d.get('start','00:00'); end=d.get('end','00:00')
        for time in (start,end):
            try: dt.datetime.strptime(time,'%H:%M')
            except (ValueError,TypeError): raise ValueError('Dienstzeiten als HH:MM eingeben.')
        record_id=existing['id'] if existing else str(d.get('id') or uid())
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',record_id): raise ValueError('Ungültige Fahrzeug-ID.')
        graphic=d.get('graphic',existing.get('graphic') if existing else DEFAULT_GRAPHIC[typ])
        if graphic not in {g['id'] for g in self.state['graphics']}: raise ValueError('Unbekannte Fahrzeuggrafik.')
        v={'graphic':graphic,'id':record_id,'callsign':call,'type':typ,'station':station,'start':start,'end':end,'staffed':bool(d.get('staffed',True)),'status':'ready','lat':home['lat'],'lon':home['lon'],'job':None,'phase_due':None,'source':str(d.get('source','Manuell gepflegt'))[:300]}
        v['status']='ready' if self.in_shift(v) else 'out'
        if existing: existing.update(v)
        else: self.state['vehicles'].append(v)
