"""User-defined 9E1/eCPR scenario; no clinical decision rules or live alerts."""
class AirOps:
    def patient_carrier(self,j):
        if j.get('carrier'):return self.get('vehicles',j['carrier'])
        units=[self.get('vehicles',id) for id in j['vehicles'] if self.get('vehicles',id)['job']==j['id'] and self.get('vehicles',id)['type'] in ('KTW','KTW-B','BKTW','RTW','RTW-C','NAH')]
        ground=[v for v in units if v['type']!='NAH']
        return (ground or units or [None])[0]

    def choose_carrier(self,data):
        j=self.get('jobs',data['job']);v=self.get('vehicles',data['vehicle'])
        active=[self.get('vehicles',id) for id in j['vehicles'] if self.get('vehicles',id)['job']==j['id']]
        if v not in active or v['type'] not in ('KTW','KTW-B','BKTW','RTW','RTW-C','NAH') or v['status'] not in ('assigned','acknowledged','enroute','scene'):raise ValueError('Eine alarmierte transportierende Ressource vor Transportbeginn wählen.')
        if any(u['status'] in ('transport','hospital') for u in active):raise ValueError('Patient ist bereits unterwegs.')
        if j.get('ecpr_state','none')!='none' and v['type']!='NAH':raise ValueError('eCPR-Szenario benötigt den vorgesehenen Hubschrauber.')
        if v['type']!='NAH' and self.ongoing_cpr(j,v):raise ValueError('Transport unter laufender Reanimation nur durch einen NAH.')
        j['carrier']=v['id'];v['phase_due']=self.state['clock']+1 if v['status']=='scene' else v['phase_due'];self.log(f'Mannschaft / Leitstelle: Patiententransport durch {v["callsign"]} abgestimmt.','Funk')

    def ecpr_precall(self,j):
        if not self.ecpr_trigger(j) or j.get('ecpr_state','none')!='none':return
        j.update(ecpr_state='prealerted',cpr_confirmed=None,cpr_due=None)
        j.setdefault('exercise_cpr',j['_scenario']['initial_percent']==0 if j.get('_scenario') else __import__('random').random()<.65)
        self.log(f'eCPR Wien: Voranmeldung für Einsatz {j["id"]}; Team bleibt im Krankenhaus, keine Anfahrt zum Einsatzort.','eCPR')

    def ask_cpr(self,data):
        j=self.get('jobs',data['job']);carrier=self.patient_carrier(j)
        if j.get('ecpr_state')!='awaiting_question' or not carrier or carrier['status']!='scene':raise ValueError('Mannschaft muss vor Ort transportbereit sein.')
        j.update(ecpr_state='question_sent',cpr_due=self.state['clock']+30)
        self.log(f'Leitstelle an {carrier["callsign"]}: Transportiert ihr unter laufender Reanimation? Bitte Rückmeldung.','Funk')

    def update_air(self,now):
        for j in self.state['jobs']:
            if j['status']=='done':
                if j.get('cpr_due') is not None:j.update(cpr_due=None,ecpr_state='closed')
                continue
            if j.get('ecpr_state')=='question_sent' and now>=j['cpr_due']:
                ongoing=j.get('exercise_cpr',True);j['cpr_confirmed']=ongoing;j['cpr_due']=None;j['ecpr_state']='confirmed' if ongoing else 'not_required'
                carrier=self.patient_carrier(j)
                self.log(f'{carrier["callsign"]} an Leitstelle: '+('Transport unter laufender Reanimation vorgesehen.' if ongoing else 'Kein Transport unter laufender Reanimation; kein eCPR-Ziel erforderlich.'),'Funk')
                j['bed_state']='none';j['crew_target']='kh-akh-ecpr' if ongoing else 'kh-donaustadt';self.crew_destination(carrier)
