# UI/UX IR accelerator pin — 2026-08-04T06:08Z

## Pin

`external/ipfs_accelerate` = `9646826c6b9d20966f254f0109986727bf96873d`

Branch tip: `merge/origin-main-into-grok-first` (also `rescue/local-main-worktree-20260801`)

PR: https://github.com/endomorphosis/ipfs_accelerate_py/pull/101

## Provider

- primary implement: `grok-4.5`
- implement fallback: `gpt-5.6-terra` medium **only** on verified Grok Build quota exhaustion
- ambient Codex discovery as implementer: **disabled**

## Evidence

Merge commit integrates `origin/main` while preserving Prefer-Grok implement routing.
