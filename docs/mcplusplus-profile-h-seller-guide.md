# MCP++ Profile H seller guide

Profile H puts a commercial condition around an MCP++ operation; it never
replaces authentication, Profile C delegation, Profile D policy, tenant,
license, privacy, or safety checks. This implementation is testnet-ready only.

## Testnet seller configuration

1. Provision a Base Sepolia receiving account in the deployment key manager and
   register only its alias (`profile-h-seller-base-sepolia`) with the service.
   The seller runtime does not accept raw signing keys.
2. Copy [`seller.testnet.example.json`](../config/mcplusplus-profile-h/seller.testnet.example.json)
   and [`pricing.testnet.example.json`](../config/mcplusplus-profile-h/pricing.testnet.example.json).
   Replace `.invalid` endpoints, DID, account/asset aliases, and protected
   operations. Keep HTTPS facilitator host allowlisting and a durable ledger.
3. Build `PaymentRequirement`, `PaidCapability`, and `CapabilityCatalog` from
   the validated catalog. Construct `PaymentPolicyEngine`,
   `DuckDBPaymentLedger`, `ArtifactStore`, a `CallbackFacilitator` or
   `X402SDKAdapter`, and `SellerRuntime`. Pass the real operation dispatcher as
   the `effect` callback so the durable settlement/execution claim is adjacent
   to the side effect.
4. Map `SellerResult` with `http_response` or `libp2p_response`. Start with one
   read-only `exact` operation. Run reconciliation before admitting paid work
   after restart, then check `runtime.diagnostics()`.

`amount`, maxima, quantities, and prices are canonical integer strings in the
asset's atomic unit—never floating point. An `upto` meter also pins its unit,
semantic version, quantum, rounding rule, and price; settlement uses the signed
reproducible usage record and can never exceed the buyer maximum. Use `exact`
when work cannot be measured reproducibly. The sample `batch` entry is disabled
because the batch gate proves local invariants but no deployed contract and
independent security approval exist.

## API behavior

An unpaid HTTP request returns status 402 and a base64 canonical JSON
`PAYMENT-REQUIRED` header containing `x402Version: 2` and `accepts`. The
Profile H extension binds `quoteCid` and `requestCid`. The paid retry carries
`PAYMENT-SIGNATURE`; a successful response carries `PAYMENT-RESPONSE`. Never
log these private headers. Public artifacts store commitments and CIDs only.

The transport-neutral decision set is `free`, `payment_required`, `paid`,
`denied`, and `unavailable`. An unlisted operation is free only when explicitly
configured that way. Invalid or expired payment, mismatched requirements,
denied domain policy, emergency pause, or uncertain settlement must reach no
side effect. Replays return stable receipts and never settle or execute twice.

## Seller checks

```sh
pytest -q tests/mcplusplus_profile_h/test_seller_runtime.py tests/mcplusplus_profile_h/test_payment_ledger.py
python scripts/run_mcplusplus_profile_h_interop_gate.py --output swissknife/test-results/mcpplusplus-profile-h-x402/interop.json
python scripts/run_mcplusplus_profile_h_metering_gate.py
```

Use `--mode testnet --facilitator-url https://…` only with generated testnet
accounts. The interoperability harness accepts process-only authorization input
and deliberately redacts it from evidence. Mock mode transfers no value.

