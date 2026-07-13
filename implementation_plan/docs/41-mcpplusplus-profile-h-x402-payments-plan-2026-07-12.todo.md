# MCP++ Profile H: x402 Payments and Paid Capability Access Plan

Status: proposed implementation plan and supervisor-ready taskboard
Created: 2026-07-12
Scope: `Mcp-Plus-Plus`, SwissKnife, `ipfs_kit_py`, `ipfs_accelerate_py`,
`ipfs_datasets_py`, MCP++ HTTP, and MCP++ `/mcp+p2p/1.0.0` sessions

## Objective

Add optional **Profile H: x402 Payments and Paid Capability Access** to
MCP++ so that:

1. SwissKnife is a buyer client and wallet that can discover a price, obtain
   explicit user or policy approval, sign an x402 payment, retry a paid MCP++
   request, and retain a verifiable receipt.
2. `ipfs_kit_py`, `ipfs_accelerate_py`, and `ipfs_datasets_py` can act as
   sellers, attach prices to individual MCP tools, resources, prompts, HTTP
   routes, model jobs, storage operations, datasets, and usage tiers, and deny
   access until payment is verified.
3. Paid access composes with MCP++ authorization and policy; payment never
   substitutes for identity, UCAN authority, tenancy, safety checks, or data
   entitlement.
4. HTTP behavior conforms to x402 v2 and equivalent MCP++ payment semantics
   work over libp2p without inventing a second economic protocol.
5. Every quote, authorization, verification, settlement, access decision, and
   result is auditable through content-addressed artifacts and Profile F events.

The first release targets testnets and fixed-price `exact` payments. Usage-based
`upto` and EVM `batch-settlement` remain negotiated, feature-gated follow-ons
until metering, refunds, and reconciliation pass their release gates.

## Protocol Baseline

The implementation targets x402 v2. At an HTTP boundary:

- an unpaid protected request receives HTTP `402 Payment Required` and a
  base64-encoded JSON `PAYMENT-REQUIRED` header;
- the client selects an acceptable requirement, constructs and signs a
  `PaymentPayload`, and retries the same request with `PAYMENT-SIGNATURE`;
- the server verifies and settles locally or through a configured facilitator;
- the success or failure response carries a base64-encoded settlement result in
  `PAYMENT-RESPONSE`;
- network identifiers use CAIP-2 notation and amounts use integer smallest-unit
  representation in canonical artifacts;
- facilitators are replaceable dependencies. No Coinbase account, hosted
  wallet, or single facilitator is a protocol requirement.

Profile H must pin supported x402 specification and SDK versions in descriptors
and conformance evidence. Implementations must not silently accept x402 v1
`X-PAYMENT` semantics.

## Non-Goals

- Creating a new token, chain, exchange, custody service, or facilitator.
- Putting seed phrases or raw private keys in browser storage, MCP messages,
  logs, IPFS, taskboards, receipts, or agent prompts.
- Treating payment as authorization to access otherwise forbidden data or run
  otherwise forbidden tools.
- Guaranteeing anonymity, refunds, chargebacks, tax treatment, or regulatory
  compliance without separately configured policy and provider support.
- Advertising mainnet readiness before threat-model, spend-control, settlement,
  and recovery gates pass.

## Architecture Decisions

### 1. Profile H composes with Profiles C through G

The access decision is an intersection, not a fallback chain:

`capability exists AND UCAN permits AND policy permits AND payment condition is satisfied`

- Profile C proves who may request or delegate an operation.
- Profile D decides whether the operation and proposed payment are allowed and
  attaches obligations such as spend limits or human confirmation.
- Profile E carries the same MCP++ method over HTTP or libp2p.
- Profile F records quote, payment, settlement, access, and execution lineage.
- Profile G may schedule paid work, but a scheduler cannot sign or raise a spend
  limit merely because a task is ready.
- Profile H proves satisfaction of the commercial condition.

The seller checks non-payment authorization both before presenting sensitive
pricing metadata and again after payment verification. A valid payment never
overrides a denial. Where feasible, policy is evaluated before settlement so a
buyer is not charged for an operation the seller already knows it must deny.

### 2. Separate commercial policy from transport middleware

Each seller has a shared `PaymentPolicyEngine` independent of FastAPI/FastMCP,
MCP JSON-RPC, or libp2p dispatch. It resolves a canonical operation identity
and request context to one of:

- `free` — continue without a payment;
- `payment_required` — return one or more acceptable requirements;
- `paid` — a verified, unconsumed or reusable entitlement covers this request;
- `denied` — access is forbidden regardless of payment;
- `unavailable` — fail closed because pricing, verifier, facilitator, or ledger
  state is unavailable.

HTTP middleware only maps this decision to x402 headers/statuses. MCP++
dispatchers enforce the same decision immediately before tool execution,
resource read, prompt retrieval, model admission, or storage mutation.

### 3. Canonical operation identity and price catalog

Prices attach to immutable `PaidCapability` records, never fragile display
labels. Each record includes:

- server DID and descriptor CID;
- MCP interface CID, operation kind, canonical tool/resource/prompt name, and
  optional route plus method;
- pricing mode, scheme, CAIP-2 network, asset identifier, atomic amount or
  maximum, payee, facilitator policy, and validity window;
- unit definition for metered work, quota/entitlement semantics, refund policy,
  and settlement timing;
- Profile C capability, Profile D policy CID, terms CID, catalog version, and
  seller signature.

The quote binds the catalog entry to the request commitment, buyer or payer
scope when disclosed, nonce, expiry, idempotency key, and server descriptor CID.
Arguments that may affect price are committed by hash without leaking secrets.
The seller must reject substitution of tool, arguments, server, amount, asset,
network, destination, quote, or expiry.

### 4. Payment artifacts are CID-native but secrets are not

Profile H defines DAG-JSON schemas for:

| Artifact | Purpose |
| --- | --- |
| `PaidCapability` | signed catalog entry and access semantics |
| `PaymentQuote` | request-bound selection of x402 requirements |
| `PaymentAuthorization` | redacted commitment to the client-signed payload |
| `PaymentVerification` | verifier/facilitator result and freshness |
| `SettlementReceipt` | settlement outcome, network reference policy, and x402 response commitment |
| `PaidEntitlement` | optional bounded reuse/quota grant linked to a settlement |
| `UsageRecord` | deterministic metered units and input/output commitments |
| `RefundRecord` | requested/approved/failed refund lineage where supported |
| `AccessReceipt` | final allow/deny decision linked to operation and payment |

Artifacts contain hashes or selectively disclosed fields when wallet addresses,
transaction identifiers, request arguments, or facilitator payloads would leak
sensitive data. Raw signatures are transmitted only where verification requires
them and are encrypted at rest if retry/recovery requires retention.

### 5. One payment cannot buy unintended duplicate execution

Every paid mutation uses an idempotency key and request commitment. Seller
ledgers enforce atomic states such as `quoted -> verified -> settling -> settled
-> consumed -> executed`, with explicit failure/reconciliation states. A replay
of the same request returns the existing result or receipt; it does not settle
or execute twice. A changed request requires a new quote/payment.

Verification and settlement are not held inside a long database transaction.
Short durable transitions, fencing, unique constraints, and reconciliation
handle crashes between external settlement and local execution.

### 6. HTTP is normative x402; libp2p carries equivalent objects

For HTTP, Profile H preserves the x402 v2 status and header contract exactly.
For `/mcp+p2p/1.0.0`, the same decoded x402 `PaymentRequired`,
`PaymentPayload`, and `SettlementResponse` objects are carried in typed MCP++
envelopes because libp2p has no HTTP status/header layer. Gateways translate
mechanically between representations and conformance tests prove identical
canonical objects and access results. Profile H does not claim that this
libp2p framing is itself part of the upstream x402 HTTP specification.

### 7. Wallet signing is isolated from the SwissKnife UI and agents

SwissKnife uses a wallet-provider interface with hardware/external wallet,
WalletConnect-compatible, and explicitly enabled local development adapters.
The renderer, MCP++ Explorer, Agent Supervisor, prompts, and remote MCP servers
never receive private key material. Signing runs in a constrained trusted
boundary and displays verified human-readable intent:

- seller identity and destination;
- capability and committed request summary;
- amount/max amount, asset, network, scheme, facilitator, and expiry;
- whether settlement is immediate, metered, or batched;
- expected entitlement and refund policy.

Autopay is opt-in and policy bounded by seller allowlist, capability, asset,
network, per-request cap, rolling/daily cap, expiry, and risk class. Unknown
seller, changed destination, new network, price increase, `upto`, batch deposit,
or policy mismatch requires fresh approval. Agents may request approval but
cannot weaken or rewrite wallet policy.

## Profile H Capability and Wire Surface

Clients request `capabilities.experimental["mcp++/x402-payments"] = true`.
Servers advertise it only after the paid dispatch path and conformance gate are
enabled. Metadata includes profile/version, x402 version, supported schemes,
CAIP-2 networks, assets, facilitator modes, catalog CID, quote bounds,
settlement policy, metering support, and privacy/receipt features.

| Operation | JSON-RPC method | REST/HTTP binding | Purpose |
| --- | --- | --- | --- |
| profile | `mcp++/payments/profile` | `GET /mcp/payments/profile` | negotiated limits and versions |
| catalog | `mcp++/payments/catalog` | `GET /mcp/payments/catalog` | signed paid-capability catalog |
| quote | `mcp++/payments/quote` | `POST /mcp/payments/quote` | request-bound requirements |
| verify | `mcp++/payments/verify` | `POST /mcp/payments/verify` | verify without granting execution |
| settle | `mcp++/payments/settle` | `POST /mcp/payments/settle` | settle an accepted authorization |
| execute | normal MCP method with Profile H payment context | original protected route | retry paid operation |
| receipt | `mcp++/payments/receipt/get` | `GET /mcp/payments/receipts/{cid}` | redacted receipt retrieval |
| entitlement | `mcp++/payments/entitlement/get` | `GET /mcp/payments/entitlements/{cid}` | quota/reuse status |
| usage | `mcp++/payments/usage/get` | `GET /mcp/payments/usage/{cid}` | metering proof |
| refund | `mcp++/payments/refund/request` | `POST /mcp/payments/refunds` | policy-dependent refund request |
| reconcile | `mcp++/payments/reconcile` | `POST /mcp/payments/reconcile` | operator recovery |

Normal paid MCP calls are not forced through a bespoke execute API. On HTTP,
the original MCP request receives 402 and is retried with
`PAYMENT-SIGNATURE`. On libp2p, the normal request returns a typed
`H_PAYMENT_REQUIRED` error and is retried with `payment_context.payload`.

Required stable errors include `H_PAYMENT_REQUIRED`, `H_PAYMENT_DECLINED`,
`H_QUOTE_EXPIRED`, `H_UNSUPPORTED_SCHEME`, `H_UNSUPPORTED_NETWORK`,
`H_AMOUNT_MISMATCH`, `H_REQUEST_MISMATCH`, `H_PAYMENT_REPLAY`,
`H_VERIFICATION_FAILED`, `H_SETTLEMENT_FAILED`, `H_ENTITLEMENT_EXHAUSTED`,
`H_PAYMENT_POLICY_DENIED`, `H_FACILITATOR_UNAVAILABLE`, and
`H_RECONCILIATION_REQUIRED`.

Profile F adds `payment_catalog_published`, `payment_quote_issued`,
`payment_approval_requested`, `payment_authorized`, `payment_verified`,
`payment_settlement_started`, `payment_settled`, `payment_failed`,
`entitlement_issued`, `entitlement_consumed`, `paid_access_allowed`,
`paid_access_denied`, `usage_recorded`, `refund_requested`, `refund_recorded`,
and `payment_reconciled`.

## Seller Responsibilities

### Shared behavior

All three Python services must use the same schema package, catalog semantics,
payment middleware contract, redaction rules, idempotency ledger, and x402 SDK
adapter. They may configure different capabilities and prices. Configuration is
deny-by-default and supports environment/file/secret-provider values for seller
address, networks, assets, facilitator URL, verification mode, pricing catalog,
free tiers, and emergency disable. Secret values never appear in descriptors.

Pricing changes create a new catalog CID and do not alter live quotes. Servers
support dry-run/testnet mode, readiness diagnostics, facilitator health, and a
kill switch that stops new paid work without corrupting settlement recovery.

### `ipfs_kit_py`

- Price storage, pinning, retrieval, bandwidth, replication, filesystem, and
  premium durability operations by explicit resource unit.
- Persist immutable Profile H artifacts and a derived DuckDB settlement,
  entitlement, replay, and reconciliation index; immutable blocks remain the
  provenance authority.
- Bind storage entitlements to CID/namespace, quota, retention class, and
  expiry. Never imply payment grants access to a private CID.
- Make eviction, partial completion, renewal, and refund semantics explicit.

### `ipfs_accelerate_py`

- Price model inference, accelerator time, batch jobs, agent-supervisor work,
  premium queues, and resource reservations.
- Reserve capacity only after policy allows and payment terms are satisfied;
  release reservations safely on declined/expired payments.
- For variable compute, use pre-priced fixed tiers first. Gate `upto` behind
  signed deterministic usage records, maximum authorization, cancellation,
  timeout, partial-result, and unused-amount rules.
- Profile G workers receive a paid entitlement CID, never wallet signing
  authority. Fencing/idempotency covers settlement and job execution.

### `ipfs_datasets_py`

- Price dataset queries, restricted derived artifacts, GraphRAG/index work,
  transformations, provenance reports, and premium API features.
- Enforce dataset license, tenant policy, row/field controls, and privacy before
  and after payment. Payment cannot unlock data the caller is not entitled to.
- Bind entitlements to dataset/version/query commitment and allowed derivation;
  prevent a paid query receipt from becoming a bearer token for unrelated data.
- Provide auditable usage/metering logic and redacted proofs for paid queries.

## SwissKnife Client and Wallet Work

SwissKnife adds a `ProfileHPaymentClient`, shared x402 codecs, wallet-provider
broker, encrypted non-exportable wallet metadata, payment-policy engine, quote
comparison, balance/network checks, receipt store, and HTTP/libp2p retry logic.

The Wallet app gains:

- accounts and supported network/asset state without displaying secrets;
- pending approval cards with verified terms and request diff;
- exact spend and maximum-authorized spend shown distinctly;
- per-service/capability limits, session and daily budgets, allow/deny lists,
  autopay controls, and a global payment pause;
- receipts, settlement state, entitlements, usage, refunds, and explorer links;
- clear states for quoted, awaiting approval, signing, verifying, settling,
  paid, executing, completed, failed, expired, and reconciliation required.

MCP++ Explorer previews catalogs and quotes and can exercise testnet payments.
Agent Supervisor links a paid task to quote, approval, settlement, entitlement,
Profile G lease, execution receipt, and output CID. No UI labels a verified but
unsettled payment as paid, or a settled payment as successful execution.

## Configuration Contract

Exact names should follow each package's existing settings system, but every
implementation exposes equivalents of:

- enable flag and mode: `disabled`, `testnet`, `mainnet`;
- x402 protocol/SDK version allowlist;
- signed catalog path/CID and hot-reload policy;
- seller address by CAIP-2 network and allowed assets/schemes;
- facilitator URL(s), trust roots, timeout, retry, and circuit breaker;
- local verification/settlement option where supported;
- quote lifetime, maximum price, idempotency/replay retention;
- encrypted ledger/receipt location and redaction policy;
- free-tier/entitlement configuration and emergency pause;
- SwissKnife wallet provider plus per-request/session/day limits.

Mainnet mode fails startup if test keys, wildcard networks, an untrusted HTTP
facilitator, missing seller identity, unsigned catalog, absent durable ledger,
or development wallet storage is configured.

## Threat Model and Required Controls

| Threat | Required control |
| --- | --- |
| price/destination substitution | signed catalog and request-bound quote; approval diff; strict field equality |
| replay/double settlement | nonce, idempotency key, unique payload commitment, atomic ledger, facilitator protections |
| double execution after payment | request commitment plus execution idempotency and Profile G fencing |
| overcharge or unit ambiguity | atomic integer amounts, explicit asset decimals/unit, `exact` first, signed usage records |
| compromised/lying facilitator | configurable trust, TLS, response validation, health/circuit breaker, reconciliation evidence |
| wallet key exfiltration | isolated signer, non-exportable/hardware option, no renderer/prompt/server key access |
| prompt-induced spending | policy engine outside model context, hard budgets, approval boundaries, seller/capability allowlists |
| payment used as auth bypass | Profile C/D and domain entitlement checks remain mandatory |
| receipt privacy leakage | redacted CID artifacts, encrypted sensitive payloads, configurable tx-hash disclosure |
| stale quote/catalog | expiry, descriptor/catalog CID binding, network and seller revalidation |
| server settles then crashes | durable pre/post-settlement states and idempotent reconciliation |
| client pays but loses response | receipt lookup and retry by idempotency/payment commitment |
| SSRF or malicious facilitator URL | operator allowlist, URL validation, egress policy, no request-controlled facilitator |
| dependency/supply-chain compromise | pinned SDK versions, lockfiles, SBOM/license/vulnerability review, conformance vectors |

Financial and private-key code requires targeted security review. Test logs and
fixtures use generated testnet accounts only. CI must scan for secrets and must
never require mainnet funds.

## Testing and Conformance Strategy

1. Canonical cross-language vectors cover base64 headers, x402 objects, CAIP-2
   networks, atomic amounts, quotes, CIDs, signatures, redaction, and errors.
2. Unit tests cover catalogs, selection, budgets, signer isolation, middleware,
   authorization ordering, ledgers, replay, metering, and receipt validation.
3. Contract tests run the same protected MCP tool/resource through all three
   sellers and SwissKnife.
4. Transport tests prove decoded object and access-result parity between HTTP
   x402 and Profile E libp2p framing.
5. Failure injection covers invalid/expired quotes, changed args, wrong seller,
   wrong chain/asset/amount, insufficient balance, facilitator timeout,
   verification success plus settlement failure, settlement plus server crash,
   duplicate retry, ledger lock contention, partition, and restart.
6. End-to-end tests use x402-supported test networks or deterministic local
   mocks. Mainnet tests are manual, budget-capped, and excluded from CI.
7. UI/E2E evidence proves informed approval, denial, autopay boundaries, global
   pause, history, reconciliation, and no secret exposure.

## Acceptance and Release Gates

| Gate | Required evidence |
| --- | --- |
| specification | Profile H text, schemas, errors, examples, and valid/invalid vectors |
| x402 conformance | v2 headers and objects match pinned upstream vectors at HTTP boundaries |
| cross-language | TypeScript and all Python implementations produce identical canonical artifacts/CIDs |
| paid restriction | every configured protected operation denies unpaid/invalid payment before side effects |
| auth composition | payment cannot bypass UCAN, policy, tenancy, license, safety, or data controls |
| wallet safety | isolated signing, hard budgets, approval tests, secret scans, and malicious-prompt tests pass |
| replay/idempotency | repeated payload/request settles and executes at most once, with stable receipt recovery |
| recovery | crash/timeout/partition cases reconcile without silent charge or execution ambiguity |
| transport parity | HTTP and libp2p yield equivalent requirements, decisions, receipts, and results |
| observability | quote-to-output lineage, redacted metrics, alerts, pause, and operator reconciliation exist |
| performance | price lookup and verification overhead meet agreed SLOs without bypass caches |
| release | testnet soak and security review pass; mainnet remains separately approved and capped |

The release is `NO_GO` if a protected operation can cause side effects before
authorization/payment enforcement; if payment can override policy; if a retry
can charge or execute twice; if the signer is exposed to browser/agent/server
code; if HTTP/libp2p results diverge; or if a settled-but-unfulfilled request
cannot be reconciled.

## Rollout and Rollback

1. Land schemas and disabled capability negotiation.
2. Run mock facilitator and test-wallet conformance in CI.
3. Enable testnet `exact` for one read-only low-cost capability per seller.
4. Add mutating/compute operations after idempotency and recovery soak.
5. Enable bounded SwissKnife autopay only after manual approval telemetry is
   understood.
6. Consider `upto`, entitlements, and `batch-settlement` independently.
7. Require explicit operator approval, security sign-off, funded-wallet limits,
   and incident runbook before any mainnet flag is accepted.

Rollback disables new quotes and paid dispatch while retaining receipt lookup,
settlement reconciliation, refund workflows, and already purchased entitlement
rules. Never delete or roll back a ledger to undo an onchain settlement.

## Supervisor Execution Contract

This board uses the field structure parsed by the `ipfs_accelerate_py agent
supervisor`: one heading per task and explicit `Status`, `Priority`, `Track`,
`Depends on`, `Outputs`, `Validation`, and `Acceptance` fields. Empty dependency
sets are written as `none`. The supervisor must preserve task IDs, update status
and completion evidence in place, and avoid claiming later tasks whose
dependencies are incomplete.

Supervisor operating rules:

- work in the current checkout and preserve unrelated/uncommitted changes;
- use generated test wallets and testnets only unless a task explicitly says
  otherwise; no task below authorizes mainnet spending;
- never print, commit, prompt with, or persist wallet secrets;
- treat `Mcp-Plus-Plus` schemas/vectors as the canonical contract and reuse
  shared runtime code rather than forked seller implementations;
- save machine-readable evidence under
  `swissknife/test-results/mcpplusplus-profile-h-x402/`;
- after each task, run its validation, attach artifact paths and exact results,
  then update `Status` to `completed`; use `blocked` only with concrete evidence;
- do not advertise `mcp++/x402-payments` until XPH-104 through XPH-109 pass.

## Taskboard

## XPH-100 Inventory x402 and paid-access integration seams

- Status: completed
- Priority: P0
- Track: discovery
- Depends on: none
- Outputs: `data/mcplusplus_profile_h/x402-inventory.json`, dependency/version
  matrix, current dispatch/middleware/wallet/persistence seam report.
- Validation: python scripts/validate_mcplusplus_profile_h_inventory.py --report data/mcplusplus_profile_h/x402-inventory.json
- Acceptance: The report identifies every MCP++ HTTP/libp2p dispatcher,
  capability descriptor, SwissKnife wallet/client seam, seller configuration
  path, existing x402 dependency, durable store, and protected operation family;
  it pins primary upstream x402 v2 references and records gaps without changing
  runtime behavior.

## XPH-101 Specify Profile H, composition rules, and threat model

- Status: completed
- Priority: P0
- Track: specification
- Depends on: XPH-100
- Outputs: `Mcp-Plus-Plus/docs/spec/x402-payments.md`, Profile H entry in
  `Mcp-Plus-Plus/docs/spec/mcp++-profiles-draft.md`, threat model, protocol
  examples, error registry, and version policy.
- Validation: python scripts/validate_mcplusplus_profile_h_spec.py
- Acceptance: The specification normatively defines negotiation, C/D/E/F/G
  composition, HTTP and libp2p representation, authorization ordering,
  idempotency, settlement/recovery, privacy, bounds, errors, and explicitly
  distinguishes upstream x402 conformance from MCP++ libp2p framing.

## XPH-102 Add canonical schemas, codecs, and conformance vectors

- Status: completed
- Priority: P0
- Track: shared-runtime
- Depends on: XPH-101
- Outputs: versioned Profile H JSON schemas, TypeScript/Python codecs,
  `Mcp-Plus-Plus/conformance/vectors/profile_h_*.json`, generated schema docs.
- Validation: python scripts/run_mcplusplus_profile_h_vector_gate.py
- Acceptance: TypeScript and Python agree byte-for-byte and CID-for-CID on
  valid fixtures; invalid base64, amount, network, expiry, request binding,
  signature, replay, redaction, and size/bounds vectors fail with stable codes.

## XPH-103 Implement shared Python seller runtime and durable ledger

- Status: completed
- Priority: P0
- Track: seller-runtime
- Depends on: XPH-102
- Outputs: shared payment policy/catalog engine, x402 verifier/facilitator
  adapters, middleware/dispatcher hooks, DuckDB derived ledger, CID artifact
  persistence adapter, reconciliation and diagnostics APIs.
- Validation: pytest -q tests/mcplusplus_profile_h/test_seller_runtime.py tests/mcplusplus_profile_h/test_payment_ledger.py
- Acceptance: Free/required/paid/denied/unavailable decisions are deterministic;
  payment is checked immediately before effects; concurrent replay settles and
  executes at most once; crash boundaries reconcile; secrets and sensitive
  payloads are absent from logs and public artifacts.

## XPH-104 Add paid capabilities to ipfs_kit_py

- Status: completed
- Priority: P0
- Track: ipfs-kit
- Depends on: XPH-103
- Outputs: signed kit catalog, protected storage/pin/retrieval fixtures,
  quota/retention entitlements, HTTP/libp2p handlers, restart/recovery evidence.
- Validation: python -m pytest -q hallucinate_app/ipfs_kit_py/tests/mcplusplus_profile_h
- Acceptance: Configured kit operations return correct x402 requirements,
  reject unpaid/invalid/replayed requests before mutation, enforce CID/namespace
  and quota scopes, settle once, recover receipts after restart, and preserve
  non-payment access controls.

## XPH-105 Add paid capabilities to ipfs_accelerate_py

- Status: completed
- Priority: P0
- Track: ipfs-accelerate
- Depends on: XPH-103
- Outputs: signed accelerator catalog, inference/job/reservation gates, fixed
  compute tiers, Profile G entitlement handoff, usage and recovery evidence.
- Validation: pytest -q external/ipfs_accelerate/tests/mcplusplus_profile_h
- Acceptance: No protected job or reservation begins before accepted payment
  and policy; payment retry cannot duplicate jobs; workers receive entitlement
  CIDs without signing authority; cancellation, failure, partial-result, and
  settled-before-crash outcomes are explicit and reconcilable.

## XPH-106 Add paid capabilities to ipfs_datasets_py

- Status: completed
- Priority: P0
- Track: ipfs-datasets
- Depends on: XPH-103
- Outputs: signed datasets catalog, protected query/transform/GraphRAG fixtures,
  dataset/version-bound entitlements, redacted usage and provenance evidence.
- Validation: pytest -q external/ipfs_datasets/tests/mcplusplus_profile_h
- Acceptance: Paid queries enforce license, tenant, row/field, and privacy
  controls independently of payment; entitlements cannot be replayed across
  datasets/versions/query commitments; usage and output receipts are CID-linked
  without leaking protected query or result content.

## XPH-107 Implement SwissKnife Profile H client and isolated wallet broker

- Status: completed
- Priority: P0
- Track: swissknife-wallet
- Depends on: XPH-102
- Outputs: Profile H client, x402 HTTP retry and libp2p payment-context support,
  wallet-provider broker, policy/budget engine, encrypted receipt store, signer
  isolation and malicious-prompt tests.
- Validation: npm --prefix swissknife test -- --runInBand test/mcp-plus-plus/profile-h-wallet.test.ts
- Acceptance: SwissKnife discovers/selects requirements, shows an accurate
  intent, enforces hard limits outside agent control, signs through an isolated
  provider, retries idempotently, validates settlement responses, and never
  exposes keys to renderer, prompt, logs, MCP peers, or committed fixtures.

## XPH-108 Build Wallet, MCP++ Explorer, and Agent Supervisor payment UX

- Status: completed
- Priority: P0
- Track: swissknife-ui
- Depends on: XPH-107
- Outputs: approval and policy screens, catalog/quote explorer, receipt and
  entitlement history, task-payment lineage, pause/reconcile controls,
  accessibility and screenshot evidence.
- Validation: npm --prefix swissknife run test:e2e -- mcp-plus-plus-profile-h-x402.spec.ts
- Acceptance: Users can distinguish exact/max authorization, verification,
  settlement, entitlement, execution, and failure states; price/destination
  changes force approval; denied/autopay/pause/reconcile flows work; no mock
  state is presented as live and no secret is rendered.

## XPH-109 Prove three-seller HTTP and libp2p interoperability

- Status: completed
- Priority: P0
- Track: integration
- Depends on: XPH-104, XPH-105, XPH-106, XPH-107, XPH-108
- Outputs: live testnet/mock-facilitator harness, per-operation parity matrix,
  decoded x402 object/CID comparisons, replay/failure/restart Event DAGs.
- Validation: python scripts/run_mcplusplus_profile_h_interop_gate.py --output swissknife/test-results/mcpplusplus-profile-h-x402/interop.json
- Acceptance: SwissKnife pays for at least one representative capability from
  each seller through HTTP and libp2p; requirements, access decisions, receipts,
  results, and CIDs are semantically identical; unpaid/invalid/auth-denied,
  duplicate, timeout, crash, and reconciliation cases pass.

## XPH-110 Add metered upto payments and bounded entitlements

- Status: completed
- Priority: P1
- Track: metering
- Depends on: XPH-109
- Outputs: deterministic usage meters, maximum authorization flow, quota
  entitlements, unused-value rules, cross-seller metering vectors and reports.
- Validation: python scripts/run_mcplusplus_profile_h_metering_gate.py
- Acceptance: Each meter has a versioned unit and reproducible signed usage
  record; actual charge never exceeds the approved maximum; cancellation,
  partial work, rounding, exhaustion, expiry, and disputes are testable; fixed
  `exact` remains available when variable pricing is unsafe.

## XPH-111 Evaluate and gate EVM batch settlement

- Status: completed
- Priority: P2
- Track: batch-settlement
- Depends on: XPH-110
- Outputs: batch threat model, escrow/deposit UX, voucher/redeem ledger,
  solvency/expiry/recovery tests, explicit enablement decision.
- Validation: python scripts/run_mcplusplus_profile_h_batch_gate.py
- Acceptance: Batch settlement stays disabled unless deposits, vouchers,
  seller redemption, duplicate protection, expiry, withdrawal, failure,
  reconciliation, and user maximum exposure are proven on a testnet and pass
  security review.

## XPH-112 Add observability, operations, and incident recovery

- Status: completed
- Priority: P1
- Track: operations
- Depends on: XPH-109
- Outputs: redacted metrics/dashboards, facilitator and ledger health probes,
  alerts, global/seller kill switches, reconciliation/refund runbook, backup and
  restore test evidence.
- Validation: python scripts/run_mcplusplus_profile_h_ops_gate.py
- Acceptance: Operators can identify quote, verify, settlement, entitlement,
  access, and execution failures without wallet secrets or protected data;
  pausing stops new spend/work but retains recovery; backup/restore preserves
  idempotency and settled-payment lineage.

## XPH-113 Complete security, performance, and testnet soak gates

- Status: completed
- Priority: P0
- Track: release
- Depends on: XPH-109, XPH-112
- Outputs: security review, dependency/SBOM/secret-scan evidence, property and
  concurrency tests, latency/throughput report, multi-day testnet soak report,
  release decision artifact.
- Validation: python scripts/run_mcplusplus_profile_h_release_gate.py --mode testnet
- Acceptance: All NO_GO conditions are absent; no unauthorized spend/access,
  double settlement/execution, secret leak, or unresolved ledger divergence is
  observed; agreed latency/SLOs and failure recovery pass; the artifact records
  testnet readiness and leaves mainnet disabled by default.

## XPH-114 Publish documentation and supervisor closeout evidence

- Status: completed
- Priority: P1
- Track: documentation
- Depends on: XPH-110, XPH-111, XPH-113
- Outputs: buyer/seller/operator guides, pricing/config examples, API and wallet
  screenshots, migration/rollback guide, documentation indexes, final
  machine-readable task/evidence manifest.
- Validation: python scripts/validate_mcplusplus_profile_h_closeout.py
- Acceptance: A new operator can configure a testnet seller and SwissKnife
  buyer without handling raw keys; docs clearly label exact/upto/batch and
  testnet/mainnet status; every board task links to validation evidence and the
  supervisor reports no pending or silently skipped required task.

## Dependency Summary

`XPH-100 -> XPH-101 -> XPH-102 -> XPH-103 -> {XPH-104, XPH-105, XPH-106}`

`XPH-102 -> XPH-107 -> XPH-108`

`{XPH-104, XPH-105, XPH-106, XPH-107, XPH-108} -> XPH-109 -> {XPH-110, XPH-112}`

`XPH-110 -> XPH-111`

`{XPH-109, XPH-112} -> XPH-113`

`{XPH-110, XPH-111, XPH-113} -> XPH-114`

## Primary References

- x402 introduction: <https://docs.x402.org/introduction>
- x402 HTTP 402 and v2 headers: <https://docs.x402.org/core-concepts/http-402>
- x402 client/server flow: <https://docs.x402.org/core-concepts/client-server>
- x402 buyer quickstart and schemes: <https://docs.x402.org/getting-started/quickstart-for-buyers>
- x402 seller quickstart: <https://docs.x402.org/getting-started/quickstart-for-sellers>
- x402 networks and tokens: <https://docs.x402.org/core-concepts/network-and-token-support>
- x402 MCP integration guide: <https://docs.x402.org/guides/mcp-server-with-x402>
- x402 v1 to v2 migration: <https://docs.x402.org/guides/migration-v1-to-v2>
- x402 signed offers and receipts: <https://docs.x402.org/extensions/offer-receipt>

## XPH-115 Resolve validation retry-budget failure for XPH-100

- Status: completed
- Completion: manual 2026-07-13: repaired Markdown-backtick command substitution, preserved the verified dependency/version inventory, and validated the legacy already-parsed command path so the supervisor can release XPH-100.
- Priority: P1
- Track: ops
- Depends on: none
- Outputs: `data/mcplusplus_profile_h/x402-inventory.json`, dependency/version, tmp/mcpplusplus_profile_h_supervisor/discovery
- Validation: python scripts/validate_mcplusplus_profile_h_inventory.py --report data/mcplusplus_profile_h/x402-inventory.json
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in XPH-100. Use evidence in tmp/mcpplusplus_profile_h_supervisor/discovery/2026-07-13-xph-115-xph-100-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release XPH-100 from strategy blocked_tasks.

## XPH-116 Resolve validation retry-budget failure for XPH-104

- Status: completed
- Completion: manual 2026-07-13: replaced the stale standalone pytest launcher with the active Python environment's pytest module, preserved the signed kit catalog and protected operation fixtures, and validated all 13 Profile H ipfs_kit tests so the supervisor can release XPH-104.
- Priority: P1
- Track: ops
- Depends on: XPH-103
- Outputs: signed kit catalog, protected storage/pin/retrieval fixtures, tmp/mcpplusplus_profile_h_supervisor/discovery
- Validation: python -m pytest -q hallucinate_app/ipfs_kit_py/tests/mcplusplus_profile_h
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in XPH-104. Use evidence in tmp/mcpplusplus_profile_h_supervisor/discovery/2026-07-13-xph-116-xph-104-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release XPH-104 from strategy blocked_tasks.
