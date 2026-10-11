import unittest
import test_fleet as helpers

class RadioTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job
    def scene(self):
        j=self.job();v=self.vehicle('77/001');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});self.e.depart(v);self.e.advance(v);return j,v
    def test_dialogue_requires_reason_and_actual_booking(self):
        j,v=self.scene();c=self.e.raise_radio(j,v,'NEF','Laufende Reanimation.')
        action=lambda step:self.e.command('radio',{'job':j['id'],'call':c['id'],'step':step})
        action('listen');self.assertEqual(c['state'],'reason_needed');self.assertIsNone(v['phase_due'])
        with self.assertRaises(ValueError):action('confirm')
        action('reason');self.assertEqual(c['state'],'awaiting_dispatch')
        with self.assertRaises(ValueError):action('confirm')
        nef=self.vehicle('77/099');self.e.dispatch({'job':j['id'],'vehicles':[nef['id']]});action('confirm');self.assertEqual(c['state'],'closed')
        text='\n'.join(l['text'] for l in reversed(self.e.state['logs']))
        for phrase in ['LEO von 77/001, kommen.','LEO hört.','Grund der Nachforderung?','Laufende Reanimation.','NEF Schwechat kommt ab Wache.','NEF Schwechat, verstanden.','LEO Ende.']:self.assertIn(phrase,text)
        self.assertEqual(j['vehicles'],[v['id'],nef['id']])
    def test_reason_already_provided_and_external_support(self):
        j,v=self.scene();c=self.e.raise_radio(j,v,'Feuerwehr',reason_initial=True)
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'listen'});self.assertEqual(c['state'],'awaiting_dispatch')
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'confirm'});self.assertTrue(j['fire']);self.assertEqual(c['state'],'closed')
    def test_pending_call_is_persistent_and_holds_crew(self):
        j,v=self.scene();c=self.e.raise_radio(j,v,'NEF');self.e.advance(v);self.assertEqual(v['status'],'scene')
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);self.assertEqual(self.e.state['radio_calls'][0]['id'],c['id'])
    def test_other_owner_cannot_answer(self):
        j,v=self.scene();c=self.e.raise_radio(j,v);j['owner']='owner'
        with self.assertRaises(ValueError):self.e.command('radio',{'job':j['id'],'call':c['id'],'step':'listen','_actor':{'id':'other','name':'Anderer'}})
        self.assertEqual(c['state'],'calling')
    def test_traffic_incident_can_request_technical_rescue(self):
        from unittest.mock import patch
        j,v=self.scene();j.update(code='RD-29D1',reinforcement_checked=False)
        with patch.dict('os.environ',{'REINFORCEMENTS_AUTO':'1'}),patch('radio.random.random',return_value=.1):self.e.maybe_reinforcement(j,v)
        self.assertEqual(self.e.state['radio_calls'][-1]['kind'],'Feuerwehr')
