#!/usr/bin/env python3
"""Compile residual SCA findings into typed MCP obligations and prove + kernel-gate.

Pipeline:
1. Load residual SCA findings (incomplete / ambiguous_*)
2. Map each finding → reviewed ``McpClaimFamily`` set
3. Build a minimal catalog entry (source + contract) per family
4. ``compile_contract_claim`` → typed ``McpContractObligation``
5. ``McpContractProver.prove`` via all datasets logic backends
6. ``verify_kernel_reconstruction`` on empty inputs (must fail-closed) and on
   any reconstruction artifacts present in provider output

Does **not** mint KERNEL_VERIFIED receipts. Solver outcomes stay candidate /
inconclusive until independent reconstruction admits them.

Usage:
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit \\
    python3 scripts/sca_obligation_kernel_pipeline.py [--max-tasks 6]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
SCA = REPO / "data" / "agent_supervisor" / "swissknife_contract_assurance"
FINDINGS = SCA / "baseline" / "runtime_components" / "findings.json"
CONTRACT_FINDINGS = SCA / "baseline" / "runtime_components" / "contract_findings.json"
SUMMARY = SCA / "baseline" / "runtime_components" / "summary.json"
REPORT = SCA / "evaluation" / "obligation_kernel_pipeline_report.json"
ENV_FILE = SCA / "evaluation" / "mcp_endpoints" / "endpoints.env"

DEFAULT_MANAGED_BIN = (
    Path.home() / ".local" / "share" / "ipfs_datasets_py" / "theorem-provers" / "bin"
)

# Finding kind → claim families (McpClaimFamily.value PascalCase strings).
# Covers all PARITY_CLAIM_FAMILIES so residual work exercises every prove route
# (schema / deontic-CEC / relation-SMT / …).
FINDING_CLAIM_FAMILIES: dict[str, tuple[str, ...]] = {
    "observed_contract_incomplete": (
        "ArgumentsPreserved",
        "DescriptorSchemaMatches",
        "PolicyBeforeEffect",
        "ResultEnvelopePreserved",
    ),
    "ambiguous_source_anchor": (
        "DiscoveryExecutionParity",
        "ArgumentsPreserved",
        "DescriptorSchemaMatches",
        "TransportParity",
    ),
    "ambiguous_target_anchor": (
        "DiscoveryExecutionParity",
        "PolicyBeforeEffect",
        "FailureParity",
        "ArgumentsPreserved",
    ),
    "ambiguous_path_class": (
        "NoCompatibilityBypass",
        "PolicyBeforeEffect",
        "TransportParity",
        "DiscoveryExecutionParity",
        "FailureParity",
    ),
}

OP_CLAIM_EXTRA: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (
        ("dispatch", "tools_", "policy", "auth", "ucan", "session", "mcpplusplus"),
        ("PolicyBeforeEffect", "NoCompatibilityBypass"),
    ),
    (
        ("workflow", "submit", "dag", "temporal", "schedule"),
        ("ArgumentsPreserved",),
    ),
]


def _setup() -> None:
    os.chdir(REPO)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export ") :]
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    managed = Path(
        os.environ.get("IPFS_THEOREM_PROVERS_BIN")
        or os.environ.get("SCA_THEOREM_PROVERS_BIN")
        or DEFAULT_MANAGED_BIN
    ).expanduser()
    if managed.is_dir():
        managed_s = str(managed.resolve())
        path = os.environ.get("PATH", "")
        if managed_s not in path.split(os.pathsep):
            os.environ["PATH"] = managed_s + os.pathsep + path
    sys.path[:0] = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "external" / "ipfs_kit"),
        str(REPO / "Mcp-Plus-Plus"),
        str(SCA / "runtime" / "pythonpath"),
    ]


def load_findings(max_tasks: int) -> list[dict[str, Any]]:
    want = set(FINDING_CLAIM_FAMILIES)
    by_id: dict[str, dict[str, Any]] = {}
    for path in (CONTRACT_FINDINGS, FINDINGS):
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for item in doc.get("findings") or []:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or item.get("reason_code") or "")
            if kind not in want:
                continue
            fid = str(item.get("finding_id") or item.get("id") or "")
            key = fid or f"{kind}:{item.get('contract_id')}"
            by_id[key] = item
    return list(by_id.values())[:max_tasks]


def claim_families_for(kind: str, op: str) -> list[str]:
    fams = list(FINDING_CLAIM_FAMILIES.get(kind, ("ArgumentsPreserved",)))
    op_l = op.lower()
    for tokens, extra in OP_CLAIM_EXTRA:
        if any(t in op_l for t in tokens):
            for f in extra:
                if f not in fams:
                    fams.append(f)
    return fams


def _resolve_claim_family(name: str):
    """Resolve PascalCase value or enum member name to McpClaimFamily."""
    from ipfs_accelerate_py.agent_supervisor.analysis.mcp_contract_catalog import (
        McpClaimFamily,
    )

    try:
        return McpClaimFamily(name)
    except ValueError:
        pass
    # Allow snake_case / member name
    normalized = name.replace("-", "_")
    for item in McpClaimFamily:
        if item.name.lower() == normalized.lower() or item.value.lower() == name.lower():
            return item
    raise ValueError(f"unknown_claim_family:{name}")


def _source_kind_for_family(family_value: str):
    from ipfs_accelerate_py.agent_supervisor.analysis.mcp_contract_catalog import (
        ContractSourceKind,
    )

    if family_value in {
        "PolicyBeforeEffect",
        "NoCompatibilityBypass",
        "NoDynamicAuthority",
        "policy_before_effect",
        "no_compatibility_bypass",
    }:
        return ContractSourceKind.POLICY_CONTRACT
    if family_value in {
        "TransportParity",
        "DiscoveryExecutionParity",
        "FailureParity",
        "transport_parity",
        "discovery_execution_parity",
    }:
        return ContractSourceKind.TYPED_INTERFACE
    return ContractSourceKind.JSON_SCHEMA


def compile_finding_obligations(
    item: dict[str, Any],
    *,
    snapshot_id: str,
    repository_id: str = "repository:swissknife-sca",
) -> list[dict[str, Any]]:
    from ipfs_accelerate_py.agent_supervisor.analysis.mcp_contract_analysis import (
        ContractParityClaim,
        ParityState,
    )
    from ipfs_accelerate_py.agent_supervisor.analysis.mcp_contract_catalog import (
        DEFAULT_MCP_CONTRACT_CATALOG,
        McpClaimFamily,
        admit_source,
        build_contract_from_sources,
        make_source_record,
        register_contract,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.formal_verification_contracts import (
        AssuranceLevel,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.mcp_contract_obligations import (
        compile_contract_claim,
    )

    contract_id = str(item.get("contract_id") or "")
    kind = str(item.get("kind") or item.get("reason_code") or "")
    finding_id = str(item.get("finding_id") or item.get("id") or contract_id)
    op = contract_id.split(":", 1)[-1] if ":" in contract_id else contract_id
    package = contract_id.split(":", 1)[0] if ":" in contract_id else "ipfs_accelerate_py"
    families = claim_families_for(kind, op)

    rows: list[dict[str, Any]] = []
    for fam_name in families:
        try:
            family = _resolve_claim_family(fam_name)
            fam_name = family.value
        except ValueError as exc:
            rows.append(
                {
                    "family": fam_name,
                    "compiled": False,
                    "error": str(exc),
                }
            )
            continue
        try:
            source = make_source_record(
                kind=_source_kind_for_family(fam_name),
                subject=op,
                source_version="sca-residual-1",
                schema_version="1",
                path=f"sca/findings/{package}/{op}/{fam_name}.json",
                payload_fingerprint=f"sha256:sca:{finding_id}:{fam_name}",
            )
            catalog = admit_source(DEFAULT_MCP_CONTRACT_CATALOG, source)
            contract, contradictions = build_contract_from_sources(
                claim_family=family,
                subject=op,
                sources=(source,),
                tool_name=op,
                package_id=package,
            )
            catalog = register_contract(
                catalog, contract, contradictions=contradictions
            )
            claim = ContractParityClaim(
                family=family,
                state=ParityState.AMBIGUOUS,
                operation_id=op,
                premise_ids=(
                    f"premise:finding:{finding_id or op}",
                    f"premise:contract:{contract_id or op}",
                    f"premise:snapshot:{snapshot_id or 'unknown'}",
                    "premise:mcp-mediation-required",
                ),
                reason_codes=(f"sca_{kind}" if kind else "sca_residual_finding",),
            )
            # Candidate-level assurance: kernel still required for promotion
            obligation = compile_contract_claim(
                claim,
                catalog=catalog,
                contract=contract.contract_id,
                repository_id=repository_id,
                snapshot_id=snapshot_id or f"tree:sca-{finding_id or op}",
                scope_ids=(
                    f"scope:package:{package}",
                    f"scope:operation:{op}",
                    f"scope:finding:{finding_id or op}",
                ),
                assumption_ids=(
                    "assumption:sca-residual-open",
                    "assumption:mcp-interop-for-cross-package",
                ),
                toolchain_id="toolchain:sca-obligation-kernel-pipeline@1",
                policy_id="policy:sca-symbolic-repair@1",
                required_assurance=AssuranceLevel.SOLVER_CHECKED,
            )
            logic_statement = ""
            try:
                logic_statement = str(
                    obligation.logic_view.statement
                    if hasattr(obligation, "logic_view")
                    else obligation.code_obligation.statement
                )
            except Exception:  # noqa: BLE001
                logic_statement = str(
                    getattr(obligation.code_obligation, "statement", "") or ""
                )
            rows.append(
                {
                    "family": fam_name,
                    "compiled": True,
                    "obligation_id": obligation.obligation_id,
                    "compiled_obligation_id": obligation.compiled_obligation_id,
                    "logic_fragment": (
                        obligation.logic_fragment.value
                        if hasattr(obligation.logic_fragment, "value")
                        else str(obligation.logic_fragment)
                    ),
                    "logic_statement": logic_statement,
                    "logic_operator": (
                        obligation.logic_view.operator.value
                        if hasattr(obligation, "logic_view")
                        and hasattr(obligation.logic_view.operator, "value")
                        else ""
                    ),
                    "supported": bool(obligation.supported),
                    "required_assurance": (
                        obligation.required_assurance.value
                        if hasattr(obligation.required_assurance, "value")
                        else str(obligation.required_assurance)
                    ),
                    "contract_id": obligation.contract_id,
                    "snapshot_id": obligation.snapshot_id,
                    "premise_ids": list(obligation.premise_ids),
                    "scope_ids": list(obligation.scope_ids),
                    "code_claim_status": (
                        obligation.code_claim.status.value
                        if hasattr(obligation.code_claim.status, "value")
                        else str(obligation.code_claim.status)
                    ),
                    "_obligation": obligation,  # stripped before report write
                }
            )
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "family": fam_name,
                    "compiled": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return rows


def _facts_for_fragment(fragment: str, premise_ids: list[str]) -> dict[str, Any]:
    """Bounded observation facts for local routes; empty for provider routes."""
    base = {
        "premise_results": {p: True for p in premise_ids},
        "satisfied_premise_ids": list(premise_ids),
    }
    if fragment == "schema":
        return {
            **base,
            "schema_valid": True,
            "schema_results": {p: True for p in premise_ids},
        }
    if fragment == "graph":
        return {
            **base,
            "graph_valid": True,
            "required_edges": [],
            "observed_edges": [],
        }
    # deontic / relation / temporal → provider path; no local facts needed
    return base


def prove_obligations(
    compiled_rows: list[dict[str, Any]],
    prover: Any,
) -> list[dict[str, Any]]:
    proved: list[dict[str, Any]] = []
    for row in compiled_rows:
        if not row.get("compiled") or "_obligation" not in row:
            proved.append({**{k: v for k, v in row.items() if k != "_obligation"}, "prove": {"skipped": True}})
            continue
        obligation = row["_obligation"]
        fragment = str(row.get("logic_fragment") or "")
        facts = _facts_for_fragment(fragment, list(row.get("premise_ids") or []))
        prove_row: dict[str, Any] = {"attempted": True, "facts_keys": sorted(facts)}
        try:
            result = prover.prove(obligation, facts=facts)
            prove_row["outcome"] = (
                result.outcome.value
                if hasattr(result.outcome, "value")
                else str(result.outcome)
            )
            prove_row["route"] = (
                result.route.value
                if hasattr(result.route, "value")
                else str(result.route)
            )
            prove_row["reason_codes"] = list(result.reason_codes or ())
            receipt = result.receipt
            prove_row["receipt"] = {
                "authoritative_verdict": str(
                    getattr(receipt, "authoritative_verdict", None)
                    or getattr(getattr(receipt, "authoritative_verdict", None), "value", None)
                    or ""
                ),
                "authoritative_assurance": str(
                    getattr(receipt, "authoritative_assurance", "")
                    or getattr(
                        getattr(receipt, "authoritative_assurance", None),
                        "value",
                        "",
                    )
                ),
                "obligation_id": getattr(receipt, "obligation_id", None),
                "evidence_count": len(getattr(receipt, "evidence", ()) or ()),
                "kernel_receipt_id": getattr(receipt, "kernel_receipt_id", None) or "",
            }
            # Inspect raw result metadata for reconstruction artifacts
            raw = result.to_dict() if hasattr(result, "to_dict") else {}
            recon_present = False
            if isinstance(raw, dict):
                blob = json.dumps(raw, default=str)
                recon_present = any(
                    k in blob
                    for k in (
                        "reconstruction_record",
                        "reconstruction_evidence",
                        "environment_lock",
                        "kernel_verified",
                    )
                )
            prove_row["reconstruction_artifacts_present"] = recon_present
            prove_row["kernel_promoted"] = False  # never auto-promote here
        except Exception as exc:  # noqa: BLE001
            prove_row["error"] = f"{type(exc).__name__}: {exc}"
        out = {k: v for k, v in row.items() if k != "_obligation"}
        out["prove"] = prove_row
        proved.append(out)
    return proved


def probe_kernel_gate(prove_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Fail-closed kernel reconstruction probe."""
    from ipfs_accelerate_py.agent_supervisor.proof.kernel_verification import (
        verify_kernel_reconstruction,
    )

    empty_probe: dict[str, Any] = {"attempted": True}
    try:
        verify_kernel_reconstruction({}, {}, {}, independent=True)
        empty_probe["result"] = "unexpected_success"
        empty_probe["fail_closed"] = False
    except Exception as exc:  # noqa: BLE001
        empty_probe["result"] = f"fail_closed:{type(exc).__name__}"
        empty_probe["fail_closed"] = True
        empty_probe["detail"] = str(exc)[:240]

    independent_false: dict[str, Any] = {"attempted": True}
    try:
        # Even with independent=False, empty records must not mint authority
        verify_kernel_reconstruction({}, {}, {}, independent=False)
        independent_false["result"] = "unexpected_success"
        independent_false["fail_closed"] = False
    except Exception as exc:  # noqa: BLE001
        independent_false["result"] = f"fail_closed:{type(exc).__name__}"
        independent_false["fail_closed"] = True

    artifacts_seen = sum(
        1
        for row in prove_rows
        if (row.get("prove") or {}).get("reconstruction_artifacts_present")
    )
    return {
        "api_importable": True,
        "empty_inputs": empty_probe,
        "independent_false_empty": independent_false,
        "prove_rows_with_recon_artifacts": artifacts_seen,
        "kernel_verified_minted": False,
        "note": (
            "KERNEL_VERIFIED requires independent reconstruction packet with "
            "exact digests, environment lock, and independent=True from a "
            "supervisor-owned kernel boundary — not present for residual SCA "
            "candidates in this pipeline."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-tasks", type=int, default=6)
    args = parser.parse_args(argv)
    _setup()

    from ipfs_accelerate_py.agent_supervisor.integrations.ipfs_datasets_logic_provider import (
        DatasetsLogicBackendKind,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.mcp_contract_prover import (
        ContractProofRoute,
        create_mcp_contract_prover_with_datasets_logic_backends,
        datasets_logic_backends_are_registered,
    )

    snapshot_id = ""
    if SUMMARY.exists():
        snapshot_id = str(
            json.loads(SUMMARY.read_text(encoding="utf-8")).get("snapshot_id") or ""
        )

    findings = load_findings(args.max_tasks)
    print(f"selected={len(findings)} snapshot={snapshot_id}")

    prover, reg = create_mcp_contract_prover_with_datasets_logic_backends(
        kinds=tuple(DatasetsLogicBackendKind)
    )
    routes = {
        "cec": datasets_logic_backends_are_registered(prover, ContractProofRoute.CEC),
        "tdfol": datasets_logic_backends_are_registered(prover, ContractProofRoute.TDFOL),
        "smt": datasets_logic_backends_are_registered(prover, ContractProofRoute.SMT),
    }
    print("routes", routes)

    rows: list[dict[str, Any]] = []
    all_prove: list[dict[str, Any]] = []
    for item in findings:
        contract_id = str(item.get("contract_id") or "")
        kind = str(item.get("kind") or item.get("reason_code") or "")
        op = contract_id.split(":", 1)[-1] if ":" in contract_id else contract_id
        compiled = compile_finding_obligations(item, snapshot_id=snapshot_id)
        proved = prove_obligations(compiled, prover)
        all_prove.extend(proved)
        ok_c = sum(1 for r in compiled if r.get("compiled"))
        outcomes = [
            (r.get("family"), (r.get("prove") or {}).get("outcome") or (r.get("prove") or {}).get("error"))
            for r in proved
        ]
        rows.append(
            {
                "contract_id": contract_id,
                "kind": kind,
                "operation": op,
                "families": claim_families_for(kind, op),
                "compiled_count": ok_c,
                "obligations": proved,
            }
        )
        print(
            f"  {kind[:28]:28} {op[:28]:28} compiled={ok_c}/{len(compiled)} "
            f"outcomes={outcomes}"
        )

    kernel = probe_kernel_gate(all_prove)
    print("kernel_empty", kernel.get("empty_inputs"))

    compiled_total = sum(r["compiled_count"] for r in rows)
    prove_attempted = sum(
        1
        for r in all_prove
        if (r.get("prove") or {}).get("attempted")
    )
    prove_errors = sum(1 for r in all_prove if (r.get("prove") or {}).get("error"))
    kernel_ok = bool((kernel.get("empty_inputs") or {}).get("fail_closed"))

    report = {
        "schema": "sca-obligation-kernel-pipeline@1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_id": snapshot_id,
        "completion_authoritative": False,
        "kernel_verified_minted": False,
        "routes_registered": routes,
        "selected_count": len(findings),
        "compiled_total": compiled_total,
        "prove_attempted": prove_attempted,
        "prove_errors": prove_errors,
        "rows": rows,
        "kernel_gate": kernel,
        "notes": [
            "Typed McpContractObligation compiled via compile_contract_claim + catalog.",
            "McpContractProver.prove uses datasets backends; candidates stay non-authoritative.",
            "verify_kernel_reconstruction fails closed on empty inputs; no KERNEL_VERIFIED minted.",
            "Cross-package effects remain MCP-mediated (package_mcp_interop).",
        ],
        "passed": (
            all(routes.values())
            and compiled_total >= 1
            and prove_attempted >= 1
            and prove_errors == 0
            and kernel_ok
            and not any(
                (r.get("prove") or {}).get("kernel_promoted") for r in all_prove
            )
        ),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(f"report={REPORT}")
    print("PASSED" if report["passed"] else "FAILED")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
