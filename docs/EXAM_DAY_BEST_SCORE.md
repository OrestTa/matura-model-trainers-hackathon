# Exam day: best matura score (track 01)

The exact on-stage path for our best-score entry. Owner: thread "Win best matura score".
Status: **model frozen, mode pending the graded held-out runs** (see "Decision" below).

## What we ship

- **Model:** Gemma 4 12B QAT, `google/gemma-4-12B-it-qat-q4_0-gguf`: `gemma-4-12b-it-qat-q4_0.gguf`
  (6.98 GB) + `mmproj-gemma-4-12b-it-qat-q4_0.gguf` (0.18 GB) = **7.16 GB**, under the 8.0 GB base
  limit. Key `gemma4-12b` in `configs/models.yaml`. The exam's pictures are sent to the model.
- **Size rule (organisers, 26.09 21:46 CEST):** every model file one submission loads counts toward
  ONE budget of 8.8 GB (8 GB + 10%): base GGUF + mmproj + every LoRA the router can load (e.g. a
  picture LoRA and an essay LoRA) + Tesseract's `pol.traineddata` when the OCR route is on. `serve_exam.sh`
  sums them as measured on disk (`quantize_checkpoint.py --check ... --extra`) and refuses to serve
  over 8.8 GB. Planned ship config: 6.98 + 0.18 + ~0.13 per r16 LoRA (+ ~0.015 OCR) = about 7.3 GB with one
  LoRA, 7.45 GB with two.
- **Server:** llama.cpp `llama-server` (CUDA build), 16 slots, router on :8080.
- **Thinking: ON**, key `gemma4-12b-think` (+2000 tokens per answer for the thought). Not the deck's 8k: graded, think8k lost to 2k
  (77 vs 84 on May 2023+2024) because thought that never closes returns a blank answer. Graded over the four
  held-out papers: thinking on 169/240 (70.4%) vs thinking off 126/240 (grader, 997f811). The token
  budget must cover the thought, or the answer comes back empty (docs/FINDINGS.md, 18:30 CEST).
- **Mode:** `MODE=<raw|routed|rag>`, the best graded one of the runs below. No LoRA unless it
  beats that by ≥3 points over the four held-out papers.

## Evidence (Claude-graded against the CKE key)

| run | May 2023 mock | 4 held-out papers | note |
|---|---|---|---|
| gemma4-12b raw, thinking on by accident (16:17 CEST) | 41/60 = 68.3% | – | 6 empty answers (7 pts) from the thinking bug |
| gemma4-12b raw, thinking on (server default, 2000 cap) | – | **169/240 = 70.4%** | closed 29/38, open 109/142, essay 31/60 (316a39f) |
| gemma4-12b raw, thinking off (g4r0) | – | 126/240 = 52.5% | worse on all four papers (997f811) |
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
bash -c 'source infra/jobs/common.sh && ensure_llama_server'   # CUDA llama-server in work/llama.cpp (a subshell: common.sh sets -u and tees all output to a job log)
python -c "from huggingface_hub import hf_hub_download as d; \
  [print(d('google/gemma-4-12B-it-qat-q4_0-gguf', f)) for f in \
  ('gemma-4-12b-it-qat-q4_0.gguf', 'mmproj-gemma-4-12b-it-qat-q4_0.gguf')]"
MODEL=gemma4-12b-think MODE=<mode> PAPERS=2023-05 bash infra/jobs/rehearsal.sh   # dress rehearsal, ~10 min
```

## On stage

```bash
export LD_LIBRARY_PATH=$PWD/work/llama.cpp/build/bin:${CUDA_LIB:-/workspace/work/cuda/lib}
export THINK_FALLBACK=1   # re-ask a blank (runaway-thinking) answer once with thinking off
export GGML_CUDA_DISABLE_GRAPHS=1   # llama-server with CUDA graphs aborted mid-paper on H100 ("illegal instruction")
ADAPTERS=/nonexistent bash scripts/serve_exam.sh gemma4-12b-think &        # waits until ready
python scripts/run_exam.py <exam package dir> --model gemma4-12b-think --mode <mode> --concurrency 16 -o answers.json
```

`ADAPTERS=/nonexistent` keeps any stray trained LoRA out. Check before uploading:

```bash
python - <<'EOF'
import json; a = json.load(open("answers.json"))["answers"]
empty = [x["id"] for x in a if not x["answer"].strip()]
print(len(a), "answers,", len(empty), "empty:", empty)
EOF
```

Empty answers mean the thought used up the token budget, or the backend call timed out: re-run
those items with a bigger `think_tokens`. The router's backend timeout defaults to 1800 s (`BACKEND_TIMEOUT`,
3965be8); at 8k thinking with 8 slots a single answer can take over 300 s, and the old 300 s limit
blanked 4 of 37 May 2023 answers. Use main ≥ 3965be8 on stage.
Even at 1800 s, the 8k-thinking run g4k8 still left 4 of 37 May 2023 answers empty (runaway thinking),
scoring 38/60. On stage, `export THINK_FALLBACK=1` before serve_exam.sh: an empty or timed-out
answer is then asked once more with thinking off (matura_router/backends/openai_compat.py). It is off
by default so graded runs stay comparable. The essay must name a topic number and have
≥300 words.
