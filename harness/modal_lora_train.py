#!/usr/bin/env python3
"""Modal GPU LoRA SFT for Warsaw Model Trainers / Tarasiuk Lab hackathon.

Reuses volume `model-training-workshop` under prefix `matura/`.
Ephemeral runs via:  modal run harness/modal_lora_train.py --model-size 3b
                     modal run harness/modal_lora_train.py --model-size 1.5b
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import modal

APP_NAME = "matura-lora-sft"
VOLUME_NAME = "model-training-workshop"
VOL_MOUNT = "/persist"
DATA_LOCAL = Path(__file__).resolve().parents[1] / "data" / "history" / "history_mcq_v1.jsonl"

MODELS = {
    "3b": {
        "hf_id": "Qwen/Qwen2.5-3B-Instruct",
        "out_dir": "matura/lora-3b-v3",
        "tag": "lora-3b-v3",
    },
    "1.5b": {
        "hf_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "out_dir": "matura/lora-1.5b-v1",
        "tag": "lora-1.5b-v1",
    },
}

# Pin reasonable, compatible stack (CUDA 12 / torch 2.4+)
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.5.1",
        "transformers==4.46.3",
        "peft==0.13.2",
        "accelerate==1.1.1",
        "safetensors==0.4.5",
        "sentencepiece==0.2.0",
        "protobuf==5.28.3",
        "huggingface_hub==0.26.2",
        "numpy==2.1.3",
    )
    .env({"HF_HOME": f"{VOL_MOUNT}/hf", "TRANSFORMERS_CACHE": f"{VOL_MOUNT}/hf"})
)

# Ship the 90-row MCQ jsonl into the image so we don't depend on volume put
image = image.add_local_file(
    str(DATA_LOCAL),
    remote_path="/data/history_mcq_v1.jsonl",
)

app = modal.App(APP_NAME)
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=False)


def _train_impl(
    model_size: str,
    max_steps: int,
    epochs: int,
    lr: float,
    lora_r: int,
    lora_alpha: int,
    gpu_name: str,
) -> dict[str, Any]:
    import time
    import traceback

    import torch
    from peft import LoraConfig, get_peft_model
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, get_linear_schedule_with_warmup

    cfg = MODELS[model_size]
    out_rel = cfg["out_dir"]
    out_path = Path(VOL_MOUNT) / out_rel
    out_path.mkdir(parents=True, exist_ok=True)
    log_path = out_path / "live.log"

    def p(msg: str) -> None:
        print(msg, flush=True)
        with log_path.open("a") as f:
            f.write(msg + "\n")

    data_path = Path("/data/history_mcq_v1.jsonl")
    rows = [json.loads(l) for l in data_path.read_text().splitlines() if l.strip()]
    p(
        f"start tag={cfg['tag']} model={cfg['hf_id']} rows={len(rows)} "
        f"gpu={gpu_name} cuda={torch.cuda.is_available()} "
        f"device={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'} "
        f"r={lora_r} alpha={lora_alpha} max_steps={max_steps} epochs={epochs} lr={lr} bf16=1"
    )

    try:
        tok = AutoTokenizer.from_pretrained(cfg["hf_id"], trust_remote_code=True)
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token

        dtype = torch.bfloat16
        model = AutoModelForCausalLM.from_pretrained(
            cfg["hf_id"],
            torch_dtype=dtype,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        model.gradient_checkpointing_enable()
        lora = LoraConfig(
            r=lora_r,
            lora_alpha=lora_alpha,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        )
        model = get_peft_model(model, lora)
        model.print_trainable_parameters()
        model.train()

        class DS(Dataset):
            def __init__(self, rows_: list[dict[str, Any]]):
                self.rows = rows_

            def __len__(self) -> int:
                return len(self.rows)

            def __getitem__(self, i: int) -> dict[str, Any]:
                text = tok.apply_chat_template(
                    self.rows[i]["messages"],
                    tokenize=False,
                    add_generation_prompt=False,
                )
                enc = tok(
                    text,
                    truncation=True,
                    max_length=512,
                    padding="max_length",
                    return_tensors="pt",
                )
                input_ids = enc["input_ids"][0]
                labels = input_ids.clone()
                labels[labels == tok.pad_token_id] = -100
                return {
                    "input_ids": input_ids,
                    "attention_mask": enc["attention_mask"][0],
                    "labels": labels,
                }

        loader = DataLoader(DS(rows), batch_size=1, shuffle=True)
        opt = torch.optim.AdamW(
            (p_ for p_ in model.parameters() if p_.requires_grad), lr=lr
        )
        planned = min(max_steps, epochs * len(loader))
        sched = get_linear_schedule_with_warmup(opt, max(1, planned // 10), planned)

        t0 = time.time()
        step = 0
        losses: list[float] = []
        for epoch in range(epochs):
            for batch in loader:
                if step >= max_steps:
                    break
                device = next(model.parameters()).device
                batch = {k: v.to(device) for k, v in batch.items()}
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    out = model(**batch)
                    loss = out.loss
                loss.backward()
                opt.step()
                sched.step()
                opt.zero_grad()
                losses.append(float(loss.detach()))
                step += 1
                if step % 10 == 0 or step == 1 or step == planned:
                    elapsed = time.time() - t0
                    p(
                        f"step {step}/{planned} epoch {epoch} "
                        f"loss {losses[-1]:.4f} elapsed_s={elapsed:.1f}"
                    )
            if step >= max_steps:
                break

        model.save_pretrained(str(out_path))
        tok.save_pretrained(str(out_path))
        meta = {
            "tag": cfg["tag"],
            "steps": step,
            "planned_steps": planned,
            "epochs_arg": epochs,
            "max_steps_arg": max_steps,
            "seconds": time.time() - t0,
            "mean_loss": sum(losses) / max(1, len(losses)),
            "last_losses": losses[-10:],
            "base": cfg["hf_id"],
            "data": str(data_path),
            "n_rows": len(rows),
            "lora_r": lora_r,
            "lora_alpha": lora_alpha,
            "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
            "lr": lr,
            "bf16": True,
            "gpu": gpu_name,
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "out_volume_path": out_rel,
            "volume": VOLUME_NAME,
        }
        (out_path / "train_meta.json").write_text(json.dumps(meta, indent=2))
        p(json.dumps(meta))
        volume.commit()
        return meta
    except Exception:
        p(traceback.format_exc())
        volume.commit()
        raise


@app.function(
    image=image,
    gpu="L4",
    cpu=4,
    memory=24576,
    timeout=60 * 60,  # 1h
    retries=0,
    max_containers=1,
    volumes={VOL_MOUNT: volume},
)
def train_lora(
    model_size: str = "3b",
    max_steps: int = 300,
    epochs: int = 3,
    lr: float = 2e-4,
    lora_r: int = 16,
    lora_alpha: int = 32,
) -> dict[str, Any]:
    if model_size not in MODELS:
        raise ValueError(f"model_size must be one of {list(MODELS)}; got {model_size!r}")
    return _train_impl(
        model_size=model_size,
        max_steps=max_steps,
        epochs=epochs,
        lr=lr,
        lora_r=lora_r,
        lora_alpha=lora_alpha,
        gpu_name="L4",
    )


@app.local_entrypoint()
def main(
    model_size: str = "3b",
    max_steps: int = 300,
    epochs: int = 3,
    lr: float = 2e-4,
    lora_r: int = 16,
    lora_alpha: int = 32,
) -> None:
    """Launch one LoRA job. Prefer sequential runs (one GPU at a time)."""
    print(
        f"launching model_size={model_size} max_steps={max_steps} epochs={epochs} "
        f"lr={lr} r={lora_r} alpha={lora_alpha} gpu=L4",
        flush=True,
    )
    meta = train_lora.remote(
        model_size=model_size,
        max_steps=max_steps,
        epochs=epochs,
        lr=lr,
        lora_r=lora_r,
        lora_alpha=lora_alpha,
    )
    print("DONE meta=", json.dumps(meta, indent=2), flush=True)
    # also write a local copy of meta for convenience
    tag = MODELS[model_size]["tag"]  # lora-3b-v3
    local_name = "modal-" + tag.replace("lora-", "", 1)  # modal-3b-v3
    local_out = Path(__file__).resolve().parents[1] / "runs" / "lora" / local_name
    local_out.mkdir(parents=True, exist_ok=True)
    (local_out / "train_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote local meta -> {local_out / 'train_meta.json'}", flush=True)
