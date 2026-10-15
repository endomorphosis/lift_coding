#!/usr/bin/env bash
# Resume the 3-lane PGIR supervisor after the current bounded master exits.
# Uses the Grok-4.6 / Codex gpt-5.6-terra launcher. Never starts a second
# master while a live pgir_parallel_master_*.pid process exists.
set -euo pipefail

PGIR_RUNTIME=/home/barberb/lift_coding/.pgir_campaign/runtime
PGIR_REPO=/home/barberb/lift_coding/.pgir_campaign/worktrees/accelerate-authority
PGIR_TARGET=agent/proof-grounded-ir-learning
OLD_MASTER_PID="${1:-3868772}"
LOG="$PGIR_RUNTIME/master/pgir_parallel_successor_waiter.log"
LAUNCH="$PGIR_RUNTIME/launch_pgir_parallel_grok.sh"

live_master() {
  if kill -0 "$OLD_MASTER_PID" 2>/dev/null; then
    return 0
  fi
  python3 - <<'PY'
from pathlib import Path
import sys
for p in Path("/home/barberb/lift_coding/.pgir_campaign/runtime/master").glob("pgir_parallel_master_*.pid"):
    try:
        pid = int(p.read_text().strip())
    except Exception:
        continue
    if Path(f"/proc/{pid}").exists():
        sys.exit(0)
sys.exit(1)
PY
}

{
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) waiting for master $OLD_MASTER_PID to exit"
  while live_master; do
    sleep 30
  done
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) no live parallel master; launching successor"
  if [[ "$(git -C "$PGIR_REPO" branch --show-current)" != "$PGIR_TARGET" ]]; then
    echo "refusing successor: unexpected branch $(git -C "$PGIR_REPO" branch --show-current)" >&2
    exit 2
  fi
  exec "$LAUNCH"
} >>"$LOG" 2>&1
