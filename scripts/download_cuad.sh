#!/usr/bin/env bash
# Download and unpack the full CUAD v1 release (txt + pdf + master CSV + QA JSON).
#
# Deliberately NOT using `datasets.load_dataset("cuad")` / the HF QA-only mirror:
# that version omits the master CSV (no yes/no -> no free absence labels) and
# the PDFs. Source of truth here is the Zenodo archive (PLAN-DAY-01.md Block 3).
#
# Safe to run from the laptop or a GPU server: paths resolve relative to the
# repo root, the download is skipped if the zip already exists, and the
# checksum is verified before unzipping.
#
# Usage: ./scripts/download_cuad.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/data/raw/cuad"
ZIP_URL="https://zenodo.org/records/4595826/files/CUAD_v1.zip"
ZIP_NAME="CUAD_v1.zip"
EXPECTED_MD5="c38f490a984420b8a62600db401fafd5"

mkdir -p "$DEST"
cd "$DEST"

if [[ -f "$ZIP_NAME" ]]; then
  echo "Found existing $ZIP_NAME, skipping download."
else
  echo "Downloading $ZIP_NAME from Zenodo..."
  curl -L --fail -o "$ZIP_NAME" "$ZIP_URL"
fi

echo "Verifying checksum..."
if command -v md5sum >/dev/null 2>&1; then
  echo "${EXPECTED_MD5}  ${ZIP_NAME}" | md5sum -c -
elif command -v md5 >/dev/null 2>&1; then
  ACTUAL_MD5="$(md5 -q "$ZIP_NAME")"
  if [[ "$ACTUAL_MD5" != "$EXPECTED_MD5" ]]; then
    echo "Checksum mismatch: expected $EXPECTED_MD5, got $ACTUAL_MD5" >&2
    exit 1
  fi
  echo "$ZIP_NAME: OK"
else
  echo "Warning: no md5sum/md5 tool found, skipping checksum verification." >&2
fi

echo "Unzipping..."
unzip -o -q "$ZIP_NAME"

echo
echo "Done. Top-level contents of $DEST:"
find "$DEST" -maxdepth 2 -mindepth 1 | sed "s|$DEST/|  |"
