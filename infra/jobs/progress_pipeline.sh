#!/usr/bin/env bash
# The whole improvement-track ("best progress") chain, serially, on the one GPU box:
#   bash infra/jobs/progress_pipeline.sh
# Base = pretrained speakleash/Bielik-11B-v2 (`bielik-11b-base`), trained = the same model after
# our DAPT + SFT, with the router + RAG harness. Every stage is skipped when its output exists,
# so a killed run resumes where it stopped. Stages:
#   0 quantize   stored NF4 checkpoint of the base (the exam's base weights, ~6.66 GB)
#   1 base       untouched base, raw + routed (the official baseline is raw)
#   2 sft0       one LoRA on the pretrained base (past papers + train_data/claude_synth.jsonl)
#   3 dapt       continued pretraining on Polish history text, merged -> bielik-11b-base-dapt
#   4 quantize   stored NF4 checkpoint of the DAPT model (the trained model's weights)
#   5 sft        the same LoRA recipe on the DAPT model
#   6 compare    sft0 vs sft (train.sh already scored raw, routed, adapters+RAG, rag); picks the better
#   7 exam env   writes $OUT/progress/exam.env (CHECKPOINT, ADAPTERS) for scripts/serve_exam.sh
# Env: STAGES="0 1 2 3 4 5 6 7" (subset to run), EVAL (default matura_all.jsonl), DAPT_TOKENS=10000000,
#      EPOCHS=2, CORPUS=$WORK/corpus. Needs the job venv (infra/jobs/common.sh).
source "$(dirname "$0")/common.sh"
STAGES="${STAGES:-0 1 2 3 4 5 6 7}"
EVAL="${EVAL:-$REPO/data/eval/matura_all.jsonl}"; export EVAL
CORPUS="${CORPUS:-$WORK/corpus}"; export CORPUS
P="$OUT/progress"; mkdir -p "$P"
has() { [[ " $STAGES " == *" $1 "* ]]; }
run() {  # run <stage-name> <command...>: logs to $P/<stage>.log, stops the chain on failure
  local s=$1; shift
  step "progress: $s"
  ( "$@" ) > "$P/$s.log" 2>&1 || { step "progress: $s FAILED (see $P/$s.log)"; finish 1; }
}
# RAG: the full Polish Wikipedia index when the corpus job built it, else the small KB.
KB="$CORPUS/rag/plwiki.sqlite"; [ -s "$KB" ] || KB="$REPO/data/kb/passages.jsonl"
python - "$KB" <<'PY'
import sys, yaml
r = yaml.safe_load(open("configs/routes.yaml")); r.setdefault("rag", {})["path"] = sys.argv[1]
yaml.safe_dump(r, open("work/routes-progress.yaml", "w"), allow_unicode=True, sort_keys=False)
PY
export ROUTES="$REPO/work/routes-progress.yaml"
TRAIN_ENV=(SINGLE_ADAPTER=1 TEACHER_HF=none EXTRA_TRAIN="$REPO/train_data/claude_synth.jsonl"
           EPOCHS="${EPOCHS:-2}" VLLM_UTIL="${VLLM_UTIL:-0.35}" SCORE_MODES=raw,routed,adapters,rag)

has 0 && [ ! -s work/checkpoints/bielik-11b-base/ship.json ] &&
  run quantize-base python scripts/quantize_checkpoint.py bielik-11b-base
has 1 && [ ! -s "$OUT/progress-base/baselines/bielik-11b-base/raw/summary.json" ] &&
  run base env NAME=progress-base OUT="$OUT/progress-base" MODELS=bielik-11b-base MODES=raw,routed \
    GPU_BUDGET_GB=14 JUDGE_HF= bash infra/jobs/baselines.sh
has 2 && [ ! -s "$OUT/progress-sft0/baselines/bielik-11b-base/adapters/summary.json" ] &&
  run sft0 env NAME=progress-sft0 OUT="$OUT/progress-sft0" TRAIN_MODELS=bielik-11b-base "${TRAIN_ENV[@]}" \
    bash infra/jobs/train.sh
DAPT_DIR=$(python -c "import yaml; print(yaml.safe_load(open('configs/models.yaml'))['models']['bielik-11b-base-dapt']['hf_id'])")
# A DAPT that already ran without merging (DAPT_MERGE=0, e.g. the Grok bot's C-033 run): merge its adapter.
has 3 && [ ! -s "$DAPT_DIR/config.json" ] && [ -s "$WORK/adapters/bielik-11b-base/domain/adapter_config.json" ] &&
  run merge-dapt python scripts/merge_dapt.py --model bielik-11b-base --work "$WORK" --merge-dir "$(dirname "$DAPT_DIR")"
has 3 && [ ! -s "$DAPT_DIR/config.json" ] &&
  run dapt env NAME=progress-dapt OUT="$OUT/progress-dapt" DAPT_MODEL=bielik-11b-base \
    DAPT_TOKENS="${DAPT_TOKENS:-10000000}" bash infra/jobs/dapt.sh
has 3 && [ ! -s "$DAPT_DIR/config.json" ] && { step "progress: DAPT model missing at $DAPT_DIR (WORK=$WORK?)"; finish 1; }
has 4 && [ ! -s work/checkpoints/bielik-11b-base-dapt/ship.json ] &&
  run quantize-dapt python scripts/quantize_checkpoint.py bielik-11b-base-dapt
has 5 && [ ! -s "$OUT/progress-sft/baselines/bielik-11b-base-dapt/adapters/summary.json" ] &&
  run sft env NAME=progress-sft OUT="$OUT/progress-sft" TRAIN_MODELS=bielik-11b-base-dapt "${TRAIN_ENV[@]}" \
    bash infra/jobs/train.sh

if has 6 || has 7; then
  python - "$OUT" "$WORK" <<'PY' > "$P/summary.md"
import json, sys
from pathlib import Path
out, work = Path(sys.argv[1]), Path(sys.argv[2])
rows = [("base (untouched)", "progress-base", "bielik-11b-base", "raw"),
        ("base, router", "progress-base", "bielik-11b-base", "routed")]
for run, key in (("progress-sft0", "bielik-11b-base"), ("progress-sft", "bielik-11b-base-dapt")):
    for mode in ("adapters", "rag"):
        rows.append((f"{run} {mode}", run, key, mode))
print("| stage | pct (scored) | pct (all rows) | earned/max | verdicts right |\n|---|---|---|---|---|")
best = None
for label, run, key, mode in rows:
    f = out / run / "baselines" / key / mode / "summary.json"
    if not f.exists():
        print(f"| {label} | – | – | – | – |"); continue
    s = json.loads(f.read_text())
    print(f"| {label} | {s.get('pct')} | {s.get('pct_all_rows')} | {s.get('earned')}/{s.get('max')} | {s.get('decision_acc')} |")
    if mode == "adapters" and (best is None or (s.get("pct") or 0) > best[0]):
        best = (s.get("pct") or 0, key)
if best:
    (out / "progress" / "exam.env").write_text(
        f"CHECKPOINT=work/checkpoints/{best[1]}\nADAPTERS={work}/adapters/{best[1]}\n")
PY
  cat "$P/summary.md"
  [ -s "$P/exam.env" ] && { step "progress: exam model -> $(tr '\n' ' ' < "$P/exam.env")"; \
    python scripts/quantize_checkpoint.py --check "$(sed -n 's/^CHECKPOINT=//p' "$P/exam.env")" \
      --adapters "$(sed -n 's/^ADAPTERS=//p' "$P/exam.env")" | tee -a "$P/summary.md"; }
fi
finish 0
