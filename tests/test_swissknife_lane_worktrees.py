from __future__ import annotations

import json
import re
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import swissknife_lane_worktrees as lanes  # noqa: E402


def _successful_receipt(node: str = "/portable/node-v22.12.0/bin/node") -> dict[str, object]:
    return {
        "schema": lanes.BROWSER_TOOLCHAIN_RECEIPT_SCHEMA,
        "ok": True,
        "node": {
            "executable": node,
            "resolvedExecutable": node,
            "semanticVersion": "22.12.0",
        },
        "packageManager": {
            "name": "npm",
            "semanticVersion": "10.9.0",
        },
        "lockfile": {"fingerprint": f"sha256:{'a' * 64}"},
    }


def _lane_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> lanes.Lane:
    repo = tmp_path / "repository"
    repo.mkdir()
    monkeypatch.setattr(lanes, "REPO_ROOT", repo)
    lane = lanes.Lane("test")
    lane.swissknife_path.mkdir(parents=True)
    (lane.swissknife_path / "scripts").mkdir()
    (lane.swissknife_path / lanes.BROWSER_TOOLCHAIN_VERIFIER).touch()
    return lane


def _shared_dependencies(repo: Path) -> Path:
    dependencies = repo / "swissknife" / "node_modules"
    dependencies.mkdir(parents=True)
    (dependencies / ".installed").write_text("ready\n", encoding="utf-8")
    return dependencies


def _successful_resolution(lane: lanes.Lane, name: str) -> lanes.BrowserToolchainResolution:
    receipt_path = lane.path / lanes.BROWSER_TOOLCHAIN_RECEIPT_DIR / f"{name}.json"
    return lanes.BrowserToolchainResolution(
        node_executable=Path("/portable/node-v22.12.0/bin/node"),
        receipt_path=receipt_path,
        receipt=_successful_receipt(),
    )


def test_verifier_uses_absolute_path_node_and_persists_fresh_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane = _lane_checkout(tmp_path, monkeypatch)
    node = "/portable/node-v22.12.0/bin/node"
    monkeypatch.setattr(lanes.shutil, "which", lambda executable: node)
    commands: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        receipt_path = Path(command[command.index("--receipt") + 1])
        receipt_path.write_text(
            json.dumps(_successful_receipt(node)),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="verified", stderr="")

    monkeypatch.setattr(lanes.subprocess, "run", fake_run)

    resolution = lanes.verify_browser_toolchain(lane, receipt_name="lane-startup")

    assert commands == [
        [
            node,
            "scripts/verify-browser-toolchain.mjs",
            "--check-node-executable",
            node,
            "--receipt",
            str(lane.path / "tmp/browser-validation-toolchain/lane-startup.json"),
        ]
    ]
    assert resolution.receipt["packageManager"] == {
        "name": "npm",
        "semanticVersion": "10.9.0",
    }


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("schema", "schema is missing or unsupported"),
        ("executable", "does not match the selected runtime"),
        ("node-version", "Node semantic version is missing or invalid"),
        ("package-manager", "npm identity is missing"),
        ("npm-version", "npm semantic version is missing or invalid"),
        ("fingerprint", "lockfile fingerprint is missing or invalid"),
    ],
)
def test_verifier_rejects_incomplete_or_unrelated_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    expected_error: str,
) -> None:
    lane = _lane_checkout(tmp_path, monkeypatch)
    node = "/portable/node-v22.12.0/bin/node"
    monkeypatch.setattr(lanes.shutil, "which", lambda executable: node)
    receipt = _successful_receipt(node)
    if mutation == "schema":
        receipt["schema"] = "unrelated.v1"
    elif mutation == "executable":
        receipt["node"]["resolvedExecutable"] = "/portable/node-v20.19.0/bin/node"  # type: ignore[index]
    elif mutation == "node-version":
        receipt["node"]["semanticVersion"] = "22.x"  # type: ignore[index]
    elif mutation == "package-manager":
        receipt.pop("packageManager")
    elif mutation == "npm-version":
        receipt["packageManager"]["semanticVersion"] = "latest"  # type: ignore[index]
    else:
        receipt["lockfile"]["fingerprint"] = "sha256:short"  # type: ignore[index]

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        receipt_path = Path(command[command.index("--receipt") + 1])
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="verified", stderr="")

    monkeypatch.setattr(lanes.subprocess, "run", fake_run)

    with pytest.raises(lanes.LaneError, match=expected_error):
        lanes.verify_browser_toolchain(lane, receipt_name="lane-startup")


def test_verifier_fails_closed_when_node_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane = _lane_checkout(tmp_path, monkeypatch)
    monkeypatch.setattr(lanes.shutil, "which", lambda executable: None)

    with pytest.raises(lanes.LaneError, match="requires Node on PATH"):
        lanes.verify_browser_toolchain(lane, receipt_name="lane-startup")


def test_validation_verifies_before_running_in_a_non_login_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane = _lane_checkout(tmp_path, monkeypatch)
    _shared_dependencies(lanes.REPO_ROOT)
    events: list[str] = []

    def fake_verify(
        selected_lane: lanes.Lane, *, receipt_name: str
    ) -> lanes.BrowserToolchainResolution:
        assert selected_lane == lane
        assert receipt_name == "clean-checkout-validation"
        events.append("verify")
        return _successful_resolution(lane, receipt_name)

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        events.append("validation")
        assert command == ["bash", "--noprofile", "--norc", "-c", "npm run build:web"]
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        assert environment["PATH"].split(lanes.os.pathsep)[0] == "/portable/node-v22.12.0/bin"
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(lanes, "verify_browser_toolchain", fake_verify)
    monkeypatch.setattr(lanes.subprocess, "run", fake_run)

    result = lanes.run_validation_command(lane, "npm run build:web")

    assert events == ["verify", "validation"]
    assert result.receipt["ok"] is True


def test_validation_command_cannot_run_after_toolchain_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane = _lane_checkout(tmp_path, monkeypatch)
    _shared_dependencies(lanes.REPO_ROOT)

    def reject_toolchain(
        selected_lane: lanes.Lane, *, receipt_name: str
    ) -> lanes.BrowserToolchainResolution:
        raise lanes.LaneError("unsupported Node 18.19.1")

    monkeypatch.setattr(lanes, "verify_browser_toolchain", reject_toolchain)
    monkeypatch.setattr(
        lanes.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("validation ran before toolchain approval"),
    )

    with pytest.raises(lanes.LaneError, match="unsupported Node"):
        lanes.run_validation_command(lane, "npm run test:browser-compat")


def test_lane_startup_runs_shared_toolchain_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane = _lane_checkout(tmp_path, monkeypatch)
    shared_dependencies = _shared_dependencies(lanes.REPO_ROOT)
    (lane.path / ".git").mkdir()
    (lane.swissknife_path / ".git").mkdir()
    monkeypatch.setattr(lanes, "configure_local_submodule_sources", lambda selected_lane: None)
    monkeypatch.setattr(lanes, "working_tree_clean", lambda path: True)
    monkeypatch.setattr(lanes, "git_ref_exists", lambda ref, cwd: False)
    monkeypatch.setattr(lanes, "git", lambda args, cwd=lanes.REPO_ROOT: "abc123")
    receipt = _successful_resolution(lane, "lane-startup")
    calls: list[tuple[lanes.Lane, str]] = []

    def fake_verify(
        selected_lane: lanes.Lane, *, receipt_name: str
    ) -> lanes.BrowserToolchainResolution:
        calls.append((selected_lane, receipt_name))
        return receipt

    monkeypatch.setattr(lanes, "verify_browser_toolchain", fake_verify)

    result = lanes.ensure_lane(lane, dry_run=False)

    assert calls == [(lane, "lane-startup")]
    assert result["browser_toolchain_receipt"] == str(receipt.receipt_path)
    assert result["browser_toolchain"] == receipt.receipt
    assert result["shared_dependency_paths"] == ["swissknife/node_modules"]
    assert lane.swissknife_path.joinpath("node_modules").is_symlink()
    assert lane.swissknife_path.joinpath("node_modules").resolve() == shared_dependencies.resolve()


def test_lane_dependencies_replace_stale_targets_and_skip_missing_optional_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane = _lane_checkout(tmp_path, monkeypatch)
    shared_dependencies = _shared_dependencies(lanes.REPO_ROOT)
    stale_target = lane.swissknife_path / "node_modules"
    stale_target.mkdir()
    (stale_target / "stale").write_text("remove me\n", encoding="utf-8")

    linked = lanes.link_shared_swissknife_dependencies(lane)

    assert linked == ["swissknife/node_modules"]
    assert stale_target.is_symlink()
    assert stale_target.resolve() == shared_dependencies.resolve()
    assert (stale_target / ".installed").read_text(encoding="utf-8") == "ready\n"


def test_lane_startup_fails_early_when_required_dependencies_are_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane = _lane_checkout(tmp_path, monkeypatch)

    with pytest.raises(lanes.LaneError, match="run npm ci"):
        lanes.link_shared_swissknife_dependencies(lane)


def test_merge_dry_run_requires_and_reports_toolchain_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane = _lane_checkout(tmp_path, monkeypatch)
    _shared_dependencies(lanes.REPO_ROOT)
    receipt = _successful_resolution(lane, "clean-checkout-validation")
    calls: list[str] = []
    monkeypatch.setattr(lanes, "integration_lock", nullcontext)
    monkeypatch.setattr(lanes, "validate_lane", lambda selected_lane: None)
    monkeypatch.setattr(lanes, "working_tree_clean", lambda path: True)

    def fake_verify(
        selected_lane: lanes.Lane, *, receipt_name: str
    ) -> lanes.BrowserToolchainResolution:
        calls.append(receipt_name)
        return receipt

    monkeypatch.setattr(lanes, "verify_browser_toolchain", fake_verify)

    result = lanes.merge_lane(lane, validation_command="npm run build:web", apply=False)

    assert calls == ["clean-checkout-validation"]
    assert result["validated"] is True
    assert result["browser_toolchain_receipt"] == str(receipt.receipt_path)
    assert result["browser_toolchain"] == receipt.receipt


def test_clean_checkout_workflows_verify_the_shared_toolchain_immediately_after_setup() -> None:
    repository = Path(__file__).resolve().parents[1]
    workflow_setup_counts = {
        "swissknife/.github/workflows/auto-heal-failed-workflows.yml": 1,
        "swissknife/.github/workflows/cd.yml": 3,
        "swissknife/.github/workflows/ci-robust.yml": 3,
        "swissknife/.github/workflows/ci.yml": 5,
        "swissknife/.github/workflows/documentation-automation.yml": 1,
        "swissknife/.github/workflows/multi-arch-build.yml": 1,
        "swissknife/.github/workflows/npm-publish.yml": 1,
        "swissknife/.github/workflows/production-deployment.yml": 3,
        "swissknife/.github/workflows/release-readiness-gates.yml": 1,
        "swissknife/.github/workflows/release.yml": 4,
        "swissknife/.github/workflows/self-hosted-arm64.yml": 1,
        "swissknife/.github/workflows/sonarqube.yml": 1,
        "swissknife/.github/workflows/test-auto-heal-example.yml": 1,
        "swissknife/.github/workflows/test.yml": 3,
        "swissknife/.github/workflows/version-bump.yml": 1,
        "swissknife/.github/workflows/wasm-prover-gates.yml": 1,
        ".github/workflows/logic-conformance.yml": 1,
    }

    for relative_path, expected_setup_count in workflow_setup_counts.items():
        source = (repository / relative_path).read_text(encoding="utf-8")
        setup_offsets = [
            match.start() for match in re.finditer(r"uses:\s*actions/setup-node@", source)
        ]
        assert len(setup_offsets) == expected_setup_count, relative_path
        assert source.count("verify-browser-toolchain.mjs") == expected_setup_count, relative_path
        assert not re.search(r"node-version:\s*['\"]?18(?:\D|$)", source), relative_path
        assert not re.search(r"node-version:\s*['\"]?20\.x", source), relative_path

        for offset in setup_offsets:
            next_named_step = re.search(r"\n[ \t]*- name:[ \t]*([^\n]+)", source[offset:])
            assert next_named_step is not None, relative_path
            assert "Verify" in next_named_step.group(1), relative_path
            step_start = offset + next_named_step.start()
            following_named_step = re.search(r"\n[ \t]*- name:[ \t]*", source[step_start + 1 :])
            step_end = (
                step_start + 1 + following_named_step.start()
                if following_named_step
                else len(source)
            )
            verifier_step = source[step_start:step_end]
            assert "node scripts/verify-browser-toolchain.mjs --receipt" in verifier_step, (
                relative_path
            )
