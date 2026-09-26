import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('qi',Path(__file__).resolve().parents[2]/'infra/small_track/forgehand_qwen_iq2.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ResumeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.config={'seed':42,'candidate_sha256':'input','files':[{'sha256':'model'}],'concurrency':2};(self.root/'manifest.json').write_text(json.dumps(dict(self.config,code_sha256='old',system=m.SYSTEM)))
  self.raw=b'{"id":"1","answer":"Original bytes", "error":null}\n';(self.root/'answers.jsonl').write_bytes(self.raw)
 def tearDown(self):self.tmp.cleanup()
 def test_skips_saved_and_preserves_bytes(self):
  saved=m.load_saved(self.root,self.config,{'1','2'},True);self.assertEqual(m.missing_rows([{'id':'1'},{'id':'2'}],saved),[{'id':'2'}]);self.assertEqual((self.root/'answers.jsonl').read_bytes(),self.raw)
 def test_config_change_rejected(self):
  with self.assertRaises(ValueError):m.load_saved(self.root,dict(self.config,seed=43),{'1'},True)
 def test_changed_system_rejected(self):
  (self.root/'manifest.json').write_text(json.dumps(dict(self.config,system='changed')))
  with self.assertRaises(ValueError):m.load_saved(self.root,self.config,{'1'},True)
 def test_unknown_and_duplicate_ids_rejected(self):
  with self.assertRaises(ValueError):m.load_saved(self.root,self.config,{'2'},True)
  (self.root/'answers.jsonl').write_bytes(self.raw+self.raw)
  with self.assertRaises(ValueError):m.load_saved(self.root,self.config,{'1'},True)
 def test_incomplete_tail_rejected_without_write(self):
  raw=self.raw+b'{';(self.root/'answers.jsonl').write_bytes(raw)
  with self.assertRaises(json.JSONDecodeError):m.load_saved(self.root,self.config,{'1'},True)
  self.assertEqual((self.root/'answers.jsonl').read_bytes(),raw)
if __name__=='__main__':unittest.main()
