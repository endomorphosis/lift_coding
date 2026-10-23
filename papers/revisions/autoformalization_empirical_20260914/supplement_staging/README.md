# Compiler-Guided Autoformalization: empirical supplement

This anonymous supplement contains actual observations from the completed bounded experiments reported in the paper. It separates structural validity, vector reconstruction, and kernel proof acceptance. It contains no independent human legal-semantic annotations.

Use Python 3.12 and NumPy 1.26.4, then run:

```sh
python reproduce.py --output reproduction_report.json
```

The command verifies all archived hashes, recomputes native compiler counts and paired repair intervals, checks numerical projection metrics and bootstrap summaries, verifies learned check-order off/on/rollback observations, recounts all 100 direct-model attempts, and regenerates the paper's measured LaTeX tables. It requires no network access or model inference. To additionally recheck the 12 admitted generated proofs, install Lean 4.33.1 on PATH and add `--proofs`.

The main components are:

| Folder | Observations and reproduction scope |
|---|---|
| `pipeline/` | All 1,913 source units and all native B/C/T5 terminal rows, paired repair effects, constructed and selection qualification |
| `autoencoder/` | Source embeddings, compact numeric projections, per-unit scores, three-seed summaries, component bootstrap, constant-training-mean control |
| `guidance/` | 5,739 source/seed off/on/rollback pairs and actual structural-check receipts |
| `natural/` | All 100 direct-model attempts, requests, responses, format/check/cycle decisions, resource provenance |
| `proof/` | 64 constructed goals and observations, generated proof bodies, native acceptance evidence, separate post-hoc syntax-policy diagnostic |
| `protocols/` | Fixed scientific profiles, source/model identities, runtime information, disclosed execution amendments |
| `table_inputs/` and `published_tables/` | Summary inputs and exact generated table outputs |

Full multi-gigabyte learned parameter states, pretrained model weights, and the complete external compiler/runtime installation are omitted. Their identities are recorded. This package reproduces the reported measurements from archived observations; it does not provide a complete fresh-inference installation. Individual component READMEs describe the exact boundaries and optional proof replay.

The source corpus is the identified revision of `justicedao/patent-legal-corpus`; its card declares CC0-1.0 and the retained records declare redistributable U.S. government works. Model cards declare Apache-2.0. These are upstream declarations, not new legal determinations. The included external-code license is retained under `licenses/`. Host paths are replaced only in identified publication copies; custody records provide both original and published hashes. Exact scientific values and unedited source/model observations are preserved where specified.

The 20 source components are operational groups across four editions, with a dominant component of 1,730 of 1,913 distinct units. Bootstrap intervals do not establish broad legal-domain generalization. Native B and C use different contracts and timeout boundaries. The learned decoder has no demonstrated compression bottleneck, and an identity-copy control is exact by construction. T3 decoder results are tied to T2; the learned check-order consumer runs every required check. These limitations are part of the reported result.
