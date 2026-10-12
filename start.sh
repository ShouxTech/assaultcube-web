#!/bin/sh
# Serves AssaultCube on http://localhost:8000 (needs Python 3). Stop with Ctrl+C.
cd "$(dirname "$0")"
PORT="${1:-8000}"
echo "AssaultCube: open http://localhost:$PORT"
exec python3 -m http.server "$PORT" --bind 127.0.0.1
