#!/usr/bin/env bash
set -u

workspace="${1:-${IPFS_ACCELERATE_AGENT_MERGE_WORKSPACE:-$(pwd)}}"
prompt_file="$(mktemp)"
trap 'rm -f "$prompt_file"' EXIT
cat > "$prompt_file"

git_common_dir="$(git -C "$workspace" rev-parse --git-common-dir 2>/dev/null || true)"
if [[ -n "$git_common_dir" && "${AGENT_RESOLVER_LOCK_BYPASS:-0}" != "1" ]] && command -v flock >/dev/null 2>&1; then
  if [[ "$git_common_dir" != /* ]]; then
    git_common_dir="$workspace/$git_common_dir"
  fi
  mkdir -p "$git_common_dir"
  exec 9>"$git_common_dir/agent-llm-resolver.lock"
  flock 9
fi

codex_bin="${CODEX_BIN:-$(command -v codex || true)}"
copilot_bin="${COPILOT_BIN:-$(command -v copilot || true)}"
codex_timeout_seconds="${CODEX_MERGE_RESOLVER_TIMEOUT_SECONDS:-60}"
prefer_copilot="${PREFER_COPILOT_MERGE_RESOLVER:-0}"

if [[ -n "$codex_bin" && "$prefer_copilot" != "1" ]]; then
  codex_command=("$codex_bin" exec --dangerously-bypass-approvals-and-sandbox -C "$workspace" -)
  if command -v timeout >/dev/null 2>&1 && [[ "$codex_timeout_seconds" != "0" ]]; then
    codex_command=(timeout "${codex_timeout_seconds}s" "${codex_command[@]}")
  fi
  if "${codex_command[@]}" < "$prompt_file"; then
    exit 0
  fi
  rc=$?
  printf 'codex merge resolver failed with exit %s; falling back to copilot\n' "$rc" >&2
fi

if [[ -z "$copilot_bin" ]]; then
  printf 'no copilot fallback binary available for merge resolution\n' >&2
  exit 127
fi

exec "$copilot_bin" \
  -C "$workspace" \
  --silent \
  --allow-all-tools \
  --allow-all-paths \
  --no-ask-user \
  --autopilot \
  --prompt "$(cat "$prompt_file")"
