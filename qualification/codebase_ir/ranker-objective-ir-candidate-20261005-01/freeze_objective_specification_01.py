"""Freeze exact original-source and scalar AST bindings without target execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
PLAN = ROOT.with_name("ranker-objective-ir-source-plan-20261005-01")
SOURCE = WORKSPACE / "artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-intent-corpus-head-20261004-01/source/benchmarks/agent_supervisor/container_coding/terminal_codebase_intent_ranker_training.py"
ARGUMENTS = {
    "expected_source_sha256": "3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a",
    "expected_objective_ast_sha256": "129da31ae6856167478c7f030a059d0f477b8362bb8fa478221eac7bac6031c2",
    "expected_stable_loss_ast_sha256": "b71027e5d37d1a5b5b574a4b880a0857f0885dbc19c81dff3e652f8f7c76287e",
    "expected_stable_factor_ast_sha256": "a5f60c17cb8efc0869ec1ac4001c04c1b43f67d7d38bc025cbb87061247d70aa",
}
DOCUMENTS = {
    "source_bindings": ("source-bindings.json", "5f76eed1e9b025c8e7bb61d23e368a4740b01f329c40472f0c77f2f909bd5c16"),
    "source_plan": ("source-plan.json", "f0e712a1b78ba1a728f5f4a41a8d8f66540017ae86418e23f4bd3c40f6cce690"),
    "ir_interface": ("ir-interface.json", "53a6ba907b4ac64d79f88a97fb9b987a54d0b2efeb930cef798c249d483a6cd0"),
}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), "canonical regular input required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 32 * 1024**2, "bounded regular input required")
        pieces, size = [], 0
        while block := os.read(fd, 1024**2):
            size += len(block)
            need(size <= 32 * 1024**2, "input grew beyond bound")
            pieces.append(block)
        fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        signature = lambda value: tuple(getattr(value, field) for field in fields)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and size == before.st_size,
             "input changed during read")
        raw = b"".join(pieces)
        return raw, {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-compiler-sha256", required=True)
    args = parser.parse_args()
    need(re.fullmatch(r"[0-9a-f]{64}", args.expected_compiler_sha256) is not None, "externally pinned compiler required")
    held = {}
    source_raw, source_pin = read(SOURCE)
    need(source_pin["bytes"] == 16391 and source_pin["sha256"] == ARGUMENTS["expected_source_sha256"], "exact original source pin required")
    held[SOURCE] = source_pin
    compiler = ROOT / "source-v2/objective_scalar_compiler.py"
    _, compiler_pin = read(compiler)
    need(compiler_pin["sha256"] == args.expected_compiler_sha256, "reviewed compiler pin differs")
    held[compiler] = compiler_pin
    descriptors, parsed = {}, {}
    for role, (name, expected) in DOCUMENTS.items():
        raw, descriptor = read(PLAN / name)
        need(descriptor["sha256"] == expected, "same-buffer planning document pin differs")
        parsed[role], descriptors[role] = json.loads(raw), descriptor
        held[PLAN / name] = descriptor
    bindings = parsed["source_bindings"]
    need(bindings["schema"] == "ranker-objective-source-ast-bindings@1" and bindings["source"] == source_pin,
         "planning source binding differs")
    need(bindings["objective"]["ast_dump_utf8_sha256"] == ARGUMENTS["expected_objective_ast_sha256"], "objective context digest differs")
    for role in ("stable_loss", "stable_factor"):
        need(bindings["selected_scalar_leaves"][role + "_scalar"]["ast_dump_utf8_sha256"] == ARGUMENTS["expected_" + role + "_ast_sha256"],
             "scalar AST binding differs")
    for path, descriptor in held.items():
        need(read(path)[1] == descriptor, "held compiler/source/planning input changed")
    specification = {
        "schema": "ranker-objective-scalar-compilation-specification@1",
        "producer": compiler_pin, "source": source_pin, **descriptors,
        "arguments": ARGUMENTS, "scope": "stable_loss_and_sign_split_factor_scalar_leaves_exact_real_only",
        "source_execution_calls": 0,
    }
    target = ROOT / "preparation/objective-slices-specification.json"
    with target.open("xb") as stream:
        stream.write((json.dumps(specification, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    target.chmod(0o444)
    print(json.dumps({"status": "frozen_file_only", "specification": read(target)[1], "held_input_count": len(held),
                      "source_AST_parse_calls": 0, "source_execution_calls": 0, "native_jobs": 0, "target_imports": 0}))


if __name__ == "__main__":
    main()
