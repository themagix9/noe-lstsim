import unittest
from unittest.mock import patch
import test_fleet as helpers
from hospitals import spoken_name
class RadioContextTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job
    def test_brief_clinic_names_in_radio_without_mutating_directory(self):
        h={'name':'Landesklinikum Baden-Mödling-Hinterbrühl · Baden-Mödling-Hinterbrühl LKL / Baden (ehem. K304)','city':'Baden','id':'example'}
        self.e.state['hospitals'].append(h)
        self.assertEqual(spoken_name(h),'Klinik Baden')
        self.assertEqual(self.e.radio_text('LEO von 77/001, Wunsch '+h['name']+'. Kommen.'),'LEO von 77/001, Wunsch Klinik Baden. Kommen.')
        self.assertIn('ehem.',h['name'])
    def test_radio_ownership_is_preserved_through_pacing(self):
        j=self.job();j['owner']='dispo';v=self.vehicle('77/002');v['job']=j['id']
        with patch.dict('os.environ',{'RADIO_INTERVAL':'2'}),patch('radio_pacing.time.time',return_value=100):
            self.e.state.update(radio_last_spoken=100,radio_pending=[])
            self.e.radio_transmit(v,'LEO','kommen.')
        row=self.e.state['radio_pending'][0];self.assertEqual((row['job'],row['vehicle'],row['owner']),(j['id'],v['id'],'dispo'))
        with patch('radio_pacing.time.time',return_value=103):self.e.flush_radio()
        self.assertEqual(self.e.state['logs'][0]['owner'],'dispo')
    def test_local_transport_has_status_update_without_routine_radio(self):
        j=self.job();v=self.vehicle('77/002');self.e.dispatch({'job':j['id'],'vehicles':[v['id']]});self.e.depart(v)
        v['status']='scene';v['assessment_due']=0;j['crew_target']='kh-moedling'
        self.e.state['logs']=[];self.e.state['radio_pending']=[]
        self.e.crew_destination(v)
        self.assertEqual(v['status'],'transport')
        self.assertFalse(any(l['channel']=='Funk' for l in self.e.state['logs']))
        self.assertTrue(any('Status 4' in l['text'] for l in self.e.state['logs']))
