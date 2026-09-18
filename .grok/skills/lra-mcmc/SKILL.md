---
name: lra-mcmc
description: Generalized Metropolis-Hastings for LRA NCA (pipeline order or custom state). Use for MCMC, MH, annealing, or CALL ptr://skill/port_mcmc. Never writes Lean. Lake is the admit oracle.
---

# LRA generalized MCMC

`nca_rankers.metropolis_hastings(state, propose=, energy=, accept=None, steps=, temperature=)`.

- Default NCA skill CALL `ptr://skill/port_mcmc` permutes `pipeline_order` stems. Energy is `1 − Bayes mean` plus a small position penalty. Writes `nca.pipeline_bias`.
- Hard `accept` is the lake / closed-fold constraint. Without it, MH only ranks.
- This is discrete MH on NCA state, not neural sampling and not `mcmc_beam.py`'s tactic-line kernel (that file stays Inits-specific).
- Do not emit Lean from the kernel. Do not call docker0. Not Track 2.
