#!/usr/bin/env python3
"""Project live SCA-180 findings into RPR-gated repair board tasks.

Pipeline:
  runtime findings → doctor transform → synthetic counterexample finding
  → CodeEditPacket → RuntimeContractMismatchRefinery → generated repair board

Also probes CEC with an optional recording trusted-receipt validator (fail-closed:
returns None unless a kernel-verified receipt is supplied — documents the hook).

**Interop rule:** cross-package work uses MCP protocol mediation
(``tools/call`` / ``tools_dispatch`` / :mod:`package_mcp_interop`), not direct
peer-package Python imports. Repair write-paths prefer each package's MCP
tool registry surface.

Usage:
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets \\
    python3 scripts/sca_project_live_repairs.py [--max-tasks 12] [--merge-live]
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
SCA = REPO / "data" / "agent_supervisor" / "swissknife_contract_assurance"
FINDINGS = SCA / "baseline" / "runtime_components" / "findings.json"
# Prefer authoritative index emission when present (post-reindex); fall back
# to findings.json which may carry observation_refresh overlays.
CONTRACT_FINDINGS = SCA / "baseline" / "runtime_components" / "contract_findings.json"
SUMMARY = SCA / "baseline" / "summary.json"
LIVE_BOARD = SCA / "generated" / "ipfs_accelerate_contract_repairs.todo.md"
LIVE_TRIAGE = SCA / "baseline" / "runtime_integrity_triage.json"
REPORT = SCA / "evaluation" / "live_repair_projection_report.json"
CANDIDATE_LOG = SCA / "evaluation" / "cec_trusted_candidates.jsonl"

PACKAGE_ROOTS = {
    "ipfs_accelerate_py": "external/ipfs_accelerate/ipfs_accelerate_py",
    "ipfs_kit_py": "external/ipfs_kit/ipfs_kit_py",
    "ipfs_datasets_py": "external/ipfs_datasets/ipfs_datasets_py",
    "Mcp-Plus-Plus": "Mcp-Plus-Plus",
    "mcp-plus-plus": "Mcp-Plus-Plus",
}

# Curated primary write-paths for known incomplete ops (repo-relative).
# Prefer the MCP tool registration / handler that owns the operation surface
# over package __init__.py so implement lanes land on real repair targets.
KNOWN_HANDLER_PATHS: dict[str, str] = {
    "ipfs_accelerate_py:semantic_search": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/"
        "search_tools/native_search_tools.py"
    ),
    "ipfs_accelerate_py:list_pins": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/"
        "ipfs_cluster_tools/native_ipfs_cluster_tools.py"
    ),
    "ipfs_accelerate_py:tools_dispatch": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/server.py"
    ),
    "ipfs_accelerate_py:tools_runtime_metrics": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/server.py"
    ),
    "ipfs_accelerate_py:get_backend_status": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/"
        "backend_management_tools/native_backend_management_tools.py"
    ),
    "ipfs_accelerate_py:load_index": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/"
        "index_management_tools/native_index_management_tools.py"
    ),
    "ipfs_accelerate_py:record_provenance": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/"
        "provenance_tools/native_provenance_tools.py"
    ),
    "ipfs_accelerate_py:ipfs_pin_add": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/"
        "ipfs/native_ipfs_tools.py"
    ),
    "ipfs_accelerate_py:ipfs_cat": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/"
        "ipfs/native_ipfs_tools.py"
    ),
    # Bare ipfs_add / dag_put surfaces are incomplete; land on native IPFS tools
    # where related add/cat/pin handlers already live.
    "ipfs_accelerate_py:ipfs_add": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/"
        "ipfs/native_ipfs_tools.py"
    ),
    "ipfs_accelerate_py:dag_put": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/"
        "ipfs/native_ipfs_tools.py"
    ),
    "ipfs_accelerate_py:WorkflowCoordinator.submit_task": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/"
        "workflow/native_workflow_tools.py"
    ),
    # Kit package findings cannot write outside accelerator-owned paths on this
    # board (owner_mismatch). Land on accelerate MCP interop so repairs bind
    # tools/call mediation (IPFS_KIT_MCP_URL) rather than direct kit imports.
    # Kit-side MCP registration remains a separate package-owned program.
    "ipfs_kit_py:ipfs.add": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/package_mcp_interop.py"
    ),
    "ipfs_kit_py:ipfs.cat": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/package_mcp_interop.py"
    ),
    "ipfs_kit_py:ipfs.dag.get": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/package_mcp_interop.py"
    ),
    "ipfs_kit_py:ipfs.dag.put": (
        "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/package_mcp_interop.py"
    ),
}

_DISCOVERY_SKIP_PARTS = (
    "/test/",
    "/tests/",
    "/mcp/tests/",
    "/__pycache__/",
    "/archives/",
    "/.git/",
    "/mocks/",
)

_DISCOVERY_PREFERS = (
    "/mcp_server/tools/",
    "/mcp_server/",
    "/mcp/tools/",
    "/datasets_integration/",
    "/agent_supervisor/",
)

_handler_path_cache: dict[str, str] = {}


def _score_handler_candidate(rel_path: str, op: str) -> int:
    """Higher score = better write-path candidate for an operation."""
    score = 0
    p = rel_path.replace("\\", "/")
    for i, pref in enumerate(_DISCOVERY_PREFERS):
        if pref in p:
            score += 50 - i
            break
    base = Path(p).name
    if base.startswith("native_") and base.endswith("_tools.py"):
        score += 30
    if base == "server.py" and op.startswith("tools_"):
        score += 40
    if base == f"{op}.py":
        score += 25
    if p.endswith("__init__.py"):
        score -= 20
    if any(s in f"/{p}/" or s in p for s in _DISCOVERY_SKIP_PARTS):
        score -= 1000
    return score


def _discover_handler_path(package_root: str, op: str) -> str | None:
    """Walk package sources for name=/def matches of op (or Class.method)."""
    if not op or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\.]*", op):
        return None
    root_path = REPO / package_root
    if not root_path.is_dir():
        return None

    class_name: str | None = None
    method_name: str | None = None
    leaf = op
    if "." in op:
        class_name, method_name = op.rsplit(".", 1)
        leaf = method_name

    # Prefer focused search dirs when present
    search_roots: list[Path] = []
    for sub in (
        "mcp_server/tools",
        "mcp_server",
        "mcp/tools",
        "datasets_integration",
        "agent_supervisor",
    ):
        candidate = root_path / sub
        if candidate.is_dir():
            search_roots.append(candidate)
    if not search_roots:
        search_roots = [root_path]

    name_pat = re.compile(
        rf"""(?:name\s*=\s*["']{re.escape(leaf)}["']|"""
        rf"""(?:async\s+)?def\s+{re.escape(leaf)}\s*\()"""
    )
    class_pat = (
        re.compile(rf"class\s+{re.escape(class_name)}\b") if class_name else None
    )
    registry_pat = re.compile(rf"""["']{re.escape(leaf)}["']\s*:""")

    scored: list[tuple[int, str]] = []
    seen: set[str] = set()
    for sroot in search_roots:
        for py in sroot.rglob("*.py"):
            try:
                rel = str(py.relative_to(REPO)).replace("\\", "/")
            except ValueError:
                continue
            if rel in seen:
                continue
            seen.add(rel)
            if any(part in f"/{rel}/" for part in _DISCOVERY_SKIP_PARTS):
                continue
            try:
                text = py.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            hit = False
            if class_pat and class_pat.search(text):
                # Class.method: class definition is the primary surface
                if method_name is None or re.search(
                    rf"(?:async\s+)?def\s+{re.escape(method_name)}\s*\(", text
                ):
                    hit = True
            if name_pat.search(text) or registry_pat.search(text):
                hit = True
            if not hit:
                continue
            score = _score_handler_candidate(rel, leaf)
            if class_name and class_pat and class_pat.search(text):
                score += 50
            if score > 0:
                scored.append((score, rel))

    if not scored:
        return None
    scored.sort(key=lambda t: (-t[0], t[1]))
    return scored[0][1]


def _path_for_contract(contract_id: str) -> str:
    cid = str(contract_id or "")
    if cid in _handler_path_cache:
        return _handler_path_cache[cid]

    # 1) Curated map (contract_id or bare op)
    if cid in KNOWN_HANDLER_PATHS:
        path = KNOWN_HANDLER_PATHS[cid]
        if (REPO / path).is_file():
            _handler_path_cache[cid] = path
            return path
    op = cid.split(":", 1)[1] if ":" in cid else cid
    for key, path in KNOWN_HANDLER_PATHS.items():
        if key.endswith(f":{op}") or key == op:
            if (REPO / path).is_file():
                _handler_path_cache[cid] = path
                return path

    pkg = cid.split(":")[0] if ":" in cid else cid.split(".")[0]
    root = PACKAGE_ROOTS.get(pkg)
    if not root:
        # baguqe... content ids — park under accelerate runtime surface
        fallback = "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime.py"
        _handler_path_cache[cid] = fallback
        return fallback

    # 2) Filesystem discovery of name=/def handlers
    discovered = _discover_handler_path(root, op)
    if discovered and (REPO / discovered).is_file():
        _handler_path_cache[cid] = discovered
        return discovered

    # 3) Coarse package fallback (last resort)
    if op.startswith("tools_"):
        fallback = (
            f"{root}/mcp_server/server.py"
            if (REPO / root / "mcp_server" / "server.py").is_file()
            else f"{root}/__init__.py"
        )
    else:
        fallback = f"{root}/__init__.py"
    _handler_path_cache[cid] = fallback
    return fallback


def _load_snapshot_id() -> str:
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    return str(data.get("snapshot_id") or "")


def make_recording_trusted_validator(log_path: Path):
    """Trusted validator that records CEC candidates and never forges kernel proof.

    When reconstruction artifacts are present, attempts
    ``verify_kernel_reconstruction`` for diagnostics only. Promotion still
    requires a fully bound ProofReceipt from that independent check; this
    helper does not invent one.
    """

    log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _validator(obligation: Any, raw_result: dict[str, Any]) -> None:
        record: dict[str, Any] = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "obligation_id": getattr(obligation, "obligation_id", ""),
            "snapshot_id": getattr(obligation, "snapshot_id", ""),
            "raw_keys": sorted(str(k) for k in (raw_result or {}).keys())[:40],
            "candidate": bool((raw_result or {}).get("candidate")),
            "proof_success": bool((raw_result or {}).get("proof_success")),
            "kernel_checked": bool((raw_result or {}).get("kernel_checked")),
            "authoritative_assurance": (raw_result or {}).get("authoritative_assurance"),
            "promoted": False,
            "reason": "kernel_reconstruction_unavailable_fail_closed",
            "kernel_reconstruction_attempted": False,
        }
        recon = (raw_result or {}).get("reconstruction_record") or (
            raw_result or {}
        ).get("reconstruction")
        evidence = (raw_result or {}).get("reconstruction_evidence")
        env_lock = (raw_result or {}).get("environment_lock")
        if recon is not None and evidence is not None and env_lock is not None:
            record["kernel_reconstruction_attempted"] = True
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
                record["kernel_status"] = str(
                    getattr(result, "status", None)
                    or getattr(result, "verdict", None)
                    or type(result).__name__
                )
                record["reason"] = "reconstruction_ran_receipt_promotion_deferred"
            except Exception as exc:  # noqa: BLE001 — fail closed, log only
                record["kernel_error"] = f"{type(exc).__name__}: {exc}"
                record["reason"] = "reconstruction_failed_fail_closed"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        # Fail closed: do not return a ProofReceipt without real kernel bind.
        return None

    return _validator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-tasks", type=int, default=12)
    parser.add_argument(
        "--merge-live",
        action="store_true",
        help="Write into generated/ipfs_accelerate_contract_repairs.todo.md",
    )
    parser.add_argument(
        "--append-existing",
        action="store_true",
        help=(
            "When writing the live board, append/refine against the current board. "
            "Default is replace so write-path upgrades do not double tasks "
            "(packet finding ids are not stable across projection runs)."
        ),
    )
    parser.add_argument(
        "--kinds",
        default=(
            "observed_contract_incomplete,"
            "ambiguous_source_anchor,"
            "ambiguous_target_anchor"
        ),
        help=(
            "Comma-separated finding kinds to project "
            "(default: incomplete + ambiguous anchors)"
        ),
    )
    args = parser.parse_args(argv)

    import os
    import sys

    os.chdir(REPO)
    sys.path[:0] = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_kit"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "Mcp-Plus-Plus"),
        str(SCA / "runtime" / "pythonpath"),
    ]

    from ipfs_accelerate_py.agent_supervisor.analysis.mcp_contract_analysis import (
        ContractCounterexample,
        ContractParityClaim,
        ParityState,
    )
    from ipfs_accelerate_py.agent_supervisor.analysis.mcp_contract_catalog import (
        McpClaimFamily,
    )
    from ipfs_accelerate_py.agent_supervisor.analysis.contract_mismatch_analyzer import (
        ContractMismatchAnalyzer,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.mcp_contract_edit_packet import (
        ExpansionHandle,
        materialize_contract_edit_packet,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.mcp_contract_prover import (
        ContractProofRoute,
        create_mcp_contract_prover_with_datasets_logic_backends,
        datasets_logic_backends_are_registered,
    )
    from ipfs_accelerate_py.agent_supervisor.integrations.ipfs_datasets_logic_provider import (
        DatasetsLogicBackendKind,
    )
    from ipfs_accelerate_py.agent_supervisor.objectives.contract_mismatch_refinery import (
        write_contract_repair_board,
    )
    from ipfs_accelerate_py.agent_supervisor.objectives.runtime_contract_mismatch_refinery import (
        RuntimeContractMismatchRefineryPolicy,
        RuntimeContractMismatchRefineryReason,
        build_runtime_contract_mismatch_triage,
        refine_runtime_contract_mismatch_packets,
    )
    from ipfs_accelerate_py.agent_supervisor.sca_doctor_bridge import map_finding
    from ipfs_accelerate_py.agent_supervisor.sca_rpr_admission import (
        AdmittedTargetPacket,
        admit_implement_task,
    )

    snapshot_id = _load_snapshot_id()
    # Merge findings.json + contract_findings.json (post-reindex emission may
    # land only in contract_findings while findings.json keeps observation refresh).
    raw_by_id: dict[str, dict[str, Any]] = {}
    for path in (FINDINGS, CONTRACT_FINDINGS):
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for item in doc.get("findings") or []:
            if not isinstance(item, dict):
                continue
            fid = str(item.get("finding_id") or item.get("id") or "")
            key = fid or f"{item.get('kind')}:{item.get('contract_id')}"
            raw_by_id[key] = item
    raw = list(raw_by_id.values())
    want_kinds = {k.strip() for k in args.kinds.split(",") if k.strip()}

    selected: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or item.get("reason_code") or "")
        if kind in want_kinds:
            selected.append(item)
        if len(selected) >= args.max_tasks:
            break

    print(f"snapshot={snapshot_id}")
    print(f"selected_findings={len(selected)} kinds={sorted(want_kinds)}")

    # CEC prover with recording trusted validator (fail-closed promotion)
    # All datasets logic backends (IR/TDFOL/CEC/SMT/HAMMER) for multi-family repair.
    prover, _reg = create_mcp_contract_prover_with_datasets_logic_backends(
        kinds=tuple(DatasetsLogicBackendKind),
        trusted_receipt_validator=make_recording_trusted_validator(CANDIDATE_LOG),
    )
    cec_ok = datasets_logic_backends_are_registered(prover, ContractProofRoute.CEC)
    tdfol_ok = datasets_logic_backends_are_registered(prover, ContractProofRoute.TDFOL)
    smt_ok = datasets_logic_backends_are_registered(prover, ContractProofRoute.SMT)
    print(
        f"routes cec={cec_ok} tdfol={tdfol_ok} smt={smt_ok} "
        f"trusted_validator=recording_fail_closed kinds=all"
    )

    analyzer = ContractMismatchAnalyzer()
    packets = []
    doctor_rows = []
    rpr_rows = []
    errors: list[str] = []

    for item in selected:
        contract_id = str(item.get("contract_id") or "")
        finding_id = str(item.get("finding_id") or item.get("id") or "")
        kind = str(item.get("kind") or item.get("reason_code") or "unknown")
        path = _path_for_contract(contract_id)
        op_name = contract_id.split(":", 1)[-1] if ":" in contract_id else contract_id

        doctor = map_finding(
            {
                "finding_id": finding_id,
                "kind": kind,
                "reason_code": str(item.get("reason_code") or kind),
                "snapshot_id": snapshot_id,
                "contract_id": contract_id,
                "path": path,
                "symbol": f"handler:{op_name}",
            }
        )
        doctor_rows.append(doctor.to_dict())
        if doctor.disposition != "transform_receipt":
            errors.append(f"{finding_id}:doctor_abstained")
            continue

        # Typed synthetic refutation for incomplete / ambiguous observation gaps.
        # Must use an SCA-051 parity family (not catalog-only claim families).
        if "dispatch" in op_name or "tools_" in op_name:
            family = McpClaimFamily.POLICY_BEFORE_EFFECT
        elif any(tok in op_name for tok in ("list", "search", "load", "get_", "dag_")):
            family = McpClaimFamily.DISCOVERY_EXECUTION_PARITY
        else:
            family = McpClaimFamily.ARGUMENTS_PRESERVED
        if "ambiguous" in kind:
            expected_surface = "unique_resolved_anchor"
            actual_surface = kind
        else:
            expected_surface = "complete_observed_contract_surface"
            actual_surface = "observed_contract_incomplete"
        claim = ContractParityClaim(
            family=family,
            state=ParityState.REFUTED,
            operation_id=op_name or "unknown.op",
            premise_ids=("premise:schema", "premise:runtime"),
            reason_codes=(kind, actual_surface),
            counterexamples=(
                ContractCounterexample(
                    reason_code=kind,
                    boundary_id=op_name or "runtime",
                    path=path,
                    expected=expected_surface,
                    actual=actual_surface,
                    source_ids=(f"source:finding:{finding_id}",),
                ),
            ),
        )
        try:
            findings = analyzer.analyze_claim(
                claim,
                snapshot_id=snapshot_id,
                contract_id=contract_id or f"contract:{op_name}",
                affected_symbols=(f"handler:{op_name}",),
                affected_paths=(path,),
                obligation_ids=(f"obligation:{op_name}",),
                cas_handles=(f"bafy:finding:{finding_id[:24]}",),
                reproduction_commands=(
                    "python3 scripts/sca_symbolic_repair_ready.py",
                    "python3 scripts/sca_project_live_repairs.py --max-tasks 1",
                ),
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{finding_id}:analyze_claim:{type(exc).__name__}:{exc}")
            continue
        if not findings:
            errors.append(f"{finding_id}:no_analyzed_finding")
            continue
        finding = findings[0]

        rpr = admit_implement_task(
            {
                "task_id": f"SCA-LIVE-{finding_id[:12]}",
                "snapshot_id": snapshot_id,
                "counterexample_id": f"cex:{kind}:{op_name}",
                "reproof_command": (
                    "python3 -m pytest "
                    "external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_proof_pipeline.py -q"
                ),
                "finding_id": finding_id,
                "contract_id": contract_id,
                "write_paths": [path],
                "doctor_disposition": doctor.disposition,
            },
            current_snapshot_id=snapshot_id,
        )
        rpr_rows.append(rpr.to_dict() if hasattr(rpr, "to_dict") else {"error": str(rpr)})
        if not isinstance(rpr, AdmittedTargetPacket):
            errors.append(f"{finding_id}:rpr_rejected")
            continue

        packet = materialize_contract_edit_packet(
            finding,
            current_snapshot_id=snapshot_id,
            task_id=rpr.task_id,
            expected_postcondition={
                "operation_id": op_name,
                "condition": (
                    "endpoint anchors resolve uniquely under mcp_server preference"
                    if "ambiguous" in kind
                    else "observed contract surface is complete and indexable"
                ),
            },
            validation_commands=(
                "python3 scripts/sca_symbolic_repair_ready.py",
            ),
            reproof_commands=(rpr.reproof_command,),
            read_paths=(path,),
            write_paths=(path,),
            dependency_ids=("SCA-180", "SCA-221", "SCA-225"),
            mandatory_dependency_ids=("SCA-180", "SCA-221"),
            expansion_handles=(
                ExpansionHandle(
                    handle_id=f"finding:{finding_id[:16]}",
                    kind="finding_artifact",
                    content_id=finding_id,
                    byte_count=512,
                ),
            ),
        )
        packets.append(packet)

    print(f"packets={len(packets)} doctor_transforms={sum(1 for d in doctor_rows if d.get('disposition')=='transform_receipt')}")

    # Live projection uses replace-by-default: materialize_contract_edit_packet
    # mints fresh finding/packet ids each run, so appending the existing board
    # duplicates SCA-REPAIR tasks whenever write_paths or packets change.
    if args.append_existing and args.merge_live and LIVE_BOARD.exists():
        existing = LIVE_BOARD.read_text(encoding="utf-8")
        print("board_mode=append_existing")
    else:
        existing = ""
        print("board_mode=replace")
    result = refine_runtime_contract_mismatch_packets(
        tuple(packets),
        current_snapshot_id=snapshot_id,
        existing_board=existing,
        current_open_work=0,
        now_epoch=int(datetime.now(timezone.utc).timestamp()),
        policy=RuntimeContractMismatchRefineryPolicy(
            cooldown_seconds=0,
            goal_id="SCA-G176",
            max_findings_per_run=max(args.max_tasks, 1),
        ),
    )
    board_path = LIVE_BOARD if args.merge_live else (SCA / "evaluation" / "live_projection_board.todo.md")
    triage_path = LIVE_TRIAGE if args.merge_live else (SCA / "evaluation" / "live_projection_triage.json")
    board_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_contract_repair_board(board_path, result.markdown)
    triage = build_runtime_contract_mismatch_triage(
        result,
        current_snapshot_id=snapshot_id,
        owner="external/ipfs_accelerate",
        source_records=tuple(p.to_dict() for p in packets),
    )
    triage_path.write_text(json.dumps(triage, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    emitted = sum(
        1
        for d in result.decisions
        if d.reason_code is RuntimeContractMismatchRefineryReason.EMITTED
    )
    print(f"board_tasks={len(result.tasks)} emitted={emitted} path={board_path}")
    print(f"triage llm={triage.get('llm_call_count')} auth={triage.get('completion_authoritative')}")

    report = {
        "schema": "ipfs_accelerate_py/agent-supervisor/sca-live-repair-projection@1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_id": snapshot_id,
        "merge_live": bool(args.merge_live),
        "append_existing": bool(args.append_existing),
        "board_mode": "append_existing" if args.append_existing else "replace",
        "selected_finding_count": len(selected),
        "packet_count": len(packets),
        "board_task_count": len(result.tasks),
        "emitted_decisions": emitted,
        "board_path": str(board_path),
        "triage_path": str(triage_path),
        "cec_registered": cec_ok,
        "trusted_validator": "recording_fail_closed",
        "candidate_log": str(CANDIDATE_LOG),
        "write_paths": sorted(
            {
                p
                for t in result.tasks
                for p in (getattr(t, "write_paths", None) or ())
            }
        ),
        "contract_write_paths": {
            (getattr(t, "contract_ids", None) or [None])[0]: list(
                getattr(t, "write_paths", None) or ()
            )
            for t in result.tasks
            if getattr(t, "contract_ids", None)
        },
        "doctor_sample": doctor_rows[:5],
        "rpr_sample": rpr_rows[:5],
        "errors": errors[:40],
        "task_ids": [
            getattr(t, "task_id", None) for t in result.tasks
        ],
        "llm_call_count": 0,
        "completion_authoritative": triage.get("completion_authoritative"),
        "automatic_repair_note": (
            "Projects non-authoritative SCA-REPAIR tasks for implement lanes. "
            "CEC/hammer candidates are logged but not kernel-promoted without reconstruction. "
            "Write paths prefer curated MCP handlers over package __init__.py."
        ),
        "empty_board_ok": len(selected) == 0 and len(packets) == 0,
        "passed": (
            triage.get("llm_call_count") == 0
            and triage.get("completion_authoritative") is False
            and cec_ok
            and tdfol_ok
            and smt_ok
            and (
                # No incomplete findings → empty non-authoritative board is success.
                (len(selected) == 0 and len(result.tasks) == 0)
                or (
                    len(packets) > 0
                    and len(result.tasks) > 0
                    and not any(
                        str(p).endswith("/__init__.py")
                        for t in result.tasks
                        for p in (getattr(t, "write_paths", None) or ())
                    )
                )
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
