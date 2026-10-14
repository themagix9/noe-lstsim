"""AAO approximation from public NÖ guidance, using simulated ETAs.
Road routing with provisional estimates while an OSRM matrix is pending.
"""
import json
from pathlib import Path
SOURCE=json.loads((Path(__file__).parent/'data'/'ampds.json').read_text())
CODES={r['code']:r for r in SOURCE['entries']}
REFERENCE='https://www.notrufnoe.at/ausrueckordnung-detail/'

def code_rule(code):
    from catalog import TRANSPORT_RULES
    transport=next((r for r in TRANSPORT_RULES if r['code']==code),None)
    if transport:return transport.copy()
    item=CODES.get(code)
    if not item:return None
    category=item['category'];signal=category in ('BLS rot','ALS grün','ALS gelb','ALS orange','ALS rot','Akuttransport rot')
    needs=[] if category in ('Telemedizin','Weitergabe','Großunfall','Alpinunfall') else ['RTW','NEF'] if category in ('ALS orange','ALS rot') else ['RTW']
    if code=='RD-9E1':needs=['RTW-C','NEF']
    return {**item,'kind':'emergency','priority':'hoch' if signal else 'mittel','needs':needs,'signal':signal}

def estimated_seconds(engine,v,j):
    from engine import distance
    from turnout import preparation
    estimate=engine.router.cached_eta(v,j) if v['type']!='NAH' else None
    if estimate and estimate['status']=='ready':return estimate['seconds']*engine.response_factor(v,j)+preparation(engine,v,j)
    return distance(v,j)*(1 if v['type']=='NAH' else 1.25)/(v.get('flight_speed',220) if v['type']=='NAH' else 45)*3600*engine.response_factor(v,j)+preparation(engine,v,j)

def recommend(engine,j):
    candidates=[v for v in engine.state['vehicles'] if engine.sendable(v,j)]
    assigned=[engine.get('vehicles',id) for id in j['vehicles']]
    result={'vehicles':[],'missing':[],'rule':j.get('code'),'category':j.get('category','Übungsregel'),'description':'Simulationsvorschlag · geschätzte Eintreffzeit aus Luftlinie + Ausrückzeit','warnings':[],'source':REFERENCE,'code_date':SOURCE['date']}
    if engine.router.enabled:
        ready=all(v['type']=='NAH' or (engine.router.cached_eta(v,j) or {}).get('status')=='ready' for v in candidates)
        failed=any((engine.router.cached_eta(v,j) or {}).get('status')=='error' for v in candidates if v['type']!='NAH')
        result['description']='Straßenrouting + Ausrückzeit; NAH Flugzeit' if ready else 'Routendienst nicht verfügbar; AAO mit Entfernungsschätzung' if failed else 'Vorläufiger Vorschlag: Straßenrouten werden berechnet, derzeit Entfernungsschätzung'
    category=j.get('category');eta=lambda v:estimated_seconds(engine,v,j)
    transport_types=('KTW','KTW-B','BKTW','RTW','RTW-C') if j['kind']=='transport' else ('KTW','RTW','RTW-C')
    transporters=[v for v in candidates if v['type'] in transport_types];nefs=[v for v in candidates if v['type']=='NEF']
    def nearest(vs):return min(vs,key=eta) if vs else None
    chosen=None;need_nef=False
    if j.get('manv') and j.get('patients'):
        pending=[p for p in j['patients'] if not p['delivered'] and engine.patient_phase(j,p)=='scene']
        critical=sum(p['percent']<45 for p in pending)
        active=[v for v in assigned if v.get('job')==j['id'] and v['status'] in ('assigned','acknowledged','standby','enroute','scene')]
        targets=[('Transportmittel',max(0,len(pending)-sum(v['type'] in transport_types+('NAH',) for v in active)),transporters),('Notarztmittel',max(0,critical-sum(v['type'] in ('NEF','NAH') for v in active)),[v for v in candidates if v['type'] in ('NEF','NAH')])]
        used=set()
        for label,count,options in targets:
            options=sorted((v for v in options if v['id'] not in used),key=eta)
            for v in options[:count]:result['vehicles'].append(v['id']);used.add(v['id'])
            if len(options)<count:result['missing'].append(f'{count-len(options)} {label}')
        result['warnings'].append('MANV-Übung: Ein Transportmittel je Patient; Notarztmittel nach kritischen Spielzuständen. Mannschaftsmeldung und Sichtung laufend prüfen.')
        return result
    if j.get('code')=='RD-9E1':
        for typ in ('RTW-C','NEF'):
            if any(v['type']==typ for v in assigned):continue
            unit=nearest([v for v in candidates if v['type']==typ])
            if unit:result['vehicles'].append(unit['id'])
            else:result['missing'].append(typ)
        result['warnings'].append('Nutzer-AAO 9E1: RTW-C + NEF + Polizei. NAH optional; bei NAH eCPR-Voranmeldung und Funkrückfrage vor Zielflug.');return result
    if category in ('Telemedizin','Weitergabe') and not j.get('secondary_unavailable'):
        result['warnings'].append('Sekundärsystem / Weitergabe benötigt normalerweise kein Rettungsmittel. Bei Nichtverfügbarkeit BLS grün als Fallback auswählen.');return result
    if category in ('Großunfall','Alpinunfall'):
        result['warnings'].append('Sonderrettung / Großeinsatz-AAO noch nicht implementiert; manuell disponieren.');result['missing']=['Sondereinsatzmittel'];return result
    if category in ('Telemedizin','Weitergabe'):category='BLS grün'
    if j['kind']=='transport':
        org=j.get('organization','RK');transporters=[v for v in transporters if v.get('organization','RK')==org]
        preferred=[v for v in transporters if v['type'] in ('KTW','KTW-B','BKTW')];chosen=nearest(preferred) or nearest(transporters)
        if j.get('code')=='KTx-96K5':
            chosen=nearest([v for v in transporters if v['type'] in ('RTW','RTW-C')]);result['warnings'].append('Arzt wird laut Auftrag beigestellt; Arztbesetzung muss organisatorisch gesichert sein (nicht als eigenes Einsatzmittel simuliert).')
    elif category=='BLS rot':
        rtws=[v for v in transporters if v['type']=='RTW'];ktws=[v for v in transporters if v['type']=='KTW'];rtw=nearest(rtws);ktw=nearest(ktws)
        chosen=rtw if rtw and (not ktw or eta(rtw)<=eta(ktw)+90) else ktw or nearest([v for v in transporters if v['type']=='RTW-C'])
    elif category=='BLS/ALS aufwertbar':
        for typ in ('RTW-C','RTW','KTW'):
            chosen=nearest([v for v in transporters if v['type']==typ])
            if chosen:break
        result['warnings'].append('Optionale Aufwertung durch ACN / Notarzt muss manuell beurteilt werden.')
    elif category in ('ALS grün','ALS gelb'):
        qualified=[v for v in transporters if v['type'] in ('RTW','RTW-C') and v.get('nfs')]
        chosen=nearest(qualified)
        if category=='ALS gelb' and not chosen:chosen=nearest(transporters);need_nef=True
        if not chosen and category=='ALS grün':result['missing'].append('RTW/RTW-C mit bestätigtem NFS')
        if category=='ALS gelb':result['warnings'].append('ACN-Pilotregionen und NKV/NKI-Zusatzregeln sind noch nicht modelliert.')
    elif category in ('ALS orange','ALS rot'):
        chosen=nearest(transporters);need_nef=True
        result['warnings'].append('NAH-Eintreffzeit als geschätzte Flugzeit; Wetter, Landeplätze und ACN-Zeitvorteile noch nicht modelliert.')
    elif category:chosen=nearest(transporters)
    else:
        # Custom exercise rule; each requirement consumes one distinct resource.
        used=[]
        for need in j['needs']:
            existing=next((v for v in assigned if v['id'] not in used and (v['type'].startswith(need) or need=='KTW' and v['type'].startswith('RTW'))),None)
            if existing:used.append(existing['id']);continue
            options=[v for v in candidates if v['id'] not in used and (v['type'].startswith(need) or need=='KTW' and v['type'].startswith('RTW'))]
            options.sort(key=lambda v:(need=='KTW' and not v['type'].startswith('KTW'),eta(v)))
            if options:result['vehicles'].append(options[0]['id']);used.append(options[0]['id'])
            else:result['missing'].append(need)
        return result
    if not any(v['type'] in transport_types for v in assigned):
        if chosen:result['vehicles'].append(chosen['id'])
        elif not result['missing']:result['missing'].append('Transportierendes Rettungsmittel')
    frs=[v for v in candidates if v['type']=='FR' and (not chosen or eta(v)<eta(chosen))]
    result['supplementary']=[nearest(frs)['id']] if frs and j['kind']=='emergency' and j.get('priority')=='hoch' and not any(v['type']=='FR' for v in assigned) else []
    if result['supplementary']:result['warnings'].append('Optionaler First Responder mit geschätztem Zeitvorteil; ersetzt kein Rettungs- oder Notarztmittel.')
    if need_nef and not any(v['type'] in ('NEF','NAH') for v in assigned):
        helicopters=[v for v in candidates if v['type']=='NAH'] if category in ('ALS orange','ALS rot') else []
        ground=nearest(nefs)
        nef=ground if category=='ALS orange' and ground and eta(ground)<=900 else nearest(nefs+helicopters)
        if nef:result['vehicles'].append(nef['id'])
        else:result['missing'].append('Notarztmittel')
    return result
