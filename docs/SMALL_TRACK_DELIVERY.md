# Delivery by 2026-09-26 20:33 UTC / 22:33 Warsaw

This is a delivery deadline, not a promise of a passing score. Isolated worktree;
no fetch or push; no Forgehand GPU or modifications to Claude's Nebius work.

Priority sequence, overlapping where dependencies permit:

1. Complete paired base/SFT inference and official-key grading, including Sol
   second opinion and Codex adjudication. Preserve original Q4 baseline.
2. Finish 100 accepted synthetic exams with reproducible training splits.
3. Evaluate visual preprocessing separately on the canonical organizer JSON and
   checksum-verified PNGs. Text-only results remain explicitly labeled ablations.
4. Select per-category configurations on development results, serialize routing,
   freeze it, then evaluate on papers excluded from this synthesis. Prior model
   exposure to these papers is unknown.
5. Package runner, route configuration, model/adapter hashes and measured bytes,
   dataset manifests, scorecards and strict answers.json exporter. Report any
   missing capabilities honestly; no external submission without user instruction.

Operational checkpoints: paired SFT outputs by 18:50 UTC; canonical visual trial
by 19:20; route candidates by 19:50; frozen route evaluation by 20:10; packaging
by 20:25. Stop exploratory launches at 20:00. These are planning targets.

Concurrency: four agent slots total. Cloud inference/training workers and API
requests run concurrently within explicit caps; synthetic generation uses up to
16 workers and second-opinion grading up to eight. Active monitoring 15–30s;
read-only heartbeat every minute. Higher concurrency must improve throughput,
not simply spend credits faster.

API budget: combined incremental Forgehand ceiling $35, retaining at least $10
available credit, accounting for team-wide usage. No top-ups or cash spillover.
Modal uses the existing bounded $20 allocation and must check remaining credits
before expansion. Preserve outputs on persistent volumes at completion/checkpoints.
