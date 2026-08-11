from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "proof_backed_test_reuse_supervisor.py"
VALIDATOR_SCRIPT = ROOT / "scripts" / "validate_proof_backed_test_reuse_board.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("proof_backed_test_reuse_supervisor", SCRIPT)
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


def _agent_route_readiness(
    *,
    grok_ready: bool = True,
    codex_ready: bool = True,
    failure_kind: str = "",
    reason_code: str = "grok_ready",
) -> SimpleNamespace:
    effective_provider = (
        "grok"
        if grok_ready
        else "codex"
        if codex_ready and failure_kind in {"authentication_failure", "launch_failure"}
        else ""
    )
    return SimpleNamespace(
        grok_ready=grok_ready,
        codex_ready=codex_ready,
        effective_provider=effective_provider,
        reason_code=reason_code,
        failure_kind=failure_kind or None,
        grok_model="grok-4.5",
        codex_model="gpt-5.6-terra",
        codex_reasoning_effort="high",
    )


def _mutate_task_block(text: str, task_id: str, mutation: Any) -> str:
    start = text.index(f"## {task_id} ")
    end = text.find("\n## PTR-", start + 1)
    if end < 0:
        end = len(text)
    original_block = text[start:end]
    mutated_block = mutation(original_block)
    assert mutated_block != original_block
    return text[:start] + mutated_block + text[end:]


def _write_mutated_task_board(
    tmp_path: Path,
    validator: Any,
    task_id: str,
    mutation: Any,
) -> Path:
    text = validator.TODO_PATH.read_text(encoding="utf-8")
    todo_path = tmp_path / "todo.md"
    todo_path.write_text(_mutate_task_block(text, task_id, mutation), encoding="utf-8")
    return todo_path


@pytest.fixture()
def supervisor(monkeypatch: pytest.MonkeyPatch) -> Any:
    module = _load_module()
    monkeypatch.setattr(
        module,
        "_grok_codex_agent_route_readiness",
        lambda: _agent_route_readiness(),
    )
    # CI runners report Codex ready via the router mock but lack a real binary;
    # merge-resolver command construction must still resolve a path.
    monkeypatch.setattr(
        module.shutil,
        "which",
        lambda name: {
            "grok": "/opt/grok/bin/grok",
            "codex": "/opt/codex/bin/codex",
        }.get(name),
    )
    return module


def _run_board_readiness(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: dict[str, object],
) -> dict[str, object]:
    state_root = tmp_path / "state"
    log_dir = tmp_path / "logs"
    task_state_path = state_root / "preflight" / "board" / "ptr_preflight_task_state.json"
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

    readiness = _run_board_readiness(supervisor, monkeypatch, tmp_path, payload)

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


def test_every_lane_uses_grok_primary_and_automatic_codex_fallback_policy(
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
    monkeypatch.setenv(
        "IPFS_PROOF_REUSE_STATE_ROOT",
        "/tmp/hostile-ambient-proof-reuse-state-root",
    )
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: {
            "grok": "/opt/grok/bin/grok",
            "codex": "/opt/codex/bin/codex",
        }.get(name),
    )
    monkeypatch.setattr(
        supervisor,
        "_grok_codex_agent_route_readiness",
        _agent_route_readiness,
    )

    assert len(supervisor.LANES) == 3
    for lane in supervisor.LANES:
        assert lane["provider"] == "grok-codex"
        assert lane["primary_provider"] == "grok"
        assert lane["primary_model"] == "grok-4.5"
        assert lane["fallback_provider"] == "codex"
        assert lane["fallback_model"] == "gpt-5.6-terra"
        assert lane["fallback_model_reasoning_effort"] == "high"
        assert lane["fallback_trigger"] == "grok_quota_auth_or_unavailable"
        environment = supervisor._runtime_environment(str(lane["provider"]))
        assert "IMPLEMENTATION_DAEMON_COMMAND" not in environment
        assert (
            environment[supervisor.MERGE_RESOLVER_COMMAND_ENV]
            == supervisor._managed_merge_resolver_command()
        )
        assert (
            "direct-codex-merge-resolver-bypass"
            not in environment[supervisor.MERGE_RESOLVER_COMMAND_ENV]
        )
        assert environment[str(supervisor.CONFIG["stateRootEnvironment"])] == str(
            supervisor.STATE_ROOT
        )
        assert environment["IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER"] == "grok-codex"
        assert environment["IPFS_ACCELERATE_AGENT_GROK_BIN"] == "/opt/grok/bin/grok"
        assert environment["IPFS_ACCELERATE_AGENT_GROK_MODEL"] == "grok-4.5"
        assert environment["IPFS_ACCELERATE_AGENT_CODEX_MODEL"] == "gpt-5.6-terra"
        assert environment["IPFS_ACCELERATE_AGENT_CODEX_REASONING_EFFORT"] == "high"
        assert (
            environment["IPFS_ACCELERATE_AGENT_PROVIDER_FALLBACK_POLICY"]
            == "grok_quota_auth_or_unavailable"
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


def test_semantic_merge_resolver_uses_managed_automatic_provider_chain(
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
    monkeypatch.setattr(
        supervisor,
        "_grok_codex_agent_route_readiness",
        _agent_route_readiness,
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
    assert option("--fallback-policy") == "grok_quota_auth_or_unavailable"
    assert "--probe-route-readiness" in command
    assert option("--probe-grok-bin") == "/opt/grok/bin/grok"
    assert option("--probe-codex-bin") == "/opt/codex/bin/codex"
    assert option("--probe-grok-model") == "grok-4.5"
    assert option("--probe-codex-model") == "gpt-5.6-terra"
    assert option("--probe-codex-reasoning-effort") == "high"
    assert "--route-stage" not in command
    assert "--route-task-id" not in command
    assert "--route-attempt" not in command
    assert "--route-receipt-path" not in command
    assert "--primary-unavailable-kind" not in command
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
        "--ephemeral",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        ".",
        "-m",
        "gpt-5.6-terra",
        "-c",
        'model_reasoning_effort="high"',
        "-",
    ]

    for lane in supervisor.LANES:
        arguments = supervisor._lane_common_arguments(lane, live=True)
        resolver_index = arguments.index("--llm-merge-resolver-command")
        assert arguments[resolver_index + 1] == encoded


@pytest.mark.parametrize("failure_kind", ("authentication_failure", "launch_failure"))
def test_semantic_merge_resolver_keeps_router_owned_route_when_grok_is_unready(
    failure_kind: str,
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: {
            "grok": "/opt/grok/bin/grok",
            "codex": "/opt/codex/bin/codex",
        }.get(name),
    )
    monkeypatch.setattr(
        supervisor,
        "_grok_codex_agent_route_readiness",
        lambda: _agent_route_readiness(
            grok_ready=False,
            failure_kind=failure_kind,
            reason_code=(
                "grok_authentication_failure"
                if failure_kind == "authentication_failure"
                else "grok_cli_unavailable"
            ),
        ),
    )

    encoded = supervisor._managed_merge_resolver_command()
    command = supervisor.shlex.split(encoded)

    def option(name: str) -> str:
        return command[command.index(name) + 1]

    assert command[:2] == [
        supervisor.sys.executable,
        str(supervisor.PROVIDER_FALLBACK_RUNNER),
    ]
    assert option("--primary-provider") == "grok"
    assert option("--fallback-provider") == "codex"
    assert option("--fallback-policy") == "grok_quota_auth_or_unavailable"
    assert "--probe-route-readiness" in command
    assert option("--probe-grok-bin") == "/opt/grok/bin/grok"
    assert option("--probe-codex-bin") == "/opt/codex/bin/codex"
    assert option("--probe-grok-model") == "grok-4.5"
    assert option("--probe-codex-model") == "gpt-5.6-terra"
    assert option("--probe-codex-reasoning-effort") == "high"
    assert "--primary-unavailable-kind" not in command
    assert "--route-stage" not in command
    assert "--route-task-id" not in command
    assert "--route-attempt" not in command
    assert "--route-receipt-path" not in command
    assert json.loads(option("--primary-command-json")) == [
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
    fallback = json.loads(option("--fallback-command-json"))
    assert fallback == [
        "/opt/codex/bin/codex",
        "exec",
        "--ephemeral",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        ".",
        "-m",
        "gpt-5.6-terra",
        "-c",
        'model_reasoning_effort="high"',
        "-",
    ]
    assert str(supervisor.GROK_CLI_RUNNER) in encoded


@pytest.mark.parametrize(
    "failure_kind",
    (
        "timeout",
        "transport_failure",
        "generic_nonzero_exit",
        "malformed_output",
        "task_failure",
    ),
)
def test_semantic_merge_resolver_rejects_terminal_grok_probe_failure(
    failure_kind: str,
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        supervisor,
        "_grok_codex_agent_route_readiness",
        lambda: _agent_route_readiness(
            grok_ready=False,
            failure_kind=failure_kind,
            reason_code=f"grok_probe_{failure_kind}",
        ),
    )

    with pytest.raises(RuntimeError, match="failed terminally"):
        supervisor._managed_merge_resolver_command()


def test_lane_launch_sets_private_umask_for_provider_logs(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_dir = tmp_path / "logs"
    runtime_dir = tmp_path / "runtime"
    log_dir.mkdir()
    runtime_dir.mkdir()
    observed: dict[str, object] = {}

    class FakeProcess:
        pid = 4242

    def fake_popen(command: list[str], **kwargs: object) -> FakeProcess:
        observed["command"] = command
        observed.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(supervisor, "LOG_DIR", log_dir)
    monkeypatch.setattr(supervisor, "RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(supervisor, "_read_pid", lambda _path: 0)
    monkeypatch.setattr(supervisor, "_lane_process_owned", lambda _name, _pid: False)
    monkeypatch.setattr(
        supervisor,
        "_lane_common_arguments",
        lambda _lane, *, live: ["--live"] if live else [],
    )
    monkeypatch.setattr(
        supervisor,
        "_runtime_environment",
        lambda _provider=None: {"TEST_PROVIDER": "codex"},
    )
    monkeypatch.setattr(supervisor.subprocess, "Popen", fake_popen)

    pid = supervisor._launch_lane(dict(supervisor.LANES[0]))

    log_path = log_dir / "ptr_lane_0_supervisor.log"
    assert pid == 4242
    assert log_path.stat().st_mode & 0o777 == 0o600
    assert observed["umask"] == 0o077
    assert observed["start_new_session"] is True
    assert observed["env"] == {"TEST_PROVIDER": "codex"}


def test_runtime_provider_metadata_preserves_identity_and_routes_grok_first(
    supervisor: Any,
) -> None:
    parallel = supervisor.PARALLEL
    assert parallel["canonicalTaskProviderRolesByShard"] == [
        "codex-implement",
        "grok-implement",
        "codex-implement",
    ]
    assert parallel["canonicalTaskProviderRolesByShardPurpose"] == ("historical_task_identity_only")
    assert parallel["runtimeExecutionProviderRolesByShard"] == [
        "grok-implement",
        "grok-implement",
        "grok-implement",
    ]
    assert parallel["semanticMergeResolver"] == {
        "provider": "grok-codex",
        "routingAuthority": "ipfs_accelerate_py.llm_router",
        "fallbackTrigger": "grok_quota_auth_or_unavailable",
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
    config["parallelRuntime"]["semanticMergeResolver"]["fallbackTrigger"] = "grok_quota_exhausted"
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


def test_board_validator_rejects_stale_v7_schedule_and_attestation_profile(
    tmp_path: Path,
) -> None:
    validator = _load_validator_module()
    config = json.loads(validator.CONFIG_PATH.read_text(encoding="utf-8"))
    profile = config["runnerAttestationProfile"]
    assert profile["signatureInput"] == ("domain-bytes||sha2-256(unsigned-envelope-bytes)")
    assert profile["trustPolicy"] == {
        "authority": "locally-pinned-trust-policy-cid",
        "cidVersion": 1,
        "multicodec": "dag-cbor",
        "multihash": "sha2-256",
        "multibase": "base32-lower",
        "trustOnFirstUse": False,
    }
    config["defaultStateRootSuffix"] = "ipfs_accelerate_py/proof-backed-test-reuse-v7"
    config["stateRootEnvironment"] = "UNSEALED_STATE_ROOT"
    projection = config["objectiveProjection"]
    projection["reviewRevision"] = "authenticated-receipt-current-tree-repair-v7"
    projection["initialClaimableTaskIds"] = [
        "PTR-161",
        "PTR-162",
    ]
    config["parallelRuntime"]["initialClaimableTaskIds"] = [
        "PTR-161",
        "PTR-162",
    ]
    config["preflight"]["requireInitialConflictFreeWidth"] = 2
    projection["sealedTaskCount"] = 76
    projection["proofMaterialAndContextWaveTaskIds"] = ["PTR-163", "PTR-164"]
    projection["exactV4PublicationJoinTaskId"] = "PTR-169"
    config["runnerAttestationProfile"]["trustPolicy"]["trustOnFirstUse"] = True
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
    assert "defaultStateRootSuffix" in errors
    assert "stateRootEnvironment" in errors
    assert "reviewRevision" in errors
    assert "stale pre-v9 fields" in errors
    assert "initial claimable task" in errors
    assert "requireInitialConflictFreeWidth" in errors
    assert "runnerAttestationProfile" in errors


def test_board_validator_seals_current_78_task_authenticated_receipt_dag() -> None:
    validator = _load_validator_module()

    result = validator.validate(
        validator.OBJECTIVE_PATH,
        validator.TODO_PATH,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )

    assert result["valid"] is True, result["errors"]
    assert result["task_count"] == 78
    assert result["completed_task_count"] == 78
    assert result["current_claimable_task_ids"] == []
    assert result["current_claimable_shards"] == []
    assert result["initial_ready_task_ids"] == ["PTR-170"]
    assert result["initial_ready_shards"] == [2]
    assert result["authenticated_receipt_correction_task_ids"] == [
        "PTR-160",
        "PTR-161",
        "PTR-162",
        "PTR-163",
        "PTR-164",
        "PTR-165",
        "PTR-166",
        "PTR-167",
        "PTR-168",
        "PTR-169",
        "PTR-170",
        "PTR-171",
    ]
    assert result["authenticated_receipt_wave_a_task_ids"] == [
        "PTR-160",
        "PTR-161",
        "PTR-162",
    ]
    assert result["authenticated_receipt_wave_a_submodules"] == {
        "PTR-160": ["external/ipfs_accelerate"],
        "PTR-161": ["external/ipfs_datasets"],
        "PTR-162": ["external/ipfs_kit"],
    }
    assert result["authenticated_receipt_wave_a_resource_width"] == 3
    assert result["authenticated_receipt_actionable_retry_task_id"] == "PTR-170"
    assert result["authenticated_receipt_actionable_retry_shard"] == 2
    assert result["authenticated_receipt_bootstrap_frontier_task_ids"] == [
        "PTR-161",
        "PTR-162",
    ]
    assert result["authenticated_receipt_wave_b_task_ids"] == [
        "PTR-163",
        "PTR-165",
    ]
    assert result["authenticated_receipt_wave_b_submodules"] == {
        "PTR-163": ["external/ipfs_datasets"],
        "PTR-165": ["<outer-superproject>"],
    }
    assert result["authenticated_receipt_wave_b_resource_width"] == 2
    assert result["authenticated_receipt_python_composition_task_id"] == "PTR-171"
    assert result["authenticated_receipt_python_composition_shard"] == 0
    assert result["authenticated_receipt_python_composition_submodules"] == [
        "external/ipfs_datasets"
    ]
    assert result["authenticated_receipt_runtime_join_task_id"] == "PTR-164"
    assert result["authenticated_receipt_runtime_join_shard"] == 2
    assert result["authenticated_receipt_runtime_join_submodules"] == ["external/ipfs_accelerate"]
    assert result["authenticated_receipt_authenticity_join_task_id"] == "PTR-166"
    assert result["authenticated_receipt_output_replay_join_task_id"] == "PTR-167"
    assert result["authenticated_receipt_zero_config_e2e_join_task_id"] == "PTR-168"
    assert result["authenticated_receipt_handoff_task_id"] == "PTR-169"
    assert result["historical_missing_output_count"] == 0
    assert result["historical_missing_artifact_count"] == 0
    assert result["historical_missing_validation_only_paths"] == []
    assert len(result["resolved_historical_artifact_paths"]) == 29
    assert result["historical_missing_artifact_quarantine"] == {}
    assert result["uncovered_historical_missing_artifact_paths"] == []
    assert result["multi_owned_historical_missing_artifact_paths"] == {}
    assert result["completed_owner_missing_historical_artifact_paths"] == {}
    assert result["uncovered_historical_missing_output_paths"] == []
    assert result["reviewed_production_correction_task_ids"] == [
        "PTR-150",
        "PTR-151",
        "PTR-152",
        "PTR-153",
        "PTR-154",
        "PTR-155",
    ]
    assert result["reviewed_production_correction_wave_one_submodules"] == {
        "PTR-150": ["external/ipfs_accelerate"],
        "PTR-151": ["external/ipfs_datasets"],
    }
    assert result["reviewed_production_correction_wave_one_resource_width"] == 2
    assert result["reviewed_production_correction_join_task_id"] == "PTR-152"
    assert result["reviewed_proof_material_context_wave_task_ids"] == [
        "PTR-153",
        "PTR-154",
    ]
    assert result["reviewed_proof_material_context_wave_shards"] == [0, 1]
    assert result["reviewed_exact_v4_publication_join_task_id"] == "PTR-155"
    assert result["reviewed_operator_handoff_task_id"] == "PTR-149"
    assert result["unordered_predicted_file_conflicts"] == []


def test_ptr_162_contract_seals_adversarial_bootstrap_and_store_repairs() -> None:
    validator = _load_validator_module()
    task = next(
        item
        for item in validator.parse_task_file(validator.TODO_PATH, "## PTR-")
        if item.task_id == "PTR-162"
    )

    assert task.canonical_task_cid == (
        "baguqeerak7y5laut7ihi2bfwaxxezko726zjtjofoe5c5zpvyre4lglx7i2q"
    )
    for requirement in (
        "complete accelerator plugin target is undiscoverable",
        "plugin found beneath PEP 420 namespace parents",
        "recursive, malformed or path-escaping blobs and candidate-index records",
        "protected against symlink substitution",
        "byte-, shape-, depth- and CID-bounded",
        "force the pure-Python JSON encoder",
        "without any `RecursionError`",
        "length-valid lone-surrogate CID",
        "non-accelerator transitive failure",
    ):
        assert requirement in task.acceptance
    assert len(task.validation) == 1
    for counterexample in (
        "/usr/bin/python3 -I",
        "chr(0xD800)",
        "deep-put",
        "missing requests",
        "transitive failure was suppressed",
    ):
        assert counterexample in task.validation[0]


def test_ptr_163_contract_seals_exact_byte_native_v5_relation() -> None:
    validator = _load_validator_module()
    task = next(
        item
        for item in validator.parse_task_file(validator.TODO_PATH, "## PTR-")
        if item.task_id == "PTR-163"
    )

    assert task.status == "completed"
    assert task.canonical_task_cid == (
        "baguqeerakxhhq45bn5sfpxumpzenosfkms3m273okr4i7hvosgkbq343etnq"
    )
    for requirement in (
        "fixed-capacity receipt and attestation byte arrays",
        "explicit bounded u32 lengths",
        "every byte after each length is constrained to zero",
        "in-circuit SHA-256 hashes exactly the selected bytes",
        "two bit/range-constrained u128 limbs",
        "never a caller-supplied 32-byte label",
        "rejects every non-canonical field encoding",
        "adding the scalar-field modulus",
        "one complete ordered public-input profile",
        "explicit ephemeral V5 setup/prove/verify",
        "proof for statement A does not verify with statement B",
        "Existing wire/schema/vector assertions are retained or strengthened",
        "truthful manifest rehash the actual V5-capable checked-in executable",
        "without any Rust test, build script, import hook or preparatory command editing",
        "actual V5-capable checked-in executable",
        "persist and bind the actual manifest",
        "never trigger setup, build, source/test mutation, download or network",
    ):
        assert requirement in task.acceptance
    envelope = json.loads(task.metadata["proposal artifact envelope"])
    assert envelope == {
        "allow_binary": True,
        "max_file_bytes": 5_000_000,
        "max_output_bytes": 16_000_000,
        "max_patch_bytes": 12_000_000,
        "paths": task.outputs,
        "schema": "ipfs_accelerate_py/agent-supervisor/task-artifact-envelope@2",
    }
    native_test = "external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_native_release.py"
    assert native_test in task.outputs
    assert native_test in task.validation[0]
    assert (
        "external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/circuit.rs"
    ) in task.outputs
    todo_text = validator.TODO_PATH.read_text(encoding="utf-8")
    assert "21282cb8779330724e496f88acdf3ed02cccbca1" in todo_text
    assert "a166f12cd5823416d31a2ebc0f5090ba245b73d5" in todo_text


def test_ptr_171_contract_seals_typed_ptr_160_v5_composition() -> None:
    validator = _load_validator_module()
    task = next(
        item
        for item in validator.parse_task_file(validator.TODO_PATH, "## PTR-")
        if item.task_id == "PTR-171"
    )

    assert task.status == "completed"
    assert task.depends_on == ["PTR-160", "PTR-161", "PTR-163"]
    assert task.canonical_task_cid == (
        "baguqeerah3rdjn5g772shubj6spygs5vcgiioue37haq6e6fouhbhlmnmxfa"
    )
    for requirement in (
        "`TestPassReceipt@1` re-encodes byte-for-byte as canonical DAG-JSON",
        "canonical DAG-CBOR and CIDv1/dag-cbor/sha2-256",
        "explicitly local-pinned policy",
        "complete ordered native public-input vector byte-for-byte",
        "Only the concrete immutable-manifest-pinned provider can yield VERIFIED",
        "forces V1-V4, hash-only and simulated openings",
        "one real typed PTR-160 composition",
        "A-to-B substitution",
        "injected True backend and downgrade",
        "never automatic setup, build, download or network",
    ):
        assert requirement in task.acceptance
    authority_test = "external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_v5_authority.py"
    assert authority_test in task.outputs
    assert authority_test in task.validation[0]
    assert not (
        set(task.outputs)
        & set(
            next(
                item
                for item in validator.parse_task_file(validator.TODO_PATH, "## PTR-")
                if item.task_id == "PTR-163"
            ).outputs
        )
    )


def test_ptr_165_contract_rejects_synthetic_or_misbound_evidence() -> None:
    validator = _load_validator_module()
    task = next(
        item
        for item in validator.parse_task_file(validator.TODO_PATH, "## PTR-")
        if item.task_id == "PTR-165"
    )

    assert task.status == "completed"
    assert task.canonical_task_cid == (
        "baguqeera6yv2kkmedurryjpozxdym72xt4to3r5vibrmxya74ffn525fkk4a"
    )
    for requirement in (
        "standalone `validate(objective, todo, config, plan)` board gate",
        "`valid=true`, `errors=[]` and `task_count=78`",
        "78 unique records in namespace `proof-backed-test-reuse-v1`",
        "match the canonical digests sealed by the current v9 root's fresh native-board and launch-preflight receipts",
        "exact `(task_id, canonical_task_key, canonical_task_cid)`",
        "never rederives a private task CID",
        "`IPFS_PROOF_REUSE_STATE_ROOT`",
        "`IPFS_PROOF_REUSE_STATE_ROOT` is the complete override",
        "implementation provider receives no state-root capability",
        "Landlock ABI-3-or-newer boundary",
        "only the exact candidate worktree and fresh private validation home writable",
        "current control state and every historical sibling remain read-only",
        "`proof_authoritative=false` and `completion_authority=false`",
        "mandatory reviewed sibling `proof-backed-test-reuse-v8`, `proof-backed-test-reuse-v6` and `proof-backed-test-reuse-v1` roots",
        "current v9 root's exact completed-queue, train, validation and event locations",
        "`project_managed_merge_queue_record`",
        "never as authentication",
        "`dedupe_key` equal to the train filename stem",
        "queue canonical CID/key and train canonical key",
        "Recovery-only records without request/dedupe/train binding",
        "non-authoritative provenance diagnostics",
        "manifest/hash-chain-verified JSONL reconciliation events",
        "never supervisor/preflight logs or a reader that repairs the evidence",
        "`implementation_branch_already_merged`",
        "`ipfs_accelerate_py.agent_supervisor.member_completion_receipt@1`",
        "`ipfs_accelerate_py/proof-backed-test-reuse-executed-validation-receipt@1`",
        "`projection/completion/validation_receipts/PTR-*.json`",
        "`validation_receipt_cid` from the body without the claim",
        "imports canonical `validation_command_identity`",
        '`{"command": command.strip()}`',
        "exact task ID/CID/goal ID",
        "clean/dirty-overlay binding",
        "Arbitrary JSON, reports",
        "failed/quarantined rows",
        "pass/exit-zero/zero-skip",
        "sealed historical-missing-artifact quarantine",
        "including native PTR-163 and Python-composition PTR-171",
        "excludes wall-clock time, absolute roots, report paths, mtimes and scan order",
        "`audit_valid` from `ready`",
        "superseded historical diagnostics are reported separately",
        "identity, schema, shape, digest, chain, root or scan failures set `audit_valid=false`",
        "77-, 76-, two- and one-task boards",
        "v1 PTR-011/PTR-041 successful-plus-failed reconciliation chain/manifest",
        "missing evidence fails rather than calling `pytest.skip`",
        "declared pytest run has zero skips",
    ):
        assert requirement in task.acceptance
    todo_text = validator.TODO_PATH.read_text(encoding="utf-8")
    assert "77aea5348cd6675e628454e9975e0937323961b2" in todo_text
    assert "zero of 71 completion/validation receipts" in todo_text
    assert "accepted just 3 of 70 completions and 0 of 70 validations" in todo_text
    assert "baguqeerar47kmz4pukq2hsfzjerdc3tkhm44aw7k62swqg6xzd4c3javw44q" in todo_text
    assert "dddece5cacf63dced8016c5b9a4bf01c0f4647cf" in todo_text
    assert "5635a7d201f862c1c7e58913c657e034fbf03a29" in todo_text


def test_board_validator_requires_full_ptr_163_native_surface(
    tmp_path: Path,
) -> None:
    validator = _load_validator_module()
    cargo_lock = "external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/Cargo.lock"

    def remove_cargo_lock(block: str) -> str:
        assert block.count(cargo_lock) == 3
        return block.replace(f", {cargo_lock}", "").replace(f'"{cargo_lock}",', "")

    todo_path = _write_mutated_task_board(tmp_path, validator, "PTR-163", remove_cargo_lock)
    result = validator.validate(
        validator.OBJECTIVE_PATH,
        todo_path,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )

    assert result["valid"] is False
    errors = "\n".join(result["errors"])
    assert "PTR-163 missing reviewed runtime repair paths" in errors
    assert cargo_lock in errors


def test_board_validator_requires_full_ptr_171_python_authority_surface(
    tmp_path: Path,
) -> None:
    validator = _load_validator_module()
    authority_test = "external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_v5_authority.py"

    def remove_authority_test(block: str) -> str:
        assert block.count(authority_test) == 3
        return block.replace(f", {authority_test}", "")

    todo_path = _write_mutated_task_board(tmp_path, validator, "PTR-171", remove_authority_test)
    result = validator.validate(
        validator.OBJECTIVE_PATH,
        todo_path,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )

    assert result["valid"] is False
    errors = "\n".join(result["errors"])
    assert "PTR-171 missing reviewed runtime repair paths" in errors
    assert authority_test in errors


def test_board_validator_requires_ptr_164_to_join_ptr_160_and_ptr_171(
    tmp_path: Path,
) -> None:
    validator = _load_validator_module()

    def remove_provider_dependency(block: str) -> str:
        expected = "- Depends on: PTR-160, PTR-171"
        assert expected in block
        return block.replace(expected, "- Depends on: PTR-160", 1)

    todo_path = _write_mutated_task_board(
        tmp_path, validator, "PTR-164", remove_provider_dependency
    )
    result = validator.validate(
        validator.OBJECTIVE_PATH,
        todo_path,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )

    assert result["valid"] is False
    errors = "\n".join(result["errors"])
    assert "PTR-164 missing required direct dependencies: ['PTR-171']" in errors
    assert "wave B must make only PTR-171 Python composition" in errors


def test_board_validator_requires_ptr_171_to_follow_native_ptr_163(
    tmp_path: Path,
) -> None:
    validator = _load_validator_module()

    def remove_native_dependency(block: str) -> str:
        expected = "- Depends on: PTR-160, PTR-161, PTR-163"
        assert expected in block
        return block.replace(expected, "- Depends on: PTR-160, PTR-161", 1)

    todo_path = _write_mutated_task_board(tmp_path, validator, "PTR-171", remove_native_dependency)
    result = validator.validate(
        validator.OBJECTIVE_PATH,
        todo_path,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )

    assert result["valid"] is False
    errors = "\n".join(result["errors"])
    assert "PTR-171 missing required direct dependencies: ['PTR-163']" in errors
    assert "wave B must be exactly" in errors


def test_board_validator_rejects_uncovered_resolved_sealed_path(
    tmp_path: Path,
) -> None:
    validator = _load_validator_module()
    shim_path = "external/ipfs_datasets/tests/unit/test_pytest_proof_reuse_shim.py"

    def remove_shim_ownership(block: str) -> str:
        assert block.count(shim_path) == 3
        mutated = block.replace(f", {shim_path}", "")
        assert mutated.count(shim_path) == 1
        return mutated

    todo_path = _write_mutated_task_board(tmp_path, validator, "PTR-161", remove_shim_ownership)
    result = validator.validate(
        validator.OBJECTIVE_PATH,
        todo_path,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )

    assert result["valid"] is False
    assert shim_path in result["resolved_historical_artifact_paths"]
    assert result["uncovered_historical_missing_artifact_paths"] == [shim_path]
    mismatch = result["exact_historical_artifact_owner_assignment_mismatches"][shim_path]
    assert mismatch == {
        "expected_owner_task_id": "PTR-161",
        "actual_owner_task_ids": [],
    }


def test_board_validator_rejects_multi_owned_resolved_sealed_path(
    tmp_path: Path,
) -> None:
    validator = _load_validator_module()
    shim_path = "external/ipfs_datasets/tests/unit/test_pytest_proof_reuse_shim.py"

    def add_second_owner(block: str) -> str:
        mutated = block.replace("\n- Validation:", f", {shim_path}\n- Validation:", 1)
        mutated = mutated.replace(
            "\n- Proposal artifact envelope:",
            f", {shim_path}\n- Proposal artifact envelope:",
            1,
        )
        return mutated

    todo_path = _write_mutated_task_board(tmp_path, validator, "PTR-163", add_second_owner)
    result = validator.validate(
        validator.OBJECTIVE_PATH,
        todo_path,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )

    assert result["valid"] is False
    assert result["multi_owned_historical_missing_artifact_paths"] == {
        shim_path: ["PTR-161", "PTR-163"]
    }
    mismatch = result["exact_historical_artifact_owner_assignment_mismatches"][shim_path]
    assert mismatch["expected_owner_task_id"] == "PTR-161"


def test_board_validator_rejects_moving_resolved_path_to_arbitrary_task(
    tmp_path: Path,
) -> None:
    validator = _load_validator_module()
    shim_path = "external/ipfs_datasets/tests/unit/test_pytest_proof_reuse_shim.py"

    def remove_named_owner(block: str) -> str:
        return block.replace(f", {shim_path}", "")

    def add_wrong_owner(block: str) -> str:
        mutated = block.replace("\n- Validation:", f", {shim_path}\n- Validation:", 1)
        return mutated.replace(
            "\n- Proposal artifact envelope:",
            f", {shim_path}\n- Proposal artifact envelope:",
            1,
        )

    text = validator.TODO_PATH.read_text(encoding="utf-8")
    text = _mutate_task_block(text, "PTR-161", remove_named_owner)
    text = _mutate_task_block(text, "PTR-163", add_wrong_owner)
    todo_path = tmp_path / "todo.md"
    todo_path.write_text(text, encoding="utf-8")
    result = validator.validate(
        validator.OBJECTIVE_PATH,
        todo_path,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )

    assert result["valid"] is False
    assert result["uncovered_historical_missing_artifact_paths"] == []
    assert result["multi_owned_historical_missing_artifact_paths"] == {}
    assert result["exact_historical_artifact_owner_assignment_mismatches"][shim_path] == {
        "expected_owner_task_id": "PTR-161",
        "actual_owner_task_ids": ["PTR-163"],
    }


def test_board_validator_fails_as_soon_as_gap_owner_completes(
    tmp_path: Path,
) -> None:
    """Completed owners must keep quarantined historical artifacts tree-reachable."""
    validator = _load_validator_module()
    missing_path = "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_assurance.py"
    artifact = validator.REPO_ROOT / missing_path
    assert artifact.is_file(), "G140 closeout requires PTR-171 outputs present"
    backup = artifact.read_bytes()
    artifact.unlink()
    try:
        result = validator.validate(
            validator.OBJECTIVE_PATH,
            validator.TODO_PATH,
            validator.CONFIG_PATH,
            validator.PLAN_PATH,
        )
    finally:
        artifact.write_bytes(backup)

    assert result["valid"] is False
    assert result["completed_owner_missing_historical_artifact_paths"][missing_path] == "PTR-171"
    assert any(
        "completed correction owners still have quarantined historical artifacts" in error
        for error in result["errors"]
    )


def test_board_validator_accepts_resolved_ledger_paths_as_progress() -> None:
    validator = _load_validator_module()
    resolved_path = "external/ipfs_datasets/tests/unit/test_pytest_proof_reuse_shim.py"

    result = validator.validate(
        validator.OBJECTIVE_PATH,
        validator.TODO_PATH,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )

    assert result["valid"] is True, result["errors"]
    assert resolved_path in result["resolved_historical_artifact_paths"]
    assert resolved_path not in result["historical_missing_artifact_paths"]
    assert resolved_path not in result["historical_missing_artifact_quarantine"]
    assert result["exact_historical_artifact_owner_assignment_mismatches"] == {}


def test_board_validator_accepts_repaired_audit_as_progressed_state(
    tmp_path: Path,
) -> None:
    """Sealed G140 board remains valid with all historical artifacts resolved."""
    validator = _load_validator_module()

    current = validator.validate(
        validator.OBJECTIVE_PATH,
        validator.TODO_PATH,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )
    assert current["valid"] is True, current["errors"]
    assert current["completed_task_count"] == 78
    assert current["current_claimable_task_ids"] == []
    assert current["completed_owner_missing_historical_artifact_paths"] == {}
    assert len(current["resolved_historical_artifact_paths"]) == 29
    assert current["historical_missing_artifact_count"] == 0

    # Reopen a leaf handoff owner (no completed dependents) so the board stays
    # valid and the owner re-enters the claimable frontier.
    def reopen(block: str) -> str:
        if "- Status: completed" in block:
            return block.replace("- Status: completed", "- Status: todo", 1)
        if "- Status: done" in block:
            return block.replace("- Status: done", "- Status: todo", 1)
        raise AssertionError(f"expected completed owner status in block:\n{block[:200]}")

    text = validator.TODO_PATH.read_text(encoding="utf-8")
    text = _mutate_task_block(text, "PTR-169", reopen)
    todo_path = tmp_path / "progressed-todo.md"
    todo_path.write_text(text, encoding="utf-8")

    result = validator.validate(
        validator.OBJECTIVE_PATH,
        todo_path,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )

    assert result["valid"] is True, result["errors"]
    assert result["completed_task_count"] == 77
    assert result["current_claimable_task_ids"] == ["PTR-169"]
    assert result["completed_owner_missing_historical_artifact_paths"] == {}
    assert len(result["resolved_historical_artifact_paths"]) == 29


def test_board_validator_orders_native_python_and_runtime_join(
    tmp_path: Path,
) -> None:
    """Wave-B ordering remains stable when reopened on the sealed G140 board."""
    validator = _load_validator_module()

    def reopen(block: str) -> str:
        if "- Status: completed" in block:
            return block.replace("- Status: completed", "- Status: todo", 1)
        if "- Status: done" in block:
            return block.replace("- Status: done", "- Status: todo", 1)
        raise AssertionError(f"expected completed status in block:\n{block[:200]}")

    def complete(block: str) -> str:
        if "- Status: todo" in block:
            return block.replace("- Status: todo", "- Status: completed", 1)
        raise AssertionError(f"expected todo status in block:\n{block[:200]}")

    # Reopen wave-B and Python composition so the frontier can be observed.
    text = validator.TODO_PATH.read_text(encoding="utf-8")
    for task_id in ("PTR-163", "PTR-165", "PTR-171", "PTR-164"):
        text = _mutate_task_block(text, task_id, reopen)
    todo_path = tmp_path / "wave-b-reopened.md"
    todo_path.write_text(text, encoding="utf-8")
    tasks = validator.parse_task_file(todo_path, "## PTR-")
    completed = {task.task_id for task in tasks if task.status == "completed"}
    claimable = sorted(
        task.task_id
        for task in tasks
        if task.status == "todo" and set(task.depends_on).issubset(completed)
    )
    assert claimable == ["PTR-163", "PTR-165"]

    text = _mutate_task_block(text, "PTR-163", complete)
    text = _mutate_task_block(text, "PTR-165", complete)
    todo_path.write_text(text, encoding="utf-8")
    tasks = validator.parse_task_file(todo_path, "## PTR-")
    completed = {task.task_id for task in tasks if task.status == "completed"}
    claimable = sorted(
        task.task_id
        for task in tasks
        if task.status == "todo" and set(task.depends_on).issubset(completed)
    )
    assert claimable == ["PTR-171"]

    text = _mutate_task_block(text, "PTR-171", complete)
    todo_path.write_text(text, encoding="utf-8")
    tasks = validator.parse_task_file(todo_path, "## PTR-")
    completed = {task.task_id for task in tasks if task.status == "completed"}
    claimable = sorted(
        task.task_id
        for task in tasks
        if task.status == "todo" and set(task.depends_on).issubset(completed)
    )
    assert claimable == ["PTR-164"]


def test_board_validator_rejects_an_unexpected_new_historical_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _load_validator_module()
    unexpected_path = (
        "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/"
        "proof/test_execution_contracts.py"
    )
    unexpected_absolute = validator.REPO_ROOT / unexpected_path
    real_exists = Path.exists

    def observed_exists(path: Path) -> bool:
        if path == unexpected_absolute:
            return False
        return real_exists(path)

    monkeypatch.setattr(Path, "exists", observed_exists)
    result = validator.validate(
        validator.OBJECTIVE_PATH,
        validator.TODO_PATH,
        validator.CONFIG_PATH,
        validator.PLAN_PATH,
    )

    assert result["valid"] is False
    assert result["unexpected_historical_missing_artifact_paths"] == [unexpected_path]
    assert any("baseline drift" in error for error in result["errors"])


def test_status_exposes_exact_model_and_automatic_fallback_policy(
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
            "model_reasoning_effort": "high",
        },
        "routing_authority": "ipfs_accelerate_py.llm_router",
        "fallback_trigger": "grok_quota_auth_or_unavailable",
        "primary_unavailable_action": "use_codex_fallback",
        "non_quota_failure_action": ("fallback_on_auth_or_launch_else_propagate"),
        "applies_to": ["implementation", "semantic_merge_resolver"],
        "semantic_merge_resolver": {
            "provider": "grok-codex",
            "routingAuthority": "ipfs_accelerate_py.llm_router",
            "fallbackTrigger": "grok_quota_auth_or_unavailable",
            "inheritedCommandPolicy": ("override_with_managed_provider_chain"),
        },
        "fallback_allowed_on": [
            "grok_quota_exhausted",
            "authentication_failure",
            "launch_failure",
        ],
        "fallback_requires": [
            "side_effects_started=false",
            "workspace_unchanged=true",
        ],
        "fallback_forbidden_on": [
            "timeout",
            "transport_failure",
            "generic_nonzero_exit",
            "malformed_output",
            "task_failure",
            "side_effects_started",
        ],
    }


def test_status_rejects_stopped_completion_snapshot_from_stale_board(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor,
        "_current_board_task_ids",
        lambda: tuple(f"PTR-{index:03d}" for index in range(66)),
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

    assert status["current_board_task_count"] == 66
    assert status["work_complete"] is False
    assert status["globally_progressable"] is False
    assert all(lane["current_board_matches"] is False for lane in status["lanes"])


def test_status_rejects_live_selectable_snapshot_from_stale_board(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor,
        "_current_board_task_ids",
        lambda: tuple(f"PTR-{index:03d}" for index in range(66)),
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
    current_ids = tuple(f"PTR-{index:03d}" for index in range(66))
    current_sha256 = supervisor._task_ids_sha256(current_ids)
    monkeypatch.setattr(supervisor, "_current_board_task_ids", lambda: current_ids)

    def lane_status(lane: dict[str, object]) -> dict[str, object]:
        stale = lane["name"] == "ptr_lane_1"
        return {
            "lane": lane["name"],
            "healthy": True,
            "unhealthy_reasons": [],
            "task_count": 53 if stale else 66,
            "completed_count": 53,
            "task_ids_sha256": None if stale else current_sha256,
            "active_task_id": None,
            "selectable_ready_count": 1 if not stale else 0,
            "blocked_task_ids": [],
        }

    monkeypatch.setattr(supervisor, "_lane_status", lane_status)

    status = supervisor._status_payload()

    stale_lane = next(lane for lane in status["lanes"] if lane["lane"] == "ptr_lane_1")
    assert status["healthy"] is False
    assert stale_lane["healthy"] is False
    assert "task_state_board_mismatch" in stale_lane["unhealthy_reasons"]


def test_provider_preflight_uses_codex_when_grok_is_unavailable(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: "/opt/codex/bin/codex" if name == "codex" else None,
    )
    monkeypatch.setattr(
        supervisor,
        "_grok_codex_agent_route_readiness",
        lambda: _agent_route_readiness(
            grok_ready=False,
            failure_kind="launch_failure",
            reason_code="grok_cli_unavailable",
        ),
    )

    providers = supervisor._provider_preflight()

    assert providers["grok"] == ""
    assert providers["codex_authenticated"] is True
    assert providers["grok_ready"] is False
    assert providers["grok_failure_kind"] == "launch_failure"
    assert providers["effective_provider"] == "codex"
    assert providers["fallback_active"] is True
    assert providers["fallback_reason"] == "launch_failure"
    assert providers["route_reason_code"] == "grok_cli_unavailable"
    assert "codex_status" not in providers
    assert "grok_version" not in providers


def test_provider_preflight_reports_grok_as_effective_primary(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: f"/opt/{name}/bin/{name}" if name in {"codex", "grok"} else None,
    )
    monkeypatch.setattr(
        supervisor,
        "_grok_codex_agent_route_readiness",
        _agent_route_readiness,
    )

    providers = supervisor._provider_preflight()

    assert providers["codex_authenticated"] is True
    assert providers["grok_authenticated"] is True
    assert providers["grok_ready"] is True
    assert providers["grok_failure_kind"] == ""
    assert providers["effective_provider"] == "grok"
    assert providers["fallback_active"] is False
    assert providers["fallback_reason"] == ""
    assert providers["route_reason_code"] == "grok_ready"
    assert "codex_status" not in providers
    assert "grok_version" not in providers
    assert providers["provider_policy"] == {
        "primary": {"provider": "grok", "model": "grok-4.5"},
        "fallback": {
            "provider": "codex",
            "model": "gpt-5.6-terra",
            "model_reasoning_effort": "high",
        },
        "routing_authority": "ipfs_accelerate_py.llm_router",
        "fallback_trigger": "grok_quota_auth_or_unavailable",
        "primary_unavailable_action": "use_codex_fallback",
        "non_quota_failure_action": ("fallback_on_auth_or_launch_else_propagate"),
        "applies_to": ["implementation", "semantic_merge_resolver"],
        "semantic_merge_resolver": {
            "provider": "grok-codex",
            "routingAuthority": "ipfs_accelerate_py.llm_router",
            "fallbackTrigger": "grok_quota_auth_or_unavailable",
            "inheritedCommandPolicy": ("override_with_managed_provider_chain"),
        },
        "fallback_allowed_on": [
            "grok_quota_exhausted",
            "authentication_failure",
            "launch_failure",
        ],
        "fallback_requires": [
            "side_effects_started=false",
            "workspace_unchanged=true",
        ],
        "fallback_forbidden_on": [
            "timeout",
            "transport_failure",
            "generic_nonzero_exit",
            "malformed_output",
            "task_failure",
            "side_effects_started",
        ],
    }


def test_provider_preflight_uses_codex_for_grok_auth_failure(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: f"/opt/{name}/bin/{name}" if name in {"codex", "grok"} else None,
    )
    monkeypatch.setattr(
        supervisor,
        "_grok_codex_agent_route_readiness",
        lambda: _agent_route_readiness(
            grok_ready=False,
            failure_kind="authentication_failure",
            reason_code="grok_authentication_failure",
        ),
    )

    providers = supervisor._provider_preflight()

    assert providers["grok_authenticated"] is False
    assert providers["grok_ready"] is False
    assert providers["grok_failure_kind"] == "authentication_failure"
    assert providers["effective_provider"] == "codex"
    assert providers["fallback_active"] is True
    assert providers["fallback_reason"] == "authentication_failure"
    assert providers["route_reason_code"] == "grok_authentication_failure"


@pytest.mark.parametrize(
    "failure_kind",
    (
        "timeout",
        "transport_failure",
        "generic_nonzero_exit",
        "malformed_output",
        "task_failure",
    ),
)
def test_provider_preflight_rejects_terminal_grok_probe_failure(
    failure_kind: str,
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: f"/opt/{name}/bin/{name}" if name in {"codex", "grok"} else None,
    )
    monkeypatch.setattr(
        supervisor,
        "_grok_codex_agent_route_readiness",
        lambda: _agent_route_readiness(
            grok_ready=False,
            failure_kind=failure_kind,
            reason_code=f"grok_probe_{failure_kind}",
        ),
    )

    with pytest.raises(RuntimeError, match="failed terminally"):
        supervisor._provider_preflight()


def test_provider_preflight_uses_inert_shadow_capability_discovery(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("IPFS_TEST_PROOF_REUSE_MODE", "readwrite")
    monkeypatch.setenv("IPFS_TEST_PROOF_REUSE_AUTO_INSTALL", "1")
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: f"/opt/{name}/bin/{name}" if name in {"codex", "grok"} else None,
    )
    monkeypatch.setattr(
        supervisor,
        "_grok_codex_agent_route_readiness",
        _agent_route_readiness,
    )
    if str(supervisor.ACCEL_ROOT) not in supervisor.sys.path:
        supervisor.sys.path.insert(0, str(supervisor.ACCEL_ROOT))
    from ipfs_accelerate_py.agent_supervisor.integrations import (
        test_reuse_capabilities,
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

    monkeypatch.setattr(test_reuse_capabilities, "TestReuseCapabilityProbe", FakeProbe)
    monkeypatch.setattr(services, "proof_reuse_dependency_plan", fake_plan)
    original_sys_path = list(supervisor.sys.path)

    providers = supervisor._provider_preflight()

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
    monkeypatch.setattr(
        supervisor,
        "_grok_codex_agent_route_readiness",
        lambda: _agent_route_readiness(codex_ready=False),
    )

    with pytest.raises(RuntimeError, match="authenticated Codex CLI fallback"):
        supervisor._provider_preflight()


def test_provider_preflight_rejects_codex_not_logged_in_status(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: f"/opt/{name}/bin/{name}" if name in {"codex", "grok"} else None,
    )
    if str(supervisor.ACCEL_ROOT) not in supervisor.sys.path:
        supervisor.sys.path.insert(0, str(supervisor.ACCEL_ROOT))
    from ipfs_accelerate_py import llm_router

    def fake_probe(
        command: list[str], *, timeout_seconds: float, **_kwargs: object
    ) -> tuple[int | None, str, object | None]:
        assert timeout_seconds > 0
        if command[-2:] == ["login", "status"]:
            return 0, "Not logged in\n", None
        assert command == ["/opt/grok/bin/grok", "models"]
        return 0, "Available models:\n  * grok-4.5\n", None

    monkeypatch.setattr(llm_router, "_bounded_agent_cli_probe", fake_probe)
    monkeypatch.setattr(
        supervisor,
        "_grok_codex_agent_route_readiness",
        lambda: llm_router.probe_grok_codex_agent_route_readiness(
            grok_bin="/opt/grok/bin/grok",
            codex_bin="/opt/codex/bin/codex",
            grok_model="grok-4.5",
            codex_model="gpt-5.6-terra",
            codex_reasoning_effort="high",
        ),
    )
    monkeypatch.setattr(
        supervisor,
        "_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("outer preflight must not parse raw provider status")
        ),
    )

    with pytest.raises(RuntimeError, match="authenticated Codex CLI fallback"):
        supervisor._provider_preflight()


def test_configured_submodule_initialization_is_scoped_and_non_updating(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
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
    assert projection["artifact_presence_is_completion_authority"] is False


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
    assert inventory["task_count"] == 78
    assert inventory["goal_count"] == 15
    assert inventory["acceptance_requirement_count"] == 50
    assert inventory["open_repair_task_ids"] == []
    assert inventory["repair_task_status_is_completion_authority"] is False
    assert inventory["managed_merge_history"]["usable_candidate_count"] == 0
    by_name = {item["name"]: item for item in inventory["requirements"]}
    approvals = by_name["genuine_reviewed_approvals_without_queue_records"]
    assert approvals["required_ids"] == [
        "PTR-000",
        "PTR-001",
        "PTR-011",
        "PTR-041",
    ]
    assert approvals["required_count"] == 4
    # Local tips may already retain historic approvals; CI runners start empty.
    assert set(approvals["missing_ids"]).issubset(set(approvals["required_ids"]))
    assert set(approvals["present_ids"]).issubset(set(approvals["required_ids"]))
    assert len(approvals["present_ids"]) + len(approvals["missing_ids"]) == 4
    validations = by_name["fresh_current_tree_proof_reuse_off_validation_receipts"]
    assert validations["required_count"] == 78
    assert validations["present_count"] == 0
    assert validations["presence_is_completion_authority"] is False
    materializer = inventory["authoritative_materializer"]
    assert materializer["configured"] is True
    assert materializer["materialization_is_completion_authority"] is False
    assert materializer["final_gate_task_id"] == "PTR-169"
    assert materializer["final_gate_goal_id"] == "PTR-G140"
    assert (
        "PTR-170 preserve bounded actionable validation retry evidence"
        in materializer["required_call_sequence"]
    )
    assert (
        "PTR-171 compose the exact PTR-160 receipt and runner attestation"
        in materializer["required_call_sequence"]
    )
    assert materializer["required_call_sequence"][-2:] == [
        "PTR-169 AuthenticatedProofReuseCurrentTreeGateV5.evaluate",
        "PTR-169 AuthenticatedProofReuseCurrentTreeGateV5.persist_bundle",
    ]
    activation = inventory["runtime_reuse_activation"]
    assert activation["schema"].endswith("authenticated-v9-runtime-projection@1")
    assert activation["authority"] == "non_authoritative_projection"
    assert activation["runtime_readiness"] == "unknown_live_probe_required"
    assert activation["static_inventory_is_completion_authority"] is False
    assert activation["static_inventory_may_authorize_skip"] is False
    assert activation["ordinary_test_fallback_action"] == "run_test"
    assert activation["live_probe"]["required"] is True
    assert activation["live_probe"]["performed_by_inventory"] is False
    assert activation["live_probe"]["must_follow_task_id"] == "PTR-169"
    assert activation["final_gate"] == {
        "task_id": "PTR-169",
        "goal_id": "PTR-G140",
        "acceptance_criterion": "ptr/authenticated-current-tree-gate-v5@1",
        "historical_ptr_122_or_v4_gate_is_authority": False,
    }
    assert activation["repair_task_ids"] == [f"PTR-{task_id}" for task_id in range(160, 172)]
    assert activation["open_repair_task_ids"] == []
    assert activation["repair_task_status_is_completion_authority"] is False
    assert [wave["task_ids"] for wave in activation["required_implementation_sequence"]] == [
        ["PTR-160"],
        ["PTR-170"],
        ["PTR-161", "PTR-162"],
        ["PTR-163", "PTR-165"],
        ["PTR-171"],
        ["PTR-164"],
        ["PTR-166"],
        ["PTR-167"],
        ["PTR-168"],
        ["PTR-169"],
    ]
    # Stale source-shape guesses must not be exposed as observed runtime facts.
    assert "default_identity_service_factory_configured" not in activation
    assert "receipt_content_identity_profiles" not in activation
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
    assert inventory["rejected_candidates"] == {"PTR-002": "canonical_task_cid_mismatch"}
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
            "closeout_input_inventory": {"inventory_is_completion_authority": False},
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

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[-1] == "--report-only"
        health_path = Path(command[command.index("--supervisor-health-input-path") + 1])
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
        lambda _lane: (_ for _ in ()).throw(AssertionError("diagnosis must not stop lanes")),
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
    assert result["input_inventory"] == {"inventory_is_completion_authority": False}
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
    monkeypatch.setattr(supervisor, "_lane_process_owned", lambda _lane, _pid: True)
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
            "closeout_input_inventory": {"inventory_is_completion_authority": False},
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
    monkeypatch.setattr(supervisor, "_lane_process_owned", lambda _lane, _pid: True)
    monkeypatch.setattr(supervisor, "_pid_alive", lambda _pid: True)

    lane = supervisor._lane_status(supervisor.LANES[0])

    assert lane["healthy"] is False
    assert reason in lane["unhealthy_reasons"]
