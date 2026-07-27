# HAO-747 Resolution

Date: 2026-07-08
Task: HAO-747
Source task: HAO-731
Kind: merge retry-budget repair

## Finding

The retry-budget evidence in
`2026-07-08-hao-747-hao-731-merge-retry-budget.md` recorded 4 consecutive
merge failures for `implementation/hao-731-attempt-4-1783515248` with merge
reason `main_checkout_dirty_conflict` and dirty path `hallucinate_app`.

Reproducing the conflict in a fresh worktree showed the `hallucinate_app`
gitlink was dirty because of a 5-level-deep chain of nested submodules whose
checked-out commits were ahead of their parents' pinned gitlink SHAs:

```
hallucinate_app/ipfs_accelerate_py
  -> ipfs_datasets_py
    -> .tools/ipfs_kit_py
      -> ipfs_accelerate_py
        -> ipfs_datasets_py
          -> .tools/ipfs_kit_py   (clean; chain terminates here)
```

Every level reported `modified content` / `new commits`, so `git status`
never went clean anywhere along the `hallucinate_app` submodule tree and the
merge daemon's dirty-checkout guard rejected the merge before it could reach
a real 3-way merge step.

Separately, verifying that HAO-731's intended implementation changes were
committed in their owning submodule surfaced one gap: the `swissknife`
gitlink's checked-out commit (`1fb753e8`, `HAO-749: merge swissknife mobile
and android schema evidence`) was missing
`src/services/mcp/ipfs-accelerate-duckdb-interop-descriptor.ts`, which
`tests/integration/test_swissknife_external_ipfs_accelerate_interop.py`
requires on disk. The file was added by `VAI-662`/`HAO-731`
(`b4901e95595bb0848c39606fc51103640abae33a`, an ancestor of the current
`swissknife` HEAD) but was inadvertently dropped by the later
`chore: add pending swissknife staged changes` commit
(`04809e82dd270eca2cf32a1f90a769ab76f9ee6c`) in that submodule's history. A
sibling branch (`implementation/mgw-570-attempt-1-1783535732-submodule-swissknife`,
commit `10433e94`) had already independently restored an equivalent copy of
the same file under a different task ID, confirming the file legitimately
belongs on `swissknife` HEAD and was not deleted on purpose.

## Repair

1. Restored the deepest dirty level first and worked upward, committing
   each already-checked-out submodule commit as the new gitlink pointer (no
   content changes, no reverts — every commit purely records the commit the
   working tree already had checked out):
   - `.../ipfs_kit_py/ipfs_accelerate_py/ipfs_datasets_py` -> `.tools/ipfs_kit_py`
   - `.../ipfs_kit_py/ipfs_accelerate_py` -> `ipfs_datasets_py`
   - `.../ipfs_datasets_py/.tools/ipfs_kit_py` -> `ipfs_accelerate_py`
   - `hallucinate_app/ipfs_accelerate_py/ipfs_datasets_py` -> `.tools/ipfs_kit_py`
   - `hallucinate_app/ipfs_accelerate_py` -> `ipfs_datasets_py`
   - `hallucinate_app` -> `ipfs_accelerate_py`
   - top-level repo -> `hallucinate_app`

   After these 7 commits, `git submodule foreach --recursive 'git status
   --porcelain'` under `hallucinate_app` reports no dirty entries at any
   level, and the top-level worktree is clean.

2. Restored `swissknife/src/services/mcp/ipfs-accelerate-duckdb-interop-descriptor.ts`
   by taking the original `VAI-662`/`HAO-731` content
   (`git show b4901e95:src/services/mcp/ipfs-accelerate-duckdb-interop-descriptor.ts`)
   and committing it directly onto the `swissknife` HEAD used by this
   worktree, then recorded the resulting `swissknife` gitlink pointer
   (`e0121c13`) — matching the pattern already used by the prior HAO-731
   attempt-2/attempt-3 confirmations to advance the `swissknife` gitlink to
   fast-forward commits that restore missing interop descriptors.

3. Initialized the `Mcp-Plus-Plus`, `external/ipfs_kit`,
   `external/meta-wearables-dat-android`, and `external/meta-wearables-dat-ios`
   gitlink submodules with `git submodule update --init` (no gitlink pointer
   changes; all four checked out cleanly at their already-pinned commits),
   the same one-time fresh-worktree checkout step recorded in every prior
   HAO-731 attempt confirmation.

Because the blocker was a nested submodule checkout/pointer-bookkeeping gap
and a single accidentally-dropped file (not a textual/semantic merge
conflict between two candidate branches),
`ipfs-accelerate-agent-merge-resolver --events-path ... --apply` was not
required, consistent with the HAO-424 precedent for this same guardrail
finding class.

## Scope note

While validating the full `tests/integration` suite, the fresh worktree also
surfaced additional missing files on the current `swissknife` HEAD (for
example `src/services/mcp/mcp-plus-plus.ts` and
`src/services/mcp/ipfs-kit-mcp-schema-interop-descriptor.ts`) that were
dropped by the same `chore: add pending swissknife staged changes` commit.
Those files back other goals in
`goal_packet/interoperability/swissknife/06921590135c`
(`VAIOS-G702`/`VAIOS-G703`, owned by other in-flight tasks such as `MGW-570`
and `MGW-572`) rather than HAO-731's `VAIOS-G701` scope, and a concurrent
`MGW-570` implementation-daemon attempt was already restoring them at the
time of this repair (`swissknife` commit `911d34b8`, not in this worktree's
lineage). Repairing every dropped file across the whole packet is outside
this merge-retry-budget repair's scope for HAO-731 and is left to those
owning tasks so as not to duplicate or conflict with their concurrent work.

## Validation

Focused validation target (HAO-731's specific proof stack):

`python -m pytest tests/integration/test_swissknife_external_ipfs_accelerate_interop.py -q` — 7 passed.

Merge-blocker validation:

`test -f data/hallucinate_multimodal_control/discovery/2026-07-08-hao-747-hao-731-merge-retry-budget.md` — passes (evidence file present).

`git status --short` at the top-level worktree and `git submodule foreach
--recursive 'git status --porcelain'` under `hallucinate_app` — clean (no
dirty entries), confirming the `main_checkout_dirty_conflict` blocker is
resolved.

Confirmed outputs (present and passing for HAO-731's VAIOS-G701 scope):

- `tests/integration/test_swissknife_external_ipfs_accelerate_interop.py`
- `docs/integration/swissknife-external_ipfs_accelerate.md`
- `swissknife/src/services/mcp/ipfs-accelerate-duckdb-interop-descriptor.ts` (restored)
- `external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql`
- `external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py`
- `external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py`
- `external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py`
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`

This merge retry-budget repair resolves the `main_checkout_dirty_conflict`
blocker recorded for HAO-731 so the supervisor can release HAO-731 from the
strategy `blocked_tasks` list.
