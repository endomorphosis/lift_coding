#!/usr/bin/env python3
"""Few-shot canaries: Leanstral generator + TypeSafe Jev gates + lake/lean oracle.

Not official Track 2. Not an Arena ranking. Jev does not generate Lean.
Never LOCK_EX. Never start llama-server. API keys are never written to receipts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
HARNESS = PAPER_ROOT / "harness"
LRA_REPO = HERE.parents[4]
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"

if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))
import _jevops_path  # noqa: E402,F401
from jevops.catalogs import ACCEL_ROOT as ROOT_ACCEL  # noqa: E402
from jevops.catalogs import AUTOSTART_ENV as AUTOSTART  # noqa: E402
from jevops.catalogs import CANARY_NAMES as LRA_CANARIES  # noqa: E402
from jevops.catalogs import FOL_CANARIES  # noqa: E402
from jevops.catalogs import TYPESAFE_KEYFILE as KEYFILE  # noqa: E402


def load_keyfile() -> None:
    from jevops.outer import load_env_file

    load_env_file(KEYFILE)


def pin_paths() -> None:
    from jevops.outer import pin_front_paths

    def _assign() -> None:
        import typesafe_router as lra_ts

        lra_ts.ACCEL_ROOT = ROOT_ACCEL
        lra_ts.TYPESAFE_INFERENCE_PATH = ROOT_ACCEL / "ipfs_accelerate_py" / "typesafe_inference.py"

    pin_front_paths(
        (HARNESS, LRA_REPO / "external/ipfs_datasets", LRA_REPO / "external/ipfs_accelerate", ROOT_ACCEL),
        env={AUTOSTART: "0"},
        defaults={
            "IPFS_ACCEL_SKIP_CORE": "1",
            "IPFS_AUTO_INSTALL": "false",
            "LRA_TYPESAFE": "distill",
            "IPFS_ACCELERATE_LLAMA_CPP_BASE_URL": "http://172.17.0.1:8080/v1",
        },
        assign_fn=_assign,
    )
    import _jevops_path  # noqa: F401


def redact(payload: Any) -> Any:
    from jevops.outer import redact_secret_fields

    return redact_secret_fields(payload)


def kernel_check_fol(declaration: str, body: str, timeout: float = 30.0) -> dict[str, Any]:
    """Self-contained Lean 4 check. Not a Mathlib/Strata lake oracle."""

    from jevops.lean import drive_home_lean

    return drive_home_lean(
        declaration,
        body,
        timeout=timeout,
        autostart_key=AUTOSTART,
        prefix="lra-fol-",
    )


def run_fol_canary(spec: Mapping[str, Any]) -> dict[str, Any]:
    from ipfs_accelerate_py.leanstral_typesafe import LeanstralGoal, propose_and_solve
    from jevops.lean import drive_fol_canary

    return drive_fol_canary(
        spec,
        goal_cls=LeanstralGoal,
        solve_fn=propose_and_solve,
        kernel_fn=kernel_check_fol,
        redact_fn=redact,
        base_url="http://172.17.0.1:8080/v1",
    )


def run_lra_canary(name: str, *, max_new_tokens: int, generate_timeout: float) -> dict[str, Any]:
    import retrieve as lra_retrieve
    import splice as lra_splice
    import typesafe_router as lra_ts
    import docker0_client as lra_d0
    import run_warmup as lra_loop
    from jevops.walk import drive_named_canary

    def _route(state: Any, names: list[str]) -> Any:
        return lra_ts.TypeSafeLraRouter(mode="distill").route(state, neighbor_names=names)

    return drive_named_canary(
        name,
        max_new_tokens=max_new_tokens,
        generate_timeout=generate_timeout,
        load_named_fn=lra_ts._load_named_record,
        neighbors_fn=lra_ts._neighbors_for,
        state_fn=lra_ts.problem_state,
        route_fn=_route,
        wants_llm_fn=lra_ts.should_call_leanstral,
        health_fn=lra_d0.probe_docker0_health,
        retrieve_fn=lra_retrieve.retrieve_record,
        prompt_fn=lra_loop.render_loop_prompt,
        generate_fn=lra_loop.maybe_generate,
        extract_fn=lra_loop.extract_generated_tactics,
        admit_fn=lra_splice.admission_view,
        redact_fn=redact,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--generate-timeout", type=float, default=180.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    load_keyfile()
    pin_paths()
    from ipfs_accelerate_py.typesafe_inference import typesafe_configured
    import docker0_client as lra_d0

    health = lra_d0.probe_docker0_health()
    started = time.perf_counter()
    rows = []
    errors = []
    for spec in FOL_CANARIES:
        try:
            rows.append(run_fol_canary(spec))
        except Exception as exc:  # noqa: BLE001 — retain the canary failure
            from jevops.outer import exc_text

            errors.append({"kind": "fol", "goal_id": spec["goal_id"], "error": exc_text(exc)})
            rows.append({"kind": "fol", "goal_id": spec["goal_id"], "ok": False, "error": exc_text(exc), "arena_score": None})
    for name in LRA_CANARIES:
        try:
            rows.append(run_lra_canary(name, max_new_tokens=args.max_new_tokens, generate_timeout=args.generate_timeout))
        except Exception as exc:  # noqa: BLE001
            from jevops.outer import exc_text

            errors.append({"kind": "lra_warmup", "name": name, "error": exc_text(exc)})
            rows.append({"kind": "lra_warmup", "name": name, "ok": False, "error": exc_text(exc), "arena_score": None})
    fol = [row for row in rows if row.get("kind") == "fol"]
    lra = [row for row in rows if row.get("kind") == "lra_warmup"]
    from jevops.outer import elapsed_ms, print_json, utc_stamp, write_json_pair

    summary = {
        "schema": "lra-canary-run/v1",
        "observed_at": utc_stamp(),
        "leanstral_health_ok": bool(health.ok),
        "typesafe_configured": bool(typesafe_configured()),
        "typesafe_key_in_receipt": False,
        "lock_ex": False,
        "llama_server_started": False,
        "official_track2": False,
        "arena_score": None,
        "n_canaries": len(rows),
        "fol_n": len(fol),
        "fol_kernel_ok": sum(1 for row in fol if (row.get("kernel") or {}).get("ok")),
        "fol_match_expected": sum(1 for row in fol if row.get("match_expected") is True),
        "lra_n": len(lra),
        "lra_admitted": sum(1 for row in lra if (row.get("admission") or {}).get("accepted")),
        "lra_jev_called": sum(1 for row in lra if (row.get("route") or {}).get("called_typesafe")),
        "errors": errors,
        "wall_ms": elapsed_ms(started),
        "canaries": rows,
    }
    summary = redact(summary)
    latest = write_json_pair(
        args.out,
        summary,
        prefix="canary-run",
        latest="latest.json",
        refuse="apikey_",
    )
    print_json({
        "ok": not errors and bool(health.ok) and bool(typesafe_configured()),
        "latest": str(latest),
        "leanstral_health_ok": summary["leanstral_health_ok"],
        "typesafe_configured": summary["typesafe_configured"],
        "fol_match_expected": summary["fol_match_expected"],
        "fol_kernel_ok": summary["fol_kernel_ok"],
        "lra_jev_called": summary["lra_jev_called"],
        "lra_admitted": summary["lra_admitted"],
        "errors": errors,
        "arena_score": None,
    })
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
