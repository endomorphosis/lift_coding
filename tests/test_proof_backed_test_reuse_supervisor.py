from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "proof_backed_test_reuse_supervisor.py"
VALIDATOR_SCRIPT = (
    ROOT / "scripts" / "validate_proof_backed_test_reuse_board.py"
)


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "proof_backed_test_reuse_supervisor", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_validator_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "validate_proof_backed_test_reuse_board", VALIDATOR_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def supervisor() -> Any:
    return _load_module()


def _run_board_readiness(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: dict[str, object],
) -> dict[str, object]:
    state_root = tmp_path / "state"
    log_dir = tmp_path / "logs"
    task_state_path = (
        state_root / "preflight" / "board" / "ptr_preflight_task_state.json"
    )
    task_state_path.parent.mkdir(parents=True)
    log_dir.mkdir()
    task_state_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(supervisor, "STATE_DIR", state_root)
    monkeypatch.setattr(supervisor, "LOG_DIR", log_dir)
    monkeypatch.setattr(
        supervisor,
        "_run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        ),
    )
    return supervisor._no_agent_readiness()


def test_completed_board_is_valid_quiescent_readiness(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {
        "task_count": 32,
        "completed_count": 32,
        "ready_count": 0,
        "selectable_ready_count": 0,
        "waiting_count": 0,
        "blocked_count": 0,
        "blocked_task_ids": [],
        "selection_idle_reason": "no_shard_selectable_ready_tasks",
    }

    readiness = _run_board_readiness(
        supervisor, monkeypatch, tmp_path, payload
    )

    assert readiness["work_complete"] is True
    assert readiness["selectable_ready_count"] == 0


def test_incomplete_board_without_selectable_work_is_rejected(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {
        "task_count": 32,
        "completed_count": 31,
        "selectable_ready_count": 0,
        "blocked_count": 0,
        "blocked_task_ids": [],
        "selection_idle_reason": "no_shard_selectable_ready_tasks",
    }

    with pytest.raises(RuntimeError, match="no selectable task"):
        _run_board_readiness(supervisor, monkeypatch, tmp_path, payload)


def test_completed_board_with_blocked_tasks_is_rejected(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {
        "task_count": 32,
        "completed_count": 32,
        "selectable_ready_count": 0,
        "blocked_count": 1,
        "blocked_task_ids": ["PTR-999"],
        "selection_idle_reason": "no_shard_selectable_ready_tasks",
    }

    with pytest.raises(RuntimeError, match="blocked tasks"):
        _run_board_readiness(supervisor, monkeypatch, tmp_path, payload)


def test_every_lane_uses_grok_primary_and_quota_only_codex_fallback_policy(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "IMPLEMENTATION_DAEMON_COMMAND",
        "python3 /tmp/provider-policy-bypass.py",
    )
    monkeypatch.setenv(
        "IPFS_ACCELERATE_AGENT_LLM_MERGE_RESOLVER_COMMAND",
        "python3 /tmp/direct-codex-merge-resolver-bypass.py",
    )
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: {
            "grok": "/opt/grok/bin/grok",
            "codex": "/opt/codex/bin/codex",
        }.get(name),
    )

    assert len(supervisor.LANES) == 3
    for lane in supervisor.LANES:
        assert lane["provider"] == "grok-codex"
        assert lane["primary_provider"] == "grok"
        assert lane["primary_model"] == "grok-4.5"
        assert lane["fallback_provider"] == "codex"
        assert lane["fallback_model"] == "gpt-5.6-terra"
        assert lane["fallback_model_reasoning_effort"] == "medium"
        assert lane["fallback_trigger"] == "grok_quota_exhausted"
        environment = supervisor._runtime_environment(str(lane["provider"]))
        assert "IMPLEMENTATION_DAEMON_COMMAND" not in environment
        assert environment[
            supervisor.MERGE_RESOLVER_COMMAND_ENV
        ] == supervisor._managed_merge_resolver_command()
        assert "direct-codex-merge-resolver-bypass" not in environment[
            supervisor.MERGE_RESOLVER_COMMAND_ENV
        ]
        assert (
            environment["IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER"]
            == "grok-codex"
        )
        assert (
            environment["IPFS_ACCELERATE_AGENT_GROK_BIN"]
            == "/opt/grok/bin/grok"
        )
        assert (
            environment["IPFS_ACCELERATE_AGENT_GROK_MODEL"]
            == "grok-4.5"
        )
        assert (
            environment["IPFS_ACCELERATE_AGENT_CODEX_MODEL"]
            == "gpt-5.6-terra"
        )
        assert (
            environment["IPFS_ACCELERATE_AGENT_CODEX_REASONING_EFFORT"]
            == "medium"
        )
        assert (
            environment["IPFS_ACCELERATE_AGENT_PROVIDER_FALLBACK_POLICY"]
            == "grok_quota_exhausted"
        )
        assert environment["IPFS_TEST_PROOF_REUSE_AUTO_INSTALL"] == "1"
        assert environment["IPFS_ACCEL_AUTO_INSTALL"] == "1"
        assert environment["IPFS_TEST_PROOF_REUSE_NLTK_DOWNLOAD"] == "1"
        assert environment["IPFS_TEST_PROOF_REUSE_GROTH16_BUILD"] == "1"
        assert environment["IPFS_TEST_PROOF_REUSE_NLTK_DATA_DIR"] == str(
            supervisor.STATE_ROOT / "dependencies" / "nltk-data"
        )
        assert environment["IPFS_TEST_PROOF_REUSE_PROVISION_DIR"] == str(
            supervisor.STATE_ROOT / "dependencies" / "provisioning"
        )


def test_semantic_merge_resolver_uses_managed_quota_only_provider_chain(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: {
            "grok": "/opt/grok/bin/grok",
            "codex": "/opt/codex/bin/codex",
        }.get(name),
    )

    encoded = supervisor._managed_merge_resolver_command()
    command = supervisor.shlex.split(encoded)

    def option(name: str) -> str:
        return command[command.index(name) + 1]

    assert command[:2] == [
        supervisor.sys.executable,
        str(supervisor.PROVIDER_FALLBACK_RUNNER),
    ]
    assert option("--workspace") == "."
    assert option("--primary-provider") == "grok"
    assert option("--fallback-provider") == "codex"
    assert option("--fallback-policy") == "grok_quota_exhausted"
    assert "llm_merge_resolver_fallback" not in encoded

    primary = json.loads(option("--primary-command-json"))
    fallback = json.loads(option("--fallback-command-json"))
    assert primary == [
        supervisor.sys.executable,
        str(supervisor.GROK_CLI_RUNNER),
        "--workspace",
        ".",
        "--grok-bin",
        "/opt/grok/bin/grok",
        "--model",
        "grok-4.5",
        "--max-turns",
        "100000",
        "--mode",
        "agent",
    ]
    assert fallback == [
        "/opt/codex/bin/codex",
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        ".",
        "-m",
        "gpt-5.6-terra",
        "-c",
        'model_reasoning_effort="medium"',
        "-",
    ]

    for lane in supervisor.LANES:
        arguments = supervisor._lane_common_arguments(lane, live=True)
        resolver_index = arguments.index("--llm-merge-resolver-command")
        assert arguments[resolver_index + 1] == encoded


def test_runtime_provider_metadata_preserves_identity_and_routes_grok_first(
    supervisor: Any,
) -> None:
    parallel = supervisor.PARALLEL
    assert parallel["canonicalTaskProviderRolesByShard"] == [
        "codex-implement",
        "grok-implement",
        "codex-implement",
    ]
    assert parallel["canonicalTaskProviderRolesByShardPurpose"] == (
        "historical_task_identity_only"
    )
    assert parallel["runtimeExecutionProviderRolesByShard"] == [
        "grok-implement",
        "grok-implement",
        "grok-implement",
    ]
    assert parallel["semanticMergeResolver"] == {
        "provider": "grok-codex",
        "fallbackTrigger": "grok_quota_exhausted",
        "inheritedCommandPolicy": "override_with_managed_provider_chain",
    }
    assert supervisor.PROVIDER_POLICY["appliesTo"] == [
        "implementation",
        "semantic_merge_resolver",
    ]


def test_board_validator_rejects_runtime_merge_provider_policy_drift(
    tmp_path: Path,
) -> None:
    validator = _load_validator_module()
    config = json.loads(validator.CONFIG_PATH.read_text(encoding="utf-8"))
    config["parallelRuntime"]["runtimeExecutionProviderRolesByShard"] = [
        "codex-implement",
        "grok-implement",
        "codex-implement",
    ]
    config["parallelRuntime"]["semanticMergeResolver"][
        "fallbackTrigger"
    ] = "any_failure"
    config["providerPolicy"]["appliesTo"] = ["implementation"]
    config_path = tmp_path / "supervisor.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = validator.validate(
        validator.OBJECTIVE_PATH,
        validator.TODO_PATH,
        config_path,
        validator.PLAN_PATH,
    )

    assert result["valid"] is False
    errors = "\n".join(result["errors"])
    assert "runtimeExecutionProviderRolesByShard" in errors
    assert "semanticMergeResolver" in errors
    assert "providerPolicy" in errors


def test_board_validator_seals_current_63_task_v4_correction_wave() -> None:
    validator = _load_validator_module()

    result = validator.validate(
        validator.OBJECTIVE_PATH,
        validator.TODO_PATH,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )

    assert result["valid"] is True, result["errors"]
    assert result["task_count"] == 63
    assert result["completed_task_count"] == 59
    assert result["current_claimable_task_ids"] == ["PTR-150", "PTR-151"]
    assert result["current_claimable_shards"] == [0, 1]
    assert result["reviewed_production_correction_task_ids"] == [
        "PTR-150",
        "PTR-151",
        "PTR-152",
    ]
    assert result[
        "reviewed_production_correction_wave_one_submodules"
    ] == {
        "PTR-150": ["external/ipfs_accelerate"],
        "PTR-151": ["external/ipfs_datasets"],
    }
    assert result[
        "reviewed_production_correction_wave_one_resource_width"
    ] == 2
    assert result["reviewed_production_correction_join_task_id"] == "PTR-152"
    assert result["reviewed_operator_handoff_task_id"] == "PTR-149"
    assert result["unordered_predicted_file_conflicts"] == []


def test_status_exposes_exact_model_and_quota_only_fallback_policy(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor,
        "_lane_status",
        lambda lane: {
            "lane": lane["name"],
            "healthy": True,
            "unhealthy_reasons": [],
            "task_count": 1,
            "completed_count": 1,
            "active_task_id": None,
            "selectable_ready_count": 0,
            "blocked_task_ids": [],
        },
    )

    status = supervisor._status_payload()

    assert status["provider_policy"] == {
        "primary": {"provider": "grok", "model": "grok-4.5"},
        "fallback": {
            "provider": "codex",
            "model": "gpt-5.6-terra",
            "model_reasoning_effort": "medium",
        },
        "fallback_trigger": "grok_quota_exhausted",
        "non_quota_failure_action": "propagate_without_fallback",
        "applies_to": ["implementation", "semantic_merge_resolver"],
        "semantic_merge_resolver": {
            "provider": "grok-codex",
            "fallbackTrigger": "grok_quota_exhausted",
            "inheritedCommandPolicy": (
                "override_with_managed_provider_chain"
            ),
        },
    }


def test_status_rejects_stopped_completion_snapshot_from_stale_board(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor,
        "_current_board_task_ids",
        lambda: tuple(f"PTR-{index:03d}" for index in range(63)),
    )
    monkeypatch.setattr(
        supervisor,
        "_lane_status",
        lambda lane: {
            "lane": lane["name"],
            "healthy": False,
            "unhealthy_reasons": ["supervisor_not_running"],
            "task_count": 53,
            "completed_count": 53,
            "task_ids_sha256": None,
            "active_task_id": None,
            "selectable_ready_count": 0,
            "blocked_task_ids": [],
        },
    )

    status = supervisor._status_payload()

    assert status["current_board_task_count"] == 63
    assert status["work_complete"] is False
    assert status["globally_progressable"] is False
    assert all(
        lane["current_board_matches"] is False for lane in status["lanes"]
    )


def test_status_rejects_live_selectable_snapshot_from_stale_board(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor,
        "_current_board_task_ids",
        lambda: tuple(f"PTR-{index:03d}" for index in range(63)),
    )
    monkeypatch.setattr(
        supervisor,
        "_lane_status",
        lambda lane: {
            "lane": lane["name"],
            "healthy": True,
            "unhealthy_reasons": [],
            "task_count": 53,
            "completed_count": 52,
            "task_ids_sha256": None,
            "active_task_id": None,
            "selectable_ready_count": 1,
            "blocked_task_ids": [],
        },
    )

    status = supervisor._status_payload()

    assert status["healthy"] is False
    assert status["work_complete"] is False
    assert status["globally_progressable"] is False


def test_status_rejects_mixed_current_and_stale_live_lanes(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    current_ids = tuple(f"PTR-{index:03d}" for index in range(63))
    current_sha256 = supervisor._task_ids_sha256(current_ids)
    monkeypatch.setattr(
        supervisor, "_current_board_task_ids", lambda: current_ids
    )

    def lane_status(lane: dict[str, object]) -> dict[str, object]:
        stale = lane["name"] == "ptr_lane_1"
        return {
            "lane": lane["name"],
            "healthy": True,
            "unhealthy_reasons": [],
            "task_count": 53 if stale else 63,
            "completed_count": 53,
            "task_ids_sha256": None if stale else current_sha256,
            "active_task_id": None,
            "selectable_ready_count": 1 if not stale else 0,
            "blocked_task_ids": [],
        }

    monkeypatch.setattr(supervisor, "_lane_status", lane_status)

    status = supervisor._status_payload()

    stale_lane = next(
        lane for lane in status["lanes"] if lane["lane"] == "ptr_lane_1"
    )
    assert status["healthy"] is False
    assert stale_lane["healthy"] is False
    assert "task_state_board_mismatch" in stale_lane["unhealthy_reasons"]


def test_provider_preflight_rejects_unavailable_grok_without_using_codex(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: "/opt/codex/bin/codex" if name == "codex" else None,
    )

    monkeypatch.setattr(
        supervisor,
        "_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Codex must not replace an unavailable Grok primary")
        ),
    )

    with pytest.raises(RuntimeError, match="Grok CLI is required.*primary"):
        supervisor._provider_preflight()


def test_provider_preflight_reports_grok_as_effective_primary(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: f"/opt/{name}/bin/{name}"
        if name in {"codex", "grok"}
        else None,
    )

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if command[-2:] == ["login", "status"]:
            stdout = "Logged in using ChatGPT\n"
        else:
            assert command == ["/opt/grok/bin/grok", "--version"]
            stdout = "grok 1.2.3\n"
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr(supervisor, "_run", fake_run)
    if str(supervisor.ACCEL_ROOT) not in supervisor.sys.path:
        supervisor.sys.path.insert(0, str(supervisor.ACCEL_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import (
        implementation_daemon,
    )

    monkeypatch.setattr(
        implementation_daemon,
        "_grok_cli_available",
        lambda: True,
    )

    providers = supervisor._provider_preflight()

    assert providers["grok_authenticated"] is True
    assert providers["provider_policy"] == {
        "primary": {"provider": "grok", "model": "grok-4.5"},
        "fallback": {
            "provider": "codex",
            "model": "gpt-5.6-terra",
            "model_reasoning_effort": "medium",
        },
        "fallback_trigger": "grok_quota_exhausted",
        "primary_unavailable_action": "fail_preflight",
        "non_quota_failure_action": "propagate_without_fallback",
        "applies_to": ["implementation", "semantic_merge_resolver"],
        "semantic_merge_resolver": {
            "provider": "grok-codex",
            "fallbackTrigger": "grok_quota_exhausted",
            "inheritedCommandPolicy": (
                "override_with_managed_provider_chain"
            ),
        },
        "fallback_forbidden_on": [
            "authentication_failure",
            "launch_failure",
            "timeout",
            "transport_failure",
            "generic_nonzero_exit",
            "malformed_output",
            "task_failure",
        ],
    }


def test_provider_preflight_rejects_grok_auth_failure_without_fallback(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: f"/opt/{name}/bin/{name}"
        if name in {"codex", "grok"}
        else None,
    )

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        stdout = (
            "Logged in using ChatGPT\n"
            if command[-2:] == ["login", "status"]
            else "grok 1.2.3\n"
        )
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(supervisor, "_run", fake_run)
    if str(supervisor.ACCEL_ROOT) not in supervisor.sys.path:
        supervisor.sys.path.insert(0, str(supervisor.ACCEL_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import (
        implementation_daemon,
    )

    monkeypatch.setattr(
        implementation_daemon,
        "_grok_cli_available",
        lambda: False,
    )

    with pytest.raises(
        RuntimeError,
        match="Codex fallback is not allowed for authentication failures",
    ):
        supervisor._provider_preflight()


def test_provider_preflight_uses_inert_shadow_capability_discovery(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("IPFS_TEST_PROOF_REUSE_MODE", "readwrite")
    monkeypatch.setenv("IPFS_TEST_PROOF_REUSE_AUTO_INSTALL", "1")
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: f"/opt/{name}/bin/{name}"
        if name in {"codex", "grok"}
        else None,
    )
    commands: list[list[str]] = []

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        stdout = (
            "Logged in using ChatGPT\n"
            if command[-2:] == ["login", "status"]
            else "grok 1.2.3\n"
        )
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr(supervisor, "_run", fake_run)
    if str(supervisor.ACCEL_ROOT) not in supervisor.sys.path:
        supervisor.sys.path.insert(0, str(supervisor.ACCEL_ROOT))
    from ipfs_accelerate_py.agent_supervisor.integrations import (
        test_reuse_capabilities,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import (
        implementation_daemon,
    )
    from ipfs_accelerate_py.testing.proof_reuse import services

    captured: dict[str, dict[str, str]] = {}

    class FakeReport:
        @staticmethod
        def to_dict() -> dict[str, object]:
            return {
                "schema_version": "TestReuseCapabilityReport@1",
                "mode": "shadow",
                "side_effect_free": True,
                "network_attempted": False,
                "daemon_started": False,
                "cache_created": False,
            }

    class FakeProbe:
        def __init__(self, *, environ: dict[str, str]) -> None:
            captured["probe"] = dict(environ)

        @staticmethod
        def probe() -> FakeReport:
            return FakeReport()

    def fake_plan(environ: dict[str, str]) -> dict[str, object]:
        captured["plan"] = dict(environ)
        return {
            "interface": "ProofReuseDependencyPlan@1",
            "lazy": True,
            "automatic_install_enabled": False,
        }

    monkeypatch.setattr(
        test_reuse_capabilities, "TestReuseCapabilityProbe", FakeProbe
    )
    monkeypatch.setattr(
        implementation_daemon,
        "_grok_cli_available",
        lambda: True,
    )
    monkeypatch.setattr(services, "proof_reuse_dependency_plan", fake_plan)
    original_sys_path = list(supervisor.sys.path)

    providers = supervisor._provider_preflight()

    assert commands == [
        ["/opt/codex/bin/codex", "login", "status"],
        ["/opt/grok/bin/grok", "--version"],
    ]
    assert captured["probe"] == captured["plan"]
    assert captured["probe"]["IPFS_TEST_PROOF_REUSE_MODE"] == "shadow"
    assert captured["probe"]["IPFS_TEST_PROOF_REUSE_AUTO_INSTALL"] == "0"
    assert captured["probe"]["IPFS_TEST_PROOF_REUSE_DATASETS_SOURCE"] == str(
        supervisor.DATASETS_ROOT
    )
    assert captured["probe"]["IPFS_DATASETS_AUTO_INSTALL"] == "false"
    assert captured["probe"]["IPFS_AUTO_INSTALL"] == "false"
    assert supervisor.os.environ["IPFS_TEST_PROOF_REUSE_MODE"] == "readwrite"
    assert supervisor.os.environ["IPFS_TEST_PROOF_REUSE_AUTO_INSTALL"] == "1"
    assert supervisor.sys.path == original_sys_path
    assert providers["test_reuse_discovery_policy"] == {
        "mode": "shadow",
        "environment_is_copy": True,
        "automatic_install_enabled": False,
        "installer_invoked": False,
        "process_started": False,
        "network_attempted": False,
        "cache_created": False,
        "completion_authority": False,
    }
    assert providers["test_reuse_capability_report"]["mode"] == "shadow"
    assert providers["proof_reuse_dependency_plan"] == {
        "interface": "ProofReuseDependencyPlan@1",
        "lazy": True,
        "automatic_install_enabled": False,
    }
    assert "optional_non_blocking_capabilities" in providers


def test_provider_preflight_requires_codex_fallback(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: "/opt/grok/bin/grok" if name == "grok" else None,
    )

    with pytest.raises(RuntimeError, match="fallback provider"):
        supervisor._provider_preflight()


def test_configured_submodule_initialization_is_scoped_and_non_updating(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, dict(kwargs)))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(supervisor.subprocess, "run", fake_run)

    initialized = supervisor._initialize_configured_submodules()

    assert initialized == (
        "external/ipfs_accelerate",
        "external/ipfs_datasets",
        "external/ipfs_kit",
    )
    assert calls[0][0] == [
        "git",
        "submodule",
        "init",
        "--",
        *initialized,
    ]
    assert "update" not in calls[0][0]
    assert calls[0][1]["cwd"] == supervisor.REPO_ROOT


def test_report_only_board_validation_does_not_persist_projection(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    projection_dir = tmp_path / "projection"
    projection_dir.mkdir()
    monkeypatch.setattr(supervisor, "PROJECTION_DIR", projection_dir)
    monkeypatch.setattr(
        supervisor,
        "_run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"valid": True, "task_count": 41}),
            stderr="",
        ),
    )

    result = supervisor._validate_board(persist_projection=False)

    assert result["valid"] is True
    assert not (projection_dir / "native_board_preflight.json").exists()


def test_closeout_artifact_presence_projects_missing_inputs_without_authority(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "goal_completion_gate.json"
    evidence_path = tmp_path / "goal_completion_evidence.json"
    paths = {
        "gatePathSuffix": gate_path,
        "evidencePathSuffix": evidence_path,
    }
    monkeypatch.setattr(
        supervisor,
        "_completion_state_path",
        lambda field: paths[field],
    )
    gate_path.write_text("{}\n", encoding="utf-8")

    projection = supervisor._required_closeout_artifact_presence()

    assert projection["artifact_presence_ready"] is False
    assert projection["missing_required_artifacts"] == ["evidence"]
    assert projection["required_artifacts"]["gate"]["present"] is True
    assert (
        projection["artifact_presence_is_completion_authority"]
        is False
    )


def test_closeout_input_inventory_enumerates_exact_unmaterialized_populations(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(supervisor, "MERGE_QUEUE_DIR", tmp_path / "merge-queue")
    monkeypatch.setattr(
        supervisor,
        "_completion_state_path",
        lambda field: tmp_path / "completion" / field,
    )

    inventory = supervisor._closeout_production_input_inventory()

    assert inventory["inventory_is_completion_authority"] is False
    assert inventory["task_count"] == 63
    assert inventory["goal_count"] == 12
    assert inventory["acceptance_requirement_count"] == 39
    assert inventory["managed_merge_history"]["usable_candidate_count"] == 0
    by_name = {item["name"]: item for item in inventory["requirements"]}
    approvals = by_name["genuine_reviewed_approvals_without_queue_records"]
    assert approvals["missing_ids"] == [
        "PTR-000",
        "PTR-001",
        "PTR-011",
        "PTR-041",
    ]
    validations = by_name[
        "fresh_current_tree_proof_reuse_off_validation_receipts"
    ]
    assert validations["required_count"] == 63
    assert validations["present_count"] == 0
    assert validations["presence_is_completion_authority"] is False
    assert inventory["authoritative_materializer"]["configured"] is False
    activation = inventory["runtime_reuse_activation"]
    assert activation["automatic_plugin_discovery"] is True
    assert activation["ordinary_enabled_run_effective_action"] == "run_test"
    assert activation["default_identity_service_factory_configured"] is False
    assert activation["two_stage_candidate_revalidation_configured"] is False
    assert activation["post_pass_receipt_requires_runtime_trace"] is False
    assert activation["deferred_request_transport_compatible"] is False
    assert activation["issuer_in_lazy_service_resolution"] is False
    assert activation["authoritative_candidate_publication_configured"] is False
    assert activation["receipt_content_identity_profiles"] == {
        "accelerator": "cidv1-base32-dag-json-sha2-256",
        "datasets_statement": "sha256-canonical-json-v1",
        "exact_conformance": False,
    }
    assert len(activation["activation_blocker_codes"]) == 9
    assert activation["implementation_gap_is_completion_authority"] is False
    assert activation["required_implementation_sequence"][-1]["goals"] == [
        "PTR-G110"
    ]
    assert not any(tmp_path.rglob("*"))


def test_managed_merge_inventory_checks_task_cid_and_current_ancestry(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    task_type = type("Task", (), {})
    first = task_type()
    first.task_id = "PTR-001"
    first.canonical_task_cid = "cid-001"
    second = task_type()
    second.task_id = "PTR-002"
    second.canonical_task_cid = "cid-002"
    completed = tmp_path / "completed"
    completed.mkdir()
    (completed / "one.json").write_text(
        json.dumps(
            {
                "task_id": "PTR-001",
                "canonical_task_id": "cid-001",
                "commit_sha": "commit-001",
                "status": "completed",
                "enqueued_at": 1,
            }
        ),
        encoding="utf-8",
    )
    (completed / "two.json").write_text(
        json.dumps(
            {
                "task_id": "PTR-002",
                "canonical_task_id": "wrong-cid",
                "commit_sha": "commit-002",
                "status": "completed",
                "enqueued_at": 2,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(supervisor, "MERGE_QUEUE_DIR", tmp_path)
    monkeypatch.setattr(
        supervisor,
        "_git_commit_is_ancestor",
        lambda commit: commit == "commit-001",
    )

    inventory = supervisor._managed_merge_input_inventory((first, second))

    assert inventory["usable_candidate_task_ids"] == ["PTR-001"]
    assert inventory["missing_candidate_task_ids"] == ["PTR-002"]
    assert inventory["rejected_candidates"] == {
        "PTR-002": "canonical_task_cid_mismatch"
    }
    assert inventory["presence_is_completion_authority"] is False


def test_inventory_does_not_count_unexpected_ids_as_required_inputs(
    supervisor: Any,
) -> None:
    item = supervisor._inventory_requirement(
        stage="PTR-111",
        name="analyzers",
        expected_ids=("required-analyzer",),
        observed_ids=("foreign-analyzer",),
    )

    assert item["present_count"] == 0
    assert item["missing_count"] == 1
    assert item["missing_ids"] == ["required-analyzer"]
    assert item["unexpected_ids"] == ["foreign-analyzer"]


def _configure_closeout_test(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    diagnosis_passed: bool,
) -> list[Path]:
    monkeypatch.setattr(
        supervisor,
        "_require_isolated_clean_checkout",
        lambda: {
            "branch": "agent/proof-backed-test-reuse",
            "commit": "commit-1",
            "tree": "tree-1",
            "submodules": {},
        },
    )
    monkeypatch.setattr(
        supervisor,
        "_validate_board",
        lambda **_kwargs: {"valid": True, "task_count": 41},
    )
    monkeypatch.setattr(
        supervisor,
        "_reviewed_completion_projection",
        lambda: {
            "implementation": {
                "task_count": 41,
                "completed_task_count": 41,
                "open_task_ids": [],
            },
            "closeout_input_inventory": {
                "inventory_is_completion_authority": False
            },
        },
    )
    monkeypatch.setattr(
        supervisor,
        "_status_payload",
        lambda: {
            "healthy": True,
            "work_complete": True,
            "lanes": [],
        },
    )
    monkeypatch.setattr(
        supervisor,
        "_completion_state_path",
        lambda field: tmp_path / field,
    )
    observed_health_paths: list[Path] = []

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert command[-1] == "--report-only"
        health_path = Path(
            command[command.index("--supervisor-health-input-path") + 1]
        )
        observed_health_paths.append(health_path)
        health = json.loads(health_path.read_text(encoding="utf-8"))
        assert health["status"]["healthy"] is True
        assert health["status"]["work_complete"] is True
        payload = {
            "mode": "report_only",
            "passed": diagnosis_passed,
            "reason_codes": [] if diagnosis_passed else ["missing_artifact"],
        }
        return subprocess.CompletedProcess(
            command,
            0 if diagnosis_passed else 1,
            json.dumps(payload),
            "",
        )

    monkeypatch.setattr(supervisor, "_run", fake_run)
    monkeypatch.setattr(
        supervisor,
        "_stop_lane",
        lambda _lane: (_ for _ in ()).throw(
            AssertionError("diagnosis must not stop lanes")
        ),
    )
    return observed_health_paths


def test_closeout_report_only_uses_ephemeral_health_and_keeps_lanes_running(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observed_health_paths = _configure_closeout_test(
        supervisor,
        monkeypatch,
        tmp_path,
        diagnosis_passed=True,
    )

    result = supervisor._closeout(report_only=True)

    assert result["diagnosis_passed"] is True
    assert result["lanes_stopped"] is False
    assert result["operator_commit_required"] is False
    assert result["input_inventory"] == {
        "inventory_is_completion_authority": False
    }
    assert len(observed_health_paths) == 1
    assert not observed_health_paths[0].exists()
    assert not any(tmp_path.iterdir())


def test_closeout_refuses_failed_diagnosis_before_stopping_lanes(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_closeout_test(
        supervisor,
        monkeypatch,
        tmp_path,
        diagnosis_passed=False,
    )

    result = supervisor._closeout()

    assert result["closeout_passed"] is False
    assert result["precloseout_diagnosis_passed"] is False
    assert result["lanes_stopped"] == []
    assert result["result"]["reason_codes"] == ["missing_artifact"]


def test_report_only_accepts_normal_agentic_maintenance_statuses(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    board_task_count = len(supervisor._current_board_task_ids())
    statuses = {
        "ptr_lane_0": "running",
        "ptr_lane_1": "agentic_maintenance_started",
        "ptr_lane_2": "agentic_maintenance_completed",
    }

    def fake_load(path: Path) -> dict[str, object]:
        for lane_name, status in statuses.items():
            if path.name == f"{lane_name}_supervisor_status.json":
                return {
                    "status": status,
                    "daemon_pid": 200,
                    "last_agentic_maintenance_error": "",
                    "control_plane_update_pending": False,
                }
            if path.name == f"{lane_name}_task_state.json":
                return {
                    "task_count": board_task_count,
                    "completed_count": board_task_count,
                    "blocked_count": 0,
                    "blocked_task_ids": [],
                    "selectable_ready_count": 0,
                }
        return {}

    monkeypatch.setattr(supervisor, "_load_json", fake_load)
    monkeypatch.setattr(supervisor, "_read_pid", lambda _path: 100)
    monkeypatch.setattr(
        supervisor, "_lane_process_owned", lambda _lane, _pid: True
    )
    monkeypatch.setattr(supervisor, "_pid_alive", lambda _pid: True)
    monkeypatch.setattr(
        supervisor,
        "_require_isolated_clean_checkout",
        lambda: {
            "branch": "agent/proof-backed-test-reuse",
            "commit": "commit-1",
            "tree": "tree-1",
            "submodules": {},
        },
    )
    monkeypatch.setattr(
        supervisor,
        "_validate_board",
        lambda **_kwargs: {"valid": True, "task_count": 41},
    )
    monkeypatch.setattr(
        supervisor,
        "_reviewed_completion_projection",
        lambda: {
            "implementation": {
                "task_count": 41,
                "completed_task_count": 41,
                "open_task_ids": [],
            },
            "closeout_input_inventory": {
                "inventory_is_completion_authority": False
            },
        },
    )
    monkeypatch.setattr(
        supervisor,
        "_completion_state_path",
        lambda field: tmp_path / field,
    )
    monkeypatch.setattr(
        supervisor,
        "_run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command,
            0,
            json.dumps({"passed": True, "reason_codes": []}),
            "",
        ),
    )

    status = supervisor._status_payload()
    result = supervisor._closeout(report_only=True)

    assert status["healthy"] is True
    assert status["work_complete"] is True
    assert result["diagnosis_passed"] is True
    assert result["lanes_stopped"] is False
    assert not any(tmp_path.iterdir())


@pytest.mark.parametrize(
    ("maintenance_error", "update_pending", "reason"),
    [
        ("reload failed", False, "agentic_maintenance_failed"),
        ("", True, "control_plane_update_pending"),
    ],
)
def test_maintenance_status_still_fails_closed_on_error_or_pending_update(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    maintenance_error: str,
    update_pending: bool,
    reason: str,
) -> None:
    def fake_load(path: Path) -> dict[str, object]:
        if path.name.endswith("_supervisor_status.json"):
            return {
                "status": "agentic_maintenance_completed",
                "daemon_pid": 200,
                "last_agentic_maintenance_error": maintenance_error,
                "control_plane_update_pending": update_pending,
            }
        return {
            "task_count": 41,
            "completed_count": 41,
            "blocked_count": 0,
            "blocked_task_ids": [],
        }

    monkeypatch.setattr(supervisor, "_load_json", fake_load)
    monkeypatch.setattr(supervisor, "_read_pid", lambda _path: 100)
    monkeypatch.setattr(
        supervisor, "_lane_process_owned", lambda _lane, _pid: True
    )
    monkeypatch.setattr(supervisor, "_pid_alive", lambda _pid: True)

    lane = supervisor._lane_status(supervisor.LANES[0])

    assert lane["healthy"] is False
    assert reason in lane["unhealthy_reasons"]
