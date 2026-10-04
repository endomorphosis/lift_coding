# NS-014 native-proof scope decision

Decision: **the named native-proof profile is unavailable for retained results**.

The sealed validation-style profile can execute the checked-in AArch64 `groth16`
CLI's help command, but that is only a capability observation. The executable
does not report a backend version, and no approved deployment/profile record
binds its digest to a source build. The v1/v2 proving and verification-key files
are present but have no retained ceremony/setup origin, verification-key ID,
allowlist, currentness/revocation record, or circuit/profile binding. They are
therefore unapproved artifacts, not usable keys. No setup, proof generation, or
proof verification was attempted.

Consequently there is no genuine proof payload, exact statement, exact public
inputs, verified circuit/profile/key, or measured generation/verification time.
Both timing values are unavailable (`null`), not zero. The executable's help
exit is not a proving or verification measurement.

## Scope retained from source inspection

The inspected adapter is opt-in and delegates to a Rust Groth16 CLI on BN254.
For its `TDFOL_v1` version-2 branch, the Python helper is limited to named
atoms, facts, and one-antecedent implications using forward chaining. This
Horn-style fragment does **not** establish arbitrary CPython or pytest
execution, runner attestation, or full temporal, deontic, or first-order
semantics.

## Table 16 disposition

No adversarial case is reported as successfully exercised end-to-end because
there is no eligible native profile. The required admission dispositions remain
binding if the scope is reopened:

- Changed outer source/test metadata with unchanged proof data: reject unless
  the actual verified public inputs bind those roots.
- A proof of axioms/derivation represented as a Python-test result: reject the
  mismatched evidence class.
- Changed circuit, verification key, profile, or revocation root: re-evaluate;
  never silently reuse.
- A batch omitting a mandatory test: reject completeness even if included leaves
  verify.
- Simulated, auto-generated, seeded/test-only, or unknown-backend artifacts:
  no retained or production credit; record unavailable/experimental only.

## Publication closure and reopening conditions

Table 18's native theorem/circuit row is **untested/unavailable/out of scope**.
The paper may retain only the bounded mechanism description and this limitation;
it must not claim native proof performance, proof-backed execution, test
attestation, deployment readiness, or full temporal/deontic semantics.

Reopen only with a digest-bound, versioned backend; a named circuit build and
precise relation; an approved verification key with setup/ceremony and
revocation provenance; exact statement/public inputs; a genuine proof that
verifies against them; separately measured prove/verify costs; and real
admission-boundary positive/rejection evidence. A Python helper, local pytest
run, CLI help, setup seed, fallback proof, or key-shaped file does not satisfy
those conditions.
