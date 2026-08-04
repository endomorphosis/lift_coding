# Proof-backed test reuse — integration pins (2026-08-04)

## Branch

- `integration/proof-backed-test-reuse-66` → tip of closed implementation board
- Also on `agent/proof-backed-test-reuse`

## Submodule pins (closed stack)

| Submodule | Revision |
| --- | --- |
| `external/ipfs_accelerate` | `ded3932433f4d08e6eb8eddc1595bfb1c0ddabf0` |
| `external/ipfs_datasets` | `1894e9dca7dced0690893d468e40751a14f0b15b` |
| `external/ipfs_kit` | `2f2fd78505fe7528bb406dbed1123abbb729ce80` |

## Worktree

`/home/barberb/lift_coding/.worktrees/proof-backed-test-reuse`

## Materialization probe

```bash
python3 scripts/materialize_proof_backed_test_reuse_closeout_inputs.py
```

Outputs under:

`~/.local/state/ipfs_accelerate_py/proof-backed-test-reuse-v1/projection/completion/materialization/`

This probe is **not** completion authority. Live closeout still requires
managed-merge / operator-approval provenance, fresh MODE=off receipts, and
authoritative PTR-110→122 gate materialization.

## Apply pins to another checkout (operator)

```bash
cd /path/to/lift_coding
git fetch . integration/proof-backed-test-reuse-66
# preferred: work from the integration branch or worktree rather than
# force-updating unrelated feature branches
git checkout -B integration/proof-backed-test-reuse-66 integration/proof-backed-test-reuse-66
git submodule update --init external/ipfs_accelerate external/ipfs_datasets external/ipfs_kit
```
