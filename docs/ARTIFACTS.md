# Artifacts: where the models and data live, and how to get them back

Written 2026-09-26 (evening, CEST) for recovery if a VM, the Forgehand box or a session dies.
One entry per artifact: location, size, fetch command, regenerate command. Nothing here is a
secret: credentials are named by their env var only. Anything not measured or read from the
code is marked **(inferred)**.

**Never commit** the CKE papers, their parsed eval sets or their page images (`data/`, `*.gguf`,
`*.safetensors`, `adapters/`, `models/` and `work/` are gitignored). This file only documents them.

## Storage locations at a glance

| Store | Name / how to address it | Credentials (env vars) |
|---|---|---|
| Hugging Face Hub | public `google/...` repos; private `orestta/...` repos | `HF_TOKEN` (needs read access to the `orestta` private repos) |
| Nebius Object Storage (S3 API) | `s3://$NB_BUCKET/` (currently `matura-jobs-claude`); `infra/nebius/nb_job.py` reads it from `NEBIUS_BUCKET` (default `matura-jobs-<project suffix>`) and passes it to jobs as `NB_BUCKET` | `AWS_ENDPOINT_URL` = Nebius storage endpoint for the region (`https://storage.eu-north1.nebius.cloud`, `NEBIUS_REGION`), S3 key made by `nb_job.py setup` into `~/.nebius/s3.env`; `NEBIUS_SERVICE_ACCOUNT_ID`, `NEBIUS_PUBLIC_KEY_ID`, `NEBIUS_PRIVATE_KEY_B64`, `NEBIUS_PROJECT_ID` |
| AWS S3 (EC2 path, `infra/aws`, `infra/jobs/ec2_job.sh`) | `s3://$BUCKET/<job>/` and `s3://$BUCKET/data/...`; `BUCKET` = `${PROJECT_TAG}-<account id>` (`infra/aws/common.sh bucket_name`) | AWS credentials in env |
| Modal volumes | `matura-jobs` (`infra/modal/modal_job.py`, `subtype_modal.py`, `hf_push.py`): `out/<job>/`, and `claude-matura` (`infra/modal/claude_gemma.py`): `eval/`, `out/<job>/`. Older workshop volume `model-training-workshop` (`harness/modal_lora_train.py`, prefix `matura/`) | `~/.modal.toml` (never committed); Modal secret `claude-hf` holds `HF_TOKEN` for `hf_push.py` |
| Project files | `/mnt/project-files/` (shared across the project's sessions): `data/`, `runs/`, `subtype/`, `uploads/` | none |
| Forgehand L40S box | local disk `/scratch/` (`/scratch/work/adapters-*`, `/scratch/out/<job>/`, `/scratch/hf`) and `/workspace/work/` (older jobs) | SSH (flaky; see `infra/forgehand/`) |
| Git repo | this repo, `main` | GitHub |

Nebius job layout (every job, `infra/nebius/nb_job.py`): code tarball `s3://$NB_BUCKET/src/<job>.tgz`;
outputs synced every few minutes to `s3://$NB_BUCKET/out/<job>/`:

- `out/<job>/adapters/gemma4-12b/all/{adapter.gguf, adapter_model.safetensors, adapter_config.json, train_meta.json}`
  (single-adapter runs, `SINGLE_ADAPTER=1`; per-type runs have one folder per question type instead of `all/`)
- `out/<job>/<paper>/answers.json` (eval answers), `out/<job>/job.log`, `out/<job>/serve_exam.log`

Common fetch commands (with the env vars above set):

```bash
python infra/nebius/nb_job.py fetch <job>                         # -> runs/nebius/<job>/
aws s3 sync s3://$NB_BUCKET/out/<job>/adapters/ adapters/<job>/ --endpoint-url "$AWS_ENDPOINT_URL"
modal volume get matura-jobs out/<job> runs/modal/
huggingface-cli download <repo_id> --local-dir <dir>              # private repos need HF_TOKEN
```

## 1. Base models (public, Hugging Face)

| Artifact | Location | Size | Fetch | Regenerate |
|---|---|---|---|---|
| Gemma 4 12B QAT q4_0 GGUF (served model, `gemma4-12b*` in `configs/models.yaml`) | HF `google/gemma-4-12B-it-qat-q4_0-gguf`, file `gemma-4-12b-it-qat-q4_0.gguf` | 6.98 GB (6,975,879,296 B, HF API) | `huggingface-cli download google/gemma-4-12B-it-qat-q4_0-gguf gemma-4-12b-it-qat-q4_0.gguf mmproj-gemma-4-12b-it-qat-q4_0.gguf --local-dir models/gemma4` (gated: `HF_TOKEN`); the job scripts do the same via `hf_hub_download` (`scripts/serve_exam.sh`, `scripts/run_baselines.py`) into `$HF_HOME` | Google's release; not rebuilt by us |
| Gemma 4 vision projector | same repo, `mmproj-gemma-4-12b-it-qat-q4_0.gguf` | 0.18 GB (175,115,616 B) | as above | as above |
| Total shipped base | GGUF + mmproj | **7.16 GB** (under the 8.0 GB base limit) | | |
| Training base (LoRA is trained on these bf16 QAT weights, then converted to a GGUF LoRA) | HF `google/gemma-4-12B-it-qat-q4_0-unquantized` (`train_hf_id`) | 23.95 GB (sum of repo files, HF API) | downloaded automatically by `scripts/train_lora.py` into `$HF_HOME`; manual: `huggingface-cli download google/gemma-4-12B-it-qat-q4_0-unquantized` | Google's release |

Other models in `configs/models.yaml` (Bielik, Qwen) are fetched by `hf_id` the same way. The Bielik DAPT
merges (`/workspace/work/models/bielik-11b-dapt`, `bielik-11b-base-dapt`) live only on the Forgehand box
(`infra/jobs/dapt.sh`, `scripts/merge_dapt.py`) and are not backed up **(inferred from the paths in models.yaml)**.

## 2. LoRA adapters (Gemma 4 12B)

HF backup: every adapter goes to a private repo `orestta/matura-gemma4-12b-lora-<name>`. Three ways it gets there:

- `infra/jobs/train.sh` (since d38c5d5) uploads after training when `HF_TOKEN` is set. Env: `HF_BACKUP=0` turns it
  off, `HF_BACKUP_OWNER` (default `orestta`), `ADAPTER_NAME` (default the job `NAME`); repo =
  `<HF_BACKUP_OWNER>/matura-<model>-lora-<ADAPTER_NAME>`. A failed upload never fails the job.
- `modal run infra/modal/hf_push.py --jobs <job>,<job>` uploads `matura-jobs:out/<job>/adapters/` to
  `orestta/matura-gemma4-12b-lora-<job minus "gemma-lora-">` (token from the Modal secret `claude-hf`).
- A watcher session uploads Nebius adapters as they land in the bucket.

**Backup status:** only **A01** is confirmed on HF. Every other HF repo below is **backup in progress** (pending).

Adapter size: not measured; a rank-16/32 LoRA on the text projections is roughly 0.1-0.3 GB per format
(safetensors and f16 GGUF each) **(inferred)**. Base + adapter must stay under 8.8 GB.

Common regenerate recipe (every Gemma LoRA below is a variant of it; exact env per job is in its
`docs/STATUS.md` row):

```bash
NAME=<job> TRAIN_MODELS=gemma4-12b TEACHER_HF=none JUDGE_HF= SINGLE_ADAPTER=1 SKIP_SCORE=1 \
  RANK=16 LR=1e-4 EPOCHS=<ep> \
  EXTRA_TRAIN="train_data/history_ext_synth.jsonl train_data/claude_synth.jsonl" \
  bash infra/jobs/train.sh
# data/train/past_papers.jsonl is added when present (PAST_PAPERS=1, default)
# Nebius: python infra/nebius/nb_job.py launch --job train --platform gpu-h100-sxm --preset 1gpu-16vcpu-200gb --env "<the env above>"
# Modal:  modal run --detach infra/modal/modal_job.py --job train --gpu H100 --env "<the env above>"
```

| Name | Where trained | Primary copy | HF backup | Recipe |
|---|---|---|---|---|
| **A01** | Forgehand L40S | `/scratch/work/adapters-A01` (box); copy at `s3://$NB_BUCKET/out/loraA01/adapters/gemma4-12b/all/adapter.gguf` | `orestta/matura-gemma4-12b-lora-A01` **confirmed** | `infra/forgehand/local/chain_v4.sh`: `train gemma-lora-A01 SKIP_SCORE=1 RANK=16 LR=1e-4 EPOCHS=0.1`, `SINGLE_ADAPTER=1 TEACHER_HF=none`, `EXTRA_TRAIN=history_ext_synth + claude_synth` (0.1 epoch = 19 steps) |
| **A1** | Forgehand L40S | `/scratch/work/adapters-A1`, run log `/scratch/out/gemma-lora-A1/` | `orestta/matura-gemma4-12b-lora-A1` backup in progress (uploading) | `infra/forgehand/local/chain_v5.sh`: same as A01 with `EPOCHS=1` |
| **S1d, S2d, S3d, S4d** | Nebius H100 | `s3://$NB_BUCKET/out/<job>/adapters/gemma4-12b/all/`; job name `gemma-S1d` ... `gemma-S4d` **(inferred from the earlier `gemma-S1c` ... `gemma-S4c` rows)** | `orestta/matura-gemma4-12b-lora-S1d` ... `-S4d` backup in progress | `train.sh` sweep over rank/LR/epochs/data mix; exact env in their `docs/STATUS.md` rows (the `c` round was r16 lr1e-4 ep0.15, 60 min cap) |
| **F4** | Nebius H100 | `s3://$NB_BUCKET/out/gemma-lora-F4/adapters/gemma4-12b/` **(inferred name, from `gemma-lora-F3`)** | `orestta/matura-gemma4-12b-lora-F4` backup in progress | F3 was r16 lr2e-4 ep0.2; F4 env in its STATUS row |
| **G2** | Nebius H100 | `s3://$NB_BUCKET/out/gemma-lora-G2/adapters/gemma4-12b/` **(inferred name, from `gemma-lora-G`)** | `orestta/matura-gemma4-12b-lora-G2` backup in progress | G was essay-weighted r16 lr2e-4 ep0.2 (`essay_claude_synth.jsonl` listed 3x in `EXTRA_TRAIN`) |
| **B4m** | Modal H100 | `modal volume matura-jobs:out/gemma-lora-B4m` (failed, RemoteError); relaunched as `gemma-lora-B4m2` | `orestta/matura-gemma4-12b-lora-B4m2` via `hf_push.py`, backup in progress | `SINGLE_ADAPTER=1 RANK=32 LR=2e-4 EPOCHS=0.5`, `EXTRA_TRAIN=history_ext_synth + claude_synth + open_claude_synth` |
| **E2m** | Modal H100 | `matura-jobs:out/gemma-lora-E2m` (failed, RemoteError) | backup in progress (only if a relaunch finishes) | `SINGLE_ADAPTER=0` (one adapter per question type) `RANK=16 LR=2e-4 EPOCHS=0.5`, same three files |
| **S4m** | Modal H100 | `matura-jobs:out/gemma-lora-S4m` (failed, RemoteError) | backup in progress (only if a relaunch finishes) | `SINGLE_ADAPTER=1 RANK=32 LR=2e-4 EPOCHS=0.15 PAST_PAPERS=0`, same three files |
| **Gm** | Modal H100 | `matura-jobs:out/gemma-lora-Gm` (failed, RemoteError); relaunched as `gemma-lora-Gm2` | `orestta/matura-gemma4-12b-lora-Gm2` via `hf_push.py`, backup in progress | `SINGLE_ADAPTER=1 RANK=16 LR=2e-4 EPOCHS=0.2`, the three files + `essay_claude_synth.jsonl` 3x |
| (Hm2) | Modal H100 | `matura-jobs:out/gemma-lora-Hm2` | backup in progress | `SINGLE_ADAPTER=1 RANK=16 LR=1e-4 EPOCHS=0.3`, the three files |
| **V1** (picture LoRA) | Forgehand L40S (training) | `/scratch/...` on the box **(inferred)** | `orestta/matura-gemma4-12b-lora-V1` backup in progress | `python scripts/train_lora.py --model gemma4-12b --vision --data-dir <unpacked vision_pack> --category vision --rank 16 --lr 1e-4` (data: section 3; the vision tower stays frozen, LoRA on the text layers). Convert to GGUF with llama.cpp's `convert_lora_to_gguf.py --base-model-id google/gemma-4-12B-it-qat-q4_0-unquantized --outtype f16` as `train.sh` does. Rank/LR/epochs **(inferred; check the V1 STATUS row)** |

Earlier adapters (`gemma-lora-B`/`C`/`D`/`E`/`F`, `-B3`, `-C3`, `-C4`, `-B4`, `-D2`, `-E2`, `-F2`, `-F3`, `-G`,
`gemma-S1c`..`S4c`, smoke runs) are under `s3://$NB_BUCKET/out/<job>/` as listed in `docs/STATUS.md`; none are backed up to HF.
Legacy Qwen2.5 3B/1.5B workshop LoRAs: Modal volume `model-training-workshop:matura/lora-3b-v3`, `matura/lora-1.5b-v1` (`notes/MODAL_TRAIN.md`).

## 3. Training data

| Artifact | Location | Size | Fetch | Regenerate |
|---|---|---|---|---|
| `train_data/claude_synth.jsonl` (952 items, Claude-written) | repo | 0.7 MB | `git pull` | parts merged with `python scripts/merge_synth.py parts/*.jsonl --eval data/eval/matura.jsonl -o train_data/claude_synth.jsonl` (see `train_data/README.md`); topics from `scripts/gen_synthetic.py`. Also copied to `/mnt/project-files/data/train/claude_synth.jsonl` (953 lines, earlier version) |
| `train_data/open_claude_synth.jsonl` (419 open-answer items) | repo | 0.35 MB | `git pull` | `scripts/merge_synth.py` over `/mnt/project-files/data/train/open_synth/checked_part*.jsonl` + `part4-6.jsonl` **(inferred)** |
| `train_data/essay_claude_synth.jsonl` (270 essays) | repo | 1.2 MB | `git pull` | `scripts/merge_synth.py` over `/mnt/project-files/data/train/essay_synth/{part0-5,w0-w9}.jsonl` **(inferred)** |
| `train_data/history_ext_synth.jsonl` (3,956 items) | repo | 2.7 MB | `git pull` | from the Grok synth set below, converted and run through `scripts/merge_synth.py --eval data/eval/matura_img.jsonl` (details in `train_data/README.md`) |
| Grok synthetic set (9,284 rows, 250 synthetic formuła-2023 exams; data of Nebius job `me2k8`) | `s3://matura-nf4-sft-20260926/train.jsonl` (another team member's bucket; which S3 provider is not recorded in the repo) | not measured | `aws s3 cp s3://matura-nf4-sft-20260926/train.jsonl .` with that bucket's credentials | Grok bot's generator, not in this repo |
| `open_synth/` (Claude open-answer parts) | `/mnt/project-files/data/train/open_synth/` (11 files) | 0.5 MB | copy from project files | Claude sessions (hand-written), merged as above |
| `essay_synth/` (Claude essay parts) | `/mnt/project-files/data/train/essay_synth/` (15 files) | 1.4 MB | copy from project files | Claude sessions, merged as above |
| `past_papers.jsonl` (133 items from non-held-out CKE papers with official keys) | `/mnt/project-files/data/train/past_papers.jsonl`; copy into `data/train/` before a job | 0.2 MB | `cp /mnt/project-files/data/train/past_papers.jsonl data/train/` | `python scripts/fetch_matura.py --papers all` then `python scripts/build_train_from_papers.py` (input `data/eval/matura_all.jsonl`; drops held-out overlaps, picture items, essays). Private HF dataset `orestta/matura-train-private` is planned for it |
| `synthetic.jsonl` (teacher-generated, per type) | `data/train/synthetic.jsonl`; S3 `s3://$BUCKET/data/train/synthetic.jsonl` (EC2 path, `train.sh`) | not measured | `train.sh` pulls it from S3 when present | `python scripts/gen_synthetic.py --base-url http://127.0.0.1:8200/v1 --model teacher --per-category 400 --eval data/eval/matura.jsonl -o data/train/synthetic.jsonl` (teacher Qwen3-235B-A22B FP8 on 8 GPUs, else Qwen3-30B-A3B FP8; `REGEN_DATA=1` in `train.sh`). Recent Gemma runs use `TEACHER_HF=none` and skip it |
| Picture LoRA data `vision.jsonl` (135 image+text rows from non-held-out papers) | `/mnt/project-files/data/train/vision/vision.jsonl` (absolute image paths) | 0.2 MB | copy | `python scripts/build_vision_train.py -o data/train/vision/vision.jsonl` (inputs `data/eval/matura_all.jsonl` with `images/`, excludes `data/eval/matura.jsonl`) |
| Picture LoRA pack `vision_pack.tgz` (`vision.jsonl` with relative paths + `images/`, 199 entries) | `/mnt/project-files/data/train/vision/vision_pack.tgz` (unpacked in `.../vision/pack/`, 14 MB) | 12.9 MB | `tar xzf vision_pack.tgz -C <dir>`; planned private HF dataset `orestta/matura-train-private` | rebuild `vision.jsonl` as above, then tar it with its page images (CKE images: never commit) |
| Per-type split | `data/by_category/*.jsonl` (per job) | small | none | `scripts/split_by_category.py` inside `train.sh` |

## 4. Eval data (CKE papers; never committed)

| Artifact | Location | Size | Fetch | Regenerate |
|---|---|---|---|---|
| CKE PDFs (papers + answer keys, `*-arkusz.pdf`, `*-zasady.pdf`) | `data/raw/cke/` in a checkout | 115 MB | none (copyright) | downloaded from cke.gov.pl by `scripts/fetch_matura.py` |
| `matura.jsonl` (headline held-out set, May 2023-2026, 154 items) | `/mnt/project-files/data/eval/matura.jsonl`; `s3://$BUCKET/data/eval/matura.jsonl` (EC2 path); Modal `claude-matura:eval/` | 0.37 MB | `cp -r /mnt/project-files/data/eval data/` | `python scripts/fetch_matura.py --images -o data/eval/matura.jsonl` |
| `matura_all.jsonl` (all 16 papers, 512 items) | `/mnt/project-files/data/eval/matura_all.jsonl` | 1.4 MB | as above | `python scripts/fetch_matura.py --papers all --images -o data/eval/matura_all.jsonl` |
| `images/` (page images, 515 JPGs) | `/mnt/project-files/data/eval/images/` | 38 MB | as above | written by `fetch_matura.py --images` |

Nebius and Modal jobs ship these from the checkout (`nb_job.py` `DATA`) or rebuild them in the container
(`modal_job.py` runs `fetch_matura.py`), so a fresh box needs either `/mnt/project-files/data` copied into
`data/` or internet access to cke.gov.pl.

## 5. RAG knowledge base

| Artifact | Location | Size | Fetch | Regenerate |
|---|---|---|---|---|
| `data/kb/passages.jsonl` (25,216 Polish Wikipedia passages, CC BY-SA 4.0; `configs/routes.yaml` `rag.path`) | `/mnt/project-files/data/kb/passages.jsonl` + `SOURCE.md` | 20 MB | `cp -r /mnt/project-files/data/kb data/` | `python scripts/build_kb.py` (needs pl.wikipedia.org; the cloud sessions can't reach it) |

## 6. Tooling cache

| Artifact | Location | Size | Fetch | Regenerate |
|---|---|---|---|---|
| Prebuilt llama.cpp (`llama-server`, CUDA) | `s3://$NB_BUCKET/bin/llama-cuda-sm<cap>.tgz` (cap = GPU compute capability without the dot, e.g. `sm90` H100, `sm89` L40S) | not measured | `ensure_llama_server` in `infra/jobs/common.sh` pulls and unpacks it into `$WORK` | the same function clones llama.cpp, builds `llama-server` with `-DGGML_CUDA=ON` and uploads the tarball when `NB_BUCKET` is set. Modal uses the `ghcr.io/ggml-org/llama.cpp:full-cuda` image instead |
| HF cache | `$HF_HOME` (`$WORK/hf`; Forgehand `/scratch/hf`) | up to ~31 GB for GGUF + training base **(inferred)** | re-download | re-download |

## 7. Results

| Artifact | Location | Size | Fetch | Regenerate |
|---|---|---|---|---|
| `results/` (baselines, `gemma4/`, `grok/`, `small/`, `subtype/`, `tracks/`, `claude-graded/`, `images_value/`) | repo (301 files committed) | 2.2 MB | `git pull` | the job scripts (`infra/jobs/*.sh`, `scripts/run_exam.py`, `scripts/subtype_collect.py`) + graders |
| `results/judged/` (Claude-judged runs, `TABLE.md`) | repo | 0.45 MB | `git pull` | `scripts/claude_judge_run.py` / `claude_judge_official.py`, table by `scripts/judge_table.py` |
| Raw run outputs | `s3://$NB_BUCKET/out/<job>/`, Modal `matura-jobs:out/<job>`, `claude-matura:out/<job>`, `/mnt/project-files/runs/` (0.6 MB), `/mnt/project-files/subtype/`, Forgehand `/scratch/out/<job>/` | varies | commands at the top | rerun the job from its `docs/STATUS.md` row |

## Recovery checklist (VM dead)

1. `git clone` the repo; set `HF_TOKEN`, Nebius env vars, `~/.modal.toml`.
2. `cp -r /mnt/project-files/data/{eval,kb,train} data/` (or rebuild eval with `fetch_matura.py`, KB with `build_kb.py`).
3. Base model: `hf_hub_download` of the GGUF + mmproj (section 1).
4. Adapter: `huggingface-cli download orestta/matura-gemma4-12b-lora-A01` (confirmed), or pull the newer ones from
   `s3://$NB_BUCKET/out/<job>/adapters/` / the Modal volume until their HF backups are confirmed.
5. Serve: `scripts/serve_exam.sh` (llama-server with the GGUF LoRA).
