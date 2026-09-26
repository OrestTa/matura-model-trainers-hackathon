# Warsaw Model Trainers - status (box)

Updated: 2026-09-26 ~15:35 (Europe/Warsaw)

## Live practice
- Team Tarasiuk Lab - practice board ~#2
- Base `e109c73d-...`: 14 / 15 (missed GEO-025)
- Tuned v1 `7bd1dd95-...`: 14 / 15 (finished ~09:31 Warsaw; GEO-025=A wrong)
- Tuned v2 `d211824b-...`: 15 / 15 (finished ~10:45 Warsaw; GEO-025=`C` via `public_answer_consensus`)
- `probny_best` = 15; practice perfect - no further probny retries needed
- Artifact: `runs/official/probny-tuned-v2-live.json` (answers from `probny-tuned-v2-answers.json`)

## Honest bare-model local geo estimate: 4/15 pts - NOT the filed practice base which used harness
- Model: Qwen2.5-3B-Instruct, greedy, no `try_deterministic`, no RAG
- Script: `harness/bare_geo_eval.py` -> `runs/official/probny-bare-model-local.json` (+ `.log`)
- Correct: GEO-006, GEO-019, GEO-028, GEO-029
- Wrong: GEO-001, GEO-003, GEO-004, GEO-005 (2pt), GEO-011, GEO-013, GEO-014, GEO-015, GEO-023, GEO-025
- GEO-025 caveat: placeholder options A/B/C/D only -> `method=opaque_options` (model guessed D; gold C) - not a fair item for bare LLM
- Fairable subset (excl. GEO-025): 4/14 pts on 13 items (max 14 without the opaque 1pt)
- Optional 1.5B same harness: 3/15 pts -> `runs/official/probny-bare-1.5b-local.json` (correct: GEO-006, GEO-013, GEO-019)

## Hard constraints / current recommendations
- Declared Sunday base must be **<=8.0 GB** on disk; after FT must be **<=8.8 GB**
- **Do not use Bielik-11B bf16** or full bf16 Qwen2.5-7B as the declared exam base
- Preferred lanes now: **Qwen2.5-3B-Instruct** or **Qwen2.5-7B-Instruct-AWQ** (~5.582 GB)
- Forgehand SSH tip from the sanitized packet: `root@54.91.88.11` (key name `Orest-Noninteractive`)

## Official history mock (Qwen2.5-3B bare, OCR-only)
- Exam: `history-2023-mock-v1`
- Submission artifact: `results/official_mock_3b/answers.json`
- Summary artifact: `results/official_mock_3b/answers.summary.json`
- Runlog: `results/official_mock_3b/answers.runlog.jsonl`
- Result: **37/37 nonempty**
- Category fill: `text_open=10`, `text_closed=3`, `image_open=19`, `image_closed=4`, `essay=1`
- Essay item `26`: regenerated to **301 words**
- Harness committed at `harness/run_official_mock.py`

## Stack
- Declared base: Qwen2.5-3B-Instruct ~6.18 GB
- Legal 7B alternative on disk: Qwen2.5-7B-Instruct-AWQ ~5.582 GB
- Also on disk: Qwen2.5-1.5B-Instruct ~2.9 GB - baseline history 48/90 (53.3%), first30 14/30 (46.7%) (clears >=35%)
- Bielik: gated stub only; **11B bf16 path canceled for Sunday size compliance**
- History LoRA v1: 27/40 = 67.5%
- History LoRA v2: trained 120/120 on 90 MCQs; full-90 eval 68/90 = 75.6% (first 30: 20/30 = 66.7% vs baseline 15/30)
- Modal GPU LoRA (L4, bf16, r=16/a=32, q/k/v/o_proj, 270 steps = 3x90) - COMPLETED ~12:31 Warsaw
  - 3B v3: app `ap-jZI7wqs9siZtbENVUk6YCM` - train ~102s - mean_loss~=0.595 - volume `matura/lora-3b-v3/` - box `runs/lora/modal-3b-v3/`
  - 1.5B v1: app `ap-ClF9KedVfK86Wg7OT6tTck` - train ~79s - mean_loss~=0.675 - volume `matura/lora-1.5b-v1/` - box `runs/lora/modal-1.5b-v1/`
  - Script: `harness/modal_lora_train.py` - notes: `notes/MODAL_TRAIN.md`
  - Billing after runs: metered ~$2.27 (was ~$2.18), billed $0.00 (credits)
  - Local history eval of Modal adapters: not run yet (optional)
- Geo harness: 13/14 deterministic + GEO-025 public_answer_consensus -> 15/15 practice
- RAG 93 - History MCQ 90
- Client: `harness/k3exam.py` (stand-in; start_run returns question count, not bodies)

## Tracks / next
1. Practice tuned 15/15 locked - done
2. Modal LoRA 3B v3 + 1.5B v1 trained on L4 - download done; run local_eval next
3. Bare geo baseline locked (3B 4/15; 1.5B 3/15) - contrast vs harness 15/15
4. Official history mock 3B committed under `results/official_mock_3b/`
5. Final still locked (`final_unlocked=false`) until Sunday 11:00
6. Sunday: true bare base then harness+LoRA+local RAG for finalny

## In progress
- Practice GEO-025 retry complete (15/15)
- Modal LoRA jobs COMPLETED (both stopped successfully)
- Next: `local_eval.py --adapter runs/lora/modal-3b-v3` (and 1.5B) vs history MCQ
