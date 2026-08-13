#!/usr/bin/env python3
"""Full SCA prover integration: matrix + protocol + MultiProverRouter + datasets.

Unifies the symbolic stack used for SwissKnife contract assurance repair:

1. **Managed theorem-prover PATH** — ``~/.local/share/ipfs_datasets_py/theorem-provers/bin``
2. **Datasets logic backends** — IR · TDFOL · CEC · SMT · HAMMER (MCP contract prover)
3. **Prover matrix** — Z3, CVC5, Vampire, E, Lean, Coq, Isabelle, ProVerif, Tamarin, …
4. **Protocol verification** — ProVerif/Tamarin end-to-end conformance + CORE model
5. **MultiProverRouter** — property-kind portfolios planned and fail-closed executed
6. **Multi-family guidance** — optional family repair plans for residual findings

Authority model (unchanged):
* Solver / protocol / hammer successes are **candidates** or domain-checked evidence.
* ``KERNEL_VERIFIED`` still requires independent reconstruction.
* LLM implement remains proposal_only / RPR-gated.

Usage:
  export PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit
  python3 scripts/sca_full_prover_integration.py [--max-tasks 8] [--execute]
  python3 scripts/sca_full_prover_integration.py --skip-conformance   # matrix plan only
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
SCA = REPO / "data" / "agent_supervisor" / "swissknife_contract_assurance"
FINDINGS = SCA / "baseline" / "runtime_components" / "findings.json"
CONTRACT_FINDINGS = SCA / "baseline" / "runtime_components" / "contract_findings.json"
SUMMARY = SCA / "baseline" / "runtime_components" / "summary.json"
REPORT = SCA / "evaluation" / "full_prover_integration_report.json"
ENV_FILE = SCA / "evaluation" / "mcp_endpoints" / "endpoints.env"

DEFAULT_MANAGED_BIN = (
    Path.home() / ".local" / "share" / "ipfs_datasets_py" / "theorem-provers" / "bin"
)

# Finding kind / op heuristics → MultiProverRouter PropertyKind values
FINDING_PROPERTY_KINDS: dict[str, tuple[str, ...]] = {
    "observed_contract_incomplete": (
        "temporal_deontic",
        "finite_constraint",
        "protocol",
    ),
    "ambiguous_source_anchor": (
        "finite_constraint",
        "first_order_theorem",
    ),
    "ambiguous_target_anchor": (
        "temporal_deontic",
        "protocol",
        "first_order_theorem",
    ),
    "ambiguous_path_class": (
        "protocol",
        "authorization",
        "temporal_deontic",
    ),
}

OP_PROPERTY_EXTRA: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (
        ("dispatch", "tools_", "policy", "auth", "ucan", "session", "mcpplusplus", "connector"),
        ("protocol", "authorization", "temporal_deontic"),
    ),
    (
        ("workflow", "submit", "dag", "temporal", "schedule"),
        ("temporal_deontic", "typed_planning"),
    ),
    (
        ("pin", "secret", "encrypt", "attest", "zk"),
        ("protocol", "hyperproperty"),
    ),
    (
        ("lease", "claim", "merge", "receipt"),
        ("protocol", "authorization"),
    ),
    (
        ("runtime", "metrics", "monitor", "trace"),
        ("runtime_trace",),
    ),
    (
        ("state", "lifecycle", "transition", "machine"),
        ("state_machine",),
    ),
]


def _setup(*, prepend_managed: bool = True) -> Path | None:
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
    sys.path[:0] = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "external" / "ipfs_kit"),
        str(REPO / "Mcp-Plus-Plus"),
        str(SCA / "runtime" / "pythonpath"),
    ]
    managed = Path(
        os.environ.get("IPFS_THEOREM_PROVERS_BIN")
        or os.environ.get("SCA_THEOREM_PROVERS_BIN")
        or DEFAULT_MANAGED_BIN
    ).expanduser()
    if prepend_managed and managed.is_dir():
        path = os.environ.get("PATH", "")
        managed_s = str(managed.resolve())
        if managed_s not in path.split(os.pathsep):
            os.environ["PATH"] = managed_s + os.pathsep + path
        return managed
    return managed if managed.is_dir() else None


def load_findings(max_tasks: int) -> list[dict[str, Any]]:
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


def property_kinds_for(kind: str, op: str) -> list[str]:
    kinds: list[str] = list(FINDING_PROPERTY_KINDS.get(kind, ("finite_constraint",)))
    op_l = op.lower()
    for tokens, extra in OP_PROPERTY_EXTRA:
        if any(t in op_l for t in tokens):
            for k in extra:
                if k not in kinds:
                    kinds.append(k)
    return kinds


def register_datasets_backends() -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.integrations.ipfs_datasets_logic_provider import (
        DatasetsLogicBackendKind,
        probe_datasets_logic_backend,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.mcp_contract_prover import (
        ContractProofRoute,
        create_mcp_contract_prover_with_datasets_logic_backends,
        datasets_logic_backends_are_registered,
    )

    prover, reg = create_mcp_contract_prover_with_datasets_logic_backends(
        kinds=tuple(DatasetsLogicBackendKind)
    )
    probes: dict[str, Any] = {}
    for kind in DatasetsLogicBackendKind:
        try:
            p = probe_datasets_logic_backend(kind)
            probes[kind.value] = {
                "available": bool(
                    getattr(p, "available", False)
                    or (isinstance(p, dict) and p.get("available"))
                ),
                "provider_id": getattr(p, "provider_id", None)
                or (p.get("provider_id") if isinstance(p, dict) else None),
                "mcp_route": getattr(p, "mcp_route", None)
                or (p.get("mcp_route") if isinstance(p, dict) else None),
            }
        except Exception as exc:  # noqa: BLE001
            probes[kind.value] = {"available": False, "error": f"{type(exc).__name__}: {exc}"}

    routes = {
        "cec": datasets_logic_backends_are_registered(prover, ContractProofRoute.CEC),
        "tdfol": datasets_logic_backends_are_registered(prover, ContractProofRoute.TDFOL),
        "smt": datasets_logic_backends_are_registered(prover, ContractProofRoute.SMT),
    }
    return {
        "all_kinds": [k.value for k in DatasetsLogicBackendKind],
        "backend_probes": probes,
        "routes_registered": routes,
        "prover_type": type(prover).__name__,
        "registry_provider_ids": list(getattr(reg, "provider_ids", lambda: {})())
        if callable(getattr(reg, "provider_ids", None))
        else {},
    }


def probe_matrix() -> tuple[Any, dict[str, Any]]:
    from ipfs_accelerate_py.agent_supervisor.proof.prover_matrix_registry import (
        probe_prover_matrix,
    )

    snap = probe_prover_matrix()
    by_id: dict[str, dict[str, Any]] = {}
    entries = getattr(snap, "entries", ()) or ()
    for entry in entries:
        d = entry.to_dict() if hasattr(entry, "to_dict") else {}
        if not isinstance(d, dict):
            continue
        pid = str(d.get("prover_id") or getattr(entry, "prover_id", "") or "")
        if not pid:
            continue
        states = d.get("states") or {}
        exe = d.get("executable") or {}
        if not isinstance(exe, dict):
            exe = {}
        by_id[pid] = {
            "display_name": d.get("display_name"),
            "family": d.get("family"),
            "highest_state": d.get("highest_state"),
            "discovered": bool(states.get("discovered")),
            "versioned": bool(states.get("versioned")),
            "smoke_tested": bool(states.get("smoke_tested")),
            "translation_conformant": bool(states.get("translation_conformant")),
            "reconstruction_capable": bool(states.get("reconstruction_capable")),
            "executable": exe.get("path"),
            "version": exe.get("version"),
            "reason": d.get("reason"),
        }
    summary = {
        "snapshot_id": getattr(snap, "snapshot_id", None),
        "entry_count": len(by_id),
        "provers": by_id,
        "discovered_or_versioned": sorted(
            k for k, v in by_id.items() if v.get("discovered") or v.get("versioned")
        ),
        "smoke_tested": sorted(k for k, v in by_id.items() if v.get("smoke_tested")),
        "absent": sorted(
            k for k, v in by_id.items() if v.get("highest_state") == "absent"
        ),
        "proverif": by_id.get("proverif"),
        "tamarin": by_id.get("tamarin"),
    }
    return snap, summary


def probe_protocol(*, run_conformance: bool) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.proof.protocol_verification import (
        CORE_PROTOCOL_MODEL,
        DEFAULT_PROTOCOL_MODELS,
        ProVerifAdapter,
        ProtocolTool,
        ProtocolVerifier,
        TamarinAdapter,
        probe_protocol_tools,
    )

    caps_raw = probe_protocol_tools(run_conformance=run_conformance)
    tools: list[dict[str, Any]] = []
    for cap in caps_raw:
        d = cap.to_dict() if hasattr(cap, "to_dict") else {}
        tool = d.get("tool") or getattr(cap, "tool", None)
        tools.append(
            {
                "tool": getattr(tool, "value", tool),
                "available": bool(d.get("available")),
                "status": str(getattr(d.get("status"), "value", d.get("status") or "")),
                "reason": d.get("reason"),
                "executable_path": d.get("executable_path"),
                "executable_version": d.get("executable_version"),
                "conformance_receipt_id": (
                    (d.get("conformance_receipt") or {}).get("receipt_id")
                    if isinstance(d.get("conformance_receipt"), dict)
                    else None
                ),
            }
        )

    core_verify: dict[str, Any] = {"attempted": False}
    if run_conformance:
        try:
            verifier = ProtocolVerifier(
                adapters=(ProVerifAdapter(), TamarinAdapter())
            )
            suite = verifier.verify(CORE_PROTOCOL_MODEL)
            sd = suite.to_dict() if hasattr(suite, "to_dict") else {}
            core_verify = {
                "attempted": True,
                "model_id": getattr(CORE_PROTOCOL_MODEL, "model_id", None),
                "suite": sd
                if isinstance(sd, dict)
                else {
                    "verdict": str(getattr(suite, "verdict", None)),
                    "reason": getattr(suite, "reason", None),
                },
            }
            # Prefer compact projection of lane results
            if isinstance(sd, dict):
                lanes = sd.get("lane_results") or sd.get("lanes") or []
                if isinstance(lanes, list):
                    core_verify["lanes"] = [
                        {
                            "tool": (
                                getattr(lr.get("tool"), "value", lr.get("tool"))
                                if isinstance(lr, dict)
                                else None
                            ),
                            "verdict": (
                                str(getattr(lr.get("verdict"), "value", lr.get("verdict")))
                                if isinstance(lr, dict)
                                else None
                            ),
                            "authoritative": lr.get("authoritative")
                            if isinstance(lr, dict)
                            else None,
                            "reason": (lr.get("reason") or "")[:160]
                            if isinstance(lr, dict)
                            else None,
                        }
                        for lr in lanes
                        if isinstance(lr, dict)
                    ][:8]
        except Exception as exc:  # noqa: BLE001
            core_verify = {
                "attempted": True,
                "error": f"{type(exc).__name__}: {exc}",
            }

    return {
        "tools": tools,
        "models": len(DEFAULT_PROTOCOL_MODELS),
        "core_model_id": getattr(CORE_PROTOCOL_MODEL, "model_id", None),
        "core_queries": len(getattr(CORE_PROTOCOL_MODEL, "queries", ()) or ()),
        "expected_tools": [ProtocolTool.PROVERIF.value, ProtocolTool.TAMARIN.value],
        "core_verify": core_verify,
        "which_proverif": shutil.which("proverif"),
        "which_tamarin": shutil.which("tamarin-prover") or shutil.which("tamarin"),
    }


def build_obligations(
    item: dict[str, Any],
    snapshot_id: str,
) -> list[Any]:
    from ipfs_accelerate_py.agent_supervisor.proof.formal_verification_contracts import (
        AssuranceLevel,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.multi_prover_router import (
        PropertyKind,
        PropertyObligation,
    )

    contract_id = str(item.get("contract_id") or "")
    kind = str(item.get("kind") or item.get("reason_code") or "")
    finding_id = str(item.get("finding_id") or item.get("id") or contract_id)
    op = contract_id.split(":", 1)[-1] if ":" in contract_id else contract_id
    pks = property_kinds_for(kind, op)
    out = []
    for pk in pks:
        try:
            property_kind = PropertyKind(pk)
        except ValueError:
            continue
        stmt = (
            f"SCA residual finding {kind} for operation {op} under contract "
            f"{contract_id}: surface must be complete, uniquely anchored, and "
            f"MCP-mediated where cross-package effects apply "
            f"(property_kind={pk})."
        )
        out.append(
            PropertyObligation(
                obligation_id=f"sca:{finding_id}:{pk}",
                property_kind=property_kind,
                statement=stmt,
                premise_ids=(
                    f"finding:{finding_id}",
                    f"contract:{contract_id}",
                    f"snapshot:{snapshot_id or 'unknown'}",
                ),
                required_assurance=AssuranceLevel.SOLVER_CHECKED,
                metadata={
                    "finding_kind": kind,
                    "contract_id": contract_id,
                    "operation": op,
                    "source": "sca_full_prover_integration",
                    "completion_authoritative": False,
                },
            )
        )
    return out


def make_portfolio_runner(
    *,
    matrix_summary: dict[str, Any],
    protocol_caps: dict[str, Any],
    backend_probes: dict[str, Any],
) -> Any:
    """Bounded fail-closed runner: capability-backed candidates only, no fake proofs."""

    from ipfs_accelerate_py.agent_supervisor.proof.multi_prover_router import (
        AttemptOutcome,
        AttemptRequest,
        ProverOutput,
    )

    provers = matrix_summary.get("provers") or {}
    proto_by_tool = {
        t.get("tool"): t for t in (protocol_caps.get("tools") or []) if isinstance(t, dict)
    }

    # Datasets / domain reasoner ids used in TEMPORAL_DEONTIC / TYPED_PLANNING policies
    datasets_lane_map = {
        "dcec": "cec",
        "tdfol": "tdfol",
        "hammer": "hammer",
        "z3": "smt",
    }

    def runner(request: AttemptRequest, cancellation: threading.Event) -> ProverOutput:
        if cancellation.is_set():
            return ProverOutput(AttemptOutcome.CANCELLED, "cancellation requested")
        prover_id = request.lane.prover_id
        entry = provers.get(prover_id) or {}

        # Protocol authorities
        if prover_id in ("proverif", "tamarin"):
            cap = proto_by_tool.get(prover_id) or {}
            status = str(cap.get("status") or "").lower()
            if cap.get("available") or status.endswith("conformant"):
                return ProverOutput(
                    AttemptOutcome.CANDIDATE,
                    (
                        f"{prover_id} conformant for protocol verification; "
                        "SCA residual obligations use CORE_PROTOCOL_MODEL guidance "
                        "and require kernel reconstruction for KERNEL_VERIFIED"
                    ),
                    {
                        "prover_id": prover_id,
                        "protocol_status": str(cap.get("status") or ""),
                        "executable_path": cap.get("executable_path") or "",
                        "authority": "protocol_checked_candidate",
                    },
                )
            if cap.get("executable_path") or entry.get("discovered"):
                return ProverOutput(
                    AttemptOutcome.UNAVAILABLE,
                    (
                        f"{prover_id} present but not conformant: "
                        f"{cap.get('reason') or entry.get('reason') or 'no fixture'}"
                    ),
                    {"prover_id": prover_id, "status": str(cap.get("status") or "")},
                )
            return ProverOutput(
                AttemptOutcome.UNAVAILABLE,
                f"{prover_id} not discovered on PATH",
                {"prover_id": prover_id},
            )

        # Datasets domain reasoners
        if prover_id in datasets_lane_map:
            backend = datasets_lane_map[prover_id]
            probe = backend_probes.get(backend) or {}
            if probe.get("available"):
                return ProverOutput(
                    AttemptOutcome.CANDIDATE,
                    f"datasets backend {backend} available (candidate only)",
                    {
                        "prover_id": prover_id,
                        "backend": backend,
                        "provider_id": str(probe.get("provider_id") or ""),
                    },
                )
            return ProverOutput(
                AttemptOutcome.UNAVAILABLE,
                f"datasets backend {backend} unavailable",
                {"prover_id": prover_id, "backend": backend},
            )

        # Matrix SMT / ATP / authorization / state / runtime / hyper
        if entry.get("smoke_tested") or entry.get("versioned") or entry.get("discovered"):
            # Candidate lane only — never authoritative VERIFIED without reconstruction
            return ProverOutput(
                AttemptOutcome.CANDIDATE,
                (
                    f"{prover_id} capability matrix state="
                    f"{entry.get('highest_state')}; retained as candidate"
                ),
                {
                    "prover_id": prover_id,
                    "highest_state": str(entry.get("highest_state") or ""),
                    "executable": str(entry.get("executable") or ""),
                    "reconstruction_capable": bool(entry.get("reconstruction_capable")),
                },
            )

        if entry:
            return ProverOutput(
                AttemptOutcome.UNAVAILABLE,
                f"{prover_id} matrix state={entry.get('highest_state')}: "
                f"{entry.get('reason') or 'not smoke-tested'}",
                {"prover_id": prover_id},
            )
        return ProverOutput(
            AttemptOutcome.UNAVAILABLE,
            f"{prover_id} absent from capability matrix",
            {"prover_id": prover_id},
        )

    return runner


def plan_and_maybe_execute(
    *,
    matrix_snap: Any,
    matrix_summary: dict[str, Any],
    protocol: dict[str, Any],
    backends: dict[str, Any],
    findings: list[dict[str, Any]],
    snapshot_id: str,
    execute: bool,
) -> list[dict[str, Any]]:
    from ipfs_accelerate_py.agent_supervisor.proof.multi_prover_router import (
        MultiProverRouter,
    )

    # Do **not** bind the matrix into MultiProverRouter for execution: matrix
    # smoke-test coverage is incomplete for some protocol tools (e.g. ProVerif
    # can be protocol-conformant while matrix highest_state=discovered). The
    # portfolio runner consults matrix + protocol conformance itself and
    # fail-closes on missing evidence.
    router = MultiProverRouter(matrix=None)
    runner = None
    if execute:
        runner = make_portfolio_runner(
            matrix_summary=matrix_summary,
            protocol_caps=protocol,
            backend_probes=backends.get("backend_probes") or {},
        )

    rows: list[dict[str, Any]] = []
    for item in findings:
        contract_id = str(item.get("contract_id") or "")
        kind = str(item.get("kind") or item.get("reason_code") or "")
        op = contract_id.split(":", 1)[-1] if ":" in contract_id else contract_id
        obligations = build_obligations(item, snapshot_id)
        plans: list[dict[str, Any]] = []
        for obl in obligations:
            plan = router.plan(obl)
            plan_row: dict[str, Any] = {
                "obligation_id": obl.obligation_id,
                "property_kind": obl.property_kind.value
                if hasattr(obl.property_kind, "value")
                else str(obl.property_kind),
                "policy_id": plan.policy_id,
                "lanes": [
                    {
                        "prover_id": lane.prover_id,
                        "role": lane.role.value
                        if hasattr(lane.role, "value")
                        else str(lane.role),
                        "stage": lane.stage,
                        "authority_capability": lane.authority_capability,
                        "requires_candidate": lane.requires_candidate,
                    }
                    for lane in plan.lanes
                ],
            }
            if execute and runner is not None:
                try:
                    result = router.execute(obl, runner)
                    plan_row["execution"] = {
                        "verdict": result.verdict.value
                        if hasattr(result.verdict, "value")
                        else str(result.verdict),
                        "assurance": result.assurance.value
                        if hasattr(result.assurance, "value")
                        else str(result.assurance),
                        "reason": result.reason,
                        "duration_ms": result.duration_ms,
                        "proved": bool(result.proved),
                        "fail_closed": bool(result.fail_closed),
                        "attempts": [
                            {
                                "prover_id": a.prover_id,
                                "role": a.role.value
                                if hasattr(a.role, "value")
                                else str(a.role),
                                "reported": a.reported_outcome.value
                                if hasattr(a.reported_outcome, "value")
                                else str(a.reported_outcome),
                                "effective": a.effective_outcome.value
                                if hasattr(a.effective_outcome, "value")
                                else str(a.effective_outcome),
                                "authoritative": a.authoritative,
                                "detail": (a.detail or "")[:200],
                            }
                            for a in result.attempts
                        ],
                    }
                except Exception as exc:  # noqa: BLE001
                    plan_row["execution"] = {
                        "error": f"{type(exc).__name__}: {exc}",
                    }
            plans.append(plan_row)
        rows.append(
            {
                "contract_id": contract_id,
                "kind": kind,
                "operation": op,
                "property_kinds": [p["property_kind"] for p in plans],
                "portfolio_plans": plans,
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-tasks", type=int, default=8)
    parser.add_argument(
        "--execute",
        action="store_true",
        default=True,
        help="Execute portfolio lanes with capability-backed runner (default)",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Plan MultiProverRouter portfolios without executing",
    )
    parser.add_argument(
        "--skip-conformance",
        action="store_true",
        help="Skip ProVerif/Tamarin end-to-end fixtures and CORE model verify",
    )
    parser.add_argument(
        "--skip-matrix",
        action="store_true",
        help="Skip prover matrix probe (still plans without capability gates)",
    )
    parser.add_argument(
        "--no-managed-path",
        action="store_true",
        help="Do not prepend managed theorem-provers bin to PATH",
    )
    parser.add_argument(
        "--with-obligations",
        action="store_true",
        help="Also run obligation compile + prove + kernel gate pipeline",
    )
    parser.add_argument(
        "--with-kernel",
        action="store_true",
        help="Also run full kernel reconstruction (Lean/Coq/Isabelle claim discharge)",
    )
    parser.add_argument(
        "--with-board-bind",
        action="store_true",
        help="Bind claim kernel receipts into repair board + RPR (implies --with-kernel)",
    )
    args = parser.parse_args(argv)
    execute = bool(args.execute) and not args.plan_only
    if args.with_board_bind:
        args.with_kernel = True

    managed = _setup(prepend_managed=not args.no_managed_path)
    print(f"managed_bin={managed}")
    print(f"which_proverif={shutil.which('proverif')}")
    print(f"which_tamarin={shutil.which('tamarin-prover') or shutil.which('tamarin')}")

    backends = register_datasets_backends()
    print(
        "backends:",
        json.dumps(backends.get("routes_registered"), indent=None),
        "probes=",
        {k: v.get("available") for k, v in (backends.get("backend_probes") or {}).items()},
    )

    matrix_snap = None
    matrix_summary: dict[str, Any] = {"skipped": True}
    if not args.skip_matrix:
        try:
            matrix_snap, matrix_summary = probe_matrix()
            print(
                f"matrix entries={matrix_summary.get('entry_count')} "
                f"smoke={len(matrix_summary.get('smoke_tested') or [])} "
                f"proverif={(matrix_summary.get('proverif') or {}).get('highest_state')} "
                f"tamarin={(matrix_summary.get('tamarin') or {}).get('highest_state')}"
            )
        except Exception as exc:  # noqa: BLE001
            matrix_summary = {"error": f"{type(exc).__name__}: {exc}"}
            print("matrix_error", matrix_summary["error"])

    protocol: dict[str, Any] = {"skipped": True}
    try:
        protocol = probe_protocol(run_conformance=not args.skip_conformance)
        print(
            "protocol_tools",
            [
                (t.get("tool"), t.get("available"), t.get("status"))
                for t in protocol.get("tools") or []
            ],
        )
        if protocol.get("core_verify", {}).get("attempted"):
            cv = protocol["core_verify"]
            print(
                "core_verify",
                cv.get("error")
                or [
                    (l.get("tool"), l.get("verdict"))
                    for l in (cv.get("lanes") or [])
                ]
                or cv.get("suite", {}).get("verdict"),
            )
    except Exception as exc:  # noqa: BLE001
        protocol = {"error": f"{type(exc).__name__}: {exc}"}
        print("protocol_error", protocol["error"])

    snapshot_id = ""
    if SUMMARY.exists():
        snapshot_id = str(
            json.loads(SUMMARY.read_text(encoding="utf-8")).get("snapshot_id") or ""
        )

    findings = load_findings(args.max_tasks)
    print(f"selected={len(findings)} snapshot={snapshot_id} execute={execute}")

    rows: list[dict[str, Any]] = []
    portfolio_error = None
    try:
        rows = plan_and_maybe_execute(
            matrix_snap=matrix_snap,
            matrix_summary=matrix_summary if isinstance(matrix_summary, dict) else {},
            protocol=protocol if isinstance(protocol, dict) else {},
            backends=backends,
            findings=findings,
            snapshot_id=snapshot_id,
            execute=execute,
        )
        for row in rows:
            kinds = ",".join(row.get("property_kinds") or [])
            exec_bits = []
            for p in row.get("portfolio_plans") or []:
                ex = p.get("execution") or {}
                if ex:
                    exec_bits.append(
                        f"{p.get('property_kind')}={ex.get('verdict') or ex.get('error')}"
                    )
            print(
                f"  {row.get('kind','')[:28]:28} {str(row.get('operation',''))[:28]:28} "
                f"kinds={kinds} {'; '.join(exec_bits)[:80]}"
            )
    except Exception as exc:  # noqa: BLE001
        portfolio_error = f"{type(exc).__name__}: {exc}"
        print("portfolio_error", portfolio_error)

    # Integration inventory: every matrix id + policy property kind
    from ipfs_accelerate_py.agent_supervisor.proof.multi_prover_router import (
        DEFAULT_PROPERTY_POLICIES,
        PropertyKind,
    )

    policy_map = {
        pk.value: {
            "policy_id": pol.policy_id,
            "lanes": [lane.prover_id for lane in pol.lanes],
        }
        for pk, pol in DEFAULT_PROPERTY_POLICIES.items()
    }

    protocol_ok = (
        isinstance(protocol, dict)
        and "error" not in protocol
        and any(
            t.get("available")
            and "conformant" in str(t.get("status", "")).lower()
            for t in (protocol.get("tools") or [])
        )
    )
    matrix_ok = (
        isinstance(matrix_summary, dict)
        and "error" not in matrix_summary
        and int(matrix_summary.get("entry_count") or 0) >= 10
    )
    backends_ok = all(
        (backends.get("backend_probes") or {}).get(k, {}).get("available")
        for k in ("cec", "tdfol", "smt", "hammer", "ir")
    ) and all((backends.get("routes_registered") or {}).values())

    # Optional: typed obligation compile + prove + kernel fail-closed gate
    obligations_summary: dict[str, Any] = {"ran": False, "skipped": True}
    if args.with_obligations:
        try:
            import subprocess

            obl_cmd = [
                sys.executable,
                str(REPO / "scripts" / "sca_obligation_kernel_pipeline.py"),
                "--max-tasks",
                str(args.max_tasks),
            ]
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join(
                [
                    str(REPO / "external" / "ipfs_accelerate"),
                    str(REPO / "external" / "ipfs_datasets"),
                    str(REPO / "external" / "ipfs_kit"),
                    str(REPO / "Mcp-Plus-Plus"),
                    env.get("PYTHONPATH", ""),
                ]
            )
            proc = subprocess.run(
                obl_cmd,
                cwd=str(REPO),
                env=env,
                capture_output=True,
                text=True,
                timeout=600,
            )
            obligations_summary = {
                "ran": True,
                "skipped": False,
                "exit_code": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-600:],
                "stderr_tail": (proc.stderr or "")[-300:],
                "report": str(
                    SCA / "evaluation" / "obligation_kernel_pipeline_report.json"
                ),
            }
            print(f"obligations_pipeline exit={proc.returncode}")
        except Exception as exc:  # noqa: BLE001
            obligations_summary = {
                "ran": False,
                "skipped": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    kernel_summary: dict[str, Any] = {"ran": False, "skipped": True}
    board_bind_summary: dict[str, Any] = {"ran": False, "skipped": True}
    if args.with_kernel:
        try:
            import subprocess

            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join(
                [
                    str(REPO / "external" / "ipfs_accelerate"),
                    str(REPO / "external" / "ipfs_datasets"),
                    str(REPO / "external" / "ipfs_kit"),
                    str(REPO / "Mcp-Plus-Plus"),
                    str(REPO / "scripts"),
                    env.get("PYTHONPATH", ""),
                ]
            )
            kr_cmd = [
                sys.executable,
                str(REPO / "scripts" / "sca_kernel_reconstruction_pipeline.py"),
                "--max-tasks",
                str(max(args.max_tasks, 8)),
                "--skip-hammer",
                "--max-isabelle-claims",
                "4",
                "--max-coq-claims",
                "16",
            ]
            proc = subprocess.run(
                kr_cmd,
                cwd=str(REPO),
                env=env,
                capture_output=True,
                text=True,
                timeout=1800,
            )
            kernel_summary = {
                "ran": True,
                "skipped": False,
                "exit_code": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-700:],
                "stderr_tail": (proc.stderr or "")[-300:],
                "report": str(SCA / "evaluation" / "kernel_reconstruction_pipeline_report.json"),
            }
            print(f"kernel_pipeline exit={proc.returncode}")
            if args.with_board_bind and proc.returncode == 0:
                bb = subprocess.run(
                    [
                        sys.executable,
                        str(REPO / "scripts" / "sca_bind_kernel_receipts_to_board.py"),
                    ],
                    cwd=str(REPO),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                board_bind_summary = {
                    "ran": True,
                    "skipped": False,
                    "exit_code": bb.returncode,
                    "stdout_tail": (bb.stdout or "")[-400:],
                    "report": str(SCA / "evaluation" / "claim_kernel_board_bind_report.json"),
                }
                print(f"board_bind exit={bb.returncode}")
        except Exception as exc:  # noqa: BLE001
            kernel_summary = {
                "ran": False,
                "skipped": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def _ok_or_skip(summary: dict[str, Any]) -> bool:
        return bool(
            summary.get("skipped")
            or (summary.get("ran") is True and summary.get("exit_code") == 0)
        )

    report = {
        "schema": "sca-full-prover-integration@2",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_id": snapshot_id,
        "completion_authoritative": False,
        "managed_bin": str(managed) if managed else None,
        "path_proverif": shutil.which("proverif"),
        "path_tamarin": shutil.which("tamarin-prover") or shutil.which("tamarin"),
        "datasets_backends": backends,
        "prover_matrix": matrix_summary,
        "protocol_layer": protocol,
        "property_policies": policy_map,
        "property_kinds": [pk.value for pk in PropertyKind],
        "execute": execute,
        "selected_count": len(findings),
        "portfolio_rows": rows,
        "portfolio_error": portfolio_error,
        "obligation_kernel_pipeline": obligations_summary,
        "kernel_reconstruction_pipeline": kernel_summary,
        "kernel_board_bind": board_bind_summary,
        "integration": {
            "datasets_backends": backends_ok,
            "prover_matrix": matrix_ok,
            "protocol_conformance": protocol_ok or args.skip_conformance,
            "multi_prover_router": portfolio_error is None,
            "managed_path": managed is not None,
            "obligation_kernel": _ok_or_skip(obligations_summary),
            "kernel_reconstruction": _ok_or_skip(kernel_summary),
            "kernel_board_bind": _ok_or_skip(board_bind_summary),
        },
        "notes": [
            "Full integration binds datasets backends + prover matrix + protocol "
            "adapters into MultiProverRouter portfolios for residual SCA findings.",
            "ProVerif/Tamarin require managed bin on PATH; conformance fixtures gate authority.",
            "Portfolio runner returns CANDIDATE for available tools — never mints KERNEL_VERIFIED.",
            "Claim KERNEL_VERIFIED uses observation_bound_operator_semantics@1 (Lean/Coq/Isabelle).",
            "Optional --with-kernel / --with-board-bind attach full residual kernel + board/RPR bind.",
            "Cross-package effects must use package_mcp_interop / tools/call.",
        ],
        "passed": (
            backends_ok
            and matrix_ok
            and portfolio_error is None
            and (protocol_ok or args.skip_conformance)
            and managed is not None
            and _ok_or_skip(obligations_summary)
            and _ok_or_skip(kernel_summary)
            and _ok_or_skip(board_bind_summary)
        ),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(f"report={REPORT}")
    print(
        "integration:",
        json.dumps(report["integration"], sort_keys=True),
    )
    print("PASSED" if report["passed"] else "FAILED")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
