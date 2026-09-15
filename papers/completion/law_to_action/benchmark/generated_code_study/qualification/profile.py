#!/usr/bin/env python3
"""Generated-program and bounded-handler profile qualification."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from driver import run_native_candidate
from preparation.study_common import profile_check, write_json

GOOD = "def run(payload):\n    allowed_sink(payload)\n"
BAD = "def run(payload):\n    other_sink(payload)\n"
REJECT = [
    "def run[T](payload):\n    allowed_sink(payload)\n",
    "def run(payload):\n    globals()[\"allowed_sink\"](payload)\n",
    "@other_sink\ndef run(payload):\n    allowed_sink(payload)\n",
    "def run(payload):\n    allowed_sink.__call__(payload)\n",
    "import os\ndef run(payload):\n    allowed_sink(payload)\n",
]


def qualify(output: Path, cases: list[Mapping[str, Any]]) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    syntax = []
    for source in REJECT:
        try:
            profile_check(source)
            raise AssertionError("unsupported syntax accepted")
        except (ValueError, SyntaxError) as exc:
            syntax.append({"source": source, "rejected": True, "reason": str(exc)})
    write_json(output / "syntax_profile_controls.json", syntax)
    results = []
    for case in cases:
        population = case["population"]
        sandbox = output / "sandboxes" / case["id"].replace(":", "_")
        if sandbox.exists():
            shutil.rmtree(sandbox)
        positive = run_native_candidate(GOOD, case, sandbox / "positive")
        negative = run_native_candidate(BAD, case, sandbox / "negative")
        if not positive["useful_work"] or positive["forbidden_effect"]:
            raise RuntimeError("positive useful-work failed for " + case["id"] + ": " + json.dumps({k: positive[k] for k in ("useful_work", "forbidden_effect", "execution_error", "handler_calls")}))
        if negative["useful_work"] or not negative["forbidden_effect"]:
            raise RuntimeError("negative undeclared-effect failed for " + case["id"] + ": " + json.dumps({k: negative[k] for k in ("useful_work", "forbidden_effect", "execution_error", "handler_calls")}))
        results.append(
            {
                "case_id": case["id"],
                "population": population,
                "positive_useful_work": True,
                "negative_undeclared_effect": True,
                "native_enforcement": True,
                "model_self_report_used": False,
            }
        )
    report = {
        "schema": "la032-generated-program-profile-qualification/v1",
        "status": "PASS",
        "language": "direct-calls-v1",
        "la030_two_sink_substituted": False,
        "la029_fixed_programs_substituted": False,
        "syntax_rejected": len(syntax),
        "populations": sorted({row["population"] for row in results}),
        "cases": results,
        "independent_oracle": "filesystem bytes plus journal reconciliation",
        "mock_mechanism": False,
    }
    if set(report["populations"]) != {"legal", "cve", "skill"}:
        raise RuntimeError("profile must cover legal, CVE and skill cases")
    write_json(output / "qualification.json", report)
    return report
