import copy
import unittest
import test_fleet as helpers

class SignalTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job

    def dispatched(self):
        j=self.job();v=self.vehicle('77/002')
        self.e.dispatch({'job':j['id'],'vehicles':[v['id']]})
        return j,v

    def route(self,j,v):
        class Roads:
            enabled=True
            url='http://test'
            def estimates(self,*args):return {}
            def cached_eta(self,*args):return None
            def route(self,*args):return {'status':'ready','seconds':600,'distance_m':20000,'geometry':[[48,16],[48,16.1],[48.1,16.1]],'cumulative':[0,10000,20000]}
        self.e.router=Roads();v.update(lat=48,lon=16);self.e.drive(v,j,'enroute')

    def instruction(self,j,v,enabled):
        self.e.command('signal_contact',{'job':j['id'],'vehicle':v['id'],'signal':enabled})
        c=self.e.state['radio_calls'][-1]
        self.e.command('signal_radio',{'job':j['id'],'call':c['id'],'step':'answer'})
        self.e.command('signal_radio',{'job':j['id'],'call':c['id'],'step':'confirm'})
        return c

    def test_defaults_and_code_selection_preserve_manual_choice(self):
        j=self.job();self.assertTrue(j['signal']);self.assertFalse(self.job('transport')['signal'])
        self.e.command('job_signal',{'job':j['id'],'signal':False})
        self.e.edit_job({'job':j['id'],'code':'RD-6D2'});self.assertFalse(j['signal'])
        self.e.edit_job({'job':j['id'],'code':'RD-17B1'});self.assertFalse(j['signal'])
        with self.assertRaises(ValueError):self.e.command('job_signal',{'job':j['id'],'signal':'false'})

    def test_dispatch_choice_is_per_resource_and_future_default_only(self):
        j=self.job();first=self.vehicle('77/002');second=self.vehicle('77/004')
        self.e.dispatch({'job':j['id'],'vehicles':[first['id']],'signal':False});self.assertFalse(first['signal'])
        self.e.command('job_signal',{'job':j['id'],'signal':True})
        self.e.dispatch({'job':j['id'],'vehicles':[second['id']]})
        self.assertFalse(self.e.signal_for(first,j));self.assertTrue(self.e.signal_for(second,j))
        self.assertEqual(self.e.response_factor(first,j),1);self.assertEqual(self.e.response_factor(second,j),.85)

    def test_radio_retimes_remaining_route_without_jumping_or_replanning(self):
        j,v=self.dispatched();self.route(j,v);self.e.state['clock']+=255;self.e.update_operations(self.e.state['clock'])
        before=(v['lat'],v['lon']);geometry=copy.deepcopy(v['leg']['geometry']);old_due=v['phase_due']
        self.e.command('signal_contact',{'job':j['id'],'vehicle':v['id'],'signal':False});c=self.e.state['radio_calls'][-1]
        with self.assertRaises(ValueError):self.e.command('signal_radio',{'job':j['id'],'call':c['id'],'step':'confirm'})
        self.assertEqual(v['phase_due'],old_due)
        self.e.command('signal_radio',{'job':j['id'],'call':c['id'],'step':'answer'})
        self.e.command('signal_radio',{'job':j['id'],'call':c['id'],'step':'confirm'})
        self.assertEqual((v['lat'],v['lon']),before);self.assertEqual(v['leg']['geometry'],geometry)
        self.assertAlmostEqual(v['phase_due']-self.e.state['clock'],300);self.assertFalse(v['signal']);self.assertTrue(j['signal'])
        self.e.state['clock']+=50;self.e.update_operations(self.e.state['clock']);before=(v['lat'],v['lon'])
        self.instruction(j,v,True);self.assertAlmostEqual(v['phase_due']-self.e.state['clock'],250*.85)
        self.assertEqual((v['lat'],v['lon']),before)

    def test_waiting_route_and_scene_instruction(self):
        j,v=self.dispatched()
        class Roads:
            enabled=True
            url='http://test'
            def estimates(self,*args):return {}
            def cached_eta(self,*args):return None
            def route(self,*args):return {'status':'pending'}
        self.e.router=Roads();self.e.drive(v,j,'enroute');self.assertTrue(v['leg']['waiting'])
        self.instruction(j,v,False);self.assertEqual(v['leg']['time_factor'],1)
        self.assertIsNone(v['phase_due'])
        v.update(status='scene',leg=None,phase_due=self.e.state['clock']+600)
        due=v['phase_due'];self.instruction(j,v,True);self.assertEqual(v['phase_due'],due)

    def test_instruction_does_not_change_other_resources_and_persists(self):
        j,v=self.dispatched();other=self.vehicle('77/004');self.e.dispatch({'job':j['id'],'vehicles':[other['id']]})
        self.instruction(j,v,False);self.assertFalse(v['signal']);self.assertTrue(other['signal'])
        self.assertEqual({m['channel'] for m in self.e.state['messages'] if 'Anweisung der Leitstelle' in m['text']},{'SDS','ESApp'})
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);self.assertFalse(self.e.get('vehicles',v['id'])['signal'])

    def test_signal_conversation_can_cancel_and_requires_job_owner(self):
        j,v=self.dispatched();j['owner']='owner';before=v['signal']
        with self.assertRaises(ValueError):self.e.command('signal_contact',{'job':j['id'],'vehicle':v['id'],'signal':False,'_actor':{'id':'other'}})
        j['owner']=None;self.e.command('signal_contact',{'job':j['id'],'vehicle':v['id'],'signal':False});c=self.e.state['radio_calls'][-1]
        self.e.command('signal_radio',{'job':j['id'],'call':c['id'],'step':'cancel'})
        self.assertEqual(v['signal'],before);self.assertEqual(c['state'],'closed')

    def test_nef_convoy_changes_together_and_reset_clears_override(self):
        j,v=self.dispatched();nef=self.vehicle('77/099');self.e.dispatch({'job':j['id'],'vehicles':[nef['id']]})
        for unit in (v,nef):self.route(j,unit);unit['status']='transport'
        nef['escort_of']=v['id'];self.instruction(j,nef,False)
        self.assertFalse(v['signal']);self.assertFalse(nef['signal']);self.assertEqual(v['phase_due'],nef['phase_due'])
        self.e.command('reset',{});self.assertNotIn('signal',self.e.get('vehicles',v['id']))

    def test_open_signal_instruction_does_not_hold_patient_care(self):
        j,v=self.dispatched();j['crew_target']='kh-hainburg'
        v.update(status='scene',leg=None,phase_due=self.e.state['clock'])
        self.e.command('signal_contact',{'job':j['id'],'vehicle':v['id'],'signal':False})
        self.e.advance(v);self.assertEqual(v['status'],'transport')
