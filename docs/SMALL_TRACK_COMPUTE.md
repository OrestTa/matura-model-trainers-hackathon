# Small-track compute — 2026-09-26

## Serving integrity correction — 20:53 UTC

The three-adapter Bielik pilot's server log warns that repeated `--lora` arguments
use only the last value. Its request adapter IDs therefore do not establish that
all three intended specialists were actually served. Preserve its answers and
grades as diagnostic evidence; withdraw specialist-specific improvement claims.
The trained adapter files themselves are unaffected. The corrected launcher uses
one comma-separated adapter argument and fails before inference unless the live
`/lora-adapters` response matches every declared adapter ID and path. A new full
run with this verification is required before reporting specialist performance.

Live verified Modal orestta Starter credits: USD25.58, no live apps before this wave. Forgehand rst USD13.67 of USD200 compute allowance, but GPU concurrency1/1 occupied; no existing process changed. Forgehand teacher credit USD49.539 available, reserved0; separate from compute.

Own checkout: /Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon. No fetch/push.

First isolated Modal app: ap-jAxNYojVylFKJGkpAcFXzj. Three L4 workers,2CPU,8GiB,1800second timeout,no retries,maxcontainers3. Unit price L4 USD0.80/h CPU USD0.0473/core/h RAM USD0.008/GiB/h; maximum three half-hour workers USD1.4379 before build/storage. First-wave budget USD6; aggregate new compute budget USD20, preserving credit margin.

Inputs:2023May candidate37items60points only; no keys or credentials uploaded. Text-only baseline deliberately marks visual omissions; it does not establish final full-modality passing performance. Configurations:Bielik1.5Q4_K_M,Bielik4.5Q3_K_M,Bielik4.5Q4_K_M. HuggingFace revisions resolved at execution; serialized bytes measured, modelserver logs and JSONL answers persisted to private volume matura-small-independent every10items.

Inference server bound127.0.0.1,no public endpoint. Local runner returns results/small_track/<run_id>/answers.jsonl and manifest.json. Each call auto-stops on completion; function timeout bounds runaway inference.

First wave completed111/111 nonempty answers,37each. Measured weights: Bielik1.5Q4 972797408bytes; Bielik4.5Q3 2303443968bytes; Bielik4.5Q4 2878886912bytes. Runtime incldownload37.8/63.5/79.8seconds. Files results/small_track/20260926-180529-*/. Modelserver image im-tyhSU7YoRCMJXQkdx4RoGx; no independent grades yet.

Secondwave launched app ap-C1wv6ZcFdDunFUse1fjIkc, same3models on11packs2017–2025,393items580points. Parent later clarified2026 may be included as development (alreadyused); it was not in this submittedwave and can follow separately. Dataset file data/small_track/development_2017_2025_candidate.jsonl. Same1800second timeout,3worker maximum. Main can monitor execsession81589; subsequent outputs returnlocal automatically.

CORRECTION: the first second-wave glob accidentally included2015/2016 because it excluded2026 without lower-bound filtering. Root caught the393/580denominator. App ap-C1wv6ZcFdDunFUse1fjIkc was immediately stopped and its partial answers NEVERread,graded,orselected. It is quarantined inferenceonly,nottraining. Sourceaggregate development_2017_2025_candidate.jsonl is INVALID and must notbeused.

REPLACEMENT app ap-i4i5QsGX4Qv18S7NrTN4bU uses row.year bounds2017<=year<=2026,VERIFIED369items540points,exactly10years. Candidate development_2017_2026_candidate.jsonl. Main monitor execsession13629.

## 18:20 UTC update
Correct ten-year wave completed and auto-stopped. Run prefix20260926-180857: Bielik1.5Q4 produced368/369 non-whitespace answers (2017-05-z26 whitespace-only,length stop),4.5Q4 369/369. Q3 server deliberately stopped after Astra graded initial paper4/60; ten-year Q3 270answers+99errors is diagnosticonly,notcomparable. No sharedproviderprocess altered.

Precision control completed: prefix20260926-181527,1.5Q8 37/37,1699568096bytes,9482completiontokens,44.8seconds;4.5Q5 37/37,3378598912bytes,11461completiontokens,90.6seconds. These elapsedtimes include startup/download; they are not pure decode rates. Eight slots/8192context each; privateHFcache; per5second GPUutilCSV and serverprops persisted. Both apps auto-stopped. All scoring requires paired Astra+Sol per updated user instruction.

Last direct utilization snapshot18:17:13UTC Q4 96%,4974MiB,71.29W,329/369finished. Earlier snapshots1.5Q4 83%,Q4 95%,Q3 95%; these precede Q3 stop. Latest billing18:17 metered4.55953656USD,billed0,creditsapplied4.49; billing may lag and does not establish instantaneous finalcost.

Training image built; infra/small_track/modal_train.py supports 1H100/1200seconds/privatepersistentvolume,periodiccommit10seconds. No trainingallocatedyet. OfficialBielik repositories gated; no existingHFtoken inenv,cachedlocation,suppliedsecrets,orModal. PublicfullprecisionGGUF import option prepared with synthetic-only validation; treat this as distinct sourceartifact from existingQ4baseline. No ForgehandGPUuse permitted. ForgehandLLM teacher remains separate.

## First paired prompt trial and SFT launch
Optimized1.5Q4 run20260926-182056 returned37/37 in27.2seconds. Astra graded16/60 versus baseline20/60 (Sol stillrequired). Reject promptchanges pending pairedjudges. Inputaudit exacthashproof: removingnewneeds_image metadata reproduces baselineSHA7dc639ff...; promptmaterialsunchanged. See input_pair_audit.json besideoptimizedanswers.

SFTsnapshot25acceptedpapers359textrows,80steps,f16GGUF1.5publicsource. Initialappfailedimport-pathbeforetraining; fixedlocalmountguard. Nextapp importedGGUFsuccessfully butfailedstep0gradients withfrozenembeddings; enable_input_require_grads fix thenrelaunched appap-6bwgcc7Ri9QraU0Ly5cUab,run20260926-182506-Bielik-1.5B-v3.0-Instruct-GGUF. Earlierfailedappsauto-stopped,notrunning. CurrentHFcacheprivatevolume; trainingcheckpointsandmergedexportpersistent. PairedHFbefore/afterevaluationfunctionprepared; no improvementclaimbeforeactualscoring.

## CURRENT 18:42 UTC — supersedes earlier snapshots
- SFT80steps completed, but pairedHFimport base isgarbled andadapterwhitespace: bothDIAGNOSTICFAILURE,neverdeploy.
- NativeF16GGUFsmoke3/3coherent;sourceweightsvalid,TransformersGGUFimport/tokenizerdefective.
- HF4.56.2 EOS/BOSmappingbugandtokenizationdifferenceconfirmed; trainexpansionpauseduntilfixed.
- Canonical37/60fourrunsDONE:20260926-183916-{bielik15,bielik45}-q4-canonical-b0;20260926-183920-{bielik15,bielik45}-q4-canonical-v1.
- V1ownQwen3.5-2Bcaptioning19/19DONE;visionweights1280835840+projector668227264=1949063104bytes.
- V1captionsresults:20260926-183536-qwen35-2b-vision-captions.
- DirectQwenvisionbaselineD0 appap-8G0hAlMWzrAUINqwnbrfEt currentlyrunning;same19images+canonical37questions.
- LatestverifiedcreditsUI24.51USD at~18:34UTC;billinglags. Oursremainingauthorizedallocation20USD minusourconsumption.
- NEWunownedModalapp claude-matura-gemma ap-YUMxGi4H8zInA3iY8jF4gN exists;do nottouchandreserve sharedcreditmargin.
- User50percentincrease uses stable4workerbaseline,target6usefulworkers;futureModal4routeisolations+Nebius2ownedworkers.
- Nebiuslivequota/balance/isolatedlaunchdelegatedsynthetic_sftagent,NO confirmedNebiuslaunchyet.
- Harddeadline20:33UTC;portableartifactfreeze20:25UTC.

18:44UTC: P2essay-only bothfavoritesDONEprefix20260926-184214;P3closed-format-only bothDONEprefix20260926-184218;all37/37. D0directvisionDONEprefix20260926-184028. NoownedGPUjobsleftactiveafterthesecompletions; Nebiuspendingexternalagent. Alloutputsreadygrading,donotmanufactureworkjusttofillquota. Canonicalpromptinputaudit proves addedsubtypemetadata only versusB0.


## 18:48 UTC — route matrix completed
All 20 distinct trials completed in Modal app ap-ohtNo8N4XDlTHXqLqh2g5Q, prefix 20260926-184624. Matrix: Bielik 1.5B/4.5B Q4 × five routes × concise or review technique. Only target-route answers were generated (148 target answers total); unchanged answers were reused from immutable canonical B0 and explicitly labeled composed. Seed 42, eight server slots, 8192 context per slot, 500 short/1600 essay output tokens per pass; review uses two passes. Every worker had a 300-second cap. Last observed concurrency was four L4 containers; 20 submitted trials does not mean 20 simultaneous GPUs. App auto-stopped after persistence. First allocation cap about $1.60; latest observed credit balance remains $24.51 at ~18:34 UTC and may lag. Astra and independent Sol evaluation pending. No trained adapter is usable: HF import baseline and adapter remain diagnostic failures. Direct Qwen vision and canonical B0/V1 outputs are complete. Nebius deployment remains delegated to synthetic_sft; no Nebius mutations from this worker.


## 18:52 UTC — crash-loop diagnosis (read-only)
All our apps are stopped, latest matrix exited normally at 18:48:07 UTC and stopped at 18:48:09. No live containers at inspection. The other agent's claude-matura-gemma app ap-YUMxGi4H8zInA3iY8jF4gN is ephemeral with zero tasks, but its logs explicitly report crash-looping at 18:47:03 UTC after 13 observed startup failures. Cause: /root/claude_gemma.py line24 computes Path(__file__).resolve().parents[2] on a shallow remote mount, raising IndexError(2) during module import. No change or stop was made to that app. Owner should guard local mount/repository discovery with modal.is_local().
User confirmed a shared ten-GPU Modal limit. Future owned concurrency must subtract other active GPUs, preserving a one-GPU buffer when ownership/count is uncertain; twenty experiments may queue but do not authorize twenty simultaneous GPUs.


## Wrap-up: user stopped experiments
Live verified zero owned Modal active apps and zero owned GPU containers. All 20 historical owned apps stopped. The other-agent matura-jobs app ap-EKp4FgCN6FoPyW9PcSLbFz is untouched. No more experiments will launch. Local outputs indexed in results/small_track/compute_artifact_index.json; weight checksums and exact bytes in artifact_manifest.json. Private Modal volumes preserve cache, logs and diagnostic checkpoints; these can incur storage charges despite zero GPU compute. No provider account-wide changes were made.


## Resumed at user clarification, 19:10 UTC
User explicitly resumed experiments toward a complete >=35% score; sole grading authority is now Forgehand gpt-6-sol. Modal verified remaining credits $23.44 at ~19:05 UTC. Four other-agent containers observed; our fleet capped at two, then one. Essay rescue1.5Q4/Q8 completed (prefix190623), sole Sol awarded both essays0; no further blind1.5prompt trials. Full frozen five-route E2E prefix190831 bothfavorites completed37/37. Current4.5 single-topic2 full37 run appap-NR8NIWs38iMqnAZngz5aUQ uses1L4/300seconds, projects only candidate-provided topic2 to prevent multi-topic essays. Closed-image concise route retained. Executable configs under infra/small_track/configs pin weights/revision/actualSHA; text-only image ablation clearly labeled. Composed4.5development candidate is not pass evidence until sole-Sol uncertainties resolve.

19:12UTC: Full fresh4.5 single-topic2 run20260926-191017-bielik45-single-topic2-e2e completed37/37 in48.97seconds,8543completiontokens. No composition. App auto-stopped. Sole-Sol grading requested; no pass claim until complete. Config+README runnable, artifact2,878,886,912bytes pinned.


## 19:22 UTC — offline OCR, trained routing, paired voting complete
Source-disjoint trained multinomialNB router uses only candidate features and weak task-type labels from2017–22/2025, with2026validation. Official2023/2024 excluded. Validation87.18% is agreement with weak labels, not human/official accuracy. Artifact2,164,004bytes. Earlier synthetic-router artifact is diagnostic and source-overlaps2017–26; not used in these runs.
Offline Tesseract pol+eng processed19/19images,6584characters. OS-level socket denial smoke passed. OCR learneddata8,878,606bytes; original37question/source/imagefields independently verified unchanged except appendedcontext+ocr_refs.
Two L4 runs completed: plain20260926-191729-bielik45-fixed-input-e2e (131.47s,25326all-sampletokens), OCR20260926-191816-bielik45-fixed-input-e2e (171.45s,30187tokens). Both37/37zeroerrors, samples seeds42/43/44,temp0.7; each has paired first-sample/answers.jsonl. Fulloriginalessay alternatives preserved, projection disabled. Only1/37lexicalmajority each;36fallbacks. Plainselectedanswers identical tosample1, no votinggain. SoleSol plainprovisional15/60 with unresolveditems8/17; notpass. OCRgradingpending.
Total unique model+router+OCR artifact bytes2,889,929,522. Allownedworkersauto-stopped. Forty tests passed. Harness options --router-model,--ocr,--vote-samples,--offline independent. Offline HTTPclient disables proxies and redirects; onlyloopbackendpoint accepted. OCRchildnetwork isolation is OS-enforced; do not conflate with platformwideairgap.

19:28UTC: Scopeexpandedto4Bvision; Qwen3.5-4B Q4+F16projector3,413,361,504bytes CPUpreloaded/actualSHAverified. Appap-zxuGDUIK3A2OkgJmegaZMK,run20260926-192720-qwen35-4b-vision-offline-b0,oneL4/900s,networkblocked+probe,original19PNGbytes unchanged.11/37answersdurable,zeroerrors atcheck.8BbranchcanceledbeforeGPU;cacheonlydownloadedbeforecancel,noresult. Actualotherfivecontainerscheckedvianvidia-smieachoneH100;old4xL40Sdashboardreferreddifferentoldapps. LatestmyfreshcreditsUI18.04USD19:25;accountsharedconsumptioncontinues.

19:33UTC: Visionbaseline recovered37/37zeroerrors112.78seconds. SoleSolsettledlowerbound23/60(38.33%),task8uncertain0–2;exactscore23–25unresolved butthresholdlowerboundclears35. Five0/4,6/7,9/11,8/23lowerbound,0/15. OriginalPNGmodel+projector3,413,361,504bytes. AllownGPUstopped. NetworkblockedSDKlargereturnfailedAFTERdurableoutputcommit; explicitfiledownloadsrecoveredalloutputs, futureworkerreturnsmetadataonly. Exactofficialformatvalidated. NativeQwenSFTpreflightdocumented,nopilotlaunchedyet.

19:35UTC: Passingvision compressionQ3 and cross-paperQ4validation launched inparallel. Q3run20260926-193419-qwen35-4b-vision-q3-offline-b0 appap-SAOIkQ7zGt9lDnB6lhMoRE,exact2023canonical37sameprompt/PNG/seed. Q4run20260926-193505-qwen35-4b-vision-2024-05-offline-b0 appap-eEXdydpsGUSJ529faJInUX,2024full40tasks60points,originalfull-pagePNGrepresentation(max2pages/task,3159textchars),notidentical2023cropformat. Bothmax1L4percall900s,networkblocked,CPUpreloaded,per-itemdurablecommit. NativeQwenTEXTSFTpilotdeferrednotcompleted.

19:38UTC: Bothvalidationjobscompleteandstopped:Q3same2023paper37/37zeroerrors;Q4full2024paper40/40zeroerrors149.14seconds. Solgradingqueued. Q3/Q4all37requesthashesidentical, quantizationonlychanged; pair_input_audit.json recordsproof. SmallerweightSHAmeasuredandartifactmanifestupdated. No additionalGPUallocationwhilegrading.

## 2026-09-26 19:52 UTC — Q3 vision plus OCR ablation

Fresh Modal credits $9.99 at approximately 19:50 UTC. Five other containers were individually verified as one H100 each; the new owned full run uses one L4, within the shared ten-GPU cap.

Five-category smoke `20260926-195050-qwen35-4b-vision-q3-smoke-ocr-offline-b0` completed: five nonempty answers, no errors, 29.67 seconds, network-denial probe passed. Smoke is not a full-paper score. Full paired run app `ap-222RjV49o5kKscxFoWErRh` is active with 900-second timeout and per-answer volume commits.

The original 37 question/source/image fields and context prefixes were checked unchanged. Existing locally generated OCR is appended; no router, majority vote or prompt changes. Aggregate deployed weights are 2,974,690,670 bytes including Q3 answering weights, shared vision projector and both Tesseract language weights. Current primary Luna grades have not yet established the target; historical Sol marks retain their provenance.

Full Q3 OCR run `20260926-195215-qwen35-4b-vision-q3-ocr-offline-b0` completed in 109.97 seconds: all 37 answers nonempty, zero errors, organizer JSON validated. Answers, manifest and logs persisted both on Modal volume and locally; paired input audit saved. App stopped and zero owned GPU containers verified at approximately 19:55 UTC. Luna evaluation requested; no OCR benefit claimed before paired marks arrive.

## 2026-09-26 20:13 UTC — native specialist compatibility

Native Qwen3.5-4B revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` loaded with Transformers 5.17.0, PEFT 0.21.0, Torch 2.8.0, Pillow 12.3.0 and torchvision 0.23.0. An initial missing vision dependency failed before training; the fixed retry completed two finite assistant-only updates, losses 0.595 and 0.375. These are smoke losses, not evaluation evidence.

Run `20260926-201020-qwen35-route-adapter-smoke` converted a rank-8 language-MLP-only adapter using upstream llama.cpp revision `694ec235484b3b0bf827ab7992a512d285f0e66b`: 18,101,920 bytes, SHA256 `53d3e768746f99b8309ffa6e54bc1893dfdc31bb139f140fbb9087583082473d`. The adapter loaded on the existing Q3_K_M model plus projector in an offline L4 worker and produced a coherent final-answer sanity response. Hybrid-attention LoRA targets remain untested; the successful smoke deliberately uses only language MLP gate/up/down projections.

Five route pilots are implemented but await completed actual OCR for the synthetic image inputs. Native Transformers uses slower reference hybrid kernels; the bounded pilots do not claim optimized training throughput. Fresh Modal credits $4.46; five other H100s verified and no owned GPUs after smoke completion.

## 2026-09-26 20:24 UTC — Bielik priority and real-only training

User redirected specialists to Bielik1.5 and forbade further synthetic fine-tuning. The completed Qwen pilot `20260926-201539-qwen35-five-route-pilot` contains five separately trained eight-step adapters (90,509,600 total bytes), preserved as historical experiments; no combined Qwen inference was launched.

Official native Bielik access returned authenticated403 for weights/config/tokenizer. Public Apache-2.0 mirror `cpral/Bielik-1.5B-v3.0-Instruct-ungated`, revision `a3a660b10fdba3a7b03c3349567e54d8875f9ac9`, exposes matching config/tokenizer/model LFS pointer Git blob IDs. Downloaded native weights are 3,193,073,112 bytes, SHA256 `3c337d1d0d3f8cafb27f617b97a9a0cf70a2067648cb3946311e2fe370c28978`. This is a native checkpoint, not the failed GGUF import.

Generation-only offline preflight `20260926-202110-bielik15-native-preflight` completed three coherent Polish responses and verified tokenizer EOS4 `<|im_end|>` against model EOS[4,2]. Results persisted locally and on `matura-small-independent`; native cache is `hf_cache/models--cpral--Bielik-1.5B-v3.0-Instruct-ungated/snapshots/a3a660b10fdba3a7b03c3349567e54d8875f9ac9/`. No Bielik training has occurred.

Real-only adapter worker prepared with explicit synthetic:false/year exclusions2023/2024 and assistant-only official-answer targets. Essay rubrics are not accepted as essay responses. Fresh Modal balance $1.37 near20:22UTC; any pilot uses oneL4 capped600s and requires ready real data.

## 2026-09-26 20:40 UTC — approved real-only Bielik pilot completed

After explicit user approval, app `ap-YB23jdghilmUhEze7gVeDf` trained and exported three actual native Bielik adapters: closed text16steps, open text16steps, essay5steps on five official CKE exemplar essays. Run `20260926-202923-bielik15-real-route-adapters` contains 48,407,904 bytes of GGUF adapters. The dataset was snapshotted before a later conservative Charlemagne exemplar exclusion; this pilot must not establish independent2024essay generalization. No synthetic targets were used.

Paired original-Q4 runtime validation completed in app `ap-v22R1hOJb1IUlVLXWF4Ar4`, run `20260926-203212-bielik15-q4-real-adapters-ocr-five-specialists-offline-b0`. The legacy filename says five, but the manifest explicitly contains only three trained adapters; both image routes fall back to base weights. All adapters loaded, five-category smoke passed, then37paired answers completed in198.08seconds. Adapted answers37nonblank; paired zero-adapter baseline has one blank at14.1, preserved for evaluation. Both official exports validate. Local Luna evaluation requested.

Aggregate deployable artifacts are 1,030,569,275 bytes: Q4base972,797,408 +3adapters48,407,904 +OCR8,878,606 +real-onlyclassifier485,357. OCR applies only to the23predicted image-route tasks, never essay/text routes. Local GGUF backups under `artifacts/small_track/bielik15-real-adapters/` were verified against each trained SHA256. Portable config `infra/small_track/configs/bielik15-q4-real-three-adapter-pilot.json` includes exact hashes and per-request LoRA IDs.

Two real image-route training datasets are now ready, but automatic approval review rejected the extra paid image-route launch as outside the earlier text-pilot approval/read-only heartbeat. It was not launched or retried. Latest observed Modal credit $0.83; the other agent had one L40S.

## 2026-09-26 21:06 UTC — five real-only Bielik specialists complete

- User explicitly approved the remaining image adapters and shared/remaining-credit compute. Reused only our Nebius H100 VM `computeinstance-e00nvzyqe70tcyzpnt`, verified initially empty GPU. Started at approximately20:49UTC, stopped and verifiedSTOPPED after results persisted at21:06UTC. Independent20-minute cloud stop guard and18-minute guest shutdown bounded the run; no Claude workloads changed. Conservative$10credit ceiling, estimated≤$1.58includingVAT; final provider billing not yet refreshed.
- Native public licensed mirror matched the official Bielik checkpoint blobs; actual3,193,073,112-byte native weightSHA checked before training. Real official data only:43closed-image and138open-image rows with actual OCR;16assistant-only updates each. Cleanessay4official exemplars,4updates. Existing25closed-text/76open-text pilots contribute16updates each. No synthetic targets. A local interpreter-path export error was fixed; failedcheckpoint preserved and bounded rerun completed.
- Five exported adapters total80,678,112bytes; sharedBielik1.5B Q4_K_M972,797,408bytes, OCR8,878,606bytes, learnedreal-only classifier485,357bytes: aggregate **1,062,839,483bytes**. All5GGUFs downloaded locally and SHAverified; privateHFbackup verified by recovery agent.
- Run `results/small_track/20260926-2102-bielik15-q4-five-real-adapters-offline`:37trained and37matchedzero-adapter answers, allnonblank, zero transport errors. Original candidate pack preserved; OCR only classifier-selected image routes. No PNG pixels encoded by this text-only model. Same prompt/seed42/temp0/500or1600token budgets; only requestLoRA differs. OwnLuna grading handed off; no score claim yet.
- **Earlier three-adapter runtime claim invalidated:** repeated`--lora` flags loaded only the last adapter. New runtime uses one comma-separated list. GET verified5exactID/path entries; initialregistry scale1 triggered fail-closed before questions. Explicit POST setall5to0, then GETverified0. Each request specifies zero adapters or exactlyone routeadapter. Exactpath+remote/local/trainingSHA audit stored in `verified_lora_handshake.json`.
- Inference ran in Docker`--network none`; outbound connection probe failed as required. Runtime0.5.0-dev build11176 commitf805c57a2; binarySHAa25ff595428ff3575b085d341006716effd840dff79fd8c58bb8a2502951438b; version/help/rawloadedlists persisted. H100 observed82%utilization during26/37pairedcompletion,2.739GBVRAM. Install/download setup consumed approximately6minutes before shorttraining; cachedenvironment nowpersists onownedbootdisk.
- Portable measured config: `infra/small_track/configs/bielik15-q4-real-five-adapter.json`. Standalone replaycode: `train_bielik_real_native.py`, `nebius_bielik_five_infer.py`; the latter now strengthens exactpath/knownSHA gates for future replays. Runtimeevidence records the actual completedrun separately.

## 2026-09-26 21:18 UTC — full real epoch and Q8 precision ablation

- Reused the same owned Nebius VM under a new15-minute cap; conservative additionalcost≤$1.18includingVAT. Coldinitialnativeweightload106s; subsequentloads usedOSpagecache. Everyroute loaded a fresh nativecheckpoint, torchseed7291, deterministicshuffle7291, rank8/lr5e-5/assistant-onlyloss unchanged.
- **286/286 real rows trained exactlyonce, zero length exclusions:**25closedtext,76opentext,43closedimage,138openimage,4officialessayexemplars. Eachadapter16,135,616bytes; allfive80,678,080bytes. Q4package1,062,839,451bytes. Trainingmanifests andallGGUFs downloaded/SHAverified; separateprivateHFfull-epochbackup retains thepilot.
- Q4run `20260926-2115-bielik15-q4-full-epoch-offline`:37matchedbase+37trainedanswers, allnonblank/noerrors; strictall5ID/exactpath/zero-scale/hashverification andoutbounddenial passed. OwnLuna grading dispatched.
- Q8_0 precisionablation authorized onlyafterQ4complete, using samefiveadapters/input/prompt/seed/caps. Pinnedbase1,699,568,096bytes SHA90c3ff5f451864151793476df8ad8364b8b23e2e6cd20de7a007eeeba10a8a3e, aggregate1,789,610,139bytes. DownloadSHAverified; started~21:18UTCwith300-second cap. Results remain unverified until retrieved.
- Operational issue: scheduled guest`shutdown -h +12` creates`pam_nologin` five minutesbeforepoweroff, blocking newSSHwhileQ8continues. Existingcloudstopguardremainsactive; Q4results/allweights alreadylocal. Userauthorizedboundedstop/start solelytofetchQ8durableoutputs, thenstop. Futureworkers should use the independentcloudguard or delayed immediatepoweroff, avoidingearlySSHlockout.


## 21:25 UTC — full-epoch recovery and paired evaluation

Own Nebius H100 VM computeinstance-e00nvzyqe70tcyzpnt trained all 286 real examples across five fresh-base specialist adapters, with zero length exclusions. Full Q4_K_M paired inference completed 37/37 tasks in each arm, zero errors, verified five-adapter identities and offline network denial. The trained aggregate is 1,062,839,451 bytes; private HF recovery is verified at commit 9b05095d287feb8be2d72b00c93078ea7a35aba9. Own Luna protocol v4 reports provisional base 12/60 versus trained 10/60, with unresolved image metadata and essay repeat disagreement; this is not a passing result. See bielik15-full-epoch-q4-paired-local-luna reports.

Q8_0 precision comparison ran under the existing 300-second cap. Scheduled guest shutdown prevented new SSH logins before output recovery; results remain on persistent disk. A separately bounded three-minute recovery boot is authorized, with no inference extension. Q8 completion and score remain unverified at this timestamp. Latest balance is stale: use the user-reported $10 less bounded own spend and other account consumption, not a claimed live balance. Modal was spend-limit blocked; shared Forgehand is authorized fallback but Claude processes must remain untouched.

### 21:27 UTC recovery outcome

Q8fullpairedrun recovered successfully:37/37base and37/37trainedanswers, allnonblank, zeroerrors; exactfiveadaptergate andnetworkdenial passed. Aggregate1,789,610,139bytes. OwnLuna handoffcomplete. Three-minute-cappedrecoveryboot performed noadditionalinference; outputs/nativeGGUFtokenizer metadata copied locally, ownVMstoprequestedimmediately. The pre-recovery experiment had completedbeforethe300-secondcap; no partialscoreclaim. Remainingcreditrequiresfreshaccountverification beforeanynextallocation.

## 2026-09-26 22:09 UTC — shared Forgehand clean-v3 pair complete

- Host remains shared with Claude; only our isolated processes were used. Cap-only
  and clean-v3 inference supervisors/servers exited after durable outputs; no VM
  stop or Claude process changes were performed.
- Cap-only Q8 base run: 37 control and 37 raised answers, no API errors. Own-Luna
  primary totals were 11/60 in both arms; no measured benefit from increasing
  500/1600 token caps to 1000/2400. This uses its own matched Forgehand runtime.
- Clean-v3 Q8 run: `results/small_track/20260926-2205-bielik15-q8-clean-v3-paired/`.
  Five real-data adapters, 138/138 training rows, aligned real router, OCR only
  predicted image routes. Total deployed weights: **1,789,438,226 bytes**; matched
  zero-adapter baseline: **1,708,760,306 bytes**. Q4 packaging of the same adapters
  would be 1,062,667,538 bytes, but this completed inference used Q8_0.
- Exact five-adapter IDs, full paths, file hashes and zero default scales verified
  before answering. Every request specified all five scales. Same 500/1600 caps,
  seed 42, temperature zero, two workers for both arms. Original fields retained;
  locally derived OCR appended separately. Server seccomp blocked outbound TCP
  connects and UDP sockets; clients used loopback with redirects/proxies disabled.
- Both arms have all 37 task IDs and zero API errors; baseline has 37 nonempty
  answers, trained has 36. The blank trained answer is preserved. Exact organizer
  JSON, executed source, runtime, handshakes, logs and completion audit are saved.
  Own-Luna evaluation is pending; completion alone establishes no score or pass.
- Shared llama-server binary SHA:
  `efe78478baa1c4f3e44cbd7b9ebb0f468894b5797f88a56b583c4b5f4fd3cadf`.
  Owned server peak observed memory was 2,816 MiB. Completion/process exit checked
  at 22:08:47 UTC. The newer router and repaired training corpus make this a new
  combined candidate; compare against its matched baseline, not older runs.

## 2026-09-26 22:25 UTC — IQ2 recovery access degraded

- Qwen3.5-4B UD-IQ2_XXS plus unchanged F16 projector totals 2,192,640,864
  bytes. The parent launched bounded offline inference at about 22:19 UTC.
  Five-category generation smoke passed and 13 answers were recovered locally.
- Subsequent SSH connections timed out during banner exchange. The Forgehand
  read-only API still reported the shared session running at the same endpoint.
  Inference completion, live RAM and later GPU allocation were not observable.
  Host memory pressure is a hypothesis, not a verified cause. No shared VM or
  Claude process was restarted, stopped or modified.
- Future owned launch scripts now require `/proc/meminfo` MemAvailable >=6 GiB
  in addition to the existing GPU-memory gate. This local change does not alter
  the currently running experiment. Shared-host monitoring has one owner and
  uses at least 60 seconds between retries.

### 22:34:41 UTC recovery checkpoint

SSH access returned after the IQ2 bound. Recovered **17/37** nonempty answers with
zero recorded API errors at
`results/small_track/20260927-qwen35-4b-iq2xxs-offline/evaluation/answers.jsonl`.
The five-task smoke passed, but this remains a partial paper: no full score or
35% claim is permitted. All prior recovered rows remain unchanged. Logs, original
candidate, runtime, executed source and a sanitized partial-completion audit are
local; no raw process-argument listing was archived.

Both our IQ2 supervisor and GPU server were verified absent. Claude's two GPU
processes remained running and were untouched. Host available RAM was 4,763 MiB,
below the new 6,144 MiB launch gate, so no resume was launched. The server log
showed generation slowing from about 31.55 to 0.21 tokens/second before bounded
cleanup. RAM pressure remains an unconfirmed explanation, not an asserted cause.
Scratch model files remained intact with 136 GB disk space free.

No fresh Nebius available-credit balance was verified. The installed CLI and
current public billing API definitions expose cost calculators, pricing policies
and consumption exports, but no supported balance read method was found. The
stale earlier console figure is not treated as current spend authorization.
