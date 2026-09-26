"""Validate the organizer's exam package and export its strict answer format."""
import argparse
import hashlib
import json
from pathlib import Path


def validate_exam(exam, root):
    ids = [item['id'] for item in exam['items']]
    if any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)):
        raise ValueError('Exam IDs must be unique strings')
    if sum(i['max_points'] for i in exam['items']) != exam['max_points']:
        raise ValueError('Exam denominator mismatch')
    root = Path(root).resolve()
    for item in exam['items']:
        for im in item['images']:
            path = (root / im['path']).resolve()
            if not path.is_relative_to(root):
                raise ValueError('Image path leaves exam folder')
            if hashlib.sha256(path.read_bytes()).hexdigest() != im['sha256']:
                raise ValueError(f'Image checksum mismatch: {im["path"]}')
    return ids


def export_answers(exam, rows):
    expected = [item['id'] for item in exam['items']]
    answers = {}
    for row in rows:
        ident = row['id']
        if ident not in expected or ident in answers:
            raise ValueError(f'Unknown or duplicate answer ID: {ident}')
        value = row['answer']
        if not isinstance(value, str) or len(value) > 100000:
            raise ValueError(f'Invalid answer type or length: {ident}')
        answers[ident] = value
    if set(answers) != set(expected):
        raise ValueError('Missing answers: use explicit empty strings for unanswered items')
    result = {'exam_id': exam['exam_id'], 'answers': [
        {'id': ident, 'answer': answers[ident]} for ident in expected]}
    encoded = json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8')
    if len(encoded) > 1024 * 1024:
        raise ValueError('Answer file exceeds 1 MiB')
    return encoded


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exam', required=True)
    p.add_argument('--answers', help='Inference JSONL using exact organizer IDs')
    p.add_argument('--output')
    args = p.parse_args()
    path = Path(args.exam)
    exam = json.loads(path.read_text(encoding='utf-8'))
    ids = validate_exam(exam, path.parent)
    if args.answers:
        if not args.output:
            p.error('--output required with --answers')
        rows = [json.loads(s) for s in Path(args.answers).read_text().splitlines() if s.strip()]
        Path(args.output).write_bytes(export_answers(exam, rows))
    print(json.dumps({'exam_id': exam['exam_id'], 'items': len(ids), 'max_points': exam['max_points'], 'image_checksums': 'verified'}))


if __name__ == '__main__':
    main()
