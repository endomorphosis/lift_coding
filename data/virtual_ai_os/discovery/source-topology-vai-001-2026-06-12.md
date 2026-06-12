# VAI-001 Source Topology Checkpoint - 2026-06-12

## Scope

Recorded the reviewed source topology and pin guardrails for the virtual AI OS
submodule integration backlog without advancing gitlinks or rewriting
`.gitmodules`.

## Root Gitlinks

Observed with `git ls-tree HEAD`:

| Path | Recorded gitlink |
| --- | --- |
| `Mcp-Plus-Plus` | `29343be704da4e193ff143bac7daae9b0f98435d` |
| `external/ipfs_accelerate` | `7913fc3a66b95cc1dc75143b84a2c4c77b838af1` |
| `external/ipfs_datasets` | `45ff065a4208e01ed7b1034a35e1ef2ffc6420b9` |
| `external/ipfs_kit` | `58873ab257104981aa9ba7bee0c2368369716be7` |
| `external/meta-wearables-dat-android` | `25f3a6d4479b7a4a72f877977b865a11af990d04` |
| `external/meta-wearables-dat-ios` | `a739e94181221e7f321304273bcda2272821b163` |
| `hallucinate_app` | `f2a935154a4124b95c897fc0e5964eb43bc51a09` |
| `swissknife` | `8865ff3b872bda4bab492433bbfb858587b03df1` |

## Root Submodule Status

Observed with `git submodule status`:

```text
 29343be704da4e193ff143bac7daae9b0f98435d Mcp-Plus-Plus (heads/implementation/vai-001-attempt-1-1781237885-submodule-Mcp-Plus-Plus)
 7913fc3a66b95cc1dc75143b84a2c4c77b838af1 external/ipfs_accelerate (heads/implementation/vai-001-attempt-1-1781237885-submodule-external-ipfs_accelerate)
 45ff065a4208e01ed7b1034a35e1ef2ffc6420b9 external/ipfs_datasets (heads/implementation/vai-001-attempt-1-1781237885-submodule-external-ipfs_datasets)
 58873ab257104981aa9ba7bee0c2368369716be7 external/ipfs_kit (v0.2.0-1424-g58873ab2)
-25f3a6d4479b7a4a72f877977b865a11af990d04 external/meta-wearables-dat-android
-a739e94181221e7f321304273bcda2272821b163 external/meta-wearables-dat-ios
 f2a935154a4124b95c897fc0e5964eb43bc51a09 hallucinate_app (heads/implementation/vai-001-attempt-1-1781238154-submodule-hallucinate_app)
 8865ff3b872bda4bab492433bbfb858587b03df1 swissknife (heads/implementation/hao-140-attempt-1-1780998898-submodule-swissknife)
```

The initialized reviewed worktrees were clean when checked with
`git -C <path> status --short --branch`.

## Current `.gitmodules` Guardrail

Root `.gitmodules` currently maps:

- `external/ipfs_datasets` to `https://github.com/endomorphosis/ipfs_datasets`
- `external/ipfs_kit` to `https://github.com/endomorphosis/ipfs_kit`
- `external/ipfs_accelerate` to `https://github.com/endomorphosis/ipfs_accelerate`
- `external/meta-wearables-dat-android` to `https://github.com/facebook/meta-wearables-dat-android`
- `external/meta-wearables-dat-ios` to `https://github.com/facebook/meta-wearables-dat-ios`
- `swissknife` to `https://github.com/endomorphosis/swissknife`
- `Mcp-Plus-Plus` to `https://github.com/endomorphosis/Mcp-Plus-Plus.git`
- `hallucinate_app` to `https://github.com/endomorphosis/hallucinate_app.git`

Do not treat this VAI-001 checkpoint as approval to rewrite the three IPFS root
URLs to `_py` upstreams or to advance any recorded gitlink. That wiring belongs
to the explicit source-alignment and pin-refresh tasks.

## Bootstrap Guardrails

- Root-level `git submodule status` is the safe topology check for this
  checkpoint.
- `git submodule status --recursive` is not a safe validation command in this
  checkout. It recurses into nested IPFS submodules and fails on a nested
  `ipfs_accelerate_py` gitlink without a matching `.gitmodules` mapping.
- Do not run recursive submodule update/bootstrap across the full tree from this
  evidence alone. Initialize or refresh specific submodules only after their
  upstream URL and recorded pin are reviewed for the owning task.
- Keep `Mcp-Plus-Plus` as the case-sensitive standalone MCP++ spec/docs source;
  do not add a second lowercase `mcp_plus_plus` submodule unless a future source
  resolution task proves a canonical upstream exists.
- `external/meta-wearables-dat-android` and
  `external/meta-wearables-dat-ios` are recorded gitlinks but were uninitialized
  in this checkpoint, as indicated by the leading `-` in root submodule status.

## Commands Run

```text
git status --short
git ls-tree HEAD Mcp-Plus-Plus external/ipfs_accelerate external/ipfs_datasets external/ipfs_kit external/meta-wearables-dat-android external/meta-wearables-dat-ios hallucinate_app swissknife
git submodule status
git -C external/ipfs_datasets status --short --branch
git -C external/ipfs_accelerate status --short --branch
git -C external/ipfs_kit status --short --branch
git -C swissknife status --short --branch
git -C hallucinate_app status --short --branch
git -C Mcp-Plus-Plus status --short --branch
git submodule status --recursive
```

`git submodule status --recursive` exited with status `128` after reporting:

```text
fatal: no submodule mapping found in .gitmodules for path 'ipfs_accelerate_py'
fatal: failed to recurse into submodule '.tools/ipfs_kit_py'
fatal: failed to recurse into submodule 'ipfs_datasets_py'
fatal: failed to recurse into submodule 'external/ipfs_accelerate'
```
