from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/swissknife_parser_failure_backlog.py"
MANIFEST = ROOT / "implementation_plan/conformance/swissknife-parser-failure-backlog-v1.json"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("swissknife_parser_failure_backlog", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def backlog() -> Any:
    return _load_module()


def _cluster_payload(family: str, path: str) -> dict[str, Any]:
    if family in {"UNIT", "BROWSER"}:
        required = "indexed_semantic_ast"
    elif path == "benchmark-results/sample-baseline.json":
        required = "indexed_structured_data"
    elif path.endswith("run_web_platform_integration_tests.js"):
        required = "reviewed_shell_nonsemantic"
    elif path.endswith("run_benchmarks.py"):
        required = "reviewed_symlink_nonsemantic"
    else:
        required = "indexed_semantic_ast"
    return {
        "clusters": [{"family": family, "task_id": "SCA-232"}],
        "rows": [
            {
                "actionable_family": family,
                "path": path,
                "task_id": "SCA-238",
                "row_id": "sca-row:old",
                "content_digest": "sha256:" + "1" * 64,
                "required_resolution": required,
            }
        ],
        "source_index": {"index_id": "sca-index:old"},
    }


def _fresh_row(
    path: str,
    *,
    status: str,
    kind: str,
    policy: str = "reviewed:fixture",
) -> dict[str, Any]:
    return {
        "path": path,
        "row_id": "sca-row:fresh",
        "content_digest": "sha256:" + "2" * 64,
        "parser_status": status,
        "disposition_kind": kind,
        "policy_rule": policy,
        "reason_code": "reviewed_fixture",
    }


def _write_fresh_index(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        json.dumps(
            {
                "index_id": "sca-index:fresh",
                "snapshot": {"snapshot_id": "sca-snapshot:fresh"},
                "rows": rows,
                "health": {
                    "metrics": {
                        "canaries_passed": True,
                        "canaries_present": True,
                        "funnel_failure_count": 0,
                        "git_root_discovery_ratio": 1.0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_materialized_backlog_covers_exact_failure_set(backlog: Any) -> None:
    payload = backlog._manifest_payload(MANIFEST)
    assert payload["counts"]["failure_rows"] == 258
    assert len(payload["clusters"]) == 6
    assert len(payload["rows"]) == 258
    assert len(payload["gates"]) == 16
    assert all("fresh_index_path" not in item for item in payload["clusters"])
    task_ids = [
        item["task_id"]
        for item in payload["clusters"]
        + payload["rows"]
        + payload["gates"]
        + [payload["aggregate"]]
    ]
    assert task_ids == [f"SCA-{value:03d}" for value in range(232, 513)]


@pytest.mark.parametrize(
    ("family", "path"),
    [
        ("ACTIVEJS", "test/mocks/stubs/chai-stub.js"),
        ("ACTIVEJS", "test/unit/cli/chat-command.test.js"),
        ("ACTIVEJS", "test/utils/mockMCPClient.js"),
        ("PYTHON", "test/fixed_web_platform/cross_browser_model_sharding.py"),
        ("PYTHON", "test/web_platform_test_output/test_hf_bert.py"),
        ("STRUCTURED", "benchmark-results/sample-baseline.json"),
    ],
)
def test_contract_sources_cannot_be_reclassified_nonsemantic(
    backlog: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    family: str,
    path: str,
) -> None:
    monkeypatch.setattr(backlog, "_manifest_payload", lambda _path: _cluster_payload(family, path))
    fresh = tmp_path / "repository-index.json"
    _write_fresh_index(
        fresh,
        [
            _fresh_row(
                path,
                status="not_applicable",
                kind="text_reference",
                policy="content_route:shebang_shell",
            )
        ],
    )
    with pytest.raises(backlog.BacklogError, match="requires indexed semantic AST"):
        backlog.verify_cluster(
            tmp_path / "manifest.json",
            family,
            fresh,
            tmp_path / "receipt.json",
        )


def test_indexed_is_the_real_semantic_success_status(
    backlog: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = "ipfs_accelerate_js/test/unit/example.test.ts"
    monkeypatch.setattr(backlog, "_manifest_payload", lambda _path: _cluster_payload("UNIT", path))
    fresh = tmp_path / "repository-index.json"
    _write_fresh_index(
        fresh,
        [_fresh_row(path, status="indexed", kind="semantic_ast")],
    )
    receipt = backlog.verify_cluster(
        tmp_path / "manifest.json",
        "UNIT",
        fresh,
        tmp_path / "receipt.json",
    )
    assert receipt["payload"]["resolutions"][0]["fresh_parser_status"] == "indexed"


def test_only_reviewed_shell_path_can_route_nonsemantic(
    backlog: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = "ipfs_accelerate_js/src/utils/run_web_platform_integration_tests.js"
    monkeypatch.setattr(
        backlog,
        "_manifest_payload",
        lambda _path: _cluster_payload("ACTIVEJS", path),
    )
    fresh = tmp_path / "repository-index.json"
    _write_fresh_index(
        fresh,
        [
            _fresh_row(
                path,
                status="not_applicable",
                kind="text_reference",
                policy="content_route:shebang_shell",
            )
        ],
    )
    receipt = backlog.verify_cluster(
        tmp_path / "manifest.json",
        "ACTIVEJS",
        fresh,
        tmp_path / "receipt.json",
    )
    assert receipt["payload"]["failure_count"] == 1


def test_reviewed_symlink_requires_exact_entry_kind_policy(
    backlog: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = "ipfs_accelerate_js/test/performance/webgpu_optimizer/run_benchmarks.py"
    monkeypatch.setattr(
        backlog,
        "_manifest_payload",
        lambda _path: _cluster_payload("PYTHON", path),
    )
    fresh = tmp_path / "repository-index.json"
    _write_fresh_index(
        fresh,
        [
            _fresh_row(
                path,
                status="not_applicable",
                kind="text_reference",
                policy="entry_kind:symlink",
            )
        ],
    )
    receipt = backlog.verify_cluster(
        tmp_path / "manifest.json",
        "PYTHON",
        fresh,
        tmp_path / "receipt.json",
    )
    assert receipt["payload"]["resolutions"][0]["required_resolution"] == (
        "reviewed_symlink_nonsemantic"
    )


def _aggregate_payload() -> dict[str, Any]:
    rows = [
        {
            "task_id": f"SCA-{238 + value:03d}",
            "row_id": f"sca-row:{value:03d}",
            "path": f"fixture/{value:03d}.ts",
            "required_resolution": "indexed_semantic_ast",
        }
        for value in range(258)
    ]
    gates = []
    for offset, nibble in enumerate("0123456789abcdef"):
        failure_count = sum(1 for value in range(258) if value % 16 == offset)
        gates.append(
            {
                "nibble": nibble,
                "task_id": f"SCA-{496 + offset:03d}",
                "failure_count": failure_count,
            }
        )
    return {
        "rows": rows,
        "gates": gates,
        "source_index": {"index_id": "sca-index:old"},
    }


def _write_gate_receipts(backlog: Any, payload: dict[str, Any], root: Path) -> None:
    root.mkdir()
    assignments = [[] for _ in range(16)]
    for offset, row in enumerate(payload["rows"]):
        assignments[offset % 16].append(
            {
                **row,
                "fresh_row_id": f"fresh:{offset:03d}",
                "fresh_parser_status": "indexed",
                "receipt_digest": "sha256:" + f"{offset:064x}",
            }
        )
    for gate, rows in zip(payload["gates"], assignments, strict=True):
        gate_payload = {
            "task_id": gate["task_id"],
            "nibble": gate["nibble"],
            "failure_count": len(rows),
            "rows": rows,
            "runtime_model_calls": 0,
        }
        backlog._write_json(
            root / f"{gate['nibble']}.json",
            backlog._envelope(gate_payload, schema=backlog.RECEIPT_SCHEMA),
        )


def test_aggregate_rejects_any_new_parser_failure(
    backlog: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = _aggregate_payload()
    monkeypatch.setattr(backlog, "_manifest_payload", lambda _path: payload)
    gate_dir = tmp_path / "gates"
    _write_gate_receipts(backlog, payload, gate_dir)
    fresh = tmp_path / "repository-index.json"
    fresh.write_text(
        json.dumps(
            {
                "index_id": "sca-index:fresh",
                "snapshot": {"snapshot_id": "sca-snapshot:fresh"},
                "rows": [
                    _fresh_row(
                        "new-contract.ts",
                        status="parse_failure",
                        kind="parse_failure",
                    )
                ],
                "health": {
                    "healthy": True,
                    "safe_for_completion_reasoning": True,
                    "status": "healthy",
                    "metrics": {"parser_failure_ratio": 0.0},
                    "thresholds": {
                        "max_parser_failures": 10,
                        "max_parser_failure_ratio": 0.01,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(backlog.BacklogError, match="contains a parser failure"):
        backlog.verify_all(
            tmp_path / "manifest.json",
            gate_dir,
            fresh,
            tmp_path / "receipt.json",
        )


def test_fresh_scan_invokes_real_indexer_with_zero_model_mode(
    backlog: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    indexer = repo / backlog.INDEXER_RELATIVE
    scope = repo / backlog.SCOPE_CONFIG_RELATIVE
    indexer.parent.mkdir(parents=True)
    scope.parent.mkdir(parents=True)
    indexer.write_text("# indexer\n", encoding="utf-8")
    scope.write_text("{}\n", encoding="utf-8")
    observed: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        observed["command"] = command
        observed["kwargs"] = kwargs
        output = Path(command[command.index("--output-root") + 1])
        _write_fresh_index(output / "repository-index.json", [])
        (output / "summary.json").write_text(
            json.dumps(
                {
                    "llm_call_count": 0,
                    "provider_call_count": 0,
                    "model_call_count": 0,
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    monkeypatch.setattr(backlog.subprocess, "run", fake_run)
    fresh, evidence = backlog._run_fresh_index_scan(
        repo_root=repo,
        output_root=tmp_path / "output",
        require_healthy=True,
    )
    assert fresh.is_file()
    assert "--require-healthy" in observed["command"]
    assert "--skip-extraction" in observed["command"]
    assert "--allow-dirty" in observed["command"]
    assert observed["kwargs"]["cwd"] == repo.resolve()
    assert evidence["mode"] == "aggregate_healthy"
    assert evidence["model_call_count"] == 0


def test_scan_all_copies_fresh_index_before_verification(
    backlog: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    generated = tmp_path / "generated-index.json"
    generated.write_text('{"rows":[]}\n', encoding="utf-8")
    evidence = {"model_call_count": 0}
    observed: dict[str, Any] = {}
    monkeypatch.setattr(
        backlog,
        "_run_fresh_index_scan",
        lambda **_kwargs: (generated, evidence),
    )

    def fake_verify_all(
        _manifest: Path,
        _gate_dir: Path,
        fresh: Path,
        _receipt: Path,
        *,
        scan_evidence: dict[str, Any],
    ) -> dict[str, Any]:
        observed["fresh"] = fresh.read_text(encoding="utf-8")
        observed["evidence"] = scan_evidence
        return {"ok": True}

    monkeypatch.setattr(backlog, "verify_all", fake_verify_all)
    destination = tmp_path / "retained" / "repository-index.json"
    result = backlog.scan_all(
        tmp_path / "manifest.json",
        tmp_path / "gates",
        destination,
        tmp_path / "receipt.json",
        repo_root=tmp_path,
    )
    assert result == {"ok": True}
    assert destination.read_bytes() == generated.read_bytes()
    assert observed == {
        "fresh": '{"rows":[]}\n',
        "evidence": evidence,
    }
