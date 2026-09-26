# Why every Gemma 4 LoRA scores below the base (26 Sep 2026, 22:30 CEST)

Question from Orest: why do the fine-tunes score below the untrained base, and what should change.
Everything below was checked against the code, the training files, the Gemma 4 chat template
(`google/gemma-4-12B-it-qat-q4_0-unquantized/chat_template.jinja`) and the graded answers in
`results/`. Claims that were not measured are marked **(inferred)**.

## Where the points are lost

Claude-graded, per paper, short items (everything except the essay) and the essay separately,
LoRA vs base (g4vr, raw, 2k thinking):

| Adapter | Setting | Paper | Short items LoRA vs base | Essay LoRA vs base |
|---|---|---|---|---|
| A01 (0.1 epoch, LR 1e-4, r16) | raw | 2026 | 35 vs 35 (0) | 0 vs 6 |
| Hm2 (0.3 ep, 1e-4, r16) | routed | 2023 | 28 vs 31 (-3) | 0 vs 10 |
| Hm2 | routed | 2024 | 30 vs 32 (-2) | 0 vs 10 |
| A1 (1 ep, 1e-4, r16) | raw | 2023 | 24 vs 31 (-7) | 0 vs 10 |
| S4m2 (0.15 ep, 2e-4, r32) | routed | 2023 | 23 vs 31 (-8) | 2 vs 10 |
| B4m2 (0.5 ep, 2e-4, r32) | routed | 2023 | 23 vs 31 (-8) | 0 vs 10 |
| Gm3 (0.2 ep, 2e-4, r16, essays x3) | routed | 2023 | 20 vs 31 (-11) | 0 vs 10 |

Two separate effects:

1. **The essay goes to 0 in every run.** That alone costs 6–10 points per paper.
2. **Short items get worse the more the adapter is trained.** The lightest adapter (A01, about 35
   optimizer steps at LR 1e-4) ties the base; every heavier one (more steps, LR 2e-4, rank 32) loses
   2–11 points. So the training signal itself is harmful, not just noisy.

## Ranked causes

### 1. The training format does not match the exam format (thinking channel) — confirmed from the template

`scripts/train_lora.py` passes `prompt` / `completion` to TRL without `enable_thinking`, so the Gemma 4
template renders with thinking off. Rendered strings (checked with jinja2 on the real template):

- Training, prompt + answer: `…<|turn>user\nQUESTION<turn|>\n<|turn>model\nANSWER<turn|>`
- Exam, thinking on (what we ship): `<|turn>system\n<|think|>\n…<|turn>model\n` and the model is expected
  to start with `<|channel>thought\n…`
- Exam, thinking off: `…<|turn>model\n<|channel>thought\n<channel|>` (an empty thought block)

So the adapter learns "right after `<|turn>model\n`, write the final answer immediately". That is the
exact position where, with thinking on, the base model starts its reasoning. The adapter pushes against
thinking. Thinking is worth about 40 points on the four papers (163 on vs 123 off), so even partly
suppressing it explains losses of this size. The training sequence also matches neither exam mode: with
thinking off the exam prompt contains an empty thought block that training never showed.

A second, smaller bug from the same mismatch: the prompt rendered with `add_generation_prompt=True` ends
with `<|channel>thought\n<channel|>`, but the full prompt+answer rendering does not contain it, so the
prompt is not a prefix of the full sequence. TRL masks the loss by the prompt's token count, so the
boundary lands a few tokens into the answer **(inferred from TRL's prompt-completion code; exact effect
depends on the TRL version on Modal/Nebius)**.

Not yet measured: how much shorter the adapters' reasoning actually is. Our answer files do not keep
`reasoning_content`. Check in step 0 of the recipe below.

### 2. The training data is mostly templated Grok data that teaches short, padded, repetitive answers

The main runs (Hm2, B4m2, S4m2, A1) trained on about 5,460 rows; 3,956 (72%) are
`train_data/history_ext_synth.jsonl` (Grok bot, 250 synthetic exams). Measured:

- **Essays are padded with fixed filler sentences.** Across its 246 essays: "Dodatkowo należy podkreślić
  znaczenie krytycznej analizy źródeł." appears 1,041 times, "Argumentacja wymaga faktów, dat i relacji
  przyczynowo-skutkowych." 969 times, "W zakończeniu wracamy do tezy…" 913, "Unikanie ocen ahistorycznych…"
  885, "Kontekst europejski wzbogaca…" 757. That is 4–5 copies of the same sentences per essay. These are
  92% of all training essays (246 of 266 in the main mix).
- **The generator's internal label leaked into 245 essays:** "W rozważaniach warto też uwzględnić kontekst
  porównawczy właściwy dla zestawu syntetycznego nr 0003…". The B4m2 exam essay reproduces it: "…właściwy
  dla zestawu syntetycznego nr 2252". The A1 and Gm3 essays loop on "W rozważaniach warto uwzględnić…",
  the same sentence shape.
- **Essays are barely over the limit:** Grok essays 310–375 words (median 314), of which 100+ words are
  filler. The model learns "about 300 words, then repeat stock sentences".
- **Short answers are much shorter than the base writes and than CKE wants:** Grok short_open median 4 words,
  source_analysis median 12 words ("Uzasadnienie: Uniwersał połaniecki i kosynierzy."). The base writes full
  2–3 sentence justifications, which is what earns the point.
- **Items are easy and duplicated:** the same answer appears up to 30 times ("lokacje miejskie" 30,
  "powstanie kościuszkowskie" 28, "Grunwald 1410" 21); distractors like "wejście do UE" for the Treaty of
  Riga. Closed items are 49% of the Grok rows and train a single letter.

So the adapter learns nothing the base does not already know, and does learn shorter answers, stock
filler and repetition.

### 3. The base essay is already at the 300-word limit, so a small shortening costs the whole essay

Base essays: 312, 370, 320, 376 words **including** the 7-word header "WYPRACOWANIE na temat nr X HISTORIA
Poziom rozszerzony". The A01 essay on 2026 is 304 words with the header, **296 without it**, and got 0 of 15
(the base got 6 on the same paper). A01 tied the base on every short item; its whole loss is this one
essay. Any adapter that makes answers slightly shorter drops the essay below 300 words and loses 6–12 points.
This also means the shipped base has only 5–69 words of margin on each essay.

### 4. Too much update for what the data offers (LR, rank, steps) — supporting cause

Losses on short items grow with the amount of training: 35 steps at 1e-4 → 0; ~100 steps at 1e-4 → -2/-3;
LR 2e-4 or rank 32 → -8; 1 epoch → -7. Hyperparameters are not the root cause (the data and format are),
but with harmful data every extra step makes it worse.

### 5. Factual errors in the essays — a symptom

LoRA essays contain wrong facts the base does not produce: "Bolesław III Wrymouth" (English name),
"Bolesław III Wstydliwy (1101–1138)", "Mieszko III Stary, 1118–1138", "Henryk I Brodaty… seniorem w 1097".
We did not find these strings in the training data. The most likely reason is less reasoning before
writing (cause 1) plus looping (cause 2) **(inferred)**. The Grok data itself has few spelling errors: a
diacritics check found about 300 of 3,956 rows with a stripped word, mostly false positives.

### Checked and ruled out, or low weight

- **bf16 training vs q4_0 serving:** the LoRA is trained on `google/gemma-4-12B-it-qat-q4_0-unquantized`,
  the QAT weights that q4_0 was made from. The mismatch is small by design. A01 at 0.1 epoch writes fluent,
  base-like text, which it would not if the adapter were badly misapplied. Low weight, not measured directly.
- **GGUF conversion / LoRA scale:** `convert_lora_to_gguf.py` keeps `lora_alpha`, and llama-server applies
  scale 1.0 (`openai_compat.py`). No sign of a wrong scale: A01 does not change short-item scores at all.
  Not measured directly; step 0 below checks it.
- **Contamination:** `merge_synth.py` and the 10-gram review removed eval overlaps; no held-out answer
  appears in the adapters' outputs. Not a cause.
- **Eval setting:** the Modal LoRA evals ran `MODE=routed` (our system prompts) while the base ran `raw`,
  so those comparisons change two things at once. A1 and A01 ran raw and still lose, so this is not the
  main cause, but the next comparison must use the same mode.

## Revised recipe (can run before Sunday 11:00)

Goal: an adapter that keeps the base's thinking and essay length, and only improves short items.

0. **Measure first (cheap, L40S or Modal, ~5 prompts):** for the base and for A1, log `reasoning_content`
   length and answer length on 5 short items and 1 essay, thinking on. If A1's reasoning is much shorter,
   cause 1 is confirmed in practice. In the same run, compare PEFT bf16 + adapter against llama.cpp q4_0 +
   GGUF adapter on the same 5 prompts (greedy): the answers should be close; if not, conversion is broken.
1. **Train in the exam format, with thinking.** Build targets by self-distillation: run the base model
   itself (thinking on, 2k cap, the exam harness) several times on each training question, keep only
   answers that the klucz or the Claude judge marks fully correct, and train on the full output
   `<|channel>thought\n…<channel|>ANSWER`. In `train_lora.py`: pass the thought as `reasoning_content` on
   the assistant message and render with `enable_thinking=True` (the template then puts the thought
   channel in the target and `<|think|>` in the system turn, and the prompt is a clean prefix). Because the
   targets are the base model's own outputs, the adapter cannot drift in style or length; it only
   reinforces the answers that scored.
2. **Drop `history_ext_synth.jsonl` completely.** Use only: past papers with klucz (133 rows,
   `/mnt/project-files/data/train/past_papers.jsonl`), `claude_synth.jsonl` without its essays, and
   `open_claude_synth.jsonl`. Deduplicate by answer.
3. **No essays in the adapter.** Route the essay to the base with no adapter (`LORA_ROUTED=1`, 7d705a3).
   The adapter then cannot cost the 10 essay points.
4. **Gentler training:** rank 16, LR 5e-5, 1 epoch over ~500–1,000 filtered rows, loss on the answer only.
   Save a checkpoint every ~50 steps and score each on a dev paper that is not held out (e.g. a 2015–2022
   paper), in the exact exam setting (raw, 2k thinking, THINK_FALLBACK). Stop when the dev score stops rising.
5. **Compare like with like:** same mode (raw), same thinking budget, same grader as the base 163/240.
   Ship only at ≥166 on the four held-out papers.

Separate from training (helps the shipped base too, needs Orest's OK because the config is frozen): the
base essays have 5–69 words of margin over the 300-word minimum. A harness check that counts the essay body
without the header and asks the model to continue when it is under ~350 words would protect 6–12 points
per paper. This is a harness change, not a fine-tune.

Honest expectation: short items tied the base at best in every run, so the realistic gain from step 1 is
a few points on short items. The essay and thinking fixes stop the losses; they do not add points by
themselves.

## Commands for the revised recipe (added 22:50 CEST)

```bash
# 1. base q4_0 GGUF on llama-server (no LoRA), thinking on via --jinja; then build the targets
python scripts/build_selfdistill.py --url http://127.0.0.1:8080 --samples 4 -o data/train/selfdistill.jsonl \
  --input /mnt/project-files/data/train/past_papers.jsonl train_data/claude_synth.jsonl train_data/open_claude_synth.jsonl
#    smoke first: add --limit 20 and check that "kept" is > 0 and that rows carry reasoning_content
# 2. train in the thinking format (asserts the thought channel is in every target)
python scripts/train_lora.py --model gemma4-12b-think --category selfdistill --data-dir data/train \
  --think --lr 5e-5 --epochs 1 --rank 16 --batch 2 --grad-accum 8 --max-len 6144
# 3. convert as in infra/jobs/train.sh (convert_lora_to_gguf.py --outtype f16), run scripts/probe_lora.py think
#    against the new adapter (reasoning length must match the base), then eval raw + 2k thinking +
#    THINK_FALLBACK with essays routed to the base (LORA_ROUTED=1), same grader as the base's 163/240.
```

## Step 0 result (L40S, 22:23 CEST, results/probe-A1/, be9e956)

Same llama-server, same 6 prompts, thinking on; A1 LoRA at scale 0 (= base) vs scale 1:

| Item | Base: reasoning chars / answer words | A1: reasoning chars / answer words |
|---|---|---|
| 2023 z2.1 | 1587 / 44 | 788 / **0** |
| 2023 z2.2 | 1932 / 42 | 1020 / 4 |
| 2023 z4.1 | 1090 / 4 | 685 / 3 |
| 2023 z5.2 | 2625 / 47 | 1662 / 51 |
| 2023 z6 | 2406 / 59 | 2056 / 46 |
| 2023 z26 essay | 3756 / 326 (stop) | 3935 / 2202 (hit 6000 tokens, looping) |

Cause 1 confirmed: the adapter cuts reasoning by 15–50% and empties or truncates short answers. PEFT (bf16) and
GGUF (q4_0) change the output about equally (0.9–1.0 of words changed on both), so the GGUF conversion is not a
cause. The HF LoRA also writes the misspelling "Strzygnięcie:", so the misspellings come from the adapter, not
from q4_0.
