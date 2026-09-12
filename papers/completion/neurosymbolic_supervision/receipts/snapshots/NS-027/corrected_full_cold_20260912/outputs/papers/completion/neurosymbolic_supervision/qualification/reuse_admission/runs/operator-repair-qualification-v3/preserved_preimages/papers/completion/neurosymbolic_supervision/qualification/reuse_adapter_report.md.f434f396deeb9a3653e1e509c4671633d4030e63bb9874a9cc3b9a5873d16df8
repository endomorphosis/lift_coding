# NS-027 Retained-byte reuse admission

Generated at 2026-09-12T09:23:34.702177+00:00. Accepted route: **enforced full-cold removal**.

## Decision

The pinned native proof-cache, certificate-store and completion-validation
modules were executed under the admitted runtime. Unconditional callbacks,
missing verifiers, mismatched verifier authority, NS-011 placeholder
CRYPTOGRAPHIC/AUTHORITATIVE certificates, changed bytes and stale keys all
produced RUN. The native TestCertificateProvider did not authorize skip.
Unsupported cryptographic reuse claims are removed. The paper reuse profile
is not retained.

## Historical NS-010/NS-011

Original receipts remain immutable. All 26 historical attempts, including
the 1/26 observed false reuse and 0/25 selected subset, stay in their
original mocked-verifier scope and are not transferred to production.

## Useful positive

- Task: `ns-hist-01-xmltodict` source `7084494972ac820ecc41625b35fda59f2da1556ea34ab46414696471369cfe63`
- Unchanged baseline nonempty: `True`
- Cold outcome: `pass` with reuse credit `False`

## Runner

C/D/C-no-route cannot take reuse credit. Final admission stays disabled.
NS-027 grants no NS-016 pilot or final-run credit. Bindings are handed to NS-028.

