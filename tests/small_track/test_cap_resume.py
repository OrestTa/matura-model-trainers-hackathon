import importlib.util,json
from pathlib import Path
import pytest

MODULE=Path(__file__).resolve().parents[2]/'infra/small_track/nebius_cap_ablation.py'
spec=importlib.util.spec_from_file_location('cap_resume',MODULE);cap=importlib.util.module_from_spec(spec);spec.loader.exec_module(cap)

def test_resume_preserves_control_when_raised_was_interrupted(tmp_path):
 out=tmp_path/'run';manifest={'candidate_sha256':'frozen','control_caps':[500,1600],'variant_caps':[1000,2400],'base_only':True,'concurrency':1}
 cap.prepare_output(out,manifest,False,{'1','2'})
 answer={'id':'1','answer':'Already generated','error':None}
 (out/'control/answers.jsonl').write_text(json.dumps(answer)+'\n')
 saved=cap.prepare_output(out,manifest,True,{'1','2'})
 assert saved['control']['1']==answer and '1' not in saved['raised']
 assert [r['id'] for r in cap.pending_rows([{'id':'1'},{'id':'2'}],saved)]==['1','2']
 (out/'raised/answers.jsonl').write_text(json.dumps(answer)+'\n')
 saved=cap.prepare_output(out,manifest,True,{'1','2'})
 assert [r['id'] for r in cap.pending_rows([{'id':'1'},{'id':'2'}],saved)]==['2']

@pytest.mark.parametrize('change',[{'candidate_sha256':'other'},{'variant_caps':[800,2400]},{'base_only':False},{'concurrency':2}])
def test_resume_rejects_changed_frozen_protocol(tmp_path,change):
 out=tmp_path/'run';m={'candidate_sha256':'frozen','variant_caps':[1000,2400],'base_only':True,'concurrency':1};cap.prepare_output(out,m,False,{'1'})
 with pytest.raises(ValueError,match='configuration'):cap.prepare_output(out,dict(m,**change),True,{'1'})
 assert json.loads((out/'manifest.json').read_text())==m

def test_resume_rejects_duplicate_saved_answer_ids(tmp_path):
 out=tmp_path/'run';cap.prepare_output(out,{},False,{'1'});(out/'control/answers.jsonl').write_text('{"id":"1"}\n{"id":"1"}\n')
 with pytest.raises(ValueError,match='duplicate'):cap.prepare_output(out,{},True,{'1'})
