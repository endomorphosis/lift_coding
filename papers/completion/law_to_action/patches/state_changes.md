# LA-012 isolated state / durable consumption changes

This task's allowed edit set is output-only. Production sources
`admissibility_enforcement.py`, `quack_state_client.py`, and
`quack_state_server.py` were **not** modified.

## Production source edits

None applied. The existing ENFORCE path already consumes a one-time
token before the delegate when an injected store is supplied. The
constructor still defaults to `InMemoryCapabilityConsumptionStore`.

## Isolated adapter (declared benchmark output)

`DuckDBCapabilityConsumptionStore` in `durable_consumption.py`:

- refuses `:memory:` paths
- installs the checksum-bound control-plane schema onto file-backed `control.duckdb`
- consumes through `QuackStateClient.submit_command` / `StateTransaction`
- treats identical command identity as `idempotent_replay` (try_consume False)
- surfaces stale generation, fence mismatch, revision conflict, and changed-payload conflict

This adapter is the selected ENFORCE deployment store for restart-safety
qualification. It is not a silent rewrite of the production default.

## Boundary regressions executed

- same-use concurrent threads
- process restart of the file-backed store
- lost owner reply
- lost ENFORCE reply after delegate
- consume-then-crash-before-delegate uncertainty
- stale generation / fence / revision
- changed-payload idempotency
- owner apply rollback
- second exclusive writer fail-closed
- in-memory contrast (excluded from the restart claim)

## Recorded failures

- No applied source patch was required for the selected durable-store cases.

## Environment pins

- duckdb 1.5.2 origin=/opt/ipfs-validation-site-packages/duckdb/__init__.py
- quack extension loaded: False
- validation site-packages: /opt/ipfs-validation-site-packages
