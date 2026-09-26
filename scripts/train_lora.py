"""Trains one LoRA adapter for one question type on one base model.

    python scripts/train_lora.py --model bielik-11b --category essay
    # reads  data/by_category/essay.jsonl   (from scripts/split_by_category.py)
    # writes adapters/bielik-11b/essay/     (what run_baselines --adapters-dir and vLLM load)

Needs `pip install -e .[train]` and a GPU. Trains in bf16 on the full-precision base;
at inference the adapter sits on the 4-bit base that fits under the 8.0 GB base limit (base + adapters must stay under 8.8 GB), and adapters
don't count toward the limit. infra/jobs/train.sh runs one of these per GPU.
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, help="key in configs/models.yaml")
    p.add_argument("--category", required=True)
    p.add_argument("--data-dir", default=str(ROOT / "data/by_category"))
    p.add_argument("--out-dir", default=str(ROOT / "adapters"))
    p.add_argument("--models-config", default=str(ROOT / "configs/models.yaml"))
    p.add_argument("--epochs", type=float, default=2)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--rank", type=int, default=16)
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--grad-accum", type=int, default=4)
    p.add_argument("--max-len", type=int, default=4096)
    p.add_argument("--min-examples", type=int, default=30)
    args = p.parse_args()

    spec = yaml.safe_load(Path(args.models_config).read_text())["models"][args.model]
    data = Path(args.data_dir) / f"{args.category}.jsonl"
    n = sum(1 for _ in open(data, encoding="utf-8")) if data.exists() else 0
    if n < args.min_examples:
        print(f"skip {args.model}/{args.category}: {n} examples (< {args.min_examples})")
        return
    out = Path(args.out_dir) / args.model / args.category

    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from trl import SFTConfig, SFTTrainer

    ds = load_dataset("json", data_files=str(data))["train"].shuffle(seed=0)
    # Prompt/completion split so the loss covers only the answer; with a plain "messages"
    # column TRL trains on the system prompt and question too (~98% of tokens on closed types).
    ds = ds.map(lambda r: {"prompt": r["messages"][:-1], "completion": r["messages"][-1:]},
                remove_columns=ds.column_names)
    cfg_kwargs = dict(
        output_dir=str(out / "checkpoints"), num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch, gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr, lr_scheduler_type="cosine", warmup_ratio=0.03,
        bf16=True, gradient_checkpointing=True, logging_steps=5, save_strategy="no",
        report_to="none", model_init_kwargs={"torch_dtype": torch.bfloat16},
    )
    # TRL renamed max_seq_length -> max_length; support both.
    params = inspect.signature(SFTConfig.__init__).parameters
    cfg_kwargs["max_length" if "max_length" in params else "max_seq_length"] = args.max_len
    if "completion_only_loss" in params:
        cfg_kwargs["completion_only_loss"] = True

    extra = {}
    if spec.get("chat_template"):  # pretrained base: train in the same format the raw baseline used
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(spec["hf_id"])
        tok.chat_template = (ROOT / spec["chat_template"]).read_text()
        tok.pad_token = tok.pad_token or tok.unk_token
        extra["processing_class"] = tok
    trainer = SFTTrainer(
        model=spec["hf_id"], train_dataset=ds, args=SFTConfig(**cfg_kwargs), **extra,
        peft_config=LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05,
                               target_modules="all-linear", task_type="CAUSAL_LM"),
    )
    result = trainer.train()
    trainer.save_model(str(out))
    # PEFT keeps LoRA weights in fp32; bf16 halves the adapters' share of the 8.8 GB
    # fine-tuned limit (about 130 MB instead of 260 MB per adapter on Bielik-11B, r=16).
    from safetensors.torch import load_file, save_file
    ad = out / "adapter_model.safetensors"
    if ad.exists():
        save_file({k: v.to(torch.bfloat16) for k, v in load_file(str(ad)).items()}, str(ad),
                  metadata={"format": "pt"})
    (out / "train_meta.json").write_text(json.dumps({
        "model": args.model, "hf_id": spec["hf_id"], "category": args.category, "examples": n,
        "epochs": args.epochs, "lr": args.lr, "rank": args.rank,
        "train_loss": result.training_loss}, indent=2))
    print(f"saved {out} (loss {result.training_loss:.3f}, {n} examples)")


if __name__ == "__main__":
    sys.exit(main())
