"""Writes the exam model as a pre-quantized checkpoint that fits the size limits on disk.

The limits count weights on disk: the base model before fine-tuning at most 8.0 GB
(`ship_limit_gb`), the fine-tuned model as shipped, weights plus LoRA adapters, at most
8.8 GB (`finetuned_limit_gb`: --adapters DIR, or --finetuned for a merged model). The RAG knowledge
base doesn't count. Quantizing at load
time doesn't help, since the 11-12B candidates are 22-24 GB in bf16. This script loads
a model from configs/models.yaml in 4-bit NF4 (bitsandbytes, the same method the
baselines use when vLLM quantizes at load time), saves it, measures it and fails if it
is over the limit:

    python scripts/quantize_checkpoint.py bielik-11b          # -> work/checkpoints/bielik-11b
    python scripts/quantize_checkpoint.py --check work/checkpoints/bielik-11b \
        --adapters work/adapters/bielik-11b                   # base <= 8.0, base + adapters <= 8.8

Needs a CUDA GPU and `transformers bitsandbytes accelerate`. vLLM serves the result
directly (`vllm serve work/checkpoints/bielik-11b --quantization bitsandbytes`), and
scripts/run_baselines.py uses it instead of the HF weights once it exists, so the
scores we measure are the model we submit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_size import deck_size, reference_size  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WEIGHT_SUFFIXES = (".safetensors", ".bin", ".gguf", ".pt")


def weights_gb(path: Path) -> float:
    """Size of the weight files in a checkpoint dir (or of a single weights file), in GB."""
    files = [path] if path.is_file() else [p for p in path.rglob("*") if p.suffix in WEIGHT_SUFFIXES]
    return sum(p.stat().st_size for p in files) / 1e9


def load_config() -> dict:
    return yaml.safe_load(open(ROOT / "configs/models.yaml"))


def quantize(hf_id: str, out: Path, chat_template: str | None = None) -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                           bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(hf_id, quantization_config=q,
                                                 torch_dtype=torch.bfloat16, device_map="auto")
    model.save_pretrained(out, safe_serialization=True)
    tok = AutoTokenizer.from_pretrained(hf_id)
    if chat_template:  # pretrained bases ship without one; vLLM reads it from the checkpoint
        tok.chat_template = (ROOT / chat_template).read_text()
    tok.save_pretrained(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", nargs="?", help="key in configs/models.yaml")
    ap.add_argument("--out", help="output dir (default work/checkpoints/<model>)")
    ap.add_argument("--check", help="only measure an existing checkpoint dir or weights file")
    ap.add_argument("--limit-gb", type=float, help="size limit (default: ship_limit_gb in models.yaml)")
    ap.add_argument("--finetuned", action="store_true",
                    help="the checkpoint is a merged fine-tuned model: check against finetuned_limit_gb")
    ap.add_argument("--adapters", help="LoRA adapter dir: base <= ship_limit_gb and base + adapters <= finetuned_limit_gb")
    args = ap.parse_args()
    cfg = load_config()
    base_limit = args.limit_gb or float(cfg["ship_limit_gb"])
    tuned_limit = float(cfg["finetuned_limit_gb"])

    if args.check:
        target = Path(args.check)
    else:
        if not args.model or args.model not in cfg["models"]:
            ap.error(f"model must be one of: {', '.join(cfg['models'])}")
        spec = cfg["models"][args.model]
        target = Path(args.out or ROOT / "work/checkpoints" / args.model)
        target.mkdir(parents=True, exist_ok=True)
        quantize(spec["hf_id"], target, spec.get("chat_template"))
        (target / "ship.json").write_text(json.dumps(
            {"model": args.model, "source": spec["hf_id"], "method": "bitsandbytes nf4",
             "size_gb": round(weights_gb(target), 2)}, indent=2))

    size = weights_gb(target)
    # Quantized size (Orest, 15:55 CEST): the deck's 8/4-bit figure when it has one for the model at
    # the precision we ship, else the measured file. A bf16 deck figure is information only.
    if args.model in cfg["models"] and not args.finetuned:  # a merged fine-tune isn't the deck's model
        deck_gb, label = deck_size(cfg["models"][args.model])
        print(f"{args.model}: measured {size:.2f} GB; deck "
              f"{f'{deck_gb:.2f} GB ({label})' if deck_gb is not None else label}")
        ref, _ = reference_size(cfg["models"][args.model], size)
        size = ref
    adapters = Path(args.adapters) if args.adapters else None
    # Alone, a checkpoint is the base model, or with --finetuned a merged fine-tune.
    limit = tuned_limit if args.finetuned and not adapters else base_limit
    ok = 0 < size <= limit
    print(f"{target}: {size:.2f} GB of weights, limit {limit} GB -> {'OK' if ok else 'OVER THE LIMIT'}")
    if adapters and adapters.exists():  # base + adapters is the fine-tuned model
        total = size + weights_gb(adapters)
        tuned_ok = total <= tuned_limit
        print(f"with adapters in {adapters}: {total:.2f} GB, fine-tuned limit {tuned_limit} GB -> "
              f"{'OK' if tuned_ok else 'OVER THE LIMIT (save adapters in bf16, lower the rank or drop one)'}")
        ok = ok and tuned_ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
