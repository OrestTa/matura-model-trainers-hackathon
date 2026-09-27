# Matura model trainers: submission candidate

<!-- FINAL-CANDIDATE-SUMMARY: keep matched verification results current. -->
- **Winning model / selected candidate:** Bielik-1.5B-v3.0-Instruct **Q8_0**, with five **F16 LoRA adapters**, a learned question-type classifier and Polish/English OCR. Total unique deployed weights: **1,789,957,828 bytes (1.790 GB)**, including adapters, classifier and OCR. This is our selected Bielik candidate, **not a confirmed competition winner**.
- **Expected performance:** the target is **at least 35% on the complete official history paper**. A defensible final estimate is pending fresh, matched offline inference and Codex Luna grading; we have not yet confirmed that this candidate reaches the target. Fresh verification uses the same pinned OCR runtime as the delivered package.
- **Performance improvement:** **not yet confirmed for this final package**. We are comparing the **Q8_0 baseline + classifier/OCR (1.709 GB)** against the **Q8_0 + five F16 adapters + classifier/OCR (1.790 GB)** using identical inputs and grading. Final total, all five category scores and percentage-point change will replace this pending status when verified.
- **What we trained on:** **225 approved real official examples**, with no year holdouts: 38 closed text, 11 closed image, 127 open text, 44 open image and 5 official essay exemplars. The available approved corpus spans **2012–2026**; it does not contain every task from every downloaded paper. The classifier uses **449 candidate-input examples with weak labels**. No synthetic answer targets or essay rubrics used as essays. The evaluated 2023 paper is represented in training, so its result is **training-set performance, not an unseen-paper estimate**. See [training provenance and coverage](docs/BIELIK_ALL_PAPERS_TRAINING_2026-09-27.md).
- **What we changed:** trained five question-type LoRA specialists for one full pass, sharing a single base; learned routing to closed text, closed image, open text, open image or essay; local OCR only for the two image routes; pinned the offline inference/OCR runtimes and packaged weights with checksums and private recovery copies. Current answer keys and rubrics never enter inference prompts. OCR reads text; it does not provide general visual understanding of maps or pictures. See [submission and recovery instructions](docs/SUBMISSION_BIELIK_ALL_PAPERS.md).

All unique deployed model weights count toward the organizer's **8.8 GB aggregate limit**, including the shared base, every adapter, classifier and OCR weights. The remainder of this README describes the earlier general router; the selected package and linked submission instructions define this candidate.

## Live status dashboard

Public URL: https://orestta.github.io/matura-model-trainers-hackathon/

- Site source: [`dashboard/`](dashboard/)
- Bot-editable data: [`dashboard/status.json`](dashboard/status.json)
- Refresh flow: update `dashboard/status.json`, commit, and push to `main`

**New here? Start with [docs/HOWTO.md](docs/HOWTO.md).**

## Hackathon operations

- Live AWS GPU infrastructure notes: [infra/aws/AWS_INFRA.md](infra/aws/AWS_INFRA.md)
- AWS automation scripts: [infra/aws/README.md](infra/aws/README.md)

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
