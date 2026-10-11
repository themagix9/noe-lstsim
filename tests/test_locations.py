import unittest
import test_fleet as helpers
from locations import ADDRESSES,HOSPITALS

class LocationTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    def test_generated_calls_use_exact_real_points(self):
        points={a['id']:a for a in ADDRESSES}
        for _ in range(20):
            j=self.e.new_job('emergency');a=points[j['address_point']['id']]
            self.assertEqual((j['address'],j['lat'],j['lon']),(a['address'],a['lat'],a['lon']))
            self.assertNotIn('Bruckneudorf',j['address'])
    def test_known_address_corrects_manual_coordinates(self):
        a=ADDRESSES[0]
        self.e.create_job({'kind':'emergency','code':'RD-1A1','address':a['address'],'lat':48,'lon':16})
        j=self.e.state['jobs'][-1]
        self.assertEqual((j['lat'],j['lon']),(a['lat'],a['lon']))
        self.assertEqual(j['address_source'],'OpenStreetMap')
    def test_hospital_locations_survive_reload(self):
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path)
        for h in self.e.state['hospitals']:
            if h['id'] in HOSPITALS:
                self.assertEqual(h['address'],HOSPITALS[h['id']]['address'])
                self.assertEqual(h['lat'],HOSPITALS[h['id']]['lat'])
