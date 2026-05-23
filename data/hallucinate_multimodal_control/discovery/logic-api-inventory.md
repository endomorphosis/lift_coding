# HAO-004 Logic API Inventory

Audit date: 2026-05-23

Audited dependency: `external/ipfs_datasets` at gitlink `c68759c211f4a46ea22d34aa05e2679ddc5b2e34`.

Primary import surface:

```python
from ipfs_datasets_py.logic import api
```

`ipfs_datasets_py.logic.api` is the only public logic-module import surface that
Hallucinate App should depend on at runtime for natural-language policy
compilation and policy evaluation. Direct imports from `logic.CEC.*` and
`processors.legal_data.reasoner.*` are useful for feature probes and later IR
design, but they should be wrapped by Hallucinate-owned adapters before runtime
use.

## Required API Contract

| Symbol | Import path | Observed signature | Runtime contract |
| --- | --- | --- | --- |
| `compile_nl_to_policy` | `ipfs_datasets_py.logic.api.compile_nl_to_policy` | `(text: str, **kw) -> Any` | Lazy wrapper around `logic.CEC.nl.nl_to_policy_compiler.compile_nl_to_policy(sentences: List[str], policy_id=None, default_actor=None, valid_until=None)`. In this checkout the operationally safe input is `list[str]`, not a bare string. Returns `CompilationResult` with `success`, `policy`, `clauses`, `dcec_formulas`, `errors`, `warnings`, and `metadata`. |
| `evaluate_nl_policy` | `ipfs_datasets_py.logic.api.evaluate_nl_policy` | `(nl_text: str, *, tool: str, actor: Optional[str] = None, **kw) -> Any` | One-shot compile and evaluate wrapper around `logic.integration.ucan_policy_bridge.compile_and_evaluate`. Returns `BridgeEvaluationResult` with `decision`, `policy_cid`, `reason`, `ucan_allowed`, and `revoked`. In this checkout, sampled calls fail closed with `decision="deny"` because `UCANPolicyBridge.evaluate` passes `at_time` to `PolicyEvaluator.evaluate`, whose current parameter is `now`. |
| `NLUCANPolicyCompiler` | `ipfs_datasets_py.logic.api.NLUCANPolicyCompiler` | `(policy_id=None, issuer_did="did:key:root", default_actor=None, valid_until=None, strict=False)` | Lazy class export. `compile(sentences: List[str], policy_id=None)` returns `NLUCANCompilerResult` with policy result, bridge result, delegation evaluator, errors, warnings, and metadata. `compile_explain` and `compile_explain_iter` provide explanation text. |
| `evaluate_with_manager` | `ipfs_datasets_py.logic.api.evaluate_with_manager` | `(policy_cid: str, tool: str, *, actor=None, leaf_cid=None, at_time=None, manager=None, audit_log=None) -> Optional[Any]` | Module-level wrapper around `UCANPolicyBridge.evaluate_audited_with_manager`. Returns `BridgeEvaluationResult` when the bridge is available. Returns `None` when the bridge import or expected bridge method is unavailable. Evaluation errors are represented as deny decisions where possible. |

## Optional Public Exports

The current checkout exposes the following optional symbols through `api.__all__`
when their imports succeed:

| Symbol group | Current status | Contract for Hallucinate App |
| --- | --- | --- |
| NL -> UCAN pipeline: `NLToDCECCompiler`, `DCECToUCANBridge`, `GrammarNLPolicyCompiler`, `NLUCANPolicyCompiler`, `UCANPolicyBridge`, `SignedPolicyResult`, `BridgeCompileResult`, `BridgeEvaluationResult` | Available through `api.__getattr__`; `_lazy_nl_ucan()` returns these symbols in this checkout. | Feature-probe with `hasattr(api, name)` or guarded attribute access. Treat `AttributeError` as "general compiler unavailable". |
| Delegation manager: `DelegationManager`, `get_delegation_manager` | Available in this checkout; `api._BW133_DELEGATION_AVAILABLE` is `True`. | Optional. Use only when the runtime has a delegation manager and leaf token CIDs. Absence must not prevent strict-template policy checks. |
| Conflict detection: `NLPolicyConflictDetector`, `PolicyConflict`, `detect_conflicts` | Available in this checkout; `api._BW133_CONFLICT_AVAILABLE` is `True`. | Run after successful compilation when clauses are present. Conflicts should force clarification or deny-over-permit handling before policy activation. |
| I18N conflict helpers: `detect_i18n_conflicts`, `I18NConflictResult`, `detect_i18n_clauses`, `I18NConflictReport`, `detect_all_languages` | Available in this checkout; `api._CD140_I18N_AVAILABLE` is `True`. `detect_all_languages` remains present and returns empty language buckets if detector imports fail. | Optional authoring-time diagnostics only. Do not gate runtime invocation on these helpers. |
| Explanation helper: `compile_explain_iter` | Present. Lazily imports `NLUCANPolicyCompiler` when called. | Optional authoring UI helper. Catch `ImportError` and `AttributeError`. |
| Signing helper: `build_signed_delegation` | Present and async. | Optional. If DID signing dependencies are absent, compile can still produce unsigned/stub delegation artifacts; signed UCAN output is not required for local control-surface mediation. |

## Logic Helper Inventory

These helpers imported cleanly during the audit, but they are not the primary
runtime API surface.

| Area | Import path | Observed symbols | HAO usage boundary |
| --- | --- | --- | --- |
| `event_calculus` | `ipfs_datasets_py.logic.CEC.native.event_calculus` | `Event(name, parameters=())`, `Fluent(name, parameters=())`, `TimePoint(value)`, `EventCalculus()` | Good semantic reference for `Happens`, `Initiates`, `Terminates`, `HoldsAt`, and `Clipped`. Hallucinate App should model its own context facts first and only use this module behind a guarded adapter. |
| `deontic` primitives | `ipfs_datasets_py.logic.api` and `hybrid_legal_ir` | `DeonticConverter`, `DeonticOperator`, `DeonticFormula`, `DeonticRuleSet`, `DeonticOp`, `Norm` | Stable enough as terminology and compile target. Runtime decisions still map to Hallucinate outcomes such as `allow`, `deny`, `require_confirmation`, `defer`, `rewrite`, `fallback_surface`, and `rate_limit`. |
| `flogic` / frame logic | `ipfs_datasets_py.processors.legal_data.reasoner.hybrid_legal_ir` | `ActionFrame`, `EventFrame`, `StateFrame`, `TemporalConstraint`, `Norm`, `LegalIR`, `compile_to_dcec`, `compile_to_temporal_deontic_fol` | There is no audited public `ipfs_datasets_py.logic.flogic` module. Use `hybrid_legal_ir` as the frame-first reference, but define Hallucinate-owned frame facts in HAO-005 to avoid leaking UI terms into legal-domain modules. |

## Observed Failure Modes

- Importing `ipfs_datasets_py.logic.api` is intended to be lightweight and
  optional-dependency tolerant, but core converter imports are still eager.
  Hallucinate App must wrap the initial import and disable the general compiler
  lane if the import fails.
- `compile_nl_to_policy` raises `ImportError` when the NL -> UCAN pipeline
  cannot be imported. Otherwise parse failures usually return
  `CompilationResult(success=False)` with populated `errors` instead of raising.
- Passing a bare string to `compile_nl_to_policy` currently iterates over the
  string as individual characters through the underlying list-oriented compiler.
  The result is `success=False` with many per-character errors and warnings.
  The adapter must pass `list[str]`.
- `evaluate_nl_policy` can raise `ImportError` if
  `logic.integration.ucan_policy_bridge` is unavailable. When the bridge is
  available, policy or evaluator errors are returned as
  `BridgeEvaluationResult(decision="deny", reason=...)`.
- In this checkout, `evaluate_nl_policy` and `evaluate_with_manager` sampled
  through the bridge fail closed with a reason containing
  `PolicyEvaluator.evaluate() got an unexpected keyword argument 'at_time'`.
  Treat this as an upstream compatibility issue and do not authorize runtime
  invocation based on these wrappers until an adapter test proves an `allow`
  decision.
- `evaluate_with_manager` returns `None` when the bridge module or expected
  method is unavailable. `None` is not a soft allow.
- Unknown policy CIDs evaluate to deny through `PolicyEvaluator`.
- Conflict detection helpers are optional. If unavailable, the adapter must
  still enforce deterministic deny-over-permit precedence in Hallucinate-owned
  policy IR.
- `event_calculus` rejects negative time values through `ValidationError`.
  Temporal context extraction should validate time windows before invoking any
  optional event-calculus helper.

## Pinned Fallback Strategy

1. Capability probe once at startup:
   `from ipfs_datasets_py.logic import api`, then require
   `compile_nl_to_policy`, `evaluate_nl_policy`, `NLUCANPolicyCompiler`, and
   `evaluate_with_manager` to exist before enabling the general compiler lane.
2. Keep strict deterministic templates as Lane A. These templates must not
   depend on `ipfs_datasets_py` and must cover common control-surface rules such
   as quiet-hours gesture suppression and confirmation before method execution.
3. Use the `ipfs_datasets_py` Lane B only for freeform rules. Pass
   `list[str]` to `compile_nl_to_policy` or `NLUCANPolicyCompiler.compile`.
   Accept a compile only when `success` is true and policy clauses or a policy
   object are present.
4. Preserve `errors`, `warnings`, `metadata`, and explanation text in the policy
   bundle. Low coverage, empty clauses, import failure, or compiler exceptions
   produce clarification, not silent allow.
5. Run `detect_conflicts` when available. If a permission and prohibition both
   match the same actor/action/resource, activate deny-over-permit behavior and
   surface the conflict to the operator before enabling the policy.
6. Runtime evaluation fails closed. `None`, exceptions, empty policy CIDs,
   unknown policy CIDs, and `BridgeEvaluationResult(decision="deny")` all block
   autonomous or destructive invocation. For low-risk human-initiated actions,
   the mediation layer may return `require_confirmation` instead of `deny`.
7. Do not import `event_calculus`, deontic internals, or `flogic`/frame-logic
   helpers directly from surface adapters. HAO-005 should introduce a
   Hallucinate-owned IR and only then add guarded conversion adapters to these
   optional upstream helpers.

## Validation Evidence

The required symbol probe passed against the populated dependency checkout:

```bash
PYTHONPATH=external/ipfs_datasets python3 -c "exec(\"from ipfs_datasets_py.logic import api\\nrequired = ['compile_nl_to_policy', 'evaluate_nl_policy', 'NLUCANPolicyCompiler', 'evaluate_with_manager']\\nmissing = [name for name in required if not hasattr(api, name)]\\nassert not missing, missing\")"
```

Additional introspection observed:

- `api.__all__` contains 115 names in this checkout.
- `compile_nl_to_policy(["Alice must not delete records"], ...)` returns
  `CompilationResult(success=True)` with one clause.
- `compile_nl_to_policy("Alice must not delete records", ...)` returns
  `CompilationResult(success=False)` because the underlying compiler expects a
  list of sentences.
- `evaluate_nl_policy(...)` and `evaluate_with_manager(...)` return deny results
  in the sampled path because of the `at_time` versus `now` evaluator mismatch.
