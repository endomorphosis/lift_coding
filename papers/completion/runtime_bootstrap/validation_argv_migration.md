`scripts/migrate_paper_validation_argv.py` corrects exactly the reviewed paper
verifier from the former `bash -lc` argv wrapper to direct argv. It requires an
explicit authenticated loopback Quack endpoint, selects that paper's current
owner generation while retaining historical owner rows, and verifies all 25
task identities/contracts before the first update. The native owner persists
live rows with status `starting` before publishing readiness; successful
authenticated queries, endpoint/generation binding, and database-UUID matching
establish the active owner here.

Every update calls `IntentRepository.upsert_task(expected_revision=...)`,
preserves task CID, goal, plan, identity, dependencies, outputs, acceptance,
validation policy, body/history, and task status, and appends a native task
revision and domain event. Already-correct rows are observed without rewriting
them. An in-progress task, unexpected argv, mismatched source command, other
paper store, or unrecognized blocked state refuses admission. Each native
update is transactional; the receipt records partial progress if a later CAS
fails, so the coordinator can inspect and resume idempotently.

Known preflight-failure blocked rows remain blocked. Their original failure
receipt is retained verbatim and included in the migration receipt. A later
requeue must bind to the returned new revision and the original failure
receipt; the migration never alters historical receipt revisions or claims
provider execution occurred. The supported unknown-observation case requires
`provider_dispatched=null` and `provider_call_allowed=false` and preserves that
unknown value.

The coordinator must own the maintenance window and process lifecycle. Invoke
the script with its trusted token already in
`IPFS_ACCELERATE_AGENT_QUACK_TOKEN`; credentials are not accepted as arguments.
It emits a JSON receipt to stdout with before/after task snapshots, preserved
contract hashes, validation hashes, source artifact hashes, revisions, and
native events. `--dry-run` performs admission and read-only observation.

```bash
.venvs/ipfs-datasets-duckdb-quack/bin/python scripts/migrate_paper_validation_argv.py \
  --paper neurosymbolic_supervision --quack-endpoint "$PAPER_QUACK_ENDPOINT" \
  --repo-root .worktrees/vericodegen-neurosymbolic_supervision-2026
```

Measured validation used only fresh temporary Quack owners and databases:

- Three initial integration tests passed in 195.059 seconds: all 75 rows,
  exact contract/policy preservation, dry-run, no-write idempotence, admission
  failures before any update, and blocked-receipt preservation.
- A real owner stop/restart test passed in 18.096 seconds: two owner-history
  rows remain, the current generation is selected, and all 25 NS rows migrate.
- The dispatch-observation unit check verifies that forbidden dispatch can
  remain unobserved and that positive dispatch is rejected.

Receipts are `validation_argv_migration_tests.json` and
`validation_argv_restart_test.json`. Temporary owner processes and state were
removed. No live campaign database was mutated during this implementation or
its tests.
