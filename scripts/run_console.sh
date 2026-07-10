#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONSOLE_DIR="$ROOT/web/console"

if [ ! -d "$CONSOLE_DIR/node_modules" ]; then
  (cd "$CONSOLE_DIR" && npm install)
fi

cd "$CONSOLE_DIR"
npm run dev
