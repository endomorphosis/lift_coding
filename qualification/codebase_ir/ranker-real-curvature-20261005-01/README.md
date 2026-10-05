# Original ranker: exact data, real calculus and advisory proofs

This qualification uses the original Terminal Bench intent corpus, four training pairs and 80 coordinates. It does not train a replacement model or replay the original training trace. One captured feature preparation supplies the stored difference vectors; a pure exact binding embeds all 320 binary64 values as rational numbers.

Lean 4.34.0 with Mathlib revision `5ed2965256430c3649e86755f9576b54eca72435` checked ten complete modules. They establish logistic coefficient bounds, finite coordinate geometry, actual real scalar and directional derivatives, the coordinate gradient, Taylor's upper bound, and a gradient-step descent theorem. The original rational matrix and parameters are explicitly cast into the real model; the original-profile descent theorem assumes no unproved data alignment premise.

For the stated real objective

`F(w) = μ/2 · Σⱼ wⱼ² + 1/4 · Σᵢ log(1 + exp(−w·dᵢ))`,

the exact original step satisfies the safe-step inequality and

`F(w − ηg(w)) ≤ F(w) − η/2 · Σⱼ gⱼ(w)²`.

This is a theorem about one step of the stated exact-real model. Binary64 products, `math.fsum`, stable branch evaluation, `exp`/`log1p` and the actual Python update still require a source-to-model and numerical-error bridge. Global or asymptotic convergence, autoencoder convergence and full benchmark task satisfaction remain open.

There were 19 actual bounded Lean invocations: ten qualified positive checks, one genuine kernel rejection of a deliberately false proposition, and eight retained inconclusive attempts. Complete objects are retained directly or reconstructed from complete 64 KiB chunks; every native solver limit remains unchanged. Failed syntax, namespace, truncation and postprocessing attempts are preserved.

The pure controls executed 249 selected test cases, including 59 earlier cache cases collected again with 17 new version-two cases. Ten actual qualified advisory cache entries returned ten same-query hits and 230 misses when one of 23 identities changed. Entries bind source, theorem, assumptions, environment, checker, original corpus and numeric parameters, translation policies and retention formats.

Native DuckDB 1.5.5/DuckLake hydration and fresh-process readback preserve 4,378 payloads across 32 families. All 4,348 inherited payloads, their order and contracts remain unchanged. Three additive families hold the exact numeric binding, all 19 check attempts and ten advisory proof entries.

`qualified-review-01.json` and `file-only-seal-01.json` bind the closed evidence. Historical mutable producer paths are distinguished from retained exact-byte aliases. No atomic whole-source snapshot or historical loader-origin claim is made. All proof/execution/completion authority and planner activation stay false; the 32 governing RPI exits remain OPEN and the benchmark score is unknown.

The full publication selection includes the owned evidence, dependency profile manifests and failed attempts for the successor curvature archive. Raw Mathlib and cache dependency trees remain local; the exact manifests and official version identify the environment to reproduce. The Git selection includes the sources, mathematical definitions, compact receipts and archive pointers. `next-obligations.json` records the remaining source, convergence and task-satisfaction work.
