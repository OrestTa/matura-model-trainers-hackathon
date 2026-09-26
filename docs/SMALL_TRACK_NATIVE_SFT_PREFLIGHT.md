# Native Qwen SFT pilot preflight

Status: deferred by orchestrator after the vision baseline passed. Not launched and not completed. Qwen3.5-4B vision now has a sole-Sol settled lower bound of23/60; prioritize its validation/compression before an unrelated SFT trial unless the orchestrator selects the training work.

Proposed native training source: Qwen/Qwen3-4B-Instruct-2507, pinned revision cdbee75f17c01a7cc42f958dc650907174af0554. Its independent native GGUF baseline is coherent; native Transformers loading still requires a three-question smoke test. No GGUF-to-Transformers conversion.

Data: data/small_track_synthetic/sft-no2023-no2024-strict-text.jsonl,40synthetic exams564text rows, SHA256 c85f7e08effc403e3fa31f7fbe6f864c06395223bce2bcbce608335f51d2bcad. Assistant-only loss and paper-separated synthetic validation are implemented by scripts/small_track_train.py. Official evaluation papers are excluded.

CPU prerequisites: cache the exact native weights/tokenizer; verify conversion script and llama-quantize binary are available; pin their versions. Then one bounded GPU smoke run generates three candidate-only answers and verifies tokenization, EOS and meaningful completion before any training allocation.

Training pilot: at most one H100 for1200seconds,80steps,LoRA rank8,learning rate5e-5,batch4×accumulation2,maximum3072tokens,BF16 dense base,gradient checkpointing. Save adapter/checkpoints/merged weights to a private persistent volume. No training launch until shared actual GPU occupancy and credits are verified; proposed total cap approximately$3 including smoke and CPU conversion.

Export: convert merged native weights to F16 GGUF, quantize Q4_K_M, measure exact bytes/SHA256 and evaluate the whole unchanged official paper with the frozen baseline prompt. Export/quantization failure means no deployable SFT result; do not count a dense training checkpoint as a submitted model or claim improvement from synthetic validation. All grading is sole Forgehand gpt-6-sol. Preserve the untrained baseline and do not splice official answer-key facts into candidate inputs.
