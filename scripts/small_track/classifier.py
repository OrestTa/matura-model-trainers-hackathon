"""Small deterministic router using only candidate task text and input metadata."""
import re

VERSION = 'rules-v1'

def classify(row):
    question = row.get('question', '').lower()
    if re.search(r'wypracowani|minimum\s+300|co najmniej\s+300', question) or row.get('max_points', row.get('points', 0)) >= 12:
        return {'subtype': 'essay', 'classifier': VERSION, 'reason': 'essay instruction or point allocation'}
    closed = bool(re.search(r'oceń prawdziwość|zaznacz.*(?:odpowiedź|odpowiedzi)|wybierz.*(?:odpowiedź|odpowiedzi)|uzupełnij tabelę.*numer', question, re.S))
    # Official images array is authoritative for whether images are supplied.
    images = bool(row['images']) if 'images' in row else bool(row.get('needs_image', False))
    return {'subtype': ('closed' if closed else 'open') + ('_with_images' if images else '_without_images'),
            'classifier': VERSION, 'reason': 'task syntax and supplied image metadata',
            'needs_image': images}
