"""Source joins, arithmetic qualification and diagnostic retention checks."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

import align_projection as subject

SOURCE = b"def align(x: int, g: int) -> int:\n    return ((x + g - 1) // g) * g\n"
PATH = "public-task/scripts/cost_model.py"


def project(raw=SOURCE, path=PATH):
    return subject.project_alignment(source_bytes=raw, source_path=path,
        source_sha256=hashlib.sha256(raw).hexdigest())


def resign(value):
    value = copy.deepcopy(value)
    value.pop("projection_id", None)
    value["projection_id"] = hashlib.sha256(subject._wire(value)).hexdigest()
    return value


def test_exact_original_slice_and_full_parent_native_projection():
    raw = b'"""Parent metadata is retained."""\nSIDE = 7\n\n' + SOURCE
    value = project(raw)
    source = value["source"]
    assert raw[source["start_byte"]:source["end_byte"]].decode() == source["function_source"]
    assert source["start_line"] == 4 and source["end_line"] == 5
    assert source["sha256"] == hashlib.sha256(raw).hexdigest()
    assert value["native_full_file_adapter"]["status"] == "partial"
    assert value["unsupported_residuals"] == ["python.module.Expr", "python.module_level_assign"]
    assert value["typed_ir"]["source_expression"] == value["typed_ir"]["target_expression"]
    assert subject.validate_alignment_projection(source_bytes=raw, source_path=PATH,
        source_sha256=source["sha256"], expected=value)["verified"] is True
    assert all(value[key] is False for key in subject.AUTHORITY)


def test_complete_public_cost_model_source_retains_real_residuals():
    public = Path("/home/barberb/lift_coding/.benchmarks/terminal-bench-2/llm-inference-batching-scheduler/environment/task_file/scripts/cost_model.py")
    raw = public.read_bytes()
    assert len(raw) == 8096
    assert hashlib.sha256(raw).hexdigest() == "0cf417fd5ff0112defcd46970d37a290c0763c5a9092e91cb3ebb86c3f20e6ce"
    value = project(raw, "llm-inference-batching-scheduler/environment/task_file/scripts/cost_model.py")
    assert value["source"]["start_byte"] == 722
    assert value["source"]["end_byte"] == 789
    assert value["source"]["start_line"] == 28
    assert value["unsupported_residuals"] == ["python.class", "python.module.AnnAssign", "python.module.Expr"]
    assert value["native_full_file_adapter"]["program"]["sources"][0]["content_sha256"] == value["source"]["sha256"]


@pytest.mark.parametrize("x", [-100000, -129, -128, -127, -65, -64, -63, -1, 0, 1, 63, 64, 65, 127, 128, 100000, 2**128, -(2**128)])
def test_integer_ir_rounding_boundary_witnesses(x):
    result = subject.evaluate_alignment(projection=project(), x=x)
    assert x <= result < x + 64
    assert result % 64 == 0
    assert result == ((x + 63) // 64) * 64


def test_negative_input_distinguishes_floor_and_truncation():
    assert subject.evaluate_alignment(projection=project(), x=-65) == -64
    assert int((-65 + 63) / 64) * 64 == 0


@pytest.mark.parametrize("granularity", [0, -64, 1, 32, 128, True, 64.0, "64"])
def test_unqualified_granularity_refused(granularity):
    with pytest.raises(subject.AlignmentProjectionError, match="granularity"):
        subject.evaluate_alignment(projection=project(), x=10, granularity=granularity)


@pytest.mark.parametrize("x", [True, False, 1.0, "1", None])
def test_non_integer_runtime_inputs_not_admitted_by_annotation(x):
    with pytest.raises(subject.AlignmentProjectionError, match="exact integer"):
        subject.evaluate_alignment(projection=project(), x=x)


@pytest.mark.parametrize("before,after", [(b"//", b"/"), (b"- 1", b"- 2"),
    (b"* g", b"+ g"), (b"x + g", b"g + x"), (b"// g", b"// 0"),
    (b"// g", b"// -64"), (b"x: int", b"x"), (b"g: int", b"g: bool"),
    (b"g: int", b"g: int = 64"), (b" -> int", b" -> float")])
def test_operator_domain_and_signature_changes_refused(before, after):
    with pytest.raises(subject.AlignmentProjectionError):
        project(SOURCE.replace(before, after))


@pytest.mark.parametrize("raw", [SOURCE + SOURCE, b"@staticmethod\n" + SOURCE,
    SOURCE + b"align = 3\n", SOURCE + b"class align:\n    pass\n",
    SOURCE.replace(b"return", b"pass\n    return"), b"\xff" + SOURCE])
def test_ambiguous_or_non_closed_declarations_refused(raw):
    with pytest.raises(subject.AlignmentProjectionError):
        project(raw)


@pytest.mark.parametrize("path", ["/tmp/cost_model.py", "../cost_model.py", "a/../cost_model.py",
    "a//cost_model.py", "a\\cost_model.py", ".git/cost_model.py", "file.txt", ""])
def test_noncanonical_source_paths_refused(path):
    with pytest.raises(subject.AlignmentProjectionError):
        project(path=path)


def test_parent_hash_changes_even_when_selected_function_does_not():
    value = project()
    changed = SOURCE + b"# different complete parent\n"
    updated = project(changed)
    assert updated["source"]["function_bytes_sha256"] == value["source"]["function_bytes_sha256"]
    assert updated["projection_id"] != value["projection_id"]
    with pytest.raises(subject.AlignmentProjectionError, match="parent source SHA"):
        subject.validate_alignment_projection(source_bytes=changed, source_path=PATH,
            source_sha256=value["source"]["sha256"], expected=value)
    with pytest.raises(subject.AlignmentProjectionError, match="replay differs"):
        subject.validate_alignment_projection(source_bytes=changed, source_path=PATH,
            source_sha256=hashlib.sha256(changed).hexdigest(), expected=value)


def test_path_join_changes_are_detected():
    value = project()
    with pytest.raises(subject.AlignmentProjectionError, match="replay differs"):
        subject.validate_alignment_projection(source_bytes=SOURCE, source_path="other-task/cost_model.py",
            source_sha256=value["source"]["sha256"], expected=value)


@pytest.mark.parametrize("mutation", ["parent_sha", "span", "source_text", "target_operator",
    "native_parent", "native_target", "residuals", "authority", "claims", "granularity"])
def test_rehashed_forged_projection_cannot_change_internal_source_join(mutation):
    value = project()
    if mutation == "parent_sha": value["source"]["sha256"] = "0" * 64
    elif mutation == "span": value["source"]["start_byte"] += 1
    elif mutation == "source_text":
        value["source"]["function_source"] = value["source"]["function_source"].replace("- 1", "- 2")
        value["source"]["function_bytes_sha256"] = hashlib.sha256(value["source"]["function_source"].encode()).hexdigest()
    elif mutation == "target_operator": value["typed_ir"]["target_expression"]["kind"] = "add"
    elif mutation == "native_parent":
        value["native_full_file_adapter"]["program"]["sources"][0]["content_sha256"] = "1" * 64
        value["native_full_file_adapter_sha256"] = hashlib.sha256(subject._wire(value["native_full_file_adapter"])).hexdigest()
    elif mutation == "native_target":
        rows = value["native_full_file_adapter"]["program"]["expressions"]
        next(row for row in rows if row["operator"] == "floordiv")["operator"] = "div"
        value["native_full_file_adapter_sha256"] = hashlib.sha256(subject._wire(value["native_full_file_adapter"])).hexdigest()
    elif mutation == "residuals": value["unsupported_residuals"] = ["fabricated.residual"]
    elif mutation == "authority": value["source_model_equivalence_proved"] = True
    elif mutation == "claims": value["model_claims"]["kernel_checked_lowering"] = True
    elif mutation == "granularity": value["assumptions"]["granularity"] = 0
    with pytest.raises(subject.AlignmentProjectionError):
        subject.evaluate_alignment(projection=resign(value), x=2)


def test_self_identity_does_not_replace_full_source_replay():
    value = project()
    value["source"]["sha256"] = "0" * 64
    with pytest.raises(subject.AlignmentProjectionError, match="identity differs"):
        subject.evaluate_alignment(projection=value, x=1)


def test_lean_sources_contain_general_lowering_real_properties_and_false_controls():
    rows = subject._lean_sources(project())
    positive = rows[0][1]
    assert "induction expression" in positive
    assert "alignment_rounding_bounds : ∀ x : Int" in positive
    assert "alignment_divisible : ∀ x : Int" in positive
    assert "native_target_correspondence" in positive
    assert "#print axioms alignment_rounding_bounds" in positive
    assert "run (-65) = 0" in rows[1][1]
    assert "run 0 = 64" in rows[2][1]
    assert [row[2] for row in rows] == [True, False, False]
    assert all("sorry" not in row[1] and "axiom " not in row[1] for row in rows)


def test_all_completed_process_diagnostics_retained_before_gate(tmp_path, monkeypatch):
    observed = []
    def fake_compile(**kwargs):
        observed.append(kwargs["filename"])
        return {"file": kwargs["filename"], "expected_success": kwargs["expected_success"],
            "status": "inconclusive", "matches_expectation": False, "stdout": "deliberate inconclusive diagnostic"}
    monkeypatch.setattr(subject, "_compile_alignment_lean", fake_compile)
    output = tmp_path / "inconclusive"
    with pytest.raises(subject.AlignmentProjectionError, match="all process diagnostics retained"):
        subject.compile_alignment_proofs(projection=project(), output=output,
            lean_executable=Path("/bin/true").resolve())
    assert len(observed) == 3
    assert all(json.loads((output / f"check-{number:02d}.json").read_text())["stdout"]
        == "deliberate inconclusive diagnostic" for number in range(1, 4))
    report = json.loads((output / "proof-report.json").read_text())
    assert report["qualified"] is False
    assert all(flag is False for flag in report["mathematical_fragment_claims"].values())


def test_runner_exception_is_recorded_without_inventing_process(tmp_path, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("explicit runner failure")
    monkeypatch.setattr(subject, "_compile_alignment_lean", fail)
    output = tmp_path / "runner-error"
    with pytest.raises(subject.AlignmentProjectionError, match="diagnostic retained"):
        subject.compile_alignment_proofs(projection=project(), output=output,
            lean_executable=Path("/bin/true").resolve())
    diagnostic = json.loads((output / "check-01-runner-error.json").read_text())
    assert diagnostic["process_result_observed"] is False
    assert diagnostic["class"] == "RuntimeError"
    assert diagnostic["message"] == "explicit runner failure"


def test_existing_output_refused_before_any_check(tmp_path):
    with pytest.raises(subject.AlignmentProjectionError, match="fresh canonical output"):
        subject.compile_alignment_proofs(projection=project(), output=tmp_path,
            lean_executable=Path("/bin/true").resolve())
