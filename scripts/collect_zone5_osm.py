"""Collect small, cached OSM API map excerpts around game municipalities.
Place coordinates only locate a search window. Every final street, house number
and address coordinate comes from an actual OSM node/building in that window.
"""
import concurrent.futures,datetime,hashlib,json,sys,threading,time,urllib.parse,urllib.request
from pathlib import Path
from import_zone5_addresses import MUNICIPALITIES

CACHE=Path('/tmp/noe-zone5-map-cache');CACHE.mkdir(exist_ok=True)
TITLES={'Heiligenkreuz':'Heiligenkreuz (Niederösterreich)','Pottenstein':'Pottenstein (Niederösterreich)','Seibersdorf':'Seibersdorf (Niederösterreich)','Baden':'Baden (Niederösterreich)','Berg':'Berg (Niederösterreich)','Höflein':'Höflein (Niederösterreich)','Hennersdorf':'Hennersdorf (Niederösterreich)','Leopoldsdorf':'Leopoldsdorf (Bezirk Bruck an der Leitha)','Lanzendorf':'Lanzendorf (Niederösterreich)','Wienerwald':'Wienerwald (Gemeinde)','Berndorf':'Berndorf (Niederösterreich)','Hernstein':'Hernstein','Rohrau':'Rohrau (Niederösterreich)'}
HEADERS={'User-Agent':'NoeDispo/1.0 (https://github.com/themagix9/noe-lstsim)','Accept':'application/json'}
# Official municipal contact-map pin; Wikipedia points to open terrain here.
CENTRE_OVERRIDES={'Sommerein':dict(lat=47.991462707519531,lon=16.658849716186523,source='https://www.sommerein.at/Gemeinde/Verwaltung/Kontakt_und_Amtszeiten')}
rate_lock=threading.Lock();next_call=[0.0]

def read_json(url,key,rate=False):
    p=CACHE/(hashlib.sha256(key.encode()).hexdigest()+'.json')
    if p.exists():return json.loads(p.read_text())
    if rate:
        with rate_lock:
            time.sleep(max(0,next_call[0]-time.monotonic()));next_call[0]=time.monotonic()+1.1
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=35) as r:data=json.load(r)
    p.write_text(json.dumps(data));return data

def centres():
    towns=[t for names in MUNICIPALITIES.values() for t in names.split('|')];result={}
    for start in range(0,len(towns),40):
        batch=towns[start:start+40];titles=[TITLES.get(t,t) for t in batch]
        url='https://de.wikipedia.org/w/api.php?'+urllib.parse.urlencode(dict(action='query',format='json',prop='coordinates',colimit='50',titles='|'.join(titles),redirects='1'))
        data=read_json(url,'centres|'+url);query=data['query'];aliases={r['from']:r['to'] for r in query.get('redirects',[])+query.get('normalized',[])}
        pages={r['title']:r for r in query['pages'].values()}
        for town,title in zip(batch,titles):
            for _ in range(4):title=aliases.get(title,title)
            coords=pages.get(title,{}).get('coordinates',[])
            if coords and 47.7<coords[0]['lat']<48.4 and 15.7<coords[0]['lon']<17.2:result[town]=coords[0]
        print('Centres',len(result),'/',len(towns),flush=True)
    result.update(CENTRE_OVERRIDES)
    return towns,result

def addresses(town,centre):
    district=next(k for k,v in MUNICIPALITIES.items() if town in v.split('|'));lat=centre['lat'];lon=centre['lon'];items={}
    for width in (.0015,.003,.006):
        bounds=(lon-width,lat-width,lon+width,lat+width);url='https://www.openstreetmap.org/api/0.6/map.json?bbox='+','.join(f'{v:.7f}' for v in bounds)
        data=read_json(url,'map|'+url,rate=True);nodes={e['id']:e for e in data.get('elements',[]) if e['type']=='node'}
        for e in data.get('elements',[]):
            tags=e.get('tags',{});street=tags.get('addr:street') or tags.get('addr:place');number=tags.get('addr:housenumber')
            if not street or not number or e['type'] not in ('node','way'):continue
            if e['type']=='node':x,y=e['lon'],e['lat'];accuracy='OSM-Adresspunkt'
            else:
                points=[nodes[n] for n in e.get('nodes',[]) if n in nodes]
                if len(points)<3 or len(points)!=len(e.get('nodes',[])):continue
                x=(min(p['lon'] for p in points)+max(p['lon'] for p in points))/2;y=(min(p['lat'] for p in points)+max(p['lat'] for p in points))/2;accuracy='OSM-Gebäudemittelpunkt'
            if not lon-width<=x<=lon+width or not lat-width<=y<=lat+width:continue
            locality=tags.get('addr:city') or town;postcode=tags.get('addr:postcode','');id=f'osm-{e["type"]}-{e["id"]}'
            items[id]=dict(id=id,osm_type=e['type'],osm_id=e['id'],lat=y,lon=x,street=street,house_number=number,postcode=postcode,city=town,municipality=town,locality=locality,district=district,address=f'{street} {number}, '+(postcode+' ' if postcode else '')+locality,source='OpenStreetMap API map excerpt',address_kind='street' if tags.get('addr:street') else 'place',coordinate_accuracy=accuracy,source_url=f'https://www.openstreetmap.org/{e["type"]}/{e["id"]}',checked=datetime.date.today().isoformat())
        if len(items)>=8:break
    selected=sorted(items.values(),key=lambda a:hashlib.sha256(a['id'].encode()).hexdigest())[:30]
    print(town,len(selected),flush=True);return selected

def collect():
    towns,points=centres();missing=[t for t in towns if t not in points];print('Missing centres',missing,flush=True)
    result=[];failures=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        tasks={pool.submit(addresses,t,c):t for t,c in points.items()}
        for task in concurrent.futures.as_completed(tasks):
            try:result.extend(task.result())
            except Exception as e:failures.append(tasks[task]);print('FAILED',tasks[task],str(e),flush=True)
    covered={a['city'] for a in result};missing=sorted(set(towns)-covered)
    data=dict(license='ODbL-1.0',attribution='© OpenStreetMap contributors',source='https://www.openstreetmap.org/copyright',retrieved=datetime.date.today().isoformat(),collection='Kleine OSM-API-Kartenausschnitte; Ortskoordinaten nur für Suchfenster via Wikipedia GeoData API',footprint='Spielgebiet: Baden, Mödling, Bruck/Leitha sowie Ebenfurth',missing_municipalities=missing,addresses=result)
    Path(sys.argv[1]).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');print('TOTAL',len(result),'municipalities',len(covered),'missing',missing,flush=True)

if __name__=='__main__':collect()
