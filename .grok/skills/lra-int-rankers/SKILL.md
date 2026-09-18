---
name: lra-int-rankers
description: Integer milles LRA rankers (SVD, PCA, ridge, OLS, logistic, k-means, kNN, ICA, NMF, Kalman, Bayes, MCMC). Use when avoiding floats or CALL ptr://skill/port_{svd,pca,ridge,ols,logistic,kmeans,knn,ica,nmf,kalman,bayes_time,mcmc}. Never writes Lean.
---

# Integer milles NCA rankers

Module: `harness/nca_int_rankers.py`. Unit is milles `0..1000`. Integer matmul, `isqrt`, integer division. No float64 in the hot path.

| CALL | Job |
| --- | --- |
| `port_svd` | Power-iteration SVD on theorem×skill ints |
| `port_pca` | Integer SVD on tactic-count matrix (not a second numpy PCA) |
| `port_ols` / `port_ridge` / `port_logistic` | Integer normal equations; logistic = OLS + milles sigmoid |
| `port_kmeans` / `port_knn` | Integer clustering / neighbors |
| `port_ica` / `port_nmf` | Integer ICA deflation / NMF on nonnegative lake counts |
| `port_kalman` | 1-D integer Kalman on skill win milles |
| `port_bayes_time` / `port_mcmc` | Integer milles posterior / MH accept |

Lake still admits. Never docker0. Not Arena scores.
