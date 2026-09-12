# LA-012 DuckDB owner and durable consumption failure matrix

This is qualification of the selected ENFORCE deployment's durable
consume adapter. It is **not** a scored A3/A4 benchmark and does
**not** claim arbitrary remote exactly-once APIs.

## Selected deployment

- Gate: `SupervisorPreInvocationEnforcement.authorize_and_delegate` in `enforce`
- Store: `DuckDBCapabilityConsumptionStore` file-backed `control.duckdb`
- Owner: typed `QuackStateClient` + `StateTransaction` (embedded exclusive-lock)
- Default `InMemoryCapabilityConsumptionStore` is a labeled contrast only
- DuckDB: 1.5.2 at `/opt/ipfs-validation-site-packages/duckdb/__init__.py`
- Quack gateway: unavailable (LOAD quack failed under sealed HOME)

## Cases

| Job | Kind | Mutation | Decision | Effects | Extra | Remote | In claim | Pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `enforce-allow-durable` | allow | none | allow | 1/1 | 0 | observed | True | True |
| `enforce-replay-durable` | replay | same-use-replay | deny | 0/0 | 0 | absent | True | True |
| `concurrent-same-use` | concurrency | two-threads-same-token | one-allow-one-deny | 1/1 | 0 | observed | True | True |
| `restart-consume-survives` | restart | close-reopen-file-backed-store | deny | 1/1 | 0 | observed | True | True |
| `in-memory-restart-contrast` | contrast | in-memory-store-lost-on-restart | allow | 2/2 | 1 | observed | False | True |
| `lost-reply-owner-idempotent-replay` | lost_reply | identical-command-after-commit | idempotent_replay | 0/0 | 0 | uncertain | True | True |
| `lost-reply-after-delegate-no-repeat-effect` | lost_reply | discard-enforcer-reply-then-retry | deny | 1/1 | 0 | uncertain | True | True |
| `crash-after-consume-before-delegate-uncertain` | uncertainty | consume-committed-delegate-not-called | deny | 0/0 | 0 | uncertain | True | True |
| `stale-generation` | owner_failure | wrong-generation | stale | 0/0 | 0 | absent | True | True |
| `stale-fence` | owner_failure | wrong-fence-epoch | stale | 0/0 | 0 | absent | True | True |
| `stale-revision` | owner_failure | stale-store-revision | conflict | 0/0 | 0 | absent | True | True |
| `changed-payload-idempotency` | idempotency | same-idempotency-key-different-command-id | idempotency_conflict | 0/0 | 0 | absent | True | True |
| `owner-failure-rollback` | owner_failure | apply-raises-before-commit | rolled_back | 0/0 | 0 | absent | True | True |
| `owner-exclusive-lock-timeout` | owner_failure | second-writer-while-owner-holds-lock | timeout | 0/0 | 0 | absent | True | True |
| `quack-gateway-unavailable` | dependency_gap | load-quack-extension | unavailable | 0/0 | 0 | absent | False | True |
| `remote-effect-not-exactly-once` | limitation | duckdb-commit-is-not-remote-exactly-once | limitation_recorded | 0/0 | 0 | uncertain | True | True |

## Selected claim

Selected durable-store cases: 14/14 passed.

## Uncertainty and lost reply

- Loss of owner reply returns `idempotent_replay` of the committed command body.
- Loss of ENFORCE reply after a successful local delegate does not re-invoke the handler.
- Consume-then-crash-before-delegate leaves local effects at zero and remote status `uncertain`.
- A DuckDB commit is not evidence that an unobserved remote API ran exactly once.

## Recorded failures and gaps

- No selected-claim assertion failures. The Quack gateway remains unqualified.

## Environment pins

- Python: `/usr/bin/python3.12` 3.12.3
- PATH: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
- HOME validation prefix observed: True
- DuckDB available: True version=1.5.2
