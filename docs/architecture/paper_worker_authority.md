# Paper worker authority

The paper campaign launches the native task worker with a separate sealed
bootstrap descriptor. The Quack transport token authorizes reads; it cannot
open a task-command session. Administrative paper contract maintenance keeps
its existing independent credential and operations.

The campaign creates one sealed memfd per lane. The owner, supervisor and
managed worker receive it through the native post-exec handoff only after
becoming non-dumpable. Credential delivery binds the exact child PID, process
birth, executable and argv. The owner starts its private Unix-socket grant
broker only when explicitly enabled. Public readiness contains socket paths
and owner identity, never bootstrap contents or a worker token.

For each mutation, the native task source exchanges the bootstrap for a
short-lived grant bound to the actual kernel peer PID, UID and process birth.
The grant opens one gateway session and admits only the existing seven native
database task commands. A read token, arbitrary client identity, foreign store,
changed process birth, unknown operation or reused session token is refused.
The native shared-hashing client receives a separate hash-only grant when its
additive schema is installed. That grant has no database task commands or SQL
mutations; derived hash observations do not grant proof or execution credit.

The existing typed gateway serializes commands on the exclusive owner's lock
and rechecks the live session immediately before dispatch. Native repository
methods apply the mutation. The migrated `idempotency_records` table stores its
request binding and result in the same transaction; no new schema or runtime
DDL is introduced. An exact retry returns the original result without another
domain event. Reusing a request ID with a different command, payload, store or
generation fails. A failed transaction rolls back both mutation and receipt.
Transport uncertainty retains the native unknown-outcome behavior.

Managed daemon handoff is explicit in the supervisor loop configuration.
Provider and validator environments are still scrubbed of state credentials;
they receive neither the bootstrap descriptor nor worker grants. Owner shutdown
seals its lifecycle before quiescing worker sockets outside the transaction
lock, then closes the transport and releases ownership.

`scripts/paper_supervisor_campaign.py` enables this path for new campaign
launches. Standalone `scripts/paper_state_owner.py` remains read-only unless
`--enable-worker-authority` receives a valid native parent handoff. Existing
live campaigns are not restarted by reconciliation; their lane source and
accelerator pin must include this implementation before a normal upgrade.

Qualification uses fresh real Quack owners, native task CAS and real execution
and coordination sidecars. Both a direct daemon claim and a managed child claim
must persist exactly one claim and attempt, with no provider invocation or
Markdown writes. Additional tests cover durable replay after reconnect,
rollback, credential denial, one-use sessions and executable-bound handoff.
These checks do not certify a complete provider campaign or the full native
proof suite.
