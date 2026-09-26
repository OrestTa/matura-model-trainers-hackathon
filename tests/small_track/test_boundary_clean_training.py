import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/small_track'))
from prepare_boundary_clean_training import eligible,GUIDE_ID,GUIDE_SHA

def guide():return {'synthetic':False,'year':2023,'id':GUIDE_ID,'category':'essay','source_pdf_sha256':GUIDE_SHA,'paper_id':'cke-supplement20230111'}
def test_exact_guide_allowlist():eligible(guide())
@pytest.mark.parametrize('field,value',[('id','2023-05-z29'),('source_pdf_sha256','wrong'),('category','open_without_images'),('paper_id','2023-05')])
def test_guide_allowlist_does_not_allow_other_eval_rows(field,value):
 r=guide();r[field]=value
 with pytest.raises(ValueError):eligible(r)
def test_synthetic_disallowed():
 r=guide();r['synthetic']=True
 with pytest.raises(ValueError):eligible(r)
