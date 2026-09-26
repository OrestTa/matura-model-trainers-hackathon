import importlib.util
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[2]/'scripts/small_track/luna_ocr_boundary_qa.py'
spec=importlib.util.spec_from_file_location('boundary',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def packet():return {'id':'2018-05-z1','images':[{'path':'page.png'}]}
def verdict():return {'id':'2018-05-z1','decision':'accept','reason':'Source and task match, no adjacent content','image_paths':['page.png'],'neighbor_content_present':False,'required_source_complete':True,'task_page_association_unambiguous':True}
def test_accept_requires_all_boundary_checks():
 r=packet();v=verdict();assert m.validate_response(v,r)==v
 for k,value in [('neighbor_content_present',True),('required_source_complete',None),('task_page_association_unambiguous',False)]:
  v=verdict();v[k]=value
  with pytest.raises(ValueError):m.validate_response(v,r)
def test_wrong_image_or_id_rejected():
 for k,value in [('id','different'),('image_paths',['wrong.png'])]:
  v=verdict();v[k]=value
  with pytest.raises(ValueError):m.validate_response(v,packet())
def test_extra_answer_field_rejected():
 v=verdict();v['answer']='forbidden'
 with pytest.raises(ValueError):m.validate_response(v,packet())
def test_uncertain_can_retain_unknown_flags():
 v=verdict();v['decision']='uncertain';v['required_source_complete']=None
 assert m.validate_response(v,packet())['decision']=='uncertain'
