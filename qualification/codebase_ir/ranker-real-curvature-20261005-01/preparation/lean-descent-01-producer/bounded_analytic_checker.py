"""Additive admitted Lean checker with explicit, externally pinned dependencies.

The caller owns admission, import guarding, and the 120-second outer attempt.
This module performs no work on import and acquires no independent lease.
It never changes an existing compiler helper or dependency directory.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

MAX_MANIFEST_BYTES = 64 * 1024**2
MAX_SOURCE_BYTES = 262144
MAX_OUTPUT_BYTES = 65536
MAX_FILES = 200000
ALLOWED_AXIOMS = frozenset(('propext', 'Classical.choice', 'Quot.sound'))
BOUNDS = {'timeout_seconds': 20, 'cpu_seconds': 20, 'max_input_bytes': MAX_SOURCE_BYTES,
          'max_output_bytes': MAX_OUTPUT_BYTES, 'max_workspace_bytes': 16 * 1024**2}
RETENTION_PROFILE = {
    'format': 'bounded_lean_chunks@1', 'native_per_file_capture_bytes': 65536,
    'native_max_declared_outputs': 64, 'chunk_bytes': 65536, 'max_chunk_files': 61,
    'max_raw_object_bytes': 61 * 65536, 'max_manifest_bytes': 65536,
    'max_object_files': 4, 'object_suffixes': ['.olean', '.olean.private', '.olean.server', '.ir'],
    'native_cpu_seconds': 20, 'native_wall_seconds': 20,
    'native_workspace_bytes': 16 * 1024**2, 'native_max_source_bytes': 262144,
    'compression': 'none', 'chunk_order': 'consecutive-global-index-and-object-concatenation',
}
RETENTION_PROFILE_SHA256 = hashlib.sha256(json.dumps(RETENTION_PROFILE, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
RETENTION_MANIFEST_NAME = 'LeanProofChunks.json'
RETENTION_CHUNK_NAMES = tuple('LeanProofChunk%03d.bin' % index for index in range(61))


def _require(condition, message):
    if condition is not True:
        raise ValueError(message)


def _hex(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def _signature(value):
    return tuple(getattr(value, 'st_' + key) for key in
                 ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns'))


def _read_pin(path, *, retain=False, maximum=None):
    path = Path(path)
    _require(path.is_absolute() and path.resolve(strict=True) == path, 'canonical absolute input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        _require(stat.S_ISREG(before.st_mode), 'regular input required')
        if maximum is not None:
            _require(before.st_size <= maximum, 'input byte bound')
        digest, size, blocks = hashlib.sha256(), 0, []
        while block := os.read(fd, 1024**2):
            digest.update(block)
            size += len(block)
            if retain:
                blocks.append(block)
        _require(size == before.st_size and _signature(before) == _signature(os.fstat(fd)) ==
                 _signature(path.lstat()), 'input changed during read')
        return {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest()}, b''.join(blocks)
    finally:
        os.close(fd)


def _binding(value):
    _require(type(value) is dict and set(value) == {'path', 'bytes', 'sha256'}, 'exact file binding required')
    _require(type(value['path']) is str and type(value['bytes']) is int and value['bytes'] >= 0
             and _hex(value['sha256']), 'malformed file binding')
    return value


def _lean_code(text):
    """Remove comments/strings for conservative forbidden-token checks."""
    out, index, depth, quoted = [], 0, 0, False
    while index < len(text):
        pair = text[index:index + 2]
        char = text[index]
        if depth:
            if pair == '/-':
                depth += 1
                index += 2
            elif pair == '-/':
                depth -= 1
                index += 2
            else:
                out.append('\n' if char == '\n' else ' ')
                index += 1
        elif quoted:
            if char == '\\':
                index += 2
            elif char == '"':
                quoted = False
                index += 1
            else:
                out.append('\n' if char == '\n' else ' ')
                index += 1
        elif pair == '/-':
            depth = 1
            out.append(' ')
            index += 2
        elif pair == '--':
            end = text.find('\n', index)
            index = len(text) if end < 0 else end
        elif char == "'" and index + 2 < len(text) and text[index + 2] == "'":
            out.append(' ')
            index += 3
        elif char == "'" and text[index + 1:index + 2] == '\\':
            end = index + 1
            while end < len(text):
                if text[end] == '\\':
                    end += 2
                elif text[end] == "'":
                    break
                else:
                    end += 1
            _require(end < len(text), 'unterminated character literal')
            out.append(' ')
            index = end + 1
        elif char == '"':
            quoted = True
            out.append(' ')
            index += 1
        else:
            out.append(char)
            index += 1
    _require(depth == 0 and not quoted, 'unterminated Lean comment/string')
    return ''.join(out)


def _lease(root_lease):
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLease
    _require(type(root_lease) is ResourceLease, 'actual frozen scheduler root lease required')
    _require(root_lease.owner_pid == os.getpid() and root_lease.parent_lease_id is None
             and root_lease.cpu_slots == 1 and root_lease.memory_mb == 2048
             and not root_lease.released and not root_lease.cancelled, 'active current-process1CPU2048MB root required')
    config = root_lease._scheduler.config
    _require(config.proof_safety_enabled is True and
             (config.proof_memory_stall_percent, config.proof_cpu_stall_percent,
              config.proof_io_stall_percent, config.proof_backoff_seconds) == (2.0, 50.0, 10.0, 2.0),
             'original proof pressure profile required')
    active = {row['lease_id']: row for row in root_lease._scheduler.active_leases()}
    _require(root_lease.lease_id in active, 'root lease absent from actual scheduler')
    actual = active[root_lease.lease_id]
    _require(actual['owner_pid'] == os.getpid() and actual['cpu_slots'] == 1
             and actual['memory_mb'] == 2048 and not actual.get('parent_lease_id'),
             'actual scheduler reservation differs from root lease')
    return root_lease.to_dict()


def _environment(path, expected):
    _require(_hex(expected), 'independent environment manifest SHA256 required')
    descriptor, raw = _read_pin(path, retain=True, maximum=MAX_MANIFEST_BYTES)
    _require(descriptor['sha256'] == expected, 'environment manifest pin mismatch')
    body = json.loads(raw)
    _require(type(body) is dict and body.get('schema') == 'ranker-real-curvature-lean-environment@1',
             'environment schema mismatch')
    executable = _binding(body['lean_executable'])
    files, paths = body['files'], body['lean_path']
    _require(type(files) is list and 0 < len(files) <= MAX_FILES, 'environment file population bound')
    _require(type(paths) is list and 0 < len(paths) <= 64 and len(set(paths)) == len(paths),
             'explicit library roots required')
    for library in paths:
        _require(type(library) is str and ':' not in library and Path(library).is_absolute()
                 and Path(library).resolve(strict=True) == Path(library) and Path(library).is_dir(),
                 'canonical library directory required')
    rows = {_binding(row)['path']: row for row in files}
    _require(len(rows) == len(files) and rows.get(executable['path']) == executable,
             'unique closure including executable required')
    for row in files:
        _require(_read_pin(row['path'])[0] == row, 'frozen environment input differs')
    modules = body.get('source_import_modules')
    _require(type(modules) is list and len(modules) > 0, 'frozen import module registry required')
    module_names = set()
    for module in modules:
        name = module['module']
        _require(type(name) is str and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_\'.]*', name)
                 is not None and name not in module_names, 'unique portable module registry required')
        module_names.add(name)
        source = _binding(module['source'])
        _require(rows.get(source['path']) == source, 'module source outside frozen closure')
        compiled = module['compiled']
        _require(type(compiled) is list and len(compiled) > 0, 'compiled module companions required')
        for compiled_pin in compiled:
            _binding(compiled_pin)
            _require(rows.get(compiled_pin['path']) == compiled_pin, 'compiled module outside frozen closure')
        relative = Path(*name.split('.')).with_suffix('.olean')
        candidates = [Path(library) / relative for library in paths if (Path(library) / relative).is_file()]
        _require(len(candidates) > 0 and any(compiled_pin['path'] == str(candidates[0]) for compiled_pin in compiled),
                 'module lookup shadowed or absent from frozen closure: ' + name)
    _require('Init' in module_names, 'implicit native Init module required')
    return descriptor, body


def _axioms(stdout, names):
    observations = []
    for name in names:
        label = re.escape("'" + name + "'")
        nonempty = re.findall(label + r' depends on axioms: \[([^\]]*)\]', stdout)
        empty = len(re.findall(label + r' does not depend on any axioms', stdout))
        _require(len(nonempty) + empty >= 1, 'missing theorem axiom report: ' + name)
        reports = [[item.strip() for item in row.split(',') if item.strip()] for row in nonempty] + [[]] * empty
        _require(all(row == reports[0] for row in reports), 'inconsistent repeated theorem axiom report: ' + name)
        used = reports[0]
        _require(len(used) == len(set(used)) and set(used) <= ALLOWED_AXIOMS,
                 'nonstandard theorem axiom dependency: ' + name)
        observations.append({'theorem': name, 'axioms': used, 'report_occurrences': len(reports)})
    return observations


def _manifest_body(raw):
    _require(type(raw) is bytes and len(raw) <= MAX_OUTPUT_BYTES, 'bounded retention manifest bytes required')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, 'duplicate retention manifest key')
            result[key] = value
        return result
    body = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
    _require(type(body) is dict and body.get('schema') == 'bounded_lean_chunks@1'
             and body.get('retention_profile_sha256') == RETENTION_PROFILE_SHA256,
             'exact retention format/profile required')
    _require(type(body.get('native_lean_invocations')) is int and body['native_lean_invocations'] == 1
             and type(body.get('native_lean_returncode')) is int,
             'exact native Lean call accounting required')
    canonical = (json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    _require(canonical == raw, 'canonical complete retention manifest required')
    return body


def _reconstruct_chunks(captured, filename):
    """Validate all captured bytes before returning complete raw object bodies.

    Returned bodies are separately bounded external dependency objects. Their
    size may exceed the unchanged64KiB native per-file capture bound.
    """
    _require(type(captured) is dict and RETENTION_MANIFEST_NAME in captured,
             'complete retention manifest absent')
    body = _manifest_body(captured[RETENTION_MANIFEST_NAME])
    _require(set(body) == {'schema', 'status', 'retention_profile_sha256', 'native_lean_invocations',
                          'native_lean_returncode', 'objects', 'chunks', 'aggregate_raw_object_bytes'}
             and body['status'] == 'complete' and body['native_lean_returncode'] == 0,
             'complete successful retention manifest required')
    _require(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*\.lean', filename) is not None,
             'portable Lean source filename required')
    objects, chunks, total = body['objects'], body['chunks'], body['aggregate_raw_object_bytes']
    _require(type(objects) is list and 1 <= len(objects) <= 4 and type(chunks) is list
             and 1 <= len(chunks) <= 61 and type(total) is int and 0 < total <= 61 * 65536,
             'fixed retained population/byte bounds')
    expected_names = list(RETENTION_CHUNK_NAMES[:len(chunks)])
    _require(set(captured) == {RETENTION_MANIFEST_NAME, *expected_names},
             'missing or extra captured chunk population')
    by_name = {}
    for index, row in enumerate(chunks):
        _require(type(row) is dict and set(row) == {'name', 'bytes', 'sha256'}
                 and row['name'] == expected_names[index] and type(row['bytes']) is int
                 and 0 < row['bytes'] <= MAX_OUTPUT_BYTES and _hex(row['sha256']),
                 'exact consecutive bounded chunk descriptor required')
        raw = captured[row['name']]
        _require(type(raw) is bytes and len(raw) == row['bytes']
                 and hashlib.sha256(raw).hexdigest() == row['sha256'], 'captured chunk content differs')
        by_name[row['name']] = raw
    stem = filename[:-5]
    allowed = [stem + suffix for suffix in RETENTION_PROFILE['object_suffixes']]
    names, used, reconstructed = [], [], []
    for row in objects:
        _require(type(row) is dict and set(row) == {'name', 'bytes', 'sha256', 'chunks'}
                 and type(row['name']) is str and row['name'] in allowed
                 and row['name'] not in names and type(row['bytes']) is int
                 and 0 < row['bytes'] <= 61 * 65536 and _hex(row['sha256'])
                 and type(row['chunks']) is list and len(row['chunks']) > 0,
                 'exact bounded compiler object descriptor required')
        _require(all(type(name) is str and name in by_name for name in row['chunks'])
                 and len(set(row['chunks'])) == len(row['chunks']), 'object chunk membership differs')
        _require(all(len(by_name[name]) == MAX_OUTPUT_BYTES for name in row['chunks'][:-1]),
                 'nonfinal object chunk must fill fixed native capture')
        raw = b''.join(by_name[name] for name in row['chunks'])
        _require(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'],
                 'complete compiler object content differs')
        names.append(row['name'])
        used.extend(row['chunks'])
        reconstructed.append((row, raw))
    _require(names[0] == allowed[0] and names == [name for name in allowed if name in names],
             'main object and fixed companion order required')
    _require(used == expected_names and sum(row['bytes'] for row in objects) == total
             and sum(row['bytes'] for row in chunks) == total,
             'exact object/chunk partition and aggregate bytes required')
    return body, reconstructed


def compile_analytic_lean(*, environment_manifest, expected_environment_manifest_sha256,
                          source_pin, retention_helper_pin, python_executable_pin,
                          output, root_lease, expected_success=True, theorem_names=()):
    """Run one native check under the caller's actual root lease.

    `theorem_names` is mandatory for a positive check. A negative source must
    contain a deliberate closed `False` control using `decide +kernel`.
    Source/closure hashing is outside the single20-second native subprocess;
    the root driver owns the entire120-second attempt and import-source guard.
    """
    _require(type(expected_success) is bool, 'exact expected-success Boolean required')
    _require(type(theorem_names) is tuple and len(set(theorem_names)) == len(theorem_names)
             and all(type(name) is str and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_\'.]*', name)
                     for name in theorem_names), 'exact theorem-name tuple required')
    _require(not expected_success or len(theorem_names) > 0, 'positive theorem axiom reports required')
    _binding(source_pin)
    _binding(retention_helper_pin)
    _binding(python_executable_pin)
    helper_descriptor, helper_raw = _read_pin(retention_helper_pin['path'], retain=True, maximum=MAX_SOURCE_BYTES)
    _require(helper_descriptor == retention_helper_pin and Path(helper_descriptor['path']).name == 'RetainLeanProof.py',
             'externally pinned retention helper differs')
    _require(_read_pin(python_executable_pin['path'])[0] == python_executable_pin,
             'externally pinned real Python executable differs')
    source_descriptor, raw = _read_pin(source_pin['path'], retain=True, maximum=MAX_SOURCE_BYTES)
    _require(source_descriptor == source_pin, 'externally bound source differs')
    source = raw.decode('utf-8')
    code = _lean_code(source)
    _require(re.search(r'\b(sorry|admit|axiom|unsafe)\b', code) is None,
             'unchecked declaration/proof token refused')
    if not expected_success:
        _require(re.search(r'\btheorem\s+\S+\s*:\s*False\s*:=\s*by\s+decide\s*\+kernel', code)
                 is not None, 'explicit closed False/decide+kernel negative control required')
    _require(all(not name.startswith('_root_.') for name in theorem_names),
             'registry names must omit the resolution-only _root_ prefix')
    # Always execute an actual fully qualified query. Source-authored prints
    # and same-basename declarations cannot suppress the kernel dependency
    # query; repeated honest output is allowed only when it agrees exactly.
    augmented = source + '\n' + '\n'.join('#print axioms _root_.' + name for name in theorem_names) + '\n'
    _require(len(augmented.encode()) + len(helper_raw) <= MAX_SOURCE_BYTES,
             'combined augmented source/helper native input bound')
    manifest_descriptor, manifest = _environment(environment_manifest, expected_environment_manifest_sha256)
    selected = manifest.get('selected_proof_sources')
    _require(type(selected) is list and source_descriptor in selected
             and source_descriptor in manifest['files'], 'actual proof source outside frozen per-job environment')
    _require(helper_descriptor in manifest['files'] and python_executable_pin in manifest['files'],
             'native helper/Python executable outside frozen per-job environment')
    direct_imports = []
    for line in code.splitlines():
        match = re.match(r'^\s*(?:(?:public|private|meta)\s+)*import\s+(.+?)\s*$', line)
        if match:
            names = match.group(1).split()
            if names and names[0] == 'all':
                names = names[1:]
            _require(len(names) > 0 and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_\'.]*', name)
                                          is not None for name in names), 'unsupported direct import declaration')
            direct_imports.extend(names)
    frozen_module_names = {module['module'] for module in manifest['source_import_modules']}
    _require(set(direct_imports) <= frozen_module_names,
             'proof source imports outside frozen transitive module closure')
    lease_before = _lease(root_lease)
    output = Path(output)
    _require(output.is_absolute() and output.resolve() == output and output.is_dir(), 'canonical owned output required')
    filename = Path(source_pin['path']).name
    _require(filename.endswith('.lean') and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*\.lean', filename)
             is not None, 'portable Lean source filename required')
    source_output = output / filename
    _require(not source_output.exists(), 'fresh source output required')
    with source_output.open('xb') as stream:
        stream.write(augmented.encode())
    object_file = str(Path(filename).with_suffix('.olean'))
    stem = str(Path(filename).with_suffix(''))
    declared_outputs = (RETENTION_MANIFEST_NAME, *RETENTION_CHUNK_NAMES)
    executable = manifest['lean_executable']['path']
    argv = (python_executable_pin['path'], '-I', '-B', '-S', 'RetainLeanProof.py', executable, filename,
            'positive' if expected_success else 'negative')
    from ipfs_datasets_py.logic.backends.process import BoundedToolRunner, ToolRunLimits, ToolRunRequest
    run = BoundedToolRunner().run(ToolRunRequest(argv=argv,
        input_files={filename: augmented, 'RetainLeanProof.py': helper_raw.decode('utf-8')}, output_paths=declared_outputs,
        environment={'LEAN_PATH': ':'.join(manifest['lean_path']), 'LEAN_NUM_THREADS': '1'},
        limits=ToolRunLimits(**BOUNDS)))
    compiled, captured, artifact_anomalies = [], [], []
    for name, data in run.output_files.items():
        if name not in declared_outputs:
            artifact_anomalies.append({'kind': 'unexpected_output_name', 'name': name, 'bytes': len(data)})
            continue
        oversized = len(data) > MAX_OUTPUT_BYTES
        if oversized:
            artifact_anomalies.append({'kind': 'oversize_output', 'name': name, 'bytes': len(data)})
        retained = data[:MAX_OUTPUT_BYTES]
        with (output / name).open('xb') as stream:
            stream.write(retained)
        captured.append({**_read_pin(output / name)[0],
                         'complete': not oversized and not run.output_truncated})
    retention_body, reconstruction_error, reconstruction = None, None, None
    try:
        retention_body = _manifest_body(run.output_files[RETENTION_MANIFEST_NAME])
        if expected_success:
            _require(not run.output_truncated and not artifact_anomalies,
                     'native retained captures incomplete')
            retention_body, bodies = _reconstruct_chunks(dict(run.output_files), filename)
            for row, raw_body in bodies:
                with (output / row['name']).open('xb') as stream:
                    stream.write(raw_body)
                compiled.append({**_read_pin(output / row['name'])[0], 'complete': True,
                                 'retention_format': 'bounded_lean_chunks@1'})
            reconstruction = {'status': 'passed', 'manifest_complete': True, 'exact_chunk_population': True,
                'aggregate_raw_object_bytes': retention_body['aggregate_raw_object_bytes'],
                'reconstructed_object_count': len(compiled), 'chunk_count': len(retention_body['chunks']),
                'reconstructed_full_module_bodies_may_exceed_native_per_file_capture': True}
        else:
            _require(set(retention_body) == {'schema', 'status', 'retention_profile_sha256',
                         'native_lean_invocations', 'native_lean_returncode'}
                     and retention_body['status'] == 'native_nonzero'
                     and retention_body['native_lean_returncode'] == run.returncode
                     and set(run.output_files) == {RETENTION_MANIFEST_NAME},
                     'exact native negative invocation receipt required')
    except (ValueError, OSError, KeyError, UnicodeError) as error:
        reconstruction_error = type(error).__name__ + ': ' + str(error)
    safe = not any((run.timed_out, run.cancelled, run.unavailable, run.resource_exhausted,
                    run.output_truncated, run.workspace_limit_exceeded, artifact_anomalies)) and run.workspace_cleaned
    axioms, axiom_error = [], None
    try:
        axioms = _axioms(run.stdout, theorem_names)
    except ValueError as error:
        axiom_error = str(error)
    logical_false = (safe and run.returncode is not None and run.returncode != 0
        and run.stdout.count('error:') == 1 and not run.stderr
        and 'Tactic `decide` proved that the proposition' in run.stdout
        and re.search(r'proposition\s+False\s+is false', run.stdout) is not None)
    has_main_object = any(Path(row['path']).name == object_file for row in compiled)
    passed = safe and run.ok and has_main_object and reconstruction_error is None and axiom_error is None
    rejected = logical_false and reconstruction_error is None and axiom_error is None
    post_error = None
    try:
        _require(_environment(environment_manifest, expected_environment_manifest_sha256)[0] == manifest_descriptor,
                 'environment manifest changed after native call')
        _require(_read_pin(source_pin['path'])[0] == source_pin, 'source changed after native call')
        _require(_read_pin(retention_helper_pin['path'])[0] == helper_descriptor
                 and _read_pin(python_executable_pin['path'])[0] == python_executable_pin,
                 'native helper/Python executable changed after native call')
        _lease(root_lease)
    except (ValueError, OSError) as error:
        post_error = type(error).__name__ + ': ' + str(error)
        passed = rejected = False
    result = {'schema': 'ranker-real-curvature-bounded-analytic-lean-check@2',
        'status': 'passed' if passed else 'rejected' if rejected else 'inconclusive',
        'expected_success': expected_success, 'matches_expectation': passed if expected_success else rejected,
        'source': source_descriptor, 'augmented_source': _read_pin(source_output)[0],
        'environment_manifest': manifest_descriptor, 'environment_file_count': len(manifest['files']),
        'proof_source_in_frozen_per_job_environment': True,
        'source_direct_imports': direct_imports, 'direct_imports_and_implicit_Init_in_frozen_registry': True,
        'lean_path': manifest['lean_path'], 'native_bounds': dict(BOUNDS), 'command': list(run.command),
        'native_invocations': 1, 'returncode': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr,
        'native_lean_invocations': retention_body['native_lean_invocations'] if retention_body else None,
        'native_lean_returncode': retention_body['native_lean_returncode'] if retention_body else None,
        'retention_format': 'bounded_lean_chunks@1', 'retention_profile': dict(RETENTION_PROFILE),
        'retention_profile_sha256': RETENTION_PROFILE_SHA256,
        'retention_helper': helper_descriptor, 'python_executable': python_executable_pin,
        'retention_manifest': next((row for row in captured if Path(row['path']).name == RETENTION_MANIFEST_NAME), None),
        'retention_manifest_body': retention_body,
        'retained_chunk_artifacts': [row for row in captured if Path(row['path']).name in RETENTION_CHUNK_NAMES],
        'reconstruction_validation': reconstruction, 'reconstruction_validation_error': reconstruction_error,
        'theorem_axiom_output': axioms, 'allowed_standard_axioms': sorted(ALLOWED_AXIOMS),
        'axiom_report_error': axiom_error, 'post_call_binding_error': post_error,
        'compiled_artifacts': compiled, 'artifact_anomalies': artifact_anomalies,
        'timed_out': run.timed_out, 'cancelled': run.cancelled,
        'unavailable': run.unavailable, 'resource_exhausted': run.resource_exhausted,
        'output_truncated': run.output_truncated, 'workspace_limit_exceeded': run.workspace_limit_exceeded,
        'workspace_cleaned': run.workspace_cleaned, 'native_elapsed_seconds': run.elapsed_seconds,
        'actual_root_lease': lease_before, 'root_lease_owned_by_caller': True,
        'outer120s_and_frozen_project_import_guard_owned_by_caller': True,
        'environment_actual_runtime_open_trace_claimed': False,
        'proof_scope': 'kernel-checked declared mathematical statements under exact frozen dependency files',
        'python_ranker_source_equivalence_proved': False, 'binary64_error_bound_proved': False,
        'historical_execution_origin_proved': False, 'optimizer_convergence_proved': False,
        'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN',
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
        'planner_activation': False, 'official_benchmark_score': None}
    payload = (json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if len(payload) > MAX_OUTPUT_BYTES:
        # Preserve exact native output separately and retain an honest bounded
        # inconclusive receipt rather than lose the invocation accounting.
        transcripts = {}
        for key in ('stdout', 'stderr'):
            transcript = output / (Path(filename).stem + '.' + key + '.txt')
            raw_transcript = result[key].encode()
            with transcript.open('xb') as stream:
                stream.write(raw_transcript[:MAX_OUTPUT_BYTES])
            transcripts[key] = {**_read_pin(transcript)[0], 'complete': len(raw_transcript) <= MAX_OUTPUT_BYTES}
            result[key] = None
        result.update(status='inconclusive', matches_expectation=False,
                      receipt_retention_overflow=True, exact_native_transcripts=transcripts)
        payload = (json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
        _require(len(payload) <= MAX_OUTPUT_BYTES, 'bounded diagnostic receipt exceeds64KiB')
    with (output / (Path(filename).stem + '.check.json')).open('xb') as stream:
        stream.write(payload)
    return result
