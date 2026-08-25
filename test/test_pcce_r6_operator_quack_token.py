"""PCCE r6 operator keeps the Quack owner vault for remaining board drain."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPERATOR = ROOT / "scripts" / "run_agent_supervisor_proof_carrying_context_engine.py"


def _load_operator():
    spec = importlib.util.spec_from_file_location("pcce_r6_operator", OPERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launch_helper_retains_owner_token_vault(tmp_path: Path) -> None:
    operator = _load_operator()
    vault = tmp_path / "env___IPFS_ACCELERATE_AGENT_QUACK_TOKEN.quack-token"
    vault.write_text("liveTok_value1234567890\n", encoding="utf-8")
    vault.chmod(0o600)

    def launch(args):
        assert args == ["launch", "--implement"]
        assert vault.is_file()
        return 0

    result = operator._launch_with_retained_owner_token(
        launch,
        ["launch", "--implement"],
        token_path=vault,
    )
    assert result == 0
    assert vault.is_file()
    assert vault.read_text(encoding="utf-8").strip() == "liveTok_value1234567890"


def test_launch_helper_refuses_missing_vault(tmp_path: Path) -> None:
    operator = _load_operator()
    vault = tmp_path / "missing.quack-token"

    def launch(_args):
        raise AssertionError("launch must not run without a vault")

    try:
        operator._launch_with_retained_owner_token(
            launch,
            ["launch"],
            token_path=vault,
        )
    except operator.OperatorError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("expected OperatorError")


def _configure_owner_env(operator, tmp_path: Path, monkeypatch) -> Path:
    class _Program:
        endpoint_secret_handle = "env://IPFS_ACCELERATE_AGENT_QUACK_TOKEN"

    class _Board:
        @staticmethod
        def resolved_database_program():
            return _Program()

    monkeypatch.setattr(
        operator,
        "_load_config",
        lambda _config_path: (_Board(), object()),
    )
    monkeypatch.setattr(
        operator,
        "_runtime_paths",
        lambda _board: {"owner": tmp_path},
    )
    return tmp_path / "env___IPFS_ACCELERATE_AGENT_QUACK_TOKEN.quack-token"


def test_owner_python_env_reuses_inherited_token_after_recycle_removes_vault(
    tmp_path: Path,
    monkeypatch,
) -> None:
    operator = _load_operator()
    vault = _configure_owner_env(operator, tmp_path, monkeypatch)
    token = "liveTok_value1234567890"
    vault.write_text(f"{token}\n", encoding="utf-8")
    vault.chmod(0o600)

    first_child_env = operator._owner_python_env(tmp_path / "config.json")
    assert first_child_env["IPFS_ACCELERATE_AGENT_QUACK_TOKEN"] == token

    # The detached watch inherits the first launch environment.  A graceful
    # state-owner stop destroys its generation-local vault before the watch
    # starts the replacement child.
    monkeypatch.setenv("IPFS_ACCELERATE_AGENT_QUACK_TOKEN", token)
    vault.unlink()
    replacement_env = operator._owner_python_env(tmp_path / "config.json")

    assert replacement_env["IPFS_ACCELERATE_AGENT_QUACK_TOKEN"] == token
    assert replacement_env["IPFS_ACCELERATE_AGENT_QUACK_TOKEN_FILE"] == str(vault)
    assert not vault.exists()


def test_owner_python_env_prefers_new_vault_over_stale_inherited_token(
    tmp_path: Path,
    monkeypatch,
) -> None:
    operator = _load_operator()
    vault = _configure_owner_env(operator, tmp_path, monkeypatch)
    vault.write_text("newGeneration_token123456\n", encoding="utf-8")
    vault.chmod(0o600)
    monkeypatch.setenv(
        "IPFS_ACCELERATE_AGENT_QUACK_TOKEN",
        "staleGeneration_token123456",
    )

    child_env = operator._owner_python_env(tmp_path / "config.json")

    assert (
        child_env["IPFS_ACCELERATE_AGENT_QUACK_TOKEN"]
        == "newGeneration_token123456"
    )
    assert child_env["IPFS_ACCELERATE_AGENT_QUACK_TOKEN_FILE"] == str(vault)


def test_owner_python_env_rejects_missing_vault_without_inherited_token(
    tmp_path: Path,
    monkeypatch,
) -> None:
    operator = _load_operator()
    vault = _configure_owner_env(operator, tmp_path, monkeypatch)
    monkeypatch.delenv("IPFS_ACCELERATE_AGENT_QUACK_TOKEN", raising=False)
    monkeypatch.delenv("IPFS_ACCELERATE_AGENT_QUACK_TOKEN_FILE", raising=False)

    with pytest.raises(operator.OperatorError, match="credential is unavailable"):
        operator._owner_python_env(tmp_path / "config.json")

    assert not vault.exists()


def test_serve_loop_does_not_execute_dml_on_listen_handle(tmp_path: Path) -> None:
    operator = _load_operator()
    inbox = tmp_path / "mutations"
    inbox.mkdir()
    request = inbox / "abc.request.json"
    request.write_text(
        '{"sql":"UPDATE tasks SET status = \'retrying\'","parameters":null}\n',
        encoding="utf-8",
    )

    class _Boom:
        def execute(self, *_args, **_kwargs):
            raise AssertionError("listen handle must not run owner DML")

    operator._process_owner_commands(
        _Boom(),
        inbox,
        token="",
        expected_store_id="store",
        expected_store_generation="gen",
        exclusive_writer=False,
    )
    assert request.is_file()
    assert (inbox / "board-unstall.bounce").is_file()
    assert list(inbox.glob("*.done.json")) == []
