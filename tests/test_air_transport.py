import unittest
from unittest.mock import patch
import test_telemedicine as telemedicine_tests
import test_fleet as helpers

class AirTransportTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job
    scene=telemedicine_tests.TelemedicineTests.scene

    def request(self,j,v,seconds=3000):
        with patch.object(self.e.router,'cached_eta',return_value={'status':'ready','seconds':seconds}):return self.e.maybe_request_transport_heli(j,v,self.e.get('hospitals','kh-hainburg'))

    def test_long_critical_ground_transfer_requests_heli_once_and_can_be_denied(self):
        j,v=self.scene(30);self.assertTrue(self.request(j,v));c=self.e.state['radio_calls'][-1]
        self.assertEqual(c['kind'],'NAH');self.assertIn('verfügbar',c['reason'])
        self.assertTrue(self.request(j,v));self.assertEqual(sum(c['kind']=='NAH' for c in self.e.state['radio_calls']),1)
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'listen'})
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'unavailable'})
        self.assertFalse(self.e.awaiting_transport_heli(j,v));self.assertFalse(self.request(j,v));self.assertTrue(c['declined'])

    def test_confirmation_requires_real_booking_and_selects_aircraft_as_carrier(self):
        j,v=self.scene(25);self.request(j,v);c=self.e.state['radio_calls'][-1]
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'listen'})
        with self.assertRaises(ValueError):self.e.radio_action({'job':j['id'],'call':c['id'],'step':'confirm'})
        heli=self.vehicle('C9');self.e.dispatch({'job':j['id'],'vehicles':[heli['id']]})
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'confirm'})
        self.assertEqual(j['carrier'],heli['id']);self.assertEqual(j['air_transport_request']['unit'],heli['id'])
        self.assertTrue(self.e.awaiting_transport_heli(j,v))
        self.e.crew_destination(v);self.assertEqual(v['status'],'scene')

    def test_stable_short_or_doctor_already_flying_does_not_request(self):
        j,v=self.scene(80);self.assertFalse(self.request(j,v))
        j['patient_condition']['percent']=30;self.assertFalse(self.request(j,v,600))
        heli=self.vehicle('C9');heli.update(job=j['id'],status='enroute')
        self.assertFalse(self.request(j,v))

    def test_approximate_ground_route_is_labelled_and_telemedicine_can_escalate_to_heli(self):
        j,v=self.scene(30);h=self.e.get('hospitals','kh-hainburg')
        j.update(crew_target=h['id'],lat=47.5,lon=15.8);v.update(lat=j['lat'],lon=j['lon'])
        self.e.router.enabled=False
        self.assertTrue(self.e.maybe_request_transport_heli(j,v))
        self.assertTrue(j['air_transport_request']['approximate'])
        self.assertIn('geschätzt',self.e.state['radio_calls'][-1]['reason'])

    def test_manv_patient_assignment_changes_only_after_heli_arrives(self):
        j,v=self.scene(25);j['patients']=[{'number':1,'percent':25,'carrier':v['id'],'doctor':None,'delivered':False},{'number':2,'percent':75,'carrier':None,'doctor':None,'delivered':False}]
        v['patient_index']=0;heli=self.vehicle('C9');heli.update(job=j['id'],status='enroute')
        j['vehicles'].append(heli['id']);j['air_transport_request']={'unit':heli['id'],'patient_number':1}
        self.e.update_transport_heli(j);self.assertEqual(j['patients'][0]['carrier'],v['id'])
        heli.update(status='scene');self.e.update_transport_heli(j)
        self.assertEqual(j['patients'][0]['carrier'],heli['id']);self.assertEqual(heli['patient_index'],0)
        self.assertEqual(v['patient_index'],1)
