#!/usr/bin/env python3
"""Python reference runner for normalized deontic parser element vectors."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "external" / "ipfs_datasets"))

from ipfs_datasets_py.logic.deontic.utils.deontic_parser import extract_normative_elements


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _first_slot(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            cleaned = _clean(item)
            if cleaned:
                return cleaned
        return ""
    return _clean(value)


def _normalize_action(action: str) -> str:
    action = re.sub(r"\s+", " ", str(action or "").strip()).lower()
    action = re.sub(r"[.;:,]+$", "", action)
    return action


def _normalize_subject(subject: str) -> str:
    subject = re.sub(r"\s+", " ", str(subject or "").strip()).lower()
    subject = re.sub(r"^(the|a|an)\s+", "", subject)
    subject = re.sub(r"[.;:,]+$", "", subject)
    return subject


def _normalize_values(values: Any) -> List[str]:
    normalized: List[str] = []
    for item in values or []:
        if isinstance(item, dict):
            item_type = _clean(item.get("type")).lower()
            item_value = _clean(item.get("value")).lower()
            if item_type and item_value:
                normalized.append(f"{item_type}:{item_value}")
                continue
            text_value = _clean(item.get("normalized_text") or item.get("raw_text")).lower()
            if text_value:
                normalized.append(text_value)
            continue
        text_value = _clean(item).lower()
        if text_value:
            normalized.append(text_value)
    return normalized


def _selected_formal_terms(element: Dict[str, Any]) -> Dict[str, str]:
    formal_terms = element.get("formal_terms") or {}
    keys = [
        "actor_id",
        "actor_predicate",
        "action_predicate",
        "object_predicate",
        "recipient_id",
        "norm_predicate",
        "category_predicate",
        "defined_term_id",
    ]
    return {key: str(formal_terms.get(key) or "") for key in keys}


def _normalize_element(element: Dict[str, Any]) -> Dict[str, Any]:
    subject = _normalize_subject(_first_slot(element.get("subject")))
    action = _normalize_action(_first_slot(element.get("action") or element.get("proposition")))
    return {
        "norm_type": str(element.get("norm_type") or ""),
        "deontic_operator": str(element.get("deontic_operator") or ""),
        "subject": subject,
        "action": action,
        "conditions": _normalize_values(element.get("conditions")),
        "temporal_constraints": _normalize_values(element.get("temporal_constraints")),
        "exceptions": _normalize_values(element.get("exceptions")),
        "cross_references": _normalize_values(element.get("cross_references")),
        "parser_warnings": sorted(str(item) for item in (element.get("parser_warnings") or [])),
        "formal_terms": _selected_formal_terms(element),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    vectors_path = Path(args.vectors)
    out_path = Path(args.out)

    payload = json.loads(vectors_path.read_text(encoding="utf-8"))
    rows: List[Dict[str, Any]] = []

    for vector in payload.get("vectors", []):
        elements = extract_normative_elements(vector.get("text", ""))
        normalized = [_normalize_element(element) for element in elements]
        rows.append(
            {
                "id": vector["id"],
                "count": len(normalized),
                "first": normalized[0] if normalized else None,
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"schemaVersion": payload.get("schemaVersion"), "results": rows}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
