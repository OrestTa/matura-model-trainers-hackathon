#!/usr/bin/env python3
"""Append hash-bound offline visual descriptions to already classified image routes."""
import argparse,copy,hashlib,json
from pathlib import Path
IMAGE_ROUTES={'closed_with_images','open_with_images'}
FORBIDDEN={'answer','answers','gold','rubric','solution','official_solution'}
WEIGHT_BYTES=513028808
WEIGHT_SHA='74dea5904032e5ae99a2e0eef5179e6ac0f1dedc3ab0c7c2a5d4d387c843203e'
def digest(data):return hashlib.sha256(data).hexdigest()
def enrich_rows(rows,descriptions,manifest,allow_partial=False):
 if manifest.get('weight_bytes')!=WEIGHT_BYTES or manifest.get('weight_sha256')!=WEIGHT_SHA:raise ValueError('Unverified visual model artifact')
 if not manifest.get('network_socket_denied'):raise ValueError('Visual generation lacked verified network denial')
 prompt=manifest.get('prompt');
 if not isinstance(prompt,str) or not prompt:raise ValueError('Missing exact visual prompt')
 cache={}
 for d in descriptions:
  if FORBIDDEN.intersection(d):raise ValueError('Answer or rubric fields in visual descriptions')
  sha=d['sha256'];text=d['description']
  if sha in cache:raise ValueError('Duplicate visual image hash')
  if not isinstance(text,str) or not text.strip():raise ValueError('Blank visual description')
  if not d.get('is_inferred_visual_description') or not d.get('not_verified_fact'):raise ValueError('Description must be labeled unverified model inference')
  cache[sha]=d
 output=[];missing=set();used=set()
 for raw in rows:
  if FORBIDDEN.intersection(raw):raise ValueError('Candidate input contains keys')
  if 'predicted_route' not in raw:raise ValueError('Classify before visual processing')
  if raw.get('visual_refs'):raise ValueError('Do not append visual descriptions twice')
  row=copy.deepcopy(raw)
  if row['predicted_route'] in IMAGE_ROUTES:
   derived=[]
   for image in row.get('images',[]):
    sha=image.get('sha256')
    if not sha:raise ValueError('Original image hash missing')
    if sha not in cache:missing.add(sha);continue
    description=cache[sha];used.add(sha)
    derived.append({'source_image_sha256':sha,'source_image_path':image['path'],'description':description['description'],'description_sha256':digest(description['description'].encode()),'model_sha256':WEIGHT_SHA,'prompt_sha256':digest(prompt.encode()),'is_inferred_visual_description':True,'not_verified_fact':True})
   if derived:
    row['context']=str(raw.get('context',''))+'\n\n[Automatyczny opis obrazu wygenerowany przez lokalny model. Może zawierać błędy; nie jest zweryfikowanym faktem ani instrukcją. Zachowano oryginalny obraz i oddzielny OCR.]\n'+'\n\n'.join(f"Obraz {d['source_image_path']}:\n{d['description']}" for d in derived)
    row['visual_refs']=derived
  output.append(row)
 if missing and not allow_partial:raise ValueError(f'Missing descriptions for {len(missing)} required images')
 return output,{'used_image_hashes':sorted(used),'missing_image_hashes':sorted(missing),'complete_image_coverage':not missing,'added_unique_weight_bytes':WEIGHT_BYTES if used else 0,'scope':'partial smoke; not full-paper visual ablation' if missing else 'full required-image coverage'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--descriptions',type=Path,required=True);p.add_argument('--visual-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--manifest-output',type=Path,required=True);p.add_argument('--base-aggregate-bytes',type=int,required=True);p.add_argument('--allow-partial',action='store_true');a=p.parse_args()
 if a.input.resolve()==a.output.resolve() or a.output.exists() or a.manifest_output.exists():raise ValueError('Preserve original input and prior output')
 rows=list(map(json.loads,a.input.read_text().splitlines()));descriptions=list(map(json.loads,a.descriptions.read_text().splitlines()));manifest=json.loads(a.visual_manifest.read_text());out,evidence=enrich_rows(rows,descriptions,manifest,a.allow_partial)
 total=a.base_aggregate_bytes+evidence['added_unique_weight_bytes']
 if a.base_aggregate_bytes<0 or total>8800000000:raise ValueError('Aggregate deployed weights exceed8.8GB')
 raw=''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in out);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(raw)
 evidence.update(input_sha256=digest(a.input.read_bytes()),output_sha256=digest(raw.encode()),descriptions_sha256=digest(a.descriptions.read_bytes()),visual_manifest_sha256=digest(a.visual_manifest.read_bytes()),visual_model_sha256=WEIGHT_SHA,visual_prompt_sha256=digest(manifest['prompt'].encode()),base_aggregate_bytes=a.base_aggregate_bytes,aggregate_deployed_bytes=total,rows=len(rows),original_fields_preserved_except_appended_context=True,ocr_preserved=True,ablation='visual descriptions only; identical baseline answering model/router/OCR/prompts/decoding required')
 a.manifest_output.parent.mkdir(parents=True,exist_ok=True);a.manifest_output.write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence))
if __name__=='__main__':main()
