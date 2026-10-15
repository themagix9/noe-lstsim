import copy
import unittest
from pathlib import Path
import test_fleet as helpers
from hospital_specialties import available,choose_target,specialty

class HospitalProfileTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job
    def hospital(self,registry):return next(h for h in self.e.state['hospitals'] if h.get('registry_id')==registry)
    def test_operator_profiles_are_separate_from_live_acceptance(self):
        self.assertGreaterEqual(sum(bool(h.get('department_profile',{}).get('departments')) for h in self.e.state['hospitals']),26)
        self.assertIn('trauma',self.hospital('K380.2')['specialties'])
        self.assertNotIn('trauma',self.hospital('K316.1')['specialties'])
        self.assertIn('dermatology',self.hospital('K917.1')['specialties'])
        self.assertTrue(all('source' in h['department_profile'] for h in self.e.state['hospitals'] if h.get('departments')))
    def test_moedling_trauma_hours_and_child_exception(self):
        h=self.hospital('K380.1');j=self.job();j['patient']['age']=44
        self.e.state['start_date']='2026-10-14';self.e.state['clock']=10*3600;self.assertTrue(available(self.e,h,'trauma',j))
        self.e.state['clock']=18*3600;self.assertFalse(available(self.e,h,'trauma',j))
        self.e.state['start_date']='2026-10-17';self.e.state['clock']=10*3600;self.assertFalse(available(self.e,h,'trauma',j))
        j['patient']['age']=8;self.e.state['clock']=2*3600;self.assertTrue(available(self.e,h,'trauma',j))
    def test_crew_chooses_baden_for_adult_injury_and_vienna_for_skin(self):
        j=self.job();j.update(lat=48.14,lon=16.48,scene='Verletzung am Bein nach Sturz.');j['patient']['age']=42
        self.e.state['clock']=18*3600
        self.assertEqual(choose_target(self.e,j,self.vehicle('77/001'))['registry_id'],'K380.2')
        j['scene']='Hautausschlag ohne Atemnot; aktuell stabil.'
        h=choose_target(self.e,j,self.vehicle('77/001'));self.assertEqual(h['registry_id'],'K917.1');self.assertEqual(j['destination_specialty'],'Dermatologie');self.assertEqual(h['region'],'Wien')
    def test_classification_uses_scene_not_mistaken_caller(self):
        j=self.job();j.update(title='Verkehrsunfall',detail='Anrufer vermutet Unfall.',scene='Erstmaliger Krampfanfall, ansprechbar.');self.assertEqual(specialty(j),'neurology')
        j['scene']='Allergische Reaktion mit ausgeprägte Atemnot.';self.assertNotEqual(specialty(j),'dermatology')
    def test_heli_candidate_requires_landing_site(self):
        j=self.job();j.update(scene='Verletzung nach Sturz.',lat=48.14,lon=16.48)
        self.assertTrue(choose_target(self.e,j,self.vehicle('C9'))['helipad'])
    def test_user_graphics_and_custom_override_persist(self):
        self.assertEqual(self.vehicle('77/001')['graphic'],'user-rtw');self.assertEqual(self.vehicle('77/099')['graphic'],'user-nef');self.assertEqual(self.vehicle('C9')['graphic'],'user-nah')
        for file in ('rtw-user.png','nef-user.png','christophorus-user.png','ktw-user.png'):
            self.assertEqual((Path(__file__).resolve().parents[1]/'app/static/graphics'/file).read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
        self.assertEqual(self.vehicle('77/003')['graphic'],'user-ktw')
        self.assertTrue(all(v['graphic']=='responder' for v in self.e.state['vehicles'] if v['type']=='FR'))
        v=self.vehicle('77/004');self.e.command('vehicle_graphic',{'vehicle':v['id'],'graphic':'box'});self.e.command('rtwc',{'vehicle':v['id']});self.assertEqual(v['graphic'],'box')
        self.e.db.close();from engine import Engine
        self.e=Engine(self.path);self.assertEqual(self.vehicle('77/004')['graphic'],'box')

    def test_ktw_default_migration_preserves_custom_icons(self):
        from user_graphics import upgrade
        from types import SimpleNamespace
        vehicles=[{'type':t,'graphic':'van'} for t in ('KTW','KTW-B','BKTW')]
        vehicles += [{'type':'FR','graphic':'car'}, {'type':'KTW','graphic':'box','graphic_custom':True}]
        old=SimpleNamespace(state={'vehicles':vehicles,'user_graphics_version':1})
        upgrade(old)
        self.assertEqual([v['graphic'] for v in vehicles],['user-ktw']*3+['responder','box'])
        self.assertEqual(old.state['user_graphics_version'],2)
        upgrade(old)
        self.assertEqual(vehicles[-1]['graphic'],'box')

if __name__=='__main__':unittest.main()
