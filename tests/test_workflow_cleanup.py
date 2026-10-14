"""Incident lifecycle, stale radio closure, BKTW restrictions and municipal pools."""
import unittest
import test_fleet as helpers

class WorkflowCleanupTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job

    def test_stale_request_can_end_after_last_unit_left(self):
        j=self.job();v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});self.e.depart(v);self.e.advance(v);v.pop('assessment_due',None)
        call=self.e.raise_radio(j,v,'NEF');self.e.radio_action({'job':j['id'],'call':call['id'],'step':'listen'})
        self.e.detach(v);self.e.drive(v,self.e.home(v),'radio')
        self.assertEqual(j['status'],'done');self.assertEqual(j['vehicles'],[])
        self.e.command('radio',{'job':j['id'],'call':call['id'],'step':'end'})
        self.assertEqual(call['state'],'closed');self.assertEqual(v['status'],'radio')
        self.assertIn('Hier LEO, verstanden, Ende.',[l['text'] for l in self.e.state['logs']])

    def test_end_resumes_scene_and_preserves_other_owner(self):
        j=self.job();v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});v.update(status='scene',assessment_due=0)
        call=self.e.raise_radio(j,v);self.e.radio_action({'job':j['id'],'call':call['id'],'step':'listen'});j['owner']='one'
        with self.assertRaises(ValueError):self.e.command('radio',{'job':j['id'],'call':call['id'],'step':'end','_actor':{'id':'two','name':'Two'}})
        self.e.command('radio',{'job':j['id'],'call':call['id'],'step':'end','_actor':{'id':'one','name':'One'}})
        self.assertIsNotNone(v['phase_due']);self.assertEqual(call['state'],'closed')

    def test_only_last_bound_unit_completes_job_even_with_police_and_fire(self):
        j=self.job();a=self.vehicle('77/002');b=self.vehicle('77/004');self.e.dispatch({'job':j['id'],'vehicles':[a['id'],b['id']]});j.update(police=True,fire=True)
        self.e.detach(a);self.assertEqual(j['vehicles'],[b['id']]);self.assertNotEqual(j['status'],'done')
        self.e.detach(b);self.assertEqual(j['vehicles'],[]);self.assertEqual(j['status'],'done');self.assertIn('completed',j)

    def test_last_storno_completes_instead_of_reopening_job(self):
        j=self.job();v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});self.e.contact_resource({'job':j['id'],'vehicle':v['id']});c=self.e.state['radio_calls'][-1]
        for step in ('answer','cancel'):self.e.cancellation_action({'job':j['id'],'call':c['id'],'step':step})
        self.assertEqual(j['status'],'done');self.assertEqual(j['vehicles'],[])

    def test_bktw_only_explicitly_ambulant_patient_transport(self):
        v=self.vehicle('77/020');j=self.job('transport')
        for code,allowed in [('KTR-93Y1',True),('KTR-93Y2',False),('KTR-90K3',False),('SIM-KT',False)]:
            j.update(code=code,detail='',additional='');self.assertEqual(self.e.eligible(v,j),allowed)
        j.update(code='KTR-93Y1',detail='Patient liegend');self.assertFalse(self.e.eligible(v,j))
        j.update(code='KTR-90K3',detail='')
        with self.assertRaises(ValueError):self.e.reserve({'job':j['id'],'vehicle':v['id']})
        with self.assertRaises(ValueError):self.e.dispatch({'job':j['id'],'vehicles':[v['id']]})
        self.assertFalse(self.e.eligible(v,self.job()))

    def test_pool_chooses_nearest_and_numbers_on_acknowledgement(self):
        j=self.job();members=[v for v in self.e.state['vehicles'] if v.get('fr_pool')=='leopoldsdorf'];self.assertEqual(len(members),5)
        nearest=self.e.nearest_responder(members[0],j)
        self.e.dispatch({'job':j['id'],'vehicles':[members[-1]['id']]})
        self.assertEqual(j['vehicles'],[nearest['id']]);self.assertNotIn('fr_number',nearest)
        with self.assertRaises(ValueError):self.e.vehicle_status({'vehicle':nearest['id'],'status':'9'})
        self.e.advance(nearest);self.assertEqual(nearest['status'],'enroute');self.assertIsNone(nearest['ack_deadline']);self.assertEqual(nearest['fr_number'],1)
        second=self.e.nearest_responder(members[0],j);self.assertNotEqual(nearest['id'],second['id'])
        self.e.dispatch({'job':j['id'],'vehicles':[second['id']]});self.e.advance(second);self.assertEqual(second['status'],'enroute');self.assertEqual(second['fr_number'],2)
        self.assertEqual(self.e.radio_name(nearest),'FR Leopoldsdorf 1');self.assertEqual(self.e.radio_name(second),'FR Leopoldsdorf 2')
        self.e.detach(nearest);self.assertNotIn('fr_number',nearest)

    def test_automatic_patient_report_is_acknowledged_without_request(self):
        j=self.job();v=self.vehicle('77/002');v.update(job=j['id'],status='scene');j['vehicles']=[v['id']];j['patient_condition'].update(percent=90,notarzt_required=False,reported=False)
        self.e.patient_report(j,v);c=self.e.state['radio_calls'][-1];self.assertEqual(c['kind'],'Lagemeldung');self.assertEqual(c['state'],'calling')
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'listen'});self.assertEqual(c['state'],'awaiting_end')
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'end'});self.assertEqual(self.e.state['logs'][0]['text'],'LEO verstanden, Ende.')

    def test_explicit_vienna_exercise_always_has_a_patient(self):
        for _ in range(4):
            self.e.command('generate',{'kind':'emergency','crew_target':'kh-donaustadt'})
            j=self.e.state['jobs'][-1]
            self.assertEqual(j['event_title'],'Bewusstlose Person')
            self.assertEqual(j['crew_target'],'kh-donaustadt')
            self.assertIsNotNone(j['patient_condition'])
            self.assertFalse(j.get('_scenario',{}).get('no_patient'))
