"""One-off ODbL address refresh from OSM administrative areas; no invented points.
Usage: python scripts/import_zone5_addresses.py /tmp/zone5-addresses.json
The game footprint is Baden, Mödling, Bruck/Leitha and Ebenfurth, not an official
published dispatch boundary. Existing manually maintained stations are unchanged.
"""
import datetime,json,sys,time,urllib.parse,urllib.request
from pathlib import Path

ENDPOINTS=['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']

def collect():
    records={};coverage=[];date=datetime.date.today().isoformat()
    for district,level in [('Baden','6'),('Mödling','6'),('Bruck an der Leitha','6'),('Ebenfurth','8')]:
        name=('Bezirk ' if level=='6' else '(Gemeinde )?')+district
        area=f'rel(47.7,15.7,48.4,17.2)["boundary"="administrative"]["admin_level"="{level}"]["name"~"^{name}$"];map_to_area'
        selection=area+'->.municipalities;' if level=='8' else area+'->.district;rel(area.district)["boundary"="administrative"]["admin_level"="8"];map_to_area->.municipalities;'
        query='[out:json][timeout:150];'+selection+'foreach.municipalities->.town(.town out tags;nwr(area.town)["addr:street"]["addr:housenumber"];out center qt 50;)'
        data=None
        for endpoint in ENDPOINTS:
            try:
                req=urllib.request.Request(endpoint,data=urllib.parse.urlencode({'data':query}).encode(),headers={'User-Agent':'NoeDispo/1.0 (https://github.com/themagix9/noe-lstsim)','Accept':'application/json'})
                with urllib.request.urlopen(req,timeout=180) as response:data=json.load(response)
                if data.get('remark'):raise ValueError(data['remark'])
                break
            except Exception as e:print(district,endpoint,str(e),flush=True);time.sleep(2)
        if data is None or data.get('remark'):raise RuntimeError('Address import failed: '+district)
        municipality=None;count=0
        for item in data.get('elements',[]):
            tags=item.get('tags',{})
            if item['type']=='area':municipality=tags.get('name','').removeprefix('Gemeinde ');continue
            if not municipality:continue
            center=item.get('center',item);street=tags.get('addr:street');number=tags.get('addr:housenumber');postcode=tags.get('addr:postcode')
            if not street or not number or not postcode or not (47.7<center.get('lat',0)<48.4 and 15.7<center.get('lon',0)<17.2):continue
            id=f'osm-{item["type"]}-{item["id"]}';locality=tags.get('addr:city') or municipality
            records[id]=dict(id=id,osm_type=item['type'],osm_id=item['id'],lat=center['lat'],lon=center['lon'],street=street,house_number=number,postcode=postcode,city=municipality,locality=locality,municipality=municipality,district=district,address=f'{street} {number}, {postcode} {locality}',source='OpenStreetMap / Overpass · administrative municipality',checked=date)
            count+=1
        coverage.append(dict(district=district,addresses=count));print(district,count,flush=True)
        if count<10:raise RuntimeError('Insufficient address coverage: '+district)
    return dict(license='ODbL-1.0',attribution='© OpenStreetMap contributors',source='https://www.openstreetmap.org/copyright',retrieved=date,footprint='Spielgebiet: Bezirke Baden, Mödling, Bruck an der Leitha sowie Ebenfurth',coverage=coverage,addresses=list(records.values()))

if __name__=='__main__':Path(sys.argv[1]).write_text(json.dumps(collect(),ensure_ascii=False,indent=2)+'\n')
