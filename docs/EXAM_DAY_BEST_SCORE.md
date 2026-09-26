# Exam day: best matura score (track 01)

The exact on-stage path for our best-score entry. Owner: thread "Win best matura score".
Status: **model frozen, mode pending the graded held-out runs** (see "Decision" below).

## What we ship

- **Model:** Gemma 4 12B QAT, `google/gemma-4-12B-it-qat-q4_0-gguf`: `gemma-4-12b-it-qat-q4_0.gguf`
  (6.98 GB) + `mmproj-gemma-4-12b-it-qat-q4_0.gguf` (0.18 GB) = **7.16 GB**, under the 8.0 GB base
  limit. Key `gemma4-12b` in `configs/models.yaml`. The exam's pictures are sent to the model.
- **Server:** llama.cpp `llama-server` (CUDA build), 16 slots, router on :8080.
- **Thinking:** off (`enable_thinking: false`, main ≥ 6359957). With it on, llama-server hides the
  thought in `reasoning_content` and short answers come back empty (docs/FINDINGS.md, 18:30 CEST).
- **Mode:** `MODE=<raw|routed|rag>`, the best graded one of the runs below. No LoRA unless it
  beats that by ≥3 points over the four held-out papers.

## Evidence (Claude-graded against the CKE key)

| run | May 2023 mock | 4 held-out papers | note |
|---|---|---|---|
| gemma4-12b raw, thinking on by accident (16:17 CEST) | 41/60 = 68.3% | – | 6 empty answers (7 pts) from the thinking bug |
| gemma4-12b raw, thinking off | pending | pending | |
| gemma4-12b routed, thinking off | pending | pending | |
| gemma4-12b-think routed | pending | pending | +2000 tokens per answer, slower |
| gemma4-12b rag (best of the two above) | pending | pending | |

References on the same mock: Gemma-3-27B via API 58.3% (too big to ship), Bielik-4.5B FP8 40.0%.

## Decision

Pick the mode with the highest total over the four held-out papers (2023-05 … 2026-05). Ties go to
the simpler mode (raw < routed < rag). Record it here and set `MODE` below.

## Before going offline (the evening before)

```bash
git pull origin main
source infra/jobs/common.sh && ensure_llama_server          # CUDA llama-server in work/llama.cpp
python -c "from huggingface_hub import hf_hub_download as d; \
  [print(d('google/gemma-4-12B-it-qat-q4_0-gguf', f)) for f in \
  ('gemma-4-12b-it-qat-q4_0.gguf', 'mmproj-gemma-4-12b-it-qat-q4_0.gguf')]"
MODEL=gemma4-12b MODE=<mode> PAPERS=2023-05 bash infra/jobs/rehearsal.sh   # dress rehearsal, ~10 min
```

## On stage

```bash
export LD_LIBRARY_PATH=$PWD/work/llama.cpp/build/bin:${CUDA_LIB:-/workspace/work/cuda/lib}
ADAPTERS=/nonexistent bash scripts/serve_exam.sh gemma4-12b &        # waits until ready
python scripts/run_exam.py <exam package dir> --model gemma4-12b --mode <mode> --concurrency 16 -o answers.json
```

`ADAPTERS=/nonexistent` keeps any stray trained LoRA out. Check before uploading:

```bash
python - <<'EOF'
import json; a = json.load(open("answers.json"))["answers"]
empty = [x["id"] for x in a if not x["answer"].strip()]
print(len(a), "answers,", len(empty), "empty:", empty)
EOF
```

Empty answers mean thinking leaked back on: re-run just those items after checking the request
carries `chat_template_kwargs.enable_thinking: false`. The essay must name a topic number and have
≥300 words.
