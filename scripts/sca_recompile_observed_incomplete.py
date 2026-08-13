#!/usr/bin/env python3
"""Focused recompile of observed package contracts for incomplete ops.

Re-extracts MCP package surfaces for accelerate, collapses multi-matches, and
recompiles observed routes for each open ``observed_contract_incomplete`` op.
Writes an evaluation receipt and optionally rewrites runtime_components
findings by closing incompletes that now resolve (observation refresh only;
not a full repository index handoff).

Usage:
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets \\
    python3 scripts/sca_recompile_observed_incomplete.py [--update-findings]
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
CONTRACT_FINDINGS = SCA / "baseline" / "runtime_components" / "contract_findings.json"


def _load_findings_doc() -> dict[str, Any]:
    """Load findings, preferring a merge of index emission + observation overlay."""
    base: dict[str, Any] = {"findings": []}
    by_id: dict[str, dict[str, Any]] = {}
    for path in (CONTRACT_FINDINGS, FINDINGS):
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if path == FINDINGS:
            base = doc if isinstance(doc, dict) else {"findings": []}
        for item in (doc.get("findings") if isinstance(doc, dict) else []) or []:
            if not isinstance(item, dict):
                continue
            fid = str(item.get("finding_id") or item.get("id") or "")
            key = fid or f"{item.get('kind')}:{item.get('contract_id')}"
            by_id[key] = item
    base = dict(base) if isinstance(base, dict) else {"findings": []}
    base["findings"] = list(by_id.values())
    return base
SUMMARY = SCA / "baseline" / "runtime_components" / "summary.json"
REPORT = SCA / "evaluation" / "observed_incomplete_recompile_report.json"
ACCELERATE = REPO / "external" / "ipfs_accelerate" / "ipfs_accelerate_py"

SURFACE_GLOBS = (
    "mcp_server/tools/**/*.py",
    "mcp_server/server.py",
    "mcp/tools/**/*.py",
    "datasets_integration/**/*.py",
)


def _setup_path() -> None:
    sys.path[:0] = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_kit"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "Mcp-Plus-Plus"),
        str(SCA / "runtime" / "pythonpath"),
    ]


def _surface_paths() -> list[Path]:
    paths: list[Path] = []
    for pattern in SURFACE_GLOBS:
        if "*" in pattern:
            paths.extend(ACCELERATE.glob(pattern))
        else:
            candidate = ACCELERATE / pattern
            if candidate.is_file():
                paths.append(candidate)
    out: list[Path] = []
    for path in paths:
        if not path.is_file() or path.suffix != ".py":
            continue
        text = str(path)
        if "/test" in text or "/__pycache__" in text or "/archives/" in text:
            continue
        out.append(path)
    return sorted(set(out))


def _build_package_surface():
    from ipfs_accelerate_py.agent_supervisor.analysis.python_mcp_surface_extractor import (
        extract_python_mcp_source,
        _build_surface,
    )

    tools = []
    unresolved = []
    source_files = []
    for path in _surface_paths():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if len(text.encode("utf-8", errors="ignore")) > 4_000_000:
            continue
        rel = str(path.relative_to(REPO))
        surface = extract_python_mcp_source(
            text, provider="ipfs_accelerate_py", path=rel
        )
        tools.extend(surface.tools)
        unresolved.extend(surface.unresolved)
        source_files.extend(surface.source_files)
    return _build_surface(
        provider="ipfs_accelerate_py",
        repository_tree_id="",
        tools=tools,
        unresolved=unresolved,
        source_files=source_files,
    )


def _incomplete_ops(findings_doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in findings_doc.get("findings") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or item.get("reason_code") or "")
        if kind != "observed_contract_incomplete":
            continue
        rows.append(item)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-findings",
        action="store_true",
        help=(
            "Rewrite runtime_components findings.json/contract_findings.json "
            "to drop incompletes that now resolve (observation refresh)"
        ),
    )
    args = parser.parse_args(argv)
    _setup_path()

    from ipfs_accelerate_py.agent_supervisor.analysis.runtime_contract_evidence_compiler import (
        _collapse_equivalent_tool_surfaces,
        compile_observed_package_contract,
        ReviewedRuntimeOperation,
    )
    from ipfs_accelerate_py.agent_supervisor.analysis.python_mcp_surface_extractor import (
        _canonical_tool_name,
    )

    findings_doc = _load_findings_doc()
    incomplete = _incomplete_ops(findings_doc)
    snapshot_id = ""
    if SUMMARY.exists():
        snapshot_id = str(
            json.loads(SUMMARY.read_text(encoding="utf-8")).get("snapshot_id") or ""
        )

    print(f"building package surface from {len(_surface_paths())} files…")
    package_surface = _build_package_surface()
    print(
        f"surface tools={len(package_surface.tools)} "
        f"unresolved={len(package_surface.unresolved)}"
    )

    results: list[dict[str, Any]] = []
    still_incomplete: list[str] = []
    resolved_ops: list[str] = []

    for item in incomplete:
        contract_id = str(item.get("contract_id") or "")
        op = contract_id.split(":", 1)[-1] if ":" in contract_id else contract_id
        tool_name = op
        # Build minimal operation for compile_observed_package_contract
        try:
            operation = ReviewedRuntimeOperation(
                operation_id=op,
                tool_name=tool_name,
                package_id="ipfs_accelerate_py",
                contract_ids=(contract_id,),
                source_ids=(f"source:finding:{item.get('finding_id', op)}",),
            )
        except TypeError:
            # Fallback if dataclass fields differ — construct via mapping API if any
            import inspect

            sig = inspect.signature(ReviewedRuntimeOperation)
            kwargs: dict[str, Any] = {}
            for name, param in sig.parameters.items():
                if name == "operation_id":
                    kwargs[name] = op
                elif name in {"tool_name", "name"}:
                    kwargs[name] = tool_name
                elif name == "package_id":
                    kwargs[name] = "ipfs_accelerate_py"
                elif name == "contract_ids":
                    kwargs[name] = (contract_id,)
                elif name == "source_ids":
                    kwargs[name] = (f"source:finding:{item.get('finding_id', op)}",)
                elif param.default is not inspect.Parameter.empty:
                    continue
                else:
                    kwargs[name] = None
            operation = ReviewedRuntimeOperation(**kwargs)

        matches = package_surface.tools_named(tool_name)
        collapsed = _collapse_equivalent_tool_surfaces(matches)
        observed, findings = compile_observed_package_contract(
            operation,
            package_surfaces=(package_surface,),
        )
        incomplete_findings = [
            f
            for f in findings
            if str(getattr(f, "kind", None) or getattr(f, "reason_code", "")).endswith(
                "incomplete"
            )
            or "incomplete" in str(getattr(f, "kind", "")).lower()
        ]
        complete = bool(observed.get("complete"))
        status = "resolved" if complete and not incomplete_findings else "still_incomplete"
        if status == "resolved":
            resolved_ops.append(op)
        else:
            still_incomplete.append(op)
        results.append(
            {
                "contract_id": contract_id,
                "operation": op,
                "canonical": _canonical_tool_name(op),
                "match_count": len(matches),
                "collapsed": collapsed is not None,
                "handler": (
                    getattr(getattr(collapsed, "handler", None), "symbol", None)
                    if collapsed
                    else None
                ),
                "observed_complete": complete,
                "status": status,
                "finding_kinds": [
                    str(getattr(f, "kind", getattr(f, "reason_code", "")))
                    for f in findings
                ],
            }
        )

    print(f"incomplete_in={len(incomplete)} resolved={len(resolved_ops)} still={len(still_incomplete)}")
    for row in results:
        print(
            f"  {row['status']:16} {row['operation']:35} "
            f"matches={row['match_count']} complete={row['observed_complete']} "
            f"handler={row.get('handler')}"
        )

    updated = False
    remaining_incomplete = len(still_incomplete)
    if args.update_findings and resolved_ops:
        resolved_set = set(resolved_ops)
        new_findings = []
        closed = 0
        for item in findings_doc.get("findings") or []:
            if not isinstance(item, dict):
                new_findings.append(item)
                continue
            kind = str(item.get("kind") or item.get("reason_code") or "")
            cid = str(item.get("contract_id") or "")
            op = cid.split(":", 1)[-1] if ":" in cid else cid
            if kind == "observed_contract_incomplete" and op in resolved_set:
                closed += 1
                continue
            new_findings.append(item)
        findings_doc["findings"] = new_findings
        findings_doc["observation_refresh"] = {
            "schema": "sca-observed-incomplete-refresh@1",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "closed_observed_contract_incomplete": closed,
            "resolved_ops": sorted(resolved_set),
            "authority": "observation_refresh_not_full_index",
            "snapshot_id_prior": snapshot_id,
        }
        FINDINGS.write_text(
            json.dumps(findings_doc, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        # Mirror into contract_findings if it carries the same incompletes
        if CONTRACT_FINDINGS.exists():
            cf = json.loads(CONTRACT_FINDINGS.read_text(encoding="utf-8"))
            if isinstance(cf.get("findings"), list):
                cf["findings"] = [
                    f
                    for f in cf["findings"]
                    if not (
                        isinstance(f, dict)
                        and str(f.get("kind") or f.get("reason_code") or "")
                        == "observed_contract_incomplete"
                        and str(f.get("contract_id") or "").split(":")[-1]
                        in resolved_set
                    )
                ]
                cf["observation_refresh"] = findings_doc["observation_refresh"]
                CONTRACT_FINDINGS.write_text(
                    json.dumps(cf, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
        updated = True
        remaining_incomplete = sum(
            1
            for f in new_findings
            if isinstance(f, dict)
            and str(f.get("kind") or f.get("reason_code") or "")
            == "observed_contract_incomplete"
        )
        print(f"updated findings: closed={closed} remaining_incomplete={remaining_incomplete}")

    report = {
        "schema": "ipfs_accelerate_py/agent-supervisor/sca-observed-incomplete-recompile@1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_id_prior": snapshot_id,
        "authority": "observation_refresh",
        "completion_authoritative": False,
        "package_surface_tool_count": len(package_surface.tools),
        "incomplete_in": len(incomplete),
        "resolved_count": len(resolved_ops),
        "still_incomplete": still_incomplete,
        "resolved_ops": resolved_ops,
        "results": results,
        "findings_updated": updated,
        "remaining_incomplete_count": remaining_incomplete,
        # Zero open incompletes is success (nothing left to recompile).
        "passed": len(still_incomplete) == 0,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(f"report={REPORT}")
    print("PASSED" if report["passed"] else "FAILED")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
