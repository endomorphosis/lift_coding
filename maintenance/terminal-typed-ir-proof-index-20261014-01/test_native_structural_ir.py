"""Native owner tests use exclusively authored source and scheduler fixtures."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

import native_structural_ir as subject
from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
from ipfs_datasets_py.logic.software_contracts.cache import CacheIntegrityError
from ipfs_datasets_py.logic.software_contracts.codebase_ir import (
    CodebaseScanLimits, StaleCodebaseError,
)
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.proof_resource_safety import ProofHostResources
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import (
    GlobalResourceScheduler, ResourceSchedulerConfig, ResourceConfigurationError,
)


def _command(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def _repo(root: Path, body: bytes = b"def increment(n: int) -> int:\n    return n + 1\n"):
    root.mkdir()
    _command(root, "init", "-q")
    (root / "unit.py").write_bytes(body)
    _command(root, "add", "--", "unit.py")
    _command(root, "-c", "user.name=Authored fixture", "-c", "user.email=fixture@invalid",
             "commit", "-qm", "Authored source fixture")
    return {"unit.py": hashlib.sha256(body).hexdigest()}


@pytest.fixture
def authored_scheduler(tmp_path, monkeypatch):
    # Deliberately synthetic host exists only for this authored unit fixture.
    # Benchmark code's _scheduler() uses the actual native host sampler.
    scheduler = GlobalResourceScheduler(ResourceSchedulerConfig.for_proof_host(
        state_path=tmp_path / "authored-unit-resource-state.json",
        proof_resource_sampler=lambda: ProofHostResources(8, 8192, 8192),
        auto_renew_leases=False,
    ))
    monkeypatch.setattr(subject, "_scheduler", lambda: scheduler)
    return scheduler


@pytest.fixture
def prepared(tmp_path, authored_scheduler):
    repository = tmp_path / "authored-source"
    sources = _repo(repository)
    output = tmp_path / "authored-output"
    result = subject.prepare_structural_ir(repository=repository, output=output,
        repository_id="authored:structural-fixture", expected_sources=sources)
    return repository, output, result, authored_scheduler


def test_native_prepare_and_fresh_owner_replay_complete_inventory(prepared):
    repository, output, result, _ = prepared
    replay = subject.verify_structural_ir(repository=repository, output=output, expected=result)
    assert replay["verified"] and replay["fresh_native_owner"]
    assert replay["same_head"] == result["head"]
    assert result["coverage"]["inventory_entries"] == 1
    assert result["coverage"]["ast_ok"] == 1
    assert result["coverage"]["formalized_properties"] == 0
    assert result["coverage"]["checked_properties"] == 0
    assert result["claims"] == subject.CLAIMS
    assert result["manifest"]["authority"] == "structural_only"
    assert result["sources"][0]["ast_cid"] == result["manifest"]["units"][0]["ast_cid"]
    assert result["sql_rows"]["source_files"] == 1
    assert result["sql_rows"]["symbols"] > 0
    assert result["resources"]["proof_safety_enabled"] is True


def test_source_body_never_imported(tmp_path, authored_scheduler):
    repository = tmp_path / "authored-source"
    marker = tmp_path / "execution-marker"
    body = ("from pathlib import Path\nPath(" + repr(str(marker)) +
            ").write_text('executed')\ndef increment(n):\n    return n + 1\n").encode()
    sources = _repo(repository, body)
    result = subject.prepare_structural_ir(repository=repository,
        output=tmp_path / "output", repository_id="authored:nonexecuting", expected_sources=sources)
    assert result["coverage"]["ast_ok"] == 1
    assert not marker.exists()


def test_multiple_bounded_files_publish_and_reopen_above_one_file_total(tmp_path, authored_scheduler):
    repository = tmp_path / "authored-multiple-source"
    first = b"#" + b"a" * 5000 + b"\ndef increment(n: int) -> int:\n    return n + 1\n"
    second = b"#" + b"b" * 5000 + b"\ndef decrement(n: int) -> int:\n    return n - 1\n"
    sources = _repo(repository, first)
    (repository / "other.py").write_bytes(second)
    sources["other.py"] = hashlib.sha256(second).hexdigest()
    _command(repository, "add", "--", "other.py")
    _command(repository, "-c", "user.name=Authored fixture", "-c", "user.email=fixture@invalid",
             "commit", "-qm", "Second authored bounded source")
    assert max(len(first), len(second)) <= subject.MAX_FILE_BYTES
    assert subject.MAX_FILE_BYTES < len(first) + len(second) <= subject.MAX_TOTAL_SOURCE_BYTES
    output = tmp_path / "authored-multiple-output"
    result = subject.prepare_structural_ir(repository=repository, output=output,
        repository_id="authored:multiple-bounded-files", expected_sources=sources)
    assert result["coverage"]["inventory_entries"] == result["coverage"]["ast_ok"] == 2
    assert result["sql_rows"]["source_files"] == 2
    assert result["resources"]["max_total_source_bytes"] == 5 * subject.MAX_FILE_BYTES
    entries = {entry["path"]: entry for entry in result["manifest"]["snapshot"]["entries"]}
    assert {row["path"] for row in result["sources"]} == set(sources)
    assert all(row["source_cid"] == entries[row["path"]]["source_cid"]
               and row["sha256"] == sources[row["path"]] for row in result["sources"])
    replay = subject.verify_structural_ir(repository=repository, output=output, expected=result)
    assert replay["verified"] and replay["source_files"] == 2
    assert replay["source_bytes"] == len(first) + len(second)
    assert replay["same_head"] == result["head"]


def test_source_edit_refuses_current_replay(prepared):
    repository, output, result, _ = prepared
    (repository / "unit.py").write_text("def increment(n):\n    return n + 2\n")
    with pytest.raises(StaleCodebaseError, match="repository differs"):
        subject.verify_structural_ir(repository=repository, output=output, expected=result)


def test_wrong_complete_head_refuses_native_observation(prepared):
    repository, output, result, scheduler = prepared
    wrong = dict(result["head"], generation=result["head"]["generation"] + 1)
    with subject._owner(output, existing=True) as (index, _):
        with pytest.raises(StaleCodebaseError, match="catalog head changed"):
            index.observe_current(repository, expected_head=CodebaseHead.from_dict(wrong),
                                  scheduler=scheduler, memory_mb=subject.MEMORY_MB)


def test_same_content_new_generation_stales_old_head(prepared):
    repository, output, result, scheduler = prepared
    head = CodebaseHead.from_dict(result["head"])
    with subject._owner(output, existing=True) as (index, _):
        receipt = index.prepare_current(repository, repository_id=head.repository_id,
            operation_id="authored-republication-02", expected_head=head,
            limits=CodebaseScanLimits(max_entries=subject.MAX_SOURCES,
                                      max_file_bytes=subject.MAX_FILE_BYTES),
            scheduler=scheduler, memory_mb=subject.MEMORY_MB)
        assert receipt.head.generation == head.generation + 1
        assert receipt.head.snapshot_cid == head.snapshot_cid
        assert receipt.head.manifest_cid == head.manifest_cid
        assert receipt.head != head
        index.observe_current(repository, expected_head=receipt.head,
                              scheduler=scheduler, memory_mb=subject.MEMORY_MB)
    with pytest.raises(StaleCodebaseError, match="catalog head changed"):
        subject.verify_structural_ir(repository=repository, output=output, expected=result)


@pytest.mark.parametrize("artifact", ["source", "ast", "manifest"])
def test_missing_native_cas_artifact_refuses_replay(prepared, artifact):
    repository, output, result, _ = prepared
    with subject._owner(output, existing=True) as (index, _):
        if artifact == "source":
            path = index.artifacts.path_for(result["sources"][0]["source_cid"], source=True)
        else:
            cid = result["manifest_cid"] if artifact == "manifest" else result["sources"][0]["ast_cid"]
            path = index.artifacts.path_for(cid)
        path.unlink()
    with pytest.raises((CacheIntegrityError, FileNotFoundError)):
        subject.verify_structural_ir(repository=repository, output=output, expected=result)


@pytest.mark.parametrize("sidecar", ["manifest.json", "head.json", "receipt.json", "structural.json"])
def test_changed_public_sidecar_refuses_replay(prepared, sidecar):
    repository, output, result, _ = prepared
    path = output / sidecar
    value = subject._read(path)
    value["extra_field"] = "authored damage"
    path.write_bytes(subject._json_bytes(value))
    with pytest.raises(subject.StructuralIRGuardError, match="sidecar"):
        subject.verify_structural_ir(repository=repository, output=output, expected=result)


def test_proof_authority_promotion_refuses_before_native_open(prepared):
    repository, output, result, _ = prepared
    changed = deepcopy(result)
    changed["claims"]["proof_authority"] = True
    with pytest.raises(subject.StructuralIRGuardError, match="authority"):
        subject.verify_structural_ir(repository=repository, output=output, expected=changed)


def test_enclosing_git_root_guard_prevents_any_native_admission(tmp_path, monkeypatch):
    parent = tmp_path / "outer-repository"
    _repo(parent)
    repository = parent / "subdirectory"
    repository.mkdir()
    sources = {"unit.py": "0" * 64}
    monkeypatch.setattr(subject, "_scheduler", lambda: pytest.fail("scope guard must precede admission"))
    with pytest.raises(subject.StructuralIRGuardError, match="own Git root"):
        subject.prepare_structural_ir(repository=repository, output=tmp_path / "output",
            repository_id="authored:wrong-scope", expected_sources=sources)


def test_extra_inventory_rejected_before_native_admission(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    sources = _repo(repository)
    (repository / "extra.py").write_text("raise RuntimeError('unexpected')\n")
    monkeypatch.setattr(subject, "_scheduler", lambda: pytest.fail("inventory guard must precede admission"))
    with pytest.raises(subject.StructuralIRGuardError, match="inventory"):
        subject.prepare_structural_ir(repository=repository, output=tmp_path / "output",
            repository_id="authored:extra", expected_sources=sources)


def test_oversized_source_rejected_before_native_admission(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    sources = _repo(repository, b"#" * (subject.MAX_FILE_BYTES + 1))
    monkeypatch.setattr(subject, "_scheduler", lambda: pytest.fail("bounds guard must precede admission"))
    with pytest.raises(subject.StructuralIRGuardError, match="bounded"):
        subject.prepare_structural_ir(repository=repository, output=tmp_path / "output",
            repository_id="authored:large", expected_sources=sources)


@pytest.mark.parametrize("sources", [{}, {f"f{i}.py": "0" * 64 for i in range(6)},
    {"../unit.py": "0" * 64}, {"unit.py": "BAD"}, {"unit.py": True}])
def test_invalid_explicit_source_profile_rejected_before_admission(tmp_path, monkeypatch, sources):
    monkeypatch.setattr(subject, "_scheduler", lambda: pytest.fail("profile guard must precede admission"))
    with pytest.raises(subject.StructuralIRGuardError):
        subject.prepare_structural_ir(repository=tmp_path / "absent",
            output=tmp_path / "output", repository_id="authored:profile", expected_sources=sources)


def test_output_inside_source_guard(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    sources = _repo(repository)
    monkeypatch.setattr(subject, "_scheduler", lambda: pytest.fail("scope guard must precede admission"))
    with pytest.raises(subject.StructuralIRGuardError, match="separate scope"):
        subject.prepare_structural_ir(repository=repository, output=repository / "output",
            repository_id="authored:output-scope", expected_sources=sources)


def test_existing_output_never_overwritten(prepared):
    repository, output, result, _ = prepared
    before = (output / "structural.json").read_bytes()
    with pytest.raises(FileExistsError):
        subject.prepare_structural_ir(repository=repository, output=output,
            repository_id="authored:overwrite", expected_sources=result["expected_sources"])
    assert (output / "structural.json").read_bytes() == before


@pytest.fixture
def authored_config_pool(tmp_path):
    safe = ResourceSchedulerConfig.for_proof_host(
        state_path=tmp_path / "authored-existing-safe-pool.json",
        proof_resource_sampler=lambda: ProofHostResources(8, 8192, 8192),
        auto_renew_leases=False,
    )
    stored = safe.persisted_dict()
    stored["total_cpu_slots"] = 4
    stored["total_memory_mb"] = 4096
    stored["total_child_process_slots"] = 4
    stored["proof_memory_headroom_mb"] += 128
    stored["proof_memory_stall_percent"] = 1.0
    stored["proof_cpu_stall_percent"] = 40.0
    stored["proof_io_stall_percent"] = 5.0
    existing = GlobalResourceScheduler(replace(safe, **stored))
    return safe, stored, existing


def test_safe_existing_lower_capacity_attachment_preserves_exact_pool(authored_config_pool, monkeypatch):
    safe, stored, existing = authored_config_pool
    before = existing.state_path.read_bytes()
    monkeypatch.setattr(subject, "_safe_scheduler_config", lambda: safe)
    attached = subject._scheduler()
    assert attached.state_path == existing.state_path
    assert subject._json_bytes(attached.config.persisted_dict()) == subject._json_bytes(stored)
    assert attached.config.proof_resource_sampler is safe.proof_resource_sampler
    assert attached.config.proof_safety_enabled is True
    assert existing.state_path.read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("proof_safety_enabled", False), ("total_cpu_slots", 1000),
    ("total_memory_mb", 1000000), ("total_child_process_slots", 1000),
    ("proof_memory_headroom_mb", 0), ("proof_memory_stall_percent", 3.0),
    ("proof_cpu_stall_percent", 51.0), ("proof_io_stall_percent", 11.0),
    ("proof_backoff_seconds", 0.0), ("max_waiting_requests", None),
    ("max_waiting_requests", 257), ("require_known_gpu_for_gpu_work", False),
    ("total_gpu_memory_mb", 8192), ("total_unified_memory_mb", 8192),
    ("total_cpu_slots", True), ("proof_memory_stall_percent", True),
    ("proof_memory_stall_percent", "1.0"), ("unknown_capacity", 1),
    ("proof_recovery_enabled", True), ("proof_resource_profile", "local-benchmark@1"),
    ("proof_recovery_samples", 3), ("proof_recovery_samples", True),
    ("proof_recovery_grants", 1), ("proof_recovery_grants", True),
    ("proof_recovery_interval_seconds", 1.0), ("proof_recovery_interval_seconds", True),
])
def test_unsafe_or_unknown_persisted_config_refused(authored_config_pool, field, value):
    safe, stored, existing = authored_config_pool
    before = existing.state_path.read_bytes()
    changed = dict(stored, **{field: value})
    with pytest.raises(ResourceConfigurationError):
        subject._conservative_existing_config(safe, changed)
    assert existing.state_path.read_bytes() == before


def test_incomplete_persisted_config_refused(authored_config_pool):
    safe, stored, _ = authored_config_pool
    changed = dict(stored)
    changed.pop("proof_cpu_stall_percent")
    with pytest.raises(ResourceConfigurationError, match="incomplete"):
        subject._conservative_existing_config(safe, changed)


def test_stricter_global_percentage_guard_preserved(authored_config_pool):
    safe, stored, _ = authored_config_pool
    guarded_safe = replace(safe, max_memory_percent=80, max_swap_percent=20)
    changed = dict(stored, max_memory_percent=70, max_swap_percent=10)
    attached = subject._conservative_existing_config(guarded_safe, changed)
    assert attached.max_memory_percent == 70
    for bad in (None, 90):
        with pytest.raises(ResourceConfigurationError, match="percentage"):
            subject._conservative_existing_config(guarded_safe, dict(changed, max_memory_percent=bad))


def test_configuration_change_between_projection_and_constructor_never_reconfigures(authored_config_pool, monkeypatch):
    safe, stored, existing = authored_config_pool
    constructor = subject._construct_existing_scheduler
    changed_bytes = None
    def racing(config):
        nonlocal changed_bytes
        # An authored idle pool deliberately changes after the attachment read.
        state = json.loads(existing.state_path.read_bytes())
        state["config"]["total_cpu_slots"] -= 1
        changed_bytes = subject._json_bytes(state)
        existing.state_path.write_bytes(changed_bytes)
        return constructor(config)
    monkeypatch.setattr(subject, "_safe_scheduler_config", lambda: safe)
    monkeypatch.setattr(subject, "_construct_existing_scheduler", racing)
    with pytest.raises(ResourceConfigurationError, match="configuration changed"):
        subject._scheduler()
    assert existing.state_path.read_bytes() == changed_bytes


def test_state_removed_before_constructor_is_never_recreated(authored_config_pool, monkeypatch):
    safe, _, existing = authored_config_pool
    constructor = subject._construct_existing_scheduler
    def racing(config):
        existing.state_path.unlink()
        return constructor(config)
    monkeypatch.setattr(subject, "_safe_scheduler_config", lambda: safe)
    monkeypatch.setattr(subject, "_construct_existing_scheduler", racing)
    with pytest.raises(ResourceConfigurationError, match="creation refused"):
        subject._scheduler()
    assert not existing.state_path.exists()


def test_config_prefix_reader_stops_before_any_private_state_byte(tmp_path, monkeypatch):
    path = tmp_path / "authored-prefix.json"
    config = {"field": "value", "nested": {"list": [1, 2]}}
    prefix = b'{"config":' + subject._json_bytes(config)
    path.write_bytes(prefix + b',"leases":{"authored-secret-placeholder":"DO_NOT_READ"}}')
    consumed = bytearray()
    original_read = os.read
    def observed(fd, size):
        value = original_read(fd, size)
        consumed.extend(value)
        return value
    monkeypatch.setattr(subject.os, "read", observed)
    assert subject._configuration_prefix(path) == config
    assert bytes(consumed) == prefix


@pytest.mark.parametrize("body", [b'{"leases":{},"config":{}}',
    b'{"config":{"field":1,"field":2}}', b'{"config":{"field":NaN}}',
    b'{"config":', b'{"config":{"field":"' + b'x' * 65536 + b'"}}'])
def test_non_native_or_unbounded_config_prefix_refused(tmp_path, body):
    path = tmp_path / "authored-prefix.json"
    path.write_bytes(body)
    with pytest.raises(ResourceConfigurationError):
        subject._configuration_prefix(path)


def test_config_prefix_symlink_refused(tmp_path):
    path = tmp_path / "authored.json"
    path.write_bytes(b'{"config":{}}')
    link = tmp_path / "authored-link.json"
    link.symlink_to(path)
    with pytest.raises(OSError):
        subject._configuration_prefix(link)
