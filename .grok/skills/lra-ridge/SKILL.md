---
name: lra-ridge
description: Ridge-logistic P(lake-ok | LRA feature_row). Use as a calibrated companion to the random forest or CALL ptr://skill/port_ridge. Never writes Lean.
---

# LRA ridge ranker

`nca_rankers.train_ridge` / `score_ridge` on the same 8-D `feature_row` as the forest.

- CALL `ptr://skill/port_ridge`. Needs ≥4 labeled lake rows. L2 = 1.
- Prefer this over the forest when n is tiny and you want a monotonic score next to Noul.
- Score is not a compile admit. Never docker0. Not Track 2.
