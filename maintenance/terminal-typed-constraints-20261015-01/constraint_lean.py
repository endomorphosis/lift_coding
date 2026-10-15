"""Candidate finite scheduler semantics and bounded native Lean kernel checks.

The exact authored mathematical model is separate from source execution,
IntentIR meaning, original-task completion, and neural convergence.
"""
from __future__ import annotations
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
ROOT = Path(__file__).resolve().parent
DATASETS = ROOT.parent / "terminal-compact-retrieval-20261011-01" / "pinned-dependencies-v10" / "datasets" / "ipfs_datasets_py"
LEAN = Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean")
SCHEMA = "terminal-typed-scheduler-lean-theory@1"
LEAN_SCHEMA = "terminal-typed-scheduler-lean-evidence@1"
LEAN_MEMORY_MB = 1024
LEAN_PROFILE = "direct-installed-lean-finite-scheduler-single-thread-rss1024MiB@1"
AUTHORITY = {name: False for name in (
    "proof_authority", "execution_authority", "completion_authority", "omission_authority",
    "source_semantics_verified", "original_task_satisfaction", "source_model_equivalence_proved",
    "convergence_proved", "native_fol_lean_equivalence_proved", "threshold_measurements_observed")}
_UNRESOLVED_NATIVE = []
def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _wire(value):
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _need(depth <= 64 and count <= 500_000, "bounded inert JSON required")
        if type(item) is dict:
            _need(all(type(key) is str for key in item), "exact JSON keys required")
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        else:
            _need(type(item) in (str, bool, int, float, type(None)), "exact inert JSON values required")
            _need(type(item) is not float or math.isfinite(item), "finite JSON required")
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("utf-8")
    _need(len(raw) <= 32 * 1024**2, "bounded projection report required")
    return raw


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _finish(value):
    value["report_sha256"] = _sha(_wire(value))
    return value


def _read(path, maximum=64 * 1024**2):
    from capsule_io import read
    return read(path, maximum)


def _write(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _pin(path, maximum=64 * 1024**2):
    raw = _read(path, maximum)
    return {"path": str(path), "sha256": _sha(raw), "bytes": len(raw)}




def _lease_check(lease):
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLease
    _need(type(lease) is ResourceLease and lease.owner_pid == os.getpid()
        and not lease.released and not lease.cancelled, "current original native resource lease required")
    _need(lease._scheduler.state_path == Path("/tmp") / ("ipfs-datasets-resource-scheduler-" + str(os.getuid()) + ".json")
        and lease._scheduler.config.proof_safety_enabled is True
        and lease._scheduler.config.proof_recovery_enabled is False,
        "original shared proof-safe resource scheduler required")


def _environment():
    return {"PATH": str(LEAN.parent) + ":/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}


def _limits():
    from ipfs_datasets_py.logic.backends.process import ToolRunLimits
    return ToolRunLimits(timeout_seconds=25, cpu_seconds=25,
        resident_memory_bytes=LEAN_MEMORY_MB * 1024**2, max_input_bytes=1024**2,
        max_output_bytes=262144, max_workspace_bytes=16 * 1024**2)


def _limit_record():
    return {"timeout_seconds": 25, "cpu_seconds": 25, "resident_memory_bytes": LEAN_MEMORY_MB * 1024**2,
        "max_input_bytes": 1024**2, "max_output_bytes": 262144, "max_workspace_bytes": 16 * 1024**2}


def _run_lean(*, source, label, output, lease, expected_success):
    from ipfs_datasets_py.logic.backends.process import (SubprocessExecutor, ProcessInvocation,
        ToolRuntime, OwnedToolCleanupError)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    _lease_check(lease)
    raw_source = source.encode("utf-8")
    _need(0 < len(raw_source) <= 1024**2, "bounded generated Lean theory required")
    source_path = output / (label + ".lean")
    _write(source_path, raw_source)
    before = _pin(LEAN)
    executor_path = Path(importlib.import_module("ipfs_datasets_py.logic.backends.process").__file__).resolve()
    executor_pin = _pin(executor_path)
    prlimit_pin = _pin(Path("/usr/bin/prlimit"))
    temporary = tempfile.TemporaryDirectory(prefix="constraint-lean-", dir=str(output))
    workspace = Path(temporary.name)
    (workspace / "ConstraintTheory.lean").write_bytes(raw_source)
    command = (str(LEAN), "-j", "1", "ConstraintTheory.lean")
    environment = _environment()
    child = lease.acquire_child(lane=ResourceLane.VALIDATION, cpu_slots=1, memory_mb=LEAN_MEMORY_MB,
        child_process_slots=1, timeout=20, request_id="terminal-typed-constraint:" + label)
    result, cleaned, unresolved, handle = None, False, False, None
    def retain_unresolved():
        nonlocal unresolved
        if not unresolved:
            temporary._finalizer.detach()
            _UNRESOLVED_NATIVE.append((handle, child, lease, temporary))
            unresolved = True
    try:
        _lease_check(child)
        invocation = ProcessInvocation(argv=command, runtime=ToolRuntime.NATIVE,
            cwd=workspace, environment=environment, stdin=None, limits=_limits(), owned_process_observation=True)
        try:
            result = SubprocessExecutor().execute(invocation,
                cancellation=lambda: lease.released or lease.cancelled or child.released or child.cancelled)
        except OwnedToolCleanupError as error:
            handle = error.cleanup_handle
            try:
                handle.attach_workspace(temporary)
                observation = handle.retry_cleanup()
                cleaned = observation.cleanup_confirmed
            finally:
                if not cleaned:
                    retain_unresolved()
            raise
        _need(result.native_cleanup_handle is not None and result.native_lifecycle is not None,
              "original native sampled lifecycle observation required")
        handle = result.native_cleanup_handle
        try:
            handle.attach_workspace(temporary)
            observation = handle.retry_cleanup()
            cleaned = observation.cleanup_confirmed
        finally:
            if not cleaned:
                retain_unresolved()
        if not cleaned:
            retain_unresolved()
        _need(cleaned, "native process/workspace cleanup incomplete; child reservation retained")
    finally:
        if not unresolved:
            if result is None or result.native_cleanup_handle is None:
                temporary.cleanup()
            child.release()
    after = _pin(LEAN)
    stdout = result.stdout.decode("utf-8", errors="strict") if type(result.stdout) is bytes else result.stdout
    stderr = result.stderr.decode("utf-8", errors="strict") if type(result.stderr) is bytes else result.stderr
    bounded = not any((result.timed_out, result.cancelled, result.output_truncated,
        result.resource_exhausted, result.workspace_limit_exceeded, result.error))
    valid = result.returncode == 0 and bounded and before == after and cleaned
    rejected = result.returncode is not None and result.returncode != 0 and bounded and before == after and cleaned
    report = {"schema": "terminal-native-constraint-lean-process@1", "label": label,
        "source": _pin(source_path, 1024**2), "requested_command": list(command),
        "actual_invocation_command": list(invocation.argv), "native_resource_wrapper": "original SubprocessExecutor prlimit",
        "executable": before, "executable_after": after, "executor": executor_pin, "prlimit": prlimit_pin,
        "environment": environment, "inherited_environment": False,
        "limits": _limit_record(),
        "child_resource_request": {"cpu_slots": 1, "memory_mb": LEAN_MEMORY_MB, "child_process_slots": 1},
        "native_shared_child_lease_used": True, "lean_threads": 1,
        "native_lifecycle": observation.to_dict(), "pid": result.pid, "returncode": result.returncode,
        "stdout": stdout, "stderr": stderr, "timed_out": result.timed_out, "cancelled": result.cancelled,
        "output_truncated": result.output_truncated, "resource_exhausted": result.resource_exhausted,
        "workspace_limit_exceeded": result.workspace_limit_exceeded, "error": result.error,
        "elapsed_seconds": result.elapsed_seconds, "backend_executed": result.pid is not None,
        "workspace_cleaned": cleaned, "expected_success": expected_success,
        "status": "passed" if valid else "rejected" if rejected else "inconclusive",
        "matches_expectation": valid if expected_success else rejected, **AUTHORITY}
    _write(output / (label + "-process.json"), _wire(report))
    return report




LEAN_LABELS = ("finite-scheduler", "false-duplicate-missing-ids", "false-nine-global-shapes",
    "false-inconsistent-batch", "false-insufficient-alignment")

GENERIC_THEOREMS = [
    'coverage_permutation', 'accepted_ids_have_count_one', 'accepted_cardinality',
    'accepted_no_unexpected_ids', 'accepted_output_ids_nodup', 'shape_check_sound',
    'aligned_ceiling_covers_prompt', 'global_cap_check_sound', 'batch_check_sound',
    'fraction_below_check_sound']

MODEL = r'''import Init
namespace SchedulerConstraint
set_option autoImplicit false
set_option maxRecDepth 4096
structure Request where
  id : String
  prompt : Nat
  generated : Nat
  deriving DecidableEq, BEq, ReflBEq, LawfulBEq, Repr
structure Shape where
  seq : Nat
  heads : Nat
  hidden : Nat
  deriving DecidableEq, BEq, ReflBEq, LawfulBEq, Repr
structure Row where
  id : String
  batch : String
  shape : Shape
  deriving DecidableEq, BEq, ReflBEq, LawfulBEq, Repr
structure Fraction where
  numerator : Nat
  denominator : Nat
  deriving DecidableEq, Repr
structure Metrics where
  cost : Fraction
  padding : Fraction
  latency : Fraction
  sequential : Fraction
  deriving DecidableEq, Repr
structure Bucket where
  requests : List Request
  rows : List Row
  metrics : Metrics
  before : String
  after : String
  deriving DecidableEq, Repr

def inputIDs (requests : List Request) : List String := requests.map Request.id
def outputIDs (rows : List Row) : List String := rows.map Row.id
def coverageCheck (requests : List Request) (rows : List Row) : Bool :=
  (outputIDs rows).isPerm (inputIDs requests)
def ceil64 (prompt : Nat) : Nat := ((prompt + 63) / 64) * 64

def shapeCheck (request : Request) (row : Row) : Bool :=
  decide (row.shape.heads = 32 ∧ row.shape.hidden = 4096 ∧
    row.shape.seq % 64 = 0 ∧ ceil64 request.prompt ≤ row.shape.seq)
def allShapeCheck (requests : List Request) (rows : List Row) : Bool :=
  rows.all (fun row => requests.any (fun request => request.id == row.id && shapeCheck request row))
def batchCheck (rows : List Row) : Bool :=
  rows.all (fun a => rows.all (fun b => a.batch != b.batch || a.shape == b.shape))
def usedShapes (a b : List Row) : List Shape := ((a ++ b).map Row.shape).eraseDups
def globalCapCheck (a b : List Row) : Bool := decide ((usedShapes a b).length ≤ 8)
def fractionBelowCheck (value : Fraction) (numerator denominator : Nat) : Bool :=
  decide (0 < value.denominator ∧ 0 < denominator ∧
    value.numerator * denominator < numerator * value.denominator)
def thresholdCheck (metrics : Metrics) (bucket : Nat) : Bool :=
  if bucket = 1 then
    fractionBelowCheck metrics.cost 300000000000 1 &&
    fractionBelowCheck metrics.padding 55 1000 &&
    fractionBelowCheck metrics.latency 2100000 1 &&
    fractionBelowCheck metrics.sequential 270000000 1
  else
    fractionBelowCheck metrics.cost 48000000000 1 &&
    fractionBelowCheck metrics.padding 15 100 &&
    fractionBelowCheck metrics.latency 210000 1 &&
    fractionBelowCheck metrics.sequential 32000000 1

def bucketCheck (bucket : Bucket) (bucketID : Nat) : Bool :=
  coverageCheck bucket.requests bucket.rows &&
  decide (inputIDs bucket.requests).Nodup &&
  allShapeCheck bucket.requests bucket.rows && batchCheck bucket.rows &&
  thresholdCheck bucket.metrics bucketID && decide (bucket.before = bucket.after)
def modelAccept (a b : Bucket) : Bool :=
  bucketCheck a 1 && bucketCheck b 2 && globalCapCheck a.rows b.rows

theorem coverage_permutation (requests : List Request) (rows : List Row)
    (accepted : coverageCheck requests rows = true) :
    (outputIDs rows).Perm (inputIDs requests) := by
  exact List.isPerm_iff.mp accepted

theorem accepted_ids_have_count_one (requests : List Request) (rows : List Row)
    (accepted : coverageCheck requests rows = true)
    (uniqueInput : (inputIDs requests).Nodup) (id : String)
    (member : id ∈ inputIDs requests) : (outputIDs rows).count id = 1 := by
  exact ((coverage_permutation requests rows accepted).count_eq id).trans
    (uniqueInput.count_of_mem member)

theorem accepted_cardinality (requests : List Request) (rows : List Row)
    (accepted : coverageCheck requests rows = true) : rows.length = requests.length := by
  simpa [inputIDs, outputIDs] using (coverage_permutation requests rows accepted).length_eq

theorem accepted_no_unexpected_ids (requests : List Request) (rows : List Row)
    (accepted : coverageCheck requests rows = true) (id : String)
    (member : id ∈ outputIDs rows) : id ∈ inputIDs requests := by
  exact (coverage_permutation requests rows accepted).mem_iff.mp member

theorem accepted_output_ids_nodup (requests : List Request) (rows : List Row)
    (accepted : coverageCheck requests rows = true)
    (uniqueInput : (inputIDs requests).Nodup) : (outputIDs rows).Nodup := by
  exact (coverage_permutation requests rows accepted).symm.nodup uniqueInput

theorem shape_check_sound (request : Request) (row : Row)
    (accepted : shapeCheck request row = true) :
    row.shape.heads = 32 ∧ row.shape.hidden = 4096 ∧
    row.shape.seq % 64 = 0 ∧ ceil64 request.prompt ≤ row.shape.seq := by
  exact of_decide_eq_true accepted

theorem aligned_ceiling_covers_prompt (prompt : Nat) : prompt ≤ ceil64 prompt := by
  unfold ceil64
  omega

theorem global_cap_check_sound (a b : List Row) (accepted : globalCapCheck a b = true) :
    (usedShapes a b).length ≤ 8 := by
  exact of_decide_eq_true accepted

theorem batch_check_sound (rows : List Row) (accepted : batchCheck rows = true)
    (a b : Row) (ha : a ∈ rows) (hb : b ∈ rows) (sameBatch : a.batch = b.batch) :
    a.shape = b.shape := by
  have outer := List.all_eq_true.mp accepted a ha
  have inner := List.all_eq_true.mp outer b hb
  simpa [sameBatch] using inner

theorem fraction_below_check_sound (value : Fraction) (numerator denominator : Nat)
    (accepted : fractionBelowCheck value numerator denominator = true) :
    0 < value.denominator ∧ 0 < denominator ∧
    value.numerator * denominator < numerator * value.denominator := by
  exact of_decide_eq_true accepted
'''


def _lean_string(value):
    _need(type(value) is str and not any(ord(c) < 32 and c not in '\n\t\r' for c in value),
          'bounded printable candidate model strings required')
    return json.dumps(value, ensure_ascii=False)


def _nat(value):
    _need(type(value) is int and 0 <= value <= 10**18, 'exact bounded nonnegative mathematical integer required')
    return str(value)


def _list(values):
    return '[' + ', '.join(values) + ']'


def _request(row):
    return '{ id := ' + _lean_string(row['request_id']) + ', prompt := ' + _nat(row['prompt_len']) + ', generated := ' + _nat(row['gen_len']) + ' }'


def _shape(row):
    return '{ seq := ' + _nat(row['seq_align']) + ', heads := ' + _nat(row['heads_align']) + ', hidden := ' + _nat(row['hidden_align']) + ' }'


def _row(row):
    return '{ id := ' + _lean_string(row['request_id']) + ', batch := ' + _lean_string(row['batch_id']) + ', shape := ' + _shape(row['shape']) + ' }'


def _fraction(row):
    return '{ numerator := ' + _nat(row['numerator']) + ', denominator := ' + _nat(row['denominator']) + ' }'


def _bucket(bucket):
    metrics = bucket['metrics']
    return ('{ requests := ' + _list([_request(row) for row in bucket['requests']]) +
        ', rows := ' + _list([_row(row) for row in bucket['plan']]) +
        ', metrics := { cost := ' + _fraction(metrics['cost']) + ', padding := ' + _fraction(metrics['pad_ratio']) +
        ', latency := ' + _fraction(metrics['p95_latency_ms']) + ', sequential := ' + _fraction(metrics['sequential_time_ms']) +
        ' }, before := ' + _lean_string(bucket['input_before']) + ', after := ' + _lean_string(bucket['input_after']) + ' }')


def _inputs(contract, cases):
    from scheduler_constraints import validate_scheduler_contract, evaluate_case, validate_case_evaluation
    validate_scheduler_contract(contract, instruction=contract["instruction"]["source_text"].encode("utf-8"),
        head=contract["head"], source_records=contract["sources"])
    _wire(contract)
    _need(type(cases) is list and 2 <= len(cases) <= 128, 'bounded complete authored case descriptor inventory required')
    seen, accepted = set(), []
    for descriptor in cases:
        _need(type(descriptor) is dict and set(descriptor) == {'case', 'expected_pass', 'intended_violation_ids'}
            and type(descriptor['expected_pass']) is bool and type(descriptor['intended_violation_ids']) is list
            and all(type(value) is str for value in descriptor['intended_violation_ids']), 'closed authored case descriptors required')
        case = descriptor['case']
        result = evaluate_case(contract, case)
        validate_case_evaluation(result, contract=contract, case=case)
        _need(result['evaluation_passed'] is descriptor['expected_pass'], 'authored case expectation differs from exact model evaluator')
        observed = {row['requirement_id'] for row in result['violations']}
        _need(set(descriptor['intended_violation_ids']) <= observed,
            'authored intended violations differ from actual finite checker refusal')
        identity = case.get('case_id') if type(case) is dict else None
        _need(type(identity) is str and identity not in seen, 'unique exact authored case identities required')
        seen.add(identity)
        if descriptor['expected_pass']:
            accepted.append(case)
    _need(len(accepted) >= 2, 'at least two actual accepted authored finite model cases required')
    return accepted


def build_lean_theory(*, contract, cases):
    """Render only our fixed generator after exact contract/case replay."""
    accepted = _inputs(contract, cases)
    common = MODEL
    common += '\ndef contractSHA256 : String := ' + _lean_string(_sha(_wire(contract))) + '\n'
    common += 'def completeCasesSHA256 : String := ' + _lean_string(_sha(_wire(cases))) + '\n'
    theorem_names = list(GENERIC_THEOREMS)
    for index, case in enumerate(accepted):
        buckets = sorted(case['buckets'], key=lambda row: row['bucket_id'])
        _need([row['bucket_id'] for row in buckets] == [1, 2], 'exact two accepted finite buckets required')
        common += '\ndef case' + str(index) + 'Bucket1 : Bucket := ' + _bucket(buckets[0]) + '\n'
        common += 'def case' + str(index) + 'Bucket2 : Bucket := ' + _bucket(buckets[1]) + '\n'
        name = 'authored_case_' + str(index) + '_accepted'
        common += 'theorem ' + name + ' : modelAccept case' + str(index) + 'Bucket1 case' + str(index) + 'Bucket2 = true := by decide\n'
        theorem_names.append(name)
    witness = r'''
def controlRequests : List Request := [{ id := "r1", prompt := 65, generated := 1 }, { id := "r2", prompt := 65, generated := 1 }]
def row1 : Row := { id := "r1", batch := "same-batch", shape := { seq := 128, heads := 32, hidden := 4096 } }
def row2 : Row := { id := "r2", batch := "same-batch", shape := { seq := 192, heads := 32, hidden := 4096 } }
def nineShapeRows : List Row := (List.range 9).map (fun n => { id := "r", batch := "b", shape := { seq := (n + 1) * 64, heads := 32, hidden := 4096 } })
'''
    common += witness
    positive = common + ''.join('#print axioms ' + name + '\n' for name in theorem_names) + 'end SchedulerConstraint\n'
    controls = [
        ('false-duplicate-missing-ids', 'coverageCheck controlRequests [row1, row1] = true'),
        ('false-nine-global-shapes', 'globalCapCheck (nineShapeRows.take 5) (nineShapeRows.drop 5) = true'),
        ('false-inconsistent-batch', 'batchCheck [row1, row2] = true'),
        ('false-insufficient-alignment', 'shapeCheck { id := "r1", prompt := 65, generated := 1 } { id := "r1", batch := "b", shape := { seq := 64, heads := 32, hidden := 4096 } } = true')]
    sources = [{'label': 'finite-scheduler', 'source': positive, 'expected_success': True}]
    for label, proposition in controls:
        source = MODEL + witness + '\ntheorem deliberate_false_control : ' + proposition + ' := by decide\nend SchedulerConstraint\n'
        sources.append({'label': label, 'source': source, 'expected_success': False})
    return _finish({'schema': SCHEMA, 'contract': json.loads(_wire(contract)), 'cases': json.loads(_wire(cases)),
        'contract_sha256': _sha(_wire(contract)), 'cases_sha256': _sha(_wire(cases)),
        'sources': sources, 'theorems': theorem_names,
        'accepted_case_ids': [case['case_id'] for case in accepted],
        'model_semantics': 'explicit_authored_bucket_qualified_finite_Nat_model_with_exact_fraction_comparisons',
        'native_intent_projection_used': False, 'native_fol_lean_correspondence': 'unproved',
        'training_steps': 0, 'provider_calls': 0, **AUTHORITY})


def _lean_sources(theory):
    _need(type(theory) is dict and type(theory.get('contract')) is dict and type(theory.get('cases')) is list,
          'complete exact finite scheduler theory required')
    expected = build_lean_theory(contract=theory['contract'], cases=theory['cases'])
    _need(_wire(theory) == _wire(expected), 'theory differs from exact contract/case generator replay')
    return [(row['label'], row['source'], row['expected_success']) for row in expected['sources']]


def producer_paths():
    from scheduler_constraints import __file__ as contract_source
    paths = [Path(__file__), Path(contract_source), LEAN, Path('/usr/bin/prlimit'),
        Path(importlib.import_module('ipfs_datasets_py.logic.backends.process').__file__).resolve()]
    _need(paths[-1].is_relative_to(DATASETS), 'original pinned native process executor required')
    return sorted(set(paths))


def compile_constraint_theory(theory, *, output, lease):
    _lease_check(lease)
    _need(isinstance(output, Path) and output.is_absolute() and output.resolve() == output
        and output.is_relative_to(ROOT) and not output.exists() and output.parent.is_dir(),
        'fresh canonical owned Lean output directory required')
    sources = _lean_sources(theory)
    _need(len(sources) == 5, 'exact one positive and four false compiler processes required')
    output.mkdir(mode=0o700)
    checks = [_run_lean(source=source, label=label, output=output, lease=lease,
        expected_success=expected) for label, source, expected in sources]
    report = _finish({'schema': LEAN_SCHEMA, 'theory_sha256': _sha(_wire(theory)),
        'profile': LEAN_PROFILE, 'lake_convenience_helper_used': False, 'checks': checks,
        'positive_compiles': sum(row['expected_success'] and row['status'] == 'passed' for row in checks),
        'false_controls_rejected': sum(not row['expected_success'] and row['status'] == 'rejected' for row in checks),
        'qualified': all(row['matches_expectation'] for row in checks),
        'syntax_typecheck_only': False, 'proved_theorems': list(theory['theorems']),
        'proof_scope': 'defined_authored_finite_model_only_not_source_semantics_or_IntentIR_equivalence',
        'training_steps': 0, 'provider_calls': 0, **AUTHORITY})
    _write(output / 'report.json', _wire(report))
    validate_constraint_lean_evidence(report, theory=theory, output=output)
    return report


def validate_constraint_lean_evidence(report, *, theory, output):
    """Check retained historical process evidence; never restore dispatch rights."""
    root_fields = {"schema", "theory_sha256", "profile", "lake_convenience_helper_used", "checks",
        "positive_compiles", "false_controls_rejected", "qualified", "syntax_typecheck_only",
        "proved_theorems", "training_steps", "provider_calls", "report_sha256", "proof_scope", *AUTHORITY}
    _need(type(report) is dict and set(report) == root_fields and report.get("schema") == LEAN_SCHEMA,
          "direct native declaration Lean evidence required")
    _need(isinstance(output, Path) and output.is_absolute() and output.resolve() == output
        and output.is_relative_to(ROOT) and output.is_dir(), "canonical owned retained Lean directory required")
    _need(report["profile"] == LEAN_PROFILE
        and type(report["training_steps"]) is int and report["training_steps"] == 0
        and type(report["provider_calls"]) is int and report["provider_calls"] == 0,
        "closed direct compiler profile and zero model activity required")
    _need(report.get("report_sha256") == _sha(_wire({k: v for k, v in report.items() if k != "report_sha256"}))
        and report.get("theory_sha256") == _sha(_wire(theory)), "Lean evidence projection or report binding differs")
    sources = _lean_sources(theory)
    checks = report["checks"]
    _need(type(checks) is list and len(checks) == len(sources), "complete positive/control process inventory required")
    births = set()
    for check, (label, source, expected) in zip(checks, sources):
        check_fields = {"schema", "label", "source", "requested_command", "actual_invocation_command",
            "native_resource_wrapper", "executable", "executable_after", "executor", "prlimit", "environment",
            "inherited_environment", "limits", "child_resource_request", "native_shared_child_lease_used",
            "lean_threads", "native_lifecycle", "pid", "returncode", "stdout", "stderr", "timed_out",
            "cancelled", "output_truncated", "resource_exhausted", "workspace_limit_exceeded", "error",
            "elapsed_seconds", "backend_executed", "workspace_cleaned", "expected_success", "status",
            "matches_expectation", *AUTHORITY}
        _need(type(check) is dict and set(check) == check_fields
            and check["schema"] == "terminal-native-constraint-lean-process@1", "closed native compiler process receipt required")
        _need(type(check["pid"]) is int and check["pid"] > 0
            and type(check["returncode"]) is int and type(check["lean_threads"]) is int
            and type(check["elapsed_seconds"]) in (int, float) and not isinstance(check["elapsed_seconds"], bool)
            and math.isfinite(check["elapsed_seconds"]) and 0 <= check["elapsed_seconds"] <= 30
            and all(type(check[field]) is str for field in ("stdout", "stderr", "error")),
            "exact bounded compiler result types required")
        _need(_wire(check) == _read(output / (label + "-process.json"), 1024**2), "retained compiler receipt changed")
        _need(check["label"] == label and check["expected_success"] is expected
            and check["source"] == _pin(output / (label + ".lean"), 1024**2)
            and _read(output / (label + ".lean"), 1024**2) == source.encode(), "compiler source differs from regenerated declaration/control")
        expected_producers = {"executable": LEAN,
            "executor": Path(importlib.import_module("ipfs_datasets_py.logic.backends.process").__file__).resolve(),
            "prlimit": Path("/usr/bin/prlimit")}
        for field, path in expected_producers.items():
            _need(_wire(check[field]) == _wire(_pin(path)), "actual compiler/runtime producer bytes changed")
        command = [str(LEAN), "-j", "1", "ConstraintTheory.lean"]
        _need(check["requested_command"] == check["actual_invocation_command"] == command
            and check["executable"] == check["executable_after"] and check["environment"] == _environment()
            and check["inherited_environment"] is False and check["lean_threads"] == 1,
            "exact single-thread compiler command/environment required")
        _need(_wire(check["limits"]) == _wire(_limit_record())
            and check["native_resource_wrapper"] == "original SubprocessExecutor prlimit",
            "closed finite compiler resource bounds required")
        lifecycle = check["native_lifecycle"]
        lifecycle_fields = {"schema", "parent", "leader", "observed_descendants", "leader_reaped",
            "descendant_tracking_complete", "group_scan_complete", "remaining_group_members",
            "remaining_tracked_descendants", "readers", "stdin_writer", "workspace", "observation_errors",
            "ownership_is_sampled", "kernel_containment_attested", "cleanup_confirmed"}
        _need(type(lifecycle) is dict and set(lifecycle) == lifecycle_fields
            and lifecycle["schema"] == "native-owned-tool-lifecycle@1"
            and lifecycle["ownership_is_sampled"] is True and lifecycle["kernel_containment_attested"] is False
            and lifecycle["descendant_tracking_complete"] is True and lifecycle["group_scan_complete"] is True,
            "closed sampled native lifecycle required")
        def exact_identity(value, fields):
            return type(value) is dict and set(value) == set(fields) and all(type(item) is int and item > 0 for item in value.values())
        identity_fields = ("pid", "birth_ticks", "parent_pid", "process_group_id", "session_id")
        _need(exact_identity(lifecycle["parent"], ("pid", "birth_ticks"))
            and exact_identity(lifecycle["leader"], identity_fields)
            and type(lifecycle["observed_descendants"]) is list
            and all(exact_identity(identity, identity_fields) for identity in lifecycle["observed_descendants"])
            and _wire(lifecycle["readers"]) == _wire({"started": 2, "joined": 2})
            and _wire(lifecycle["stdin_writer"]) == _wire({"started": 0, "joined": 0})
            and type(lifecycle["workspace"]) is dict and set(lifecycle["workspace"]) == {"device", "inode", "removed"}
            and type(lifecycle["workspace"]["device"]) is int and lifecycle["workspace"]["device"] >= 0
            and type(lifecycle["workspace"]["inode"]) is int and lifecycle["workspace"]["inode"] > 0,
            "exact historical process, pipe and workspace identities required")
        leader = lifecycle["leader"]
        _need(leader["parent_pid"] == lifecycle["parent"]["pid"]
            and leader["process_group_id"] == leader["session_id"] == leader["pid"],
            "native compiler must have its own sampled process session")
        birth = (leader["pid"], leader["birth_ticks"])
        _need(leader["pid"] == check["pid"] and type(leader["birth_ticks"]) is int and leader["birth_ticks"] > 0
            and birth not in births and lifecycle["cleanup_confirmed"] is True
            and lifecycle["leader_reaped"] is True and lifecycle["workspace"]["removed"] is True
            and lifecycle["observation_errors"] == [] and lifecycle["remaining_group_members"] == []
            and lifecycle["remaining_tracked_descendants"] == [], "complete distinct historical native process cleanup required")
        births.add(birth)
        _need(check["native_shared_child_lease_used"] is True and check["backend_executed"] is True
            and check["workspace_cleaned"] is True and check["matches_expectation"] is True
            and _wire(check["child_resource_request"]) == _wire({"cpu_slots": 1, "memory_mb": LEAN_MEMORY_MB, "child_process_slots": 1})
            and all(check[key] is False for key in ("timed_out", "cancelled", "output_truncated", "resource_exhausted", "workspace_limit_exceeded"))
            and check["error"] == "" and all(check.get(key) is False for key in AUTHORITY),
            "bounded compiler observation or authority differs")
        if expected:
            _need("sorryAx" not in check["stdout"] and "uses 'sorry'" not in check["stdout"]
                and all(("SchedulerConstraint." + name) in check["stdout"] for name in theory["theorems"]),
                "every theorem must have actual axiom inspection without admitted holes")
            _need(check["status"] == "passed" and check["returncode"] == 0, "native generated declarations did not typecheck")
        else:
            _need(check["status"] == "rejected" and check["returncode"] != 0
                and "tactic `decide` proved that the proposition" in check["stdout"].lower()
                and "is false" in check["stdout"].lower(), "genuine kernel-rejected false theorem control required")
    _need(type(report["positive_compiles"]) is int and report["positive_compiles"] == 1
        and type(report["false_controls_rejected"]) is int and report["false_controls_rejected"] == 4
        and report["qualified"] is True and report["syntax_typecheck_only"] is False
        and report["proved_theorems"] == theory["theorems"]
        and report["proof_scope"] == "defined_authored_finite_model_only_not_source_semantics_or_IntentIR_equivalence" and report["lake_convenience_helper_used"] is False
        and all(report.get(key) is False for key in AUTHORITY), "Lean compilation scope or qualification differs")
    _need(_read(output / "report.json", 8 * 1024**2) == _wire(report), "retained complete Lean report changed")
    return report
