#!/usr/bin/env python3
"""Seal an explicit retained source basis for historical admission replay."""

from __future__ import annotations

import argparse
from pathlib import Path

from audit import digest, json_bytes
from observed_profile import derive_profile
from retained_provenance import (
    Reader,
    document,
    exact_sha,
    need,
    pin_row,
    resolve_path,
    source_owner,
)
from retained_supplement import verify_profile
from snapshot_verify import verify_snapshot

SCHEMA = "codebase-ir-retained-replay-snapshot/v1"
MAX_FILES = 512
MAX_BYTES = 16777216
MAX_FILE_BYTES = 2097152


def critical_sources(before: dict, after: dict, *, workspace: Path, config: dict,
                     before_path: Path, reader: Reader) -> dict[tuple[str, str], dict]:
    fields = {"schema", "scope", "source_count", "sources"}
    need(set(before) == fields and set(after) == fields | {"changed_paths"}
         and before["schema"] == after["schema"] == "finite-admission-critical-producer-snapshot@1"
         and type(before["source_count"]) is int and type(after["source_count"]) is int
         and type(before["sources"]) is list and type(after["sources"]) is list
         and 1 <= len(before["sources"]) == before["source_count"] <= 128
         and len(after["sources"]) == after["source_count"] == before["source_count"]
         and after["changed_paths"] == [], "stable nonempty exact critical source population required")
    ending = {}
    for row in after["sources"]:
        pin_row(row, size_field="size_bytes")
        path = resolve_path(row["path"], workspace)
        need(path not in ending, "duplicate critical ending original path")
        ending[path] = row
    sources = {}
    for row in before["sources"]:
        pin_row(row, size_field="size_bytes", extra={"retained_source"})
        path = resolve_path(row["path"], workspace)
        owner, relative = source_owner(path, config)
        key = (owner, relative)
        need(key not in sources and path in ending, "duplicate or missing critical original path")
        end = ending[path]
        need(row["sha256"] == end["sha256"] and row["size_bytes"] == end["size_bytes"],
             "critical before/after identities conflict")
        retained = resolve_path(row["retained_source"], workspace)
        need(path.is_relative_to(workspace)
             and retained == before_path.parent / "sources" / path.relative_to(workspace),
             "critical retained copy does not bind exact original path")
        raw = reader.read(retained, row, size_field="size_bytes")
        need(len(raw) <= MAX_FILE_BYTES, "critical retained source exceeds source file ceiling")
        sources[key] = {"original_path": str(path), "retained_path": str(retained),
                        "sha256": row["sha256"], "bytes": row["size_bytes"],
                        "before": row, "after": end, "raw": raw}
    need({Path(row["original_path"]) for row in sources.values()} == set(ending),
         "critical ending population differs")
    return sources


def seal_retained_sources(
    *, historical_report: Path, historical_report_sha256: str, fixture: Path,
    source_before: Path, source_before_sha256: str, source_after: Path,
    source_after_sha256: str, initial_snapshot: Path, initial_snapshot_sha256: str,
    workspace: Path, config: dict, output: Path,
    supplemental_profile: Path | None = None, supplemental_profile_sha256: str | None = None,
) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    specs = {spec["name"]: spec for spec in config["repositories"]}
    need(len(specs) == len(config["repositories"]), "unique configured repository owners required")
    roots = [historical_report.parent, fixture, source_before.parent, source_after.parent,
             initial_snapshot] + [Path(spec["root"]).resolve(strict=True) for spec in specs.values()]
    reader = Reader(roots)
    if supplemental_profile is not None:
        reader.roots.append(supplemental_profile.parent)
    report = {"schema": SCHEMA, "disposition": "incomplete", "scope": "explicit retained source basis for selected historical replay",
              "runtime_closure_proven": False, "current_freshness_verified": False,
              "original_whole_producer_closure_replayed": False, "signature_verification_performed": False,
              "native_execution_performed": False, "production_qualified": False,
              "source_basis": "verified original critical copies override recorded current imports explicitly",
              "bounds": {"max_files": MAX_FILES, "max_bytes": MAX_BYTES, "max_file_bytes": MAX_FILE_BYTES}}
    inputs, selected, overrides, provenance_only = {}, {}, [], []
    supplement, supplemental_capture = None, None
    try:
        need((supplemental_profile is None) == (supplemental_profile_sha256 is None),
             "supplemental profile requires both path and explicit SHA256")
        def load(role: str, path: Path, expected: str | None = None) -> dict:
            need(expected is None or exact_sha(expected), "exact input SHA256 pin required")
            raw = reader.read(path)
            need(expected is None or digest(raw) == expected, "input artifact differs from explicit SHA256 pin")
            inputs[role] = {"path": str(path), "sha256": digest(raw), "bytes": len(raw)}
            (output / (role + ".json")).write_bytes(raw)
            return document(raw)
        historical = load("historical_report", historical_report, historical_report_sha256)
        need(historical.get("schema") == "codebase-ir-owner-local-historical-replay@1"
             and historical.get("status") in {"refused", "passed"}
             and historical.get("runtime_source_mode") == "working_tree_observed_read_only"
             and historical.get("read_files_unchanged") is True
             and historical.get("observed_current") is False
             and historical.get("native_observation_or_proof_invoked") is False
             and historical.get("worker_launched") is False
             and type(historical.get("training_steps")) is int and historical["training_steps"] == 0,
             "stable read-only historical import observation required")
        observed = historical.get("import_observations")
        need(type(observed) is dict and set(observed) == {"schema", "core_package_roots", "modules", "source_bytes_total", "complete_import_closure_claimed"}
             and observed["schema"] == "codebase-ir-historical-read-only-import-observation@1"
             and observed["complete_import_closure_claimed"] is False
             and type(observed["core_package_roots"]) is list
             and sorted(observed["core_package_roots"]) == sorted(str(Path(spec["root"]).resolve(strict=True)) for spec in specs.values())
             and type(observed["source_bytes_total"]) is int, "exact historical import observation scope required")
        synthetic = {"schema": "codebase-ir-finite-planning-qualification@1", "status": "passed",
                     "production_qualified": False, "runtime_source_mode": "working_tree_observed",
                     "imported_native_source_bytes_stable": True, "imported_native_sources": observed["modules"]}
        profile = derive_profile(json_bytes(synthetic), historical_report, config["repositories"])
        need(not profile["late_imports_unqualified"]
             and sum(row["observation"]["before"]["size_bytes"] for row in profile["files"]) == observed["source_bytes_total"],
             "late imports or historical aggregate byte mismatch refused")
        fixture_result = load("fixture_result", fixture / "result.json")
        need(fixture_result.get("schema") == "finite-repository-admission-qualification@1"
             and fixture_result.get("status") == "completed", "complete retained fixture source basis required")
        critical = critical_sources(load("critical_before", source_before, source_before_sha256),
                                    load("critical_after", source_after, source_after_sha256),
                                    workspace=workspace, config=config, before_path=source_before, reader=reader)
        prior = verify_snapshot(initial_snapshot, initial_snapshot_sha256)
        prior_manifest = load("initial_snapshot_manifest", initial_snapshot / "snapshot.json")
        need(prior_manifest["snapshot_sha256"] == initial_snapshot_sha256,
             "prior snapshot identity differs")
        bases: dict[tuple[str, str], list[dict]] = {}
        for row in profile["files"]:
            observation = row["observation"]
            bases.setdefault((row["repository"], row["path"]), []).append({
                "origin": "recorded_historical_import", "path": observation["path"],
                "sha256": observation["before"]["sha256"], "bytes": observation["before"]["size_bytes"],
                "observation": observation})
        for row in prior["files"]:
            need(row["repository"] in specs and Path(row["path"]).parts[0] in specs[row["repository"]]["packages"]
                 and row["path"].endswith(".py"), "prior snapshot file has no configured Python package owner")
            bases.setdefault((row["repository"], row["path"]), []).append({
                "origin": "verified_prior_generation", "path": str(initial_snapshot / row["repository"] / row["path"]),
                "sha256": row["sha256"], "bytes": row["bytes"], "generation_sha256": initial_snapshot_sha256})
        if supplemental_profile is not None:
            supplement, supplemental_capture = verify_profile(load("supplemental_profile", supplemental_profile, supplemental_profile_sha256),
                initial_snapshot=initial_snapshot, initial_snapshot_sha256=initial_snapshot_sha256, config=config)
            legacy_root = Path(supplement["legacy_snapshot"]["root"])
            report["source_basis"] += "; explicit supplemental basis: " + supplement["source_basis"]
            reader.roots.append(legacy_root)
            for row in supplement["selected_files"]:
                key = row["repository"], row["path"]
                need(key not in bases, "supplemental source conflicts with existing historical/prior scope")
                origin = "verified_original_retained_dependency_copy" if row["origin"] == "original_retained_dependency_copy" else "verified_earlier_static_capture"
                source_path = Path(row["source_path"])
                reader.roots.append(source_path.parent)
                bases[key] = [{"origin": origin, "path": str(source_path),
                               "sha256": row["sha256"], "bytes": row["bytes"],
                               "supplemental_profile_sha256": supplemental_profile_sha256,
                               "legacy_snapshot": supplement["legacy_snapshot"], "source_report": supplement["source_report"],
                               "frontier_report": supplement["frontier_report"], "static_selection": row}]
        for key, row in critical.items():
            if key not in bases:
                provenance_only.append({**{key: value for key, value in row.items() if key != "raw"},
                                        "disposition": "verified selected source outside recorded imported/prior-generation scope"})
        total = 0
        for key in sorted(bases):
            rows = bases[key]
            source = critical.get(key)
            if source is not None:
                raw = source["raw"]
                origin = "verified_original_critical_copy"
                actual_path = source["retained_path"]
                if any(row["sha256"] != source["sha256"] or row["bytes"] != source["bytes"] for row in rows):
                    overrides.append({"repository": key[0], "path": key[1],
                                      "selected_sha256": source["sha256"], "selected_bytes": source["bytes"],
                                      "selected_retained_path": actual_path, "replaced_bases": rows,
                                      "reason": "explicit original critical producer basis selected; different observed-current import retained as separate provenance"})
            else:
                need(rows and len({(row["sha256"], row["bytes"]) for row in rows}) == 1,
                     "conflicting same-original-path source bases without explicit retained override")
                chosen = next((row for row in rows if row["origin"] == "verified_prior_generation"), rows[0])
                actual_path, origin = chosen["path"], chosen["origin"]
                need(chosen["bytes"] <= MAX_FILE_BYTES, "selected source exceeds per-file bound")
                raw = reader.read(Path(actual_path), chosen)
            total += len(raw)
            need(len(selected) < MAX_FILES and total <= MAX_BYTES, "retained source snapshot file/byte bound exceeded")
            selected[key] = {"raw": raw, "repository": key[0], "path": key[1], "sha256": digest(raw),
                             "bytes": len(raw), "selected_origin": origin, "selected_path": actual_path,
                             "recorded_bases": rows,
                             "critical_copy_provenance": {k: v for k, v in source.items() if k != "raw"} if source else None}
        # Initializers may be supplied only by the explicit recorded source union.
        namespace_directories = set()
        for repository, path in selected:
            for parent in Path(path).parents:
                if parent == Path("."):
                    break
                init = (parent / "__init__.py").as_posix()
                if (repository, init) not in selected:
                    owner_root = Path(specs[repository]["root"])
                    need(not (owner_root / init).exists(), f"unrecorded ancestor package initializer refused: {repository}:{init}")
                    namespace_directories.add((repository, parent.as_posix()))
        stable = reader.stability()
        need(stable["stable"], "recorded retained source changed before sealing")
        if supplemental_capture is not None:
            need(supplemental_capture.stability()["stable"], "supplemental capture changed before sealing")
        target = output / "snapshots/generation-000"
        target.mkdir(parents=True)
        for repository in specs:
            (target / repository).mkdir()
        files = []
        for key, row in selected.items():
            path = target / key[0] / key[1]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(row["raw"])
            path.chmod(0o444)
            files.append({key: row[key] for key in ("repository", "path", "sha256", "bytes")})
        for repository, path in namespace_directories:
            (target / repository / path).mkdir(parents=True, exist_ok=True)
        manifest = {"schema": "codebase-ir-runtime-demand/v1", "generation": 0,
                    "parent_snapshot_sha256": initial_snapshot_sha256, "files": files,
                    "namespace_directories": [{"repository": repo, "path": path} for repo, path in sorted(namespace_directories)]}
        identity = digest(json_bytes(manifest))
        manifest["snapshot_sha256"] = identity
        (target / "snapshot.json").write_bytes(json_bytes(manifest))
        (target / "snapshot.json").chmod(0o444)
        for path in sorted((p for p in target.rglob("*") if p.is_dir()), reverse=True):
            path.chmod(0o555)
        target.chmod(0o555)
        verification = verify_snapshot(target.resolve(), identity)
        report.update({"disposition": "snapshot_sealed", "snapshot_root": str(target.resolve()),
                       "snapshot_roots": verification["snapshot_roots"], "snapshot_sha256": identity,
                       "snapshot_verification": verification, "initial_snapshot_verification": prior,
                       "source_origins": [{key: value for key, value in row.items() if key != "raw"} for row in selected.values()],
                       "retained_overrides": overrides, "provenance_only_sources": provenance_only,
                       "supplemental_basis": supplement,
                       "counts": {"files": len(selected), "bytes": total, "historical_import_files": len(profile["files"]),
                                  "original_critical_sources": len(critical), "prior_generation_files": len(prior["files"]),
                                  "retained_overrides": len(overrides), "provenance_only_sources": len(provenance_only)}})
        if supplement is not None:
            report["counts"]["supplemental_files"] = supplement["counts"]["selected_files"]
            report["counts"]["supplemental_earlier_static_files"] = sum(row["origin"] == "earlier_static_capture"
                                                                       for row in supplement["selected_files"])
            report["counts"]["supplemental_original_retained_dependency_files"] = sum(row["origin"] == "original_retained_dependency_copy"
                                                                                      for row in supplement["selected_files"])
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        report["disposition"] = "retained_snapshot_refused"
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report["input_artifacts"] = inputs
        report["raw_historical_report_sha256"] = inputs.get("historical_report", {}).get("sha256")
        report["raw_result_sha256"] = inputs.get("fixture_result", {}).get("sha256")
        report["source_stability"] = reader.stability()
        if supplemental_capture is not None:
            report["supplemental_source_stability"] = supplemental_capture.stability()
            if not report["supplemental_source_stability"]["stable"]:
                report["disposition"] = "retained_snapshot_refused"
                report["error"] = "supplemental earlier capture changed during snapshot qualification"
        if not report["source_stability"]["stable"]:
            report["disposition"] = "retained_snapshot_refused"
            report["error"] = "retained source changed during snapshot qualification"
        (output / "summary.json").write_bytes(json_bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-report", type=Path, required=True)
    parser.add_argument("--historical-report-sha256", required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--source-before", type=Path)
    parser.add_argument("--source-before-sha256", required=True)
    parser.add_argument("--source-after", type=Path)
    parser.add_argument("--source-after-sha256", required=True)
    parser.add_argument("--initial-snapshot", type=Path, required=True)
    parser.add_argument("--initial-snapshot-sha256", required=True)
    parser.add_argument("--supplemental-profile", type=Path)
    parser.add_argument("--supplemental-profile-sha256")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("runtime_service.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fixture = args.fixture.absolute()
    source_root = fixture.parent / fixture.name.replace("finite-admission-qualification-", "finite-admission-tests-")
    before = (args.source_before or source_root / "critical-source-before.json").absolute()
    after = (args.source_after or source_root / "critical-source-after.json").absolute()
    try:
        config_path = args.config.absolute()
        config = document(Reader([config_path.parent]).read(config_path))
        report = seal_retained_sources(historical_report=args.historical_report.absolute(),
                                      historical_report_sha256=args.historical_report_sha256,
                                      fixture=fixture, source_before=before, source_before_sha256=args.source_before_sha256,
                                      source_after=after, source_after_sha256=args.source_after_sha256,
                                      initial_snapshot=args.initial_snapshot.absolute(),
                                      initial_snapshot_sha256=args.initial_snapshot_sha256,
                                      workspace=args.workspace.absolute(), config=config, output=args.output.absolute(),
                                      supplemental_profile=args.supplemental_profile.absolute() if args.supplemental_profile else None,
                                      supplemental_profile_sha256=args.supplemental_profile_sha256)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"retained snapshot input refused: {exc}\n")
    print(json_bytes({key: report.get(key) for key in ("disposition", "snapshot_root", "snapshot_roots", "snapshot_sha256", "counts")}).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
