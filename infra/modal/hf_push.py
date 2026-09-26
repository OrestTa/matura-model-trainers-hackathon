"""Backs up LoRA adapters from the Modal volume to private Hugging Face repos (for recovery).

    modal run infra/modal/hf_push.py --jobs gemma-lora-B4m2,gemma-lora-Gm2

Uploads matura-jobs:out/<job>/adapters/ (PEFT files + adapter.gguf per route) to the private
model repo orestta/matura-gemma4-12b-lora-<job minus the gemma-lora- prefix>. The token comes
from the Modal secret `claude-hf` (HF_TOKEN); it never touches the repo.
"""
import modal

volume = modal.Volume.from_name("matura-jobs")
app = modal.App("claude-hf-push", image=modal.Image.debian_slim().pip_install("huggingface_hub"))


@app.function(volumes={"/vol": volume}, secrets=[modal.Secret.from_name("claude-hf")], timeout=1800)
def push(job: str) -> str:
    from pathlib import Path
    from huggingface_hub import HfApi
    volume.reload()
    src = Path(f"/vol/out/{job}/adapters")
    if not any(src.rglob("adapter_config.json")):
        return f"{job}: no adapters yet"
    repo = f"orestta/matura-gemma4-12b-lora-{job.removeprefix('gemma-lora-')}"
    api = HfApi()
    api.create_repo(repo, private=True, exist_ok=True)
    api.upload_folder(repo_id=repo, folder_path=str(src), commit_message=f"{job} adapters")
    return f"{job}: https://huggingface.co/{repo}"


@app.local_entrypoint()
def main(jobs: str):
    for line in push.map(jobs.split(",")):
        print(line)
