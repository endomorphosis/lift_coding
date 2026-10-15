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
SCHEMA = "terminal-total-jsonl-decoder-lean-theory@1"
LEAN_SCHEMA = "terminal-total-jsonl-decoder-lean-evidence@1"
LEAN_MEMORY_MB = 1024
LEAN_PROFILE = "direct-installed-lean-total-jsonl-decoder-single-thread-rss1024MiB@1"
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
    return ToolRunLimits(timeout_seconds=60, cpu_seconds=60,
        resident_memory_bytes=LEAN_MEMORY_MB * 1024**2, max_input_bytes=1024**2,
        max_output_bytes=262144, max_workspace_bytes=16 * 1024**2)


def _limit_record():
    return {"timeout_seconds": 60, "cpu_seconds": 60, "resident_memory_bytes": LEAN_MEMORY_MB * 1024**2,
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
    temporary = tempfile.TemporaryDirectory(prefix="decoder-lean-", dir=str(output))
    workspace = Path(temporary.name)
    (workspace / "DecoderTheory.lean").write_bytes(raw_source)
    command = (str(LEAN), "-j", "1", "DecoderTheory.lean")
    environment = _environment()
    child = lease.acquire_child(lane=ResourceLane.VALIDATION, cpu_slots=1, memory_mb=LEAN_MEMORY_MB,
        child_process_slots=1, timeout=20, request_id="terminal-total-jsonl-decoder:" + label)
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
    report = {"schema": "terminal-native-decoder-lean-process@1", "label": label,
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



DECODER_LABELS = ("jsonl-decoder", "false-altered-byte", "false-altered-row",
    "false-duplicate-key", "false-control-character", "false-incorrect-result")
PROOF_SCOPE = 'concrete_exact_byte_decoder_equalities_and_authored_finite_model_results_not_general_Python_or_source_equivalence'

FINITE_MODEL = r'''
namespace DecoderKernel
structure Fraction where
  numerator : Nat
  denominator : Nat
  deriving DecidableEq
structure Metrics where
  cost : Fraction
  padding : Fraction
  latency : Fraction
  sequential : Fraction
  deriving DecidableEq
structure Bucket where
  requests : List Request
  rows : List Row
  metrics : Metrics
  before : List Nat
  after : List Nat
  deriving DecidableEq
def inputIDs (requests : List Request) : List Scalars := requests.map Request.id
def outputIDs (rows : List Row) : List Scalars := rows.map Row.id
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
end DecoderKernel
'''


def _nats(values):
    _need(type(values) is list and len(values) <= 65536
        and all(type(n) is int and 0 <= n <= 1114111 for n in values),
        'bounded plain numeric list required')
    return '[' + ','.join(str(n) for n in values) + ']'


def _scalar_string(value):
    _need(type(value) is str, 'plain Unicode text required')
    value.encode('utf-8', errors='strict')
    return _nats([ord(c) for c in value])


def _natural(value):
    _need(type(value) is int and 0 <= value <= 10**18, 'exact bounded natural required')
    return str(value)


def _shape(value):
    _need(type(value) is dict and set(value) == {'seq_align', 'heads_align', 'hidden_align'},
        'exact shape fields required')
    return '{ seq := ' + _natural(value['seq_align']) + ', heads := ' + _natural(value['heads_align']) + ', hidden := ' + _natural(value['hidden_align']) + ' }'


def _request(value, *, scalars):
    _need(type(value) is dict and set(value) == {'request_id', 'prompt_len', 'gen_len'},
        'exact request fields required')
    identifier = _nats(value['request_id']) if scalars else _scalar_string(value['request_id'])
    return '{ id := ' + identifier + ', prompt := ' + _natural(value['prompt_len']) + ', generated := ' + _natural(value['gen_len']) + ' }'


def _row(value, *, scalars):
    _need(type(value) is dict and set(value) == {'request_id', 'batch_id', 'shape'},
        'exact plan fields required')
    identifier = _nats(value['request_id']) if scalars else _scalar_string(value['request_id'])
    batch = _nats(value['batch_id']) if scalars else _scalar_string(value['batch_id'])
    return '{ id := ' + identifier + ', batch := ' + batch + ', shape := ' + _shape(value['shape']) + ' }'


def _rows(rows, *, kind, scalars):
    _need(type(rows) is list and len(rows) <= 256, 'bounded exact row inventory required')
    render = _request if kind == 'requests' else _row
    return '[' + ','.join(render(row, scalars=scalars) for row in rows) + ']'


def _fraction(value):
    _need(type(value) is dict and set(value) == {'numerator', 'denominator'},
        'exact supplied rational fields required')
    return '{ numerator := ' + _natural(value['numerator']) + ', denominator := ' + _natural(value['denominator']) + ' }'


def _bucket(bucket):
    metrics = bucket['metrics']
    return ('{ requests := ' + _rows(bucket['requests'], kind='requests', scalars=False) +
        ', rows := ' + _rows(bucket['plan'], kind='plan', scalars=False) +
        ', metrics := { cost := ' + _fraction(metrics['cost']) + ', padding := ' + _fraction(metrics['pad_ratio']) +
        ', latency := ' + _fraction(metrics['p95_latency_ms']) + ', sequential := ' + _fraction(metrics['sequential_time_ms']) +
        ' }, before := ' + _nats(list(bucket['input_before'].encode('utf-8'))) +
        ', after := ' + _nats(list(bucket['input_after'].encode('utf-8'))) + ' }')


def _scalar_rows(rows, kind):
    out = []
    for value in rows:
        item = json.loads(_wire(value))
        item['request_id'] = [ord(c) for c in value['request_id']]
        if kind == 'plan':
            item['batch_id'] = [ord(c) for c in value['batch_id']]
        out.append(item)
    return out


def _kernel():
    raw = _read(ROOT / 'decoder_kernel.lean', 128 * 1024)
    text = raw.decode('utf-8', errors='strict')
    # Closed retained source template. No trusted evaluator or admitted holes.
    _need(all(token not in text for token in ('partial ', 'unsafe ', 'native_decide', 'axiom ', 'sorry', 'admit')),
        'total kernel-reducible decoder template required')
    _need(text.startswith('import Init\n') and text.endswith('end DecoderKernel\n'),
        'closed decoder namespace and core imports required')
    return text


def _validated_witnesses(witnesses):
    from strict_jsonl import parse_jsonl, StrictJSONLError
    _wire(witnesses)
    _need(type(witnesses) is dict and type(witnesses.get('witnesses')) is list
        and 2 <= len(witnesses['witnesses']) <= 512
        and type(witnesses.get('derived_cases')) is list
        and len(witnesses['derived_cases']) == 16, 'complete bounded byte witnesses and sixteen derived cases required')
    result, seen = [], set()
    for witness in witnesses['witnesses']:
        _need(type(witness) is dict and set(witness) == {'witness_id', 'kind', 'raw_hex', 'raw_bytes',
            'raw_sha256', 'expected_parse_success', 'expected_rows', 'origins'}, 'closed exact byte witness required')
        _need(type(witness['witness_id']) is str and witness['witness_id'] not in seen
            and witness['kind'] in ('requests', 'plan') and type(witness['kind']) is str,
            'unique exact witness identity and row kind required')
        seen.add(witness['witness_id'])
        _need(type(witness['raw_hex']) is str and len(witness['raw_hex']) <= 131072, 'bounded canonical hex bytes required')
        raw = bytes.fromhex(witness['raw_hex'])
        _need(raw.hex() == witness['raw_hex'] and type(witness['raw_bytes']) is int
            and witness['raw_bytes'] == len(raw) and witness['raw_sha256'] == _sha(raw), 'exact witness bytes differ')
        _need(type(witness['expected_parse_success']) is bool and type(witness['origins']) is list
            and len(witness['origins']) > 0, 'explicit concrete result and complete origins required')
        try:
            parsed = parse_jsonl(raw, kind=witness['kind'])
            rows, accepted = _scalar_rows(parsed['rows'], witness['kind']), True
        except StrictJSONLError:
            rows, accepted = None, False
        _need(witness['expected_parse_success'] is accepted and _wire(witness['expected_rows']) == _wire(rows),
            'retained expected rows differ from exact Python parser replay')
        result.append((witness, raw))
    return result


def build_decoder_theory(*, witnesses):
    """Emit concrete byte equalities, not a theorem about the Python program.

    Supplied origins, summaries and joins confer no filesystem authority. Callers
    must separately rebuild this report with ``build_decoder_witnesses`` from
    fully validated, currently observed file cases. The native experiment,
    cold verifier and finalizer enforce that independent provenance boundary.
    """
    checked = _validated_witnesses(witnesses)
    source = (_kernel() + FINITE_MODEL + '\nnamespace DecoderKernel\n'
        'set_option maxRecDepth 65536\nset_option maxHeartbeats 4000000\n')
    theorem_names = ['decoded_request_ids_unique', 'decoded_plan_ids_unique']
    dedup, joins, unique = {}, [], []
    for witness, raw in checked:
        key = (witness['kind'], raw)
        if key not in dedup:
            index = len(dedup)
            name = 'exact_file_' + str(index)
            raw_name = 'rawFile' + str(index)
            expected_name = 'expectedFile' + str(index)
            kind = witness['kind']
            typ = 'Request' if kind == 'requests' else 'Row'
            decoder = 'decodeRequests' if kind == 'requests' else 'decodePlans'
            expected = ('some ' + _rows(witness['expected_rows'], kind=kind, scalars=True)
                        if witness['expected_parse_success'] else 'none')
            source += '\ndef ' + raw_name + ' : List Nat := ' + _nats(list(raw)) + '\n'
            source += 'def ' + expected_name + ' : Option (List ' + typ + ') := ' + expected + '\n'
            source += 'theorem ' + name + ' : ' + decoder + ' ' + raw_name + ' = ' + expected_name + ' := by decide\n'
            theorem_names.append(name)
            dedup[key] = {'index': index, 'theorem': name, 'kind': kind, 'raw_bytes': len(raw),
                'raw_sha256': _sha(raw), 'expected_parse_success': witness['expected_parse_success']}
            unique.append(dedup[key])
        joins.append({'witness_id': witness['witness_id'], 'theorem': dedup[key]['theorem']})
    by_identity = {w['witness_id']: (w, raw) for w, raw in checked}
    case_bindings = witnesses.get('case_bindings')
    _need(type(case_bindings) is list, 'explicit byte-to-case bindings required for composed checks')
    composed_joins = []
    for index, descriptor in enumerate(witnesses['derived_cases']):
        _need(type(descriptor) is dict and set(descriptor) == {'case', 'expected_pass', 'intended_violation_ids'}
            and type(descriptor['expected_pass']) is bool, 'complete finite-case descriptors required')
        case = descriptor['case']
        buckets = sorted(case['buckets'], key=lambda row: row['bucket_id'])
        _need([b['bucket_id'] for b in buckets] == [1, 2], 'exact finite two-bucket join required')
        source += '\ndef case' + str(index) + 'Bucket1 : Bucket := ' + _bucket(buckets[0]) + '\n'
        source += 'def case' + str(index) + 'Bucket2 : Bucket := ' + _bucket(buckets[1]) + '\n'
        name = 'exact_model_' + str(index)
        source += 'theorem ' + name + ' : modelAccept case' + str(index) + 'Bucket1 case' + str(index) + 'Bucket2 = ' + ('true' if descriptor['expected_pass'] else 'false') + ' := by decide\n'
        theorem_names.append(name)
        selected = [binding for binding in case_bindings
                    if binding.get('derived_case_index') == index
                    and type(binding.get('derived_case_index')) is int]
        _need(len(selected) == 1 and selected[0].get('case_id') == case['case_id'],
            'exact one bound source case per composed model check required')
        binding, bound_files, rewrites = selected[0], [], []
        for bucket in buckets:
            bucket_id = bucket['bucket_id']
            request_path = 'input_data/requests_bucket_' + str(bucket_id) + '.jsonl'
            plan_path = 'output_data/plan_b' + str(bucket_id) + '.jsonl'
            for path, kind, field in ((request_path, 'requests', 'requests'), (plan_path, 'plan', 'plan')):
                identity = binding['files']['after'][path]
                _need(identity in by_identity, 'composed model refers to an unknown byte witness')
                witness, raw = by_identity[identity]
                _need(witness['kind'] == kind and witness['expected_parse_success'] is True
                    and _wire(witness['expected_rows']) == _wire(_scalar_rows(bucket[field], kind)),
                    'composed decoded rows differ from exact supplied finite-model rows')
                info = dedup[(kind, raw)]
                bound_files.append({'bucket_id': bucket_id, 'kind': kind, 'path': path,
                    'witness_id': identity, 'file_index': info['index'], 'decoder_theorem': info['theorem']})
                rewrites.extend([info['theorem'], 'expectedFile' + str(info['index'])])
            before_id = binding['files']['before'][request_path]
            after_id = binding['files']['after'][request_path]
            _need(before_id in by_identity and after_id in by_identity
                and by_identity[before_id][1] == bucket['input_before'].encode('utf-8')
                and by_identity[after_id][1] == bucket['input_after'].encode('utf-8'),
                'composed input-byte equality differs from actual bound raw request bytes')
        decoded_name = 'decodedOutcome' + str(index)
        source += '\ndef ' + decoded_name + ' : Option Bool := do\n'
        for file in bound_files:
            variable = ('requests' if file['kind'] == 'requests' else 'rows') + str(file['bucket_id'])
            decoder = 'decodeRequests' if file['kind'] == 'requests' else 'decodePlans'
            source += '  let ' + variable + ' ← ' + decoder + ' rawFile' + str(file['file_index']) + '\n'
        source += '  let a : Bucket := { case' + str(index) + 'Bucket1 with requests := requests1, rows := rows1 }\n'
        source += '  let b : Bucket := { case' + str(index) + 'Bucket2 with requests := requests2, rows := rows2 }\n'
        source += '  some (modelAccept a b)\n'
        composed_name = 'exact_decoded_model_' + str(index)
        source += 'theorem ' + composed_name + ' : ' + decoded_name + ' = some ' + ('true' if descriptor['expected_pass'] else 'false') + ' := by\n'
        simplifiers = [decoded_name, *dict.fromkeys(rewrites), 'Option.bind_eq_bind', 'Option.bind_some',
            'case' + str(index) + 'Bucket1', 'case' + str(index) + 'Bucket2']
        source += '  simpa only [' + ', '.join(simplifiers) + '] using congrArg (fun b : Bool => some b) ' + name + '\n'
        theorem_names.append(composed_name)
        composed_joins.append({'case_id': case['case_id'], 'derived_case_index': index,
            'theorem': composed_name, 'expected_pass': descriptor['expected_pass'], 'files': bound_files,
            'decode_success_required_before_model_evaluation': True, 'supplied_metrics_runtime_observed': False})
    source += ''.join('#print axioms ' + name + '\n' for name in theorem_names) + 'end DecoderKernel\n'
    good_raw = b'{"request_id":"r","prompt_len":64,"gen_len":1}\n'
    altered_raw = good_raw.replace(b':64', b':65')
    duplicate_raw = b'{"request_id":"r","request_id":"r","prompt_len":64,"gen_len":1}\n'
    control_raw = b'{"request_id":"\\b","prompt_len":64,"gen_len":1}\n'
    good_row = '{ id := [114], prompt := 64, generated := 1 }'
    zero = '{ numerator := 0, denominator := 1 }'
    empty_bucket = '{ requests := [], rows := [], metrics := { cost := ' + zero + ', padding := ' + zero + ', latency := ' + zero + ', sequential := ' + zero + ' }, before := [], after := [] }'
    good_plan = b'{"request_id":"r","batch_id":"b","shape":{"seq_align":64,"heads_align":32,"hidden_align":4096}}\n'
    decoded_control = ('def controlDecodedOutcome : Option Bool := do\n'
        '  let requests ← decodeRequests ' + _nats(list(good_raw)) + '\n'
        '  let rows ← decodePlans ' + _nats(list(good_plan)) + '\n'
        '  let a : Bucket := { ' + empty_bucket[2:-2] + ' }\n'
        '  let bucket : Bucket := { a with requests := requests, rows := rows }\n'
        '  some (modelAccept bucket bucket)\n')
    controls = [
        ('false-altered-byte', 'decodeRequests ' + _nats(list(altered_raw)) + ' = some [' + good_row + ']'),
        ('false-altered-row', 'decodeRequests ' + _nats(list(good_raw)) + ' = some [{ id := [114], prompt := 65, generated := 1 }]'),
        ('false-duplicate-key', 'decodeRequests ' + _nats(list(duplicate_raw)) + ' = some [' + good_row + ']'),
        ('false-control-character', 'decodeRequests ' + _nats(list(control_raw)) + ' = some [{ id := [12], prompt := 64, generated := 1 }]'),
        ('false-incorrect-result', 'controlDecodedOutcome = some false')]
    sources = [{'label': DECODER_LABELS[0], 'source': source, 'expected_success': True}]
    for label, proposition in controls:
        prefix = decoded_control if label == 'false-incorrect-result' else ''
        control = _kernel() + FINITE_MODEL + '\nnamespace DecoderKernel\n' + prefix + 'theorem deliberate_false_control : ' + proposition + ' := by decide\nend DecoderKernel\n'
        sources.append({'label': label, 'source': control, 'expected_success': False})
    _need(tuple(row['label'] for row in sources) == DECODER_LABELS, 'closed ordered native compiler inventory required')
    return _finish({'schema': SCHEMA, 'witnesses': json.loads(_wire(witnesses)),
        'witnesses_sha256': _sha(_wire(witnesses)), 'kernel_template': _pin(ROOT / 'decoder_kernel.lean'),
        'sources': sources, 'theorems': theorem_names, 'unique_files': unique,
        'witness_theorem_joins': joins, 'finite_model_case_count': 16,
        'composed_case_joins': composed_joins, 'composed_decoded_model_case_count': 16,
        'general_python_parser_equivalence_proved': False, 'general_checker_model_equivalence_proved': False,
        'source_runtime_semantics_verified': False, 'training_steps': 0, 'provider_calls': 0, **AUTHORITY})


def _lean_sources(theory):
    _need(type(theory) is dict and type(theory.get('witnesses')) is dict,
        'complete exact byte decoder theory required')
    expected = build_decoder_theory(witnesses=theory['witnesses'])
    _need(_wire(theory) == _wire(expected), 'theory differs from exact byte witness generator replay')
    return [(row['label'], row['source'], row['expected_success']) for row in expected['sources']]

def producer_paths():
    from scheduler_constraints import __file__ as contract_source
    paths = [Path(__file__), Path(contract_source), ROOT / "decoder_kernel.lean", LEAN, Path('/usr/bin/prlimit'),
        Path(importlib.import_module('ipfs_datasets_py.logic.backends.process').__file__).resolve()]
    _need(paths[-1].is_relative_to(DATASETS), 'original pinned native process executor required')
    return sorted(set(paths))


def compile_decoder_theory(theory, *, output, lease):
    _lease_check(lease)
    _need(isinstance(output, Path) and output.is_absolute() and output.resolve() == output
        and output.is_relative_to(ROOT) and not output.exists() and output.parent.is_dir(),
        'fresh canonical owned Lean output directory required')
    sources = _lean_sources(theory)
    _need(len(sources) == 6, 'exact one positive and five false compiler processes required')
    output.mkdir(mode=0o700)
    checks = [_run_lean(source=source, label=label, output=output, lease=lease,
        expected_success=expected) for label, source, expected in sources]
    report = _finish({'schema': LEAN_SCHEMA, 'theory_sha256': _sha(_wire(theory)),
        'profile': LEAN_PROFILE, 'lake_convenience_helper_used': False, 'checks': checks,
        'positive_compiles': sum(row['expected_success'] and row['status'] == 'passed' for row in checks),
        'false_controls_rejected': sum(not row['expected_success'] and row['status'] == 'rejected' for row in checks),
        'qualified': all(row['matches_expectation'] for row in checks),
        'syntax_typecheck_only': False, 'proved_theorems': list(theory['theorems']),
        'proof_scope': 'concrete_exact_byte_decoder_equalities_and_authored_finite_model_results_not_general_Python_or_source_equivalence',
        'training_steps': 0, 'provider_calls': 0, **AUTHORITY})
    _write(output / 'report.json', _wire(report))
    validate_decoder_evidence(report, theory=theory, output=output)
    return report


def validate_decoder_evidence(report, *, theory, output):
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
            and check["schema"] == "terminal-native-decoder-lean-process@1", "closed native compiler process receipt required")
        _need(type(check["pid"]) is int and check["pid"] > 0
            and type(check["returncode"]) is int and type(check["lean_threads"]) is int
            and type(check["elapsed_seconds"]) in (int, float) and not isinstance(check["elapsed_seconds"], bool)
            and math.isfinite(check["elapsed_seconds"]) and 0 <= check["elapsed_seconds"] <= 65
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
        command = [str(LEAN), "-j", "1", "DecoderTheory.lean"]
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
                and all(("DecoderKernel." + name) in check["stdout"] for name in theory["theorems"]),
                "every theorem must have actual axiom inspection without admitted holes")
            _need(check["status"] == "passed" and check["returncode"] == 0, "native generated declarations did not typecheck")
        else:
            _need(check["status"] == "rejected" and check["returncode"] != 0
                and "tactic `decide` proved that the proposition" in check["stdout"].lower()
                and "is false" in check["stdout"].lower(), "genuine kernel-rejected false theorem control required")
    _need(type(report["positive_compiles"]) is int and report["positive_compiles"] == 1
        and type(report["false_controls_rejected"]) is int and report["false_controls_rejected"] == 5
        and report["qualified"] is True and report["syntax_typecheck_only"] is False
        and report["proved_theorems"] == theory["theorems"]
        and report["proof_scope"] == "concrete_exact_byte_decoder_equalities_and_authored_finite_model_results_not_general_Python_or_source_equivalence" and report["lake_convenience_helper_used"] is False
        and all(report.get(key) is False for key in AUTHORITY), "Lean compilation scope or qualification differs")
    _need(_read(output / "report.json", 8 * 1024**2) == _wire(report), "retained complete Lean report changed")
    return report


# Explicit compatibility name for reviewers of the previous Lean evidence API.
validate_decoder_lean_evidence = validate_decoder_evidence
