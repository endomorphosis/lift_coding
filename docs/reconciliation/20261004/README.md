# Repository reconciliation — 2026-10-04

All captured unmerged tips in the seven primary repositories are reachable from their published main histories. Conflicting historical alternatives remain in ancestry; current source contracts and compatible captured additions determine the final trees. Sanitized commit mappings preserve provenance for large assets and credential removal. Original working checkouts were protected throughout reconciliation.

Production IntentIR, SecurityIR, UI/UX IR and LegalIR autoencoder/decoder releases were downloaded from their latest public Hugging Face main revisions and checked against exact release manifests, SHA-256 digests and sizes. Experimental and historical checkpoints are preserved privately at https://huggingface.co/Publicus/autoencoder-decoder-checkpoints under the local-history and local-refresh releases. They are archived states, not newly qualified production models.

Large historical Git assets and compressed conflict-resolution ledgers are archived in the same private repository. The datasets repository includes tools/restore_historical_asset.py and immutable revision references for restoring original bytes. GitHub main histories were pushed normally; no main force push or paid LFS quota expansion was used.

Cleanup removed 27,718 local branches, 3,748 remote branches and 17 inactive clean original worktrees after ancestry checks. Branch deletion used captured object identities, and remote deletion used leases. Active, dirty, locked and artifact-bearing worktrees, independent nested Git stores, occupied branches and new work created after inventory were retained. The default Docker context contained no containers. A new running rootless deployment container created during final checks was retained; no stale containers remained at that audit. Images and volumes were retained.

Validation includes broad changed-source suites and focused current interface checks. Historical lineage reuse profiles can refuse newer producer hashes, and legacy paper migration scripts can be rejected by the current closed Quack mutation protocol. Those historical validation results are retained in the audit; they do not authorize producer compatibility or broaden writer permissions. Detailed final outcomes and publication heads are recorded in summary.json.

The complete local audit is retained in artifacts/reconciliation-20261004, including branch inventories, snapshot receipts, per-path conflict decisions, test logs, Hugging Face verification, publication receipts and cleanup plans/results.
