# Class balance — all 41 CUAD categories

Source: `scripts/class_balance.py`, run against `data/raw/cuad/CUAD_v1/` (510 contracts, both `master_clauses.csv` and `CUAD_v1.json`, cross-checked independently). Reproduce:

```bash
python scripts/class_balance.py                 # the 15 LegalPsy fields
python scripts/class_balance.py --all-categories # all 41 CUAD categories, ranked
```

This is the `PLAN-DAY-01.md` Block 4 deliverable: test whether *"CUAD is ~99.75% negative per label per contract"* (`PLAN.md` At-a-glance) is a real item-level class-balance claim, or a misread of the *"~0.25% of a contract is highlighted for any given label"* character-density figure (`PLAN.md` §8).

**Update, 2026-08-19 (`docs/DECISIONS.md` D8):** this analysis motivated one schema change. Field 13 (MFN / Price Restrictions) was too data-thin to keep — 28/510 and 15/510 positive — and was swapped for **License Grant** (255/510, the best-balanced category in all of CUAD). The other 14 fields, including `Parties` despite ranking last of 41 on balance, stay as `PLAN.md` §1.1's commercial picks. All tables below reflect the schema after that change; the all-41 analysis itself (which categories exist, their raw rates) is unaffected by which 15 are chosen.

## Verdict

**Misread. The real item-level positive rate is ~31–32%, not 0.25%.** Both figures are individually correct — they just measure different things. 0.25% is *how much of a document's text* a label occupies on average. ~31% is *how often the label is present at all*. A label can be present in a third of contracts and still occupy a tiny share of characters, because the clause itself is short.

Measured two independent ways, over all 510 contracts × 41 categories = 20,910 `(contract, category)` items:

| Source | items | positive (n) | **positive %** | naive-absent accuracy |
|---|---|---|---|---|
| CSV yes/no columns | 20,910 | 6,558 | **31.4%** | 68.6% |
| QA JSON (≥1 span) | 20,910 | 6,702 | **32.1%** | 67.9% |

The two sources agree within 0.7 points in aggregate. Mean per-category text-share density across all 41 categories: **0.363%** — same order of magnitude as PLAN.md's ~0.25% claim, so the density intuition was basically right; the class-balance conclusion drawn from it was not.

**Consequence for `PLAN-DAYS-1-7.md` Day 5:** the always-absent fake-model baseline should expect **~68–69% accuracy**, not ~99.7%. That prediction is currently wrong and needs correcting before Day 5, since the point of that baseline is to sanity-check the metric itself.

## All 41 categories, ranked by training/eval signal

"Best suited for this research" is operationalized here as **minority-class n** — of the 510 contracts, how many fall on the *rarer* side of present/absent for that category. This is the real bottleneck: a model needs enough examples of the rare class to learn it, and an eval set needs enough of them to score reliably. Because every category is measured over the same 510 contracts, minority-class count and "how close to 50/50" (`balance`) rank identically — one number captures both.

`*` marks a category already in the current 15-field schema (`PLAN.md` §1.1).

```
rank  category                              csv present (n)  csv present %  naive-absent accuracy  minority n  balance  csv/json gap  avg text share %
----  ------------------------------------  ---------------  -------------  ---------------------  ----------  -------  ------------  ----------------
1     License Grant *                       255/510           50.0%          50.0%                 255         50.0%     0.0%         1.232%
2     Cap On Liability *                    275/510           53.9%          46.1%                 235         46.1%     0.0%         0.995%
3     Audit Rights                          214/510           42.0%          58.0%                 214         42.0%     0.0%         0.557%
4     Termination For Convenience *         183/510           35.9%          64.1%                 183         35.9%     0.0%         0.293%
5     Post-Termination Services             182/510           35.7%          64.3%                 182         35.7%     0.0%         0.517%
6     Expiration Date *                     329/510           64.5%          35.5%                 181         35.5%    16.5%         0.738%
7     Exclusivity *                         180/510           35.3%          64.7%                 180         35.3%     0.0%         0.632%
8     Insurance                             167/510           32.7%          67.3%                 167         32.7%     0.2%         0.554%
9     Revenue/Profit Sharing                166/510           32.5%          67.5%                 166         32.5%     0.0%         0.655%
10    Minimum Commitment *                  165/510           32.4%          67.6%                 165         32.4%     0.0%         0.548%
11    Renewal Term *                        163/510           32.0%          68.0%                 163         32.0%     2.5%         0.361%
12    Effective Date *                      359/510           70.4%          29.6%                 151         29.6%     6.1%         0.265%
13    Non-Transferable License              138/510           27.1%          72.9%                 138         27.1%     0.0%         0.394%
14    Anti-Assignment *                     374/510           73.3%          26.7%                 136         26.7%     0.0%         0.823%
15    Ip Ownership Assignment               124/510           24.3%          75.7%                 124         24.3%     0.0%         0.547%
16    Change Of Control *                   121/510           23.7%          76.3%                 121         23.7%     0.0%         0.294%
17    Non-Compete                           119/510           23.3%          76.7%                 119         23.3%     0.0%         0.427%
18    Uncapped Liability *                  111/510           21.8%          78.2%                 111         21.8%     0.0%         0.239%
19    Notice Period To Terminate Renewal *  101/510           19.8%          80.2%                 101         19.8%     2.0%         0.222%
20    Covenant Not To Sue                   100/510           19.6%          80.4%                 100         19.6%     0.0%         0.260%
21    Rofr/Rofo/Rofn                        85/510            16.7%          83.3%                 85          16.7%     0.0%         0.428%
22    Volume Restriction                    82/510            16.1%          83.9%                 82          16.1%     0.0%         0.230%
23    Governing Law *                       434/510           85.1%          14.9%                 76          14.9%     0.6%         0.614%
24    Competitive Restriction Exception     76/510            14.9%          85.1%                 76          14.9%     0.0%         0.236%
25    Warranty Duration                     75/510            14.7%          85.3%                 75          14.7%     0.0%         0.236%
26    Irrevocable Or Perpetual License      70/510            13.7%          86.3%                 70          13.7%     0.0%         0.256%
27    Liquidated Damages *                  61/510            12.0%          88.0%                 61          12.0%     0.0%         0.174%
28    No-Solicit Of Employees               59/510            11.6%          88.4%                 59          11.6%     0.0%         0.175%
29    Affiliate License-Licensee            59/510            11.6%          88.4%                 59          11.6%     0.0%         0.200%
30    Joint Ip Ownership                    46/510             9.0%          91.0%                 46           9.0%     0.0%         0.086%
31    Agreement Date                        465/510           91.2%           8.8%                 45           8.8%     1.0%         0.109%
32    Non-Disparagement                     38/510             7.5%          92.5%                 38           7.5%     0.0%         0.105%
33    No-Solicit Of Customers               34/510             6.7%          93.3%                 34           6.7%     0.0%         0.096%
34    Third Party Beneficiary               33/510             6.5%          93.5%                 33           6.5%     0.2%         0.045%
35    Most Favored Nation                   28/510             5.5%          94.5%                 28           5.5%     0.0%         0.075%
36    Affiliate License-Licensor            23/510             4.5%          95.5%                 23           4.5%     0.0%         0.094%
37    Unlimited/All-You-Can-Eat-License     17/510             3.3%          96.7%                 17           3.3%     0.0%         0.069%
38    Price Restrictions                    15/510             2.9%          97.1%                 15           2.9%     0.0%         0.053%
39    Source Code Escrow                    13/510             2.5%          97.5%                 13           2.5%     0.0%         0.100%
40    Parties *                             509/510           99.8%           0.2%                 1            0.2%     0.0%         0.717%
41    Document Name                         510/510          100.0%           0.0%                 0            0.0%     0.0%         0.248%
```

(Sorted by minority n / balance rather than by raw rate, since that's what answers "which terms are best suited for the research." The raw rate spread is visible in the `csv present %` column regardless: from 2.5% to 100%.)

## Which terms are best suited for this research

**Top 10 by balance** (best signal for learning true present/absent discrimination — neither "always yes" nor "always no" is a free ride):

| Category | Balance | Minority n | In current 15? |
|---|---|---|---|
| License Grant | 50.0% | 255 | **Yes** (added 2026-08-19, replacing MFN/Price Restrictions — D8) |
| Cap On Liability | 46.1% | 235 | **Yes** |
| Audit Rights | 42.0% | 214 | No |
| Termination For Convenience | 35.9% | 183 | **Yes** |
| Post-Termination Services | 35.7% | 182 | No |
| Expiration Date | 35.5% | 181 | **Yes** |
| Exclusivity | 35.3% | 180 | **Yes** |
| Insurance | 32.7% | 167 | No |
| Revenue/Profit Sharing | 32.5% | 166 | No |
| Minimum Commitment | 32.4% | 165 | **Yes** |

6 of the 10 statistically best-balanced categories in all of CUAD are now in the current 15-field schema (was 5 of 10 before the D8 swap). The schema is still chosen for commercial relevance (`PLAN.md` §1.1 — what Pramata monetizes) first, and it lands well on the statistics as a side effect for 13 of the 14 unchanged fields.

**The remaining weak point in the current 15** is `Parties` (rank 40/41, minority n = 1): with only 1 absent example in 510 contracts, "present/absent" is not a meaningful classification target for it at all — it's really a *which-parties* extraction task wearing a presence/absence label. Don't score it as an abstention field; score extraction quality (did the model name the right parties) instead. Kept as-is (`docs/DECISIONS.md` D8) since it's commercially load-bearing ("every downstream join key," `PLAN.md` §1.1) regardless of its balance.

**Statistically attractive categories still not in scope:** Audit Rights (#3), Post-Termination Services (#5), Insurance (#8), and Revenue/Profit Sharing (#9) all outrank several of the current 15 on pure balance. This remains informational, not a recommendation to swap further — `PLAN.md` §1.1's selection criterion is commercial relevance, which this analysis doesn't speak to for these four. Worth knowing if the schema is ever revisited or extended again.

## The 15-field schema, sorted by rate

From `python scripts/class_balance.py` (unfiltered run), reordered ascending by CSV presence rate:

| Field | csv present (n) | csv present % | json present % | csv/json gap | naive-absent accuracy |
|---|---|---|---|---|---|
| liquidated_damages | 61/510 | 12.0% | 12.0% | 0.0% | 88.0% |
| notice_period_to_terminate_renewal | 101/510 | 19.8% | 21.8% | 2.0% | 80.2% |
| uncapped_liability | 111/510 | 21.8% | 21.8% | 0.0% | 78.2% |
| change_of_control | 121/510 | 23.7% | 23.7% | 0.0% | 76.3% |
| renewal_term | 163/510 | 32.0% | 34.5% | 2.5% | 68.0% |
| minimum_commitment | 165/510 | 32.4% | 32.4% | 0.0% | 67.6% |
| exclusivity | 180/510 | 35.3% | 35.3% | 0.0% | 64.7% |
| termination_for_convenience | 183/510 | 35.9% | 35.9% | 0.0% | 64.1% |
| license_grant | 255/510 | 50.0% | 50.0% | 0.0% | 50.0% |
| cap_on_liability | 275/510 | 53.9% | 53.9% | 0.0% | 46.1% |
| expiration_date | 329/510 | 64.5% | 81.0% | 16.5% | 35.5% |
| effective_date | 359/510 | 70.4% | 76.5% | 6.1% | 29.6% |
| anti_assignment | 374/510 | 73.3% | 73.3% | 0.0% | 26.7% |
| governing_law | 434/510 | 85.1% | 85.7% | 0.6% | 14.9% |
| parties | 509/510 | 99.8% | 99.8% | 0.0% | 0.2% |

**15-field aggregate** (one item per field per contract, 7,650 items): 47.3% positive (CSV) / 49.2% positive (JSON) / 52.7% naive-absent accuracy. (Before the D8 swap, with MFN/Price Restrictions counted via OR: 44.5% / 46.4% / 55.5%. License Grant's 50/510 balance pulled the aggregate up ~3 points.)

`expiration_date` and `effective_date` carry the largest CSV/JSON gaps (16.5 and 6.1 points). Both are date fields, where the CSV's answer is a *derived* value (e.g. computed from "3 years after Effective Date") while the JSON only has a span if CUAD annotators highlighted literal date text — so JSON systematically under-counts presence for computed dates. Treat the CSV yes/no column as the presence label for dates; use JSON only for span/citation supervision where a literal span exists.

## What this does to the abstention pitch

The abstention framing survives, and gets more interesting, not less. A benchmark that was uniformly ~99.75% negative would make "predict absent" an almost-free 99.75% score everywhere — a weak design, since it can't distinguish a model that understands absence from one that just never answers. What's actually here is a **spread of naive-absent accuracy from 0.0% to 97.5%** across categories: `Document Name` is present in all 510 contracts (so "always predict absent" scores 0%), `Parties` in 509/510 (0.2%), while `Source Code Escrow` and `Price Restrictions` are present in barely 2.5–2.9% of contracts (so "always predict absent" scores ~97% there). That spread is a *better* experimental design than a flat rate: it lets the eval show whether a model's abstention rate actually tracks the true base rate per field, rather than collapsing to one learned prior. The number that can no longer be used, in a writeup or anywhere else, is "CUAD is 99.75% negative" as an item-level claim — it isn't. The defensible version is: *most `(contract, field)` pairs are negative for the 15 chosen fields (52.7%), absence is the majority answer for most of them, the naive-absent-accuracy baseline varies by nearly two orders of magnitude field to field, and the commonly-cited density figure is a different, smaller number measuring something else entirely.*

## Open follow-up

`PLAN.md`'s At-a-glance and §8, and `PLAN-DAYS-1-7.md`'s Trap 5 and Day 5 fake-model table, still cite the inherited ~99.75% / ~0.25%-as-class-balance numbers. Per `PLAN-DAY-01.md` Block 4, those should be updated to cite this document's measured numbers instead — not done here since it wasn't asked for in this pass.
