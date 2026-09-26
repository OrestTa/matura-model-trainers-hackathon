# Plan: staggered expert harness for the exam (2026-09-27 morning)

Written 2026-09-26 ~13:00 CEST. Inspired by the workshop repo
[stared/train-llm-from-scratch](https://github.com/stared/train-llm-from-scratch)
(data and tokens → pretraining → SFT → RLVR, with a live viewer of every run).
Deadline: **2026-09-27 11:00 CET**. Size cap assumed: **everything we ship ≤ 8.9 GB on disk**
(STATUS/INSIGHTS say the official cap is 8 GB, with ~8.9 GB only if the organizers allow it; confirm
before we pick the budget-heavy option below).

## 1. The idea in one line

Answer each question at the **cheapest stage that is confident**, and escalate only when it isn't:

```
question ─► S0 rules/tools ─► S1 router ─► S2 expert (base + LoRA for that type) ─► S3 check ─► answer
              (free, exact)    (which type?)   (one adapter per question type)       (vote / verify / retry)
```

"Staggered" means two things here. At run time, the stages above form a cascade. For training, we
build and ship in waves, and each wave is scored before the next one starts, so we always have a
submittable stack.

## 2. Stages at exam time

| Stage | What | Size | Already in repo |
|---|---|---|---|
| S0 | Deterministic solvers: regex/format parsing, lookup tables, RAG over CKE materials, geo tools (15/15 on practice) | ~0.1 GB index | `harness/`, geo harness |
| S1 | Router: rule classifier by question type, LLM fallback when unsure | 0 (rules) | `matura_router/classifier.py` |
| S2 | One shared base model, 4-bit, plus one LoRA adapter per question type (`closed_choice`, `true_false`, `matching`, `chronology`, `source_analysis`, `short_open`, `essay`) | base 5.8–6.5 GB + 7 × ~0.1 GB | `configs/routes.yaml`, `scripts/train_lora.py` |
| S3 | Check: self-consistency (k=5 samples, majority) on auto-scorable types; format validator with retry; for open answers, the base model grades its own draft against the rubric once | 0 | new, small (`matura_router/router.py`) |

The size budget decides the base model:

| Option | Base | Adapters | Extra | Total |
|---|---|---|---|---|
| **A (default)** | Bielik-11B bnb-4bit 6.5 GB | 7 × ~0.15 GB | RAG index ~0.1 GB | **~7.6 GB** |
| B (small prize) | Bielik-4.5B 4-bit 2.9 GB | 7 × ~0.08 GB | — | ~3.5 GB |
| C (if 8.9 allowed) | Qwen2.5-7B GPTQ-Int8 8.88 GB | none fit | — | 8.88 GB, no experts, so don't pick it |

Option A is the main entry. We also submit B for "Mały, ale wariat" (≥ 35 %). Whatever the
baselines chart shows as best under the cap overrides this table.

## 3. Training, in the workshop's four steps

1. **Data and tokens.** Check how each candidate tokenizer splits Polish exam text (tokens per
   word). Bielik's tokenizer is Polish-native, and fewer tokens means more context and faster
   essays. It takes one script and one chart.
2. **"Pretraining" = continued pretraining (DAPT), not from scratch.** A 30M model from scratch (the
   workshop's step 2) is a nice chart for the demo, but it can't pass the exam. Instead: one LoRA
   pass of next-token loss over Polish exam-domain text (CKE informators, past papers' source texts,
   Wolne Lektury readings on the reading list, PL Wikipedia history/geography). About 1 h on the
   L40S. Merge it into the base before per-type SFT, or keep it as a shared "domain" adapter.
3. **SFT per question type** (the workshop's prawko recipe, which is what `train.sh` runs now):
   teacher-generated items in the exact answer format, one adapter per type. For MCQ types, log
   the A/B/C/D probabilities per checkpoint, like the workshop's SFT view.
4. **RLVR (GRPO) on the auto-scorable types** (`closed_choice`, `true_false`, `matching`,
   `chronology`). Reward = 1 if exact match with the synthetic item's known key, plus a format
   reward (the workshop's "six words" exercise is exactly a format reward). Start from the SFT
   adapter, 8 samples per prompt, ~300 steps per type, TRL `GRPOTrainer`. Hold out 20 % of the
   synthetic items and the real CKE eval as the dev set. Keep the RL adapter only if the real eval
   goes up.

Open types (`essay`, `short_open`, `source_analysis`) stay SFT only: there's no reliable
verifier, and an LLM-judge reward invites reward hacking overnight.

## 4. Visualization (what the jury and we look at)

Borrow the workshop viewer's model: every run writes `runs/<name>/` JSON (loss curve,
checkpoints, sampled answers, rewards). Our charts (`scripts/plot_baselines.py`, report in
`work/out/report/`) gain:

- **Staircase chart:** score per model for plain → routed → +SFT adapters → +RLVR → +S3 check,
  one bar per stage, for bases A and B. This is the "progress prize" story.
- **Cascade chart:** per question type, the share answered at S0/S2/S3 and each stage's accuracy.
- **Type × stage heatmap:** where each adapter helps or hurts (sets `adapter: null` in routes).
- **Size bar:** base + adapters + index against the cap line.
- **Training curves:** SFT loss per adapter, GRPO reward and dev accuracy per step.

## 5. Waves and timeline (CEST)

| When | Wave | Compute | Output |
|---|---|---|---|
| Now–15:00 | Baselines for all candidates | Modal (other thread) | pick base A/B |
| Now–16:00 | W1: teacher data (Qwen3-30B-A3B FP8) + SFT adapters for Bielik-11B | L40S VM (`tmux train`) | `work/adapters/bielik-11b/*` |
| 15:00–18:00 | W2: DAPT LoRA on domain text; SFT for base B | Modal L40S | domain adapter, B adapters |
| 17:00–21:00 | W3: GRPO on the 4 auto-scorable types, from W1 adapters | L40S VM | RL adapters + reward curves |
| 21:00–23:00 | W4: S3 check (vote/validate/retry), full eval, staircase + cascade charts | VM | report, `routes.yaml` final |
| 23:00–01:00 | Freeze: pack base + adapters, size check, offline dry run of `matura_router serve` | laptop/VM | ship bundle ≤ cap |
| 08:00–11:00 | Exam: run, submit base (`--modes raw`) and harness | exam box | answers |

Each wave ends with a scored eval committed to `results/` and a line in `docs/FINDINGS.md`. If a
wave slips, we ship the last scored stack.

## 6. Risks

- **Cap is 8 GB, not 8.9:** option A still fits (~7.6 GB); option C is off anyway.
- **Teacher data quality:** spot-check 20 items per type before training on them. Drop items
  whose key the teacher gets wrong on a second pass.
- **Eval leakage:** `gen_synthetic.py` already drops items close to eval questions. Don't tune
  RL on the real eval set.
- **Images:** models are text-only. Questions with maps or charts go to S0 tools or get the
  best-guess prior per type; count them separately (`pct_text_only`).
- **One GPU on the VM:** the teacher (~31 GB FP8) and training can't run at the same time; W3 GRPO
  with vLLM generation needs the whole card.

## Open questions

1. Is the cap 8 GB or 8.9 GB, and does it count adapters and the RAG index?
2. Is exam-day hardware GPU or CPU only? (If CPU, llama.cpp GGUF Q4 of base + LoRA.)
3. Do we have an HF token for gated models (Gemma), or do we drop it?
