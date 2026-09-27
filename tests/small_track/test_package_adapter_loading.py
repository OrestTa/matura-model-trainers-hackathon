import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/small_track'))
from package_run import adapter_args,submission_payload
class AdapterLoading(unittest.TestCase):
 def config(self):return {'routes':{str(i):{'lora':[{'id':i,'scale':1.0}]} for i in reversed(range(5))},'artifacts':{str(i):{'filename':str(i)+'.gguf'} for i in range(5)}}
 def test_single_comma_argument_preserves_server_ids(self):
  self.assertEqual(adapter_args(self.config(),Path('/package')),['--lora','/package/0.gguf,/package/1.gguf,/package/2.gguf,/package/3.gguf,/package/4.gguf','--lora-init-without-apply'])
 def test_duplicate_ids_rejected(self):
  c=self.config();c['routes']['4']['lora'][0]['id']=0
  with self.assertRaises(ValueError):adapter_args(c,Path('/package'))
 def test_comma_path_rejected(self):
  with self.assertRaises(ValueError):adapter_args(self.config(),Path('/bad,path'))
 def test_payload_matches_paired_protocol(self):
  route={'system_prompt':'Polish system','max_tokens':500,'essay_tokens':1600,'lora':[{'id':i,'scale':float(i==2)} for i in reversed(range(5))]}
  payload=submission_payload({'subtype':'image','context':'source','question':'question','points':1},{'routes':{'image':route}})
  self.assertNotIn('model',payload)
  self.assertEqual(payload['messages'][1]['content'],'source\n\nquestion')
  self.assertEqual(payload['lora'],[{'id':i,'scale':float(i==2)} for i in range(5)])
  self.assertEqual(payload['max_tokens'],500)
if __name__=='__main__':unittest.main()
