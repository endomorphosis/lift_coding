---
name: lra-random-forest
description: Rank LRA portable drafts with a tiny random forest over lake wins/losses. Use when ranking skills, leftover drafts, or CALL ptr://skill/port_random_forest. Never writes Lean. Lake is the oracle.
---

# LRA random forest ranker

Train and score with `papers/completion/lean_refactor_arena/harness/nca_rankers.py`.

- CALL `ptr://skill/port_random_forest` from NCA ops (or `call_ranker("port_random_forest", memory=..., tactics=...)`).
- Features: tokens, wins, losses, AutoResearch help/unsafe, remaining_cut, leftover drafts, Bayes mean.
- Needs at least four labeled lake rows. Writes `nca.pipeline_bias`. Does **not** change tactic text.
- Do not treat forest score as a compile admit. Do not call docker0. Not an Arena score.
