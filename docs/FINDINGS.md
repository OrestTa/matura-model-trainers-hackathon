# Findings

Shared log for every bot and person on this repo. Newest first, dated, one short entry per finding.
Pull before you add, commit straight to main.

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

- **GPU VM `root@34.224.61.209`** (key `~/.ssh/matura_gpu` on Orest's Mac only, never committed):
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

## 2026-09-26 12:35 CEST: Grok bot results live only in its chat

- The Grok bot reported these numbers in its chat, which is all we have for them:
  - Bare Qwen 3B scored 4/15 on the practice geo set with no formulas and no RAG. Only GEO-006, GEO-019, GEO-028 and GEO-029 were correct.
  - Qwen 1.5B scored 3/15 on the same set.
  - The practice run filed at 14/15 was almost all harness. Report a true bare base on Sunday or the progress score is misleading.
  - Also mentioned: history LoRA v2, a size-track 1.5B check, and a GEO-025 retry at 10:35.
- None of these runs, logs or files exist on Orest's Mac, in the `ai-sandbox-visual-grokbot` Docker container or in this repo's history as of 12:35. Grok Bot runs them in its own cloud sandbox.
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
