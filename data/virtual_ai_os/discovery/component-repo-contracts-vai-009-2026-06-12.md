# VAI-009 Component Repo Contracts - 2026-06-12

## Scope

Added a code-level environment, pin, and bootstrap contract for the root
component repositories that make up the virtual AI OS. This task did not
advance submodule gitlinks, fetch remotes, or initialize optional device
submodules.

## Contract Surface

- Source contract:
  `src/handsfree/virtual_ai_os_components.py` enumerates every root submodule
  path and URL from `.gitmodules`.
- Environment contract:
  each component has one `HANDSFREE_VAI_*_ROOT` override used by integration
  harnesses and isolated worktrees.
- Pin contract:
  the root superproject gitlink is the reviewed pin; bootstrap may initialize
  or sync a worktree but must not fetch, checkout, or advance it without an
  explicit pin-refresh task.
- Bootstrap contract:
  recursive bootstrap is disabled for the component set. `external/ipfs_kit`
  is status-only for nested traversal until nested pins are reviewed.
- Device references:
  `external/meta-wearables-dat-android` and
  `external/meta-wearables-dat-ios` remain optional validation references.

## Current `.gitmodules` Evidence

Observed with
`git config --file .gitmodules --get-regexp '^submodule\..*\.(path|url)$'`:

```text
submodule.external/ipfs_datasets.path external/ipfs_datasets
submodule.external/ipfs_datasets.url https://github.com/endomorphosis/ipfs_datasets_py
submodule.external/ipfs_kit.path external/ipfs_kit
submodule.external/ipfs_kit.url https://github.com/endomorphosis/ipfs_kit_py
submodule.external/ipfs_accelerate.path external/ipfs_accelerate
submodule.external/ipfs_accelerate.url https://github.com/endomorphosis/ipfs_accelerate_py
submodule.external/meta-wearables-dat-android.path external/meta-wearables-dat-android
submodule.external/meta-wearables-dat-android.url https://github.com/facebook/meta-wearables-dat-android
submodule.external/meta-wearables-dat-ios.path external/meta-wearables-dat-ios
submodule.external/meta-wearables-dat-ios.url https://github.com/facebook/meta-wearables-dat-ios
submodule.swissknife.path swissknife
submodule.swissknife.url https://github.com/endomorphosis/swissknife
submodule.Mcp-Plus-Plus.path Mcp-Plus-Plus
submodule.Mcp-Plus-Plus.url https://github.com/endomorphosis/Mcp-Plus-Plus.git
submodule.hallucinate_app.path hallucinate_app
submodule.hallucinate_app.url https://github.com/endomorphosis/hallucinate_app.git
```

## Current Submodule Status

Observed with `git submodule status`:

```text
29343be704da4e193ff143bac7daae9b0f98435d Mcp-Plus-Plus
7913fc3a66b95cc1dc75143b84a2c4c77b838af1 external/ipfs_accelerate
45ff065a4208e01ed7b1034a35e1ef2ffc6420b9 external/ipfs_datasets
58873ab257104981aa9ba7bee0c2368369716be7 external/ipfs_kit
-25f3a6d4479b7a4a72f877977b865a11af990d04 external/meta-wearables-dat-android
-a739e94181221e7f321304273bcda2272821b163 external/meta-wearables-dat-ios
d1c940ed63107b00cc9077c5aa635c2d2e7bd67c hallucinate_app
8865ff3b872bda4bab492433bbfb858587b03df1 swissknife
```

The leading `-` on the Meta DAT entries means those optional native validation
references were not initialized in this worktree.

## Validation Added

`tests/test_virtual_ai_os_component_contracts.py` validates:

- every root `.gitmodules` path and URL is represented by the component
  contract,
- environment overrides resolve the component root path without changing the
  default submodule path for other components,
- `ipfs_kit` keeps the status-only nested bootstrap guard,
- optional Meta DAT repositories use the optional validation bootstrap mode,
- the existing virtual AI OS observability contract exposes the component repo
  environment, pin, and bootstrap contracts.
