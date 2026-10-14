import copy
import unittest
from unittest.mock import patch
import test_fleet as helpers

class AgencyTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    job=helpers.FleetTests.job
    vehicle=helpers.FleetTests.vehicle
    def request(self,kind='fire',task='assist'):
        j=self.job();j['code_confirmed']=True
        return j,self.e.agency_request({'job':j['id'],'kind':kind,'task':task})
    def step(self,now):
        self.e.state['clock']=now;self.e.update_agencies(now)
    def arrive(self,j,r):
        v=next(v for v in self.e.state['agency_units'] if v['id']==r['unit'])
        self.step(v['phase_due']);self.assertEqual(v['status'],'enroute');self.step(v['leg']['end']);return v
    def test_finite_fleet_and_timed_task_return(self):
        j,r=self.request();v=self.arrive(j,r);self.assertEqual(r['status'],'working');self.assertEqual(v['status'],'scene')
        self.step(r['work_due']);self.assertEqual(r['status'],'onscene');self.assertIsNotNone(r['task_completed'])
        self.e.agency_release({'job':j['id'],'request':r['id']});self.assertEqual(r['status'],'cancelled');self.assertIsNone(v['job'])
        if v['leg']:self.step(v['leg']['end'])
        self.assertEqual(v['status'],'ready')
    def test_extrication_blocks_transport_until_completed(self):
        j,r=self.request(task='extrication');v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});v.update(status='scene',assessment_due=0)
        self.assertIsNone(self.e.agency_gate(j));self.assertTrue(self.e.agency_gate(j,'transport'))
        self.e.start_transport(v);self.assertEqual(v['status'],'scene');self.assertTrue(v['agency_transport_wait'])
        self.arrive(j,r);self.step(r['work_due']);self.assertIsNone(self.e.agency_gate(j,'transport'));self.assertFalse(v.get('agency_transport_wait',False))
        j['destination']='kh-hainburg';self.e.start_transport(v);self.assertEqual(v['status'],'transport')
    def test_safety_blocks_assessment_and_cancel_does_not_clear_danger(self):
        j,r=self.request('police','safety');v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});v.update(status='scene',assessment_due=self.e.state['clock'])
        self.e.update_assessments(self.e.state['clock']);self.assertFalse(j['patient_condition']['reported'])
        self.e.agency_release({'job':j['id'],'request':r['id']});self.assertTrue(self.e.agency_gate(j))
        r=self.e.agency_request({'job':j['id'],'kind':'police','task':'safety'});self.arrive(j,r);self.step(r['work_due']);self.assertIsNone(self.e.agency_gate(j));self.assertGreater(v['assessment_due'],self.e.state['clock'])
    def test_last_rd_release_releases_agencies_without_keeping_incident_open(self):
        j,r=self.request();v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});self.e.detach(v)
        self.assertEqual(j['status'],'done');self.assertEqual(r['status'],'released');self.assertTrue(all(u.get('job')!=j['id'] for u in self.e.state['agency_units']))
    def test_wait_queue_allocates_only_when_unit_becomes_free(self):
        for u in self.e.state['agency_units']:u['status']='out'
        j,r=self.request('police');self.assertEqual(r['status'],'waiting');self.assertIsNone(r['unit'])
        unit=next(u for u in self.e.state['agency_units'] if u['kind']=='police');unit['status']='ready'
        self.step(self.e.state['clock']);self.assertEqual(r['unit'],unit['id']);self.assertEqual(r['status'],'alarmed')
        other=self.job();other['code_confirmed']=True;r2=self.e.agency_request({'job':other['id'],'kind':'police'});self.assertEqual(r2['status'],'waiting')
    def test_real_road_geometry_and_pending_does_not_move(self):
        j,r=self.request();v=next(v for v in self.e.state['agency_units'] if v['id']==r['unit'])
        class Road:
            enabled=True
            def route(self,*args):return {'status':'pending'}
        self.e.router=Road();origin=(v['lat'],v['lon']);self.step(v['phase_due']);self.assertTrue(v['leg']['waiting']);self.step(self.e.state['clock']+1000);self.assertEqual((v['lat'],v['lon']),origin)
        from routing import cumulative
        geometry=[[v['lat'],v['lon']],[v['lat'],j['lon']],[j['lat'],j['lon']]]
        self.e.router.route=lambda *args:dict(status='ready',seconds=600,geometry=geometry,cumulative=cumulative(geometry),distance_m=10000)
        self.step(self.e.state['clock']+1);self.assertEqual(v['leg']['geometry'],geometry);self.step(self.e.state['clock']+200);self.assertNotEqual((v['lat'],v['lon']),origin)
    def test_radio_confirmation_creates_real_support_and_task(self):
        j=self.job();v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});v.update(status='scene',assessment_due=0)
        c=self.e.raise_radio(j,v,'Feuerwehr','Patient eingeklemmt, technische Rettung erforderlich.',True)
        for step in ('listen','confirm'):self.e.radio_action({'job':j['id'],'call':c['id'],'step':step})
        self.assertEqual(j['agency_requests'][0]['task'],'extrication');self.assertIsNotNone(j['agency_requests'][0]['unit'])
    def test_additional_edit_while_transporting_is_independent_and_sends_updates(self):
        j=self.job();v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});v['status']='transport';before=copy.deepcopy(v);code=j['code']
        self.e.command('job_additional',{'job':j['id'],'additional':'Zugang über Hof','previous':j['additional']})
        self.assertEqual(v,before);self.assertEqual(j['code'],code);self.assertEqual(j['additional'],'Zugang über Hof')
        self.assertEqual({m['channel'] for m in self.e.state['messages'] if m['text'].startswith('EINSATZUPDATE')},{'SDS','ESApp'})
        with self.assertRaises(ValueError):self.e.command('job_additional',{'job':j['id'],'additional':'Konflikt','previous':''})
        j['owner']='owner'
        with self.assertRaises(ValueError):self.e.command('job_additional',{'job':j['id'],'additional':'Fremd','_actor':{'id':'other','name':'Other'}})
    def test_pacing_uses_real_seconds_and_survives_pause_and_reload(self):
        with patch.dict('os.environ',{'RADIO_INTERVAL':'2'}),patch('radio_pacing.time.time',return_value=100):
            self.e.log('Erste Meldung');self.e.log('Zweite Meldung');self.e.log('Dritte Meldung');self.assertEqual(len(self.e.state['radio_pending']),2)
        self.e.state['paused']=True
        self.e.state['clock']+=3600
        with patch.dict('os.environ',{'RADIO_INTERVAL':'2'}),patch('radio_pacing.time.time',return_value=101.9):self.e.snapshot();self.assertEqual(len(self.e.state['radio_pending']),2)
        with patch.dict('os.environ',{'RADIO_INTERVAL':'2'}),patch('radio_pacing.time.time',return_value=102):self.e.snapshot();self.assertEqual(len(self.e.state['radio_pending']),1)
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path)
        with patch.dict('os.environ',{'RADIO_INTERVAL':'2'}),patch('radio_pacing.time.time',return_value=200):self.e.snapshot();self.assertFalse(self.e.state['radio_pending']);self.assertEqual(self.e.state['logs'][0]['text'],'Dritte Meldung')
    def test_scene_report_offers_only_surplus_approaching_units(self):
        j=self.job();j['patient_condition'].update(percent=0,notarzt_required=True)
        a=self.vehicle('77/002');nef=self.vehicle('77/099');extra=self.vehicle('77/004');self.e.dispatch({'job':j['id'],'vehicles':[a['id'],nef['id'],extra['id']]})
        a.update(status='scene',assessment_due=0);nef.update(status='scene',assessment_due=0);extra['status']='enroute';j['scene_report']={'text':'Reanimation läuft.'}
        c=self.e.raise_scene_radio(j,nef);self.e.radio_action({'job':j['id'],'call':c['id'],'step':'listen'})
        self.assertIn('Laufende Reanimation',c['report']);self.assertIn('77/002 bereits vor Ort',c['report']);self.assertEqual(c['cancel_candidates'],[extra['id']])
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'cancel_excess','vehicles':[extra['id']]});self.assertIsNone(extra['job']);self.assertEqual(nef['job'],j['id'])
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'end'});self.assertEqual(c['state'],'closed');self.assertEqual(self.e.state['logs'][0]['text'],'LEO verstanden, Ende.')

    def test_support_permissions_and_persistence(self):
        j,r=self.request('police','safety');j['owner']='owner';unit=r['unit']
        with self.assertRaises(ValueError):self.e.command('agency_release',{'job':j['id'],'request':r['id'],'_actor':{'id':'other','name':'Other'}})
        self.assertEqual(r['status'],'alarmed');self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);restored=self.e.get('jobs',j['id'])
        self.assertEqual(restored['agency_requests'][0]['unit'],unit);self.assertTrue(self.e.agency_gate(restored))
        self.assertEqual(next(v for v in self.e.state['agency_units'] if v['id']==unit)['job'],j['id'])

    def test_arriving_doctor_gets_own_situation_request_after_first_crew_report(self):
        j=self.job();a=self.vehicle('77/002');nef=self.vehicle('77/099');self.e.dispatch({'job':j['id'],'vehicles':[a['id'],nef['id']]})
        a.update(status='scene',assessment_due=0);self.e.patient_report(j,a)
        nef.update(status='scene',assessment_due=0);self.e.patient_report(j,nef)
        self.assertTrue(any(c['kind']=='Lagemeldung' and c['vehicle']==nef['id'] for c in self.e.state['radio_calls']))

    def test_automatic_transport_codes_match_mobility_and_manual_stays_unconfirmed(self):
        for _ in range(20):
            j=self.e.new_job('transport')
            self.assertTrue(j['code_confirmed']);self.assertEqual(self.e.rule(j['code'])['kind'],'transport')
            mode=j['transport_mode'];title=self.e.rule(j['code'])['title'].lower()
            self.assertIn({'gehfaehig':'gehfähig','tragstuhl':'tragstuhl','liegend':'liegend'}[mode],title)
            self.assertEqual(self.e.eligible(self.vehicle('77/020'),j),mode=='gehfaehig')
        manual=self.e.new_job('transport',manual=True);self.assertFalse(manual.get('code_confirmed',False))

    def test_all_rd9_codes_alarm_virtual_ecpr_without_helicopter(self):
        from aao import CODES
        codes=[code for code in CODES if code.startswith('RD-9') and len(code)>4 and not code[4].isdigit()]
        for code in codes:
            j=self.job();self.e.edit_job({'job':j['id'],'code':code});v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]})
            self.assertEqual(j['ecpr_team']['status'],'alarmed',code);self.assertTrue(j['ecpr_team']['virtual']);self.e.detach(v)
            self.assertNotIn('ecpr_team',j);self.assertEqual(j['status'],'done');v.update(status='ready',phase_due=None,leg=None)
    def test_active_code_upgrade_preserves_patient_and_units_and_deduplicates_ecpr(self):
        j=self.job();v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});v.update(status='scene',assessment_due=0)
        before=copy.deepcopy(v);patient=copy.deepcopy(j['patient_condition'])
        self.e.command('job_code',{'job':j['id'],'code':'RD-9E1'});self.assertEqual(v,before);self.assertEqual(j['patient_condition'],patient)
        id=j['ecpr_team']['id'];self.e.command('job_code',{'job':j['id'],'code':'RD-9E1'});self.assertEqual(j['ecpr_team']['id'],id)
        self.assertEqual(len([l for l in self.e.state['logs'] if l['text'].startswith('eCPR AKH alarmiert')]),1)
        self.assertEqual(j['code_history'][-1]['after'],'RD-9E1')
    def test_ecpr_ready_on_transport_removed_after_handover_and_persisted(self):
        j=self.job();v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});v.update(status='scene',assessment_due=0)
        self.e.command('job_code',{'job':j['id'],'code':'RD-9E1'});j['destination']='kh-hainburg';self.e.start_transport(v)
        self.assertEqual(j['ecpr_team']['status'],'ready');self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);j=self.e.get('jobs',j['id']);v=self.e.get('vehicles',v['id']);self.assertEqual(j['ecpr_team']['status'],'ready')
        self.e.advance(v);self.assertIn('ecpr_team',j);self.e.advance(v);self.assertNotIn('ecpr_team',j);self.assertEqual(j['status'],'done')
    def test_reclassification_during_transport_marks_ecpr_ready_immediately(self):
        j=self.job();v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});v.update(status='scene',assessment_due=0);j['destination']='kh-hainburg';self.e.start_transport(v)
        before=copy.deepcopy(v['leg']);self.e.command('job_code',{'job':j['id'],'code':'RD-9E1'})
        self.assertEqual(j['ecpr_team']['status'],'ready');self.assertEqual(v['leg'],before)
