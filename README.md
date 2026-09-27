# Matura model trainers: question router

Our entry for the Warsaw Model Trainers hackathon: a small local model (base weights ≤ 8.0 GB on disk, ≤ 8.8 GB with the fine-tuning)
sitting the Polish history matura.

**★ Best-performance candidate: [docs/BEST_SCORE_CANDIDATE.md](docs/BEST_SCORE_CANDIDATE.md)** (harness: main at `007fb17` or later).

**Final submission (27.09.2026):** Gemma 4 12B QAT q4_0 GGUF + mmproj (7.15 GB), no fine-tune. None of
our LoRA fine-tunes beat the base, so the sections below on per-type adapters describe what we tried,
not what we ship. Exact on-stage commands: [docs/EXAM_DAY_BEST_SCORE.md](docs/EXAM_DAY_BEST_SCORE.md);
results for base and every fine-tune: [docs/FINAL_RESULTS.md](docs/FINAL_RESULTS.md); submission form
fields: [docs/SUBMISSION.md](docs/SUBMISSION.md).

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
