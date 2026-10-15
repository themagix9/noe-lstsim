"""Ministry hospital/site directory, with source metadata and conservative local targets."""
import copy
import json
import math
from pathlib import Path

DIRECTORY=json.loads((Path(__file__).parent/'data'/'hospitals-at.json').read_text())
ALIASES={'K316.1':'kh-hainburg','K380.1':'kh-moedling','K956.1':'kh-donaustadt','K901.1':'kh-akh-ecpr'}

def located(h):
    return isinstance(h.get('lat'),(int,float)) and isinstance(h.get('lon'),(int,float)) and math.isfinite(h['lat']) and math.isfinite(h['lon'])

def upgrade_hospitals(engine):
    from locations import HOSPITALS
    if engine.state.get('hospital_directory_version')==1:return
    existing={h['id']:h for h in engine.state['hospitals']}
    for source in DIRECTORY['hospitals']:
        record=copy.deepcopy(source);record['id']=ALIASES.get(record['registry_id'],record['id'])
        if record['id'] in HOSPITALS:record.update(HOSPITALS[record['id']]);record['helipad']=True
        if record['id']=='kh-akh-ecpr':record.update(ecpr=True,emergency=True,region='Wien')
        if record['id'] not in existing:engine.state['hospitals'].append(record)
        else:existing[record['id']].update(record)
    engine.state['hospital_directory_version']=1

def nearby(engine,point,region=None,emergency=False):
    from engine import distance
    items=[h for h in engine.state['hospitals'] if located(h) and not h.get('ecpr') and (region is None or h['region']==region) and (not emergency or h.get('emergency',True))]
    return sorted(items,key=lambda h:distance(point,h))

def destination(engine,j):
    return j.get('transport_destination') or engine.get('hospitals',j['destination'])

def edit_hospital(engine,data):
    h=engine.get('hospitals',data['id'])
    if any(j['status']!='done' and h['id'] in (j.get('destination'),j.get('requested_destination'),j.get('origin_hospital')) for j in engine.state['jobs']):raise ValueError('Krankenhaus wird in einem laufenden Auftrag verwendet.')
    try:lat,lon=float(data['lat']),float(data['lon'])
    except (KeyError,TypeError,ValueError):raise ValueError('Gültige Kartenposition eingeben.')
    if not math.isfinite(lat) or not math.isfinite(lon) or not 46<lat<50 or not 9<lon<18:raise ValueError('Kartenposition in Österreich prüfen.')
    h.update(lat=lat,lon=lon,coordinate_status='Manuell im Simulator bestätigt',coordinate_source='Sitzungsleiter',helipad=bool(data.get('helipad',h['helipad'])),emergency=bool(data.get('emergency',h['emergency'])))

def plan_transport(engine,j):
    import random
    from locations import ADDRESSES
    vienna=nearby(engine,j,'Wien',True)[:6]
    if not vienna:return
    route=random.choice(['local','local','noe-to-vienna','vienna-to-noe','hospital-transfer'])
    if route=='noe-to-vienna':
        h=random.choice(vienna);j.update(destination=h['id'],transport_direction='NÖ → Wien')
    elif route in ('vienna-to-noe','hospital-transfer'):
        origin=random.choice(vienna);j.update(address=origin['address'],place=origin.get('city','Wien'),lat=origin['lat'],lon=origin['lon'],address_source=origin['address_source'],origin_hospital=origin['id'],transport_direction='Wien → NÖ',address_point=None)
        if route=='vienna-to-noe':
            home=random.choice(ADDRESSES);target={'id':'home-'+j['id'],'name':'Wohnadresse · '+home['city'],'address':home['address'],'lat':home['lat'],'lon':home['lon'],'region':'NÖ'}
            j.update(destination=target['id'],transport_destination=target,title='Entlassung',scene='Patient übernommen; Heimtransport laut elektronischem Auftrag.')
        else:
            h=random.choice(nearby(engine,j,'NÖ',True)[:5]);j.update(destination=h['id'],title='Ambulanztermin')
    else:j['transport_direction']='NÖ · regional'


def spoken_name(h):
    """Brief operational names; retain registry labels in the hospital directory."""
    import re
    known={'kh-akh-ecpr':'AKH Wien','kh-moedling':'Klinik Mödling','kh-hainburg':'Klinik Hainburg','kh-donaustadt':'Klinik Donaustadt'}
    if h.get('id') in known:return known[h['id']]
    name=h.get('name','Krankenhaus')
    if h.get('registry_id')=='K380.2':return 'Klinik Baden'
    suffix=re.search(r' / ([^(·/]+)',name)
    if 'Baden-Mödling' in name and ('Baden' in (suffix[1] if suffix else h.get('city',''))):return 'Klinik Baden'
    short=(suffix[1] if suffix else name).split(' · ')[0].strip()
    short=re.sub(r'\s*\([^)]*\)','',short)
    short=re.sub(r'^(?:Landesklinikum|Universitätsklinikum|Landeskrankenhaus|LKH)\s+','Klinik ',short)
    if suffix and not re.match(r'Klinik|AKH|Krankenhaus|Spital',short):short='Klinik '+short
    return short.strip()
