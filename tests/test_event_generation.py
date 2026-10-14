import copy,math,unittest
from unittest.mock import patch
import test_fleet as helpers

class EventTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown

    def test_rates_disabled_transport_and_manual_generation(self):
        self.e.configure_events({'emergency_per_hour':12,'transport_per_hour':8,'transports_enabled':False})
        self.assertIsNone(self.e.state['next_transport'])
        self.e.state['next_emergency']=self.e.state['clock']
        with patch('event_generation.random.uniform',return_value=1):self.e.generate_events(self.e.state['clock'])
        self.assertEqual([j['kind'] for j in self.e.state['jobs']],['emergency'])
        self.assertEqual(self.e.state['next_emergency']-self.e.state['clock'],300)
        manual=self.e.new_job('transport');self.assertEqual(manual['kind'],'transport')

    def test_changes_clear_old_due_times_without_catchup_burst(self):
        existing=self.e.new_job('transport');self.e.configure_events({'emergency_per_hour':0,'transport_per_hour':0})
        self.e.generate_events(self.e.state['clock']+86400);self.assertEqual(len(self.e.state['jobs']),1)
        self.assertEqual(self.e.state['jobs'][0],existing)
        with patch('event_generation.random.uniform',return_value=1):self.e.configure_events({'transport_per_hour':6,'transports_enabled':True})
        due=self.e.state['next_transport'];self.assertEqual(due-self.e.state['clock'],600)
        self.e.generate_events(due-1);self.assertEqual(len(self.e.state['jobs']),1)
        self.e.generate_events(due+86400);self.assertEqual(len(self.e.state['jobs']),2)

    def test_settings_survive_pause_reset_reload(self):
        settings={'emergency_per_hour':7.5,'transport_per_hour':3,'transports_enabled':False}
        self.e.command('event_settings',settings);self.e.command('reset',{})
        self.assertEqual(self.e.event_settings(),settings);self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);self.assertEqual(self.e.snapshot()['event_settings'],settings)
        before=self.e.state['clock'];self.e.tick(100);self.assertEqual(self.e.state['clock'],before)

    def test_invalid_update_is_atomic(self):
        before=copy.deepcopy(self.e.state)
        for value in (-1,121,float('nan'),float('inf'),True,'no'):
            with self.assertRaises(ValueError):self.e.configure_events({'emergency_per_hour':value})
        with self.assertRaises(ValueError):self.e.configure_events({'emergency_per_hour':5,'transports_enabled':'false'})
        self.assertEqual(self.e.state,before)
