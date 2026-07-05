#!/usr/bin/env python3
"""Python reference runner for Legal-IR multiview document merge parity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

from ipfs_datasets_py.logic.bridge.multiview import _merge_reports_to_document
from ipfs_datasets_py.logic.bridge.types import (
    BridgeEvaluationReport,
    GraphProjectionResult,
    LegalIRDocument,
    LogicIRView,
    ProofGateResult,
    RoundTripMetrics,
)


def _view_from_payload(name: str, payload: Mapping[str, Any]) -> LogicIRView:
    return LogicIRView(
        name=name,
        payload=payload.get("payload") or {},
        format=str(payload.get("format") or ""),
        source_component=str(payload.get("sourceComponent") or payload.get("source_component") or ""),
        metadata=payload.get("metadata") or {},
    )


def _document_from_payload(payload: Mapping[str, Any]) -> LegalIRDocument:
    views = {
        str(name): _view_from_payload(str(name), view_payload)
        for name, view_payload in (payload.get("views") or {}).items()
    }
    return LegalIRDocument(
        document_id=str(payload["documentId"]),
        source_text=str(payload.get("sourceText") or ""),
        normalized_text=str(payload.get("normalizedText") or ""),
        source=str(payload.get("source") or "us_code"),
        citation=payload.get("citation"),
        views=views,
        frame_logic_triples=tuple(payload.get("frameLogicTriples") or []),
        metadata=payload.get("metadata") or {},
        version=str(payload.get("version") or "legal-ir-bridge-v1"),
    )


def _proof_gate_from_payload(payload: Mapping[str, Any]) -> ProofGateResult:
    return ProofGateResult(
        attempted_count=int(payload.get("attemptedCount") or payload.get("attempted_count") or 0),
        valid_count=int(payload.get("validCount") or payload.get("valid_count") or 0),
        unavailable_count=int(payload.get("unavailableCount") or payload.get("unavailable_count") or 0),
        error_count=int(payload.get("errorCount") or payload.get("error_count") or 0),
        failed_count=int(payload.get("failedCount") or payload.get("failed_count") or 0),
        verified_by=tuple(payload.get("verifiedBy") or payload.get("verified_by") or ()),
        details=tuple(payload.get("details") or ()),
    )


def _graph_projection_from_payload(payload: Mapping[str, Any]) -> GraphProjectionResult:
    return GraphProjectionResult(
        graph_id=str(payload.get("graphId") or payload.get("graph_id") or ""),
        neo4j_compatible=bool(payload.get("neo4jCompatible") or payload.get("neo4j_compatible") or False),
        node_count=int(payload.get("nodeCount") or payload.get("node_count") or 0),
        relationship_count=int(payload.get("relationshipCount") or payload.get("relationship_count") or 0),
        node_labels=tuple(payload.get("nodeLabels") or payload.get("node_labels") or ()),
        relationship_types=tuple(payload.get("relationshipTypes") or payload.get("relationship_types") or ()),
        metadata=payload.get("metadata") or {},
    )


def _report_from_payload(payload: Mapping[str, Any]) -> BridgeEvaluationReport:
    return BridgeEvaluationReport(
        adapter_name=str(payload["adapterName"]),
        target_component=str(payload.get("targetComponent") or ""),
        ir_document=_document_from_payload(payload["document"]),
        round_trip=RoundTripMetrics(),
        proof_gate=_proof_gate_from_payload(payload.get("proofGate") or {}),
        graph_projection=_graph_projection_from_payload(payload.get("graphProjection") or {}),
        decoded_text=str(payload.get("decodedText") or ""),
        status=str(payload.get("status") or "partial"),
        metadata=payload.get("metadata") or {},
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.vectors).read_text(encoding="utf-8"))
    rows: List[Dict[str, Any]] = []

    for vector in payload.get("vectors", []):
        reports = {
            str(report_payload["adapterName"]): _report_from_payload(report_payload)
            for report_payload in vector.get("reports", [])
        }
        document = _merge_reports_to_document(
            str(vector.get("sourceText") or ""),
            bridge_names=tuple(vector.get("bridgeNames") or ()),
            citation=vector.get("citation"),
            document_id=vector.get("documentId"),
            compiler_guidance=vector.get("compilerGuidance"),
            failures=vector.get("failures") or {},
            reports=reports,
            source=str(vector.get("source") or "us_code"),
        )
        rows.append(
            {
                "id": vector["id"],
                "document": document.to_dict(),
            }
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {"schemaVersion": payload.get("schemaVersion"), "results": rows},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
