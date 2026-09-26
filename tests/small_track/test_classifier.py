import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / 'scripts/small_track'))
from classifier import classify
from harness import load_rows

def test_routes_use_question_and_images():
    assert classify({'question': 'Oceń prawdziwość stwierdzeń.', 'images': []})['subtype'] == 'closed_without_images'
    assert classify({'question': 'Zaznacz właściwą odpowiedź.', 'images': [{}]})['subtype'] == 'closed_with_images'
    assert classify({'question': 'Wyjaśnij przyczyny.', 'images': []})['subtype'] == 'open_without_images'
    assert classify({'question': 'Rozstrzygnij i uzasadnij.', 'images': [{}]})['subtype'] == 'open_with_images'
    assert classify({'question': 'Wybierz temat. Minimum 300 wyrazów.', 'images': []})['subtype'] == 'essay'

def test_official_sources_and_format_preserved(tmp_path):
    import json
    path = tmp_path / 'exam.json'
    path.write_text(json.dumps({'exam_id': 'test', 'max_points': 1, 'instructions': 'Instrukcja', 'items': [
        {'id': '2.1', 'max_points': 1, 'question': 'Wyjaśnij.', 'source_text': 'Źródło', 'images': [], 'answer_format': 'Tekst'}]}))
    row = load_rows(path)[0]
    assert row['id'] == '2.1'
    assert 'Źródło' in row['context'] and 'Instrukcja' in row['context'] and 'Tekst' in row['context']
    assert row['subtype'] == 'open_without_images'
