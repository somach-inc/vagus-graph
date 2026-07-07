#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/dist"
SOURCE_DIR="$ROOT_DIR/butterbase-static"
ZIP_PATH="$OUT_DIR/vagus-graph-butterbase.zip"

mkdir -p "$OUT_DIR"
rm -f "$ZIP_PATH"

(
  cd "$SOURCE_DIR"
  zip -qr "$ZIP_PATH" .
)

echo "$ZIP_PATH"
