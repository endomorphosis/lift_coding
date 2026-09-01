"""Security and determinism tests for the opt-in PCTDD user-systemd ensure."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
INSTALLER = (
    ROOT
    / "scripts"
    / "ops"
    / "agent_supervisor"
    / "parallel_content_sealing_proof_carrying_tdd_user_systemd.py"
)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, INSTALLER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _binding() -> dict[str, object]:
    return {
        "source_head": "1" * 40,
        "source_tree": "2" * 40,
        "configuration_root": "sha256:" + "3" * 64,
        "control_roots": {"config/control.json": "sha256:" + "4" * 64},
    }


def _capability() -> dict[str, object]:
    return {
        "systemctl": "/usr/bin/systemctl",
        "loginctl": "/usr/bin/loginctl",
        "manager_state": "running",
        "linger_enabled": True,
        "_environment": {"PATH": "/usr/bin:/bin"},
    }


def _stub_admission(module, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        module,
        "_validate_current_controls",
        lambda _path: _binding(),
    )
    monkeypatch.setattr(module, "_require_user_systemd", _capability)


def test_templates_render_deterministically_to_resume_only() -> None:
    module = _load("pctdd_systemd_deterministic_render")

    first = module._render_units()
    second = module._render_units()

    assert first == second
    assert set(first) == {module.SERVICE_NAME, module.TIMER_NAME}
    service = first[module.SERVICE_NAME].decode("utf-8")
    timer = first[module.TIMER_NAME].decode("utf-8")
    exec_lines = [line for line in service.splitlines() if line.startswith("ExecStart=")]
    assert len(exec_lines) == 1
    command = exec_lines[0]
    assert str(module.OPERATOR_SCRIPT) in command
    assert str(module.SCHEDULER_CONFIG) in command
    assert " -E -P " in command
    assert " -I " not in command
    assert " resume --monitor-seconds 180" in command
    assert " state-owner" not in command
    assert " launch " not in command
    assert "token" not in command.lower()
    assert "secret" not in command.lower()
    assert "Environment=" not in service
    assert "EnvironmentFile=" not in service
    assert "Type=oneshot" in service
    assert "TimeoutStartSec=3600" in service
    assert module.TIMEOUT_SECONDS >= (
        (2 * 900)
        + (module.MONITOR_SECONDS + 30)
        + 120
        + 900
        + module.MONITOR_SECONDS
    )
    assert "Restart=no" in service
    assert "KillMode=process" in service
    assert "StartLimitIntervalSec=1800" in service
    assert "StartLimitBurst=3" in service
    assert "Documentation=file:///" in service
    assert "file://file://" not in service
    assert "OnBootSec=3min" in timer
    assert "OnUnitActiveSec=10min" in timer
    assert "Persistent=true" in timer
    assert "RandomizedDelaySec=45s" in timer
    assert f"Unit={module.SERVICE_NAME}" in timer
    assert "WantedBy=timers.target" in timer


def test_user_systemd_controls_are_sealed_and_worker_protected() -> None:
    controls = {
        "config/parallel_content_sealing_proof_carrying_tdd_ensure.service.in",
        "config/parallel_content_sealing_proof_carrying_tdd_ensure.timer",
        (
            "scripts/ops/agent_supervisor/"
            "parallel_content_sealing_proof_carrying_tdd_user_systemd.py"
        ),
        "test/api/parallel_content_sealing/test_pctdd_user_systemd_ensure.py",
    }
    scheduler = json.loads(
        (
            ROOT
            / "config"
            / "agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json"
        ).read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (
            ROOT
            / "config"
            / "parallel_content_sealing_proof_carrying_tdd_control_manifest.json"
        ).read_text(encoding="utf-8")
    )
    seal = json.loads(
        (
            ROOT
            / "config"
            / "parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json"
        ).read_text(encoding="utf-8")
    )

    assert controls <= set(scheduler["protected_paths"])
    assert controls <= set(
        scheduler["descendant_source_successor_materialization"][
            "operator_control_paths"
        ]
    )
    assert controls <= set(
        manifest["protected_control_hashes_before_manifest_and_seal"]
    )
    assert controls <= set(seal["artifacts"])


def test_rendered_units_pass_systemd_analyze_when_available(tmp_path: Path) -> None:
    tool = shutil.which("systemd-analyze", path="/usr/bin:/bin")
    if not tool:
        pytest.skip("systemd-analyze is unavailable")
    module = _load("pctdd_systemd_analyze_rendered_units")
    units = module._render_units()
    paths: list[str] = []
    for name, payload in sorted(units.items()):
        path = tmp_path / name
        path.write_bytes(payload)
        path.chmod(0o600)
        paths.append(str(path))

    result = subprocess.run(
        (tool, "verify", *paths),
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "LANG": "C"},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=15.0,
        check=False,
    )

    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")


def test_install_rejects_control_gate_before_capability_or_external_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_control_gate_first")
    unit_dir = tmp_path / "user-units"
    monkeypatch.setattr(
        module,
        "_validate_current_controls",
        lambda _path: (_ for _ in ()).throw(module.EnsureError("current_tree_rejected")),
    )
    monkeypatch.setattr(
        module,
        "_require_user_systemd",
        lambda: pytest.fail("capability probing must follow current-tree admission"),
    )
    monkeypatch.setattr(
        module,
        "_ensure_unit_dir",
        lambda _path: pytest.fail("rejected controls must not create a unit directory"),
    )

    with pytest.raises(module.EnsureError, match="current_tree_rejected"):
        module.install(
            module.SCHEDULER_CONFIG,
            unit_dir=unit_dir,
            daemon_reload=False,
            enable=False,
        )

    assert not unit_dir.exists()


def test_install_revalidates_controls_before_first_external_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_control_revalidation")
    unit_dir = tmp_path / "user-units"
    _stub_admission(module, monkeypatch)
    monkeypatch.setattr(
        module,
        "_require_stable_validation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            module.EnsureError("current_controls_changed_before_external_write")
        ),
    )
    monkeypatch.setattr(
        module,
        "_ensure_unit_dir",
        lambda _path: pytest.fail("drifted controls must not create a unit directory"),
    )

    with pytest.raises(module.EnsureError, match="changed_before_external_write"):
        module.install(
            module.SCHEDULER_CONFIG,
            unit_dir=unit_dir,
            daemon_reload=False,
            enable=False,
        )

    assert not unit_dir.exists()


def test_inert_install_is_atomic_private_and_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_inert_idempotent_install")
    unit_dir = tmp_path / "user-units"
    _stub_admission(module, monkeypatch)
    monkeypatch.setattr(
        module,
        "_systemctl_action",
        lambda *_args, **_kwargs: pytest.fail(
            "install without explicit flags must not mutate systemd"
        ),
    )

    first = module.install(
        module.SCHEDULER_CONFIG,
        unit_dir=unit_dir,
        daemon_reload=False,
        enable=False,
    )
    second = module.install(
        module.SCHEDULER_CONFIG,
        unit_dir=unit_dir,
        daemon_reload=False,
        enable=False,
    )

    assert first["created"] == sorted([module.SERVICE_NAME, module.TIMER_NAME])
    assert first["already_exact"] == []
    assert first["upgraded_from_sealed_predecessor"] == []
    assert second["created"] == []
    assert second["already_exact"] == sorted([module.SERVICE_NAME, module.TIMER_NAME])
    assert second["upgraded_from_sealed_predecessor"] == []
    assert first["daemon_reload"] is False
    assert first["timer_enabled_and_started"] is False
    assert first["direct_owner_or_master_launch"] is False
    expected = module._render_units()
    for name, payload in expected.items():
        path = unit_dir / name
        assert path.read_bytes() == payload
        observed = os.lstat(path)
        assert stat.S_ISREG(observed.st_mode)
        assert observed.st_nlink == 1
        assert stat.S_IMODE(observed.st_mode) == 0o600


def test_install_atomically_upgrades_exact_sealed_predecessor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_sealed_predecessor_upgrade")
    unit_dir = tmp_path / "user-units"
    unit_dir.mkdir(mode=0o700)
    units = module._render_units()
    migratable = module._migratable_unit_payloads(units)
    legacy_service = migratable[module.SERVICE_NAME]
    assert len(legacy_service) == 1
    for name, payload in units.items():
        path = unit_dir / name
        path.write_bytes(
            legacy_service[0] if name == module.SERVICE_NAME else payload
        )
        path.chmod(0o600)
    _stub_admission(module, monkeypatch)
    monkeypatch.setattr(
        module,
        "_systemctl_action",
        lambda *_args, **_kwargs: pytest.fail(
            "inert migration must not mutate systemd"
        ),
    )

    result = module.install(
        module.SCHEDULER_CONFIG,
        unit_dir=unit_dir,
        daemon_reload=False,
        enable=False,
    )
    repeated = module.install(
        module.SCHEDULER_CONFIG,
        unit_dir=unit_dir,
        daemon_reload=False,
        enable=False,
    )

    assert result["created"] == []
    assert result["already_exact"] == [module.TIMER_NAME]
    assert result["upgraded_from_sealed_predecessor"] == [
        module.SERVICE_NAME
    ]
    assert (unit_dir / module.SERVICE_NAME).read_bytes() == units[
        module.SERVICE_NAME
    ]
    assert repeated["upgraded_from_sealed_predecessor"] == []
    assert repeated["already_exact"] == sorted(units)
    assert not list(unit_dir.glob(".*.upgrade.*"))


def test_sealed_predecessor_digest_cannot_drift_with_current_template() -> None:
    module = _load("pctdd_systemd_predecessor_digest")
    units = module._render_units()
    units[module.SERVICE_NAME] = units[module.SERVICE_NAME].replace(
        b"Restart=no\n",
        b"Restart=yes\n",
    )

    with pytest.raises(module.EnsureError, match="predecessor_derivation"):
        module._migratable_unit_payloads(units)


def test_upgrade_exchange_rolls_back_a_raced_unknown_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_upgrade_exchange_race")
    unit_dir = tmp_path / "user-units"
    unit_dir.mkdir(mode=0o700)
    units = module._render_units()
    legacy = module._migratable_unit_payloads(units)[module.SERVICE_NAME][0]
    service = unit_dir / module.SERVICE_NAME
    service.write_bytes(legacy)
    service.chmod(0o600)
    timer = unit_dir / module.TIMER_NAME
    timer.write_bytes(units[module.TIMER_NAME])
    timer.chmod(0o600)
    raced = unit_dir / "raced.service"
    unknown = b"[Service]\nExecStart=/bin/false\n"
    raced.write_bytes(unknown)
    raced.chmod(0o600)
    _stub_admission(module, monkeypatch)
    real_exchange = module._rename_exchange_at
    exchanged = False

    def race_then_exchange(directory_fd: int, left: str, right: str) -> None:
        nonlocal exchanged
        if not exchanged:
            exchanged = True
            os.replace(
                raced.name,
                right,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
        real_exchange(directory_fd, left, right)

    monkeypatch.setattr(module, "_rename_exchange_at", race_then_exchange)

    with pytest.raises(module.EnsureError, match="changed_before_upgrade"):
        module.install(
            module.SCHEDULER_CONFIG,
            unit_dir=unit_dir,
            daemon_reload=False,
            enable=False,
        )

    assert service.read_bytes() == unknown
    assert not list(unit_dir.glob(".*.upgrade.*"))


def test_preexisting_temporary_is_never_removed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_preexisting_temporary")
    unit_dir = tmp_path / "user-units"
    unit_dir.mkdir(mode=0o700)
    token = "a" * 32
    monkeypatch.setattr(module.secrets, "token_hex", lambda _size: token)
    temporary = unit_dir / (
        f".{module.SERVICE_NAME}.tmp.{os.getpid()}.{token}"
    )
    unknown = b"preserve this unrelated temporary\n"
    temporary.write_bytes(unknown)
    temporary.chmod(0o600)
    _stub_admission(module, monkeypatch)

    with pytest.raises(module.EnsureError, match="atomic_unit_write_failed"):
        module.install(
            module.SCHEDULER_CONFIG,
            unit_dir=unit_dir,
            daemon_reload=False,
            enable=False,
        )

    assert temporary.read_bytes() == unknown
    assert not (unit_dir / module.SERVICE_NAME).exists()


def test_directory_swap_is_detected_with_dirfd_anchored_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_directory_swap")
    unit_dir = tmp_path / "user-units"
    displaced = tmp_path / "displaced-user-units"
    _stub_admission(module, monkeypatch)
    real_create = module._atomic_private_create
    swapped = False

    def swap_then_create(name: str, payload: bytes, directory_fd: int) -> None:
        nonlocal swapped
        if not swapped:
            swapped = True
            unit_dir.rename(displaced)
            unit_dir.mkdir(mode=0o700)
        real_create(name, payload, directory_fd)

    monkeypatch.setattr(module, "_atomic_private_create", swap_then_create)

    with pytest.raises(module.EnsureError, match="directory_changed"):
        module.install(
            module.SCHEDULER_CONFIG,
            unit_dir=unit_dir,
            daemon_reload=False,
            enable=False,
        )

    assert list(unit_dir.iterdir()) == []
    assert sorted(path.name for path in displaced.iterdir()) == sorted(
        [module.SERVICE_NAME, module.TIMER_NAME]
    )


def test_directory_mode_change_is_detected_before_install_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_directory_mode_race")
    unit_dir = tmp_path / "user-units"
    _stub_admission(module, monkeypatch)
    real_create = module._atomic_private_create
    changed = False

    def chmod_then_create(name: str, payload: bytes, directory_fd: int) -> None:
        nonlocal changed
        if not changed:
            changed = True
            unit_dir.chmod(0o777)
        real_create(name, payload, directory_fd)

    monkeypatch.setattr(module, "_atomic_private_create", chmod_then_create)

    with pytest.raises(module.EnsureError, match="directory_changed"):
        module.install(
            module.SCHEDULER_CONFIG,
            unit_dir=unit_dir,
            daemon_reload=False,
            enable=False,
        )

    assert stat.S_IMODE(unit_dir.stat().st_mode) == 0o777


def test_unrecognized_existing_unit_blocks_all_install_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_unknown_existing_install")
    unit_dir = tmp_path / "user-units"
    unit_dir.mkdir(mode=0o700)
    service = unit_dir / module.SERVICE_NAME
    service.write_bytes(b"[Service]\nExecStart=/bin/false\n")
    service.chmod(0o600)
    _stub_admission(module, monkeypatch)
    monkeypatch.setattr(
        module,
        "_systemctl_action",
        lambda *_args, **_kwargs: pytest.fail("unknown units must block systemctl"),
    )

    with pytest.raises(module.EnsureError, match="unrecognized_existing_unit_content"):
        module.install(
            module.SCHEDULER_CONFIG,
            unit_dir=unit_dir,
            daemon_reload=False,
            enable=False,
        )

    assert service.read_bytes() == b"[Service]\nExecStart=/bin/false\n"
    assert not (unit_dir / module.TIMER_NAME).exists()


@pytest.mark.parametrize("unsafe_kind", ["symlink", "hardlink"])
def test_unsafe_existing_unit_custody_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_kind: str,
) -> None:
    module = _load(f"pctdd_systemd_unsafe_{unsafe_kind}")
    unit_dir = tmp_path / "user-units"
    unit_dir.mkdir(mode=0o700)
    target = unit_dir / "outside"
    target.write_bytes(module._render_units()[module.SERVICE_NAME])
    target.chmod(0o600)
    service = unit_dir / module.SERVICE_NAME
    if unsafe_kind == "symlink":
        service.symlink_to(target)
    else:
        os.link(target, service)
    _stub_admission(module, monkeypatch)

    with pytest.raises(module.EnsureError):
        module.install(
            module.SCHEDULER_CONFIG,
            unit_dir=unit_dir,
            daemon_reload=False,
            enable=False,
        )

    assert not (unit_dir / module.TIMER_NAME).exists()


def test_enable_requires_explicit_reload_before_any_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_enable_requires_reload")
    monkeypatch.setattr(
        module,
        "_validate_current_controls",
        lambda _path: pytest.fail("invalid activation flags must fail first"),
    )

    with pytest.raises(module.EnsureError, match="enable_requires_explicit"):
        module.install(
            module.SCHEDULER_CONFIG,
            unit_dir=tmp_path / "units",
            daemon_reload=False,
            enable=True,
        )


def test_systemctl_actions_require_the_exact_default_unit_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_action_default_directory")
    custom = tmp_path / "custom"
    default = tmp_path / "default"
    monkeypatch.setattr(module, "_default_unit_dir", lambda: default)
    monkeypatch.setattr(
        module,
        "_validate_current_controls",
        lambda _path: pytest.fail("directory authority must fail before validation"),
    )

    with pytest.raises(module.EnsureError, match="default_unit_directory"):
        module.install(
            module.SCHEDULER_CONFIG,
            unit_dir=custom,
            daemon_reload=True,
            enable=True,
        )


def test_explicit_install_activation_uses_only_timer_enable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_explicit_activation")
    unit_dir = tmp_path / "user-units"
    _stub_admission(module, monkeypatch)
    monkeypatch.setattr(module, "_default_unit_dir", lambda: unit_dir)
    actions: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        module,
        "_systemctl_action",
        lambda _capability, *arguments: actions.append(tuple(arguments)),
    )

    result = module.install(
        module.SCHEDULER_CONFIG,
        unit_dir=unit_dir,
        daemon_reload=True,
        enable=True,
    )

    assert actions == [
        ("daemon-reload",),
        ("enable", "--now", module.TIMER_NAME),
    ]
    assert result["timer_enabled_and_started"] is True
    assert all(module.SERVICE_NAME not in action for action in actions)


def test_user_systemd_probe_avoids_environment_dump_and_requires_linger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_capability_probe")
    monkeypatch.setattr(
        module,
        "_resolve_executable",
        lambda name, *, capability: Path(f"/usr/bin/{name}"),
    )
    monkeypatch.setattr(
        module,
        "_subprocess_environment",
        lambda *, systemd: {"PATH": "/usr/bin:/bin"},
    )
    calls: list[tuple[str, ...]] = []

    def run(argv, **_kwargs):
        calls.append(tuple(argv))
        if argv[0].endswith("systemctl"):
            return subprocess.CompletedProcess(argv, 0, stdout=b"running\n", stderr=b"")
        return subprocess.CompletedProcess(argv, 0, stdout=b"no\n", stderr=b"")

    monkeypatch.setattr(module, "_run_process", run)

    with pytest.raises(module.UserSystemdUnavailable, match="linger_not_enabled"):
        module._require_user_systemd()

    assert all("show-environment" not in call for call in calls)
    assert calls[0][-1] == "is-system-running"
    assert calls[1][-2:] == ("--property=Linger", "--value")


def test_typed_unavailable_cli_has_no_write_or_secret_echo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load("pctdd_systemd_typed_unavailable_cli")
    secret = "private_quack_token_must_not_echo_123"
    monkeypatch.setenv("IPFS_ACCELERATE_AGENT_QUACK_TOKEN", secret)
    monkeypatch.setattr(module, "_validate_current_controls", lambda _path: _binding())
    monkeypatch.setattr(
        module,
        "_require_user_systemd",
        lambda: (_ for _ in ()).throw(
            module.UserSystemdUnavailable("linger_capability_unavailable")
        ),
    )
    monkeypatch.setattr(
        module,
        "_ensure_unit_dir",
        lambda _path: pytest.fail("typed unavailable must not create units"),
    )

    result = module.main(
        [
            "--config",
            str(module.SCHEDULER_CONFIG),
            "--unit-dir",
            str(tmp_path / "units"),
            "install",
        ]
    )
    captured = capsys.readouterr()

    assert result == 3
    payload = json.loads(captured.err)
    assert payload["terminal"] == "typed_external_capability_unavailable"
    assert payload["reason_code"] == "linger_capability_unavailable"
    assert payload["external_writes"] is False
    assert secret not in captured.err
    assert secret not in captured.out


def test_systemctl_child_environment_scrubs_quack_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_scrubbed_action_environment")
    secret = "private_quack_token_action_123"
    monkeypatch.setenv("IPFS_ACCELERATE_AGENT_QUACK_TOKEN", secret)
    monkeypatch.setenv("PCTDD_QUACK_TOKEN", secret)
    monkeypatch.setenv("HOME", "/attacker/home")
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/attacker/runtime")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/attacker/bus")
    monkeypatch.setattr(
        module.pwd,
        "getpwuid",
        lambda _uid: SimpleNamespace(pw_dir="/home/exact-user"),
    )

    def lstat(path: Path):
        mode = stat.S_IFSOCK | 0o600 if str(path).endswith("/bus") else stat.S_IFDIR | 0o700
        return SimpleNamespace(st_mode=mode, st_uid=os.geteuid())

    monkeypatch.setattr(module.os, "lstat", lstat)
    environment = module._subprocess_environment(systemd=True)
    capability = _capability()
    capability["_environment"] = environment
    captured: dict[str, object] = {}

    def run(argv, **kwargs):
        captured["argv"] = tuple(argv)
        captured["environment"] = dict(kwargs["env"])
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(module.subprocess, "run", run)
    module._systemctl_action(capability, "daemon-reload")

    assert captured["argv"] == (
        "/usr/bin/systemctl",
        "--user",
        "--no-pager",
        "daemon-reload",
    )
    environment = captured["environment"]
    assert isinstance(environment, dict)
    assert "IPFS_ACCELERATE_AGENT_QUACK_TOKEN" not in environment
    assert "PCTDD_QUACK_TOKEN" not in environment
    assert environment["HOME"] == "/home/exact-user"
    assert environment["XDG_RUNTIME_DIR"] == f"/run/user/{os.getuid()}"
    assert environment["DBUS_SESSION_BUS_ADDRESS"] == (
        f"unix:path=/run/user/{os.getuid()}/bus"
    )
    assert secret not in json.dumps(environment, sort_keys=True)


def test_child_environment_does_not_iterate_unrelated_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_environment_name_allowlist")

    class Environment:
        def get(self, name: str, default=None):
            values = {
                "LANG": "C.UTF-8",
                "IPFS_ACCELERATE_AGENT_QUACK_TOKEN": "must-never-be-read",
            }
            return values.get(name, default)

        def items(self):
            pytest.fail("credential-bearing environment must not be iterated")

    monkeypatch.setattr(module, "os", SimpleNamespace(environ=Environment()))

    assert module._subprocess_environment(systemd=False) == {
        "LANG": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def test_uninstall_refuses_unknown_content_before_disable_or_removal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_unknown_uninstall")
    unit_dir = tmp_path / "user-units"
    unit_dir.mkdir(mode=0o700)
    service = unit_dir / module.SERVICE_NAME
    service.write_text("unrecognized\n", encoding="utf-8")
    service.chmod(0o600)
    _stub_admission(module, monkeypatch)
    monkeypatch.setattr(module, "_default_unit_dir", lambda: unit_dir)
    monkeypatch.setattr(
        module,
        "_systemctl_action",
        lambda *_args: pytest.fail("unknown content must block disable/reload"),
    )

    with pytest.raises(module.EnsureError, match="unrecognized_existing_unit_content"):
        module.uninstall(
            module.SCHEDULER_CONFIG,
            unit_dir=unit_dir,
            daemon_reload=True,
            disable=True,
        )

    assert service.read_text(encoding="utf-8") == "unrecognized\n"


def test_clean_uninstall_disables_timer_then_removes_only_exact_units(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_clean_uninstall")
    unit_dir = tmp_path / "user-units"
    unrelated = unit_dir / "unrelated.service"
    _stub_admission(module, monkeypatch)
    module.install(
        module.SCHEDULER_CONFIG,
        unit_dir=unit_dir,
        daemon_reload=False,
        enable=False,
    )
    unrelated.write_text("keep\n", encoding="utf-8")
    monkeypatch.setattr(module, "_default_unit_dir", lambda: unit_dir)
    actions: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        module,
        "_systemctl_action",
        lambda _capability, *arguments: actions.append(tuple(arguments)),
    )

    result = module.uninstall(
        module.SCHEDULER_CONFIG,
        unit_dir=unit_dir,
        daemon_reload=True,
        disable=True,
    )

    assert actions == [
        ("disable", "--now", module.TIMER_NAME),
        ("daemon-reload",),
    ]
    assert result["removed"] == sorted([module.SERVICE_NAME, module.TIMER_NAME])
    assert result["timer_disabled_and_stopped"] is True
    assert not (unit_dir / module.SERVICE_NAME).exists()
    assert not (unit_dir / module.TIMER_NAME).exists()
    assert unrelated.read_text(encoding="utf-8") == "keep\n"


def test_disable_refuses_incomplete_exact_pair_without_systemctl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_incomplete_disable")
    unit_dir = tmp_path / "user-units"
    unit_dir.mkdir(mode=0o700)
    units = module._render_units()
    service = unit_dir / module.SERVICE_NAME
    service.write_bytes(units[module.SERVICE_NAME])
    service.chmod(0o600)
    _stub_admission(module, monkeypatch)
    monkeypatch.setattr(module, "_default_unit_dir", lambda: unit_dir)
    monkeypatch.setattr(
        module,
        "_systemctl_action",
        lambda *_args: pytest.fail("partial unit pair must not touch systemd"),
    )

    with pytest.raises(module.EnsureError, match="complete_exact_unit_pair"):
        module.uninstall(
            module.SCHEDULER_CONFIG,
            unit_dir=unit_dir,
            daemon_reload=True,
            disable=True,
        )

    assert service.is_file()
    assert not (unit_dir / module.TIMER_NAME).exists()


def test_uninstall_of_absent_directory_is_idempotent_and_has_no_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("pctdd_systemd_absent_uninstall")
    unit_dir = tmp_path / "missing-units"
    _stub_admission(module, monkeypatch)
    monkeypatch.setattr(
        module,
        "_systemctl_action",
        lambda *_args: pytest.fail("absent exact units grant no systemctl authority"),
    )

    result = module.uninstall(
        module.SCHEDULER_CONFIG,
        unit_dir=unit_dir,
        daemon_reload=False,
        disable=False,
    )

    assert result["removed"] == []
    assert result["already_absent"] == sorted(
        [module.SERVICE_NAME, module.TIMER_NAME]
    )
    assert not unit_dir.exists()
