"""Closed old-timer migration and explicit timer-only activation rearm."""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
NATIVE_ROOT = "/home/barberb/lift_coding/.worktrees/pctdd-g9-orphan-recovery"


def load():
    path = (
        ROOT
        / "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_user_systemd.py"
    )
    spec = importlib.util.spec_from_file_location("native_timer_anchor_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_units(module):
    """Render the exact namespace already bound by the legacy service SHA.

    Test installation stays in a private tmp directory with systemctl mocked.
    We preserve the production SHA check; rebasing test render paths is a fixture
    for that exact native namespace, not an alternate accepted runtime scope.
    """
    units = module._render_units()
    units[module.SERVICE_NAME] = (
        units[module.SERVICE_NAME]
        .replace(str(module.ROOT).encode(), NATIVE_ROOT.encode())
        .replace(str(module._python_executable()).encode(), b"/usr/bin/python3.12")
    )
    return units


@pytest.fixture
def installer(tmp_path, monkeypatch):
    module = load()
    units = canonical_units(module)
    unit_dir = tmp_path / "user-units"
    binding = {
        "source_head": "1" * 40,
        "source_tree": "2" * 40,
        "configuration_root": "sha256:" + "3" * 64,
        "control_roots": {},
    }
    capability = {"manager_state": "running", "linger_enabled": True}
    monkeypatch.setattr(module, "_validate_current_controls", lambda path: dict(binding))
    monkeypatch.setattr(module, "_require_user_systemd", lambda: capability)
    monkeypatch.setattr(module, "_render_units", lambda: dict(units))
    monkeypatch.setattr(module, "_default_unit_dir", lambda: unit_dir)
    actions = []
    monkeypatch.setattr(module, "_systemctl_action", lambda capability, *args: actions.append(args))
    return module, units, unit_dir, actions, binding


def test_new_timer_has_one_activation_bootstrap_and_existing_recurring_interval():
    module = load()
    timer = module._render_units()[module.TIMER_NAME].decode()
    assert [line for line in timer.splitlines() if line.startswith("On")] == [
        "OnActiveSec=3min",
        "OnUnitActiveSec=10min",
    ]
    assert "OnBootSec=" not in timer
    assert "Unit=" + module.SERVICE_NAME in timer


def test_migration_requires_exact_previous_timer_and_native_service_namespace():
    module = load()
    units = canonical_units(module)
    old = module._migratable_unit_payloads(units)
    previous = old[module.TIMER_NAME][0]
    assert hashlib.sha256(previous).hexdigest() == module.LEGACY_TIMER_SHA256
    assert b"OnBootSec=3min\n" in previous and b"OnActiveSec=" not in previous
    assert (
        hashlib.sha256(old[module.SERVICE_NAME][0]).hexdigest()
        == "b153a19680f7c700d07ccc87bafc2bd587911a0dbd60c8cea6128eea3c9d2ee8"
    )


@pytest.mark.parametrize(
    "change",
    [
        b"OnCalendar=*:0/1\n",
        b"OnActiveSec=1s\n",
        b"Unit=foreign.service\n",
        b"# unknown revision\n",
    ],
)
def test_changed_timer_cannot_be_derived_into_known_predecessor(change):
    module = load()
    units = canonical_units(module)
    units[module.TIMER_NAME] += change
    with pytest.raises(module.EnsureError):
        module._migratable_unit_payloads(units)


@pytest.mark.parametrize(
    "directive", ["OnBootSec=3min", "OnActiveSec=3min", "OnCalendar=*:0/1", "OnUnitInactiveSec=1s"]
)
def test_renderer_rejects_extra_or_duplicate_timer_schedule(tmp_path, monkeypatch, directive):
    module = load()
    path = tmp_path / "timer"
    path.write_text(module.TIMER_TEMPLATE.read_text() + directive + "\n")
    monkeypatch.setattr(module, "TIMER_TEMPLATE", path)
    with pytest.raises(module.EnsureError, match="timer_template_policy_invalid"):
        module._render_units()


def test_exact_old_timer_upgrades_under_existing_atomic_installer(installer):
    module, units, directory, actions, binding = installer
    directory.mkdir(mode=0o700)
    old = module._migratable_unit_payloads(units)
    for name, payload in units.items():
        path = directory / name
        path.write_bytes(old[name][0] if name == module.TIMER_NAME else payload)
        path.chmod(0o600)
    result = module.install(
        module.SCHEDULER_CONFIG, unit_dir=directory, daemon_reload=False, enable=False
    )
    assert result["upgraded_from_sealed_predecessor"] == [module.TIMER_NAME]
    assert (directory / module.TIMER_NAME).read_bytes() == units[module.TIMER_NAME]
    assert result["timer_activation_anchor_rearmed"] is False and actions == []


def test_foreign_old_timer_preserves_all_existing_unit_bytes(installer):
    module, units, directory, actions, binding = installer
    directory.mkdir(mode=0o700)
    for name, payload in units.items():
        path = directory / name
        path.write_bytes(
            payload if name == module.SERVICE_NAME else b"[Timer]\nUnit=foreign.service\n"
        )
        path.chmod(0o600)
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(module.EnsureError):
        module.install(
            module.SCHEDULER_CONFIG, unit_dir=directory, daemon_reload=False, enable=False
        )
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before and actions == []


def test_enable_rearms_only_timer_after_current_control_revalidation(installer):
    module, units, directory, actions, binding = installer
    result = module.install(
        module.SCHEDULER_CONFIG, unit_dir=directory, daemon_reload=True, enable=True
    )
    assert actions == [
        ("daemon-reload",),
        ("enable", "--now", module.TIMER_NAME),
        ("restart", module.TIMER_NAME),
    ]
    assert result["timer_activation_anchor_rearmed"] is True
    assert all(module.SERVICE_NAME not in action for action in actions)


def test_changed_source_before_rearm_prevents_restart(installer, monkeypatch):
    module, units, directory, actions, binding = installer
    calls = 0

    def changed(path):
        nonlocal calls
        calls += 1
        return {**binding, "source_tree": "4" * 40} if calls >= 3 else dict(binding)

    monkeypatch.setattr(module, "_validate_current_controls", changed)
    with pytest.raises(module.EnsureError):
        module.install(module.SCHEDULER_CONFIG, unit_dir=directory, daemon_reload=True, enable=True)
    assert ("restart", module.TIMER_NAME) not in actions
    assert all(module.SERVICE_NAME not in action for action in actions)


def test_activation_still_requires_explicit_daemon_reload(installer):
    module, units, directory, actions, binding = installer
    with pytest.raises(module.EnsureError, match="enable_requires_explicit_daemon_reload"):
        module.install(
            module.SCHEDULER_CONFIG, unit_dir=directory, daemon_reload=False, enable=True
        )
    assert not directory.exists() and actions == []


def test_actual_systemd_parser_accepts_activation_bootstrap_units(tmp_path):
    module = load()
    units = canonical_units(module)
    for name, payload in units.items():
        (tmp_path / name).write_bytes(payload)
    result = subprocess.run(
        ["/usr/bin/systemd-analyze", "--user", "verify", *[str(tmp_path / name) for name in units]],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
