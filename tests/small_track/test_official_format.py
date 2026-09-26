import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('official_format', Path(__file__).parents[2] / 'scripts/small_track/official_format.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
EXAM = {'exam_id': 'mock', 'items': [{'id': '1'}, {'id': '2.1'}]}

def test_exact_output_and_no_metadata():
    rows = [{'id': '2.1', 'answer': 'Żółć\nA', 'model': 'private'}, {'id': '1', 'answer': ''}]
    result = json.loads(module.export_answers(EXAM, rows))
    assert result == {'exam_id': 'mock', 'answers': [{'id': '1', 'answer': ''}, {'id': '2.1', 'answer': 'Żółć\nA'}]}

@pytest.mark.parametrize('rows', [
    [{'id': '1', 'answer': ''}],
    [{'id': '1', 'answer': ''}, {'id': '1', 'answer': ''}],
    [{'id': '1', 'answer': ''}, {'id': '2.1', 'answer': None}],
    [{'id': '1', 'answer': ''}, {'id': '2.1', 'answer': 'x' * 100001}],
])
def test_reject_invalid_submission(rows):
    with pytest.raises(ValueError):
        module.export_answers(EXAM, rows)
