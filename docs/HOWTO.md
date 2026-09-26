# How to use the harness

The path from nothing to a trained, scored entry. Heavy work runs on a rented GPU
box (Nebius, Modal, Labqoat, anything Linux with NVIDIA GPUs); your laptop only
reads the charts.

> 2026-09-26: the AWS account was suspended, so `infra/jobs/ec2_job.sh` is out of
> use. The jobs below run directly on whatever GPU machine we get.

## 0. On the GPU box

```bash
git clone https://github.com/OrestTa/matura-model-trainers-hackathon && cd matura-model-trainers-hackathon
export HF_TOKEN=...   # optional: a Hugging Face read token, needed only for Gemma (gated)
```

The jobs install vLLM and the training stack into `work/venv` on first run (or use
them if the box already has them), and write everything to `work/out/`.

## 1. Baseline: how good is each model untouched?

```bash
bash infra/jobs/baselines.sh
```

It builds the eval set from the 2023–2026 CKE papers, scores every model in
`configs/models.yaml` (one per GPU, several at once), and writes the report to
`work/out/report/index.html`. With 4+ GPUs the last two serve a judge model that
grades open answers; with fewer, only the ~60 auto-scorable items count.

- A subset: `MODELS=bielik-11b,qwen3-8b bash infra/jobs/baselines.sh`
- No judge: `JUDGE_HF= bash infra/jobs/baselines.sh`
- Copy the report home: `scp -r box:matura-model-trainers-hackathon/work/out/report .`

Commit the numbers you want to keep (`work/out/baselines/*/*/summary.json` and the
CSV) under `results/` and add a line to `docs/FINDINGS.md`.

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
TRAIN_MODELS=bielik-11b bash infra/jobs/train.sh
```

This:

1. serves a large open teacher model (Qwen3-235B on 8 GPUs, Qwen3-30B on fewer) and
   generates about 400 matura-style items per question type, in the exact answer
   format each adapter must produce (`scripts/gen_synthetic.py`). Items too close to
   an eval question are dropped, so the eval stays honest. The data is kept in
   `data/train/synthetic.jsonl` and reused next time (`REGEN_DATA=1` regenerates).
   Any OpenAI-compatible API can be the teacher instead: run `gen_synthetic.py
   --base-url ... --model ...` yourself first.
2. splits the items per question type and trains one LoRA adapter per type, one per
   GPU in parallel (`scripts/train_lora.py`), into `work/adapters/<model>/<type>/`.
3. re-scores the model plain, routed, and with adapters, and draws the same charts,
   now with a green "Router + LoRA adapters" bar.

Useful knobs: `PER_CATEGORY=800` for more data, `EPOCHS=3`,
`TRAIN_MODELS=bielik-11b,qwen3-8b` to train two bases at once.

If an adapter makes its question type worse, set that type's `adapter: null` in
`configs/routes.yaml` and it falls back to the base model.

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
