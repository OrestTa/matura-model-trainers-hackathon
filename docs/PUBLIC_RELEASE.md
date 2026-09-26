# Making the repo public (deadline 2026-09-27 11:00 CEST)

Audit on 2026-09-26 11:55Z of the tree and all 50+ commits of history.

## Done on main

- `docs/hackathon-brief.pdf` (venue door code on page 9, organiser document) removed from the tree.
- GPU VM IP removed from `docs/FINDINGS.md`; AWS account ID redacted in `infra/aws/AWS_INFRA.md`
  and `notes/AWS_INFRA.md`.
- `SOURCE.md` checked: the exact required line, byte for byte.
- `SOURCES.md` lists every dataset and model with its licence and fetch script.
- README opens with a reproduce section and points at `scripts/serve_exam.sh` (on-stage harness).
- `.gitignore` covers `secrets/`, `.env`, `*.env`, `.modal.toml`, `data/`, weights and adapters.

## Tree: clean

No tokens, private keys, passwords or TEAM_KEY in the tree. No exam papers, keys or corpora
(`examples/sample_questions.jsonl` is our own). `infra/aws/orest-noninteractive.pub` is a public
key only. Team name and GitHub handle appear on purpose.

## Still in git history (needs a rewrite to remove)

| What | Where it was | Risk |
|---|---|---|
| `docs/hackathon-brief.pdf` with the door code | added in 58d5dce | venue access code, organiser's file |
| GPU VM public IP | docs/STATUS.md, docs/FINDINGS.md, dashboard seed | VM is reachable over SSH |
| Second IP (localtunnel "password" IP) and a `*.loca.lt` URL | README / dashboard, later removed | tunnel is dead; IP identifies a host |
| AWS account ID | infra/aws/AWS_INFRA.md, notes/AWS_INFRA.md | low (not a credential) |

No tokens or private keys were found anywhere in history (searched for AWS, HF, GitHub,
OpenAI-style, Modal and PEM patterns).

## History-scrub plan (NOT run: Orest chose to leave history as is, 2026-09-26 12:36Z)

1. Pause writers: ask the Grok bot and all threads to stop pushing to main.
2. Fresh mirror clone, then with `git filter-repo` (pip install git-filter-repo):
   ```bash
   git clone --mirror https://github.com/OrestTa/matura-model-trainers-hackathon scrub.git && cd scrub.git
   git filter-repo --invert-paths --path docs/hackathon-brief.pdf
   cat > ../replace.txt <<'RULES'
   regex:\b(?!127\.0\.0\.1\b|0\.0\.0\.0\b)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b==><ip>
   regex:[a-z-]+\.loca\.lt==><tunnel>
   regex:(Account[^\n]{0,8})\d{12}==>\1<aws-account>
   RULES
   git filter-repo --replace-text ../replace.txt
   git log -p --all | grep -E 'loca\.lt|[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | grep -vE "127.0.0.1|0.0.0.0"   # expect nothing
   git push --force --mirror origin      # or: git push --force origin main
   ```
3. Everyone re-clones or runs `git fetch && git reset --hard origin/main` (the GPU VM checkout too).
4. Old commits stay reachable on GitHub by SHA for a while (and in any fork or PR ref).
   Deleting the brief from history is best effort; the door code should be treated as seen.

Alternative with no rewrite: publish a fresh repo containing only the current tree
(one squashed commit) and share that with the jury. Loses history but touches nothing
others are pushing to.

## Only Orest can do

- Rotate the Modal token, the GPU VM SSH key and the AWS console password (all were pasted in chat).
- Delete the AWS root access key (AWS console, Security credentials).
- Approve (or reject) the history scrub above.
- Make the repo public, or add the jury as readers, before 2026-09-27 11:00 CEST.
- Submit exam results for both the base model and the trained model.
