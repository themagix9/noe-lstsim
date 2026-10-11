import copy
import unittest
import test_fleet as helpers

class AirStaffingTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job
    def test_night_minimum_and_fixed_c(self):
        self.e.state['clock']=23*3600
        active=[v for v in self.e.state['vehicles'] if v['station']=='schwechat' and v['type'] in ('NEF','RTW-C','RTW','KTW') and self.e.in_shift(v)]
        self.assertGreaterEqual(len(active),3)
        self.assertTrue(self.e.in_shift(self.vehicle('77/030')))
        self.assertLess(len(active),16)
    def test_all_ground_daytime_and_roster_stability(self):
        self.e.state['clock']=8*3600
        self.assertTrue(all(self.e.in_shift(v) for v in self.e.state['vehicles'] if v['type'] not in ('NAH','FR') and v['staffed']))
        self.e.state['clock']=23*3600;plan=self.e.staff_plan()[:];self.e.state['clock']+=3600
        self.assertEqual(plan,self.e.staff_plan());self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);self.assertEqual(plan,self.e.staff_plan())
    def test_fr_home_and_no_wache_or_ack_deadline(self):
        fr=self.vehicle('FR-FIS-01');self.assertEqual(fr['status'],'fr_ready');home=(fr['lat'],fr['lon'])
        with self.assertRaises(ValueError):self.e.vehicle_status({'vehicle':fr['id'],'status':'1'})
        self.e.vehicle_status({'vehicle':fr['id'],'status':'8'});self.assertIsNone(fr['ack_deadline'])
        j=self.job();self.e.dispatch({'job':j['id'],'vehicles':[fr['id']]});self.e.depart(fr);self.e.advance(fr);self.e.advance(fr);self.e.advance(fr)
        self.assertEqual(fr['status'],'fr_ready');self.assertEqual((fr['lat'],fr['lon']),home)
    def test_fifteen_distinct_fischamend_homes(self):
        fr=[v for v in self.e.state['vehicles'] if v['organization']=='FR Fischamend']
        self.assertEqual(len(fr),15);self.assertEqual(len({(v['home_lat'],v['home_lon']) for v in fr}),15)
        self.assertTrue(all(48.10<v['lat']<48.13 and 16.59<v['lon']<16.63 for v in fr))
    def ecpr_job(self,ongoing=True):
        j=self.job();self.e.edit_job({'job':j['id'],'code':'RD-9E1'});j['exercise_cpr']=ongoing
        self.e.state['clock']=12*3600;nah=self.vehicle('C9');rtw=self.vehicle('77/001');nef=self.vehicle('77/099')
        self.e.dispatch({'job':j['id'],'vehicles':[nah['id'],rtw['id'],nef['id']]})
        self.e.depart(nah);self.e.advance(nah);self.e.advance(nah)
        return j,nah,rtw,nef
    def test_9e1_aao_does_not_replace_nef_by_nah(self):
        j=self.job();self.e.edit_job({'job':j['id'],'code':'RD-9E1'})
        result=self.e.recommendation(j);self.assertCountEqual([self.e.get('vehicles',id)['type'] for id in result['vehicles']],['RTW-C','NEF']);self.assertTrue(j['police'])
    def test_ecpr_waits_for_radio_and_only_hospital_alert(self):
        j,nah,rtw,nef=self.ecpr_job();self.assertEqual(j['ecpr_state'],'awaiting_question');self.assertEqual(nah['status'],'scene');self.assertIsNone(j['destination'])
        self.assertTrue(any(l['channel']=='eCPR' for l in self.e.state['logs']))
        with self.assertRaises(ValueError):self.e.request_bed({'job':j['id'],'hospital':'kh-akh-ecpr'})
        self.e.ask_cpr({'job':j['id']});self.e.update_air(self.e.state['clock']+29);self.assertIsNone(j['cpr_confirmed'])
        self.e.update_air(self.e.state['clock']+30);self.assertTrue(j['cpr_confirmed']);self.assertEqual(j['requested_destination'],'kh-akh-ecpr')
        with self.assertRaises(ValueError):self.e.request_bed({'job':j['id'],'hospital':'kh-donaustadt'})
    def test_ecpr_flight_after_case_to_single_carrier(self):
        j,nah,rtw,nef=self.ecpr_job();self.e.ask_cpr({'job':j['id']});self.e.update_air(self.e.state['clock']+30)
        self.e.request_bed({'job':j['id'],'hospital':'kh-akh-ecpr'});self.e.update_operations(self.e.state['clock']+30)
        self.e.send_case({'job':j['id'],'channel':'ESApp'});self.assertEqual(nah['status'],'transport');self.assertNotEqual(rtw['status'],'transport')
        self.e.advance(nah);self.assertEqual(nah['status'],'hospital');self.e.advance(nah);self.assertTrue(j['patient_delivered'])
    def test_no_cpr_no_ecpr_destination(self):
        j,nah,_,_=self.ecpr_job(False);self.e.ask_cpr({'job':j['id']});self.e.update_air(self.e.state['clock']+30)
        self.assertFalse(j['cpr_confirmed']);self.assertEqual(j['ecpr_state'],'not_required');self.assertEqual(j['requested_destination'],'kh-donaustadt')
    def test_normal_air_transport_carrier_and_landing_validation(self):
        j=self.job();self.e.state['clock']=12*3600;nah=self.vehicle('C3');self.e.dispatch({'job':j['id'],'vehicles':[nah['id']]})
        self.e.depart(nah);self.e.advance(nah);j['crew_target']='kh-hainburg';self.e.advance(nah);self.assertEqual(nah['status'],'transport')
        self.e.advance(nah);self.e.advance(nah);self.assertEqual(j['status'],'done')
