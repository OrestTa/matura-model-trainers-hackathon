import importlib.util
import json
import unittest
import tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('second_opinion',Path(__file__).resolve().parents[1]/'scripts/small_track_second_opinion.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class GradeValidationTests(unittest.TestCase):
    def test_strict_marks_and_uncertainty(self):
        valid=dict(earned_points=1,uncertain=False,rationale='Reason',rubric_reference='Task1')
        self.assertEqual(module.validate_grade(valid,2)['earned_points'],1)
        for invalid in [-1,1.5,True,'1',3,None]:
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):module.validate_grade(dict(valid,earned_points=invalid),2)
        with self.assertRaises(ValueError):module.validate_grade(dict(valid,uncertain='false'),2)
    def test_incomplete_or_unstructured_response_fails(self):
        with self.assertRaises(ValueError):module.parse_response({'status':'incomplete'},2)
        with self.assertRaises(ValueError):module.parse_response({'status':'completed','output':[{'content':[{'type':'output_text','text':'Score:1'}]}]},2)
    def test_reuse_requires_exact_binding_and_completed_grade(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'item.json'
            data=dict(status='graded',input_sha256='exact',earned_points=1,max_points=1,uncertain=False,rationale='ok',rubric_reference='task',estimated_cost_usd=0.01)
            path.write_text(json.dumps(data))
            self.assertIsNone(module.reusable_record(path,'changed'))
            copied=module.reusable_record(path,'exact')
            self.assertEqual(copied['estimated_cost_usd'],0)
            self.assertEqual(copied['estimated_cost_usd_original'],0.01)
            path.write_text(json.dumps(dict(data,status='started')))
            self.assertIsNone(module.reusable_record(path,'exact'))

    def test_exact_json_parse(self):
        grade=dict(earned_points=0,uncertain=True,rationale='Needs source image',rubric_reference='Task1')
        response={'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(grade)}]}]}
        self.assertEqual(module.parse_response(response,1),grade)
if __name__=='__main__':unittest.main()
