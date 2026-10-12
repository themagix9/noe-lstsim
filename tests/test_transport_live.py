import os
import unittest
from unittest.mock import patch
import test_fleet as helpers
from catalog import TRANSPORT_RULES
from routing import cumulative

class TransportLiveTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job
    def test_transport_codes_are_separate_and_manual_code_required(self):
        self.assertEqual(len(TRANSPORT_RULES),27)
        self.assertEqual(self.e.rule('KTR-93Y2')['kind'],'transport')
        self.assertTrue(self.e.rule('KTR-94B1')['signal'])
        with self.assertRaises(ValueError):self.e.create_job({'address':'Test','lat':48,'lon':16})
        j=self.e.create_job({'kind':'transport','code':'KTR-90K3','address':'Test','lat':48,'lon':16,'destination':'kh-moedling'})
        self.assertEqual(j['code'],'KTR-90K3');self.assertEqual(j['kind'],'transport')
    def test_status_four_moves_along_hospital_route(self):
        j=self.job('transport');v=self.vehicle('77/003');v.update(job=j['id'],status='scene',lat=j['lat'],lon=j['lon']);j['vehicles']=[v['id']]
        h=self.e.get('hospitals',j['destination']);geometry=[[v['lat'],v['lon']],[v['lat'],h['lon']],[h['lat'],h['lon']]]
        class Road:
            enabled=True
            def route(self,*args):return {'status':'ready','seconds':600,'geometry':geometry,'cumulative':cumulative(geometry),'distance_m':12000}
        self.e.router=Road();self.e.start_transport(v);origin=(v['lat'],v['lon']);self.e.update_operations(self.e.state['clock']+300)
        self.assertEqual(v['status'],'transport');self.assertNotEqual((v['lat'],v['lon']),origin)
        self.assertEqual((v['leg']['target_lat'],v['leg']['target_lon']),(h['lat'],h['lon']))
        v['leg']=None;self.e.update_operations(self.e.state['clock']+301);self.assertIsNotNone(v['leg'])
    def test_patient_game_status_triggers_nef_request(self):
        j=self.job();v=self.vehicle('77/002');v.update(job=j['id'],status='scene');j['vehicles']=[v['id']]
        self.e.ensure_patient_condition(j);j['patient_condition'].update(percent=20,notarzt_required=True)
        with patch.dict(os.environ,{'REINFORCEMENTS_AUTO':'1'}):self.e.patient_report(j,v)
        self.assertEqual(self.e.state['radio_calls'][-1]['kind'],'NEF')
        self.assertTrue(j['patient_condition']['reported']);self.assertIn('keine medizinische',j['patient_condition']['model'])
    def test_stable_patient_reports_no_doctor_required(self):
        j=self.job();v=self.vehicle('77/002');v.update(job=j['id'],status='scene');j['vehicles']=[v['id']]
        j['patient_condition'].update(percent=90,notarzt_required=False)
        self.e.patient_report(j,v);self.assertFalse(self.e.state['radio_calls'])
        self.assertTrue(any('kein Notarztmittel' in l['text'] for l in self.e.state['logs']))
    def test_numeric_status_reports_use_status_channel(self):
        v=self.vehicle('77/002');self.e.vehicle_status({'vehicle':v['id'],'status':'6'})
        self.assertEqual(self.e.state['logs'][0]['channel'],'Status')
    def test_generated_pickups_are_half_hour_slots(self):
        self.e.state['clock']=8*3600+123
        for _ in range(20):
            j=self.e.new_job('transport');self.assertEqual(j['due']%1800,0);self.assertGreater(j['due'],self.e.state['clock'])
    def test_manual_pickup_rejects_quarter_hour_and_can_be_edited(self):
        payload={'kind':'transport','code':'KTR-90K3','address':'Test','lat':48,'lon':16,'destination':'kh-moedling'}
        with self.assertRaises(ValueError):self.e.create_job({**payload,'due':8*3600+900})
        j=self.e.create_job({**payload,'due':9*3600})
        self.e.edit_job({'job':j['id'],'due':9*3600+1800});self.assertEqual(j['due'],9*3600+1800)
        with self.assertRaises(ValueError):self.e.edit_job({'job':j['id'],'due':9*3600+100})
