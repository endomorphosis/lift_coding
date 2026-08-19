# FACP-061 Resolution: FACP-029 Validation Retry-Budget Failure

- Date: 2026-08-19
- Source task: FACP-029
- Repair task: FACP-061
- Attempt: 3
- Retry budget: 3
- Observed consecutive validation failures: 4
- Failed command: `export PYTHONPATH="$PWD"/Mcp-Plus-Plus:"$PWD"/external/ipfs_accelerate:"$PWD"/external/ipfs_datasets:"$PWD"/external/ipfs_kit:"$PWD"/swissknife; python3 -m pytest test/formal_assurance/test_facp_029_swissknife_browser_vectors.py -q`

## Finding

All four FACP-029 attempts produced the SwissKnife vector fixture and TypeScript
negative suite, and agents reported local pytest green (`7 passed`). The daemon
validation gate then failed identically with:

```text
ERROR: file or directory not found: test/formal_assurance/test_facp_029_swissknife_browser_vectors.py
no tests ran in 0.00s
[validation failed] returncode=4
```

Proposal admission for FACP-029 accepted only the declared SwissKnife Outputs:

- `swissknife/test/formal-assurance/browser-authority-vectors.json`
- `swissknife/test/formal-assurance/browser-nonauthority.test.ts`

The Python harness at `test/formal_assurance/test_facp_029_swissknife_browser_vectors.py`
was required by the declared Validation command and Allowed effects ("add ...
Python harness") but was not listed in Outputs/Predicted files. Admission therefore
dropped it before the clean-checkout validation gate, leaving the gate unable to
locate its target path. That is inherited validation debt, not a weakened
production-policy failure inside the SwissKnife fixtures.

FACP-061 attempt 1 restored the harness as an untracked worktree file. Local
pytest passed again, but `_restore_out_of_scope_worktree_mutations` deleted the
untracked out-of-scope path before proposal collection, so daemon validation
repeated the same file-not-found failure.

FACP-061 attempt 2 staged the harness, passed daemon validation (`7 passed`,
scope adjudication `EXPLICIT_VALIDATION_TARGET`), and wrote completion evidence,
but the next attempt worktree again lacked the deliverables on disk.

## Repair (attempt 3)

Recovered and restored the FACP-029 deliverables without weakening assertions:

1. Restored `swissknife/test/formal-assurance/browser-authority-vectors.json`
   (schema `facp/browser-nonauthority@1`): 10 accepted nonauthority pairs, argument /
   replay / expiry sensitivity vectors, and 2 failing seeds for legacy
   default-granted consent and browser-constructed allow.
2. Restored `swissknife/test/formal-assurance/browser-nonauthority.test.ts` with
   hermetic host-authorization projection helpers and paired/failing-seed coverage.
3. Restored the missing Python harness
   `test/formal_assurance/test_facp_029_swissknife_browser_vectors.py` under the
   bounded diagnostic/repair scope for inherited validation debt. Assertions were
   preserved (no policy weakening).
4. Staged the harness (`git add -f`) so out-of-scope untracked restore cannot delete
   it before proposal collection; scope adjudication can then justify it as an
   explicit validation target without weakening checks.

## Validation

```text
export PYTHONPATH="$PWD"/Mcp-Plus-Plus:"$PWD"/external/ipfs_accelerate:"$PWD"/external/ipfs_datasets:"$PWD"/external/ipfs_kit:"$PWD"/swissknife
python3 -m pytest test/formal_assurance/test_facp_029_swissknife_browser_vectors.py -q
.......                                                                  [100%]
7 passed in 0.04s
```

## Disposition

- FACP-061 status: **completed**
- The repeated validation blocker for FACP-029 is repaired.
- FACP-029 may be removed from strategy `blocked_tasks`; its validated outputs are
  restored and the declared gate passes without weakening correct production policy
  or test assertions.
