"""Five-category table for probny-2026-01 claude_score.json files: closed / open / essay, and non-essay items
without vs with pictures (needs_image). python results/judged/b15-probny/breakdown.py <arm> [<arm> ...]"""
import json, sys
CLOSED = {"closed_choice", "true_false", "matching", "chronology"}
rows = {json.loads(l)["id"].split("-z", 1)[1]: json.loads(l) for l in open("/mnt/project-files/data/eval/matura_all.jsonl")
        if '"probny-2026-01"' in l}
def cat(i):
    r = rows[i]; out = []
    if r["category"] == "essay": return ["essay"]
    out.append("closed" if r["category"] in CLOSED else "open")
    out.append("with pictures" if str(r.get("needs_image")) == "True" else "text only")
    return out
cols = ["closed", "open", "essay", "text only", "with pictures"]
print("| arm | " + " | ".join(cols) + " | total |"); print("|---" * (len(cols) + 2) + "|")
for a in sys.argv[1:]:
    d = json.load(open(f"results/judged/b15-probny/{a}/claude_score.json"))
    got = {c: 0.0 for c in cols}; mx = {c: 0.0 for c in cols}
    for it in d["items"]:
        for c in cat(it["id"]): got[c] += it["claude_points"]; mx[c] += it["max_points"]
    print(f"| {a} | " + " | ".join(f"{got[c]:g}/{mx[c]:g}" for c in cols) + f" | {d['total']:g}/60 |")
