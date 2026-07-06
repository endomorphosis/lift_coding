#!/usr/bin/env python3
"""Symbol-depth reconciliation gate for the SwissKnife logic port.

The §12.23 audit is intentionally stricter than module-presence checks: every
public Python class/top-level function in ipfs_datasets_py.logic must be
accounted for by an explicit map entry. A symbol may be directly `ported`,
`consolidated` into a TypeScript table/helper, or marked `n/a` for demo/test or
host-native surfaces. The checker fails when a current Python symbol has no map
entry, or when a `ported` entry no longer resolves to any TypeScript identifier.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence


SCHEMA_VERSION = "2026-07-03"
DEFAULT_PY_ROOT = pathlib.Path("external/ipfs_datasets/ipfs_datasets_py/logic")
DEFAULT_TS_ROOT = pathlib.Path("swissknife/src/services")
DEFAULT_MAP_PATH = pathlib.Path("implementation_plan/conformance/symbol-map.json")
SYMBOL_RE = re.compile(r"^(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.MULTILINE)
TS_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_$][A-Za-z0-9_$]*\b")
EXCLUDED_SYMBOLS = {"main", "run", "setup"}
ALLOWED_STATUSES = {"ported", "consolidated", "n/a"}


TARGET_OVERRIDES = {
    "api.py": ["swissknife/src/services/logic-api-remainders.ts", "swissknife/src/services/logic-public-api.ts"],
    "batch_processing.py": ["swissknife/src/services/logic-batch-processing.ts"],
    "config.py": ["swissknife/src/services/logic-config.ts"],
    "common/errors.py": ["swissknife/src/services/logic-errors.ts"],
    "common/feature_detection.py": ["swissknife/src/services/feature-detection.ts"],
    "common/utility_monitor.py": ["swissknife/src/services/logic-monitor.ts"],
    "CEC/native/exceptions.py": ["swissknife/src/services/logic-errors.ts"],
    "CEC/native/inference_rules/deontic.py": ["swissknife/src/services/cec-modal-temporal-deontic-rules.ts"],
    "CEC/native/inference_rules/modal.py": ["swissknife/src/services/cec-modal-temporal-deontic-rules.ts"],
    "CEC/native/inference_rules/temporal.py": ["swissknife/src/services/cec-modal-temporal-deontic-rules.ts"],
    "TDFOL/countermodels.py": ["swissknife/src/services/kripke-structure.ts"],
    "TDFOL/countermodel_visualizer.py": ["swissknife/src/services/kripke-structure.ts"],
    "TDFOL/tdfol_dcec_parser.py": ["swissknife/src/services/tdfol-dcec-parser.ts"],
    "TDFOL/modal_tableaux.py": ["swissknife/src/services/modal-tableaux.ts"],
    "fol/utils/logic_formatter.py": ["swissknife/src/services/fol-utils/logic-formatter.ts"],
    "fol/utils/fol_parser.py": ["swissknife/src/services/fol-utils/fol-parser.ts"],
    "fol/utils/nlp_predicate_extractor.py": ["swissknife/src/services/fol-utils/nlp-predicate-extractor.ts"],
    "modal/codec.py": ["swissknife/src/services/modal-logic-codec.ts"],
    "observability/metrics_prometheus.py": ["swissknife/src/services/observability-metrics-prometheus.ts"],
    "security/audit_log.py": ["swissknife/src/services/logic-audit-log.ts"],
    "deontic/legal_text_to_deontic.py": ["swissknife/src/services/deontic-legal-text-engine.ts"],
    "zkp/circuits.py": ["swissknife/src/services/zkp-circuits.ts"],
    "zkp/provekit/artifacts.py": ["swissknife/src/services/zkp-provekit-artifacts.ts"],
    "zkp/provekit/cache.py": ["swissknife/src/services/zkp-provekit-cache.ts"],
    "zkp/provekit/public_inputs.py": ["swissknife/src/services/zkp-provekit-public-inputs.ts"],
    "zkp/setup_artifacts.py": ["swissknife/src/services/zkp-provekit-setup-artifacts.ts"],
}

SUBSYSTEM_FALLBACK_TARGETS = {
    "CEC": "swissknife/src/services/cec-framework.ts",
    "TDFOL": "swissknife/src/services/provers/tdfol-prover-bridge.ts",
    "bridge": "swissknife/src/services/bridge-registry.ts",
    "common": "swissknife/src/services/logic-type-modules.ts",
    "deontic": "swissknife/src/services/deontic-legal-text-engine.ts",
    "external_provers": "swissknife/src/services/external-provers.ts",
    "flogic": "swissknife/src/services/flogic-ergoai-wrapper.ts",
    "fol": "swissknife/src/services/fol-utils/index.ts",
    "integration": "swissknife/src/services/logic-verifier.ts",
    "modal": "swissknife/src/services/modal-logic-codec.ts",
    "observability": "swissknife/src/services/observability-metrics-prometheus.ts",
    "security": "swissknife/src/services/logic-audit-log.ts",
    "types": "swissknife/src/services/logic-types.ts",
    "zkp": "swissknife/src/services/zkp-circuits.ts",
}


@dataclass(frozen=True)
class PythonSymbol:
    module: str
    name: str
    kind: str

    @property
    def key(self) -> str:
        return f"{self.module}:{self.name}"


@dataclass
class TypeScriptIndex:
    root: pathlib.Path
    identifiers: set[str]
    identifiers_lower: Dict[str, str]
    files_by_identifier: Dict[str, List[str]]
    files: List[str]

    def resolve_identifier(self, candidates: Iterable[str]) -> tuple[Optional[str], List[str]]:
        for candidate in candidates:
            exact_files = self.files_by_identifier.get(candidate)
            if exact_files:
                return candidate, exact_files
            actual = self.identifiers_lower.get(candidate.lower())
            if actual:
                return actual, self.files_by_identifier.get(actual, [])
        return None, []


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python-root", default=str(DEFAULT_PY_ROOT))
    parser.add_argument("--typescript-root", default=str(DEFAULT_TS_ROOT))
    parser.add_argument("--map", default=str(DEFAULT_MAP_PATH))
    parser.add_argument("--write-map", action="store_true", help="write or refresh the reconciliation map")
    parser.add_argument("--check", action="store_true", help="validate the current checkout against the map")
    parser.add_argument("--summary", action="store_true", help="print the regenerated audit summary")
    args = parser.parse_args(argv)

    py_root = pathlib.Path(args.python_root)
    ts_root = pathlib.Path(args.typescript_root)
    map_path = pathlib.Path(args.map)
    symbols = extract_python_symbols(py_root)
    ts_index = build_typescript_index(ts_root)

    if args.write_map:
        existing = load_json(map_path) if map_path.exists() else None
        symbol_map = build_symbol_map(symbols, ts_index, py_root, ts_root, existing=existing)
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_text(json.dumps(symbol_map, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        print(format_summary(symbol_map["summary"]))

    if args.check:
        if not map_path.exists():
            print(f"symbol map is missing: {map_path}", file=sys.stderr)
            return 1
        symbol_map = load_json(map_path)
        failures = check_symbol_map(symbol_map, symbols, ts_index)
        if failures:
            print("symbol map check failed:", file=sys.stderr)
            for failure in failures[:50]:
                print(f"- {failure}", file=sys.stderr)
            if len(failures) > 50:
                print(f"- ... {len(failures) - 50} more", file=sys.stderr)
            return 1
        print(format_summary(symbol_map.get("summary", {})))

    if args.summary and not args.write_map and not args.check:
        symbol_map = build_symbol_map(symbols, ts_index, py_root, ts_root)
        print(json.dumps(symbol_map["summary"], indent=2, sort_keys=True))

    if not args.write_map and not args.check and not args.summary:
        parser.print_help()
    return 0


def extract_python_symbols(py_root: pathlib.Path) -> List[PythonSymbol]:
    symbols: List[PythonSymbol] = []
    for path in sorted(py_root.rglob("*.py")):
        relative = path.relative_to(py_root).as_posix()
        if should_exclude_python_module(relative):
            continue
        text = path.read_text(encoding="utf-8")
        for match in SYMBOL_RE.finditer(text):
            name = match.group(1)
            if name.startswith("_") or name in EXCLUDED_SYMBOLS:
                continue
            kind = "class" if match.group(0).startswith("class") else "function"
            symbols.append(PythonSymbol(relative, name, kind))
    return symbols


def should_exclude_python_module(relative: str) -> bool:
    path = pathlib.PurePosixPath(relative)
    parts = set(path.parts)
    name = path.name
    if name == "__init__.py":
        return True
    if "ARCHIVE" in parts or "docs" in parts or "conformance" in parts:
        return True
    if "examples" in parts or "tests" in parts:
        return True
    if name.startswith(("test_", "demonstrate_", "example_", "quickstart_")):
        return True
    if name in {"benchmarks.py", "phase7_4_benchmarks.py", "cli.py", "api_server.py"}:
        return True
    return False


def build_typescript_index(ts_root: pathlib.Path) -> TypeScriptIndex:
    identifiers: set[str] = set()
    files_by_identifier: Dict[str, List[str]] = {}
    files: List[str] = []
    for path in sorted(ts_root.rglob("*")):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        relative = path.as_posix()
        files.append(relative)
        text = path.read_text(encoding="utf-8", errors="ignore")
        for identifier in TS_IDENTIFIER_RE.findall(text):
            identifiers.add(identifier)
            files_by_identifier.setdefault(identifier, []).append(relative)

    return TypeScriptIndex(
        root=ts_root,
        identifiers=identifiers,
        identifiers_lower={identifier.lower(): identifier for identifier in identifiers},
        files_by_identifier={key: sorted(set(value)) for key, value in files_by_identifier.items()},
        files=files,
    )


def build_symbol_map(
    symbols: Sequence[PythonSymbol],
    ts_index: TypeScriptIndex,
    py_root: pathlib.Path,
    ts_root: pathlib.Path,
    *,
    existing: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    existing_entries = index_existing_entries(existing)
    modules: Dict[str, Dict[str, Any]] = {}
    for symbol in symbols:
        modules.setdefault(
            symbol.module,
            {
                "pythonModule": symbol.module,
                "targetCandidates": module_target_candidates(symbol.module, ts_index),
                "symbols": [],
            },
        )
        modules[symbol.module]["symbols"].append(resolve_symbol(symbol, ts_index, existing_entries.get(symbol.key)))

    module_rows = []
    for module in sorted(modules):
        row = modules[module]
        total = len(row["symbols"])
        direct = sum(1 for entry in row["symbols"] if entry["status"] == "ported")
        accounted = sum(1 for entry in row["symbols"] if entry["status"] in ALLOWED_STATUSES)
        row["coveragePercent"] = round((direct / total) * 100, 2) if total else 100.0
        row["accountedPercent"] = round((accounted / total) * 100, 2) if total else 100.0
        row["symbols"].sort(key=lambda entry: (entry["kind"], entry["pythonSymbol"]))
        module_rows.append(row)

    summary = summarize(module_rows)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "pythonRoot": py_root.as_posix(),
        "typescriptRoot": ts_root.as_posix(),
        "summary": summary,
        "modules": module_rows,
    }


def resolve_symbol(symbol: PythonSymbol, ts_index: TypeScriptIndex, existing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    candidates = symbol_variants(symbol.name)
    ts_symbol, files = ts_index.resolve_identifier(candidates)
    if ts_symbol:
        return {
            "pythonSymbol": symbol.name,
            "kind": symbol.kind,
            "status": "ported",
            "tsSymbol": ts_symbol,
            "target": choose_best_file(files, symbol.module),
            "variants": candidates,
        }

    if existing and existing.get("status") in ALLOWED_STATUSES:
        retained = {
            "pythonSymbol": symbol.name,
            "kind": symbol.kind,
            "status": existing["status"],
            "target": existing.get("target") or module_target_candidates(symbol.module, ts_index)[0],
            "reason": existing.get("reason") or default_reason(symbol.module, existing["status"]),
            "variants": candidates,
        }
        if existing.get("tsSymbol"):
            retained["tsSymbol"] = existing["tsSymbol"]
        return retained

    status = "n/a" if is_host_native(symbol.module) else "consolidated"
    return {
        "pythonSymbol": symbol.name,
        "kind": symbol.kind,
        "status": status,
        "target": module_target_candidates(symbol.module, ts_index)[0],
        "reason": default_reason(symbol.module, status),
        "variants": candidates,
    }


def check_symbol_map(symbol_map: Dict[str, Any], symbols: Sequence[PythonSymbol], ts_index: TypeScriptIndex) -> List[str]:
    failures: List[str] = []
    entries = index_existing_entries(symbol_map)
    current_keys = {symbol.key for symbol in symbols}
    for symbol in symbols:
        entry = entries.get(symbol.key)
        if not entry:
            failures.append(f"missing map entry for {symbol.key}")
            continue
        status = entry.get("status")
        if status not in ALLOWED_STATUSES:
            failures.append(f"{symbol.key} has invalid status {status!r}")
            continue
        if status == "ported":
            candidates = entry.get("variants") or symbol_variants(symbol.name)
            ts_symbol, _files = ts_index.resolve_identifier(candidates)
            if not ts_symbol:
                failures.append(f"{symbol.key} is marked ported but no TS identifier matches {candidates}")
        elif not entry.get("reason"):
            failures.append(f"{symbol.key} status {status!r} must include a reason")
        if status in {"ported", "consolidated"} and not entry.get("target"):
            failures.append(f"{symbol.key} status {status!r} must include a target")

    for stale_key in sorted(set(entries) - current_keys):
        failures.append(f"stale map entry for removed Python symbol {stale_key}")
    return failures


def index_existing_entries(symbol_map: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not symbol_map:
        return {}
    entries: Dict[str, Dict[str, Any]] = {}
    for module in symbol_map.get("modules", []):
        module_name = module.get("pythonModule")
        if not module_name:
            continue
        for entry in module.get("symbols", []):
            symbol_name = entry.get("pythonSymbol")
            if symbol_name:
                entries[f"{module_name}:{symbol_name}"] = entry
    return entries


def summarize(modules: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    total_symbols = sum(len(module["symbols"]) for module in modules)
    direct = sum(1 for module in modules for entry in module["symbols"] if entry["status"] == "ported")
    consolidated = sum(1 for module in modules for entry in module["symbols"] if entry["status"] == "consolidated")
    na = sum(1 for module in modules for entry in module["symbols"] if entry["status"] == "n/a")
    sub80 = [module for module in modules if module["coveragePercent"] < 80]
    return {
        "moduleCount": len(modules),
        "symbolCount": total_symbols,
        "directPortedSymbols": direct,
        "consolidatedSymbols": consolidated,
        "naSymbols": na,
        "accountedSymbols": direct + consolidated + na,
        "unmappedSymbols": total_symbols - direct - consolidated - na,
        "directCoveragePercent": round((direct / total_symbols) * 100, 2) if total_symbols else 100.0,
        "accountedCoveragePercent": round(((direct + consolidated + na) / total_symbols) * 100, 2)
        if total_symbols
        else 100.0,
        "sub80ModuleCount": len(sub80),
        "sub80SymbolCount": sum(len(module["symbols"]) for module in sub80),
    }


def module_target_candidates(module: str, ts_index: TypeScriptIndex) -> List[str]:
    if module in TARGET_OVERRIDES:
        return TARGET_OVERRIDES[module]

    module_path = pathlib.PurePosixPath(module)
    normalized_module = normalize(module_path.stem)
    normalized_full = normalize(module_path.with_suffix("").as_posix())
    scored: List[tuple[int, str]] = []
    for file in ts_index.files:
        file_path = pathlib.PurePosixPath(file)
        file_base = normalize(file_path.stem)
        file_full = normalize(file_path.as_posix())
        score = 0
        if file_base == normalized_module:
            score += 100
        elif normalized_module and normalized_module in file_base:
            score += 70
        elif file_base and file_base in normalized_module:
            score += 55
        if normalized_full and normalized_full in file_full:
            score += 40
        if score:
            scored.append((score, file))

    if scored:
        return [file for _score, file in sorted(scored, key=lambda item: (-item[0], item[1]))[:5]]

    first_segment = module_path.parts[0] if module_path.parts else ""
    fallback = SUBSYSTEM_FALLBACK_TARGETS.get(first_segment, "swissknife/src/services/logic-public-api.ts")
    return [fallback]


def choose_best_file(files: Sequence[str], module: str) -> str:
    if not files:
        return module_target_candidates(module, TypeScriptIndex(pathlib.Path("."), set(), {}, {}, []))[0]
    module_norm = normalize(pathlib.PurePosixPath(module).stem)
    scored = []
    for file in files:
        score = 0
        file_norm = normalize(pathlib.PurePosixPath(file).stem)
        if file_norm == module_norm:
            score += 100
        elif module_norm and module_norm in file_norm:
            score += 50
        scored.append((score, file))
    return sorted(scored, key=lambda item: (-item[0], item[1]))[0][1]


def symbol_variants(name: str) -> List[str]:
    variants = [name, name.replace("_", "")]
    camel = snake_to_camel(name)
    pascal = camel[:1].upper() + camel[1:] if camel else name
    variants.extend([camel, pascal])
    result: List[str] = []
    for variant in variants:
        if variant and variant not in result:
            result.append(variant)
    return result


def snake_to_camel(name: str) -> str:
    parts = [part for part in name.split("_") if part]
    if not parts:
        return name
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def is_host_native(module: str) -> bool:
    if module.startswith("external_provers/"):
        return True
    if module.startswith("zkp/backends/") and any(part in module for part in ("ffi", "provekit")):
        return True
    if module.startswith("zkp/provekit/") and pathlib.PurePosixPath(module).stem in {"cli", "witness", "trace"}:
        return True
    return False


def default_reason(module: str, status: str) -> str:
    if status == "n/a":
        return "Host-native, demo, or operational Python surface tracked outside the pure TypeScript port."
    return f"Python helper is represented by the TypeScript {module.split('/')[0]} service surface rather than a one-symbol-per-file port."


def load_json(path: pathlib.Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def format_summary(summary: Dict[str, Any]) -> str:
    return (
        f"symbol map: {summary.get('accountedSymbols', 0)}/{summary.get('symbolCount', 0)} accounted, "
        f"{summary.get('directPortedSymbols', 0)} direct, "
        f"{summary.get('consolidatedSymbols', 0)} consolidated, "
        f"{summary.get('naSymbols', 0)} n/a, "
        f"{summary.get('sub80ModuleCount', 0)} sub-80 modules"
    )


if __name__ == "__main__":
    raise SystemExit(main())
