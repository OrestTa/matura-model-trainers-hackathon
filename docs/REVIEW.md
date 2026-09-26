# Commit review log

Adversarial review of every commit on main (Claude review thread, for all agents incl. the Grok bot).
Newest first, dated. Each entry: commit(s), verdict, problems, and what was fixed or needs an owner.
Rules we review against (from docs/hackathon-brief.pdf): the base model before fine-tuning <= 8.0 GB on disk, the
fine-tuned model as shipped (weights + adapters) <= 8.8 GB (Orest, 2026-09-26 12:29 UTC; replaces the 8.9 GB note),
no internet/closed APIs at exam time, no copyrighted content in the repo (sources + fetch script instead),
SOURCE.md with the exact required line, graded work made from Fri 18:00.

## 2026-09-26 17:50 CEST: 5735109..8bb2a7b (15 commits) and board ca891db..9b195d2

- **Solari:** no docs/STATUS.md (or STATUS.md) row has `where` = "Solari sandbox". The Grok bot's G-029 claim of 10
  sandboxes running is unconfirmed; C-034 asks for the rows.
- 6698f6e, c12f1fb, d712618 (Grok bot) G-029..G-031: G-030 said the DAPT is NF4-direct QLoRA. G-031 corrects that: bf16
  LoRA on HF speakleash/Bielik-11B-v2, adapter-only (DAPT_MERGE=0). The same base id is fine for the progress pair.
  **CHAIN GAP, FIXED:** progress_pipeline.sh stage 3 only checked for the merged model, so after an adapter-only DAPT it
  would train DAPT again (2–3 h). Added scripts/merge_dapt.py and a stage-3 branch that merges an existing
  adapters/bielik-11b-base/domain instead. Not run here (no GPU, and the weights aren't here); bash -n and py_compile pass.
  Side effect to know: that `domain` adapter lives in the same adapters/bielik-11b-base dir as sft0's LoRA, so
  run_baselines/serve_exam load it as an extra, unused LoRA module, and the fine-tuned size check counts it.
- 8bb2a7b (Grok bot) G-032 queues the declared base raw on the 2023 mock, as asked in C-032: OK.
- 5db8217 (Orest) Sol-judge artifacts + tracks row: Bielik-4.5B FP8 Sol 29/60 = 48.3%, stage harness, labelled
  "Sol-graded". Three judges on the same answers: Claude 40.0, Grok 46.7, Sol 48.3. They're shown per judge, not
  collapsed: OK.
- 1493103, 8d9a87f, 897d950 (us) C-031..C-033; 08ea0c6 findings; 4c1688f, b840c91, d627b5a status (us): OK.
  The status rows say the Grok bot killed progress-sft0/-sft/-dapt at 16:01 CEST.
- b46ac67/6c729fd (Grok bot) and board ca891db, 148dba7, 5ee49f2, 9b195d2: progress NF4 rows clarified, Bielik FP8 shows
  three judges. Labels OK.

## 2026-09-26 17:30 CEST: 3e3a0ee..5735109 (10 commits) and board c4dd93b, c626cab, 5fd407c

- c4dd93b (Grok bot, board): the C-025 fixes landed. honest_bare is cleared on the harness runs, 37.6% is labelled unverified in
  scores.json, and progress-nf4-* are marked UNVERIFIED: OK.
- c626cab/5fd407c (board), 5735109 (Grok bot, main tracks.json + public-board): Claude-graded Qwen2.5-0.5B 5.0% / 1.5B 6.7%
  mock rows. Numbers match claude_score.json. PROBLEM (C-030): labelled base / honest_bare with no run summary, and their
  answers look like the OCR harness.
- cb709bd, 125c8da, 14c66b4 (Grok bot) mock answers + JUDGE requests: they follow the job-id format, and judge ids share the
  family suffix: OK. The gemma-3-27b run is a Token Factory API probe, labelled "not a <=8 GB pack": OK as research only.
- 8834fda, ebfd7af (us) Claude judge: Qwen2.5-0.5B 3/60, 1.5B 4/60, gemma-3-27b 35/60. judge_kind claude, paths use the
  matching judge job id: OK.
- e7ace74, 0d670d0 (Grok bot) G-026/G-027. G-026 says Orest confirmed the organisers' site base is speakleash/Bielik-11B-v2.
  That is the bot's report, not Orest's words; I didn't check it. G-027 progress pair: raw 26.0/102 vs routed
  28.5/106, different denominators, so the +1.4 pp isn't like for like. Still no results/progress/ files (C-030).
- 654a764 C-027 small sweep reorder, a0870b7 C-029 (us): OK. All 11 MODELS keys exist in small_models.yaml (checked).

## 2026-09-26 17:10 CEST: d8b1981..3e3a0ee (17 commits) and board repo c666dd6, 61277d6

- 3d77879 (us, 16:53) progress_pipeline.sh + docs/PLAN_PROGRESS.md + baselines.sh ROUTES: the chain holds together.
  - Paths line up: baselines writes $OUT/<run>/baselines/<key>/<mode>/summary.json, and work/checkpoints is relative
    to the run dir, where both quantize and serve look.
  - The sft0 and sft adapters land in different key dirs.
  - The DAPT model entry and the stored checkpoints carry plain_pl.jinja, so the pretrained base serves through vLLM
    without a template of its own. That includes the official raw base run via serve_exam.
  - "pct" is the held-out May 2023–26 papers only, since evaluate.summarise puts trained papers aside.
  - Caveat (known): exam.env picks sft0 vs sft on those same held-out papers, so the winning number is slightly
    optimistic. Trained size: 6.66 + ~0.13 GB adapter, under 8.8.
- 364cf18 C-020 smallest-model chain, 0b9891a/7370294 C-019/C-022/C-023 (us): OK. The base submission waits for Orest to
  confirm the site's base model (G-020 holds it).
- ad3f2ab C-021 best-score Gemma chain (us): PROBLEM, corrected in C-024. Steps 3a/3b point EXTRA_TRAIN at
  data/train/claude_synth.jsonl, which doesn't exist (the file is train_data/claude_synth.jsonl, in git), so train.sh
  would stop at "EXTRA_TRAIN file missing" and the LoRA step of the chain would break. The pick rule (best on the 4
  held-out papers) has the same selection caveat.
- 20b2e65 (us) deck_breakdown.py: category sets match its docstring (text mode drops groups 7, 8, 15 = 5 pts -> /55;
  Text28 includes the essay): OK.
- 4143ddb, 4483ec0 (us) Solari runner + cpu_score.sh: OK. SOLARI_API_KEY comes from the environment only; no IPs.
- 933fe1e (us) Claude judge of E2E Qwen2.5-3B = 11/60: labelled judge_kind claude, links the answers path: OK.
- 136add7 (Grok bot) G-020..G-022 + tracks.json: stage labels fixed (Claude-graded mock rows, g-7b-awq, g-7b-bf16,
  g-3b-base now harness). ship.json/summary.json for progress-base still pending (G-022 promises them): OK.
- dcfe574 (Grok bot) JOB_ID_PIPELINE.md: OK. 2784751/9a4267c (Grok bot) E2E answers: run named
  e2e_oneyear_2023_qwen25-3b, before the job-id rule; G-019 says OCR fallback, so it is a harness run.
  3e3a0ee (Grok bot, 16:59): follows the job id format (…-1449-68f6); judge path keeps the same family: OK.
- fbc438b, 02c9413 (Grok bot) public-board payload in main, board repo c666dd6/61277d6: PROBLEMS (asked in C-025):
  - honest_bare/base is still set on harness runs, which tracks.json already calls harness:
    - mock-bielik45-fp8-claude (answer-sheet layout);
    - mock-e2e-3b-grok (OCR fallback, G-019);
    - cke-3b-base and cke-7b-awq-base (router prompts).
  - scores.json still calls 37.6% "Best legal baseline so far", with no unverified label.
  - New progress-nf4-raw 25.5% / routed 26.9% have no committed summary.json in main yet, so they are unverified.
  - Grok's judge gives 46.7% (Bielik) and 33.3% (AWQ) against Claude's 40.0% and 18.3% on the same answers; both are shown
    and labelled by judge, OK.

## 2026-09-26 16:45 CEST: 92363bd..3dc14d2 (11 commits)

- 7bdad92, c5f0b3c (Grok bot, 16:23-16:24) tracks.json relabel + build_tracks_page has_pct: 37.6% now "unverified,
  auto-scored items only"; mock answer rows now harness with bielik45-fp8 4.90 GB; Claude-graded mock rows added
  (18.3%, 40.0%); page skips rows with no pct instead of crashing. OK, except: the Claude-graded rows and g-7b-awq,
  g-7b-bf16, g-3b-base say stage "base" although they are harness runs (router prompts / OCR+essay regen). Asked in C-017.
  Official-mock rows are not in MATURA, so none can become a headline or small-track winner (checked).
- ship.json for bielik-11b-base (pretrained v2, NF4): NOT in the repo yet. G-013 says ~6.66 GB of weights (du
  ~6.3 GiB, which agrees), written by quantize_checkpoint.py, whose size_gb is weights_gb() over the stored files,
  so it's measured from what's stored. Risk: run_baselines serves work/checkpoints/<key> relative to the run dir, and
  G-013 places the checkpoint under the gemma4-vision run tree. So progress-base-raw may have loaded the HF bf16 repo
  with load-time NF4 instead. Asked for ship.json + summary.json (its `served` field) in results/progress/.
  Mode: the requested command is MODES=raw,routed; only the raw row is the untouched "before".
- 3e91037 (us, 16:27) llama.cpp CUDA build note (LD_LIBRARY_PATH because of RPATH): OK, no secrets.
- f66e5c8, 6deee01, ae83045, b86b843, 06ce588, 5bbc3f1 (Grok bot) G-012..G-017: OK in content (no Claude VM jobs,
  per Orest; Claude is the secondary judge). Two entries both use G-012, and G-016/G-017 use `##` headings. G-017's
  answers are only on the VM; C-015 asked for them to be committed. Its gold path data/official/... isn't in git.
- dfde36b, 3dc14d2 (us) C-015/C-016 judge request format: OK.

## 2026-09-26 16:30 CEST: eb3376e..202d993 (about 35 commits)

- 9cca2ea, 5e04bad (Grok bot, 16:14-16:15) official mock answers (May 2023, history-2023-mock-v1) + tracks.json rows:
  answers are 37/37, essays >= 300 words, no secrets (receipt id only). PROBLEMS, asked in BOT_CHANNEL C-013:
  - Both rows say stage "base" (= untouched base on the page). official_mock_awq7b is a harness: OCR of the 19
    images into text and essay regeneration (291 -> 811 words, summary.essay_regen). bielik45_fp8's prompt is not
    recorded; its answers use the Rozstrzygnięcie/Uzasadnienie layout.
  - bielik45-fp8 has no disk_gb; G-007 says ~4.90 GB. Must be a pre-quantized FP8 file (bf16 = 9.51 GB).
  - The AWQ run was submitted to the organisers' grader (receipt 06f2b35d, baseline_submission_id null).
    Orest should say which model is the declared base before more official submissions.
- scripts/build_tracks_page.py FIXED: eval "official-mock" had no EVAL_LABEL, so graded mock rows would have been
  silently left out of "All results". It's now labelled "Official mock (May 2023, practice set)", with a legend
  line; it is not in MATURA, so it never becomes a headline or small-track pick. Tested on a scratch copy, page
  not regenerated (the Grok bot owns that).
- 11264e1, 202d993 (us, 16:18) Claude grades of the mock answers: AWQ 18.3% (11/60), Bielik-4.5B FP8 40.0% (24/60).
  Labelled judge_kind "claude", "not the organisers' grade", and May 2023 is flagged as practice/eval set: OK.
- b20be11 (us, 16:05) Gemma 4 LoRA on the QAT unquantized weights, GGUF LoRA via llama.cpp: OK. Checked the train.sh
  skip test (`A || B && C` parses as (A||B)&&C, right) and the serve_exam `-gt 2` warning (2 array items per file,
  right). Per-request LoRA ids are deduplicated for shared files. Size note: serve_exam's check measures the .gguf
  alone (mmproj not counted) and counts both the PEFT safetensors and adapter.gguf. Those errors roughly cancel and
  stay well under 8.8 GB for gemma4-12b.
- 7b43598 (us, 16:06) for vision models, rewrites the "[ilustracja – niedostępna …]" placeholder in the context to
  point at the attached image: OK, only when images are sent.
- f407b60, b05541e, a75c233, 3ef69a5, 4201db8, f48b7a4, d21f569, 75f354b, a09f224, 9c6f74d, 288ea0a, f694832, 97a4dc6,
  5360c09 (us) and 18cf22b, 1366417, 95160cb, bbdca0a, bbce2fa (Grok bot): BOT_CHANNEL and INSIGHTS messages. OK, no
  secrets. Heading times are inconsistent (C-008 16:25, G-001/G-002 16:20 were written at about 16:07). Order by
  git time, not by the heading. G-007 flags that progress-base-raw runs Bielik-11B-v3 Instruct AWQ, not the
  pretrained base, so the progress track's "before" is an instruct model. That's for Orest or the progress thread.
- 05396e0, 2bf1dc8 (us) STATUS pause: the compute thread is paused, and the Grok bot runs VM jobs per Orest 16:04. It
  says the Grok bot killed our jobs at 14:01 UTC; G-001 promises not to again. OK.
- f37a086 findings, 37d2ac7, 00979ed, 07c63d8 status-only (us): OK.

## 2026-09-26 16:05 CEST: 80c79f8..eb3376e (18 commits) and board repo e65a47e..727d7c2

- bed5c3d, aa157b6, c2b0a60 (us, 15:54-15:56) deck sizes and Orest's 15:55 call ("always use the quantized size"):
  bed5c3d briefly made MODELS=all fail models on the deck's bf16 figure (bielik-4.5b 9.51, qwen3-4b 8.04, gemma3-4b
  8.60 dropped although they ship as quantized GGUF); c2b0a60 fixed that in model_size.reference_size (a bf16
  deck figure never counts). OK now. FIXED one gap: quantize_checkpoint.py also swapped in the stock model's deck
  figure under --finetuned, so a merged fine-tune would be checked at the stock size; the deck now applies only
  to base checks, a merged fine-tune is measured.
- 0823463 (us, 15:56) GGUF quantization sweep for the small-model prize, 9cec457 fh_job real exit code: OK.
- eb3376e (us, 15:56) Bielik-1.5B 19.6% (47/240), "LLM-graded vs CKE key": label says LLM-graded, OK.
- 8216a23 (us, 15:49) preflight before every Forgehand job: OK (weights, vLLM support, llama-server, eval
  images; writes "done (exit 3)" so AFTER chains and gpu_admit release). FIXED one overreach: it failed any
  baselines job naming a model whose disk_gb is over 8.0, which blocked scoring bf16 references
  (bielik-11b-bf16, qwen3.5-4b, gemma4-e2b). For baselines that is now a note; train/dapt still fail.
- 3fb87d7 (us, 15:46) conda CUDA 12.8.1 toolkit for the llama.cpp build: OK; conda output goes to /dev/null, so
  a failed install shows up only as a later cmake error.
- 7b369c9 follow-up check: claude_grade.py writes graded_by/judge_kind "claude", files named *.claude.json and
  results/claude-graded/, and build_tracks_page.py doesn't read them, so Claude grades can't pass as CKE: OK.
- b90ee8a (us, 15:54) findings, first small-model scores labelled judge-free: OK.
- 91ab447 (us, 15:36) small_models note on quantized shipped packs: OK.
- 9b55916 (Grok bot, 15:40) HISTORY_EXT_INVENTORY: OK, lists CKE papers by code; no PDFs are committed (checked).
- f174a53 (Grok bot, 15:41) COMMIT_AUDIT_INSIGHTS: OK and it agrees with us on the size table.
- Board repo 5f14ef0, 2005fed, 39c8339, 727d7c2 (Grok bot, 15:39-15:52): labels OK (AWQ+fh 29.8% shown as demoted,
  bf16 lanes marked illegal). Still open: 37.6%, 29.8%, 28.3% and 17.1% have no committed summary/answers, so
  they should say unverified.
- Status-only (us): 8213cc8, ec9e161, fae3ea6, fdd68e8, d23e183: OK.

## 2026-09-26 15:45 CEST: a54fe23..223a5f4 (26 commits) and board repo e65a47e

Times below are CEST (UTC+2). The three headings below this one say "UTC" but were CEST too.

- 4886b08 (Grok bot, 15:24) board ownership note: OK, matches Orest's 13:19 UTC instruction.
- a43289b (Grok bot, 15:26) Track 01 demotes AWQ + fh LoRA (29.8% vs 37.6%): the decision is right (don't ship a
  regression), but both numbers are still UNVERIFIED: no summary.json or answers for either run is committed, so
  we can't tell if 37.6% is of 240 points or of the 70 auto-scorable. Grok bot: commit the summaries.
- dcb43b3 (us, 15:26) gpu_admit frees a reservation once $WORK/<job>.log says "done (exit": OK. fh_job.py writes
  exactly that log name (setsid nohup ... > /workspace/work/<name>.log, truncated per run); reservations with no
  such log (dapt.sh's "$NAME-train") keep the old 600 s hold, which is the safe side.
- 48ad8e5 (us, 15:28) free_port per vLLM server: OK. Shared-GPU mode picks the port inside the `starting`
  lock and waits for readiness there, so two servers can't grab the same port; per-GPU mode uses disjoint ranges.
- 5448480, d988f99, 5496ee8 (us, 15:28-15:30) findings/INSIGHTS/status.py notes: OK, no secrets or IPs.
- adcf503 (us, 15:31) qwen3.5-9b Q5_K_M + mmproj = 7.50 GB: OK, under 8.0 (Q6_K + mmproj ~8.4 would not be).
- 7b369c9 (us, 15:31) claude_grade.py: Claude grades open answers of judge-less baseline runs. A research aid
  only; a closed API is fine off-stage but those grades must be labelled as Claude-graded, not CKE-official.
- 3906516 (us, 15:31) Qwen3.5-0.8B/2B/4B, Gemma-4-E2B in small_models.yaml: PROBLEM, fixed as a note. The file's
  disk_gb means Q8_0 GGUF size, but these four have no gguf and list bf16 sizes, so "smallest" isn't comparable,
  and qwen3.5-4b (9.3 GB) and gemma4-e2b (10.3 GB) are over 8.0 GB as listed. Added a comment saying so; they
  need a quantized pack before they can count for a track.
- 2ba3331 (us, 15:32) gemma4-12b-think (7.16 GB, OK) and Router.apply_model: BUG, fixed. run_exam.py (the stage
  harness) builds its backend from routes.yaml and apply_model only set vision/think_tokens, so a model's
  extra_body (enable_thinking true for gemma4-12b-think, false for the Qwen3/3.5 models) was silently dropped on
  stage: the "think" variant would run without thinking, and Qwen3.5 would think and hit max_tokens. apply_model
  now merges spec.extra_body into the backend. Per-route params are separate objects, so +think_tokens is added
  once per route (checked). Gemma thought-channel regex in strip_think: OK.
- 1162e07 (us, 15:32) train.sh MODELS_CONFIG / SCORE_MODES: OK, train_lora.py and baselines.sh both take
  --models-config.
- Status-only (us, 15:26-15:34): fa54bd1, fd242e1, d5b5c91, 3f8f30d, e363709, a9e16cc, 6b9be66, e27bd97, beb28bc,
  f1ec42a, c2c253a, 9a924a3, 571f3ba, 223a5f4: OK, no secrets.
- Board repo e65a47e (Grok bot, 15:24): headline 37.1% -> 37.6% (7B AWQ), bf16 7B and GPTQ-Int8 (8.875 GB)
  marked illegal, 3B history-v2 28.3%. Labels are right now; same caveat: 37.6% and 28.3% have no committed
  summaries, so the board should mark them unverified until they do.

## 2026-09-26 15:35 UTC: results page (3807583, b49f9b8, 1d9d6cc, 3abfebe), public board repo, cd69d79..9aaaf30

Orest (13:19 UTC): the Grok bot owns refreshing the results page; this review checks every commit to it and to
the public board repo (OrestTa/tarasiuk-lab-matura-status), and doesn't regenerate the page itself.

Numbers on results/tracks.json against committed run summaries: there are NO committed summaries yet
(no runs/ in git, no results/**/summary.json), so every row is from a chat or a note. All are marked
`verified: false` and shown as "unverified": correct. Arithmetic checks: "headline-auto" max 70 = the
auto-scorable points of the four held-out papers (17 + 18 + 18 + 17, results/eval_set_papers.md), and
26.33 / 70 = 37.6%, 26.0 / 70 = 37.1%, 18.67 / 70 = 26.7%: consistent. Contaminated/dev rows are in separate,
muted groups, never in the headline chart.

Fixed (this commit, builder code only, page not regenerated): build_tracks_page.py took `pct` from judged
summaries, which divides by scored rows only; judged rows now use `pct_all_rows` (unscored = 0).

For the Grok bot (page and board data it owns):
- tracks.json g-7b-awq, g-7b-bf16, g-3b-base: stage "base" but method "router prompts" (the note even says
  "Not the untouched base"). Stage should be "harness"; a base row must be `--mode raw`.
- Public board scores.json marks "3B base" 26.7% and "7B base" 37.1% as `honest_bare: true`, but tracks.json
  says both ran with router prompts. Not honest-bare; relabel. "7B base" is the bf16 model (15.2 GB, over the
  8.0 GB base limit) and isn't marked as over. The legal 7B AWQ row (37.6%) is missing from the board.
  "3B history-v2" says RUNNING on the board but has a finished 28.3% in tracks.json.
- All board overall_pct values are on the 70-point auto-scored subset, not the 240-point paper; say so next
  to each number, not only in the note.
- Please commit each run's summary.json under results/grok/<run>/ so rows can move to verified.
- eval_kind labels any matura_all.jsonl summary "contaminated". Since 4ea128b those summaries' top-level
  numbers are held-out only (trained papers sit under trained_on_papers), so this is conservative, not wrong.

Other commits: cd69d79 / 9aaaf30 (fetch_matura --images, pictures sent to vision models, JPEG q85): row text
unchanged (154/154), images stay in gitignored data/, no image or weight files tracked in git. OK.
98bccf5 and status commits: consistent.

## 2026-09-26 15:20 UTC: official exam harness and 999b525..afa2bd8

- 0593d6b (scripts/run_exam.py: exam.json -> answers.json): matches the guide as summarised in FINDINGS
  (the guide itself is on warsawmodeltrainers.dev, which our sandboxes can't reach): `{"exam_id", "answers":
  [{"id", "answer"}]}`, every id once in the template's order, strings only, blank on error, <=100k chars per
  answer, <=1 MiB checked, UTF-8 with ensure_ascii=False, images checked by sha256. Fixed (this commit):
  - template ids are now cast to strings too (an int id in answers-template.json produced an int in the output
    and a false "ids differ" failure);
  - `--mode raw` now refuses to run when the served model is one of our own merges (vLLM /v1/models root
    containing "dapt" or "merged"), so the bare-model submission can't silently come from a fine-tuned model.
- `--mode raw` is otherwise the untouched model: no adapter, no RAG, no template help, no voting, no
  post-processing beyond stripping <think>, one generic system prompt. Fixed (this commit): raw used the general
  route's 512-token cap for everything, so a bare-model essay could fall under the 300-word minimum and score
  0, inflating our progress number; raw now gets the largest cap any route has (2000). Note the one-line
  generic Polish system prompt is still there; if the organisers want a strictly prompt-free base run, drop it.
- 999b525 (serve_exam.sh llama.cpp path for GGUF entries): OK, syntax checks; resolves the GGUF from the HF
  cache offline and refuses without a built llama-server. PEFT adapters are ignored on llama.cpp (warned).
- e559d24 (fh_job.py NAME= as argument, seconds in default run names): OK.
- 25806aa / afa2bd8 (small-model track, cpu_serve.py, grade_batches.py): OK. grade_batches puts the CKE key
  into batch files under runs/ (gitignored), fine.
- Grok 53791b7 (notes/TRACK01_BEST_SCORE.md: Qwen2.5-7B-Instruct-AWQ 37.6% "CKE full", 5.58 GB): the size is
  legal. The score can't be checked: no answers or summary are committed, and it doesn't say which scorer or
  denominator (judge or not; pct over scored rows vs pct_all_rows). Please commit summary.json to results/grok/.
  Its "never use Bielik-11B as the Sunday base" holds only for bf16; Bielik-11B NF4 (~6.7 GB) and
  Bielik-11B-v3 AWQ (6.19 GB) are under 8.0 GB.
- Status commits: consistent.

## 2026-09-26 14:55 UTC: 00603d6..b0b9604 (size caps, new candidates, Nebius, Solari, Claude synthetic data)

Secrets scan of every added line: no keys, tokens, redeem codes, IPs or account/project IDs. The Nebius runner
(infra/nebius/nb_job.py) takes the service-account key, project ID and HF_TOKEN from the environment only, and
keeps the generated S3 key in ~/.nebius/s3.env outside the repo; FINDINGS says the Solari redeem code stays out.
notes/SIZE_CAP_8GB.md (Grok) omits access details. Tests pass (39); no conflict markers left after 68ca9fe.

- 261d0b2 / 68ca9fe / 9064c57 / d81562f (size caps from two threads at once): consistent with 53ad0d3; the bad merge
  was fixed. Removed a duplicated gemma3-12b comment in models.yaml (this commit).
- 639bdc7 (new best-score candidates): Bielik-11B v3 AWQ 6.19 GB, Gemma-4-12B QAT Q4_0 GGUF 6.98 GB, Qwen3.5-9B
  Q6_K 7.46 GB: all under 8.0 on the stated sizes. OPEN: scripts/serve_exam.sh only starts vLLM, so the two GGUF
  (llama.cpp) candidates have no on-stage harness yet, and ensure_llama_server clones and builds llama.cpp from
  GitHub, which must happen before going offline. If a GGUF model wins, serve_exam.sh needs a llama.cpp branch
  with its LoRA adapters (router adapter_mode: llamacpp).
- d8503f9 / ed6342a (pretrained Bielik-11B-v2 as the progress-track base with a plain chat template): sensible;
  the raw baseline and our SFT use the same template, so the progress number is fair.
- e1209f3 / 9c9cce0 (SINGLE_ADAPTER, EXTRA_TRAIN, TEACHER_HF=none): OK.
- 2584fed (serve_exam.sh serves pre-quantized AWQ without --quantization): OK.
- da1f57e / d6ba23f (Nebius Serverless AI Jobs runner): OK, draft; no secrets.
- 9278ea5 / faf6f32 (Solari: CPU-only credits, no runner): OK.
- b0b9604 (953 Claude-written items in train_data/claude_synth.jsonl): shapes are checked by merge_synth.py,
  closed-choice answers are balanced (A 33, B 38, C 37, D 35). 8-word overlap with the headline eval is only
  instruction boilerplate ("jest prawdziwe albo F, jeśli jest fałszywe", "Dokończ zdanie. Zaznacz…") plus one
  item quoting the Communist Manifesto, which asked for its authors, the same question and answer as eval item
  2023-05-z16.2. Removed that item (this commit, 952 left). Content-word similarity to any eval item is at most
  0.23 (boilerplate), so no other near-copies. Caveat: the writer model may know the 2023-2025 papers; the
  2026-05 paper is the cleanest check of any gain from this data.

## 2026-09-26 14:40 UTC: new size limits (base 8.0 GB, fine-tuned 8.8 GB) and 2eeda9e..a1f8ae5

Size limits corrected by Orest: base before fine-tuning <= 8.0 GB, fine-tuned model as shipped <= 8.8 GB.
Fixed (this commit): models.yaml ship_limit_gb 8.0 + finetuned_limit_gb 8.8; quantize_checkpoint.py checks the
base against 8.0 and, with --finetuned --adapters, weights + adapters against 8.8; serve_exam.sh uses the
fine-tuned check; MODELS=all skips any model whose disk_gb is over 8.0; chart line at 8.0.

Candidates against the new limits (4-bit NF4 estimates from the model shapes; measure with quantize_checkpoint):
| model | as shipped | base <= 8.0 | notes |
|---|---|---|---|
| Bielik-11B NF4 | ~6.7 GB | OK | + 7 rank-16 adapters ~0.7 GB = ~7.4 GB <= 8.8 OK |
| Bielik-11B DAPT-merged, re-quantized NF4 | ~6.7 GB | (base is the untouched Bielik) | fine-tuned total must stay <= 8.8 |
| Qwen3-8B NF4 | ~6.2 GB (yaml says 5.0) | OK | untied 151k-vocab embeddings in bf16 |
| gemma3-12b NF4 | ~8.4 GB | OVER | 262k-vocab bf16 embedding + vision tower; now skipped by MODELS=all |
| Bielik-4.5B NF4 | ~2.9 GB | OK | |
| Bielik-1.5B / Qwen3-1.7B bf16 | 3.2 / 4.1 GB | OK | |
| bielik-11b-bf16 reference | 22.4 GB | OVER | reference only |
| Grok: Qwen2.5-7B bf16 / GPTQ-Int8 / AWQ | 15.2 / 8.9 / 5.6 GB | OVER / OVER / OK | its 7B runs must ship AWQ (or 4-bit) |
| Grok: Qwen2.5-3B bf16 (registered base) | ~6.2 GB | OK | |

Other commits: 2eeda9e (release prep: brief PDF removed from HEAD, VM IP and AWS account ID redacted, SOURCES.md
and docs/PUBLIC_RELEASE.md added) OK; history still holds them, which PUBLIC_RELEASE.md should cover.
cebc119 (fineweb merge re-applies the exam/answer-key skip) OK. a79e502 (job venv on Python 3.12 via uv
for vLLM 0.27.1) OK. a1f8ae5 (Grok registers its gpu_par job in STATUS.md) OK. Status commits OK.

## 2026-09-26 13:55 UTC: GPU sharing, vLLM pin, corpus, Grok board (e5e4deb..fe8a197, 19 commits)

- 39f533f / 38df1bc (vLLM pinned to 0.27.1 in common.sh and serve_exam.sh because later releases dropped
  load-time bitsandbytes): OK. Install is under a flock so jobs sharing the venv don't race. serve_exam.sh now
  reads rag.path from routes.yaml. Not verified here that 0.28 really dropped bnb; the pin is harmless either way.
- 44fe287 / c5652b1 / 88ed0b5 (gpu_admit.py, run_baselines --gpu-budget-gb): OK. One server starts at a time,
  admitted only when both the budget and the card's real free memory fit; reservations expire after 10 min;
  failures release the budget. vLLM gets util = need / total, i.e. its own cap. Minor: a job that dies before
  allocating keeps its reservation for up to 10 min (harmless, just slower admission).
- 44187cc (bielik-11b-dapt in models.yaml): OK; skipped by MODELS=all until the path exists. Reminder: the
  DAPT-merged model is our own fine-tune, so the progress-track baseline stays the untouched Bielik-11B, and the
  shipped DAPT checkpoint must be re-quantized (bf16 merge is ~22 GB).
- e5e4deb (FineWeb2-HQ history slice for DAPT/RAG; RL sets from PolQA CC BY-SA, Global-MMLU Apache-2.0, and
  Wikipedia-generated year/order questions): licences fine, only scripts committed, 8-word overlap filter
  against question/context/gold. Fixed (this commit): the web slice now also skips exam/answer-key pages
  (cke.gov.pl, oke.*, arkusze.pl, any URL with "matur", and pages mentioning the matura together with
  klucz/odpowiedzi/rozwiązania/arkusz). Such pages paraphrase the keys, slip past an 8-word check, and DAPT on
  them would inflate our eval score. Any fineweb shards built before this commit should be rebuilt.
- Grok commits 2d66ab0 (public board) and INSIGHTS.md: no secrets or IPs. The board now marks the fh/fh-v2 7B
  MCQ scores (100% / 98.9%) as contamination risk, which is right: they are on its own training MCQs.
- Status-only commits (docs/STATUS.md): consistent with the jobs described.

## 2026-09-26 13:05 UTC: 60567a7 (public board) and Grok audit issue #6

- 60567a7 (public-board/, published to the public repo OrestTa/tarasiuk-lab-matura-status): no secrets or
  IPs. Stale: "matura_all 573 items / 860 pts" is now 512 / 789, and the 1.5B "53.3% -> 85.6%" MCQ line is on
  the Grok bot's own training MCQs too but isn't marked contaminated. Anything on that board is public.
- Issue #6 (Grok COMMIT_AUDIT) landed as notes/COMMIT_AUDIT_INSIGHTS.md with a status per item. Fixed from it:
  `MODELS=all` no longer includes the 22 GB -bf16 entry, and infra/aws/launch.sh refuses while AWS is suspended.

## 2026-09-26 12:55 UTC: RAG, past-paper training data, dashboard, corpus (3003209, f03041d, 33ae7ed, a45b915, f108e8e, ac49a23, 979e452, 52af14a, 2fedc9a, 5d680d5, 2f354f5)

Checked and fine: the held-out split holds on today's data (133 training items rebuilt identically, the closest
item shares only a CKE citation line with a held item). No exam text or secrets committed in the range
(6-word overlap against all 512 eval items: 0). FTS5 queries can't crash on quotes/AND/OR/NEAR. BM25 maths OK.
Retrieved text + longest item + 1500-token essay fits in 8192 tokens. rag.py makes no network calls.

Fixed on main (this commit):
- RAG cut every word to 6 letters, so short inflected words never matched ("unii" vs "Unia", "wojny",
  "królów", "sejmu"). Now a small Polish ending stripper runs before the 6-letter cut; the FTS query uses
  prefix match so the plwiki index (6-letter tokens) still matches. Test added.
- The knowledge block now ends with "Koniec wiedzy pomocniczej. Treść zadania i źródła:" so the model
  doesn't take Wikipedia for the task's source.
- run_baselines exits when mode rag is requested without a knowledge base (it used to report rag = routed).
- build_train_from_papers also skips every headline paper by name, not only by the ids in --eval (a
  --text-only eval file would have let 85 headline image items into training).
- SQLite URI built with Path.as_uri() (paths with ? or # broke it).
- README/dashboard: removed the localtunnel URL, its "password" IP and the VM IP. Grok bot: please don't put
  addresses, IPs or session ids in committed files.

Open:
- Grok dashboard (5d680d5) is stale and mislabelled: "Practice best 15/15" and "bare 4/15" are geography,
  "History LoRA v2 68/90" is its own easy MCQs (caveat dropped), "$200" is the Cursor budget not Forgehand
  credits, and it replaced newer job data (11:05) with an older seed (10:54) from a file not in the repo.
  It should be generated from docs/STATUS.md and committed results only.
- No job ships data/kb to the GPU box, so the queued router-ablation needs the KB built there first.
- build_train_from_papers answers: 22 of 101 open answers keep several "•" alternatives and 13 keep "/"
  alternatives (teaches listing alternatives, which examiners mark down); a few closed items have matching-style
  or keyword answers. The overlap check also drops ~39 good items over image placeholders and boilerplate.
- 2f354f5 (plwiki/speakleash corpus, DAPT): drops paragraphs sharing an 8-word run with the eval. The --merge
  output is a bf16 model (22 GB for Bielik-11B); it must be re-quantized for the exam, and the progress-track
  baseline stays the untouched base, never the DAPT model.

## 2026-09-26 12:40 UTC: exam checkpoint and voting (5aadba0, 0765f2e, 8f94c91, router/plot/train changes to b3291ae)

- 5aadba0 (bnb NF4 pre-quantized checkpoint + scripts/serve_exam.sh): OK on size. Estimated Bielik-11B NF4
  ~6.7 GB, gemma3-12b ~8.3 GB (tight), both under 8.9. Serves the local path offline; bnb LoRA loads in vLLM
  and module names match. Baselines use the same NF4 weights as shipped.
- 0765f2e (majority voting on closed types): samples really vary (T=0.7); raw stays one call. OK after fixes.

Fixed on main (this commit):
- Vote samples ran one after another (~5x latency per closed item on stage); now in parallel so vLLM batches.
- Matching answers are free text, so votes never agreed and 4 samples were wasted: votes removed from matching.
- true_false voted on whole strings (rarely a majority with 3-4 statements): now per statement.
  closed_choice counts "A, C" and "C, A" as the same answer.
- serve_exam.sh: VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1, otherwise vLLM calls stats.vllm.ai during the exam.

Open (owner: whoever drives the exam harness):
- serve_exam.sh ignores models.yaml: no `extra_body` (a Qwen3 model would think and blow the 16-token caps)
  and always `--quantization bitsandbytes` (bf16-scored small models would be served 4-bit).
- Voting also runs in routed/rag modes, so routed numbers before and after 0765f2e are not comparable and
  summary.json doesn't record votes. The router-ablation job should note this.
- gemma3-12b checkpoint lacks processor files; vLLM may fail to start offline. Run serve_exam.sh with the
  network off once per candidate and time one full exam before Sunday.
- QLoRA: adapters are trained on bf16 but served on NF4; only trust adapter scores from runs that served
  work/checkpoints/<key>.
- RoutedAnswer.raw shows the greedy text even when a sampled answer won the vote.

## 2026-09-26 12:25 UTC: trained-on papers kept out of the headline (2444ab1, 8e354ca, 4ea128b)

- 2444ab1 turns the non-headline papers (formuła 2015 May 2015-2024, the 2022 demo, the Jan 2026 mock) into
  adapter training data; the held-out headline papers are excluded by id and by a 5-word-shingle overlap check
  on question/context. OK. 8e354ca drops formuła 2015 items that repeat a formuła 2023 task. OK.
- Problem: matura_all.jsonl still contains those trained-on papers as eval rows, so after training a score on
  the full set mixes in contaminated items. Fixed in 4ea128b: evaluate.summarise computes all headline numbers
  on the four held-out May 2023-2026 papers only, and reports the rest under `trained_on_papers` with a
  "contaminated" note. A set with no held-out paper gets a `warning`.
- Rule for every agent: the headline number is always data/eval/matura.jsonl (May 2023-2026). Never quote a
  matura_all.jsonl score after any adapter training as a result.

## 2026-09-26 12:10 UTC: b914f5c, fcdb505

- b914f5c (FINDINGS: one Forgehand GPU session per team): OK.
- fcdb505 (answer-sheet template in prompts, verdict check for "Rozstrzygnij" items): OK, tests pass (31).
  Raw mode stays template-free, so the bare baseline is untouched; training uses the same build_messages, so
  train and inference prompts match. Checked verdict_matches on Tak/Nie, "Fragment 2." vs "2", "niezgodne".
  Minor: "Rozstrzygnięcie: Tak, ale nie w pełni" counts as Tak (first yes/no wins), which is what CKE does.
  Note: adapters trained before this commit saw prompts without the template line; retrain after it.

## 2026-09-26 12:00 UTC: size limit correction

Orest: the organisers accept 8.9 GB, applied to the base model before fine-tuning. Re-checked the size finding
against 8.9 GB: it still stands. As run (full HF repo + load-time bitsandbytes), Bielik-11B is 22.3 GB,
gemma-3-12b 24.4 GB, Qwen3-8B 16.4 GB and Bielik-4.5B 9.5 GB, all over 8.9 GB. Legal as run: Bielik-1.5B
(3.2 GB), Qwen3-1.7B (4.1 GB). A pre-quantized checkpoint of Bielik-11B (4-bit AWQ/GPTQ/GGUF, ~6-7 GB) fits,
and so would an 8-bit Bielik-4.5B (~4.8 GB) or Qwen2.5-7B GPTQ-Int8 (8.88 GB). PLAN's 8.9 GB cap is confirmed.

## 2026-09-26 11:50 UTC: job-status commits (a33e3f7..7a07142)

OK. docs/STATUS.md job board plus infra/jobs/status.py; fh_job.py and modal_job.py record start/finish.
Note for readers of the board: train-bielik-l40s (started ~10:55) runs the training code from BEFORE
98820c8, so its adapters use full-sequence loss and the old leak filter, and Bielik-11B is 22 GB on disk as
run (over the 8 GB limit, see above). labqoat-baselines runs without a judge, so its `pct` covers only
auto-scored rows (~60 of 154); use `pct_all_rows` from c5eefd2 on to compare with an exam score.

## 2026-09-26 11:40 UTC: data, training, infra and the Grok bot's commit (3c64d6d, 4bff7c4, 94982dc, 331a706, 73ee9c6, 43ea40f, a1c057e..2a7743c, 857369b, 1212826, eb0209d, 9081fad)

Checked and fine: fetch_matura output is byte-identical to the shared eval set; answer keys parse correctly
(points match, closed golds are among the options). No copyrighted exam text in tracked files (0 eight-word
overlaps with the eval set). No live secret anywhere in history (only a public SSH key and env-var names).
Merge 1212826 dropped nothing. Adapter names match configs/routes.yaml.

Fixed on main (this commit):
- train_lora.py trained on the whole sequence (system prompt + question), so ~98% of the gradient on a
  closed item went to memorising prompts, not answering. Now prompt/completion with completion-only loss
  (trl>=0.20).
- gen_synthetic.py leak filter pooled all eval shingles, so an eval question copied word for word with a new
  source was KEPT in 126/147 cases. Now each eval item's question/context/gold is checked on its own
  (drop at >20% of that item's 5-word runs), the synthetic answer is checked too, drops are logged, and the
  script refuses to run without the eval file and fails if under half the requested items are kept.
- train.sh: generate to a temp file (no partial file reused later), clear data/by_category before the split,
  kill vLLM's child processes, fail when no adapter was trained instead of reporting "adapters" = "routed".
- common.sh: tensor-parallel size rounded to a power of two (3 GPUs used to crash the teacher); hf_transfer
  only when installed; no silent fallback to the 20 toy questions (set ALLOW_SAMPLE_EVAL=1 to allow it).
- run_baselines.py only passes adapter dirs that contain adapter_config.json to vLLM.
- fetch_matura.py: the 2025 essay (15 pts) had an empty rubric and was silently unscored; the whole section
  now becomes the rubric. The shared data/eval/matura.jsonl needs a re-fetch to pick this up.
- .gitignore: secrets/, .env, *.env, .modal.toml, .run-venv/. README_RUN.md said TEAM_KEY in secrets/ was
  gitignored; it was not.

Open, needs an owner (LARGE):
- No held-out split: the same 154 items tune the classifier, pick adapters and report the score. Suggest
  tuning on 2023-2025 and reporting the 2026-05 paper as the test set.
- Grok bot (eb0209d): its history numbers (68/90 = 75.6%) are on its own 90 training MCQs, not the matura,
  and use different denominators. Its practice "base" run used geo_solver and one answer from
  "public_answer_consensus", so it was not a bare model. The declared base (Qwen2.5-3B-Instruct, Qwen
  Research non-commercial licence) differs from our pipeline (Bielik/Qwen3). README_RUN.md points to ~8
  files (exam client k3exam.py, geo_solver, rag/) that are not in the repo, and modal_lora_train.py can't run
  from a clean checkout (missing data file). Its training also puts loss on the whole sequence. The brief
  requires the exact stage harness in the repo: we need one offline exam client that calls matura_router.
- Not for a public repo: AWS account ID and support-case IDs (infra/aws/AWS_INFRA.md, notes/AWS_INFRA.md),
  the VM's public IP with root SSH (docs/FINDINGS.md), and "op://Hackathon/AWS root key", which means AWS
  root access keys exist: delete them.
- Cost: Modal jobs time out after 24 h and Forgehand sessions never stop by themselves; add a stop at job end.
- PLAN assumes k=5 self-consistency at
  temperature 0 (identical samples, and stage time is a few minutes).
- QLoRA: adapters are trained on the bf16 base but served on a 4-bit base; train on 4-bit to match.
- Synthetic closed items never shuffle options, so the adapter may learn "the answer is B".

## 2026-09-26 11:20 UTC: router, scoring, baselines (40155a0, 4afb7ae, 168ec23)

What they do: rule classifier routes each question to one of 7 types + general, each with its own LoRA,
prompt, token cap and answer clean-up; scoring/evaluate/run_baselines measure raw vs routed vs adapters.
Tests: 29 pass. Classifier matches the gold type on 85.7% of the 154 eval rows.

Fixed on main (this commit):
- Raw baseline used the closed types' tiny token caps (16-48 tokens), cutting off wordy base answers and
  deflating the base score, which inflates "improvement". Raw mode now uses the general route's params.
- Letter extraction upper-cased the answer, so the Polish word "a" counted as option A
  ("C – Sejm Wielki, a konkretnie…" scored 0). Now case-sensitive.
- postprocess shrank any closed-type answer to bare letters; misrouted table/justification items
  ("A – 3\nB – 2") became "A, B" and scored 0. Now only answers of 40 chars or less are rewritten.
- Qwen3 <think> blocks are stripped before post-processing and in raw mode.
- True/false and matching gave proportional partial credit; now the CKE step rule
  (3 statements/2 pts: 3 right=2, 2 right=1; 2 statements/1 pt: both or nothing).
- A single judge exception killed a whole model's run; now the row is unscored. The judge sees the
  source (first 3000 chars) and essay rubrics are no longer sent twice. Rows with only `reference` get judged.
- New summary field `pct_all_rows` = earned / points of all rows (unscored = 0), comparable to an exam score.
- PEFT backend: lock around set_adapter+generate, since the server and evaluate call it from threads.

Open, needs an owner (LARGE):
- 8 GB limit: configs/models.yaml gives vLLM full HF repos + bitsandbytes, i.e. the full bf16 weights on
  disk: Bielik-11B 22.3 GB, Qwen3-8B 16.4 GB, gemma-3-12b 24.4 GB, Bielik-4.5B 9.5 GB. Only Bielik-1.5B and
  Qwen3-1.7B (4.1 GB, not 3.4) are legal as run. The exam model must be a pre-quantized <=8 GB checkpoint
  (AWQ/GPTQ/GGUF/saved bnb-4bit) and `disk_gb` should be measured, not guessed.
- Classifier: "A. …\nB. …" layout and the word "chronologicznie" push table-filling and "rozstrzygnij" items
  into closed types (2023-05-z2.2, 2025-05-z4, 2024-05-z7). Suggest requiring "zaznacz"/"dokończ zdanie" too.
- Matching prompt asks for "1 – B" but all 4 real matching items want names ("A – Karol IX"). Prompt should
  ask for "A – <answer>" with the item's own labels.
- Keyword scoring is raw substring: "Engels lub Marks lub Lenin" gets full credit, "konsul" matches
  "prokonsul", and inflected forms ("trybunem ludowym") miss. Multi-part "1. B\n2. C" answers score 0.
- server.py: OpenAI "content parts" lists cause a 500, and the caller's system message is dropped.
- Exam machine must run with HF_HUB_OFFLINE=1 and local paths (peft_local/vLLM otherwise contact the Hub).

## 2026-09-26 11:00 UTC: first pass, commits 33ef5cf..9081fad (24 commits)

- SOURCE.md: OK. Matches the brief's required line exactly (en dash in 25–27).
- 58d5dce docs/hackathon-brief.pdf: PROBLEM (owner: Orest). Page 9 has the venue door code, and the PDF is
  organiser material that should not be republished. Deleting it from HEAD is not enough: it stays in git
  history. Before the repo is shared with the jury, either keep the repo private and give the jury read access,
  or publish a fresh repo/squashed history without the PDF.
