# Submission draft: Bielik history specialists

Project name: Bielik 1.5B offline history specialists.
Requested categories: Biggest Improvement and Smallest Model. Team code and team category allocation must be confirmed by the orchestrator before any external submission. Each category is available once per team; coordinate Claude's project. This file does not submit or reveal final questions.

Repository: https://github.com/OrestTa/matura-model-trainers-hackathon/tree/codex/small-model-offline-harness

Candidate staged for comparison: Bielik-1.5B-v3.0-Instruct Q8_0 shared base1,699,568,096bytes; five F16 LoRA adapters80,677,920bytes combined; learned multinomial classifier833,206bytes; Polish/English OCR8,878,606bytes. Total1,789,957,828bytes (1.789958GB), below8.8GB. Repeated inference does not duplicate weights. No semantic visual model is included; image routes use OCR only.

Private adapter recovery: https://huggingface.co/orestta/matura-small-track-recovery/tree/c32dbe77349739a8d3612629c67c57f5c1deab9e/models/bielik15/all-papers-v2
Base public pinned revision6c316d2be07dee472901150c3f3e9d4f725a4706 in second-state/Bielik-1.5B-v3.0-Instruct-GGUF, filename Bielik-1.5B-v3.0-Instruct-Q8_0.gguf.
Private repositories require organizer access or delivery of the full local bundle; a private URL alone is not a retrievable submission.

Final selection and score remain pending the orchestrator's matched comparison. Training used225 approved official rows, no year holdouts. All36non-essay2023 mock tasks were included; any2023 result is training-set performance. BiggestImprovement evidence must identify the baseline required by the organizer: bare individual model versus adapter/OCR/router pipeline, with identical inputs and judging. A matched OCR/router baseline is an ablation and is not automatically that competition baseline. No claims of unseen35% performance are made here.

## Running the actual final input

From the delivered package, place organizer's actual exam.json beside its images directory. Use a new empty output location:

    ./check-runtime.sh
    ./run.sh --exam /absolute/path/final-exam/exam.json --output /absolute/path/final-preflight
    ./run.sh --exam /absolute/path/final-exam/exam.json --output /absolute/path/final-result --run

Only final-result/answers.json produced from the actual final exam can be uploaded. Check status.json errors=0, all expected answer IDs, and original input SHA before upload. Dry-run EMPTY answers and2023 mock answers are not final submissions. Inference uses only local weights and original candidate input; no answer key, judge or network model is consulted.

Submission page: https://warsawmodeltrainers.dev/submissions.html?exam=final
Do not reveal questions before all team projects are finished. Actual upload remains a separate orchestrator action after team allocation and final selection.
