# NS-007 Semantic context, invalidation, and source-preserving repair qualification

Generated at 2026-09-12T01:56:24+00:00. This is a sealed-profile qualification record, not a live A–D experiment and not a CST/AST linker result.

## Profile

- Producer: `ipfs_datasets_py.logic.software_contracts.semantic_index + semantic_state`
- Context consumer: `ipfs_accelerate_py.agent_supervisor.semantic_state.context_pack + worktree`
- Source-linked edit path: `IsolatedPatchWorktree@1`
- Fixture: `SemanticStateControlledFixture@1`
- Selection policy: `ns-007-context-qualification-v1` with `allow_full_fallback=true`

## Environment and shims

- Interpreter: `/usr/bin/python3.12` (3.12.3)
- Sealed `PATH` at process start: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
- `PATH` after datasets import (package may prepend its own bin): `/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/neurosymbolic_supervision/worktrees/ns-007-cdce4e292a90-attempt-1-1789176842/external/ipfs_datasets/bin:/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/neurosymbolic_supervision/worktrees/ns-007-cdce4e292a90-attempt-1-1789176842/external/ipfs_datasets/bin/.deps/npm/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
- anyio: `False`
- multiformats: `False`
- provider tokenizer (tiktoken): `False`
- pytest: `8.1.1`
- git: `/usr/bin/git`
- Public `semantic_state` package import: ModuleNotFoundError: No module named 'anyio'
- CID identity: in-tree `ipfs_accelerate_py.utils.cid_utils` because multiformats is absent.

The public accelerate `semantic_state` package `__init__` imports the harness, which imports MCP++ `task_queue` and therefore `anyio`. The qualification loads the actual `context_pack.py`, `worktree.py`, and `capsules.py` files after installing a namespace package object so those consumer modules can be exercised without claiming that the full package import is available.

## Tokenizer

- Estimator: `calibrated_utf8`
- Provider-aware: `False`
- Version pin used by ContextPack: `context-compiler-calibrated_utf8@1`
- Fallback rate: `1.0` (no provider tokenizer in the sealed profile; both raw and semantic modes used this same estimator object).

## Coverage

- Result rows: 26
- Retained rows: 25
- Failed rows: 0 (none)
- Families retained: configuration, context_core, deleted, dependency, dynamic, fixture, localized, native, renamed, repair, stale_map, unchanged
- Cold/incremental mismatches: none
- Selected/full pytest mismatches: none

## Context reduction

- Paired raw/semantic token reductions (semantic vs raw): min=-0.7544, max=-0.2786, n=19.
- Required target/surrounding/test source CIDs were identical across modes; capsules never replaced those kinds.

## Selection fallback

- Observed fallback counts: {"authored_full": 3, "both": 8, "none": 11}
- Authored dynamic/native/monkey cases require full fallback or an explicit opaque/raw-source frontier.

## Repair parity

- `repair_valid_source_bound`: status=pass codes={'applied': True, 'reason_codes': [], 'pre_tree': '72204e13c53a3df5a76c690a8b04fa77a4c3c374', 'post_tree': '38841d5c12301203d554b9f4908d95f08936dccb', 'caller_root_unchanged': True, 'worktree_target_changed': True, 'preimage_exact': True}
- `repair_stale_preimage`: status=pass codes=['invisible_preimage']
- `repair_out_of_scope`: status=pass codes=['malformed_patch']
- `repair_invisible_preimage`: status=pass codes=['invisible_preimage']

## Limitations

- CST/AST relinking, tokenizer-alias editing, and generic semantic IR round-trip ablations are **not** part of the implemented claim. The qualified edit path is IsolatedPatchWorktree with exact preimages.
- Native cases use the fixture's declared native-library identity; no real native extension is loaded.
- Token accounting uses the calibrated UTF-8 estimator because no provider tokenizer is installed. Fallback rate is retained rather than reported as a model-tokenizer saving.
- Public import of `ipfs_accelerate_py.agent_supervisor.semantic_state` remains blocked without anyio. Submodule file load is an explicit sealed-profile bypass, not a deployment claim.
- CID identity is the in-tree sealed CIDv1 profile, not a live `multiformats` install.
- Pytest selected-vs-full execution ran on a declared subset of cases; remaining cases compare producer selection against the authored oracle.
- This receipt is qualification evidence for NS-007. It is not a matched A–D live repair result.

## Case outcomes

| case_id | family | retained | status | notes |
|---|---|---|---|---|
| `unchanged` | unchanged | true | pass | roots=agree fallback=none |
| `local_body` | localized | true | pass | roots=agree fallback=none |
| `signature` | localized | true | pass | roots=agree fallback=none |
| `cross_module` | localized | true | pass | roots=agree fallback=none |
| `schema` | localized | true | pass | roots=agree fallback=none |
| `exception` | localized | true | pass | roots=agree fallback=none |
| `fixture` | fixture | true | pass | roots=agree fallback=both |
| `config` | configuration | true | pass | roots=agree fallback=both |
| `plugin` | configuration | true | pass | roots=agree fallback=none |
| `lock` | dependency | true | pass | roots=agree fallback=both |
| `policy` | configuration | true | pass | roots=agree fallback=both |
| `interface` | configuration | true | pass | roots=agree fallback=both |
| `generated` | dependency | true | pass | roots=agree fallback=none |
| `dynamic` | dynamic | true | pass | roots=agree fallback=both |
| `monkey` | dynamic | true | pass | roots=agree fallback=both |
| `native` | native | true | pass | roots=agree fallback=none |
| `format` | localized | true | pass | roots=agree fallback=none |
| `delete` | deleted | true | pass | roots=agree fallback=none |
| `rename` | renamed | true | pass | roots=agree fallback=both |
| `repair_valid_source_bound` | repair | true | pass | Exact preimage source-bound patch applies inside a fenced worktree without mutat |
| `repair_stale_preimage` | stale_map | true | pass | Stale visibility-map preimage is rejected; worktree and caller root stay unchang |
| `repair_out_of_scope` | repair | true | pass | Out-of-scope policy.toml patch is rejected by IsolatedPatchWorktree admission. |
| `repair_invisible_preimage` | stale_map | true | pass | Empty visibility map rejects the patch as an invisible preimage. |
| `stale_capsule_map` | stale_map | true | pass | Baseline capsules assessed against a mutated semantic root must go stale or requ |
| `context_core_nontruncatable` | context_core | true | pass | ContextCompiler retains goal/authority/scope/acceptance and required target sour |
| `unsupported_cst_alias_ir` | context_core | false | pass | cst_alias_ir_linking_not_implemented_claim |
