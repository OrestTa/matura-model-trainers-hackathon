import importlib.util
from pathlib import Path
import unittest

SPEC=importlib.util.spec_from_file_location('fresh_luna',Path(__file__).resolve().parents[2]/'scripts/small_track/local_luna_fresh_grade.py')
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)

class GradeEvidenceValidation(unittest.TestCase):
    def setUp(self):
        self.packet={'id':'4.2','max_points':1,'original_images':[{'path':'/original.png'}]}
        self.grade={'id':'4.2','earned_points':0,'uncertain':False,'rationale':'Saved judge rationale','rubric_reference':'Official criterion','viewed_images':['/original.png']}

    def test_zero_with_actual_image_metadata_is_preserved(self):
        self.assertIs(MODULE.validate_grade(self.grade,self.packet),self.grade)

    def test_missing_or_foreign_image_metadata_rejected_even_for_zero(self):
        for paths in [[],['/different.png']]:
            with self.subTest(paths=paths),self.assertRaises(AssertionError):
                MODULE.validate_grade({**self.grade,'viewed_images':paths},self.packet)

    def test_boolean_and_out_of_range_points_rejected(self):
        for points in [True,-1,2]:
            with self.subTest(points=points),self.assertRaises(AssertionError):
                MODULE.validate_grade({**self.grade,'earned_points':points},self.packet)

    def test_wrong_id_and_extra_fields_rejected(self):
        for change in [{'id':'other'},{'extra':'unexpected'}]:
            with self.subTest(change=change),self.assertRaises(AssertionError):
                MODULE.validate_grade({**self.grade,**change},self.packet)

    def test_text_item_requires_empty_image_metadata(self):
        packet={**self.packet,'original_images':[]}
        grade={**self.grade,'viewed_images':[]}
        self.assertEqual(MODULE.validate_grade(grade,packet),grade)

if __name__=='__main__':unittest.main()
