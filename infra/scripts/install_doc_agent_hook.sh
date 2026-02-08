#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
HOOK_SRC="$ROOT_DIR/infra/hooks/post-commit"
HOOK_DST="$ROOT_DIR/.git/hooks/post-commit"

if [[ ! -f "$HOOK_SRC" ]]; then
  echo "Doc agent hook not found at $HOOK_SRC" >&2
  exit 1
fi

if [[ -f "$HOOK_DST" ]]; then
  if ! cmp -s "$HOOK_SRC" "$HOOK_DST"; then
    echo "Existing post-commit hook detected at $HOOK_DST" >&2
    echo "Refusing to overwrite. Merge manually or move the existing hook." >&2
    exit 1
  fi
fi

cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"

echo "Installed post-commit hook to $HOOK_DST"
