# Tiny visual auxiliary feasibility,2026-09-27

This is an unlaunched candidate-only smoke test, not a measured improvement.
The official [SmolVLM256M card](https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct)
lists Idefics3 architecture, English language and Apache2.0 licensing. Use native
BF16 weights at revision `cee7dc33d83ff2ddec17238b7aba85145169e631`.
The official Git LFS pointer declares exactly513,028,808bytes and SHA256
`74dea5904032e5ae99a2e0eef5179e6ac0f1dedc3ab0c7c2a5d4d387c843203e`.
These are metadata-verified sizes; the smoke will verify downloaded bytes too.
All visual weights are in that file; no separate learned projector is declared.
Combined with the clean-v3 BielikQ4 five adapters, classifier and OCR, total weights
would be1,575,696,346bytes. Processor/tokenizer files are required runtime assets
and must also be retained, but are not additional learned weights.

Existing isolated Transformers5.17.0 successfully imports AutoProcessor and
Idefics3ForConditionalGeneration. That establishes API availability, not successful
model execution or useful Polish-history visual descriptions. The native source
config declares BF16 and Transformers4.46.0; the loader uses local files only.

`scripts/small_track/smolvlm_visual_smoke.py` expects preloaded local weights and
five image-only packets from `data/small_track_smolvlm_smoke_v1/candidate-images.jsonl`.
The fixed image IDs are1,3,7,14.1,20. They were selected without evaluation keys.
Original image hashes are checked; no original question or source is replaced.
A generic English prompt requests visible objects, symbols, positions and labels,
explicitly discouraging historical guesses. The run uses greedy160-token outputs,
10% PyTorch allocator fraction, a6GiB free-memory gate, and a Linux seccomp network
ban before generation with a denied-socket probe. Parent must supply an external
timeout and coordinate sharedGPU availability. No GPU was launched by preparation.

Any future Bielik augmentation must keep inferred descriptions separate from OCR
and original input, label uncertainty, classify first, and apply only to image
routes. Tiny-model captions can hallucinate; a successful smoke alone does not
justify treating them as verified source facts or claiming improved exam accuracy.
