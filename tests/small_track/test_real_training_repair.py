import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('repair',ROOT/'scripts/small_track/repair_real_training.py')
repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)
class RealTrainingRepairTests(unittest.TestCase):
 def test_question_follows_source_and_ocr(self):
  prompt=repair.repaired_prompt({'context':'ORIGINAL SOURCE','question':'ORIGINAL QUESTION'},[('page.png','ACTUAL OCR')])
  self.assertTrue(prompt.startswith('ORIGINAL SOURCE'))
  self.assertTrue(prompt.endswith('ORIGINAL QUESTION'))
  self.assertLess(prompt.index('ACTUAL OCR'),prompt.index('ORIGINAL QUESTION'))
 def test_no_ocr_in_text_prompt(self):
  self.assertEqual(repair.repaired_prompt({'context':'S','question':'Q'}),'S\n\nQ')
 def test_only_explicit_single_answer_selects_official_alternative(self):
  a='Przykładowe odpowiedzi:\n• Pierwsza oficjalna odpowiedź.\n• Druga oficjalna odpowiedź.'
  answer,changes=repair.normalize_target(a,'Podaj jeden przykład.')
  self.assertEqual(answer,'Pierwsza oficjalna odpowiedź.')
  self.assertTrue(any('Select first' in x for x in changes))
 def test_multiple_requested_answers_preserved(self):
  a='Przykładowe odpowiedzi:\n• A.\n• B.'
  answer,changes=repair.normalize_target(a,'Podaj dwa przykłady.')
  self.assertIn('A.',answer);self.assertIn('B.',answer)
  self.assertFalse(any('Select first' in x for x in changes))
 def test_slash_aliases_not_guessed(self):
  a='Rzym / Imperium Rzymskie'
  self.assertEqual(repair.normalize_target(a,'Podaj nazwę.')[0],a)
if __name__=='__main__':unittest.main()
