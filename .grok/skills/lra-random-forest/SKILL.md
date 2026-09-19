---
name: lra-random-forest
description: Rank LRA portable drafts with a tiny random forest over lake wins/losses. Use when ranking skills, leftover drafts, or CALL ptr://skill/port_random_forest. Never writes Lean. Lake is the oracle.
---

Canonical skill: `~/lift_coding/JevOps/skills/jevops-random-forest/SKILL.md`.
Modules: `jevops.rankers`, `jevops.skill_tree`. PYTHONPATH must include JevOps.

LRA `harness/nca_rankers.py` / `nca_skill_tree.py` are shims.
