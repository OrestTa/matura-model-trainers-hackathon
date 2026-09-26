import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('small_ocr',Path(__file__).parents[2]/'scripts/small_track/ocr.py');ocr=importlib.util.module_from_spec(spec);spec.loader.exec_module(ocr)
class OCRTests(unittest.TestCase):
 def test_candidate_keys_rejected_before_engine(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);src=p/'in';src.write_text(json.dumps({'id':'1','question':'q','official_solution':'secret'})+'\n')
   with patch.object(ocr,'assets') as assets,self.assertRaises(ValueError):ocr.enrich(src,p/'out',p/'assets',p)
   assets.assert_not_called()
 def test_image_integrity_and_root_boundary(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'x.png').write_bytes(b'image')
   with self.assertRaises(ValueError):list(ocr.image_sources({'images':[{'path':'x.png','sha256':'wrong'}]},p))
   with self.assertRaises(ValueError):list(ocr.image_sources({'images':[{'path':'../outside.png'}]},p))
 def test_original_unchanged_deduplicated_and_derived_only(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'x.png').write_bytes(b'image');sha=hashlib.sha256(b'image').hexdigest();row={'id':'1','question':'q','context':'original','source_text':'source','images':[{'path':'x.png','sha256':sha}]};src=p/'in';src.write_text(json.dumps(row)+'\n'+json.dumps(dict(row,id='2'))+'\n');before=src.read_bytes()
   def fake_assets(directory,*args):directory.mkdir(parents=True);return 'tesseract',{'total_weight_bytes':10}
   with patch.object(ocr,'assets',side_effect=fake_assets),patch.object(ocr,'run_isolated',return_value=type('Result',(),{'stdout':'Warszawa 1918'})()) as run:
    manifest=ocr.enrich(src,p/'out',p/'assets',p)
   self.assertEqual(src.read_bytes(),before);self.assertEqual(run.call_count,1);self.assertEqual(manifest['unique_images'],1)
   out=json.loads((p/'out').read_text().splitlines()[0]);self.assertEqual(out['question'],row['question']);self.assertEqual(out['source_text'],'source');self.assertEqual(out['images'],row['images']);self.assertIn('Warszawa 1918',out['context']);self.assertEqual(out['ocr_refs'],[sha])
 def test_refuse_overwriting_original(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'input'
   with self.assertRaises(ValueError):ocr.enrich(p,p,p.parent/'assets',p.parent)
if __name__=='__main__':unittest.main()
