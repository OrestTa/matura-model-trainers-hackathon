# How to run (Grok Bot box)

Working directory: `/workspace`
Python env: `source .run-venv/bin/activate` (transformers / peft / torch)

## TEAM_KEY
- `secrets/team.json` -> `team_key` (also `secrets/team.env`)
- Do not commit or paste publicly
- Load: `export TEAM_KEY=$(python3 -c 'import json;print(json.load(open("secrets/team.json"))["team_key"])')`

## Geography practice (`probny`) - official sheet is GEO, not history

Questions cache: `data/official/probny_questions.json` (14 Qs).
Answer formats only (never copy into submissions): `data/official/dryrun_probny_tuned_answers.json`.

### Solver (deterministic + optional LLM)
```bash
cd /workspace && source .run-venv/bin/activate
# deterministic-only smoke (no model load):
python -c "from harness.geo_solver import try_deterministic; import json
qs=json.load(open('data/official/probny_questions.json'))
[print(q['id'], try_deterministic(q)) for q in qs]"

# full solver (loads Qwen fp16 CPU if needed):
python harness/geo_solver.py --questions data/official/probny_questions.json \
  --model models/Qwen__Qwen2.5-3B-Instruct \
  --out runs/official/probny-solver-preview.json
```

### Exam client (`harness/k3exam.py`)
```bash
cd /workspace && source .run-venv/bin/activate
# DRY-RUN only (no API submit):
python harness/k3exam.py --set probny --kind base --key "$TEAM_KEY" \
  --label "Qwen2.5-3B-Instruct untouched" --dry-run \
  --model models/Qwen__Qwen2.5-3B-Instruct

# LIVE submit - ONE practice base run; then 60 min cooldown. Prefer a single owner.
# python harness/k3exam.py --set probny --kind base --key "$TEAM_KEY" \
#   --label "Qwen2.5-3B-Instruct untouched" \
#   --model models/Qwen__Qwen2.5-3B-Instruct
```
Flags: `--model PATH`, `--adapter PATH` (history LoRA optional; not required for GEO), `--dry-run`, `--limit` (if supported), `--out PATH`.
Logs under `runs/official/`. PostgREST: `mh_start_run` -> `mh_answer` x N -> `mh_finish_run`.

**Do not start a second live `probny` run while cooldown is active.**

## Lexical RAG (history + geography)
- Chunks: `data/rag/chunks.jsonl` (93 entries; ~40 GEO facts added)
- Retrieve: `python harness/rag/retrieve.py "skala mapy"` (from repo root)
- Provenance: `data/SOURCE.md`

## History baseline / LoRA (separate track)
```bash
python harness/local_eval.py \
  --model models/Qwen__Qwen2.5-3B-Instruct \
  --data data/history/history_mcq_v1.jsonl \
  --out runs/baseline/qwen25-3b-full.json

python harness/local_eval.py \
  --model models/Qwen__Qwen2.5-3B-Instruct \
  --adapter runs/lora/qwen25-3b-history-v1 \
  --data data/history/history_mcq_v1.jsonl \
  --out runs/lora/qwen25-3b-history-v1-eval.json
```
Prior: baseline 15/30 (50%); LoRA eval 27/40 (67.5%).
If another process is loading the model, wait (`pgrep -af local_eval`).

## Tokens on this box
- Modal / HF: not present - skip gated Bielik until tokens are added locally.
