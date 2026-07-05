#!/usr/bin/env python3
"""Python reference runner for normalized deontic parser element vectors."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

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


def _normalize_element(element: Dict[str, Any]) -> Dict[str, str]:
    subject = _normalize_subject(_first_slot(element.get("subject")))
    action = _normalize_action(_first_slot(element.get("action") or element.get("proposition")))
    return {
        "deontic_operator": str(element.get("deontic_operator") or ""),
        "subject": subject,
        "action": action,
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
