import copy
import unittest
from unittest.mock import patch
import test_fleet as helpers
from scenario_catalog import CATALOG
from scenarios import EXTRA_SCENARIOS
from manv_scenarios import MANV_SCENARIOS
from caller_context import groups_for,answer_for,gender_for_name

class CallerContextTests(unittest.TestCase):
    setUp=helpers.FleetTests.setUp
    tearDown=helpers.FleetTests.tearDown
    def call(self,id):
        s=next(s for s in CATALOG+EXTRA_SCENARIOS+MANV_SCENARIOS if s['scenario_id']==id)
        j=self.e.new_job('emergency',scenario=s);self.e.prepare_call(j)
        return j
    def test_entire_catalogue_has_consistent_self_perspective(self):
        count=0
        for scenario in CATALOG+EXTRA_SCENARIOS+MANV_SCENARIOS:
            j=self.e.new_job('emergency',scenario=scenario);self.e.prepare_call(j);call=j['call']
            self.assertIn(call['context']['role'],('self','relative','witness','group','agency'))
            if call['context']['role']!='self':continue
            count+=1
            text=answer_for(call,[q for q in call['questions'] if q['key'] in ('patient','consciousness','breathing')])
            self.assertNotIn('ungefähr',text);self.assertNotIn('Die Person',text)
            self.assertNotIn('Wer ist betroffen',str(groups_for(call)))
            self.assertIsNotNone(call['context']['age'])
            if call['context']['age'] is not None:self.assertIn(f"Ich bin {call['context']['age']} Jahre alt.",text)
        self.assertGreater(count,50)
    def test_dog_bite_self_age_and_no_invented_door_helper(self):
        j=self.call('dog-bite');call=j['call'];answers={q['key']:q['answer'] for q in call['questions']}
        self.assertEqual(answers['patient'],'Ich bin 31 Jahre alt.')
        self.assertNotIn('zweite Person',answers['access']);self.assertNotIn('direkt davor',answers['location'])
        self.assertIn('ich bin',answers['location'])
        self.assertFalse(j.get('code_confirmed'))
    def test_relative_knows_child_age_but_witness_estimates_it(self):
        call=self.call('child-poison')['call'];self.assertIn('4 Jahre',call['questions'][2]['answer']);self.assertNotIn('ungefähr',call['questions'][2]['answer'])
        call=self.call('assault')['call'];self.assertIn('ungefähr',call['questions'][2]['answer'])
    def test_pregnant_self_caller_has_female_name_and_voice(self):
        from caller_context import normalize_questions
        j=self.call('birth-imminent');j['call']['caller_name']='Simon Eder'
        normalize_questions(j)
        from voice_profiles import caller_profile
        self.assertEqual(j['call']['caller_gender'],'female');self.assertEqual(gender_for_name(j['call']['caller_name']),'female')
        self.assertEqual(caller_profile(j)['model'],'female')
    def test_remote_witness_does_not_invent_breathing_observation(self):
        call=self.call('zone5-118')['call'];answers={q['key']:q['answer'] for q in call['questions']}
        self.assertIn('nicht erkennen',answers['consciousness']);self.assertIn('nicht sagen',answers['breathing'])
    def test_co_alarm_reports_two_people(self):
        self.assertEqual(self.call('co-alarm')['call']['questions'][2]['answer'],'Zwei Personen sind betroffen.')
    def test_restore_normalizes_only_future_rows(self):
        j=self.call('dog-bite')
        with patch.dict('os.environ',{'CALL_AUTO':'1'}):
            self.e.accept_call(j);call=j['call'];spoken=copy.deepcopy(call['transcript']);call.pop('context_version')
            for row in call['pending']:
                if 'patient' in row.get('answered_keys',[]):row['text']='Eine Person, ungefähr 31 Jahre alt.'
            self.e.resume_calls()
        self.assertEqual(spoken,call['transcript']);self.assertIn('Ich bin 31 Jahre alt.',next(row['text'] for row in call['pending'] if 'patient' in row.get('answered_keys',[])))
