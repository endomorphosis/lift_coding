# Worldwide legal search campaign package

Start with [PLAN.md](PLAN.md) for the product, worldwide jurisdiction model, UI/UX, TypeScript data/search architecture, validation and repair strategy. Give [HANDOFF.md](HANDOFF.md) to the `ipfs_accelerate_py` supervisor to begin admission and implementation.

The definition has one root goal, ten goals, twenty subgoals and 64 core tasks. The core task DAG expands into bounded per-source normalization, indexing, geographic-join, publication and verification tasks after the Hugging Face inventory is pinned. Every task has dependencies, repository ownership, write scope, acceptance, validation argv, evidence requirements and retry bounds.

| File | Purpose |
| --- | --- |
| `plan.json` | Machine-readable goals, subgoals, task DAG, provider route and source-expansion templates |
| `tasks.todo.md` | Native supervisor task bootstrap projection |
| `goals.objectives.md` | Native root, goal and subgoal objective records |
| `supervisor.json` | Native scheduler profile; does not itself activate a provider or authorize launch |
| `watchdog_loop.py`, `watchdog.policy.json` | Executable observation/recovery-request loop with durable incident/action budgets |
| `WATCHDOG.md` | Native adapter protocol, activation prerequisite and commands |
| `test_watchdog.py` | Scenario tests for stalls, blockers, effects, persistence, completion and source expansion |
| `validate_plan.py`, `build_plan.py` | Structural/native compatibility validation and reproducible projections |
| `research.json` | Inspected source revisions, observations, official references and pending runtime checks |
| `validation_results.json` | Recorded validation output and artifact hashes |

Run from the repository root:

```bash
python3 -B implementation_plan/worldwide_legal_search/validate_plan.py --native-root /home/barberb/ipfs_accelerate_py
python3 -B -m unittest discover -s implementation_plan/worldwide_legal_search -p 'test_*.py'
```

The primary agent route is `llm_router` → `grok_cli` → `grok-4.7`, with the existing typed emergency Codex policy. The site remains a static GitHub Pages application. The operational supervisor/watchdog runs on the development host.

Planning does not start the implementation campaign, invoke a model, publish data or deploy the website. The executable watchdog can be tested immediately; live automatic repair depends on the native adapter/readiness canary explicitly assigned to the first milestone. A complete plan validation is not evidence of complete worldwide legal coverage or of a running recovery service.
