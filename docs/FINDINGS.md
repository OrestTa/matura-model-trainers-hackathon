# Findings

Shared log for every bot and person on this repo. Newest first, dated, one short entry per finding.
Pull before you add, commit straight to main.

## 2026-09-26 12:35 CEST: Grok bot results live only in its chat

- The Grok bot reported these numbers in its chat, which is all we have for them:
  - Bare Qwen 3B scored 4/15 on the practice geo set with no formulas and no RAG. Only GEO-006, GEO-019, GEO-028 and GEO-029 were correct.
  - Qwen 1.5B scored 3/15 on the same set.
  - The practice run filed at 14/15 was almost all harness. Report a true bare base on Sunday or the progress score is misleading.
  - Also mentioned: history LoRA v2, a size-track 1.5B check, and a GEO-025 retry at 10:35.
- None of these runs, logs or files exist on Orest's Mac, in the `ai-sandbox-visual-grokbot` Docker container or in this repo's history as of 12:35. Grok Bot runs them in its own cloud sandbox.
- This "Grok Bot" build talks to Cursor's backend (`api2.cursor.sh`). Transcripts are stored server-side, and there is no API or export.
- Its local logs (`~/.grokbot/local-exec-daemon.log`, container `launch.log`) record only the helper process and connection errors, never commands, scores or paths.
- **Ask for:** Grok bot, commit each run's scores (per item where possible) plus the exact model and command to `results/grok/` here, so other bots can check and reuse them.
- Access notes: `http://127.0.0.1:3080` is a noVNC desktop viewer for the container, not a chat API. SSH on port 2223 currently fails because `/config/.ssh` is owned by uid 911 instead of abc (1000). The fix is `chown -R abc:abc /config/.ssh`, and `cont-init-sshd` should use `$PUID:$PGID`. `docker exec -it ai-sandbox-visual-grokbot-desktop-1 bash` works.

## 2026-09-26 · Eval set from real CKE papers (eval-set thread)

- `python scripts/fetch_matura.py` builds `data/eval/matura.jsonl` from the May 2023–2026 historia
  (rozszerzony) papers and official keys: 154 items, 4 × 60 = 240 points. Every paper parses to exactly
  60 points, and every official key scores full marks against `matura_router/scoring.py`.
- **85 of 154 items need a picture** (map, photo, poster, plan, stamp) that a text model only sees as
  `[ilustracja – niedostępna w wersji tekstowej]`. Flag: `needs_image`; `--text-only` drops them.
  A text-only model has a hard ceiling well below 100% on the full paper.
- **The exam is mostly source analysis.** Gold types: source_analysis 109, short_open 13, true_false 12,
  closed_choice 12, matching 4, essay 4 (15 pts each, 25% of the paper), **chronology 0**. Formuła 2023
  papers have no ordering tasks, so a chronology adapter buys nothing on this exam.
- **52 items are "Rozstrzygnij … uzasadnij"** (verdict + justification, 1 pt only if both are right).
  This is the single most common task shape and may deserve its own prompt/adapter. The bare expected
  verdict is in the `decision` field.
- Rule classifier vs gold types: all closed/essay types routed correctly; 13 of 109 source_analysis
  items go elsewhere (5 general, 5 short_open, 2 closed_choice, 1 chronology).
- ~60 items are auto-scorable (closed keys + `gold_keywords`); the rest need the judge.
- Scorer gap: `scoring._pairs` only reads "1 – B". Letter-keyed matching keys ("Fragment A – Karol IX",
  "A – 3") are therefore emitted as `gold_keywords` instead of `gold`.
- Older formuła 2015 papers (2015–2022) are not included; they have more closed/chronology items and
  could serve as extra training data, not as a faithful eval.
