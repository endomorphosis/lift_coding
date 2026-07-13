# MCP++ Profile H testnet release gate

XPH-113 is a fail-closed release gate for `mcp++/x402-payments`. It approves
testnet readiness only. It cannot enable or approve mainnet, and it does not
read wallet or payment-payload environment variables.

Run the complete gate from the repository root:

```sh
python scripts/run_mcplusplus_profile_h_release_gate.py --mode testnet
```

The command writes a portable evidence packet under
`swissknife/test-results/mcpplusplus-profile-h-x402/release/`. The packet
contains the release decision, targeted security review, CycloneDX SBOM and
dependency review, secret-scan results, property/concurrency evidence,
latency/throughput measurements, and an accelerated deterministic 72-hour
testnet state-machine soak report.

## Decision policy

Every constituent gate is required. Missing or failed evidence yields
`NO_GO` and a nonzero process exit. The release is also `NO_GO` for any
unauthorized spend/access, duplicate settlement/execution, secret exposure,
transport divergence, unresolved ledger divergence, SLO failure, or attempt to
use this command as mainnet approval.

The soak uses generated Base Sepolia identities and no valuable assets. Each
logical hour covers all three sellers over HTTP and libp2p, with deterministic
lost-response/crash injection and reconciliation. `logicalDurationHours` is
therefore protocol/state-machine duration, not a claim that CI slept for three
days. A production deployment should retain this packet alongside continuous
wall-clock testnet telemetry before a separate mainnet review.

## Operational interpretation

- `GO` means the checked revision is eligible for testnet rollout with the
  existing budgets, allowlists, health probes, and kill switches.
- `NO_GO` means new spend and paid work remain paused. Receipt lookup,
  reconciliation, refunds, and backup/restore stay available.
- `mainnetEnabled` and `mainnetReady` always remain `false`. Mainnet requires a
  separate human security sign-off, funded-wallet caps, and explicit operator
  configuration.
