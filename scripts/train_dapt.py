"""Continued pretraining (DAPT): one LoRA pass of next-token loss over Polish history text.

    python scripts/train_dapt.py --model bielik-11b --max-tokens 20_000_000
    # reads  data/dapt/*.jsonl  ({"text": ...}, best first; from scripts/corpus/plwiki.py)
    # writes adapters/<model>/domain/            (LoRA adapter + train_meta.json)
    #        work/models/<model>-dapt/           (with --merge: base + adapter in bf16, for
    #                                             the per-type SFT in train_lora.py to start from)

Takes documents in file order (the corpus scripts write the most history-dense first) until
--max-tokens, packs them into --max-len blocks and trains every token. On one L40S a
Bielik-11B LoRA does roughly 2-3k tokens/s, so 20M tokens is about 2-3 hours; start with
--max-tokens 5_000_000 to check the loss curve. Needs `pip install -e .[train]` and a GPU.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, help="key in configs/models.yaml")
    p.add_argument("--data", nargs="+", default=sorted(glob.glob(str(ROOT / "data/dapt/*.jsonl"))))
    p.add_argument("--out-dir", default=str(ROOT / "adapters"))
    p.add_argument("--models-config", default=str(ROOT / "configs/models.yaml"))
    p.add_argument("--max-tokens", type=int, default=20_000_000)
    p.add_argument("--max-len", type=int, default=2048)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--rank", type=int, default=32)
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--grad-accum", type=int, default=8)
    p.add_argument("--merge", action="store_true", help="also save base+adapter merged")
    p.add_argument("--merge-dir", default=str(ROOT / "work/models"))
    args = p.parse_args()
    if not args.data:
        sys.exit("no data/dapt/*.jsonl: run scripts/corpus/plwiki.py build first")

    spec = yaml.safe_load(Path(args.models_config).read_text())["models"][args.model]
    out = Path(args.out_dir) / args.model / "domain"

    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import (AutoModelForCausalLM, AutoTokenizer, DataCollatorForLanguageModeling,
                              Trainer, TrainingArguments)

    tok = AutoTokenizer.from_pretrained(spec["hf_id"])
    # Round-robin over the files so each corpus contributes its best documents first.
    streams = [open(f, encoding="utf-8") for f in args.data]
    blocks, buf, total, docs = [], [], 0, 0
    while streams and total < args.max_tokens:
        for s in list(streams):
            line = s.readline()
            if not line:
                streams.remove(s)
                continue
            ids = tok(json.loads(line)["text"], add_special_tokens=False)["input_ids"]
            buf += ids + [tok.eos_token_id]
            total += len(ids) + 1
            docs += 1
            while len(buf) >= args.max_len:
                blocks.append(buf[:args.max_len])
                buf = buf[args.max_len:]
    print(f"{docs} documents, {total:,} tokens, {len(blocks)} blocks of {args.max_len}", flush=True)
    ds = Dataset.from_dict({"input_ids": blocks})

    model = AutoModelForCausalLM.from_pretrained(spec["hf_id"], torch_dtype=torch.bfloat16,
                                                 device_map="auto")
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=2 * args.rank,
                                             lora_dropout=0.05, target_modules="all-linear",
                                             task_type="CAUSAL_LM"))
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    targs = dict(
        output_dir=str(out / "checkpoints"), num_train_epochs=1,
        per_device_train_batch_size=args.batch, gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr, lr_scheduler_type="cosine", bf16=torch.cuda.is_available(),
        logging_steps=10, save_strategy="steps", save_steps=200, save_total_limit=1,
        report_to="none")
    steps = max(1, len(blocks) // (args.batch * args.grad_accum))
    # transformers 5 dropped warmup_ratio; warmup_steps works in every version.
    targs["warmup_steps"] = max(1, steps // 50)
    trainer = Trainer(model=model, train_dataset=ds, args=TrainingArguments(**targs),
                      data_collator=DataCollatorForLanguageModeling(tok, mlm=False))
    result = trainer.train()
    model.save_pretrained(str(out))
    tok.save_pretrained(str(out))
    (out / "train_meta.json").write_text(json.dumps({
        "model": args.model, "hf_id": spec["hf_id"], "kind": "dapt", "data": args.data,
        "documents": docs, "tokens": total, "max_len": args.max_len, "lr": args.lr,
        "rank": args.rank, "train_loss": result.training_loss,
        "log": trainer.state.log_history}, indent=2))
    print(f"saved {out} (loss {result.training_loss:.3f}, {total:,} tokens)")

    if args.merge:
        merged = Path(args.merge_dir) / f"{args.model}-dapt"
        model.merge_and_unload().save_pretrained(str(merged), safe_serialization=True)
        tok.save_pretrained(str(merged))
        print(f"merged -> {merged}")


if __name__ == "__main__":
    sys.exit(main())
