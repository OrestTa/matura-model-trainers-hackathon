# Forgehand L40S overnight logs (26–27 Sep 2026)

- `master_chain.log`: one line per start and end of every job the box ran (times in UTC).
- `consoles/`: stdout of each run. For the two llama-server logs (`v9-server.log` on :8100 and `essay-server.log` on :8101), only the last 3,000 lines are kept.
- The job scripts are in `infra/forgehand/local/`:
  - `main_v9.sh`: the :8100 queue.
  - `essay_arms_8101.sh`: the essay arms on :8101.
  - `p_arms_inline.sh`: the practice arms P1–P3.
  - `stage_rehearsal.sh` and `r2_e9.sh`: the stage rehearsals and essay best-of-5.
  - `sd1_merge.py` and `sd1_train.sh`: SD1 data merge, training and eval.
  - `watchdog*.sh`: restarts :8100 if it dies.
  - `patch*.py`: the queue edits applied to the running scripts.
  - `v9_shipper.sh`: the local results shipper. It refuses runs with more than 10% blank answers.
- RAM incident: the box has 30 GB of RAM and no swap. Two llama-servers, each with the default 8 GiB host prompt cache, triggered 3 out-of-memory kills (22:25–23:36Z). The fix is `--cache-ram 0 --load-mode none`.
