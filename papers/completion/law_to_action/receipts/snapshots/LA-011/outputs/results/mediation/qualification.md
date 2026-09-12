# LA-011 complete mediation, strict capabilities, and exact live context

This record qualifies named authorization routes under the sealed
validation PATH. It is **not** a scored A3 or A4 benchmark.

## Selected safety claim

The only route included in the tested safety claim is
`SupervisorPreInvocationEnforcement.authorize_and_delegate` in explicit
`ENFORCE` mode around the benchmark-owned `BoundedExportHandler.export_json`
mutation. Independent filesystem-journal effect counters are retained.

- Mode: `enforce` (not the source default `off`)
- Clock, roots, and receipt issuer: injected and pinned
- Consumption store: process-local `InMemoryCapabilityConsumptionStore` (restart safety is LA-012)
- Unprotected, observational, and nonidentical routes were tested and **excluded**

## Authoritative environment

- Python: `/usr/bin/python3.12` 3.12.3
- PATH: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
- HOME prefix required: `ipfs-accelerate-validation-home-` (observed=False)
- Ed25519 provider: cryptography 41.0.7 (`HAVE_CRYPTO_ED25519=True`)
- Canonical Profile D evaluator: unavailable (`multiformats` missing)
- MCPServer import: unavailable (`anyio` missing); AuthorizationGate was executed directly

## Paper-named routes and claim inclusion

| Route | Protection | In safety claim | allow | deny | unknown | context-mutation |
| --- | --- | --- | --- | --- | --- | --- |
| `supervisor_pre_invocation_enforce` | protected | True | 1 | 2 | 2 | 9 |
| `supervisor_pre_invocation_off` | pass_through | False | 1 | 1 | 1 | 1 |
| `supervisor_pre_invocation_audit` | observational | False | 1 | 1 | 1 | 1 |
| `supervisor_pre_invocation_shadow` | observational | False | 1 | 1 | 1 | 1 |
| `execution_permit` | related_nonidentical | False | 1 | 1 | 1 | 3 |
| `ucan_gated_mcp_authorization_gate` | protected_but_not_selected | False | 3 | 1 | 2 | 9 |
| `profile_d_lightweight_dispatcher` | compatibility_bypass | False | 1 | 1 | 1 | 1 |
| `direct_bounded_export_handler` | unprotected | False | 1 | 1 | 1 | 1 |
| `proof_ucan_binding_adapter` | uncomposed | False | 0 | 0 | 0 | 1 |

## Selected ENFORCE cases

Selected claim cases: 14/14 passed.

| Job | Kind | Mutation | Decision | Effects | Pass |
| --- | --- | --- | --- | --- | --- |
| `enforce-allow` | allow | none | allow | 1/1 | True |
| `enforce-replay` | deny | replay | deny | 0/0 | True |
| `enforce-deny` | deny | deny-receipt | deny | 0/0 | True |
| `enforce-unknown-indeterminate` | unknown | missing-evidence-indeterminate | unknown | 0/0 | True |
| `enforce-wrong-audience` | context_mutation | wrong-audience | deny | 0/0 | True |
| `enforce-wrong-actor` | context_mutation | wrong-actor | deny | 0/0 | True |
| `enforce-changed-args` | context_mutation | changed-arguments | deny | 0/0 | True |
| `enforce-undeclared-code-effect` | context_mutation | undeclared-generated-code-effect | deny | 0/0 | True |
| `enforce-environment-changed` | context_mutation | changed-live-environment | deny | 0/0 | True |
| `enforce-root-changed` | context_mutation | changed-roots | deny | 0/0 | True |
| `enforce-expired` | context_mutation | expired-capability | deny | 0/0 | True |
| `enforce-missing-receipt` | unknown | missing-receipt | deny | 0/0 | True |
| `enforce-tenant-ab-resource` | context_mutation | tenant-a-versus-tenant-ab | deny | 0/0 | True |
| `enforce-forged-proof-id` | context_mutation | forged-proof-identifiers | deny | 0/0 | True |

## Real cryptographic verification

Real Ed25519 UCAN jobs executed: 14.
Tokens were issued with `cryptography` Ed25519 and verified by `UCANVerifier`
against a durable `RevocationLedger`. Injected verifiers are labeled fixtures.

| Job | Mutation | Crypto | Decision | Effects | Pass |
| --- | --- | --- | --- | --- | --- |
| `gate-allow-real-ucan-fixture-policy` | none | real-ed25519 | allow | 1 | True |
| `gate-canonical-profile-d-unavailable` | canonical-profile-d-unavailable | real-ed25519 | deny | 0 | True |
| `gate-wrong-audience` | wrong-audience | real-ed25519 | deny | 0 | True |
| `gate-tenant-ab-widening` | tenant-a-versus-tenant-ab | real-ed25519 | deny | 0 | True |
| `gate-expired` | expired-token | real-ed25519 | deny | 0 | True |
| `gate-revoked` | revoked-token | real-ed25519 | deny | 0 | True |
| `gate-forged-signature` | forged-proof-identifiers | real-ed25519 | deny | 0 | True |
| `gate-forged-untrusted-key` | untrusted-private-key | real-ed25519 | deny | 0 | True |
| `gate-replay` | replay | real-ed25519 | deny | 0 | True |
| `gate-missing-ucan` | missing-ucan | real-ed25519 | deny | 0 | True |
| `gate-allow-with-obligations-denied` | unresolved-obligations | real-ed25519 | deny | 0 | True |
| `gate-changed-resource-args` | changed-args-resource | real-ed25519 | deny | 0 | True |
| `gate-attenuated-chain-allow` | none-attenuated-chain | real-ed25519 | allow | 1 | True |
| `gate-child-widens-to-tenant-ab` | tenant-a-versus-tenant-ab-attenuation | real-ed25519 | deny | 0 | True |

## Fixture verifiers (not live crypto)

- `gate-fixture-verifier-labeled`: `fixture-ucan-verifier` labeled `fixture-verifier`; in_safety_claim=False.

## Failures and limitations recorded

- No case-level assertion failures. Dependency gaps remain as recorded limitations.

- Canonical `ipfs_datasets_py` Profile D evaluator is unavailable without `multiformats`.
- `MCPServer` cannot be constructed without `anyio`; `tools/call` was exercised at `AuthorizationGate`.
- Proof-derived `AuthorizationCapability` and signed UCAN are not composed at one production entry point.
- Default `OFF` / `AUDIT` / `SHADOW` still produce handler effects and are outside the safety claim.
- Direct `BoundedExportHandler.execute` is an unprotected reachable mutation and is outside the safety claim.
- Durable consumption and restart safety are LA-012, not claimed here.
- This is qualification evidence, not a scored A3/A4 forbidden-effect rate.
