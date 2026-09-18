---
name: lra-bayes-time
description: Sequential Beta-Bernoulli estimates of LRA skill win-rate with exponential forget. Use for Bayesian estimation over time, posterior energy, or CALL ptr://skill/port_bayes_time. Never writes Lean.
---

# LRA Bayesian estimation over time

Use `nca_rankers.observe_bayes` / `sync_bayes_from_memory` / `posterior`.

- Prior `Beta(1,1)`. Each live lake result is a Bernoulli trial. Forget factor `0.98` toward the prior on every `observe_bayes`.
- CALL `ptr://skill/port_bayes_time` rebuilds counts from `memory.successes` / `failures` and writes posterior mean onto `ptr://skill/port_*` cells.
- Posterior mean ranks pipeline order; it does **not** admit a proof. Lake is the oracle. Never docker0.
