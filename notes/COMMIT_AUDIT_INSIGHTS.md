# COMMIT_AUDIT (Grok bot), landed from issue #6

The Grok bot's adversarial audit, copied from issue #6 at its request (its full notes/COMMIT_AUDIT.md
lives on its box). Status of each item after the Claude review (docs/REVIEW.md), 2026-09-26 13:00 UTC:

| ID | Severity | Item | Status |
|----|----------|------|--------|
| CA-01 | RED | Practice "base" filing (14/15) used the geo harness; bare local ~4/15 | Open. Sunday: file the base as `--modes raw` of the shipped model, no solver, no baked answers. |
| CA-02 | RED | Size cap confusion | Resolved for current status notes: use base <= 8.0 GB and after fine-tuning <= 8.8 GB, with measured sizes only. |
| CA-03 | RED | `bielik-11b-bf16` (22.4 GB) in `MODELS=all` | Fixed: `all` skips `-bf16` keys (run_baselines.py). |
| CA-04 | YELLOW | History LoRA scored on its own 90 training MCQs | Open. Never quote these as matura results; the headline is data/eval/matura.jsonl. |
| CA-05 | YELLOW | AWS scripts still callable | Fixed: infra/aws/launch.sh refuses unless AWS_REENABLED=1. |
| CA-06 | YELLOW | Ops leakage (IP, AWS account, workspace UUID) | Partly: tunnel URL and IPs removed from README/dashboard; the VM IP stays in FINDINGS for the agents and in history. Keep the repo private; give the jury read access. |
| CA-07 | YELLOW | `.gitignore` gap | Fixed (secrets/, .env, *.env, .modal.toml, .run-venv/). |
| CA-08 | YELLOW | Two stacks, two bases (registration = Qwen2.5-3B) | Open, Orest to decide the declared base once. |
| CA-09 | INFO | 85/154 items need images; chronology adapter useless | Noted; summaries report pct_text_only and pct_all_rows. |
| CA-10 | INFO | Modal/Forgehand runners fragile | Noted. |

Checklist from the audit: agree the Sunday base once; Grok keeps bare numbers in results/ or `STATUS.md`;
one Modal story in docs/HOWTO.md (modal_lora_train.py vs infra/modal/modal_job.py) is still open.
