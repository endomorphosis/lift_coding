---
name: lra-turing
description: Turing-machine tools on the LRA neural tape and stack, plus a decision-transformer context packer. Use for TM step/run, tape L/R/write, stack push/pop, or CALL ptr://skill/port_{tm_step,tm_run,tm_left,tm_right,tm_write,tm_read,tm_push,tm_pop,decision_transformer}. Never writes Lean.
---

Canonical skill: `~/lift_coding/JevOps/skills/jevops-turing/SKILL.md`.
Modules: `jevops.turing`, `jevops.tape`, `jevops.tape_tools`, `jevops.stack`. PYTHONPATH must include JevOps.

LRA `harness/nca_turing.py` / `neural_tape.py` / `nca_tape_tools.py` are shims.
