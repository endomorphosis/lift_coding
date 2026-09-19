---
name: lra-plan
description: LRA goal/subgoal/task DAG and graph-of-thoughts in NCA memory for Jev. Use when managing the board, recording Jev scores as thoughts, or CALL ptr://skill/port_nca_plan / port_got. No campaign DuckDB. Never writes Lean.
---

Canonical skill: `~/lift_coding/JevOps/skills/jevops-plan/SKILL.md`.
Modules: `jevops.plan`, `jevops.board`. PYTHONPATH must include JevOps.

LRA `harness/nca_plan.py` / `board_graph.py` are shims. `tasks.json` and `fetch_board` stay LRA.
