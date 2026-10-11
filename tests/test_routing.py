import copy
import json
from pathlib import Path
import tempfile
import unittest
import test_fleet as helpers
from routing import Router,cumulative,position

class RouteTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job
    def test_geometry_follows_corner_and_persists(self):
        j=self.job();v=self.vehicle('77/001');a={'lat':48,'lon':16};b={'lat':48.1,'lon':16.1};geometry=[[48,16],[48.1,16],[48.1,16.1]]
        class Fake:
            enabled=True
            def route(self,*args):return {'status':'ready','seconds':600,'geometry':geometry,'cumulative':cumulative(geometry),'distance_m':18500}
        self.e.router=Fake();v.update(lat=a['lat'],lon=a['lon']);self.e.drive(v,b,'enroute')
        start=self.e.state['clock'];self.e.state['clock']=start+300;self.e.update_operations(start+300)
        self.assertAlmostEqual(v['lon'],16);self.assertGreater(v['lat'],48.05)
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);v=self.vehicle('77/001');self.assertEqual(v['leg']['geometry'],geometry)
        self.assertEqual(position(v['leg'],1),b)
    def test_failed_or_pending_route_never_drives_straight(self):
        v=self.vehicle('77/001');home=(v['lat'],v['lon'])
        class Fake:
            enabled=True
            def route(self,*args):return {'status':'error'}
        self.e.router=Fake();self.e.drive(v,{'lat':48.2,'lon':16.6},'enroute');self.e.state['clock']+=3600;self.e.update_operations(self.e.state['clock'])
        self.assertEqual((v['lat'],v['lon']),home);self.assertIsNone(v['phase_due']);self.assertTrue(v['leg']['waiting']);self.assertEqual(v['route_state'],'error')
    def test_osrm_response_cache_and_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            responses=[]
            def fetch(path):
                responses.append(path)
                if path.startswith('/table'):return {'code':'Ok','durations':[[120],[360]],'distances':[[1400],[5100]]}
                return {'code':'Ok','routes':[{'duration':120,'distance':1400,'geometry':{'coordinates':[[16,48],[16,48.01],[16.01,48.01]]}}]}
            router=Router(Path(directory)/'cache.db',enabled=False,fetcher=fetch)
            a={'id':'a','lat':48,'lon':16};b={'id':'b','lat':48.02,'lon':16.04};target={'lat':48.01,'lon':16.01}
            k='route|'+router.cachekey(a,target);router.fetch_route(k,a,target);router.fetch_matrix([a,b],target)
            self.assertEqual(router.items[k]['geometry'][1],[48.01,16]);self.assertEqual(router.cached_eta(b,target)['seconds'],360)
            router.db.close();router=Router(Path(directory)/'cache.db',enabled=False)
            self.assertEqual(router.items[k]['seconds'],120);router.db.close()
            self.assertIn('geometries=geojson',responses[0]);self.assertIn('sources=0;1&destinations=2',responses[1])
    def test_legacy_ground_journey_waits_for_road_route(self):
        v=self.vehicle('77/001');self.e.drive(v,{'lat':48.2,'lon':16.6},'enroute');origin=(v['lat'],v['lon'])
        class Fake:
            enabled=True
            def route(self,*args):return {'status':'pending'}
        self.e.router=Fake();self.e.update_operations(self.e.state['clock']+100)
        self.assertTrue(v['leg']['waiting']);self.assertEqual((v['lat'],v['lon']),origin);self.assertIsNone(v['phase_due'])
