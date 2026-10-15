import unittest
import test_fleet as helpers

class RadioTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job
    def scene(self):
        j=self.job();v=self.vehicle('77/001');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});self.e.depart(v);self.e.advance(v);self.e.state['clock']=v['assessment_due'];self.e.update_assessments(self.e.state['clock']);return j,v
    def test_dialogue_requires_reason_and_actual_booking(self):
        j,v=self.scene();c=self.e.raise_radio(j,v,'NEF','Laufende Reanimation.')
        action=lambda step:self.e.command('radio',{'job':j['id'],'call':c['id'],'step':step})
        action('listen');self.assertEqual(c['state'],'reason_needed');self.assertIsNone(v['phase_due'])
        with self.assertRaises(ValueError):action('confirm')
        action('reason');self.assertEqual(c['state'],'awaiting_dispatch')
        with self.assertRaises(ValueError):action('confirm')
        nef=self.vehicle('77/099');self.e.dispatch({'job':j['id'],'vehicles':[nef['id']]});action('confirm');self.assertEqual(c['state'],'closed')
        text='\n'.join(l['text'] for l in reversed(self.e.state['logs']))
        for phrase in ['LEO von 77/001, kommen.','77/001 von LEO, hört, kommen.','Grund der Nachforderung?','Laufende Reanimation.','NEF Schwechat kommt ab Wache.','NEF Schwechat, verstanden.','LEO Ende.']:self.assertIn(phrase,text)
        self.assertEqual(j['vehicles'],[v['id'],nef['id']])
    def test_reinforcement_eta_uses_remaining_journey_and_turnout(self):
        from unittest.mock import patch
        j,v=self.scene();nef=self.vehicle('77/099')
        self.e.dispatch({'job':j['id'],'vehicles':[nef['id']]})
        now=self.e.state['clock'];nef['turnout_due']=now+30
        with patch.object(self.e.router,'cached_eta',return_value={'status':'ready','seconds':300}):
            expected=__import__('math').ceil((300*self.e.response_factor(nef,j)+30)/60)
            self.assertIn(f'ca. {expected} Minuten',self.e.reinforcement_eta_text(nef,j))
        nef.update(status='enroute',leg={'end':now+121})
        self.assertEqual(self.e.reinforcement_eta_text(nef,j),'Eintreffzeit ca. 3 Minuten.')
        self.e.state['clock']+=62
        self.assertEqual(self.e.reinforcement_eta_text(nef,j),'Eintreffzeit ca. 1 Minute.')
        nef['status']='scene'
        self.assertEqual(self.e.reinforcement_eta_text(nef,j),'Bereits am Berufungsort.')

    def test_confirmation_announces_booked_doctor_eta(self):
        j,v=self.scene();c=self.e.raise_radio(j,v,'NEF',reason_initial=True)
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'listen'})
        nef=self.vehicle('77/099');self.e.dispatch({'job':j['id'],'vehicles':[nef['id']]})
        nef.update(status='enroute',leg={'end':self.e.state['clock']+420})
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'confirm'})
        text=' '.join(x['text'] for x in self.e.state['logs'])
        self.assertIn('77/001 von LEO, NEF Schwechat kommt ab Wache. Eintreffzeit ca. 7 Minuten. Kommen.',text)

    def test_reason_already_provided_and_external_support(self):
        j,v=self.scene();c=self.e.raise_radio(j,v,'Feuerwehr',reason_initial=True)
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'listen'});self.assertEqual(c['state'],'awaiting_dispatch')
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'confirm'});self.assertTrue(j['fire']);self.assertEqual(c['state'],'closed')
    def test_pending_call_is_persistent_and_holds_crew(self):
        j,v=self.scene();c=self.e.raise_radio(j,v,'NEF');self.e.advance(v);self.assertEqual(v['status'],'scene')
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);self.assertTrue(any(x['id']==c['id'] and x['state']!='closed' for x in self.e.state['radio_calls']))
    def test_other_owner_cannot_answer(self):
        j,v=self.scene();c=self.e.raise_radio(j,v);j['owner']='owner'
        with self.assertRaises(ValueError):self.e.command('radio',{'job':j['id'],'call':c['id'],'step':'listen','_actor':{'id':'other','name':'Anderer'}})
        self.assertEqual(c['state'],'calling')
    def test_repeat_and_wait_keep_conversation_open(self):
        j,v=self.scene();c=self.e.raise_radio(j,v,'NEF','Zunehmende Atemnot.')
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'listen'})
        for step in ('repeat','wait'):self.e.radio_action({'job':j['id'],'call':c['id'],'step':step})
        self.assertEqual(c['state'],'reason_needed')
        text=' '.join(l['text'] for l in self.e.state['logs'])
        self.assertIn('ich wiederhole',text);self.assertIn('von LEO, warten',text)
    def test_notarzt_resources_use_official_radio_names(self):
        self.assertEqual(self.e.radio_name(self.vehicle('77/099')),'NEF Schwechat')
        self.assertEqual(self.e.radio_name(self.vehicle('C3')),'Christophorus 3')
    def test_traffic_incident_can_request_technical_rescue(self):
        from unittest.mock import patch
        j,v=self.scene();j.update(code='RD-29D1',reinforcement_checked=False)
        with patch.dict('os.environ',{'REINFORCEMENTS_AUTO':'1'}),patch('radio.random.random',return_value=.1):self.e.maybe_reinforcement(j,v)
        self.assertEqual(self.e.state['radio_calls'][-1]['kind'],'Feuerwehr')

    def test_negative_response_is_allowed_even_if_support_is_booked(self):
        j,v=self.scene();c=self.e.raise_radio(j,v,'NEF',reason_initial=True)
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'listen'})
        nef=self.vehicle('77/099');self.e.dispatch({'job':j['id'],'vehicles':[nef['id']]})
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'unavailable'})
        self.assertEqual(c['state'],'closed');self.assertIsNone(self.e.raise_radio(j,v,'NEF'))
        text=' '.join(log['text'] for log in self.e.state['logs']);self.assertIn('Negativ',text);self.assertIn('LEO Ende.',text)
