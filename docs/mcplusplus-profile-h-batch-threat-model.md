# Profile H EVM batch-settlement threat model

Status: **disabled**. Scope: XPH-111 evaluation on approved EVM testnets only.
This model does not approve or describe a production smart contract.

## Assets, actors, and trust boundaries

The protected assets are the buyer's escrowed token balance and maximum
exposure, seller voucher claims, withdrawal rights, the nonce/redemption
ledger, and the linkage from a voucher to the paid capability. The buyer wallet
signer, seller redeemer, off-chain DuckDB index, RPC/facilitator, and eventual
escrow contract are separate trust boundaries. Agents, prompts, renderers,
sellers, and RPC responses are untrusted. Wallet private keys and raw
transaction payloads never enter public evidence.

## Threats and required mitigations

| Threat | Impact | Required control and gate evidence |
| --- | --- | --- |
| Deposit or voucher exceeds approval | Buyer loses more than intended | Integer atomic values; fresh deposit approval; `deposit <= maximumExposure`; transactional reservation rejects aggregate overcommitment. |
| Voucher forgery or seller substitution | Unauthorized redemption | Buyer Ed25519/EVM signature verification; voucher commits deposit, seller DID, network, asset, amount, nonce, and expiry. Contract design must use domain/chain/contract separation. |
| Replay, nonce reuse, concurrent redeem | Double payment | Unique voucher CID and `(deposit, seller, nonce)`; on-chain consumed marker; idempotent duplicate response; concurrency/property tests. |
| Cross-chain or cross-contract replay | Double payment on another deployment | Approved testnet allowlist and signed EIP-712 domain containing chain ID and verifying contract. |
| Insolvent oversubscription across sellers | Sellers cannot redeem valid claims | Reserve every issued voucher transactionally; require deposited balance to cover redeemed plus all unexpired reservations. |
| Expiry boundary manipulation | Premature release or late redemption | Signed absolute expiry, chain-time semantics, documented clock tolerance, expiry race tests, and withdrawal delay after deposit expiry. |
| Withdrawal races redemption | Seller or buyer loses valid funds | Block withdrawal while reservations or unknown outcomes exist; contract-level atomic state transition; reorg/finality tests. |
| RPC timeout, revert, or reorg | Duplicate retry or stuck funds | Distinguish known failure from unknown outcome; unknown enters `reconciliation_required`; finalized receipt reconciliation precedes retry/withdrawal. |
| Ledger loss or tampering | Replays and incorrect balances | Contract is source of truth; rebuildable event index; backups and invariant reconciliation; no enablement based only on DuckDB. |
| Malicious/upgradeable escrow | Total deposit loss | Minimal audited contract, pinned bytecode and address, verified source, least-privilege administration, timelocked upgrades, pause/recovery review. |
| Token quirks or gas griefing | Incorrect accounting or denial of redeem | Asset allowlist, received-balance checks, no fee-on-transfer/rebase token, pull-based redeem, bounded batches, failure tests. |
| UI deception or agent autopay | Uninformed deposit | Wallet-owned approval view shows contract, testnet, asset, atomic amount, maximum exposure, expiry, delay, and full-at-risk warning; batch deposits never inherit autopay. |

## Recovery and enablement decision

Known failed redemption stays retryable and retains its reservation. Unknown
redemption blocks withdrawal until finalized chain evidence reconciles it as
confirmed or absent. Expired, unredeemed vouchers release reservations; funds
are withdrawable only after the delay and with no pending reconciliation.

The implementation gate proves deterministic off-chain invariants but records
neither a deployed contract nor independent review. Batch settlement therefore
remains disabled. Testnet enablement requires every control returned by
`evaluate_batch_enablement` to be true, including deployed-bytecode evidence,
solvency, voucher/redeem, duplicate, expiry, withdrawal, failure/reconciliation,
maximum-exposure tests, and an approved independent security review. Mainnet
remains disabled regardless of that testnet decision and requires a separate
release process.
