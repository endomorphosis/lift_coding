# LA-010 solver and checker qualification

This record qualifies one bounded proof-oriented route in the
authoritative validation environment and scopes every other paper
family without inventing results.

## Selected route

The benchmark-required proof-oriented route for generated-code effect
invariants is a **QF_BOOL / propositional SAT** encoding of a Hoare-style
security invariant (`matching_roots ∧ grant → ¬forbidden_effect`).
The provider is SymPy's DPLL SAT solver, executed as a child process.
The independent checker enumerates all assignments and does not share
the DPLL implementation. Both emit `satisfiability` authority only.

- Provider: `sympy.logic.inference.satisfiable` 1.12
- Checker: `enumerate-all-assignments`
- Fragment: `QF_BOOL`
- Kernel reconstruction: not selected and not available
- Closed-profile theorem allow: **not authorized** by this route

## Authoritative environment

- Python: `/usr/bin/python3.12`
- PATH: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
- HOME prefix: `ipfs-accelerate-validation-home-`
- User-profile toolchains (`~/.elan`, `~/.local`, theorem-provers/bin) were not searched and are not admitted.

## Cases executed on the selected route

| Job | Case | Provider | Checker | Authority |
| --- | --- | --- | --- | --- |
| `sat-success-unsat` | success | unsat | unsat | satisfiability |
| `sat-counterexample` | counterexample | sat | sat | satisfiability |
| `sat-timeout` | timeout | timeout | not-run | unavailable |
| `sat-unsupported-quantifiers` | unsupported | unsupported | unsupported | unsupported |
| `sat-unsupported-qflia-interpolation` | unsupported | unsupported | unsupported | unsupported |
| `sat-forged-model` | forged-evidence | sat | sat | satisfiability |

## Authority checks

Authorization proof jobs composed by `AuthorizationQueryComposer@1`
require `theorem_proof`. SAT, policy, simulation, and monitor paths
cannot allow.

- `ResultAuthority(satisfiability).require(theorem_proof)` raised: `satisfiability authority cannot be used as theorem_proof`
- Portfolio maps UNSAT under SAT authority to `sat_only`
- Simulated theorem maps to `simulation`
- Policy approval maps to `policy`
- `select_job_result` on a SAT-only attempt claiming PROVED yields `sat_only` / `sat_only`
- Closed-profile decisions for SAT-only, policy, simulated, monitor, and unavailable kernel: none allowed (`no_decision_allowed=True`)

## Families

| Family | Status | Authority | Invented results |
| --- | --- | --- | --- |
| `qf_bool_sympy_sat` | qualified | satisfiability | False |
| `z3_smt` | unavailable | satisfiability | False |
| `cvc5_smt` | unavailable | satisfiability | False |
| `cvc5_qflia_interpolation` | not_selected_unavailable | satisfiability | False |
| `vampire_fol` | unavailable | theorem_proof | False |
| `eprover_fol` | unavailable | theorem_proof | False |
| `lean_kernel` | unavailable | theorem_proof | False |
| `coq_rocq_kernel` | unavailable | theorem_proof | False |
| `isabelle_kernel` | unavailable | theorem_proof | False |
| `runtime_monitor` | not_selected | runtime_monitor | False |
| `policy_approval` | not_selected | policy_approval | False |

## Claim limits

- This is qualification evidence, not a scored A4 benchmark run.
- SAT UNSAT is not a kernel theorem and does not authorize closed-profile allow.
- Z3, cvc5, Vampire, E, Lean, Coq/Rocq, and Isabelle were absent from the sealed PATH; no host-profile binary was adopted.
- QF_LIA interpolation was not selected and was not executed.
- No learned hammer, no remote solver, and no digest-bound native SMT deployment was available under the authoritative PATH.
