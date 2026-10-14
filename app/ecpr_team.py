"""Virtual AKH eCPR standby requested by the user; not a dispatchable vehicle."""
import re

class EcprTeam:
    def sync_ecpr_team(self,j):
        if j['status']=='done' or j.get('patient_delivered'):
            if j.pop('ecpr_team',None):self.log(f'eCPR AKH: Einsatz {j["incident_number"]} beendet, Team aus dem Auftrag entlassen.','eCPR')
            return
        trigger=bool(re.match(r'^(?:RD-)?9(?:[A-Z]|$)',j.get('code',''),re.I)) or bool(re.search(r'Reanimation|Wiederbelebung|Kreislaufstillstand',j.get('title',''),re.I))
        if not trigger or j.get('dispatched_at') is None and not j.get('vehicles'):return
        if not j.get('ecpr_team'):
            j['ecpr_team']=dict(id='ecpr-akh-'+j['id'],name='eCPR AKH',status='alarmed',alarmed_at=self.state['clock'],virtual=True)
            self.log(f'eCPR AKH alarmiert · Einsatz {j["incident_number"]}. Team verbleibt im AKH, keine Anfahrt.','eCPR')
        if j['ecpr_team']['status']!='ready' and any(v.get('job')==j['id'] and v['type'] not in ('NEF','FR') and v['status'] in ('transport','hospital') for v in self.state['vehicles']):
            j['ecpr_team'].update(status='ready',ready_at=self.state['clock'])
            self.log(f'eCPR AKH bereit · Einsatz {j["incident_number"]}, Patiententransport begonnen.','eCPR')

    def update_job_code(self,data):
        j=self.get('jobs',data['job']);rule=self.rule(data.get('code',''))
        if not j['accepted'] or j['status']=='done':raise ValueError('Einen angenommenen, laufenden Einsatz wählen.')
        if not rule or rule['kind']!=j['kind']:raise ValueError('Passendes Alarmierungsstichwort wählen.')
        if rule['code']==j.get('code') and j.get('code_confirmed'):self.sync_ecpr_team(j);return
        old=j.get('code');j.setdefault('code_history',[]).append(dict(time=self.state['clock'],before=old,after=rule['code'],actor=data.get('_actor',{}).get('name','Disponent')))
        j.update(code=rule['code'],title=rule['title'],priority=rule['priority'],needs=rule['needs'][:],category=rule.get('category'),code_confirmed=True)
        if j['code']=='RD-9E1':j.update(needs=['RTW-C','NEF'],police=True)
        self.log(f'Einsatz {j["incident_number"]}: Alarmierungsstichwort {old} → {j["code"]}.','Aufträge')
        self.sync_ecpr_team(j);self.ensure_agency_requests(j)
        for v in self.state['vehicles']:
            if v.get('job')!=j['id']:continue
            text=f'EINSATZUPDATE {j["incident_number"]} | Alarmierungsstichwort: {j["code"]} – {j["title"]} | Zusatz: {j.get("additional") or "—"}'
            for channel in ('SDS','ESApp'):
                self.state['messages'].append(dict(job=j['id'],vehicle=v['id'],channel=channel,time=self.state['clock'],text=text));self.log(f'{v["callsign"]} ← {text}',channel)
        self.state['messages']=self.state['messages'][-250:]
