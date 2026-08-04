# Proof-backed test reuse — main-checkout port note (2026-08-04)

## What landed on this branch

Documentation, board artifacts, and outer supervisor scripts from
`agent/proof-backed-test-reuse` were staged into the main `lift_coding`
checkout so operators can read the closed board without entering the worktree:

| Path | Role |
| --- | --- |
| `implementation_plan/docs/46-proof-backed-test-reuse.todo.md` | 66-task board (all completed) |
| `implementation_plan/docs/46-proof-backed-test-reuse.objectives.md` | protected objective heap (not live-closed) |
| `implementation_plan/docs/46-proof-backed-test-reuse-plan-2026-07-31.md` | plan |
| `implementation_plan/docs/46-proof-backed-test-reuse-readiness-audit-2026-08-04.md` | current readiness + closeout diagnosis |
| `implementation_plan/docs/46-proof-backed-test-reuse-closeout-*.json` | report-only closeout capture |
| `config/proof_backed_test_reuse_supervisor.json` | three-lane supervisor config |
| `scripts/proof_backed_test_reuse_supervisor.py` | outer supervisor / closeout CLI |
| `scripts/validate_proof_backed_test_reuse_board.py` | board validator |

## What did **not** land automatically

| Item | Why |
| --- | --- |
| Full merge of `agent/proof-backed-test-reuse` | Divergent history from current main branch work; avoid surprise submodule/gitlink churn |
| Submodule pin updates for `external/ipfs_accelerate`, `external/ipfs_datasets`, `external/ipfs_kit` | Main checkout may carry other in-flight work; pins must be applied deliberately |
| Live objective closeout / warm-skip authority | Report-only diagnosis still refuses (missing gate evidence + activation gap) |

## Canonical closed stack (worktree)

- Worktree: `/home/barberb/lift_coding/.worktrees/proof-backed-test-reuse`
- Branch: `agent/proof-backed-test-reuse` @ `6d76db81a` (audit commit) / board close `39e8992ad`
- Submodule pins:
  - accelerate `ded3932433f4d08e6eb8eddc1595bfb1c0ddabf0`
  - datasets `1894e9dca7dced0690893d468e40751a14f0b15b`
  - kit `2f2fd78505fe7528bb406dbed1123abbb729ce80`

## Recommended operator commands (from the worktree)

```bash
cd /home/barberb/lift_coding/.worktrees/proof-backed-test-reuse
python3 scripts/validate_proof_backed_test_reuse_board.py
python3 scripts/proof_backed_test_reuse_supervisor.py status
IPFS_TEST_PROOF_REUSE_MODE=off \
  python3 scripts/proof_backed_test_reuse_supervisor.py closeout --report-only
```

Do not run live `closeout` until report-only is ready.
