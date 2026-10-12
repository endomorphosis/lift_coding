# Reversible read-only repository views

The supervisor now has compact source candidates with complete KEEP/DELETE
byte maps backed by the [retained committed inventory](87-supervisor-retained-source-inventory-2026-10-12.md).
It can restore unchanged original bytes after the source checkout is gone,
without copying deleted text into every sidecar or creating another database
owner. The representation is historical/read-only; executable checkouts and
accepted edits remain separate responsibilities.

The [codec and inventory guide](https://github.com/endomorphosis/ipfs_accelerate_py/blob/a5c1ca93931445f1a91d3b187efd542efd774a53/docs/agent_supervisor/reversible_source_views.md)
and [qualification](https://github.com/endomorphosis/ipfs_accelerate_py/tree/a5c1ca93931445f1a91d3b187efd542efd774a53/docs/agent_supervisor/evidence/reversible-source-views-20261012)
are published at accelerator `a5c1ca93931445f1a91d3b187efd542efd774a53`.
This integrates the concurrent full instruction-dedup trial and preserves datasets
pin `c18390b350c7ab40f5bd342578204a03dc34fe05`, also used for qualification.

## Implemented profiles and replay

The default `python-whitespace@1` profile preserves all comments and removes safe
trailing trivia. Explicit `python-comments@1` also removes ordinary comments,
retaining conservative headers, licenses, directives/security/contracts and
caller-protected lines. Identity fallback preserves unsupported language,
encoding, syntax/newlines, excessive token/piece bounds and valid f-string
sources. Strings/docstrings, UTF-8 byte offsets, physical lines and CRLF/LF
remain checked. No AST unparse, renaming or target execution occurs.

Only regular `.py`/`.pyi` entries are nominated for Python views. Other files and
symlink targets remain exact; Gitlinks retain explicit child-reference gaps.
Unchanged views reference original source custody instead of copying large whole
blobs. Changed views and bounded structured sidecars/pages use the same supplied
CAS. Every row retains original path/mode/OID/source identities, view identity
and its sidecar binding; the closed root retains source inventory, independent
request/limits, profile, protected lines, codec binding and canonical pages.

Replay checks the complete source population, actual view bytes, closed maps,
codec/profile regeneration and exact inverse. Rehashed arbitrary deletion maps,
edited views, changed bindings, omissions and noncanonical pages refuse. Root
publication follows replay and is rechecked afterward. Source/store/input/policy
continuity remains guarded around callbacks. Checks are sequential, with no
atomic lease or rollback; failures can leave immutable artifacts without returning
a successful reference. Host metadata pages are not qualified Quack/model tools.

Transformation is bounded to 1 MiB, 131,072 token records and 4,096 pieces;
original inventory limits still govern complete materialization. Codec and
stdlib source hashes plus reported Python identities are strict replay bindings,
not complete toolchain attestation. Repeated local hashing/token/AST work remains
an explicit cost; no speed or provider-token improvement is claimed.

## Qualification and parallel evidence

**40 distinct tests passed**: 21 codec controls and 19 repository integration
cases, without skips and with normal AST sealing/isolated state. Fresh-process
replay restores original and view bytes after deleting the authored original
repository. Tests cover corruption, forged maps, protected comments, cold storage,
complete population, Gitlinks, input/policy/store/codec drift and conservative
fallbacks. The initial 39-pass/one-failure run is retained: its malformed fixture
expected an AST error although tokenization failed first. Correcting that fixture
required no product change. Repeated cases are not added to the distinct count.

Concurrent main now retains a separate live instruction-only pair: 311,776
baseline versus 309,813 treatment tokens, 1,963 fewer (0.63%), with both official
rewards 1. The difference was principally cached input; uncached input fell by
32, output grew by 245, setup/execution took longer and cost is unknown. One
independently planned pair does not establish repeatable savings. That frozen
trial did not run these new source views. Its Source384 coverage remained 0/4
aligned and IntentIR failed open without a checkpoint; separate numerical
projections retained 45 pending obligations. Preserve those limits and original
assets rather than attributing their results to this codec.

Qualified source/test hashes remained exact after merging parallel main. Four
exact local documentation workflow steps and five changed-guide link checks
passed. The exact-commit [GitHub documentation job](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38208910757)
executed no steps because the account is locked due to a billing issue; hosted
CI is not represented as passing.

Next qualify bounded current-owner source/capsule and residual-obligation lookup
through the actual coding interface, with source freshness after edits, response
bounds and full accounting. Keep original-source edits before any mapped-view
edit profile. Rebuild and qualify a current worker archive, then compare complete
rendered inputs and all native planning/coding/lookup/repair attempts against
official rewards. Semantic reconstruction, supported validators and IntentIR
checkpoint/grammar integration remain distinct improvements.

LegalIR, SecurityIR, CodebaseIR and IntentIR retain separate inventories and
schema/version/decoder-task/8D/384D/768D checkpoint identities. This phase reuses
existing source custody and performs no model inference, training, embedding
regeneration, Hugging Face upload or provider/prover call.
