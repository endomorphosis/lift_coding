#!/bin/bash
# Kill the chunk-driver machinery by exact comm match (never pattern-matches
# our own shell: this file's path is all that appears in the caller cmdline).
for pid in $(pgrep -x bash); do
  cmd=$(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)
  case "$cmd" in
    *supervise_chunks2.sh*|*run_chunks2.sh*|*run_chunks.sh*)
      kill $pid 2>/dev/null && echo "killed driver-shell $pid :: $cmd" ;;
  esac
done
sleep 1
for pid in $(pgrep -x git); do
  cmd=$(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)
  case "$cmd" in
    *"checkout f4a823231ad52c9252504810a1b00ed4738346b6"*)
      kill $pid 2>/dev/null && echo "killed git $pid" ;;
  esac
done
for pid in $(pgrep -x timeout); do
  cmd=$(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)
  case "$cmd" in
    *"checkout f4a823231ad52c9252504810a1b00ed4738346b6"*)
      kill $pid 2>/dev/null && echo "killed timeout $pid" ;;
  esac
done
sleep 2
echo "--- remaining:"
ps -eo pid,cmd | grep -E "chunks|f4a823" | grep -v grep | head -5
echo "(end)"
