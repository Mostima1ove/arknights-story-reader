#!/usr/bin/env bash
# 一行装（macOS / Linux）
# 用法：curl -fsSL https://raw.githubusercontent.com/<你的用户名>/arknights-story-reader/main/install.sh | bash
set -euo pipefail

REPO="https://github.com/Mostima1ove/arknights-story-reader"
NAME="arknights-story-reader"
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
SKILLS="$DSH_HOME/skills"
DEST="$SKILLS/$NAME"

mkdir -p "$SKILLS"

if command -v git >/dev/null 2>&1; then
  if [ -d "$DEST/.git" ]; then
    echo "更新已有安装 ..."
    git -C "$DEST" pull --ff-only
  else
    echo "克隆到 $DEST ..."
    rm -rf "$DEST"
    git clone --depth 1 "$REPO" "$DEST"
  fi
else
  echo "没装 git，改用 zip 包 ..."
  TMP=$(mktemp -d)
  curl -fsSL "$REPO/archive/refs/heads/main.zip" -o "$TMP/pkg.zip"
  (cd "$TMP" && unzip -q pkg.zip)
  SRC=$(find "$TMP" -maxdepth 1 -type d -name '*-main' | head -1)
  rm -rf "$DEST"
  cp -R "$SRC" "$DEST"
  rm -rf "$TMP"
fi

PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ] && [ -x "$DSH_HOME/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3" ]; then
  PY="$DSH_HOME/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3"
fi

if [ -n "$PY" ]; then
  echo "安装依赖 pillow / numpy ..."
  "$PY" -m pip install --quiet pillow numpy
  "$PY" -c "import PIL, numpy; print('依赖 OK')"
else
  echo "没找到 Python，请手动装：pip install pillow numpy"
fi

echo ""
echo "装好了：$DEST"
echo "重启 DSH 后生效；之后说「把《活动名》的剧情做成读本」就会用它。"
