# AF-027 human-review handoff

This note is the public operator handoff for the privately bound 100-unit semantic-review sample. It is not a review result. Independent human judgments remain blank until AF-028.

## What is frozen

- Guideline freeze: `AF-005/v1`
- Public packet schema: `autoformalization-annotation-packet/v1`
- Public gold schema: `autoformalization-gold-facet/v1`
- Sampling plan digest: `41bfb6978de5560fcc7404c04e34fe8b42297c3c875c7ec3353c9fc55348e87a`
- Population: 1913 unique final-test units in 20 operational groups
- Sample: 100 unique units, one per reserved public slot
- Inclusion probability: `n_h / N_h`
- Inverse-probability weight: `N_h / n_h` (weights sum to 1913)
- Estimand: finite-population unit mean over the 1913 unique units, with group dependence retained

Public repository files contain packet identities, anonymous grouping, inclusion formulas, and cryptographic commitments only. They do not contain source bodies, record identifiers, unit digests, or gold values.

## Private store (operator-owned, not Git)

Directory (mode `0700`, files `0600`):

`/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization/af005-independent-annotation-v1`

| File | Role | SHA-256 |
| --- | --- | --- |
| `sampling_plan.json` | Frozen allocation/randomization | `41bfb6978de5560fcc7404c04e34fe8b42297c3c875c7ec3353c9fc55348e87a` |
| `binding_manifest.private.json` | Source digests, groups, `N_h`/`n_h` rows | `cd5e5a0915144289e20632ae7db0f20df4c9af046806dfcbc9657feeae4a3f91` |
| `annotation_packets.private.jsonl` | Bound packets with source bodies | `d9b205cd871deb47f8c28c1597dad531b06a0204080c5d68945118b328432ddf` |
| `gold_facets.pending.private.jsonl` | Separate pending gold custody | `8611d4f80dc6d43748cf3a9f1a72c66a6b368079aa650216f42b05c7a071694c` |

Gold custody is a separate private file from the packets. Reviewers fill the pending gold forms; they do not write into public `gold_facets.jsonl` until AF-028 import.

The AF-027 worker boundary could not read this directory. That is expected: nested workers must not load holdout bodies. Operators deliver packets only through the authorized annotator workflow.

## Public identities

- 100 public templates `AF005-FT-G01-U01` … retain their original packet ids.
- Private bound packet ids `AF005-BOUND-001` … `AF005-BOUND-100` supersede provisional membership.
- Mapping from public template to bound id is recorded in `papers/completion/autoformalization/data/review_binding_manifest.json` without source digests.
- Reviewer judgments in that manifest are `blank_until_AF-028`.

## Reviewer rules (AF-028)

1. Two independent reviewer identities plus an adjudicator.
2. Packets stay candidate-blind: no A–E/T0–T5 predictions, teacher IR, or compiler targets.
3. Unknown/missing is distinct from negative.
4. Do not change selection after outcomes.
5. Return files to the private store. Public import is a schema/commitment check only.

## Importer

```
python3 papers/completion/autoformalization/evaluation/review_import.py verify-blank
python3 papers/completion/autoformalization/evaluation/review_import.py import --returned PATH
```

`verify-blank` must keep public packets and gold templates unlabeled. `import` fail-closes on a missing file, empty import, generated label, or selection change. No agent may invent annotations and call them independent human review.

## Limits

- 100 bound sources are prepared, not independently annotated.
- Twenty operational components are correlated; they are not 20 publishers.
- The 1730-unit component dominates unit weighting.
- This handoff authorizes no semantic-fidelity, agreement, or Table 6 claim.
