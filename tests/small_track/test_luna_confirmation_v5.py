import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/small_track'))
from luna_confirmation_v5 import choose_verdict, validation_issues, policy_hash

class ConfirmationPolicy(unittest.TestCase):
    def setUp(self):
        self.packet={'id':'1','max_points':1,'original_images':[{'path':'/original.png'}]}
        self.grade={'id':'1','earned_points':0,'uncertain':False,'rationale':'Criterion absent',
                    'rubric_reference':'Official point criterion','point_awards':[{'point_number':1,'awarded':False,'criterion':'Required fact','evidence':'No answer','requirements_met':False}],
                    'components':[{'label':'Task','max_points':1,'earned_points':0,'reason':'No answer'}],
                    'viewed_images':[],'visual_basis':'unnecessary_for_decision','visual_explanation':'Empty answer earns no points regardless of image content.',
                    'self_consistent':True,'consistency_explanation':'No point condition met; total zero.','unresolved_reasons':[]}
    def earned(self):
        g=copy.deepcopy(self.grade);g['earned_points']=1;g['point_awards'][0].update(awarded=True,requirements_met=True);g['components'][0]['earned_points']=1;return g
    def test_policy_hash_frozen(self):
        self.assertEqual(policy_hash(),'e4d579e874a7eec9ca1b4191ad8a540b14caea70c1c433500aa7dde849a9c870')
    def test_zero_without_unnecessary_image_inspection_resolves(self):
        self.assertEqual(validation_issues(self.grade,self.packet),[])
        self.assertEqual(choose_verdict(self.grade,self.packet)['points'],0)
    def test_false_image_inspection_fails(self):
        self.assertIn('image_inspection_metadata',validation_issues({**self.grade,'visual_basis':'inspected'},self.packet))
    def test_malformed_responses_remain_unresolved(self):
        for g in [None,[],0,{},'bad']:
            with self.subTest(g=g): self.assertFalse(choose_verdict(g,self.packet)['resolved'])
    def test_points_boolean_not_integer(self):
        self.assertIn('point_range',validation_issues({**self.grade,'earned_points':True},self.packet))
    def test_awarded_point_requires_criteria(self):
        g=self.earned();g['point_awards'][0]['requirements_met']=False
        self.assertIn('point_awards_contradiction',validation_issues(g,self.packet))
    def test_component_sum_contradiction(self):
        g=self.earned();g['components'][0]['earned_points']=0
        self.assertIn('component_contradiction',validation_issues(g,self.packet))
    def test_essay_repeat_does_not_pick_highest(self):
        r=choose_verdict(self.grade,self.packet,[self.grade,self.earned(),self.grade])
        self.assertFalse(r['resolved']);self.assertEqual(r['provisional_points'],0);self.assertEqual((r['lower'],r['upper']),(0,1))
    def test_clarification_can_lower_or_raise(self):
        for primary,clarification in [(self.earned(),self.grade),(self.grade,self.earned())]:
            r=choose_verdict(primary,self.packet,clarification=clarification,external_flags=['logical_contradiction'])
            self.assertTrue(r['resolved']);self.assertEqual(r['points'],clarification['earned_points'])
    def test_unneeded_clarification_cannot_replace_first(self):
        r=choose_verdict(self.grade,self.packet,clarification=self.earned())
        self.assertEqual(r['points'],0);self.assertEqual(r['selected_source'],'initial_first')
    def test_uncertain_clarification_stays_unresolved(self):
        g={**self.grade,'uncertain':True,'unresolved_reasons':['Unreadable evidence']}
        r=choose_verdict(None,self.packet,clarification=g)
        self.assertFalse(r['resolved']);self.assertIsNone(r['points'])
    def test_three_consistent_essay_marks_resolve(self):
        self.assertTrue(choose_verdict(self.grade,self.packet,[self.grade]*3)['resolved'])
if __name__=='__main__':unittest.main()
