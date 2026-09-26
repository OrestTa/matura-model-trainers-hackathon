import copy,importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('native',ROOT/'infra/small_track/train_bielik_real_native.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_real_guide_requires_row_and_source_hash(monkeypatch):
 r={'synthetic':False,'year':2023,'id':m.GUIDE_ID,'category':'essay','paper_id':'cke-supplement20230111','source_pdf_sha256':m.GUIDE_PDF_SHA,'messages':[{'role':'assistant','content':'fixture'}]}
 monkeypatch.setattr(m,'GUIDE_ROW_SHA',m.row_sha(r));m.validate_real_row(r,m.CLEAN_MANIFEST_SHA)
 for field,value in [('id','2023-05-z29'),('source_pdf_sha256','wrong'),('year',2024),('paper_id','2023-05'),('category','open_without_images')]:
  changed=copy.deepcopy(r);changed[field]=value
  with pytest.raises(ValueError):m.validate_real_row(changed,m.CLEAN_MANIFEST_SHA)
 changed=copy.deepcopy(r);changed['messages'][0]['content']='changed'
 with pytest.raises(ValueError):m.validate_real_row(changed,m.CLEAN_MANIFEST_SHA)
 with pytest.raises(ValueError):m.validate_real_row(r,'wrongmanifest')
@pytest.mark.parametrize('year',[2015,2016,2023,2024])
def test_reserved_exam_ban(year):
 with pytest.raises(ValueError):m.validate_real_row({'synthetic':False,'year':year,'id':f'{year}-05-z1'})
class CUDA:
 def __init__(self,free):self.free=free;self.called=False
 def mem_get_info(self):return self.free,48<<30
 def set_per_process_memory_fraction(self,fraction,device):self.called=True
class Torch:
 def __init__(self,free):self.cuda=CUDA(free)
def test_memory_gate_fails_before_allocation():
 t=Torch(8<<30)
 with pytest.raises(RuntimeError):m.memory_preflight(t,.2)
 assert not t.cuda.called
 t=Torch(15<<30);report=m.memory_preflight(t,.2);assert t.cuda.called and report['fraction']==.2
@pytest.mark.parametrize('fraction',[0,-.1,.251,1])
def test_memory_fraction_ceiling(fraction):
 with pytest.raises(ValueError):m.memory_preflight(Torch(48<<30),fraction)
