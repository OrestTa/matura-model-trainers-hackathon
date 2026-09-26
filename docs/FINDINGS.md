# Findings

Shared log for every bot and person on this repo. Newest first, dated, one short entry per finding.
Pull before you add, commit straight to main.

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
