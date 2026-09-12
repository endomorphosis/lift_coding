# LA-028 development qualification and final-run entry points

This file is the executable contract for source adapters, review import, and
the selected runtime boundary. It is not a scored paper result.

Independent human labels remain pending in LA-027. Final examples are not
scored here.

## Frozen before predictions

`qualify_final_runtime.py qualify` writes `frozen_inputs.json`,
`frozen_budgets.json`, and `runtime_manifest.json` **before** the source
pipeline emits predictions. Arm A4 budgets are frozen with `model_calls = 0`.
Calibration and final families are excluded.

Pinned inputs:

- `benchmark/manifests/sources.json`
- `benchmark/manifests/splits.json`
- `benchmark/corpus_counts.json`
- development-split rows from legal/CVE/skill packets
- selected runtime pins in `runtime_manifest.json`

## Development command (this task)

From the repository root, under the sealed validation `PATH` and
`/usr/bin/python3.12`:

```bash
/usr/bin/python3.12 papers/completion/law_to_action/benchmark/qualify_final_runtime.py qualify \
  --out papers/completion/law_to_action/results/development_qualification
```

That command:

1. Freezes inputs, A4 budgets, and admission requirements.
2. Runs `source_pipeline.py` on the six development families (12 reserved cases).
3. Runs `review_import.py`, which refuses the missing independent review return.
4. Executes one source-derived A4 allow attempt and one A4 deny attempt through
   QF_BOOL SAT, real Ed25519 UCAN verification, `ENFORCE`
   `authorize_and_delegate`, file-backed DuckDB consumption, and
   `BoundedExportHandler` / `EffectObserver`.
5. Records a model/provider ledger. A4 does not require model calls; none are
   invented.
6. Refuses final admission and analysis.

Stage receipts live in `papers/completion/law_to_action/results/development_qualification/`.

Individual stages:

```bash
/usr/bin/python3.12 papers/completion/law_to_action/benchmark/source_pipeline.py run \
  --split development \
  --out papers/completion/law_to_action/results/development_qualification

/usr/bin/python3.12 papers/completion/law_to_action/benchmark/review_import.py refuse-missing \
  --out papers/completion/law_to_action/results/development_qualification
```

`source_pipeline.py --split final` is refused. Final labels are not inspected.

## Fixture-only routes are not production

| Route | Role | Production? |
| --- | --- | --- |
| `benchmark/run.py` LA-008 trusted fixture harness | measurement-integrity smoke | no |
| Injected UCAN fixture verifiers | mediation contrast | no |
| `InMemoryCapabilityConsumptionStore` | labeled non-durable contrast | no |
| Supervisor `OFF` / `AUDIT` / `SHADOW` | pass-through / observational | no |
| Preselected LA-014 fixed-candidate mapping | comparability qualification | no |
| Selected A4 development command in this task | source-derived handler-boundary qualification | not a scored production run |

The selected development arm is A4 (`full_enforcement`). It is qualification
evidence for the proof/capability/effect-observing boundary. It is not LA-015
scoring and not a closed-loop model study.

## Review import, final admission, analysis

`review_import.py` admits a return only when:

- every frozen selected case is present (60 planned cases / 30 families);
- independent reviewer identity and timestamp are present;
- independent labels exist;
- provenance is not agent- or supervisor-generated;
- blank packet fields are no longer blank.

Otherwise it refuses. Missing reviewers cannot yield a complete review or a
scored fidelity claim.

```bash
/usr/bin/python3.12 papers/completion/law_to_action/benchmark/review_import.py import \
  --returned /path/to/independent_review_return.json \
  --out papers/completion/law_to_action/results/development_qualification

/usr/bin/python3.12 papers/completion/law_to_action/benchmark/qualify_final_runtime.py admit-final
/usr/bin/python3.12 papers/completion/law_to_action/benchmark/qualify_final_runtime.py analyze
```

`admit-final` and `analyze` refuse until independent labels, available runtime
routes, and complete populations exist. They do not score final examples.

## Closed-loop model arm

Closed-loop A4 is declared, unmatched to any pinned scientific model, and
unrun. If selected, the qualifier records an actual unavailable-provider
ledger entry rather than a fixture completion. Paid provider budget is 0.

## After LA-027

When an independent review return exists, re-run `review_import.py import`.
Only a complete import unblocks later scoring tasks (LA-009 / LA-015). Those
tasks must still freeze the same inputs and arm budgets before evaluated
predictions and must not treat fixture harness output as production.
