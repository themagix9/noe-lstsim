import copy
import os
import unittest
from unittest.mock import patch
import test_fleet as helpers

class TelemedicineTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    vehicle=helpers.FleetTests.vehicle
    job=helpers.FleetTests.job

    def scene(self,score=60,unit=None):
        j=self.job();v=unit or self.vehicle('77/002')
        j.update(status='scene',vehicles=[v['id']],scene_report={'text':'Patient benötigt weitere Einschätzung.'},no_patient=False)
        v.update(job=j['id'],status='scene',assessment_due=0,phase_due=None,lat=j['lat'],lon=j['lon'])
        j['patient_condition'].update(percent=score,notarzt_required=score<45,reported=True)
        return j,v

    def book(self,j,v):
        c=self.e.raise_radio(j,v,'Telenotarzt',reason_initial=True)
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'listen'})
        self.e.radio_action({'job':j['id'],'call':c['id'],'step':'confirm'})
        return j['telenotarzt']

    def test_booking_sends_phone_on_both_channels_without_vehicle_or_status(self):
        j,v=self.scene();count=len(self.e.state['vehicles']);t=self.book(j,v)
        self.assertEqual(t['name'],'Telenotarzt');self.assertNotIn('status',t)
        self.assertEqual(len(self.e.state['vehicles']),count);self.assertEqual(j['vehicles'],[v['id']])
        for channel in ('SDS','ESApp'):
            messages=[m for m in self.e.state['messages'] if m['job']==j['id'] and m['channel']==channel]
            self.assertEqual(len(messages),1);self.assertIn(t['phone'],messages[0]['text']);self.assertEqual(messages[0]['vehicle'],v['id'])
        self.assertEqual(self.e.snapshot()['telenotarzt_pool'],{'total':10,'available':9})

    def test_phone_connection_then_care_no_bonus_before_call_and_pool_persists(self):
        j,v=self.scene();t=self.book(j,v);now=self.e.state['clock']
        with patch.dict(os.environ,{'PATIENT_EVOLUTION':'1'}):
            self.e.update_telenotarzt(now+29);self.assertEqual(j['patient_condition']['percent'],60)
            self.e.state['clock']=now+30;self.e.update_telenotarzt(now+30)
            self.assertTrue(self.e.tna_active(j));self.assertEqual(j['patient_condition']['percent'],60)
            self.e.state['clock']=now+90;self.e.update_telenotarzt(now+90);self.assertEqual(j['patient_condition']['percent'],63)
        self.e.save();self.e.db.close()
        from engine import Engine
        self.e=Engine(self.path);j=self.e.get('jobs',j['id'])
        self.assertEqual(j['telenotarzt']['phone'],t['phone']);self.assertTrue(self.e.tna_active(j));self.assertEqual(len(self.e.tna_free_slots()),9)

    def test_pool_exhaustion_atomic_failure_and_reuse(self):
        units=[v for v in self.e.state['vehicles'] if v['type'] in ('KTW','RTW','RTW-C')][:11]
        jobs=[]
        for unit in units[:10]:
            j,v=self.scene(unit=unit);jobs.append(j);self.e.allocate_telenotarzt(j,v)
        self.assertEqual(self.e.tna_free_slots(),[])
        j,v=self.scene(unit=units[10]);before=len(self.e.state['messages'])
        with self.assertRaises(ValueError):self.e.allocate_telenotarzt(j,v)
        self.assertNotIn('telenotarzt',j);self.assertEqual(len(self.e.state['messages']),before)
        self.e.release_telenotarzt(jobs[0]);t=self.e.allocate_telenotarzt(j,v);self.assertEqual(t['slot'],1)

    def test_telenotarzt_releases_on_transport_and_cannot_escort(self):
        j,v=self.scene();self.book(j,v);j.update(destination='kh-hainburg',bed_state='crew_selected')
        self.e.start_transport(v)
        self.assertNotIn('telenotarzt',j);self.assertEqual(v['status'],'transport')
        self.assertFalse(any(u.get('escort_of')==v['id'] for u in self.e.state['vehicles']))
        self.assertEqual(len(self.e.tna_free_slots()),10)

    def test_critical_telephone_assessment_requests_actual_nef(self):
        j,v=self.scene(30);t=self.book(j,v);now=self.e.state['clock']+30
        self.e.state['clock']=now
        with patch.object(self.e,'maybe_request_transport_heli',return_value=False):self.e.update_telenotarzt(now)
        requests=[c for c in self.e.state['radio_calls'] if c['kind']=='NEF' and c['state']!='closed']
        self.assertEqual(len(requests),1);self.assertIn('Telenotarzt',requests[0]['reason'])
        self.e.update_telenotarzt(now+10)
        self.assertEqual(sum(c['kind']=='NEF' for c in self.e.state['radio_calls']),1)

    def test_zero_score_never_revived_and_doctor_takes_over(self):
        j,v=self.scene(0);t=self.book(j,v);now=self.e.state['clock']+30;self.e.state['clock']=now
        self.e.update_telenotarzt(now)
        with patch.dict(os.environ,{'PATIENT_EVOLUTION':'1'}):self.e.update_telenotarzt(now+60)
        self.assertEqual(j['patient_condition']['percent'],0)
        nef=self.vehicle('77/099');nef.update(job=j['id'],status='scene',assessment_due=0)
        self.e.sync_telenotarzt();self.assertNotIn('telenotarzt',j)

    def test_other_owner_cannot_release_and_invalid_crew_cannot_book(self):
        j,v=self.scene();self.book(j,v);j['owner']='someone'
        with self.assertRaises(ValueError):self.e.command('telenotarzt_release',{'job':j['id'],'_actor':{'id':'other'}})
        self.assertIn('telenotarzt',j)
        j2,v2=self.scene(unit=self.vehicle('77/011'));v2['status']='enroute'
        with self.assertRaises(ValueError):self.e.allocate_telenotarzt(j2,v2)

    def test_moderate_scene_can_generate_telephone_request_but_kt_remains_quiet(self):
        j,v=self.scene();self.e.state['radio_calls']=[]
        with patch('random.random',return_value=0):self.e.maybe_telenotarzt_request(j,v)
        self.assertEqual(self.e.state['radio_calls'][-1]['kind'],'Telenotarzt')
        j2,v2=self.scene(unit=self.vehicle('77/011'));j2['kind']='transport'
        before=len(self.e.state['radio_calls']);self.e.maybe_telenotarzt_request(j2,v2);self.assertEqual(len(self.e.state['radio_calls']),before)

    def test_concurrent_eleventh_booking_cannot_overbook_pool(self):
        import threading
        units=[v for v in self.e.state['vehicles'] if v['type'] in ('KTW','RTW','RTW-C')][:11]
        requests=[]
        for unit in units:
            j,v=self.scene(unit=unit);c=self.e.raise_radio(j,v,'Telenotarzt',reason_initial=True)
            self.e.radio_action({'job':j['id'],'call':c['id'],'step':'listen'});requests.append((j,c))
        barrier=threading.Barrier(11);results=[]
        def book(item):
            j,c=item;barrier.wait()
            try:self.e.command('radio',{'job':j['id'],'call':c['id'],'step':'confirm'});results.append(True)
            except ValueError:results.append(False)
        threads=[threading.Thread(target=book,args=(item,)) for item in requests]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        self.assertEqual(results.count(True),10);self.assertEqual(results.count(False),1)
        slots=[j['telenotarzt']['slot'] for j in self.e.state['jobs'] if j.get('telenotarzt')]
        self.assertEqual(len(set(slots)),10)

    def test_split_calltaker_cannot_release_telenotarzt(self):
        from sessions import Sessions
        from pathlib import Path
        sessions=Sessions(str(Path(self.tmp.name)/'roles.sqlite3'))
        try:
            auth=sessions.create({'name':'Dispo','workflow':'split','role':'dispatcher'})
            host=sessions.member(auth['token']);code=sessions.snapshot(host)['session']['code']
            auth2=sessions.join({'name':'Calltaker','code':code,'role':'calltaker'})
            member=sessions.member(auth2['token'])
            with self.assertRaises(PermissionError):sessions.command(member,'telenotarzt_release',{'job':'missing'})
        finally:sessions.close()

    def test_automatic_tna_request_waits_for_initial_scene_report_to_close(self):
        j,v=self.scene();c=self.e.raise_scene_radio(j,v,force=True)
        with patch.dict(os.environ,{'REINFORCEMENTS_AUTO':'1'}),patch('random.random',return_value=0):
            self.e.update_telenotarzt(self.e.state['clock'])
            self.assertFalse(any(c['kind']=='Telenotarzt' for c in self.e.state['radio_calls']))
            self.e.radio_action({'job':j['id'],'call':c['id'],'step':'end'})
            self.e.update_telenotarzt(self.e.state['clock']+1)
            self.assertEqual(self.e.state['radio_calls'][-1]['kind'],'Telenotarzt')
