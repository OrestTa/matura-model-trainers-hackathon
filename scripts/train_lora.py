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
import os
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
    p.add_argument("--vision", action="store_true",
                   help="rows carry `images` (scripts/build_vision_train.py): train through the frozen "
                        "vision tower with the processor; LoRA stays on the text layers")
    p.add_argument("--think", action="store_true",
                   help="train in the thinking-on exam format (Gemma 4): render with enable_thinking=True and "
                        "put the assistant's `reasoning_content` in the thought channel of the target "
                        "(scripts/build_selfdistill.py rows; docs/LORA_ROOT_CAUSE.md cause 1)")
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
    # <data-dir>/exclude_sources.txt: item ids (the rows' "source") to drop, e.g. past-paper items whose sources
    # overlap the held-out May 2023-2026 papers (build_selfdistill.py --held-out check).
    excl = Path(args.data_dir) / "exclude_sources.txt"
    if excl.exists() and "source" in ds.column_names:
        drop = {l.strip() for l in excl.read_text().splitlines() if l.strip()}
        before = len(ds)
        ds = ds.filter(lambda r: r["source"] not in drop)
        print(f"excluded {before - len(ds)} rows listed in {excl}")
    # Prompt/completion split so the loss covers only the answer; with a plain "messages"
    # column TRL trains on the system prompt and question too (~98% of tokens on closed types).
    if args.vision:
        from datasets import Image, Sequence
        ds = ds.map(lambda r: {"prompt": r["messages"][:-1], "completion": r["messages"][-1:],
                            # relative image paths are relative to the data file (a portable pack)
                            "images": [str(data.parent / i) for i in r["images"]]},
                    remove_columns=ds.column_names).cast_column("images", Sequence(Image()))
    elif args.think:
        # Without this, TRL renders Gemma 4's template with thinking off: the target starts right after
        # `<|turn>model\n`, where the thinking-on exam starts its reasoning, so the adapter learns to skip it.
        # Rendered here as plain strings; the prompt is then an exact prefix of prompt + target.
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(spec.get("train_hf_id") or spec["hf_id"])

        def render(r):
            m = r["messages"]
            prompt = tok.apply_chat_template(m[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=True)
            full = tok.apply_chat_template(m, tokenize=False, enable_thinking=True)
            assert full.startswith(prompt) and "<|channel>thought" in full[len(prompt):], "thinking target not rendered"
            bos = tok.bos_token or ""
            return {"prompt": prompt[len(bos):] if bos and prompt.startswith(bos) else prompt,
                    "completion": full[len(prompt):].rstrip("\n")}
        ds = ds.map(render, remove_columns=ds.column_names)
        print("think-format sample:", repr(ds[0]["prompt"][-120:] + " || " + ds[0]["completion"][:200]))
    else:
        ds = ds.map(lambda r: {"prompt": r["messages"][:-1], "completion": r["messages"][-1:]},
                    remove_columns=ds.column_names)
    cfg_kwargs = dict(
        output_dir=str(out / "checkpoints"), num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch, gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr, lr_scheduler_type="cosine",
        bf16=True, gradient_checkpointing=True, logging_steps=5, save_strategy="no",
        report_to="none", model_init_kwargs={"torch_dtype": torch.bfloat16},  # transformers 5 reads "dtype" (set below)
    )
    # TRL renamed max_seq_length -> max_length; support both.
    params = inspect.signature(SFTConfig.__init__).parameters
    cfg_kwargs["max_length" if "max_length" in params else "max_seq_length"] = args.max_len
    # transformers 5 dropped warmup_ratio; its warmup_steps takes a float < 1 as a ratio.
    cfg_kwargs["warmup_ratio" if "warmup_ratio" in params else "warmup_steps"] = 0.03
    # TRL >= 1.x defaults to loss_type="chunked_nll", whose lm_head patch crashes on Gemma 4
    # ("'functools.partial' object has no attribute '__func__'"); plain nll is the same math.
    # transformers 5 ignores torch_dtype: the 12B loaded in fp32 (48 GB) and got offloaded to meta/CPU.
    import transformers
    if int(transformers.__version__.split(".")[0]) >= 5:
        cfg_kwargs["model_init_kwargs"] = {"dtype": torch.bfloat16}
    if "loss_type" in params:
        cfg_kwargs["loss_type"] = "nll"
    if "completion_only_loss" in params:
        cfg_kwargs["completion_only_loss"] = True

    extra = {}
    if spec.get("chat_template"):  # pretrained base: train in the same format the raw baseline used
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(spec.get("train_hf_id") or spec["hf_id"])
        tok.chat_template = (ROOT / spec["chat_template"]).read_text()
        tok.pad_token = tok.pad_token or tok.unk_token
        extra["processing_class"] = tok
    if args.vision:
        from transformers import AutoProcessor
        extra["processing_class"] = AutoProcessor.from_pretrained(spec.get("train_hf_id") or spec["hf_id"])
        if args.think:
            # TRL renders the processor's template itself: make thinking the default so the system turn gets
            # <|think|> and the assistant's reasoning_content goes into the thought channel of the target.
            proc = extra["processing_class"]
            for obj in (proc, getattr(proc, "tokenizer", None)):
                t = getattr(obj, "chat_template", None)
                if t:
                    assert "enable_thinking | default(false)" in t, "Gemma 4 template changed: can't turn thinking on"
                    obj.chat_template = t.replace("enable_thinking | default(false)", "enable_thinking | default(true)")
            probe = proc.apply_chat_template(ds[0]["prompt"] + ds[0]["completion"], tokenize=False)
            assert "<|think|>" in probe and "<|channel>thought" in probe, "thinking target not rendered"
            print("think-format sample:", repr(probe[-400:]))
        # Whole exam pages are big images: keep them uncut, never truncate the image tokens.
        cfg_kwargs["max_length"] = None
        trainer_args = SFTConfig(**cfg_kwargs)
    trainer = SFTTrainer(
        # Pre-quantized entries (AWQ, GGUF) train on their full-precision twin, `train_hf_id`;
        # the adapter then loads onto the quantized weights at serve time.
        model=spec.get("train_hf_id") or spec["hf_id"], train_dataset=ds,
        args=trainer_args if args.vision else SFTConfig(**cfg_kwargs), **extra,
        peft_config=LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05,
                               target_modules=spec.get("lora_target") or "all-linear",  # a regex keeps LoRA off vision layers
                               task_type="CAUSAL_LM"),
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
    code = main()
    # On Modal (transformers 5.17) the process hung after the save, so train.sh never reached the
    # GGUF step: leave without waiting for stray non-daemon threads.
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(code or 0)
