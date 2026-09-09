# DOEP verifier retry recovery

A completion recovery seed can remain bound to a historical merge target while deployed source advances. Its failed verification must preserve the blocked task and historical evidence. The native operator can now admit one new attempt through the existing task-scoped Quack blocked-retry CAS:

```sh
python3 scripts/ops/agent_supervisor/direct_objective_event_driven_planning_handoff.py recover-claim-verification --task DOEP-011 --expected-revision 24
```

Stop the DOEP service first. The command refuses a live operator, dirty operator controls, a different task/revision, quarantine, and any reason other than the exact pre-provider completion-seed claim-verification failure. It stores content-addressed task/receipt evidence and authorization before the owner CAS. The owner preserves the task body, verifies terminal claim identity and execution route, requires no live lease, increases the attempt budget by exactly one without refund, and installs a mandatory fresh Portal validation obligation. Existing completion receipts never count as acceptance for the new attempt.

Restart the native supervisor after accepted recovery and verify fresh task/event progress through its owner monitor. Existing task candidates and historical evidence stay available. This command does not merge a candidate, complete a task, or accept a quarantined row.

The board generator pins the reviewed DOEP-011 present validator baseline to its canonical task CID, exact output path, and SHA-256. Regeneration therefore preserves the repaired prerequisite; it cannot silently return an already merged target to an absent baseline or learn a new digest from unreviewed runtime bytes. Native dependency preflight still verifies the file against this source attestation.
