import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_fleet as helpers
from routing import Router,cumulative,position

class RouteTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job
    def test_segment_times_drive_server_position_by_time_not_distance(self):
        from routing import segment_times
        geometry=[[48,16],[48,16.01],[48,16.02]]
        route={'duration':150,'legs':[{'annotation':{'duration':[36,94]}}]}
        times=segment_times(route,geometry)
        self.assertEqual(times,[0,36,130])
        leg={'geometry':geometry,'cumulative':cumulative(geometry),'time_cumulative':times}
        self.assertAlmostEqual(position(leg,36/130)['lon'],16.01)
        self.assertGreater(position(leg,.5)['lon'],16.01)
        self.assertIsNone(segment_times({'legs':[{'annotation':{'duration':[10]}}]},geometry))
        self.assertIsNone(segment_times({'legs':[{'annotation':{'duration':[float('nan'),1]}}]},geometry))
        self.assertIsNone(segment_times({'legs':[{'annotation':{'duration':[0,0]}}]},geometry))

    def test_eta_pending_has_deadline_even_when_queue_is_full(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            router=Router(Path(directory)/'cache.db',enabled=False);router.enabled=True
            router.pending={str(i) for i in range(200)}
            a={'id':'a','lat':48,'lon':16};target={'lat':48.01,'lon':16.01}
            with patch('routing.time.time',return_value=100):self.assertEqual(router.estimates([a],target)['a']['status'],'pending')
            with patch('routing.time.time',return_value=113):self.assertEqual(router.estimates([a],target)['a']['status'],'error')
            self.assertEqual(len(router.tasks.queue),0);router.db.close()
    def test_pending_and_failed_routes_have_immediate_approximate_eta(self):
        j=self.job();self.e.router.enabled=True
        for status in ('pending','error'):
            from unittest.mock import patch
            with patch.object(self.e.router,'estimates',return_value={v['id']:{'status':status} for v in self.e.state['vehicles']}):
                result=next(x for x in self.e.snapshot()['jobs'] if x['id']==j['id'])
            eta=result['resource_eta'][self.vehicle('77/001')['id']]
            self.assertTrue(eta['approximate']);self.assertGreaterEqual(eta['seconds'],60);self.assertGreaterEqual(eta['arrival'],self.e.state['clock']+60)
            self.assertNotIn('distance_m',eta)
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
                return {'code':'Ok','routes':[{'duration':120,'distance':1400,'geometry':{'coordinates':[[16,48],[16,48.01],[16.01,48.01]]},'legs':[{'annotation':{'duration':[20,100]}}]}]}
            router=Router(Path(directory)/'cache.db',enabled=False,fetcher=fetch)
            a={'id':'a','lat':48,'lon':16};b={'id':'b','lat':48.02,'lon':16.04};target={'lat':48.01,'lon':16.01}
            k='route|'+router.cachekey(a,target);router.fetch_route(k,a,target);router.fetch_matrix([a,b],target)
            self.assertEqual(router.items[k]['geometry'][1],[48.01,16]);self.assertEqual(router.items[k]['time_cumulative'],[0,20,120]);self.assertEqual(router.cached_eta(b,target)['seconds'],360)
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

    def test_no_route_recovers_using_connected_nearest_road(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            def fetch(path):
                paths.append(path)
                if path.startswith('/nearest'):
                    start='16.0,48.0' in path
                    return {'code':'Ok','waypoints':[
                        {'location':[16.001 if start else 16.02,48.001 if start else 48.02],'distance':20,'hint':'isolated' if start else 'target'},
                        {'location':[16.002 if start else 16.021,48.002 if start else 48.021],'distance':80,'hint':'connected' if start else 'other'}]}
                if 'connected' not in path:return {'code':'NoRoute'}
                return {'code':'Ok','routes':[{'duration':300,'distance':1500,'geometry':{'coordinates':[[16.002,48.002],[16.002,48.02],[16.02,48.02]]}}]}
            router=Router(Path(directory)/'cache.db',enabled=False,fetcher=fetch);router.next_call=0
            a={'lat':48.0,'lon':16.0};b={'lat':48.02,'lon':16.02};k='route|'+router.cachekey(a,b)
            with patch('routing.time.sleep'):router.fetch_route(k,a,b)
            route=router.items[k];self.assertTrue(route['recovered']);self.assertEqual(route['geometry'][0],[48.002,16.002])
            self.assertEqual(router.cached_eta(a,b)['seconds'],300)
            self.assertEqual(sum(p.startswith('/nearest') for p in paths),2)
            v=self.vehicle('77/001');self.e.router=type('Ready',(),{'enabled':True,'route':lambda *args:route})()
            self.e.drive(v,b,'enroute');self.assertEqual((v['lat'],v['lon']),(48.002,16.002))
            self.assertIsNotNone(v['phase_due']);self.assertFalse(v['leg']['waiting']);self.assertTrue(v['leg']['recovered'])
            router.db.close()

    def test_unreachable_snaps_are_bounded_and_network_errors_not_teleported(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            def fetch(path):
                paths.append(path)
                return {'code':'Ok','waypoints':[{'location':[16,48],'distance':5000}]} if path.startswith('/nearest') else {'code':'NoSegment'}
            router=Router(Path(directory)/'cache.db',enabled=False,fetcher=fetch)
            with patch('routing.time.sleep'),self.assertRaises(ValueError):router.fetch_route('x',{'lat':48,'lon':16},{'lat':48.1,'lon':16.1})
            self.assertEqual(len(paths),3);self.assertNotIn('x',router.items)
            paths.clear()
            def offline(path):paths.append(path);raise OSError('offline')
            router.fetcher=offline
            with patch('routing.time.sleep'),self.assertRaises(OSError):router.fetch_route('x',{'lat':48,'lon':16},{'lat':48.1,'lon':16.1})
            self.assertEqual(len(paths),1);self.assertNotIn('x',router.items);router.db.close()

    def test_http_no_segment_reaches_recovery_instead_of_network_error(self):
        import io,urllib.error
        with tempfile.TemporaryDirectory() as directory:
            router=Router(Path(directory)/'cache.db',enabled=False)
            error=urllib.error.HTTPError('https://router/route',400,'Bad Request',{},io.BytesIO(b'{"code":"NoSegment"}'))
            with patch('routing.urllib.request.urlopen',side_effect=error),patch('routing.time.sleep'):
                self.assertEqual(router.request('/route')['code'],'NoSegment')
            router.db.close()

    def test_failed_matrix_does_not_flood_driving_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            router=Router(Path(directory)/'cache.db',enabled=False,fetcher=lambda path:{'code':'Ok','durations':[[None],[None]],'distances':[[None],[None]]})
            router.enabled=True
            a={'id':'a','lat':48,'lon':16};b={'id':'b','lat':48.01,'lon':16};target={'lat':48.1,'lon':16.1}
            with patch('routing.time.sleep'):router.fetch_matrix([a,b],target)
            self.assertEqual(len(router.tasks.queue),0)
            self.assertEqual(router.route(a,target)['status'],'pending');self.assertEqual(len(router.journeys.queue),1)
            router.db.close()

    def test_origin_only_recovery_is_three_calls_and_reuses_nearest_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            def fetch(path):
                paths.append(path)
                if path.startswith('/nearest'):return {'code':'Ok','waypoints':[{'location':[16.001,48.001],'distance':20,'hint':'road'}]}
                if '/16.0,48.0;' in path:return {'code':'NoRoute'}
                lon,lat=map(float,path.split('?')[0].rsplit(';',1)[1].split(','))
                return {'code':'Ok','routes':[{'duration':120,'distance':1000,'geometry':{'coordinates':[[16.001,48.001],[lon,lat]]}}]}
            router=Router(Path(directory)/'db',url='http://local-router',enabled=False,fetcher=fetch)
            a={'lat':48,'lon':16};b={'lat':48.02,'lon':16.02}
            k='route|'+router.cachekey(a,b);router.fetch_route(k,a,b)
            self.assertEqual(len(paths),3);self.assertTrue(router.items[k]['recovered'])
            self.assertEqual(sum(p.startswith('/nearest') for p in paths),1)
            b={'lat':48.03,'lon':16.03};router.fetch_route('second',a,b)
            self.assertEqual(len(paths),5);self.assertEqual(sum(p.startswith('/nearest') for p in paths),1)
            router.db.close()

    def test_active_journey_is_not_blocked_by_slow_eta_matrix(self):
        import threading
        with tempfile.TemporaryDirectory() as directory:
            entered=threading.Event();release=threading.Event();routed=threading.Event()
            def fetch(path):
                if path.startswith('/table'):
                    entered.set();release.wait(3)
                    raise OSError('late matrix timeout')
                routed.set();return {'code':'Ok','routes':[{'duration':120,'distance':1000,'geometry':{'coordinates':[[16,48],[16.01,48.01]]}}]}
            router=Router(Path(directory)/'db',url='http://local-router',enabled=True,fetcher=fetch)
            a={'id':'one','lat':48,'lon':16};b={'lat':48.01,'lon':16.01}
            try:
                router.estimates([a],b);self.assertTrue(entered.wait(1))
                router.route(a,b);self.assertTrue(routed.wait(1),'Driving must start while matrix is still blocked')
                self.assertFalse(release.is_set())
            finally:
                release.set();router.tasks.join();router.journeys.join()
                self.assertEqual(router.cached_eta(a,b)['status'],'ready','A late matrix timeout must not erase the completed route ETA')
                router.db.close()

    def test_private_router_has_no_artificial_delay_and_driving_has_reserved_queue_space(self):
        with tempfile.TemporaryDirectory() as directory:
            router=Router(Path(directory)/'db',url='http://osrm:5000',enabled=False,fetcher=lambda path:{'code':'Ok'})
            self.assertEqual(router.min_interval,0)
            with patch('routing.time.sleep') as sleep:
                router.request('/one');router.request('/two');sleep.assert_not_called()
            router.pending={str(i) for i in range(200)};router.enabled=True
            router.route({'lat':48,'lon':16},{'lat':48.1,'lon':16.1})
            self.assertEqual(len(router.journeys.queue),1);self.assertEqual(len(router.tasks.queue),0)
            router.db.close()

    def test_backup_router_uses_independent_cache_and_circuit_breaker(self):
        with tempfile.TemporaryDirectory() as directory:
            primary=Router(Path(directory)/'db',url='http://offline',enabled=False,backup_url='http://backup')
            backup=Router(Path(directory)/'other',url='http://backup',enabled=False,backup_url='',fetcher=lambda path:{'code':'Ok','routes':[{'duration':120,'distance':1000,'geometry':{'coordinates':[[16,48],[16.01,48.01]]}}]})
            primary.backup=backup
            a={'lat':48,'lon':16};b={'lat':48.01,'lon':16.01}
            with patch.object(primary,'road_route',side_effect=OSError('offline')) as request:
                primary.fetch_route('one',a,b);primary.fetch_route('two',a,b)
            self.assertEqual(request.call_count,1,'Failed primary cools down instead of delaying every vehicle')
            self.assertEqual(primary.items['one']['geometry'],[[48,16],[48.01,16.01]])
            self.assertTrue(primary.items['one']['backup']);self.assertEqual(primary.cached_eta(a,b)['status'],'ready')
            primary.db.close();backup.db.close()

    def test_backup_also_recovers_primary_no_segment(self):
        with tempfile.TemporaryDirectory() as directory:
            primary=Router(Path(directory)/'db',url='http://bad-dataset',enabled=False,backup_url='http://backup',fetcher=lambda path:{'code':'NoSegment'})
            backup=Router(Path(directory)/'other',url='http://backup',enabled=False,backup_url='',fetcher=lambda path:{'code':'Ok','routes':[{'duration':60,'distance':500,'geometry':{'coordinates':[[16,48],[16.01,48.01]]}}]})
            primary.backup=backup;primary.fetch_route('one',{'lat':48,'lon':16},{'lat':48.01,'lon':16.01})
            self.assertTrue(primary.items['one']['backup']);self.assertEqual(backup.nearest_cache,{})
            primary.db.close();backup.db.close()

    def test_storno_recovers_pending_return_turns_off_signal_and_reaches_home(self):
        v=self.vehicle('77/002');j=self.job();self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});self.e.depart(v)
        home=self.e.home(v);v.update(lat=home['lat']+.01,lon=home['lon']+.01,signal=True)
        geometry=[[v['lat'],v['lon']],[home['lat'],v['lon']],[home['lat'],home['lon']]]
        from types import SimpleNamespace
        router=SimpleNamespace(enabled=True,url='http://fixture',route=lambda a,b:{'status':'error'},estimates=lambda origins,target:{v['id']:{'status':'error'} for v in origins},cached_eta=lambda *args:None)
        self.e.router=router
        self.e.command('resource_call',{'job':j['id'],'vehicle':v['id']});call=self.e.state['radio_calls'][-1]
        self.e.command('cancel_radio',{'job':j['id'],'call':call['id'],'step':'answer'})
        self.e.command('cancel_radio',{'job':j['id'],'call':call['id'],'step':'cancel'})
        self.assertEqual(v['status'],'radio');self.assertFalse(v['signal']);self.assertIsNone(v['job']);self.assertTrue(v['leg']['waiting'])
        router.route=lambda a,b:{'status':'ready','seconds':120,'geometry':geometry,'cumulative':cumulative(geometry),'distance_m':2000,'backup':True}
        start=self.e.state['clock'];self.e.update_operations(start)
        self.assertFalse(v['leg']['waiting']);self.assertEqual(v['leg']['time_factor'],1)
        self.e.update_operations(start+60);self.assertNotEqual((v['lat'],v['lon']),tuple(geometry[0]))
        self.e.state['clock']=start+121;self.e.update_operations(start+121);self.e.advance(v);self.assertEqual(v['status'],'ready');self.assertAlmostEqual(v['lat'],home['lat']);self.assertAlmostEqual(v['lon'],home['lon'])
