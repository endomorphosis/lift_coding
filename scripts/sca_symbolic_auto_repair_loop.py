#!/usr/bin/env python3
"""Symbolic auto-repair loop via ipfs_accelerate_py agent supervisor.

Preferred path: ``agent_supervisor.sca_symbolic_repair.run_symbolic_repair_stack``
(policy from supervisor ``symbolicRepairPolicy``). Falls back to staged scripts.

Uses:
* Supervisor-native orchestration (all logic families + kernel ITPs)
* Live package MCP endpoints (``IPFS_*_MCP_URL`` / package_mcp_interop)
* **All** datasets logic backends (IR/TDFOL/CEC/SMT/HAMMER)
* **All** multi-family analyzers (protocol, kernels, ATP, state, deontic, …)
* MultiProverRouter + ProVerif/Tamarin protocol layer
* Observation-bound claim KERNEL_VERIFIED (Lean/Coq/Isabelle)
* Board + RPR claim receipt bind
* Doctor bridge + RPR (LLM remains proposal_only)

Usage:
  set -a; source data/agent_supervisor/swissknife_contract_assurance/evaluation/mcp_endpoints/endpoints.env; set +a
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit \\
    python3 scripts/sca_symbolic_auto_repair_loop.py [--max-tasks 5]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
SCA = REPO / "data" / "agent_supervisor" / "swissknife_contract_assurance"
FINDINGS = SCA / "baseline" / "runtime_components" / "findings.json"
CONTRACT_FINDINGS = SCA / "baseline" / "runtime_components" / "contract_findings.json"
SUMMARY = SCA / "baseline" / "runtime_components" / "summary.json"
REPORT = SCA / "evaluation" / "symbolic_auto_repair_loop_report.json"
ENV_FILE = SCA / "evaluation" / "mcp_endpoints" / "endpoints.env"


DEFAULT_MANAGED_BIN = (
    Path.home() / ".local" / "share" / "ipfs_datasets_py" / "theorem-provers" / "bin"
)


def _setup() -> None:
    os.chdir(REPO)
    # Prefer endpoints.env if present
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export ") :]
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    # Managed ProVerif/Tamarin/Vampire/… for MultiProverRouter + protocol layer
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


def _probe_mcp(url: str) -> dict[str, Any]:
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    ).encode()
    for path in ("/mcp", "/mcp/", ""):
        target = url.rstrip("/") + path
        try:
            req = urllib.request.Request(
                target,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                data = json.loads(body) if body else {}
                tools = (data.get("result") or {}).get("tools") if isinstance(data, dict) else None
                return {
                    "ok": True,
                    "url": target,
                    "tool_count": len(tools) if isinstance(tools, list) else None,
                }
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
    return {"ok": False, "url": url, "error": last}


def _call_mcp_tool(url: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
    ).encode()
    last = "failed"
    for path in ("/mcp/tools/call", "/mcp", "/mcp/"):
        target = url.rstrip("/") + path
        try:
            req = urllib.request.Request(
                target,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60.0) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                data = json.loads(body) if body else {}
                if isinstance(data, dict) and data.get("error"):
                    return {"ok": False, "error": data["error"], "url": target}
                return {
                    "ok": True,
                    "url": target,
                    "result": data.get("result") if isinstance(data, dict) else data,
                }
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
    return {"ok": False, "error": last, "tool": tool_name}


def _load_selected(max_tasks: int) -> list[dict[str, Any]]:
    want = {
        "observed_contract_incomplete",
        "ambiguous_source_anchor",
        "ambiguous_target_anchor",
        "ambiguous_path_class",
    }
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-tasks", type=int, default=5)
    parser.add_argument(
        "--skip-mcp-require",
        action="store_true",
        help="Continue even if datasets/accelerate MCP probes fail",
    )
    parser.add_argument(
        "--supervisor-stack",
        action="store_true",
        default=True,
        help="Use agent_supervisor.sca_symbolic_repair orchestrator (default)",
    )
    parser.add_argument(
        "--legacy-stages",
        action="store_true",
        help="Force legacy multi-script stages instead of supervisor stack",
    )
    args = parser.parse_args(argv)
    _setup()

    # Supervisor-native stack: single policy-driven orchestration
    if args.supervisor_stack and not args.legacy_stages:
        try:
            from ipfs_accelerate_py.agent_supervisor.sca_symbolic_repair import (
                load_policy_from_supervisor_profile,
                run_symbolic_repair_stack,
                write_stack_report,
            )

            policy = load_policy_from_supervisor_profile(
                REPO / "config" / "swissknife_symbolic_contract_assurance_supervisor.json"
            )
            policy.repo_root = str(REPO)
            policy.max_tasks = max(int(args.max_tasks), int(policy.max_tasks or 8))
            policy.skip_mcp_require = bool(args.skip_mcp_require)
            print(
                f"supervisor_stack all_families={policy.all_logic_families} "
                f"max_tasks={policy.max_tasks} "
                f"kernel_itps={policy.kernel_itps}"
            )
            result = run_symbolic_repair_stack(policy)
            stack_path = write_stack_report(result)
            for st in result.stages:
                print(
                    f"  stage={st.name:18} ok={st.ok} exit={st.exit_code} "
                    f"{st.error[:60] if st.error else ''}"
                )
            # Still probe MCP for the loop report surface
            from ipfs_accelerate_py.mcp_server.package_mcp_interop import (
                package_mcp_endpoint,
            )

            endpoints = {
                "ipfs_accelerate_py": package_mcp_endpoint("ipfs_accelerate_py")
                or os.environ.get("IPFS_ACCELERATE_MCP_URL", "http://127.0.0.1:8000"),
                "ipfs_datasets_py": package_mcp_endpoint("ipfs_datasets_py")
                or os.environ.get("IPFS_DATASETS_MCP_URL", "http://127.0.0.1:3002"),
                "ipfs_kit_py": package_mcp_endpoint("ipfs_kit_py")
                or os.environ.get("IPFS_KIT_MCP_URL", "http://127.0.0.1:8004"),
            }
            probes = {pkg: _probe_mcp(url) for pkg, url in endpoints.items()}
            report = {
                "schema": "sca-symbolic-auto-repair-loop@2",
                "orchestrator": "ipfs_accelerate_py.agent_supervisor.sca_symbolic_repair",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "completion_authoritative": False,
                "endpoints": endpoints,
                "probes": probes,
                "supervisor_stack": result.to_dict(),
                "supervisor_stack_report": str(stack_path),
                "selected_count": args.max_tasks,
                "notes": [
                    "Orchestrated by agent_supervisor.sca_symbolic_repair under symbolicRepairPolicy.",
                    "All logic families + datasets backends + MultiProverRouter + kernel ITPs.",
                    "Claim KERNEL_VERIFIED is observation_bound_operator_semantics@1.",
                    "LLM implement remains proposal_only; board completion non-authoritative.",
                ],
                "passed": bool(result.passed)
                and (
                    args.skip_mcp_require
                    or (
                        bool(probes["ipfs_datasets_py"].get("ok"))
                        and bool(probes["ipfs_accelerate_py"].get("ok"))
                    )
                ),
            }
            REPORT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            REPORT.write_text(
                json.dumps(report, indent=2, sort_keys=True, default=str) + "\n"
            )
            print(f"report={REPORT}")
            print("PASSED" if report["passed"] else "FAILED")
            return 0 if report["passed"] else 1
        except Exception as exc:  # noqa: BLE001
            print(f"supervisor_stack_error {type(exc).__name__}: {exc}")
            print("falling back to legacy stages")

    from ipfs_accelerate_py.agent_supervisor.integrations.ipfs_datasets_logic_provider import (
        DatasetsLogicBackendKind,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.mcp_contract_prover import (
        ContractProofRoute,
        create_mcp_contract_prover_with_datasets_logic_backends,
        datasets_logic_backends_are_registered,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.mcp_contract_obligations import (
        McpContractObligation,
    )
    from ipfs_accelerate_py.agent_supervisor.analysis.mcp_contract_catalog import (
        McpClaimFamily,
    )
    from ipfs_accelerate_py.agent_supervisor.sca_doctor_bridge import map_finding
    from ipfs_accelerate_py.mcp_server.package_mcp_interop import (
        call_package_mcp_tool_sync,
        package_mcp_endpoint,
    )

    # Endpoint probes
    endpoints = {
        "ipfs_accelerate_py": package_mcp_endpoint("ipfs_accelerate_py")
        or os.environ.get("IPFS_ACCELERATE_MCP_URL", "http://127.0.0.1:8000"),
        "ipfs_datasets_py": package_mcp_endpoint("ipfs_datasets_py")
        or os.environ.get("IPFS_DATASETS_MCP_URL", "http://127.0.0.1:3002"),
        "ipfs_kit_py": package_mcp_endpoint("ipfs_kit_py")
        or os.environ.get("IPFS_KIT_MCP_URL", "http://127.0.0.1:8004"),
    }
    probes = {pkg: _probe_mcp(url) for pkg, url in endpoints.items()}
    print("endpoint_probes:")
    for pkg, probe in probes.items():
        print(f"  {pkg:20} ok={probe.get('ok')} tools={probe.get('tool_count')} {probe.get('url') or probe.get('error')}")

    if not probes["ipfs_datasets_py"].get("ok") and not args.skip_mcp_require:
        print("FAILED datasets MCP not reachable — start with scripts/sca_start_mcp_endpoints.py")
        return 1
    if not probes["ipfs_accelerate_py"].get("ok") and not args.skip_mcp_require:
        print("FAILED accelerate MCP not reachable")
        return 1

    # Logic prover via process-local datasets backends (supervisor path)
    # Register *all* datasets logic backends (IR/TDFOL/CEC/SMT/HAMMER), not CEC only.
    prover, reg = create_mcp_contract_prover_with_datasets_logic_backends(
        kinds=tuple(DatasetsLogicBackendKind)
    )
    cec_ok = datasets_logic_backends_are_registered(prover, ContractProofRoute.CEC)
    tdfol_ok = datasets_logic_backends_are_registered(prover, ContractProofRoute.TDFOL)
    smt_ok = datasets_logic_backends_are_registered(prover, ContractProofRoute.SMT)
    print(f"routes_registered cec={cec_ok} tdfol={tdfol_ok} smt={smt_ok}")

    # Live MCP logic surface + process-local datasets logic (supervisor path).
    # Hierarchical tools_dispatch on datasets currently lists logic_tools empty;
    # process-local cec_prove / backend probes are the reliable symbolic path.
    cec_mcp: dict[str, Any] = {"attempted": False}
    if probes["ipfs_datasets_py"].get("ok"):
        cec_mcp["attempted"] = True
        for tool, tool_args in (
            (
                "tools_dispatch",
                {
                    "category": "logic_tools",
                    "tool": "cec_prove",
                    "params": json.dumps({"goal": "True", "timeout": 10}),
                },
            ),
            ("logic_tools.cec_prove_tool", {"goal": "True", "timeout": 10}),
        ):
            r = _call_mcp_tool(endpoints["ipfs_datasets_py"], tool, tool_args)
            cec_mcp[tool] = {
                "ok": r.get("ok"),
                "error": r.get("error"),
                "has_result": r.get("result") is not None,
                "result_preview": str(r.get("result"))[:240] if r.get("result") else None,
            }
        print(f"datasets_logic_mcp={cec_mcp}")

    # Process-local datasets logic (same package as theorem prover module)
    local_logic: dict[str, Any] = {}
    try:
        import asyncio
        from ipfs_datasets_py.mcp_server.tools.logic_tools.cec_prove_tool import (
            cec_prove,
        )

        local_logic["cec_prove"] = asyncio.run(
            cec_prove(goal="True", strategy="auto", timeout=15)
        )
    except Exception as exc:  # noqa: BLE001
        local_logic["cec_prove_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from ipfs_accelerate_py.agent_supervisor.integrations.ipfs_datasets_logic_provider import (
            probe_datasets_logic_backend,
        )

        local_logic["backend_probes"] = {}
        for kind in (
            DatasetsLogicBackendKind.CEC,
            DatasetsLogicBackendKind.HAMMER,
            DatasetsLogicBackendKind.SMT,
            DatasetsLogicBackendKind.TDFOL,
            DatasetsLogicBackendKind.IR,
        ):
            try:
                probe = probe_datasets_logic_backend(kind)
                local_logic["backend_probes"][kind.value] = {
                    "available": bool(getattr(probe, "available", False) or (isinstance(probe, dict) and probe.get("available"))),
                    "provider_id": getattr(probe, "provider_id", None)
                    or (probe.get("provider_id") if isinstance(probe, dict) else None),
                    "mcp_route": getattr(probe, "mcp_route", None)
                    or (probe.get("mcp_route") if isinstance(probe, dict) else None),
                    "reconstruction_compatible": bool(
                        getattr(probe, "reconstruction_compatible", False)
                        or (
                            isinstance(probe, dict)
                            and probe.get("reconstruction_compatible")
                        )
                    ),
                }
            except Exception as exc:  # noqa: BLE001
                local_logic["backend_probes"][kind.value] = {
                    "available": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
    except Exception as exc:  # noqa: BLE001
        local_logic["backend_probe_error"] = f"{type(exc).__name__}: {exc}"
    print(f"local_logic={json.dumps(local_logic, default=str)[:500]}")

    snapshot_id = ""
    if SUMMARY.exists():
        snapshot_id = str(
            json.loads(SUMMARY.read_text(encoding="utf-8")).get("snapshot_id") or ""
        )

    selected = _load_selected(args.max_tasks)
    print(f"selected_findings={len(selected)} snapshot={snapshot_id}")

    # Multi-family symbolic repair plans (all logic families) via subprocess
    # so PYTHONPATH/env match the operator scripts.
    import subprocess

    shared_env = os.environ.copy()
    shared_env["PYTHONPATH"] = os.pathsep.join(
        [
            str(REPO / "external" / "ipfs_accelerate"),
            str(REPO / "external" / "ipfs_datasets"),
            str(REPO / "external" / "ipfs_kit"),
            str(REPO / "Mcp-Plus-Plus"),
            shared_env.get("PYTHONPATH", ""),
        ]
    )

    multi_family_summary: dict[str, Any] = {"ran": False}
    try:
        mf_cmd = [
            sys.executable,
            str(REPO / "scripts" / "sca_multi_family_symbolic_repair.py"),
            "--max-tasks",
            str(args.max_tasks),
            "--all-families",
            "--protocol-conformance",
        ]
        proc = subprocess.run(
            mf_cmd,
            cwd=str(REPO),
            env=shared_env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        multi_family_summary = {
            "ran": True,
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-800:],
            "stderr_tail": (proc.stderr or "")[-400:],
            "report": str(
                REPO
                / "data/agent_supervisor/swissknife_contract_assurance/evaluation/multi_family_symbolic_repair_report.json"
            ),
        }
    except Exception as exc:  # noqa: BLE001
        multi_family_summary = {"ran": False, "error": f"{type(exc).__name__}: {exc}"}
    print(
        f"multi_family="
        f"{multi_family_summary.get('exit_code') if multi_family_summary.get('ran') else multi_family_summary}"
    )

    # Full prover matrix + protocol + MultiProverRouter integration
    full_integration: dict[str, Any] = {"ran": False}
    try:
        fi_cmd = [
            sys.executable,
            str(REPO / "scripts" / "sca_full_prover_integration.py"),
            "--max-tasks",
            str(args.max_tasks),
            "--execute",
            "--with-obligations",
            # Kernel + board bind run as dedicated stages below (caps/timeouts).
        ]
        proc = subprocess.run(
            fi_cmd,
            cwd=str(REPO),
            env=shared_env,
            capture_output=True,
            text=True,
            timeout=900,
        )
        full_integration = {
            "ran": True,
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-900:],
            "stderr_tail": (proc.stderr or "")[-400:],
            "report": str(
                REPO
                / "data/agent_supervisor/swissknife_contract_assurance/evaluation/full_prover_integration_report.json"
            ),
        }
    except Exception as exc:  # noqa: BLE001
        full_integration = {"ran": False, "error": f"{type(exc).__name__}: {exc}"}
    print(
        f"full_integration="
        f"{full_integration.get('exit_code') if full_integration.get('ran') else full_integration}"
    )

    # Typed obligation + kernel gate (also nested under full integration;
    # run standalone for a dedicated receipt path when full integration fails)
    obligation_kernel: dict[str, Any] = {"ran": False}
    try:
        ok_cmd = [
            sys.executable,
            str(REPO / "scripts" / "sca_obligation_kernel_pipeline.py"),
            "--max-tasks",
            str(args.max_tasks),
        ]
        proc = subprocess.run(
            ok_cmd,
            cwd=str(REPO),
            env=shared_env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        obligation_kernel = {
            "ran": True,
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-600:],
            "stderr_tail": (proc.stderr or "")[-300:],
            "report": str(
                REPO
                / "data/agent_supervisor/swissknife_contract_assurance/evaluation/obligation_kernel_pipeline_report.json"
            ),
        }
    except Exception as exc:  # noqa: BLE001
        obligation_kernel = {"ran": False, "error": f"{type(exc).__name__}: {exc}"}
    print(
        f"obligation_kernel="
        f"{obligation_kernel.get('exit_code') if obligation_kernel.get('ran') else obligation_kernel}"
    )

    # Live Lean/Coq kernel reconstruction (toolchain bound + claim fail-closed)
    kernel_reconstruction: dict[str, Any] = {"ran": False}
    try:
        # Cover residual set (at least board-aligned ops); cap expensive ITPs.
        kr_tasks = max(int(args.max_tasks), 8)
        kr_cmd = [
            sys.executable,
            str(REPO / "scripts" / "sca_kernel_reconstruction_pipeline.py"),
            "--max-tasks",
            str(kr_tasks),
            "--skip-hammer",
            "--max-isabelle-claims",
            "4",
            "--max-coq-claims",
            "12",
        ]
        proc = subprocess.run(
            kr_cmd,
            cwd=str(REPO),
            env=shared_env,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        kernel_reconstruction = {
            "ran": True,
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-700:],
            "stderr_tail": (proc.stderr or "")[-300:],
            "report": str(
                REPO
                / "data/agent_supervisor/swissknife_contract_assurance/evaluation/kernel_reconstruction_pipeline_report.json"
            ),
        }
    except Exception as exc:  # noqa: BLE001
        kernel_reconstruction = {
            "ran": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    print(
        f"kernel_reconstruction="
        f"{kernel_reconstruction.get('exit_code') if kernel_reconstruction.get('ran') else kernel_reconstruction}"
    )

    # Bind claim KERNEL_VERIFIED receipts into repair board + RPR readiness
    kernel_board_bind: dict[str, Any] = {"ran": False}
    try:
        kb_cmd = [
            sys.executable,
            str(REPO / "scripts" / "sca_bind_kernel_receipts_to_board.py"),
        ]
        proc = subprocess.run(
            kb_cmd,
            cwd=str(REPO),
            env=shared_env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        kernel_board_bind = {
            "ran": True,
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-500:],
            "stderr_tail": (proc.stderr or "")[-200:],
            "report": str(
                REPO
                / "data/agent_supervisor/swissknife_contract_assurance/evaluation/claim_kernel_board_bind_report.json"
            ),
        }
    except Exception as exc:  # noqa: BLE001
        kernel_board_bind = {"ran": False, "error": f"{type(exc).__name__}: {exc}"}
    print(
        f"kernel_board_bind="
        f"{kernel_board_bind.get('exit_code') if kernel_board_bind.get('ran') else kernel_board_bind}"
    )

    rows: list[dict[str, Any]] = []
    for item in selected:
        contract_id = str(item.get("contract_id") or "")
        finding_id = str(item.get("finding_id") or "")
        kind = str(item.get("kind") or item.get("reason_code") or "")
        op = contract_id.split(":", 1)[-1] if ":" in contract_id else contract_id
        package = contract_id.split(":", 1)[0] if ":" in contract_id else "ipfs_accelerate_py"

        doctor = map_finding(
            {
                "finding_id": finding_id,
                "kind": kind,
                "reason_code": kind,
                "snapshot_id": snapshot_id,
                "contract_id": contract_id,
                "symbol": f"handler:{op}",
            }
        )

        # Symbolic prove attempt on a bounded obligation for this op
        prove_row: dict[str, Any] = {"attempted": False}
        try:
            from ipfs_accelerate_py.agent_supervisor.proof.formal_verification_contracts import (
                AssuranceLevel,
            )

            # Prefer POLICY_BEFORE_EFFECT for dispatch-ish; else ARGUMENTS_PRESERVED
            if "dispatch" in op or "tools_" in op:
                family = McpClaimFamily.POLICY_BEFORE_EFFECT
            else:
                family = McpClaimFamily.ARGUMENTS_PRESERVED

            # Build obligation if helper exists; else mark unavailable
            obligation = None
            try:
                # Many codepaths use factory helpers — probe prove with minimal mapping
                if hasattr(prover, "prove_contract_claim"):
                    prove_row["attempted"] = True
                    result = prover.prove_contract_claim(  # type: ignore[attr-defined]
                        {
                            "contract_id": contract_id,
                            "operation_id": op,
                            "claim_family": family.value if hasattr(family, "value") else str(family),
                            "snapshot_id": snapshot_id,
                        }
                    )
                    prove_row["result_type"] = type(result).__name__
                    prove_row["raw"] = (
                        result.to_dict()
                        if hasattr(result, "to_dict")
                        else (result if isinstance(result, dict) else str(result)[:500])
                    )
                elif hasattr(prover, "prove"):
                    prove_row["attempted"] = True
                    prove_row["note"] = "prover.prove present; need typed McpContractObligation"
            except Exception as exc:  # noqa: BLE001
                prove_row["error"] = f"{type(exc).__name__}: {exc}"

        except Exception as exc:  # noqa: BLE001
            prove_row["error"] = f"{type(exc).__name__}: {exc}"

        # Cross-package MCP interop probe for kit contracts
        interop_row: dict[str, Any] | None = None
        if package == "ipfs_kit_py":
            interop_row = call_package_mcp_tool_sync(
                "ipfs_kit_py",
                op.replace(".", "_") if "." in op else op,
                {},
            )

        rows.append(
            {
                "contract_id": contract_id,
                "finding_id": finding_id,
                "kind": kind,
                "doctor": doctor.to_dict() if hasattr(doctor, "to_dict") else str(doctor),
                "prove": prove_row,
                "kit_interop": interop_row,
            }
        )
        print(
            f"  {kind:28} {op:30} doctor={getattr(doctor, 'disposition', None)} "
            f"prove={prove_row.get('attempted')} err={prove_row.get('error', '')[:60]}"
        )

    report = {
        "schema": "sca-symbolic-auto-repair-loop@1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "completion_authoritative": False,
        "endpoints": endpoints,
        "probes": probes,
        "cec_registered": cec_ok,
        "tdfol_registered": tdfol_ok,
        "smt_registered": smt_ok,
        "all_backend_kinds": [k.value for k in DatasetsLogicBackendKind],
        "datasets_logic_mcp": cec_mcp,
        "local_logic": local_logic,
        "multi_family": multi_family_summary,
        "full_prover_integration": full_integration,
        "obligation_kernel_pipeline": obligation_kernel,
        "kernel_reconstruction_pipeline": kernel_reconstruction,
        "kernel_board_bind": kernel_board_bind,
        "selected_count": len(selected),
        "rows": rows,
        "notes": [
            "Doctor emits transform receipts only; code edits still require RPR-admitted packets + re-prove.",
            "All logic families run via multi_family --all-families + protocol conformance.",
            "Claim-bound KERNEL_VERIFIED uses observation_bound_operator_semantics@1 (Lean/Coq/Isabelle).",
            "Claim kernel receipts bind into repair board + RPR readiness (non-authoritative completion).",
            "Cross-package kit calls use package_mcp_interop (tools/call), not direct imports.",
            "Full prover integration binds MultiProverRouter + protocol (ProVerif/Tamarin) + matrix.",
            "Obligation kernel pipeline compiles typed McpContractObligation and fail-closes empty packets.",
        ],
        "passed": (
            cec_ok
            and tdfol_ok
            and smt_ok
            and (
                args.skip_mcp_require
                or (
                    bool(probes["ipfs_datasets_py"].get("ok"))
                    and bool(probes["ipfs_accelerate_py"].get("ok"))
                )
            )
            and multi_family_summary.get("ran") is True
            and multi_family_summary.get("exit_code") == 0
            and full_integration.get("ran") is True
            and full_integration.get("exit_code") == 0
            and obligation_kernel.get("ran") is True
            and obligation_kernel.get("exit_code") == 0
            and kernel_reconstruction.get("ran") is True
            and kernel_reconstruction.get("exit_code") == 0
            and kernel_board_bind.get("ran") is True
            and kernel_board_bind.get("exit_code") == 0
        ),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(f"report={REPORT}")
    print("PASSED" if report["passed"] else "FAILED")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
