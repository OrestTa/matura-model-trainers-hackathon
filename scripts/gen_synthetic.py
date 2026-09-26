"""Generates matura-style training Q&A per question type with a large "teacher" model.

The teacher is any OpenAI-compatible endpoint: on EC2 we serve a big open model with
vLLM (infra/jobs/train.sh), but a hosted API works too, since closed models are
allowed for synthetic data before the exam.

    python scripts/gen_synthetic.py --base-url http://localhost:8200/v1 --model teacher \
        --per-category 400 -o data/train/synthetic.jsonl

Output rows are {"category", "question", "context", "answer", "topic"}, the input
format of scripts/split_by_category.py. Answers follow the same format the router's
prompts ask for, so each adapter learns exactly the output shape it will be graded on.
Items too similar to an eval question are dropped, so the eval stays honest.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from matura_router.backends import GenerationParams  # noqa: E402
from matura_router.backends.openai_compat import OpenAICompatBackend  # noqa: E402

# Breadth of the history matura (poziom rozszerzony): Polish and world history.
TOPICS = [
    "cywilizacje starożytnego Bliskiego Wschodu", "demokracja ateńska", "Sparta i wojny grecko-perskie",
    "hellenizm i Aleksander Macedoński", "republika rzymska", "cesarstwo rzymskie i chrześcijaństwo",
    "Bizancjum", "państwo Franków i Karol Wielki", "feudalizm i system lenny", "wyprawy krzyżowe",
    "spór o inwestyturę", "państwo Mieszka I i Bolesława Chrobrego", "rozbicie dzielnicowe",
    "zjednoczenie Polski i Kazimierz Wielki", "unia polsko-litewska i Jagiellonowie",
    "wojna z zakonem krzyżackim i pokój toruński", "odrodzenie i humanizm", "reformacja w Europie",
    "wielkie odkrycia geograficzne", "demokracja szlachecka i sejm walny", "unia lubelska",
    "pierwsze wolne elekcje i artykuły henrykowskie", "wojny XVII wieku i potop szwedzki",
    "Jan III Sobieski i odsiecz wiedeńska", "czasy saskie", "absolutyzm we Francji",
    "rewolucja angielska i monarchia parlamentarna", "oświecenie w Europie",
    "reformy stanisławowskie i Sejm Czteroletni", "Konstytucja 3 maja", "rozbiory Rzeczypospolitej",
    "powstanie kościuszkowskie", "rewolucja amerykańska", "rewolucja francuska",
    "epoka napoleońska i Księstwo Warszawskie", "kongres wiedeński i Królestwo Polskie",
    "powstanie listopadowe", "Wielka Emigracja", "Wiosna Ludów", "powstanie styczniowe",
    "rewolucja przemysłowa", "zjednoczenie Niemiec i Włoch", "wojna secesyjna w USA",
    "praca organiczna i pozytywizm", "zabór pruski i Kulturkampf", "autonomia galicyjska",
    "imperializm i kolonializm", "I wojna światowa", "sprawa polska w czasie I wojny światowej",
    "rewolucje w Rosji 1917", "odzyskanie niepodległości i walki o granice 1918–1921",
    "wojna polsko-bolszewicka", "II Rzeczpospolita: ustrój i przewrót majowy",
    "gospodarka II RP i reformy Grabskiego", "systemy totalitarne: ZSRS, III Rzesza, faszyzm włoski",
    "polityka zagraniczna II RP", "wybuch II wojny światowej i kampania wrześniowa",
    "okupacja niemiecka i sowiecka ziem polskich", "Polskie Państwo Podziemne i powstanie warszawskie",
    "Holokaust", "konferencje Wielkiej Trójki", "przejęcie władzy przez komunistów w Polsce",
    "zimna wojna", "stalinizm w Polsce", "Październik 1956", "Marzec 1968 i Grudzień 1970",
    "Solidarność i stan wojenny", "Okrągły Stół i przemiany 1989", "dekolonizacja",
    "integracja europejska", "rozpad ZSRS i Jesień Ludów", "III Rzeczpospolita, NATO i UE",
]

FORMATS = {
    "closed_choice": ("zadanie zamknięte jednokrotnego wyboru z odpowiedziami A–D",
                      "sama litera poprawnej odpowiedzi, np. \"B\""),
    "true_false": ("ocena prawdziwości 3 zdań (P – prawda, F – fałsz), najlepiej na podstawie krótkiego źródła",
                   "\"1. P\\n2. F\\n3. P\""),
    "matching": ("przyporządkowanie: 3 elementy ponumerowane 1–3 i 4–5 opcji A–E",
                 "\"1 – B\\n2 – D\\n3 – A\""),
    "chronology": ("uporządkowanie chronologiczne 4 wydarzeń oznaczonych A–D",
                   "kolejność od najwcześniejszego, np. \"C, A, D, B\""),
    "source_analysis": ("zadanie do krótkiego tekstu źródłowego (pole context: 3–6 zdań, parafraza "
                        "prawdziwego źródła z epoki z podpisem), np. „Rozstrzygnij… Uzasadnij” albo "
                        "„Wyjaśnij, do jakiego wydarzenia odnosi się źródło”. Połowa zadań to „Rozstrzygnij, czy… "
                        "Odpowiedź uzasadnij…”; takie polecenie kończy się liniami karty odpowiedzi "
                        "\"Rozstrzygnięcie: …\\nUzasadnienie: …\"",
                        "zwięzła odpowiedź jak w kluczu CKE; przy „Rozstrzygnij” dokładnie \"Rozstrzygnięcie: "
                        "<krótko, np. Tak/Nie/A>\\nUzasadnienie: <1–2 zdania z faktem i odwołaniem do źródła>\""),
    "short_open": ("krótkie zadanie otwarte: podaj / wyjaśnij / wymień",
                   "1–2 zdania z dokładnymi nazwami, nazwiskami i datami"),
    "essay": ("temat wypracowania maturalnego (np. „Oceń…”, „Porównaj…”, „Scharakteryzuj…”)",
              "wypracowanie 350–500 słów: teza, co najmniej 3 argumenty z faktami, kontekst epoki, wniosek"),
}

PROMPT = """Jesteś doświadczonym autorem zadań maturalnych z historii (CKE, poziom rozszerzony, formuła 2023).
Ułóż {n} różnych zadań typu: {kind}.
Temat: {topic}.
Używaj wyłącznie pewnych, ogólnie przyjętych faktów historycznych. Nie kopiuj zadań z prawdziwych arkuszy.
Odpowiedź wzorcowa: {answer_fmt}.

Zwróć wyłącznie tablicę JSON, bez komentarzy, w formacie:
[{{"question": "polecenie z ewentualnymi opcjami", "context": "tekst źródła albo pusty napis", "answer": "odpowiedź wzorcowa"}}]"""


def parse_items(text: str) -> list[dict]:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\[.*\]", text, flags=re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group())
    except json.JSONDecodeError:
        return []
    return [i for i in items if isinstance(i, dict) and i.get("question") and i.get("answer")]


def shingles(s: str, n: int = 5) -> set[str]:
    w = re.findall(r"\w+", s.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--model", default="teacher")
    p.add_argument("--api-key", default="none")
    p.add_argument("--categories", default=",".join(FORMATS))
    p.add_argument("--per-category", type=int, default=300)
    p.add_argument("--batch", type=int, default=5, help="items asked for per request")
    p.add_argument("--concurrency", type=int, default=64)
    p.add_argument("--eval", default=str(ROOT / "data/eval/matura.jsonl"),
                   help="eval set to keep out of the training data")
    p.add_argument("-o", "--out", default=str(ROOT / "data/train/synthetic.jsonl"))
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    rng = random.Random(args.seed)
    teacher = OpenAICompatBackend(base_url=args.base_url, base_model=args.model, api_key=args.api_key,
                                  timeout=900,
                                  extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    if not Path(args.eval).exists():
        sys.exit(f"eval set {args.eval} not found: refusing to generate without the leak filter")
    # Per eval item: its question, context and answer shingles, checked separately so a long new
    # context can't dilute a copied question (the old pooled ratio kept verbatim eval questions).
    eval_parts = []
    for line in open(args.eval, encoding="utf-8"):
        r = json.loads(line)
        for field in ("question", "context", "gold"):
            sh = shingles(str(r.get(field) or ""))
            if len(sh) >= 3:
                eval_parts.append((r.get("id"), field, sh))

    def leak(it: dict):
        mine = shingles(" ".join([it["question"], it["context"], it["answer"]]))
        for eid, field, sh in eval_parts:
            if len(sh & mine) / len(sh) > 0.2:
                return eid, field
        return None

    jobs = []
    for cat in args.categories.split(","):
        batch = 1 if cat == "essay" else args.batch
        for _ in range(-(-args.per_category // batch)):
            jobs.append((cat, rng.choice(TOPICS), batch))

    def run(job):
        cat, topic, n = job
        kind, fmt = FORMATS[cat]
        try:
            out = teacher.chat([{"role": "user", "content": PROMPT.format(
                n=n, kind=kind, topic=topic, answer_fmt=fmt)}], None,
                GenerationParams(max_tokens=4000, temperature=0.8, top_p=0.95))
        except Exception as e:  # noqa: BLE001
            print(f"request failed ({cat}, {topic}): {e}", file=sys.stderr)
            return []
        return [dict(category=cat, topic=topic, question=i["question"].strip(),
                     context=(i.get("context") or "").strip(), answer=i["answer"].strip())
                for i in parse_items(out)]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    seen, kept, leaked = set(), 0, 0
    with ThreadPoolExecutor(args.concurrency) as pool, open(args.out, "w", encoding="utf-8") as f:
        for items in pool.map(run, jobs):
            for it in items:
                key = re.sub(r"\W+", " ", it["question"].lower()).strip()
                if key in seen:
                    continue
                hit = leak(it)
                if hit:
                    leaked += 1
                    print(f"dropped as close to eval {hit[0]} ({hit[1]}): {it['question'][:60]!r}",
                          file=sys.stderr)
                    continue
                seen.add(key)
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
                kept += 1
    print(f"{kept} items -> {args.out} ({leaked} dropped as too close to the eval set)")
    wanted = args.per_category * len(args.categories.split(","))
    if kept < wanted // 2:
        sys.exit(f"only {kept} of {wanted} items kept: teacher mostly failed")


if __name__ == "__main__":
    main()
