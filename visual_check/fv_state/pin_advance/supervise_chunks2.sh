#!/bin/bash
# Retry wrapper for run_chunks2.sh: relaunches it if it dies without
# printing DRIVER2-DONE (VM reboots / session teardowns kill detached
# drivers in this environment). Chunks are resumable via chunks2.done.
PA="$HOME/workspace/lift_coding/visual_check/fv_state/pin_advance"
for i in $(seq 1 60); do
  if grep -q "DRIVER2-DONE" "$PA/chunks2.log" 2>/dev/null; then
    echo "supervisor: DRIVER2-DONE present, exiting" >> "$PA/supervisor.log"
    exit 0
  fi
  echo "supervisor: launching driver attempt $i $(date -u +%FT%TZ)" >> "$PA/supervisor.log"
  bash "$PA/run_chunks2.sh" >> "$PA/driver2.out" 2>&1
  echo "supervisor: driver attempt $i exited rc=$? $(date -u +%FT%TZ)" >> "$PA/supervisor.log"
  sleep 10
done
echo "supervisor: exhausted attempts" >> "$PA/supervisor.log"
