# MCP++ Profile H seller runtime

This package is the shared Python commercial-policy boundary for MCP++ sellers.
It deliberately does not contain wallet keys and does not make payment an
authorization mechanism.

`CapabilityCatalog` and `PaymentPolicyEngine` produce the transport-neutral
`free`, `payment_required`, `paid`, `denied`, and `unavailable` decisions.
`SellerRuntime.dispatch` accepts the private x402 v2 payload only in request
memory, verifies it through a replaceable `CallbackFacilitator` or
`X402SDKAdapter`, durably fences settlement and execution in
`DuckDBPaymentLedger`, and persists only redacted CID-addressed artifacts.

HTTP servers map a result with `http_response`; libp2p dispatchers use
`libp2p_response`. The guarded callback is the side-effect boundary and must be
the direct operation dispatcher, mutation, reservation, or job-admission call.
On restart, call `SellerRuntime.reconcile` before retrying entries reported by
`DuckDBPaymentLedger.pending_reconciliation`. An `executing` entry is never
automatically repeated because its domain effect may already have occurred.

## Three-seller interoperability gate

Run the deterministic, no-value mock-facilitator gate with:

```sh
python scripts/run_mcplusplus_profile_h_interop_gate.py \
  --output swissknife/test-results/mcpplusplus-profile-h-x402/interop.json
```

It invokes the standalone `ipfs_kit`, `ipfs_datasets`, and `ipfs_accelerate`
seller facades through HTTP and libp2p, validates decoded x402 objects and
content-addressed receipts, and records replay/failure/restart Event DAGs.

An operator may opt into an HTTPS testnet facilitator with `--mode testnet
--facilitator-url URL`. Signed authorization bodies must be injected through
the process-only `X402_INTEROP_PAYMENT_PAYLOAD` environment variable. It may
be one JSON object accepted by all six calls, or
`{"payments":{"ipfs-kit:http":{...}, ...}}` with one inner x402 authorization
body per `seller:transport`. The harness never writes these bodies, transaction
references, keys, or signatures to the evidence report. Mainnet is not
supported by this gate.

## Metered `upto` payments

`metering.py` implements the variable-price boundary without floating point
arithmetic. A `MeterUnit` names a base quantity, semantic version, integer
quantum, and `ceil`, `floor`, or `exact` rounding rule. Its CID is included in
the immutable `MeterDefinition`; changing any billing semantic changes the
CID. `DeterministicMeter` verifies a maximum authorization against a configured
buyer public key and creates a seller-signed usage record containing only
measured totals plus commitments to protected input and output content.

`DuckDBEntitlementLedger` issues scoped, expiring quota entitlements and
transactionally consumes each signed usage CID and sequence at most once. It
never converts the unspent authorization into a charge: cancellation and
partial completion report the remaining amount as released. Applications
settle only `UsageResult.actual_charge`, which is proven not to exceed the
signed maximum. Keep fixed-price `exact` catalog entries for work whose usage
cannot be measured reproducibly.

Run the cross-seller XPH-110 gate with:

```sh
python scripts/run_mcplusplus_profile_h_metering_gate.py
```

The default report is
`swissknife/test-results/mcpplusplus-profile-h-x402/metering.json`. Use
`--output` or `--state-dir` to retain evidence and the derived quota index in a
different location. The gate covers storage bytes, rows scanned, and compute
milliseconds along with cancellation, partial work, rounding, exhaustion,
expiry, tamper disputes, maximum rejection, and exact-pricing fallback.

## EVM batch-settlement evaluation

`batch.py` contains the fail-closed deposit and voucher accounting model. A
deposit is testnet-only, bounded by a user-approved maximum, and presented as a
fresh wallet approval with the full amount-at-risk, contract, asset, expiry,
and delayed-withdrawal terms. The transactional voucher ledger signs and
reserves seller-scoped claims, prevents nonce and redemption replay, maintains
solvency across sellers, expires unredeemed claims, blocks unsafe withdrawals,
and reconciles unknown chain outcomes.

Run the XPH-111 evaluation with:

```sh
python scripts/run_mcplusplus_profile_h_batch_gate.py
```

Passing this gate does not enable batching. It produces local invariant
evidence and an explicit `disabled` decision because no deployed testnet
contract or independent security review is supplied. See
`docs/mcplusplus-profile-h-batch-threat-model.md`. `evaluate_batch_enablement`
requires every testnet and review control to be explicitly true and never
enables mainnet.

## Operations and recovery

`operations.py` provides aggregate-only lifecycle counters, portable dashboard
and alert contracts, bounded facilitator and ledger readiness probes, durable
global/per-seller kill switches, and a digest-verified ledger/artifact backup.
Pass the same `RedactedMetrics` and `KillSwitches` instances into
`SellerRuntime` to enforce pause immediately before paid work and emit quote,
verification, settlement, access, and execution outcomes. Entitlement, refund,
and reconciliation handlers use the same fixed-stage `observe` API.

The switches stop new spend and execution without disabling health, receipts,
backup, reconciliation, or refund handling. See
`docs/mcplusplus-profile-h-incident-recovery.md` and run:

```sh
python scripts/run_mcplusplus_profile_h_ops_gate.py
```
