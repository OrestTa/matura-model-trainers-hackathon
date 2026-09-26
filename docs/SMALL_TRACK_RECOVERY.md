# Small-model storage, recovery and reproduction

Updated 2026-09-26. This is the recovery map for the independent Codex effort.
Do not alter Claude's worktree, Forgehand GPU, Nebius jobs or shared filesystems.

## Code and authoritative local copy

- GitHub: `OrestTa/matura-model-trainers-hackathon`, branch
  `codex/small-model-offline-harness`. Only this branch is pushed.
- Working copy on the user's Mac:
  `/Users/Orest/.codex/worktrees/small-model-track/matura-model-trainers-hackathon`.
- Paths below are relative to that working copy unless explicitly absolute.
- Code, configurations, provenance and compact score reports belong in Git.
  Model binaries, downloaded exams, raw synthesis and credentials do not.
  A Git clone alone therefore does **not** restore the data/model directories.
- Never copy the credentials inventory into a backup or model repository.

## Storage inventory

| Artifact | Durable location | Local copy / recovery evidence |
|---|---|---|
| Bielik inference weights and outputs; Qwen3.5 vision weights/outputs | Modal volume `matura-small-independent`, ID `vo-U1bPKYrsksXdkfrwjOxZo5`, mounted as `/outputs` | `results/small_track/<run_id>/`; weight provenance in per-run manifests |
| Qwen3-4B-2507 weights/outputs | Modal volume `matura-qwen-independent`, ID `vo-QWGa4kMgFdodkCyZZm7vDs`, mounted as `/outputs` | `results/small_track/20260926-192723-qwen3-4b-2507-q4-canonical-b0/` |
| Invalid first SFT pilot | Modal volume `matura-small-sft-independent` | `data/small_track_synthetic/diagnostics/`; cloud adapter/merged/checkpoints are diagnostic only |
| Four Nebius 2024 runs and two Bielik Q4 weights | Own managed boot disk `computedisk-e00xg1jfsnvt0sspeb`, 80 GB | All four answers/manifests copied to `data/small_track_cloud/nebius-20260926/`; GGUFs remain on disk/public pinned upstream |
| Official 2017–2026 papers, keys and extracted rows | User's Mac: `data/small_track/<paper_id>/` | `data/small_track/manifest.json`; recreate from pinned source configuration |
| 2015–2016 reserved papers | User's Mac under `data/small_track/` | Separate source entries/split metadata; excluded from synthesis, prior external exposure unknown |
| Organizer-format 2023 input | User's Mac: `data/small_track/official_mock_v1/` | `exam.json`, `answers-template.json`, `images/`, candidate JSONL; per-run manifests record original image hashes |
| 100 synthetic papers and raw generation/review records | User's Mac: `data/small_track_synthetic/` | `final_manifest.json` and per-exam files; generation is stochastic, so back up these exact files |
| Strict SFT split excluding 2023/2024 source examples and blueprints | `data/small_track_synthetic/sft-no2023-no2024-strict-text.jsonl` | 40 exams / 564 rows; SHA256 `c85f7e08effc403e3fa31f7fbe6f864c06395223bce2bcbce608335f51d2bcad` |
| Offline OCR outputs and exact Polish/English weights | `data/small_track/official_mock_v1/ocr-offline-v1/` | Original/derived hashes, 19 image records and copied traineddata in its manifest |
| Trained router | `artifacts/small_track/router-real-source-disjoint-compact.json` | 458,956 bytes; SHA256 `97f6cdf9588ed0f8ada059b14ce277b1bc70240b13f35cad43f4af6362127dbd` |
| Sol/Luna raw responses and grade bindings | Per-run `sol_primary_v3/` and `results/small_track/luna-calibration-20260926/` | Mac files; compact selection reports in Git; no inference worker receives these |

The Mac copies survive a GPU VM/container failure. They are **not** a second
offsite backup against losing the Mac. The private HF model backup below covers
only its verified allowlisted model files, not all exam/synthesis/results dumps.
Never claim a whole-run backup exists merely because a model was uploaded.

## Exact current model identities

All sizes are bytes. A vision model includes its required projector. The organizer
clarification relayed on 2026-09-26 requires summing ALL deployed model weights
within 8 GB + 10% margin (8,800,000,000 bytes). Optimize this aggregate, not the
largest individual model. Count OCR and learned routers, distinct quantizations
separately, and genuinely shared identical weight files once. Repeated sampling
from the same weights increases compute but not packaged weight bytes.

The standalone Q4 vision bundle totals 3,413,361,504 bytes; standalone Q3 totals
2,965,812,064 bytes. Combining Q4 and Q3 with their one shared projector totals
5,706,749,952 bytes BEFORE adding a learned router or OCR. These are package
sizes, not claims that a combined routing configuration has passed evaluation.

| Component | Pinned Hugging Face repository and revision | File | Bytes | SHA256 |
|---|---|---|---:|---|
| Passing-bound Qwen3.5-4B Q4 | `unsloth/Qwen3.5-4B-GGUF` @ `e87f176479d0855a907a41277aca2f8ee7a09523` | `Qwen3.5-4B-Q4_K_M.gguf` | 2740937888 | `00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4` |
| Its required vision projector | same | `mmproj-F16.gguf` | 672423616 | `cd88edcf8d031894960bb0c9c5b9b7e1fea6ebee02b9f7ce925a00d12891f864` |
| Q3 candidate, not yet a demonstrated pass | same | `Qwen3.5-4B-Q3_K_M.gguf` | 2293388448 | `d6981ab4d77ba712b48ef69d69042d75b5e39b9dce5fb5a5b054fd08e06afb95` |
| Qwen3-4B-2507 Q4 text baseline | `unsloth/Qwen3-4B-Instruct-2507-GGUF` @ `a06e946bb6b655725eafa393f4a9745d460374c9` | `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` | 2497281120 | `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597` |
| Bielik 1.5B Q4 | `second-state/Bielik-1.5B-v3.0-Instruct-GGUF` @ `6c316d2be07dee472901150c3f3e9d4f725a4706` | `Bielik-1.5B-v3.0-Instruct-Q4_K_M.gguf` | 972797408 | `ea9cc250a6c65718c290fd963d8e3237b924ccfc7632f20a6127bba5904a50d9` |
| Bielik 4.5B Q4 | `second-state/Bielik-4.5B-v3.0-Instruct-GGUF` @ `5ed9534f824c7c184c21320f4d339e75569d0987` | `Bielik-4.5B-v3.0-Instruct-Q4_K_M.gguf` | 2878886912 | `39fb78db7c5e1582d3ef5bded109cd98606aabd5acbb5c98601155174b6763e1` |

Qwen3.5-4B Q4 plus projector totals **3,413,361,504 bytes**; Q3 plus the same
projector totals **2,965,812,064 bytes**. The cancelled 8B branch is not part of
the deployment. Prior Qwen3.5-2B identities are in
`results/small_track/artifact_manifest.json`; precision experiments retain their
own run manifests. Do not silently substitute model revisions or projectors.

Modal model cache paths are volume-relative:
`hf_cache/models--OWNER--REPO/snapshots/REVISION/FILENAME`.
For example the Qwen3.5 Q4 cache is
`hf_cache/models--unsloth--Qwen3.5-4B-GGUF/snapshots/e87f176479d0855a907a41277aca2f8ee7a09523/Qwen3.5-4B-Q4_K_M.gguf`.
HF snapshot entries can be symlinks to cache blobs; recover the actual bytes,
not a broken link. Independent public upstream downloads are another recovery path.

## Recover a Modal run without restarting a GPU

Modal volumes survive ephemeral app/container termination. New workers flush
and commit each answer. A worker can finish inference yet fail to return its
large RPC payload under network isolation: this happened to the Qwen vision
run; all 37 answers were recovered from its volume without rerunning inference.
Future workers return a small pointer and the host retrieves files separately.

With your existing Modal login, run from any recovery machine:

```sh
mkdir -p recovered-vision
modal volume get matura-small-independent \
  /20260926-192720-qwen35-4b-vision-offline-b0/answers.jsonl \
  recovered-vision/answers.jsonl
modal volume get matura-small-independent \
  /20260926-192720-qwen35-4b-vision-offline-b0/manifest.json \
  recovered-vision/manifest.json
modal volume get matura-small-independent \
  /20260926-192720-qwen35-4b-vision-offline-b0/server.log \
  recovered-vision/server.log
```

Use explicit file paths and create the destination directory first. This avoids
observed ambiguity when downloading a remote directory to a nonexistent local
destination. Avoid `--force` unless deliberately replacing a verified local copy.
Use `matura-qwen-independent` and its run ID for the text-model run. The same
file command downloads cached GGUFs, but first allow enough local disk space.

## Recover Nebius data

Owned VM: `computeinstance-e00nvzyqe70tcyzpnt`, named
`codex-small-two-favorites-20260926`. Its boot disk ID is listed above. Last
verified state is STOPPED; consult `resumed_stopped_instance.json`, not an old
public IP, before reconnecting. Do not delete the VM/disk as cleanup.

- Model directory: `/opt/codex-small-track/models/`.
- Four run directories:
  `/opt/codex-small-track/bielik{1.5,4.5}-2024-{baseline,concise-routes}`.
- All answers/manifests and baseline server logs are already copied to the Mac
  directory in the inventory; no restart is required to access those results.
- If the VM is lost but its managed disk survives, attach **our disk only** to
  an owned recovery VM, mount it read-only, and copy `/opt/codex-small-track/`.
  Never repurpose another agent's disk or VM. Deletion can remove a managed disk.
- SSH private authentication is not in Git. The current temporary local key is
  `/tmp/small-track-nebius-auth/id_ed25519`; its existence is not guaranteed after
  a Mac restart. If unavailable, use authorized Nebius disk recovery, not a key
  copied into documentation or a public model repository.

## Private Hugging Face backup

Account identity verified as `orestta`. Repository:
https://huggingface.co/orestta/matura-small-track-recovery (private).

First verified commit: `6229ff8a31fb685d741efd8669b1ae08d014a562`.
It contains the compact router and `ocr/weights/{pol,eng}.traineddata`, OCR
manifest/README and licensing metadata. Exact verified paths/hashes are in
`artifacts/small_track/hf-recovery-compact.json`.

Large GGUF uploads are now independently verified at private repository commit
`7afd09ec596c4f664c4ade11a65977899727e862`. Evidence is in
`artifacts/small_track/hf-recovery-models.json`: all three source hashes match
Hub LFS SHA256 and sizes, totaling 5,910,642,624 bytes. Verified paths are:

- `models/qwen3-4b/Qwen3-4B-Instruct-2507-Q4_K_M.gguf`
- `models/qwen35-4b/Qwen3.5-4B-Q4_K_M.gguf`
- `models/qwen35-4b/mmproj-F16.gguf`

Authenticate with the user's HF account using the normal CLI login or an
existing protected token; never put a token in shell history, Git or this guide.
For a reproducible download, use the exact verified commit, not moving `main`:

```sh
hf download orestta/matura-small-track-recovery \
  router/router-real-source-disjoint-compact.json \
  --revision 6229ff8a31fb685d741efd8669b1ae08d014a562 \
  --local-dir recovered-models
```

For public upstream restoration use `hf download OWNER/REPO FILENAME
--revision REVISION --local-dir recovered-models` with the table above, then
verify bytes and SHA256 (`shasum -a 256 FILE`). Preparation downloads are allowed;
exam inference itself remains offline. Preserve upstream licenses/attribution.

## Recreate data and run a fast check

1. Restore this Git branch and install its Python/Modal dependencies. Existing
   local test interpreter: `/tmp/matura-small-track-venv/bin/python`; recreate it
   if temporary files have been removed. The environment itself is not a backup.
2. Rebuild official downloads with `python scripts/small_track_data.py` and
   validate with `python scripts/small_track_data.py --validate-only`.
   `configs/history_2017_2026_sources.json` pins URLs, splits and parser Git
   revision. Keep candidate questions and `judge.jsonl` keys physically separate.
3. Restore the organizer pack with its exact original hashes. It is a different
   representation from the PDF parser output and cannot be replaced silently.
   Preserve the local pack or obtain the organizer's original archive again;
   the grading guide URL alone is not an exact archive backup.
4. Restore exact synthetic files from the Mac copy for reproducible SFT.
   Re-running `scripts/small_track_synth.py` is paid, stochastic regeneration,
   not recovery of the original training dataset. Native SFT must use the strict
   split above; the first GGUF-import adapter is invalid and must not be deployed.
5. Run tests: `python -m pytest tests/small_track tests/test_small_track_second_opinion.py`.
   Dry-run five candidate-only tasks, one per category, with no keys in the
   inference filesystem. Verify schema, IDs, hashes, nonempty strings, no remote
   inference calls, output persistence and actual weight size before a full run.
6. For the verified vision baseline use
   `modal run infra/small_track/modal_expanded.py --quant q4`; for Q3 use `--quant q3`.
   Inspect current code/config and live shared GPU capacity first; no cloud launch
   is implied by reading this document. Model preloading is CPU-only; inference
   uses Modal `block_network=True` and an actual outbound-denial probe.
7. Grade completed submissions separately through the user's own ChatGPT Codex
   `gpt-6-luna`, using official CKE keys and original images where relevant.
   Keep historical Sol scores labeled.
   No Astra grading. Retain unresolved marks, full denominators, five categories,
   paired baseline/optimized deltas, and the unmatched-Ania caveat.

## Preserve future work

Every new run must persist candidate/input/image hashes, model revisions and
measured weight bytes, exact prompts/decoding, route decisions, all vote samples,
selected answers and errors, execution logs and judge bindings. Commit small
manifests and recovery instructions to the own Git branch; copy large artifacts
to the private model repository/owned volumes and verify remote hashes before
retiring any unique copy. HF model backup does not include credentials or keys.


## Verified private recovery additions (latest)

Private repository `orestta/matura-small-track-recovery`, verified model commit `8d8624a48b0fb74537491b7de3f565bdc5da6e52`, now also contains Qwen3.5 Q3 (2,293,388,448 bytes), Bielik1.5 Q4 (972,797,408 bytes), two valid real-data text GGUF adapters (16,135,968 bytes each), and the current real-only router (485,357 bytes). Per-file hashes and commits are recorded in `artifacts/small_track/hf-recovery-current.json`. The required Qwen projector was reverified at672,423,616bytes against its knownSHA.

The large additions used Hugging Face server-side cross-repository copy from pinned public upstream commits, then destinationLFS SHA/size checks. No paid compute was required: Modal refused its CPU recovery launch at the account spend limit. The replacement local transfer was stopped after server-side copies succeeded. Public base weights remain independently available upstream, while adapters and classifier now have private recovery copies.

Paths: `models/qwen35-4b/Qwen3.5-4B-Q3_K_M.gguf`, `models/qwen35-4b/mmproj-F16.gguf`, `models/bielik15/Bielik-1.5B-v3.0-Instruct-Q4_K_M.gguf`, `models/bielik15/adapters-real/{closed_without_images,open_without_images}/adapter-f16.gguf`, and `router/router-real-2026-0926.json`. Use authenticated `hf download REPO PATH --revision COMMIT --local-dir recovery` for each needed file; never embed tokens in commands.

Final update: all five clean adapters are verified in private HF model commit `b9df21dc184775f24397b9f30813bf13a82ff616`; recovery instructions/manifests are at `bdddf2b493edf9e21c550d351b11ad2c27dca547`. Their total is80,678,112bytes. The full BielikQ4 plus five adapters plus real-only router and pol/eng OCR totals1,062,839,483bytes. The clean essay source SHA matches the frozen four-real-exemplar dataset exactly; its training used only those four IDs. The older essay checkpoint that trained on the subsequently excluded Charlemagne exemplar was never uploaded. No exam data, keys, synthetic-trained model artifacts or invalid converted SFT checkpoints are included in these additions.

Final clean adapter Mac paths: `artifacts/small_track/bielik15-real-final-adapters/adapters/<route>/adapter-f16.gguf`. Private remote equivalents: `models/bielik15/adapters-real/<route>/adapter-f16.gguf`. Download all five route names listed in `artifacts/small_track/bielik-real-recovery-provenance.json`; combine with the one shared BielikQ4 base, real2026router, and OCR weights. These backups restore inference weights; they do not include private exam datasets or optimizer state. Weight recovery does not establish an accuracy threshold.


## Full-epoch version: verified separate backup

All five adapters from run `20260926-2115-bielik15-real-full-epoch` are independently backed up under `models/bielik15/adapters-real-full-epoch-20260926/<route>/adapter-f16.gguf`. Private HF weights commit: `ba88af4d4c20aea1c6d0bd24bf9754803a286b39`; manifest/README commit: `9b05095d287feb8be2d72b00c93078ea7a35aba9`. Each remote SHA and byte size was verified, and the private flag checked. Evidence: `artifacts/small_track/hf-recovery-full-epoch.json`.

Each route starts from a fresh native base; complete route counts25/43/76/138/4 sum to286rows, with zero length exclusions. Source dataset manifest SHA is `022b107ec04dfa7df392ab13869b2cce4eaf82b4b2a852687507e48f22b65bef`. All source JSONL hashes match the training manifests. The four essays are real official exemplars; the Charlemagne example remains excluded. No question/key data was uploaded.

Five full-epoch GGUF deltas total80,678,080bytes (16,135,616each). With the shared BielikQ4 base, real-only classifier and OCR, total deployment is1,062,839,451bytes. This version is ungraded at backup time; do not infer improvement from completed training. The earlier pilot remains under its previous path and immutable commits. Download one version's five deltas, never combine or stack pilot/full-epoch copies. Local copies are `artifacts/small_track/bielik15-real-full-epoch/adapters/<route>/adapter-f16.gguf`.

## Boundary-clean v3: completed private recovery

The clean138-row run is backed up separately under
`models/bielik15/adapters-real-boundary-clean-v3-20260926/<route>/adapter-f16.gguf`
in private `orestta/matura-small-track-recovery`.
Verified weights commit: `7c015a205cf7b45f0d8dc507430133ea447b3d44`.
Documentation/manifest commit: `8d0e2514f1aa3e8eea2e0bb00b8cc119cea8d551`.
All five adapter SHA256 values and sizes match the local training manifests;
aggregate adapters80,677,920bytes. The aligned classifier is separately recoverable
at `router/real-specialist-aligned-v1.json`:313,604bytes,
SHA256 `7b3c6c17031d7374f9597581b43d5b3f2e5344a2f176b72e3717738d97e9f0cf`.
Private status was verified after upload. No exam data, answer keys or secrets
were uploaded. Prior pilot/full-epoch backups remain unchanged.

Download only this adapter prefix and the aligned classifier, together with the
previously backed-up shared Bielik base and OCR weights. Do not mix adapter versions.
Use `revision="7c015a205cf7b45f0d8dc507430133ea447b3d44"` for those weights;
use the documentation commit for the updated manifest. Supply Hugging Face
authentication through a protected environment/token store, never source code.
Q4 aggregate weights:1,062,667,538bytes. Q8 variant:1,789,438,226bytes;
the new backup operation did not add a Q8 base copy.

Local evidence: `artifacts/small_track/hf-recovery-clean-v3.json`.
Local adapters: `artifacts/small_track/bielik15-real-boundary-clean-v3/adapters/`.
Local training manifest: `results/small_track/20260926-clean-v3-bielik15/manifests.json`.
Owned VM path: `/workspace/codex-small-track-clean-v3/output/clean-v3-full-epoch/`.
Versioned package configs: `infra/small_track/configs/bielik15-q4-real-five-adapter-boundary-clean-v3.json`
and correspondingQ8 config. Accuracy evaluation remains separate; backup completion
is not a claim that this candidate meets35%.

The full clean-v3 Q4 weight package is now also present on the Mac at
`artifacts/small_track/offline-bielik-clean-v3-q4/`:all nine weight files verified,
1,062,667,538bytes, zero missing. The weights manifest SHA256 is
`034420954f1c29cafa063829b0205eef2b77f7f3c71f538524172f284b00dae5`.
Its accompanying `run.py` completed a37-item structural dry run with original
image checksums and strict empty-answer export. This backup includes weights and
portable Python code; host-specific CUDA/llama/Tesseract binaries remain runtime
prerequisites, and the dry run is not measured exam accuracy.
