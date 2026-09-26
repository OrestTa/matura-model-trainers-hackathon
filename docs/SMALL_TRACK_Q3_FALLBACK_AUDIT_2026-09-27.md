# Qwen Q3 fallback audit — 2026-09-27

The saved Qwen3.5-4B Q3_K_M + F16 projector result remains a **historical development-paper pass: 25/60 (41.67%)**, using the user's own Codex GPT-6-Luna `local-luna-official-v2` protocol. This audit checks artifacts and arithmetic only; it introduces no answer judgments or new model calls. It does not establish generalization, a global minimum, or bit-for-bit replay. The current experiments continue to target smaller packages and Bielik.

Run: `results/small_track/20260926-193419-qwen35-4b-vision-q3-offline-b0/`.

| Category | Plain Q3 | Q3 + OCR |
|---|---:|---:|
| Closed without images | 3/4 (75.00%) | 3/4 (75.00%) |
| Closed with images | 4/7 (57.14%) | 4/7 (57.14%) |
| Open without images | 6/11 (54.55%) | 6/11 (54.55%) |
| Open with images | 12/23 (52.17%) | 10/23 (43.48%) |
| Essay | 0/15 (0.00%) | 0/15 (0.00%) |
| Total | 25/60 (41.67%) | 23/60 (38.33%) |

Historical same-protocol OCR delta: −2 points (−3.33 percentage points), with one inference per arm and unquantified serving/judge variance. Packages: 2,965,812,064 versus 2,974,690,670 bytes. Matching Ania Qwen3.5-4B reference is unverified; adapted-text/full-page benchmark inputs differ, so no numerical Ania delta is available. New IQ2 Luna-v4 results must not be treated as a controlled difference from this Luna-v2 reference.

## Verified locally in this audit

- All 37 inference answers are nonempty, with zero recorded errors. Saved Luna grades cover 37 items, sum to 25, and contain no uncertain flags.
- All 37 request hashes reconstruct exactly from the original canonical text and all 19 original PNGs. Image checksums match the run manifest. No OCR, router or adapter is needed by this plain vision candidate.
- Candidate file: `data/small_track/official_mock_v1/canonical-b0-candidate.jsonl`, SHA256 `3ecfcc62c05cc28ba668ff751fa6ce33a81e54a5cd8e958cf1ae0d2e5c6b031a`. The manifest's separately serialized candidate hash also matches.
- `official_answers.json` is byte-identical to an in-memory export using `scripts/small_track/official_format.py`: correct exam ID, all 37 string IDs, strict fields, 45,063 bytes. SHA256 `d0adbe8358d9b69d6c38cbdee6e684cadd4688a98f0029b9c869fc9cc122530a`. This checks submission structure, not new answer correctness. Nothing was submitted externally.
- `threshold-verified.local-luna-v2.json` still binds exactly to these files:

| File relative to run | SHA256 |
|---|---|
| `answers.jsonl` | `15099842e41c484e5a8cd2f0370d2ad4f4cb9b6d297d90fbb84ed5ac785f8572` |
| `manifest.json` | `381c32b0ed835c20e1f62d42662a37376a6c93cfbfa064031b1c9d32b7b44c22` |
| `local_luna_official_v2/summary.luna.json` | `e24ead18745fcd0f7d261055b96d9a51002fd1b7279556536e97b23af4dc6cca` |
| `local_luna_official_v2/grades.luna.jsonl` | `8a30b731c77d9a2738098990ae840a6b64f233e4da8369163af298e89643930e` |

## Recovery sources

Pinned public repository: `unsloth/Qwen3.5-4B-GGUF`, revision `e87f176479d0855a907a41277aca2f8ee7a09523`.

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `Qwen3.5-4B-Q3_K_M.gguf` | 2,293,388,448 | `d6981ab4d77ba712b48ef69d69042d75b5e39b9dce5fb5a5b054fd08e06afb95` |
| `mmproj-F16.gguf` | 672,423,616 | `cd88edcf8d031894960bb0c9c5b9b7e1fea6ebee02b9f7ce925a00d12891f864` |

Previously verified private copy: `orestta/matura-small-track-recovery`, commit `8d8624a48b0fb74537491b7de3f565bdc5da6e52`, under `models/qwen35-4b/`. Evidence: `artifacts/small_track/hf-recovery-current.json`. Remote availability was **not** rechecked during this read-only audit. The two weights were not present in the worktree artifacts directory or standard local HF snapshot cache checked here; a self-contained local model bundle is therefore not established.

Inference configuration: `infra/small_track/configs/qwen35-4b-Q3_K_M-harness.json`. Historical settings: original PNG content, temperature 0, seed 42, 500 short-answer / 1600 essay tokens, reasoning disabled, 4 slots with 8192 context per slot. The run records Modal network blocking plus outbound-denial probe. Current `infra/small_track/modal_expanded.py --quant q3` is a recovery route, not a launch instruction or exact historical snapshot.

## Missing replay provenance

The run has no pinned original container digest, llama-server binary SHA/build version (`server_build_evidence` is empty), or immutable executed-runner snapshot. Current source has changed since inference. Weight and request reconstruction is strong, but exact runtime reproduction cannot be claimed. A replay would require recovering the original runtime or explicitly declaring a new runtime and measuring it again.

The organizer mock is the 2023 development paper with cropped PNGs and transcribed sources. It is neither an untouched holdout nor the earlier full-page Ania input representation. Canonical repository rules require own-Codex Luna for new judging; older Forgehand wording in historical recovery notes is superseded.
