# Automated-scope qualification and final-run entry points

This file is the executable contract for source adapters, automated
admission, optional review import, and the selected runtime boundary. It is
not a scored paper result.

Outside reviewers are not required for the automated evidence scope bound by
LA-027. Optional author review is not independent annotation. Human identity
and label fields remain uncollected unless an authentic return exists.
Development qualification is not a held-out score.

## Frozen before predictions

`qualify_final_runtime.py qualify-automated` writes `frozen_inputs.json`,
`frozen_budgets.json`, `runtime_manifest.json`, and the automated reference
bindings **before** the source pipeline emits predictions. Arm A4 budgets are
frozen with `model_calls = 0`. Calibration and final families stay bound in
the inventory but are not scored here.

Pinned inputs:

- `benchmark/automated_evidence_amendment.json`
- original protocol SHA-256 `ba03394cd66f51999d1b177a29558b6130429eb9fc3faebea5e57c780857940f`
- `benchmark/manifests/sources.json`
- `benchmark/manifests/splits.json`
- `benchmark/annotations/automated_reference_manifest.json`
- selected runtime pins in the qualification `runtime_manifest.json`

## Automated-scope command (this task)

From the repository root, under the sealed validation `PATH` and
`/usr/bin/python3.12`:

```bash
/usr/bin/python3.12 papers/completion/law_to_action/benchmark/qualify_final_runtime.py qualify-automated \
  --out papers/completion/law_to_action/results/automated_scope_qualification
```

That command:

1. Freezes inputs, A4 budgets, amendment/protocol hashes, machine-expectation
   provenance and admission requirements.
2. Runs `source_pipeline.py` on the six development families (12 reserved cases).
3. Executes one source-derived A4 allow attempt and one A4 deny attempt through
   QF_BOOL SAT, real Ed25519 UCAN verification, `ENFORCE`
   `authorize_and_delegate`, file-backed DuckDB consumption, and
   `BoundedExportHandler` / `EffectObserver`.
4. Admits the automated scope **without** reviewer identities or human labels.
5. Runs focused refusal controls (missing bindings, incomplete accounting,
   invalid expectation provenance, self-reported success, stale profile or
   budget, automated output labeled human gold). Failed controls have a
   non-zero admission `exit_status`.
6. Records a model/provider ledger. A4 does not require model calls; none are
   invented.
7. Analyzes only automated-scope qualification. Held-out examples are not
   scored. Fixture output is not useful-work success.

Stage receipts live in `papers/completion/law_to_action/results/automated_scope_qualification/`.

Individual stages:

```bash
/usr/bin/python3.12 papers/completion/law_to_action/benchmark/automated_evidence.py build-manifest
/usr/bin/python3.12 papers/completion/law_to_action/benchmark/source_pipeline.py run \
  --split development \
  --out papers/completion/law_to_action/results/automated_scope_qualification
/usr/bin/python3.12 papers/completion/law_to_action/benchmark/automated_evidence.py admit-live \
  --out papers/completion/law_to_action/results/automated_scope_qualification
/usr/bin/python3.12 papers/completion/law_to_action/benchmark/automated_evidence.py controls \
  --out papers/completion/law_to_action/results/automated_scope_qualification
/usr/bin/python3.12 papers/completion/law_to_action/benchmark/qualify_final_runtime.py admit-final \
  --out papers/completion/law_to_action/results/automated_scope_qualification
/usr/bin/python3.12 papers/completion/law_to_action/benchmark/qualify_final_runtime.py analyze \
  --out papers/completion/law_to_action/results/automated_scope_qualification
```

`source_pipeline.py --split final` is refused. Final labels are not inspected.
A failed automated admission exits non-zero and is not an executed study.

## Fixture-only routes are not production

| Route | Role | Production? |
| --- | --- | --- |
| `benchmark/run.py` LA-008 trusted fixture harness | measurement-integrity smoke | no |
| Injected UCAN fixture verifiers | mediation contrast | no |
| `InMemoryCapabilityConsumptionStore` | labeled non-durable contrast | no |
| Supervisor `OFF` / `AUDIT` / `SHADOW` | pass-through / observational | no |
| Preselected LA-014 fixed-candidate mapping | comparability qualification | no |
| Selected A4 automated-scope command in this task | source-derived handler-boundary qualification | not a scored production run |

The selected development arm is A4 (`full_enforcement`). It is qualification
evidence for the proof/capability/effect-observing boundary. It is not LA-015
scoring and not a closed-loop model study. No held-out result or useful-work
success is inferred from it.

## Optional review import remains strict and unused

`review_import.py` is not the automated-scope gate. It still admits a human
return only when:

- every frozen selected case is present (60 planned cases / 30 families);
- independent reviewer identity and timestamp are present;
- independent labels exist;
- provenance is not agent- or supervisor-generated;
- blank packet fields are no longer blank.

Otherwise it refuses. Do not pass fabricated `review.admitted=true` into the
old gate. Optional author readings, if later supplied, are labeled
non-independent and cannot replace frozen automated evidence.

```bash
/usr/bin/python3.12 papers/completion/law_to_action/benchmark/review_import.py refuse-missing \
  --out papers/completion/law_to_action/results/automated_scope_qualification
```

## Closed-loop model arm

Closed-loop A4 is declared, unmatched to any pinned scientific model, and
unrun. If selected, the qualifier records an actual unavailable-provider
ledger entry rather than a fixture completion. Paid provider budget is 0.

## Manuscript instructions

Write from measured automated evidence and explicit scoped omissions. Do not
wait for outside reviewers. Do not claim expert legal fidelity, human
agreement or independent human validation without authentic independent data.
Original LA-005/007/026/028 receipts and blank packets remain history.
