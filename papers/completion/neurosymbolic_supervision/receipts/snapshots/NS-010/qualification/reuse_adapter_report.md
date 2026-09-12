# NS-010 Fixture-instance and phase-aware reuse seam

Generated at 2026-09-12T02:51:03+00:00. This is a sealed-profile qualification record, not a live A–D experiment and not the NS-011 cold-oracle mutation campaign.

## Profile

- Collection seed: `ProofReuseCollectionSeed@1` (lookup only; action `RUN`)
- Fixture/hook identity: `collect_fixture_hook_identity`
- Execution key: `TestExecutionKey@1`
- Pass receipt: `TestPassReceipt@1` (setup/call/teardown must all pass to admit)
- Cache admission: `TestProofCache@1`
- Supervisor completion: `ProofCachedTestValidation@1`
- Lifecycle capture: `PostPassRuntimeTraceCapture`
- Policy: `ns-010-reuse-qualification-v1`

## Environment

- Interpreter: `/usr/bin/python3.12` (3.12.3)
- Sealed `PATH` at process start: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
- pytest: `8.1.1`
- datasets test-selection import: `imported`

## Coverage

- Result rows: 27
- Failed rows: 0
- Collection seed authorizes skip: `False` (must be false)
- Unchanged eligible reuse: `SKIP` / `proof_cache_hit`
- Teardown-failure skip: `RUN` / `receipt_mismatch`

## Reuse lookup cannot become a passing outcome

Collection seeds attach a locator and never an execution key. Eligibility classification never emits `SKIP`. A pytest skip string presented to `ProofCachedTestValidation.validate` is `plain_skip_not_evidence` and is not completion evidence. Cache absence is `RUN` with `candidate_missing`. Simulated certificates are `certificate_non_attested`.

## Fixture, plugin, policy, runtime, and snapshot mutations invalidate reuse

The test-function CID is held constant (`cid:function:unchanged-body`). Changing fixture CIDs, plugin CIDs, conftest closure, runtime-trace root, external snapshots, or policy forces `TestProofCache.lookup` to `RUN` (`execution_key_mismatch` or `policy_mismatch`). Autouse and transitive fixture definitions are included in `FixtureHookIdentity`; a definition-body change changes the fixture CID set.

## Call reuse after setup still runs teardown

`PostPassRuntimeTraceCapture.execute_lifecycle_once` records setup, a non-reinvoked call placeholder, and teardown exactly once. Capture itself `may_authorize_skip=false`. A setup failure still runs teardown and does not invoke the call body. `TestPassReceipt` rejects `admitted=True` when teardown is not `pass`. A teardown-failure receipt cannot skip (`receipt_mismatch`). Unhealthy xdist workers cannot skip or publish.

## Unchanged eligible reuse and explicit fallbacks

The unchanged eligible case reused receipt `baguqeerazrfpi6jrmof7phetw2w3pxpkjhnuxa4jwibxyfiwnhenllha3ljq` under `proof_cache_hit`. Uncontrolled fixture values record `uncontrolled_fixture_value`. Callables cannot be canonicalized (no pickle/repr fallback). Incomplete runtime traces fall back to `incomplete_trace`/`RUN`.

## Staged identity (Table 8)

| stage | name | decision allowed |
|---|---|---|
| 0 | `collection_seed` | candidate lookup only; not a passing outcome |
| 1 | `fixture_definition_closure` | whole-item pre-setup reuse only under a closed policy |
| 2 | `fixture_instance_commitment` | post-setup eligibility; opaque/uncontrolled values force execution |
| 3 | `execution_key` | re-admit a prior receipt or execute; no optimistic pass |
| 4 | `phase_receipt` | fresh observation; teardown failure prevents whole-item pass |

## Limitations

- Qualification uses constructed locators/keys/receipts plus live contract, cache, identity, lifecycle, and validation APIs. It is not a historical repair task.
- Native Groth16 verification of pytest execution is not claimed; the cache verifier in this profile is a local authoritative callback over retained canonical bytes.
- Independent cold full-run scoring and adversarial mutation rates are NS-011, not this task.
- This receipt is Table 18 fixture/call/teardown reuse qualification, not a matched A–D outcome.

## Case outcomes

| case_id | family | polarity | stage | status | reason |
|---|---|---|---|---|---|
| `collection_seed_not_passing_outcome` | lookup_not_pass | invalid | `0-collection-seed` | pass | `collection_seed_not_passing_outcome` |
| `locator_not_skip_authority` | lookup_not_pass | invalid | `0-collection-seed` | pass | `locator_not_skip_authority` |
| `eligibility_never_emits_skip` | lookup_not_pass | diagnostic | `1-fixture-definition` | pass | `eligibility_never_emits_skip` |
| `plain_skip_not_completion_evidence` | lookup_not_pass | invalid | `3-execution-key` | pass | `plain_skip_not_evidence` |
| `lookup_miss_is_run` | lookup_not_pass | diagnostic | `3-execution-key` | pass | `candidate_missing` |
| `simulated_certificate_cannot_skip` | lookup_not_pass | invalid | `4-phase-receipt` | pass | `certificate_non_attested` |
| `unchanged_eligible_reuses_admitted_result` | reuse_progress | valid | `3-execution-key` | pass | `proof_cache_hit` |
| `fixture_definition_change_invalidates` | identity_invalidation | invalid | `1-fixture-definition` | pass | `execution_key_mismatch` |
| `fixture_value_change_invalidates` | identity_invalidation | invalid | `2-fixture-instance` | pass | `execution_key_mismatch` |
| `plugin_change_invalidates` | identity_invalidation | invalid | `1-fixture-definition` | pass | `execution_key_mismatch` |
| `runtime_trace_change_invalidates` | identity_invalidation | invalid | `3-execution-key` | pass | `execution_key_mismatch` |
| `external_snapshot_change_invalidates` | identity_invalidation | invalid | `2-fixture-instance` | pass | `execution_key_mismatch` |
| `conftest_change_invalidates` | identity_invalidation | invalid | `1-fixture-definition` | pass | `execution_key_mismatch` |
| `unchanged_body_fixture_still_invalidates` | identity_invalidation | invalid | `1-fixture-definition` | pass | `execution_key_mismatch` |
| `policy_change_invalidates` | identity_invalidation | invalid | `3-execution-key` | pass | `policy_mismatch` |
| `autouse_transitive_fixture_bound` | identity_invalidation | valid | `1-fixture-definition` | pass | `autouse_transitive_fixture_bound` |
| `call_reuse_after_setup_runs_teardown` | lifecycle | valid | `4-phase-receipt` | pass | `teardown_ran_after_call_reuse` |
| `teardown_failure_blocks_admitted_receipt` | lifecycle | invalid | `4-phase-receipt` | pass | `teardown_failure_blocks_admitted_receipt` |
| `teardown_fail_receipt_cannot_skip` | lifecycle | invalid | `4-phase-receipt` | pass | `receipt_mismatch` |
| `setup_failure_still_runs_teardown` | lifecycle | valid | `4-phase-receipt` | pass | `setup_failure_still_runs_teardown` |
| `xdist_unhealthy_worker_cannot_skip` | lifecycle | invalid | `3-execution-key` | pass | `xdist_coordination_unavailable` |
| `unknown_uncontrolled_fixture_fallback` | fallback | diagnostic | `2-fixture-instance` | pass | `uncontrolled_fixture_value` |
| `opaque_object_serialization_rejected` | fallback | invalid | `2-fixture-instance` | pass | `opaque_object_serialization_rejected` |
| `incomplete_trace_falls_back_to_run` | fallback | diagnostic | `3-execution-key` | pass | `incomplete_trace` |
| `full_item_vs_call_only_phase_distinction` | lifecycle | valid | `1-fixture-definition` | pass | `full_item_vs_call_only_phase_distinction` |
| `parametrization_bound_on_locator` | identity_invalidation | valid | `0-collection-seed` | pass | `parametrization_bound_on_locator` |
| `interpreter_policy_external_bound` | identity_invalidation | valid | `3-execution-key` | pass | `interpreter_policy_external_bound` |
