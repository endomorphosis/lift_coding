"""PCCE r6 operator keeps the Quack owner vault for remaining board drain."""

from __future__ import annotations

import importlib.util
from pathlib import Path

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
