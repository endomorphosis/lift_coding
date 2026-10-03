# Supervisor qualification after restart

The recovered full supervisor fixture now completes with a pinned 384D
autoencoder checkpoint. Its 195.35-second run includes source repair, public
validation, publication, independent cold comparison and STOP. All three source
inventories retain 15 entries. Three actual checkpoint inference passes execute,
with zero LLM calls, zero head refits and no remaining owned processes or leases.
The original 90-second planning limit is unchanged.

The [preparation profile documentation](../../external/ipfs_accelerate/docs/agent_supervisor/REPOSITORY_PREPARATION_PROFILE.md)
describes the independent scan, index, proof, training and inference selections.
Its [qualification evidence](../../external/ipfs_accelerate/docs/agent_supervisor/evidence/repository-preparation-profile-20261002/qualification.json)
retains 83 distinct passing controls across 85 selected attempts, including two
CPU admission refusals, and all five preceding failed native attempts.

Checkpoint consumption is verified; neural formalization remains unqualified.
Each inference pass returns one unsupported source row and three unqualified
candidates. The existing deterministic symbolic planner and independent proof
checks govern the repair. The authored scalar fixture is an integration test;
there is no new Terminal Bench score or matched Codex token comparison.

The same release includes bounded CID memoization with fresh registry guards,
opt-in native per-process limits, and durable recovery of local peer federation.
Their focused suites passed 63, 52 and 49 tests respectively. Peer recovery
reconstructs completed results after lost replies without refitting, redelivery
or moving the model head. Its scope is two sequential local process profiles,
shared artifacts and an 8D federation protocol. Distributed 384D training and
aggregate resource enforcement remain open.

The [32-item backlog ledger](../../external/ipfs_accelerate/docs/architecture/repository_proof_index_backlog_status.json)
records 26 criteria qualified for their declared profile and 18 closed with
dependencies satisfied. Its audit verifies 73 evidence references. The remaining
14 production criteria are still open; scoped test passes do not close unmet
dependencies.

All four local documentation workflow checks pass. The observed
[GitHub Actions run](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/37080317198)
could not start because GitHub reported an account billing lock. That remote
result is not recorded as a passing CI run.

Source, test generations and failed attempts are retained in the pinned
submodule evidence directories. Release worktrees now live under the persistent
workspace `.worktrees` directory. Publication preserves concurrent upstream work
and leaves the original working checkouts intact. No checkpoint was promoted or
uploaded during this recovery.
