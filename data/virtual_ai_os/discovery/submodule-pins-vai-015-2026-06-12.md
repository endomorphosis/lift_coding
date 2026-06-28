# VAI-015 Submodule Pin Refresh and Automation Guardrails - 2026-06-12

## Scope

Refresh the reviewed submodule pin table and restate automation guardrails
after the initial backlog (VAI-001 through VAI-014) merged into `main`.

## Refreshed Root Gitlinks

Observed with `git ls-tree HEAD`:

| Path | Recorded gitlink | Change vs VAI-001 |
| --- | --- | --- |
| `Mcp-Plus-Plus` | `29343be704da4e193ff143bac7daae9b0f98435d` | unchanged |
| `external/ipfs_accelerate` | `7913fc3a66b95cc1dc75143b84a2c4c77b838af1` | advanced |
| `external/ipfs_datasets` | `45ff065a4208e01ed7b1034a35e1ef2ffc6420b9` | unchanged |
| `external/ipfs_kit` | `58873ab257104981aa9ba7bee0c2368369716be7` | advanced |
| `external/meta-wearables-dat-android` | `25f3a6d4479b7a4a72f877977b865a11af990d04` | unchanged |
| `external/meta-wearables-dat-ios` | `a739e94181221e7f321304273bcda2272821b163` | unchanged |
| `hallucinate_app` | `5e2173fd2f825fa06572d3de8c7f281f570c43bc` | advanced |
| `swissknife` | `8865ff3b872bda4bab492433bbfb858587b03df1` | unchanged |

## Root Submodule Status

Observed with `git submodule status`:

```text
 29343be704da4e193ff143bac7daae9b0f98435d Mcp-Plus-Plus (heads/implementation/vai-001-attempt-1-1781237885-submodule-Mcp-Plus-Plus)
 7913fc3a66b95cc1dc75143b84a2c4c77b838af1 external/ipfs_accelerate (heads/implementation/vai-001-attempt-1-1781237885-submodule-external-ipfs_accelerate)
 45ff065a4208e01ed7b1034a35e1ef2ffc6420b9 external/ipfs_datasets (heads/implementation/vai-001-attempt-1-1781237885-submodule-external-ipfs_datasets)
 58873ab257104981aa9ba7bee0c2368369716be7 external/ipfs_kit (v0.2.0-1424-g58873ab2)
-25f3a6d4479b7a4a72f877977b865a11af990d04 external/meta-wearables-dat-android
-a739e94181221e7f321304273bcda2272821b163 external/meta-wearables-dat-ios
 5e2173fd2f825fa06572d3de8c7f281f570c43bc hallucinate_app (heads/implementation/hao-315-attempt-1-1781242002-submodule-hallucinate_app)
 8865ff3b872bda4bab492433bbfb858587b03df1 swissknife (heads/implementation/hao-140-attempt-1-1780998898-submodule-swissknife)
```

All initialized worktrees were clean (no uncommitted changes in working tree).

## What Changed Since VAI-001

- `external/ipfs_accelerate` advanced from `765583468e28fc1229db849739a584816129251e`
  to `7913fc3a66b95cc1dc75143b84a2c4c77b838af1` during the initial backlog
  implementation branches.
- `external/ipfs_kit` advanced from `17acebc422bb09f803be504b3212258db7b5b600`
  to `58873ab257104981aa9ba7bee0c2368369716be7`; the updated pin is on the
  `v0.2.0` tag lineage (`v0.2.0-1424-g58873ab2`) and includes the nested
  `ipfs_accelerate_py` `.gitmodules` mapping added by VAI-021.
- `hallucinate_app` advanced from `8ccbb84362fb95e1636b5515c32f5af0bbfeab3b`
  to `5e2173fd2f825fa06572d3de8c7f281f570c43bc` during Hallucinate App backlog
  work merged into `main`.

## Automation Guardrails (refreshed)

### Safe validation command

```sh
git submodule status
```

Root-level `git submodule status` is the safe pin-check command for this
topology. It reports clean or modified state for every initialized submodule
without recursing into nested gitlinks.

### Not safe without additional caution

```sh
git submodule status --recursive
```

Recursive status still fails in this checkout. The nested `external/ipfs_kit`
submodule now has a `.gitmodules` entry for `ipfs_accelerate_py` (added by
VAI-021), but the recursive traversal still encounters a missing
`.gitmodules` mapping further up the IPFS nesting chain and exits with status
`128`. Do not rely on a zero exit from recursive status as a readiness signal.

### Submodule bootstrap rule

- Initialize specific submodules by name only:
  `git submodule update --init <path>`
- Never run `git submodule update --init --recursive` from the repository root
  without first verifying that all nested gitlinks resolve cleanly.
- Use `git -C <path> submodule status` to inspect nested gitlinks in isolation
  before recursing.

### Pin-advance guardrails

- Do not advance `swissknife` automatically. Its worktree carries in-progress
  work; any pin advance must be an explicit superproject commit with a matching
  reviewed upstream branch.
- Do not add a new lowercase `mcp_plus_plus` root submodule. The
  `https://github.com/endomorphosis/mcp_plus_plus` URL still returns
  `Repository not found`. The case-sensitive `Mcp-Plus-Plus` pin remains the
  canonical standalone MCP++ spec/docs source.
- `external/meta-wearables-dat-android` and `external/meta-wearables-dat-ios`
  remain uninitialized (leading `-` in `git submodule status`). Do not
  initialize them during routine submodule refresh work; they require a
  Meta-device-specific integration task.
- `external/ipfs_datasets` is currently aligned with its recorded superproject
  gitlink. Any local-checkout drift discovered in future runs must be treated
  as a deliberate superproject change, not an incidental refresh side-effect.

### `.gitmodules` URL guardrail

Root `.gitmodules` maps the three IPFS paths to non-`_py` URL suffixes
(`ipfs_datasets`, `ipfs_kit`, `ipfs_accelerate`). The target canonical upstreams
use `_py` suffixes. Do not rewrite these URLs without a dedicated
source-alignment task; the current URLs resolve to the same repositories via
redirect but should be updated in an explicit, reviewed commit.

## Commands Run

```text
git status --short
git ls-tree HEAD Mcp-Plus-Plus external/ipfs_accelerate external/ipfs_datasets external/ipfs_kit external/meta-wearables-dat-android external/meta-wearables-dat-ios hallucinate_app swissknife
git submodule status
git -C Mcp-Plus-Plus status --short --branch
git -C external/ipfs_accelerate status --short --branch
git -C external/ipfs_datasets status --short --branch
git -C external/ipfs_kit status --short --branch
git -C swissknife status --short --branch
git -C hallucinate_app status --short --branch
git submodule status --recursive
```

`git submodule status --recursive` exited non-zero; partial output before the
first fatal:

```text
fatal: no submodule mapping found in .gitmodules for path 'ipfs_accelerate_py'
fatal: failed to recurse into submodule '.tools/ipfs_kit_py'
fatal: failed to recurse into submodule 'ipfs_datasets_py'
fatal: failed to recurse into submodule 'external/ipfs_accelerate'
```

This matches the VAI-001 checkpoint behavior; recursive status is not yet a
safe guardrail.
