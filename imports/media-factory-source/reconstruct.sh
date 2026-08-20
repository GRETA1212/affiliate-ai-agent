#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMPORT_DIR="$REPO_ROOT/imports/media-factory-source"
ARCHIVE="${TMPDIR:-/tmp}/media-factory-source.tar.xz"
EXPECTED="c9fb36364e49b5e0f92af0bfbe0bfb96a7a11b81e26fb8361b15c8de88823876"

cat "$IMPORT_DIR"/part-*.b64 | base64 --decode > "$ARCHIVE"

if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  ACTUAL="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
else
  echo "No SHA-256 tool found (need sha256sum or shasum)." >&2
  exit 1
fi

if [[ "$ACTUAL" != "$EXPECTED" ]]; then
  echo "Archive hash mismatch." >&2
  echo "Expected: $EXPECTED" >&2
  echo "Actual:   $ACTUAL" >&2
  exit 1
fi

if [[ -e "$REPO_ROOT/media-factory" ]]; then
  echo "Refusing to overwrite existing $REPO_ROOT/media-factory" >&2
  exit 1
fi

tar -xJf "$ARCHIVE" -C "$REPO_ROOT"
echo "Extracted verified source to $REPO_ROOT/media-factory"
