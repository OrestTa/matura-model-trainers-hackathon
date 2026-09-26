# Commit review log

Adversarial review of every commit on main (Claude review thread, for all agents incl. the Grok bot).
Newest first, dated. Each entry: commit(s), verdict, problems, and what was fixed or needs an owner.
Rules we review against (from docs/hackathon-brief.pdf): each model <= 8 GB on disk as run (LoRA does not count),
no internet/closed APIs at exam time, no copyrighted content in the repo (sources + fetch script instead),
SOURCE.md with the exact required line, graded work made from Fri 18:00.

## 2026-09-26 11:00 UTC: first pass, commits 33ef5cf..9081fad (24 commits)

- SOURCE.md: OK. Matches the brief's required line exactly (en dash in 25–27).
- 58d5dce docs/hackathon-brief.pdf: PROBLEM (owner: Orest). Page 9 has the venue door code, and the PDF is
  organiser material that should not be republished. Deleting it from HEAD is not enough: it stays in git
  history. Before the repo is shared with the jury, either keep the repo private and give the jury read access,
  or publish a fresh repo/squashed history without the PDF.
- Code review of the remaining commits in progress; results follow below.
