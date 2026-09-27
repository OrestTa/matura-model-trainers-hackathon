# Matura model trainers: question router

## What we changed to beat the base model

We did not fine-tune the shipped model. Every gain comes from how our harness asks the questions
(`scripts/run_exam.py --mode subtype`, harness at commit `007fb17`). The model file is the same as the base.

| Change | What it does | What it bought (Claude-graded, blind) |
|---|---|---|
| Thinking on, capped at 2,000 tokens | The model reasons before answering. | Held-out 163/240 vs 123/240 with thinking off (+40). This is the model's default, so we count it as part of the base (316a39f, 7e6fe48). |
| Blank-answer retry (`THINK_FALLBACK=1`) | If thinking uses up the budget and the answer is blank, ask once more with thinking off. | Removes the blank answers (6 blanks, 7 points on May 2023 before this). |
| Question type routing (`--mode subtype`, `configs/subtypes.yaml`) | Each question goes to a setting for its type: closed, open text, open picture, essay. | The frame the changes below plug into. |
| Closed questions: 3 of 5 vote | Answer 5 times, keep the majority. | Neutral on held-out (164 vs 165); kept as a guard against one-off slips. |
| Open questions: the exam prompt unchanged | No extra instructions; we tested several and none helped. | Extra prompts, describe-the-picture and best of 3 all stayed within ±2 on 49 practice items (results/judged/matura-judge-claude-dev-*). |
| Essay: plan first, then best of 3 drafts at 350–550 words, printed plan removed | The model writes a plan (16k thinking tokens), then three essays; we keep the best one. | Blind essay batches: 71 vs 56 of 120 (06f9aac), 69 vs 61 of 150 (125605a), side by side 40 vs 35 of 60. No essay can fall under the 300-word minimum (the base wrote 276 and 297 words = 0 points). |

**Result on the Jan 2026 mock (60 points):** plain base with thinking on 32/60, our harness 43/60 (rehearsal, 964c246)
and 38/60 (final run, 5b9f270; 41 after regrading the essay without its printed plan, fixed in 007fb17).
That is **+10 to +18 percentage points**. Most of the gain is in open questions (+6) and questions with pictures (+5).

**Honest limit:** on the four held-out papers (May 2023–2026) the full harness ties the thinking-on base,
163 vs 163 of 240 (efcb3ed). The essay gain shows in blind side-by-side grading, but a paper-by-paper grade
did not confirm it (29 vs 30 of 60). Run-to-run noise is about ±2 per 240 points and ±3 per paper.

## How we measured (protocol)

- **Papers.** Held-out set: the four real CKE papers May 2023, 2024, 2025, 2026 (240 points). They were never used for
  training or for choosing prompts. Dev set: the January 2026 official mock and older practice papers.
  Past answer keys were used only as training data, never in an exam prompt.
- **Grading.** Claude Opus graders, one per paper per answer set, blind to which model wrote the answers.
  They grade against the official CKE key, open the picture crops for picture questions and use the full CKE
  essay criteria. An essay under 300 words scores 0. Check: our graders give the organisers' own deck answers
  45/60 against the deck's 46 (7e6fe48).
- **Essays in the same batch.** Essay grades drift 5–10 points between batches, so the base essay always sits in the
  same blind batch as the candidate.
- **Smoke first.** Every new job type first runs a small end-to-end test. A run with more than 10% blank answers is
  thrown away (`run_exam.py` exits 2).
- **Size.** We count the quantized file on disk. Base ≤ 8.0 GB; base plus fine-tune ≤ 8.8 GB; all models in one
  entry are added up. Ours: 7.15 GB (q4_0 model + picture reader).
- **Score tables** always show five categories (closed, open, essay, text only, with pictures) plus the total.

## Everything we tried, in short

### Gemma 4 12B settings (held-out /240 unless marked)
- Thinking off: 123. Routed prompts with thinking off: 129. Thinking on, 2k: 163 (repeat run 165). (TABLE.md, 7e6fe48)
- Thinking 8k (essays 16k): 81/120 on two papers vs 83 for 2k. Thinking often ran out and left blanks.
- Thinking 4k vs 2k on practice papers: 49 vs 50. No gain.
- 5-vote harness (closed vote, routed open): 164 vs 165 raw; essays −4.
- Per-type harness without fine-tune: 123/180 on three papers vs base 122.
- Picture text via OCR added to the prompt: −6.5 points per 100 on 26 paired items. Gemma reads pictures itself, so OCR is off.
- Open questions best of 3, describe the picture first, or both: within ±2 of plain (pictures +4, text −5 for both).
- Essay variants on 12 dev essays (/150): base 63, plan 68, length guard 56, plan + guard 67. Held-out essays (/120):
  base 56, plan + best of 3 71, retrieval (RAG) + plan 66, plan + best of 3 without word targets 63. Best of 5: 71 vs 69 for best of 3 (noise).

### Fine-tunes of Gemma 4 12B (LoRA; none shipped)
- A1 (1 epoch): 24/60 on May 2023 vs 41. Essays loop, 0/15.
- B4m2: 23/60. Copied the synthetic label "zestawu syntetycznego nr" into exam answers.
- Hm2: 58/120. Gm3 (essay-weighted): 81/180. S4m2: 114/240. Essays 0–2 per paper.
- A01 (0.1 epoch): 131/240. Short items tied the base; its essay was 296 words, so 0.
- Root cause (ac32391, docs/LORA_ROOT_CAUSE.md): the training used thinking off while the exam uses thinking on,
  72% of the data was the Grok bot's synthetic set, and more training hurt short answers more.
- SD1, the fixed recipe (264 rows from real past papers, the model's own thinking as targets, essays left to the base):
  155/240 vs 163 (fc60fe3). Short items within 2 of the base; lost on one 298-word essay.
- SDALL (SD1 plus the held-out papers, an overfit test): stopped at 08:10 CEST for the deadline, never trained (d209713).

### Training data
- Grok bot's synthetic set: 9,284 rows from 250 invented exams. Essays repeat the same filler sentences
  (one sentence 1,041 times), and 245 contain the "synthetic set" label. Dropped.
- Real CKE past papers with official keys (formuła 2015 and 2023), May 2023–2026 always excluded.

### Other models (May 2023 /60 unless marked)
- Gemma-3-27B via API: 35 (too big to ship). Bielik-4.5B FP8 with OCR: 24. Bielik-11B NF4: 12 (a third of answers ran on past the answer).
  Qwen2.5-7B AWQ: 11 (18.3%). Qwen2.5-3B: 11. Qwen2.5-1.5B: 4. Qwen2.5-0.5B: 3. Qwen3-4B Q3: 22.1% of held-out (no picture reading).
- Bielik-11B domain pretraining and the Grok bot's Bielik-11B fine-tune: no graded result before the freeze.

### Smallest model and biggest improvement tracks (Jan 2026 mock /60, 9bc74e5, cc1beca)
- Bielik-1.5B: bare 9; our harness with OCR 9; without OCR 8; per-type 6; our adapters 8; Codex adapters 6, and 5 when trained on this mock.
  The essay scored 0 in every version (length guard, anti-repetition, written in parts). The model lacks the facts:
  it calls Poniatowski a Vasa king. Best improvement 0, dropped.
- Bielik-4.5B: 13 plain, 11–12 with our harness. Under the 35% bar (21/60), dropped.
- Gemma 4 E4B (4.2–5.2 GB) and a smaller 12B quantization (Q3, 5.87 GB): never run before the freeze.
- So one Gemma 4 12B project (7.15 GB) enters all three categories. Tables: [docs/TRACKS_SMALL_AND_IMPROVEMENT.md](docs/TRACKS_SMALL_AND_IMPROVEMENT.md).

## Our final entry (all three categories), in short

- **Categories:** one project, the same Gemma 4 12B file, enters **Best exam score**, **Smallest model passing 35%**
  (7.15 GB; no smaller model we tried reached 35%) and **Biggest improvement** (base = the same file with the plain
  exam prompt and thinking on: 32/60 on the Jan 2026 mock vs 38–43/60 with our harness, +10 to +18 pp). Bielik-1.5B
  (best 9/60) and Bielik-4.5B (best 13/60) were dropped. Tables: [docs/TRACKS_SMALL_AND_IMPROVEMENT.md](docs/TRACKS_SMALL_AND_IMPROVEMENT.md).

- **Winning model:** Gemma 4 12B QAT, `google/gemma-4-12B-it-qat-q4_0-gguf` (q4_0 GGUF + mmproj vision
  projector), **7.15 GB**, **no fine-tune**. Harness: this repo at `007fb17` or later. Exact copy of the files:
  https://huggingface.co/orestta/matura-gemma4-12b-best-score (private; the same files as the Google repo above). Details: [docs/BEST_SCORE_CANDIDATE.md](docs/BEST_SCORE_CANDIDATE.md).
- **Expected performance:** about 163/240 (**67.9%**) on the four held-out papers May 2023–2026, and 38–43/60
  on the Jan 2026 practice paper (two runs of the same setup). Graded by Claude against the official CKE key, with pictures viewed.
- **Improvement over the plain base model:** the held-out total is the **same** (163 vs 163). The essays are better when graded side by
  side (40 vs 35 of 60, and 71 vs 56 of 120), and essays can no longer score 0 for being under 300 words.
  On the Jan 2026 practice paper the dress rehearsal scored 43/60 vs 37 for the plain base.
- **What we trained on:** the shipped model is not fine-tuned. Our fine-tunes (LoRA) used real CKE past papers and
  their official keys (formuła 2015 and 2023, May 2023–2026 always excluded). The best one, SD1 (264 rows), scored
  155/240, below the base, so none is shipped. Earlier synthetic data was dropped.
- **What we changed vs the base model:** closed questions take a 3-of-5 vote. Essays write a plan first
  (16k thinking tokens), then 3 drafts of 350–550 words, keep the best and remove the printed plan. A blank answer
  is asked once more with thinking off. Open questions get the exam prompt unchanged.
- All scores, including every rejected fine-tune: [docs/FINAL_RESULTS.md](docs/FINAL_RESULTS.md). On-stage commands:
  [docs/EXAM_DAY_BEST_SCORE.md](docs/EXAM_DAY_BEST_SCORE.md). Form fields: [docs/SUBMISSION.md](docs/SUBMISSION.md).

The rest of this README describes the per-type LoRA router we built and tried; it is not what we ship.

Our entry for the Warsaw Model Trainers hackathon: a small local model (base weights ≤ 8.0 GB on disk, ≤ 8.8 GB with the fine-tuning)
sitting the Polish history matura.

The harness classifies each exam question by type and sends it to a LoRA adapter
fine-tuned for just that type. All adapters sit on **one shared base model**, so
the base must fit 8.0 GB and base plus adapters 8.8 GB, and switching adapters per
question is cheap.

Made during the Warsaw Model Trainers hackathon, Kolektyw3, 25–27.09.2026 (see
[SOURCE.md](SOURCE.md)). Data and model sources: [SOURCES.md](SOURCES.md). Nothing
copyrighted is committed; every dataset is fetched by a script.

## Reproduce

Tested on Linux with one 48 GB GPU (NVIDIA L40S), Python 3.11, CUDA 12+.

```bash
git clone https://github.com/OrestTa/matura-model-trainers-hackathon && cd matura-model-trainers-hackathon
python -m venv .venv && . .venv/bin/activate
pip install -e .[dev,data,peft,train,eval] vllm==0.27.1    # vLLM pin: bitsandbytes 4-bit checkpoints
python -m pytest -q                              # router, scoring, fetch, RAG, training tests

# 1. Eval set from the official CKE papers (not committed)
python scripts/fetch_matura.py                   # data/eval/matura.jsonl, May 2023-2026

# 2. Pre-quantize the base model under the 8.0 GB base limit
python scripts/quantize_checkpoint.py bielik-11b     # -> work/checkpoints/bielik-11b

# 3. Baseline: untouched base model (the "base" result)
python scripts/run_baselines.py --models bielik-11b --modes raw

# 4. Train: synthetic data (open teacher, served locally) + past papers -> one LoRA adapter per question type
python scripts/fetch_matura.py --papers all -o data/eval/matura_all.jsonl
python scripts/build_train_from_papers.py      # data/train/past_papers.jsonl, headline papers excluded
TRAIN_MODELS=bielik-11b bash infra/jobs/train.sh

# 5. Trained model (the "trained" result), then the exact on-stage harness
python scripts/run_baselines.py --models bielik-11b --modes raw,routed,adapters --adapters-dir work/adapters
bash scripts/serve_exam.sh bielik-11b            # vLLM + adapters + router on :8080, fully offline
```

Run `python <script> --help` for every option; [docs/HOWTO.md](docs/HOWTO.md) walks
through each step. The optional RAG knowledge base is built with `scripts/build_kb.py`
(or the Wikipedia index from `scripts/corpus/plwiki.py`) and its path is set in
`configs/routes.yaml` (`rag.path`).

### On stage

`scripts/serve_exam.sh` is the exact harness we run for the exam. It refuses a checkpoint
over the size limit, sets every Hugging Face and vLLM switch to offline, serves the
4-bit base model with its adapters, and puts the router in front as an OpenAI-style
endpoint on `:8080`. No closed API or web access is used while answering.

### Results

Base (untouched) and trained scores are committed under [`results/`](results/) as they
come in; job progress is in [docs/STATUS.md](docs/STATUS.md) and findings in
[docs/FINDINGS.md](docs/FINDINGS.md).

## How it works

```
question ──► classifier ──► route (adapter + prompt + decoding) ──► base model + LoRA ──► post-process ──► answer
                 │                                                        ▲
                 └── unsure? ──────────── base model, no adapter ─────────┘
```

## Question types

| Category | Matura task | Adapter output |
|---|---|---|
| `closed_choice` | zaznacz / wybierz A–D | letters, e.g. `B` or `A, C` |
| `true_false` | oceń prawdziwość (P/F) | `1. P` / `2. F` … |
| `matching` | przyporządkuj / dobierz | `1 – B` … |
| `chronology` | uporządkuj chronologicznie | `C, A, D, B` |
| `source_analysis` | na podstawie tekstu / mapy / tabeli | short grounded answer |
| `short_open` | podaj / wyjaśnij / wymień | 1–2 sentences |
| `essay` | wypracowanie | full essay |
| `general` | classifier unsure | base model, no adapter |

The classifier (`matura_router/classifier.py`) is rule-based: CKE words each task
type very consistently, so weighted Polish keyword patterns get it right instantly
without a GPU. A closed-format instruction (P/F, A–D, ordering) wins over "has a
source", since those tasks are answered in the closed format. When the top score is
low or too close to the runner-up, the question goes to the base model. Setting
`classifier.llm_fallback: true` asks the base model for a label first.

A route whose adapter isn't loaded yet falls back to the base model, and so does a
request whose adapter errors. The harness therefore runs today with no adapters,
and each adapter improves its category once it's trained.

## Setup

```bash
pip install -e .[dev]        # router only (stdlib + pyyaml)
pip install -e .[peft]       # optional: in-process transformers/PEFT backend
python -m pytest -q
```

## Running

Check routing without a model:

```bash
python -m matura_router classify examples/sample_questions.jsonl
```

Serve the base model with every adapter, then point the router at it
(`configs/routes.yaml`):

```bash
# vLLM: each adapter becomes its own model name
vllm serve <base-model> --served-model-name base --enable-lora --max-loras 8 \
  --lora-modules closed_choice=adapters/closed_choice true_false=adapters/true_false \
                 matching=adapters/matching chronology=adapters/chronology \
                 source_analysis=adapters/source_analysis short_open=adapters/short_open \
                 essay=adapters/essay

# or llama.cpp: set adapter_mode: llamacpp and llamacpp_lora_ids in routes.yaml
llama-server -m base.gguf --lora-init-without-apply --lora adapters/closed_choice.gguf ...
```

Answer a file of questions, or a single one:

```bash
python -m matura_router run exam.jsonl -o answers.jsonl
python -m matura_router ask "Uporządkuj chronologicznie: A. hołd pruski B. chrzest Polski"
```

Input rows are `{"id", "question", "context"?}`; each output row carries the answer
plus `category`, `adapter`, `confidence` and latency.

If the exam script expects an OpenAI-style endpoint, put the router in front of the
model server:

```bash
python -m matura_router serve --port 8080
# POST http://localhost:8080/v1/chat/completions with model "router" (auto)
# or a category name such as "essay" to force a route
```

## Baselines per model

`configs/models.yaml` lists the candidate base models (Bielik-11B, Qwen3-8B,
Gemma-3-12B, plus small ones for the "Mały, ale wariat" category), each with the
quantization we'd ship under the 8.0 GB base limit (Gemma-3-12B doesn't fit). `scripts/run_baselines.py` serves each one with
vLLM on its own GPU and scores it on the eval set in two modes:

- `raw`: one generic prompt, untouched base model. This is the official baseline.
- `routed`: the router's per-type prompts and answer clean-up, still no adapters.
- `adapters` (later): the full harness, with `--adapters-dir adapters/` holding
  `adapters/<model>/<category>/`.

`scripts/plot_baselines.py` turns the results into `runs/report/index.html` with
three charts: score per model (raw vs routed, with the 35% line), a model × question
type heatmap, and shipped size vs score with the 8.0 GB base limit.

On EC2 (used early in the event; the AWS account was later suspended, so the final runs used a Labqoat L40S VM with the same `infra/jobs/*.sh` scripts):

```bash
infra/jobs/ec2_job.sh baselines                               # all models, 1x g6e.48xlarge
MODELS=bielik-11b,qwen3-8b infra/jobs/ec2_job.sh baselines    # a subset
```

It ships HEAD as a tarball through S3, starts a guarded instance with
`infra/aws/launch.sh`, runs `infra/jobs/baselines.sh` on it over SSM, and downloads
the results and charts to `runs/ec2/<name>/`. The instance powers off when the job
ends. Six GPUs run candidate models; the last two serve an open judge model
(`JUDGE_HF`, default Qwen/Qwen3-32B) that grades open answers against the CKE key and
rubric, since most matura items are open. `JUDGE_HF=` turns the judge off. Each
summary reports the full score and `pct_text_only`, the score on items that don't
depend on a picture or map, which text-only models can't see. If no eval set is
given, the instance builds it with `scripts/fetch_matura.py`. Set `HF_TOKEN` for Gemma (it is gated). Put the eval set at
`data/eval/matura.jsonl` (not committed) and it is uploaded with the job.

Locally against a server you already run:

```bash
python scripts/run_baselines.py --models qwen3-8b --base-url http://localhost:8000/v1
python scripts/plot_baselines.py
```

### Building the eval set from past papers

`scripts/fetch_matura.py` downloads every history paper (poziom rozszerzony) CKE publishes with an
answer key, into `data/raw/cke/`, and parses them into eval JSONL. Nothing it downloads is committed.
Sets: `headline` (default: formuła 2023, May 2023–2026, 154 items → `data/eval/matura.jsonl`),
`formula2023` (plus the 2022 demo paper and the January 2026 mock), `formula2015` (the previous
format, May 2015–2024) and `all` (16 papers, 512 distinct items, 789 points → `data/eval/matura_all.jsonl`; old-format items
that repeat a current-format task are dropped unless `--keep-duplicates`).
Per-paper coverage is in [results/eval_set_papers.md](results/eval_set_papers.md).

```bash
pip install -e .[data]
python scripts/fetch_matura.py                     # headline set
python scripts/fetch_matura.py --papers all        # every paper
python scripts/fetch_matura.py --text-only         # drop items that need a picture
python scripts/fetch_matura.py --papers 2025-05 -o data/eval/2025.jsonl
python scripts/run_baselines.py --eval data/eval/matura_all.jsonl ...   # score the full set
```

Rows carry `paper`, `year`, `formula` (2023 or 2015) and `kind` (main, demo, mock), so the
summary can be split per paper or per format.

The papers outside the headline set double as training data with official answers:
`python scripts/build_train_from_papers.py` writes `data/train/past_papers.jsonl` (133 items) in
`split_by_category.py`'s input format, skipping essays, items that need a picture and anything that
overlaps the headline eval. `infra/jobs/train.sh` adds it to the synthetic data when present
(`PAST_PAPERS=0` turns that off), and the Forgehand, Modal and EC2 runners upload it.
Each item keeps its shared sources in `context` and the instruction in `question`;
pictures (maps, photos, posters, plans) become a `[ilustracja – …]` placeholder.
`needs_image: true` marks items that can't be answered without the picture (85 of 154),
so text-only models can be scored on both the full paper and the text-only subset.
Closed items get a key in the scorer's format; short open answers get
`gold_keywords`; the rest carry the official model answer as `gold` for the judge,
plus CKE's `rubric` and, for "Rozstrzygnij … uzasadnij" items, the bare `decision`.

### Eval set format

One JSONL row per exam item: `id`, `question`, optional `context` (source text),
`category` (gold question type), `points` (default 1), and either `gold` (the key:
`"B"`, `"P, F, P"`, `"1 – B, 2 – D"`, `"C, A, D, B"`, or a model answer for open
items) or `gold_keywords` (groups of alternatives an open answer must mention). Closed
items get partial credit per statement or pair. Open items without keywords are
scored by an LLM judge when `--judge-url` is given, otherwise reported as unscored.

## Training the adapters

The whole loop runs as one EC2 job: `infra/jobs/ec2_job.sh train`. See
[docs/HOWTO.md](docs/HOWTO.md) for the step-by-step version.

1. `scripts/gen_synthetic.py` asks a big open teacher model (served with vLLM on
   the instance; any OpenAI-compatible API works) for matura-style items per question
   type, in the exact answer format the router expects. Items too close to an eval
   question are dropped.
2. `scripts/split_by_category.py` turns them into one chat dataset per question
   type, with the same system prompts as inference.
3. `scripts/train_lora.py --model <key> --category <type>` trains one LoRA adapter
   (TRL + PEFT, bf16) into `adapters/<model>/<type>/`. Types with too few examples
   are skipped and stay on the base model.
4. `run_baselines.py --modes raw,routed,adapters --adapters-dir adapters` re-scores,
   so the charts show the gain from routing and from each adapter.

## Data and copyright

No exam papers, weights or adapters are committed. `examples/sample_questions.jsonl`
holds our own matura-style questions for testing the classifier. Real past papers
must be fetched with a script from their sources, not checked in.

See [SOURCE.md](SOURCE.md).
