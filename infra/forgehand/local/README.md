# Running on the Forgehand box's local disk (/scratch)

Since ~18:31 CEST on 26 Sep, /workspace and /team (NFS) on session 01a0ddc1 answer "Permission denied"
(same fault as 14:30 CEST; a session restart fixed it then). These scripts run everything from local /scratch:

- `fhput.py <local> <remote>`: copy a file onto the box through the Jupyter terminal (base64 lines; ~1 MB/s).
- `fhx.py exec '<cmd>'`: run a command on the box (cwd /scratch). Needs `fh login` first.
- `setup_box.sh`: unpack `git archive` of main into /scratch/repo, uv venv (vLLM 0.27.1 + training stack) at
  /scratch/work/venv-py312, and a llama-server wrapper that finds the CUDA libs from the pip nvidia wheels.
- `gemma_chain.sh`: best-score chain on the 4 held-out papers, serial (rehearsal.sh owns port 8000):
  gemma4-12b raw, routed, gemma4-12b-text raw (pictures A/B), gemma4-12b-think routed. Out: /scratch/out/<job_id>/.

HF cache: /scratch/hf (token in /scratch/hf/token, never committed).
