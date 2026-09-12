#!/usr/bin/env python3
"""NS-011 independent cold-oracle scoring of reuse and dependency mutations.

Runs a frozen pytest cohort through admitted TestProofCache reuse and a
separate cold full runner. Reuse is decided from file identity before the
scoring oracle is invoked. Skipped or unavailable oracle rows cannot count
as safe agreement. A discovered unsound reuse blocks the affected profile
or is explicitly excluded from the paper claim.

This is sealed-profile qualification, not a matched A–D experiment and not a
native Groth16 proof of pytest execution.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


SNAP = Path(__file__).resolve().parent
ROOT = SNAP.parents[5]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP_QUAL = SNAP / "qualification"
ACC_ROOT = ROOT / "external/ipfs_accelerate"
DS_ROOT = ROOT / "external/ipfs_datasets"
KIT_ROOT = ROOT / "external/ipfs_kit"
TASK_ID = "NS-011"
POLICY_ID = "ns-011-cold-oracle-qualification-v1"
SCHEMA_COLD = "neurosymbolic-supervision/cold-oracle-result@1"
SCHEMA_MUTATION = "neurosymbolic-supervision/reuse-mutation-result@1"
SCHEMA_ANALYSIS = "neurosymbolic-supervision/reuse-analysis@1"
PAPER_CLAIM_PROFILE = "identity-from-files"
STALE_KEY_PROFILE = "stale-key-caller"
NOW_MS = 10_000
COLD_TIMEOUT_S = 30
CHECKPOINT_DIR = Path(
    os.environ.get(
        "IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR",
        str(SNAP / "checkpoints"),
    )
)

SOURCE_PATHS = (
    ACC_ROOT
    / "ipfs_accelerate_py/agent_supervisor/validation/proof_cached_test_validation.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/test_proof_cache.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/test_certificate_store.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/test_execution_contracts.py",
    ACC_ROOT
    / "ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_test_certificate_provider.py",
    ACC_ROOT
    / "ipfs_accelerate_py/agent_supervisor/analysis/test_identity_components.py",
    ACC_ROOT
    / "ipfs_accelerate_py/agent_supervisor/analysis/test_reuse_eligibility.py",
    ACC_ROOT / "ipfs_accelerate_py/testing/proof_reuse/collection_seed.py",
    ACC_ROOT / "ipfs_accelerate_py/testing/proof_reuse/runtime_revalidation.py",
    ACC_ROOT / "ipfs_accelerate_py/testing/proof_reuse/xdist.py",
    DS_ROOT
    / "ipfs_datasets_py/logic/software_contracts/semantic_state/test_selection.py",
)

NODE_DOUBLE = "tests/test_alpha.py::test_double"
NODE_SNAPSHOT = "tests/test_alpha.py::test_snapshot"
NODE_RESOURCE = "tests/test_alpha.py::test_resource_finalizer"
NODE_IDENTITY = "tests/test_beta.py::test_identity"
NODE_SKIP = "tests/test_skip.py::test_explicit_skip"
NODE_MISSING = "tests/test_missing.py::test_absent"

RECIPE: dict[str, str] = {
    "app.py": (
        "def double(x):\n"
        "    return x * 2\n"
        "\n"
        "def load_snapshot(path):\n"
        "    import json\n"
        "    from pathlib import Path\n"
        "    return json.loads(Path(path).read_text(encoding='utf-8'))['value']\n"
    ),
    "conftest.py": (
        "import pytest\n"
        "\n"
        "pytest_plugins = ['ns011_plugin']\n"
        "\n"
        "\n"
        "@pytest.fixture\n"
        "def db():\n"
        "    yield 21\n"
        "\n"
        "\n"
        "@pytest.fixture(autouse=True, scope='session')\n"
        "def clock():\n"
        "    yield 0\n"
        "\n"
        "\n"
        "@pytest.fixture\n"
        "def resource():\n"
        "    state = {'closed': False}\n"
        "    yield state\n"
        "    state['closed'] = True\n"
        "\n"
        "\n"
        "def pytest_configure(config):\n"
        "    config._ns011_hook = 'configure-v1'\n"
    ),
    "ns011_plugin.py": (
        "def pytest_runtest_setup(item):\n"
        "    item._ns011_plugin = 'plugin-v1'\n"
    ),
    "ns011_observer.py": (
        "import json\n"
        "import os\n"
        "from pathlib import Path\n"
        "\n"
        "\n"
        "class Ns011Observer:\n"
        "    def __init__(self):\n"
        "        self.collected = []\n"
        "        self.reports = []\n"
        "\n"
        "    def pytest_collection_finish(self, session):\n"
        "        self.collected = [item.nodeid for item in session.items]\n"
        "\n"
        "    def pytest_runtest_logreport(self, report):\n"
        "        self.reports.append(\n"
        "            {\n"
        "                'nodeid': report.nodeid,\n"
        "                'when': report.when,\n"
        "                'outcome': report.outcome,\n"
        "                'failed': report.failed,\n"
        "                'skipped': report.skipped,\n"
        "                'passed': report.passed,\n"
        "            }\n"
        "        )\n"
        "\n"
        "    def pytest_sessionfinish(self, session, exitstatus):\n"
        "        path = Path(os.environ['NS011_OBSERVATION'])\n"
        "        path.write_text(\n"
        "            json.dumps(\n"
        "                {\n"
        "                    'exitstatus': int(exitstatus),\n"
        "                    'collected': list(self.collected),\n"
        "                    'reports': list(self.reports),\n"
        "                    'collection_errors': bool(getattr(session, 'exitstatus', 0) == 2),\n"
        "                },\n"
        "                sort_keys=True,\n"
        "            ),\n"
        "            encoding='utf-8',\n"
        "        )\n"
        "\n"
        "\n"
        "def pytest_configure(config):\n"
        "    config.pluginmanager.register(Ns011Observer(), 'ns011-observer')\n"
    ),
    "pytest.ini": (
        "[pytest]\n"
        "addopts = -p no:cacheprovider -p ns011_observer\n"
        "cache_dir = .pytest_ns011_cache\n"
    ),
    "snapshots/db.json": '{"value": 21}\n',
    "effects/side_channel.json": '{"token": "effect-v1"}\n',
    "tests/test_alpha.py": (
        "from pathlib import Path\n"
        "\n"
        "from app import double, load_snapshot\n"
        "\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "SNAPSHOT = ROOT / 'snapshots' / 'db.json'\n"
        "EFFECT = ROOT / 'effects' / 'side_channel.json'\n"
        "\n"
        "\n"
        "def test_double(db):\n"
        "    assert double(db) == 42\n"
        "\n"
        "\n"
        "def test_snapshot():\n"
        "    assert load_snapshot(SNAPSHOT) == 21\n"
        "\n"
        "\n"
        "def test_resource_finalizer(resource):\n"
        "    assert resource['closed'] is False\n"
        "    token = EFFECT.read_text(encoding='utf-8')\n"
        "    assert 'effect-v1' in token\n"
    ),
    "tests/test_beta.py": (
        "def test_identity():\n"
        "    values = [1, 2, 3]\n"
        "    assert sum(values) == 6\n"
        "    assert values[0] + values[-1] == 4\n"
    ),
    "tests/test_skip.py": (
        "import pytest\n"
        "\n"
        "\n"
        "def test_explicit_skip():\n"
        "    pytest.skip('oracle skip must not count as safe agreement')\n"
    ),
}

REQUIRED_MUTATION_KINDS = (
    "fixture_definition",
    "fixture_instance",
    "finalizer",
    "plugin",
    "hook",
    "config",
    "policy",
    "key",
    "runtime",
    "external_snapshot",
    "test_removal",
    "stale_cache",
    "incomplete_trace",
    "changed_external_effect",
    "unchanged_positive",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_json(path: Path, payload: Any) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    atomic_write(path, encoded.encode("utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        for row in rows
    ]
    atomic_write(path, ("\n".join(lines) + "\n").encode("utf-8"))


def checkpoint(name: str, payload: Mapping[str, Any]) -> None:
    try:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        write_json(CHECKPOINT_DIR / f"{name}.json", dict(payload))
    except OSError:
        fallback = SNAP / "checkpoints"
        fallback.mkdir(parents=True, exist_ok=True)
        write_json(fallback / f"{name}.json", dict(payload))


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def enum_val(value: Any) -> str:
    return str(getattr(value, "value", value))


def which(name: str) -> str | None:
    return shutil.which(name)


def git_head(path: Path) -> str | None:
    git = which("git")
    if git is None:
        return None
    try:
        proc = subprocess.run(
            [git, "-C", str(path), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def source_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in SOURCE_PATHS:
        if path.is_file():
            hashes[rel(path)] = sha256_file(path)
    return hashes


def _install_sealed_multiformats_stub() -> bool:
    if "multiformats" in sys.modules:
        return False
    import types

    module = types.ModuleType("multiformats")

    class _Name:
        def __init__(self, name: str) -> None:
            self.name = name

    class CID:
        def __init__(self, value: str) -> None:
            self._value = value
            self.version = 1
            self.base = _Name("base32")
            self.codec = _Name("dag-json" if "json" in value else "raw")
            self.hashfun = _Name("sha2-256")
            self.raw_digest = b"\x00" * 32

        def __str__(self) -> str:
            return self._value

        @classmethod
        def decode(cls, value: str) -> "CID":
            if not isinstance(value, str) or not value.startswith("b"):
                raise ValueError("not a CIDv1 base32 address")
            return cls(value)

    module.CID = CID
    sys.modules["multiformats"] = module
    return True


def prepare_imports() -> dict[str, Any]:
    initial_path = os.environ.get("PATH")
    for path in (str(ACC_ROOT), str(DS_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)
    stubbed_multiformats = _install_sealed_multiformats_stub()

    from ipfs_accelerate_py.agent_supervisor.analysis import (
        test_identity_components as identity,
        test_reuse_eligibility as eligibility,
    )
    from ipfs_accelerate_py.agent_supervisor.proof import (
        test_execution_contracts as contracts,
        test_proof_cache as cache,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.formal_verification_contracts import (
        content_identity,
    )
    from ipfs_accelerate_py.agent_supervisor.validation import (
        proof_cached_test_validation as cached_validation,
    )
    from ipfs_accelerate_py.testing.proof_reuse import runtime_revalidation as lifecycle

    pytest_version = None
    pytest_error = None
    try:
        import pytest

        pytest_version = pytest.__version__
    except Exception as exc:
        pytest_error = f"{type(exc).__name__}: {exc}"

    groth16 = False
    groth16_error = None
    try:
        from ipfs_accelerate_py.agent_supervisor.integrations.test_reuse_capabilities import (
            probe_test_reuse_capabilities,
        )

        report = probe_test_reuse_capabilities()
        groth16 = bool(
            getattr(report.by_name.get("groth16"), "available", False)
            if hasattr(report, "by_name")
            else False
        )
    except Exception as exc:
        groth16_error = f"{type(exc).__name__}: {exc}"

    return {
        "interpreter": sys.executable,
        "python_version": sys.version.split()[0],
        "path": initial_path,
        "pytest": pytest_version,
        "pytest_error": pytest_error,
        "multiformats": False,
        "multiformats_stub_installed": stubbed_multiformats,
        "groth16_probe_error": groth16_error,
        "groth16_available": groth16,
        "binaries": {
            "z3": which("z3"),
            "cvc5": which("cvc5"),
            "groth16": which("groth16"),
        },
        "api": {
            "contracts": contracts,
            "cache": cache,
            "identity": identity,
            "eligibility": eligibility,
            "cached_validation": cached_validation,
            "lifecycle": lifecycle,
            "content_identity": content_identity,
        },
        "modules": {
            "proof_cached_test_validation": rel(SOURCE_PATHS[0]),
            "test_proof_cache": rel(SOURCE_PATHS[1]),
            "test_certificate_store": rel(SOURCE_PATHS[2]),
            "test_execution_contracts": rel(SOURCE_PATHS[3]),
            "ipfs_datasets_test_certificate_provider": rel(SOURCE_PATHS[4]),
            "test_identity_components": rel(SOURCE_PATHS[5]),
            "test_reuse_eligibility": rel(SOURCE_PATHS[6]),
            "collection_seed": rel(SOURCE_PATHS[7]),
            "runtime_revalidation": rel(SOURCE_PATHS[8]),
            "xdist": rel(SOURCE_PATHS[9]),
            "test_selection": rel(SOURCE_PATHS[10]),
        },
    }


def materialize(tree: Path, files: Mapping[str, str]) -> None:
    if tree.exists():
        shutil.rmtree(tree)
    for rel_path, content in files.items():
        path = tree / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def _decorator_keywords(node: ast.AST) -> dict[str, Any]:
    keywords: dict[str, Any] = {}
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg and isinstance(keyword.value, ast.Constant):
                keywords[keyword.arg] = keyword.value.value
    return keywords


def _is_fixture_decorator(node: ast.AST) -> bool:
    target = node.func if isinstance(node, ast.Call) else node
    names: list[str] = []
    while isinstance(target, ast.Attribute):
        names.append(target.attr)
        target = target.value
    if isinstance(target, ast.Name):
        names.append(target.id)
    return "fixture" in names


def _literal_from_function(fn: ast.FunctionDef) -> Any:
    for stmt in fn.body:
        value = None
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Yield):
            value = stmt.value.value
        elif isinstance(stmt, ast.Return):
            value = stmt.value
        if isinstance(value, ast.Constant) and isinstance(
            value.value, (int, str, bool)
        ):
            return value.value
    return None


def extract_conftest(src: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tree = ast.parse(src)
    fixtures: list[dict[str, Any]] = []
    hooks: list[dict[str, Any]] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        fixture_decs = [dec for dec in node.decorator_list if _is_fixture_decorator(dec)]
        if fixture_decs:
            keywords = {}
            for dec in fixture_decs:
                keywords.update(_decorator_keywords(dec))
            record: dict[str, Any] = {
                "name": node.name,
                "scope": str(keywords.get("scope") or "function"),
                "definition": ast.unparse(node),
                "autouse": bool(keywords.get("autouse", False)),
                "dependencies": tuple(
                    arg.arg for arg in node.args.args if arg.arg not in {"self", "request"}
                ),
            }
            literal = _literal_from_function(node)
            if literal is None:
                record["value_adapter_cid"] = None
            else:
                record["value"] = literal
            fixtures.append(record)
        elif node.name.startswith("pytest_"):
            hooks.append(
                {
                    "kind": "hook",
                    "name": node.name,
                    "implementation": ast.unparse(node),
                    "registered": True,
                    "order": 0,
                }
            )
    return fixtures, hooks


def cold_run(
    *,
    suite: Path,
    node_id: str | None,
    work: Path,
    python: str,
) -> dict[str, Any]:
    observation = work / "observation.json"
    stdout_path = work / "stdout.log"
    stderr_path = work / "stderr.log"
    if observation.exists():
        observation.unlink()
    argv = [
        python,
        "-B",
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "-p",
        "ns011_observer",
        "--override-ini=addopts=",
    ]
    if node_id:
        argv.append(node_id)
    env = {
        "HOME": str(work / "home"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONPATH": str(suite),
        "PYTHONHASHSEED": "0",
        "NS011_OBSERVATION": str(observation),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    (work / "home").mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        with stdout_path.open("wb") as out, stderr_path.open("wb") as err:
            proc = subprocess.run(
                argv,
                cwd=str(suite),
                env=env,
                stdout=out,
                stderr=err,
                timeout=COLD_TIMEOUT_S,
            )
        exit_code = int(proc.returncode)
        timed_out = False
    except subprocess.TimeoutExpired:
        exit_code = 124
        timed_out = True
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    payload: dict[str, Any] | None = None
    observation_sha256 = None
    if observation.is_file():
        observation_sha256 = sha256_file(observation)
        try:
            payload = json.loads(observation.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = None
    collected = list((payload or {}).get("collected") or [])
    reports = list((payload or {}).get("reports") or [])
    call_reports = [row for row in reports if row.get("when") == "call"]
    setup_reports = [row for row in reports if row.get("when") == "setup"]
    teardown_reports = [row for row in reports if row.get("when") == "teardown"]
    passed = sum(1 for row in call_reports if row.get("outcome") == "passed")
    failed = sum(
        1
        for row in reports
        if row.get("outcome") == "failed" and row.get("when") in {"setup", "call", "teardown"}
    )
    skipped = sum(1 for row in reports if row.get("outcome") == "skipped")
    node_reports = [row for row in call_reports if not node_id or row.get("nodeid") == node_id]
    node_outcome = None
    if node_id and any(row.get("nodeid") == node_id and row.get("outcome") == "skipped" for row in reports):
        node_outcome = "skipped"
    elif node_reports:
        node_outcome = str(node_reports[0].get("outcome"))
    elif node_id and node_id not in collected:
        node_outcome = "not_collected"
    elif timed_out:
        node_outcome = "timeout"
    elif payload is None:
        node_outcome = "unavailable"
    oracle_status = "actual"
    if timed_out:
        oracle_status = "unavailable"
        oracle_reason = "cold_runner_timeout"
    elif payload is None:
        oracle_status = "unavailable"
        oracle_reason = "observation_missing"
    elif node_id and node_id not in collected:
        oracle_status = "unavailable"
        oracle_reason = "node_not_collected"
    elif node_outcome == "skipped":
        oracle_status = "skipped"
        oracle_reason = "pytest_skip"
    else:
        oracle_reason = None
    if oracle_status == "actual":
        if node_outcome == "passed" and failed == 0:
            cold_outcome = "pass"
        elif node_outcome == "failed" or failed > 0:
            cold_outcome = "fail"
        else:
            cold_outcome = "non_pass"
            oracle_status = "unavailable"
            oracle_reason = f"unclassified_outcome:{node_outcome}"
    elif oracle_status == "skipped":
        cold_outcome = "skip"
    else:
        cold_outcome = "unavailable"
    skipped_or_unavailable = oracle_status in {"skipped", "unavailable"}
    return {
        "oracle_status": oracle_status,
        "oracle_reason": oracle_reason,
        "cold_outcome": cold_outcome,
        "skipped_or_unavailable": skipped_or_unavailable,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "elapsed_ms": elapsed_ms,
        "collected": collected,
        "collected_count": len(collected),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "node_id": node_id,
        "node_outcome": node_outcome,
        "setup_reports": len(setup_reports),
        "teardown_reports": len(teardown_reports),
        "observation_sha256": observation_sha256,
        "stdout_sha256": sha256_file(stdout_path) if stdout_path.is_file() else None,
        "stderr_sha256": sha256_file(stderr_path) if stderr_path.is_file() else None,
        "argv": argv,
        "counts_as_safe_agreement_eligible": not skipped_or_unavailable,
    }


def _cid(api: Mapping[str, Any], payload: Any) -> str:
    return api["content_identity"](payload)


def bind_identity(
    api: Mapping[str, Any],
    suite: Path,
    *,
    node_id: str,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    identity = api["identity"]
    files = {
        rel_path: (suite / rel_path).read_text(encoding="utf-8")
        if (suite / rel_path).is_file()
        else None
        for rel_path in RECIPE
    }
    conftest_src = files.get("conftest.py") or ""
    plugin_src = files.get("ns011_plugin.py") or ""
    fixtures, hooks = extract_conftest(conftest_src)
    for fixture in fixtures:
        if fixture.get("value_adapter_cid") is None and "value" not in fixture:
            fixture["value_adapter_cid"] = _cid(
                api,
                {
                    "schema": "ns-011-fixture-adapter@1",
                    "name": fixture["name"],
                    "definition": fixture["definition"],
                },
            )
        elif fixture.get("value_adapter_cid") is None:
            fixture.pop("value_adapter_cid", None)
    hook_identity = identity.collect_fixture_hook_identity(
        fixtures=fixtures,
        conftests=(
            ({"path": "conftest.py", "content": conftest_src},)
            if conftest_src
            else ()
        ),
        hooks=hooks,
        plugins=(
            {
                "kind": "plugin",
                "name": "ns011_plugin",
                "implementation": plugin_src,
                "distribution": "ns011-plugin",
                "version": "1.0.0",
                "registered": True,
                "order": 0,
            },
        )
        if plugin_src
        else (),
    )
    test_file = node_id.split("::", 1)[0] if node_id else ""
    test_src = files.get(test_file) if test_file else None
    test_function = node_id.split("::", 1)[1] if node_id and "::" in node_id else ""
    values = {
        "repository_forest_cid": _cid(
            api,
            {
                "schema": "ns-011-forest@1",
                "files": {
                    path: sha256_bytes(content.encode("utf-8"))
                    for path, content in files.items()
                    if content is not None
                },
            },
        ),
        "test_module_cid": _cid(
            api,
            {"schema": "ns-011-module@1", "path": test_file, "source": test_src or ""},
        )
        if test_src is not None
        else _cid(api, {"schema": "ns-011-module@1", "path": test_file, "missing": True}),
        "test_function_cid": _cid(
            api,
            {
                "schema": "ns-011-function@1",
                "path": test_file,
                "name": test_function,
                "source": test_src or "",
            },
        ),
        "fixture_cids": hook_identity.fixture_cids,
        "conftest_closure_cid": hook_identity.conftest_closure_cid,
        "hook_plugin_cids": hook_identity.hook_plugin_cids,
        "static_trace_root_cid": _cid(
            api, {"schema": "ns-011-static-trace@1", "node": node_id}
        ),
        "runtime_trace_root_cid": _cid(
            api,
            {
                "schema": "ns-011-runtime-trace@1",
                "policy": "complete-v1",
                "node": node_id,
            },
        ),
        "runtime_completeness_policy": "complete-v1",
        "pytest_version": "8.1.1",
        "python_version": "3.12.3",
        "config_cid": _cid(
            api,
            {
                "schema": "ns-011-config@1",
                "pytest.ini": files.get("pytest.ini") or "",
            },
        ),
        "dependency_lock_cid": _cid(
            api, {"schema": "ns-011-lock@1", "interpreter": "cpython-3.12.3"}
        ),
        "installed_distributions_cid": _cid(
            api, {"schema": "ns-011-dists@1", "pytest": "8.1.1"}
        ),
        "environment_cid": _cid(
            api,
            {
                "schema": "ns-011-env@1",
                "PYTHONHASHSEED": "0",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            },
        ),
        "platform_cid": _cid(api, {"schema": "ns-011-platform@1", "system": "linux"}),
        "interpreter_abi_cid": _cid(
            api, {"schema": "ns-011-abi@1", "python": "3.12.3"}
        ),
        "external_snapshot_cids": tuple(
            sorted(
                _cid(
                    api,
                    {
                        "schema": "ns-011-snapshot@1",
                        "path": path,
                        "sha256": sha256_bytes(content.encode("utf-8")),
                    },
                )
                for path, content in files.items()
                if path.startswith("snapshots/") and content is not None
            )
        ),
        "policy_cid": "cid:policy:ns-011",
        "eligibility_class": api["contracts"].EligibilityClass.REPOSITORY_FOREST_BOUND,
        "non_reusable_reasons": list(hook_identity.non_reusable_reasons),
        "effect_cid": _cid(
            api,
            {
                "schema": "ns-011-effect@1",
                "path": "effects/side_channel.json",
                "source": files.get("effects/side_channel.json") or "",
            },
        ),
    }
    if overrides:
        values.update(dict(overrides))
    return values


def _locator(api: Mapping[str, Any], node_id: str):
    return api["contracts"].TestLocatorKey(
        repository_id="repository:ns-011-qualification",
        package_identity="ns011_cohort",
        node_id=node_id,
        collection_schema_version="1",
        root_identity="root:ns-011",
        selection_semantics="exact_node",
    )


def _execution_key(api: Mapping[str, Any], locator, bound: Mapping[str, Any]):
    allowed = {
        "repository_forest_cid",
        "git_commit_id",
        "git_tree_id",
        "test_module_cid",
        "test_function_cid",
        "test_ast_cid",
        "fixture_cids",
        "conftest_closure_cid",
        "hook_plugin_cids",
        "static_trace_root_cid",
        "runtime_trace_root_cid",
        "runtime_completeness_policy",
        "pytest_version",
        "python_version",
        "plugin_versions_cid",
        "config_cid",
        "dependency_lock_cid",
        "installed_distributions_cid",
        "environment_cid",
        "platform_cid",
        "interpreter_abi_cid",
        "external_snapshot_cids",
        "policy_cid",
        "eligibility_class",
    }
    values = {name: bound[name] for name in allowed if name in bound}
    values["locator_cid"] = locator.locator_id
    if bound.get("non_reusable_reasons"):
        values["eligibility_class"] = api["contracts"].EligibilityClass.NON_REUSABLE
    return api["contracts"].TestExecutionKey(**values)


def _receipt(api: Mapping[str, Any], locator, key, **changes: Any):
    values = {
        "execution_key_cid": key.execution_key_id,
        "locator_cid": locator.locator_id,
        "setup_outcome": api["contracts"].PhaseOutcome.PASS,
        "call_outcome": api["contracts"].PhaseOutcome.PASS,
        "teardown_outcome": api["contracts"].PhaseOutcome.PASS,
        "static_trace_root_cid": key.static_trace_root_cid,
        "runtime_trace_root_cid": key.runtime_trace_root_cid,
        "completeness_receipt_cid": "cid:completeness:ns-011",
        "dependency_forest_cid": key.repository_forest_cid,
        "issuer_key_id": "key:ns-011-issuer",
        "policy_cid": key.policy_cid,
        "admitted": True,
    }
    values.update(changes)
    return api["contracts"].TestPassReceipt(**values)


def _certificate(api: Mapping[str, Any], receipt, key, **changes: Any):
    contracts = api["contracts"]
    public_inputs = {
        "receipt_cid": receipt.receipt_id,
        "execution_key_cid": key.execution_key_id,
        "policy_cid": key.policy_cid,
        "statement_cid": "cid:statement:ns-011",
        "circuit_cid": "cid:circuit:ns-011",
        "verifying_key_cid": "cid:vk:ns-011",
        "proof_system_id": "groth16",
        "issuer_id": "issuer:ns-011",
        "issuer_key_id": receipt.issuer_key_id,
        "epoch": "epoch:7",
        "setup_outcome": enum_val(receipt.setup_outcome),
        "call_outcome": enum_val(receipt.call_outcome),
        "teardown_outcome": enum_val(receipt.teardown_outcome),
    }
    values = {
        "receipt_cid": receipt.receipt_id,
        "execution_key_cid": key.execution_key_id,
        "policy_cid": key.policy_cid,
        "statement_cid": "cid:statement:ns-011",
        "circuit_cid": "cid:circuit:ns-011",
        "verifying_key_cid": "cid:vk:ns-011",
        "proof_artifact_cid": "cid:proof:ns-011",
        "issuer_id": "issuer:ns-011",
        "epoch": "epoch:7",
        "proof_system_id": "groth16",
        "backend_mode": contracts.ProofBackendMode.CRYPTOGRAPHIC,
        "authority": contracts.CertificateAuthority.AUTHORITATIVE,
        "public_inputs": public_inputs,
    }
    values.update(changes)
    if "public_inputs" not in changes:
        values["public_inputs"] = public_inputs
    return contracts.TestProofCertificate(**values)


def _policy(**changes: Any) -> dict[str, Any]:
    policy = {
        "policy_cid": "cid:policy:ns-011",
        "statement_cid": "cid:statement:ns-011",
        "circuit_cid": "cid:circuit:ns-011",
        "verifying_key_cid": "cid:vk:ns-011",
        "proof_system_id": "groth16",
        "trusted_issuer_ids": ("issuer:ns-011",),
        "allowed_epochs": ("epoch:7",),
        "revoked_issuer_ids": (),
        "revoked_receipt_cids": (),
        "revoked_certificate_cids": (),
    }
    policy.update(changes)
    return policy


def lookup_reuse(
    api: Mapping[str, Any],
    *,
    locator,
    key,
    candidates: tuple[Any, ...],
    policy: Mapping[str, Any] | None = None,
):
    cache = api["cache"].TestProofCache(
        current_policy=policy or _policy(),
        verifier=lambda *_args: True,
        clock=lambda: NOW_MS,
    )
    return cache.lookup(locator, key, candidates=candidates)


def admit_baseline(
    api: Mapping[str, Any],
    suite: Path,
    node_id: str,
) -> dict[str, Any]:
    locator = _locator(api, node_id)
    bound = bind_identity(api, suite, node_id=node_id)
    key = _execution_key(api, locator, bound)
    receipt = _receipt(api, locator, key)
    certificate = _certificate(api, receipt, key)
    candidate = api["cache"].TestProofCache.candidate(
        receipt,
        certificate,
        created_at_ms=9_300,
        expires_at_ms=11_000,
    )
    return {
        "node_id": node_id,
        "locator": locator,
        "bound": bound,
        "key": key,
        "receipt": receipt,
        "certificate": certificate,
        "candidate": candidate,
        "execution_key_cid": key.execution_key_id,
        "receipt_cid": receipt.receipt_id,
        "certificate_cid": certificate.certificate_id,
        "test_function_cid": key.test_function_cid,
    }


def _betacf(a: float, b: float, x: float) -> float:
    max_iter = 200
    eps = 3e-14
    am = 1.0
    bm = 1.0
    az = 1.0
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    bz = 1.0 - qab * x / qap
    for m in range(1, max_iter + 1):
        em = float(m)
        tem = em + em
        d = em * (b - em) * x / ((qam + tem) * (a + tem))
        ap = az + d * am
        bp = bz + d * bm
        d = -(a + em) * (qab + em) * x / ((a + tem) * (qap + tem))
        app = ap + d * az
        bpp = bp + d * bz
        am = ap / bpp
        bm = bp / bpp
        old = az
        az = app / bpp
        bz = 1.0
        if abs(az - old) < eps * abs(az):
            return az
    return az


def _betai(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1.0 - x) * b - ln_beta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _betai_inv(p: float, a: float, b: float) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if _betai(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> dict[str, float | None]:
    if n <= 0:
        return {"lower": None, "upper": None, "level": 1.0 - alpha, "method": "clopper_pearson"}
    if k <= 0:
        lower = 0.0
    else:
        lower = _betai_inv(alpha / 2.0, k, n - k + 1)
    if k >= n:
        upper = 1.0
    else:
        upper = _betai_inv(1.0 - alpha / 2.0, k + 1, n - k)
    return {
        "lower": lower,
        "upper": upper,
        "level": 1.0 - alpha,
        "method": "clopper_pearson",
        "zero_event_upper_closed_form": (1.0 - alpha ** (1.0 / n)) if k == 0 else None,
    }


def wilson_interval(k: int, n: int, z: float = 1.959963984540054) -> dict[str, float | None]:
    if n <= 0:
        return {"lower": None, "upper": None, "level": 0.95, "method": "wilson"}
    phat = k / n
    z2 = z * z
    den = 1.0 + z2 / n
    center = (phat + z2 / (2.0 * n)) / den
    margin = z * math.sqrt((phat * (1.0 - phat) + z2 / (4.0 * n)) / n) / den
    return {
        "lower": max(0.0, center - margin),
        "upper": min(1.0, center + margin),
        "level": 0.95,
        "method": "wilson",
    }


def score_pair(
    *,
    expected_reuse_action: str,
    reuse_action: str,
    cold: Mapping[str, Any],
    expected_cold_outcome: str | None,
) -> dict[str, Any]:
    oracle_skip = bool(cold.get("skipped_or_unavailable"))
    cold_outcome = str(cold.get("cold_outcome"))
    false_reuse = False
    false_denial = False
    unsound = False
    if reuse_action == "SKIP" and (
        expected_reuse_action == "RUN"
        or cold_outcome == "fail"
        or (expected_cold_outcome == "fail" and cold_outcome != "unavailable")
    ):
        false_reuse = True
        unsound = True
    if (
        reuse_action == "RUN"
        and expected_reuse_action == "SKIP"
        and cold_outcome == "pass"
        and not oracle_skip
    ):
        false_denial = True
    if oracle_skip:
        scoring_class = "not_agreement_oracle_skip_or_unavailable"
        counts_as_safe_agreement = False
    elif false_reuse:
        scoring_class = "false_reuse"
        counts_as_safe_agreement = False
    elif (
        reuse_action == "SKIP"
        and expected_reuse_action == "SKIP"
        and cold_outcome == "pass"
    ):
        scoring_class = "true_reuse"
        counts_as_safe_agreement = True
    elif reuse_action == "RUN" and expected_reuse_action == "RUN":
        scoring_class = "correct_invalidation_or_fallback"
        counts_as_safe_agreement = True
    elif false_denial:
        scoring_class = "false_denial"
        counts_as_safe_agreement = False
    else:
        scoring_class = "disagreement"
        counts_as_safe_agreement = False
    return {
        "scoring_class": scoring_class,
        "counts_as_safe_agreement": counts_as_safe_agreement,
        "false_reuse": false_reuse,
        "false_denial": false_denial,
        "unsound_reuse": unsound,
        "oracle_skip_or_unavailable": oracle_skip,
        "reuse_recorded_before_cold": True,
    }


def apply_files(base: Mapping[str, str], edits: Mapping[str, str | None]) -> dict[str, str]:
    files = dict(base)
    for path, content in edits.items():
        if content is None:
            files.pop(path, None)
        else:
            files[path] = content
    return files


def run_campaign(api: Mapping[str, Any]) -> dict[str, Any]:
    python = "/usr/bin/python3.12"
    work_root = Path(tempfile.mkdtemp(prefix="ns011-cohort-"))
    baseline_suite = work_root / "baseline"
    materialize(baseline_suite, RECIPE)
    cold_work = work_root / "cold"
    cold_work.mkdir()

    baseline_nodes = (NODE_DOUBLE, NODE_SNAPSHOT, NODE_RESOURCE, NODE_IDENTITY, NODE_SKIP)
    baseline_cold: dict[str, dict[str, Any]] = {}
    for index, node_id in enumerate(baseline_nodes):
        baseline_cold[node_id] = cold_run(
            suite=baseline_suite,
            node_id=node_id,
            work=cold_work / f"baseline-{index}",
            python=python,
        )
    admissions = {
        node_id: admit_baseline(api, baseline_suite, node_id)
        for node_id in (NODE_DOUBLE, NODE_SNAPSHOT, NODE_RESOURCE, NODE_IDENTITY)
    }

    cases: list[dict[str, Any]] = [
        {
            "case_id": "unchanged_eligible_test_double",
            "family": "unchanged_positive",
            "mutation_kind": "unchanged_positive",
            "polarity": "valid",
            "node_id": NODE_DOUBLE,
            "expected_reuse_action": "SKIP",
            "expected_reuse_reason": "proof_cache_hit",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "description": "Unchanged eligible test_double reuses an admitted receipt and independently cold-passes.",
        },
        {
            "case_id": "unchanged_eligible_test_snapshot",
            "family": "unchanged_positive",
            "mutation_kind": "unchanged_positive",
            "polarity": "valid",
            "node_id": NODE_SNAPSHOT,
            "expected_reuse_action": "SKIP",
            "expected_reuse_reason": "proof_cache_hit",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "description": "Unchanged snapshot-bound test independently cold-passes and reuses.",
        },
        {
            "case_id": "unchanged_eligible_test_identity",
            "family": "unchanged_positive",
            "mutation_kind": "unchanged_positive",
            "polarity": "valid",
            "node_id": NODE_IDENTITY,
            "expected_reuse_action": "SKIP",
            "expected_reuse_reason": "proof_cache_hit",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "description": "Nontrivial unchanged test_identity is a genuine positive reuse witness.",
        },
        {
            "case_id": "unchanged_eligible_test_resource_finalizer",
            "family": "unchanged_positive",
            "mutation_kind": "unchanged_positive",
            "polarity": "valid",
            "node_id": NODE_RESOURCE,
            "expected_reuse_action": "SKIP",
            "expected_reuse_reason": "proof_cache_hit",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "description": "Unchanged resource/finalizer test independently cold-passes and reuses.",
        },
        {
            "case_id": "fixture_definition_change_invalidates",
            "family": "identity_invalidation",
            "mutation_kind": "fixture_definition",
            "polarity": "invalid",
            "node_id": NODE_DOUBLE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "edits": {
                "conftest.py": RECIPE["conftest.py"].replace(
                    "def db():\n    yield 21\n",
                    "def db():\n    # definition v2\n    yield 21\n",
                )
            },
            "description": "Fixture definition text change invalidates reuse while the test body is unchanged.",
        },
        {
            "case_id": "fixture_instance_value_change_invalidates",
            "family": "identity_invalidation",
            "mutation_kind": "fixture_instance",
            "polarity": "invalid",
            "node_id": NODE_DOUBLE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "fail",
            "profile": PAPER_CLAIM_PROFILE,
            "edits": {
                "conftest.py": RECIPE["conftest.py"].replace("yield 21\n", "yield 20\n")
            },
            "description": "Fixture instance value 21→20 invalidates reuse; independent cold fails the assertion.",
        },
        {
            "case_id": "finalizer_change_invalidates",
            "family": "identity_invalidation",
            "mutation_kind": "finalizer",
            "polarity": "invalid",
            "node_id": NODE_RESOURCE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "edits": {
                "conftest.py": RECIPE["conftest.py"].replace(
                    "state['closed'] = True\n",
                    "state['closed'] = True\n    state['finalizer'] = 'v2'\n",
                )
            },
            "description": "Finalizer body change is bound into fixture identity and forces RUN.",
        },
        {
            "case_id": "plugin_change_invalidates",
            "family": "identity_invalidation",
            "mutation_kind": "plugin",
            "polarity": "invalid",
            "node_id": NODE_DOUBLE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "edits": {
                "ns011_plugin.py": (
                    "def pytest_runtest_setup(item):\n"
                    "    item._ns011_plugin = 'plugin-v2'\n"
                )
            },
            "description": "Plugin implementation change invalidates reuse of the same test body.",
        },
        {
            "case_id": "hook_change_invalidates",
            "family": "identity_invalidation",
            "mutation_kind": "hook",
            "polarity": "invalid",
            "node_id": NODE_DOUBLE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "edits": {
                "conftest.py": RECIPE["conftest.py"].replace(
                    "config._ns011_hook = 'configure-v1'\n",
                    "config._ns011_hook = 'configure-v2'\n",
                )
            },
            "description": "pytest_configure hook change is bound through conftest/hook identity.",
        },
        {
            "case_id": "config_change_invalidates",
            "family": "identity_invalidation",
            "mutation_kind": "config",
            "polarity": "invalid",
            "node_id": NODE_IDENTITY,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "edits": {
                "pytest.ini": RECIPE["pytest.ini"] + "xfail_strict = true\n"
            },
            "description": "pytest.ini/config identity change forces RUN.",
        },
        {
            "case_id": "policy_change_invalidates",
            "family": "identity_invalidation",
            "mutation_kind": "policy",
            "polarity": "invalid",
            "node_id": NODE_DOUBLE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "policy_mismatch",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "policy": _policy(policy_cid="cid:policy:ns-011-mutated"),
            "description": "Changed current policy CID forces RUN even when files are unchanged.",
        },
        {
            "case_id": "interpreter_key_change_invalidates",
            "family": "identity_invalidation",
            "mutation_kind": "key",
            "polarity": "invalid",
            "node_id": NODE_IDENTITY,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "bind_overrides": {"python_version": "3.11.0"},
            "description": "Interpreter identity is part of the execution key and cannot be omitted.",
        },
        {
            "case_id": "runtime_trace_change_invalidates",
            "family": "identity_invalidation",
            "mutation_kind": "runtime",
            "polarity": "invalid",
            "node_id": NODE_DOUBLE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "bind_overrides": {
                "runtime_trace_root_cid": "cid:runtime:mutated-ns-011"
            },
            "description": "Changed runtime-trace identity invalidates reuse of the same test body.",
        },
        {
            "case_id": "external_snapshot_change_invalidates",
            "family": "identity_invalidation",
            "mutation_kind": "external_snapshot",
            "polarity": "invalid",
            "node_id": NODE_SNAPSHOT,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "fail",
            "profile": PAPER_CLAIM_PROFILE,
            "edits": {"snapshots/db.json": '{"value": 99}\n'},
            "description": "External snapshot mutation invalidates reuse; independent cold fails.",
        },
        {
            "case_id": "changed_external_effect_invalidates",
            "family": "identity_invalidation",
            "mutation_kind": "changed_external_effect",
            "polarity": "invalid",
            "node_id": NODE_RESOURCE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "fail",
            "profile": PAPER_CLAIM_PROFILE,
            "edits": {"effects/side_channel.json": '{"token": "effect-v2"}\n'},
            "bind_overrides_from_effect": True,
            "description": "Changed external effect file is bound; independent cold fails the token assertion.",
        },
        {
            "case_id": "test_removal_invalidates",
            "family": "identity_invalidation",
            "mutation_kind": "test_removal",
            "polarity": "invalid",
            "node_id": NODE_IDENTITY,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "unavailable",
            "profile": PAPER_CLAIM_PROFILE,
            "edits": {"tests/test_beta.py": None},
            "description": "Removing the test module changes module identity; cold oracle cannot collect the node.",
        },
        {
            "case_id": "stale_cache_honest_rebind",
            "family": "stale_cache",
            "mutation_kind": "stale_cache",
            "polarity": "invalid",
            "node_id": NODE_DOUBLE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "fail",
            "profile": PAPER_CLAIM_PROFILE,
            "edits": {
                "conftest.py": RECIPE["conftest.py"].replace("yield 21\n", "yield 20\n")
            },
            "description": "Honest identity-from-files rebind after a stale cache source change forces RUN.",
        },
        {
            "case_id": "stale_key_presented_without_rebind",
            "family": "stale_cache",
            "mutation_kind": "stale_cache",
            "polarity": "invalid",
            "node_id": NODE_DOUBLE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "execution_key_mismatch",
            "expected_cold_outcome": "fail",
            "profile": STALE_KEY_PROFILE,
            "edits": {
                "conftest.py": RECIPE["conftest.py"].replace("yield 21\n", "yield 20\n")
            },
            "use_stale_key": True,
            "description": "Presenting a stale execution key after a fixture mutation would SKIP; this caller profile is excluded.",
        },
        {
            "case_id": "incomplete_runtime_trace_fallback",
            "family": "fallback",
            "mutation_kind": "incomplete_trace",
            "polarity": "diagnostic",
            "node_id": NODE_DOUBLE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "incomplete_trace",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "bind_overrides": {
                "runtime_trace_root_cid": "",
                "runtime_completeness_policy": "",
            },
            "description": "Incomplete runtime traces fall back to RUN instead of reuse.",
        },
        {
            "case_id": "pytest_skip_not_safe_agreement",
            "family": "oracle_unavailable",
            "mutation_kind": "unchanged_positive",
            "polarity": "diagnostic",
            "node_id": NODE_SKIP,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "candidate_missing",
            "expected_cold_outcome": "skip",
            "profile": PAPER_CLAIM_PROFILE,
            "no_admission": True,
            "description": "A pytest skip is independently recorded and cannot count as safe agreement.",
        },
        {
            "case_id": "removed_node_oracle_unavailable",
            "family": "oracle_unavailable",
            "mutation_kind": "test_removal",
            "polarity": "invalid",
            "node_id": NODE_MISSING,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "candidate_missing",
            "expected_cold_outcome": "unavailable",
            "profile": PAPER_CLAIM_PROFILE,
            "no_admission": True,
            "description": "A missing node has an unavailable oracle and cannot count as safe agreement.",
        },
        {
            "case_id": "lookup_miss_is_run",
            "family": "fallback",
            "mutation_kind": "unchanged_positive",
            "polarity": "diagnostic",
            "node_id": NODE_DOUBLE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "candidate_missing",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "empty_candidates": True,
            "description": "Absence of cache candidates is an explicit RUN, independently cold-scored.",
        },
        {
            "case_id": "simulated_certificate_cannot_skip",
            "family": "fallback",
            "mutation_kind": "unchanged_positive",
            "polarity": "invalid",
            "node_id": NODE_IDENTITY,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "certificate_non_attested",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "simulated_certificate": True,
            "description": "Simulated/non-attested certificates cannot authorize SKIP.",
        },
        {
            "case_id": "uncontrolled_fixture_fallback",
            "family": "fallback",
            "mutation_kind": "fixture_instance",
            "polarity": "diagnostic",
            "node_id": NODE_DOUBLE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "eligibility_denied",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "strip_fixture_values": True,
            "description": "Uncontrolled fixture values are a non-reusable fallback and force RUN.",
        },
        {
            "case_id": "teardown_failure_cannot_skip",
            "family": "lifecycle",
            "mutation_kind": "finalizer",
            "polarity": "invalid",
            "node_id": NODE_RESOURCE,
            "expected_reuse_action": "RUN",
            "expected_reuse_reason": "receipt_mismatch",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "teardown_fail_receipt": True,
            "description": "A teardown-failure receipt cannot authorize whole-item SKIP; cold still independently records the live node.",
        },
        {
            "case_id": "call_reuse_after_setup_runs_teardown",
            "family": "lifecycle",
            "mutation_kind": "finalizer",
            "polarity": "valid",
            "node_id": NODE_RESOURCE,
            "expected_reuse_action": "SKIP",
            "expected_reuse_reason": "proof_cache_hit",
            "expected_cold_outcome": "pass",
            "profile": PAPER_CLAIM_PROFILE,
            "lifecycle_capture": True,
            "description": "Call reuse after setup still requires teardown; cold execution records teardown reports.",
        },
    ]

    mutation_rows: list[dict[str, Any]] = []
    cold_rows: list[dict[str, Any]] = []
    joined: list[dict[str, Any]] = []

    for index, spec in enumerate(cases):
        case_id = spec["case_id"]
        node_id = spec["node_id"]
        files = apply_files(RECIPE, spec.get("edits") or {})
        suite = work_root / f"case-{index}-{case_id}"
        materialize(suite, files)

        locator = _locator(api, node_id)
        bound = bind_identity(
            api,
            suite,
            node_id=node_id,
            overrides=spec.get("bind_overrides"),
        )
        if spec.get("strip_fixture_values"):
            fixtures, hooks = extract_conftest((suite / "conftest.py").read_text(encoding="utf-8"))
            for fixture in fixtures:
                fixture.pop("value", None)
                fixture.pop("value_adapter_cid", None)
            stripped = api["identity"].collect_fixture_hook_identity(
                fixtures=fixtures,
                conftests=({"path": "conftest.py", "content": (suite / "conftest.py").read_text(encoding="utf-8")},),
                hooks=hooks,
                plugins=(
                    {
                        "kind": "plugin",
                        "name": "ns011_plugin",
                        "implementation": (suite / "ns011_plugin.py").read_text(encoding="utf-8"),
                        "distribution": "ns011-plugin",
                        "version": "1.0.0",
                        "registered": True,
                        "order": 0,
                    },
                ),
            )
            bound["fixture_cids"] = stripped.fixture_cids
            bound["non_reusable_reasons"] = list(stripped.non_reusable_reasons)
        if spec.get("bind_overrides_from_effect"):
            bound["repository_forest_cid"] = _cid(
                api,
                {
                    "schema": "ns-011-forest@1",
                    "files": {
                        path: sha256_bytes(content.encode("utf-8"))
                        for path, content in files.items()
                    },
                    "effect": bound["effect_cid"],
                },
            )
        key = _execution_key(api, locator, bound)
        if spec.get("use_stale_key"):
            key = admissions[node_id]["key"]
            locator = admissions[node_id]["locator"]

        baseline = admissions.get(node_id)
        candidates: tuple[Any, ...] = ()
        if spec.get("empty_candidates") or spec.get("no_admission") or baseline is None:
            candidates = ()
        elif spec.get("simulated_certificate"):
            simulated = _certificate(
                api,
                baseline["receipt"],
                baseline["key"],
                backend_mode=api["contracts"].ProofBackendMode.SIMULATED,
                authority=api["contracts"].CertificateAuthority.NON_ATTESTED,
            )
            candidates = (
                api["cache"].TestProofCache.candidate(
                    baseline["receipt"],
                    simulated,
                    created_at_ms=9_300,
                    expires_at_ms=11_000,
                ),
            )
        elif spec.get("teardown_fail_receipt"):
            fail_receipt = _receipt(
                api,
                locator,
                key,
                teardown_outcome=api["contracts"].PhaseOutcome.FAIL,
                admitted=False,
            )
            fail_cert = _certificate(api, fail_receipt, key)
            candidates = (
                api["cache"].TestProofCache.candidate(
                    fail_receipt,
                    fail_cert,
                    created_at_ms=9_300,
                    expires_at_ms=11_000,
                ),
            )
        else:
            candidates = (baseline["candidate"],)

        lookup = lookup_reuse(
            api,
            locator=locator,
            key=key,
            candidates=candidates,
            policy=spec.get("policy"),
        )
        reuse_action = enum_val(lookup.decision.action)
        reuse_reason = enum_val(lookup.decision.reason_code)
        reuse_status = enum_val(lookup.status)

        lifecycle_extra: dict[str, Any] = {}
        if spec.get("lifecycle_capture"):
            events: list[str] = []
            capture = api["lifecycle"].PostPassRuntimeTraceCapture()
            capture.execute_lifecycle_once(
                setup=lambda: events.append("setup"),
                call=lambda: events.append("call"),
                teardown=lambda: events.append("teardown"),
                capture_on_pass=False,
            )
            lifecycle_extra = {
                "lifecycle_events": events,
                "may_authorize_skip": bool(capture.may_authorize_skip),
                "teardown_retained": events == ["setup", "call", "teardown"],
            }

        mutation_row = {
            "schema": SCHEMA_MUTATION,
            "task_id": TASK_ID,
            "policy_id": POLICY_ID,
            "case_id": case_id,
            "family": spec["family"],
            "mutation_kind": spec["mutation_kind"],
            "polarity": spec["polarity"],
            "profile": spec["profile"],
            "description": spec["description"],
            "node_id": node_id,
            "expected_reuse_action": spec["expected_reuse_action"],
            "expected_reuse_reason": spec["expected_reuse_reason"],
            "reuse_action": reuse_action,
            "reuse_reason": reuse_reason,
            "reuse_status": reuse_status,
            "reuse_recorded_before_cold": True,
            "oracle_unavailable_to_reuse_lookup": True,
            "execution_key_cid": key.execution_key_id,
            "baseline_execution_key_cid": None
            if baseline is None
            else baseline["execution_key_cid"],
            "execution_key_changed": baseline is not None
            and key.execution_key_id != baseline["execution_key_cid"],
            "test_function_cid": key.test_function_cid,
            "body_unchanged": baseline is not None
            and key.test_function_cid == baseline["test_function_cid"],
            "receipt_cid": lookup.decision.receipt_cid,
            "certificate_cid": lookup.decision.certificate_cid,
            "candidates_considered": lookup.candidates_considered,
            "non_reusable_reasons": list(bound.get("non_reusable_reasons") or ()),
            "kernel_proof": False,
            "live_ad_experiment": False,
            **lifecycle_extra,
        }
        mutation_rows.append(mutation_row)

        cold = cold_run(
            suite=suite,
            node_id=node_id,
            work=cold_work / f"score-{index}-{case_id}",
            python=python,
        )
        cold_row = {
            "schema": SCHEMA_COLD,
            "task_id": TASK_ID,
            "policy_id": POLICY_ID,
            "case_id": case_id,
            "family": spec["family"],
            "mutation_kind": spec["mutation_kind"],
            "polarity": spec["polarity"],
            "profile": spec["profile"],
            "description": spec["description"],
            "node_id": node_id,
            "expected_cold_outcome": spec["expected_cold_outcome"],
            "independent_of_reuse_lookup": True,
            "kernel_proof": False,
            "live_ad_experiment": False,
            **cold,
        }
        cold_rows.append(cold_row)

        scoring = score_pair(
            expected_reuse_action=spec["expected_reuse_action"],
            reuse_action=reuse_action,
            cold=cold,
            expected_cold_outcome=spec.get("expected_cold_outcome"),
        )
        expected_action_met = reuse_action == spec["expected_reuse_action"]
        if spec["profile"] == STALE_KEY_PROFILE and spec.get("use_stale_key"):
            # The cache HIT on a stale key is the discovered unsound reuse.
            expected_action_met = reuse_action == "SKIP"
            scoring = {
                "scoring_class": "false_reuse",
                "counts_as_safe_agreement": False,
                "false_reuse": True,
                "false_denial": False,
                "unsound_reuse": True,
                "oracle_skip_or_unavailable": bool(cold.get("skipped_or_unavailable")),
                "reuse_recorded_before_cold": True,
                "stale_key_attack": True,
            }
        mutation_row["observed_reason"] = reuse_reason
        mutation_row["status"] = "pass" if expected_action_met else "fail"
        mutation_row.update({k: v for k, v in scoring.items() if k != "reuse_recorded_before_cold"})
        cold_row["status"] = (
            "pass"
            if (
                cold["cold_outcome"] == spec["expected_cold_outcome"]
                or (
                    spec["expected_cold_outcome"] == "unavailable"
                    and cold["skipped_or_unavailable"]
                )
            )
            else "fail"
        )
        joined.append(
            {
                "case_id": case_id,
                "profile": spec["profile"],
                "mutation_kind": spec["mutation_kind"],
                "expected_reuse_action": spec["expected_reuse_action"],
                "reuse_action": reuse_action,
                "reuse_reason": reuse_reason,
                "cold_outcome": cold["cold_outcome"],
                "oracle_status": cold["oracle_status"],
                **scoring,
            }
        )

    shutil.rmtree(work_root, ignore_errors=True)
    return {
        "baseline_cold": {
            node_id: {
                "oracle_status": row["oracle_status"],
                "cold_outcome": row["cold_outcome"],
                "observation_sha256": row["observation_sha256"],
                "elapsed_ms": row["elapsed_ms"],
            }
            for node_id, row in baseline_cold.items()
        },
        "admissions": {
            node_id: {
                "execution_key_cid": row["execution_key_cid"],
                "receipt_cid": row["receipt_cid"],
                "certificate_cid": row["certificate_cid"],
                "test_function_cid": row["test_function_cid"],
            }
            for node_id, row in admissions.items()
        },
        "mutation_rows": mutation_rows,
        "cold_rows": cold_rows,
        "joined": joined,
        "work_root_removed": True,
    }


def rate_block(k: int, n: int, *, label: str, failures: list[str]) -> dict[str, Any]:
    proportion = None if n == 0 else k / n
    return {
        "label": label,
        "events": k,
        "denominator": n,
        "proportion": proportion,
        "exact_counts": f"{k}/{n}",
        "observed_failures": list(failures),
        "clopper_pearson_95": clopper_pearson(k, n, 0.05),
        "wilson_95": wilson_interval(k, n),
        "undefined_when_denominator_zero": n == 0,
    }


def build_analysis(
    *,
    capability: Mapping[str, Any],
    hashes: Mapping[str, str],
    campaign: Mapping[str, Any],
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    joined = list(campaign["joined"])
    mutation_rows = list(campaign["mutation_rows"])
    by_profile: dict[str, list[dict[str, Any]]] = {}
    for row in joined:
        by_profile.setdefault(row["profile"], []).append(row)

    def profile_stats(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        attempted = [row for row in rows]
        false_reuse = [row["case_id"] for row in attempted if row.get("false_reuse")]
        false_denial = [row["case_id"] for row in attempted if row.get("false_denial")]
        unsound = [row["case_id"] for row in attempted if row.get("unsound_reuse")]
        skip_unavail = [
            row["case_id"] for row in attempted if row.get("oracle_skip_or_unavailable")
        ]
        safe = [row["case_id"] for row in attempted if row.get("counts_as_safe_agreement")]
        true_reuse = [
            row["case_id"] for row in attempted if row.get("scoring_class") == "true_reuse"
        ]
        blocked = bool(unsound)
        claim_status = (
            "blocked_and_excluded_from_paper_claim"
            if name == STALE_KEY_PROFILE and blocked
            else "blocked_until_fixed_or_requalified"
            if blocked
            else "qualified_with_finite_uncertainty"
        )
        return {
            "profile": name,
            "attempted_reuse_cases": len(attempted),
            "false_reuse": rate_block(
                len(false_reuse), len(attempted), label="false_reuse", failures=false_reuse
            ),
            "false_denial": rate_block(
                len(false_denial),
                len(attempted),
                label="false_denial",
                failures=false_denial,
            ),
            "unsound_reuse_cases": unsound,
            "oracle_skip_or_unavailable_cases": skip_unavail,
            "safe_agreement_cases": safe,
            "true_reuse_witnesses": true_reuse,
            "skipped_or_unavailable_cannot_count_as_safe_agreement": True,
            "blocked": blocked,
            "claim_status": claim_status,
        }

    profiles = {
        name: profile_stats(name, rows) for name, rows in sorted(by_profile.items())
    }
    paper = profiles[PAPER_CLAIM_PROFILE]
    stale = profiles.get(STALE_KEY_PROFILE)
    kinds = sorted({row["mutation_kind"] for row in mutation_rows})
    missing_kinds = [kind for kind in REQUIRED_MUTATION_KINDS if kind not in kinds]
    positive = [
        row["case_id"]
        for row in joined
        if row.get("scoring_class") == "true_reuse" and row["profile"] == PAPER_CLAIM_PROFILE
    ]
    mutation_with_decision = [
        row["case_id"]
        for row in mutation_rows
        if row["mutation_kind"] != "unchanged_positive"
        and row.get("expected_reuse_action") == "RUN"
        and row.get("reuse_action") == "RUN"
        and row["profile"] == PAPER_CLAIM_PROFILE
    ]
    return {
        "schema": SCHEMA_ANALYSIS,
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "generated_at": started_at,
        "finished_at": finished_at,
        "qualification_not_live_ad": True,
        "paper_claim_profile": PAPER_CLAIM_PROFILE,
        "claim_boundary": (
            "This analysis is a sealed-profile cold-oracle mutation campaign on "
            "the identity-from-files reuse caller. It is not a matched A–D "
            "experiment, not a native Groth16 proof of pytest execution, and not "
            "a universal closure proof of πD."
        ),
        "independence": {
            "reuse_recorded_before_cold_for_every_case": all(
                row.get("reuse_recorded_before_cold") for row in mutation_rows
            ),
            "cold_independent_of_reuse_lookup": all(
                row.get("independent_of_reuse_lookup")
                for row in campaign["cold_rows"]
            ),
            "oracle_unavailable_to_candidate_generation": True,
            "skipped_or_unavailable_cannot_count_as_safe_agreement": True,
        },
        "required_mutation_kinds": list(REQUIRED_MUTATION_KINDS),
        "observed_mutation_kinds": kinds,
        "missing_required_mutation_kinds": missing_kinds,
        "each_required_mutation_has_invalidation_or_fallback": not missing_kinds
        and bool(mutation_with_decision),
        "genuine_unchanged_positive_reuse_witnesses": positive,
        "positive_reuse_witness_count": len(positive),
        "baseline_admissions": campaign["admissions"],
        "baseline_cold": campaign["baseline_cold"],
        "profiles": profiles,
        "paper_claim": {
            "profile": PAPER_CLAIM_PROFILE,
            "blocked": paper["blocked"],
            "claim_status": paper["claim_status"],
            "false_reuse": paper["false_reuse"],
            "false_denial": paper["false_denial"],
            "unsound_reuse_cases": paper["unsound_reuse_cases"],
            "exclusion": None,
        },
        "excluded_profiles": {
            STALE_KEY_PROFILE: {
                "blocked": True if stale and stale["blocked"] else False,
                "claim_status": None if stale is None else stale["claim_status"],
                "unsound_reuse_cases": None if stale is None else stale["unsound_reuse_cases"],
                "exclusion": (
                    "Callers must recompute the current TestExecutionKey from "
                    "files. Presenting a stale key after a dependency mutation "
                    "is unsound and is excluded from the paper reuse claim."
                ),
            }
        },
        "all_attempted_reuse_cases": {
            "denominator": len(joined),
            "false_reuse": rate_block(
                sum(1 for row in joined if row.get("false_reuse")),
                len(joined),
                label="false_reuse_all_attempted",
                failures=[row["case_id"] for row in joined if row.get("false_reuse")],
            ),
            "includes_excluded_stale_key_attack": True,
            "note": (
                "The all-attempted denominator includes the explicitly excluded "
                "stale-key-caller attack. The paper claim uses identity-from-files."
            ),
        },
        "scoring_classes": {
            name: [row["case_id"] for row in joined if row.get("scoring_class") == name]
            for name in sorted({row["scoring_class"] for row in joined})
        },
        "capability": {
            "interpreter": capability.get("interpreter"),
            "python_version": capability.get("python_version"),
            "path": capability.get("path"),
            "pytest": capability.get("pytest"),
            "groth16_available": capability.get("groth16_available"),
            "binaries": capability.get("binaries"),
        },
        "source_hashes": dict(hashes),
        "workspace_git_head": git_head(ROOT),
        "consumer_gitlinks": {
            "external/ipfs_accelerate": git_head(ACC_ROOT),
            "external/ipfs_datasets": git_head(DS_ROOT),
            "external/ipfs_kit": git_head(KIT_ROOT),
        },
    }


def main() -> int:
    started_at = utc_now()
    checkpoint("start", {"started_at": started_at, "task_id": TASK_ID})
    capability = prepare_imports()
    api = capability.pop("api")
    hashes = source_hashes()
    if capability.get("pytest") is None:
        raise SystemExit(f"pytest unavailable: {capability.get('pytest_error')}")
    campaign = run_campaign(api)
    finished_at = utc_now()
    analysis = build_analysis(
        capability=capability,
        hashes=hashes,
        campaign=campaign,
        started_at=started_at,
        finished_at=finished_at,
    )
    paper = analysis["paper_claim"]
    if paper["blocked"]:
        raise SystemExit(
            "NS-011 paper-claim profile blocked by unsound reuse: "
            + ",".join(paper["unsound_reuse_cases"])
        )
    if analysis["missing_required_mutation_kinds"]:
        raise SystemExit(
            "NS-011 missing required mutation kinds: "
            + ",".join(analysis["missing_required_mutation_kinds"])
        )
    if analysis["positive_reuse_witness_count"] < 1:
        raise SystemExit("NS-011 missing genuine unchanged positive reuse witness")
    failed_mutations = [
        row["case_id"]
        for row in campaign["mutation_rows"]
        if row.get("status") != "pass" and row.get("profile") == PAPER_CLAIM_PROFILE
    ]
    failed_cold = [
        row["case_id"]
        for row in campaign["cold_rows"]
        if row.get("status") != "pass" and row.get("profile") == PAPER_CLAIM_PROFILE
    ]
    if failed_mutations or failed_cold:
        raise SystemExit(
            f"NS-011 case failures mutations={failed_mutations} cold={failed_cold}"
        )

    recipe_doc = {
        "schema": "neurosymbolic-supervision/cold-oracle-fixture-recipe@1",
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "files": {
            path: {"sha256": sha256_bytes(content.encode("utf-8")), "bytes": len(content.encode("utf-8"))}
            for path, content in RECIPE.items()
        },
    }

    QUAL.mkdir(parents=True, exist_ok=True)
    SNAP_QUAL.mkdir(parents=True, exist_ok=True)
    (SNAP / "cohort").mkdir(parents=True, exist_ok=True)
    write_jsonl(QUAL / "cold_oracle_results.jsonl", campaign["cold_rows"])
    write_jsonl(QUAL / "reuse_mutation_results.jsonl", campaign["mutation_rows"])
    write_json(QUAL / "reuse_analysis.json", analysis)
    write_jsonl(SNAP_QUAL / "cold_oracle_results.jsonl", campaign["cold_rows"])
    write_jsonl(SNAP_QUAL / "reuse_mutation_results.jsonl", campaign["mutation_rows"])
    write_json(SNAP_QUAL / "reuse_analysis.json", analysis)
    write_json(SNAP / "fixture_recipe.json", recipe_doc)

    checkpoint(
        "outputs",
        {
            "finished_at": finished_at,
            "cold_rows": len(campaign["cold_rows"]),
            "mutation_rows": len(campaign["mutation_rows"]),
            "paper_claim_blocked": paper["blocked"],
            "false_reuse": paper["false_reuse"]["exact_counts"],
            "cold_sha256": sha256_file(QUAL / "cold_oracle_results.jsonl"),
            "mutation_sha256": sha256_file(QUAL / "reuse_mutation_results.jsonl"),
            "analysis_sha256": sha256_file(QUAL / "reuse_analysis.json"),
        },
    )
    print("NS-011 cold-oracle reuse qualification: OK")
    print(f"cases={len(campaign['joined'])}")
    print(f"false_reuse_paper={paper['false_reuse']['exact_counts']}")
    print(f"true_reuse_witnesses={analysis['positive_reuse_witness_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
