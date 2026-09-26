# Job status board (Track 01)

Updated: 2026-09-26 15:22 Europe/Warsaw (CEST)

## Hard caps

- Base on disk: **<= 8.0 GB**
- After FT: **<= 8.8 GB**

| Job | Platform | State | Notes |
|---|---|---|---|
| AWQ 7B download | box | **DONE** | 5.582 GB measured; legal |
| `cke_7b_awq_base` | Modal A10G | **DONE 37.6% / 38.9% text** | Best legal CKE |
| `cke_7b_awq_fh` | Modal | **RUNNING** | AWQ + Forgehand fh LoRA; do not cancel |
| Forgehand host verification | Forgehand L40S | **DONE** | SSH verified; L40S 46,068 MiB; GPU idle at check |
| AWQ sync to Forgehand | Forgehand L40S | **DONE** | Complete 5.582 GB pack present on VM |
| AWQ + fh LoRA offline CKE | Forgehand L40S | **DONE 29.8% / 32.1% text** | PID 5112; below bare AWQ 37.6%, so do not promote adapter |
| Forgehand oversize cancellation | Forgehand L40S | **STAGED** | Cancel script ready; never start 11B/bf16 exam path |
| CKE 3B + history-v2 | Forgehand | **DONE 28.3% / 31.3% text** | Prior result |
| CKE 7B bf16 | Forgehand | **DONE 37.1%** | Research only; illegal declared base |
| 7B fh/fh-v2 bf16 CKE | Forgehand | **CANCEL / DEMOTE** | Not a legal Sunday base |
| Bielik-11B DAPT/train/serve | Forgehand | **CANCEL / DEMOTE** | Over cap |

## Host access

Use `scripts/forgehand_ssh.sh` with `FORGEHAND_HOST` exported. No host address
is stored in this packet.

2026-09-26 15:25 CEST  
Official mock 3B DONE: `runs/official_mock_3b/answers.json` (`37/37`).
