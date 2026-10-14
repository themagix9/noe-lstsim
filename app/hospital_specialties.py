"""Source-labelled departments and fictional crew destination selection.
Department existence is not a live bed/acceptance guarantee.
"""
import copy
import datetime as dt
import json
import re
from pathlib import Path
DATA=json.loads((Path(__file__).parent/'data/hospital-specialties.json').read_text())
LABELS={'trauma':'Orthopädie / Traumatologie','dermatology':'Dermatologie','neurology':'Neurologie','ophthalmology':'Augenheilkunde','obstetrics':'Gynäkologie / Geburtshilfe','psychiatry':'Psychiatrie','paediatrics':'Kinder- und Jugendheilkunde','internal':'Innere Medizin','cardiology':'Kardiologie','urology':'Urologie','pulmonology':'Pneumologie','ent':'HNO'}
PATTERNS={'trauma':r'traumatologie|unfallchirurgie','dermatology':r'dermatologie|haut- und geschlechts','neurology':r'neurologie','ophthalmology':r'augen','obstetrics':r'geburtshilfe','psychiatry':r'psychiatrie','paediatrics':r'kinder- und jugendheilkunde|kinder- und jugendabteilung','internal':r'innere medizin|medizinische abteilung|diabetologie|gastroenterologie','cardiology':r'kardiologie','urology':r'urologie','pulmonology':r'pneumologie|pulmologie','ent':r'hals.*nasen.*ohren'}

def upgrade(engine):
    profiles={p['registry_id']:p for p in DATA['profiles']}
    for h in engine.state['hospitals']:
        p=profiles.get(h.get('registry_id'))
        if h.get('department_profile'):continue
        if p and p['departments']:
            departments=p['departments'];profile=copy.deepcopy(p)
        else:
            departments=h.get('departments',[])
            from hospitals import DIRECTORY
            profile={'departments':copy.deepcopy(departments),'source':DIRECTORY.get('source','Amtliches österreichisches Krankenanstaltenverzeichnis'),'checked':DIRECTORY.get('date','18.09.2026'),'status':'Amtlicher Verzeichnisstand; aktuelle Betreiberprüfung offen'}
            if p:profile['operator_check']=p['status']
        h.update(departments=copy.deepcopy(departments),specialties=[key for key,pattern in PATTERNS.items() if any(re.search(pattern,name,re.I) for name in departments)],department_profile=profile)

def age(j):
    value=j.get('patient',{}).get('age')
    if isinstance(value,(int,float)) and 0<=value<=120:return value
    text=j.get('_scenario',{}).get('answers',{}).get('patient','')
    match=re.search(r'(\d{1,3})\s*Jahre?',text,re.I)
    return int(match[1]) if match else None

def specialty(j):
    # Use the crew's finding, not the potentially mistaken caller diagnosis.
    text=str(j.get('scene') or j.get('_scenario',{}).get('report') or '').lower()
    if re.search(r'auge|augen',text):return 'ophthalmology'
    if re.search(r'hautausschlag|dermatolog|hautentzündung',text) and not re.search(r'anaphylax|atemproblemen|ausgeprägte atemnot',text):return 'dermatology'
    if re.search(r'verletz|fraktur|trauma|bissverletz|sturz|verkehrsunfall|wundversorgung',text):return 'trauma'
    if re.search(r'geburt|schwanger|wehen',text):return 'obstetrics'
    if re.search(r'schlaganfall|krampfanfall|neurolog',text):return 'neurology'
    if re.search(r'psychiatr|psychose',text):return 'psychiatry'
    years=age(j)
    if years is not None and years<=16:return 'paediatrics'
    return 'internal'

def available(engine,h,field,j):
    if field not in h.get('specialties',[]):return False
    if field=='trauma' and h.get('registry_id')=='K380.1':
        years=age(j)
        if years is not None and years<=10:return True
        day=dt.date.fromisoformat(engine.state['start_date'])+dt.timedelta(days=int(engine.state['clock']//86400))
        return day.weekday()<5 and 8*3600<=engine.state['clock']%86400<13*3600
    return True

def choose_target(engine,j,v,region=None):
    from engine import distance
    from hospitals import nearby
    field=specialty(j)
    candidates=[h for h in nearby(engine,j,region,emergency=True) if v['type']!='NAH' or h.get('helipad')]
    if not candidates:raise ValueError('Kein positioniertes Akutkrankenhaus mit passender Transportmöglichkeit verfügbar.')
    matching=[h for h in candidates if available(engine,h,field,j)]
    chosen=matching[0] if matching else candidates[0]
    years=age(j)
    if field=='trauma' and (years is None or years>10) and matching:
        baden=next((h for h in matching if h.get('registry_id')=='K380.2'),None)
        if baden and distance(j,baden)<=distance(j,chosen)+20:chosen=baden
    if field=='dermatology' and matching:
        landstrasse=next((h for h in matching if h.get('registry_id')=='K917.1'),None)
        if landstrasse and distance(j,landstrasse)<=distance(j,chosen)+20:chosen=landstrasse
    j['destination_specialty']=LABELS[field]
    j['destination_profile_verified']=bool(matching)
    j['destination_reason']=('Fachabteilung laut Betreiberprofil; keine Echtzeit-Aufnahmezusage.' if matching else 'Fachabteilungsprofil für dieses Ziel offen; nächstes Akutkrankenhaus als Übungsfallback.')
    return chosen
