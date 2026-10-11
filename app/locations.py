"""Real OSM address points and public hospital contact addresses; patients are fictional."""
import json
from pathlib import Path
ADDRESSES=json.loads((Path(__file__).parent/'data'/'addresses.json').read_text())['addresses']
ADDRESS_CITIES=sorted({a['city'] for a in ADDRESSES})
HOSPITALS={
 'kh-hainburg':{'address':'Hofmeisterstraße 70, 2410 Hainburg an der Donau','lat':48.1432994,'lon':16.9580624,'address_source':'https://hainburg.lknoe.at/fuer-besucher/kontakt-und-anfahrt','coordinate_source':'Kartenmarker auf offizieller Betreiberseite'},
 'kh-moedling':{'address':'Sr. M. Restituta-Gasse 12, 2340 Mödling','lat':48.0885476,'lon':16.2977629,'address_source':'https://moedling.lknoe.at/fuer-besucher/kontakt-und-anfahrt','coordinate_source':'Kartenmarker auf offizieller Betreiberseite'},
 'kh-donaustadt':{'address':'Langobardenstraße 122, 1220 Wien','lat':48.219397,'lon':16.462914,'address_source':'https://klinik-donaustadt.gesundheitsverbund.at/anreise-und-parken/','coordinate_source':'Vom Nutzer bereitgestellte Kartenreferenz; kein verifizierter Rettungseingang'},
 'kh-akh-ecpr':{'address':'Währinger Gürtel 18–20, 1090 Wien','lat':48.22132,'lon':16.346206,'address_source':'https://gesundheitsverbund.at/kliniken/','coordinate_source':'Vom Nutzer bereitgestellte Kartenreferenz; Landeplatz separat noch zu verifizieren'}
}

def upgrade_locations(engine):
    state=engine.state
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
