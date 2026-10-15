#!/usr/bin/env bash
# Implementation provider: Grok 4.6 first, Codex gpt-5.6-terra on
# missing-binary / auth / startup failure. Task-level Grok failures are not
# re-run on Codex.
set -u
export HOME="${HOME:-/home/barberb}"
export GROK_HOME="${GROK_HOME:-/home/barberb/.grok}"
PGIR_REPO="${PGIR_REPO:-/home/barberb/lift_coding/.pgir_campaign/worktrees/accelerate-authority}"
PGIR_PY="${PGIR_PY:-/home/barberb/.local/bin/python}"
GROK_BIN="${IPFS_ACCELERATE_AGENT_GROK_BIN:-$(command -v grok || true)}"
GROK_MODEL="${IPFS_ACCELERATE_AGENT_GROK_MODEL:-grok-4.6}"
CODEX_BIN="${CODEX_BIN:-/usr/local/bin/codex}"
CODEX_MODEL="${IPFS_ACCELERATE_AGENT_CODEX_MODEL:-gpt-5.6-terra}"
RUNNER="$PGIR_REPO/ipfs_accelerate_py/agent_supervisor/grok_cli_runner.py"
WORKDIR="${PWD}"

prompt=$(mktemp)
err=$(mktemp)
trap 'rm -f "$prompt" "$err"' EXIT
cat >"$prompt"

use_codex() {
  exec "$CODEX_BIN" exec --approve-for-me --ephemeral --skip-git-repo-check \
    -m "$CODEX_MODEL" -C "$WORKDIR" - <"$prompt"
}

if [ -n "$GROK_BIN" ] && [ -x "$GROK_BIN" ] && [ -f "$RUNNER" ]; then
  set +e
  "$PGIR_PY" "$RUNNER" \
    --workspace "$WORKDIR" \
    --grok-bin "$GROK_BIN" \
    --model "$GROK_MODEL" \
    --mode agent \
    <"$prompt" 2>"$err"
  rc=$?
  set -e
  cat "$err" >&2
  if [ "$rc" -eq 0 ]; then
    exit 0
  fi
  if grep -Eiq 'not signed in|not authenticated|not found|Grok CLI is not|login|empty implementation prompt' "$err"; then
    use_codex
  fi
  if [ "$rc" -eq 127 ] || [ "$rc" -eq 2 ]; then
    use_codex
  fi
  exit "$rc"
fi

use_codex
