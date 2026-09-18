---
name: lra-plan
description: LRA goal/subgoal/task DAG and graph-of-thoughts in NCA memory for Jev. Use when managing the board, recording Jev scores as thoughts, or CALL ptr://skill/port_nca_plan / port_got. No campaign DuckDB. Never writes Lean.
---

# Plan and graph of thoughts

Inspired by `ipfs_accelerate_py.agent_supervisor` (goal→subgoal→task, objective heap) without leases or campaign DuckDB.

- Seed: `seed_nca_from_board` also fills `nca.plan`.
- Thoughts: `add_thought` / `record_jev` (Choice/Score/Noul milles) linked to `task_id`.
- CALL `port_nca_plan` (DAG) and `port_got` (thought graph, keep-best).
- Outer Grok prompt includes `nca_status.plan`.
- JSON-LD is the graph interface. Lake is the oracle. Never docker0.
