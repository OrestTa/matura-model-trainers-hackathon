# How to use the harness

The path from nothing to a trained, scored entry. All heavy work runs on EC2 with
the AWS credits; your laptop only starts jobs and reads the charts.

## 0. One-time setup

```bash
git clone https://github.com/OrestTa/matura-model-trainers-hackathon && cd matura-model-trainers-hackathon
pip install -e .[dev]              # router, eval, charts (no GPU needed)
pip install awscli
export AWS_PROFILE=matura          # the root key profile from the AWS thread
infra/aws/setup.sh                 # once: GPU quotas, S3 bucket, budgets (see infra/aws/README.md)
```

Optional: `export HF_TOKEN=...` (a Hugging Face read token) so Gemma, which is gated,
can be downloaded. Without it Gemma fails and the other models still run.

## 1. Baseline: how good is each model untouched?

```bash
infra/jobs/ec2_job.sh baselines
```

This starts one g6e.48xlarge (8 GPUs), builds the eval set from the 2023–2026 CKE
papers, scores every model in `configs/models.yaml`, and downloads the report to
`runs/ec2/baselines-<time>/report/index.html`. The machine shuts itself down when
the job ends. Expect roughly an hour, most of it downloading models.

To run a subset: `MODELS=bielik-11b,qwen3-8b infra/jobs/ec2_job.sh baselines`.
Progress while it runs: `aws s3 cp s3://matura-hackathon-<account>/<name>/job.log -`.
Check spend at any time with `infra/aws/status.sh`.

## 2. Reading the charts

- **Score per model:** blue is the untouched model with a plain prompt, which is the
  official baseline you submit. Orange is the same model behind the router's
  per-type prompts. The dashed line is 35%, the bar for the smallest-model prize.
- **Score by question type:** a model × type heatmap. Weak columns show which
  adapters matter most.
- **Size vs score:** shipped size on disk against score. Anything in the grey area
  is over the 8 GB limit.
- The table under the charts adds `pct_text_only`, the score on items that don't
  need a picture. The models can't see pictures, so this is the fairer comparison.

Pick the base model with the best score under 8 GB. Bielik-11B is the expected
winner, but the chart decides.

## 3. Fine-tune: one adapter per question type

```bash
TRAIN_MODELS=bielik-11b infra/jobs/ec2_job.sh train
```

On one instance this:

1. serves a large open teacher model (Qwen3-235B) and generates about 400
   matura-style items per question type, in the exact answer format each adapter
   must produce (`scripts/gen_synthetic.py`). Items too close to an eval question
   are dropped, so the eval stays honest. The data is saved to S3 and reused on the
   next run (`REGEN_DATA=1` regenerates it).
2. splits the items per question type and trains one LoRA adapter per type, one per
   GPU in parallel (`scripts/train_lora.py`).
3. re-scores the model plain, routed, and with adapters, and draws the same charts,
   now with a green "Router + LoRA adapters" bar.

Adapters land in `s3://…/<name>/adapters/<model>/<type>/`. Useful knobs:
`PER_CATEGORY=800` for more data, `EPOCHS=3`, `TRAIN_MODELS=bielik-11b,qwen3-8b` to
train two bases at once, `TYPE=p5.48xlarge` for H100s if the quota came through.

To compare: open both reports. If an adapter makes its question type worse, set that
type's `adapter: null` in `configs/routes.yaml` and it falls back to the base model.

## 4. Changing things

- **Add a model:** add an entry to `configs/models.yaml` (HF id, quantization,
  size on disk) and rerun step 1 with `MODELS=<key>`.
- **Tune a prompt or answer format:** `matura_router/prompts.py`. The same prompts
  are used for training data, so retrain after changing them.
- **Question-type rules:** `matura_router/classifier.py`. Check them with
  `python -m matura_router classify data/eval/matura.jsonl` (it prints the accuracy).
- Run `python -m pytest -q` before pushing. We push straight to main.

## 5. Exam day

The exam runs offline on our own hardware. Serve the chosen base model plus its
adapters with vLLM (or llama.cpp), then put the router in front:

```bash
vllm serve speakleash/Bielik-11B-v2.3-Instruct --served-model-name base \
  --quantization bitsandbytes --enable-lora --max-lora-rank 64 \
  --lora-modules closed_choice=adapters/bielik-11b/closed_choice essay=adapters/bielik-11b/essay ...
python -m matura_router serve --port 8080        # OpenAI-style endpoint for the exam script
python -m matura_router run exam.jsonl -o answers.jsonl   # or answer a file directly
```

Submit results for both the base model (`--modes raw`) and the trained harness,
since the progress prize compares them.
