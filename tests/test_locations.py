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
        self.assertEqual(j['event_title'],self.e.rule('RD-1A1')['title'])
        self.assertNotIn('Unfallstelle',j['detail'])
    def test_hospital_locations_survive_reload(self):
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path)
        for h in self.e.state['hospitals']:
            if h['id'] in HOSPITALS:
                self.assertEqual(h['address'],HOSPITALS[h['id']]['address'])
                self.assertEqual(h['lat'],HOSPITALS[h['id']]['lat'])

    def test_confirmed_rk_nef_locations_share_real_address_and_survive_upgrade(self):
        from locations import upgrade_confirmed_stations
        expected={'moedling':('Neusiedler Straße 20, 2340 Mödling',48.08133,16.28427),'baden':('Rotes Kreuz-Gasse 6, 2500 Baden',48.00147,16.25389)}
        for base,(address,lat,lon) in expected.items():
            for id in (base,'nef-'+base):
                station=self.e.station(id)
                self.assertEqual((station['address'],station['lat'],station['lon']),(address,lat,lon))
                self.assertNotIn('prüfen',station['name']);self.assertFalse(station['external'])
        v=next(v for v in self.e.state['vehicles'] if v['station']=='nef-moedling')
        v.update(status='enroute',job='active-test',lat=48.2,lon=16.5)
        self.e.state.pop('confirmed_station_locations_version')
        upgrade_confirmed_stations(self.e)
        self.assertEqual((v['lat'],v['lon']),(48.2,16.5),'Active units must not teleport during address migration')
        self.e.save()
        v.update(status='ready',job=None)
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path)
        self.assertEqual(self.e.station('nef-moedling')['address'],expected['moedling'][0])
