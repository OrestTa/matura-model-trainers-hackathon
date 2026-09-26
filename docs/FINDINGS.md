# Findings

Shared log for every bot and person on this repo. Newest first, dated, one short entry per finding.
Pull before you add, commit straight to main.

## 2026-09-26 15:35 CEST · best-score thread: the eval set now carries the pictures

- `python scripts/fetch_matura.py --images` (and `--papers all --images`) saves every picture in the
  papers as a JPEG in `data/eval/images/` (gitignored: CKE content) and lists them per item in
  `images`. **All 85 headline items that need a picture get one** (103 items have at least one);
  515 pictures over the 16 papers, 36 MB (8.7 MB for the headline four). Row text is unchanged
  (154/154 identical to the old set). Copies in /mnt/project-files/data/eval/ (+ images/).
- A model with `vision: true` in configs/models.yaml sees them in eval (`run_baselines.py`) and at the
  exam (`run_exam.py --model <key>`; `serve_exam.sh` adds llama.cpp's `--mmproj`). Only `gemma4-12b`
  has it so far. `fh_job.py run` now ships `data/eval/images` with the eval set.

## 2026-09-26 15:15 CEST · results page thread: one page, a tab per prize track

- `python scripts/build_tracks_page.py` writes `results/tracks/index.html`: tabs for best score, best progress
  and "Mały, ale wariat", each with best-so-far numbers, a chart, base→trained pairs, candidates and the
  track's jobs from docs/STATUS.md.
- **When you get a score, add a row to `results/tracks.json`** (`eval`: headline / headline-auto / contaminated / dev;
  `stage`: base / trained, and `base` = the id of its untouched base row for progress). run_baselines
  summaries under runs/baselines or results/**/summary.json are picked up automatically.
- The Grok bot's CKE numbers (e.g. 7B AWQ 37.6%) are over the **auto-scored items only (70 of 240 pts)** and
  were not measured by us; the page labels them that way. No judged 240-pt score exists yet.
- **Owner from 15:20 CEST: the Grok bot** (Orest). To refresh: `git pull`, add or edit rows in
  `results/tracks.json` (times in UTC there; the page shows CEST), update each track's `status`/`next`/`blockers`,
  run `python scripts/build_tracks_page.py`, commit `results/tracks.json` + `results/tracks/index.html` to main.
  Don't hand-edit the HTML. Claude threads no longer rebuild it.

## 2026-09-26 15:10 CEST · question-router thread: the official exam format (organisers' guide)

- Source: matura-json-guide (link from Orest). **Input:** a package with `exam.json` (`exam_id`,
  `instructions`, `items[]` with `id` string like "2.1", `max_points`, `question`, `source_text`,
  `images[{path, source_page, sha256}]`, `answer_format`), `images/*.png` and `answers-template.json`.
  **Output:** `answers.json` = `{"exam_id", "answers": [{"id", "answer"}]}`, every id once, strings
  only ("" allowed), Polish, `\n` line breaks, ≤ 1 MiB, ≤ 100k chars per answer. Uploaded with the
  team key on their page; **graded later by an LLM against the CKE key, in batches every ~30 min.**
  No time limit is stated. The mock is the May 2023 paper (37 items, 60 pts), which is in our eval set.
- **The exam sends pictures** (separate PNGs; "send the actual image content to your model"). 85 of our
  154 eval items need one, so a vision-language base under 8.0 GB could win a lot of points a text
  model can't. Candidates (unverified on vLLM 0.27.1 + bitsandbytes): Qwen2.5-VL-7B-Instruct,
  Qwen3-VL-8B-Instruct, Gemma-3-4B-it in 4-bit.
- Essay (item 26): must state the chosen topic number and have **at least 300 words**; the essay prompt
  now asks for "Temat nr X" and 400-600 words (max_tokens 2000).
- `scripts/run_exam.py <package> -o answers.json` answers a package through the router and validates
  the file; `--mode raw` gives the bare-model submission. `backend.vision: true` in routes.yaml sends
  the PNGs as image parts; otherwise the model sees our eval set's placeholder.

## 2026-09-26 14:50 CEST · Nebius: reachable from the cloud, use Serverless AI Jobs (no SSH)

- The Nebius API (api.nebius.cloud, gRPC) and Object Storage (storage.eu-north1.nebius.cloud) are reachable from our
  cloud sandboxes; the CLI installs with `curl -sSL https://storage.eu-north1.nebius.cloud/cli/install.sh | bash`.
- Outbound SSH (port 22) is blocked, so plain VMs are awkward. `nebius ai job create --image ... --platform gpu-h100-sxm
  --preset 1gpu-16vcpu-200gb --env K=V --container-command ... --timeout 12h` runs a container job without SSH; logs via
  `nebius ai job logs`, S3 buckets mountable with `--volume s3://BUCKET:/path`.
- Auth for bots: a service account in the `editors` group with an authorized key, kept in env vars, never in the repo.
- Untested draft runner: infra/nebius/nb_job.py (Claude stopped; the Grok bot owns the Nebius setup per Orest).
  Hackathon Nebius credits come from Gleb on Telegram.

## 2026-09-26 14:55 CEST · Solari credits: CPU-only, no GPUs

- **Solari (getsolari.com, organisers' "1 month of credits") has no GPUs.** Per docs.getsolari.com it sells
  cloud Chrome browsers, Linux VMs and headless sandboxes on Cloud Hypervisor microVMs: max **8 vCPU / 16 GB RAM**
  per machine, one region (us-west), max session 5 h (Starter) or 24 h (Professional). No GPU option in the
  docs, API reference or pricing page. It cannot run vLLM, training or GPU eval.
- api.getsolari.com and docs are reachable from our cloud sandboxes (API returns 401 without a key).
- At most useful for CPU side-jobs (data cleaning, dedup, BM25/RAG index building). Llama.cpp on 8 vCPU
  would be far too slow for a 7 GB model on the eval set. No runner built; not worth the effort vs Nebius.
- Redeem code stays out of the repo (it's in the organisers' announcement).

## 2026-09-26 14:55 CEST · best-progress thread: pretrained Bielik-11B-v2 as the progress base

- **Progress = trained score − untouched base score**, so the progress category wants a base that is weak
  raw but strong once trained. Proposed to Orest: **`speakleash/Bielik-11B-v2`**, the *pretrained* model
  (no instruction/chat tuning) that SpeakLeash built the Instruct versions from. Ungated, ~6.7 GB in NF4
  (under 8.0). Our own DAPT + SFT + RAG does the instruction tuning, so the whole gain is ours; we don't
  borrow SpeakLeash's instruct tuning. `configs/models.yaml`: `bielik-11b-base`, `bielik-11b-base-dapt`.
- It has no chat template. `configs/chat_templates/plain_pl.jinja` (plain "### Pytanie / ### Odpowiedź",
  answer ends in `</s>`) is applied by run_baselines (`--chat-template`), train_lora, train_dapt and
  quantize_checkpoint, so the raw baseline and our SFT see one neutral format.
- `train.sh SINGLE_ADAPTER=1`: one adapter on all types, linked under every category name and
  `general` (the untuned fallback would answer in free text). `routes.yaml` general now uses a
  `general` adapter when loaded; other models without one fall back to the base as before.
- Training data: Claude-written matura-style items (allowed: closed LLMs for synthetic data), filtered
  against the eval set with gen_synthetic's shingle filter, coming to `train_data/claude_synth.jsonl`.
- Open question for Orest/organisers: does a team file one base/trained pair for all categories?

## 2026-09-26 14:55 CEST · best-score thread: newer base models that fit 8.0 GB

- **We are testing Bielik v2.3, but Bielik-11B v3.0 is out (Nov 2025)** and speakleash ships
  its own AWQ W4A16 checkpoint, `speakleash/Bielik-11B-v3.0-Instruct-awq`: **6.19 GB on disk**
  (HF API sizes), not gated (no HF_TOKEN), loads natively in vLLM with no bitsandbytes. Config key
  `bielik-11b-v3`. Leaves 2.6 GB for adapters under the 8.8 GB fine-tuned limit.
- **Gemma 4 12B fits as Google's QAT Q4_0 GGUF**: `google/gemma-4-12B-it-qat-q4_0-gguf`, 6.98 GB
  (+0.18 GB mmproj for pictures; 85 of 154 headline items have one). Google's vLLM-native w4a16
  is 10.3 GB (bf16 262k-vocab embedding), so over. Config key `gemma4-12b`, served by llama.cpp.
- Also `qwen3.5-9b` (Qwen3.5-9B Q6_K GGUF, 7.46 GB). Qwen3-14B-AWQ is 9.98 GB: over.
- `run_baselines.py` now serves GGUF entries (`gguf_file`, `server: llamacpp`) with llama-server;
  `infra/jobs/common.sh ensure_llama_server` builds it with CUDA on the box. On a 1-GPU box
  `JUDGE_HF=... JUDGE_GB=n` runs the judge on the same card, so open answers get scored.

## 2026-09-26 14:05 CEST · release thread: repo audit before going public

- **Tree is clean now**: brief PDF removed, VM IP and AWS account ID redacted, no tokens or keys. Please
  keep IPs, tunnel URLs, account IDs and anything from the brief out of commits from here on.
- **History still has** the brief PDF (door code), two IPs, a loca.lt URL and the AWS account ID. No
  credentials. A tested `git filter-repo` plan is in `docs/PUBLIC_RELEASE.md`; it needs Orest's go and a
  pause on all pushes, since it rewrites main.
- New: `SOURCES.md` (datasets, models, licences, fetch scripts) and a reproduce section at the top of
  the README. SOURCE.md verified byte for byte.

## 2026-09-26 13:55 CEST · compute thread: pin vLLM 0.27.1 (0.28+ has no bitsandbytes)

- **vLLM 0.28.0+ removed `--quantization bitsandbytes`.** An unpinned `pip install vllm`
  now gets 0.30.0, and every 4-bit model in configs/models.yaml fails at startup with
  "Unknown quantization method: bitsandbytes" (seen on the Labqoat box). 0.27.1 is the last
  release with it (checked vllm's quantization registry at each tag). `infra/jobs/common.sh`
  and the Modal image now pin `vllm==0.27.1`; `scripts/serve_exam.sh` needs the same on
  exam day.
- **vLLM 0.27.1 also needs Python 3.12**: its pinned flashinfer 0.6.16.post3 fails to import on
  3.11 ("type 'array.array' is not subscriptable"), which the Labqoat image has. common.sh now
  builds `$WORK/venv-py312` with uv (`/opt/conda/bin/uv` is on the box).
- One L40S can now hold several jobs: `run_baselines.py --gpu-budget-gb` runs models side by
  side, and `infra/jobs/gpu_admit.py` (fh_job.py `GPU_GB=<n>`) admits a job when its memory
  fits.

## 2026-09-26 14:05 CEST · matura_all.jsonl no longer double-counts the 2023/2024 papers (eval-set thread)

- The old-format (EHIP) 2023 and 2024 papers are almost the same exam as the new-format (MHIP) ones:
  28 of 33 and 33 of 35 items repeat a formuła 2023 task. `fetch_matura.py` now marks these with
  `duplicate_of` and drops them from the full set by default. **`matura_all.jsonl` is now 512 distinct
  items, 789 points** (was 573 / 860). Headline `matura.jsonl` is unchanged (154 items, 240 points).

## 2026-09-26 13:55 CEST · 133 real past-paper items as training data (eval-set thread)

- `scripts/build_train_from_papers.py` turns the non-headline papers (formuła 2015 May 2015–2024, 2022 demo,
  Jan 2026 mock) into `data/train/past_papers.jsonl`: **133 items with official CKE answers** (source_analysis 82,
  closed_choice 22, short_open 19, true_false 10), answers in the router's output shapes (template filled in,
  first model answer only). `train.sh` now appends it to synthetic.jsonl automatically.
- **The old-format 2023/2024 papers (EHIP) share most tasks with the headline 2023/2024 papers (MHIP)**, sat the
  same day: 64 items were dropped as overlapping the eval. Don't train on `matura_all.jsonl` rows blindly, and
  don't average EHIP and MHIP 2023/2024 as if they were independent papers.
- Skipped: 209 items that need a picture, 12 essays (the key is a rubric, not an essay), 1 with an image key.

## 2026-09-26 13:45 CEST · question-router thread: majority voting on closed types

- Closed choice, true/false and matching now answer 5 times (greedy + 4 samples at T=0.7) and keep
  the majority, ties to the greedy answer (`votes:` in `configs/routes.yaml`, `Router._vote`). Raw
  mode never votes. Unmeasured so far: compare routed runs with and without `votes` once a GPU is free,
  and set `votes: 1` for a type where it doesn't help.

## 2026-09-26 13:35 CEST · question-router thread: offline RAG mode

- New router mode **`rag`** (router prompts + retrieval, base model); **`adapters`** now also retrieves.
  BM25 with 6-letter prefix stemming over `data/kb/passages.jsonl` (`matura_router/rag.py`, pure
  Python, no GPU). Raw and routed never see retrieved text, so the baselines stay comparable.
- The knowledge base comes from Polish Wikipedia via `python scripts/build_kb.py` (CC BY-SA, one URL
  per passage). **Cloud sessions can't reach Wikipedia** (proxy denies pl.wikipedia.org), so build it
  on the GPU box. Not built yet; no RAG scores yet.

## 2026-09-26 13:30 CEST · Every past history matura with a key is now in the eval set (eval-set thread)

- `python scripts/fetch_matura.py --papers all` builds `data/eval/matura_all.jsonl`: **16 papers, 573 items,
  860 points**. That is every historia (rozszerzony) paper CKE publishes with an answer key: formuła 2023
  May 2023–2026 plus the March 2022 demo and January 2026 mock (6 × 60 pts), and formuła 2015 May 2015–2024
  (10 × 50 pts). Every paper parses to exactly its official point total. Per-paper table:
  `results/eval_set_papers.md`. The default (`headline`) is still the four real formuła 2023 May papers.
- CKE only publishes the main May session for history. No June/August papers, and no poziom podstawowy
  since 2015. Pre-2015 papers (the old matura, 2005–2014) are no longer linked on cke.gov.pl.
- Auto-scorable without a judge: 205 of 573 items. Needs a picture: 305 of 573.
- **Chronology is essentially absent from every format since 2015**: 1 item in 573. Source analysis is 379.
- Formuła 2015 keys differ from formuła 2023 keys ("Schemat punktowania" before "Poprawna odpowiedź",
  "Odpowiedź: A" + justification). Two keys are images in the PDF (f15-2016 z8, f15-2019 z11.2) and are
  marked with a `warning`.
- Baseline scores per paper are not run yet: no GPU is reachable from this session. The baseline job
  picks the full set up with `--eval data/eval/matura_all.jsonl`.

## 2026-09-26 13:20 CEST · question-router thread: answer templates, verdict check, frozen exam checkpoint

- **72 of 154 eval items carry an answer-sheet template** ("Rozstrzygnięcie: … / Uzasadnienie: …",
  "Fragment A – …", "Cecha: …"). Routed and adapter modes now tell the model to fill it in line by
  line (`matura_router/prompts.py:answer_template`); raw mode doesn't, so the bare baseline stays bare.
- **The 52 "Rozstrzygnij" items are now partly judge-free.** A verdict that disagrees with the key's
  `decision` scores 0 (as in the CKE key), and every summary.json has `decision_acc`. All 52 official
  keys pass the matcher; swapping in any other item's verdict fails except "Fragment 2." vs "Źródło 2".
- **Size limit is 8.9 GB for the base model's weights on disk** (Orest, from the organisers). vLLM's
  load-time quantization doesn't count, so `scripts/quantize_checkpoint.py <model>` writes a 4-bit NF4
  checkpoint to `work/checkpoints/<model>` and fails if it is over the limit. `run_baselines.py` serves
  it once it exists (`served` in summary.json), and `scripts/serve_exam.sh <model>` is the on-stage
  harness (checkpoint + adapters + router, offline). Not yet run on a GPU.

## 2026-09-26 13:10 CEST · compute thread: Forgehand has one GPU for the whole team

- Forgehand team `rst` may run **one GPU session at a time**, and the only GPU class is
  `gpu-l40s-small` (1x L40S 48 GB, $1.86/h). A second `fh session start` fails with "your
  team already has 1 GPU session running". Jobs must queue on the one card: `WAIT_GPU=1
  infra/forgehand/fh_job.py run <session> <job>` waits until GPU memory is under 2 GB.
- `fh_job.py` now works from cloud sessions against the live session (exec, run, log).
  Jupyter rejects hidden paths, so uploads live in `/workspace/work/upload/`.
- Queued: `labqoat-baselines` (all models, no judge) behind the Grok bot's 7B LoRA.

## 2026-09-26 13:00 CEST · GPU VM thread: 1x L40S box runs training; staggered-harness plan

- **GPU VM (`root@<vm-ip>`, address kept out of the repo)** (key `~/.ssh/matura_gpu` on Orest's Mac only, never committed):
  a Labqoat/Forgehand container (overlay FS, JupyterLab on :8888, no AWS metadata, so it is not
  Orest's suspended AWS account). 1x NVIDIA L40S 46 GB, driver 595.91, CUDA 13.2, 4 vCPU, 30 GB RAM,
  139 GB free disk, Ubuntu 22.04, Python 3.11, tmux + git, no docker. `~` is `/workspace/.home`
  (persistent). The repo is private, so it was rsynced from the Mac, not cloned.
- **Training is NOT running there yet (the box is shared).** I started `train.sh` in tmux `train` at
  12:53 CEST. At ~13:00 another agent's job replaced it (a different tmux `train` in
  `/workspace/hackathon`: `harness/forgehand_lora_train.py --model-size 7b`, a history LoRA, 2000
  steps, plus a `hist_eval` session). That killed my pip install halfway (`work/venv` has no vllm/trl).
  That job uses ~17 GB of the 46 GB card, which leaves too little for the 31 GB FP8 teacher. Restart
  `train.sh` in a tmux session with a unique name (e.g. `bielik-train`) once the card is free, or
  run the teacher/data step on Modal and only SFT here.
- **Plan for the exam:** [docs/PLAN_STAGGERED_HARNESS.md](PLAN_STAGGERED_HARNESS.md): a cascade of
  rules/tools, then the router, then a 4-bit base with one LoRA per question type, then a
  vote/verify check. Training follows the workshop's steps (domain continued-pretraining, per-type
  SFT, GRPO/RLVR on the auto-scorable types), with a staircase chart per stage and waves until
  01:00.

## 2026-09-26 13:15 CEST · compute thread: Modal can't run from Claude cloud sessions

- The Modal client speaks gRPC, which the cloud sandbox proxy can't carry ("Could not
  connect to the Modal server" even with a token). Launch Modal only from Orest's Mac.
- Websockets do pass the proxy, so `infra/forgehand/fh_job.py` (JupyterLab terminal
  over wss) should work from the cloud once signed in to Forgehand.
- Orest wants runs started from the cloud, so baselines go to Forgehand.

## 2026-09-26 13:05 CEST · compute thread: Modal runner, Forgehand as fallback

- Orest: **use Modal** for compute. `modal run --detach infra/modal/modal_job.py --job
  baselines` runs `infra/jobs/baselines.sh` unchanged on Modal GPUs (default `--gpu
  L40S:4`: two GPUs score models, two serve the judge). Job settings go in `--env
  "MODELS=qwen3-8b JUDGE_HF="`. Outputs, adapters and the HF cache are on the Modal
  volume `matura-jobs` (`modal volume get matura-jobs out/<name> runs/modal/`). The
  Modal login lives only on Orest's Mac (`~/.modal.toml`, workspace `orestta`), so
  cloud threads launch through the Mac's Remote Control session.
- **Labqoat Forgehand (app.forgehand.app)**: fallback. Cloud sessions reach it over
  HTTPS, but outbound SSH (port 22) is blocked, so `infra/forgehand/fh_job.py` drives a
  session through its JupyterLab API instead. CLI: `npm i -g @qforge/forgehand`
  (`fh`), auth by emailed code or a `FORGEHAND_TOKEN` access token (Settings -> Access
  tokens). Node fetch needs `NODE_USE_ENV_PROXY=1` behind the sandbox proxy. Workspace
  has persistent `/workspace`, team-shared `/team`, and `/scratch`; secrets
  (e.g. HF_TOKEN) are set on its Secrets page. Not yet tested against a live session.
- `infra/jobs/common.sh` now takes `OUT` from the environment (default `$WORK/out`).

## 2026-09-26 12:45 CEST · question-router thread: AWS is out, jobs run on any GPU box

- Orest: the AWS account was suspended; don't invest in EC2 any more.
- `infra/jobs/baselines.sh` and `infra/jobs/train.sh` now run directly on any Linux
  GPU box (Nebius, Modal, a rented server) with no AWS or S3: `bash
  infra/jobs/baselines.sh` writes to `work/out/`. Checked end to end locally with a
  stubbed GPU and vLLM (eval set built, both modes scored, report drawn).
  See [docs/HOWTO.md](HOWTO.md).

## 2026-09-26 12:39 CEST: AWS account suspended, stop using AWS

- Orest reports the AWS account is suspended. Don't plan training or baselines on AWS anymore;
  `infra/aws/` and `infra/jobs/ec2_job.sh` are dead ends unless that changes. Use the other
  compute (Nebius, Labqoat/Forgehand, Modal free tier, per the brief).

## 2026-09-26 12:40 CEST: AWS access and spending guards

- **GPU quota is the bottleneck, not money.** Applied EC2 quota for P and G/VT instances is 0 in
  every scanned region; requests are pending (tracker in `infra/aws/AWS_INFRA.md`). p5.48xlarge in
  us-east-1 also failed on capacity. Until a quota lands, `infra/aws/launch.sh` cannot start GPUs.
- **Only the Activate credit may pay** (about $98.4k left, expires 2026-09-30). `launch.sh` refuses
  to start anything if month-to-date cost after credits is above `MAX_NET_USD` ($5), or if the
  projected on-demand cost of everything running until the Sunday 10:30 CEST cutoff passes
  `BUDGET_USD` ($95k). Cost Explorer lags a few hours, so the $5 check catches card charges late.
- **Every instance self-terminates at `DEADLINE_UTC`** (shutdown behaviour terminate plus a
  `shutdown -h` timer), and `/opt/work/out` syncs to S3 every 10 minutes. Anything not under that
  path is lost at the cutoff.
- **No SSH needed:** `infra/aws/run.sh <id> <cmd>` runs commands over SSM. The security group has no
  inbound rules. `launch.sh` now attaches the `Orest-Noninteractive` key pair (set `KEY_NAME=` to
  skip) in case someone opens port 22.
- **Scripts run on macOS** (bash 3.2, BSD date/sed) as of commit 274b411; earlier versions failed
  there on an empty array under `set -u` and on `date -d`.
- **Claude cloud sessions** reach AWS endpoints through the proxy but have no AWS keys; only
  Orest's Mac (profile `matura`) has credentials. AWS work from cloud threads needs keys added to
  the project environment settings first.

## 2026-09-26 12:40 CEST · question-router thread: baselines are blocked on EC2 quota

- **No GPU can be launched yet: EC2 quota is 0 everywhere** (see
  [infra/aws/AWS_INFRA.md](../infra/aws/AWS_INFRA.md)). `infra/jobs/ec2_job.sh`
  defaults to g6e.48xlarge (8 GPUs), which failed with "vCPU limit 0". If only a
  small G quota (32 vCPUs, e.g. g6e.8xlarge with 1 L40S) comes through first, run
  with `TYPE=g6e.8xlarge`. Baselines then run one model at a time with no judge
  (only auto-scored items count), and the train job switches to a 30B teacher that
  fits one GPU.
- Routing on the real eval set: 132/154 = 85.7% (`python -m matura_router classify
  data/eval/matura.jsonl`). Beyond the source_analysis misses listed below, 4 of 13
  short_open items go to source_analysis and 3 to general. Open types are handled
  alike, so the cost is small.
- **Judge output must be parsed strictly.** A judge that echoed an answer containing
  a year ("1791") was read as full marks. Fixed in `matura_router/scoring.py`: only a
  small integer no larger than the item's points counts.
- Gemma-3-12B is gated on Hugging Face: set `HF_TOKEN` or that model's baseline
  fails (the others still run).

## 2026-09-26 13:50 CEST: Grok bot GPU jobs must be registered

The L40S in Forgehand session 01a0dd4b is shared by several bots. Your tmux sessions `gpu_par` and `dl7b` (`hf_eval_matura.py`, ~22 GB) have no rows in `docs/STATUS.md`, so other jobs can't plan around them and may OOM.
- Before taking GPU memory: `python3 infra/jobs/gpu_admit.py <job-id> <need-gb>` (waits until the card has room).
- On start, state change and finish: `python infra/jobs/status.py <job-id> state=running where="Forgehand 01a0dd4b, tmux <name>" what="..." out=<dir> owner="Grok bot"`, then pull and push.
- Please add rows for `gpu_par` and `dl7b` now.

## 2026-09-26 12:35 CEST: Grok bot results live only in its chat

- The Grok bot reported these numbers in its chat, which is all we have for them:
  - Bare Qwen 3B scored 4/15 on the practice geo set with no formulas and no RAG. Only GEO-006, GEO-019, GEO-028 and GEO-029 were correct.
  - Qwen 1.5B scored 3/15 on the same set.
  - The practice run filed at 14/15 was almost all harness. Report a true bare base on Sunday or the progress score is misleading.
  - Also mentioned: history LoRA v2, a size-track 1.5B check, and a GEO-025 retry at 10:35.
- None of these runs, logs or files existed on Orest's Mac or in the `ai-sandbox-visual-grokbot` Docker container at 12:35. Grok Bot runs them remotely (Modal, Forgehand). Update 13:50: it now syncs results to `INSIGHTS.md`, `HACKATHON_LOG.md` and `dashboard/status.json`.
- This "Grok Bot" build talks to Cursor's backend (`api2.cursor.sh`). Transcripts are stored server-side, and there is no API or export.
- Its local logs (`~/.grokbot/local-exec-daemon.log`, container `launch.log`) record only the helper process and connection errors, never commands, scores or paths.
- **Ask for:** Grok bot, commit each run's scores (per item where possible) plus the exact model and command to `results/grok/` here, so other bots can check and reuse them.
- Access notes: `http://127.0.0.1:3080` is a noVNC desktop viewer for the container, not a chat API. SSH on port 2223 currently fails because `/config/.ssh` is owned by uid 911 instead of abc (1000). The fix is `chown -R abc:abc /config/.ssh`, and `cont-init-sshd` should use `$PUID:$PGID`. `docker exec -it ai-sandbox-visual-grokbot-desktop-1 bash` works.

## 2026-09-26 · Eval set from real CKE papers (eval-set thread)

- `python scripts/fetch_matura.py` builds `data/eval/matura.jsonl` from the May 2023–2026 historia
  (rozszerzony) papers and official keys: 154 items, 4 × 60 = 240 points. Every paper parses to exactly
  60 points, and every official key scores full marks against `matura_router/scoring.py`.
- **85 of 154 items need a picture** (map, photo, poster, plan, stamp) that a text model only sees as
  `[ilustracja – niedostępna w wersji tekstowej]`. Flag: `needs_image`; `--text-only` drops them.
  A text-only model has a hard ceiling well below 100% on the full paper.
- **The exam is mostly source analysis.** Gold types: source_analysis 109, short_open 13, true_false 12,
  closed_choice 12, matching 4, essay 4 (15 pts each, 25% of the paper), **chronology 0**. Formuła 2023
  papers have no ordering tasks, so a chronology adapter buys nothing on this exam.
- **52 items are "Rozstrzygnij … uzasadnij"** (verdict + justification, 1 pt only if both are right).
  This is the single most common task shape and may deserve its own prompt/adapter. The bare expected
  verdict is in the `decision` field.
- Rule classifier vs gold types: all closed/essay types routed correctly; 13 of 109 source_analysis
  items go elsewhere (5 general, 5 short_open, 2 closed_choice, 1 chronology).
- ~60 items are auto-scorable (closed keys + `gold_keywords`); the rest need the judge.
- Scorer gap: `scoring._pairs` only reads "1 – B". Letter-keyed matching keys ("Fragment A – Karol IX",
  "A – 3") are therefore emitted as `gold_keywords` instead of `gold`.
- Older formuła 2015 papers (2015–2022) are not included; they have more closed/chronology items and
  could serve as extra training data, not as a faithful eval.
