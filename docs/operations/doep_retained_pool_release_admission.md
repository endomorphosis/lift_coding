# DOEP retained pool release admission

The native operator provides `retained-pool-release-admission --request-json PATH`
for DOEP-032 and DOEP-041. It returns a versioned read-only decision after the
ordinary current-root preflight and an independently scoped native status/history
read. It can reject mismatched scope or identify missing evidence. This version
cannot authorize release, retry, source adoption or completion, and performs no
pool, task, lease, lifecycle or receipt mutation.

The command is available on the next qualified owner launch, which binds the
sealed status scope before task dispatch. The existing running owner cannot be
retrofitted by borrowing its lane credentials or replaying a previous process
identity. The `authoritative-status` result now includes its verified
`store_generation` record for constructing an exact request.

The request is a single JSON object using schema
`ipfs_accelerate_py/agent-supervisor/doep-retained-pool-release-request@1` with
these fields. Unknown fields are rejected; caller-provided authority and receipt
claims cannot grant release.

| Fields | Binding |
| --- | --- |
| `task_alias`, `task_cid`, `task_revision` | Current canonical task and revision; only 032/041 are in scope. |
| `attempt_id`, `binding_id` | Exact immutable native DatabasePortal attempt binding. |
| `pool_lease_token` | Exact retained pool filename token; paths are derived within the native runtime. |
| `pool_owner` | Original lifecycle owner `pid`, `start_time_ticks`, `boot_id`, `parent_pid`. |
| `lifecycle_lease_id`, `lifecycle_fence` | Retained canonical lifecycle custody. |
| `owner_identity` | Fresh reader owner `server_id`, `process_birth_id`, `store_id`, `database_uuid`, `generation`, `fence_epoch`. |
| `store_generation` | Full fresh native generation record, including its verified content ID. |

Construct these values from fresh independently admitted status and exact native
bindings. A request from a previous owner, generation, task revision or pool
lease is rejected. The reader compares canonical history and native generation
again after checking the retained lifecycle, immutable Portal projection and
pool records. It rechecks source and file bytes before emitting the result.
File reads use a pinned chain of directory descriptors and reject symlinks,
FIFOs, hardlinks, oversized files and namespace replacement.

A `deferred` result includes task-specific canonical observations: current task
status, receipt presence and attempt binding, explicit unknown callback outcome,
and matching open task claims, leases or effects. Missing or truncated canonical
relations remain visible. Unavailable transport/history returns `unavailable`
without a local-file or alternate-credential fallback.

Current native interfaces do not independently admit the full canonical
execution-attempt, callback/effect settlement and terminal-event chain, or the
original fingerprint-bound retained-candidate receipt required for recovery.
Local terminal lifecycle records and `implementation_finished` logs cannot fill
those gaps. Even a canonical task body asserting release is not an independently
validated release grant. The response names these missing contracts explicitly.
DOEP-031 remains outside this release interface; its original unknown callback
and any successor acceptance still require separate exact-history reconciliation.

A future mutation operation must be owned by the qualified native service and
must independently verify the bound callback/effect disposition and original
receipt, then atomically journal an exact request and custody CAS. It must
preserve retained workspace bytes, branches and proof obligations. Existing
`recover_retained_verification_deferred_candidate` requires the original
receipt; a newly calculated fingerprint cannot recreate that historical receipt.
The internal pool-release method is not an external admission interface.
