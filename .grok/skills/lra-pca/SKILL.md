---
name: lra-pca
description: CALL the existing LRA PCA/MCA fan-out (SVD on tactic-count features). Use for principal proof style, MCA residuals, or ptr://skill/port_pca. Do not add a second AST SVD.
---

Integer milles PCA: `~/lift_coding/JevOps/skills/jevops-pca/SKILL.md` (`jevops.int_rankers`).

Proof-style SVD of Lean tactic counts stays LRA: `harness/pca_mca_fanout.fit_pca_mca`. CALL `port_pca` from the kernel still hits milles PCA. Do not add a second AST SVD. PYTHONPATH must include JevOps.
