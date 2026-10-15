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

    def test_text_call_finishes_in_30_to_45_real_seconds(self):
        with patch.dict('os.environ',{'CALL_AUTO':'1'}),patch('calls.time.time',return_value=100) as clock:
            j=self.accept();call=j['call']
            self.assertEqual(len(call['transcript']),1)
            while call['state']=='connected':
                clock.return_value=call['next_line_at']-.001;self.assertFalse(self.e.flush_calls())
                clock.return_value=call['next_line_at'];self.assertTrue(self.e.flush_calls())
            self.assertGreaterEqual(clock.return_value-100,30);self.assertLessEqual(clock.return_value-100,45)
            self.assertTrue(j['asked']);self.assertEqual(len(call['answered']),6)
            self.assertEqual([l['speaker'] for l in call['transcript']],['LEO','Anrufer']*5)
            self.assertIn('Wir schicken jemanden',call['transcript'][-2]['text'])

    def test_pause_reopen_and_audio_ack_preserve_cursor(self):
        with patch.dict('os.environ',{'CALL_AUTO':'1'}),patch('calls.time.time',return_value=100) as clock:
            j=self.accept();call=j['call'];self.e.command('call_playback',{'job':j['id'],'mode':'speech'})
            clock.return_value=110;self.e.command('call_playback',{'job':j['id'],'mode':'pause'})
            clock.return_value=1000;self.assertFalse(self.e.flush_calls());self.assertEqual(len(call['transcript']),1)
            self.e.command('call_playback',{'job':j['id'],'mode':'speech'})
            self.assertFalse(call['paused']);self.assertFalse(self.e.flush_calls())
            self.e.command('call_playback',{'job':j['id'],'mode':'done','line':0})
            self.assertEqual(len(call['transcript']),2)
            self.e.command('call_playback',{'job':j['id'],'mode':'done','line':0})
            self.assertEqual(len(call['transcript']),2,'Stale/double completion cannot advance twice')
            self.e.command('call_playback',{'job':j['id'],'mode':'pause'})
            self.e.command('call_playback',{'job':j['id'],'mode':'done','line':1})
            self.assertEqual(len(call['transcript']),2)

    def test_speed_pause_and_late_tick_do_not_batch_transcript(self):
        with patch.dict('os.environ',{'CALL_AUTO':'1'}),patch('calls.time.time',return_value=100) as clock:
            j=self.accept();self.e.state.update(paused=True,speed=60)
            clock.return_value=1000;self.e.tick(1)
            self.assertEqual(len(j['call']['transcript']),2)
            self.e.snapshot();self.e.tick(60);self.assertEqual(len(j['call']['transcript']),2)
            self.assertGreater(j['call']['next_line_at'],1000)
            with self.assertRaises(ValueError):self.e.command('call_question',{'job':j['id'],'question':'location'})
            v=next(v for v in self.e.state['vehicles'] if v['callsign']=='77/002')
            self.e.command('dispatch',{'job':j['id'],'vehicles':[v['id']]})
            self.assertEqual(j['call']['state'],'connected','Early disposition must not hang up')

    def test_reload_preserves_paused_script_and_other_owner_cannot_resume(self):
        with patch.dict('os.environ',{'CALL_AUTO':'1'}),patch('calls.time.time',return_value=100) as clock:
            j=self.accept();self.e.command('call_playback',{'job':j['id'],'mode':'pause'});self.e.save();self.e.db.close()
            from engine import Engine
            self.e=Engine(self.path);j=self.e.get('jobs',j['id']);clock.return_value=1000
            self.assertFalse(self.e.flush_calls());self.assertTrue(j['call']['paused'])
            j['owner']='a'
            with self.assertRaises(ValueError):self.e.command('call_playback',{'job':j['id'],'mode':'speech','_actor':{'id':'b'}})

    def test_releasing_call_does_not_get_reclaimed_by_audio_pause(self):
        with patch.dict('os.environ',{'CALL_AUTO':'1'}),patch('calls.time.time',return_value=100):
            j=self.accept();j['owner']='a';actor={'id':'a','name':'A'}
            self.e.command('release',{'id':j['id'],'_actor':actor})
            self.e.command('call_playback',{'job':j['id'],'mode':'pause','_actor':actor})
            self.assertIsNone(j['owner']);self.assertTrue(j['call']['paused'])
