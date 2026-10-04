#!/usr/bin/env python3
"""Convert recorded native imports to an exact, bounded invocation source profile."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from audit import digest, json_bytes

SCHEMA = "codebase-ir-observed-invocation-profile/v1"
MAX_REPORT_BYTES = 16777216


class ObservedProfileError(ValueError):
    pass


def sha(value: object) -> bool:
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def exact_pin(pin: object) -> bool:
    return (
        type(pin) is dict
        and set(pin) == {"sha256", "size_bytes"}
        and sha(pin["sha256"])
        and type(pin["size_bytes"]) is int
        and pin["size_bytes"] >= 0
    )


def unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ObservedProfileError("duplicate observation JSON key")
        result[key] = value
    return result


def owned_path(path: str, repositories: list[dict]) -> tuple[str, str, str]:
    target = Path(path)
    if not target.is_absolute() or target.resolve() != target or target.suffix != ".py":
        raise ObservedProfileError("observed source requires canonical absolute Python path")
    owners = []
    for repo in repositories:
        root = Path(repo["root"]).resolve()
        if target.is_relative_to(root):
            relative = target.relative_to(root)
            if relative.parts and relative.parts[0] in repo["packages"]:
                owners.append((repo["name"], relative))
    if len(owners) != 1:
        raise ObservedProfileError("observed source has no unique configured package owner")
    name, relative = owners[0]
    if any(part.startswith(".") or part in {"state", "workspace", "artifacts", "__pycache__"}
           for part in relative.parts):
        raise ObservedProfileError("observed source lies outside package source scope")
    module = ".".join(relative.with_suffix("").parts).removesuffix(".__init__")
    if not all(part.isidentifier() for part in module.split(".")):
        raise ObservedProfileError("observed path cannot name a Python module")
    return name, relative.as_posix(), module


def derive_profile(raw: bytes, source: Path, repositories: list[dict]) -> dict:
    if len(raw) > MAX_REPORT_BYTES:
        raise ObservedProfileError("observation report exceeds bounded input size")
    report = json.loads(raw, object_pairs_hook=unique_pairs)
    if (type(report) is not dict
            or report.get("schema") != "codebase-ir-finite-planning-qualification@1"
            or report.get("status") != "passed"
            or report.get("production_qualified") is not False
            or report.get("runtime_source_mode") != "working_tree_observed"
            or report.get("imported_native_source_bytes_stable") is not True):
        raise ObservedProfileError("completed stable working-source planning observation required")
    rows = report.get("imported_native_sources")
    if type(rows) is not list or not rows:
        raise ObservedProfileError("nonempty observed source records required")
    files, late, seen, seen_modules = [], [], set(), set()
    for row in rows:
        if (type(row) is not dict
                or set(row) != {"path", "module_names", "before", "after", "unchanged"}
                or type(row["path"]) is not str
                or type(row["module_names"]) is not list or not row["module_names"]
                or not all(type(name) is str and all(p.isidentifier() for p in name.split("."))
                           for name in row["module_names"])
                or len(set(row["module_names"])) != len(row["module_names"])
                or not exact_pin(row["after"])):
            raise ObservedProfileError("invalid observed file schema or exact digest/size")
        repository, path, module = owned_path(row["path"], repositories)
        key = (repository, path)
        if key in seen:
            raise ObservedProfileError("duplicate observed source path")
        seen.add(key)
        if seen_modules.intersection(row["module_names"]):
            raise ObservedProfileError("duplicate module assigned to different observed files")
        seen_modules.update(row["module_names"])
        package = module.split(".")[0]
        if module not in row["module_names"] or any(
            name.split(".")[0] != package for name in row["module_names"]
        ):
            raise ObservedProfileError("observed module names do not bind owned source")
        normalized = {"repository": repository, "path": path, "module": module,
                      "observation": row}
        if row["before"] is None:
            if row["unchanged"] is not False:
                raise ObservedProfileError("late import cannot assert before/after stability")
            late.append(normalized)
        elif not exact_pin(row["before"]) or row["before"] != row["after"] or row["unchanged"] is not True:
            raise ObservedProfileError("observed source changed or lacks exact before/after binding")
        else:
            files.append(normalized)
    profile = {"schema": SCHEMA, "source_report": str(source.resolve()),
               "source_report_sha256": digest(raw), "source_basis": "recorded_working_source_bytes",
               "files": sorted(files, key=lambda row: (row["repository"], row["path"])),
               "late_imports_unqualified": sorted(late, key=lambda row: (row["repository"], row["path"])),
               "observed_file_count": len(rows), "function_invocation_closure_proven": False}
    profile["profile_sha256"] = digest(json_bytes(profile))
    return profile


def validate_profile(profile: dict, repositories: list[dict]) -> dict[tuple[str, str], dict]:
    fields = {"schema", "source_report", "source_report_sha256", "source_basis", "files",
              "late_imports_unqualified", "observed_file_count", "function_invocation_closure_proven",
              "profile_sha256"}
    if (type(profile) is not dict or set(profile) != fields or profile["schema"] != SCHEMA
            or not sha(profile["source_report_sha256"]) or not sha(profile["profile_sha256"])
            or type(profile["source_report"]) is not str
            or type(profile["observed_file_count"]) is not int
            or profile["source_basis"] != "recorded_working_source_bytes"
            or profile["function_invocation_closure_proven"] is not False
            or type(profile["files"]) is not list or type(profile["late_imports_unqualified"]) is not list):
        raise ObservedProfileError("invalid observed profile schema")
    content = {key: value for key, value in profile.items() if key != "profile_sha256"}
    if digest(json_bytes(content)) != profile["profile_sha256"]:
        raise ObservedProfileError("observed profile identity differs")
    # Re-derive the records, including late imports, to avoid trusting normalized ownership fields.
    synthetic = {"schema": "codebase-ir-finite-planning-qualification@1", "status": "passed",
                 "production_qualified": False, "runtime_source_mode": "working_tree_observed",
                 "imported_native_source_bytes_stable": True, "imported_native_sources": []}
    for normalized in profile["files"] + profile["late_imports_unqualified"]:
        if type(normalized) is not dict or set(normalized) != {"repository", "path", "module", "observation"}:
            raise ObservedProfileError("invalid normalized observed source schema")
        synthetic["imported_native_sources"].append(normalized["observation"])
    derived = derive_profile(json_bytes(synthetic), Path(profile["source_report"]), repositories)
    if (derived["files"] != profile["files"]
            or derived["late_imports_unqualified"] != profile["late_imports_unqualified"]
            or derived["observed_file_count"] != profile["observed_file_count"]):
        raise ObservedProfileError("normalized observed ownership or population differs")
    return {(row["repository"], row["path"]): row for row in profile["files"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--report-sha256", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", action="append", default=[])
    args = parser.parse_args()
    with args.report.open("rb") as stream:
        raw = stream.read(MAX_REPORT_BYTES + 1)
    if digest(raw) != args.report_sha256:
        parser.error("observation report differs from explicit SHA256 pin")
    config = json.loads(args.config.read_bytes())
    config["observed_profile"] = derive_profile(raw, args.report, config["repositories"])
    config["nominate_eager_imports"] = False
    config["seeds"] = list(dict.fromkeys(config["seeds"] + args.seed))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(json_bytes(config))
    print(json.dumps({"output": str(args.output.resolve()),
                      "profile_sha256": config["observed_profile"]["profile_sha256"],
                      "observed_files": len(config["observed_profile"]["files"]),
                      "late_unqualified": len(config["observed_profile"]["late_imports_unqualified"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
