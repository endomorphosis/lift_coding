"""File-only, bounded construction of an additive objective-scalar metadata batch.

No project imports, source execution, native jobs, hydration, or network calls.
Run only after independent source review and both actual module qualifications.
Adapted from the byte-identical sealed Q4 builder; old inputs are never written.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import stat
from pathlib import Path


Q5 = Path(__file__).absolute().parent
SOURCE_SHA = "3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a"
COMPILER_SHA = "a9f4c93423c0f10e432e005ce4f8986e903706cf7ea5b493699633618519d9d9"
TEST_SHA = "c18c4a95bde5da2c780a91bc77e1ad5358ebd30723087e11fb0a8b96448c35c1"
PRIOR_SHA = "99405523f277ab10b3248a1e9ca5c1af1373fbe26c086f35c7f6bd8157e91e35"
SLICES_SHA = "20f4cc89a1b92a9ab2eb3a53ec15298e9892c00550b5cb61891d278256fae124"
GENERATED_SHA = "c6ba9dbc3a9ed056d04d004692180efd76db4e8d379681d7c8ff2edb1da8e919"
GENERIC_SOURCE_SHA = "ae4d1ebec782c2395cc9d2585f40296988fc2ec10cfdab3f946258251c527d71"
OBJECTIVE_SHA = "129da31ae6856167478c7f030a059d0f477b8362bb8fa478221eac7bac6031c2"
LOSS_SHA = "b71027e5d37d1a5b5b574a4b880a0857f0885dbc19c81dff3e652f8f7c76287e"
FACTOR_SHA = "a5f60c17cb8efc0869ec1ac4001c04c1b43f67d7d38bc025cbb87061247d70aa"
L2_RATIO = {"kind": "num", "numerator": "5764607523034235", "denominator": "576460752303423488"}
CHECKER_SHA = "04015267ed110533a7406c0b39c38b88a974a1d80259fd5755a99ef908a8a8b4"
RETENTION_SHA = "ccdf7df547844ac5d39cc077c8a14194fd06f7bb51838d80ffa9d7f349999e66"
PROFILE_SHA = "ac20651cebbf99688eedc01b10dfc3efffbb90be0938db7441728e9132c190ff"
MAX_FILE = 32 * 1024 * 1024
MAX_READ = 256 * 1024 * 1024
MAX_PAYLOAD = 64 * 1024 * 1024
MAX_ROW = 262144
NATIVE_BOUNDS = {"cpu_seconds": 20, "max_input_bytes": 262144, "max_output_bytes": 65536,
                 "max_workspace_bytes": 16777216, "timeout_seconds": 20}
AUTHORITY = {"proof_authority": False, "execution_authority": False, "completion_authority": False,
             "formalization_authority": False, "mutation_authority": False, "omission_authority": False,
             "planner_activation": False, "global_autoencoder_convergence_proved": False,
             "full_task_satisfaction": "unknown", "official_benchmark_score": None}
FRONTIERS = {"host_parser_correctness_theorem_proved": False, "python_ranker_source_equivalence_proved": False,
             "binary64_error_bound_proved": False, "full_objective_semantics_proved": False,
             "full_preparation_semantics_proved": False, "full_training_semantics_proved": False,
             "whole_IR_semantic_preservation_proved": False, "strict_cache_admission": False,
             "full_gradient_semantics_proved": False, "Python_Float_semantics_proved": False,
             "Python_libm_semantics_proved": False, "CPython_math_fsum_semantics_proved": False,
             "optimizer_source_convergence_proved": False,
             "all32_governing_RPI_exits": "OPEN"}
GENERIC_QUERIES = tuple("RankerObjectiveIR." + name for name in (
    "compile_scalar_sound", "compile_scalar_refuses_unsupported", "compile_scalar_refuses_unknown_name",
    "stableLoss_eval_success", "stableFactor_eval_success"))
GENERATED_QUERIES = tuple("RankerObjectiveIRGenerated." + name for name in (
    "emitted_compile_scalar_sound", "emitted_compile_refuses_unsupported", "emitted_compile_refuses_unknown_name",
    "emitted_stableLoss_compiles", "emitted_stableFactor_compiles", "emitted_stableLoss_eval_success",
    "emitted_stableFactor_eval_success", "emitted_stableLoss_eq_pairLoss", "emitted_stableFactor_eq_logisticP"))
FIXED_DELTAS = {"ast": 2, "sources": 3, "ranker_real_curvature_proofs": 2, "kg": 9}
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_PHASE = re.compile(r"[a-z][a-z0-9-]{0,79}\Z")


def need(ok, message):
    if ok is not True:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def keys(value, expected, label):
    need(type(value) is dict and set(value) == set(expected), label + " keys")


def digest(value):
    need(type(value) is str and len(value) == 64 and _HEX.fullmatch(value) is not None, "exact SHA256 required")
    return value


def descriptor(value):
    need(type(value) is dict and all(k in value for k in ("path", "bytes", "sha256")), "file descriptor required")
    p, n, sha = value["path"], value["bytes"], value["sha256"]
    need(type(p) is str and len(p) <= 4096 and Path(p).is_absolute() and os.path.normpath(p) == p,
         "absolute normalized file path required")
    need(type(n) is int and 0 <= n <= MAX_FILE, "bounded exact file byte count required")
    return {"path": p, "bytes": n, "sha256": digest(sha)}


def same_pin(a, b):
    return canonical(descriptor(a)) == canonical(descriptor(b))


def same_content(a, b):
    left, right = descriptor(a), descriptor(b)
    return canonical({k: left[k] for k in ("bytes", "sha256")}) == canonical({k: right[k] for k in ("bytes", "sha256")})


def census_descriptor(value):
    """Validate metadata for comparison only; never authorize a file body read.

    Native dependency census entries may exceed MAX_FILE (for example Lean's
    shared library). Their sizes fit signed filesystem offsets. Reader.read
    still calls descriptor(), retaining its unchanged 32 MiB body-read cap.
    """
    need(type(value) is dict and all(k in value for k in ("path", "bytes", "sha256")), "census file descriptor required")
    p, n, sha = value["path"], value["bytes"], value["sha256"]
    need(type(p) is str and len(p) <= 4096 and Path(p).is_absolute() and os.path.normpath(p) == p,
         "absolute normalized census path required")
    need(type(n) is int and 0 <= n <= (1 << 63) - 1, "exact filesystem-size census byte count required")
    return {"path": p, "bytes": n, "sha256": digest(sha)}


def same_census_pin(a, b):
    return canonical(census_descriptor(a)) == canonical(census_descriptor(b))


def row_bounds(value):
    need(len(canonical(value)) <= MAX_ROW, "new metadata row byte limit")
    todo, count = [(value, 1)], 0
    while todo:
        current, depth = todo.pop()
        count += 1
        need(count <= 50000 and depth <= 32, "new metadata row depth/node limit")
        children = current.values() if type(current) is dict else current if type(current) is list else ()
        for child in children:
            need(count + len(todo) < 50000, "new metadata row pending-node limit")
            todo.append((child, depth + 1))


def _pairs(values):
    result = {}
    for key, value in values:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def json_body(raw):
    def nonfinite(_):
        raise ValueError("nonfinite JSON value")
    result = json.loads(raw, object_pairs_hook=_pairs, parse_constant=nonfinite)
    todo, count = [(result, 1)], 0
    while todo:
        value, depth = todo.pop()
        count += 1
        need(count <= 1000000 and depth <= 32, "input JSON depth/node budget")
        children = value.values() if type(value) is dict else value if type(value) is list else ()
        for child in children:
            need(count + len(todo) < 1000000, "input JSON pending budget")
            todo.append((child, depth + 1))
    return result


class Reader:
    def __init__(self):
        self.cache, self.total = {}, 0

    def read(self, pin):
        row = descriptor(pin)
        path = row["path"]
        if path in self.cache:
            previous, raw = self.cache[path]
            need(canonical(previous) == canonical(row), "conflicting descriptors for same path")
            return raw
        need(os.path.realpath(path) == path, "file aliases refused")
        need(self.total + row["bytes"] <= MAX_READ, "aggregate read budget")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            need(stat.S_ISREG(before.st_mode) and before.st_size == row["bytes"], "regular pinned file required")
            parts, size = [], 0
            while True:
                part = os.read(fd, min(1024 * 1024, row["bytes"] - size + 1))
                if not part:
                    break
                parts.append(part)
                size += len(part)
                need(size <= row["bytes"], "file grew during read")
            after = os.fstat(fd)
            need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                 (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), "file changed during read")
        finally:
            os.close(fd)
        raw = b"".join(parts)
        need(len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"], "file digest mismatch")
        self.total += len(raw)
        self.cache[path] = (row, raw)
        return raw

    def load(self, pin):
        return json_body(self.read(pin))

    def post_verify(self):
        # Fresh no-cache reads close the read-only construction boundary.
        other = Reader()
        for row, _ in self.cache.values():
            other.read(row)
        return {"files": len(other.cache), "bytes": other.total, "all_pins_rehashed": True}


def drained(owned):
    need(owned.get("schema") == "terminal-ranker-curvature-owned-control@1", "owned control schema")
    need(owned.get("cleanup_errors") == [] and owned.get("root_release_returned") is True, "owned cleanup/release")
    state = owned.get("final_resource_state")
    need(type(state) is dict, "final scheduler state")
    for key in ("active_lease_count", "active_root_lease_count", "active_child_lease_count", "waiting_request_count"):
        need(type(state.get(key)) is int and state[key] == 0, "scheduler not drained: " + key)
    for key in ("fit_calls", "autoencoder_fit_calls", "gradient_evaluations", "optimizer_updates", "native_preparation_calls"):
        need(type(owned.get(key)) is int and owned[key] == 0, "forbidden operation counter: " + key)
    for key in ("proof_authority", "execution_authority", "completion_authority", "planner_activation"):
        need(owned.get(key) is False, "owned authority activated")
    need(type(owned.get("strict_old_input_count")) is int and owned["strict_old_input_count"] == 2108 and
         type(owned.get("protected_live_source_count")) is int and owned["protected_live_source_count"] == 4 and
         owned.get("all_strict_old_and_protected_live_inputs_unchanged") is True,
         "2108 strict old and four protected live inputs unchanged")


def passed_outer(outer):
    need(outer.get("schema") == "terminal-ranker-curvature-outer-control@1" and
         type(outer.get("returncode")) is int and outer["returncode"] == 0 and
         outer.get("primary_error") is None and outer.get("cleanup_errors") == [], "outer control failed")


def invocation(reader, pin, owned):
    value = reader.load(pin)
    need(value.get("schema") == "terminal-ranker-curvature-frozen-invocation@1" and
         value.get("mode") == owned.get("mode") and value.get("outer_timeout_seconds") == 120 and
         same_pin(owned["invocation"], pin), "owned invocation join")
    all_pins = value.get("inputs", []) + value.get("extra_inputs", [])
    need(type(value.get("inputs")) is list and type(value.get("extra_inputs")) is list and 1 <= len(all_pins) <= 1000,
         "invocation input population")
    for row in all_pins:
        reader.read(row)
    if "request" in value:
        reader.read(value["request"])
    return value, all_pins


def retained_objects(reader, check, module):
    need(check.get("retention_format") == "bounded_lean_chunks@1" and
         check.get("retention_profile_sha256") == PROFILE_SHA, "retention profile identity")
    profile = check["retention_profile"]
    need(hashlib.sha256(canonical(profile)).hexdigest() == PROFILE_SHA and
         profile.get("chunk_bytes") == 65536 and profile.get("max_chunk_files") == 61 and
         profile.get("max_raw_object_bytes") == 3997696 and profile.get("max_object_files") == 4,
         "fixed retention limits")
    manifest = reader.load(check["retention_manifest"])
    need(canonical(manifest) == canonical(check["retention_manifest_body"]) and
         manifest.get("schema") == "bounded_lean_chunks@1" and manifest.get("status") == "complete" and
         manifest.get("retention_profile_sha256") == PROFILE_SHA and
         type(manifest.get("native_lean_returncode")) is int and manifest["native_lean_returncode"] == 0 and
         type(manifest.get("native_lean_invocations")) is int and manifest["native_lean_invocations"] == 1,
         "retention manifest binding")
    chunks, objects = manifest["chunks"], manifest["objects"]
    need(type(chunks) is list and 1 <= len(chunks) <= 61 and type(objects) is list and 1 <= len(objects) <= 4,
         "complete bounded object population")
    names = [value.get("name") for value in objects]
    need(names[0] == module + ".olean" and len(names) == len(set(names)) and
         names == [module + suffix for suffix in profile["object_suffixes"] if module + suffix in names],
         "exact module companion names/order")
    captured_chunks = check["retained_chunk_artifacts"]
    complete = check["compiled_artifacts"]
    need(len(captured_chunks) == len(chunks) and len(complete) == len(objects), "capture population mismatch")
    by_name = {}
    directory = Path(descriptor(check["retention_manifest"])["path"]).parent
    for i, (chunk, captured) in enumerate(zip(chunks, captured_chunks)):
        keys(chunk, ("name", "bytes", "sha256"), "retention chunk")
        need(chunk["name"] == "LeanProofChunk%03d.bin" % i and type(chunk["bytes"]) is int and
             0 < chunk["bytes"] <= 65536 and captured.get("complete") is True,
             "consecutive complete chunk population")
        row = {"path": str(directory / chunk["name"]), "bytes": chunk["bytes"], "sha256": digest(chunk["sha256"])}
        need(same_pin(row, captured), "chunk descriptor join")
        by_name[chunk["name"]] = reader.read(row)
    used, aggregate = [], 0
    for obj, captured in zip(objects, complete):
        keys(obj, ("name", "bytes", "sha256", "chunks"), "retention object")
        need(type(obj["name"]) is str and Path(obj["name"]).name == obj["name"] and
             obj["name"].endswith((".olean", ".olean.private", ".olean.server", ".ir")) and
             type(obj["bytes"]) is int and 0 < obj["bytes"] <= 3997696 and
             type(obj["chunks"]) is list and 1 <= len(obj["chunks"]) <= 61 and captured.get("complete") is True and
             captured.get("retention_format") == "bounded_lean_chunks@1", "complete object required")
        need(all(type(name) is str and name in by_name for name in obj["chunks"]), "unknown object chunk")
        used.extend(obj["chunks"])
        raw = b"".join(by_name[name] for name in obj["chunks"])
        row = {"path": str(directory / obj["name"]), "bytes": obj["bytes"], "sha256": digest(obj["sha256"])}
        need(same_pin(row, captured) and len(raw) == obj["bytes"] and hashlib.sha256(raw).hexdigest() == obj["sha256"] and
             raw == reader.read(row), "chunk/full object reconstruction mismatch")
        aggregate += len(raw)
    need(type(manifest.get("aggregate_raw_object_bytes")) is int and
         used == [chunk["name"] for chunk in chunks] and len(set(used)) == len(used) and
         aggregate == manifest["aggregate_raw_object_bytes"] and aggregate <= 3997696,
         "exact aggregate retention denominator")
    validation = check.get("reconstruction_validation")
    need(type(validation) is dict and validation.get("status") == "passed" and validation.get("exact_chunk_population") is True and
         validation.get("manifest_complete") is True and type(validation.get("aggregate_raw_object_bytes")) is int and
         validation["aggregate_raw_object_bytes"] == aggregate and type(validation.get("chunk_count")) is int and
         validation["chunk_count"] == len(chunks) and type(validation.get("reconstructed_object_count")) is int and
         validation["reconstructed_object_count"] == len(objects),
         "checker reconstruction audit join")
    return {"aggregate_raw_object_bytes": aggregate, "chunk_count": len(chunks), "object_count": len(objects),
            "all_chunks_and_full_objects_rehashed_and_compared": True}


def native_attempt(reader, row):
    keys(row, ("role", "module", "phase", "specification", "invocation", "owned_closed", "outer_closed", "check_result"),
         "native attempt")
    role = row["role"]
    need(role in ("generic_failed", "generic_accepted", "generated_failed", "generated_accepted") and type(row["phase"]) is str and
         len(row["phase"]) <= 80 and
         _PHASE.fullmatch(row["phase"]) is not None, "native attempt role/phase")
    generated_role = role.startswith("generated_")
    accepted_role = role.endswith("_accepted")
    expected_module = "GeneratedObjectiveScalarLeaves" if generated_role else "ObjectiveScalarIR"
    queries = GENERATED_QUERIES if generated_role else GENERIC_QUERIES
    need(row["module"] == expected_module, "native module role")
    spec, check = reader.load(row["specification"]), reader.load(row["check_result"])
    owned, outer = reader.load(row["owned_closed"]), reader.load(row["outer_closed"])
    need(owned.get("mode") == row["phase"], "native phase join")
    need(check.get("schema") == "ranker-real-curvature-bounded-analytic-lean-check@2" and
         outer.get("schema") == "terminal-ranker-curvature-outer-control@1" and
         same_pin(outer["invocation"], row["invocation"]), "native/check/outer invocation join")
    drained(owned)
    call, inputs = invocation(reader, row["invocation"], owned)
    need(any(same_pin(value, row["specification"]) for value in inputs), "specification absent from invocation")
    need(any(descriptor(value)["sha256"] == CHECKER_SHA and Path(descriptor(value)["path"]).name == "bounded_analytic_checker.py"
             for value in inputs), "reviewed checker absent")
    need(spec.get("schema") == "terminal-ranker-curvature-native-check-specification@1" and spec.get("expected_success") is True and
         tuple(spec.get("theorem_names", [])) == queries, "frozen native specification")
    for key in ("source", "environment_manifest", "python_executable", "retention_helper", "freeze_producer"):
        reader.read(spec[key])
    need(descriptor(spec["retention_helper"])["sha256"] == RETENTION_SHA, "retention identity")
    source = reader.read(spec["source"])
    environment = reader.load(spec["environment_manifest"])
    need(environment.get("schema") == "ranker-real-curvature-lean-environment@1" and
         environment.get("all_dependencies_readonly_required_by_root_before_proof_execution") is True and
         environment.get("whole_source_equivalence_proved") is False and
         environment.get("native_per_file_capture_bytes_unchanged") == 65536 and
         environment.get("private_native_workspace_and_retention_limits_changed") is False,
         "fixed frozen environment profile")
    need(any(same_pin(value, spec["source"]) for value in environment.get("selected_proof_sources", [])), "source absent from profile")
    for key in ("source", "environment_manifest", "python_executable", "retention_helper"):
        need(same_pin(spec[key], check[key]), "native check/spec join: " + key)
    need(canonical(check.get("native_bounds")) == canonical(NATIVE_BOUNDS) and
         type(check.get("native_invocations")) is int and check["native_invocations"] == 1 and
         type(check.get("native_lean_invocations")) is int and check["native_lean_invocations"] == 1 and
         check.get("expected_success") is True and check.get("post_call_binding_error") is None,
         "actual bounded native invocation")
    calls = owned.get("native_checker_attempts")
    need(type(calls) is list and len(calls) == 1 and type(calls[0]) is dict and
         same_pin(calls[0]["specification"], row["specification"]) and
         type(calls[0].get("native_invocations_observed")) is int and calls[0]["native_invocations_observed"] == 1 and
         type(owned.get("native_proof_checks")) is list and len(owned["native_proof_checks"]) == 1 and
         same_pin(owned["native_proof_checks"][0], row["check_result"]),
         "owned native result binding")
    augmented = source + b"\n" + b"\n".join(("#print axioms _root_." + name).encode() for name in queries) + b"\n"
    need(reader.read(check["augmented_source"]) == augmented, "source/queried augmented source join")
    standard = {"propext", "Classical.choice", "Quot.sound"}
    need(set(check.get("allowed_standard_axioms", [])) == standard, "standard axiom policy")
    reconstruction = None
    if not accepted_role:
        need(check.get("status") == "inconclusive" and check.get("matches_expectation") is False and
             owned.get("status") == "failed" and owned.get("primary_error") is not None and
             type(outer.get("returncode")) is int and outer["returncode"] != 0 and outer.get("cleanup_errors") == [],
             "failed native history must remain inconclusive/unadmitted")
        need(check.get("compiled_artifacts") == [] and check.get("retained_chunk_artifacts") == [],
             "failed attempt must not register a compiled module")
        failed_manifest = reader.load(check["retention_manifest"])
        need(canonical(failed_manifest) == canonical(check["retention_manifest_body"]) and
             failed_manifest.get("status") == "native_nonzero", "failed native manifest retained")
    else:
        passed_outer(outer)
        need(owned.get("status") == "passed" and owned.get("primary_error") is None and check.get("status") == "passed" and
             check.get("matches_expectation") is True and check.get("returncode") == 0 and check.get("native_lean_returncode") == 0,
             "actual passed native module required")
        for flag in ("output_truncated", "timed_out", "cancelled", "unavailable", "resource_exhausted", "workspace_limit_exceeded"):
            need(check.get(flag) is False, "native refusal flag: " + flag)
        need(check.get("artifact_anomalies") == [] and check.get("axiom_report_error") is None and
             check.get("reconstruction_validation_error") is None and check.get("workspace_cleaned") is True,
             "native artifacts/report/cleanup")
        reports = check.get("theorem_axiom_output")
        need(type(reports) is list and tuple(value.get("theorem") for value in reports) == queries, "complete ordered theorem reports")
        for report in reports:
            need(type(report.get("axioms")) is list and len(report["axioms"]) == len(set(report["axioms"])) and
                 set(report["axioms"]) <= standard and type(report.get("report_occurrences")) is int and report["report_occurrences"] == 2,
                 "standard-only complete theorem query")
        reconstruction = retained_objects(reader, check, row["module"])
    imports = ["ObjectiveScalarIR"] if generated_role else ["RealStableFactor", "TypedNumericSlice"]
    need(check.get("source_direct_imports") == imports, "exact direct module imports")
    for flag in ("proof_authority", "execution_authority", "completion_authority", "planner_activation",
                 "python_ranker_source_equivalence_proved", "binary64_error_bound_proved"):
        need(check.get(flag) is False, "native scope flag: " + flag)
    return {"row": row, "spec": spec, "check": check, "source": source, "environment": environment, "imports": imports,
            "reconstruction": reconstruction}


def _source_bindings(reader, plan):
    for key, sha in (("prior_metadata", PRIOR_SHA), ("compiler_source", COMPILER_SHA), ("compiler_tests", TEST_SHA),
                     ("original_source", SOURCE_SHA), ("source_slices", SLICES_SHA), ("generated_lean", GENERATED_SHA)):
        need(descriptor(plan[key])["sha256"] == sha, "frozen input identity: " + key)
        reader.read(plan[key])
    source, slices = reader.read(plan["original_source"]), reader.load(plan["source_slices"])
    need(len(source) == 16391 and slices.get("schema") == "ranker-objective-scalar-source-slices@1" and
         slices.get("source", {}).get("sha256") == SOURCE_SHA and
         slices.get("status") == "compiled_source_only_kernel_pending",
         "compiled original source identity")
    specification = reader.load(plan["source_specification"])
    need(same_pin(specification["source"], plan["original_source"]) and
         specification.get("schema") == "ranker-objective-scalar-compilation-specification@1" and
         same_pin(specification["producer"], plan["compiler_source"]), "source specification join")
    for key in ("source_bindings", "source_plan", "ir_interface"):
        reader.read(specification[key])
    arguments = {"expected_source_sha256": SOURCE_SHA, "expected_objective_ast_sha256": OBJECTIVE_SHA,
                 "expected_stable_loss_ast_sha256": LOSS_SHA, "expected_stable_factor_ast_sha256": FACTOR_SHA}
    need(canonical(specification.get("arguments")) == canonical(arguments), "exact compiler specification arguments")
    module = ast.parse(source, filename="<pinned-ranker-source>")
    functions = [n for n in module.body if type(n) is ast.FunctionDef and n.name == "_objective"]
    need(len(functions) == 1, "unique objective function")
    objective = functions[0]
    ast_sha = lambda node: hashlib.sha256(ast.dump(node, annotate_fields=True, include_attributes=False).encode()).hexdigest()
    need(ast_sha(objective) == OBJECTIVE_SHA and ast_sha(module) == slices["source"]["module_ast_sha256"] and
         ast_sha(objective) == slices["objective_context"]["ast_sha256"], "same-byte function/module AST joins")
    node_pairs = (("stable_loss", objective.body[1].value.left.args[0].elt),
                  ("stable_factor", objective.body[3].value.elt))

    def lower(node):
        if type(node) is ast.Name:
            need(node.id == "z" and type(node.ctx) is ast.Load, "bound scalar name")
            return {"kind": "var", "slot": 0}
        if type(node) is ast.Constant:
            need(type(node.value) in (int, float), "exact numeric constant")
            n, d = node.value.as_integer_ratio() if type(node.value) is float else (node.value, 1)
            return {"kind": "num", "numerator": str(n), "denominator": str(d)}
        if type(node) is ast.UnaryOp:
            need(type(node.op) is ast.USub, "supported scalar negation")
            return {"kind": "neg", "value": lower(node.operand)}
        if type(node) is ast.BinOp:
            kind = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "div"}.get(type(node.op))
            need(kind is not None, "generic arithmetic operator")
            return {"kind": kind, "left": lower(node.left), "right": lower(node.right)}
        if type(node) is ast.Call:
            need(node.keywords == [], "positional scalar calls")
            if type(node.func) is ast.Name and node.func.id in ("abs", "max"):
                kind = node.func.id
            else:
                need(type(node.func) is ast.Attribute and type(node.func.value) is ast.Name and
                     node.func.value.id == "math" and node.func.attr in ("exp", "log1p"), "scalar math call")
                kind = node.func.attr
            need(len(node.args) == (2 if kind == "max" else 1), "scalar call arity")
            if kind == "max":
                return {"kind": kind, "left": lower(node.args[0]), "right": lower(node.args[1])}
            return {"kind": kind, "value": lower(node.args[0])}
        need(type(node) is ast.IfExp and type(node.test) is ast.Compare and len(node.test.ops) == 1 and
             type(node.test.ops[0]) is ast.GtE and len(node.test.comparators) == 1 and
             type(node.test.comparators[0]) is ast.Constant and type(node.test.comparators[0].value) in (int, float) and
             node.test.comparators[0].value == 0, "generic ifNonneg scalar condition")
        return {"kind": "ifNonneg", "condition": lower(node.test.left),
                "then": lower(node.body), "else": lower(node.orelse)}

    def named(node):
        if node["kind"] == "var":
            return {"kind": "var", "name": "z"}
        return {key: named(value) if type(value) is dict else value for key, value in node.items()}

    def render(node):
        kind = node["kind"]
        if kind == "var":
            return '(.var "z")'
        if kind == "num":
            return "(.num (" + node["numerator"] + " : Rat))" if node["denominator"] == "1" else \
                "(.num ((" + node["numerator"] + " : Rat) / " + node["denominator"] + "))"
        if kind in ("neg", "abs", "exp", "log1p"):
            return "(." + kind + " " + render(node["value"]) + ")"
        if kind == "ifNonneg":
            return "(.ifNonneg " + render(node["condition"]) + " " + render(node["then"]) + " " + render(node["else"]) + ")"
        return "(." + kind + " " + render(node["left"]) + " " + render(node["right"]) + ")"

    for name, node in node_pairs:
        body = lower(node)
        need(canonical(slices[name]["ir"]) == canonical({"schema": "ranker-objective-scalar-ir@1", "slots": 1, "body": body}) and
             canonical(slices[name]["source_scalar"]) == canonical(named(body)) and
             slices[name]["lean_source_scalar"] == render(body), "actual AST/operator-tree/source-literal joins")
        need(ast_sha(node) == (LOSS_SHA if name == "stable_loss" else FACTOR_SHA), "actual selected expression pin")
    l2_nodes = [n.value for n in module.body if type(n) is ast.Assign and len(n.targets) == 1 and
                type(n.targets[0]) is ast.Name and n.targets[0].id == "L2"]
    need(len(l2_nodes) == 1 and canonical(lower(l2_nodes[0])) == canonical(L2_RATIO) and
         canonical(slices["source_L2"]["ir"]["body"]) == canonical(L2_RATIO) and
         slices["source_L2"]["prior_exact_mu_rat_matches"] is True, "exact source L2 ratio retained")
    source_bindings = reader.load(specification["source_bindings"])
    need(same_pin(source_bindings["source"], plan["original_source"]) and
         source_bindings["objective"]["ast_dump_utf8_sha256"] == OBJECTIVE_SHA, "P6 original binding join")
    need(len(slices["source_snippets"]) == 9 and len(slices["statements"]) == 7, "scalar/context snippet denominator")
    for name, node in node_pairs:
        snippet = slices["source_snippets"][name + "_scalar"]
        segment = ast.get_source_segment(source.decode(), node)
        need(snippet["ast_sha256"] == ast_sha(node) and snippet["source_segment"] == segment and
             snippet["source_segment_utf8_sha256"] == hashlib.sha256(segment.encode()).hexdigest(), "actual scalar snippet provenance")
    need(canonical(slices["conditional_policy"]) == canonical({"syntax_validation": "both branches eager", "exact_real_evaluation": "selected branch only lazy"}),
         "conditional validation/evaluation distinction")
    for field in ("proof_authority", "python_ranker_source_equivalence_proved", "objective_to_IR_translation_proved",
                  "gradient_to_IR_translation_proved", "Python_Float_semantics_proved", "full_training_loop_to_IR_translation_proved"):
        need(slices[field] is False, "compiled receipt scope promoted")
    generated = reader.read(plan["generated_lean"])
    for field, definition in (("stable_loss", "emittedStableLossSource"), ("stable_factor", "emittedStableFactorSource"),
                              ("source_L2", "emittedSourceL2")):
        line = ("def " + definition + " : SourceScalar := " + slices[field]["lean_source_scalar"] + "\n").encode()
        need(generated.count(line) == 1, "actual emitted literal constructor binding")
    need(generated.count(b"#print axioms ") == 9, "actual generated theorem query population")
    return slices, node_pairs


def _source_audit(reader, plan):
    audits = {}
    for label in ("pure", "compile"):
        owned, outer = reader.load(plan[label + "_closed"]), reader.load(plan[label + "_outer"])
        drained(owned)
        passed_outer(outer)
        need(same_pin(outer["invocation"], owned["invocation"]), "source outer/owned invocation join")
        need(owned.get("status") == "passed" and owned.get("primary_error") is None and owned.get("native_proof_checks") == [],
             "pure source audit failed")
        call, _ = invocation(reader, owned["invocation"], owned)
        pins = call["inputs"] + call["extra_inputs"]
        need(any(same_pin(value, plan["compiler_source"]) for value in pins), "final compiler absent from source phase")
        need(any(same_pin(value, plan["original_source"]) for value in pins), "pinned original source absent from source phase")
        if label == "pure":
            need(any(same_pin(value, plan["compiler_tests"]) for value in pins), "final tests absent from pure phase")
        else:
            need(any(same_pin(value, plan["source_specification"]) for value in pins),
                 "actual admitted source compilation specification absent from compile invocation")
        audits[label] = {"owned": owned, "invocation": owned["invocation"]}
    pure, compiled = audits["pure"]["owned"], audits["compile"]["owned"]
    cases = pure.get("selected_test_count")
    need(type(cases) is int and cases == 98 and type(pure.get("pytest_returncode")) is int and pure["pytest_returncode"] == 0 and
         type(pure.get("native_runner_calls_refused")) is int and pure["native_runner_calls_refused"] == 0 and
         type(pure.get("direct_process_calls_refused")) is int and pure["direct_process_calls_refused"] == 0,
         "98-case inert pure test audit")
    phases = reader.load(plan["pure_phases"])
    need(descriptor(plan["pure_phases"])["path"] ==
         str(Path(descriptor(plan["pure_closed"])["path"]).parent / "phases.json"),
         "pure phase transcript belongs to selected owned phase")
    need(type(phases) is list and len(phases) == 3 * cases, "complete pure-test phase denominator")
    grouped = {}
    for item in phases:
        need(type(item) is dict and item.get("outcome") == "passed" and type(item.get("nodeid")) is str and
             item.get("phase") in ("setup", "call", "teardown"), "pure-test phase status")
        grouped.setdefault(item["nodeid"], []).append(item["phase"])
    need(len(grouped) == cases and all(values == ["setup", "call", "teardown"] for values in grouped.values()),
         "unique complete selected pure tests")
    need(type(compiled.get("source_AST_parse_calls")) is int and compiled["source_AST_parse_calls"] == 2 and
         type(compiled.get("source_function_execution_calls")) is int and compiled["source_function_execution_calls"] == 0 and
         type(compiled.get("new_native_qualification_jobs")) is int and compiled["new_native_qualification_jobs"] == 0 and
         compiled.get("host_parser_correctness_theorem_proved") is False and
         same_pin(compiled["objective_scalar_slices"], plan["source_slices"]) and
         same_pin(compiled["generated_Lean_candidate"], plan["generated_lean"]), "inert source compilation/emission audit")
    audits["cases"], audits["phases"] = cases, len(phases)
    return audits


def build_metadata(plan):
    keys(plan, ("schema", "prior_metadata", "compiler_source", "compiler_tests", "original_source", "source_slices",
                "generated_lean", "source_specification", "compile_closed", "compile_outer", "pure_closed", "pure_outer",
                "pure_phases", "native_attempts"), "metadata build plan")
    need(plan["schema"] == "ranker-objective-scalar-metadata-build-plan@1", "build plan schema")
    reader = Reader()
    slices, node_pairs = _source_bindings(reader, plan)
    audits = _source_audit(reader, plan)
    prior = reader.load(plan["prior_metadata"])
    need(type(prior) is dict and len(prior) == 32 and all(type(rows) is list for rows in prior.values()) and
         sum(map(len, prior.values())) == 4440 and len(prior.get("vectors", [])) == 375 and
         type(prior.get("contracts")) is list and len(prior["contracts"]) == 2 and
         set(FIXED_DELTAS) | {"ranker_real_curvature_checks"} <= set(prior), "exact prior 32-family/4440-row baseline")
    attempts = plan["native_attempts"]
    need(type(attempts) is list and 2 <= len(attempts) <= 12 and all(type(row) is dict for row in attempts),
         "bounded actual native attempt population")
    roles = [row.get("role") for row in attempts]
    need(roles.count("generic_accepted") == 1 and roles.count("generated_accepted") == 1 and
         all(role in ("generic_failed", "generic_accepted", "generated_failed", "generated_accepted") for role in roles),
         "one actually accepted generic and generated module required")
    checked = [native_attempt(reader, row) for row in attempts]
    need(len({row["row"]["phase"] for row in checked}) == len(checked), "duplicate native attempt")
    actual_paths = {str(path.absolute()) for path in (Q5 / "evidence").glob("lean-objective-*/check-result.json")}
    need(actual_paths == {descriptor(row["check_result"])["path"] for row in attempts}, "every actual native result indexed")
    generic = next(row for row in checked if row["row"]["role"] == "generic_accepted")
    generated = next(row for row in checked if row["row"]["role"] == "generated_accepted")
    need(descriptor(generic["spec"]["source"])["sha256"] == GENERIC_SOURCE_SHA and len(generic["source"]) == 13094,
         "reviewed generic mathematical semantics source identity")
    need(same_content(generated["spec"]["source"], plan["generated_lean"]) and
         generated["source"] == reader.read(plan["generated_lean"]), "actual generated source qualification join")
    generic_bindings = [row for row in generated["environment"].get("local_checked_modules", [])
                        if row.get("module") == "ObjectiveScalarIR"]
    need(len(generic_bindings) == 1 and
         same_pin(generic_bindings[0]["qualification"], generic["row"]["check_result"]) and
         same_pin(generic_bindings[0]["environment"], generic["spec"]["environment_manifest"]),
         "generated environment uses this actually qualified generic module")
    generic_imports = [row for row in generated["environment"].get("source_import_modules", [])
                       if row.get("module") == "ObjectiveScalarIR"]
    need(len(generic_imports) == 1 and generic_imports[0].get("package") == "qualified-local-theorem" and
         same_pin(generic_imports[0]["source"], generic["check"]["augmented_source"]) and
         canonical([descriptor(row) for row in generic_imports[0]["compiled"]]) ==
         canonical([descriptor(row) for row in generic["check"]["compiled_artifacts"]]),
         "generated import registry uses exact accepted generic source and complete ordered objects")
    for registered in [generic_imports[0]["source"], *generic_imports[0]["compiled"]]:
        need(any(same_census_pin(registered, row) for row in generated["environment"].get("files", [])),
             "accepted generic import source/object absent from generated frozen file population")
    deltas = {**FIXED_DELTAS, "ranker_real_curvature_checks": len(checked)}
    added_rows = sum(deltas.values())
    total_rows = 4440 + added_rows
    records = {family: list(rows) for family, rows in prior.items()}
    new_ids = set()
    prior_ids = {row["record_id"] for rows in prior.values() for row in rows
                 if type(row) is dict and type(row.get("record_id")) is str}

    def add(family, kind, identity, **fields):
        record_id = "ranker-objective-ir-candidate-20261005-01/" + identity
        need(record_id not in new_ids and record_id not in prior_ids, "duplicate new/prior record ID")
        new_ids.add(record_id)
        value = {"schema": kind, "record_id": record_id, **fields, **AUTHORITY, **FRONTIERS}
        row_bounds(value)
        records[family].append(value)
        return record_id

    ast_ids, ir_ids = {}, {}
    for name, node in node_pairs:
        snippet = slices["source_snippets"][name + "_scalar"]
        ast_ids[name] = add("ast", "ranker-objective-scalar-AST@1", "ast/" + name,
            slice=name, original_source=plan["original_source"], compiler_receipt=plan["source_slices"],
            selected_path=snippet["ast_path"], ast_dump=ast.dump(node, include_attributes=False),
            expression_ast_sha256=snippet["ast_sha256"], source_snippet=snippet,
            objective_context=slices["objective_context"], module_ast_sha256=slices["source"]["module_ast_sha256"])
        ir_ids[name] = add("sources", "ranker-objective-scalar-typed-IR-record@1", "ir/" + name,
            slice=name, ast_record_id=ast_ids[name], complete_typed_ir=slices[name]["ir"],
            complete_typed_ir_sha256=hashlib.sha256(canonical(slices[name]["ir"])).hexdigest(),
            source_constructor=slices[name]["lean_source_scalar"], compiler_receipt=plan["source_slices"],
            actual_emitted_Lean=plan["generated_lean"], numeric_backend="exact_real",
            environment="one named exact-real scalar z", conditional_policy=slices["conditional_policy"],
            interpretation="partial exact-real scalar evaluator; division by zero/log1p outside positive domain refuse",
            Python_runtime_contract_claimed=False)
    audit_id = add("sources", "ranker-objective-scalar-compiler-owned-audit@1", "source-audit",
        compiler_source=plan["compiler_source"], compiler_tests=plan["compiler_tests"],
        source_specification=plan["source_specification"], compilation_receipt=plan["source_slices"],
        emitted_Lean=plan["generated_lean"], pure_owned_closed=plan["pure_closed"], pure_outer_closed=plan["pure_outer"],
        pure_invocation=audits["pure"]["invocation"], pure_phases=plan["pure_phases"],
        compile_owned_closed=plan["compile_closed"], compile_outer_closed=plan["compile_outer"],
        compile_invocation=audits["compile"]["invocation"], unique_pure_test_cases=audits["cases"], all_passed_test_phases=audits["phases"],
        compiler_phase_source_AST_parses=2, compiler_phase_source_function_executions=0, builder_source_AST_parses=1,
        new_fit_calls=0, new_gradient_evaluations=0, new_optimizer_updates=0, new_AE_fit_calls=0,
        generated_body_kernel_checks_separate=True, source_snippets=slices["source_snippets"],
        context_statement_count=len(slices["statements"]), exact_source_L2=slices["source_L2"],
        scalar_scope="stable loss and sign-split factor only; surrounding loops/gradient are context, not compiled")
    check_ids, proof_ids = {}, {}
    for attempt in checked:
        row, check, spec = attempt["row"], attempt["check"], attempt["spec"]
        accepted = row["role"].endswith("_accepted")
        check_ids[row["phase"]] = add("ranker_real_curvature_checks", "ranker-objective-scalar-native-check-index@1",
            "check/" + row["phase"], phase=row["phase"], module=row["module"], status=check["status"],
            source=spec["source"], augmented_source=check["augmented_source"], environment_manifest=spec["environment_manifest"],
            specification=row["specification"], invocation=row["invocation"], owned_closed=row["owned_closed"],
            outer_closed=row["outer_closed"], qualification=row["check_result"], native_invocations=1,
            native_bounds=NATIVE_BOUNDS, theorem_axiom_output=check["theorem_axiom_output"],
            qualified_module_admitted=accepted)
        if not accepted:
            continue
        proof_ids[row["module"]] = add("ranker_real_curvature_proofs", "ranker-objective-scalar-qualified-module-index@1",
            "proof/" + row["module"], module=row["module"], source=spec["source"], augmented_source=check["augmented_source"],
            qualification=row["check_result"], specification=row["specification"], environment_manifest=spec["environment_manifest"],
            owned_closed=row["owned_closed"], outer_closed=row["outer_closed"],
            theorem_axiom_output=check["theorem_axiom_output"], complete_compiled_artifacts=check["compiled_artifacts"],
            complete_retained_chunks=check["retained_chunk_artifacts"], retention_manifest=check["retention_manifest"],
            reconstruction=attempt["reconstruction"],
            scope=("accepted scalar compiler preserves a partial exact-real evaluator; explicit unsupported/unknown-name refusal"
                   if row["module"] == "ObjectiveScalarIR" else
                   "actual emitted stable-loss and sign-split-factor constructors compile and evaluate to prior exact-real scalar functions"),
            accepted_program_premise_is_compile_result_not_desired_identity=True,
            full_source_gradient_or_training_convergence_implication=False)

    def edge(identity, relation, origin, target, **fields):
        need(origin in new_ids, "unknown KG origin")
        need(target in new_ids or target in ("module:RealStableFactor", "module:TypedNumericSlice"),
             "unknown KG target")
        return add("kg", "ranker-objective-scalar-evidence-edge@1", "edge/" + identity,
                   relation=relation, from_record_id=origin, to_record_id=target,
                   Python_semantics_preservation_implication=False, **fields)
    for name in ("stable_loss", "stable_factor"):
        edge(name + "-AST-IR", "AST_extracted_to_IR", ast_ids[name], ir_ids[name], host_audit_record_id=audit_id)
        edge(name + "-IR-module", "scalar_projection_checked_in_module", ir_ids[name], proof_ids["GeneratedObjectiveScalarLeaves"],
             qualification=generated["row"]["check_result"])
    for attempt in (generic, generated):
        row = attempt["row"]
        edge(row["module"] + "-check", "check_evidence", proof_ids[row["module"]], check_ids[row["phase"]],
             qualification=row["check_result"])
        for imported in attempt["imports"]:
            target = proof_ids.get(imported, "module:" + imported)
            edge(row["module"] + "-import-" + imported, "imports_checked_module", proof_ids[row["module"]], target,
                 from_module=row["module"], to_module=imported, source=attempt["spec"]["source"],
                 frozen_environment=attempt["spec"]["environment_manifest"], qualification=row["check_result"])
    need(set(records) == set(prior) and len(records) == 32 and sum(map(len, records.values())) == total_rows,
         "exact final family/row denominator")
    for family, rows in prior.items():
        need(canonical(records[family][:len(rows)]) == canonical(rows) and
             len(records[family]) - len(rows) == deltas.get(family, 0), "canonical prefix/delta drift: " + family)
    need(canonical(records["vectors"]) == canonical(prior["vectors"]) and
         canonical(records["contracts"]) == canonical(prior["contracts"]),
         "vectors or mathematical domain population drift")
    raw = canonical(records)
    need(len(raw) <= MAX_PAYLOAD and len(records) <= 32 and sum(map(len, records.values())) <= 65536, "unchanged storage caps")
    post = reader.post_verify()
    receipt = {"schema": "ranker-objective-scalar-metadata-file-build@1", "status": "passed",
        "prior_metadata": plan["prior_metadata"], "prior_payload_rows": 4440, "metadata_payload_rows": total_rows,
        "added_payload_rows": added_rows, "metadata_family_count": 32, "family_deltas": deltas,
        "family_counts": {family: len(rows) for family, rows in records.items()},
        "all_prior_payload_prefixes_preserved_canonically": True, "prior_wrapper_row_ids_rebound_by_new_snapshot": True,
        "vectors375_unchanged_canonically": True, "prior_contract_prefix_preserved_canonically": True,
        "new_mathematical_projection_domain_records": 0, "new_runtime_contracts": 0,
        "prior_two_mathematical_domains_unchanged_canonically": True,
        "actual_native_attempts_indexed": len(checked), "accepted_module_records": 2,
        "inconclusive_attempts_unadmitted": len(checked) - 2, "qualified_theorem_query_entries": 14,
        "actual_native_check_bindings": [row["row"] for row in checked], "metadata_input_bytes": len(raw),
        "metadata_input_sha256": hashlib.sha256(raw).hexdigest(), "post_build_input_pins": post,
        "builder_source_AST_parse_calls": 1, "ranker_source_execution_calls": 0, "native_jobs_run_by_builder": 0,
        "metadata_hydration_jobs_run_by_builder": 0, "strict_advisory_cache_entries_added": 0,
        "full_external_dependency_closure_revalidated_here": False, "new_dependency_admission_claimed": False,
        "pinned_executable_and_local_compiled_object_bodies_read": True, **AUTHORITY, **FRONTIERS}
    return records, receipt


def main():
    need(__debug__ is True, "optimized Python invocation refused")
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    plan_path = Path(args.plan).absolute()
    size = plan_path.stat().st_size
    need(size <= 65536, "build plan byte cap")
    plan_pin = {"path": str(plan_path), "bytes": size, "sha256": digest(args.plan_sha256)}
    plan_reader = Reader()
    plan = plan_reader.load(plan_pin)
    records, receipt = build_metadata(plan)
    plan_reader.post_verify()
    output = Path(args.output_dir).absolute()
    need(output != Q5 and os.path.normpath(str(output)) == str(output) and
         output.is_relative_to(Q5 / "preparation") and os.path.realpath(output.parent) == str(output.parent),
         "new candidate preparation output namespace required")
    output.mkdir(mode=0o755)
    raw = canonical(records)
    with (output / "metadata-inputs.json").open("xb") as stream:
        stream.write(raw)
    receipt["frozen_build_plan"] = plan_pin
    receipt["metadata_inputs"] = {"path": str(output / "metadata-inputs.json"), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    with (output / "build-receipt.json").open("xb") as stream:
        stream.write(canonical(receipt))
    print(json.dumps({"status": receipt["status"], "metadata_inputs": receipt["metadata_inputs"],
                      "metadata_payload_rows": receipt["metadata_payload_rows"], "native_jobs_run_by_builder": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
