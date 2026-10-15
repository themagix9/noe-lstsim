import copy,unittest
import test_fleet as helpers

class VehicleOrderTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job

    def test_hold_persists_then_return_restarts_route_and_reaches_home(self):
        v=self.vehicle('77/002');self.e.drive(v,{'lat':48.2,'lon':16.6},'radio')
        self.e.state['clock']+=30;self.e.update_operations(self.e.state['clock']);point=(v['lat'],v['lon'])
        self.e.command('vehicle_order',{'vehicle':v['id'],'order':'hold'})
        self.assertTrue(v['holding']);self.assertIsNone(v['leg']);self.assertIsNone(v['phase_due'])
        self.e.state['clock']+=600;self.e.update_operations(self.e.state['clock']);self.assertEqual(point,(v['lat'],v['lon']))
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);v=self.vehicle('77/002');self.assertTrue(v['holding'])
        self.e.command('vehicle_order',{'vehicle':v['id'],'order':'return'})
        self.assertFalse(v.get('holding'));self.assertIsNotNone(v['leg'])
        home=self.e.home(v);self.assertEqual((v['leg']['target_lat'],v['leg']['target_lon']),(home['lat'],home['lon']))
        self.e.advance(v);self.assertEqual(v['status'],'ready');self.assertEqual((v['lat'],v['lon']),(home['lat'],home['lon']))
        radio='\n'.join(l['text'] for l in self.e.state['logs'] if l['channel']=='Funk')
        self.assertIn('77/002 von LEO, kommen.',radio);self.assertIn('LEO von 77/002, hört, kommen.',radio)
        self.assertIn('Standort halten',radio);self.assertIn('Bitte zur Heimatdienststelle einrücken.',radio)

    def test_bound_patient_and_invalid_status_orders_are_atomic(self):
        v=self.vehicle('77/002');j=self.job();self.e.dispatch({'job':j['id'],'vehicles':[v['id']]})
        before=copy.deepcopy(v)
        for order in ['return','hold']:
            with self.assertRaises(ValueError):self.e.command('vehicle_order',{'vehicle':v['id'],'order':order})
            self.assertEqual(v,before)
        self.e.detach(v)
        for status in ['ready','out','hospital','assigned','enroute','transport','scene','standby','acknowledged']:
            v['status']=status;before=copy.deepcopy(v)
            with self.assertRaises(ValueError):self.e.command('vehicle_order',{'vehicle':v['id'],'order':'hold'})
            self.assertEqual(v,before)
        v.update(status='duty',fueling=True)
        with self.assertRaises(ValueError):self.e.command('vehicle_order',{'vehicle':v['id'],'order':'return'})

    def test_new_dispatch_releases_hold(self):
        v=self.vehicle('77/002');v['status']='radio';self.e.vehicle_order({'vehicle':v['id'],'order':'hold'})
        j=self.job();self.e.dispatch({'job':j['id'],'vehicles':[v['id']]})
        self.assertFalse(v.get('holding'));self.assertEqual(v['job'],j['id'])
