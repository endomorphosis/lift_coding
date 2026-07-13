# MCP++ Profile H operator guide

This is the deployment checklist for a new testnet seller and SwissKnife buyer.
The approved release state is: `exact` enabled on testnet, bounded `upto`
enabled on testnet, `batch` disabled, and all mainnet modes disabled.

## First testnet rollout

1. Run `python scripts/run_mcplusplus_profile_h_release_gate.py --mode testnet`.
   Continue only on `GO`; retain the generated release packet.
2. Provision seller and buyer accounts through an OS keychain, HSM, hardware
   wallet, or managed wallet provider. Record public aliases and addresses in
   the allowlist. No operator needs to handle or export a raw key.
3. Install the three [testnet examples](../config/mcplusplus-profile-h/), set
   deployment-owned writable ledger/receipt paths, and substitute verified
   Base Sepolia facilitator, asset, seller DID, account aliases, and budgets.
4. Validate the JSON, require `mode=testnet`, HTTPS, CAIP-2 `eip155:84532`,
   x402 v2, durable storage, exact allowlists, `mainnetEnabled=false`, and
   `batchSettlement.enabled=false`. Reject wildcard networks or payees.
5. Start globally paused. Check facilitator and ledger readiness, create an
   encrypted backup, then unpause only one seller and one read-only exact offer.
6. In SwissKnife, leave autopay off. Request and manually approve a small
   generated-account payment. Confirm quote → approval → verification →
   settlement → entitlement → execution lineage and retrieve the receipt.
7. Repeat over HTTP and libp2p, then enable bounded `upto` only after its unit,
   rounding, maximum, signed usage, cancellation, and unused-value behavior are
   reviewed. Never enable batch from the example.

## Day-two operations

Watch only aggregate/redacted quote, verify, settlement, entitlement, access,
and execution metrics. Alert on facilitator/ledger readiness, error ratios,
reconciliation age, or divergence. Never put payloads, signatures, transaction
references, protected data, or wallet material in logs or dashboards.

The global and per-seller kill switches stop new spend and work but retain
health, receipts, backup, reconciliation, and refunds. For settlement with an
unknown outcome, keep execution fenced and look up by the non-secret payment
commitment. For an `executing` crash boundary, use domain-specific idempotency
evidence; do not automatically repeat the effect. Full incident procedures are
in the [incident recovery runbook](mcplusplus-profile-h-incident-recovery.md).

## Go/no-go matrix

| Mode | Testnet | Mainnet |
| --- | --- | --- |
| `exact` immediate | GO after release gate | disabled; separate approval required |
| `upto` metered | GO after meter review | disabled; separate approval required |
| EVM `batch` | disabled | disabled |

Run the final documentation/evidence audit with:

```sh
python scripts/validate_mcplusplus_profile_h_closeout.py
```

