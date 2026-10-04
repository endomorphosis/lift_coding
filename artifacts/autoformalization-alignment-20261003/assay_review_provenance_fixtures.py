"""Bounded disposable fixture signature canary, separate from actual reviews."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import resource
import signal
import subprocess
import sys
import tempfile
import time
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = Path(__file__).resolve().parent
OUTPUT = CAMPAIGN / "review-provenance-01/synthetic"
OWNER = REPO / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_review_provenance.py"
TEST = REPO / "tests/unit/logic/formalization/autoencoder/test_alignment_review_provenance.py"
CRYPTO_ROOT = ROOT / ".venv/lib/python3.12/site-packages/cryptography"
MAX_OUTPUT = 8 * 1024**2
WALL_SECONDS = 30


def load_io():
    path = CAMPAIGN / "assay_relation_readiness.py"
    data = path.read_bytes()
    expected = "39f327de0787d4fdb3a13ac3a9bb784d0916cf911e24ecd3f12cc9c403f0b320"
    if not 0 < len(data) <= 16 * 1024**2 or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("frozen stdlib I/O helper differs before execution")
    spec = importlib.util.spec_from_file_location("assay_relation_readiness", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["assay_relation_readiness"] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


io = load_io()


def selected_module(path, expected_sha, name):
    """Verify before compiling those same bytes; import no unverified helper."""
    data = path.read_bytes()
    io.require(0 < len(data) <= 16 * 1024**2 and hashlib.sha256(data).hexdigest() == expected_sha,
               "explicitly selected fixture source differs before execution")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def provider_bindings():
    distribution = importlib.metadata.distribution("cryptography")
    io.require(distribution.version == "44.0.0" and Path(distribution.locate_file("cryptography")).resolve() == CRYPTO_ROOT,
               "selected rootvenv cryptography installation required")
    paths = [CRYPTO_ROOT / "__init__.py", CRYPTO_ROOT / "hazmat/primitives/asymmetric/ed25519.py",
             CRYPTO_ROOT / "hazmat/bindings/_rust.abi3.so"]
    return [io.read(path, parse=False)[1] for path in paths]


def implementation_bindings(owner_sha, test_sha):
    io.require(io.read(OWNER, owner_sha, parse=False)[1]["sha256"] == owner_sha, "owner selection differs")
    io.require(io.read(TEST, test_sha, parse=False)[1]["sha256"] == test_sha, "test helper selection differs")
    paths = [Path(__file__), Path(io.__file__), OWNER, TEST,
             *(REPO / "ipfs_datasets_py/logic/formalization/autoencoder" / name for name in
               ("alignment_lane_bundle.py", "alignment_stage_declarations.py", "alignment_relation_declarations.py",
                "alignment_relation_mask_handoff.py")),
             REPO / "tests/unit/logic/formalization/autoencoder/test_alignment_relation_mask_handoff.py",
             REPO / "tests/unit/logic/formalization/autoencoder/test_alignment_relation_declarations.py"]
    return [io.read(path, parse=False)[1] for path in paths]


def prepare_fixture_assay(owner_sha, test_sha, observe=None):
    """Two detached checks from one authored fixture; write no persistent files."""
    sources_before = implementation_bindings(owner_sha, test_sha)
    provider_before = provider_bindings()
    callback = observe if observe is not None else lambda _label: None
    io.owners()
    owner = selected_module(OWNER, owner_sha,
                            "ipfs_datasets_py.logic.formalization.autoencoder.alignment_review_provenance")
    sys.path.insert(0, str(TEST.parent))
    tests = selected_module(TEST, test_sha, "root_selected_review_provenance_fixture")
    callback("before_fixture")
    fixture = tests.provenance_fixture(n=2)
    callback("after_fixture_signing")
    activity = fixture["fixture_activity"]
    io.require(activity == {"deterministic_private_key_objects_initialized": 2,
                           "random_key_generation_calls": 0, "signatures_created": 12}, "fixture activity contract differs")
    required = ("declaration", "handoff_envelope", "registry", "policy", "attestations", "expected_bindings")
    io.require(all(name in fixture for name in required), "complete authored provenance fixture required")
    io.require(len(fixture["registry"]["keys"]) == 2 and len(fixture["attestations"]["rows"]) == 12,
               "two fixture keys and twelve authored signatures required")
    arguments = [fixture[name] for name in required[:-1]]
    baseline = owner.verify_train_review_provenance(*arguments, expected_bindings=fixture["expected_bindings"])
    io.require(baseline["signature_checks_executed"] == baseline["valid_signature_count"]
               == baseline["declared_fixture_scope_permitted_count"] == 12 and baseline["denied_attestation_count"] == 0,
               "authored signatures did not all pass selected fixture scope")
    callback("after_baseline_verification")
    tampered = deepcopy(fixture["attestations"])
    entry = tampered["rows"][0]
    signature = bytearray.fromhex(entry["signature_hex"])
    signature[0] ^= 1
    entry["signature_hex"] = bytes(signature).hex()
    entry.pop("content_sha256")
    tampered["rows"][0] = io.seal(entry)
    tampered.pop("content_sha256")
    tampered = io.seal(tampered)
    tampered_pins = deepcopy(fixture["expected_bindings"])
    tampered_pins["attestations_sha256"] = io.digest(tampered)
    denied = owner.verify_train_review_provenance(*arguments[:-1], tampered, expected_bindings=tampered_pins)
    io.require(denied["signature_checks_executed"] == 12 and denied["valid_signature_count"]
               == denied["declared_fixture_scope_permitted_count"] == 11 and denied["denied_attestation_count"] == 1,
               "single corrupted signature did not remain denied")
    io.require(denied["attestation_rows"][0]["signature_status"] == "invalid", "corrupted signature status differs")
    for result in (baseline, denied):
        io.require(result["actual_fit_authorized"] is False and result["human_reviews_authenticated"] == 0
                   and all(mask == 0 for mask in result["masks"].values()), "fixture signature promoted authority")
        for name in ("objective_positive_mask", "objective_permitted_negative_mask", "admitted_positive_mask", "admitted_permitted_negative_mask"):
            io.require(all(value is False for row in result[name] for value in row), "signature promoted a mask")
    io.require(implementation_bindings(owner_sha, test_sha) == sources_before and provider_bindings() == provider_before,
               "fixture implementation or provider changed")
    import cryptography
    from cryptography.hazmat.bindings import _rust
    from cryptography.hazmat.primitives.asymmetric import ed25519

    io.require(cryptography.__version__ == "44.0.0"
               and {str(Path(module.__file__).resolve()) for module in (cryptography, ed25519, _rust)}
               == {selected["path"] for selected in provider_before}, "loaded provider paths differ")
    callback("after_all_checks")
    return {"fixture": {name: fixture[name] for name in required}, "fixture_activity": activity,
            "baseline_verification": baseline, "tampered_attestations": tampered,
            "tampered_expected_bindings": tampered_pins, "tampered_verification": denied,
            "source_bindings": sources_before, "provider_bindings": provider_before}


def apply_resource_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (10, 15))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT, MAX_OUTPUT))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def worker(output, owner_sha, test_sha):
    apply_resource_limits()
    started = time.monotonic()
    observations = []

    def observe(label):
        usage = resource.getrusage(resource.RUSAGE_SELF)
        observations.append({"label": label, "wall_seconds": time.monotonic() - started,
                             "user_cpu_seconds": usage.ru_utime, "system_cpu_seconds": usage.ru_stime,
                             "peak_rss_kib": usage.ru_maxrss})

    try:
        observe("before_source_imports")
        prepared = prepare_fixture_assay(owner_sha, test_sha, observe)
        selected = {name: io.save(output, name + ".json", prepared[name]) for name in
                    ("fixture", "baseline_verification", "tampered_attestations", "tampered_expected_bindings", "tampered_verification")}
        report = io.seal({
            "schema": "alignment-review-provenance-synthetic-assay/v1", "created_utc": datetime.now(UTC).isoformat(),
            "status": "passed_disposable_fixture_signature_math_only", "artifacts": selected,
            "source_bindings": prepared["source_bindings"], "provider_bindings": prepared["provider_bindings"],
            "fixture_activity": prepared["fixture_activity"], "fixture_activity_scope": "counted_source_reviewed_helper_not_global_framework_hook",
            "baseline_signature_checks": 12, "baseline_valid_signatures": 12,
            "tampered_signature_checks": 12, "tampered_valid_signatures": 11, "tampered_denied_signatures": 1,
            "single_signature_bit_corruption_denied": True, "crypto_provider_version": "44.0.0",
            "resource_observations": observations, "trusted_resource_bounded_worker": True, "os_sandbox": False,
            "resource_limits": {"cpu_soft_seconds": 10, "cpu_hard_seconds": 15, "address_space_bytes": 768 * 1024**2,
                                "parent_wall_seconds": WALL_SECONDS, "max_output_file_bytes": MAX_OUTPUT},
            "authentic_registry_selected": False, "genuine_human_keys_created": False, "human_reviews_authenticated": 0,
            "source_fidelity_established": False, "semantic_labels_admitted": 0, "proof_authority": False,
            "actual_fit_authorized": False, "numerical_objectives_executed": 0,
            "model_calls": 0, "encoder_calls": 0, "prover_calls": 0, "optimizer_updates": 0,
            "masks": dict.fromkeys(prepared["baseline_verification"]["masks"], 0),
            "torch_imported": "torch" in sys.modules, "real_train_data_used": False,
            "provider_selection_scope": "three_explicit_provider_files_not_complete_binary_dependency_closure",
        })
        io.require(report["torch_imported"] is False, "model stack entered fixture math")
        io.save(output, "assay.json", report)
        return 0
    except BaseException as error:
        io.save(output, "failure.json", io.seal({"status": "failed_fixture_check_no_admission",
            "error_type": type(error).__name__, "error_message": str(error), "resource_observations": observations,
            "human_reviews_authenticated": 0, "optimizer_updates": 0, "actual_fit_authorized": False}))
        return 1


def run_bounded(output, owner_sha, test_sha):
    before = implementation_bindings(owner_sha, test_sha)
    output = output.resolve()
    io.require(not output.exists() and output.parent.is_dir(), "fresh fixture directory beneath existing campaign required")
    output.mkdir(mode=0o700)
    command = [str(ROOT / ".venv/bin/python"), "-I", "-B", str(Path(__file__).resolve()), "--worker",
               "--output-directory", str(output), "--owner-sha", owner_sha, "--test-sha", test_sha]
    environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
                   "IPFS_DATASETS_AUTO_INSTALL_TEST_DEPS": "0", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(command, cwd=output, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            process.wait(timeout=WALL_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise TimeoutError("fixture signature canary exceeded wall limit") from None
        io.require(stdout.tell() <= MAX_OUTPUT and stderr.tell() <= MAX_OUTPUT, "fixture child output exceeded")
        stdout.seek(0)
        stderr.seek(0)
        data, errors = stdout.read(MAX_OUTPUT + 1), stderr.read(MAX_OUTPUT + 1)
    io.save(output, "child_exit.json", io.seal({"returncode": process.returncode, "command": command,
        "stdout_bytes": len(data), "stderr_bytes": len(errors), "stderr_utf8": errors.decode("utf-8", "replace"),
        "source_bindings": before, "optimizer_updates": 0, "actual_fit_authorized": False}))
    io.require(process.returncode == 0, "fixture signature child failed; evidence preserved")
    io.require(implementation_bindings(owner_sha, test_sha) == before, "fixture source changed during bounded run")
    return io.read(output / "assay.json")[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, default=OUTPUT)
    parser.add_argument("--owner-sha", required=True)
    parser.add_argument("--test-sha", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--worker", action="store_true")
    mode.add_argument("--replay-only", action="store_true", help="bounded no-file replay; caller must enforce the wall limit")
    args = parser.parse_args()
    for value in (args.owner_sha, args.test_sha):
        io.require(type(value) is str and len(value) == 64 and all(char in "0123456789abcdef" for char in value), "canonical selected source SHA required")
    if args.worker or args.replay_only:
        pid = os.fork()
        if pid == 0:
            if args.replay_only:
                apply_resource_limits()
                prepared = prepare_fixture_assay(args.owner_sha, args.test_sha)
                data = json.dumps(prepared, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                io.require(len(data) < MAX_OUTPUT, "replay output exceeded")
                sys.stdout.buffer.write(data + b"\n")
                sys.stdout.buffer.flush()
                os._exit(0)
            os._exit(worker(args.output_directory.resolve(), args.owner_sha, args.test_sha))
        _pid, status = os.waitpid(pid, 0)
        raise SystemExit(os.WEXITSTATUS(status) if os.WIFEXITED(status) else 128 + os.WTERMSIG(status))
    print(json.dumps({"assay_binding": run_bounded(args.output_directory, args.owner_sha, args.test_sha)}, sort_keys=True))


if __name__ == "__main__":
    main()
