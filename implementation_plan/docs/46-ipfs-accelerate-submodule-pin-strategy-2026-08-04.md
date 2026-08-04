# ipfs_accelerate monorepo pin strategy (2026-08-04)

**Status:** operator note (non-normative)  
**Audience:** maintainers working in `lift_coding` with `external/ipfs_accelerate`  
**Scope:** How to consume current `ipfs_accelerate_py` `main` without destroying
the long-lived rescue checkout used by prompt-entrypoint / swissknife work.

## Current facts

| Location | Branch / tip | Role |
| --- | --- | --- |
| `external/ipfs_accelerate` (submodule worktree) | `rescue/local-main-worktree-20260801` @ `f2db26020` | Live rescue line; **~55 ahead / ~1330 behind** `origin/main` |
| Parent gitlink at monorepo `HEAD` | `032c384e8` (gitlink) | Recorded pin; may lag the checked-out worktree |
| Clean docs worktree | `.worktrees/ipfs-accelerate-docs-refresh` | Docs refresh branch; keep ff-merged to `origin/main` |
| Clean main worktree | `.worktrees/ipfs-accelerate-main` | Dedicated `origin/main` checkout for monorepo tools that need product tip without touching rescue |
| Upstream product main | `origin/main` on `endomorphosis/ipfs_accelerate_py` | Includes DOC closeout, version pin fix, link checker, documentation-gates CI + branch protection |

Do **not** force `external/ipfs_accelerate` to `origin/main` while rescue WIP and
supervisor lanes still depend on the rescue branch.

## Rules

1. **Rescue stays put** until an explicit rescue→main merge (or cherry-pick
   series) is planned and validated.
2. **Docs / packaging / CI consumption of current main** uses a separate
   worktree or clone, not a destructive submodule reset.
3. **Parent monorepo submodule pin updates** are deliberate commits on the
   monorepo branch that needs them; they are not a side effect of docs work.
4. **Swissknife / SCA lanes** that list `external/ipfs_accelerate` as a
   worktree submodule path continue to use the rescue checkout until those
   programs migrate.

## Recommended layouts

### A. Keep using rescue (default for in-flight supervisors)

```text
lift_coding/external/ipfs_accelerate  →  rescue/local-main-worktree-20260801
```

No action required.

### B. Need current product main without touching rescue

Preferred clean tip (created 2026-08-04):

```bash
cd /home/barberb/lift_coding/.worktrees/ipfs-accelerate-main
git fetch origin main
git merge --ff-only origin/main   # or: git reset --hard origin/main on this worktree only
```

Docs-oriented worktree (same remote, docs branch history):

```bash
cd /home/barberb/lift_coding/.worktrees/ipfs-accelerate-docs-refresh
git fetch origin main
git merge --ff-only origin/main
```

Point tools that need modern docs/CI only at one of those worktrees — never
`git reset --hard origin/main` inside `external/ipfs_accelerate` while rescue
lanes are live.

### C. Promote rescue into main (future, high cost)

1. Inventory the 55 rescue-only commits and open tasks on that branch.
2. Merge or rebase onto `origin/main` in an isolated worktree.
3. Run supervisor matrices + documentation-gates.
4. Land to `origin/main` via PR (now blocked until `documentation-gates` is green).
5. Only then move `external/ipfs_accelerate` and the parent gitlink.

## Documentation / CI notes (product repo)

On `ipfs_accelerate_py` `main`:

- Offline gates: `scripts/docs/check_agent_supervisor_docs.py`,
  `scripts/docs/check_current_docs_links.py`
- Workflow: `.github/workflows/documentation-gates.yml`
- Branch protection requires status check **`documentation-gates`**
  (`enforce_admins` off; force-push and deletion disabled)

## Non-goals of this note

- Does not change monorepo gitlinks
- Does not merge rescue into main
- Does not stop running swissknife supervisors
