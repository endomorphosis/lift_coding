# NS-009 Translation preservation and retained symbolic checker admission

Generated at 2026-09-12T02:34:50+00:00. This is a sealed-profile qualification record, not a live A–D experiment and not a kernel proof of arbitrary Python.

## Profile

- Translation contract: `logic_translation_validation.validate_translation`
- Converter: `TDFOLToFOLConverter` / `tdfol_to_fol`
- Caller admission: `SupervisorLogicPlatformReceiptAdmission@1` (`admit_receipt`)
- Solver readiness: `probe_solver_readiness`
- Retained TDFOL checker: `TDFOLProver.prove` (non-kernel)
- Located CEGAR: `ipa.refine_spurious_paths`
- Finite-trace evaluator: `formal_logic_vocabulary.evaluate_formula` (plan-check only)
- Policy: `ns-009-logic-qualification-v1`

## Environment

- Interpreter: `/usr/bin/python3.12` (3.12.3)
- Sealed `PATH` at process start: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
- pytest: `8.1.1`
- z3 module: `False`
- binaries: `{"coqc": null, "cvc5": null, "lean": null, "souffle": null, "z3": null}`

## Coverage

- Result rows: 32
- Declared cases: 32
- Failed rows: 0
- Exact translation progress: `True`
- Modal-erasure source claim admitted: `False` (must be false)
- Z3 supported: `False`
- IPA CEGAR useful progress: `True`
- Interpolant located: `False`

## Valid supported translations can progress

An exact FOL atom with matching source/target inventories is conformant and `promotion_allowed` at `solver_checked` translation assurance. The caller `admit_receipt` records that translation under a non-conclusive solver-result envelope bound to the exact formula root, theory, solver identity, and environment. The same envelope cannot complete a kernel-required source claim: `solver_result` plus `proved` is rejected.

## Unjustified lifting is rejected

`TDFOLToFOLConverter` maps `O(Done)` and `Done` to the same FOL atom, and maps `p U q` to `p ∧ q`. Exact translation contracts that drop modal operators or bounds are quarantined (`dropped_modal_operator`). Finite-trace evaluation of reviewed `SAFETY(p)` is false on a trace where `p` holds only at step 0, so a target proof of `p` does not establish `□p`. Conservative approximations with a declared modal-erasure log progress only at `candidate` assurance and still cannot lift to kernel completion.

## Caller receipts bind formula, source, theory, solver, and environment

Every retained translation row records `formula_root`, source/target forms, contract/artifact identities, solver id, and `environment_id`. Stale formula roots (`source_identity_mismatch`), stale fingerprints, fixture-set mismatches, and colliding named assertion IDs fail closed. Unvalidated solver results cannot satisfy kernel reconstruction.

## Vacuity, unknown, unsupported, and budget exhaustion are distinct

| class | case | meaning |
|---|---|---|
| proved (non-kernel) | `tdfol_axiom_proved_non_kernel` | TDFOL axiom lookup; not kernel proof |
| unknown | `unknown_not_proved` | Forward chaining exhausted |
| timeout | `timeout_budget_exhausted` | `timeout_ms=0` |
| unsupported | `unsupported_clause_uncovered` | Obligation has no finite-trace semantics |
| vacuous | `vacuity_unsat_guarantee` | Unsatisfiable G makes G⇒A true; rejected as proof |
| unavailable | `sat_smt_unavailable` / `unsat_smt_unavailable` | Z3 absent; SMT SAT/UNSAT not simulated |

## CEGAR, interpolants, and composition

IPA `refine_spurious_paths` is located and exercised: a spurious finding is refined away and a corpus seed is not. The draft's named QF_LIA interpolating CEGAR adapter, interpolant checker, `CompositionEdge`, cyclic assume-guarantee closure, and incremental SMT wrapper were not located as those mechanisms. They are recorded as unavailable/specification-only. No interpolant, SMT SAT/UNSAT, or composition-edge discharge was simulated.

## Solver versus reconstruction versus kernel

`probe_solver_readiness` marks Z3 `unsupported` and never sets `proof_success`. Discoverable TDFOL/DCEC/CEC/hammer surfaces remain non-authoritative until kernel reconstruction. Assertion identity checks are replay, not retained solver-state incrementality. No retained-clause speedup is established.

## Limitations

- Qualification uses reviewed atoms, TDFOL converter examples, and IPA findings; it is not a historical repair task.
- Finite-trace evaluation is a bounded plan-check artifact and is not a proof of Python programs.
- SMT G∧¬A SAT/UNSAT cannot be obtained in the sealed profile because Z3 is absent.
- This receipt is Table 18 loss-aware formal translation qualification, not a matched A–D outcome.

## Case outcomes

| case_id | family | polarity | status | useful_progress | source_claim_admitted | reason |
|---|---|---|---|---|---|---|
| `exact_atom_supported_progress` | translation | valid | pass | true | false | `exact_translation_conformant` |
| `modal_erasure_obligation_lift` | lossy_projection | invalid | pass | false | false | `dropped_modal_operator` |
| `temporal_erasure_always_lift` | lossy_projection | invalid | pass | false | false | `dropped_modal_operator` |
| `until_conjunction_lossy_projection` | lossy_projection | invalid | pass | false | false | `until_approximated_by_conjunction` |
| `declared_conservative_modal_progress` | translation | valid | pass | true | false | `conservative_candidate_only` |
| `heuristic_cannot_prove` | translation | invalid | pass | false | false | `translation_class_heuristic` |
| `undeclared_abstraction_quarantine` | translation | invalid | pass | false | false | `undeclared_abstraction` |
| `bounded_abstraction_progress` | translation | valid | pass | true | false | `bounded_abstraction_conformant` |
| `missing_finite_bounds` | translation | invalid | pass | false | false | `missing_finite_bounds` |
| `fixture_set_mismatch` | binding | invalid | pass | false | false | `fixture_set_mismatch` |
| `stale_formula_root` | binding | invalid | pass | false | false | `source_identity_mismatch` |
| `duplicate_named_assertions` | binding | invalid | pass | false | false | `duplicate_named_assertion_id` |
| `unsupported_clause_uncovered` | solver_outcome | diagnostic | pass | false | false | `unsupported_not_proof` |
| `opaque_clause_uncovered` | solver_outcome | diagnostic | pass | false | false | `opaque_clause_uncovered` |
| `solver_readiness_z3_unavailable` | solver_outcome | diagnostic | pass | false | false | `backend_unavailable` |
| `tdfol_axiom_proved_non_kernel` | solver_outcome | valid | pass | true | false | `tdfol_axiom_lookup_non_kernel` |
| `unknown_not_proved` | solver_outcome | diagnostic | pass | false | false | `unknown` |
| `timeout_budget_exhausted` | solver_outcome | diagnostic | pass | false | false | `timeout` |
| `vacuity_unsat_guarantee` | composition | invalid | pass | false | false | `vacuous_implication_not_proof` |
| `reachability_gap` | composition | diagnostic | pass | false | false | `unreachable_assumption` |
| `unvalidated_solver_result_rejected` | binding | invalid | pass | false | false | `evidence_kind_does_not_support_verdict` |
| `sat_smt_unavailable` | solver_outcome | diagnostic | pass | false | false | `smt_sat_unavailable` |
| `unsat_smt_unavailable` | solver_outcome | diagnostic | pass | false | false | `smt_unsat_unavailable` |
| `stale_solver_fingerprint` | binding | invalid | pass | false | false | `stale_solver_fingerprint` |
| `cegar_ipa_spurious_refine` | cegar | valid | pass | true | false | `ipa_spurious_path_refined` |
| `cegar_qf_lia_adapter_unlocated` | cegar | diagnostic | pass | false | false | `qf_lia_cegar_adapter_unlocated` |
| `interpolant_mechanism_unavailable` | interpolant | diagnostic | pass | false | false | `interpolant_checker_unlocated` |
| `invalid_interpolant_not_admitted` | interpolant | invalid | pass | false | false | `invalid_interpolant_not_admitted` |
| `composition_edge_unlocated` | composition | diagnostic | pass | false | false | `composition_edge_unlocated` |
| `cyclic_composition_unlocated` | composition | diagnostic | pass | false | false | `cyclic_closure_checker_unlocated` |
| `incremental_smt_wrapper_unlocated` | solver_outcome | diagnostic | pass | false | false | `incremental_smt_wrapper_unlocated` |
| `kernel_vs_solver_evidence_classes` | evidence_class | diagnostic | pass | false | false | `solver_unsat_is_not_kernel_proof` |
