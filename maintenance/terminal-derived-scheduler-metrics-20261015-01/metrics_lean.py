"""Concrete exact-decimal metric proofs over observed JSONL byte projections.

The retained source AST profile and independent source evaluator establish
replayable inputs.  The Lean kernel proves the closed mathematical projection,
not general Python implementation or binary64/source equivalence.
"""
from __future__ import annotations
import importlib
import json
import math
import re
from pathlib import Path

import decoder_lean as D
from decoder_lean import (_need, _wire, _sha, _read, _write, _pin, _finish,
    _lease_check, _environment, _limit_record, _run_lean, LEAN, LEAN_MEMORY_MB,
    DATASETS, AUTHORITY)

ROOT = Path(__file__).resolve().parent
SCHEMA = 'terminal-derived-decimal-metrics-lean-theory@1'
LEAN_SCHEMA = 'terminal-derived-decimal-metrics-lean-evidence@1'
LEAN_PROFILE = 'direct-installed-lean-derived-decimal-metrics-single-thread-rss1024MiB@1'
PROOF_SCOPE = 'concrete_exact_JSONL_decode_and_default_decimal_rational_metrics_not_binary64_or_Python_source_equivalence'
METRICS_LABELS = ('derived-metrics-0', 'derived-metrics-1', 'derived-metrics-2',
    'derived-metrics-3', 'false-cost', 'false-padding', 'false-p95',
    'false-compilation', 'false-sequential')


def _kernel():
    raw = _read(ROOT / 'metrics_kernel.lean', 128 * 1024)
    text = raw.decode('utf-8', errors='strict')
    _need(text.startswith('namespace DecoderKernel\n') and text.endswith('end DecoderKernel\n')
        and all(token not in text for token in ('partial ', 'unsafe ', 'native_decide',
            'axiom ', 'sorry', 'admit')), 'closed total metric kernel required')
    return D._kernel() + D.FINITE_MODEL + text


def _metrics(value):
    _need(type(value) is dict and set(value) == {'cost', 'pad_ratio', 'p95_latency_ms',
        'sequential_time_ms'}, 'exact four rational derived metrics required')
    return ('{ cost := ' + D._fraction(value['cost']) + ', padding := ' +
        D._fraction(value['pad_ratio']) + ', latency := ' +
        D._fraction(value['p95_latency_ms']) + ', sequential := ' +
        D._fraction(value['sequential_time_ms']) + ' }')


def _raw_metrics(derivation):
    """Retain the kernel's unreduced denominators for one closed calculation."""
    exact = derivation['exact_rational_metrics']
    def scaled(name):
        fraction = exact[name]
        numerator = fraction['numerator'] * 2500
        _need(numerator % fraction['denominator'] == 0, 'exact 1/2500 latency scale required')
        return {'numerator': numerator // fraction['denominator'], 'denominator': 2500}
    return {'cost': exact['cost'],
        'pad_ratio': {'numerator': derivation['pad_tokens'],
            'denominator': max(1, derivation['real_tokens'])},
        'p95_latency_ms': scaled('p95_latency_ms'),
        'sequential_time_ms': scaled('sequential_time_ms')}


def _validated_report(report):
    from source_metric_cases import validate_metric_case_data
    _wire(report)
    validate_metric_case_data(report)
    _need(type(report) is dict and type(report.get('entries')) is list
        and 1 <= len(report['entries']) <= 128, 'bounded complete metric case report required')
    return report


def _case_material(entry):
    from observed_files import decode_file
    from strict_jsonl import parse_jsonl
    buckets, files = [], []
    model = entry['model']
    _need(model is None or model['case']['case_id'] == entry['case_id'],
        'model case identity must match exact file entry')
    for number in (1, 2):
        parsed = {}
        for kind, path in (('requests', 'input_data/requests_bucket_' + str(number) + '.jsonl'),
                ('plan', 'output_data/plan_b' + str(number) + '.jsonl')):
            raw = decode_file(entry['after'], path)
            rows = parse_jsonl(raw, kind=kind)['rows']
            parsed[kind] = rows
            files.append({'bucket_id': number, 'kind': kind, 'path': path,
                'raw': raw, 'rows': rows})
        request_path = 'input_data/requests_bucket_' + str(number) + '.jsonl'
        zero = {'numerator': 0, 'denominator': 1}
        metrics = ({name: dict(zero) for name in ('cost', 'pad_ratio', 'p95_latency_ms',
            'sequential_time_ms')} if model is None else
            model['case']['buckets'][number - 1]['metrics'])
        bucket = {'bucket_id': number, 'requests': parsed['requests'], 'plan': parsed['plan'],
            'metrics': metrics,
            'input_before': decode_file(entry['before'], request_path).decode('utf-8'),
            'input_after': decode_file(entry['after'], request_path).decode('utf-8')}
        if model is not None:
            _need(_wire(bucket) == _wire(model['case']['buckets'][number - 1]),
                'derived model differs from independently parsed exact after bytes')
        buckets.append(bucket)
    return buckets, files


def build_metrics_theory(*, report):
    report = _validated_report(report)
    prefix = _kernel() + '\nnamespace DecoderKernel\n'
    prefix += 'set_option maxRecDepth 65536\nset_option maxHeartbeats 4000000\nset_option Elab.async false\n'
    source = prefix
    names, unique, cases, dedup, calculations = ['derivedModelAccept_of_metrics',
        'decodedDerivedModelAccept_of_decodes'], [], [], {}, {}
    source += '#print axioms derivedModelAccept_of_metrics\n#print axioms decodedDerivedModelAccept_of_decodes\n'
    probe_expressions = [
        ('sum_square_zero', 'sumSquares 64 0 = 0'),
        ('sum_square_one', 'sumSquares 64 1 = 4096'),
        ('sum_square_two', 'sumSquares 64 2 = 4096 + 4225'),
        ('sum_square_seven', 'sumSquares 64 7 = sumNats ((List.range 7).map (fun k => (64+k)*(64+k)))'),
        ('sum_linear_seven', 'sumLinear 64 7 = sumNats ((List.range 7).map (fun k => 64+k))'),
        ('nearest_rank_empty', 'p95Units [] = 0'),
        ('nearest_rank_twenty', 'p95Units (List.range 20) = 18'),
        ('nearest_rank_twenty_one', 'p95Units (List.range 21) = 19')]
    for name, expression in probe_expressions:
        source += 'theorem ' + name + ' : ' + expression + ' := by decide +kernel\n'
        source += '#print axioms ' + name + '\n'
        names.append(name)
    for index, entry in enumerate(report['entries']):
        buckets, files = _case_material(entry)
        rewrites, bindings = [], []
        for file in files:
            key = (file['kind'], file['raw'])
            if key not in dedup:
                file_index = len(dedup)
                raw_name, rows_name = 'metricRaw' + str(file_index), 'metricRows' + str(file_index)
                theorem = 'exact_metric_file_' + str(file_index)
                decoder = 'decodeRequests' if file['kind'] == 'requests' else 'decodePlans'
                typ = 'Request' if file['kind'] == 'requests' else 'Row'
                source += 'def ' + raw_name + ' : List Nat := ' + D._nats(list(file['raw'])) + '\n'
                source += 'def ' + rows_name + ' : List ' + typ + ' := ' + D._rows(file['rows'], kind=file['kind'], scalars=False) + '\n'
                source += 'theorem ' + theorem + ' : ' + decoder + ' ' + raw_name + ' = some ' + rows_name + ' := by decide +kernel\n'
                source += '#print axioms ' + theorem + '\n'
                names.append(theorem)
                info = {'file_index': file_index, 'raw_name': raw_name, 'rows_name': rows_name,
                    'theorem': theorem, 'kind': file['kind'], 'raw_bytes': len(file['raw']),
                    'raw_sha256': _sha(file['raw'])}
                dedup[key] = info
                unique.append(info)
            info = dedup[key]
            bindings.append({'bucket_id': file['bucket_id'], 'kind': file['kind'],
                'path': file['path'], **info})
            rewrites.extend([info['theorem'], info['rows_name']])
        calculation_bindings = []
        for number, bucket in enumerate(buckets, 1):
            bucket_name = 'metricCase' + str(index) + 'Bucket' + str(number)
            source += 'def ' + bucket_name + ' : Bucket := ' + D._bucket(bucket) + '\n'
            if entry['model'] is not None:
                key = _wire([bucket['requests'], bucket['plan']])
                if key not in calculations:
                    calculation_index = len(calculations)
                    calculation_prefix = 'metricCalculation' + str(calculation_index)
                    calculation = {'requests': calculation_prefix + 'Requests', 'rows': calculation_prefix + 'Rows',
                        'expected': calculation_prefix + 'Expected', 'theorem': 'exact_metric_calculation_' + str(calculation_index)}
                    source += 'def ' + calculation['requests'] + ' : List Request := ' + D._rows(bucket['requests'], kind='requests', scalars=False) + '\n'
                    source += 'def ' + calculation['rows'] + ' : List Row := ' + D._rows(bucket['plan'], kind='plan', scalars=False) + '\n'
                    raw_metrics = _raw_metrics(entry['derived_metrics'][str(number)])
                    source += 'def ' + calculation['expected'] + ' : Metrics := ' + _metrics(raw_metrics) + '\n'
                    source += 'theorem ' + calculation['theorem'] + ' : derivedMetrics ' + calculation['requests'] + ' ' + calculation['rows'] + ' = some ' + calculation['expected'] + ' := by decide +kernel\n'
                    source += '#print axioms ' + calculation['theorem'] + '\n'
                    names.append(calculation['theorem'])
                    calculations[key] = calculation
                calculation = calculations[key]
                calculation_bindings.append(calculation)
                theorem = 'exact_metrics_' + str(index) + '_' + str(number)
                source += 'theorem ' + theorem + ' : metricsMatch (derivedMetrics ' + bucket_name + '.requests ' + bucket_name + '.rows) ' + _metrics(bucket['metrics']) + ' = true := by\n'
                source += '  change metricsMatch (derivedMetrics ' + calculation['requests'] + ' ' + calculation['rows'] + ') ' + _metrics(bucket['metrics']) + ' = true\n'
                source += '  rewrite [' + calculation['theorem'] + ']\n  decide +kernel\n'
                source += '#print axioms ' + theorem + '\n'
                names.append(theorem)
        expected = ('none' if entry['model'] is None else
            'some ' + ('true' if entry['model']['evaluation']['evaluation_passed'] else 'false'))
        case_a, case_b = 'metricCase' + str(index) + 'Bucket1', 'metricCase' + str(index) + 'Bucket2'
        theorem = 'exact_derived_outcome_' + str(index)
        source += 'theorem ' + theorem + ' : derivedModelAccept ' + case_a + ' ' + case_b + ' = ' + expected + ' := by\n'
        if entry['model'] is not None:
            left, right = calculation_bindings
            source += '  exact Eq.trans (derivedModelAccept_of_metrics ' + case_a + ' ' + case_b + ' ' + left['expected'] + ' ' + right['expected'] + ' ' + left['theorem'] + ' ' + right['theorem'] + ') (by decide +kernel)\n'
        else:
            source += '  decide +kernel\n'
        source += '#print axioms ' + theorem + '\n'
        names.append(theorem)
        decoded = 'decodedDerivedOutcome' + str(index)
        raw_arguments = ' '.join(binding['raw_name'] for binding in bindings)
        source += 'def ' + decoded + ' : Option Bool := decodedDerivedModelAccept ' + case_a + ' ' + case_b + ' ' + raw_arguments + '\n'
        composed = 'exact_decoded_derived_outcome_' + str(index)
        decode_proofs = ' '.join(binding['theorem'] for binding in bindings)
        source += 'theorem ' + composed + ' : ' + decoded + ' = ' + expected + ' :=\n  Eq.trans (decodedDerivedModelAccept_of_decodes ' + case_a + ' ' + case_b + ' ' + raw_arguments + ' ' + decode_proofs + ') ' + theorem + '\n'
        source += '#print axioms ' + composed + '\n'
        names.append(composed)
        cases.append({'case_id': entry['case_id'], 'case_index': index,
            'decimal_model_result': None if entry['model'] is None else entry['model']['evaluation']['evaluation_passed'],
            'observed_outcome': entry['outcome'], 'theorem': theorem,
            'composed_theorem': composed, 'files': bindings,
            'calculation_theorems': [row['theorem'] for row in calculation_bindings],
            'metrics_derived_from_decoded_rows': True, 'binary64_equivalence_proved': False})
    # Compile bounded proof partitions. Definitions remain visible in each
    # independent kernel process; only the needed theorem dependencies repeat.
    # No compiled cache, admitted theorem, evaluator oracle or larger lease.
    commands = re.split(r'(?m)(?=^(?:def |theorem |#print axioms ))', source[len(prefix):])
    sources = []
    for shard in range(4):
        chosen = {'derivedModelAccept_of_metrics', 'decodedDerivedModelAccept_of_decodes',
            *(name for name, _ in probe_expressions)}
        chosen_definitions = set()
        for case in cases[shard * 9:(shard + 1) * 9]:
            chosen.update(file['theorem'] for file in case['files'])
            chosen_definitions.update(name for file in case['files']
                for name in (file['raw_name'], file['rows_name']))
            chosen.update(case['calculation_theorems'])
            for calculation in calculations.values():
                if calculation['theorem'] in case['calculation_theorems']:
                    chosen_definitions.update(calculation[field] for field in ('requests', 'rows', 'expected'))
            chosen.update((case['theorem'], case['composed_theorem']))
            chosen_definitions.update(('metricCase' + str(case['case_index']) + 'Bucket1',
                'metricCase' + str(case['case_index']) + 'Bucket2',
                'decodedDerivedOutcome' + str(case['case_index'])))
            if case['decimal_model_result'] is not None:
                chosen.update('exact_metrics_' + str(case['case_index']) + '_' + str(bucket)
                    for bucket in (1, 2))
        selected_names = [name for name in names if name in chosen]
        body = ''
        for command in commands:
            match = re.match(r'(def |theorem |#print axioms )(\w+)', command)
            if (match is None or (match.group(1) == 'def ' and match.group(2) in chosen_definitions)
                    or (match.group(1) != 'def ' and match.group(2) in chosen)):
                body += command
        sources.append({'label': METRICS_LABELS[shard],
            'source': prefix + body + 'end DecoderKernel\n', 'expected_success': True,
            'theorems': selected_names})
    controls = [
        ('false-cost', 'prefillCost 64 = 270337'),
        ('false-padding', '(batchFromRequests [] {seq:=64,heads:=32,hidden:=4096} [{id:=[114],prompt:=63,generated:=1}]).padding = 0'),
        ('false-p95', 'p95Units (List.range 20) = 19'),
        ('false-compilation', 'compileCost {seq:=64,heads:=32,hidden:=4096} = 0'),
        ('false-sequential', 'sumNats ([maxNats [100,200],maxNats [300,400]]) = 1000')]
    for label, proposition in controls:
        control = _kernel() + '\nnamespace DecoderKernel\ntheorem deliberate_false_control : ' + proposition + ' := by decide\nend DecoderKernel\n'
        sources.append({'label': label, 'source': control, 'expected_success': False, 'theorems': []})
    _need(tuple(row['label'] for row in sources) == METRICS_LABELS,
        'closed ordered positive and false metric compiler inventory required')
    _need(set(names) == {name for row in sources for name in row['theorems']},
        'all mathematical theorem names must occur in bounded compiler partitions')
    return _finish({'schema': SCHEMA, 'metric_case_report': json.loads(_wire(report)),
        'metric_case_report_sha256': _sha(_wire(report)),
        'decoder_kernel_template': _pin(ROOT / 'decoder_kernel.lean'),
        'metric_kernel_template': _pin(ROOT / 'metrics_kernel.lean'),
        'sources': sources, 'theorems': names, 'unique_files': unique, 'case_joins': cases,
        'metric_case_count': len(cases), 'decimal_interpretation': 'exact_retained_decimal_tokens',
        'source_binary64_equivalence_proved': False, 'general_source_equivalence_proved': False,
        'training_steps': 0, 'provider_calls': 0, **AUTHORITY})


def _lean_sources(theory):
    _need(type(theory) is dict and type(theory.get('metric_case_report')) is dict,
        'complete exact derived metric theory required')
    expected = build_metrics_theory(report=theory['metric_case_report'])
    _need(_wire(theory) == _wire(expected), 'metric theory differs from exact report replay')
    return [(row['label'], row['source'], row['expected_success']) for row in expected['sources']]


def producer_paths():
    return sorted(set(D.producer_paths() + [Path(__file__), ROOT / 'metrics_kernel.lean']))


def compile_metrics_theory(theory, *, output, lease):
    _lease_check(lease)
    _need(isinstance(output, Path) and output.is_absolute() and output.resolve() == output
        and output.is_relative_to(ROOT) and not output.exists() and output.parent.is_dir(),
        'fresh canonical owned metric Lean output required')
    sources = _lean_sources(theory)
    output.mkdir(mode=0o700)
    checks = [_run_lean(source=source, label=label, output=output, lease=lease,
        expected_success=expected) for label, source, expected in sources]
    evidence = _finish({'schema': LEAN_SCHEMA, 'theory_sha256': _sha(_wire(theory)),
        'profile': LEAN_PROFILE, 'lake_convenience_helper_used': False, 'checks': checks,
        'positive_compiles': sum(row['expected_success'] and row['status'] == 'passed' for row in checks),
        'false_controls_rejected': sum(not row['expected_success'] and row['status'] == 'rejected' for row in checks),
        'qualified': all(row['matches_expectation'] for row in checks),
        'syntax_typecheck_only': False, 'proved_theorems': list(theory['theorems']),
        'proof_scope': PROOF_SCOPE, 'training_steps': 0, 'provider_calls': 0, **AUTHORITY})
    _write(output / 'report.json', _wire(evidence))
    validate_metrics_evidence(evidence, theory=theory, output=output)
    return evidence


def validate_metrics_evidence(report, *, theory, output):
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
                and all(("DecoderKernel." + name) in check["stdout"] for name in
                    next(row['theorems'] for row in theory['sources'] if row['label'] == label)),
                "every theorem must have actual axiom inspection without admitted holes")
            _need(check["status"] == "passed" and check["returncode"] == 0, "native generated declarations did not typecheck")
        else:
            _need(check["status"] == "rejected" and check["returncode"] != 0
                and "tactic `decide` proved that the proposition" in check["stdout"].lower()
                and "is false" in check["stdout"].lower(), "genuine kernel-rejected false theorem control required")
    _need(type(report["positive_compiles"]) is int and report["positive_compiles"] == 4
        and type(report["false_controls_rejected"]) is int and report["false_controls_rejected"] == 5
        and report["qualified"] is True and report["syntax_typecheck_only"] is False
        and report["proved_theorems"] == theory["theorems"]
        and report["proof_scope"] == "concrete_exact_JSONL_decode_and_default_decimal_rational_metrics_not_binary64_or_Python_source_equivalence" and report["lake_convenience_helper_used"] is False
        and all(report.get(key) is False for key in AUTHORITY), "Lean compilation scope or qualification differs")
    _need(_read(output / "report.json", 8 * 1024**2) == _wire(report), "retained complete Lean report changed")
    return report


