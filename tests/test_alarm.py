import unittest
import test_fleet as helpers

class AlarmTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job

    def test_identity_survives_reload_and_reset(self):
        a=self.e.new_job('emergency');b=self.e.new_job('transport')
        self.assertNotEqual(a['incident_number'],b['incident_number'])
        number=a['incident_number'];self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path)
        self.assertEqual(self.e.get('jobs',a['id'])['incident_number'],number)
        self.e.command('reset',{})
        c=self.e.new_job('emergency')
        self.assertNotIn(c['incident_number'],[a['incident_number'],b['incident_number']])

    def test_ampds_title_and_per_resource_alarm(self):
        j=self.job();self.e.edit_job({'job':j['id'],'code':'RD-9E1','additional':'Übungszusatz'})
        units=[self.vehicle('77/001'),self.vehicle('77/099')]
        self.e.dispatch({'job':j['id'],'vehicles':[v['id'] for v in units]})
        messages=[m for m in self.e.state['messages'] if m['channel'] in ('SDS','ESApp')]
        self.assertEqual(len(messages),4)
        for v in units:
            channels=[m for m in messages if m['vehicle']==v['id']]
            self.assertEqual({m['channel'] for m in channels},{'SDS','ESApp'})
            self.assertEqual(channels[0]['time'],channels[1]['time'])
        for message in messages:
            v=next(v for v in units if v['id']==message['vehicle'])
            for field in [j['incident_number'],'RD-9E1',j['title'],j['address'],j['billing_number'],v['callsign'],'Übungszusatz']:
                self.assertIn(field,message['text'])
        self.assertTrue(j['patient']['fictitious'])
        self.assertFalse(any(l['channel']=='Funk' and 'Leitstelle an' in l['text'] for l in self.e.state['logs']))
        generated=self.e.new_job('emergency')
        self.assertEqual(generated['title'],self.e.rule(generated['code'])['title'])

    def test_reset_keeps_fr_at_home(self):
        fr=self.vehicle('FR-FIS-01');home=(fr['home_lat'],fr['home_lon'])
        self.e.command('reset',{})
        fr=self.vehicle('FR-FIS-01')
        self.assertEqual((fr['lat'],fr['lon']),home)
        self.assertEqual(fr['status'],'fr_ready')
