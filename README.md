# Matura model trainers: question router

Our entry for the Warsaw Model Trainers hackathon: a small local model (≤ 8 GB)
sitting the Polish history matura.

The harness classifies each exam question by type and sends it to a LoRA adapter
fine-tuned for just that type. All adapters sit on **one shared base model**, so
only the base counts toward the 8 GB limit, and switching adapters per question is
cheap.

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
quantization we'd ship under 8 GB. `scripts/run_baselines.py` serves each one with
vLLM on its own GPU and scores it on the eval set in two modes:

- `raw`: one generic prompt, untouched base model. This is the official baseline.
- `routed`: the router's per-type prompts and answer clean-up, still no adapters.
- `adapters` (later): the full harness, with `--adapters-dir adapters/` holding
  `adapters/<model>/<category>/`.

`scripts/plot_baselines.py` turns the results into `runs/report/index.html` with
three charts: score per model (raw vs routed, with the 35% line), a model × question
type heatmap, and shipped size vs score with the 8 GB limit.

On EC2 (all compute-heavy work runs there, on credits):

```bash
infra/jobs/ec2_baselines.sh                                   # all models, 1x g6e.12xlarge
MODELS=bielik-11b,qwen3-8b infra/jobs/ec2_baselines.sh        # a subset
```

It ships HEAD as a tarball through S3, starts a guarded instance with
`infra/aws/launch.sh`, runs `infra/jobs/baselines.sh` on it over SSM, and downloads
the results and charts to `runs/ec2/<name>/`. The instance powers off when the job
ends. Set `HF_TOKEN` for Gemma (it is gated). Put the eval set at
`data/eval/matura.jsonl` (not committed) and it is uploaded with the job.

Locally against a server you already run:

```bash
python scripts/run_baselines.py --models qwen3-8b --base-url http://localhost:8000/v1
python scripts/plot_baselines.py
```

### Building the eval set from past papers

`scripts/fetch_matura.py` downloads the real CKE history papers (poziom rozszerzony,
formuła 2023, May 2023–2026) and their official answer keys from cke.gov.pl into
`data/raw/cke/`, and parses them into `data/eval/matura.jsonl`. Nothing it downloads
is committed.

```bash
pip install -e .[data]
python scripts/fetch_matura.py                     # 154 items, 4 × 60 points
python scripts/fetch_matura.py --text-only         # drop items that need a picture
python scripts/fetch_matura.py --papers 2025-05 -o data/eval/2025.jsonl
```

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

`scripts/split_by_category.py` turns a Q&A set into one chat-format dataset per
question type, using the same system prompts as inference:

```bash
python scripts/split_by_category.py data/train.jsonl -o data/by_category
# -> data/by_category/{closed_choice,true_false,...}.jsonl, one LoRA each
```

Train one LoRA per file against the same base model and drop them in `adapters/`.
Categories with little data can stay on the base model (`adapter: null`).

## Data and copyright

No exam papers, weights or adapters are committed. `examples/sample_questions.jsonl`
holds our own matura-style questions for testing the classifier. Real past papers
must be fetched with a script from their sources, not checked in.

See [SOURCE.md](SOURCE.md).
