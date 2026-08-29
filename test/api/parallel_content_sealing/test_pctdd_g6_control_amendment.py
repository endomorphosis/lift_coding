from __future__ import annotations

import hashlib
import importlib.util
import importlib.metadata
import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[3]
GENERATOR = ROOT / "scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py"
DISPATCHER = ROOT / "scripts/run_parallel_content_sealing_proof_carrying_tdd_validation.py"
MATERIALIZER = ROOT / "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py"
BOARD_VALIDATOR = ROOT / "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py"
FACADE = ROOT / "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_g6_amendment_has_exact_generation_and_component_safe_migration() -> None:
    generator = _load("pctdd_g6_generator", GENERATOR)
    config = generator.render_config()
    assert generator.PLAN_REVISION == "PCTDD-PLAN-V1.1"
    assert config["accepted_plan_revision_alias"] == "PCTDD-PLAN-V1.1"
    assert config["database_program"]["store_generation"] == "pctdd-v1-g6"
    assert config["database_program"]["predecessor_store_generation"] == "pctdd-v1-g5"
    assert config["database_program"]["predecessor_is_read_only_history"] is True
    assert config["database_program"]["quack_endpoint"] == "quack:127.0.0.1:42778"
    assert "_g6/" in config["database_program"]["store_id"]
    assert "_g6/ducklake/" in config["ducklake_projection_program"]["catalog_path"]
    assert config["initial_projection"]["completed_task_ids"] == []
    assert config["initial_projection"]["ready_task_ids"] == []
    assert config["initial_projection"]["post_operator_completed_task_ids"] == ["PCTDD-000"]
    assert config["initial_projection"]["post_operator_ready_task_ids"] == [
        "PCTDD-001", "PCTDD-002", "PCTDD-003", "PCTDD-004"
    ]
    assert config["provider"]["implementation_fallback_authorized"] is False
    assert config["provider"]["provider_id"] == "grok_cli"
    assert config["provider"]["model_id"] == "grok-4.6"
    assert config["provider"]["completion_authority"] == "controller_owned_sealed_validation_and_database_cas"
    assert not any(key.startswith("fallback_") for key in config["provider"])

    migration = generator.g5_migration_inventory()
    tracked = json.loads(
        (ROOT / "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g5_migration_inventory.json").read_text(encoding="utf-8")
    )
    assert tracked == migration
    predecessor = migration["predecessor"]
    assert predecessor["bootstrap_event_watermark"] == 103
    assert predecessor["preserved_failed_validation_rescue_branch_count"] == 29
    assert _sha256(ROOT / predecessor["frozen_database_path"]) == predecessor["frozen_database_sha256"]
    assert _sha256(ROOT / predecessor["bootstrap_receipt_path"]) == predecessor["bootstrap_receipt_sha256"]
    assert migration["migration_policy"]["copy_task_status_or_acceptance"] is False
    assert migration["migration_policy"]["rescue_candidates_are_authority"] is False

    candidates = migration["w1_rescue_candidates"]
    for task_id in ("PCTDD-001", "PCTDD-002", "PCTDD-003"):
        assert candidates[task_id]["classification"] == "receipt-observation-only"
        assert candidates[task_id]["component_commits"] == {}
        assert "never cherry-pick" in candidates[task_id]["application_policy"]
    pctdd_004 = candidates["PCTDD-004"]
    component = pctdd_004["component_commits"]["external/ipfs_accelerate"]
    assert pctdd_004["classification"] == "component-reuse-candidate-only"
    assert "never adopt the outer gitlink" in pctdd_004["application_policy"]
    assert component["commit"] == "48edb688ac31bc3d05fdd5c8efd7e50ab14b755e"
    assert component["prior_gitlink"] == "cfbd381ee6196e818ecd59a438386a60b5d71bd7"
    assert component["changed_paths"] == [
        "ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/critical_path.py",
        "test/api/parallel_content_sealing/test_cold_warm_critical_path.py",
    ]
    outer = subprocess.check_output(
        ["git", "ls-tree", pctdd_004["outer_commit"], "external/ipfs_accelerate"],
        cwd=ROOT,
        text=True,
    ).split()
    parent = subprocess.check_output(
        ["git", "ls-tree", pctdd_004["outer_commit"] + "^", "external/ipfs_accelerate"],
        cwd=ROOT,
        text=True,
    ).split()
    assert outer[2] == component["commit"]
    assert parent[2] == component["prior_gitlink"]


def test_all_tasks_have_strict_unique_profiles_and_exact_w1_splits() -> None:
    generator = _load("pctdd_profile_generator", GENERATOR)
    dispatcher = _load("pctdd_profile_dispatcher", DISPATCHER)
    payload = generator.validation_profiles()
    tracked_payload = json.loads(
        (ROOT / "config/parallel_content_sealing_proof_carrying_tdd_validation_profiles.json").read_text(encoding="utf-8")
    )
    assert tracked_payload == payload
    profiles = dispatcher.validate_profile_document(payload)
    assert tuple(sorted(profiles)) == tuple(f"PCTDD-{n:03d}" for n in range(54))
    assert len({profile["profile_id"] for profile in profiles.values()}) == 54
    assert len({profile["required_test_target"] for profile in profiles.values()}) == 54

    expected_policy = {
        "controller_owned_independent_validation": True,
        "machine_readable_pytest_phase_evidence": True,
        "disallowed_outcomes": ["failed", "skipped", "xfail", "xpass", "error", "rerun"],
        "worker_authored_test_is_sufficient_alone": False,
    }
    for task_id, profile in profiles.items():
        target = profile["required_test_target"]
        assert profile["required_acceptance"] == expected_policy
        assert profile["commands"][0]["argv"] == [
            "python", "-m", "pytest", "-q", target, "--tb=short"
        ]
        assert profile["commands"][0]["evidence_policy"] == "required_acceptance"
        assert len(profile["commands"]) >= 2

    pctdd_002 = profiles["PCTDD-002"]
    assert len(pctdd_002["commands"]) == 4
    assert [item["evidence_policy"] for item in pctdd_002["commands"][1:]] == [
        "protected_baseline_regression",
        "isolated_predecessor_regression",
        "explicit_green_predecessor_nodes",
    ]
    excluded = {item["node_id"] for item in pctdd_002["known_baseline_exclusions"]}
    assert excluded == dispatcher.PCTDD_002_EXCLUDED_NODE_IDS
    assert all(item["authoritative_acceptance"] is False for item in pctdd_002["known_baseline_exclusions"])
    for command in pctdd_002["commands"][1:]:
        for target in command["argv"][4:-1]:
            assert (ROOT / target.split("::", 1)[0]).is_file()


def test_board_uses_recognized_roles_budget_rollout_and_exact_outputs() -> None:
    generator = _load("pctdd_board_generator", GENERATOR)
    validator = _load("pctdd_board_validator", BOARD_VALIDATOR)
    board = generator.render_board()
    blocks = validator._parse_blocks(board, validator.TASK_RE)
    assert len(blocks) == 54
    fields_by_task = {task_id: fields for task_id, _title, fields in blocks}
    all_exact_outputs: list[str] = []
    for number, task_id in enumerate(generator.TASKS):
        fields = fields_by_task[task_id]
        expected_role = "operator-only" if number == 0 else "grok-only"
        assert fields["provider_role"] == expected_role
        assert fields["llm_context_budget_bytes"] == "24000"
        exact_outputs = validator._items(fields["outputs"])
        predicted_files = validator._items(fields["predicted_files"])
        owning_scope = validator._items(generator.scope_for(number, generator.owner_for(number)))
        assert "predicted_paths" not in fields
        assert exact_outputs == generator.outputs_for(number)
        assert predicted_files == generator.predicted_files_for(number)
        assert set(exact_outputs).issubset(predicted_files)
        assert set(owning_scope).issubset(predicted_files)
        if number:
            assert not any(
                validator._contains_path(path, protected)
                for path in predicted_files
                for protected in validator.PROTECTED_PATHS
            )
        all_exact_outputs.extend(exact_outputs)
        if number:
            acceptance = fields["acceptance_criteria"]
            assert "controller-owned validation authority independently executes" in acceptance
            assert "implementation model cannot fall back" in acceptance
            assert "worker-authored test alone is never sufficient" in acceptance
            assert "protected baseline regressions" in acceptance
    assert fields_by_task["PCTDD-004"]["owning_repository"] == "endomorphosis/ipfs_accelerate_py"
    assert len(all_exact_outputs) == len(set(all_exact_outputs))
    assert "critical_path.py" in fields_by_task["PCTDD-004"]["predicted_files"]
    datasets_scope = "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/pctdd"
    assert datasets_scope in validator._items(fields_by_task["PCTDD-005"]["predicted_files"])
    assert datasets_scope not in validator._items(fields_by_task["PCTDD-005"]["outputs"])
    assert fields_by_task["PCTDD-047"]["rollout_mode"] == "protected"
    assert "schema-aware required-mode completion gate" in fields_by_task["PCTDD-047"]["acceptance_criteria"]
    for number in range(48, 54):
        fields = fields_by_task[f"PCTDD-{number:03d}"]
        assert fields["rollout_mode"] == "required"
        assert "PCTDD-047 schema-aware gate" in fields["acceptance_criteria"]
        for evidence_name in validator.REQUIRED_REQUIRED_MODE_EVIDENCE:
            assert evidence_name in fields["required_evidence"]

    objectives = validator._parse_blocks(generator.render_objectives(), validator.GOAL_RE)
    for goal_id, _title, fields in objectives:
        expected: list[str] = []
        for task_id in validator.EXPECTED_TASK_IDS:
            current = validator.TASK_GOALS[task_id]
            while current is not None and current != goal_id:
                current = validator.GOAL_PARENTS[current]
            if current == goal_id:
                expected.append(task_id)
        assert validator._items(fields["producing_tasks"]) == tuple(expected)


def test_control_manifest_covers_every_preseal_protected_control() -> None:
    generator = _load("pctdd_manifest_generator", GENERATOR)
    manifest = generator.render_control_manifest()
    expected = set(generator.PROTECTED_ARTIFACTS) - {
        generator.CONTROL_MANIFEST.relative_to(ROOT).as_posix(),
        generator.SEAL.relative_to(ROOT).as_posix(),
    }
    assert set(manifest["protected_control_hashes_before_manifest_and_seal"]) == expected
    assert "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json" in expected
    assert manifest["dependency_seal_must_hash_this_manifest"] is True
    assert manifest["manifest_is_completion_receipt"] is False


def test_theorem_prover_inventory_distinguishes_installation_from_sealed_admission() -> None:
    generator = _load("pctdd_theorem_generator", GENERATOR)
    capabilities = generator.theorem_prover_capabilities()
    assert set(capabilities) == {"lean", "cvc5", "coq"}
    for record in capabilities.values():
        assert record["provisioning"] == "ipfs_datasets_py managed theorem-prover installer"
        assert record["required"] is False
        assert isinstance(record["installer_discovered"], bool)
        if not record["available"] and record["installer_discovered"]:
            assert record["classification"] == "installed_unqualified_user_mutable"


def test_dependency_seal_capabilities_are_captured_from_current_runtime() -> None:
    generator = _load("pctdd_runtime_generator", GENERATOR)
    seal = generator.render_seal()
    environment = seal["environment"]
    assert environment["pytest_version"] == importlib.metadata.version("pytest")
    assert environment["pytest_xdist_version"] == importlib.metadata.version("pytest-xdist")
    assert environment["duckdb_version"] == importlib.metadata.version("duckdb")
    for name in ("quack", "ducklake"):
        expected = generator.duckdb_extension_capability(
            name, required_for_launch=name == "quack"
        )
        assert environment["capabilities"][name] == expected
        assert Path(expected["extension_directory"]).is_dir()
        extension = Path(expected["install_path"])
        assert extension.is_file()
        assert expected["install_sha256"] == "sha256:" + hashlib.sha256(
            extension.read_bytes()
        ).hexdigest()


def test_sealed_duckdb_extension_binding_survives_neutral_home() -> None:
    generator = _load("pctdd_extension_generator", GENERATOR)
    validator = _load(
        "pctdd_extension_dependency_validator",
        ROOT / "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    )
    errors: list[str] = []
    for name in ("quack", "ducklake"):
        record = generator.duckdb_extension_capability(
            name, required_for_launch=name == "quack"
        )
        directory = validator._sealed_extension_directory(name, record, errors)
        state = validator._extension_state(name, extension_directory=directory)
        assert state["available"] is True
        assert state["loaded"] is True
        assert state["install_path"] == record["install_path"]
        assert state["install_sha256"] == record["install_sha256"]
    assert errors == []


def test_dependency_seal_never_serializes_origin_credentials() -> None:
    generator = _load("pctdd_origin_generator", GENERATOR)
    assert generator.public_origin("https://example.invalid/owner/repository.git") == (
        "https://example.invalid/owner/repository.git"
    )
    assert generator.public_origin("git@example.invalid:owner/repository.git") == (
        "git@example.invalid:owner/repository.git"
    )
    assert generator.public_origin("ssh://git@example.invalid/owner/repository.git") == (
        "ssh://git@example.invalid/owner/repository.git"
    )
    with pytest.raises(ValueError, match="credentials"):
        generator.public_origin("https://token@example.invalid/owner/repository.git")
    with pytest.raises(ValueError, match="credentials"):
        generator.public_origin("https://user:secret@example.invalid/owner/repository.git")
    with pytest.raises(ValueError, match="single-line"):
        generator.public_origin("https://example.invalid/repository.git\nsecret")


def test_dispatcher_rejects_prose_shell_options_and_profile_gaps() -> None:
    generator = _load("pctdd_negative_generator", GENERATOR)
    dispatcher = _load("pctdd_negative_dispatcher", DISPATCHER)
    payload = generator.validation_profiles()

    missing = json.loads(json.dumps(payload))
    missing["profiles"].pop("PCTDD-053")
    with pytest.raises(dispatcher.ProfileError, match="cover exactly"):
        dispatcher.validate_profile_document(missing)

    prose = json.loads(json.dumps(payload))
    prose["profiles"]["PCTDD-001"]["commands"][0]["argv"] = ["python", "-c", "pass"]
    with pytest.raises(dispatcher.ProfileError, match="exact isolated required-acceptance"):
        dispatcher.validate_profile_document(prose)

    option = json.loads(json.dumps(payload))
    option["profiles"]["PCTDD-001"]["commands"][1]["argv"].insert(-1, "--maxfail=1")
    with pytest.raises(dispatcher.ProfileError, match="unsealed pytest option"):
        dispatcher.validate_profile_document(option)

    shell = json.loads(json.dumps(payload))
    shell["profiles"]["PCTDD-001"]["commands"][0]["argv"].extend(["&&", "echo", "pass"])
    with pytest.raises(dispatcher.ProfileError, match="forbidden shell syntax"):
        dispatcher.validate_profile_document(shell)


def test_required_phase_evidence_is_complete_all_pass_or_rejected(tmp_path: Path) -> None:
    dispatcher = _load("pctdd_phase_dispatcher", DISPATCHER)
    target = "test/api/parallel_content_sealing/test_example.py"
    evidence = {
        "schema": "pctdd/pytest-phase-outcome@1",
        "required_test_target": target,
        "exitstatus": 0,
        "test_count": 2,
        "phase_count": 6,
        "fully_passed_test_count": 2,
        "counts": {
            "passed": 6,
            "failed": 0,
            "skipped": 0,
            "xfail": 0,
            "xpass": 0,
            "error": 0,
            "rerun": 0,
        },
        "node_ids": [target + "::test_a", target + "::test_b"],
    }
    path = tmp_path / "phase.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    accepted = dispatcher._load_required_phase_evidence(path, target=target)
    assert accepted["test_count"] == 2
    assert accepted["phase_count"] == 6

    skipped = json.loads(json.dumps(evidence))
    skipped["counts"]["passed"] = 5
    skipped["counts"]["skipped"] = 1
    path.write_text(json.dumps(skipped), encoding="utf-8")
    with pytest.raises(dispatcher.ProfileError, match="skipped"):
        dispatcher._load_required_phase_evidence(path, target=target)

    duplicate_phase = json.loads(json.dumps(evidence))
    duplicate_phase["phase_count"] = 7
    duplicate_phase["counts"]["passed"] = 7
    path.write_text(json.dumps(duplicate_phase), encoding="utf-8")
    with pytest.raises(dispatcher.ProfileError, match="incomplete_phases"):
        dispatcher._load_required_phase_evidence(path, target=target)


def test_materializer_requires_exact_role_budget_outputs_and_independent_controller_validation() -> None:
    generator = _load("pctdd_binding_generator", GENERATOR)
    materializer = _load("pctdd_binding_materializer", MATERIALIZER)
    profiles = generator.validation_profiles()["profiles"]
    task_id = "PCTDD-001"
    fields = {
        "validation": generator.validation_command_for(1),
        "validation_profile": profiles[task_id]["profile_id"],
        "provider_role": "grok-only",
        "llm_context_budget_bytes": "24000",
        "acceptance_criteria": (
            "the controller-owned validation authority independently executes the profile; "
            "the implementation model cannot fall back to the completion authority; "
            "the worker-authored test alone is never sufficient; verify protected baseline regressions"
        ),
    }
    assert materializer._task_validation_binding(
        task_id,
        fields,
        generator.outputs_for(1),
        profiles,
    ) == (fields["validation"], fields["validation_profile"])

    drifted = dict(fields, provider_role="implementation_worker_then_independent_validator")
    with pytest.raises(materializer.MaterializationError, match="provider role"):
        materializer._task_validation_binding(task_id, drifted, generator.outputs_for(1), profiles)
    drifted = dict(fields, llm_context_budget_bytes="")
    with pytest.raises(materializer.MaterializationError, match="llm_context_budget_bytes"):
        materializer._task_validation_binding(task_id, drifted, generator.outputs_for(1), profiles)
    with pytest.raises(materializer.MaterializationError, match="exact output manifest"):
        materializer._task_validation_binding(task_id, fields, generator.outputs_for(1)[:-1], profiles)


def test_materializer_operator_stage_has_no_ready_workers_before_seal() -> None:
    materializer = _load("pctdd_stage_materializer", MATERIALIZER)
    population = {
        "tasks": [object()] * 54,
        "objectives": [object()] * 24,
        "task_dependency_count": 121,
    }

    class FakeSource:
        def __init__(self, completed: bool):
            self.completed = completed

        def snapshot(self):
            return SimpleNamespace(to_dict=lambda: {
                "task_count": 54,
                "goal_count": 24,
                "dependency_count": 121,
                "projection_cid": "projection",
            })

        def list_tasks(self, *, limit: int):
            return SimpleNamespace(tasks=[SimpleNamespace(task_alias=item) for item in materializer.TASK_IDS])

        def get_task(self, task_id: str):
            assert task_id == "PCTDD-000"
            return SimpleNamespace(status="completed" if self.completed else "in_progress")

        def ready_tasks(self, *, limit: int):
            aliases = materializer.INITIAL_READY if self.completed else ()
            return SimpleNamespace(tasks=[SimpleNamespace(task_alias=item) for item in aliases])

    _snapshot, ready = materializer._verify_materialized_source(
        FakeSource(False), population, operator_completed=False
    )
    assert ready == ()
    _snapshot, ready = materializer._verify_materialized_source(
        FakeSource(True), population, operator_completed=True
    )
    assert ready == materializer.INITIAL_READY


def test_materializer_recovers_only_exact_post_cas_operator_receipt() -> None:
    materializer = _load("pctdd_recovery_materializer", MATERIALIZER)
    receipt = {
        "schema": materializer.CONTROL_EVIDENCE_SCHEMA,
        "evidence_digest": "evidence:control",
        "evidence_event_id": "event:1",
        "source_head": "a" * 40,
        "repository_tree_id": "b" * 40,
        "plan_root_cid": "plan:1",
    }
    task = SimpleNamespace(
        task_cid="task:0",
        revision=2,
        body={"completion_receipt": receipt},
    )
    payloads: list[dict[str, object]] = []

    def identity(payload):
        payloads.append(payload)
        return f"cid:{len(payloads)}"

    evidence, completion = materializer._recover_operator_completion_receipt(
        task,
        exact_head="a" * 40,
        exact_tree="b" * 40,
        plan_root_cid="plan:1",
        content_identity=identity,
    )
    assert evidence == "evidence:control"
    assert completion == "cid:2"
    assert payloads[0]["revision"] == 2
    assert payloads[1]["namespace"] == "completion-receipt"
    with pytest.raises(materializer.MaterializationError, match="binding differs"):
        materializer._recover_operator_completion_receipt(
            task,
            exact_head="c" * 40,
            exact_tree="b" * 40,
            plan_root_cid="plan:1",
            content_identity=identity,
        )


def test_dispatcher_uses_nonshadowable_plugin_and_process_tree_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    dispatcher = _load("pctdd_run_dispatcher", DISPATCHER)
    with dispatcher._sealed_validation_environment() as (environment, python, _receipt):
        assert str(ROOT / "scripts") == environment["PYTHONPATH"].split(dispatcher.os.pathsep)[0]
        assert dispatcher._run_child(
            [python, "-c", f"import {dispatcher.PYTEST_PLUGIN_NAME}"],
            cwd=ROOT,
            environment=environment,
            timeout_seconds=30,
        ) == 0

    calls: list[dict[str, object]] = []

    class FakeProcess:
        returncode = 0

        def communicate(self, *, timeout: int):
            calls.append({"timeout": timeout})
            return (None, None)

    def fake_popen(args, **kwargs):
        calls.append({"args": list(args), **kwargs})
        return FakeProcess()

    monkeypatch.setattr(dispatcher.subprocess, "Popen", fake_popen)
    assert dispatcher._run_child(
        ["python", "-V"], cwd=ROOT, environment={}, timeout_seconds=17
    ) == 0
    launch = calls[0]
    assert launch["shell"] is False
    assert launch["start_new_session"] is True
    assert launch["close_fds"] is True
    assert calls[1]["timeout"] == 17


def test_facade_preflight_and_launch_are_operator_seal_gated(monkeypatch: pytest.MonkeyPatch) -> None:
    facade = _load("pctdd_operator_facade", FACADE)
    calls: list[str] = []
    monkeypatch.setattr(facade, "_load_board", lambda _path: (object(), {}))

    def reject(_path):
        calls.append("seal")
        raise facade.OperatorError("not sealed")

    monkeypatch.setattr(facade, "_require_operator_seal", reject)
    monkeypatch.setattr(facade, "_run", lambda *_args, **_kwargs: calls.append("run"))
    with pytest.raises(facade.OperatorError, match="not sealed"):
        facade.preflight(ROOT / "config/example.json")
    assert calls == ["seal"]


def test_facade_passes_confined_relative_config_to_materializer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_relative_config_facade", FACADE)
    config = ROOT / "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json"

    class FakePath:
        def __init__(self, *, present: bool, relative: str) -> None:
            self.present = present
            self.relative = relative

        def is_file(self) -> bool:
            return self.present

        def relative_to(self, _root: Path) -> Path:
            return Path(self.relative)

    database = FakePath(present=True, relative="data/test/control.duckdb")
    owner_status = FakePath(present=False, relative="data/test/owner.json")
    calls: list[list[str]] = []
    monkeypatch.setattr(facade, "_load_board", lambda _path: (object(), {}))
    monkeypatch.setattr(
        facade,
        "_runtime_paths",
        lambda _board: {"database": database, "owner_status": owner_status},
    )

    def successful_child(argv, **_kwargs):
        calls.append(list(argv))
        return {"returncode": 0, "json": {"materialized": True}}

    monkeypatch.setattr(facade, "_run", successful_child)
    result = facade.materialize(config)
    assert result["materialized"] is True
    assert calls[0][-2:] == [
        "--config",
        "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json",
    ]
    with pytest.raises(facade.OperatorError, match="escapes"):
        facade._repository_relative_argument(tmp_path / "outside.json")
