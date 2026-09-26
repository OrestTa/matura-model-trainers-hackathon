# Commit review log

Adversarial review of every commit on main (Claude review thread, for all agents incl. the Grok bot).
Newest first, dated. Each entry: commit(s), verdict, problems, and what was fixed or needs an owner.
Rules we review against (from docs/hackathon-brief.pdf): the base model before fine-tuning <= 8.0 GB on disk, the
fine-tuned model as shipped (weights + adapters) <= 8.8 GB (Orest, 2026-09-26 12:29 UTC; replaces the 8.9 GB note),
no internet/closed APIs at exam time, no copyrighted content in the repo (sources + fetch script instead),
SOURCE.md with the exact required line, graded work made from Fri 18:00.

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
