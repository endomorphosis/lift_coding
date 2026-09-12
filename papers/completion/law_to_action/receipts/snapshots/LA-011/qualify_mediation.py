#!/usr/bin/python3.12
"""LA-011 qualification: complete mediation, strict capabilities, exact context.

Runs under the sealed validation PATH. Real Ed25519 UCAN verification is
executed. Injected policy/verifier objects are labeled fixtures. Unprotected
and non-identical routes are tested with effect counters and excluded from
the selected safety claim. This is qualification, not a scored A3/A4 run.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[6]
SNAPSHOT = Path(__file__).resolve().parent
LIVE = ROOT / "papers" / "completion" / "law_to_action"
PYTHON = "/usr/bin/python3.12"
HANDLERS = LIVE / "benchmark" / "handlers" / "effects.py"

for path in (
    ROOT / "external" / "ipfs_accelerate",
    ROOT / "external" / "ipfs_datasets",
    ROOT / "external" / "ipfs_kit",
):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)
sys.path.append(str(ROOT / "external" / "ipfs_accelerate"))


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_handlers():
    spec = importlib.util.spec_from_file_location("la011_bounded_handlers", HANDLERS)
    if spec is None or spec.loader is None:
        raise RuntimeError("bounded export handler module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class CaseResult:
    job_id: str
    route_id: str
    case_kind: str
    mutation: str
    expected_decision: str
    expected_effect_count: int
    in_safety_claim: bool
    crypto: str
    policy: str
    decision: str = ""
    delegated: bool = False
    handler_calls: int = 0
    observed_effect_count: int = 0
    journal_event_count: int = 0
    denial_reason: str = ""
    reason_codes: list[str] = field(default_factory=list)
    passed: bool = False
    failure: str | None = None
    notes: str = ""
    verifier_kind: str = "none"
    empirical_benchmark_result: bool = False

    def to_record(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "route_id": self.route_id,
            "case_kind": self.case_kind,
            "mutation": self.mutation,
            "expected_decision": self.expected_decision,
            "decision": self.decision,
            "delegated": self.delegated,
            "handler_calls": self.handler_calls,
            "observed_effect_count": self.observed_effect_count,
            "journal_event_count": self.journal_event_count,
            "expected_effect_count": self.expected_effect_count,
            "denial_reason": self.denial_reason,
            "reason_codes": self.reason_codes,
            "passed": self.passed,
            "failure": self.failure,
            "in_safety_claim": self.in_safety_claim,
            "crypto": self.crypto,
            "policy": self.policy,
            "verifier_kind": self.verifier_kind,
            "notes": self.notes,
            "empirical_benchmark_result": False,
        }


class CountingDelegate:
    def __init__(self, fn: Callable[[], Any] | None = None) -> None:
        self.calls = 0
        self.fn = fn

    def __call__(self) -> Any:
        self.calls += 1
        if self.fn is not None:
            return self.fn()
        return {"status": "ok"}


@dataclass
class FixturePolicy:
    """Injected Profile D stand-in. Fixture only; not the datasets evaluator."""

    available: bool = True
    decision: str = "allow"
    fixture: bool = True
    provider: str = "la-011-fixture-profile-d"
    calls: list = field(default_factory=list)

    def metadata(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "available": self.available,
            "fail_closed": True,
            "fixture": True,
            "label": "fixture_only",
        }

    def evaluate(self, **kwargs: Any) -> dict[str, Any]:
        from ipfs_kit_py.mcp.profile_d_policy import policy_root

        self.calls.append(kwargs)
        return {
            "decision": self.decision,
            "policy_root": policy_root(kwargs.get("policy"), kwargs.get("policy_text")),
            "fixture": True,
        }


@dataclass
class FixtureVerifier:
    """Injected UCAN stand-in used only to label fixture-versus-live crypto."""

    allowed: bool = True
    fixture: bool = True
    calls: list = field(default_factory=list)

    def verify(self, chain: Any, **kwargs: Any) -> Any:
        self.calls.append({"chain": chain, **kwargs})

        class _Result:
            def __init__(self, allowed: bool) -> None:
                self.allowed = allowed
                self.code = "ok" if allowed else "fixture_denied"

            def to_receipt(self) -> dict[str, Any]:
                return {
                    "schema": "la-011-fixture-ucan-receipt",
                    "allowed": self.allowed,
                    "code": self.code,
                    "chain_length": 1,
                    "fixture": True,
                }

        return _Result(self.allowed)


def source_pins() -> dict[str, dict[str, str]]:
    files = {
        "admissibility_enforcement.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py",
        "execution_permit.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/execution_permit.py",
        "authorization.py": ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py",
        "ucan.py": ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/mcplusplus/ucan.py",
        "revocation.py": ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/mcplusplus/revocation.py",
        "server.py": ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/server.py",
        "profile_d_policy_kit.py": ROOT / "external/ipfs_kit/ipfs_kit_py/mcp/profile_d_policy.py",
        "profile_d_policy_datasets.py": ROOT
        / "external/ipfs_datasets/ipfs_datasets_py/logic/profile_d_policy.py",
        "receipt.py": ROOT / "external/ipfs_datasets/ipfs_datasets_py/logic/admissibility/receipt.py",
        "effects.py": HANDLERS,
        "test_ucan_verifier.py": ROOT
        / "external/ipfs_kit/tests/runtime_readiness/mcplusplus/test_ucan_verifier.py",
        "test_authorization_dispatch_gate.py": ROOT
        / "external/ipfs_kit/tests/runtime_readiness/mcplusplus/test_authorization_dispatch_gate.py",
    }
    return {
        name: {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
        for name, path in files.items()
        if path.is_file()
    }


def probe_environment() -> dict[str, Any]:
    import cryptography
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from ipfs_kit_py.mcp_server.mcplusplus import ucan as ucan_mod
    from ipfs_kit_py.mcp.profile_d_policy import ProfileDPolicyProvider
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        datasets_auth_available,
    )

    key = Ed25519PrivateKey.generate()
    return {
        "observed_at": utc_now(),
        "python": PYTHON,
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "python_sha256": sha256_file(Path(sys.executable)),
        "path": os.environ.get("PATH"),
        "home": os.environ.get("HOME"),
        "home_is_validation_prefix": "ipfs-accelerate-validation-home-"
        in str(os.environ.get("HOME", "")),
        "cryptography_version": cryptography.__version__,
        "cryptography_origin": getattr(cryptography, "__file__", None),
        "ed25519_generated": type(key).__name__,
        "HAVE_CRYPTO_ED25519": bool(ucan_mod.HAVE_CRYPTO_ED25519),
        "datasets_auth_available": datasets_auth_available(),
        "canonical_profile_d_available": bool(ProfileDPolicyProvider().available),
        "canonical_profile_d_error": str(ProfileDPolicyProvider()._load_error or ""),
        "anyio": importlib.util.find_spec("anyio") is not None,
        "multiformats": importlib.util.find_spec("multiformats") is not None,
        "mcp_server_importable": importlib.util.find_spec("anyio") is not None,
        "source_pins": source_pins(),
    }


def observe_export(state_dir: Path, run_id: str) -> dict[str, Any]:
    handlers = load_handlers()
    return handlers.EffectObserver(state_dir).observe(run_id=run_id)


def make_export_sandbox(job_id: str) -> tuple[Path, str, dict[str, Any], Callable[[], Any]]:
    handlers = load_handlers()
    state_dir = Path(tempfile.mkdtemp(prefix=f"la011-{job_id}-"))
    run_id = f"la011-{job_id}"
    instruction = {
        "operation": "export_json",
        "path": f"exports/{job_id}.json",
        "payload": {"job_id": job_id, "task": "LA-011"},
    }
    handler = handlers.BoundedExportHandler(state_dir)

    def delegate() -> Any:
        return handler.execute(instruction, run_id=run_id)

    return state_dir, run_id, instruction, delegate


def finish_effects(result: CaseResult, state_dir: Path, run_id: str, calls: int) -> None:
    result.handler_calls = calls
    observation = observe_export(state_dir, run_id)
    result.observed_effect_count = int(observation.get("observed_effect_count") or 0)
    result.journal_event_count = int(observation.get("journal_event_count") or 0)
    shutil.rmtree(state_dir, ignore_errors=True)


def mark(result: CaseResult) -> CaseResult:
    if result.failure:
        result.passed = False
        return result
    decision_ok = result.decision == result.expected_decision
    effects_ok = result.observed_effect_count == result.expected_effect_count
    calls_ok = (result.handler_calls > 0) == (result.expected_effect_count > 0) or (
        result.handler_calls == result.expected_effect_count
    )
    if result.expected_effect_count == 0:
        calls_ok = result.handler_calls == 0
        effects_ok = result.observed_effect_count == 0 and result.journal_event_count == 0
    else:
        calls_ok = result.handler_calls == result.expected_effect_count
        effects_ok = (
            result.observed_effect_count == result.expected_effect_count
            and result.journal_event_count == result.expected_effect_count
        )
    result.passed = bool(decision_ok and effects_ok and calls_ok)
    if not result.passed:
        result.failure = (
            f"decision={result.decision!r} expected={result.expected_decision!r} "
            f"calls={result.handler_calls} effects={result.observed_effect_count} "
            f"journal={result.journal_event_count} expected_effects={result.expected_effect_count}"
        )
    return result


# ---------------------------------------------------------------------------
# Supervisor ENFORCE / OFF / AUDIT / SHADOW
# ---------------------------------------------------------------------------


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
DIGEST_F = "f" * 64
DIGEST_1 = "1" * 64
DIGEST_2 = "2" * 64
ISSUED = "2026-07-28T12:00:00Z"
DEADLINE = "2026-07-28T12:05:00Z"
EXPIRY = "2026-07-28T12:10:00Z"
NOW_OK = "2026-07-28T12:02:00Z"
NOW_EXPIRED = "2026-07-28T12:11:00Z"


def receipt_modules():
    from ipfs_datasets_py.logic.admissibility.compose import InternalDecisionStatus
    from ipfs_datasets_py.logic.admissibility.receipt import (
        BoundContext,
        BoundRoots,
        build_decision_receipt,
        derive_capability,
    )

    return InternalDecisionStatus, BoundContext, BoundRoots, build_decision_receipt, derive_capability


def bound_roots(**overrides: Any):
    _, _, BoundRoots, _, _ = receipt_modules()
    base = {
        "policy_root": "policy:root-v1",
        "corpus_roots": ("corpus:legal-v1", "corpus:security-v1"),
        "revocation_root": "revocation:root-v1",
        "circuit_roots": ("circuit:auth-v1",),
        "vk_roots": ("vk:auth-v1",),
    }
    base.update(overrides)
    return BoundRoots(**base)


def bound_context(**overrides: Any):
    _, BoundContext, _, _, _ = receipt_modules()
    base = {
        "request_digest": DIGEST_A,
        "arguments_digest": DIGEST_B,
        "actor_id": "actor:alice",
        "audience_id": "audience:supervisor-dispatcher",
        "tool_id": "tool:supervisor.delegate",
        "tool_version": "1.0.0",
        "effect_ids": ("effect:filesystem.export_json", "effect:notify"),
        "environment_digest": DIGEST_C,
        "environment_id": "env:prod-sandbox",
        "delegation_ids": ("delegation:link-1",),
        "delegation_digest": DIGEST_D,
        "resource_ids": ("resource:tenant-a/exports/report.json",),
        "capability_ids": ("capability:write",),
        "nonce": "nonce-supervisor-001",
    }
    base.update(overrides)
    return BoundContext(**base)


def make_receipt(*, outcome=None, **overrides: Any):
    InternalDecisionStatus, _, _, build_decision_receipt, _ = receipt_modules()
    kwargs: dict[str, Any] = {
        "receipt_id": overrides.pop("receipt_id", "receipt:allow-supervisor-001"),
        "context": overrides.pop("context", bound_context()),
        "roots": overrides.pop("roots", bound_roots()),
        "outcome": outcome if outcome is not None else InternalDecisionStatus.ALLOW,
        "reasons": ("positive grant proved",),
        "reason_codes": ("allow.positive_grant",),
        "selected_evidence_cids": (
            "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
        ),
        "obligation_ids": ("obl:pre-check",),
        "residual_duties": (),
        "attempt_digests": (DIGEST_1,),
        "result_digests": (DIGEST_2,),
        "decision_digest": DIGEST_E,
        "policy_digest": DIGEST_F,
        "profile_id": "profile:closed-world",
        "issued_at": ISSUED,
        "deadline": DEADLINE,
        "expiry": EXPIRY,
        "producer_id": "producer:auth-service",
    }
    kwargs.update(overrides)
    return build_decision_receipt(**kwargs)


def make_capability(receipt: Any):
    _, _, _, _, derive_capability = receipt_modules()
    return derive_capability(
        receipt,
        capability_id="capability:supervisor-once",
        allowed_effects=("effect:filesystem.export_json",),
        require_strict_subset=True,
    )


def supervisor_context(**overrides: Any):
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        SupervisorInvocationContext,
    )

    base = {
        "actor_id": "actor:alice",
        "audience_id": "audience:supervisor-dispatcher",
        "tool_id": "tool:supervisor.delegate",
        "tool_version": "1.0.0",
        "request_digest": DIGEST_A,
        "arguments_digest": DIGEST_B,
        "environment_digest": DIGEST_C,
        "environment_id": "env:prod-sandbox",
        "effect_ids": ("effect:filesystem.export_json",),
        "task_id": "task:la-011",
        "plan_id": "plan:pre-dispatch",
        "delegation_ids": ("delegation:link-1",),
        "delegation_digest": DIGEST_D,
        "nonce": "nonce-supervisor-001",
        "resource_ids": ("resource:tenant-a/exports/report.json",),
    }
    base.update(overrides)
    return SupervisorInvocationContext(**base)


def run_enforcer(
    *,
    mode: str,
    context: Any,
    receipt: Any | None,
    capability: Any | None,
    job_id: str,
    expected_roots: Any | None = None,
    clock: Callable[[], str] | None = None,
    store: Any | None = None,
) -> tuple[Any, int, Path, str]:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        InMemoryCapabilityConsumptionStore,
        SupervisorPreInvocationEnforcement,
    )

    state_dir, run_id, _instruction, raw_delegate = make_export_sandbox(job_id)
    counter = CountingDelegate(raw_delegate)
    enforcer = SupervisorPreInvocationEnforcement(
        mode=mode,
        store=store or InMemoryCapabilityConsumptionStore(),
        expected_roots=expected_roots if expected_roots is not None else bound_roots(),
        clock=clock or (lambda: NOW_OK),
    )
    outcome = enforcer.authorize_and_delegate(
        context, counter, receipt=receipt, capability=capability
    )
    return outcome, counter.calls, state_dir, run_id


def map_enforce_decision(outcome: Any) -> str:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        EnforcementDisposition,
    )

    if outcome.observation.disposition is EnforcementDisposition.ALLOWED:
        return "allow"
    if outcome.observation.disposition is EnforcementDisposition.OFF:
        return "off-passthrough"
    if outcome.observation.disposition is EnforcementDisposition.AUDITED:
        return "audit-passthrough"
    if outcome.observation.disposition is EnforcementDisposition.SHADOW_ALLOWED:
        return "shadow-allow"
    if outcome.observation.disposition is EnforcementDisposition.SHADOW_WOULD_BLOCK:
        return "shadow-would-block"
    reason = outcome.observation.denial_reason or ""
    codes = tuple(outcome.observation.reason_codes or ())
    if reason in {"abstain"} or "abstain" in codes:
        return "unknown"
    if reason in {"reject", "not-allow"}:
        return "deny"
    if reason:
        return "deny"
    return "deny"


def enforce_cases() -> list[CaseResult]:
    InternalDecisionStatus, _, BoundRoots, _, _ = receipt_modules()
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        InMemoryCapabilityConsumptionStore,
    )

    results: list[CaseResult] = []
    allow_receipt = make_receipt()
    allow_cap = make_capability(allow_receipt)
    shared_store = InMemoryCapabilityConsumptionStore()
    off_allow_receipt = make_receipt(receipt_id="receipt:off-allow")
    audit_allow_receipt = make_receipt(receipt_id="receipt:audit-allow")
    shadow_allow_receipt = make_receipt(receipt_id="receipt:shadow-allow")

    specs = [
        {
            "job_id": "enforce-allow",
            "case_kind": "allow",
            "mutation": "none",
            "expected": "allow",
            "effects": 1,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(),
            "receipt": allow_receipt,
            "capability": allow_cap,
            "store": shared_store,
        },
        {
            "job_id": "enforce-replay",
            "case_kind": "deny",
            "mutation": "replay",
            "expected": "deny",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(),
            "receipt": allow_receipt,
            "capability": allow_cap,
            "store": shared_store,
        },
        {
            "job_id": "enforce-deny",
            "case_kind": "deny",
            "mutation": "deny-receipt",
            "expected": "deny",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(),
            "receipt": make_receipt(
                receipt_id="receipt:deny-1",
                outcome=InternalDecisionStatus.DENY,
                reasons=("negative grant",),
                reason_codes=("deny.prohibition",),
            ),
            "capability": None,
        },
        {
            "job_id": "enforce-unknown-indeterminate",
            "case_kind": "unknown",
            "mutation": "missing-evidence-indeterminate",
            "expected": "unknown",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(),
            "receipt": make_receipt(
                receipt_id="receipt:unknown-1",
                outcome=InternalDecisionStatus.INDETERMINATE,
                reasons=("missing evidence",),
                reason_codes=("unknown.missing_evidence",),
            ),
            "capability": None,
        },
        {
            "job_id": "enforce-wrong-audience",
            "case_kind": "context_mutation",
            "mutation": "wrong-audience",
            "expected": "deny",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(audience_id="audience:wrong"),
            "receipt": make_receipt(),
            "capability": make_capability(make_receipt()),
        },
        {
            "job_id": "enforce-wrong-actor",
            "case_kind": "context_mutation",
            "mutation": "wrong-actor",
            "expected": "deny",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(actor_id="actor:intruder"),
            "receipt": make_receipt(),
            "capability": make_capability(make_receipt()),
        },
        {
            "job_id": "enforce-changed-args",
            "case_kind": "context_mutation",
            "mutation": "changed-arguments",
            "expected": "deny",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(arguments_digest="9" * 64),
            "receipt": make_receipt(),
            "capability": make_capability(make_receipt()),
        },
        {
            "job_id": "enforce-undeclared-code-effect",
            "case_kind": "context_mutation",
            "mutation": "undeclared-generated-code-effect",
            "expected": "deny",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(
                effect_ids=("effect:filesystem.export_json", "effect:undeclared-network")
            ),
            "receipt": make_receipt(),
            "capability": make_capability(make_receipt()),
        },
        {
            "job_id": "enforce-environment-changed",
            "case_kind": "context_mutation",
            "mutation": "changed-live-environment",
            "expected": "deny",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(environment_digest="8" * 64),
            "receipt": make_receipt(),
            "capability": make_capability(make_receipt()),
        },
        {
            "job_id": "enforce-root-changed",
            "case_kind": "context_mutation",
            "mutation": "changed-roots",
            "expected": "deny",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(),
            "receipt": make_receipt(),
            "capability": make_capability(make_receipt()),
            "expected_roots": BoundRoots(
                policy_root="policy:root-v2",
                corpus_roots=("corpus:legal-v1", "corpus:security-v1"),
                revocation_root="revocation:root-v1",
                circuit_roots=("circuit:auth-v1",),
                vk_roots=("vk:auth-v1",),
            ),
        },
        {
            "job_id": "enforce-expired",
            "case_kind": "context_mutation",
            "mutation": "expired-capability",
            "expected": "deny",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(),
            "receipt": make_receipt(),
            "capability": make_capability(make_receipt()),
            "clock": lambda: NOW_EXPIRED,
        },
        {
            "job_id": "enforce-missing-receipt",
            "case_kind": "unknown",
            "mutation": "missing-receipt",
            "expected": "deny",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(),
            "receipt": None,
            "capability": None,
        },
        {
            "job_id": "enforce-tenant-ab-resource",
            "case_kind": "context_mutation",
            "mutation": "tenant-a-versus-tenant-ab",
            "expected": "deny",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(
                resource_ids=("resource:tenant-ab/exports/report.json",),
                arguments_digest="7" * 64,
            ),
            "receipt": make_receipt(),
            "capability": make_capability(make_receipt()),
        },
        {
            "job_id": "enforce-forged-proof-id",
            "case_kind": "context_mutation",
            "mutation": "forged-proof-identifiers",
            "expected": "deny",
            "effects": 0,
            "in_claim": True,
            "mode": "enforce",
            "context": supervisor_context(),
            "receipt": "forged",
            "capability": None,
        },
        {
            "job_id": "off-allow-passthrough",
            "case_kind": "allow",
            "mutation": "mode-off-bypass",
            "expected": "off-passthrough",
            "effects": 1,
            "in_claim": False,
            "mode": "off",
            "context": supervisor_context(),
            "receipt": off_allow_receipt,
            "capability": make_capability(off_allow_receipt),
        },
        {
            "job_id": "off-deny-still-effects",
            "case_kind": "deny",
            "mutation": "mode-off-ignores-deny",
            "expected": "off-passthrough",
            "effects": 1,
            "in_claim": False,
            "mode": "off",
            "context": supervisor_context(),
            "receipt": make_receipt(
                receipt_id="receipt:off-deny",
                outcome=InternalDecisionStatus.DENY,
                reasons=("would deny",),
                reason_codes=("deny.prohibition",),
            ),
            "capability": None,
        },
        {
            "job_id": "off-unknown-still-effects",
            "case_kind": "unknown",
            "mutation": "mode-off-missing-receipt",
            "expected": "off-passthrough",
            "effects": 1,
            "in_claim": False,
            "mode": "off",
            "context": supervisor_context(),
            "receipt": None,
            "capability": None,
        },
        {
            "job_id": "off-wrong-audience-still-effects",
            "case_kind": "context_mutation",
            "mutation": "mode-off-wrong-audience",
            "expected": "off-passthrough",
            "effects": 1,
            "in_claim": False,
            "mode": "off",
            "context": supervisor_context(audience_id="audience:wrong"),
            "receipt": make_receipt(),
            "capability": make_capability(make_receipt()),
        },
        {
            "job_id": "audit-allow-passthrough",
            "case_kind": "allow",
            "mutation": "mode-audit-allow",
            "expected": "audit-passthrough",
            "effects": 1,
            "in_claim": False,
            "mode": "audit",
            "context": supervisor_context(),
            "receipt": audit_allow_receipt,
            "capability": make_capability(audit_allow_receipt),
        },
        {
            "job_id": "audit-deny-still-effects",
            "case_kind": "deny",
            "mutation": "mode-audit-nonblocking",
            "expected": "audit-passthrough",
            "effects": 1,
            "in_claim": False,
            "mode": "audit",
            "context": supervisor_context(),
            "receipt": make_receipt(
                receipt_id="receipt:audit-deny",
                outcome=InternalDecisionStatus.DENY,
                reasons=("would deny",),
                reason_codes=("deny.prohibition",),
            ),
            "capability": None,
        },
        {
            "job_id": "audit-unknown-still-effects",
            "case_kind": "unknown",
            "mutation": "mode-audit-indeterminate",
            "expected": "audit-passthrough",
            "effects": 1,
            "in_claim": False,
            "mode": "audit",
            "context": supervisor_context(),
            "receipt": make_receipt(
                receipt_id="receipt:audit-unknown",
                outcome=InternalDecisionStatus.INDETERMINATE,
                reasons=("missing evidence",),
                reason_codes=("unknown.missing_evidence",),
            ),
            "capability": None,
        },
        {
            "job_id": "audit-wrong-audience-still-effects",
            "case_kind": "context_mutation",
            "mutation": "mode-audit-wrong-audience",
            "expected": "audit-passthrough",
            "effects": 1,
            "in_claim": False,
            "mode": "audit",
            "context": supervisor_context(audience_id="audience:wrong"),
            "receipt": make_receipt(receipt_id="receipt:audit-audience"),
            "capability": None,
        },
        {
            "job_id": "shadow-allow",
            "case_kind": "allow",
            "mutation": "mode-shadow-allow",
            "expected": "shadow-allow",
            "effects": 1,
            "in_claim": False,
            "mode": "shadow",
            "context": supervisor_context(),
            "receipt": shadow_allow_receipt,
            "capability": make_capability(shadow_allow_receipt),
        },
        {
            "job_id": "shadow-deny-still-effects",
            "case_kind": "deny",
            "mutation": "mode-shadow-nonblocking",
            "expected": "shadow-would-block",
            "effects": 1,
            "in_claim": False,
            "mode": "shadow",
            "context": supervisor_context(),
            "receipt": make_receipt(
                receipt_id="receipt:shadow-deny",
                outcome=InternalDecisionStatus.DENY,
                reasons=("would deny",),
                reason_codes=("deny.prohibition",),
            ),
            "capability": None,
        },
        {
            "job_id": "shadow-unknown-still-effects",
            "case_kind": "unknown",
            "mutation": "mode-shadow-indeterminate",
            "expected": "shadow-would-block",
            "effects": 1,
            "in_claim": False,
            "mode": "shadow",
            "context": supervisor_context(),
            "receipt": make_receipt(
                receipt_id="receipt:shadow-unknown",
                outcome=InternalDecisionStatus.INDETERMINATE,
                reasons=("missing evidence",),
                reason_codes=("unknown.missing_evidence",),
            ),
            "capability": None,
        },
        {
            "job_id": "shadow-wrong-audience-still-effects",
            "case_kind": "context_mutation",
            "mutation": "mode-shadow-wrong-audience",
            "expected": "shadow-would-block",
            "effects": 1,
            "in_claim": False,
            "mode": "shadow",
            "context": supervisor_context(audience_id="audience:wrong"),
            "receipt": make_receipt(receipt_id="receipt:shadow-audience"),
            "capability": None,
        },
    ]

    for spec in specs:
        result = CaseResult(
            job_id=spec["job_id"],
            route_id=(
                "supervisor_pre_invocation_enforce"
                if spec["mode"] == "enforce"
                else f"supervisor_pre_invocation_{spec['mode']}"
            ),
            case_kind=spec["case_kind"],
            mutation=spec["mutation"],
            expected_decision=spec["expected"],
            expected_effect_count=spec["effects"],
            in_safety_claim=spec["in_claim"],
            crypto="receipt-integrity-sha256",
            policy="proof-derived-capability",
            verifier_kind="datasets-decision-receipt",
        )
        try:
            receipt = spec["receipt"]
            if receipt == "forged":
                genuine = make_receipt()
                payload = genuine.to_dict()
                payload["selected_evidence_cids"] = [
                    "bafybeifaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                ]
                receipt = payload
            try:
                outcome, calls, state_dir, run_id = run_enforcer(
                    mode=spec["mode"],
                    context=spec["context"],
                    receipt=receipt,
                    capability=spec.get("capability"),
                    job_id=spec["job_id"],
                    expected_roots=spec.get("expected_roots"),
                    clock=spec.get("clock"),
                    store=spec.get("store"),
                )
            except Exception as raised:
                from ipfs_datasets_py.logic.admissibility.receipt import ReceiptError

                if spec["job_id"] == "enforce-forged-proof-id" and isinstance(raised, ReceiptError):
                    state_dir, run_id, _instruction, raw = make_export_sandbox(spec["job_id"])
                    result.decision = "deny"
                    result.delegated = False
                    result.denial_reason = "forged-receipt-integrity"
                    result.reason_codes = ["error", "forged-proof-identifier"]
                    result.notes = (
                        "from_dict raises ReceiptError instead of a deny observation; "
                        "delegate is not called. Isolated wrap recorded in mediation_changes.md."
                    )
                    finish_effects(result, state_dir, run_id, 0)
                    results.append(mark(result))
                    continue
                raise
            result.decision = map_enforce_decision(outcome)
            result.delegated = bool(outcome.delegate_called)
            result.denial_reason = str(outcome.observation.denial_reason or "")
            result.reason_codes = list(outcome.observation.reason_codes or ())
            finish_effects(result, state_dir, run_id, calls)
        except Exception as exc:  # noqa: BLE001
            result.failure = f"{type(exc).__name__}: {exc}"
            result.notes = traceback.format_exc()
        results.append(mark(result))
    return results


def direct_handler_bypass() -> list[CaseResult]:
    specs = [
        ("direct-handler-allow", "allow", "no-gate", "unprotected-allow"),
        ("direct-handler-deny-ignored", "deny", "no-gate-deny-request", "unprotected-allow"),
        ("direct-handler-unknown-ignored", "unknown", "no-gate-missing-evidence", "unprotected-allow"),
        ("direct-handler-wrong-audience-ignored", "context_mutation", "no-gate-wrong-audience", "unprotected-allow"),
    ]
    results: list[CaseResult] = []
    for job_id, case_kind, mutation, expected in specs:
        result = CaseResult(
            job_id=job_id,
            route_id="direct_bounded_export_handler",
            case_kind=case_kind,
            mutation=mutation,
            expected_decision=expected,
            expected_effect_count=1,
            in_safety_claim=False,
            crypto="none",
            policy="none",
            verifier_kind="none",
            notes="Reachable mutation without authorize_and_delegate; excluded from safety claim.",
        )
        try:
            state_dir, run_id, _instruction, delegate = make_export_sandbox(job_id)
            counter = CountingDelegate(delegate)
            counter()
            result.decision = "unprotected-allow"
            result.delegated = True
            finish_effects(result, state_dir, run_id, counter.calls)
        except Exception as exc:  # noqa: BLE001
            result.failure = f"{type(exc).__name__}: {exc}"
        results.append(mark(result))
    return results


# ---------------------------------------------------------------------------
# Real UCAN + AuthorizationGate
# ---------------------------------------------------------------------------


UCAN_ISSUER = "did:key:root-tenant-a"
UCAN_CLIENT = "did:client:tenant-a"
UCAN_SERVICE = "did:service:tenant-a"
UCAN_RESOURCE = "tenant-a/bucket-a/documents/report.txt"
UCAN_TOOL = "export_json"


def ucan_setup(tmp: Path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from ipfs_kit_py.mcp_server.mcplusplus.revocation import RevocationLedger
    from ipfs_kit_py.mcp_server.mcplusplus.ucan import UCANVerifier, public_key_bytes

    root_key = Ed25519PrivateKey.generate()
    service_key = Ed25519PrivateKey.generate()
    ledger = RevocationLedger(tmp / "ucan-ledger.json")
    ledger.register_public_key(UCAN_ISSUER, "root-v1", public_key_bytes(root_key))
    ledger.register_public_key(UCAN_SERVICE, "service-v1", public_key_bytes(service_key))
    verifier = UCANVerifier(ledger=ledger, trusted_issuers={UCAN_ISSUER})
    return ledger, verifier, root_key, service_key


def issue_token(key, *, nonce: str, **kwargs: Any) -> str:
    from ipfs_kit_py.mcp_server.mcplusplus.ucan import issue_ucan

    now = time.time()
    capability = kwargs.get("capability") or {"resource": UCAN_RESOURCE, "ability": UCAN_TOOL}
    return issue_ucan(
        issuer=kwargs.get("issuer", UCAN_ISSUER),
        audience=kwargs.get("audience", UCAN_CLIENT),
        capabilities=[capability],
        private_key=key,
        kid=kwargs.get("kid", "root-v1"),
        expires_at=kwargs.get("exp", now + 300),
        nonce=nonce,
        issued_at=kwargs.get("issued_at", now - 10),
        proofs=kwargs.get("proofs", ()),
        not_before=kwargs.get("nbf"),
    )


def gate_envelope(token: str | list[str], *, rid: str, resource: str = UCAN_RESOURCE, actor: str = UCAN_CLIENT, policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    from ipfs_kit_py.mcp.profile_d_policy import policy_root

    policy = policy or {
        "policy_id": "la-011-export",
        "clauses": [
            {
                "clause_type": "permission",
                "actor": actor,
                "action": UCAN_TOOL,
                "resource": resource,
            }
        ],
    }
    return {
        "tool": UCAN_TOOL,
        "resource": resource,
        "ability": UCAN_TOOL,
        "actor": actor,
        "ucan": token,
        "policy_root": policy_root(policy, None),
        "request_id": rid,
        "transaction_id": rid,
        "policy": policy,
    }


def run_gate_case(
    *,
    job_id: str,
    case_kind: str,
    mutation: str,
    expected: str,
    effects: int,
    in_claim: bool,
    crypto: str,
    policy_label: str,
    verifier_kind: str,
    setup: Callable[[Any, Any, Any, Any, Path], tuple[str, Mapping[str, Any], Any, Any]],
    notes: str = "",
) -> CaseResult:
    from ipfs_kit_py.mcp_server.authorization import AuthorizationDenied, AuthorizationGate
    from ipfs_kit_py.mcp_server.mcplusplus.event_dag import EventDAGStore
    from ipfs_kit_py.mcp_server import mcplusplus
    from ipfs_kit_py.mcp.profile_d_policy import ProfileDPolicyProvider

    result = CaseResult(
        job_id=job_id,
        route_id="ucan_gated_mcp_authorization_gate",
        case_kind=case_kind,
        mutation=mutation,
        expected_decision=expected,
        expected_effect_count=effects,
        in_safety_claim=in_claim,
        crypto=crypto,
        policy=policy_label,
        verifier_kind=verifier_kind,
        notes=notes,
    )
    tmp = Path(tempfile.mkdtemp(prefix=f"la011-gate-{job_id}-"))
    try:
        ledger, verifier, root_key, service_key = ucan_setup(tmp)
        token, arguments, policy_provider, gate_verifier = setup(
            ledger, verifier, root_key, service_key, tmp
        )
        dag = EventDAGStore(storage_dir=str(tmp / "dag"))
        gate = AuthorizationGate(
            policy_provider=policy_provider or ProfileDPolicyProvider(),
            ucan_verifier=gate_verifier,
            ledger=ledger,
            audit_store=dag,
            envelope_validator=mcplusplus.validate_packet,
            validator_available=True,
        )
        state_dir, run_id, _instruction, raw_delegate = make_export_sandbox(job_id)
        counter = CountingDelegate(raw_delegate)
        envelope = arguments.pop("_envelope")
        try:
            decision = gate.authorize(
                tool=UCAN_TOOL, arguments=arguments, envelope=envelope
            )
            counter()
            gate.record_effect(decision, {"status": "ok"})
            result.decision = "allow"
            result.delegated = True
        except AuthorizationDenied as denied:
            result.decision = "deny" if denied.code not in {"authorization_envelope_required"} else "unknown"
            if denied.code in {
                "ucan_required",
                "authorization_envelope_required",
                "envelope_validator_unavailable",
            }:
                result.decision = "unknown" if expected == "unknown" else "deny"
            result.denial_reason = denied.code
            result.reason_codes = [denied.code]
            result.delegated = False
        finish_effects(result, state_dir, run_id, counter.calls)
    except Exception as exc:  # noqa: BLE001
        result.failure = f"{type(exc).__name__}: {exc}"
        result.notes = (notes + "\n" + traceback.format_exc()).strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return mark(result)


def ucan_gate_cases() -> list[CaseResult]:
    from ipfs_kit_py.mcp.profile_d_policy import ProfileDPolicyProvider, policy_root
    from ipfs_kit_py.mcp_server.mcplusplus.ucan import resource_covers, ucan_token_id

    widening = {
        "tenant-a/* covers tenant-a/x": resource_covers("tenant-a/*", "tenant-a/x"),
        "tenant-a/* covers tenant-ab": resource_covers("tenant-a/*", "tenant-ab"),
        "tenant-a/* covers tenant-ab/x": resource_covers("tenant-a/*", "tenant-ab/x"),
    }
    write_json(SNAPSHOT / "probe" / "tenant-widening.json", widening)

    policy = {
        "policy_id": "la-011-export",
        "clauses": [
            {
                "clause_type": "permission",
                "actor": UCAN_CLIENT,
                "action": UCAN_TOOL,
                "resource": UCAN_RESOURCE,
            }
        ],
    }

    def args_for(token, rid, **extra):
        envelope = gate_envelope(token, rid=rid, policy=policy, **extra)
        body = {
            "resource": envelope["resource"],
            "policy": policy,
            "_envelope": envelope,
        }
        return token, body

    cases: list[CaseResult] = []

    def setup_allow(ledger, verifier, root, service, tmp):
        token = issue_token(root, nonce="allow-1")
        token, body = args_for(token, "req-allow")
        return token, body, FixturePolicy(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-allow-real-ucan-fixture-policy",
            case_kind="allow",
            mutation="none",
            expected="allow",
            effects=1,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_allow,
            notes="Allow path uses real UCAN and a fixture Profile D provider. Not the selected safety claim.",
        )
    )

    def setup_canonical(ledger, verifier, root, service, tmp):
        token = issue_token(root, nonce="canon-1")
        token, body = args_for(token, "req-canon")
        return token, body, ProfileDPolicyProvider(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-canonical-profile-d-unavailable",
            case_kind="unknown",
            mutation="canonical-profile-d-unavailable",
            expected="deny",
            effects=0,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="canonical-unavailable",
            verifier_kind="real-ucan-verifier",
            setup=setup_canonical,
            notes="Datasets Profile D evaluator cannot import multiformats; gate fail-closes.",
        )
    )

    def setup_wrong_aud(ledger, verifier, root, service, tmp):
        token = issue_token(root, nonce="aud-1", audience="did:wrong")
        token, body = args_for(token, "req-aud")
        return token, body, FixturePolicy(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-wrong-audience",
            case_kind="context_mutation",
            mutation="wrong-audience",
            expected="deny",
            effects=0,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_wrong_aud,
        )
    )

    def setup_tenant_ab(ledger, verifier, root, service, tmp):
        token = issue_token(
            root,
            nonce="ab-1",
            capability={"resource": "tenant-a/*", "ability": UCAN_TOOL},
        )
        envelope = gate_envelope(token, rid="req-ab", resource="tenant-ab/secret", policy=policy)
        body = {"resource": "tenant-ab/secret", "policy": policy, "_envelope": envelope}
        return token, body, FixturePolicy(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-tenant-ab-widening",
            case_kind="context_mutation",
            mutation="tenant-a-versus-tenant-ab",
            expected="deny",
            effects=0,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_tenant_ab,
        )
    )

    def setup_expired(ledger, verifier, root, service, tmp):
        token = issue_token(root, nonce="exp-1", exp=time.time() - 5, issued_at=time.time() - 30)
        token, body = args_for(token, "req-exp")
        return token, body, FixturePolicy(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-expired",
            case_kind="context_mutation",
            mutation="expired-token",
            expected="deny",
            effects=0,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_expired,
        )
    )

    def setup_revoked(ledger, verifier, root, service, tmp):
        token = issue_token(root, nonce="rev-1")
        ledger.revoke(ucan_token_id(token), reason="la-011-revocation")
        token, body = args_for(token, "req-rev")
        return token, body, FixturePolicy(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-revoked",
            case_kind="context_mutation",
            mutation="revoked-token",
            expected="deny",
            effects=0,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_revoked,
        )
    )

    def setup_forged(ledger, verifier, root, service, tmp):
        token = issue_token(root, nonce="forge-1")
        forged = token[:-8] + ("A" if token[-8] != "A" else "B") + token[-7:]
        token, body = args_for(forged, "req-forge")
        return forged, body, FixturePolicy(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-forged-signature",
            case_kind="context_mutation",
            mutation="forged-proof-identifiers",
            expected="deny",
            effects=0,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_forged,
        )
    )

    def setup_forged_key(ledger, verifier, root, service, tmp):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        token = issue_token(Ed25519PrivateKey.generate(), nonce="forge-key")
        token, body = args_for(token, "req-forge-key")
        return token, body, FixturePolicy(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-forged-untrusted-key",
            case_kind="context_mutation",
            mutation="untrusted-private-key",
            expected="deny",
            effects=0,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_forged_key,
        )
    )

    def setup_replay(ledger, verifier, root, service, tmp):
        token = issue_token(root, nonce="replay-1")
        # Consume the nonce through the real verifier first.
        verifier.verify(
            token,
            resource=UCAN_RESOURCE,
            ability=UCAN_TOOL,
            audience=UCAN_CLIENT,
            consume_nonce=True,
        )
        token, body = args_for(token, "req-replay")
        return token, body, FixturePolicy(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-replay",
            case_kind="context_mutation",
            mutation="replay",
            expected="deny",
            effects=0,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_replay,
        )
    )

    def setup_missing(ledger, verifier, root, service, tmp):
        envelope = gate_envelope("pending", rid="req-missing")
        envelope.pop("ucan")
        body = {"resource": UCAN_RESOURCE, "policy": policy, "_envelope": envelope}
        return "", body, FixturePolicy(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-missing-ucan",
            case_kind="unknown",
            mutation="missing-ucan",
            expected="deny",
            effects=0,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_missing,
        )
    )

    def setup_obligations(ledger, verifier, root, service, tmp):
        token = issue_token(root, nonce="obl-1")
        token, body = args_for(token, "req-obl")
        return token, body, FixturePolicy(decision="allow_with_obligations"), verifier

    cases.append(
        run_gate_case(
            job_id="gate-allow-with-obligations-denied",
            case_kind="deny",
            mutation="unresolved-obligations",
            expected="deny",
            effects=0,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_obligations,
            notes="Strict gate accepts plain allow only.",
        )
    )

    def setup_fixture_verifier(ledger, verifier, root, service, tmp):
        token = "eyJ.not-a-real-bearer-token.signature"
        envelope = gate_envelope(token, rid="req-fixture-ver")
        body = {"resource": UCAN_RESOURCE, "policy": policy, "_envelope": envelope}
        return token, body, FixturePolicy(), FixtureVerifier(allowed=True)

    cases.append(
        run_gate_case(
            job_id="gate-fixture-verifier-labeled",
            case_kind="allow",
            mutation="injected-test-verifier",
            expected="allow",
            effects=1,
            in_claim=False,
            crypto="fixture-verifier",
            policy_label="fixture-profile-d",
            verifier_kind="fixture-ucan-verifier",
            setup=setup_fixture_verifier,
            notes="Existing MCP dispatch tests inject this class of verifier. Fixture only.",
        )
    )

    def setup_changed_args(ledger, verifier, root, service, tmp):
        token = issue_token(root, nonce="args-1")
        envelope = gate_envelope(token, rid="req-args")
        body = {
            "resource": "tenant-b/other",
            "policy": policy,
            "_envelope": envelope,
        }
        return token, body, FixturePolicy(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-changed-resource-args",
            case_kind="context_mutation",
            mutation="changed-args-resource",
            expected="deny",
            effects=0,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_changed_args,
        )
    )

    def setup_parent_proof(ledger, verifier, root, service, tmp):
        now = time.time()
        parent = issue_token(
            root,
            nonce="parent-1",
            audience=UCAN_SERVICE,
            capability={"resource": "tenant-a/*", "ability": UCAN_TOOL},
            issued_at=now - 20,
            exp=now + 300,
        )
        child = issue_token(
            service,
            nonce="child-1",
            issuer=UCAN_SERVICE,
            kid="service-v1",
            proofs=(ucan_token_id(parent),),
            capability={"resource": UCAN_RESOURCE, "ability": UCAN_TOOL},
            issued_at=now - 10,
            exp=now + 240,
        )
        envelope = gate_envelope([parent, child], rid="req-chain")
        body = {"resource": UCAN_RESOURCE, "policy": policy, "_envelope": envelope}
        return [parent, child], body, FixturePolicy(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-attenuated-chain-allow",
            case_kind="allow",
            mutation="none-attenuated-chain",
            expected="allow",
            effects=1,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_parent_proof,
        )
    )

    def setup_widened_child(ledger, verifier, root, service, tmp):
        now = time.time()
        parent = issue_token(
            root,
            nonce="parent-w",
            audience=UCAN_SERVICE,
            capability={"resource": "tenant-a/*", "ability": UCAN_TOOL},
            issued_at=now - 20,
            exp=now + 300,
        )
        child = issue_token(
            service,
            nonce="child-w",
            issuer=UCAN_SERVICE,
            kid="service-v1",
            proofs=(ucan_token_id(parent),),
            capability={"resource": "tenant-ab/*", "ability": UCAN_TOOL},
            issued_at=now - 10,
            exp=now + 240,
        )
        envelope = gate_envelope([parent, child], rid="req-wide", resource="tenant-ab/secret")
        body = {"resource": "tenant-ab/secret", "policy": policy, "_envelope": envelope}
        return [parent, child], body, FixturePolicy(), verifier

    cases.append(
        run_gate_case(
            job_id="gate-child-widens-to-tenant-ab",
            case_kind="context_mutation",
            mutation="tenant-a-versus-tenant-ab-attenuation",
            expected="deny",
            effects=0,
            in_claim=False,
            crypto="real-ed25519",
            policy_label="fixture-profile-d",
            verifier_kind="real-ucan-verifier",
            setup=setup_widened_child,
        )
    )

    return cases


def profile_d_dispatcher_cases() -> list[CaseResult]:
    """Lightweight Profile D dispatcher: policy only, no UCAN. Not the safety claim."""

    results: list[CaseResult] = []
    matrix = [
        ("profile-d-fixture-allow", "allow", "none", "allow", 1, "allow"),
        ("profile-d-fixture-deny", "deny", "prohibition", "deny", 0, "deny"),
        ("profile-d-fixture-unknown", "unknown", "no-matching-permission", "deny", 0, "unknown-as-deny"),
        ("profile-d-fixture-obligations", "context_mutation", "allow-with-obligations", "deny", 0, "allow_with_obligations"),
    ]
    for job_id, case_kind, mutation, expected, effects, decision_in in matrix:
        result = CaseResult(
            job_id=job_id,
            route_id="profile_d_lightweight_dispatcher",
            case_kind=case_kind,
            mutation=mutation,
            expected_decision=expected,
            expected_effect_count=effects,
            in_safety_claim=False,
            crypto="none",
            policy="fixture-profile-d",
            verifier_kind="none",
            notes="Policy-only dispatcher omits UCAN. Enumerated bypass; excluded from safety claim.",
        )
        try:
            provider = FixturePolicy(
                decision=(
                    "allow"
                    if decision_in == "allow"
                    else "deny"
                    if decision_in in {"deny", "unknown-as-deny"}
                    else "allow_with_obligations"
                )
            )
            evaluation = provider.evaluate(
                actor=UCAN_CLIENT, action=UCAN_TOOL, resource=UCAN_RESOURCE, policy={"policy_id": "x"}
            )
            allowed = evaluation.get("decision") == "allow"
            state_dir, run_id, _instruction, raw = make_export_sandbox(job_id)
            counter = CountingDelegate(raw)
            if allowed:
                counter()
                result.decision = "allow"
                result.delegated = True
            else:
                result.decision = "deny"
                result.delegated = False
            finish_effects(result, state_dir, run_id, counter.calls)
        except Exception as exc:  # noqa: BLE001
            result.failure = f"{type(exc).__name__}: {exc}"
        results.append(mark(result))
    return results


def execution_permit_cases() -> list[CaseResult]:
    from ipfs_accelerate_py.agent_supervisor.control.execution_permit import (
        ExecutionAttempt,
        PermitReplayError,
        PermitVerificationError,
        PermitVerificationCode,
    )
    from test.api.test_agent_supervisor_execution_permit import NOW, _permit

    results: list[CaseResult] = []

    def run_one(job_id: str, case_kind: str, mutation: str, expected: str, effects: int, attempt_fn) -> CaseResult:
        result = CaseResult(
            job_id=job_id,
            route_id="execution_permit",
            case_kind=case_kind,
            mutation=mutation,
            expected_decision=expected,
            expected_effect_count=effects,
            in_safety_claim=False,
            crypto="none",
            policy="execution-permit",
            verifier_kind="execution-permit-verifier",
            notes="Related but nonidentical checks. Not the selected protected route.",
        )
        try:
            issuer, permit = _permit()
            verifier = issuer.verifier()
            state_dir, run_id, _instruction, raw = make_export_sandbox(job_id)
            counter = CountingDelegate(raw)
            try:
                attempt_fn(issuer, permit, verifier)
                counter()
                result.decision = "allow"
                result.delegated = True
            except PermitReplayError as exc:
                result.decision = "deny"
                result.denial_reason = str(exc.code.value if hasattr(exc.code, "value") else exc.code)
                result.reason_codes = [result.denial_reason]
            except PermitVerificationError as exc:
                result.decision = "deny"
                result.denial_reason = str(exc.code.value if hasattr(exc.code, "value") else exc.code)
                result.reason_codes = [result.denial_reason]
            finish_effects(result, state_dir, run_id, counter.calls)
        except Exception as exc:  # noqa: BLE001
            result.failure = f"{type(exc).__name__}: {exc}"
            result.notes = traceback.format_exc()
        return mark(result)

    results.append(
        run_one(
            "permit-allow",
            "allow",
            "none",
            "allow",
            1,
            lambda issuer, permit, verifier: verifier.verify(
                permit, ExecutionAttempt.from_permit(permit, now_ms=NOW + 1)
            ),
        )
    )

    def replay(issuer, permit, verifier):
        attempt = ExecutionAttempt.from_permit(permit, now_ms=NOW + 1)
        verifier.verify(permit, attempt)
        verifier.verify(permit, attempt)

    results.append(run_one("permit-replay", "deny", "replay", "deny", 0, replay))

    def wrong_caller(issuer, permit, verifier):
        verifier.verify(
            permit,
            ExecutionAttempt.from_permit(permit, now_ms=NOW + 1, caller="agent-supervisor:other"),
        )

    results.append(
        run_one(
            "permit-wrong-caller",
            "context_mutation",
            "wrong-audience-caller",
            "deny",
            0,
            wrong_caller,
        )
    )

    def path_widen(issuer, permit, verifier):
        verifier.verify(
            permit,
            ExecutionAttempt.from_permit(
                permit, now_ms=NOW + 1, actual_paths=("src/0.py", "src/escape.py")
            ),
        )

    results.append(
        run_one(
            "permit-path-widening",
            "context_mutation",
            "widened-path",
            "deny",
            0,
            path_widen,
        )
    )

    def expired(issuer, permit, verifier):
        verifier.verify(
            permit, ExecutionAttempt.from_permit(permit, now_ms=NOW + 120_000)
        )

    results.append(
        run_one("permit-expired", "context_mutation", "expired-permit", "deny", 0, expired)
    )

    def unknown_state(issuer, permit, verifier):
        # A verifier with neither trusted IDs nor resolver rejects.
        from ipfs_accelerate_py.agent_supervisor.control.execution_permit import (
            ExecutionPermitVerifier,
        )

        ExecutionPermitVerifier().verify(
            permit, ExecutionAttempt.from_permit(permit, now_ms=NOW + 1)
        )

    results.append(
        run_one(
            "permit-unknown-untrusted",
            "unknown",
            "missing-trust-authority",
            "deny",
            0,
            unknown_state,
        )
    )
    return results


def binding_cases() -> list[CaseResult]:
    """Explicit proof-capability / UCAN field binding. Production does not compose these."""

    result = CaseResult(
        job_id="binding-proof-capability-and-ucan-not-composed",
        route_id="proof_ucan_binding_adapter",
        case_kind="context_mutation",
        mutation="uncomposed-production-entry-point",
        expected_decision="deny",
        expected_effect_count=0,
        in_safety_claim=False,
        crypto="uncomposed",
        policy="uncomposed",
        verifier_kind="qualification-binding-check",
        notes=(
            "AuthorizationCapability and signed UCAN are distinct. Production "
            "authorize_and_delegate does not call UCANVerifier; AuthorizationGate "
            "does not verify DecisionReceipt. Combined A4 binding is uncomposed."
        ),
    )
    try:
        from ipfs_accelerate_py.agent_supervisor.proof import admissibility_enforcement as enf
        from ipfs_kit_py.mcp_server.authorization import AuthorizationGate

        source = Path(enf.__file__).read_text(encoding="utf-8")
        gate_source = Path(AuthorizationGate.__module__.replace(".", "/") )
        # Production enforcement source must not silently equate the formats.
        composed = "UCANVerifier" in source or "issue_ucan" in source
        result.decision = "deny"
        result.delegated = False
        result.handler_calls = 0
        result.observed_effect_count = 0
        result.passed = composed is False
        if composed:
            result.failure = "admissibility_enforcement unexpectedly imports UCANVerifier"
        result.notes += f" composed={composed} gate_module={AuthorizationGate.__module__}"
        del gate_source
    except Exception as exc:  # noqa: BLE001
        result.failure = f"{type(exc).__name__}: {exc}"
        result.passed = False
    return [result]


def build_inventory(env: dict[str, Any], cases: list[CaseResult]) -> dict[str, Any]:
    by_route: dict[str, list[CaseResult]] = {}
    for case in cases:
        by_route.setdefault(case.route_id, []).append(case)

    def kinds(route_id: str) -> dict[str, int]:
        rows = by_route.get(route_id, [])
        counts = {"allow": 0, "deny": 0, "unknown": 0, "context_mutation": 0}
        for row in rows:
            counts[row.case_kind] = counts.get(row.case_kind, 0) + 1
        return counts

    routes = [
        {
            "id": "supervisor_pre_invocation_enforce",
            "paper_name": "SupervisorPreInvocationEnforcement.authorize_and_delegate in enforce mode",
            "symbol": "SupervisorPreInvocationEnforcement.authorize_and_delegate",
            "path": "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py",
            "sha256": env["source_pins"]["admissibility_enforcement.py"]["sha256"],
            "protection": "protected",
            "in_safety_claim": True,
            "handler": "BoundedExportHandler.export_json",
            "crypto": "receipt-integrity-sha256 plus optional derived AuthorizationCapability",
            "tests": kinds("supervisor_pre_invocation_enforce"),
            "mode": "enforce",
        },
        {
            "id": "supervisor_pre_invocation_off",
            "paper_name": "Off mode pass-through",
            "symbol": "SupervisorPreInvocationEnforcement.authorize_and_delegate",
            "protection": "pass_through",
            "in_safety_claim": False,
            "reason": "Default OFF delegates without receipt verification or consumption.",
            "tests": kinds("supervisor_pre_invocation_off"),
        },
        {
            "id": "supervisor_pre_invocation_audit",
            "paper_name": "Audit mode",
            "protection": "observational",
            "in_safety_claim": False,
            "reason": "Audit records and still calls the delegate.",
            "tests": kinds("supervisor_pre_invocation_audit"),
        },
        {
            "id": "supervisor_pre_invocation_shadow",
            "paper_name": "Shadow mode",
            "protection": "observational",
            "in_safety_claim": False,
            "reason": "Shadow records would-block and still calls the delegate.",
            "tests": kinds("supervisor_pre_invocation_shadow"),
        },
        {
            "id": "execution_permit",
            "paper_name": "ExecutionPermit short-lived permit path",
            "symbol": "ExecutionPermitVerifier.verify",
            "path": "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/execution_permit.py",
            "sha256": env["source_pins"]["execution_permit.py"]["sha256"],
            "protection": "related_nonidentical",
            "in_safety_claim": False,
            "reason": "Plan admission is not the selected sandbox delegate boundary.",
            "tests": kinds("execution_permit"),
        },
        {
            "id": "ucan_gated_mcp_authorization_gate",
            "paper_name": "UCAN-gated MCP server tools/call via AuthorizationGate",
            "symbol": "AuthorizationGate.authorize",
            "path": "external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py",
            "sha256": env["source_pins"]["authorization.py"]["sha256"],
            "protection": "protected_but_not_selected",
            "in_safety_claim": False,
            "reason": "Qualified as the A3 capability/policy mechanism, not the selected complete-mediation claim.",
            "crypto": "real Ed25519 UCANVerifier; fixture Profile D labeled",
            "mcp_server_importable": env["mcp_server_importable"],
            "tests": kinds("ucan_gated_mcp_authorization_gate"),
        },
        {
            "id": "profile_d_lightweight_dispatcher",
            "paper_name": "Lightweight Profile D dispatcher",
            "symbol": "ProfileDPolicyProvider.evaluate",
            "path": "external/ipfs_kit/ipfs_kit_py/mcp/profile_d_policy.py",
            "protection": "compatibility_bypass",
            "in_safety_claim": False,
            "reason": "Policy-only path omits UCAN and exact proof-context binding.",
            "canonical_available": env["canonical_profile_d_available"],
            "tests": kinds("profile_d_lightweight_dispatcher"),
        },
        {
            "id": "direct_bounded_export_handler",
            "paper_name": "Historical compatibility: unguarded handler",
            "symbol": "BoundedExportHandler.execute",
            "protection": "unprotected",
            "in_safety_claim": False,
            "reason": "Reachable mutation without a gate. Enumerated and excluded.",
            "tests": kinds("direct_bounded_export_handler"),
        },
        {
            "id": "proof_ucan_binding_adapter",
            "paper_name": "Proof-derived AuthorizationCapability bound to signed UCAN",
            "protection": "uncomposed",
            "in_safety_claim": False,
            "reason": "Distinct formats; production does not compose them at one entry point.",
            "tests": kinds("proof_ucan_binding_adapter"),
        },
    ]
    return {
        "schema": "law-to-action-route-inventory/v1",
        "task": "LA-011",
        "qualified_at": env["observed_at"],
        "empirical_benchmark_result": False,
        "authoritative_environment": {
            "python": env["python"],
            "python_version": env["python_version"],
            "path": env["path"],
            "home_prefix": "ipfs-accelerate-validation-home-",
            "home_is_validation_prefix": env["home_is_validation_prefix"],
            "HAVE_CRYPTO_ED25519": env["HAVE_CRYPTO_ED25519"],
            "cryptography_version": env["cryptography_version"],
            "canonical_profile_d_available": env["canonical_profile_d_available"],
            "anyio": env["anyio"],
            "multiformats": env["multiformats"],
        },
        "selected_safety_claim": {
            "route_id": "supervisor_pre_invocation_enforce",
            "symbol": "SupervisorPreInvocationEnforcement.authorize_and_delegate",
            "mode": "enforce",
            "handler": "BoundedExportHandler.export_json",
            "includes_unprotected_routes": False,
            "includes_off_audit_shadow": False,
            "includes_execution_permit": False,
            "includes_mcp_dispatch": False,
            "includes_fixture_verifiers": False,
        },
        "paper_named_routes": [
            "SupervisorPreInvocationEnforcement.authorize_and_delegate",
            "off/audit/shadow modes",
            "ExecutionPermit",
            "lightweight Profile D dispatcher",
            "UCAN-gated MCP server AuthorizationGate/tools/call",
            "historical compatibility/unguarded handler",
        ],
        "routes": routes,
        "source_pins": env["source_pins"],
        "fixture_labels": [
            "la-011-fixture-profile-d",
            "la-011-fixture-ucan-receipt / FixtureVerifier",
            "existing test_authorization_dispatch_gate._Verifier/_PolicyProvider/BEARER",
        ],
        "claim_limits": [
            "Qualification, not a scored A3 or A4 benchmark.",
            "Canonical Profile D evaluator is unavailable without multiformats.",
            "MCPServer cannot be imported without anyio; AuthorizationGate is the tools/call check.",
            "InMemoryCapabilityConsumptionStore is process-local; restart safety is LA-012.",
        ],
    }


def qualification_markdown(inventory: dict[str, Any], cases: list[CaseResult], env: dict[str, Any]) -> str:
    selected = [c for c in cases if c.in_safety_claim]
    selected_pass = sum(1 for c in selected if c.passed)
    real_crypto = [c for c in cases if c.crypto == "real-ed25519"]
    fixture_crypto = [c for c in cases if c.crypto == "fixture-verifier"]
    failures = [c for c in cases if not c.passed]
    lines = [
        "# LA-011 complete mediation, strict capabilities, and exact live context",
        "",
        "This record qualifies named authorization routes under the sealed",
        "validation PATH. It is **not** a scored A3 or A4 benchmark.",
        "",
        "## Selected safety claim",
        "",
        "The only route included in the tested safety claim is",
        "`SupervisorPreInvocationEnforcement.authorize_and_delegate` in explicit",
        "`ENFORCE` mode around the benchmark-owned `BoundedExportHandler.export_json`",
        "mutation. Independent filesystem-journal effect counters are retained.",
        "",
        "- Mode: `enforce` (not the source default `off`)",
        "- Clock, roots, and receipt issuer: injected and pinned",
        "- Consumption store: process-local `InMemoryCapabilityConsumptionStore` (restart safety is LA-012)",
        "- Unprotected, observational, and nonidentical routes were tested and **excluded**",
        "",
        "## Authoritative environment",
        "",
        f"- Python: `{env['python']}` {env['python_version']}",
        f"- PATH: `{env['path']}`",
        f"- HOME prefix required: `ipfs-accelerate-validation-home-` (observed={env['home_is_validation_prefix']})",
        f"- Ed25519 provider: cryptography {env['cryptography_version']} (`HAVE_CRYPTO_ED25519={env['HAVE_CRYPTO_ED25519']}`)",
        f"- Canonical Profile D evaluator: {'available' if env['canonical_profile_d_available'] else 'unavailable (`multiformats` missing)'}",
        f"- MCPServer import: {'available' if env['anyio'] else 'unavailable (`anyio` missing); AuthorizationGate was executed directly'}",
        "",
        "## Paper-named routes and claim inclusion",
        "",
        "| Route | Protection | In safety claim | allow | deny | unknown | context-mutation |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for route in inventory["routes"]:
        tests = route.get("tests") or {}
        lines.append(
            f"| `{route['id']}` | {route.get('protection')} | {route.get('in_safety_claim')} | "
            f"{tests.get('allow', 0)} | {tests.get('deny', 0)} | {tests.get('unknown', 0)} | "
            f"{tests.get('context_mutation', 0)} |"
        )
    lines.extend(
        [
            "",
            "## Selected ENFORCE cases",
            "",
            f"Selected claim cases: {selected_pass}/{len(selected)} passed.",
            "",
            "| Job | Kind | Mutation | Decision | Effects | Pass |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for case in selected:
        lines.append(
            f"| `{case.job_id}` | {case.case_kind} | {case.mutation} | {case.decision} | "
            f"{case.observed_effect_count}/{case.expected_effect_count} | {case.passed} |"
        )
    lines.extend(
        [
            "",
            "## Real cryptographic verification",
            "",
            f"Real Ed25519 UCAN jobs executed: {len(real_crypto)}.",
            "Tokens were issued with `cryptography` Ed25519 and verified by `UCANVerifier`",
            "against a durable `RevocationLedger`. Injected verifiers are labeled fixtures.",
            "",
            "| Job | Mutation | Crypto | Decision | Effects | Pass |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for case in real_crypto:
        lines.append(
            f"| `{case.job_id}` | {case.mutation} | {case.crypto} | {case.decision} | "
            f"{case.observed_effect_count} | {case.passed} |"
        )
    lines.extend(
        [
            "",
            "## Fixture verifiers (not live crypto)",
            "",
        ]
    )
    for case in fixture_crypto:
        lines.append(
            f"- `{case.job_id}`: `{case.verifier_kind}` labeled `{case.crypto}`; "
            f"in_safety_claim={case.in_safety_claim}."
        )
    if not fixture_crypto:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Failures and limitations recorded",
            "",
        ]
    )
    if failures:
        for case in failures:
            lines.append(f"- `{case.job_id}`: {case.failure}")
    else:
        lines.append("- No case-level assertion failures. Dependency gaps remain as recorded limitations.")
    lines.extend(
        [
            "",
            "- Canonical `ipfs_datasets_py` Profile D evaluator is unavailable without `multiformats`.",
            "- `MCPServer` cannot be constructed without `anyio`; `tools/call` was exercised at `AuthorizationGate`.",
            "- Proof-derived `AuthorizationCapability` and signed UCAN are not composed at one production entry point.",
            "- Default `OFF` / `AUDIT` / `SHADOW` still produce handler effects and are outside the safety claim.",
            "- Direct `BoundedExportHandler.execute` is an unprotected reachable mutation and is outside the safety claim.",
            "- Durable consumption and restart safety are LA-012, not claimed here.",
            "- This is qualification evidence, not a scored A3/A4 forbidden-effect rate.",
            "",
        ]
    )
    return "\n".join(lines)


def mediation_changes_markdown(env: dict[str, Any], cases: list[CaseResult]) -> str:
    failures = [c for c in cases if not c.passed]
    return "\n".join(
        [
            "# LA-011 isolated mediation changes",
            "",
            "This task's allowed edit set is output-only. Production sources",
            "`admissibility_enforcement.py` and `authorization.py` were **not**",
            "modified. Boundary regressions ran against the existing gates.",
            "Failures and dependency gaps remain recorded in `raw.jsonl`.",
            "",
            "## Production source edits",
            "",
            "None applied. The existing `ENFORCE` adapter already:",
            "",
            "- blocks non-allow / unknown / expired / stale-root / context-mismatch receipts",
            "- consumes a one-time token before the delegate",
            "- leaves `OFF` / `AUDIT` / `SHADOW` as documented weaker modes",
            "",
            "The existing `AuthorizationGate` already:",
            "",
            "- requires envelope / tool / resource / ability / actor bindings",
            "- calls a concrete UCAN verifier and ledger",
            "- fail-closes when the canonical Profile D provider is unavailable",
            "- accepts plain `allow` only (not `allow_with_obligations`)",
            "- rejects `tenant-a/*` covering `tenant-ab` at the UCAN resource-cover check",
            "",
            "## Isolated proposed adapters (not applied)",
            "",
            "1. **Proof-capability ↔ UCAN binding adapter.** Production",
            "   `authorize_and_delegate` does not invoke `UCANVerifier`, and",
            "   `AuthorizationGate` does not verify `DecisionReceipt`. An isolated",
            "   adapter would deny unless actor, audience, tool/version, arguments",
            "   digest, effects, roots, and remaining use match across both",
            "   objects. Boundary regression:",
            "   `binding-proof-capability-and-ucan-not-composed`.",
            "2. **Canonical Profile D under sealed PATH.** The datasets evaluator",
            "   imports `multiformats`, which is absent. Do not substitute a",
            "   fixture evaluator when claiming A3 scored results. Boundary",
            "   regression: `gate-canonical-profile-d-unavailable` fail-closes.",
            "3. **MCPServer sealed-environment import.** `server.py` imports",
            "   `anyio`, which is absent. Gate tests therefore call",
            "   `AuthorizationGate` directly, which is the `tools/call` check.",
            "4. **Shared ExecutionPermit ledger.** `issuer.verifier()` without an",
            "   injected ledger creates a fresh in-memory ledger. Callers must",
            "   retain one verifier instance for replay. Boundary regression:",
            "   `permit-replay`.",
            "5. **Forged receipt integrity wrap.** `_coerce_receipt` lets",
            "   `DecisionReceipt.from_dict` raise `ReceiptError` instead of",
            "   returning a deny observation. The delegate is still not called.",
            "   An isolated wrap would map that exception to `error`/`deny`.",
            "   Boundary regression: `enforce-forged-proof-id`.",
            "",
            "## Boundary regressions executed",
            "",
            "Every paper-named route has allow, deny, unknown, and context-mutation",
            "effect-counter cases. Mutations include wrong audience, tenant-a versus",
            "tenant-ab, expiry, revocation, forged signatures/proof identifiers,",
            "changed arguments/effects/environment, missing evidence, undeclared",
            "generated-code effects, and replay.",
            "",
            "## Recorded failures",
            "",
        ]
        + (
            [f"- `{case.job_id}`: {case.failure}" for case in failures]
            if failures
            else ["- No applied source patch was required for the selected ENFORCE claim cases."]
        )
        + [
            "",
            "## Environment pins",
            "",
            f"- cryptography {env['cryptography_version']}; HAVE_CRYPTO_ED25519={env['HAVE_CRYPTO_ED25519']}",
            f"- datasets auth available: {env['datasets_auth_available']}",
            f"- canonical Profile D available: {env['canonical_profile_d_available']}",
            f"- anyio: {env['anyio']}; multiformats: {env['multiformats']}",
            "",
        ]
    )


def copy_outputs(inventory: dict[str, Any], records: list[dict[str, Any]], qualification: str, changes: str) -> None:
    raw_text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in records)
    mapping_json = {
        SNAPSHOT / "outputs" / "benchmark" / "route_inventory.json": inventory,
        LIVE / "benchmark" / "route_inventory.json": inventory,
    }
    for path, value in mapping_json.items():
        write_json(path, value)
    for path in (
        SNAPSHOT / "outputs" / "results" / "mediation" / "raw.jsonl",
        LIVE / "results" / "mediation" / "raw.jsonl",
    ):
        write_text(path, raw_text)
    for path in (
        SNAPSHOT / "outputs" / "results" / "mediation" / "qualification.md",
        LIVE / "results" / "mediation" / "qualification.md",
    ):
        write_text(path, qualification)
    for path in (
        SNAPSHOT / "outputs" / "patches" / "mediation_changes.md",
        LIVE / "patches" / "mediation_changes.md",
    ):
        write_text(path, changes)


def main() -> int:
    env = probe_environment()
    write_json(SNAPSHOT / "probe" / "sealed-environment.json", env)
    if not env["HAVE_CRYPTO_ED25519"]:
        write_json(SNAPSHOT / "probe" / "summary.json", {"status": "crypto_unavailable"})
        print("LA-011: Ed25519 cryptography unavailable under sealed PATH", file=sys.stderr)
        return 1

    cases: list[CaseResult] = []
    cases.extend(enforce_cases())
    cases.extend(direct_handler_bypass())
    cases.extend(ucan_gate_cases())
    cases.extend(profile_d_dispatcher_cases())
    cases.extend(execution_permit_cases())
    cases.extend(binding_cases())

    records = [case.to_record() for case in cases]
    write_json(SNAPSHOT / "traces" / "cases.json", records)
    inventory = build_inventory(env, cases)
    qualification = qualification_markdown(inventory, cases, env)
    changes = mediation_changes_markdown(env, cases)
    copy_outputs(inventory, records, qualification, changes)

    selected = [c for c in cases if c.in_safety_claim]
    real_crypto = [c for c in cases if c.crypto == "real-ed25519"]
    summary = {
        "status": "ok",
        "cases": len(cases),
        "passed": sum(1 for c in cases if c.passed),
        "failed": [c.job_id for c in cases if not c.passed],
        "selected_claim_cases": len(selected),
        "selected_claim_passed": sum(1 for c in selected if c.passed),
        "real_ed25519_jobs": len(real_crypto),
        "real_ed25519_passed": sum(1 for c in real_crypto if c.passed),
        "fixture_verifier_jobs": [c.job_id for c in cases if c.crypto == "fixture-verifier"],
        "unprotected_in_claim": any(c.in_safety_claim and c.route_id != "supervisor_pre_invocation_enforce" for c in cases),
        "HAVE_CRYPTO_ED25519": env["HAVE_CRYPTO_ED25519"],
        "canonical_profile_d_available": env["canonical_profile_d_available"],
        "empirical_benchmark_result": False,
    }
    write_json(SNAPSHOT / "probe" / "summary.json", summary)
    json.dump(summary, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    if summary["selected_claim_passed"] != summary["selected_claim_cases"]:
        return 1
    if summary["real_ed25519_jobs"] < 8:
        return 1
    if not env["HAVE_CRYPTO_ED25519"]:
        return 1
    if summary["unprotected_in_claim"]:
        return 1
    if not summary["fixture_verifier_jobs"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
