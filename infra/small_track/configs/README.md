# Frozen five-route experiments

## Current fixed-input workflow

The current direct-vision baseline is `modal run infra/small_track/modal_expanded.py --quant q4`;
use `--quant q3` for the paired smaller quantization. Full original questions,
source text and PNGs remain available; no topic projection. Weights are cached
before GPU allocation, then inference uses provider-level network blocking.
See `docs/SMALL_TRACK_RECOVERY.md` for exact artifacts, storage and restore steps.
Primary grading now uses Forgehand GPT-6-Luna; historical Sol results remain labeled.

The following frozen prompt trials are historical. In particular, `single-topic2`
removes alternatives and is superseded by the user's fixed-input requirement.

Run from the isolated worktree with an authenticated Modal CLI:

```sh
modal run infra/small_track/modal_infer.py::frozen --model bielik45 --config-suffix single-topic2
```

The default input is canonical-b0-candidate.jsonl. The local candidate-only rules-v1 classifier assigns all five routes. Every question is inferred freshly; this command does not compose old answers. Model revision, serialized byte count and SHA256 are pinned in JSON. Each worker is bounded to 300 seconds; inspect shared Modal occupancy first, never exceed the account-wide ten-GPU limit or alter other agents' jobs.

Bielik4.5 single-topic2 applies concise instructions to closed questions with images, projects essay topic2 from the supplied alternatives, and uses baseline prompting elsewhere. The input manifest hashes the original complete candidates; the answer row records the projected topic. Essay budget3200, other tasks500, seed42, greedy decoding,8slots/8192context.

Bielik1.5 frozen applies essay-rescue prompting only. Earlier Sol results showed no essay improvement; retained for reproducibility, not recommended as a pass candidate.

These are text-only ablations. The classifier recognizes supplied images, but this pipeline does not encode image pixels. Do not market these as a complete vision pipeline. Selection used the2023 development mock; no held-out generalization claim. Sole score authority is Forgehand gpt-6-sol.

## Passing vision model, portable offline harness

The Qwen3.5-4B vision configurations contain measured Q4/Q3 model and F16 projector hashes/bytes. They route all five task types to the same own vision model and preserve the complete supplied text and linked PNGs. No external answering service is used. Q4 has a settled Sol lower bound23/60 on the2023 mock; Q3 grading is pending. Candidate2024 full-page images use a different representation.

After retrieving and verifying the pinned artifacts, start a local native server:

```sh
llama-server -m Qwen3.5-4B-Q4_K_M.gguf --mmproj mmproj-F16.gguf --alias qwen35-4b --host 127.0.0.1 --port 8080 -ngl 99 -c 32768 -np 4 --jinja --reasoning-budget 0
python scripts/small_track/harness.py --input data/small_track/official_mock_v1/exam.json --config infra/small_track/configs/qwen35-4b-Q4_K_M-harness.json --output results/qwen35-answers.jsonl --concurrency 4 --offline
```

For exact reproduction leave OCR, trained-router and voting toggles disabled; these are separately measured optional techniques. The winning baseline already performs direct visual interpretation. Network-blocked Modal runs verified outbound denial; the portable HTTP client enforces loopback, disables proxies and blocks redirects. The server process still needs an OS/container egress restriction for a strict airgap.
