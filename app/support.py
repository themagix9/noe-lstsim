"""Simulated neighbour dispatch requests; never contacts a real control centre."""
import uuid

SUPPORT_TYPES=('KTW','KTW-B','BKTW','RTW','RTW-C','NEF','NAH')

class Support:
    def upgrade_support(self):
        if self.state.get('support_version')==1:return
        from fleet import defaults
        sites=[
            ('c15','Christophorus 15 · Ybbsitz','01','Niederösterreich',47.969110,14.939298,'Haselgraben 69, 3341 Ybbsitz','https://www.oeamtc.at/standorte/niederoesterreich/'),
            ('c16','Christophorus 16 · Oberwart','BG','Burgenland',47.288,16.214,'Am Flugfeld 21, 7400 Oberwart','https://www.oeamtc.at/standorte/burgenland/'),
        ]
        for id,name,dispo,region,lat,lon,address,source in sites:
            if not any(s['id']==id for s in self.state['stations']):
                self.state['stations'].append(dict(id=id,name=name,dispo=dispo,region=region,zone=region,lat=lat,lon=lon,address=address,source=source,external=True,support_only=True,coordinate_accuracy='Öffentliche Standortangabe; Kartenpunkt noch zu prüfen'))
            call='C'+id[1:]
            if not any(v['callsign']==call for v in self.state['vehicles']):
                v={'id':uuid.uuid4().hex[:12],**defaults(call,'NAH',id),'job':None,'reservation':None,'phase_due':None,'leg':None,'manual_out':False,'ack_deadline':None,'alarm_from':'ready','lat':lat,'lon':lon,'duty_managed':False,'daylight_start':7*60,'source':source+' · Tageslichtdienst simuliert; Fluggeschwindigkeit Übungsannahme'}
                v['status']=self.idle_status(v);self.state['vehicles'].append(v)
        # Remove only unbound leadership cars from the original photo seed.
        self.state['vehicles'][:]=[v for v in self.state['vehicles'] if not(v['type']=='BEL' and v.get('source','').startswith(('Kennung/Typ: Nutzerfoto','Nutzerbestätigung')) and not v.get('job') and not v.get('reservation'))]
        self.state['support_version']=1

    def support_required(self,v):
        s=self.station(v['station'])
        return bool(s.get('support_only') or s.get('dispo')!=self.state['setup']['dispo'])

    def support_reason(self,v,j,request=None):
        if not self.in_shift(v):return 'Außerhalb der Dienstzeit oder unbesetzt'
        if v.get('manual_out') or v['status']=='out':return 'Außer Betrieb'
        if v.get('job') or v['status'] not in ('ready','radio'):return 'Ressource derzeit gebunden'
        if v.get('reservation'):return 'Für einen anderen Auftrag vordisponiert'
        if v.get('support_request') and v['support_request']!=request:return 'Andere Unterstützungsanfrage läuft'
        if v.get('support_job') and v['support_job']!=j['id']:return 'Noch an einen anderen Einsatzbereich übergeben'
        if not self.eligible(v,j):return 'Für diesen Auftrag ungeeigneter Fahrzeugtyp'
        return None

    def support_catalog(self):
        result=[]
        for v in self.state['vehicles']:
            if v['type'] not in SUPPORT_TYPES or not self.support_required(v):continue
            s=self.station(v['station'])
            result.append(dict(vehicle=v['id'],callsign=v['callsign'],type=v['type'],station=s['name'],region=s.get('region','Niederösterreich'),dispo=s['dispo'],status=v['status'],in_shift=self.in_shift(v)))
        return result

    def request_support(self,data):
        j=self.get('jobs',data['job']);v=self.get('vehicles',data['vehicle'])
        if not j['accepted'] or j['status']=='done':raise ValueError('Einen angenommenen, offenen Einsatz wählen.')
        if not j.get('code_confirmed'):raise ValueError('Zuerst das Alarmierungsstichwort auswählen und speichern.')
        if j.get('call',{}).get('state') not in (None,'ended'):raise ValueError('Zuerst die Anrufabfrage abschließen.')
        if not self.support_required(v) or v['type'] not in SUPPORT_TYPES:raise ValueError('Eine externe Rettungsressource wählen.')
        if j['kind']=='transport' and j['vehicles']:raise ValueError('Transportauftrag bereits disponiert.')
        if any(r['vehicle']==v['id'] and r['state']=='pending' for r in j.get('support_requests',[])):raise ValueError('Die Unterstützungsanfrage läuft bereits.')
        r=dict(id=uuid.uuid4().hex[:12],vehicle=v['id'],callsign=v['callsign'],type=v['type'],state='pending',created=self.state['clock'],reply_due=self.state['clock']+45,reason=str(data.get('reason','Unterstützung benötigt')).strip()[:250] or 'Unterstützung benötigt')
        j.setdefault('support_requests',[]).append(r)
        if not self.support_reason(v,j):v['support_request']=r['id']
        self.log(f'LEO → Unterstützung {self.station(v["station"])["name"]}: Bitte {v["type"]} {v["callsign"]} zu Einsatz {j["incident_number"]}, {j["address"]}. Grund: {r["reason"]}.','Telefon')

    def cancel_support(self,data):
        j=self.get('jobs',data['job']);r=next((r for r in j.get('support_requests',[]) if r['id']==data.get('request')),None)
        if not r or r['state']!='pending':raise ValueError('Keine offene Unterstützungsanfrage.')
        self.finish_support_request(j,r,'cancelled','Anfrage durch Disposition zurückgezogen')

    def finish_support_request(self,j,r,status,reason):
        v=self.get('vehicles',r['vehicle'])
        if v.get('support_request')==r['id']:v['support_request']=None
        r.update(state=status,reply=self.state['clock'],response=reason)
        self.log(f'Unterstützung {self.station(v["station"])["name"]} → LEO · Einsatz {j["incident_number"]}: {reason}.','Telefon')

    def update_support(self,now):
        for v in self.state['vehicles']:
            if v.get('support_job') and not v.get('job') and not v.get('leg') and v['status'] in ('ready','out'):v['support_job']=None
        for j in self.state['jobs']:
            for r in j.get('support_requests',[]):
                if r['state']!='pending':continue
                if j['status']=='done':self.finish_support_request(j,r,'cancelled','Einsatz bereits abgeschlossen');continue
                if now<r['reply_due']:continue
                v=self.get('vehicles',r['vehicle']);reason=self.support_reason(v,j,r['id'])
                if j['kind']=='transport' and j['vehicles']:reason='Transportauftrag inzwischen disponiert'
                if reason:self.finish_support_request(j,r,'declined',v['callsign']+' kann nicht übernommen werden: '+reason);continue
                v['support_request']=None;v['support_job']=j['id']
                try:self.dispatch({'job':j['id'],'vehicles':[v['id']]})
                except ValueError as error:
                    v['support_job']=None;self.finish_support_request(j,r,'declined',str(error));continue
                self.finish_support_request(j,r,'accepted',v['callsign']+' wird geschickt; Alarmierung über SDS und ESApp übermittelt')
