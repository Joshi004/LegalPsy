from pathlib import Path
from collections import Counter
import csv, json

ROOT = Path("data/raw/cuad")

ext = Counter(p.suffix.lower() or "(none)" for p in ROOT.rglob("*") if p.is_file())
for e, n in ext.most_common():
    print(f"{e:12s} {n:6d}")






print ("\n"+"*"*100)


csv_path = next(ROOT.rglob("*.csv"))
with csv_path.open(newline="", encoding="utf-8-sig") as f:
    r = csv.reader(f)
    header = next(r)
    rows = list(r)
print(len(header), "columns,", len(rows), "rows")
print("answer columns:", sum("answer" in h.lower() for h in header))

print ("\n"+"*"*100)


obj = json.loads(next(ROOT.rglob("CUAD_v1.json")).read_text())
docs = obj["data"]
qas = [q for d in docs for p in d["paragraphs"] for q in p["qas"]]
answered = [q for q in qas if q.get("answers")]
spans = sum(len(q.get("answers", [])) for q in qas)
print(len(docs), "docs")
print(len(qas), "questions", f"({len(qas)/len(docs):.1f}/doc)")
print(len(answered), "answered")
print(spans, "spans")
print(f"item positive rate {len(answered)/len(qas):.1%}")