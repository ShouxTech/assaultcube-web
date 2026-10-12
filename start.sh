#!/bin/sh
# Serves AssaultCube on http://localhost:8000 (needs Python 3). Stop with Ctrl+C.
cd "$(dirname "$0")"
PORT="${1:-8000}"
echo "AssaultCube: open http://localhost:$PORT"
( sleep 1; (open "http://localhost:$PORT" || xdg-open "http://localhost:$PORT") >/dev/null 2>&1 ) &
exec python3 -m http.server "$PORT" --bind 127.0.0.1
