#!/usr/bin/env bash
set -euo pipefail
REPO="https://github.com/Mostima1ove/arknights-story-reader"
NAME="arknights-story-reader"
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
DEST="$DSH_HOME/skills/$NAME"
mkdir -p "$DSH_HOME/skills"
if command -v git >/dev/null 2>&1; then
  if [ -d "$DEST/.git" ]; then git -C "$DEST" pull --ff-only
  else rm -rf "$DEST"; git clone --depth 1 "$REPO" "$DEST"; fi
else
  TMP=$(mktemp -d)
  curl -fsSL "$REPO/archive/refs/heads/main.zip" -o "$TMP/pkg.zip"
  (cd "$TMP" && unzip -q pkg.zip)
  SRC=$(find "$TMP" -maxdepth 1 -type d -name '*-main' | head -1)
  rm -rf "$DEST"; cp -R "$SRC" "$DEST"; rm -rf "$TMP"
fi
PY=""
for c in python3 python; do command -v "$c" >/dev/null 2>&1 && PY="$c" && break; done
[ -n "$PY" ] && "$PY" -m pip install --quiet pillow numpy opencv-python-headless
echo "装好了：$DEST"
