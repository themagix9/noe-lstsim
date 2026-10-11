"""User-confirmed Schwechat fleet, 11 October 2026. Not a live roster."""
import copy
import datetime as dt
from zoneinfo import ZoneInfo
SOURCE='Nutzerbestätigung 11.10.2026; Bodendienstzeiten noch unbestätigt (24h Übungsannahme)'
STATIONS=[
 {'id':'nef-baden','name':'NEF Baden · Stützpunktlage prüfen','lat':48.002,'lon':16.246,'address':'Baden · ungeprüfter Übungsstartpunkt','external':True},
 {'id':'nef-moedling','name':'NEF Mödling · Stützpunktlage prüfen','lat':48.087,'lon':16.286,'address':'Mödling · ungeprüfter Übungsstartpunkt','external':True},
 {'id':'schwechat','name':'RK Schwechat','lat':48.1384,'lon':16.4802,'address':'Bruck-Hainburger Straße 27, 2320 Schwechat'},
 {'id':'goetzendorf','name':'RK Götzendorf','lat':48.0133,'lon':16.5866,'address':'Dr. Heudrich Gasse 6, 2434 Götzendorf'},
 {'id':'himberg','name':'RK Himberg','lat':48.0835,'lon':16.4372,'address':'Wiener Straße 9, 2325 Himberg'},
 {'id':'leopoldsdorf','name':'RK Leopoldsdorf','lat':48.1124,'lon':16.4035,'address':'Achauerstraße 43, 2333 Leopoldsdorf'},
 {'id':'fr-fischamend','name':'First Responder Fischamend','lat':48.116,'lon':16.612,'address':'Getreideplatz, 2401 Fischamend'},
 {'id':'c3','name':'Christophorus 3 · Wiener Neustadt','lat':47.843,'lon':16.260,'address':'Viktor-Lang-Straße 4, Flugplatz Ost, Wiener Neustadt','external':True},
 {'id':'c9','name':'Christophorus 9 · Wien-Erdberg','lat':48.1844,'lon':16.4136,'address':'Baumgasse 129, 1030 Wien','external':True},
]
ROWS=[('52/099','NEF','nef-baden'),('64/099','NEF','nef-moedling'),('77/001','RTW-C','schwechat'),('77/002','RTW','schwechat'),('77/004','RTW','schwechat')]+[(f'77/{n:03}','KTW','schwechat') for n in (3,5,7,8)]+[(f'77/{n:03}','RTW','schwechat') for n in (11,15)]+[(f'77/{n:03}','KTW','schwechat') for n in (12,13,16,31,32)]+[('77/020','BKTW','schwechat'),('77/030','RTW-C','goetzendorf'),('77/006','RTW','goetzendorf'),('77/060','RTW','leopoldsdorf'),('77/050','RTW','himberg'),('C3','NAH','c3'),('C9','NAH','c9')]+[(f'FR-SCH-{n:02}','FR','schwechat') for n in range(1,11)]+[('FR-FISCHAMEND-POOL','FR','fr-fischamend')]

def defaults(call,typ,station):
    return {'callsign':call,'type':typ,'station':station,'start':'00:00','end':'00:00','staffed':call!='FR-FISCHAMEND-POOL','nfs':typ=='RTW-C','rtwc_capable':call in ('77/001','77/002','77/004','77/030') or typ=='RTW-C','rtwc_fixed':call=='77/030','daylight':typ=='NAH','organization':'ÖAMTC' if typ=='NAH' else 'FR Fischamend' if station=='fr-fischamend' else 'RK','source':SOURCE if typ not in ('NAH','FR') else 'C3/C9: ÖAMTC Standorte und Tageslichtdienst; FR: fiktive Übungskennungen, Anzahl Schwechat laut Nutzer, Fischamend Anzahl offen','turnout':180 if typ=='NAH' else 60,'flight_speed':220 if typ=='NAH' else 0,'graphic':'helicopter' if typ=='NAH' else 'responder' if typ=='FR' else 'car' if typ=='NEF' else 'box' if typ=='RTW-C' else 'van'}

def upgrade(engine):
    state=engine.state
    state.setdefault('start_date',dt.datetime.now(ZoneInfo('Europe/Vienna')).date().isoformat())
    if state.get('fleet_version',0)>=2:
        upgrade_addresses(state);return
    from engine import uid
    for item in STATIONS:
        existing=next((s for s in state['stations'] if s['id']==item['id']),None)
        if not existing:state['stations'].append({**copy.deepcopy(item),'zone':'Bruck/Leitha','dispo':'05','source':'Öffentliche Betreiberadressen; Kartenkoordinaten angenähert','external':item.get('external',False)})
        elif item['id']=='schwechat':
            existing.setdefault('address',item['address']);existing.setdefault('source','Koordinaten aus älterem Übungsbestand')
    upgrade_addresses(state)
    pending=False
    for call,typ,station in ROWS:
        v=next((v for v in state['vehicles'] if v['callsign']==call),None)
        if v and not v.get('source','').startswith('Kennung/Typ: Nutzerfoto'):continue
        if v and (v.get('job') or v.get('reservation')):pending=True;continue
        data=defaults(call,typ,station);home=engine.station(station)
        data.update(lat=home['lat'],lon=home['lon'],job=None,phase_due=None,reservation=None,alarm_from='ready',ack_deadline=None,manual_out=False,leg=None)
        if v:v.update(data)
        else:v={'id':uid(),**data};state['vehicles'].append(v)
        v['status']='ready' if engine.in_shift(v) else 'out'
    if not pending:state['fleet_version']=2

def upgrade_addresses(state):
    if not state.get('address_version'):
        base='https://www.roteskreuz.at/niederoesterreich/'
        verified={
            'schwechat':('Bruck-Hainburger Straße 27, 2320 Schwechat',base+'wer-wir-sind-der-landesverband-noe/bezirksstellen'),
            'goetzendorf':('Dr. Heudrich Gasse 6, 2434 Götzendorf',base+'schwechat/kontakte/bezirksstelle/rotes-kreuz-goetzendorf'),
            'himberg':('Wiener Straße 9, 2325 Himberg',base+'schwechat/kontakte/bezirksstelle/rotes-kreuz-himberg'),
            'leopoldsdorf':('Achauerstraße 43, 2333 Leopoldsdorf',base+'schwechat/kontakte/bezirksstelle/rotes-kreuz-leopoldsdorf'),
            'bruck':('Höfleiner Straße 18, 2460 Bruck an der Leitha',base+'bruck-an-der-leitha/kontakte/bezirksstelle'),
            'hainburg':('Rot-Kreuz-Straße 14, 2410 Hainburg an der Donau',base+'wer-wir-sind-der-landesverband-noe/bezirksstellen')}
        for station in state['stations']:
            if station['id'] in verified and not station.get('source','').startswith('Manuell'):
                address,url=verified[station['id']]
                station.update(address=address,address_source=url,address_checked='2026-10-11',coordinate_accuracy='Angenäherter Kartenpunkt; noch nicht gebäudegenau verifiziert')
        if all(any(s['id']==id for s in state['stations']) for id in verified):state['address_version']=1

class Fleet:
    def configure_rtwc(self,data):
        v=self.get('vehicles',data['vehicle']);station=self.station(v['station'])
        if not v.get('rtwc_capable'):raise ValueError('Dieses Fahrzeug ist nicht RTW-C-fähig.')
        group=[u for u in self.state['vehicles'] if u['station']==station['id'] and u['type']=='RTW-C' and u['id']!=v['id']]
        if v.get('job') or v.get('reservation') or any(u.get('job') or u.get('reservation') or u.get('rtwc_fixed') for u in group):raise ValueError('RTW-C-Wechsel nur bei freien, nicht reservierten Fahrzeugen; feste Zuordnung bleibt geschützt.')
        for u in group:u['type']='RTW';u['graphic']='van'
        v.update(type='RTW-C',nfs=True,graphic='box')
        self.log(f'{station["name"]}: {v["callsign"]} als RTW-C besetzt, mindestens ein NFS bestätigt.','System')
