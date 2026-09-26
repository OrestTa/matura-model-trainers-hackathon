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

## Completed execution smoke; fidelity pending

The parent-approved smoke completed all five images. Outputs are recovered at
`results/small_track/20260927-smolvlm256m-visual-smoke/`; generation took15.09seconds
total. Exact local weight bytes/hash and original image hashes passed, and the
OS socket-denial probe succeeded. Three descriptions were terse/vague/refusal-like;
two made detailed identification or translation claims. These are raw observations,
not expert fidelity judgments. The loader emitted a pad_token_id128002/vocabulary
31999 warning; generation completed, but this compatibility warning is preserved.

`scripts/small_track/luna_visual_fidelity_qa.py` is prepared for a separate parent
launch (`--execute`). Its dry run validates all five original image hashes. It uses
own Codex gpt-6-luna, at most four concurrent calls, no automatic retries, original
images plus generated descriptions only, and no questions or keys. Classification
is faithful/unsupported/missing_details/unsafe_to_use. No description is integrated
into Bielik input merely because inference returned nonempty text.

## Luna fidelity outcome and next prepared candidate

Own Codex gpt-6-luna completed all five fidelity reviews: three `missing_details`
(IDs1,3,7), two `unsafe_to_use` (IDs14.1,20). SmolVLM256M caption integration is
rejected. This conclusion comes from Luna image-fidelity review, not Astra grading.

The next prepared candidate is [Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B),
Apache2.0, using [Unsloth's published GGUFs](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF)
at immutable revision `6ab461498e2023f6e3c1baea90a8f0fe38ab64d0`.
Exact publisher blob metadata:

| Artifact | Bytes | SHA256 |
|---|---:|---|
| Qwen3.5-0.8B-Q4_K_M.gguf |532517120|bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517|
| Qwen3.5-0.8B-Q3_K_M.gguf |470167808|c49ad509cd0a3f8584c4eff50d84202336bf9475b8a724c89f4061687c1fb510|
| mmproj-F16.gguf |204987232|56e4c6cfe73b0c82e3e82bc518d7591997e61d81f723fc41a586f4fa69ea2453|

Q4 plus required projector is737,504,352bytes; with clean BielikQ4 the aggregate is
1,800,171,890bytes. Q3 alternative totals1,737,822,578bytes. PreferQ4 for the first
quality probe; Q3 saves only62,349,312bytes. SmolVLM500M native weights at revision
`a7da5b986cb59b408707209984f360a5f4ad7e47` are1,015,025,832bytes,
SHA256 `d05b567eeaf534e83d375551f068ed57b5f52d37c657197f644af5ef9db091a2`;
its combined package would be2,077,693,370bytes. All are metadata checks, not quality
measurements. The selected probe requires actual downloaded-hash verification.

`qwen08_visual_smoke.py` and `infra/small_track/qwen08_caption_smoke.sh` are prepared
but were not launched during preparation. They retain the same five images and
caption prompt,160-token greedy outputs, a single4096-token server slot, a6GB free
VRAM gate, and the existing owned llama.cpp81bc6b8 binary with verified SHA256.
Port18934 is isolated from other experiments. The server's outbound network is
blocked by seccomp and proof checked by the fixed-loopback client. Parent should
wrap the complete staging/launch script in480seconds; the inference child itself
is bounded to240seconds. Outputs still require independent Luna fidelity review.
