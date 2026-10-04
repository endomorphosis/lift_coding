"""Explicit native-site recovery for the frozen synthetic numerical helper.

Selecting the native user site does not process its .pth files. Publication and temporary no-write replay use a
fresh bounded CPU child; the frozen original checks and first failed files are
preserved exactly.  Selecting a Torch installation is not a model attestation.
"""
from __future__ import annotations

import argparse
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
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parent
HELPER_PATH = CAMPAIGN / "assay_masked_contrastive.py"
HELPER_SHA256 = "7e428638cce2f3f011747fa8bc50502518a48665009e5f2aa9395097531411bb"
TRUSTED_SITE = Path("/home/barberb/.local/lib/python3.12/site-packages")
TORCH_INIT = TRUSTED_SITE / "torch/__init__.py"
TORCH_INIT_SHA256 = "cf40c075c95864036e835795756d69b8cccfafa76f3bcde5eba9d06065ccd3d1"
DEFAULT_OUTPUT = CAMPAIGN / "masked-contrastive-01/numerical-02"
FAILED_FILES = {
    "failure.json": "3421dd50397c2a00a88cba8f6a1298e0dab6ec2b9e2144e20a3dadc895ed2c39",
    "child_exit.json": "be6c759906081f70902c29b2d5f31c332903bbe0fe3f52c990f7e8ea1e370a02",
    "resource_observations.jsonl": "92d06b3b4b3cd1cde1496a78faf4855dc3c7acab4f87a1e936acdc398b163d03",
}


def _helper():
    spec = importlib.util.spec_from_file_location("frozen_masked_contrastive_assay", HELPER_PATH)
    helper = importlib.util.module_from_spec(spec)
    previous_bytecode_policy = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(helper)
    finally:
        sys.dont_write_bytecode = previous_bytecode_policy
    helper.require(helper.binding(HELPER_PATH)["sha256"] == HELPER_SHA256, "frozen helper pin differs")
    return helper


def _native_site(helper):
    helper.require(TORCH_INIT.resolve() == TORCH_INIT and helper.binding(TORCH_INIT)["sha256"] == TORCH_INIT_SHA256,
                   "selected native Torch initializer pin differs")
    # Explicit path insertion does not execute .pth files or user-site startup.
    if str(TRUSTED_SITE) not in sys.path:
        sys.path.insert(0, str(TRUSTED_SITE))
    distribution = importlib.metadata.distribution("torch")
    helper.require(distribution.version == "2.13.0"
                   and Path(distribution.locate_file("torch/__init__.py")).resolve() == TORCH_INIT,
                   "selected native distribution differs")
    return {"trusted_site": str(TRUSTED_SITE), "site_selection_method": "sys.path.insert_only_no_addsitedir_no_pth",
            "torch_distribution_version": distribution.version, "torch_init_binding": helper.binding(TORCH_INIT),
            "torch_distribution_scope": "initializer_and_distribution_selection_not_all_package_binary_files_pinned"}


def _selection(helper):
    failed = {}
    for filename, expected in FAILED_FILES.items():
        selected = helper.binding(CAMPAIGN / "masked-contrastive-01/numerical" / filename)
        helper.require(selected["sha256"] == expected, "first failed attempt binding differs")
        failed[filename] = selected
    return helper.sealed({
        "schema": "alignment-masked-contrastive-native-selection/v1",
        "driver_binding": helper.binding(Path(__file__).resolve()),
        "original_implementation_bindings": helper.implementation_bindings(),
        "failed_attempt_bindings": failed,
        "failed_attempt_status": "torch_import_unavailable_under_isolated_mode_before_numerical_work",
        "failed_attempt_numerical_objective_calls": 0, "failed_attempt_fixture_initializations": 0,
        "failed_attempt_optimizer_updates": 0, "original_helper_modified": False,
        "masks": dict.fromkeys(helper.MASK_NAMES, 0), **_native_site(helper), **helper.FALSE_FLAGS,
    })


def _replay_child(helper):
    resource.setrlimit(resource.RLIMIT_CPU, (helper.CPU_SOFT_SECONDS, helper.CPU_HARD_SECONDS))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (helper.MAX_OUTPUT_BYTES, helper.MAX_OUTPUT_BYTES))
    start = time.monotonic()

    def observe(_label):
        values = helper._linux_resource()
        helper.require(max(values["linux_current_rss_kib"], values["linux_peak_hwm_kib"],
                           values["resource_ru_maxrss_kib"]) < helper.MAX_RSS_KIB,
                       "temporary numerical replay exceeded cooperative RSS budget")
        helper.require(time.monotonic() - start < helper.WALL_SECONDS, "temporary replay wall limit exceeded")

    observe("before_torch_import")
    guard = helper._NoEncoderImports()
    sys.meta_path.insert(0, guard)
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    helper.require(Path(torch.__file__).resolve() == TORCH_INIT and not torch.cuda.is_initialized(),
                   "native Torch import path or CUDA state differs")
    load_attempts = []

    def no_load(*_args, **_kwargs):
        load_attempts.append(True)
        raise ValueError("checkpoint/model loading prohibited in temporary synthetic replay")

    torch.load = no_load
    torch.hub.load = no_load
    torch.hub.load_state_dict_from_url = no_load
    observe("after_torch_import")
    checks = helper.prepare_numerical_assay(observe=observe)
    helper.require(not load_attempts and not guard.attempts and not torch.cuda.is_initialized(),
                   "temporary replay observed forbidden imports/loading/CUDA")
    observe("after_checks")
    sys.stdout.buffer.write(helper.raw(checks) + b"\n")
    sys.stdout.buffer.flush()
    return 0


def _child(helper, output, replay):
    _native_site(helper)
    if not replay:
        return helper._fresh_worker(output, helper.REPOSITORY)
    worker_pid = os.fork()
    if worker_pid == 0:
        os._exit(_replay_child(helper))
    _pid, status = os.waitpid(worker_pid, 0)
    return os.WEXITSTATUS(status) if os.WIFEXITED(status) else 128 + os.WTERMSIG(status)


def _invoke(helper, output, replay):
    environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "CUDA_VISIBLE_DEVICES": "",
                   "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                   "PYTHONDONTWRITEBYTECODE": "1", "IPFS_DATASETS_AUTO_INSTALL_TEST_DEPS": "0",
                   "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    command = [str(helper.NATIVE_PYTHON), "-I", "-B", str(Path(__file__).resolve()), "--child"]
    command += ["--replay-only"] if replay else ["--output-directory", str(output)]
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(command, cwd=output if output is not None else "/tmp", env=environment,
                                   stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            process.wait(timeout=helper.WALL_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise TimeoutError("native synthetic child exceeded parent wall limit") from None
        stdout_size = stdout.tell()
        stderr_size = stderr.tell()
        helper.require(stdout_size <= helper.MAX_OUTPUT_BYTES and stderr_size <= helper.MAX_OUTPUT_BYTES,
                       "bounded child output exceeded")
        stdout.seek(0)
        stderr.seek(0)
        data = stdout.read(helper.MAX_OUTPUT_BYTES + 1)
        errors = stderr.read(helper.MAX_OUTPUT_BYTES + 1)
    return {"command": command, "returncode": process.returncode, "stdout": data, "stderr": errors}


def replay_numerical_checks():
    """Bounded native no-persistent-write replay of the frozen exact checks."""
    helper = _helper()
    before = _selection(helper)
    result = _invoke(helper, None, True)
    helper.require(result["returncode"] == 0, "temporary native replay failed: " + result["stderr"].decode("utf-8", "replace"))
    helper.require(before == _selection(helper), "selected files changed during temporary replay")
    checks = json.loads(result["stdout"].decode("utf-8", errors="strict"))
    helper.require(checks["content_sha256"] == helper.digest({key: value for key, value in checks.items() if key != "content_sha256"}),
                   "temporary replay checks seal differs")
    return checks


def run_native(output_directory=DEFAULT_OUTPUT):
    helper = _helper()
    before = _selection(helper)
    output = Path(output_directory).resolve()
    helper.require(not output.exists(), "fresh native recovery directory required")
    output.mkdir(mode=0o700)
    helper._write_new(output / "native_selection.json", before)
    result = _invoke(helper, output, False)
    exit_receipt = helper.sealed({
        "schema": "alignment-masked-contrastive-native-child-exit/v1", "command": result["command"],
        "returncode": result["returncode"], "stdout_bytes": len(result["stdout"]), "stderr_bytes": len(result["stderr"]),
        "stdout_utf8": result["stdout"].decode("utf-8", errors="replace"),
        "stderr_utf8": result["stderr"].decode("utf-8", errors="replace"),
        "selection_binding": helper.binding(output / "native_selection.json"), "optimizer_updates": 0,
        "masks": dict.fromkeys(helper.MASK_NAMES, 0), **helper.FALSE_FLAGS,
    })
    helper._write_new(output / "native_child_exit.json", exit_receipt)
    helper.require(result["returncode"] == 0, "native recovery child failed; preserved diagnostic files")
    helper.require(before == _selection(helper), "selected files changed during native recovery")
    report = output / "numerical_assay.json"
    return {"report_binding": helper.binding(report), "native_selection_binding": helper.binding(output / "native_selection.json"),
            "native_child_exit_binding": helper.binding(output / "native_child_exit.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--replay-only", action="store_true")
    parser.add_argument("--child", action="store_true")
    arguments = parser.parse_args()
    if arguments.child:
        raise SystemExit(_child(_helper(), arguments.output_directory.resolve(), arguments.replay_only))
    if arguments.replay_only:
        print(json.dumps(replay_numerical_checks(), sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(run_native(arguments.output_directory), sort_keys=True))


if __name__ == "__main__":
    main()
