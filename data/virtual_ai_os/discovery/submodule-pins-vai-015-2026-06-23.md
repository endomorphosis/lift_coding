# VAI-015 Submodule Pins and Automation Guardrails - 2026-06-23

## Scope

VAI-015 reconciles the root submodule pin policy with the current integration
evidence from VAI-002 source alignment and VAI-009 component repo contracts.
This pass did not fetch, initialize optional device submodules, run recursive
updates, or advance root gitlinks.

## Current Root Pins

Observed with `git ls-tree HEAD` for the root component paths:

```text
160000 commit 29343be704da4e193ff143bac7daae9b0f98435d Mcp-Plus-Plus
160000 commit 46b3e05ed10b3109c28820442359241bd26b7fbc external/ipfs_accelerate
160000 commit c8dbe9c99c2ed13f34e622253687d965537f8c05 external/ipfs_datasets
160000 commit d125a18374c5f9959c01d01d77fea51f3e67fe5e external/ipfs_kit
160000 commit 25f3a6d4479b7a4a72f877977b865a11af990d04 external/meta-wearables-dat-android
160000 commit a739e94181221e7f321304273bcda2272821b163 external/meta-wearables-dat-ios
160000 commit be3315553727a8ca491300adcb79a9bcaf1478bd hallucinate_app
160000 commit 0348884c24f86b92063b86b7fe9ad1410358b1bf swissknife
```

Observed with `git submodule status`:

```text
 29343be704da4e193ff143bac7daae9b0f98435d Mcp-Plus-Plus
 46b3e05ed10b3109c28820442359241bd26b7fbc external/ipfs_accelerate
 c8dbe9c99c2ed13f34e622253687d965537f8c05 external/ipfs_datasets
 d125a18374c5f9959c01d01d77fea51f3e67fe5e external/ipfs_kit
-25f3a6d4479b7a4a72f877977b865a11af990d04 external/meta-wearables-dat-android
-a739e94181221e7f321304273bcda2272821b163 external/meta-wearables-dat-ios
 be3315553727a8ca491300adcb79a9bcaf1478bd hallucinate_app
 0348884c24f86b92063b86b7fe9ad1410358b1bf swissknife
```

The leading `-` on the Meta DAT entries means those optional native validation
references are not initialized in this worktree. Their root gitlinks still
match the parent index.

## Upstream Main Check

Observed with `git ls-remote <url> refs/heads/main`:

| Path | Root gitlink | Upstream `main` | Result |
| --- | --- | --- | --- |
| `Mcp-Plus-Plus` | `29343be704da4e193ff143bac7daae9b0f98435d` | `29343be704da4e193ff143bac7daae9b0f98435d` | Matches. |
| `external/ipfs_accelerate` | `46b3e05ed10b3109c28820442359241bd26b7fbc` | `46b3e05ed10b3109c28820442359241bd26b7fbc` | Matches. |
| `external/ipfs_datasets` | `c8dbe9c99c2ed13f34e622253687d965537f8c05` | `c8dbe9c99c2ed13f34e622253687d965537f8c05` | Matches. |
| `external/ipfs_kit` | `d125a18374c5f9959c01d01d77fea51f3e67fe5e` | `135c36c210f516688dffa644851c5c321d232f38` | Upstream differs; do not move without nested-bootstrap review. |
| `external/meta-wearables-dat-android` | `25f3a6d4479b7a4a72f877977b865a11af990d04` | `25f3a6d4479b7a4a72f877977b865a11af990d04` | Matches. |
| `external/meta-wearables-dat-ios` | `a739e94181221e7f321304273bcda2272821b163` | `a739e94181221e7f321304273bcda2272821b163` | Matches. |
| `hallucinate_app` | `be3315553727a8ca491300adcb79a9bcaf1478bd` | `b95c09ae36d1c81030acfa18e15281b786a40a2b` | Upstream differs; defer to desktop-operator evidence review. |
| `swissknife` | `0348884c24f86b92063b86b7fe9ad1410358b1bf` | `a43e46139b78fdd9cafd83297db4ed543b86ddd3` | Upstream differs; keep current launch-readiness pin unless reviewed work requires movement. |

## Reviewed Pin Decision

No root gitlink movement is required for VAI-015.

The initialized submodule worktrees are clean and agree with the parent-index
gitlinks. The three upstream differences above are not automatic update
instructions:

- `external/ipfs_kit` remains coupled to nested bootstrap hygiene. Any movement
  to `135c36c210f516688dffa644851c5c321d232f38` requires a separate reviewed
  pin-refresh task with `external/ipfs_kit` nested submodule validation.
- `hallucinate_app` should only move after desktop-operator evidence validates
  the newer upstream pin.
- `swissknife` should not be normalized to upstream `main` by automation because
  the current root pin records local launch-readiness evidence.

## Automation Guardrails

- Use `git submodule status` as the VAI-015 validation guardrail.
- Keep recursive submodule update disabled for broad daemon bootstrap. Recursive
  status checks are acceptable for hygiene, but recursive updates through
  `external/ipfs_kit` require reviewed nested pins first.
- Daemon and supervisor worktrees may read root gitlinks and may use clean
  component checkouts for validation, but parent gitlink movement must be an
  explicit reviewed commit with old SHA, new SHA, validation command, and
  reason recorded.
- Optional Meta DAT Android and iOS checkouts remain status-only until a
  physical or native validation task needs them initialized.

## Validation

- `git submodule status`
- `rg -n "VAI-015|submodule pins|automation guardrails" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery`
