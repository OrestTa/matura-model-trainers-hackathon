"""Merge an existing DAPT adapter into its bf16 base, as `train_dapt.py --merge` would have.

    python scripts/merge_dapt.py --model bielik-11b-base
    # reads  adapters/<model>/domain/        (train_dapt.py output, e.g. a DAPT_MERGE=0 run)
    # writes work/models/<model>-dapt/       (bf16, with our chat template; quantize_checkpoint.py
    #                                         then stores it as NF4)

For a DAPT that ran without --merge, so progress_pipeline.sh can go on to quantize + SFT without
training the domain pass again. CPU is enough (bf16 Bielik-11B needs ~25 GB RAM).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="bielik-11b-base")
    p.add_argument("--models-config", default=str(ROOT / "configs/models.yaml"))
    p.add_argument("--adapter", help="default: <work>/adapters/<model>/domain")
    p.add_argument("--work", default=str(ROOT / "work"))
    p.add_argument("--merge-dir", default=str(ROOT / "work/models"))
    args = p.parse_args()

    spec = yaml.safe_load(Path(args.models_config).read_text())["models"][args.model]
    adapter = Path(args.adapter or Path(args.work) / "adapters" / args.model / "domain")
    if not (adapter / "adapter_config.json").exists():
        sys.exit(f"no DAPT adapter at {adapter}")
    out = Path(args.merge_dir) / f"{args.model}-dapt"

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(spec["hf_id"])
    if spec.get("chat_template"):  # pretrained bases have none; the merged model keeps ours
        tok.chat_template = (ROOT / spec["chat_template"]).read_text()
    model = AutoModelForCausalLM.from_pretrained(spec["hf_id"], torch_dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(model, str(adapter)).merge_and_unload()
    model.save_pretrained(str(out), safe_serialization=True)
    tok.save_pretrained(str(out))
    print(f"merged {adapter} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
