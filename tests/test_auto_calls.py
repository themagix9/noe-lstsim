import unittest
from unittest.mock import patch
import test_fleet as helpers

class AutoCallTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown

    def accept(self):
        from engine import SCENARIOS
        j=self.e.new_job('emergency',scenario=SCENARIOS[1])
        self.e.command('accept',{'id':j['id']});return j

    def test_every_line_has_real_two_second_gap_and_auto_closes(self):
        with patch.dict('os.environ',{'CALL_AUTO':'1'}),patch('calls.time.time',return_value=100) as clock:
            j=self.accept();self.assertEqual(len(j['call']['transcript']),1)
            self.assertEqual(j['call']['state'],'connected')
            clock.return_value=101.99;self.assertFalse(self.e.flush_calls())
            for index in range(1,10):
                clock.return_value=100+index*2;self.assertTrue(self.e.flush_calls())
                self.assertEqual(len(j['call']['transcript']),index+1)
                self.assertFalse(self.e.flush_calls())
            self.assertEqual(j['call']['state'],'ended');self.assertTrue(j['asked'])
            self.assertEqual(len(j['call']['answered']),6)
            self.assertEqual([l['speaker'] for l in j['call']['transcript']],['LEO','Anrufer']*5)
            self.assertTrue(all(b['spoken_at']-a['spoken_at']==2 for a,b in zip(j['call']['transcript'],j['call']['transcript'][1:])))
            self.assertIn('Wir schicken jemanden',j['call']['transcript'][-2]['text'])

    def test_pause_speed_and_late_tick_do_not_batch_or_duplicate_speech(self):
        with patch.dict('os.environ',{'CALL_AUTO':'1'}),patch('calls.time.time',return_value=100) as clock:
            j=self.accept();self.e.state.update(paused=True,speed=60)
            clock.return_value=1000;self.e.tick(1)
            self.assertEqual(len(j['call']['transcript']),2)
            self.e.snapshot();self.e.tick(60);self.assertEqual(len(j['call']['transcript']),2)
            self.assertEqual(j['call']['next_line_at'],1002)
            with self.assertRaises(ValueError):self.e.command('call_question',{'job':j['id'],'question':'location'})
            with self.assertRaises(ValueError):self.e.command('dispatch',{'job':j['id'],'vehicles':[self.e.state['vehicles'][0]['id']]})

    def test_reload_preserves_remaining_script_and_old_calls_resume(self):
        with patch.dict('os.environ',{'CALL_AUTO':'1'}),patch('calls.time.time',return_value=100) as clock:
            j=self.accept();clock.return_value=102;self.e.flush_calls();self.e.save();self.e.db.close()
            from engine import Engine
            self.e=Engine(self.path);j=self.e.get('jobs',j['id']);self.assertEqual(len(j['call']['transcript']),2)
            clock.return_value=104;self.e.snapshot();self.assertEqual(len(j['call']['transcript']),3)
            self.assertEqual(j['call']['transcript'][-1]['speaker'],'LEO')
            j['call'].pop('automatic');j['call'].pop('pending');self.e.resume_calls()
            self.assertTrue(j['call']['automatic']);self.assertTrue(j['call']['pending'])

    def test_two_clients_observe_one_server_owned_transcript(self):
        with patch.dict('os.environ',{'CALL_AUTO':'1'}),patch('calls.time.time',return_value=100) as clock:
            j=self.accept();clock.return_value=102
            a=self.e.snapshot();b=self.e.snapshot()
            ac=next(x for x in a['jobs'] if x['id']==j['id'])['call']
            bc=next(x for x in b['jobs'] if x['id']==j['id'])['call']
            self.assertEqual(ac['transcript'],bc['transcript']);self.assertEqual(len(ac['transcript']),2)
