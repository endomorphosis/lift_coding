---
name: lra-pca
description: CALL the existing LRA PCA/MCA fan-out (SVD on tactic-count features). Use for principal proof style, MCA residuals, or ptr://skill/port_pca. Do not add a second AST SVD.
---

# LRA PCA CALL

Wraps `pca_mca_fanout.fit_pca_mca` (already `np.linalg.svd` on z-scored tactic counts).

- CALL `ptr://skill/port_pca`. Stores serializable principal/minor loadings on `nca.pca`.
- Writes `ptr://family/...` cells from `amenable_families` for the current tactics.
- Keep the PCA skeleton; MCA holes are drop candidates. Jev ranks; lake admits.
- Not a leftover-draft ranker (that is forest/ridge/SVD-grid). Never docker0.
