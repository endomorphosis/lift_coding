"""Read-only core interface checks with all writes confined to a fresh output.

Default checks parse requirements and compile exact source without running it.
--observe additionally runs bounded Python/Lean checks on private authored
repositories. No production admission, worker launch, or registry updates occur.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from codebase_ir_acceptance import (
    FALSE_AUTHORITY,
    OFFSET_CLAUSE,
    TYPE_CLAUSE,
    canonical_bytes,
    scenarios,
    sha256,
    source_function,
    validate_native_result,
)


def native_source_snapshot() -> tuple[list[Path], dict[str, dict[str, Any]]]:
    """Snapshot possible core imports before execution; retain only actual imports."""
    roots, snapshots = [], {}
    for name in ("ipfs_accelerate_py", "ipfs_datasets_py"):
        specification = importlib.util.find_spec(name)
        if specification is None:
            continue
        for location in specification.submodule_search_locations or []:
            root = Path(location).resolve()
            roots.append(root)
            for path in root.rglob("*.py"):
                if not path.is_file():
                    continue
                raw = path.read_bytes()
                snapshots[str(path.resolve())] = {"sha256": sha256(raw), "size_bytes": len(raw)}
    return roots, snapshots


def imported_native_sources(roots: list[Path], before: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    imported = {}
    for module_name, module in tuple(sys.modules.items()):
        raw_path = getattr(module, "__file__", None)
        if not raw_path:
            continue
        path = Path(raw_path).resolve()
        if path.suffix != ".py" or not any(path.is_relative_to(root) for root in roots):
            continue
        imported.setdefault(path, []).append(module_name)
    records = []
    for path, module_names in sorted(imported.items()):
        raw = path.read_bytes()
        after = {"sha256": sha256(raw), "size_bytes": len(raw)}
        initial = before.get(str(path))
        records.append({"path": str(path), "module_names": sorted(module_names),
            "before": initial, "after": after, "unchanged": initial == after})
    return records


def contract_checks(cases: list[dict[str, Any]]) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.planning import finite_integer_codebase as matcher
    from ipfs_datasets_py.logic.software_contracts.codebase_integer_profile import (
        IntegerOffsetContract,
        UnsupportedIntegerProfile,
        compile_integer_offset,
    )
    checks = []
    for case in cases:
        prompt = case["requirements"]["original_prompt"]
        disposition = case["expected"]["route_disposition"]
        try:
            document = matcher.build_finite_integer_intent(prompt)
        except matcher.FiniteIntegerIntentError as exc:
            if disposition != "refusal_invalid_cnl":
                raise AssertionError(f"unexpected native parser refusal: {case['scenario_id']}") from exc
            checks.append({"scenario_id": case["scenario_id"], "parser": "refused",
                "original_clause_ids_retained": case["expected"]["preserved_clause_ids"],
                "compiler": "not_called", "fixture_code_executed": False})
            continue
        if disposition == "refusal_invalid_cnl":
            raise AssertionError(f"unsupported normative meaning parsed as finite: {case['scenario_id']}")
        query = matcher.prepare_finite_integer_query(intent_document=document, source_text=prompt)
        if not query["supported"] or query["requirement_ids"] != sorted([TYPE_CLAUSE, OFFSET_CLAUSE]):
            raise AssertionError("complete canonical finite requirements must be supported")
        if query["domain_inputs"] != case["requirements"]["domain_inputs"]:
            raise AssertionError("native query changed the reviewed finite input set")
        native_sources = {row.ref_id: row for row in document.sources}
        by_clause = {row["clause_id"]: row for row in case["requirements"]["clauses"]}
        for statement in document.statements:
            source = native_sources[statement.source_ref_ids[0]]
            clause = by_clause[statement.statement_id]
            if (source.span.start_char != clause["start_char"] or source.span.end_char != clause["end_char"]
                    or statement.normalized_text != clause["text"]):
                raise AssertionError("native requirement span differs from original authored ledger")
        contract = IntegerOffsetContract.from_dict(query["contract"])
        if contract.path != case["selected"]["path"]:
            raise AssertionError("same-name target path aliased another unit")
        raw = case["source_bytes"][contract.path]
        try:
            compiled = compile_integer_offset(raw, contract, revision="authored-contract-check:1")
        except UnsupportedIntegerProfile as exc:
            if disposition != "unsupported_source":
                raise AssertionError(f"unexpected compiler unsupported source: {case['scenario_id']}") from exc
            compilation = "unsupported_source"
            diagnostics = str(exc)
        else:
            if disposition != "supported_finite":
                raise AssertionError("closed integer compiler accepted unsupported source")
            if compiled.body_offset != case["training_truth"]["body_offset"]:
                raise AssertionError("compiler confused captured body with desired requirement")
            compilation, diagnostics = "source_correspondence_compiled", None
        checks.append({"scenario_id": case["scenario_id"], "parser": "supported_finite",
            "compiler": compilation, "diagnostic": diagnostics,
            "fixture_code_executed": False, "production_admitted": False})
    # A changed recorded intent cannot nominate a fact for another prompt's bytes.
    prompt = cases[0]["requirements"]["original_prompt"]
    document = matcher.build_finite_integer_intent(prompt).to_dict()
    changed_identity = copy.deepcopy(document["sources"])
    changed_identity[0]["source_revision"] = "foreign:revision"
    try:
        matcher.prepare_finite_integer_query(intent_document=document, source_text=prompt,
            source_identity=sorted(changed_identity, key=lambda row: row["ref_id"]))
    except matcher.FiniteIntegerIntentError:
        identity_refused = True
    else:
        raise AssertionError("foreign source identity accepted")
    document["statements"][0]["arguments"][-1] = "different_required_type"
    changed = matcher.prepare_finite_integer_query(intent_document=document, source_text=prompt)
    if changed["supported"] or changed["semantic_alignment_verified"]:
        raise AssertionError("changed meaning reused finite query semantics")
    inventory_checks = []
    for row in cases[0]["sources"]:
        symbol_name = row["symbols"][0]["symbol_name"]
        contract = IntegerOffsetContract(row["path"], symbol_name, "n", 1)
        try:
            compile_integer_offset(cases[0]["source_bytes"][row["path"]], contract,
                revision="authored-inventory-check:1")
        except UnsupportedIntegerProfile:
            if row["path"] not in {"consumer.py", "effectful.py"}:
                raise
            disposition = "unsupported_source"
        else:
            if row["path"] in {"consumer.py", "effectful.py"}:
                raise AssertionError("effectful or imported dependency unit falsely admitted to closed finite profile")
            disposition = "source_correspondence_compiled"
        inventory_checks.append({"path": row["path"], "source_sha256": row["sha256"],
            "compiler": disposition, "fixture_code_executed": False})
    return {"checks": checks, "inventory_checks": inventory_checks,
        "wrong_intent_identity_refused": identity_refused,
        "changed_native_clause_meaning_retained_as_unsupported": True,
        "fixture_code_executed": False, "production_admitted": False}


def _git(repository: Path, *arguments: str) -> str:
    environment = dict(os.environ, GIT_AUTHOR_DATE="2000-01-01T00:00:00Z",
                       GIT_COMMITTER_DATE="2000-01-01T00:00:00Z",
                       GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.check_output(["git", "-C", str(repository), *arguments],
        env=environment, text=True, stderr=subprocess.STDOUT, timeout=20).strip()


def owner_checks(output: Path, cases: list[dict[str, Any]], *, lean: Path) -> dict[str, Any]:
    import duckdb

    from ipfs_accelerate_py.agent_supervisor.planning import finite_integer_codebase as matcher
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseCatalog
    from ipfs_datasets_py.logic.software_contracts.cache import ImmutableCAS
    from ipfs_datasets_py.logic.software_contracts.codebase_finite_integer_observation import (
        FiniteIntegerObservationError,
        seal_finite_integer_tools,
        validate_finite_integer_observation,
    )
    from ipfs_datasets_py.logic.software_contracts.codebase_integer_profile import (
        IntegerOffsetContract,
    )
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import (
        RepositoryCodebaseIndex,
        StaleCodebaseError,
    )
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured
    from ipfs_datasets_py.logic.software_contracts.duckdb_ast_store import DuckDBASTStore
    from ipfs_datasets_py.logic.software_contracts.duckdb_ingest import DuckDBASTIngestor
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import (
        GlobalResourceScheduler,
        ResourceSchedulerConfig,
    )
    if not lean.is_file() or not shutil.which("git"):
        raise FileNotFoundError("--observe requires an installed Lean executable and git")
    repository = output / "repository"
    repository.mkdir(mode=0o700)
    baseline = cases[0]
    successor = next(case for case in cases if case["scenario_id"] == "successor")
    for path, raw in baseline["source_bytes"].items():
        (repository / path).write_bytes(raw)
    _git(repository, "init", "-q")
    _git(repository, "add", ".")
    _git(repository, "-c", "user.name=CodebaseIR Fixture", "-c", "user.email=fixture@example.invalid",
         "commit", "-qm", "authored multi-unit finite acceptance control")
    git_head = _git(repository, "rev-parse", "HEAD")
    policy = seal_finite_integer_tools(python_executable=Path(sys.executable).resolve(), lean_executable=lean.resolve())
    scheduler = GlobalResourceScheduler(ResourceSchedulerConfig.for_proof_host(
        state_path=output / "resource_leases.json", lane_reservations={},
        total_cpu_slots=2, total_child_process_slots=1, auto_renew_leases=False))
    repository_id = "repository:authored-multi-unit-acceptance"

    def open_index():
        connection = duckdb.connect(str(output / "codebase.duckdb"), config={"threads": 1, "memory_limit": "64MB"})
        store = DuckDBASTStore(connection=connection)
        artifacts = ImmutableCAS(output / "artifacts")
        return connection, RepositoryCodebaseIndex(ingestor=DuckDBASTIngestor(store=store),
            artifacts=artifacts, catalog=CodebaseCatalog(store, artifacts))

    connection, index = open_index()
    head = index.prepare_current(repository, repository_id=repository_id,
        operation_id="acceptance-baseline", expected_head=None, scheduler=scheduler).head

    def fresh_match(case, expected_head, name):
        prompt = case["requirements"]["original_prompt"]
        result = matcher.match_finite_integer_intent(index=index, repository=repository,
            repository_id=repository_id, expected_head=expected_head,
            intent_document=matcher.build_finite_integer_intent(prompt), source_text=prompt,
            tool_policy=policy, scheduler=scheduler, output=output / name,
            admission_timeout_seconds=15, timeout_seconds=60, memory_mb=1024)
        if result["match_cid"] != cid_for_structured({key: value for key, value in result.items() if key != "match_cid"}):
            raise AssertionError("native matcher returned inconsistent record identity")
        validate_native_result(result, case)
        (output / f"{name}.json").write_bytes(canonical_bytes(result) + b"\n")
        return result

    try:
        initial = fresh_match(baseline, head, "baseline_observation")
        manifest = index.load(head.manifest_cid)
        inventory = {entry.path: entry.source_cid for entry in manifest.snapshot.entries}
        if set(inventory) != set(baseline["source_bytes"]):
            raise AssertionError("captured source inventory dropped an unsupported unit")
        if inventory["calc.py"] == inventory["decoy.py"]:
            raise AssertionError("same-name decoy aliased the selected source bytes")
        if initial["source_cid"] != inventory["calc.py"]:
            raise AssertionError("fresh finite fact bound the same-name decoy")
        observation = initial["observation"]
        contract = IntegerOffsetContract.from_dict(observation["contract"])
        refused_corruptions = []
        for name in ("wrong_source_digest", "wrong_domain", "missing_trace_row", "altered_trace_output", "authority_escalation"):
            corrupted = copy.deepcopy(observation)
            if name == "wrong_source_digest":
                corrupted["source_sha256"] = "0" * 64
            elif name == "wrong_domain":
                corrupted["domain_inputs"] = [0, 1, 2]
            elif name == "missing_trace_row":
                corrupted["observations"] = corrupted["observations"][:-1]
            elif name == "altered_trace_output":
                corrupted["observations"][0]["output"] = 999
            else:
                corrupted["behavior_authority"] = True
            # Recompute the record's self-ID: valid content addressing alone
            # cannot repair a forged native relationship or artifact mismatch.
            corrupted["result_cid"] = cid_for_structured({key: value for key, value in corrupted.items() if key != "result_cid"})
            try:
                validate_finite_integer_observation(corrupted, expected_head=head,
                    contract=contract, inputs=baseline["requirements"]["domain_inputs"], tool_policy=policy)
            except FiniteIntegerObservationError:
                refused_corruptions.append(name)
            else:
                raise AssertionError(f"resealed corrupted observation accepted: {name}")
        (repository / "calc.py").write_bytes(source_function(2))
        if _git(repository, "rev-parse", "HEAD") != git_head:
            raise AssertionError("dirty source successor unexpectedly changed Git HEAD")
        try:
            fresh_match(baseline, head, "stale_observation")
        except StaleCodebaseError:
            stale_refused = True
        else:
            raise AssertionError("old source generation accepted a same-HEAD edit")
        next_head = index.prepare_current(repository, repository_id=repository_id,
            operation_id="acceptance-successor", expected_head=head, scheduler=scheduler).head
        second = fresh_match(successor, next_head, "successor_observation")
        if initial["current_root_id"] == second["current_root_id"] or initial["source_cid"] == second["source_cid"]:
            raise AssertionError("source-changing successor did not get fresh identities")
        # A newly constructed native owner hydrates current state; history stays
        # readable but cannot bypass fresh Python/Lean observation.
        connection.close()
        connection, index = open_index()
        if index.current(repository_id) != next_head:
            raise AssertionError("native owner did not hydrate the current head after reopen")
        history = index.load(head.manifest_cid)
        if history.snapshot.snapshot_cid != manifest.snapshot.snapshot_cid:
            raise AssertionError("historical parent source became unreplayable")
        restarted = fresh_match(successor, next_head, "restart_observation")
        for key in ("eligible_clause_ids", "residual_clause_ids", "finite_counterexamples"):
            if restarted[key] != second[key]:
                raise AssertionError("native reopen changed finite requirement dispositions")
        snapshot = scheduler.snapshot()
        if snapshot["active_lease_count"] or snapshot["waiting_request_count"]:
            raise AssertionError("finite validation leaked leases or waiting requests")
        return {"status": "passed", "git_head_before_and_after": git_head,
            "same_head_source_edit_refused": stale_refused, "inventory_paths": sorted(inventory),
            "initial_eligible_clause_ids": initial["eligible_clause_ids"],
            "initial_residual_clause_ids": initial["residual_clause_ids"],
            "successor_eligible_clause_ids": second["eligible_clause_ids"],
            "successor_residual_clause_ids": second["residual_clause_ids"],
            "native_reopen_with_fresh_observation": True,
            "resealed_corrupted_observations_refused": refused_corruptions,
            "fresh_native_observations": 3, "zero_active_leases_and_waiters": True,
            "tool_policy": policy,
            "private_state_paths": {"repository": str(repository),
                "duckdb": str(output / "codebase.duckdb"),
                "cas": str(output / "artifacts"), "scheduler": str(output / "resource_leases.json")},
            "fixture_code_executed": True, "worker_launched": False,
            "production_admitted": False, "signed_evidence_admitted": False,
            **{name: False for name in FALSE_AUTHORITY}}
    finally:
        connection.close()


def run(output: Path, *, observe: bool = False, lean: Path | None = None) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise ValueError("native check output must be a fresh private directory")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    cases = scenarios()
    report = {"schema": "codebase-ir-native-contract-checks@1", "production_qualified": False,
        "contract_checks": None, "owner_checks": {"status": "not_requested"}, "status": "incomplete",
        "started_at": datetime.now(UTC).isoformat(),
        "python_executable": str(Path(sys.executable).resolve()), "python_version": sys.version,
        "output": str(output)}
    roots, before = [], {}
    try:
        roots, before = native_source_snapshot()
        report["contract_checks"] = contract_checks(cases)
        if observe:
            if lean is None:
                raise ValueError("--observe requires --lean <installed executable>")
            report["owner_checks"] = owner_checks(output, cases, lean=lean)
        report["status"] = "passed"
    except ImportError as exc:
        report["status"] = "unavailable"
        report["error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        report["finished_at"] = datetime.now(UTC).isoformat()
        report["imported_native_sources"] = imported_native_sources(roots, before)
        report["imported_native_source_bytes_stable"] = bool(report["imported_native_sources"]) and all(
            row["unchanged"] for row in report["imported_native_sources"])
        if report["status"] == "passed" and not report["imported_native_source_bytes_stable"]:
            report["status"] = "source_changed_during_run"
        (output / "native_contract_checks.json").write_bytes(canonical_bytes(report) + b"\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="fresh private check output directory")
    parser.add_argument("--observe", action="store_true", help="run actual bounded Python/Lean observation on authored private source")
    parser.add_argument("--lean", type=Path, help="owner-selected installed Lean executable")
    args = parser.parse_args(argv)
    try:
        report = run(args.output, observe=args.observe, lean=args.lean)
    except (ValueError, OSError, AssertionError) as exc:
        parser.exit(2, f"native qualification failed; retained output: {exc}\n")
    print(json.dumps({"status": report["status"], "report": str(args.output.resolve() / "native_contract_checks.json"),
        "owner_checks": report["owner_checks"].get("status"), "production_qualified": False}, sort_keys=True))
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
