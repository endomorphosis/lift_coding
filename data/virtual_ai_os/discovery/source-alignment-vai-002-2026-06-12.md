# VAI-002 Source Alignment - 2026-06-12

## Scope

Aligned the root `.gitmodules` wiring for the IPFS component gitlinks with the
canonical `_py` upstream repositories. No root gitlinks were advanced.

## Root URL Alignment

| Path | Canonical upstream |
| --- | --- |
| `external/ipfs_datasets` | `https://github.com/endomorphosis/ipfs_datasets_py` |
| `external/ipfs_accelerate` | `https://github.com/endomorphosis/ipfs_accelerate_py` |
| `external/ipfs_kit` | `https://github.com/endomorphosis/ipfs_kit_py` |

The existing non-IPFS root submodule URLs were left unchanged, including the
case-sensitive `Mcp-Plus-Plus` upstream and the tracked `hallucinate_app`
upstream.

## Pin Guardrail

Observed root gitlinks during this alignment:

| Path | Recorded gitlink |
| --- | --- |
| `Mcp-Plus-Plus` | `29343be704da4e193ff143bac7daae9b0f98435d` |
| `external/ipfs_accelerate` | `7913fc3a66b95cc1dc75143b84a2c4c77b838af1` |
| `external/ipfs_datasets` | `45ff065a4208e01ed7b1034a35e1ef2ffc6420b9` |
| `external/ipfs_kit` | `58873ab257104981aa9ba7bee0c2368369716be7` |
| `external/meta-wearables-dat-android` | `25f3a6d4479b7a4a72f877977b865a11af990d04` |
| `external/meta-wearables-dat-ios` | `a739e94181221e7f321304273bcda2272821b163` |
| `hallucinate_app` | `1fb7f0d205609c749c1133086fe73a2b6f7f7ce6` |
| `swissknife` | `8865ff3b872bda4bab492433bbfb858587b03df1` |

`external/ipfs_accelerate` and `external/ipfs_kit` match the `HEAD` and
`refs/heads/main` revisions advertised by their canonical `_py` upstreams on
2026-06-12. `external/ipfs_datasets` remains at the recorded root gitlink;
`git fetch --dry-run https://github.com/endomorphosis/ipfs_datasets_py
45ff065a4208e01ed7b1034a35e1ef2ffc6420b9` resolved that commit without
advancing the checkout, while reporting duplicate nested `.gitmodules` warnings
from upstream history.

## Commands Run

```text
git status --short
git ls-tree HEAD Mcp-Plus-Plus external/ipfs_accelerate external/ipfs_datasets external/ipfs_kit external/meta-wearables-dat-android external/meta-wearables-dat-ios hallucinate_app swissknife
git config --file .gitmodules --get-regexp '^submodule\..*\.url$'
git ls-remote https://github.com/endomorphosis/ipfs_datasets_py 45ff065a4208e01ed7b1034a35e1ef2ffc6420b9 HEAD refs/heads/main
git ls-remote https://github.com/endomorphosis/ipfs_accelerate_py 7913fc3a66b95cc1dc75143b84a2c4c77b838af1 HEAD refs/heads/main
git ls-remote https://github.com/endomorphosis/ipfs_kit_py 58873ab257104981aa9ba7bee0c2368369716be7 HEAD refs/heads/main
git fetch --dry-run https://github.com/endomorphosis/ipfs_datasets_py 45ff065a4208e01ed7b1034a35e1ef2ffc6420b9
git submodule status
rg -n "VAI-002|ipfs_datasets_py|ipfs_accelerate_py|ipfs_kit_py|source-alignment-vai-002" .gitmodules implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery/source-alignment-vai-002-2026-06-12.md
```
