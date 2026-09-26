# Hackathon assessment, 26 September 2026

## Update: newer public dashboard supersedes the initial readiness assessment

After the initial assessment, the user supplied
[Tarasiuk Lab's status dashboard](https://orestta.github.io/tarasiuk-lab-matura-status/).
Its displayed update time is **2026-09-26 19:08 CEST**. All three track tabs were
inspected in the browser. It contains substantial newer results absent from the
local checkout. The original assessment below is retained as a dated audit of
that checkout; its claims about missing history progress are superseded by this
update. These are dashboard-reported results, not independently replayed runs or
official Sunday grades. Linked artifact paths were not recovered in this check.

| Track | New evidence reported by dashboard | Revised priority |
|---|---|---|
| Highest score | Gemma 4 12B QAT GGUF + projector, measured pack 7.16 GB; Claude 41/60 = 68.3% on May 2023 CKE. Six of 37 answers were empty due to a reportedly fixed thinking-mode bug. | First priority: reuse this existing package and verify the fix; do not replace it with the merely proposed Bartowski package without a reason. |
| Smallest passing | Bielik-4.5B FP8, approximately 4.898 GB; same mock answers graded Claude 24/60, Grok 28/60, Sol 29/60 (40.0%, 46.7%, 48.3%). | Strong second priority: preserve this passing mock configuration, then test more compact quantization on identical inputs. |
| Best progress | Pretrained Bielik-11B-v2 NF4, approximately 6.66 GB; Claude bare score 12/60 = 20.0%. No completed comparable tuned mock score shown. | Third by demonstrated readiness, with possible upside. Need an actual paired improvement before expanding training. |

The dashboard distinguishes Gemma's May 2023 CKE run from the standing
`history-2023-mock-v1` gauge. Do not directly subtract or rank percentages as if
the model inputs and grading protocols were identical. Run the same frozen
mock/input pack across finalists and reserve another year as holdout.

Specific implications:

- The work is substantially further along than the initial checkout suggested:
  actual history answer sets, multiple judges, image input, measured quantized
  packages and additional 2024–2026 source packs are now reported. The dashboard
  explicitly flags contaminated MCQ scores and demotes partial auto-scoring.
- **Gemma's six empty answers are the first repair to verify.** Re-run the frozen
  benchmark after checking the inference fix, report old/new complete answer
  sets, then test an untouched year. Six missing answers do not translate to a
  predictable point gain; their point weights and answer quality matter.
- Bielik's conservative 24/60 is only **three points above** the 21/60 passing
  threshold. Quantization experiments should preserve that fallback and assess
  per-item regressions and another paper, not just minimum file size.
- Qwen2.5-0.5B and 1.5B now have reported full mock scores of 3/60 and 4/60.
  Deprioritize further sweeps of those configurations. This is evidence against
  those tested setups, not proof that every sub-2B model/harness must fail.
- **Judge disagreement is not progress.** The board shows +6.7/+8.3 next to
  Grok/Sol Bielik grades and +15 next to Grok's AWQ grade, but these are differences
  on the same answers. AWQ receives 11/60 versus 20/60 across judges: a nine-point
  discrepancy. Resolve rubric disagreements per item before ranking close runs.
- The old 3B Modal adapter and 7B Forgehand adapter regress on the partial proxy
  (26.7→17.1 and 37.6→29.8). Do not promote them based on training-set MCQ gains.
- Progress's bare output reportedly has run-on chat/LaTeX in about 12/37 answers
  and a 234-word essay. Audit the base model's prompt format, stop conditions,
  generation budget and any answer cleaning. Preserve a fair untouched baseline;
  a decoding/configuration defect must not artificially inflate claimed gain.
- The dashboard says 8.0 GB base / 8.8 GB after fine-tuning, while the PDF excludes
  LoRA and older repo notes mention 8.9 GB. Its listed finalist packages are below
  8 GB anyway. Treat the newer rule wording and per-track registration claims as
  reports until reconciled with current organiser instructions.
- Dashboard text describing DAPT and job ownership was read as status, not as
  authorization to start/stop jobs or communicate with other bots. No cloud or
  dashboard state was changed by this follow-up.

**Revised recommendation:** consolidate the existing Gemma 7.16 GB package for
maximum score; preserve and carefully compress Bielik-4.5 FP8 for size; obtain
one properly controlled tuned NF4 result for progress. Synchronize newer source
and artifacts before applying the earlier checkout's code findings to current
cloud code, since some may already have been fixed remotely.

## Original checkout assessment

Assessment at approximately 19:55 Europe/Warsaw. Local code reviewed at
`7a687ad44f1eaea0b3ce8ab2b7f2e5810d95ebff`. Three sub-agents audited evaluation,
cloud state, and track strategy. No new training or official submission was run.

## Decision

The current work is a useful prototype, but there is no independently verified
held-out final-history result establishing prize readiness. The next investment
should be a trustworthy full-paper evaluation and an image-capable baseline,
not additional epochs on the same 90 MCQs.

The user explicitly confirmed **history** during this assessment. The linked
slides describe history as a case study separate from a geography final; this
discrepancy was raised and resolved for planning by that clarification.

Run two experimental configurations: a strong multimodal model for maximum
score, and a small model with the same useful offline harness components for
progress and size. These are experiments, not an assumption that the organisers
allow separate prize submissions. The PDF specifies one team submission and
uses the strongest individual bare model as an ensemble's progress baseline.
Adding a larger model can therefore reduce improvement-track competitiveness.
Clarify how independently frozen variants and ensemble size are judged before
choosing the final submission.

## Current state: what the evidence supports

| Component | Assessment |
|---|---|
| Router, prompts, fallback, training scripts | Real reusable implementation, not merely a plan. Keep it, but demand measured gains from routing/adapters. |
| Geography practice 15/15 | Reported in STATUS; includes public-answer consensus on one item. Not a history generalization result. Live rank was not verified. |
| Filed practice base 14/15 | Notes explicitly say it used the harness. Cannot serve as an untouched-model comparison. |
| Bare 3B 4/15 and 1.5B 3/15 | Reported local geography results; underlying per-item artifacts were not recovered in this assessment. |
| History LoRA 68/90 | Same 90-item set used for training and evaluation. Training-set accuracy, not evidence of unseen-exam improvement. |
| Small-model 48/90 | Easy local factoids, not a demonstrated 35% official-history pass. |
| Modal adapters | Completion claimed in notes. Current visible Modal app list was empty; this does not establish whether stored adapters exist. |
| Full history evaluation | Parser/evaluator exists, but scorer defects and incomplete grading undermine current selection metrics. |
| Exam integration | Several referenced Grok harness/client files and run artifacts are absent from this checkout; integration is not reproducible here yet. |

Grokbot's reported work appears strongest in practice-specific tools and rapid
small-model experiments. Claude's contribution provides broader routing,
evaluation and compute infrastructure. Their integration is incomplete: model
identities, artifact locations, status files and assumptions differ. Recovering
one reproducible end-to-end candidate is more valuable than another architecture.

## Track priorities

| Track | Recommended route | Main uncertainty |
|---|---|---|
| Highest score | First test a modern multimodal checkpoint with actual page images, source grounding and appropriate answer length. | Quantized accuracy, latency and runtime compatibility have not been measured. |
| Best progress | Small, genuinely untouched baseline versus the same model with local history RAG, source-grounded prompts and selective SFT. | Need an honest paired held-out gain; a stronger ensemble member raises the baseline. |
| Smallest passing model | Establish a reliable full-paper pass, then reduce serialized size. Begin with existing 1.5B/3B artifacts and benchmark-informed small alternatives. | No current small configuration has demonstrated the full-history threshold. Smallest-model accounting for ensembles is unspecified. |

This is a ranking of promising experiments, not estimated winning probabilities.
Competitors' final results and valid final-format scores are unknown. Progress
and size share useful work, while the larger candidate protects the absolute
score objective. Do not select a deliberately impaired baseline to enlarge gain.

## Shortlist supported by the supplied benchmark

The linked deck's slides 20–23 report these AI-graded history results. They are
different setups, not a controlled model-size experiment or our own scores.

| Candidate | External benchmark | Concrete artifact to test |
|---|---|---|
| Gemma 4 12B IT | 46/60 = 76.7%, original page images | Bartowski Q4_K_M 7.66 GB + F16 projector 0.122 GB, approximately 7.782 GB. Exclude optional MTP weights. |
| Qwen3.5 9B | 36/60 = 60.0%, original page images | Unsloth Q5_K_M 6.58 GB + F16 projector 0.918 GB, approximately 7.498 GB. Q4_K_M plus projector is approximately 6.598 GB. |
| Bielik 1.5B / Qwen3 1.7B | 27.3% / 23.6%, adapted text /55 | Small-model challengers; need harness gains and actual quantized-package evaluation. |
| Bielik 4.5B / Qwen3 4B Instruct 2507 | 41.8% / 40.0%, adapted text /55 | Passing-baseline hypotheses after quantization, not proven full-exam passes. |

Artifact sizes are rounded file-list figures checked during the assessment, not
downloaded byte manifests. Include the projector and all required model tensors;
retest accuracy after quantization. The 76.7% and 60.0% scores are **not** scores
for these specific GGUF packages. Test the exact runtime before committing to
either, and retain an existing working model as fallback. Do not download every
quantization in the repositories.

Sources:
- [Supplied benchmark deck](https://docs.google.com/presentation/d/1iGH2E6JURWe0Nq0Qqf0_nHoSA7s0LKaj5WSN6BpS3uI/htmlpresent), inspected through the browser, including speaker notes.
- [Gemma quantization publisher files](https://huggingface.co/bartowski/gemma-4-12B-it-GGUF/tree/main)
- [Qwen quantization publisher files](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/tree/main)
- [Gemma publisher](https://huggingface.co/google/gemma-4-12B-it)
- [Qwen publisher](https://huggingface.co/Qwen/Qwen3.5-9B)
- `docs/hackathon-brief.pdf`, especially pages 19–23 and 27.

## Findings that change decisions

1. **Matching scorer gives correct answers zero.** `scoring.py:114–120` treats
   `reference` as closed-format `gold` before considering `gold_keywords`.
   `fetch_matura.py:401–406` emits those fields for unsupported letter-keyed
   matching. A reproduction using the actual functions scored the exact correct
   answer `Fragment A – Karol IX / Fragment B – Ludwik XIV` as 0/2. Fix with
   label-aware matching; unordered keyword presence alone accepts swapped pairs.
2. **Incomplete grading can look like passing.** `evaluate.py:67–93` computes
   `pct` over scored rows only; `plot_baselines.py:62–81` plots it against 35% as
   a matura score. Ungraded essays/open answers vanish from the denominator.
   Report grading coverage and full available points. `pct_all_rows` is only a
   lower bound while answers remain ungraded, not a finished official score.
3. **Judge parsing is not strict.** `scoring.py:139` accepts `-1` and `1.5` as
   one point. Both were reproduced. Require a complete valid integer response.
4. **The model catalog confuses runtime quantization with disk packaging.**
   `configs/models.yaml` assigns estimated compact sizes to original checkpoint
   IDs loaded through bitsandbytes. Export/select a real quantized checkpoint
   and measure it; estimated GPU footprint is not proof of size eligibility.
5. **Images and open answers dominate the useful work.** Repo findings report
   85/154 items flagged image-dependent, 52 verdict-plus-justification items,
   and essays worth 60/240 points. These counts were not regenerated here.
   The current server/router is text-oriented; a model swap alone does not add
   image transport. Preserve source images and shared source packets throughout.
6. **Training recipe is narrow.** `harness/modal_lora_train.py:137–146` truncates
   chats at 512 tokens and supervises prompt tokens as well as answers. Check
   answer retention and use assistant-only loss for subsequent targeted SFT.
7. **Cloud packaging could include credentials.** The Modal checkout uploader
   omitted supplied credential filenames and local secret paths from exclusions.
   This assessment added explicit exclusions and a gitignore pattern. No evidence
   of a previous upload was established; no job was launched.

These scorer/training findings are recorded, not fixed by this assessment.
Full pytest could not run because local Python lacks pytest/PyYAML. The scoring
reproductions used actual implementations via standard-library loading.

## Cloud status and execution plan

Live checks around 17:49 UTC found one running Forgehand L40S 48 GB session at
$1.861/hour, with approximately $9.33 accrued and idle termination disabled.
Its address differs from repo notes. Authenticated Jupyter responded and two
existing terminals had recent activity. SSH reset and Contents API returned
404, so no current training process, checkpoint, or held-out score was verified.
No existing terminal or job was changed. Modal listed no apps in the configured
environment. AWS suspension/zero-quota information remains a repo report,
not a fresh live check. AWS's default termination deadline also precedes the
stated Sunday exam opening by half an hour; do not use it unchanged.

Recommended sequence for the remaining evening and morning:

1. **Recover visibility and artifacts.** Identify the active operator/job on the
   L40S; retrieve the actual harness, model revisions, adapters, data manifests,
   run commands and per-item answers. Preserve existing training. Use one GPU
   job owner and unique output paths. Avoid launching from stale status tables.
2. **Repair evaluation before choosing winners.** Fix matching/judge parsing;
   choose a complete held-out history paper and audit source extraction. Keep
   train, development and final holdout separate, including quantization data.
   Compare identical inputs and record all missing/error/ungraded points.
3. **Run a short multimodal feasibility check.** Load Gemma Q4 and test a map,
   a source-grounded short answer, and an essay. If unsupported or too slow,
   try Qwen Q5. Then run a complete timed paper on the successful candidate.
4. **Run the small-model paired comparison.** Bare → grounded prompts → local
   retrieval → existing adapter. Keep only components that improve held-out
   score. Use matching source inputs and adequate output budgets for the bare
   baseline; no tools, few-shot examples, or tuned prompts in that baseline.
5. **Target the largest errors.** Prioritize verdict plus evidence, extraction
   from images/tables, and essay completeness. Train one useful adapter only
   after the paired evaluation justifies it. Defer DAPT, GRPO, seven experts,
   chronology-specific training, and further geography practice retries.
6. **Freeze and rehearse before Sunday 11:00 Warsaw.** Save exact byte counts,
   hashes, configs and answers; pre-download assets; run with inference/retrieval
   network access disabled while retaining the separate official submission
   transport. Time the whole exam. Confirm judge repo access and keep SOURCE.md.

For the small track, aim for a margin above 35% on an untouched full paper
before shrinking further; a single barely-passing score is fragile. Do not
repeatedly select models against the final holdout. Obtain the organiser's
current submission format and size-track variant policy before final selection.

## Changes made during this assessment

Added this report and the previously missing `AGENTS.md` / `.Codex/rules/`
guidance. Added credential-file gitignore and Modal upload exclusions. No commits,
pushes, registrations, official submissions, model downloads or paid compute
launches were made. The user's existing `notes/COMMIT_AUDIT.md` was left intact.
