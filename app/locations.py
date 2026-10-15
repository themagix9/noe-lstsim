"""Real OSM address points and public hospital contact addresses; patients are fictional."""
import json
import random
import hashlib
from pathlib import Path
ADDRESS_DATA=Path(__file__).parent/'data'
ADDRESS_INDEX=json.loads((ADDRESS_DATA/'addresses.json').read_text())
ADDRESSES=ADDRESS_INDEX.get('addresses',[])+[a for filename in ADDRESS_INDEX.get('address_files',[]) for a in json.loads((ADDRESS_DATA/filename).read_text())['addresses']]
ADDRESS_CITIES=sorted({a['city'] for a in ADDRESSES})
ADDRESS_BY_CITY={city:[a for a in ADDRESSES if a['city']==city] for city in ADDRESS_CITIES}
ADDRESS_POOL=hashlib.sha256('|'.join(ADDRESS_CITIES).encode()).hexdigest()

def choose_address(engine):
    bag=engine.state.get('address_rotation',[])
    if engine.state.get('address_pool')!=ADDRESS_POOL or not bag:
        bag=ADDRESS_CITIES[:];random.shuffle(bag)
        if len(bag)>1 and bag[-1]==engine.state.get('last_address_city'):bag[0],bag[-1]=bag[-1],bag[0]
    city=bag.pop();engine.state.update(address_pool=ADDRESS_POOL,address_rotation=bag,last_address_city=city)
    points=ADDRESS_BY_CITY[city];previous=engine.state.get('last_address_id')
    choices=[a for a in points if a['id']!=previous] or points
    result=random.choice(choices);engine.state['last_address_id']=result['id'];return result
HOSPITALS={
 'kh-hainburg':{'address':'Hofmeisterstraße 70, 2410 Hainburg an der Donau','lat':48.1432994,'lon':16.9580624,'address_source':'https://hainburg.lknoe.at/fuer-besucher/kontakt-und-anfahrt','coordinate_source':'Kartenmarker auf offizieller Betreiberseite'},
 'kh-moedling':{'address':'Sr. M. Restituta-Gasse 12, 2340 Mödling','lat':48.0885476,'lon':16.2977629,'address_source':'https://moedling.lknoe.at/fuer-besucher/kontakt-und-anfahrt','coordinate_source':'Kartenmarker auf offizieller Betreiberseite'},
 'kh-donaustadt':{'address':'Langobardenstraße 122, 1220 Wien','lat':48.219397,'lon':16.462914,'address_source':'https://klinik-donaustadt.gesundheitsverbund.at/anreise-und-parken/','coordinate_source':'Vom Nutzer bereitgestellte Kartenreferenz; kein verifizierter Rettungseingang'},
 'kh-akh-ecpr':{'address':'Währinger Gürtel 18–20, 1090 Wien','lat':48.22132,'lon':16.346206,'address_source':'https://gesundheitsverbund.at/kliniken/','coordinate_source':'Vom Nutzer bereitgestellte Kartenreferenz; Landeplatz separat noch zu verifizieren'}
}

def upgrade_locations(engine):
    state=engine.state
    upgrade_confirmed_stations(engine)
    if state.get('location_version'):return
    for h in state['hospitals']:
        if h['id'] in HOSPITALS:h.update(HOSPITALS[h['id']])
    # Public OSM Schwechat position and a few factual points from the user reference.
    coords={'schwechat':(48.1399658,16.4866308),'goetzendorf':(48.0127366,16.5800011),'himberg':(48.0844732,16.4376294),'hainburg':(48.1433613,16.9604027)}
    for station in state['stations']:
        if station['id'] in coords and not station.get('source','').startswith('Manuell'):
            station['lat'],station['lon']=coords[station['id']]
            station['coordinate_accuracy']='OSM-Dienststellenpunkt' if station['id']=='schwechat' else 'Nutzer-Kartenreferenz; Gebäudezugang noch nicht verifiziert'
            for v in state['vehicles']:
                if v['station']==station['id'] and v['type']!='FR' and v['status']=='ready' and not v.get('job'):v.update(lat=station['lat'],lon=station['lon'])
    state['location_version']=1


def upgrade_confirmed_stations(engine):
    state=engine.state
    if state.get('confirmed_station_locations_version',0)>=1:return
    places={
      'moedling':('Neusiedler Straße 20, 2340 Mödling',48.08133,16.28427,'https://www.roteskreuz.at/niederoesterreich/moedling/kontakte/bezirksstelle','https://www.openstreetmap.org/way/840585110'),
      'baden':('Rotes Kreuz-Gasse 6, 2500 Baden',48.00147,16.25389,'https://www.roteskreuz.at/niederoesterreich/baden/kontakte','https://www.openstreetmap.org/way/35683540')}
    for station in state['stations']:
        id=station['id'];base=id.removeprefix('nef-')
        if base not in places:continue
        address,lat,lon,url,osm=places[base]
        station.update(name=('NEF ' if id.startswith('nef-') else 'RK ')+('Mödling' if base=='moedling' else 'Baden'),address=address,lat=lat,lon=lon,external=False,zone='Mödling' if base=='moedling' else 'Baden',dispo='05',address_source=url,coordinate_source=osm,coordinate_accuracy='OSM-Gebäudemittelpunkt; Straßenanschluss wird vom Router ermittelt',address_checked='2026-10-15',source='Nutzerbestätigung 15.10.2026; Adresse durch Betreiber bestätigt')
        for v in state['vehicles']:
            if v['station']==id and v['type']!='FR' and not v.get('job') and not v.get('leg') and v['status'] in ('ready','out'):
                v.update(lat=lat,lon=lon)
    state['confirmed_station_locations_version']=1
