import importlib.util,re,json
from pathlib import Path
from types import SimpleNamespace
ROOT=Path.cwd()
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=module('parser',ROOT/'scripts/fetch_matura.py');b=module('builder',ROOT/'scripts/small_track_data.py');original=p.pdf_lines
def lines(*a,**kw):return [re.sub(r'\((\d+)\s*pkt\)',r'(0–\1)',x) for x in original(*a,**kw)]
p.pdf_lines=lines
for y in range(2010,2015):
 folder=ROOT/f'data/small_track_legacy/{y}-05';old=json.loads((folder/'manifest.json').read_text());(folder/'download-manifest.json').write_text(json.dumps(old,ensure_ascii=False,indent=2));source={'year':y,'paper_id':f'{y}-05','formula':'pre-2015','split':'training_eligible_pending_QA','max_points':50,'paper_urls':[old['files']['paper']['url']],'rubric_urls':[old['files']['rubric']['url']],'license':'Copyright CKE; no open redistribution license verified','provenance':'CKE documents from Arkusze.pl mirror','training_ready':False};b.build(source,ROOT/'data/small_track_legacy',p)
