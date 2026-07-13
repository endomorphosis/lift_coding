# MCP++ Profile H migration and rollback

## Migrate to Profile H 1.0 and x402 v2

Inventory every protected HTTP/MCP/libp2p operation, its existing authorization
checks, side effect, idempotency boundary, store, and wallet seam. Land Profile
H negotiation and catalogs disabled first. x402 v1 `X-PAYMENT` and
`X-PAYMENT-RESPONSE` headers are not accepted; migrate clients to the v2
`PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE`, and `PAYMENT-RESPONSE` objects.

Add the durable ledger and artifact store before enabling a price. Preserve the
existing domain authorization checks, then place the Profile H guard directly
around the effect. Roll out one read-only `exact` testnet operation, then
mutating operations, and finally reviewed `upto` meters. A changed catalog,
meter definition, price, payee, asset, or network gets a new CID and forces a
new approval. Never translate an old approval silently.

Do not migrate to batch settlement: it is disabled pending a deployed testnet
contract, independent security review, and explicit enablement decision.
Mainnet is outside this release and remains disabled.

## Roll back safely

1. Engage the global or seller kill switch and disable new quotes, approvals,
   settlement, entitlement issuance, and paid execution.
2. Keep health, receipt lookup, reconciliation, refunds, backups, and already
   purchased entitlement rules online. Do not delete a ledger, rewind a nonce,
   reuse an idempotency key, or attempt to undo an on-chain settlement by
   restoring an older database.
3. Reconcile `verification`, `settling`, `settled`, and `executing` boundaries.
   Unknown settlement stays fenced until facilitator lookup. Unknown execution
   requires domain evidence and must not be retried automatically.
4. Verify and back up ledger/artifact lineage, export redacted incident
   evidence, then route the capability to its pre-Profile-H behavior only if
   that behavior remains authorized and explicitly configured (free or denied).
5. To roll forward, deploy the fixed catalog/config with a new version/CID,
   rerun operations, interop, metering, and testnet release gates, and unpause a
   single seller before widening traffic.

Rollback success means no new spend or paid work, no lost receipt/refund path,
no duplicate settlement/execution, and zero unresolved ledger divergence.

