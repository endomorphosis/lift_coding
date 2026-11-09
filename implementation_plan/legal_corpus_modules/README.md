# Legal corpus modules plan

This directory is a goal, subgoal, and task plan for reorganizing legal data into versioned modules. It is the work queue for a later implementation pass. It is not a live campaign.

The worldwide legal search supervisor must not load this package. Its board namespace is `legal-corpus-modules-v1` on paper only. Markdown status fields are bootstrap text. They are not progress, and they are not completion evidence.

Read in this order:

1. `PLAN.md` for the contracts that already exist and the rules that stay in force.
2. `PARALLEL.md` for the waves that can run at the same time.
3. `goals.objectives.md` for the goal tree.
4. `tasks.todo.md` for every task, its dependencies, and its write scope.

Tasks in one wave may run together only when their `Depends on` entries are satisfied and their write scopes do not overlap. A task that deletes, rewrites, or moves an existing scraper tree waits for a named go-ahead even after its dependencies are done.

Documentation of the reorganized code is a later wave. Those tasks read the files that landed and describe those files. This plan describes the tree as it stands before that move.

The supervisor watchdog installed with this plan is not part of the refactor. It lives at `~/.grok/long-running-background-tasks/worldwide-supervisor-watchdog/` and does not replace the failed `worldwide-legal-search-watchdog.service` unit.
