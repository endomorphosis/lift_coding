#!/usr/bin/env python3
"""Validate NS-008 published provider-gate qualification artifacts.

Stdlib plus the sealed kernel/gate/invocation sources. Re-checks structural
invariants and performs a live smoke of deterministic close, residual
authorization, capability deferral, and deny-all non-progress. Does not claim
a live A–D experiment or a production model identity.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import runpy
import sys


ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP = PAPER / "receipts/snapshots/NS-008"
SNAP_QUAL = SNAP / "qualification"
RUNNER = SNAP / "run_provider_gate_qualification.py"
PROVIDER = SNAP / "residual_provider.py"

CRITERIA = (
    "At least one valid residual request reaches the intended real provider and produces a traceable independently checked outcome.",
    "At least one deterministic closure progresses without a provider call and passes the fixed oracle.",
    "Each invalid pair fails for the expected binding/authority reason; missing capabilities stay unavailable.",
    "No workflow-level savings are inferred from zero hooks inside the kernel, and deny-all cannot pass useful-progress criteria.",
)

REQUIRED_CASES = (
    "residual_authorized_progress",
    "deterministic_unique_close",
    "closes_claim_untrusted",
    "residual_missing_authority_receipts",
    "residual_mismatched_task",
    "residual_mismatched_forest",
    "residual_mismatched_views",
    "residual_gate_omits_views",
    "residual_forged_receipt_identity",
    "residual_missing_packet",
    "ambiguous_candidates",
    "missing_planner",
    "missing_doctor",
    "production_llm_unavailable",
    "unknown_provider_effect",
    "repeated_residual_no_blind_retry",
    "deny_all_control",
    "authorization_permit_execute",
    "authorization_deny_task_scope",
)

INVALID_BINDING_CASES = (
    "residual_missing_authority_receipts",
    "residual_mismatched_task",
    "residual_mismatched_forest",
    "residual_mismatched_views",
    "residual_gate_omits_views",
    "residual_forged_receipt_identity",
    "residual_missing_packet",
    "authorization_deny_task_scope",
)

UNAVAILABLE_CASES = (
    "missing_planner",
    "missing_doctor",
    "production_llm_unavailable",
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"NS-008 validation failed: {message}")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    cases_path = QUAL / "provider_gate_cases.json"
    receipts_path = QUAL / "provider_gate_receipts.jsonl"
    report_path = QUAL / "provider_gate_report.md"
    for path in (cases_path, receipts_path, report_path, RUNNER, PROVIDER):
        if not path.is_file():
            fail(f"missing {path}")

    cases = load_json(cases_path)
    rows = load_jsonl(receipts_path)
    report = report_path.read_text(encoding="utf-8")

    if cases.get("schema") != "neurosymbolic-supervision/provider-gate-cases@1":
        fail("unexpected cases schema")
    if cases.get("task_id") != "NS-008":
        fail("cases task_id mismatch")
    if cases.get("rules", {}).get("kernel_zero_hooks_are_not_workflow_savings") is not True:
        fail("cases omitted kernel-zero-hooks-are-not-savings rule")
    if cases.get("rules", {}).get("deny_all_cannot_pass_useful_progress") is not True:
        fail("cases omitted deny-all rule")
    if cases.get("intended_provider", {}).get("admitted_production") is not False:
        fail("intended provider must not be admitted production")
    if not rows:
        fail("empty receipts")
    if any(row.get("schema") != "neurosymbolic-supervision/provider-gate-receipt@1" for row in rows):
        fail("receipt schema mismatch")

    by_id = {row["case_id"]: row for row in rows}
    missing = [name for name in REQUIRED_CASES if name not in by_id]
    if missing:
        fail(f"missing required cases: {missing}")

    for row in rows:
        if row.get("status") != "pass":
            fail(f"case failed: {row['case_id']}")
        if row.get("workflow_savings_inferred") is not False:
            fail(f"workflow savings inferred: {row['case_id']}")
        if row.get("closes_claim_trusted") is True:
            fail(f"closes_claim was trusted: {row['case_id']}")
        hooks = row.get("kernel_provider_hook_count")
        if hooks not in (0, None):
            fail(f"kernel hook count is not zero: {row['case_id']}")

    residual = by_id["residual_authorized_progress"]
    if residual.get("useful_progress") is not True:
        fail("valid residual did not produce independently checked progress")
    if residual.get("provider_authorized") is not True:
        fail("valid residual was not provider-authorized")
    invocation = residual.get("invocation") or {}
    if invocation.get("invoked") is not True:
        fail("valid residual did not invoke the provider")
    invoked_count = invocation.get("actual_process_invocations") or invocation.get("provider_hook_count") or 0
    if int(invoked_count) < 1:
        fail("valid residual invocation count was not counted at the provider boundary")
    if residual.get("served_provider_id") != cases["intended_provider"]["id"]:
        fail("valid residual did not reach the intended provider identity")
    oracle = residual.get("independent_oracle") or {}
    if oracle.get("passed") is not True or oracle.get("independent_of_closes_claim") is not True:
        fail("valid residual lacked an independent oracle pass")
    if residual.get("admitted_production") is True:
        fail("qualification residual was labeled admitted production")

    deterministic = by_id["deterministic_unique_close"]
    if deterministic.get("useful_progress") is not True:
        fail("deterministic close did not pass the independent oracle")
    if deterministic.get("provider_authorized") is not False:
        fail("deterministic close authorized a provider")
    if deterministic.get("dispatch_blocked") is not True:
        fail("deterministic close did not block provider dispatch")
    if (deterministic.get("independent_oracle") or {}).get("passed") is not True:
        fail("deterministic close oracle did not pass")
    if (deterministic.get("analytical_close") or {}).get("applied") is not True:
        fail("deterministic close did not apply a real mutation")
    if (deterministic.get("analytical_close") or {}).get("mutated") is not True:
        fail("deterministic close reported apply without mutation")

    untrusted = by_id["closes_claim_untrusted"]
    if untrusted.get("useful_progress") is not False:
        fail("untrusted closes_claim was treated as useful progress")
    if (untrusted.get("independent_oracle") or {}).get("passed") is True:
        fail("unfixed closes_claim fixture unexpectedly passed the oracle")

    for name in INVALID_BINDING_CASES:
        row = by_id[name]
        if row.get("provider_authorized") is True:
            fail(f"invalid pair authorized a provider: {name}")
        if row.get("useful_progress") is True:
            fail(f"invalid pair reported useful progress: {name}")
        if row.get("reason_matched") is not True:
            fail(f"invalid pair reason mismatch: {name} observed={row.get('observed_reason')}")

    for name in UNAVAILABLE_CASES:
        row = by_id[name]
        if row.get("capability_available") is not False:
            fail(f"missing capability was marked available: {name}")
        if row.get("useful_progress") is True:
            fail(f"unavailable capability reported useful progress: {name}")
        if name != "production_llm_unavailable" and row.get("provider_authorized") is True:
            fail(f"unavailable capability authorized a provider: {name}")

    deny = by_id["deny_all_control"]
    if deny.get("useful_progress") is not False:
        fail("deny-all passed useful-progress criteria")
    if deny.get("deny_all_useful_progress") is not False:
        fail("deny-all flag was not false")
    if deny.get("provider_called") is not False:
        fail("deny-all called a provider")

    if "provider_hook_count=0" not in report and "provider_hook_count = 0" not in report.replace(" ", ""):
        if "provider_hook_count=0" not in report:
            fail("report omitted kernel zero-hook non-saving explanation")
    if "Deny-all" not in report and "deny-all" not in report:
        fail("report omitted deny-all limitation")
    if "closes_claim" not in report:
        fail("report omitted closes_claim limitation")
    if "admitted_production" not in report and "production" not in report.lower():
        fail("report omitted production-identity limitation")
    if "ResidualProviderInvocation" not in report:
        fail("report omitted residual invocation wrapper")
    if "AnalyticalCloseExecutor" not in report:
        fail("report omitted analytical close executor")

    for name in ("provider_gate_cases.json", "provider_gate_receipts.jsonl", "provider_gate_report.md"):
        current = QUAL / name
        snapshot = SNAP_QUAL / name
        if not snapshot.is_file():
            fail(f"missing snapshot {snapshot}")
        if digest(current) != digest(snapshot):
            fail(f"current output differs from snapshot: {name}")

    sys.path.insert(0, str(SNAP))
    runner = runpy.run_path(str(RUNNER))
    capability = runner["prepare_imports"]()
    api = capability["api"]
    Candidate = api["AnalyticalRepairCandidate"]
    roots = runner["forest"](api, salt="validate")
    task_cid = runner["cid"](api, "validate-task")
    closed = runner["evaluate_bound_gate"](
        api,
        task_cid=task_cid,
        forest_roots=roots,
        analytical_candidates=(Candidate(candidate_id="only", closes_claim=True),),
    )
    if closed.disposition.value != "closed_deterministic" or closed.provider_authorized or closed.provider_hook_count != 0:
        fail("live smoke: unique analytical candidate did not close without a provider")
    missing = runner["evaluate_bound_gate"](
        api,
        task_cid=task_cid,
        forest_roots=roots,
        planner_available=False,
        analytical_candidates=(Candidate(candidate_id="only", closes_claim=True),),
    )
    if missing.disposition.value != "defer_capability" or missing.provider_authorized:
        fail("live smoke: missing planner did not defer")

    receipts = runner["authority_receipts"](
        api, task_cid=task_cid, forest_cid=roots.repository_forest_cid
    )
    receipt_cids = {kind: item["content_id"] for kind, item in receipts.items()}
    packet = runner["seal_packet"](
        api,
        task_id="NS-008-validate",
        forest_id=roots.repository_forest_cid,
        tree_id=roots.git_tree_id,
    )
    authorized = runner["evaluate_bound_gate"](
        api,
        task_cid=task_cid,
        forest_roots=roots,
        residual_packet_cid=packet.packet_id or packet.content_id,
        analytical_candidates=(Candidate(candidate_id="non-closing", closes_claim=False),),
        authority_receipt_cids=receipt_cids,
        authority_receipt_resolver=runner["resolver_for"](receipts),
        obligation_graph_cid=receipt_cids["obligation"],
        plan_cid=receipt_cids["planner"],
        doctor_cid=receipt_cids["doctor"],
    )
    if authorized.disposition.value != "residual_llm_authorized" or not authorized.provider_authorized:
        fail("live smoke: exact bindings did not authorize residual dispatch")
    gate = api["evaluate_provider_gate"](
        task_cid=task_cid,
        forest_roots=roots,
        residual_packet_cid=packet.packet_id or packet.content_id,
        analytical_candidates=(Candidate(candidate_id="non-closing", closes_claim=False),),
        authority_receipt_cids=receipt_cids,
        authority_receipt_resolver=runner["resolver_for"](receipts),
    )
    if gate.provider_authorized:
        fail("live smoke: thin gate helper authorized residual without view CIDs")

    print("NS-008 provider-gate qualification: OK")
    print(f"rows={len(rows)} required={len(REQUIRED_CASES)}")
    print("residual=independently_checked; deterministic=oracle_pass_no_provider")
    print("invalid_pairs=expected_reasons; deny_all=not_useful_progress; kernel_hooks=not_savings")
    print("live_smoke=closed_deterministic,defer_capability,residual_authorized,thin_gate_blocked")


if __name__ == "__main__":
    main()
