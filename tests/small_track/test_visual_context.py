import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/small_track'))
from visual_context import enrich_rows,WEIGHT_BYTES,WEIGHT_SHA
class VisualContextTests(unittest.TestCase):
 def setUp(self):
  self.row={'id':'x','question':'Q','source_text':'original','context':'Original context plus OCR','ocr_refs':['a'],'images':[{'path':'images/x.png','sha256':'a'}],'predicted_route':'open_with_images'}
  self.description={'sha256':'a','description':'A visible arrow.','is_inferred_visual_description':True,'not_verified_fact':True}
  self.manifest={'weight_bytes':WEIGHT_BYTES,'weight_sha256':WEIGHT_SHA,'network_socket_denied':True,'prompt':'Describe visible objects only.'}
 def test_preserves_original_and_ocr(self):
  before=copy.deepcopy(self.row);out,m=enrich_rows([self.row],[self.description],self.manifest)
  self.assertEqual(self.row,before);self.assertTrue(out[0]['context'].startswith(before['context']))
  for k,v in before.items():
   if k!='context':self.assertEqual(out[0][k],v)
  self.assertEqual(out[0]['visual_refs'][0]['model_sha256'],WEIGHT_SHA)
 def test_no_text_or_essay_append_even_with_image(self):
  for route in ['closed_without_images','open_without_images','essay']:
   r=dict(self.row,predicted_route=route);out,m=enrich_rows([r],[self.description],self.manifest);self.assertEqual(out,[r]);self.assertEqual(m['added_unique_weight_bytes'],0)
 def test_shared_model_counted_once(self):
  out,m=enrich_rows([self.row,dict(self.row,id='y')],[self.description],self.manifest);self.assertEqual(m['added_unique_weight_bytes'],WEIGHT_BYTES)
 def test_missing_hash_fails_full_run(self):
  with self.assertRaises(ValueError):enrich_rows([self.row],[],self.manifest)
  _,m=enrich_rows([self.row],[],self.manifest,True);self.assertFalse(m['complete_image_coverage'])
 def test_keys_bad_model_and_duplicate_rejected(self):
  for rows,descriptions,manifest in [([dict(self.row,answer='key')],[self.description],self.manifest),([self.row],[self.description],dict(self.manifest,weight_sha256='bad')),([self.row],[self.description,self.description],self.manifest)]:
   with self.assertRaises(ValueError):enrich_rows(rows,descriptions,manifest)
 def test_classifier_required(self):
  r=dict(self.row);r.pop('predicted_route')
  with self.assertRaises(ValueError):enrich_rows([r],[self.description],self.manifest)
if __name__=='__main__':unittest.main()
