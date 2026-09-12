# Anonymous implementation and reproducibility package

This bundle supports double-blind review of the compiler-guided autoformalization study.
It contains frozen retained-claim inputs, table regenerators, S01-S40 content hashes, and
hash-bound references for artifacts that exceed the 100 MB workshop supplement limit.
Private repository identities, operator HOME paths, credentials, and the AF-003 ledger
are excluded. No public upload or workshop submission is performed by this package.
Independent human source-facet review was not collected and is not fabricated.

## Environment

- Interpreter: `/usr/bin/python3.12`
- `PATH`: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
- Standard library only for table regeneration. No model call, training, or native checker is required.
- Sealed-PATH Lean/Z3/CVC5 are absent; native useful-proof cells remain unavailable, not zeros.

## Regenerate reported tables

Unpack `supplement.zip` and run:

```
python3.12 -S regenerate_tables.py --check
python3.12 -S verify_retained_inputs.py
```

Expected SHA-256 values:

- `table6_pipeline.tex`: `a2ebba34895da30b383954e93ec582d2738a212d15de7b329fecf5a4d0c7aa49`
- `table11_training.tex`: `dcb2582f2c091a48b3c26bb1b1698e1287d70d77cc2c3824b4f1f822bd2d6e74`
- `table13_assistance.tex`: `655dfb58c0c1a960b636dbe35292ee243fbcb197fad1108f8a047742e2f62d3f`
- `summary.json`: `62e63725fe02f4ac9f9c5a3b397d0b2d9f9d7a1e25fc87e9eb7fdc21cb01cc72`

If the paper tree is available, the original AF-021 regenerator may be replayed:

```
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin /usr/bin/python3.12 -S papers/completion/autoformalization/evaluation/analyze_results.py --check
```

Unrun and unavailable cells are not measured zeros. Independent source-semantic fidelity
remains unmeasured. Teacher/prover/reconstruction scores are not original-source gold.

## Locate retained-claim inputs

`manifest.json` and `checksums.json` list every retained input. Files included in this ZIP
live under `frozen/` with the SHA-256 recorded in `checksums.json`. Large checkpoints and
the public MiniLM weights are hash-bound; see `large_artifacts` in `manifest.json`.

## S01-S40 mapping

`S01_S40_map.json` maps each manuscript source role to audited and current content hashes,
evidence class, and an anonymous access strategy. Private repository roots are omitted.
S14 and S32 remain unresolved. Roles S23, S24, and S26-S28/S31 were later patched; both
the AF-003 audit hash and the current hash are recorded.

## Large artifacts

Native packed-CPU states are about 5.8 GB each and are not shipped. MiniLM
`model.safetensors` is 90,868,376 bytes and is obtained from the public Hub revision
pinned in the environment pin, not from an author URL. Exact checksums are listed.
These bytes are not required to regenerate Tables 6, 11, and 13.

## What this package does not claim

- No public upload, OpenReview/workshop submission, or publication occurred here.
- No fabricated independent human review, agreement statistic, or source-fidelity score.
- Arm E is not promoted. T4 is unactivated. Final-test 1913 units remain locked.

## Commands that are not empirical results

LaTeX compilation of the manuscript is not a substitute for the table-hash checks above.
