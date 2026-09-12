#!/usr/bin/python3.12
"""In-process QF_BOOL SAT provider using SymPy (LA-010).

This is a satisfiability provider. It never emits theorem_proof authority.
Unsupported fragments (quantifiers, interpolation, non-Boolean theories)
are rejected without a SAT answer.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def _fail(status: str, reason: str, extra: dict | None = None) -> int:
    payload = {"status": status, "reason": reason, "authority_kind": "satisfiability"}
    if extra:
        payload.update(extra)
    json.dump(payload, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if status in {"sat", "unsat", "unsupported"} else 2


def _parse_dimacs(text: str) -> tuple[int, list[list[int]]]:
    nvars = 0
    clauses: list[list[int]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("c"):
            continue
        if line.startswith("p "):
            parts = line.split()
            if len(parts) < 4 or parts[1] != "cnf":
                raise ValueError(f"invalid DIMACS header: {line!r}")
            nvars = int(parts[2])
            continue
        lits = [int(tok) for tok in line.split()]
        if not lits or lits[-1] != 0:
            raise ValueError(f"DIMACS clause must end with 0: {line!r}")
        clause = lits[:-1]
        if not clause:
            continue
        clauses.append(clause)
    if nvars <= 0:
        raise ValueError("DIMACS formula missing variable count")
    return nvars, clauses


def _solve_dimacs(nvars: int, clauses: list[list[int]]) -> dict:
    from sympy.core.symbol import Symbol
    from sympy.logic.boolalg import And, Or, Not, true
    from sympy.logic.inference import satisfiable

    symbols = {i: Symbol(f"x{i}") for i in range(1, nvars + 1)}
    encoded = []
    for clause in clauses:
        terms = []
        for lit in clause:
            if lit == 0 or abs(lit) > nvars:
                raise ValueError(f"literal {lit} out of range for {nvars} vars")
            atom = symbols[abs(lit)]
            terms.append(atom if lit > 0 else Not(atom))
        encoded.append(Or(*terms) if len(terms) > 1 else terms[0])
    formula = And(*encoded) if encoded else true
    started = time.perf_counter()
    model = satisfiable(formula, algorithm="dpll")
    elapsed = time.perf_counter() - started
    import sympy

    if model is False:
        return {
            "status": "unsat",
            "model": None,
            "elapsed_seconds": elapsed,
            "nvars": nvars,
            "nclauses": len(clauses),
            "provider": "sympy.logic.inference.satisfiable",
            "algorithm": "dpll",
            "sympy_version": sympy.__version__,
            "authority_kind": "satisfiability",
            "query_kind": "satisfiability",
        }
    assignment = {str(sym): bool(val) for sym, val in dict(model).items()}
    return {
        "status": "sat",
        "model": assignment,
        "elapsed_seconds": elapsed,
        "nvars": nvars,
        "nclauses": len(clauses),
        "provider": "sympy.logic.inference.satisfiable",
        "algorithm": "dpll",
        "sympy_version": sympy.__version__,
        "authority_kind": "satisfiability",
        "query_kind": "satisfiability",
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return _fail("error", "usage: sat_provider.py FORMULA.json")
    path = Path(argv[1])
    spec = json.loads(path.read_text(encoding="utf-8"))
    unsupported = spec.get("unsupported")
    if unsupported:
        return _fail(
            "unsupported",
            str(unsupported),
            {
                "fragment": spec.get("fragment"),
                "family": spec.get("family"),
                "query_kind": spec.get("query_kind", "unknown"),
                "provider": "sympy-sat",
            },
        )
    fmt = spec.get("format")
    if fmt != "dimacs":
        return _fail("unsupported", f"formula format {fmt!r} is not QF_BOOL DIMACS")
    nvars, clauses = _parse_dimacs(spec["dimacs"])
    result = _solve_dimacs(nvars, clauses)
    result["formula_id"] = spec.get("id")
    json.dump(result, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except Exception as exc:  # noqa: BLE001 — provider must emit a record
        json.dump(
            {
                "status": "error",
                "reason": f"{type(exc).__name__}: {exc}",
                "authority_kind": "satisfiability",
            },
            sys.stdout,
            sort_keys=True,
        )
        sys.stdout.write("\n")
        raise SystemExit(2)
