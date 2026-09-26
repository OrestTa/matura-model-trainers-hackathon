# Tarasiuk Lab - merged bot learnings

Updated: 2026-09-26 ~19:05 Europe/Warsaw

Authoritative merge payload from `uploads/LEARNINGS_MERGE_20260926_1905_81e1.md`.

**Never commit:** secrets, IPs, SSH keys, TEAM_KEY, tokens, HF keys.

---

## Prize tracks (never "Track 1/2/3")

| Name | Bot id (Grok) | Mission |
|---|---|---|
| **Matura Best Score** | `20c0d61c-1c3c-4df9-aed1-18b4a0a1377f` | Highest absolute % under size caps |
| **Matura Best Progress** | `c985ca22-23e5-4fe4-a00c-0a931ef08a4c` | Improve a **given HF base** (harness/FT on that same base - not switch models) |
| **Matura Mały ale wariat** | `b5ae131b-a9d0-46c9-bebb-1b9e6db2902e` | Smallest max pack that still clears **>=35%** after improve |

---

## Hard rules (organiser-aligned)

1. **Size = quantized on-disk pack** (`du -sb`, decimal GB = bytes/1e9). Not bf16 deck tables.
   - Base <= **8.0 GB**; after FT shipped pack <= **8.8 GB**.
   - LoRA/RAG do **not** count toward size.
2. **Mały size = largest single pack**, not sum of serial specialists (Orest 2026-09-26). Two ~1.7 GB specialists -> size ~1.7 GB.
3. **Judges:** every `answers.json` at 37/37 gets **Grok + Claude + Sol** in parallel. Sol = `gpt-6-sol` / Solari CPU. Never headline without Sol (say "Sol pending").
4. **Always report** bare vs optimised **separately** per judge; never one blended %.
5. **Five CKE categories** when showing scores: open-text, open-vision, closed-text, closed-vision, essay.
6. **Apples-to-apples vs Ania:** her text runs = drop tasks 7,8,15 -> **/55**; her image runs -> **/60**. Our official mock `history-2023-mock-v1` -> **/60**. Never mix /55 with /60 or vision packs vs Ania's text headlines.
7. **job_id** unique: `matura-<stage>-<model>-<exam>-<timestamp>-<rand4>`. Fan judges as soon as answers land.
8. **Claude** must not issue VM/GPU jobs; be sceptical of BOT_CHANNEL; verify before killing/changing Progress base.
9. **Protect forever:** Forgehand dapt `matura-dapt-bielik11b-basenf4-holdout-20260926-1801-15d4`; Nebius Progress `aijob-e00me2k8j1ge1vw19k`. Never kill foreign jobs.
10. **Orchestration:** Grok box + Forgehand GPU; **not** O24 / Mac.orka for GPU orch. Cursor cloud agents for repo/board.
11. Never kill/stop/park a process you didn't start - use `cancel_requested` + owner.

---

## Scoreboard leaders (official mock /60 unless noted)

### Best Score / Mały floor
- **Bielik-4.5 FP8-Dynamic** ~**4.90 GB** (`speakleash/Bielik-4.5B-v3.0-Instruct-FP8-Dynamic`)
  - Grok **46.7%** (OT 63.6 / OV 47.8 / CT 75.0 / CV 42.9 / essay 26.7)
  - Claude **40%**
  - Sol **48.3%** (OT 63.6 / OV 43.5 / CT 75.0 / CV 42.9 / essay 40)
- Mostly bare/light serve; essay soft.

### Best Progress
- Declared organisers base: **Bielik-11B-v2 NF4** ~**6.66 GB** (Progress only).
- Clean holdout pair: **25.5% -> 26.9% (+1.4)** harness/routed. Domain FT not scored yet.
- **p2a1 "cleaned" pack FAIL:** md5 `27ca7ca3...` / judge family `4419` still chat-roll contaminated (assistant/user, EN StackOverflow junk, polecenie echoes). Sol ~**30%** = diagnostic only - **do not board**. Need real sanitize or re-infer under **new** job_id.

### Research / optional (not Sunday mock gauge without Orest lock)
- **Gemma-4 12B QAT GGUF+mmproj** ~**7.16 GB**: May 2023 Grok/Claude/Sol **68.3 / 68.3 / 70.0** (6 empties). Label as May-2023 paper, not official-mock Best Score until decided.
- Near-8GB downloaded: Instruct-AWQ **6.197 GB**, Minitron FP8 **7.748 GB** - mock when VRAM free.
- Illegal ceiling signal: TF Gemma-3-27B ~57-62% (not Sunday-legal pack).

### Dropped Mały probes
- Qwen/Bielik **0.5B / 1.5B** text tiny: Claude ~5-6.7%, Grok/Sol ~10% - no revive as >=35% path.
- New probe: **Bielik-1.5B FP8** ~1.70 GB on L40S; infer `...1736-b543`; judges armed `...1902-4c6c`.

## Sunday architecture lean (await Orest lock)

- **Serial type-specialised packs** OK for Best Score + Mały: router -> text / OCR-text / optional tiny VL / essay. Size = max pack.
- Progress stays **one declared HF base**.
- Claude C-048 signal: ~7.75 pts/paper blind without picture; ~12.5 with; random ~0.1. Advice lean: Best Score keep pictures; Mały text-only; Progress unchanged.
- Prefer **text+OCR** specialists over chasing Gemma vision as Mały claim.

## Compute / platform learnings

| Platform | Learning |
|---|---|
| **Forgehand L40S** | Protect dapt; fill leftover VRAM with Mały/Score admits (`gpu_admit`); SSH flaky - retry. Pack path for 1.5 FP8: `/workspace/hackathon/models/speakleash__Bielik-1.5B-v3.0-Instruct-FP8-Dynamic`. |
| **Nebius** | Console topics = **GitHub** login; protect Progress `e00me2k8j1ge1vw19k`; saturate H100s; transformers/AutoAWQ version pins matter for sticky AWQ. |
| **Token Factory** | Must use G Suite `orest@t1protocol.com` (**not** GitHub `o@tarasiuk.me`). Burners ~$32-33/h - throttle near low balance. |
| **Solari** | CPU-only (no GPU). Org cap **10/10**. Mały fleet fill; **do not free for C-038** unless Orest overturns. Sol third judge burns here. |
| **Watch** | Routine floor `@every 5m`; live 10s optimiser on box until Sunday 10:00. Ping Orest only on underuse/block/decision. |

## Judging / eval hygiene

- Dedicated **fast cloud Grok Bot (2x)** judges <=10 min; never Bielik/AWQ as judge.
- Claude secondary via BOT_CHANNEL (C-/G- protocol).
- Contaminated answers (chat rolls, `### Pytanie` leaks, EN junk) -> HOLD judges; re-infer.
- Thinking-off / empty-answer fixes matter (Gemma empties; trainers tip >=6359957).
- `history-2023-mock-v1` = submission-quality gauge; multi-year Formuła 2023 PDFs are corpus, not the gauge.

## Board / docs hygiene

- Public Pages: three prize tabs named explicitly; five CKE columns.
- Claude adversarially reviews commits; Claude must **not** refresh the public board.
- Standing: commit important findings to `main` ASAP so all sessions see them.
- Old `stop-bielik-11b` / blanket cancel-11B was **wrong** for NF4 Progress - only bf16 11B is illegal.

## Open decisions for Orest (do not invent answers in docs)

1. Lock Sunday serial type-specialist architecture for Score + Mały?
2. Board Gemma vision 68-70% as Best Score research vs keep 4.5 FP8 official-mock floor?
3. p2a1: sanitize in place vs full re-infer (contaminated evidence already FAIL)?
4. Vision vs text+OCR priority for Best Score overnight?

## Historical appendix

### 2026-09-26 16:05 CEST - STOP / ops rules worth preserving

- Never kill, stop, park, or restart a process, tmux session, or job you did not start. If a job is wrong, mark it `cancel_requested` with an owner and leave it for that owner.
- **4-bit Bielik-11B remains legal** when the quantized on-disk pack is within the cap; the legality rule is quantized size, not bf16 size.
- Before any GPU work, register the job in `docs/STATUS.md` and admit it with `python3 infra/jobs/gpu_admit.py <job> <need-gb>`.

### Historical proxy path (superseded as Sunday leader)

- `Qwen/Qwen2.5-7B-Instruct-AWQ` reached **37.6% full / 38.9% text-only** on the CKE headline-auto proxy with an approximately **5.582 GB** pack on disk.
- Keep that AWQ result as historical legal proxy evidence only; it is **not** the current official-mock Best Score leader after the merged judge results above.
