"""Import ministry XLSX contact/site facts and geocode them with cached OSM Photon results.

Usage: python tools/import_hospitals.py SOURCE.xlsx OUTPUT.json
Public one-off geocoding: at most one request/second, four waiting workers.
"""
import concurrent.futures
import json
from pathlib import Path
import re
import sys
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

SOURCE='https://www.sozialministerium.gv.at/Themen/Gesundheit/Gesundheitssystem/Krankenanstalten/Krankenanstalten-und-selbststaendige-Ambulatorien-in-Oesterreich/Krankenanstalten-in-Oesterreich.html'
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def workbook(path):
    archive=zipfile.ZipFile(path)
    strings=[''.join(t.itertext()) for t in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si',NS)]
    def rows(sheet):
        result=[]
        for row in ET.fromstring(archive.read('xl/worksheets/'+sheet+'.xml')).findall('s:sheetData/s:row',NS):
            record={}
            for cell in row.findall('s:c',NS):
                value=cell.find('s:v',NS)
                if value is not None:record[re.sub('[0-9]','',cell.get('r'))]=strings[int(value.text)] if cell.get('t')=='s' else value.text
            result.append(record)
        return result
    site_rows=rows('sheet2')
    return rows('sheet1')[1:],[r for r in site_rows if r.get('A','').startswith('K')],site_rows[2]

def normalize(value):
    return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',value.casefold().replace('ß','ss')).encode('ascii','ignore').decode()).replace('strasse','str')

def records(path):
    institutions,sites,department_names=workbook(path);items=[]
    for ka in institutions:
        locations=[s for s in sites if s['A'].split('.')[0]==ka['B']]
        if not locations:locations=[{'A':ka['B']+'.1','B':ka['C'],'D':ka['O'].split(',')[-1].strip(),'E':','.join(ka['O'].split(',')[:-1]).strip()}]
        for site in locations:
            address=site['E']+', '+site['D'];match=re.search(r'\b(\d{4})\s+(.+)',site['D'])
            items.append({'id':'ka-'+site['A'].lower().replace('.','-'),'registry_id':site['A'],'name':ka['C'] if len(locations)==1 else ka['C']+' · '+site['B'],
                'site_name':site['B'],'address':address,'city':match.group(2) if match else site['D'],'postcode':match.group(1) if match else '',
                'region':'NÖ' if ka['A']=='Niederösterreich' else ka['A'],'sector':ka['E'],'care_type':ka['F'],'ka_type':ka['J'],
                'emergency':ka['E']=='Akutversorgung' and ka['F']=='Allgemeinversorgung' and (not sites or any(site.get(key) not in (None,'','0') for key in ('J','L'))),'departments':[department_names[key] for key,value in site.items() if key in department_names and key not in ('A','B','C','D','E') and value not in ('','0') and department_names[key]],
                'website':ka.get('Q',''),'address_source':SOURCE,'source_date':'2026-09-18','helipad':False,'ecpr':False,'lat':None,'lon':None})
    return items,len(institutions)

if __name__=='__main__':
    items,institution_count=records(sys.argv[1]);cache_path=Path('/tmp/noe-hospital-geocoding.json')
    cache=json.loads(cache_path.read_text()) if cache_path.exists() else {}
    lock=threading.Lock();rate_lock=threading.Lock();last=[0.0]
    def geocode(item):
        address=item['address']
        if address in cache:result=cache[address]
        else:
            with rate_lock:
                delay=max(0,1.05-(time.monotonic()-last[0]));time.sleep(delay);last[0]=time.monotonic()
            try:
                url='https://photon.komoot.io/api/?'+urllib.parse.urlencode({'q':address+' Österreich','limit':5})
                request=urllib.request.Request(url,headers={'User-Agent':'NoeDispo/0.9 educational simulator; public addresses'})
                features=json.load(urllib.request.urlopen(request,timeout=25))['features']
                result=None
                for f in features:
                    p=f['properties'];x,y=f['geometry']['coordinates']
                    if p.get('countrycode','').upper()!='AT' or not (46<y<50 and 9<x<18):continue
                    street=p.get('street',p.get('name',''));official_street=re.sub(r'\s+\d.*$','',address.split(',')[0])
                    if p.get('postcode')!=item['postcode'] or normalize(street)!=normalize(official_street):continue
                    result={'lat':y,'lon':x,'coordinate_source':'https://photon.komoot.io/ · OpenStreetMap','coordinate_status':'OSM address match','osm_id':p.get('osm_id'),'osm_type':p.get('osm_type')};break
            except Exception:result=None
            with lock:
                cache[address]=result;cache_path.write_text(json.dumps(cache,ensure_ascii=False))
        if result:item.update(result)
        else:item['coordinate_status']='Adresse amtlich; Kartenposition noch zu prüfen'
        return item
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        output=[]
        for n,item in enumerate(pool.map(geocode,items),1):
            output.append(item)
            if n%20==0:print(n,'/',len(items),'geocoded',sum(h['lat'] is not None for h in output),flush=True)
    Path(sys.argv[2]).write_text(json.dumps({'source':SOURCE,'date':'2026-09-18','institution_count':institution_count,'license_note':'Amtliches Verzeichnis zur Weiterverarbeitung; OSM-Koordinaten ODbL-1.0','attribution':'BMASGPK; © OpenStreetMap contributors','hospitals':output},ensure_ascii=False,indent=2)+'\n')
    print('done',len(output),'sites;',sum(h['lat'] is not None for h in output),'geocoded',flush=True)
