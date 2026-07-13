#!/usr/bin/env python3
"""Validate the normative XPH-101 Profile H specification surface."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHAPTER = ROOT / "Mcp-Plus-Plus/docs/spec/x402-payments.md"
REGISTRY = ROOT / "Mcp-Plus-Plus/docs/spec/mcp++-profiles-draft.md"
PINNED_X402_COMMIT = "0a604079aca7b5a45a2e1620ba444e13982646c8"

HEADINGS = {
    "Scope and conformance",
    "Negotiation and advertisement",
    "Canonical operation and artifacts",
    "Authorization and settlement ordering",
    "HTTP x402 v2 binding",
    "Profile E libp2p binding",
    "Idempotency, settlement, and recovery",
    "Profile F evidence",
    "Stable error registry",
    "Threat model and required controls",
    "Privacy and data handling",
    "Required bounds and abuse resistance",
    "Version and dependency policy",
    "Protocol examples",
}

ARTIFACTS = {
    "PaidCapability", "PaymentQuote", "PaymentAuthorization",
    "PaymentVerification", "SettlementReceipt", "PaidEntitlement",
    "UsageRecord", "RefundRecord", "AccessReceipt",
}

ERRORS = {
    "H_PAYMENT_REQUIRED", "H_PAYMENT_DECLINED", "H_QUOTE_EXPIRED",
    "H_UNSUPPORTED_X402_VERSION", "H_UNSUPPORTED_SCHEME",
    "H_UNSUPPORTED_NETWORK", "H_UNSUPPORTED_ASSET", "H_AMOUNT_MISMATCH",
    "H_REQUEST_MISMATCH", "H_PAYMENT_REPLAY", "H_VERIFICATION_FAILED",
    "H_SETTLEMENT_FAILED", "H_ENTITLEMENT_EXHAUSTED",
    "H_PAYMENT_POLICY_DENIED", "H_FACILITATOR_UNAVAILABLE",
    "H_RECONCILIATION_REQUIRED", "H_LIMIT_EXCEEDED",
    "H_INVALID_PAYMENT_MESSAGE",
}

EVENTS = {
    "payment_catalog_published", "payment_quote_issued",
    "payment_approval_requested", "payment_authorized", "payment_verified",
    "payment_settlement_started", "payment_settled", "payment_failed",
    "entitlement_issued", "entitlement_consumed", "paid_access_allowed",
    "paid_access_denied", "usage_recorded", "refund_requested",
    "refund_recorded", "payment_reconciled",
}

METHODS = {
    "mcp++/payments/profile", "mcp++/payments/catalog",
    "mcp++/payments/quote", "mcp++/payments/verify",
    "mcp++/payments/settle", "mcp++/payments/receipt/get",
    "mcp++/payments/entitlement/get", "mcp++/payments/usage/get",
    "mcp++/payments/refund/request", "mcp++/payments/reconcile",
}


def _headings(text: str) -> set[str]:
    return {
        re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", match.group(1)).strip()
        for match in re.finditer(r"^#{2,6}\s+(.+?)\s*$", text, re.MULTILINE)
    }


def validate(chapter: str, registry: str) -> list[str]:
    """Return all specification failures, allowing tests to exercise the gate."""
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    missing_headings = HEADINGS - _headings(chapter)
    require(not missing_headings, f"missing normative sections: {sorted(missing_headings)}")
    require(chapter.count("MUST") >= 55, "chapter lacks normative MUST/MUST NOT requirements")
    require("mcp++/x402-payments" in chapter, "capability key is not specified")
    require('"profileVersion": "1.0"' in chapter, "structured Profile H version selection is missing")
    require('"x402Version": 2' in chapter, "x402 v2 negotiation is missing")
    require('"environment": "testnet"' in chapter, "testnet-first selection is missing")
    require("CAIP-2" in chapter and "smallest unit" in chapter, "network/atomic amount rules are incomplete")

    for header in ("PAYMENT-REQUIRED", "PAYMENT-SIGNATURE", "PAYMENT-RESPONSE"):
        require(header in chapter, f"missing x402 v2 HTTP header: {header}")
    require("402 Payment Required" in chapter, "HTTP 402 behavior is missing")
    require("X-PAYMENT" in chapter and "MUST NOT" in chapter, "legacy x402 v1 headers are not forbidden")
    require("standard padded base64" in chapter, "HTTP header encoding is ambiguous")

    require("/mcp+p2p/1.0.0" in chapter, "Profile E protocol representation is missing")
    require("payment_context" in chapter and "paymentRequired" in chapter, "typed Profile E objects are missing")
    require("not upstream x402 HTTP" in chapter or "not part of upstream x402" in chapter,
            "upstream x402 and MCP++ libp2p conformance are not distinguished")
    require("same decoded objects" in chapter or "same canonical decoded" in chapter,
            "HTTP/libp2p parity requirement is missing")

    for profile in ("C (UCAN)", "D (policy)", "E (transport)", "F (provenance)", "G (scheduling)"):
        require(profile in chapter, f"composition rule missing for Profile {profile[0]}")
    require("authorize before" in chapter and "before settlement" in chapter and "before execution" in chapter,
            "authorization ordering is incomplete")
    require("MUST NOT grant identity" in chapter, "payment-as-authorization prohibition is missing")

    missing_artifacts = ARTIFACTS - set(re.findall(r"`([A-Z][A-Za-z]+)`", chapter))
    require(not missing_artifacts, f"missing artifact registry entries: {sorted(missing_artifacts)}")
    missing_errors = ERRORS - set(re.findall(r"`(H_[A-Z0-9_]+)`", chapter))
    require(not missing_errors, f"missing stable errors: {sorted(missing_errors)}")
    missing_events = EVENTS - set(re.findall(r"`([a-z][a-z0-9_]+)`", chapter))
    require(not missing_events, f"missing Profile F events: {sorted(missing_events)}")
    missing_methods = METHODS - set(re.findall(r"`(mcp\+\+/payments/[a-z/]+)`", chapter))
    require(not missing_methods, f"missing Profile H methods: {sorted(missing_methods)}")

    for state in ("quoted", "verified", "settling", "settled", "execution_reserved", "executing", "executed", "reconciliation_required"):
        require(state in chapter, f"settlement/recovery state is missing: {state}")
    require("at most once" in chapter and "unique" in chapter, "idempotency/double execution rule is incomplete")
    require("settled-but-unfulfilled" in chapter, "post-settlement denial recovery is missing")

    threat_rows = len(re.findall(r"^\| [^\n|]+ \| [^\n|]+ \|$", chapter, re.MULTILINE))
    require(threat_rows >= 30, "threat model, bounds, or registries are unexpectedly incomplete")
    for term in ("prompt-induced", "SSRF", "downgrade", "double execution", "privacy"):
        require(term.lower() in chapter.lower(), f"threat/control is missing: {term}")
    require("Hard maximum" in chapter and "JSON nesting depth" in chapter, "parser/resource bounds are missing")
    require("redacted" in chapter and "encrypted" in chapter, "privacy/storage controls are incomplete")
    require("private key" in chapter and "isolated" in chapter, "wallet isolation requirement is missing")

    require(PINNED_X402_COMMIT in chapter, "immutable upstream x402 specification pin is missing")
    require("lockfile-resolved versions/integrities" in chapter, "SDK version/integrity policy is missing")
    require("SDK patch/minor upgrades require" in chapter, "SDK upgrade gate is missing")

    require("Profiles A-H interoperability candidate" in registry, "top-level status does not include Profile H")
    require("Profile H: x402 Payments and Paid Capability Access" in registry, "Profile H registry entry is missing")
    require("[docs/spec/x402-payments.md](x402-payments.md)" in registry,
            "Profile H registry does not link its normative chapter")
    require("| H (x402 payments) |" in registry, "Profile H wire-binding table row is missing")
    require("`mcp++/x402-payments` (Profile H)" in registry, "Profile H capability key is missing from registry")
    require("MUST NOT be represented as upstream x402 HTTP conformance" in registry,
            "registry does not preserve the libp2p/upstream distinction")
    return failures


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in (CHAPTER, REGISTRY) if not path.is_file()]
    if missing:
        for path in missing:
            print(f"FAIL: missing {path}", file=sys.stderr)
        return 1
    failures = validate(CHAPTER.read_text(encoding="utf-8"), REGISTRY.read_text(encoding="utf-8"))
    if failures:
        print(f"FAIL: {len(failures)} Profile H specification error(s)", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    print("PASS: XPH-101 normatively specifies Profile H negotiation, composition, transports, recovery, threats, errors, and version policy", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
