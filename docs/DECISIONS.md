# Decisions

Format: `Dn · YYYY-MM-DD · decision · rationale · revisit-if`

## D0 · 2026-08-__ · Compute
...

## D7 · 2026-08-__ · Python 3.12, uv, src layout, argparse
Rationale: 3.13 wheel risk in the PDF/ML stack; src layout so `python -m legalpsy.cli.eval` works from anywhere.
Revisit if: a required package is 3.13-only.
