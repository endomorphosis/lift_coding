# MCP++ Profile H buyer guide

This guide configures SwissKnife as an x402 v2 buyer on Base Sepolia. Profile H
is **testnet-ready only**. Mainnet is disabled. Fixed `exact` and bounded `upto`
pricing are supported; EVM `batch` settlement remains disabled.

## Configure without exporting a key

1. Import or create a Base Sepolia account in an OS keychain, hardware wallet,
   or another SwissKnife wallet-provider plugin. Give the account the alias
   `swissknife-profile-h-base-sepolia`. Never paste a mnemonic, seed, or signing
   key into JSON, a shell, the browser, an agent prompt, or a seller process.
2. Copy
   [`swissknife-buyer.testnet.example.json`](../config/mcplusplus-profile-h/swissknife-buyer.testnet.example.json)
   to the deployment's secret-free configuration directory. Select the account
   by provider and alias. Replace the allowlisted seller DID, payee alias, asset
   contract, and budgets with operator-verified testnet values.
3. Keep `mode: testnet`, `mainnetEnabled: false`, `autopay: false`, and
   `batchSettlement.enabled: false` for first use. A wallet-provider process
   performs signing after policy evaluation; only the x402 authorization leaves
   that boundary.
4. Open **MCP++ Explorer → Paid capability catalog**, inspect the operation,
   network, asset, destination, expiry, and catalog/quote commitments, then
   request approval. Open **Wallet → Approvals** to approve or deny it.

For `exact`, the displayed atomic amount is the only permitted charge. For
`upto`, approval is a maximum: the signed usage record determines the lower or
equal actual charge and unused value is released. Destination, price, network,
asset, request, or quote changes invalidate approval. `batch` offers must remain
unselectable.

## HTTP and libp2p flow

HTTP uses x402 v2 `PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE`, and
`PAYMENT-RESPONSE` headers. SwissKnife retries the same request and idempotency
key after approval. It rejects legacy `X-PAYMENT` headers. On libp2p, the same
decoded objects are carried in the private Profile H payment context; that is
MCP++ parity, not a claim of upstream HTTP transport conformance.

The wallet timeline separates Quoted, Authorized, Verified, Settled, Entitled,
Profile G lease, Executed, and Completed. Settlement does not prove execution.
If the response is lost, do not pay again: use **Reconcile payments** with the
original idempotency/payment commitment. Pause blocks new signing/spend while
receipt lookup and reconciliation remain available.

## Buyer verification

```sh
npm --prefix swissknife test -- --runInBand test/mcp-plus-plus/profile-h-wallet.test.ts
npm --prefix swissknife run test:e2e -- mcp-plus-plus-profile-h-x402.spec.ts
```

The UI evidence is the [API catalog and quote](../swissknife/test-results/mcpplusplus-profile-h-x402/api-catalog-quote.png),
[wallet policy](../swissknife/test-results/mcpplusplus-profile-h-x402/wallet-policy.png),
and [payment lineage](../swissknife/test-results/mcpplusplus-profile-h-x402/agent-supervisor-payment-lineage.png)
captures. Each screen labels its deterministic fixture as not live.

