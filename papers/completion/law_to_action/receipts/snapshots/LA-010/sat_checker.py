#!/usr/bin/python3.12
"""Independent exhaustive SAT checker for small QF_BOOL CNF (LA-010).

This checker enumerates all 2^n assignments for n <= 16. It does not use
SymPy's DPLL and cannot upgrade SAT/UNSAT into theorem_proof.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


MAX_VARS = 16


def _parse_dimacs(text: str) -> tuple[int, list[list[int]]]:
    nvars = 0
    clauses: list[list[int]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("c"):
            continue
        if line.startswith("p "):
            parts = line.split()
            nvars = int(parts[2])
            continue
        lits = [int(tok) for tok in line.split()]
        if not lits or lits[-1] != 0:
            raise ValueError(f"DIMACS clause must end with 0: {line!r}")
        clause = lits[:-1]
        if clause:
            clauses.append(clause)
    return nvars, clauses


def _clause_holds(clause: list[int], bits: int) -> bool:
    for lit in clause:
        bit = (bits >> (abs(lit) - 1)) & 1
        if lit > 0 and bit == 1:
            return True
        if lit < 0 and bit == 0:
            return True
    return False


def _cnf_holds(clauses: list[list[int]], bits: int) -> bool:
    return all(_clause_holds(clause, bits) for clause in clauses)


def _model_to_bits(model: dict, nvars: int) -> int | None:
    bits = 0
    for i in range(1, nvars + 1):
        key = f"x{i}"
        if key not in model:
            return None
        if bool(model[key]):
            bits |= 1 << (i - 1)
    return bits


def main(argv: list[str]) -> int:
    if len(argv) not in {2, 3}:
        print(json.dumps({"status": "error", "reason": "usage: sat_checker.py FORMULA.json [PROVIDER.json]"}))
        return 2
    spec = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    provider = None
    if len(argv) == 3:
        provider = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    if spec.get("unsupported"):
        payload = {
            "status": "unsupported",
            "reason": spec["unsupported"],
            "checker": "exhaustive-truth-table",
            "authority_kind": "satisfiability",
            "agrees_with_provider": provider.get("status") == "unsupported" if provider else None,
        }
        json.dump(payload, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    nvars, clauses = _parse_dimacs(spec["dimacs"])
    if nvars > MAX_VARS:
        payload = {
            "status": "timeout_or_too_large",
            "reason": f"exhaustive checker refuses nvars={nvars} > {MAX_VARS}",
            "checker": "exhaustive-truth-table",
            "authority_kind": "satisfiability",
        }
        json.dump(payload, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    started = time.perf_counter()
    sat = False
    witness = None
    for bits in range(1 << nvars):
        if _cnf_holds(clauses, bits):
            sat = True
            witness = {f"x{i}": bool((bits >> (i - 1)) & 1) for i in range(1, nvars + 1)}
            break
    elapsed = time.perf_counter() - started
    claimed = None
    forged = False
    if provider and provider.get("status") == "sat":
        claimed = provider.get("model") or {}
        bits = _model_to_bits(claimed, nvars)
        forged = bits is None or not _cnf_holds(clauses, bits)
    elif provider and provider.get("status") == "unsat" and sat:
        forged = True
    elif provider and provider.get("status") == "sat" and not sat:
        forged = True
    agrees = None
    if provider and provider.get("status") in {"sat", "unsat"}:
        agrees = (provider["status"] == "sat") == sat and not forged
    payload = {
        "status": "sat" if sat else "unsat",
        "model": witness,
        "elapsed_seconds": elapsed,
        "nvars": nvars,
        "nclauses": len(clauses),
        "assignments_examined": 1 << nvars,
        "checker": "exhaustive-truth-table",
        "algorithm": "enumerate-all-assignments",
        "authority_kind": "satisfiability",
        "claimed_model_accepted": (not forged) if claimed is not None else None,
        "forged_evidence": forged,
        "agrees_with_provider": agrees,
    }
    json.dump(payload, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
