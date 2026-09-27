# Bielik all-paper training and final verification

At the user's explicit request, this run has no year holdouts. Its 2023 paper score is a training-set measurement, not a generalization claim. Targets are extracted official answers and five official essay exemplars; no synthetic targets.

Frozen corpus: `data/small_track_real_training_all_papers_v2/manifest.json`, SHA256 `ef4bd556304c7a856622ca06dfa5cc3a410c5ac859452ef93a0e405774136c07`. Completed one epoch over all225 included rows:38 closed text,11 closed image,127 open text,44 open image,5 essays. Zero length exclusions. Unreviewed/unusable source tasks are documented by the corpus, so this does not claim every task from every downloaded paper was trainable.

Five rank8/alpha16 assistant-only LoRAs use a fresh frozen native Bielik1.5 base per route, learning rate0.00005, seed7291, context3072. Training completed06:11UTC on the isolated Forgehand workspace. All native PEFT artifacts, optimizer/RNG checkpoints and GGUF exports are recovered under `artifacts/small_track/bielik15-all-papers-v2/`. GGUF exports total80,677,920 bytes.

Final Q8_0 package weights total1,789,957,828 bytes:base1,699,568,096; five adapters80,677,920; learned router833,206; OCR8,878,606. OCR applies only to the two predicted image routes. Original questions remain unchanged.

Fresh paired verification uses identical original2023 input, router/OCR, runtime, system prompt, seed42, temperature0, caps500/1600 and concurrency1/context8192. Base sets all five LoRA scales to0; trained sets only the predicted specialist to1. Registry IDs, exact paths, weight hashes and zero default scales are checked before inference. The server blocks outgoing TCP connections and UDP sockets. Runtime and executed source are persisted alongside answers.

Results live in `results/small_track/20260927-bielik15-all-papers-v2-pair/`. Own Codex Luna policyv5 is frozen before inference. Until its complete report is available, no passing score is claimed.

Only our isolated Forgehand processes are used. Claude processes are preserved. Nebius and Modal are not used. Delivery cutoff is2026-09-27T06:40:39Z.
