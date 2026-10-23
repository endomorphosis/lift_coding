"""The optional retrieval codec crosses real argument boundaries safely.

Deployment and providers are mocked. The coding boundary case independently
replays a real public five-hit native index while stubbing signed-source and
semantic admission loaders; it does not claim live admission or provider use.
"""
import asyncio
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
from types import SimpleNamespace

import pytest
from harbor.models.agent.context import AgentContext

from benchmarks.agent_supervisor.container_coding import full_supervisor_benchmark as benchmark
from benchmarks.agent_supervisor.container_coding import full_supervisor_harbor_agent as adapter
from benchmarks.agent_supervisor.container_coding import terminal_container_supervisor as driver
from benchmarks.agent_supervisor.container_coding.terminal_doctor_dispatch import implementation_argv
from benchmarks.agent_supervisor.container_coding.test_terminal_instruction_delivery import PINS, dispatch
from ipfs_accelerate_py.agent_supervisor.runtime import router_implementation_runner as runner


@pytest.mark.parametrize("mode,arm,semantic,retrieval", [
    ("unknown", "full", "native", "full"), (None, "full", "native", "full"),
    (True, "full", "native", "full"), (1, "full", "native", "full"),
    ([], "full", "native", "full"), ({}, "full", "native", "full"),
    ("compact", "no-index", "identifiers", "full"),
    ("compact", "full", "identifiers", "full"), ("compact", "full", "native", "frontier"),
])
def test_invalid_codec_refuses_before_config_archive_logs_state_or_owner(tmp_path, monkeypatch, mode, arm, semantic, retrieval):
    monkeypatch.setattr(benchmark, "baseline_config", lambda *_: pytest.fail("invalid selection built config"))
    monkeypatch.setattr(driver.os, "geteuid", lambda: pytest.fail("invalid selection accessed owner"))
    selection = dict(code_retrieval_codec=mode, semantic_transport=semantic, code_retrieval_transport=retrieval)
    with pytest.raises(ValueError, match="code retrieval codec"):
        benchmark.config_for(tmp_path / "dataset", tmp_path / "output", tmp_path / "archive", arm, **selection)
    with pytest.raises(ValueError, match="code retrieval codec"):
        benchmark.prepare(dataset=tmp_path / "dataset", output=tmp_path / "output", archive=tmp_path / "archive", arm=arm, **selection)
    with pytest.raises(ValueError, match="code retrieval codec"):
        adapter.FullSupervisorAgent(logs_dir=tmp_path / "logs", model_name="pinned", runtime_archive=str(tmp_path / "archive"), arm=arm, **selection)
    with pytest.raises(ValueError, match="code retrieval codec"):
        driver.run(instruction=tmp_path / "source.md", state=tmp_path / "uncreated/state", arm=arm, **selection)
    assert not any((tmp_path / name).exists() for name in ("output", "logs", "uncreated"))


@pytest.mark.parametrize("mode", ["expanded", "compact"])
def test_real_host_prepare_persists_codec_selection_and_existing_defaults(tmp_path, monkeypatch, mode):
    dataset = tmp_path / "dataset"
    task = dataset / benchmark.TASK
    task.mkdir(parents=True)
    instruction = task / "instruction.md"
    instruction.write_text("Inspect bottle.py, repair it and write report.jsonl.\n")
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "runtime.tar.gz").write_bytes(b"authored-archive")
    (archive / "manifest.json").write_text(json.dumps({"archive_sha256": benchmark._hash(archive / "runtime.tar.gz")}))
    calls = []
    monkeypatch.setattr(benchmark, "_task_hashes", lambda *_: {"instruction.md": benchmark._hash(instruction)})
    monkeypatch.setattr(benchmark.subprocess, "run", lambda argv, **_: calls.append(argv) or SimpleNamespace(returncode=0, stdout="fixture", stderr=""))
    output = tmp_path / "prepared"
    receipt = benchmark.prepare(dataset=dataset, output=output, archive=archive, arm="full", semantic_transport="native", code_retrieval_codec=mode)
    kwargs = json.loads((output / "config.json").read_text())["agents"][0]["kwargs"]
    assert receipt["prepared"] is True and receipt["provider_calls"] == 0 and len(calls) == 1
    assert receipt["code_retrieval_codec"] == kwargs["code_retrieval_codec"] == mode
    assert kwargs["semantic_transport"] == "native" and kwargs["code_retrieval_transport"] == "full"
    assert kwargs["doctor_profile"] == "header-contract" and kwargs["intent_requirements_transport"] == "expanded"


def test_collect_retains_codec_detects_drift_and_defaults_legacy(tmp_path, monkeypatch):
    config = benchmark.config_for(Path("/dataset"), tmp_path, Path("/archive"), "full", semantic_transport="native", code_retrieval_codec="compact")
    prepared = dict(arm="full", dataset="/dataset", task_input_sha256={}, semantic_transport="native", code_retrieval_codec="compact")
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "preparation.json").write_text(json.dumps(prepared))
    monkeypatch.setattr(benchmark, "_task_hashes", lambda *_: {})
    collected = benchmark.collect(tmp_path)
    assert collected["code_retrieval_codec"] == "compact" and collected["code_retrieval_codec_config_unchanged"] is True
    config["agents"][0]["kwargs"]["code_retrieval_codec"] = "expanded"
    (tmp_path / "config.json").write_text(json.dumps(config))
    assert benchmark.collect(tmp_path)["code_retrieval_codec_config_unchanged"] is False
    config["agents"][0]["kwargs"].pop("code_retrieval_codec")
    prepared.pop("code_retrieval_codec")
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "preparation.json").write_text(json.dumps(prepared))
    legacy = benchmark.collect(tmp_path)
    assert legacy["code_retrieval_codec"] == "expanded" and legacy["code_retrieval_codec_config_unchanged"] is True


@pytest.mark.parametrize("mode", ["expanded", "compact"])
def test_harbor_adapter_command_and_metadata_retain_codec(tmp_path, monkeypatch, mode):
    commands = []
    async def observe(*_): return {"status": "fixture"}
    monkeypatch.setattr(adapter, "capture_public_inputs", observe)
    monkeypatch.setattr(adapter, "export_public_outputs", observe)
    class Environment:
        async def upload_file(self, source, target): pass
        async def exec(self, **kwargs):
            commands.append(shlex.split(kwargs["command"]))
            return SimpleNamespace(return_code=0, stdout="", stderr="")
        async def download_file(self, source, target): raise FileNotFoundError(source)
    (tmp_path / "manifest.json").write_text(json.dumps({"archive_sha256": "fixture", "learned_requirements": []}))
    agent = adapter.FullSupervisorAgent(logs_dir=tmp_path / "logs", runtime_archive=str(tmp_path), model_name="gpt-5.6-sol", arm="full", semantic_transport="native", code_retrieval_codec=mode)
    context = AgentContext()
    asyncio.run(agent.run("Literal public task", Environment(), context))
    argv = commands[0]
    assert argv[argv.index("--code-retrieval-codec") + 1] == context.metadata["code_retrieval_codec"] == mode
    assert argv[argv.index("--semantic-transport") + 1] == "native"
    assert argv[argv.index("--code-retrieval-transport") + 1] == "full"
    assert argv[argv.index("--timeout-seconds") + 1] == "285"


@pytest.mark.parametrize("mode", [None, "expanded", "compact"])
def test_driver_retains_codec_in_report_and_actual_native_argv(tmp_path, monkeypatch, mode):
    root = tmp_path / "deployment"
    state = root / "state/trial"
    calls = []
    monkeypatch.setattr(driver, "ROOT", root)
    monkeypatch.setattr(driver.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(driver.signal, "signal", lambda *_: None)
    monkeypatch.setattr(driver.signal, "setitimer", lambda *_: None)
    monkeypatch.setattr(driver.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0))
    def prepare(**kwargs):
        state.mkdir(parents=True)
        (state / "admission.json").write_text("{}")
        return {"intent_preplanning": {"status": "fixture"}}
    monkeypatch.setattr(driver.preparation, "prepare", prepare)
    monkeypatch.setattr(driver.preparation, "initial_context", lambda **_: {"provider_calls": 0})
    monkeypatch.setattr(driver.preparation, "plan", lambda **_: {"qualified": True})
    monkeypatch.setattr(driver.preparation, "context", lambda **_: {"context_bundle": {"bound": True}})
    monkeypatch.setattr(driver, "verify_local_benchmark_admission", lambda *_args, **_kwargs: {"graph": SimpleNamespace(tasks=[SimpleNamespace(task_cid="cid:task", task_key="TASK")])})
    monkeypatch.setattr(driver, "prepare_terminal_doctor_dispatch", lambda **_: {"route": "model_router", "status": "residual"})
    def argv(**kwargs):
        calls.append(implementation_argv(**kwargs))
        raise RuntimeError("stop after native argv boundary")
    monkeypatch.setattr(driver, "implementation_argv", argv)
    monkeypatch.setattr(driver, "open_existing_native_owner", lambda **_: pytest.fail("test dispatched native owner"))
    monkeypatch.setattr(driver, "_final_context_audit", lambda *_args, **_kwargs: None)
    selection = {} if mode is None else {"code_retrieval_codec": mode}
    report = driver.run(instruction=tmp_path / "public.md", state=state, arm="full", semantic_transport="native", **selection)
    expected = "expanded" if mode is None else mode
    assert len(calls) == 1 and calls[0][calls[0].index("--code-retrieval-codec") + 1] == expected
    assert report["code_retrieval_codec"] == expected and report["provider_invocations"] == []
    assert report["error"]["message"] == "stop after native argv boundary"
    assert json.loads((state.parent / "trial-result.json").read_text())["code_retrieval_codec"] == expected


@pytest.mark.parametrize("module", [benchmark, driver, runner])
@pytest.mark.parametrize("mode", [None, "compact"])
def test_host_driver_and_runner_cli_forward_default_or_compact(monkeypatch, capsys, module, mode):
    calls = []
    if module is benchmark:
        monkeypatch.setattr(module, "prepare", lambda **kwargs: calls.append(kwargs) or {"prepared": True})
        argv = ["benchmark", "prepare", "--dataset", "/dataset", "--archive", "/archive", "--output", "/output"]
    elif module is driver:
        monkeypatch.setattr(module, "run", lambda **kwargs: calls.append(kwargs) or dict(task_completed=False, arm="full", semantic_transport="native", doctor_profile="header-contract", doctor_profile_experimental=False, seconds=0, provider_invocations=[]))
        argv = ["driver", "--instruction", "/public.md", "--state", "/state", "--arm", "full"]
    else:
        monkeypatch.setattr(module, "run", lambda **kwargs: (calls.append(kwargs) or "fixture", {}))
        monkeypatch.setattr("sys.stdin", SimpleNamespace(buffer=io.BytesIO(b"native-fixture")))
        argv = ["runner", "--provider", "codex_cli", "--model", "pinned"]
    if mode is not None: argv += ["--code-retrieval-codec", mode]
    monkeypatch.setattr("sys.argv", argv)
    module.main()
    assert calls[0]["code_retrieval_codec"] == ("expanded" if mode is None else mode)
    if module is not runner:
        assert calls[0]["code_retrieval_transport"] == "full" and calls[0]["intent_requirements_transport"] == "expanded"
    capsys.readouterr()


@pytest.mark.parametrize("mode", [None, "expanded", "compact"])
def test_codec_crosses_actual_doctor_argv_and_embedded_worker_parser(monkeypatch, mode):
    doctor = {"route": "model_router", "status": "residual"}
    selection = {} if mode is None else {"code_retrieval_codec": mode}
    argv = implementation_argv(router=Path("/router-worker"), model="pinned", reasoning="high", timeout=90,
        semantic_repository=Path("/app"), semantic_transport="native", doctor=doctor, **selection)
    code, calls = dispatch(monkeypatch, [*argv[1:], *PINS])
    expected = "expanded" if mode is None else mode
    assert code == 0 and len(calls) == 1
    forwarded = calls[0]
    assert forwarded[forwarded.index("--code-retrieval-codec") + 1] == expected
    assert forwarded[forwarded.index("--semantic-transport") + 1] == "native"
    assert forwarded[-len(PINS):] == PINS


@pytest.mark.parametrize("extra", [[], ["--semantic-repository", "/app", *PINS],
    ["--semantic-repository", "/app", "--semantic-transport", "native"],
    ["--semantic-repository", "/app", "--semantic-transport", "native", *PINS, "--purpose", "planning"],
    ["--semantic-repository", "/app", "--semantic-transport", "native", *PINS, "--preflight"],
    ["--doctor-candidate-artifact", "/candidate", "--doctor-candidate-sha256", "c" * 64, "--doctor-task-cid", "cid:task"]])
def test_embedded_worker_rejects_unused_compact_before_any_dispatch(monkeypatch, extra):
    code, calls = dispatch(monkeypatch, ["--code-retrieval-codec", "compact", *extra])
    assert code != 0 and calls == []


def test_legacy_worker_no_index_and_doctor_candidate_keep_expanded_default(monkeypatch):
    kwargs = benchmark.config_for(Path("/dataset"), Path("/output"), Path("/archive"), "no-index")["agents"][0]["kwargs"]
    assert kwargs["code_retrieval_codec"] == "expanded"
    code, calls = dispatch(monkeypatch, ["--purpose", "planning"])
    assert code == 0 and calls[0][calls[0].index("--code-retrieval-codec") + 1] == "expanded"
    doctor = dict(route="doctor_candidate", status="candidate_ready", provider_calls=0, artifact="/candidate", sha256="c" * 64, task_cid="cid:task")
    argv = implementation_argv(router=Path("/router"), model="pinned", reasoning="high", timeout=90, semantic_repository=None, doctor=doctor)
    assert "--code-retrieval-codec" not in argv


@pytest.mark.parametrize("selection", [
    {"code_retrieval_codec": "unknown"}, {"code_retrieval_codec": True},
    {"code_retrieval_codec": "compact"},
    {"code_retrieval_codec": "compact", "semantic_repository": Path("/source")},
    {"code_retrieval_codec": "compact", "semantic_transport": "native", "semantic_repository": Path("/source")},
    {"code_retrieval_codec": "compact", "semantic_transport": "native", "semantic_repository": Path("/source"),
     "public_instruction_artifact": Path("/public.json"), "public_instruction_sha256": "a" * 64, "public_instruction_task_cid": "cid:task", "purpose": "planning"},
])
def test_runner_invalid_selection_rejects_before_git_or_provider(monkeypatch, selection):
    from ipfs_accelerate_py import llm_router
    monkeypatch.setattr(runner.subprocess, "check_output", lambda *_args, **_kwargs: pytest.fail("invalid selection performed Git IO"))
    monkeypatch.setattr(llm_router, "generate_text", lambda *_args, **_kwargs: pytest.fail("invalid selection called provider"))
    with pytest.raises(ValueError, match="code retrieval codec"):
        runner.run(prompt="native", provider="codex_cli", model="pinned", timeout=30, max_output_tokens=100, **selection)


def test_runner_cli_invalid_codec_does_not_read_stdin_or_dispatch(monkeypatch):
    class Input:
        def read(self, *_): pytest.fail("invalid codec read stdin")
    monkeypatch.setattr("sys.stdin", SimpleNamespace(buffer=Input()))
    monkeypatch.setattr("sys.argv", ["runner", "--provider", "codex_cli", "--model", "pinned", "--code-retrieval-codec", "unknown"])
    monkeypatch.setattr(runner, "run", lambda **_: pytest.fail("invalid codec dispatched runner"))
    with pytest.raises(SystemExit) as stopped:
        runner.main()
    assert stopped.value.code == 2


@pytest.fixture
def public_native_coding_case(tmp_path, monkeypatch):
    from ipfs_accelerate_py.agent_supervisor.runtime import supervisor_meta_index as metadata
    from test.api.test_verified_code_retrieval_projection import native_case
    monkeypatch.setenv(metadata.ENV_DUCKDB, str(tmp_path / "fresh-coding-metadata.duckdb"))
    monkeypatch.delenv(metadata.ENV_DUCKLAKE, raising=False)
    case = native_case.__wrapped__(tmp_path)
    repository = case["repository"]
    repository.chmod(0o755)
    for name in ("mod.py", "instruction.md", "retrieval.json"):
        (repository / name).chmod(0o644)
    def git(*args):
        subprocess.run(["/usr/bin/git", "-C", str(repository), *args], check=True,
                       capture_output=True, text=True)
    git("init")
    git("add", "mod.py", "instruction.md")
    git("-c", "user.name=Public fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-m", "public fixture")
    worktree = tmp_path / "allocated-worktree"
    git("worktree", "add", "--detach", str(worktree), "HEAD")
    case["workspace"] = worktree
    return case


@pytest.mark.parametrize("mode", ["expanded", "compact"])
def test_real_coding_runner_preserves_native_identity_five_hits_and_literal_instruction(
        public_native_coding_case, monkeypatch, capsys, mode):
    """Replay and codec are real; admission loaders and provider are explicit stubs."""
    from ipfs_accelerate_py import llm_router
    from ipfs_accelerate_py.cli_runtime.cli_metadata import set_last_cli_observation
    from ipfs_accelerate_py.llm_allocation import intelligence_index
    from ipfs_accelerate_py.agent_supervisor.runtime import (
        compact_code_retrieval as codec, codex_usage_receipt, doctor_residual_context,
        multi_supervisor_runner, router_public_instruction, semantic_router_translation,
        verified_code_retrieval_projection as wrapper,
    )
    from test.api.test_verified_code_retrieval_projection import inclusion
    case = public_native_coding_case
    source, prompt = case["source_text"], case["prompt"]
    block, source_receipt = inclusion(source, tail="\nVerified task appendix remains outside the codec.\n")
    residual = "\nDoctor residual advisory stays separate.\n"
    native_hash = hashlib.sha256(prompt.encode()).hexdigest()
    monkeypatch.chdir(case["workspace"])
    for name in (*multi_supervisor_runner.DATABASE_PROGRAM_ENV_NAMES,
                 *multi_supervisor_runner.STATE_CREDENTIAL_ENV_NAMES,
                 "IPFS_ACCELERATE_AGENT_STATE_OWNER_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(semantic_router_translation, "encode_semantic_router_prompt", lambda **_: SimpleNamespace(receipt={
        "task_id": "CODE-1", "scope_cid": "scope:authored", "semantic_root_cid": "semantic:authored",
        "semantic_sha256": hashlib.sha256(b"authored semantic admission fixture").hexdigest(), "native_prompt_sha256": native_hash,
        "native_prompt_bytes": len(prompt.encode()), "freshness_checked": True,
    }))
    monkeypatch.setattr(router_public_instruction, "load_public_instruction", lambda **_: (block, source_receipt))
    monkeypatch.setattr(doctor_residual_context, "load_doctor_residual_advisory", lambda **_: (residual, {"completion_authority": False}))
    monkeypatch.setattr(intelligence_index, "discover_available_providers", lambda: ["codex_cli"])
    monkeypatch.setattr(intelligence_index, "select_efficient_route", lambda **_: SimpleNamespace(
        provider="codex_cli", model_name="gpt-5.6-sol", catalog_revision="fixture:pinned"))
    monkeypatch.setattr(llm_router, "get_llm_provider", lambda *_args, **_kwargs: object())
    # Prevent even the usage collector from inspecting a real native CLI home.
    monkeypatch.setattr(codex_usage_receipt, "recover_codex_usage", lambda **_: {"status": "unknown"})
    observed, projections = [], []
    actual_project = wrapper.project_verified_code_retrieval_prompt
    def project(**kwargs):
        selected, receipt = actual_project(**kwargs)
        projections.append((selected, receipt, kwargs["decoder_command"]))
        return selected, receipt
    monkeypatch.setattr(wrapper, "project_verified_code_retrieval_prompt", project)
    def fake_provider(actual_prompt, **kwargs):
        observed.append((actual_prompt, kwargs))
        set_last_cli_observation("codex_cli", {"exit_code": 0, "prompt_tokens": 123, "completion_tokens": 7})
        return "Authored fake-provider response"
    monkeypatch.setattr(llm_router, "generate_text", fake_provider)
    response, receipt = runner.run(prompt=prompt, provider="codex_cli", model="gpt-5.6-sol", timeout=30,
        max_output_tokens=100, semantic_repository=case["repository"], semantic_transport="native",
        code_retrieval_codec=mode, public_instruction_artifact=case["repository"] / "public-binding.json",
        public_instruction_sha256="a" * 64, public_instruction_task_cid="task:fixture",
        doctor_residual_artifact=case["repository"] / "residual.json", doctor_residual_sha256="b" * 64,
        doctor_residual_task_cid="task:fixture")
    assert response == "Authored fake-provider response" and len(observed) == 1
    actual_prompt, provider_options = observed[0]
    assert actual_prompt.endswith(residual + block)
    assert receipt["prompt_sha256"] == receipt["native_prompt_sha256"] == native_hash
    assert receipt["native_prompt_bytes"] == len(prompt.encode())
    assert receipt["model_prompt_sha256"] == hashlib.sha256(actual_prompt.encode()).hexdigest()
    assert receipt["model_prompt_bytes"] == len(actual_prompt.encode())
    assert receipt["public_instruction"] == source_receipt
    assert receipt["completion_authority"] is False and receipt["router_calls"] == 1
    assert provider_options["allow_local_fallback"] is provider_options["allow_cross_provider_fallback"] is False
    if mode == "expanded":
        assert projections == [] and receipt["code_retrieval_projection"] is None
        assert actual_prompt.endswith(prompt + residual + block)
    else:
        assert len(projections) == 1
        projected, projection, decoder = projections[0]
        assert projection["selected_transport"] == "compact"
        assert projection["native_verification"]["code_hit_count"] == 5
        assert projection["native_verification"]["captured_public_native_replay_verified"] is True
        assert projection["native_verification"]["semantic_producer_authentication_claimed"] is False
        assert projection["native_verification"]["metadata_owner_suppressed"] is True
        assert actual_prompt.endswith(projected + residual + block)
        packet = codec.parse_code_retrieval_prompt(projected, decoder_command=decoder)
        assert codec.decode_code_retrieval_prompt(packet, source) == prompt
        assert packet["code_context"]["hits"] == json.loads(case["code_text"])["hits"]
        assert len(projected.encode()) < len(prompt.encode())
    capsys.readouterr()
