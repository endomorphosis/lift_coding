"""Collect pinned unavailable-review and disposable signature evidence only."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.abc
import importlib.util
import json
import math
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = Path(__file__).resolve().parent
OUTPUT = CAMPAIGN / "review-provenance-01"
DOCUMENT = ROOT / "implementation_plan/docs/57-autoformalization-signed-review-provenance-2026-10-04.md"
LOGS = Path("/tmp/autoformalization-provenance-root-20261004")
PRIOR = CAMPAIGN / "relation-mask-handoff-01/verification.json"
PRIOR_SHA = "e127039aa2e7d84fba5890b7e9f7a2c600d9ba06466ca5033fcec89e92af2e00"
IO = CAMPAIGN / "assay_relation_readiness.py"
IO_SHA = "39f327de0787d4fdb3a13ac3a9bb784d0916cf911e24ecd3f12cc9c403f0b320"
UNAVAILABLE_RUNNER = CAMPAIGN / "assay_review_provenance.py"
FIXTURE_RUNNER = CAMPAIGN / "assay_review_provenance_fixtures.py"
OWNER = REPO / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_review_provenance.py"
OWNER_SHA = "f666f3e5b1be498687662c0b9cfae2d8befe319c58625259ed7e1d360d65f222"
TEST = REPO / "tests/unit/logic/formalization/autoencoder/test_alignment_review_provenance.py"
TEST_SHA = "a1935d24b845dea8d06600d230c3627f436e7a5f2238728c0ee5ba5bba4fd1f3"
MAX_FILE = 128 * 1024**2
MAX_JSON = 16 * 1024**2
MAX_OUTPUT = 8 * 1024**2
WALL_SECONDS = 30
MASKS = {"weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision", "proof_supervision", "fidelity_evaluation"}
MATRICES = ("objective_positive_mask", "objective_permitted_negative_mask", "admitted_positive_mask", "admitted_permitted_negative_mask")
TEST_COUNTS = {
    "test_alignment_review_provenance.py": 70,
    "test_alignment_relation_mask_handoff.py": 61,
    "test_alignment_relation_declarations.py": 46,
    "test_alignment_lane_bundle.py": 158,
    "test_alignment_stage_declarations.py": 72,
}
LOG_NAMES = ("tests.xml", "pytest.stdout", "pytest.stderr", "command.json", "ruff.stdout", "ruff.stderr", "ruff-command.json")
FORBIDDEN = {"cryptography", "torch", "numpy", "scipy", "transformers", "sentence_transformers", "spacy", "safetensors", "tensorflow", "jax", "lean", "z3", "cvc5"}
PROVIDER = ROOT / ".venv/lib/python3.12/site-packages/cryptography"
PROVIDER_SHAS = {
    str(PROVIDER / "__init__.py"): "5ec44bfcfc5b53a520a32a20940809412ac908ff7ba2f040f18204436fae23af",
    str(PROVIDER / "hazmat/primitives/asymmetric/ed25519.py"): "925eb77e0ee6cae32335398ca1515e1fa895af4c791648cd9a08312114e5a099",
    str(PROVIDER / "hazmat/bindings/_rust.abi3.so"): "9ea3bd3630d980e2eca178d577564ead08134a115fe4d45a41855cd517d905bf",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def seal(value):
    require(type(value) is dict and "content_sha256" not in value, "fresh receipt body required")
    return {**value, "content_sha256": digest(value)}


def sha(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "canonical external SHA required")
    return value


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def read_file(path, expected_sha=None, *, limit=MAX_FILE):
    path = Path(path).absolute()
    require(all(not parent.is_symlink() for parent in (path, *path.parents)), "symlink input forbidden")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= limit, "bounded ordinary file required")
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    require(len(data) == before.st_size and identity(before) == identity(after) == identity(path.lstat()), "input changed while reading")
    selected = {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    require(expected_sha is None or selected["sha256"] == sha(expected_sha), "external file pin differs: " + str(path))
    return data, selected


def parse_json(data):
    require(0 < len(data) <= MAX_JSON, "bounded JSON required")

    def pairs(entries):
        result = {}
        for key, value in entries:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def constant(value):
        raise ValueError("nonfinite JSON constant: " + value)

    value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    nodes = 0

    def walk(item, depth=0):
        nonlocal nodes
        nodes += 1
        require(depth <= 40 and nodes <= 1_000_000, "JSON structure exceeds bound")
        if type(item) is dict:
            require(all(type(key) is str for key in item), "ordinary JSON object required")
            for child in item.values():
                walk(child, depth + 1)
        elif type(item) is list:
            for child in item:
                walk(child, depth + 1)
        elif type(item) is float:
            require(math.isfinite(item), "finite JSON number required")
        else:
            require(item is None or type(item) in (str, bool, int), "ordinary JSON value required")

    walk(value)
    raw(value)
    if type(value) is dict and "content_sha256" in value:
        require(value["content_sha256"] == digest({key: item for key, item in value.items() if key != "content_sha256"}), "JSON selfseal differs")
    return value


def read_json(path, expected_sha=None):
    data, selected = read_file(path, expected_sha, limit=MAX_JSON)
    return parse_json(data), selected


def iter_bindings(value):
    if type(value) is dict:
        if set(value) == {"path", "bytes", "sha256"}:
            yield value
        else:
            for item in value.values():
                yield from iter_bindings(item)
    elif type(value) is list:
        for item in value:
            yield from iter_bindings(item)


class RejectRuntime(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in FORBIDDEN:
            raise ImportError("collector parent excludes crypto, model and prover stacks")
        return None


def selected_module(path, expected_sha, name):
    data, _selected = read_file(path, expected_sha, limit=MAX_JSON)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def integer(value, expected, label):
    require(type(value) is int and value == expected, label + " differs")


def zero_authority(value, owner=None):
    require(type(value["masks"]) is dict and set(value["masks"]) == MASKS
            and all(type(mask) is int and mask == 0 for mask in value["masks"].values()), "supervision promoted")
    for key in ("actual_fit_authorized", "source_fidelity_established", "proof_authority"):
        require(value[key] is False, "authority promoted: " + key)
    for key in ("human_reviews_authenticated", "semantic_labels_admitted", "optimizer_updates"):
        if key in value:
            integer(value[key], 0, key)
    if owner is not None:
        require(all(value[key] is False for key in owner.FALSE), "receipt authority flag promoted")
        require(all(type(value[key]) is int and value[key] == 0 for key in owner.handoffs.COUNTERS), "receipt activity or admission promoted")


def check_verification(receipt, n, owner):
    integer(receipt["train_row_count"], n, "receipt TRAIN row count")
    integer(receipt["pair_count"], n * n, "receipt Cartesian pair count")
    require(len(receipt["endpoint_rows"]) == n and len(receipt["endpoint_signature_ledger"]) == 2 * n
            and len(receipt["pair_signature_ledger"]) == 2 * n * n, "signature coverage ledger truncated")
    integer(receipt["expected_signature_slot_count"], 2 * n + 2 * n * n, "signature slot count")
    for name in MATRICES:
        matrix = receipt[name]
        require(type(matrix) is list and len(matrix) == n
                and all(type(row) is list and len(row) == n for row in matrix)
                and all(cell is False for row in matrix for cell in row), "signature enabled a mask or lost a pair")
        require(receipt["matrix_sha256"][name] == digest(matrix), "matrix checksum differs")
    zero_authority(receipt, owner)


def replay_fixtures(selected, source_bindings, provider_bindings):
    """Parent enforces wall/process-group bounds; child owns CPU/AS/file limits."""
    command = [str(ROOT / ".venv/bin/python"), "-I", "-B", str(FIXTURE_RUNNER), "--replay-only",
               "--owner-sha", OWNER_SHA, "--test-sha", TEST_SHA]
    environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
                   "IPFS_DATASETS_AUTO_INSTALL_TEST_DEPS": "0", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    require(not (OUTPUT / "replay-exit.json").exists(), "fresh replay exit diagnostic required")
    started = time.monotonic()
    timed_out, oversized, parent_error, cleanup_error = False, False, None, None
    process, cleanup_attempted, cleanup_timed_out = None, False, False
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.Popen(command, cwd=CAMPAIGN, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, close_fds=True, start_new_session=True)
            while process.poll() is None:
                if time.monotonic() - started >= WALL_SECONDS:
                    timed_out = True
                    break
                if os.fstat(stdout.fileno()).st_size > MAX_OUTPUT or os.fstat(stderr.fileno()).st_size > MAX_OUTPUT:
                    oversized = True
                    break
                time.sleep(0.02)
            timed_out = timed_out or time.monotonic() - started >= WALL_SECONDS
        except BaseException as error:
            parent_error = type(error).__name__
        finally:
            if process is not None:
                cleanup_attempted = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except OSError as error:
                    cleanup_error = type(error).__name__
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    cleanup_error, cleanup_timed_out = "TimeoutExpired", True
                except OSError as error:
                    cleanup_error = type(error).__name__
        stdout_size, stderr_size = os.fstat(stdout.fileno()).st_size, os.fstat(stderr.fileno()).st_size
        oversized = oversized or stdout_size > MAX_OUTPUT or stderr_size > MAX_OUTPUT
        stdout.seek(0)
        stderr.seek(0)
        data, errors = stdout.read(MAX_OUTPUT), stderr.read(MAX_OUTPUT)
    returncode = None if process is None else process.returncode
    successful = not timed_out and not oversized and parent_error is None and cleanup_error is None and returncode == 0 and not errors
    exit_diagnostic = seal({
        "schema": "alignment-review-provenance-parent-replay-exit/v1",
        "status": "completed_bounded_fixture_replay_process" if successful else "failed_bounded_fixture_replay_process",
        "command": command, "source_bindings": source_bindings, "provider_bindings": provider_bindings,
        "timed_out": timed_out, "output_limit_exceeded": oversized, "parent_error_type": parent_error,
        "child_launched": process is not None, "cleanup_error_type": cleanup_error,
        "cleanup_wait_timed_out": cleanup_timed_out, "cleanup_wait_limit_seconds": 5,
        "returncode": returncode, "wall_seconds": time.monotonic() - started,
        "stdout_observed_bytes": stdout_size, "stderr_observed_bytes": stderr_size,
        "stdout_captured_bytes": len(data), "stderr_captured_bytes": len(errors),
        "stdout_captured_sha256": hashlib.sha256(data).hexdigest(), "stderr_captured_sha256": hashlib.sha256(errors).hexdigest(),
        "stdout_truncated": stdout_size > len(data), "stderr_truncated": stderr_size > len(errors),
        "stream_digest_scope": "captured_prefix_up_to_8MiB_each_full_stream_only_when_not_truncated",
        "parent_wall_limit_seconds": WALL_SECONDS, "stdout_stderr_byte_limit_each": MAX_OUTPUT,
        "process_group_cleanup_attempted": cleanup_attempted, "child_stdin_closed": True, "inherited_descriptors_closed": True,
        "temporary_stdio_only": True, "persistent_fixture_artifact_writes": False,
        "parent_exit_diagnostic_written": True, "os_sandbox": False,
        "human_reviews_authenticated": 0, "semantic_labels_admitted": 0, "optimizer_updates": 0,
        "actual_fit_authorized": False, "source_fidelity_established": False, "proof_authority": False,
        "masks": dict.fromkeys(sorted(MASKS), 0),
    })
    exit_binding = write_exclusive(OUTPUT, "replay-exit.json", raw(exit_diagnostic) + b"\n")
    directory_descriptor = os.open(OUTPUT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)
    require(successful, "bounded fixture replay failed; parent exit diagnostic preserved")
    require(returncode == 0 and not errors, "bounded fixture replay failed or emitted stderr")
    require(read_file(FIXTURE_RUNNER, selected["sha256"])[1] == selected, "fixture runner changed during replay")
    require(data.endswith(b"\n") and data[:-1] == raw(parse_json(data)), "fixture replay stdout is not exact canonical JSON")
    return parse_json(data), {"command": command, "returncode": returncode, "wall_seconds": exit_diagnostic["wall_seconds"],
                              "stdout_bytes": len(data), "stderr_bytes": len(errors), "parent_wall_limit_seconds": WALL_SECONDS,
                              "stdout_stderr_byte_limit_each": MAX_OUTPUT, "process_group_cleanup_attempted": True,
                              "temporary_stdio_only": True, "persistent_fixture_artifact_writes": False, "os_sandbox": False,
                              "parent_exit_diagnostic_binding": exit_binding}


def private_directory(path, expected_names):
    require(path.is_dir() and not path.is_symlink() and stat.S_IMODE(path.stat().st_mode) == 0o700, "private evidence directory required")
    require({entry.name for entry in path.iterdir()} == set(expected_names), "unexpected or missing evidence artifacts")
    for entry in path.iterdir():
        require(entry.is_file() and not entry.is_symlink() and stat.S_IMODE(entry.stat().st_mode) == 0o600, "private ordinary evidence file required")


def test_evidence(check):
    data, xml_binding = read_file(LOGS / "tests.xml", limit=MAX_OUTPUT)
    require(b"<!DOCTYPE" not in data and b"<!ENTITY" not in data, "JUnit external declarations forbidden")
    tree = ET.fromstring(data)
    suite = tree if tree.tag == "testsuite" else tree.find("testsuite")
    require(suite is not None and (tree.tag == "testsuite" or len(tree.findall("testsuite")) == 1), "one targeted JUnit suite required")
    counts = {name: int(suite.attrib[name]) for name in ("tests", "errors", "failures", "skipped")}
    require(counts == {"tests": 407, "errors": 0, "failures": 0, "skipped": 0}, "407 successful targeted cases required")
    cases = suite.findall("testcase")
    require(len(cases) == 407 and not any(case.find(tag) is not None for case in cases for tag in ("failure", "error", "skipped")), "JUnit case outcomes differ")
    symbols, counts_by_source, selected_sources = {}, {}, {}
    for filename, expected_count in TEST_COUNTS.items():
        path = TEST.parent / filename
        source, selected = read_file(path)
        check(selected)
        selected_sources[str(path)] = selected
        names = {node.name for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
        require(names and not set(symbols).intersection(names), "test function attribution ambiguous")
        symbols.update(dict.fromkeys(names, filename))
        actual = sum(case.attrib["name"].split("[", 1)[0] in names for case in cases)
        integer(actual, expected_count, "test count for " + filename)
        counts_by_source[filename] = actual
    require(all(case.attrib["name"].split("[", 1)[0] in symbols for case in cases), "unselected test case present")
    command, command_binding = read_json(LOGS / "command.json")
    integer(command["exit_code"], 0, "test command exit")
    require(type(command["command"]) is list and command["command"] and type(command["environment_overrides"]) is dict,
            "test invocation manifest required")
    relative_tests = ["tests/unit/logic/formalization/autoencoder/" + name for name in TEST_COUNTS]
    require(command["cwd"] == str(REPO) and command["command"][:4] == [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest"]
            and command["command"][-5:] == relative_tests
            and "--junitxml=" + str(LOGS / "tests.xml") in command["command"], "test interpreter, cwd or selected cases differ")
    require(command["environment_overrides"].get("IPFS_DATASETS_AUTO_INSTALL_TEST_DEPS") == "0"
            and command["environment_overrides"].get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") == "1", "test auto-installs or plugins not disabled")
    selected_owners = {str(OWNER.parent / filename) for filename in (
        "alignment_review_provenance.py", "alignment_relation_mask_handoff.py", "alignment_relation_declarations.py",
        "alignment_lane_bundle.py", "alignment_stage_declarations.py")}
    command_sources = {item["path"]: item for item in command["checked_source_bindings"]}
    require(len(command["checked_source_bindings"]) == len(command_sources) == 10
            and set(command_sources) == set(selected_sources) | selected_owners
            and all(command_sources[path] == selected for path, selected in selected_sources.items()), "test command source pins differ")
    for item in command["checked_source_bindings"]:
        check(item)
    lint, lint_binding = read_json(LOGS / "ruff-command.json")
    integer(lint["exit_code"], 0, "Ruff exit")
    wanted = {str(path) for path in (OWNER, TEST, UNAVAILABLE_RUNNER, FIXTURE_RUNNER, Path(__file__).resolve())}
    require(type(lint["files"]) is list and len(lint["files"]) == 5
            and {item["path"] for item in lint["checked_source_bindings"]} == wanted
            and len(lint["checked_source_bindings"]) == 5, "five new Ruff source pins required")
    require({str((Path(lint["cwd"]) / path).resolve()) for path in lint["files"]} == wanted
            and type(lint["command"]) is list and "check" in lint["command"], "Ruff selected file arguments differ")
    for item in lint["checked_source_bindings"]:
        check(item)
    require(read_file(LOGS / "ruff.stdout")[0].decode("utf-8").strip() == "All checks passed!", "Ruff success output differs")
    require(read_file(LOGS / "ruff.stderr")[0] == b"" and read_file(LOGS / "pytest.stderr")[0] == b"", "verification command stderr not empty")
    for selected in (xml_binding, command_binding, lint_binding):
        check(selected)
    logs = {}
    for filename in LOG_NAMES:
        data, selected = read_file(LOGS / filename, limit=MAX_OUTPUT)
        check(selected)
        logs[filename] = (data, selected)
    return counts, counts_by_source, logs


def write_exclusive(directory, name, data):
    path = directory / name
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return read_file(path)[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unavailable-assay-sha", required=True, type=sha)
    parser.add_argument("--synthetic-assay-sha", required=True, type=sha)
    args = parser.parse_args()
    require(not FORBIDDEN.intersection(sys.modules), "collector parent must start without crypto/model runtimes")
    sys.dont_write_bytecode = True
    sys.meta_path.insert(0, RejectRuntime())
    checked = {}

    def check(selected):
        require(type(selected) is dict and set(selected) == {"path", "bytes", "sha256"}
                and type(selected["path"]) is str and Path(selected["path"]).is_absolute()
                and type(selected["bytes"]) is int and 0 <= selected["bytes"] <= MAX_FILE, "closed ordinary file binding required")
        actual = read_file(selected["path"], selected["sha256"])[1]
        require(actual == selected, "bound file changed: " + selected["path"])
        require(selected["path"] not in checked or checked[selected["path"]] == selected, "conflicting file generations")
        checked[selected["path"]] = selected

    prior, prior_binding = read_json(PRIOR, PRIOR_SHA)
    require(type(prior["checked_file_bindings"]) is list, "prior file inventory required")
    for selected in prior["checked_file_bindings"]:
        check(selected)
    require(len(checked) == prior["checked_file_count"] == 245, "preceding245 file accounting differs")
    require(prior["human_reviews_authenticated"] == 0 and prior["actual_fit_authorized"] is False, "preceding review authority differs")
    check(prior_binding)
    unavailable, unavailable_binding = read_json(OUTPUT / "unavailable/assay.json", args.unavailable_assay_sha)
    synthetic, synthetic_binding = read_json(OUTPUT / "synthetic/assay.json", args.synthetic_assay_sha)
    require(unavailable["schema"] == "alignment-review-provenance-unavailable-assay/v1"
            and synthetic["schema"] == "alignment-review-provenance-synthetic-assay/v1", "saved assay schemas differ")
    require(unavailable["status"] == "completed_unavailable_registry_preflight_only"
            and synthetic["status"] == "passed_disposable_fixture_signature_math_only", "saved assay outcomes differ")
    for selected in (unavailable_binding, synthetic_binding, *iter_bindings(unavailable), *iter_bindings(synthetic)):
        check(selected)
    check(read_file(OWNER, OWNER_SHA)[1])
    check(read_file(TEST, TEST_SHA)[1])
    require(len(unavailable["source_bindings"]) == 7 and len(synthetic["source_bindings"]) == 10
            and len(synthetic["provider_bindings"]) == 3, "explicit source/provider inventory differs")
    sources = {item["path"]: item for item in unavailable["source_bindings"]}
    require(str(IO) in sources and sources[str(IO)]["sha256"] == IO_SHA
            and str(UNAVAILABLE_RUNNER) in sources and str(OWNER) in sources and sources[str(OWNER)]["sha256"] == OWNER_SHA,
            "unavailable source selections differ")
    selected_module(IO, IO_SHA, "assay_relation_readiness")
    assay = selected_module(UNAVAILABLE_RUNNER, sources[str(UNAVAILABLE_RUNNER)]["sha256"], "root_selected_unavailable_review_assay")
    prepared = assay.prepare_assay()
    require(not FORBIDDEN.intersection(sys.modules), "crypto/model runtime entered unavailable replay")
    owner = sys.modules["ipfs_datasets_py.logic.formalization.autoencoder.alignment_review_provenance"]
    require(Path(owner.__file__).resolve() == OWNER, "unavailable replay owner differs")
    saved_unavailable = {}
    require(set(unavailable["artifacts"]) == {"registry", "policy", "attestations", "expected_bindings", "verification"}, "unavailable artifact closure differs")
    for name, selected in unavailable["artifacts"].items():
        value, observed = read_json(selected["path"], selected["sha256"])
        check(observed)
        require(raw(value) == raw(prepared[name]), "complete unavailable replay differs: " + name)
        saved_unavailable[name] = value
    require(unavailable["input_file_bindings"] == prepared["input_file_bindings"]
            and unavailable["source_bindings"] == prepared["source_bindings"], "unavailable selected provenance differs")
    receipt = saved_unavailable["verification"]
    check_verification(receipt, 16, owner)
    require(receipt["status"] == "unavailable_review_process" and saved_unavailable["registry"]["keys"] == []
            and saved_unavailable["registry"]["process_id"] is None and saved_unavailable["attestations"]["rows"] == [], "actual registry/review unavailable state differs")
    for name, expected in (("missing_attestation_slot_count", 544), ("signature_checks_executed", 0), ("valid_signature_count", 0),
                           ("attestation_count", 0), ("unassociated_attestation_count", 0)):
        integer(receipt[name], expected, name)
    require(all(row["status"] == "missing_attestation" and row["attestation_id"] is None and row["signature_valid"] is False
                and row["declared_fixture_scope_permitted"] is False for row in (*receipt["endpoint_signature_ledger"], *receipt["pair_signature_ledger"])),
            "actual review ledger inferred evidence")
    zero_authority(unavailable)
    for key in ("actual_registry_selected", "actual_review_process_selected", "authentic_review_packages_accessed", "cryptography_imported",
                "torch_imported", "formal_target_body_read", "query_reference_panel_accessed", "original_train_masks_modified",
                "existing_losses_or_checkpoints_modified", "accepted", "qualified"):
        require(unavailable[key] is False, "actual preflight scope differs: " + key)
    for key in ("attestations_submitted", "signature_verification_calls", "keys_initialized", "model_calls", "encoder_calls", "prover_calls"):
        integer(unavailable[key], 0, key)
    integer(unavailable["train_row_count"], 16, "actual TRAIN count")
    integer(unavailable["ordered_pair_count"], 256, "actual ordered pair count")
    synthetic_sources = {item["path"]: item for item in synthetic["source_bindings"]}
    require(len(synthetic_sources) == 10 and str(FIXTURE_RUNNER) in synthetic_sources
            and synthetic_sources[str(OWNER)]["sha256"] == OWNER_SHA and synthetic_sources[str(TEST)]["sha256"] == TEST_SHA,
            "fixture source pins differ")
    require({item["path"]: item["sha256"] for item in synthetic["provider_bindings"]} == PROVIDER_SHAS,
            "selected rootvenv provider bytes differ")
    replayed, replay_execution = replay_fixtures(synthetic_sources[str(FIXTURE_RUNNER)], synthetic["source_bindings"], synthetic["provider_bindings"])
    check(replay_execution["parent_exit_diagnostic_binding"])
    require(set(replayed) == {"fixture", "fixture_activity", "baseline_verification", "tampered_attestations", "tampered_expected_bindings",
                              "tampered_verification", "source_bindings", "provider_bindings"}, "fixture replay output is not closed")
    require(set(synthetic["artifacts"]) == {"fixture", "baseline_verification", "tampered_attestations", "tampered_expected_bindings", "tampered_verification"},
            "synthetic artifact closure differs")
    saved_synthetic = {}
    for name, selected in synthetic["artifacts"].items():
        value, observed = read_json(selected["path"], selected["sha256"])
        check(observed)
        require(raw(value) == raw(replayed[name]), "complete synthetic replay differs: " + name)
        saved_synthetic[name] = value
    for name in ("fixture_activity", "source_bindings", "provider_bindings"):
        require(raw(synthetic[name]) == raw(replayed[name]), "fixture replay provenance differs: " + name)
    activity = {"deterministic_private_key_objects_initialized": 2, "random_key_generation_calls": 0, "signatures_created": 12}
    require(synthetic["fixture_activity"] == activity and all(type(value) is int for value in synthetic["fixture_activity"].values()), "fixture activity differs")
    for name, expected in (("baseline_signature_checks", 12), ("baseline_valid_signatures", 12),
                           ("tampered_signature_checks", 12), ("tampered_valid_signatures", 11), ("tampered_denied_signatures", 1)):
        integer(synthetic[name], expected, "saved assay " + name)
    require(synthetic["single_signature_bit_corruption_denied"] is True, "saved corruption result differs")
    fixture = saved_synthetic["fixture"]
    require(set(fixture) == {"declaration", "handoff_envelope", "registry", "policy", "attestations", "expected_bindings"}
            and len(fixture["registry"]["keys"]) == 2 and len(fixture["attestations"]["rows"]) == 12, "complete two-key disposable fixture required")
    baseline, denied = saved_synthetic["baseline_verification"], saved_synthetic["tampered_verification"]
    for value, valid, denied_count in ((baseline, 12, 0), (denied, 11, 1)):
        check_verification(value, 2, owner)
        for name, expected in (("attestation_count", 12), ("signature_checks_executed", 12), ("valid_signature_count", valid),
                               ("declared_fixture_scope_permitted_count", valid), ("denied_attestation_count", denied_count), ("missing_attestation_slot_count", 0)):
            integer(value[name], expected, name)
        require(value["status"] == "synthetic_signature_diagnostics_only" and len(value["attestation_rows"]) == 12
                and all(row["human_review_authenticated"] is False and row["actual_fit_authorized"] is False for row in value["attestation_rows"]),
                "fixture claim promoted authentic reviews")
    require(denied["attestation_rows"][0]["signature_status"] == "invalid" and denied["attestation_rows"][0]["denial_reasons"] == ["signature_invalid"],
            "corrupted fixture signature denial differs")
    tampered = deepcopy(fixture["attestations"])
    entry = tampered["rows"][0]
    bits = bytearray.fromhex(entry["signature_hex"])
    require(len(bits) == 64, "complete fixture signature required")
    bits[0] ^= 1
    entry["signature_hex"] = bytes(bits).hex()
    entry.pop("content_sha256")
    tampered["rows"][0] = seal(entry)
    tampered.pop("content_sha256")
    tampered = seal(tampered)
    require(raw(tampered) == raw(saved_synthetic["tampered_attestations"]), "tampering changed more than selected signature bit and seals")
    tampered_pins = deepcopy(fixture["expected_bindings"])
    tampered_pins["attestations_sha256"] = digest(tampered)
    require(raw(tampered_pins) == raw(saved_synthetic["tampered_expected_bindings"]), "tampered pin recipe differs")
    zero_authority(synthetic)
    for key in ("authentic_registry_selected", "genuine_human_keys_created", "torch_imported", "real_train_data_used", "os_sandbox"):
        require(synthetic[key] is False, "synthetic scope differs: " + key)
    for key in ("numerical_objectives_executed", "model_calls", "encoder_calls", "prover_calls"):
        integer(synthetic[key], 0, key)
    require(synthetic["crypto_provider_version"] == "44.0.0" and synthetic["trusted_resource_bounded_worker"] is True
            and synthetic["resource_limits"] == {"cpu_soft_seconds": 10, "cpu_hard_seconds": 15, "address_space_bytes": 768 * 1024**2,
                "parent_wall_seconds": 30, "max_output_file_bytes": MAX_OUTPUT}, "saved fixture resource contract differs")
    observations = synthetic["resource_observations"]
    require([row["label"] for row in observations] == ["before_source_imports", "before_fixture", "after_fixture_signing", "after_baseline_verification", "after_all_checks"],
            "saved worker resource checkpoints differ")
    for index, row in enumerate(observations):
        require(set(row) == {"label", "wall_seconds", "user_cpu_seconds", "system_cpu_seconds", "peak_rss_kib"}, "closed resource observation required")
        for key in ("wall_seconds", "user_cpu_seconds", "system_cpu_seconds"):
            require(type(row[key]) in (int, float) and math.isfinite(row[key]) and row[key] >= 0
                    and (index == 0 or row[key] >= observations[index - 1][key]), "resource observation nonfinite or nonmonotonic")
        require(row["wall_seconds"] < WALL_SECONDS and row["user_cpu_seconds"] + row["system_cpu_seconds"] < 15
                and type(row["peak_rss_kib"]) is int and 0 < row["peak_rss_kib"] < 768 * 1024, "saved worker exceeds selected bounds")
    exit_receipt, exit_binding = read_json(OUTPUT / "synthetic/child_exit.json")
    check(exit_binding)
    require(exit_receipt["returncode"] == 0 and type(exit_receipt["returncode"]) is int
            and exit_receipt["stdout_bytes"] == exit_receipt["stderr_bytes"] == 0 and exit_receipt["stderr_utf8"] == ""
            and exit_receipt["source_bindings"] == synthetic["source_bindings"] and exit_receipt["actual_fit_authorized"] is False,
            "saved fixture child exit or source joins differ")
    integer(exit_receipt["optimizer_updates"], 0, "child optimizer updates")
    require(exit_receipt["command"] == [str(ROOT / ".venv/bin/python"), "-I", "-B", str(FIXTURE_RUNNER), "--worker",
                "--output-directory", str(OUTPUT / "synthetic"), "--owner-sha", OWNER_SHA, "--test-sha", TEST_SHA], "saved bounded worker invocation differs")
    private_directory(OUTPUT / "unavailable", {"assay.json", *(name + ".json" for name in saved_unavailable)})
    private_directory(OUTPUT / "synthetic", {"assay.json", "child_exit.json", *(name + ".json" for name in saved_synthetic)})
    require(OUTPUT.is_dir() and not OUTPUT.is_symlink() and stat.S_IMODE(OUTPUT.stat().st_mode) == 0o700, "private outer generation required")
    counts, source_counts, logs = test_evidence(check)
    document, document_binding = read_file(DOCUMENT, limit=MAX_JSON)
    check(document_binding)
    links = []
    for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", document.decode("utf-8")):
        if target.startswith(("http://", "https://", "#")):
            continue
        path = (DOCUMENT.parent / target.split("#", 1)[0]).resolve()
        require(path == OUTPUT / "validation.json" or path.is_file(), "local documentation link missing: " + str(path))
        links.append(str(path))
        if path != OUTPUT / "validation.json":
            check(read_file(path)[1])
    check(read_file(Path(__file__).resolve())[1])
    require(not any((OUTPUT / name).exists() for name in (*LOG_NAMES, "validation.json")), "fresh exclusive collector outputs required")
    for selected in list(checked.values()):
        check(selected)
    copied_logs = {}
    for name, (data, selected) in logs.items():
        require(read_file(selected["path"], selected["sha256"])[0] == data, "root evidence changed before copy")
        copied = write_exclusive(OUTPUT, name, data)
        require(copied["bytes"] == selected["bytes"] and copied["sha256"] == selected["sha256"], "log copy differs")
        check(copied)
        copied_logs[name] = {"original": selected, "published_copy": copied}
    result = seal({
        "schema": "autoformalization-review-provenance-validation/v1", "status": "passed_unavailable_review_and_disposable_signature_math_only",
        "created_utc": datetime.now(UTC).isoformat(), "checked_file_count": len(checked),
        "checked_file_bindings": sorted(checked.values(), key=lambda selected: selected["path"]),
        "prior_relation_mask_handoff_binding": prior_binding, "prior245_file_bindings_rechecked": True,
        "older554_file_chain_rechecked": False, "complete_dependency_manifest": False,
        "unavailable_assay_binding": unavailable_binding, "synthetic_assay_binding": synthetic_binding,
        "document_binding": document_binding, "local_link_count": len(links), "root_log_bindings": copied_logs,
        "targeted_test_counts": counts, "test_counts_by_source_function_names": source_counts,
        "new_review_provenance_test_count": source_counts[TEST.name], "final_ruff_passed": True, "ruff_checked_files": 5,
        "unavailable_exact_replay_before_any_crypto_import": True, "collector_parent_cryptography_imported": False,
        "saved_fixture_inputs_and_checks_exact_no_write_replay": True, "fixture_replay_execution": replay_execution,
        "actual_train_row_count": 16, "actual_ordered_pair_count": 256, "actual_endpoint_signature_slots": 32,
        "actual_pair_signature_slots": 512, "actual_missing_signature_slots": 544, "actual_signature_checks": 0,
        "actual_keys_initialized": 0, "actual_registry_selected": False, "actual_review_process_selected": False,
        "synthetic_private_key_objects_initialized_per_fixture_run": 2, "synthetic_signatures_created_per_fixture_run": 12,
        "synthetic_random_key_generation_calls": 0, "synthetic_baseline_valid_signatures": 12,
        "synthetic_tampered_valid_signatures": 11, "synthetic_tampered_denied_signatures": 1,
        "original_canary_signature_checks": 24, "collector_no_write_replay_signature_checks": 24,
        "original_canary_signatures_created": 12, "collector_no_write_replay_signatures_created": 12,
        "signature_activity_scope": "source_reviewed_fixture_calls_per_run_not_global_framework_or_test_instrumentation",
        "single_signature_bit_mutation_seals_and_external_pins_rechecked": True, "crypto_provider_version": "44.0.0",
        "provider_binding_count": 3, "provider_selection_scope": "three_explicit_provider_files_not_complete_binary_dependency_closure",
        "source_selection_scope": "explicit_campaign_and_owner_files_not_complete_dependency_closure",
        "signature_scope": "fixture_key_payload_integrity_only_not_human_identity_independence_or_semantic_verification",
        "registry_selection_authenticated": False, "human_reviews_authenticated": 0, "independent_reviews_authenticated": 0,
        "semantic_labels_admitted": 0, "admitted_positive_pair_count": 0, "admitted_negative_pair_count": 0,
        "actual_fit_authorized": False, "masks": dict.fromkeys(sorted(MASKS), 0), "source_fidelity_established": False,
        "proof_authority": False, "accepted": False, "qualified": False, "actual_training_or_evaluation_admission": False,
        "numerical_objectives_executed": 0, "model_calls": 0, "encoder_calls": 0, "prover_calls": 0, "optimizer_updates": 0,
        "actual_train_uses_synthetic_review_assertions": False, "genuine_human_keys_created": False, "genuine_human_reviews_created": False,
        "original_train_masks_modified": False, "existing_losses_or_checkpoints_modified": False, "production_defaults_changed": False,
        "os_sandbox": False, "os_reference_confinement_established": False, "derivative_exclusion_authenticated": False,
        "review_reference_contents_verified": False, "current_revocation_status_verified": False, "evaluation_clock_authenticated": False,
        "broad_pilot_family_count": 40, "broad_pilot_semantic_evaluation_executed": False,
        "prior_existing_legacy_manifest_mismatch_preserved": prior["prior_existing_legacy_manifest_mismatch_preserved"],
        "prior_standalone_numerical_launcher_ordering_limitation_preserved": True,
        "prior_standalone_signature_launcher_failure_evidence_limitation_preserved": True,
        "standalone_signature_launcher_failure_paths_qualified": False,
        "fixture_transitive_dependencies_verified_before_execution": False,
        "selected_fixture_source_bindings_rechecked_before_and_after_replay": True,
        "standalone_numerical_launcher_qualified": False, "renderer_preview_inspected": False,
    })
    require(not FORBIDDEN.intersection(sys.modules), "optional runtime entered collector parent")
    for selected in list(checked.values()):
        check(selected)
    output_binding = write_exclusive(OUTPUT, "validation.json", raw(result) + b"\n")
    descriptor = os.open(OUTPUT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    print(json.dumps({"validation_binding": output_binding, "checked_files": len(checked), "targeted_tests": counts["tests"],
                      "new_tests": source_counts[TEST.name], "actual_train_pairs": 256, "actual_admitted_pairs": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
