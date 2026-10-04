# Reviewed paper contract maintenance

The paper owner supports two local administrative corrections: replace the former nested-shell validation argv with the reviewed literal argv, and add the already-declared receipt snapshot directory to a ready task's outputs. Requests name the operation, task CID, expected revision, and exact live owner identity. The requester cannot supply SQL, replacement commands, output paths, status changes, or completion credit.

Only owners with one of the four reviewed `vericodegen-2026-<paper>` store IDs enable this interface. They create `paper-maintenance/credential` inside their private state directory. This mode-0600 credential is separate from the Quack read token, rotates on restart, and is removed on shutdown. The request and signed response bind the database UUID, server ID, generation, process birth identity, and endpoint. Pending requests expire after 30 seconds. The inbox limits request size and work per polling pass.

The owner holds its existing exclusive connection lock, checks the current source-file hashes and complete reviewed task population, and computes the correction itself. The native repository applies the expected-revision CAS inside an explicit transaction. Before committing, the owner verifies the new revision, exact intended change, and preservation of the remaining task contract. A successful correction appends one native event; already-correct tasks append none. A lost response is an unknown outcome: reobserve the task before deciding whether to retry. Replaying an applied request with its old revision cannot append a second event.

For argv migration, stop workers for the maintenance window. Every task must be ready or carry the exact supported blocked preflight receipt; no task may be in progress. The migration preserves that blocked receipt and does not requeue the task. Snapshot repair can run with active or completed tasks present; their records are preserved and only ready tasks receive the missing declaration.

Run the updated owner first, then use its existing read-token environment and exact endpoint to inspect the tasks. Supply its state directory explicitly with `--owner-state-dir`, or set `PAPER_OWNER_STATE_DIR`. An older running owner has no maintenance credential and must be upgraded during its normal maintenance window.

```bash
python3 scripts/migrate_paper_validation_argv.py \
  --paper neurosymbolic_supervision \
  --quack-endpoint "$PAPER_QUACK_ENDPOINT" \
  --owner-state-dir "$PAPER_OWNER_STATE_DIR" --dry-run

python3 scripts/migrate_paper_validation_argv.py \
  --paper neurosymbolic_supervision \
  --quack-endpoint "$PAPER_QUACK_ENDPOINT" \
  --owner-state-dir "$PAPER_OWNER_STATE_DIR"

python3 scripts/repair_paper_snapshot_outputs.py \
  --paper neurosymbolic_supervision \
  --quack-endpoint "$PAPER_QUACK_ENDPOINT" \
  --owner-state-dir "$PAPER_OWNER_STATE_DIR" --apply
```

Qualification uses fresh actual Quack owners and native databases. Historical fixture mutations happen offline before startup. Controls exercise all four board populations, owner restart, idempotent repetition, active/completed task preservation, blocked receipt preservation, stale revisions, forged credentials, arbitrary operation names, extra request fields, foreign generations, and owner-side admission independent of client preflight. General Quack write templates and worker claim authority are unchanged.
