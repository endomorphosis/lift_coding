# LA-011 isolated mediation changes

This task's allowed edit set is output-only. Production sources
`admissibility_enforcement.py` and `authorization.py` were **not**
modified. Boundary regressions ran against the existing gates.
Failures and dependency gaps remain recorded in `raw.jsonl`.

## Production source edits

None applied. The existing `ENFORCE` adapter already:

- blocks non-allow / unknown / expired / stale-root / context-mismatch receipts
- consumes a one-time token before the delegate
- leaves `OFF` / `AUDIT` / `SHADOW` as documented weaker modes

The existing `AuthorizationGate` already:

- requires envelope / tool / resource / ability / actor bindings
- calls a concrete UCAN verifier and ledger
- fail-closes when the canonical Profile D provider is unavailable
- accepts plain `allow` only (not `allow_with_obligations`)
- rejects `tenant-a/*` covering `tenant-ab` at the UCAN resource-cover check

## Isolated proposed adapters (not applied)

1. **Proof-capability ↔ UCAN binding adapter.** Production
   `authorize_and_delegate` does not invoke `UCANVerifier`, and
   `AuthorizationGate` does not verify `DecisionReceipt`. An isolated
   adapter would deny unless actor, audience, tool/version, arguments
   digest, effects, roots, and remaining use match across both
   objects. Boundary regression:
   `binding-proof-capability-and-ucan-not-composed`.
2. **Canonical Profile D under sealed PATH.** The datasets evaluator
   imports `multiformats`, which is absent. Do not substitute a
   fixture evaluator when claiming A3 scored results. Boundary
   regression: `gate-canonical-profile-d-unavailable` fail-closes.
3. **MCPServer sealed-environment import.** `server.py` imports
   `anyio`, which is absent. Gate tests therefore call
   `AuthorizationGate` directly, which is the `tools/call` check.
4. **Shared ExecutionPermit ledger.** `issuer.verifier()` without an
   injected ledger creates a fresh in-memory ledger. Callers must
   retain one verifier instance for replay. Boundary regression:
   `permit-replay`.
5. **Forged receipt integrity wrap.** `_coerce_receipt` lets
   `DecisionReceipt.from_dict` raise `ReceiptError` instead of
   returning a deny observation. The delegate is still not called.
   An isolated wrap would map that exception to `error`/`deny`.
   Boundary regression: `enforce-forged-proof-id`.

## Boundary regressions executed

Every paper-named route has allow, deny, unknown, and context-mutation
effect-counter cases. Mutations include wrong audience, tenant-a versus
tenant-ab, expiry, revocation, forged signatures/proof identifiers,
changed arguments/effects/environment, missing evidence, undeclared
generated-code effects, and replay.

## Recorded failures

- No applied source patch was required for the selected ENFORCE claim cases.

## Environment pins

- cryptography 41.0.7; HAVE_CRYPTO_ED25519=True
- datasets auth available: True
- canonical Profile D available: False
- anyio: False; multiformats: False
