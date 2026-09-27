# Exam day: best matura score (track 01)

The exact on-stage path for our best-score entry. Owner: thread "Win best matura score".
Status: **FROZEN 27.09 03:10 CEST: base Gemma 4 12B QAT, no LoRA, key `gemma4-12b-exam`, `MODE=subtype`,
`THINK_FALLBACK=1`. Open items get the exact raw 2k-thinking request that scored 163/240, closed items 5 samples with a 3-of-5 vote (Orest 22:33; same score as raw on held-out v5), and the essay gets
"plan first, then best of 3 drafts" (`ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550`, 16k thinking).**
Held-out essays (blind side-by-side, 2 runs, results/judged/heldout-essay): 71/120 vs base 56. **Measured on the full
stage run over the four held-out papers: 163/240 (38/44/39/42), the same total as the base** (essay 29/60 vs 30 when graded
paper by paper). The essay setup was chosen on the 12 practice essays first (4 blind batches, +9 to +13/150).
Dress rehearsal of this exact path (rehearsal.sh, 964c246, L40S, probny-2026-01 practice paper): 0/38 blank, 542 s,
size check 7.15 GB of 8.8 GB OK; graded 43/60 vs 37 for every earlier probny run (essay 11 vs 6–8; 7e23140).
**Why we keep the stage path over plain raw (27.09 07:30 CEST):** it measured the same total on held-out (163 vs 163),
won the practice paper (43 vs 37), and won the blind side-by-side essay comparison (71 vs 56/120). It also guards the
essay against the 300-word zero: three raw essays tonight came out at 276, 297 and 298 words (P2 pokaz, P1 probny,
SD1-run 2025), and each scores 0 under the CKE rule, while the stage path drops drafts under 300 words and targets 550.
Blind side-by-side of the stage-run essays (70e8f2f): stage 40/60 vs frozen base 35, ahead on all 4 papers. The cost is time (~10 min per paper vs ~4 for raw). If the stage time budget is tight, fall back to raw (below).
Previous freeze (26.09 22:30): `gemma4-12b-think`, `MODE=raw`.
Every fine-tune we graded scored below the base (see "Fine-tunes tried"); full table in docs/FINAL_RESULTS.md.

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
- **Mode:** `MODE=raw` (the exam prompt as given, no harness help): the best graded setting on the
  held-out papers. No LoRA: none reached base + 3.
- **Submission size:** 7.16 GB (no adapter, no OCR model), under the 8.8 GB all-models budget.

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

## Decision (22:30 CEST)

Graded with pictures viewed and the full CKE essay criteria (7e6fe48), the base scores **163/240**
(41/42/39/41; picture 67/101, text 66/79, essay 30/60). Ship bar for a fine-tune: 166/240.

### Fine-tunes tried (all rejected)

| adapter | training | graded | base on the same paper | failure |
|---|---|---|---|---|
| A1 | 1 epoch, 5,041 synth + past-paper items | May 2023 24/60 | 41 | essay loops (1,747 words), invented facts |
| B4m2 | r32, 0.5 epoch | May 2023 23/60 | 41 | essay 147 words (under 300 = 0) |
| Hm2 | r16, lr 1e-4, 0.3 epoch | May 2023 28/60 | 41 | essay 198 words |
| S4m2 | r32, 0.15 epoch, no past papers | May 2023 25/60 | 41 | essay 2/15 (factual errors), picture misreads |
| Gm3 | essay-weighted (essay_claude_synth 3x) | May 2023 20/60 | 41 | essay loops on one sentence |
| A01 | 0.1 epoch | 4 papers 131/240 | 163 | essays 7/60 (three under 300 words); short items below base on every paper |
| SD1 | self-distilled on real past papers only, thinking on | probny 36/60 | 37 (stage 43) | no gain on short items (29 vs 29–31); essay 7/15 (dd87719) |

Every adapter broke the essay and none beat the base on short items, so the picture LoRA V1 and
per-type routing (`LORA_ROUTED=1`, 7d705a3) stay unused.

The per-subtype harness (`--mode subtype`) gave **no clear gain** on the held-out papers: 123 vs raw 122 on
May 2023–2025 (c4a87e5), 77/138 vs 79.5/134 on the half-answered sweep (dab51bc). Its dev pick for open
picture questions (OCR notes) lost 6.5 pts per 100 on held-out, and its essay length guard only works in
subtype mode. So the on-stage mode is `raw` with `THINK_FALLBACK=1`.

## Before going offline (the evening before)

```bash
git pull origin main
bash -c 'source infra/jobs/common.sh && ensure_llama_server'   # CUDA llama-server in work/llama.cpp (a subshell: common.sh sets -u and tees all output to a job log)
python -c "from huggingface_hub import hf_hub_download as d; \
  [print(d('google/gemma-4-12B-it-qat-q4_0-gguf', f)) for f in \
  ('gemma-4-12b-it-qat-q4_0.gguf', 'mmproj-gemma-4-12b-it-qat-q4_0.gguf')]"
ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550 THINK_FALLBACK=1 MODEL=gemma4-12b-exam MODE=subtype CONCURRENCY=8 PAPERS=2023-05 bash infra/jobs/rehearsal.sh   # dress rehearsal, ~15 min
```

## On stage

```bash
export LD_LIBRARY_PATH=$PWD/work/llama.cpp/build/bin:${CUDA_LIB:-/workspace/work/cuda/lib}
export THINK_FALLBACK=1   # re-ask a blank (runaway-thinking) answer once with thinking off
export GGML_CUDA_DISABLE_GRAPHS=1   # llama-server with CUDA graphs aborted mid-paper on H100 ("illegal instruction")
export ESSAY_BEST_OF=3 ESSAY_MIN_WORDS=350 ESSAY_TARGET_WORDS=550   # essay: 3 drafts, keep the best one of 300+ words
ADAPTERS=/nonexistent bash scripts/serve_exam.sh gemma4-12b-exam &        # 8 slots x 24k; waits until ready
python scripts/run_exam.py <exam package dir> --model gemma4-12b-exam --mode subtype --concurrency 8 -o answers.json
# configs/subtypes.yaml: open items = the exact raw request, closed = 5-sample vote; essay = plan prompt, 16k thinking, 2600 answer tokens.
# The essay env values are also defaults in configs/subtypes.yaml `env:` (run_exam prints "essay settings: ..."; check it says 3/350/550).
# A plan the model prints before its essay is stripped (router.strip_essay_plan), so only the essay goes into answers.json.
# The essay takes ~8 min (p50 458 s on an L40S); everything else finishes first.
```

**If the stage time budget is tight** (the essay alone takes ~8 min: 16k thinking × 3 drafts, p50 458 s on an L40S):
1. `ESSAY_BEST_OF=1` (keep the plan profile and 350/550): one essay, about a third of the time; +5/150 over base on
   practice essays (2 blind batches), not checked on held-out.
2. `--mode raw --model gemma4-12b-think --concurrency 16`: the previous freeze (163/240), fastest.

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
