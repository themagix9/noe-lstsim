import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from engine import Engine, SCENARIOS
from operations import STATUS_LABELS
from sessions import Sessions

class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=str(Path(self.temp.name)/'db');self.e=Engine(self.path)
        self.v=next(v for v in self.e.state['vehicles'] if v['type']=='KTW')
    def tearDown(self):self.e.db.close();self.temp.cleanup()
    def test_graphic_change_preserves_busy_vehicle_and_persists(self):
        before=copy.deepcopy(self.v);before.update(status='duty',job='active',phase_due=9876,lat=48.11,lon=16.45)
        self.v.update(before);self.e.command('vehicle_graphic',{'vehicle':self.v['id'],'graphic':'box'})
        self.assertEqual(self.v,{**before,'graphic':'box','graphic_custom':True})
        self.e.db.close();self.e=Engine(self.path);self.assertEqual(self.e.get('vehicles',self.v['id'])['graphic'],'box')
    def test_unknown_graphic_does_not_change_vehicle(self):
        before=copy.deepcopy(self.v)
        with self.assertRaises(ValueError):self.e.command('vehicle_graphic',{'vehicle':self.v['id'],'graphic':'missing'})
        self.assertEqual(self.v,before)
    def job(self,kind='transport'):
        j=self.e.new_job(kind,manual=kind=='transport',scenario=SCENARIOS[1] if kind=='emergency' else None)
        if kind=='emergency':j['accepted']=True
        return j
    def dispatch(self,j,v=None,**extra):return self.e.command('dispatch',{'job':j['id'],'vehicles':[(v or self.v)['id']],**extra})
    def advance(self,v=None):
        v=v or self.v;self.e.state['clock']=v['phase_due'];self.e.advance(v)
    def scene(self,region='Wien'):
        v=next(v for v in self.e.state['vehicles'] if v['type']=='RTW');j=self.job('emergency');j['crew_target']='kh-donaustadt' if region=='Wien' else 'kh-hainburg'
        self.dispatch(j,v);self.e.command('vehicle_status',{'vehicle':v['id'],'status':'2'});self.advance(v);self.advance(v);return j,v
    def test_status_numbers(self):
        self.assertEqual({int(label.split(' · ')[0]) for key,label in STATUS_LABELS.items() if key!='fr_ready'},set(range(10)))
    def test_dispatcher_cannot_set_emergency_destination(self):
        j=self.job('emergency');v=next(v for v in self.e.state['vehicles'] if v['type']=='RTW')
        self.assertIsNone(j['destination'])
        with self.assertRaises(ValueError):self.dispatch(j,v,destination='kh-hainburg')
        self.assertIsNone(v['job'])
    def test_crew_selects_noe_target(self):
        j,v=self.scene('NÖ');self.assertEqual(j['destination'],'kh-hainburg');self.assertEqual(v['status'],'transport');self.assertIsNone(j['case_number'])
    def test_vienna_waits_for_bed_and_sds(self):
        j,v=self.scene();self.assertEqual(j['bed_state'],'requested');self.assertEqual(v['status'],'scene');self.assertIsNone(v['phase_due'])
        with self.assertRaises(ValueError):self.e.command('send_case',{'job':j['id'],'channel':'SDS'})
        self.e.command('bed_request',{'job':j['id'],'hospital':'kh-donaustadt'})
        self.e.command('control',{'paused':False});self.e.tick(30)
        self.assertEqual(j['bed_state'],'allocated');self.assertEqual(v['status'],'scene');self.assertTrue(j['case_number'].startswith('SIM-W-'))
        self.e.command('send_case',{'job':j['id'],'channel':'SDS'});self.assertEqual(v['status'],'transport')
        self.advance(v);self.assertEqual(v['status'],'hospital')
        self.assertTrue(any(j['case_number'] in l['text'] and 'Aufnahme' in l['text'] for l in self.e.state['logs']))
        with self.assertRaises(ValueError):self.e.command('send_case',{'job':j['id'],'channel':'SDS'})
    def test_esapp_and_invalid_bed_target(self):
        j,v=self.scene()
        with self.assertRaises(ValueError):self.e.command('bed_request',{'job':j['id'],'hospital':'kh-hainburg'})
        self.assertEqual(j['bed_state'],'requested')
        self.e.command('bed_request',{'job':j['id'],'hospital':'kh-donaustadt'});self.e.update_operations(self.e.state['clock']+30)
        with self.assertRaises(ValueError):self.e.command('send_case',{'job':j['id'],'channel':'SMS'})
        self.assertEqual(v['status'],'scene');self.e.command('send_case',{'job':j['id'],'channel':'ESApp'});self.assertEqual(self.e.state['messages'][-1]['channel'],'ESApp')
    def test_reservation_does_not_alarm_and_can_be_released(self):
        j=self.job();self.e.command('reserve',{'job':j['id'],'vehicle':self.v['id']})
        self.assertIsNone(self.v['job']);self.assertEqual(self.v['status'],'ready');self.assertEqual(j['reserved'],self.v['id'])
        self.e.command('unreserve',{'job':j['id']});self.assertIsNone(self.v['reservation'])
    def test_reservation_conflict_and_send_clears_reservation(self):
        a=self.job();b=self.job();self.e.command('reserve',{'job':a['id'],'vehicle':self.v['id']})
        with self.assertRaises(ValueError):self.dispatch(b)
        with self.assertRaises(ValueError):self.e.command('reserve',{'job':b['id'],'vehicle':self.v['id']})
        self.dispatch(a);self.assertIsNone(self.v['reservation']);self.assertIsNone(a['reserved'])
    def test_reassignment_clears_previous_reservation(self):
        j=self.job();self.e.command('reserve',{'job':j['id'],'vehicle':self.v['id']})
        other=next(v for v in self.e.state['vehicles'] if v['type']=='RTW')
        self.dispatch(j,other);self.assertIsNone(self.v['reservation']);self.assertIsNone(j['reserved'])

    def test_busy_reservation_rejected_then_status5_can_reserve_and_send(self):
        a=self.job();self.dispatch(a);self.e.command('vehicle_status',{'vehicle':self.v['id'],'status':'2'})
        b=self.job()
        with self.assertRaises(ValueError):self.e.command('reserve',{'job':b['id'],'vehicle':self.v['id']})
        with self.assertRaises(ValueError):self.dispatch(b)
        for _ in range(3):self.advance()
        self.assertEqual(self.v['status'],'hospital');handover_due=self.v['phase_due']
        self.e.command('reserve',{'job':b['id'],'vehicle':self.v['id']})
        self.dispatch(b);self.assertEqual(a['status'],'done');self.assertEqual(self.v['alarm_from'],'hospital');self.e.command('vehicle_status',{'vehicle':self.v['id'],'status':'2'})
        self.assertEqual(self.v['status'],'acknowledged');self.assertEqual(self.v['phase_due'],handover_due)
        self.advance();self.assertEqual(self.v['status'],'enroute');self.assertEqual(self.v['job'],b['id'])
    def test_alarm_and_ack_or_direct_status2(self):
        j=self.job();self.dispatch(j);self.assertEqual(self.v['alarm_from'],'ready')
        self.e.command('vehicle_status',{'vehicle':self.v['id'],'status':'9'});self.assertEqual(self.v['status'],'acknowledged')
        self.advance();self.assertEqual(self.v['status'],'enroute')
        other=next(v for v in self.e.state['vehicles'] if v['type']=='RTW');self.e.command('vehicle_status',{'vehicle':other['id'],'status':'6'})
        self.dispatch(self.job(),other);self.assertEqual(other['alarm_from'],'radio');self.e.command('vehicle_status',{'vehicle':other['id'],'status':'2'});self.assertEqual(other['status'],'enroute')
    def test_automatic_ack_and_direct_departure(self):
        with patch('operations.random.random',return_value=.1):self.dispatch(self.job())
        self.advance()
        self.assertEqual(self.v['status'],'enroute')
    def test_standby_deadline_reminder_without_fake_ack(self):
        self.dispatch(self.job(),standby=True);self.assertEqual(self.v['status'],'standby');self.assertEqual(self.v['ack_deadline'],self.e.state['clock']+600)
        self.v['phase_due']=None;self.e.command('control',{'paused':False});self.e.tick(601)
        self.assertEqual(self.v['status'],'standby');self.assertTrue(any('Quittierungsfrist' in l['text'] for l in self.e.state['logs']))
        self.e.command('vehicle_status',{'vehicle':self.v['id'],'status':'9'});self.assertEqual(self.v['status'],'acknowledged')
    def test_manual_out_stays_out(self):
        self.e.command('vehicle_status',{'vehicle':self.v['id'],'status':'0'});self.e.command('control',{'paused':False});self.e.tick(1);self.assertEqual(self.v['status'],'out')
        self.e.command('vehicle_status',{'vehicle':self.v['id'],'status':'1'});self.assertEqual(self.v['status'],'ready')
    def test_position_interpolates_while_driving(self):
        self.dispatch(self.job());self.e.command('vehicle_status',{'vehicle':self.v['id'],'status':'2'});leg=copy.deepcopy(self.v['leg'])
        self.e.command('control',{'paused':False});self.e.tick((leg['end']-leg['start'])/2)
        self.assertAlmostEqual(self.v['lat'],(leg['lat']+leg['target_lat'])/2);self.assertEqual(self.v['status'],'enroute')
    def test_late_nef_does_not_hide_waiting_vienna_target(self):
        j,v=self.scene();self.assertEqual(j['status'],'awaiting_bed')
        nef=next(x for x in self.e.state['vehicles'] if x['type']=='NEF');self.dispatch(j,nef)
        self.assertEqual(j['status'],'awaiting_bed');self.e.command('vehicle_status',{'vehicle':nef['id'],'status':'2'});self.advance(nef)
        self.assertEqual(nef['status'],'scene');self.assertEqual(j['status'],'awaiting_bed');self.assertEqual(j['bed_state'],'requested')

    def test_second_transporting_unit_uses_existing_crew_destination(self):
        j,v=self.scene('NÖ');other=next(x for x in self.e.state['vehicles'] if x['type']=='RTW' and x['id']!=v['id'])
        self.dispatch(j,other);self.e.command('vehicle_status',{'vehicle':other['id'],'status':'2'});self.advance(other);self.advance(other)
        self.assertEqual(other['status'],'radio');self.assertEqual(j['destination'],'kh-hainburg')

    def test_pending_bed_and_reservations_persist(self):
        j,v=self.scene();self.e.command('bed_request',{'job':j['id'],'hospital':'kh-donaustadt'});t=self.job();free=next(v for v in self.e.state['vehicles'] if v['type']=='KTW' and v['status']=='ready' and v['id']!=self.v['id']);self.e.command('reserve',{'job':t['id'],'vehicle':free['id']})
        reopened=Engine(self.path);self.assertEqual(self.e.snapshot(),reopened.snapshot());reopened.db.close()
    def test_reset_clears_reservations_but_keeps_fleet(self):
        j=self.job();self.e.command('reserve',{'job':j['id'],'vehicle':self.v['id']});self.e.command('reset',{})
        self.assertTrue(all(v['reservation'] is None for v in self.e.state['vehicles']));self.assertEqual(self.e.state['jobs'],[])
    def test_reserved_vehicle_cannot_be_deleted_or_edited(self):
        j=self.job();self.e.command('reserve',{'job':j['id'],'vehicle':self.v['id']})
        with self.assertRaises(ValueError):self.e.command('delete_vehicle',{'id':self.v['id']})
        with self.assertRaises(ValueError):self.e.command('vehicle',copy.deepcopy(self.v))

    def test_reservation_status_allowlist_and_atomic_rejection(self):
        first=self.job();second=self.job();self.e.reserve({'job':first['id'],'vehicle':self.v['id']})
        other=next(v for v in self.e.state['vehicles'] if v['type']=='KTW' and v['id']!=self.v['id']);other['staffed']=True
        for status in ['enroute','scene','transport','duty','standby','acknowledged','out','assigned']:
            with self.subTest(status=status):
                other['status']=status
                with self.assertRaises(ValueError):self.e.reserve({'job':first['id'],'vehicle':other['id']})
                self.assertEqual(first['reserved'],self.v['id']);self.assertEqual(self.v['reservation'],first['id']);self.assertIsNone(other['reservation'])
        for status in ['ready','hospital','radio']:
            with self.subTest(status=status):
                other['status']=status;self.e.reserve({'job':second['id'],'vehicle':other['id']})
                self.assertEqual(second['reserved'],other['id']);self.e.unreserve({'job':second['id']})
        other.update(status='ready',staffed=False)
        with self.assertRaises(ValueError):self.e.reserve({'job':second['id'],'vehicle':other['id']})
        self.assertIsNone(second['reserved'])

class ModeTests(unittest.TestCase):
    def test_singleplayer_has_no_code_and_cannot_be_joined(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Sessions(str(Path(tmp)/'db'));auth=s.create({'name':'Julian','mode':'single'});host=s.member(auth['token']);state=s.snapshot(host)
            self.assertEqual(state['session']['mode'],'single');self.assertIsNone(state['session']['code'])
            code=s.db.execute('SELECT code FROM rooms WHERE id=?',(host['room_id'],)).fetchone()[0]
            with self.assertRaises(ValueError):s.join({'name':'Gast','code':code})
            s.close()
    def test_multiplayer_owner_guards_new_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Sessions(str(Path(tmp)/'db'));h=s.member(s.create({'name':'Host'})['token']);g=s.member(s.join({'name':'Gast','code':s.snapshot(h)['session']['code']})['token']);s.command(h,'generate',{'kind':'transport'});j=s.snapshot(h)['jobs'][-1];v=s.snapshot(h)['vehicles'][0];s.command(h,'claim',{'id':j['id']})
            with self.assertRaises(ValueError):s.command(g,'reserve',{'job':j['id'],'vehicle':v['id']})
            s.command(h,'dispatch',{'job':j['id'],'vehicles':[v['id']]})
            with self.assertRaises(ValueError):s.command(g,'vehicle_status',{'vehicle':v['id'],'status':'2'})
            s.close()

