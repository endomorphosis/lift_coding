# MCP++ Profile H operations and incident recovery

This runbook applies to Profile H quote, verification, settlement, entitlement,
access, execution, reconciliation, and refund incidents. Operational surfaces
are aggregate-only: never paste payment payloads, wallet addresses, transaction
identifiers, request arguments, protected inputs/outputs, UCANs, or facilitator
responses into metrics, alerts, tickets, or chat.

## Routine readiness

Poll the facilitator and ledger probes independently. A seller is ready for new
paid work only when both report `ready`. The ledger probe checks queryability,
required tables, transition referential integrity, settled receipt linkage, and
the recovery queue. The facilitator probe has a hard timeout and deliberately
returns no exception or upstream response body.

Use the dashboard lifecycle panel to locate the failing stage. Labels are only
`stage`, `outcome`, configured `seller`, and stable `H_*` reason code. Quote and
access failures normally precede spend; settlement failures may have an unknown
external outcome and require reconciliation; execution failures after settlement
require domain-effect reconciliation and possibly refund review.

## Containment

1. Activate the affected seller switch when the incident is isolated. Activate
   the global switch for ledger integrity, widespread facilitator failures, or
   suspected unauthorized spend.
2. Confirm new quotes, verification, settlement, entitlement consumption, and
   execution are stopped. Do not delete the ledger, receipts, or artifact store.
3. Confirm receipt lookup, health, backup, reconciliation, and refund operations
   remain available. A pause is containment, not rollback of settled value.
4. Record the public `H_*` reason, affected seller, first/last observed time,
   aggregate count, and snapshot evidence CID. Keep private evidence in the
   approved encrypted incident system only.

## Reconciliation and refunds

Process `reconciliation_required`, `settling`, and `executing` entries oldest
first. For settlement uncertainty, query the configured facilitator using the
stored payment commitment; never resubmit the authorization merely because a
response was lost. Mark the ledger settled only after validating matching
network, amount, seller, and immutable receipt evidence. Mark it failed only
after a definitive negative lookup. Leave an unknown outcome fenced.

For `executing`, consult the domain operation's own idempotency/result record.
If it ran, attach the access/result receipt without repeating the effect. If it
definitively did not run, follow the service's safe replay policy. If paid value
cannot be fulfilled, create a refund request linked to the settlement CID,
apply the published refund policy, persist the redacted `RefundRecord`, then
reconcile its outcome. A refund never edits or deletes the original settlement.

## Backup and restore

`BackupManager.create` checkpoints DuckDB, copies immutable artifacts, validates
every artifact CID, and commits a digest manifest. Store snapshots encrypted,
access-controlled, and according to ledger retention policy.

To restore, stop writers and restore into empty paths. `BackupManager.restore`
verifies the manifest, ledger digest/schema, and every artifact digest/CID before
activation. Open the restored ledger and require a ready health probe. Verify:

- an executed payment retains its quote-to-result transition history;
- settled payment and access receipt CIDs are unchanged;
- replaying a different payment against the same idempotency key is rejected;
- uncertain settlement/execution entries remain in the recovery queue;
- receipt lookup works before any switch is resumed.

Never restore an older ledger over a live one to reverse settlement. Preserve
the failed instance for forensic comparison, reconcile external settlement
state, and resume the seller switch first. Resume the global switch only after
all critical alerts clear and a second operator reviews the evidence.

## Validation

Run `python scripts/run_mcplusplus_profile_h_ops_gate.py`. Its report at
`swissknife/test-results/mcpplusplus-profile-h-x402/operations.json` proves
bounded redacted telemetry, dashboard/alerts, dependency probes, persistent
global and seller switches, recovery availability under pause, and a verified
backup/restore with idempotency and settled lineage intact.

