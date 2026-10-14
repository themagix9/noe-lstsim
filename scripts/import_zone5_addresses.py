"""Import real OSM address nodes/ways for the Dispo 05 game municipalities.
Usage: python scripts/import_zone5_addresses.py /tmp/zone5-addresses.json
One-off data refresh; game runtime never queries Overpass. Existing stations are
unchanged. The game footprint is not a published official dispatch boundary.
"""
import datetime,hashlib,json,re,sys,time,urllib.parse,urllib.request
from pathlib import Path

ENDPOINTS=['https://overpass-api.de/api/interpreter','https://overpass.private.coffee/api/interpreter']
MUNICIPALITIES={
 'Baden':'Alland|Altenmarkt an der Triesting|Bad Vöslau|Baden|Berndorf|Blumau-Neurißhof|Ebreichsdorf|Enzesfeld-Lindabrunn|Furth an der Triesting|Günselsdorf|Heiligenkreuz|Hernstein|Hirtenberg|Klausen-Leopoldsdorf|Kottingbrunn|Leobersdorf|Mitterndorf an der Fischa|Oberwaltersdorf|Pfaffstätten|Pottendorf|Pottenstein|Reisenberg|Schönau an der Triesting|Seibersdorf|Sooß|Tattendorf|Teesdorf|Traiskirchen|Trumau|Weißenbach an der Triesting',
 'Mödling':'Achau|Biedermannsdorf|Breitenfurt bei Wien|Brunn am Gebirge|Gaaden|Gießhübl|Gumpoldskirchen|Guntramsdorf|Hennersdorf|Hinterbrühl|Kaltenleutgeben|Laab im Walde|Laxenburg|Maria Enzersdorf|Mödling|Münchendorf|Perchtoldsdorf|Vösendorf|Wiener Neudorf|Wienerwald',
 'Bruck an der Leitha':'Au am Leithaberge|Bad Deutsch-Altenburg|Berg|Bruck an der Leitha|Ebergassing|Enzersdorf an der Fischa|Fischamend|Göttlesbrunn-Arbesthal|Götzendorf an der Leitha|Gramatneusiedl|Hainburg an der Donau|Haslau-Maria Ellend|Himberg|Hof am Leithaberge|Höflein|Hundsheim|Klein-Neusiedl|Lanzendorf|Leopoldsdorf|Mannersdorf am Leithagebirge|Maria-Lanzendorf|Moosbrunn|Petronell-Carnuntum|Prellenkirchen|Rauchenwarth|Rohrau|Scharndorf|Schwadorf|Schwechat|Sommerein|Trautmannsdorf an der Leitha|Wolfsthal|Zwölfaxing',
 'Ebenfurth':'Ebenfurth',
}
# Postal locality spellings in OSM may differ from administrative names.
ALIASES={'Maria Lanzendorf':'Maria-Lanzendorf','Kleinneusiedl':'Klein-Neusiedl','Klein Neusiedl':'Klein-Neusiedl','Weissenbach an der Triesting':'Weißenbach an der Triesting','Blumau':'Blumau-Neurißhof','Breitenfurt':'Breitenfurt bei Wien','Hainburg':'Hainburg an der Donau','Weissenbach':'Weißenbach an der Triesting','Sittendorf':'Wienerwald','Sulz im Wienerwald':'Wienerwald','Göttlesbrunn':'Göttlesbrunn-Arbesthal','Arbesthal':'Göttlesbrunn-Arbesthal','Haslau an der Donau':'Haslau-Maria Ellend','Maria Ellend':'Haslau-Maria Ellend'}

def collect():
    records={};coverage=[];date=datetime.date.today().isoformat()
    for district,names in MUNICIPALITIES.items():
        towns=names.split('|');accepted=towns+[a for a,b in ALIASES.items() if b in towns]
        regex='^('+'|'.join(re.escape(n) for n in accepted)+')$'
        query='[out:json][timeout:75];'+''.join('nwr(47.7,15.7,48.4,17.2)["addr:city"='+json.dumps(town,ensure_ascii=False)+']["addr:street"]["addr:housenumber"]["addr:postcode"];out center qt 40;' for town in accepted)
        cache=Path('/tmp/noe-zone5-postal-'+district+'.json');data=json.loads(cache.read_text()) if cache.exists() else None
        for endpoint in ([] if data is not None else ENDPOINTS):
            try:
                req=urllib.request.Request(endpoint,data=urllib.parse.urlencode({'data':query}).encode(),headers={'User-Agent':'NoeDispo/1.0 (https://github.com/themagix9/noe-lstsim)','Accept':'application/json'})
                with urllib.request.urlopen(req,timeout=90) as response:data=json.load(response)
                if data.get('remark'):raise ValueError(data['remark'])
                break
            except Exception as e:print(district,endpoint,str(e),flush=True);time.sleep(2)
        if data is None or data.get('remark'):raise RuntimeError('Address import failed: '+district)
        cache.write_text(json.dumps(data));buckets={town:[] for town in towns}
        for item in data.get('elements',[]):
            tags=item.get('tags',{});locality=tags.get('addr:city');municipality=ALIASES.get(locality,locality)
            if municipality not in buckets:continue
            center=item.get('center',item);street=tags.get('addr:street');number=tags.get('addr:housenumber');postcode=tags.get('addr:postcode')
            if not street or not number or not postcode or not (47.7<center.get('lat',0)<48.4 and 15.7<center.get('lon',0)<17.2):continue
            id=f'osm-{item["type"]}-{item["id"]}'
            buckets[municipality].append(dict(id=id,osm_type=item['type'],osm_id=item['id'],lat=center['lat'],lon=center['lon'],street=street,house_number=number,postcode=postcode,city=municipality,locality=locality,municipality=municipality,district=district,address=f'{street} {number}, {postcode} {locality}',source='OpenStreetMap / Overpass · postal locality',checked=date))
        missing=[town for town,points in buckets.items() if not points]
        if missing:print('Missing postal localities:',missing,flush=True)
        count=0
        for town,points in buckets.items():
            # Deterministic spatial variety instead of just the first OSM IDs.
            for record in sorted(points,key=lambda a:hashlib.sha256(a['id'].encode()).hexdigest())[:40]:records[record['id']]=record;count+=1
        coverage.append(dict(district=district,addresses=count,municipalities=len(towns)-len(missing),missing=missing));print(district,count,'addresses',len(towns)-len(missing),'municipalities',flush=True)
        if count<10:raise RuntimeError('Insufficient address coverage: '+district)
    return dict(license='ODbL-1.0',attribution='© OpenStreetMap contributors',source='https://www.openstreetmap.org/copyright',retrieved=date,footprint='Spielgebiet: Bezirke Baden, Mödling, Bruck an der Leitha sowie Ebenfurth',coverage=coverage,addresses=list(records.values()))

if __name__=='__main__':Path(sys.argv[1]).write_text(json.dumps(collect(),ensure_ascii=False,indent=2)+'\n')
