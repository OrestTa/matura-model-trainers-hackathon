from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/small_track'))
from package_run import validate_candidate

def test_candidate_package_rejects_root_keys():
 with pytest.raises(ValueError):validate_candidate({'items':[],'answers':[]})
def test_candidate_package_rejects_nested_item_key():
 with pytest.raises(ValueError):validate_candidate({'items':[{'id':'1','official_solution':'secret'}]})
def test_candidate_package_accepts_source_text():
 validate_candidate({'items':[{'id':'1','source_text':'original passage','question':'Question?'}]})
