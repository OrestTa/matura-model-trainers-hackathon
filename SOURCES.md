# Sources

This repository holds code, configs and our own notes only. No exam papers, answer keys,
corpora, model weights or adapters are committed; `data/`, `models/`, `adapters/`, `work/`
and `runs/` are gitignored. Everything below is downloaded by a script in this repo.

## Exam papers (evaluation and past-paper training items)

| Source | Licence / terms | Fetched by | Used for |
|---|---|---|---|
| CKE (Centralna Komisja Egzaminacyjna), matura z historii, poziom rozszerzony: papers and "zasady oceniania" keys, formuła 2023 (May 2023–2026, 2022 demo, Jan 2026 mock) and formuła 2015 (May 2015–2024), https://cke.gov.pl | © CKE, not redistributed here | `scripts/fetch_matura.py` (URLs in `PAPERS`) | eval set `data/eval/matura.jsonl` (headline: May 2023–2026) and `matura_all.jsonl` |
| Same papers, non-headline only | as above | `scripts/build_train_from_papers.py` | adapter training items `data/train/past_papers.jsonl` |

The headline eval papers (May 2023–2026, formuła 2023) are never used for training.

## Text corpora and knowledge base

| Source | Licence | Fetched by | Used for |
|---|---|---|---|
| Polish Wikipedia, live API https://pl.wikipedia.org/w/api.php | CC BY-SA 4.0 | `scripts/build_kb.py` | local RAG knowledge base |
| Polish Wikipedia dump, `wikimedia/wikipedia` 20231101.pl on Hugging Face | CC BY-SA 4.0 | `scripts/corpus/plwiki.py` | history slice for DAPT and the RAG index |
| SpeakLeash corpora `plwikisource`, `wolne_lektury_corpus` (speakleash.org) | per dataset manifest (public domain / free licences) | `scripts/corpus/speakleash.py` | DAPT corpus |
| `epfml/FineWeb2-HQ` and `HuggingFaceFW/fineweb-2` (pol_Latn) | ODC-By 1.0 | `scripts/corpus/fineweb.py` | DAPT corpus (history slice; exam and answer-key pages skipped) |
| `ipipan/polqa` | CC BY-SA 4.0 | `scripts/corpus/rl_sets.py` | RL / eval questions |
| `CohereLabs/Global-MMLU` (pl) | Apache-2.0 | `scripts/corpus/rl_sets.py` | RL / eval questions |

## Synthetic training data

Generated before the exam by an open teacher model served locally with vLLM
(`Qwen/Qwen3-235B-A22B-Instruct-2507-FP8`, or `Qwen/Qwen3-30B-A3B-Instruct-2507-FP8` on
small GPUs; see `infra/jobs/train.sh`) through `scripts/gen_synthetic.py`. Items too close to
an eval question are dropped. The generated data is not committed.

## Models

Base model candidates are listed in `configs/models.yaml` and downloaded from Hugging Face:
`speakleash/Bielik-11B-v2.3-Instruct`, `speakleash/Bielik-4.5B-v3.0-Instruct`,
`speakleash/Bielik-1.5B-v3.0-Instruct`, `Qwen/Qwen3-8B`, `Qwen/Qwen3-1.7B`,
`google/gemma-3-12b-it` (gated, needs `HF_TOKEN`), and `Qwen/Qwen2.5-3B-Instruct`
(registered team base). Each keeps its own licence. The shipped exam checkpoint is a 4-bit
NF4 quantization made with `scripts/quantize_checkpoint.py`.

## Our own content

`examples/sample_questions.jsonl` holds matura-style questions we wrote ourselves for
testing the classifier. All code, configs and docs are ours.
