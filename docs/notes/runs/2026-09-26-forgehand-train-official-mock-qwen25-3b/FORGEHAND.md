# Forgehand (Labqoat) - CLI setup

**Checked:** 2026-09-26 ~12:42 Europe/Warsaw (CEST)  
**App:** https://app.forgehand.app  
**Role:** hackathon GPU compute path (AWS suspended - ignore AWS; Modal is the
other path)

## CLI install (done on this box)

| Item | Value |
|------|--------|
| Node | **v24.21.0** via nvm (`nvm use 24`; unset `NPM_CONFIG_PREFIX` first) |
| Package | `@qforge/forgehand@0.3.3` (npm latest as of check) |
| Binary | `fh` / `forgehand` at `~/.nvm/versions/node/v24.21.0/bin/fh` |
| Config | default `~/.config/forgehand/config.json` (not written - auth failed) |

```sh
unset NPM_CONFIG_PREFIX
export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
nvm use 24
# Auth (PAT from Settings -> Access tokens; do not commit):
```

## `fh` command surface (0.3.3)

- `fh login [--url URL] [--token fh_...]` - email OTP or PAT
- `fh whoami` - email + teams
- `fh ssh-key ls|add|rm` - account SSH keys (installed as `root` on sessions)
- `fh workspaces` / `fh workspace create <team> <name> [--image REF]`
- `fh classes` - compute classes + prices (team-restricted marked `*`)
- `fh session start <workspace> [--class SLUG] [--wait]`
- `fh session ls [<workspace>] [--all]` / `stop` / `ssh` / `jupyter`
- `fh port expose <session> <port> [--public]` / `fh port rm`
- `fh skills list|install` - agent skills (no login required)
- `--json` for machine-readable output

## Intended launch (once auth works)

Prefer **one** max GPU session within team/free credit limits (not multiple):

1. `fh whoami` - confirm team membership (hackathon team credits via
   Labqoat/Nebius).
2. `fh ssh-key ls` - expect label **Orest-Noninteractive** already on account.
3. `fh classes` - pick the largest GPU slug allowed for the team / remaining
   credits (README example: `gpu-l4`; actual max may be higher - use live
   `fh classes` + Usage page).
4. `fh workspaces` - use existing workspace or
   `fh workspace create <team-slug> <name>`.
5. `fh session start <workspace> --class <largest-allowed-gpu> --wait`
6. Connect: `fh session ssh <session>` or `fh session jupyter <session>`.
7. Stop when done: `fh session stop <session>` (compute bills until stop).

Usage/credits: web **Usage** page (monthly compute + separate LLM prepaid). CLI
has no spend-total command; `fh session ls --all` shows session costs;
`fh classes` shows rates.

Organizer FAQ: log in at app.forgehand.app, add team, get a machine; Nebius +
Labqoat provide team compute credits.

## SSH

- Public key on box: `/workspace/hackathon/secrets/orest-noninteractive.pub`
  (comment/label **Orest-Noninteractive**).
- User states this key is already registered on the Forgehand account -
  **not re-verified** (CLI auth blocked).
- Do not re-upload unless `fh ssh-key ls` shows it missing after a successful
  login.

## Auth attempt (blocked)

| Check | Result |
|-------|--------|
| `fh login --token ...` | Failed |
| Example requestId | `eb6d5abf-404a-4f9c-948d-264fa5d38ae3` (also seen: `20e26811-...`, `dd7aee4d-...`) |
| `fh whoami` / `classes` / `workspaces` / `session ls` | All blocked (not logged in) |
| Browser OTP | Failed earlier (wrong code) - not retried here |

**No config.json written** (avoids persisting a rejected token).  
**No session/VM launched.**

### Unblock

1. Sign in at https://app.forgehand.app (email OTP or working method).
2. **Settings -> Access tokens** - create a new personal access token (shown once).

If the stored value was truncated/copied wrong, a fresh PAT is required - the
current file is rejected by the API as unauthenticated.

## Status summary

| Field | Value |
|-------|--------|
| CLI version | **0.3.3** |
| Usage/credits | **Unknown** (auth required) |
| Launched VM | **None** |

## Live session - matura-hack (checked 2026-09-26 12:45 Europe/Warsaw)

The existing team session was confirmed in the Forgehand UI; no new GPU session
was started.

| Field | Value |
|-------|-------|
| Workspace | `matura-hack` |
| Compute | `gpu-l40s-small` - 1x L40S 48 GB |
| Status | Running |
| SSH host/IP | `<previous Forgehand host>` |
| SSH username | `root` |
| Connect command | `ssh -i /workspace/hackathon/secrets/orest-noninteractive root@<previous Forgehand host>` |
| Session ID | `01a0dd4b-7179-72b4-a089-bb38eec8c18a` |

The Forgehand session detail page exposed the command above and session ID (the
ID is the `/sessions/<id>/go` target of its Open JupyterLab link).

### SSH verification (done 2026-09-26 ~12:49 Europe/Warsaw / CEST)

**Verified** with private key `/workspace/hackathon/secrets/orest-noninteractive`
(mode 600; never printed/committed). Connect via paramiko Ed25519Key or
`ssh -i ...` (openssh-client now on box).

| Check | Result |
|-------|--------|
| Host | `root@<previous Forgehand host>` |
| GPU | NVIDIA L40S 46068 MiB (driver 595.91.07, CUDA 13.2) |
| Disk | `/` ~139G free; `/workspace` NFS persist |
| Python | 3.11.14 at `/scratch/.venv/bin/python3` |
| Torch | 2.9.1+cu128, `cuda=True`, device NVIDIA L40S |
| Train deps | transformers 4.46.3, peft 0.13.2, accelerate 1.1.1 (installed on VM) |

Screenshot of the session detail page:
`/home/box/agent-data/agents/4cd1cf76-c1e3-4209-8473-cfce2d7a170c/assets/429e01d739260ca4d7186fb40cb1b2a045bf1ad950775583d5690e67e492253e.png`

### Active training (started ~12:49 CEST)

Synced (no secrets): `data/history/history_mcq_v1.jsonl`,
`harness/forgehand_lora_train.py` (+ train/modal scripts, notes). HF cache on VM:
`/workspace/hf` (~15G Qwen2.5-7B).

| Field | Value |
|-------|--------|
| Model | `Qwen/Qwen2.5-7B-Instruct` bf16 LoRA r=16 alpha=32 |
| Data | history MCQ 90 rows, max_steps=300, epochs=4 |
| VRAM | ~16945 MiB / 46068 (no OOM; 3B fallback unused) |
| tmux | session `train` |
| PID | **184** (`python3 -u harness/forgehand_lora_train.py ...`) |
| Log | **`/workspace/matura/train.log`** (also `runs/lora/forgehand-lora-7b-fh/live.log`) |
| Adapter out (VM) | **`/workspace/hackathon/runs/lora/forgehand-lora-7b-fh/`** |
| Exam path later | GPTQ-Int8 base `Qwen/Qwen2.5-7B-Instruct-GPTQ-Int8` + this adapter |

Train command (inside tmux on VM):

```sh
cd /workspace/hackathon
export PYTHONUNBUFFERED=1 HF_HOME=/workspace/hf TOKENIZERS_PARALLELISM=false
python3 -u harness/forgehand_lora_train.py \
  --model-size 7b --max-steps 300 --epochs 4 --lora-r 16 --lora-alpha 32 \
  2>&1 | tee -a /workspace/matura/train.log
```

Log evidence (loss falling): step 1 loss 2.7918 -> step 100 loss 0.5884 ->
step 140 loss 0.2367 (still running toward 300).

Pull adapters back to box when done:

```sh
# once openssh works; else paramiko SFTP
scp -i /workspace/hackathon/secrets/orest-noninteractive -r \
  root@<previous Forgehand host>:/workspace/hackathon/runs/lora/forgehand-lora-7b-fh/ \
  /workspace/hackathon/runs/lora/forgehand-lora-7b-fh/
# or: rsync -avz -e 'ssh -i /workspace/hackathon/secrets/orest-noninteractive' \
#   root@<previous Forgehand host>:/workspace/hackathon/runs/lora/forgehand-lora-7b-fh/ \
#   /workspace/hackathon/runs/lora/forgehand-lora-7b-fh/
```

Do **not** start a second Forgehand GPU. AWS remains suspended.

## Live session (2026-09-26)

**Updated:** ~12:45 Europe/Warsaw (from Matura Hack browser login)

| Field | Value |
|-------|--------|
| Account | `o@tarasiuk.me` |
| Team | `rst` |
| Compute spend | **$0.21 / $200** this month |
| GPU concurrency | **1 / 1** (do not start a second GPU) |
| CPU concurrency | 0 / 0 |
| LLM prepaid | $50 granted, $0 spent (separate from compute) |
| Active session | **matura-hack** |
| Class | `gpu-l40s-small` - 1x L40S 48 GB, 4 vCPU, 32 GB RAM, **$1.86/h** |
| Image | `.../forgehand/base:cuda` (CUDA base) |
| Workspace note | `gpu-max` was created but cannot start another GPU until matura-hack stops |
| SSH | `ssh -i /workspace/hackathon/secrets/orest-noninteractive root@<previous Forgehand host>` (matura-hack; IP changes on restart) |
| JupyterLab | Open from session row in the web UI |

### Operating rule

Use the existing **matura-hack** L40S for training. Do **not** stop it without
coordinating. Do **not** launch a second GPU.

### Connect (once IP known)

```sh
# From session row copy:
ssh root@<ip>
# Then:
cd /workspace
nvidia-smi
```

Sync training code/data onto the VM via `scp`/`rsync` or Jupyter upload into
`/workspace` (persist) or stage heavy IO on `/scratch`.

Preferred box key for this session:
`/workspace/hackathon/secrets/orest-noninteractive` (Orest-Noninteractive).
Alternate: `~/.ssh/id_ed25519_forgehand` if registered.

### Box SSH keys (2026-09-26)

- Registered **Forgehand-Train-box** (`~/.ssh/id_ed25519_forgehand`,
  SHA256:kXxyLAPmNN+qHMeU1F5uO0jtEjPYdLcUXEu2cix6U+g).
- Working deploy key: `/workspace/hackathon/secrets/orest-noninteractive`
  (registered as **maturahack**; same fingerprint as derived pub).

## SSH status - size-cap enforcement (2026-09-26 14:34 Europe/Warsaw (CEST))

| Field | Value |
|-------|-------|
| Session | matura-hack / `01a0dd4b-7179-72b4-a089-bb38eec8c18a` / **running** |
| API + UI SSH IP | **<previous Forgehand host>** (unchanged) |
| From box | TCP 22 connects -> **kex Connection reset by peer** (no banner) |
| Action | Session **not** stopped; VM work via JupyterLab computerUse |

## Live session - new IP (2026-09-26 ~14:53 Europe/Warsaw)

| Item | Value |
|------|--------|
| SSH | `ssh -i /workspace/hackathon/secrets/orest-noninteractive root@${FORGEHAND_HOST}` |
| Previous IP | `<previous Forgehand host>` (kex reset; abandoned) |
| GPU | L40S idle at first connect |
| Size cap | STOP notes on VM; no Bielik jobs |
