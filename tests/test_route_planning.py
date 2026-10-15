"""Dispatch preparation, lock-free waiting and no post-ack routing stall."""
import copy
import threading
import time
from pathlib import Path
from unittest.mock import patch
import unittest
import test_fleet as helpers
from routing import Router,cumulative,rebase_route
from sessions import Sessions


def road(a,b):
    geometry=[[a['lat'],a['lon']],[b['lat'],a['lon']],[b['lat'],b['lon']]]
    return dict(status='ready',seconds=120,distance_m=2000,geometry=geometry,cumulative=cumulative(geometry))

class PlanningTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job

    def test_prepared_route_survives_ack_and_departure_without_second_request(self):
        v=self.vehicle('77/002');j=self.job();j.update(lat=v['lat']+.01,lon=v['lon']+.01)
        origin={k:v[k] for k in ('lat','lon')};target={k:j[k] for k in ('lat','lon')}
        route=road(origin,target)
        with patch.object(self.e.router,'route',side_effect=AssertionError('Route already planned')):
            self.e.dispatch({'job':j['id'],'vehicles':[v['id']],'_planned_routes':{v['id']:{'origin':origin,'target':target,'route':route}}})
            self.assertEqual(v['route_state'],'ready');self.assertIn('prepared_route',v)
            self.e.router.enabled=True
            self.e.acknowledge(v)
            self.assertEqual(v['status'],'acknowledged');self.assertFalse(v['leg'].get('waiting',False))
            due=v['phase_due'];self.e.state['clock']=due;self.e.advance(v)
            self.assertEqual(v['status'],'enroute');self.assertEqual(v['leg']['start'],due)
            self.e.update_operations(due+30);self.assertNotEqual(v['lat'],origin['lat'])

    def test_radio_unit_uses_prepared_route_immediately_at_quittierung(self):
        v=self.vehicle('77/002');v['status']='radio';j=self.job();j.update(lat=v['lat']+.01,lon=v['lon']+.01)
        a={k:v[k] for k in ('lat','lon')};b={k:j[k] for k in ('lat','lon')}
        self.e.dispatch({'job':j['id'],'vehicles':[v['id']],'_planned_routes':{v['id']:{'origin':a,'target':b,'route':road(a,b)}}})
        self.e.router.enabled=True;self.e.acknowledge(v)
        now=self.e.state['clock'];self.assertEqual(v['leg']['start'],now)
        self.e.update_operations(now+5);self.assertNotEqual(v['lat'],a['lat'])
        self.e.state['clock']=now+5;self.e.advance(v)
        self.assertEqual(v['leg']['start'],now,'Status 2 must not restart a moving status 9 journey')

    def test_preflight_rebases_moving_vehicle_without_returning_to_old_origin(self):
        a={'lat':48,'lon':16};b={'lat':48.01,'lon':16.01};route=road(a,b)
        result=rebase_route(route,{'lat':48.005,'lon':16},a)
        self.assertAlmostEqual(result['geometry'][0][0],48.005);self.assertLess(result['seconds'],120)
        self.assertEqual(route['geometry'][0],[48,16],'Cache geometry must remain immutable')
        with self.assertRaises(ValueError):rebase_route(route,{'lat':49,'lon':17},a)

    def test_orphan_driving_status_recovers_except_hold_and_fueling(self):
        v=self.vehicle('77/002');home=self.e.home(v)
        for status in ('radio','duty'):
            for stop in (None,'holding','fueling'):
                v.update(status=status,job=None,lat=home['lat']+.01,leg=None,phase_due=None)
                v.pop('holding',None);v.pop('fueling',None)
                if stop:v[stop]=True
                self.e.update_operations(self.e.state['clock'])
                self.assertEqual(v['leg'] is None,stop is not None)

    def test_initial_ok_route_also_snaps_offroad_start_immediately(self):
        router=Router(Path(self.tmp.name)/'offroad',url='http://local',enabled=False,fetcher=lambda _:dict(code='Ok',routes=[dict(duration=120,distance=2000,geometry=dict(coordinates=[[16,48],[16.01,48.01]]))]))
        a={'lat':48.001,'lon':16.001};b={'lat':48.01,'lon':16.01}
        router.fetch_route('test',a,b)
        self.assertTrue(router.items['test']['recovered']);router.db.close()

    def test_wait_routes_are_concurrent_and_fail_without_fabricated_geometry(self):
        entered=threading.Barrier(3)
        def fetch(path):
            entered.wait(timeout=2)
            coords=path.split('?')[0].rsplit('/',1)[1]
            points=[list(map(float,p.split(','))) for p in coords.split(';')]
            return dict(code='Ok',routes=[dict(duration=120,distance=2000,geometry=dict(coordinates=points))])
        router=Router(Path(self.tmp.name)/'parallel',url='http://local',enabled=True,fetcher=fetch)
        a={'lat':48,'lon':16};b={'lat':48.01,'lon':16.01};c={'lat':48.02,'lon':16.02}
        thread=threading.Thread(target=lambda:entered.wait(timeout=2));thread.start()
        result=router.wait_routes([('a',a,b),('b',a,c)],timeout=3);thread.join()
        self.assertTrue(all(r['status']=='ready' for r in result.values()))
        router.journeys.join();router.db.close()
        router=Router(Path(self.tmp.name)/'offline',url='http://offline',enabled=True,fetcher=lambda _:(_ for _ in ()).throw(OSError('offline')))
        with self.assertRaisesRegex(ValueError,'Alarmierung noch nicht gesendet'):router.wait_routes([('a',a,b)],timeout=1)
        router.journeys.join();router.db.close()

    def test_preflight_does_not_freeze_sessions_or_commit_an_incomplete_alarm(self):
        s=Sessions(str(Path(self.tmp.name)/'rooms'));auth=s.create({'name':'Tester','mode':'single'});member=s.member(auth['token']);engine=s.engine(member['room_id'])
        v=next(v for v in engine.state['vehicles'] if v['callsign']=='77/002')
        j=engine.new_job('transport',manual=True);j['accepted']=True
        entered=threading.Event();release=threading.Event();errors=[]
        class Waiting:
            enabled=True
            def wait_routes(self,journeys):
                entered.set();release.wait(2);raise ValueError('Alarmierung noch nicht gesendet')
        engine.router=Waiting()
        def dispatch():
            try:s.command(member,'dispatch',{'job':j['id'],'vehicles':[v['id']]})
            except ValueError as e:errors.append(str(e))
        worker=threading.Thread(target=dispatch);worker.start()
        try:
            self.assertTrue(entered.wait(1))
            self.assertTrue(s.lock.acquire(timeout=.1));s.lock.release()
            self.assertTrue(engine.lock.acquire(timeout=.1));engine.lock.release()
            self.assertIsNone(v['job']);self.assertFalse(engine.state['messages'])
        finally:release.set();worker.join(3);s.close()
        self.assertTrue(errors);self.assertIsNone(v['job']);self.assertFalse(j['vehicles'])

    def test_split_dispatcher_can_plan_manual_transport_without_call_handoff(self):
        s=Sessions(str(Path(self.tmp.name)/'split'));auth=s.create({'name':'Disponent','mode':'multi','workflow':'split','role':'dispatcher'});member=s.member(auth['token']);engine=s.engine(member['room_id'])
        j=engine.new_job('transport',manual=True);j['accepted']=True
        self.assertFalse(j.get('call'));engine.router.enabled=False
        v=next(v for v in engine.state['vehicles'] if v['callsign']=='77/002')
        try:
            s.command(member,'dispatch',{'job':j['id'],'vehicles':[v['id']]})
            self.assertEqual(v['job'],j['id'])
        finally:s.close()

    def test_split_calltaker_is_denied_before_ownership_or_route_checks(self):
        s=Sessions(str(Path(self.tmp.name)/'guard'));auth=s.create({'name':'Calltaker','mode':'multi','workflow':'split','role':'calltaker'});member=s.member(auth['token']);engine=s.engine(member['room_id'])
        j=engine.new_job('transport',manual=True);j.update(accepted=True,owner='another-dispatcher')
        try:
            for id in (j['id'],'unknown-job'):
                with self.assertRaises(PermissionError):s.command(member,'dispatch',{'job':id,'vehicles':[]})
        finally:s.close()
