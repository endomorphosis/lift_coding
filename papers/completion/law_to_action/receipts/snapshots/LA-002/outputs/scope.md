# LA-002 scope decision

This decision selects the smallest credible paper contribution: a bounded, sandboxed test of whether a generated-code effect, correlated with a reviewed security/intent constraint, is mediated at the actual delegate boundary. It is not an evaluation of legal interpretation, all listed logics, a trained normalizer, distributed storage, peer availability, or a general theorem of agent safety.

## Selected contribution and routes

The central question is: under explicit `ENFORCE` configuration, does an invalid or mismatched context-bound admission prevent a deliberately instrumented sandbox handler from performing its declared forbidden mutation, while a matched admitted case can still perform useful permitted work?

The protected route is deliberately narrow:

1. `SupervisorPreInvocationEnforcement.authorize_and_delegate` in `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py` is the only enforced delegate boundary. The benchmark must call it immediately around one benchmark-owned sandbox mutation handler and count handler calls/effects.
2. `map_code_security_requests` and `correlate_security_requests` in `cve_security_gate.py` supply the separately retained generated-code-effect correlation input. The benchmark must not treat a model assertion or an Intent label as an independently observed code effect.

The experiment must instantiate `ENFORCE` explicitly, inject roots, clock, issuer/service and a durable consumption store if replay/single-use is claimed. No existing caller has been qualified as complete mediation. `ExecutionPermit`, MCP dispatch, Quack/DuckDB state, remote handlers, and arbitrary supervisor routes are not selected protected routes.

## Non-negotiable limitations

The source default is `OFF`; in that mode `authorize_and_delegate` passes through without receipt verification or consumption. Its default consumption store is `InMemoryCapabilityConsumptionStore`, so it does not support restart-safe or cross-worker replay claims. `AUDIT` and `SHADOW` are non-blocking observational modes, not enforcement.

Existing CVE e2e, admissibility benchmark, and MCP dispatch tests are fixture/hermetic surfaces. In particular, the CVE live smoke requires explicit opt-in and exact hub revision, manifest hash, and release-root variables; no such pins were supplied or run. The MCP dispatch test injects fake verifier/policy providers and a deliberately fake bearer token. These tests are useful conformance scaffolding only.

## Essential next experiments

- LA-003: freeze the fixed-action protocol, source lineage splits, bounded sandbox handler, effect-counter semantics, arms, seeds, and stopping rules before results.
- LA-006: pin genuine vulnerable/fixed/unrelated CVE cases and independently review effect mappings.
- LA-008: establish the selected handler’s only mutation route and configure the gate at that route.
- LA-010: qualify one selected fragment/backend with a real executable and retained translation/receipt, or report the authoritative-environment dependency gap.
- LA-015: run allowed, forbidden, replayed, forged/missing receipt, and changed actor/audience/arguments/effects/roots/clock cases. Report forbidden effects, useful permitted work, false denials, unknowns, and every timeout/failure.
- LA-012: before claiming single-use across restart or worker boundaries, qualify a durable consumption adapter with concurrency and restart failure injection.

## Explicitly optional or outside this paper’s core

Legal corpus fidelity needs real licensed source records and expert review; it is not a substitute for the selected runtime route. The trained SkillCenter normalizer/encoder has no pinned weights, training provenance, or held-out evaluation and is excluded. The registry’s other logic families, QF_LIA interpolation, kernel proof claims, peer availability, live UCAN cryptography, network transport parity, DuckDB owner recovery, semantic refactoring/sealing, learned residuals, and closed-loop agent studies are separate follow-ups. They must remain unrun/future work unless later tasks acquire direct evidence.

The manuscript should therefore describe this work as a bounded generated-code-effect mediation evaluation, not as universal safety or an end-to-end empirical result, until the planned raw evidence exists.
