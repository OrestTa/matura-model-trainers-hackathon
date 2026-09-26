# Job status

Live table of GPU jobs, one row per job, newest first. Written by
`infra/jobs/status.py` (the job wrappers call it); pull before reading.
Times are UTC.

Policy note (2026-09-26): Sunday declared base must stay <=8.0 GB on disk and
<=8.8 GB after FT/shipping. Treat Bielik-11B bf16 and Qwen2.5-7B bf16-as-base
lanes as cancelled; prefer Qwen2.5-3B or a quantized 7B.

| job | what | where | state | started | updated | out | owner |
|---|---|---|---|---|---|---|---|
| cke_7b_fh | CKE eval Qwen2.5-7B + forgehand-lora-7b-fh, routed (~20 GB) | Forgehand L40S, tmux gpu_par | running (~15.3 GiB VRAM; started after 3B wave freed room) | 2026-09-26 12:13 | 2026-09-26 12:13 | runs/history_eval/cke_7b_fh.json | Grok bot |
| cke_3b_history_v2 | CKE eval Qwen2.5-3B + history-v2 LoRA, routed, matura.jsonl (~9 GB) | Forgehand L40S, tmux gpu_par (MPS+budget scheduler) | running (parallel with cke_7b_fh) | 2026-09-26 12:02 | 2026-09-26 12:13 | runs/history_eval/cke_3b_history_v2.json | Grok bot |
| gpu_par | scripts/gpu_parallel_jobs.sh queue-worker: MCQ/CKE wave on one L40S (MPS + reserved MiB) | Forgehand L40S, tmux gpu_par | running (live: cke_3b_history_v2 + cke_7b_fh; queue: cke_7b_fh_v2 @20 GB) | 2026-09-26 11:42 | 2026-09-26 12:13 | runs/history_eval/parallel/ | Grok bot |
| cke_7b_fh_v2 | CKE eval Qwen2.5-7B + forgehand-lora-7b-fh-v2, routed (~20 GB) | Forgehand L40S, gpu_par queue | queued: after cke_7b_fh / history_v2 free ~20 GB | 2026-09-26 11:42 | 2026-09-26 12:13 | runs/history_eval/cke_7b_fh_v2.json | Grok bot |
| cke_3b_modal_v3 | CKE eval Qwen2.5-3B + modal-3b-v3 LoRA, routed, matura.jsonl (~9 GB) | Forgehand L40S, tmux gpu_par | completed (scored 60/154, 12/70=17.1%) | 2026-09-26 11:43 | 2026-09-26 12:13 | runs/history_eval/cke_3b_modal_v3.summary.json | Grok bot |
| cke_3b_base | CKE eval Qwen2.5-3B base, routed, matura.jsonl (~9 GB) | Forgehand L40S, tmux gpu_par | completed (scored 60/154, 18.67/70=26.7%) | 2026-09-26 11:45 | 2026-09-26 12:13 | runs/history_eval/cke_3b_base.summary.json | Grok bot |
| cke_7b_base | CKE eval Qwen2.5-7B base, routed, matura.jsonl (was ~20 GB) | Forgehand L40S, tmux gpu_par | completed (scored 60/154, 26/70=37.1%) | 2026-09-26 11:44 | 2026-09-26 12:13 | runs/history_eval/cke_7b_base.summary.json | Grok bot |
| mcq_7b_fh_v2 | history MCQ 90: Qwen2.5-7B + fh-v2 LoRA (train-overlap risk) | Forgehand L40S, tmux gpu_par | completed (89/90 = 98.9%) | 2026-09-26 11:44 | 2026-09-26 12:13 | runs/history_eval/mcq_7b_fh_v2.summary.json | Grok bot |
| mcq_7b_fh | history MCQ 90: Qwen2.5-7B + fh LoRA (train-overlap risk) | Forgehand L40S, tmux gpu_par | completed (90/90 = 100%) | 2026-09-26 11:43 | 2026-09-26 12:13 | runs/history_eval/mcq_7b_fh.summary.json | Grok bot |
| mcq_7b_base | history MCQ 90: Qwen2.5-7B base | Forgehand L40S, tmux gpu_par | completed (69/90 = 76.7%) | 2026-09-26 11:42 | 2026-09-26 12:13 | runs/history_eval/mcq_7b_base.summary.json | Grok bot |
| dl7b | download Qwen/Qwen2.5-7B-Instruct into HF hub cache for CKE/MCQ | Forgehand L40S, tmux dl7b | completed (download exit 0; irrelevant for further GPU) | 2026-09-26 11:42 | 2026-09-26 12:13 | HF hub cache Qwen2.5-7B-Instruct | Grok bot |
| grok-lora-7b-fh-v2 | Grok bot: harness/forgehand_lora_train.py --model-size 7b, 80 rows, tag lora-7b-fh-v2, 2000 steps | Forgehand L40S, tmux train | completed (TRAIN_V2_EXIT:0; adapter forgehand-lora-7b-fh-v2) | 2026-09-26 11:06 | 2026-09-26 12:13 | runs/lora/forgehand-lora-7b-fh-v2 | Grok bot |
| baselines-all2 | baselines, all 16 papers, bielik-11b + qwen3-8b + qwen3-1.7b side by side (gated models need HF_TOKEN) | Forgehand L40S | setting up (Python 3.12 venv) | 2026-09-26 12:05 | 2026-09-26 12:05 | /workspace/work/out/baselines-all2 | Modal compute setup thread |
| dapt-bielik | dapt DAPT_MODEL=bielik-11b DAPT_TOKENS=10000000 CORPUS=/workspace/work/corpus | Forgehand L40S | cancelled: oversize under Sunday 8.0/8.8 GB rule (Bielik-11B bf16 lane) | 2026-09-26 11:46 | 2026-09-26 11:51 | /workspace/work/out/dapt-bielik | Polish Wikipedia thread |
| baselines-all | baselines, all 16 papers (573 items), models side by side, no judge | Forgehand L40S | failed: vLLM 0.27.1 flashinfer import error on Python 3.11; replaced by baselines-all2 | 2026-09-26 11:46 | 2026-09-26 12:05 | /workspace/work/out/baselines-all | Modal compute setup thread |
| dapt-prep | dapt PREP_ONLY=1 CORPUS=/workspace/work/corpus | Forgehand L40S | running | 2026-09-26 11:41 | 2026-09-26 11:41 | /workspace/work/out/dapt-prep | Polish Wikipedia thread |
| router-ablation | bielik-11b MODES=raw,routed,rag on headline eval (needs data/kb from build_kb.py); measures template+voting+RAG gains | next free GPU | queued: wants a GPU after labqoat-baselines | 2026-09-26 11:13 | 2026-09-26 11:13 | work/out/router-ablation | Question router thread |
| train-bielik-l40s | train TRAIN_MODELS=bielik-11b-dapt VLLM_UTIL=0.8 | Forgehand L40S | cancelled: downstream of oversize Bielik-11B bf16 lane | 2026-09-26 10:58 | 2026-09-26 12:05 | /workspace/work/out/train-bielik-l40s | Modal compute setup thread |
| labqoat-baselines | baselines on all 16 papers (matura_all.jsonl, 573 items), no judge | Forgehand L40S | cancelled 12:31 (stale copy; old code incl. bielik-11b-bf16 22 GB, over the 8.0 GB base limit) | 2026-09-26 10:58 | 2026-09-26 12:30 | /workspace/work/out/labqoat-baselines | Modal compute setup thread |
