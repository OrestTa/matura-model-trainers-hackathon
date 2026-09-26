# Size caps (user 2026-09-26 ~14:29 Warsaw)

| Cap | Limit |
|-----|-------|
| Declared **base** weights on disk | **<= 8.0 GB** |
| After fine-tuning (base + what organizers count) | **<= 8.8 GB** |

Previous "8.9 GB base OK" organizer note is superseded for our planning by this tighter user rule.

## Fit / no-fit (expected; confirm with `du` on VM)

| Model | Typical disk | Sunday base? |
|-------|--------------|--------------|
| Qwen2.5-1.5B-Instruct bf16 | ~3 GB | YES |
| Qwen2.5-3B-Instruct bf16 | ~6 GB | YES (registered practice base) |
| Qwen2.5-7B-Instruct bf16 | ~14-15 GB | **NO** as bf16 base |
| Qwen2.5-7B AWQ/GPTQ Int4/Int8 / NF4 | often ~4-8 GB | YES if measured <=8.0 |
| Bielik-11B bf16 | ~22 GB | **NO** |
| Bielik-11B 4-bit | often ~6-8 GB | ONLY if measured <=8.0 base and <=8.8 with adapters |

## Actions
- Cancel jobs certain oversize: Bielik-11B full/bf16 train & serve-as-exam-base; bf16 7B as declared Sunday base; dapt-bielik if base >8.0.
- Keep 3B (+ LoRA if total <=8.8) as safe default.
- Quantize 7B before any Sunday declare / further 7B-as-base train.
