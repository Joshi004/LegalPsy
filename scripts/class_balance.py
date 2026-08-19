#!/usr/bin/env python3
"""Item-level class balance for LegalPsy's 15 CUAD fields.

PLAN.md At-a-glance claims ~99.75% negative per (contract, field). Block 4 of
PLAN-DAY-01.md asks whether that is a real item rate or a misread of
character-density (~0.25% of the text highlighted per label).

This script measures both, from the master CSV and the QA JSON independently.

--all-categories extends the same measurement to all 41 CUAD categories (not
just the 15 in the current schema) and ranks them by "minority class n" --
since every category is measured over the same 510 contracts, min(present,
absent) is a direct, transparent proxy for how much real training/eval signal
exists for the rarer class. This is a second, independent axis from PLAN.md
Sec 1.1's commercial-relevance selection, not a replacement for it: as of
2026-08-19 it motivated exactly one swap (field 13, MFN/Price Restrictions ->
License Grant, decided too data-thin at 15-28/510 positives either side) and
left the other 14 fields as-is on commercial grounds despite some of them
ranking below several out-of-schema categories on balance alone. See
docs/DECISIONS.md and docs/CLASS-BALANCE.md.

Usage:
    python scripts/class_balance.py
    python scripts/class_balance.py --all-categories
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUAD_ROOT = ROOT / "data" / "raw" / "cuad"

# PLAN.md §1.1 — LegalPsy field -> one or more CUAD categories.
# Field 13 was MFN/Price Restrictions (a two-category OR) until 2026-08-19;
# swapped to License Grant for data volume (docs/DECISIONS.md). The list-of-
# categories shape is kept generic in case a future field needs an OR again,
# but no current field does, so or_count()'s branch below is currently unused.
FIELDS: list[tuple[str, list[str]]] = [
    ("parties", ["Parties"]),
    ("effective_date", ["Effective Date"]),
    ("expiration_date", ["Expiration Date"]),
    ("renewal_term", ["Renewal Term"]),
    ("notice_period_to_terminate_renewal", ["Notice Period To Terminate Renewal"]),
    ("termination_for_convenience", ["Termination For Convenience"]),
    ("cap_on_liability", ["Cap On Liability"]),
    ("uncapped_liability", ["Uncapped Liability"]),
    ("liquidated_damages", ["Liquidated Damages"]),
    ("change_of_control", ["Change Of Control"]),
    ("anti_assignment", ["Anti-Assignment"]),
    ("minimum_commitment", ["Minimum Commitment"]),
    ("license_grant", ["License Grant"]),
    ("exclusivity", ["Exclusivity"]),
    ("governing_law", ["Governing Law"]),
]


def find_one(pattern: str) -> Path:
    matches = sorted(CUAD_ROOT.rglob(pattern))
    if not matches:
        raise SystemExit(
            f"No file matching {pattern!r} under {CUAD_ROOT}. "
            "Run ./scripts/download_cuad.sh first."
        )
    return matches[0]


def answer_column(headers: list[str], category: str) -> str:
    for candidate in (f"{category}-Answer", f"{category}- Answer"):
        if candidate in headers:
            return candidate
    raise SystemExit(f"CSV has no answer column for {category!r}")


def all_cuad_categories(headers: list[str]) -> list[str]:
    """Derive all 41 CUAD category names from the CSV's *-Answer columns.

    Derived rather than hand-typed from the README so this can never drift
    out of sync with answer_column()'s own suffix-stripping (e.g. the
    "Notice Period To Terminate Renewal- Answer" space quirk).
    """
    categories = []
    for h in headers:
        if h == "Filename" or "answer" not in h.lower():
            continue
        base = h
        for suffix in ("-Answer", "- Answer"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        categories.append(base.strip())
    return categories


def csv_present(value: str) -> bool:
    """Yes/No fields: Yes. Fact fields (dates, names, states): non-empty."""
    text = (value or "").strip()
    if not text or text.lower() == "no":
        return False
    return True


def pct(n: int, d: int) -> str:
    return f"{n / d:6.1%}" if d else "   n/a"


def print_table(rows: list[tuple[str, ...]], headers: tuple[str, ...]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    fmt = "  ".join(f"{{:{w}}}" for w in widths)
    print(fmt.format(*headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt.format(*row))


def load_csv(
    path: Path, categories: list[str]
) -> tuple[int, dict[str, int], dict[str, list[bool]]]:
    """Per-category positive counts and per-row presence flags."""
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        headers = list(reader.fieldnames or [])
        rows = list(reader)

    flags: dict[str, list[bool]] = {}
    counts: dict[str, int] = {}
    for category in categories:
        col = answer_column(headers, category)
        present = [csv_present(row[col]) for row in rows]
        flags[category] = present
        counts[category] = sum(present)
    return len(rows), counts, flags


def load_json(
    path: Path, categories: list[str]
) -> tuple[int, dict[str, int], dict[str, list[bool]], list[str], dict[str, list[int]]]:
    """Per-category counts, per-doc flags, titles, and highlighted-char lengths."""
    obj = json.loads(path.read_text(encoding="utf-8"))
    docs = obj["data"]
    wanted = set(categories)

    flags: dict[str, list[bool]] = {c: [] for c in wanted}
    span_chars: dict[str, list[int]] = {c: [] for c in wanted}
    titles: list[str] = []

    for doc in docs:
        titles.append(doc["title"])
        answers_by_cat: dict[str, list] = {c: [] for c in wanted}
        for paragraph in doc.get("paragraphs", []):
            for qa in paragraph.get("qas", []):
                category = qa["id"].split("__", 1)[-1]
                if category in wanted:
                    answers_by_cat[category] = qa.get("answers") or []
        for category in wanted:
            answers = answers_by_cat[category]
            flags[category].append(bool(answers))
            span_chars[category].append(sum(len(a.get("text", "")) for a in answers))

    counts = {c: sum(flags[c]) for c in wanted}
    return len(docs), counts, flags, titles, span_chars


def or_count(flags: dict[str, list[bool]], categories: list[str], n: int) -> int:
    return sum(
        1 for i in range(n) if any(flags[c][i] for c in categories)
    )


def mean_text_share(
    titles: list[str],
    highlighted: list[int],
    txt_len: dict[str, int],
) -> str:
    """Avg text share %: mean over ALL contracts of highlighted/total chars.

    Absent contracts contribute 0, not a skip -- this is the PLAN.md ~0.25%
    density figure (how much of the document this label occupies on
    average), not a presence rate. A field can be present in most contracts
    and still have a tiny avg text share, if the clause is short.
    """
    rates = []
    for title, n_hl in zip(titles, highlighted):
        n_chars = txt_len.get(title)
        if n_chars:
            rates.append(n_hl / n_chars)
    if not rates:
        return "n/a"
    return f"{sum(rates) / len(rates):.3%}"


def minority_n(present: int, total: int) -> int:
    """How many examples exist of the rarer class. The real data bottleneck:

    with a fixed n=510, a field's present/absent split ratio and its
    minority-class *count* rank identically, so this one number captures
    both "how balanced" and "how much signal for the rare side" at once.
    """
    return min(present, total - present)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--all-categories",
        action="store_true",
        help="Rank all 41 CUAD categories by training/eval signal (minority-class n).",
    )
    args = parser.parse_args()

    csv_path = find_one("master_clauses.csv")
    json_path = find_one("CUAD_v1.json")

    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        csv_headers = list(csv.DictReader(fh).fieldnames or [])
    all_categories = all_cuad_categories(csv_headers)
    legalpsy_categories = list(dict.fromkeys(cat for _, cats in FIELDS for cat in cats))

    # Loaded once over all 41 categories; the 15-field section below just
    # reads the subset it needs out of these superset dicts.
    n_csv, csv_counts, csv_flags = load_csv(csv_path, all_categories)
    n_json, json_counts, json_flags, titles, span_chars = load_json(json_path, all_categories)

    txt_dir = CUAD_ROOT / "CUAD_v1" / "full_contract_txt"
    txt_len = {
        p.stem: len(p.read_text(encoding="utf-8", errors="replace"))
        for p in txt_dir.glob("*.txt")
    }

    print(f"CSV  {csv_path.relative_to(ROOT)}  ({n_csv} contracts)")
    print(f"JSON {json_path.relative_to(ROOT)}  ({n_json} contracts)")
    print()
    print("Present = clause present (CSV Yes / non-empty fact; JSON has \u22651 span).")
    print("avg text share % = mean(highlighted chars / contract chars) from JSON spans,")
    print("  averaged over ALL contracts (absent ones contribute 0) \u2014 this is the")
    print("  ~0.25%-per-label density figure, not a presence rate.")
    print("naive-absent accuracy = score of a dummy model that always predicts absent,")
    print("  scored against that column's source (= 100% - present %).")
    print()

    headers = (
        "field",
        "csv present (n)",
        "csv present %",
        "json present (n)",
        "json present %",
        "csv/json gap",
        "avg text share %",
        "naive-absent accuracy",
    )
    table: list[tuple[str, ...]] = []
    legalpsy_csv = 0
    legalpsy_json = 0
    legalpsy_n = 0

    for field, categories in FIELDS:
        if len(categories) == 1:
            cat = categories[0]
            cpos = csv_counts[cat]
            jpos = json_counts[cat]
            gap = abs(cpos / n_csv - jpos / n_json)
            table.append(
                (
                    field,
                    f"{cpos}/{n_csv}",
                    pct(cpos, n_csv),
                    f"{jpos}/{n_json}",
                    pct(jpos, n_json),
                    f"{gap:5.1%}",
                    mean_text_share(titles, span_chars[cat], txt_len),
                    pct(n_csv - cpos, n_csv),
                )
            )
            legalpsy_csv += cpos
            legalpsy_json += jpos
            legalpsy_n += n_csv
            continue

        for cat in categories:
            cpos = csv_counts[cat]
            jpos = json_counts[cat]
            gap = abs(cpos / n_csv - jpos / n_json)
            table.append(
                (
                    f"{field} [{cat}]",
                    f"{cpos}/{n_csv}",
                    pct(cpos, n_csv),
                    f"{jpos}/{n_json}",
                    pct(jpos, n_json),
                    f"{gap:5.1%}",
                    mean_text_share(titles, span_chars[cat], txt_len),
                    pct(n_csv - cpos, n_csv),
                )
            )
        c_or = or_count(csv_flags, categories, n_csv)
        j_or = or_count(json_flags, categories, n_json)
        gap = abs(c_or / n_csv - j_or / n_json)
        table.append(
            (
                f"{field} (OR)",
                f"{c_or}/{n_csv}",
                pct(c_or, n_csv),
                f"{j_or}/{n_json}",
                pct(j_or, n_json),
                f"{gap:5.1%}",
                "n/a",
                pct(n_csv - c_or, n_csv),
            )
        )
        legalpsy_csv += c_or
        legalpsy_json += j_or
        legalpsy_n += n_csv

    print_table(table, headers)

    or_note = " (multi-category fields counted via OR)" if any(
        len(cats) > 1 for _, cats in FIELDS
    ) else ""
    print()
    print(f"15-field aggregate (one item per field per contract{or_note})")
    print(f"  items                       {legalpsy_n}")
    print(f"  csv present %                {legalpsy_csv}/{legalpsy_n}  {legalpsy_csv / legalpsy_n:.1%}")
    print(f"  json present %               {legalpsy_json}/{legalpsy_n}  {legalpsy_json / legalpsy_n:.1%}")
    print(
        f"  naive-absent accuracy (csv) {(legalpsy_n - legalpsy_csv) / legalpsy_n:.1%}"
        "   (PLAN Day-5 fake model used ~99.7%)"
    )
    print()
    print(
        "If the item rate is tens of percent, 99.75% negative is density, not class "
        "balance. Per-label avg text share % should still sit near 0.25%."
    )

    if args.all_categories:
        print()
        print("=" * 100)
        print("All 41 CUAD categories, ranked by minority-class n (highest = most")
        print("balanced = most real signal for BOTH present and absent behaviour,")
        print("since every category is measured over the same 510 contracts).")
        print()
        print("This is a statistical view, not a recommendation to change the schema:")
        print("PLAN.md Sec 1.1 fixes the 15 fields by commercial relevance (what")
        print("Pramata monetizes), not by balance. '*' marks a category already in")
        print("the current 15-field schema.")
        print("=" * 100)
        print()

        stats = []
        for cat in all_categories:
            cpos = csv_counts[cat]
            jpos = json_counts[cat]
            gap = abs(cpos / n_csv - jpos / n_json)
            m = minority_n(cpos, n_csv)
            stats.append(
                {
                    "cat": cat,
                    "cpos": cpos,
                    "gap": gap,
                    "minority": m,
                    "balance": m / n_csv,
                    "density": mean_text_share(titles, span_chars[cat], txt_len),
                    "used": cat in legalpsy_categories,
                }
            )
        stats.sort(key=lambda s: s["minority"], reverse=True)

        rows = []
        for rank, s in enumerate(stats, start=1):
            name = s["cat"] + (" *" if s["used"] else "")
            rows.append(
                (
                    f"{rank}",
                    name,
                    f"{s['cpos']}/{n_csv}",
                    pct(s["cpos"], n_csv),
                    pct(n_csv - s["cpos"], n_csv),
                    f"{s['minority']}",
                    f"{s['balance']:5.1%}",
                    f"{s['gap']:5.1%}",
                    s["density"],
                )
            )
        print_table(
            rows,
            (
                "rank",
                "category",
                "csv present (n)",
                "csv present %",
                "naive-absent accuracy",
                "minority n",
                "balance",
                "csv/json gap",
                "avg text share %",
            ),
        )

        print()
        print("Top 10 by balance (best signal for learning true present/absent")
        print("discrimination -- neither 'always yes' nor 'always no' is a free ride):")
        for s in stats[:10]:
            tag = "in current 15" if s["used"] else "NOT in current 15"
            print(
                f"  {s['cat']:38s} balance={s['balance']:5.1%}  "
                f"minority_n={s['minority']:3d}  ({tag})"
            )

        print()
        print("Bottom 10 by balance (most skewed -- easiest to shortcut, thinnest")
        print("minority-class data; watch these for over-abstention / memorization):")
        for s in stats[-10:]:
            tag = "in current 15" if s["used"] else "not in current 15"
            print(
                f"  {s['cat']:38s} balance={s['balance']:5.1%}  "
                f"minority_n={s['minority']:3d}  ({tag})"
            )

        print()
        print("Where the current 15-field schema's CUAD categories rank out of 41")
        print("(by minority n -- lower rank number = more balanced):")
        for rank, s in enumerate(stats, start=1):
            if s["used"]:
                print(
                    f"  #{rank:2d}/41  {s['cat']:38s} "
                    f"minority_n={s['minority']:3d}  balance={s['balance']:5.1%}"
                )

        total_n = n_csv * len(all_categories)
        total_csv_pos = sum(csv_counts[c] for c in all_categories)
        total_json_pos = sum(json_counts[c] for c in all_categories)
        densities = [
            float(s["density"].rstrip("%")) for s in stats if s["density"] != "n/a"
        ]
        mean_density = sum(densities) / len(densities)

        print()
        print("All-41 aggregate (contract, category) item rate -- this is the number")
        print("that resolves whether PLAN.md's ~99.75%-negative claim is an item rate")
        print("or a misread of character density:")
        print(f"  items                          {total_n}  (= {n_csv} contracts x {len(all_categories)} categories)")
        print(f"  csv present %                  {total_csv_pos}/{total_n}  {total_csv_pos / total_n:.1%}")
        print(f"  json present %                 {total_json_pos}/{total_n}  {total_json_pos / total_n:.1%}")
        print(f"  naive-absent accuracy (csv)    {(total_n - total_csv_pos) / total_n:.1%}")
        print(
            f"  mean avg text share % (41 cats) {mean_density:.3f}%   "
            "(PLAN.md At-a-glance claims ~0.25%)"
        )


if __name__ == "__main__":
    main()
