#!/usr/bin/env python3
"""Download official 2017–2026 history papers; separate candidates from keys.

Requires pymupdf. Example: python scripts/small_track_data.py --years 2023
Default builds all ten years. All copyrighted downloads/derivatives stay ignored.
The pinned repository parser is loaded read-only from Git for reproducibility.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def download(urls, path):
    errors = []
    for url in urls:
        try:
            if not path.exists():
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (research corpus)'})
                with urllib.request.urlopen(req, timeout=90) as response:
                    content = response.read()
                if not content.startswith(b'%PDF'):
                    raise ValueError('Not a PDF')
                path.write_bytes(content)
            content = path.read_bytes()
            if not content.startswith(b'%PDF'):
                raise ValueError('Cached file not PDF')
            return {'url': url, 'path': str(path.relative_to(ROOT)), 'bytes': len(content),
                    'sha256': hashlib.sha256(content).hexdigest()}
        except Exception as exc:
            errors.append(f'{url}: {exc}')
    raise RuntimeError('; '.join(errors))



def classify_candidate(question, context, points, parser):
    """Candidate-only routing. Page screenshots alone never imply visual need."""
    answer_format = parser.detect_category(question, context, points, '')
    closed = answer_format in {'closed_choice', 'true_false', 'matching', 'chronology'}
    # Vector diagrams are not always present in PDF raster-image inventories.
    visual_reference = bool(re.search(
        r'fotografi|ilustracj|karykatur|plakat|rycin|rysun|schemat|wykres|'
        r'\bmap(?:a|y|ie|ę|ą)\b|monet|medal|pieczę|banknot|znaczk|'
        r'widoczn|przedstawion\w* na|plan(?:ie|u)? miasta',
        question + '\n' + context, re.I))
    raster_marker = '[ilustracja' in context or '[ilustracja' in question
    image_dependency = parser.image_needed(context, question)
    needs_image = image_dependency or visual_reference or raster_marker
    uncertain = bool(needs_image and not (visual_reference and raster_marker))
    subtype = ('essay' if answer_format == 'essay' else
               ('closed' if closed else 'open') + ('_with_images' if needs_image else '_without_images'))
    return {'subtype': subtype, 'answer_format': answer_format,
            'needs_image': bool(needs_image), 'needs_image_uncertain': uncertain,
            'classification_method': 'candidate-only answer-format and visual-reference heuristics'}


def build(source, out, parser):
    import pymupdf
    pid = source['paper_id']
    folder = out / pid
    folder.mkdir(parents=True, exist_ok=True)
    result = {k: v for k, v in source.items() if not k.endswith('_urls')}
    result['files'] = {}
    try:
        for kind in ('paper', 'rubric'):
            result['files'][kind] = download(source[f'{kind}_urls'], folder / f'{kind}.pdf')
    except Exception as exc:
        result.update(status='download_failed', error=str(exc))
        return result
    paper = folder / 'paper.pdf'
    rubric = folder / 'rubric.pdf'
    items = parser.paper_items(parser.clean(parser.pdf_lines(paper, mark_images=True)))
    keys = parser.key_items(parser.clean(parser.pdf_lines(rubric, mark_images=False)))
    missing = [i for i in items if i['task'] not in keys]
    spare = [k for k in keys if k not in {i['task'] for i in items}]
    mappings = {}
    if len(missing) == len(spare) == 1 and missing[0]['points'] == keys[spare[0]]['points']:
        mappings[missing[0]['task']] = spare[0]
        keys[missing[0]['task']] = keys.pop(spare[0])
    pages = []
    task_pages = {}
    current_group = None
    doc = pymupdf.open(paper)
    cover = doc[0].get_text()
    denominator = re.search(r'LICZBA\s+PUNKTÓW\s+DO\s+UZYSKANIA\s*:\s*(\d+)', cover, re.I)
    if denominator:
        result['max_points'] = int(denominator[1])
        result['denominator_source'] = 'Official paper cover'
    for index, page in enumerate(doc):
        text = page.get_text(sort=True)
        image = folder / 'pages' / f'{index+1:02d}.png'
        image.parent.mkdir(exist_ok=True)
        if not image.exists():
            page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(image)
        entry = {'page': index+1, 'text': text, 'image': str(image.relative_to(ROOT))}
        pages.append(entry)
        header = re.search(r'Zadanie\.?\s+\d+(?:\.\d+)?\.', text)
        labels = re.findall(r'Zadanie\.?\s+(\d+)(?:\.(\d+))?\.', text)
        continuation = text[:header.start()] if header else text
        # Exclude the next task's page unless meaningful source text continues;
        # answer-only lined pages should not multiply vision inference cost.
        if current_group and len(re.findall(r'[^\W\d_]', continuation)) > 180:
            task_pages.setdefault(current_group, set()).add(index+1)
        for major, minor in labels:
            current_group = major
            task_pages.setdefault(major, set()).add(index+1)
            if minor:
                task_pages.setdefault(f'{major}.{minor}', set()).add(index+1)
    write_json(folder / 'paper_pages.json', pages)
    write_json(folder / 'rubric_pages.json', [{'page': n+1, 'text': p.get_text(sort=True)}
                                            for n, p in enumerate(pymupdf.open(rubric))])
    candidates, judges = [], []
    for item in items:
        task = item['task']
        page_nums = sorted(task_pages.get(task.split('.')[0], set()) | task_pages.get(task, set()))
        shared = {'id': f'{pid}-z{task}', 'paper_id': pid, 'task_id': task,
                  'year': source['year'], 'formula': source['formula'], 'split': source['split'],
                  'points': item['points'], 'max_points': item['points']}
        context, question = parser.join(item['context']), parser.join(item['question'])
        routing = classify_candidate(question, context, item['points'], parser)
        candidates.append({**shared, **routing, 'context': context,
                           'question': question, 'pages': page_nums,
                           'page_images': [pages[p-1]['image'] for p in page_nums],
                           'paper_pdf': result['files']['paper']['path']})
        key = keys.get(task, {})
        judges.append({**shared, 'official_solution': key.get('solution', ''),
                       'rubric': key.get('rubric', ''), 'key_present': bool(key),
                       'rubric_task_id': mappings.get(task, task),
                       'rubric_pdf': result['files']['rubric']['path'],
                       'solution_requires_pdf_review': bool(not key.get('solution') and item['points'] < 10)})
    for name, rows in [('candidate', candidates), ('judge', judges)]:
        (folder / f'{name}.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows))
    result.update(status='extracted', item_count=len(items), extracted_points=sum(i['points'] for i in items),
                  missing_keys=[i['task'] for i in items if i['task'] not in keys],
                  extra_keys=sorted(set(keys)-{i['task'] for i in items}), key_id_mappings=mappings,
                  candidate_path=str((folder/'candidate.jsonl').relative_to(ROOT)),
                  judge_path=str((folder/'judge.jsonl').relative_to(ROOT)),
                  page_count=len(pages), visual_policy='Full rendered paper pages, including vector diagrams',
                  extraction_note='Heuristic text extraction; page images and original PDFs are authoritative.')
    result['missing_page_images'] = [row['task_id'] for row in candidates if not row['page_images']]
    result['ready_for_scoring'] = (result['extracted_points'] == result['max_points']
                                   and not result['missing_keys'] and not result['missing_page_images'])
    write_json(folder / 'manifest.json', result)
    print(json.dumps({k:result[k] for k in ['paper_id','item_count','extracted_points','missing_keys','ready_for_scoring']}), flush=True)
    return result


def validate_corpus(out):
    """Validate real outputs: full denominator, pairing, files and key isolation."""
    forbidden = {'gold', 'gold_keywords', 'reference', 'rubric', 'official_solution', 'decision'}
    report = {'papers': 0, 'tasks': 0, 'points': 0, 'subtypes': {}, 'image_uncertain': 0}
    for entry in sorted(out.glob('*/manifest.json')):
        meta = json.loads(entry.read_text())
        candidates = [json.loads(line) for line in (entry.parent/'candidate.jsonl').read_text().splitlines()]
        judges = [json.loads(line) for line in (entry.parent/'judge.jsonl').read_text().splitlines()]
        assert len({r['id'] for r in candidates}) == len(candidates), entry
        assert [r['id'] for r in candidates] == [r['id'] for r in judges], entry
        assert sum(r['max_points'] for r in candidates) == meta['max_points'], entry
        for candidate, judge in zip(candidates, judges):
            assert not (forbidden & candidate.keys()), candidate['id']
            assert candidate['max_points'] == judge['max_points'], candidate['id']
            assert judge['key_present'] and (judge['rubric'] or judge['official_solution']), candidate['id']
            assert candidate['page_images'], candidate['id']
            assert all((ROOT/path).is_file() for path in candidate['page_images']), candidate['id']
            label = candidate['subtype']
            assert label in {'closed_without_images','closed_with_images','open_without_images','open_with_images','essay'}
            report['subtypes'][label] = report['subtypes'].get(label, 0) + 1
            report['image_uncertain'] += candidate['needs_image_uncertain']
        for file in meta['files'].values():
            assert hashlib.sha256((ROOT/file['path']).read_bytes()).hexdigest() == file['sha256']
        report['papers'] += 1
        report['tasks'] += len(candidates)
        report['points'] += meta['max_points']
    assert report['papers'], 'No papers found'
    print(json.dumps(report, indent=2))
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sources', type=Path, default=ROOT/'configs/history_2017_2026_sources.json')
    ap.add_argument('--out', type=Path, default=ROOT/'data/small_track')
    ap.add_argument('--years', help='Comma-separated years; default all ten')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--validate-only', action='store_true')
    args = ap.parse_args()
    if args.validate_only:
        validate_corpus(args.out)
        return
    config = json.loads(args.sources.read_text())
    revision = config['parser_revision']
    code = subprocess.check_output(['git','show',f'{revision}:scripts/fetch_matura.py'], cwd=ROOT)
    namespace = {'__name__':'pinned_fetch_matura', '__file__':str(ROOT/'scripts/fetch_matura.py')}
    exec(compile(code, 'pinned_fetch_matura.py', 'exec'), namespace)
    parser = SimpleNamespace(**namespace)
    sources = [s for s in config['papers'] if not args.years or str(s['year']) in args.years.split(',')]
    args.out.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda s:build(s,args.out,parser), sources))
    write_json(args.out/'manifest.json', {'schema_version':1, 'created_at':datetime.now(timezone.utc).isoformat(),
              'parser_revision':revision, 'parser_sha256':hashlib.sha256(code).hexdigest(),
              'holdout_note':config['holdout_note'], 'papers':results})


if __name__ == '__main__':
    main()
