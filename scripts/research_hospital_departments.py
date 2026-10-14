"""Refresh source-labelled NÖ department snapshots from official operator pages."""
import concurrent.futures,html,json,re,urllib.request
from pathlib import Path
MAPPING={'amstetten':'K303.1','hainburg':'K316.1','tulln':'K324.1','klosterneuburg':'K324.2','krems':'K326.1','mauer':'K333.1','melk':'K334.1','mistelbach':'K335.1','gaenserndorf':'K335.2','neunkirchen':'K338.1','korneuburg':'K343.1','stockerau':'K343.2','hollabrunn':'K343.3','scheibbs':'K347.1','waidhofen-ybbs':'K354.1','wienerneustadt':'K367.1','hochegg':'K367.2','horn':'K377.1','allentsteig':'K377.3','moedling':'K380.1','baden':'K380.2','stpoelten':'K382.1','lilienfeld':'K382.2','zwettl':'K383.1','gmuend':'K383.2','waidhofen-thaya':'K383.3'}
def fetch(item):
 slug,registry=item;errors=[]
 for route in ('abteilungen','klinische-abteilungen'):
  url=f'https://{slug}.lknoe.at/fuer-patienten/{route}'
  try:
   with urllib.request.urlopen(url,timeout=12) as r:s=r.read().decode()
   blocks=re.findall(r'<h2[^>]*>(.*?)</h2>\s*<ul[^>]*>(.*?)</ul>',s,re.S|re.I)
   selected=[b for title,b in blocks if re.search('Abteilungen',html.unescape(re.sub('<[^>]+>','',title)),re.I)]
   if not selected:raise ValueError('Keine Abteilungsübersicht gefunden')
   names=[]
   for block in selected:
    for name in re.findall(r'<a[^>]*>(.*?)</a>',block,re.S):
     name=' '.join(html.unescape(re.sub('<[^>]+>','',name)).split())
     if name and name not in names:names.append(name)
   if slug=='moedling':names=[n for n in names if 'Hinterbrühl' not in n]
   return dict(registry_id=registry,site=slug,departments=names,source=url,checked='2026-10-14',status='Betreiber-Abteilungsübersicht; keine Echtzeit-Aufnahmezusage')
  except Exception as e:errors.append(str(e))
 return dict(registry_id=registry,site=slug,departments=[],checked='2026-10-14',status='Abteilungsprofil noch ungeprüft',errors=errors)
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(fetch,MAPPING.items()))
 path=Path(__file__).resolve().parents[1]/'app/data/hospital-specialties.json'
 path.write_text(json.dumps({'profiles':results,'checked':'2026-10-14'},ensure_ascii=False,indent=2))
 for r in results:print(r['site'],':',', '.join(r['departments']) or r['status'])
