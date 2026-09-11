The first real task dispatch reached native dependency preflight but was
rejected before any provider call. The reviewed board declared a direct
`python3 scripts/paper_supervisors.py verify-task ...` command. The campaign
materializer incorrectly encoded it as `['bash', '-lc', command]`, which the
native database Portal bridge preserved when rendering the task projection.
`validation_command_repository_root()` deliberately rejects nested shells;
that explains `validation_repository_root_is_unsafe`. The worker checkout and
its Git common directory were valid.

The materializer now stores the exact direct verifier argv, checks its
paper/task binding, and rejects wrappers or compound commands during import.
The native shell safety policy was not changed. Five materializer tests pass,
including all 75 task contracts, a real fresh database/Portal projection, and
negative tests for wrappers, compound commands, and a different task ID.

`validation_worktree_repro.py` independently imported NS-001 into a fresh
temporary database, rendered and parsed its actual native Portal projection,
created a detached worker checkout from the NS integration lane, initialized
all three external repositories through native
`PortalImplementationDaemon._initialize_worktree_submodules()`, and called the
actual dependency preflight with its real sealed Python probe. The original
wrapped command failed with the observed root-safety error. The corrected
command passed with
`approved_validation_environment_satisfies_project_dependencies` using sealed
`/usr/bin/python3.12`. Its repository-root project contract and required Python
version were satisfied. No dependency installation or provider call occurred.

The script removed only its temporary worker/submodule worktrees. The root
index remained unchanged, and no live task rows or supervisor processes were
changed. Its measured receipt is `validation_worktree_repro.json`.

Run the reproduction from the repository root:

```bash
.venvs/ipfs-datasets-duckdb-quack/bin/python \
  papers/completion/runtime_bootstrap/validation_worktree_repro.py
```

Existing campaign database rows still contain the old wrapper until the
coordinator applies a reviewed metadata migration. This source correction by
itself does not modify or retry any live task.
