#!/usr/bin/env python3
"""AST + registration-rule repair for SCA observed_contract_incomplete findings.

Two tracks in one operator script:

1. **Surface repair (observation)** — classify incomplete ops against static
   MCP package surfaces and report whether registration aliases / collapse
   rules / explicit surfaces already cover them. Does not invent kernel proof.

2. **Kernel reconstruction probe (authority)** — route a sample CEC candidate
   through ``verify_kernel_reconstruction`` / trusted-validator hooks and
   record what is still missing for KERNEL_VERIFIED promotion.

Usage:
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets \\
    python3 scripts/sca_auto_repair_incomplete_surfaces.py [--probe-kernel]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
SCA = REPO / "data" / "agent_supervisor" / "swissknife_contract_assurance"
FINDINGS = SCA / "baseline" / "runtime_components" / "findings.json"
REPORT = SCA / "evaluation" / "auto_repair_incomplete_surfaces_report.json"
ACCELERATE = REPO / "external" / "ipfs_accelerate" / "ipfs_accelerate_py"

# Files touched by the registration-surface repair tranche.
EXPECTED_SURFACE_FILES = (
    "mcp_server/tools/ipfs/native_ipfs_tools.py",
    "mcp_server/tools/backend_management_tools/native_backend_management_tools.py",
    "mcp_server/tools/embedding_tools/native_embedding_tools.py",
    "mcp_server/tools/ipfs_cluster_tools/native_ipfs_cluster_tools.py",
    "mcp_server/tools/workflow/native_workflow_tools.py",
    "mcp_server/server.py",
)

KNOWN_OPS = (
    "semantic_search",
    "list_pins",
    "tools_dispatch",
    "tools_runtime_metrics",
    "get_backend_status",
    "load_index",
    "record_provenance",
    "ipfs_pin_add",
    "ipfs_cat",
    "ipfs_add",
    "dag_put",
    "WorkflowCoordinator.submit_task",
)


def _setup_path() -> None:
    sys.path[:0] = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_kit"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "Mcp-Plus-Plus"),
        str(SCA / "runtime" / "pythonpath"),
    ]


def _load_incomplete_ops() -> list[str]:
    if not FINDINGS.exists():
        return list(KNOWN_OPS)
    doc = json.loads(FINDINGS.read_text(encoding="utf-8"))
    raw = doc.get("findings") or []
    ops: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or item.get("reason_code") or "")
        if kind != "observed_contract_incomplete":
            continue
        cid = str(item.get("contract_id") or "")
        op = cid.split(":", 1)[-1] if cid else ""
        if op and op not in ops:
            ops.append(op)
    return ops or list(KNOWN_OPS)


def classify_surfaces(ops: list[str]) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.analysis.python_mcp_surface_extractor import (
        extract_python_mcp_source,
    )
    from ipfs_accelerate_py.agent_supervisor.analysis.runtime_contract_evidence_compiler import (
        _collapse_equivalent_tool_surfaces,
    )

    # Extract from the repair tranche files (+ search tools for semantic_search).
    paths = [ACCELERATE / rel for rel in EXPECTED_SURFACE_FILES]
    paths.append(ACCELERATE / "mcp_server/tools/search_tools/native_search_tools.py")
    paths.append(
        ACCELERATE
        / "mcp_server/tools/index_management_tools/native_index_management_tools.py"
    )
    paths.append(
        ACCELERATE / "mcp_server/tools/provenance_tools/native_provenance_tools.py"
    )

    tools_by_name: dict[str, list[Any]] = {}
    unresolved = 0
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = str(path.relative_to(REPO))
        surface = extract_python_mcp_source(
            text, provider="ipfs_accelerate_py", path=rel
        )
        unresolved += len(surface.unresolved)
        for tool in surface.tools:
            tools_by_name.setdefault(tool.canonical_name, []).append(tool)
            for alias in tool.aliases:
                tools_by_name.setdefault(alias, []).append(tool)

    rows: list[dict[str, Any]] = []
    resolved = 0
    for op in ops:
        # Mirror tools_named + collapse used by evidence compiler.
        from ipfs_accelerate_py.agent_supervisor.analysis.python_mcp_surface_extractor import (
            _canonical_tool_name,
        )

        key = _canonical_tool_name(op)
        matches = list(tools_by_name.get(key, []))
        # Also try raw op if different
        if op != key:
            matches.extend(tools_by_name.get(op, []))
        # de-dupe by tool_id
        seen: set[str] = set()
        unique_matches = []
        for m in matches:
            tid = getattr(m, "tool_id", None) or id(m)
            if tid in seen:
                continue
            seen.add(tid)
            unique_matches.append(m)
        collapsed = _collapse_equivalent_tool_surfaces(unique_matches)
        status = "resolved" if collapsed is not None else (
            "ambiguous" if len(unique_matches) > 1 else "missing"
        )
        if status == "resolved":
            resolved += 1
        rows.append(
            {
                "operation": op,
                "canonical": key,
                "match_count": len(unique_matches),
                "status": status,
                "handler": (
                    getattr(getattr(collapsed, "handler", None), "symbol", None)
                    if collapsed
                    else None
                ),
                "registration_api": (
                    getattr(collapsed, "registration_api", None) if collapsed else None
                ),
                "paths": sorted(
                    {
                        str(getattr(getattr(m, "registration_span", None), "path", "") or "")
                        for m in unique_matches
                    }
                ),
            }
        )

    return {
        "ops": rows,
        "resolved_count": resolved,
        "total": len(ops),
        "unresolved_registrations_seen": unresolved,
        "surface_files_scanned": [str(p.relative_to(REPO)) for p in paths if p.is_file()],
    }


def probe_kernel_reconstruction() -> dict[str, Any]:
    """Probe CEC + kernel reconstruction boundary without forging receipts."""
    from ipfs_accelerate_py.agent_supervisor.integrations.ipfs_datasets_logic_provider import (
        DatasetsLogicBackendKind,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.mcp_contract_prover import (
        ContractProofRoute,
        create_mcp_contract_prover_with_datasets_logic_backends,
        datasets_logic_backends_are_registered,
    )

    kernel_attempts: list[dict[str, Any]] = []

    def trusted_validator(obligation: Any, raw_result: dict[str, Any]) -> None:
        record: dict[str, Any] = {
            "obligation_id": getattr(obligation, "obligation_id", ""),
            "candidate": bool((raw_result or {}).get("candidate")),
            "proof_success": bool((raw_result or {}).get("proof_success")),
            "kernel_checked": bool((raw_result or {}).get("kernel_checked")),
            "raw_keys": sorted(str(k) for k in (raw_result or {}).keys())[:40],
            "promoted": False,
        }
        # Attempt real reconstruction when artifacts are present.
        recon = (raw_result or {}).get("reconstruction_record") or (
            raw_result or {}
        ).get("reconstruction")
        evidence = (raw_result or {}).get("reconstruction_evidence")
        env_lock = (raw_result or {}).get("environment_lock")
        if recon and evidence and env_lock:
            try:
                from ipfs_accelerate_py.agent_supervisor.proof.kernel_verification import (
                    verify_kernel_reconstruction,
                )

                result = verify_kernel_reconstruction(
                    recon,
                    evidence,
                    env_lock,
                    obligation=obligation,
                    independent=True,
                )
                record["kernel_reconstruction_attempted"] = True
                record["kernel_status"] = str(
                    getattr(result, "status", None)
                    or getattr(result, "verdict", None)
                    or result
                )
                # Still fail closed here: only return ProofReceipt when the
                # kernel result is actually proved AND bindings match. We do
                # not mint receipts in this probe.
                record["promoted"] = False
                record["reason"] = "reconstruction_ran_receipt_promotion_deferred"
            except Exception as exc:  # noqa: BLE001 — probe must not crash
                record["kernel_reconstruction_attempted"] = True
                record["kernel_error"] = f"{type(exc).__name__}: {exc}"
                record["reason"] = "reconstruction_failed_fail_closed"
        else:
            record["kernel_reconstruction_attempted"] = False
            record["reason"] = "no_reconstruction_artifacts_in_candidate"
        kernel_attempts.append(record)
        return None

    prover, reg = create_mcp_contract_prover_with_datasets_logic_backends(
        kinds=(DatasetsLogicBackendKind.CEC, DatasetsLogicBackendKind.HAMMER),
        trusted_receipt_validator=trusted_validator,
    )
    cec_ok = datasets_logic_backends_are_registered(prover, ContractProofRoute.CEC)
    hammer_ok = False
    try:
        # Hammer may register under a different route name depending on version.
        for attr in ("HAMMER", "ATP", "MULTI_PROVER"):
            route = getattr(ContractProofRoute, attr, None)
            if route is not None:
                hammer_ok = datasets_logic_backends_are_registered(prover, route)
                if hammer_ok:
                    break
    except Exception:  # noqa: BLE001
        hammer_ok = False

    # Lightweight capability probe if available
    capability: dict[str, Any] = {
        "cec": cec_ok,
        "hammer": hammer_ok,
        "routes": [r.value for r in ContractProofRoute],
    }
    try:
        # Register-info only; full prove needs a real obligation from the board.
        capability["registration"] = {
            "kinds": [str(k) for k in getattr(reg, "kinds", ()) or ()],
        }
    except Exception as exc:  # noqa: BLE001
        capability["registration_error"] = str(exc)

    # Probe verify_kernel_reconstruction API shape with empty inputs → expect fail closed
    api_probe: dict[str, Any] = {}
    try:
        from ipfs_accelerate_py.agent_supervisor.proof.kernel_verification import (
            verify_kernel_reconstruction,
        )

        api_probe["verify_kernel_reconstruction_import"] = True
        api_probe["callable"] = callable(verify_kernel_reconstruction)
        try:
            verify_kernel_reconstruction({}, {}, {}, independent=True)
            api_probe["empty_inputs"] = "unexpected_success"
        except Exception as exc:  # noqa: BLE001
            api_probe["empty_inputs"] = f"fail_closed:{type(exc).__name__}"
    except Exception as exc:  # noqa: BLE001
        api_probe["verify_kernel_reconstruction_import"] = False
        api_probe["error"] = str(exc)

    return {
        "cec_registered": cec_ok,
        "hammer_registered": hammer_ok,
        "trusted_validator": "probe_fail_closed",
        "capability": capability,
        "kernel_api_probe": api_probe,
        "kernel_attempts": kernel_attempts,
        "note": (
            "Candidates remain non-authoritative until reconstruction artifacts "
            "bind exactly and independent kernel verification admits a receipt."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--probe-kernel",
        action="store_true",
        help="Also probe CEC/hammer + kernel reconstruction boundary",
    )
    args = parser.parse_args(argv)

    _setup_path()
    ops = _load_incomplete_ops()
    classification = classify_surfaces(ops)
    kernel: dict[str, Any] | None = None
    if args.probe_kernel:
        kernel = probe_kernel_reconstruction()

    report = {
        "schema": "ipfs_accelerate_py/agent-supervisor/sca-auto-repair-incomplete-surfaces@1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "authority": "observation_plus_kernel_probe",
        "completion_authoritative": False,
        "classification": classification,
        "kernel_probe": kernel,
        "applied_source_repairs": [
            "collapse_equivalent_tool_surfaces in evidence compiler",
            "alias regs: ipfs_add, ipfs_cat, get_backend_status",
            "disambiguate embedding_semantic_search vs search semantic_search",
            "static tools_dispatch/tools_runtime_metrics registration names",
            "list_pins thin surface",
            "dag_put contract surface",
            "WorkflowCoordinator.submit_task facade registration",
        ],
        "passed": (
            classification["resolved_count"] >= max(1, classification["total"] // 2)
            and (kernel is None or bool(kernel.get("cec_registered")))
        ),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")

    print(f"ops={classification['total']} resolved={classification['resolved_count']}")
    for row in classification["ops"]:
        print(
            f"  {row['status']:10} {row['operation']:35} "
            f"matches={row['match_count']} handler={row.get('handler')}"
        )
    if kernel:
        print(
            f"kernel_probe cec={kernel.get('cec_registered')} "
            f"hammer={kernel.get('hammer_registered')} "
            f"api={kernel.get('kernel_api_probe')}"
        )
    print(f"report={REPORT}")
    print("PASSED" if report["passed"] else "FAILED")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
