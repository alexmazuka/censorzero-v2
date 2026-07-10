#!/usr/bin/env bash
# Wait until an outlet's host stops blocking us, then run the gentle fetch.
# The fetch itself is resumable (spool) and has its own cooldown/abort logic.
set -u
OUTLET="${1:?usage: fetch_when_ready.sh <outlet> <probe_url>}"
PROBE="${2:?missing probe url}"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
cd "$(dirname "$0")/.."

while true; do
  code=$(curl -s -m 12 -L -o /dev/null -w "%{http_code}" -A "$UA" "$PROBE")
  if [ "$code" = "200" ]; then
    echo "$(date +%H:%M:%S) $OUTLET reachable (200) — starting fetch"
    uv run --frozen python scripts/01_snapshot.py fetch "$OUTLET"
    rc=$?
    if [ $rc -eq 0 ]; then echo "$OUTLET fetch complete"; break; fi
    echo "$(date +%H:%M:%S) $OUTLET fetch exited rc=$rc (likely re-throttled); waiting 180s then resuming"
    sleep 180
  else
    echo "$(date +%H:%M:%S) $OUTLET blocked ($code); waiting 60s"
    sleep 60
  fi
done
