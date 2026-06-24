#!/usr/bin/env bash
set -euo pipefail

TARGET_INSTANCES="${TARGET_INSTANCES:-512}"
TARGET_WATCHES="${TARGET_WATCHES:-262144}"
TARGET_QUEUE="${TARGET_QUEUE:-32768}"
SYSCTL_DROPIN="${SYSCTL_DROPIN:-/etc/sysctl.d/99-lift-coding-inotify.conf}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/inotify_doctor.sh check
  scripts/inotify_doctor.sh apply

Commands:
  check  Print inotify limits, current usage, and top consumers.
  apply  Persist recommended limits in /etc/sysctl.d and reload sysctl.
         Requires root privileges.

Environment overrides:
  TARGET_INSTANCES (default: 512)
  TARGET_WATCHES   (default: 262144)
  TARGET_QUEUE     (default: 32768)
  SYSCTL_DROPIN    (default: /etc/sysctl.d/99-lift-coding-inotify.conf)
USAGE
}

current_sysctl() {
  sysctl -n "$1" 2>/dev/null || echo "unknown"
}

print_top_consumers() {
  python3 - <<'PY'
import os,glob
from collections import Counter
counter = Counter()
for fd in glob.glob('/proc/[0-9]*/fd/*'):
    try:
        if os.readlink(fd) == 'anon_inode:inotify':
            pid = int(fd.split('/')[2])
            counter[pid] += 1
    except Exception:
        pass

total = sum(counter.values())
print(f"TOTAL_INOTIFY_INSTANCES={total}")
for pid,count in counter.most_common(25):
    cmd = ''
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            cmd = f.read().replace(b'\x00', b' ').decode('utf-8', 'ignore').strip()
    except Exception:
        cmd = '[unreadable]'
    if not cmd:
        cmd = '[kernel-or-empty]'
    print(f"{count:4d} pid={pid} {cmd[:200]}")
PY
}

check_cmd() {
  local cur_instances cur_watches cur_queue
  cur_instances="$(current_sysctl fs.inotify.max_user_instances)"
  cur_watches="$(current_sysctl fs.inotify.max_user_watches)"
  cur_queue="$(current_sysctl fs.inotify.max_queued_events)"

  echo "fs.inotify.max_user_instances=${cur_instances}"
  echo "fs.inotify.max_user_watches=${cur_watches}"
  echo "fs.inotify.max_queued_events=${cur_queue}"
  echo
  print_top_consumers
  echo
  echo "Recommended floor for this workspace:"
  echo "  fs.inotify.max_user_instances=${TARGET_INSTANCES}"
  echo "  fs.inotify.max_user_watches=${TARGET_WATCHES}"
  echo "  fs.inotify.max_queued_events=${TARGET_QUEUE}"
}

apply_cmd() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "error: apply requires root. Re-run with sudo." >&2
    exit 1
  fi

  install -d -m 0755 "$(dirname "${SYSCTL_DROPIN}")"
  cat > "${SYSCTL_DROPIN}" <<EOF
fs.inotify.max_user_instances=${TARGET_INSTANCES}
fs.inotify.max_user_watches=${TARGET_WATCHES}
fs.inotify.max_queued_events=${TARGET_QUEUE}
EOF

  sysctl --system >/dev/null
  echo "Applied inotify limits from ${SYSCTL_DROPIN}"
  check_cmd
}

main() {
  local cmd="${1:-check}"
  case "${cmd}" in
    check)
      check_cmd
      ;;
    apply)
      apply_cmd
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
