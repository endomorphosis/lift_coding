# Lean Refactor Arena competition report

Competition-track report for the NeurIPS 2026 VeriCodeGen workshop, built from:

- Warm-up JSONL: `data/benchmark_data_warmup.jsonl` (SHA-256 `6209680cf00cde0765b77b24834cd72c64dd585b2f7e3f2a58209980ab59a804`)
- Arena Space: https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena
- Workshop: https://vericodegen.github.io/
- Competition site: https://leanrefactor.github.io/

This is **not** one of the three research-track boards (`autoformalization`, `law_to_action`, `neurosymbolic_supervision`). It is not registered in `scripts/paper_supervisors.py`. It does **not** claim Arena leaderboard scores, official 4×A100 Track 2 results, or token savings.

## What is measured

The public 15-problem warm-up subset (3 each from Strata, PhysLib, CSLib, ArkLib, PutnamBench). Regenerate the census with:

```
python3 papers/completion/lean_refactor_arena/tools/summarize_warmup.py
```

The script fails closed if the JSONL hash drifts.

## What is unrun

The Leanstral refactoring harness specified in `manuscript/main.tex` (Approach / Models / Budget accounting / Reproduction). No candidate proofs, no elaboration scores, no Space submission.

## Build the PDF

```
cd papers/completion/lean_refactor_arena/manuscript
latexmk -pdf -interaction=nonstopmode main.tex
```

Template: `neurips_2026_vericode_competition.sty` (competition track, not the research workshop style). Reports are single-blind: author name and email are real.

## Layout

| Path | Role |
| --- | --- |
| `typesafe_nca.md` | TypeSafe NCA architecture for agents and harness engineers |
| `harness/nca_rankers.py` | RF, Thompson, plus dispatch to integer milles rankers |
| `harness/nca_int_rankers.py` | SVD, PCA, ridge, OLS, logistic, k-means, kNN, ICA, NMF, Kalman, Bayes, MCMC (no float64) |
| `harness/nca_autoencoder.py` | VAE text→Lean round-trip; Jev batch loss; shortest lake-ok Lean |
| `harness/nca_more_rankers.py` | SGD/mask/diffuse wraps; Markov; isotonic; AdaBoost; quantiles; PageRank; contrastive |
| `harness/nca_graph.py` | Graph traverse, GraphRAG search, milles neural message-passing |
| `harness/nca_jsonld.py` | JSON-LD graph interface; optional DuckDB adapter |
| `harness/nca_skill_tree.py` | Hierarchical skill tree searched by random forest |
| `harness/nca_temporal.py` | Hawkes, CRF, submodular, delayed bandit, tape conv/DFT |
| `harness/nca_turing.py` | Turing tape/stack tools; decision-transformer (s,a,R) window |
| `harness/nca_tape_tools.py` | Tape splice/mask/pop/crop/keep/checkpoint for DT context |
| `data/benchmark_data_warmup.jsonl` | Frozen organizer warm-up |
| `data/warmup_summary.json` | Machine-readable census |
| `tools/summarize_warmup.py` | Hash check + table + receipt |
| `manuscript/main.tex` | Competition report |
| `evidence/import_receipt.json` | Import provenance |
| `protocol.md` | Frozen claim boundary |
