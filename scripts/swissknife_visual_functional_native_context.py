"""Supply a declared, compact backend contract to inline-only app repairs."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import stat
import ast
import os
import re
import time
import uuid
import sys
import math

CONTRACTS = {
    'p2p-chat-unified': ('pubsub', 'swissknife/docs/svf-pubsub-app-contract.json'),
    'p2p-chat': ('pubsub', 'swissknife/docs/svf-pubsub-app-contract.json'),
    'agent-supervisor': ('supervisor', 'swissknife/docs/svf-supervisor-app-contract.json'),
}


def load_native_app_context(root: Path, task: dict) -> dict | None:
    selected = CONTRACTS.get(task.get('app_id'))
    if selected is None or selected[1] not in task.get('execution_inputs', []):
        return None
    capability, relative = selected
    root = Path(root).resolve()
    path = root / relative
    if path.resolve() != path or path.is_symlink():
        raise ValueError('native app contract escaped its declared physical checkout')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 8192:
        raise ValueError('native app contract exceeds its exact source bound')
    data = path.read_bytes()
    if len(data) != info.st_size:
        raise ValueError('native app contract changed during its read')
    def pairs(rows):
        out = {}
        for key, value in rows:
            if key in out:
                raise ValueError('duplicate native app contract key')
            out[key] = value
        return out
    value = json.loads(data, object_pairs_hook=pairs)
    if (type(value) is not dict or set(value) != {'schema', 'capability', 'app_ids', 'tools',
            'request_contract', 'response_contract', 'scope'}
            or value['schema'] != 'swissknife.native-foundation-app-context.v1'
            or value['capability'] != capability or type(value['app_ids']) is not list
            or value['app_ids'] != [k for k, v in CONTRACTS.items() if v == selected]
            or task['app_id'] not in value['app_ids']):
        raise ValueError('native app contract belongs to another declared capability')
    return {'contract': value, 'original': {'path': relative,
        'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)},
        'authority': 'Readonly backend API context only; original edit scope, consent, workflow, receipt, and visual gates remain mandatory'}


# The two new backend foundations already declare this readonly closure in
# execution_inputs. Inline-only proposals must actually receive its interface,
# not merely the paths/hashes in the task database.
FOUNDATION_DOC = 'swissknife/docs/svf-native-foundation-contracts.md'
OWNERSHIP = 'scripts/svf_backends/foundation_service_ownership.py'
OBSERVER = 'scripts/svf_backends/foundation_native_entrypoint.py'
PINNED_IPFS = 'external/ipfs_kit/ipfs_kit_py/assurance/pinned_ipfs.py'
INTENT = 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/intent_repository.py'
DATABASE = 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/database_task_source.py'
RUNNER = 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/verification/process_runner.py'
FOUNDATIONS = {
    'SVF-043': {
        'family': 'kit-pubsub',
        'full': ('scripts/svf_backends/validate_pubsub_foundation.py',
                 'tests/test_svf_pubsub_foundation_contract.py',
                 'config/swissknife_visual_functional_pubsub.json'),
        'api': {PINNED_IPFS: {'LivePinnedIpfsAdapter': ('__init__', 'validate_configuration', 'content_cid', 'health', 'node_id', 'swarm_peers', 'add', 'cat', 'pin', 'unpin', 'close')}},
    },
    'SVF-044': {
        'family': 'accelerate-supervisor',
        'full': ('scripts/svf_backends/validate_supervisor_foundation.py',
                 'tests/test_svf_supervisor_foundation_contract.py',
                 'scripts/svf_backends/fixed_supervisor_worker.py',
                 'scripts/svf_backends/fixed_supervisor_output_validator.py'),
        'api': {
            INTENT: {'IntentRepository': ('__init__', 'upsert_objective', 'upsert_goal', 'link_goal_edge', 'upsert_plan', 'upsert_task', 'get_task', 'select_ready_tasks', 'record_validation_result', 'cas_task_status', 'required_evidence_satisfied')},
            DATABASE: {'DatabaseTaskSource': ('__init__', 'ready_tasks', 'get_task', 'compare_and_set_status')},
            RUNNER: {'VerificationProcessRunner': ('__init__', 'run'), 'VerificationCancellation': ('cancel',)},
        },
    },
}


def _foundation_source(root: Path, name: str) -> tuple[str, dict]:
    path = root / name
    if path.resolve() != path or path.is_symlink():
        raise ValueError('foundation context escaped its declared physical checkout')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 1048576:
            raise ValueError('foundation context source exceeds its exact bound')
        raw = stream.read(1048577)
        after = os.fstat(stream.fileno())
    current = path.lstat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if len(raw) != before.st_size or identity(before) != identity(after) or identity(before) != identity(current):
        raise ValueError('foundation context source changed during its read')
    return raw.decode('utf8'), {'path': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def _fragment(lines: list[str], first: int, last: int) -> dict:
    return {'start_line': first, 'end_line': last, 'text': ''.join(lines[first - 1:last])}


def _api_headers(text: str, classes: dict[str, tuple[str, ...]]) -> list[dict]:
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    found = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in classes:
            methods = {item.name: item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))}
            if set(classes[node.name]) - set(methods):
                raise ValueError('declared foundation public SDK interface is missing')
            parts = [_fragment(lines, node.lineno, node.lineno)]
            for name in classes[node.name]:
                method = methods[name]
                first = min([method.lineno, *[item.lineno for item in method.decorator_list]])
                last = max(method.lineno, method.body[0].lineno - 1)
                parts.append(_fragment(lines, first, last))
            found[node.name] = parts
    if set(found) != set(classes):
        raise ValueError('declared foundation public SDK class is missing')
    return [{'class': name, 'fragments': found[name]} for name in classes]


def _helper_interfaces(ownership: str, observer: str) -> list[dict]:
    result = []
    for relative, text, names in ((OWNERSHIP, ownership, ('ensure_owned_services', 'inspect_registered_pubsub_peers')),
                                  (OBSERVER, observer, ('read_snapshot',))):
        lines = text.splitlines(keepends=True)
        nodes = {node.name: node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}
        fragments = []
        for name in names:
            if name not in nodes:
                raise ValueError('protected foundation helper interface is missing')
            node = nodes[name]
            fragments.append(_fragment(lines, node.lineno, max(node.lineno, node.body[0].lineno - 1)))
            # Return keys are useful API, without inlining protected control
            # internals or asking a candidate to implement instrumentation.
            returns = [item for item in ast.walk(node) if isinstance(item, ast.Return) and isinstance(item.value, ast.Dict)]
            if returns:
                item = max(returns, key=lambda value: value.lineno)
                fragments.append(_fragment(lines, item.lineno, item.end_lineno))
            if name == 'inspect_registered_pubsub_peers':
                calls = [item for item in ast.walk(node) if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute)
                         and item.func.attr == 'append' and item.args and isinstance(item.args[0], ast.Dict)]
                if calls:
                    item = max(calls, key=lambda value: value.lineno)
                    fragments.append(_fragment(lines, item.lineno, item.end_lineno))
        result.append({'path': relative, 'fragments': fragments})
    if len(json.dumps(result, ensure_ascii=False).encode()) > 4096:
        raise ValueError('foundation helper API projection exceeds its fixed bound')
    return result


def load_native_foundation_context(root: Path, task: dict) -> dict | None:
    selected = FOUNDATIONS.get(task.get('task_id'))
    if selected is None or task.get('kind') != 'backend-repair' or task.get('app_id'):
        return None
    root = Path(root).resolve()
    required = {FOUNDATION_DOC, OWNERSHIP, OBSERVER, *selected['full'], *selected['api']}
    if not required <= set(task.get('execution_inputs', [])):
        raise ValueError('foundation readonly context is not declared by the task')
    if required & set(task.get('edit_paths', [])):
        raise ValueError('foundation protected context cannot be an edit target')
    texts = {}; sources = []
    for name in sorted(required):
        text, identity = _foundation_source(root, name)
        texts[name] = text; sources.append(identity)
    document = texts[FOUNDATION_DOC]
    first = document.find('# Protected SVF-043 pubsub contract\n')
    second = document.find('# Protected R13 supervisor fixture contract (draft, not admitted)\n')
    if not 0 <= first < second:
        raise ValueError('foundation engineering contract sections are missing')
    # Keep the actual source lines for this capability, and fence the entire
    # original document. The other foundation cannot displace required bytes.
    start, stop = (first, document.rfind('Source snapshot:', first, second)) if task['task_id'] == 'SVF-043' else (second, len(document))
    if task['task_id'] == 'SVF-043' and not first < stop < second:
        raise ValueError('foundation capability contract boundary is missing')
    doc_lines = document.splitlines(keepends=True)
    first_line = document.count('\n', 0, start) + 1
    last_line = document.count('\n', 0, stop) + (0 if document[:stop].endswith('\n') else 1)
    engineering = {'path': FOUNDATION_DOC, 'fragments': [_fragment(doc_lines, first_line, last_line)]}
    api = [{'path': name, 'classes': _api_headers(texts[name], classes)} for name, classes in selected['api'].items()]
    if len(json.dumps(api, ensure_ascii=False).encode()) > 16384:
        raise ValueError('foundation public SDK API projection exceeds its fixed bound')
    existing_edits = [name for name in task.get('edit_paths', []) if (root / name).is_file() and not (root / name).is_symlink()]
    missing_edits = [name for name in task.get('edit_paths', []) if not (root / name).exists()]
    context = {
        'schema': 'swissknife.native-foundation-authoring-context.v1',
        'family': selected['family'], 'sources': sources,
        'engineering_contract': engineering, 'sdk_public_api': api,
        'api_projection_scope': 'Exact class/method signature excerpts only; bodies are omitted. Use the complete protected gate/test and capability contract for behavior, and never guess omitted private helpers.',
        'protected_helper_api': _helper_interfaces(texts[OWNERSHIP], texts[OBSERVER]),
        'instrumentation_policy': 'Native startup instrumentation and owned-service controls are supplied by protected code. Implement only declared editable SDK/backend/facade files; never implement or forge capture events, receipts, gate results or service owners. Public readonly SDK signatures are exact source excerpts; do not guess or call omitted private storage helpers.',
        'proposal_evidence_policy': {'allowed_existing_source_paths': sorted(required | set(existing_edits)),
            'missing_edit_targets_are_not_evidence': missing_edits,
            'instruction': 'Every findings.evidence_paths entry must identify a CURRENT existing physical file. A newly proposed missing target is not evidence until applied: mention it in description only and cite an existing supplied contract/test/source path. Preserve the strict response evidence existence check.'},
        'authority': 'Readonly implementation context only; original checks and live qualification decide acceptance. No edit, service control, completion, or budget authority.'}
    return {'context': context, 'sources': sources, 'full_inputs': list(selected['full']), 'replace_inputs': [FOUNDATION_DOC]}


BACKEND_REPORT_SCHEMA = 'swissknife.backend-original-checks.v1'
BACKEND_REFERENCE_SCHEMA = 'swissknife.backend-checks-reference.v1'
BACKEND_RUNTIME = 'data/agent_supervisor/swissknife_visual_functional'
BACKEND_GLOBAL_METADATA = {
    'config/swissknife_visual_functional_tasks.json',
    'implementation_plan/docs/53-swissknife-visual-functional-mcplusplus.todo.md',
    'implementation_plan/docs/53-swissknife-visual-functional-mcplusplus.objectives.md',
}
BACKEND_CONTROLLER_INPUTS = (
    'scripts/swissknife_visual_functional_worker.py',
    'scripts/swissknife_visual_functional_native_context.py',
    'scripts/swissknife_visual_functional_llm.py',
    'scripts/swissknife_visual_functional_blocked.py',
    'scripts/swissknife_visual_functional_recovery.py',
    'scripts/swissknife_visual_functional_phase_budget.py',
    'config/swissknife_visual_functional_supervisor.json',
)


def _backend_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def backend_task_semantics_sha256(task: dict) -> str:
    if type(task) is not dict or task.get('kind') != 'backend-repair' or re.fullmatch(r'SVF-[A-Z0-9-]{1,64}', str(task.get('task_id', ''))) is None:
        raise ValueError('backend checks require an actual backend-repair task')
    fields = ('task_id', 'kind', 'app_id', 'acceptance', 'checks', 'edit_paths', 'dependencies',
              'llm_limits', 'conflict_policy', 'context_paths', 'execution_inputs',
              'semantic_recovery_inputs', 'timeout_seconds')
    return hashlib.sha256(_backend_json({name: task[name] for name in fields if name in task})).hexdigest()


def _backend_path(root: Path, relative: str) -> Path:
    if type(relative) is not str or not relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('backend source/report path must be repository relative')
    path = root / relative
    if path.resolve() != path or path.is_symlink():
        raise ValueError('backend source/report escaped its physical checkout')
    return path


def _backend_bytes(path: Path, maximum: int, *, private: bool = False) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= maximum
                or private and (before.st_uid != os.getuid() or before.st_mode & 0o077)):
            raise ValueError('backend source/report is not a bounded safe regular file')
        raw = stream.read(maximum + 1); after = os.fstat(stream.fileno())
    same = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if len(raw) != before.st_size or same(before) != same(after) or same(before) != same(path.lstat()):
        raise ValueError('backend source/report changed while being read')
    return raw


def backend_source_hashes(root: Path, task: dict) -> dict:
    """Fence declared/static controller inputs; lane status and attempts are not sources."""
    backend_task_semantics_sha256(task)
    root = Path(root).resolve(); names = list(BACKEND_CONTROLLER_INPUTS)
    for field in ('execution_inputs', 'context_paths', 'edit_paths', 'semantic_recovery_inputs'):
        values = task.get(field, [])
        if type(values) is not list or len(values) > 256:
            raise ValueError('invalid backend static source policy')
        names += values
    checks = task.get('checks')
    if type(checks) is not list or not checks or len(checks) > 64:
        raise ValueError('backend repair requires bounded original executable checks')
    for command in checks:
        if type(command) is not list or not command or len(command) > 128 or any(type(item) is not str for item in command):
            raise ValueError('invalid original backend check argv')
        names += [item for item in command[1:] if item.startswith(('scripts/', 'tests/', 'swissknife/', 'external/', 'config/'))
                  and Path(item).suffix in {'.py', '.js', '.mjs', '.cjs', '.json'}]
    result = {}
    for name in dict.fromkeys(names):
        path = _backend_path(root, name)
        if name in BACKEND_GLOBAL_METADATA or name.startswith(BACKEND_RUNTIME + '/') and not name.startswith(BACKEND_RUNTIME + '/backends/fixtures/'):
            continue
        try: raw = _backend_bytes(path, 4 * 1024 * 1024)
        except FileNotFoundError: result[name] = None
        else: result[name] = hashlib.sha256(raw).hexdigest()
    return result


def backend_output_tail(stdout: str, stderr: str, limit: int = 16000) -> str:
    return (stdout + '\n' + stderr).encode()[-limit:].decode(errors='ignore')


def _backend_check_records(task: dict, report: dict) -> None:
    checks = report.get('checks'); original = task['checks']
    if (type(checks) is not list or not checks or len(checks) > len(original)
            or report.get('original_checks') != original or report.get('outcome') not in {'passed', 'failed'}):
        raise ValueError('backend report omitted or changed original checks')
    for index, value in enumerate(checks):
        if (type(value) is not dict or set(value) != {'index', 'declared_argv', 'executed_argv', 'exit_code', 'output_tail'}
                or type(value['index']) is not int or value['index'] != index or value['declared_argv'] != original[index]
                or type(value['executed_argv']) is not list or not value['executed_argv']
                or any(type(item) is not str for item in value['executed_argv'])
                or type(value['exit_code']) is not int or type(value['output_tail']) is not str
                or len(value['output_tail'].encode()) > 16000):
            raise ValueError('invalid actual backend check observation')
        executed = list(value['executed_argv']); declared = list(original[index])
        if Path(declared[0]).name in {'python', 'python3'}:
            if Path(executed[0]).resolve() != Path(sys.executable).resolve():
                raise ValueError('backend check did not use its actual worker Python')
            executed[0] = declared[0] = 'python3'
        if executed != declared or index < len(checks) - 1 and value['exit_code'] != 0:
            raise ValueError('backend report execution differs from its original command')
    diagnostic = report.get('diagnostic')
    if report['outcome'] == 'passed':
        if len(checks) != len(original) or any(row['exit_code'] != 0 for row in checks) or diagnostic is not None:
            raise ValueError('backend passing report is incomplete or claims an actual failure')
    elif (checks[-1]['exit_code'] == 0 or type(diagnostic) is not dict
          or set(diagnostic) != {'stage', 'code', 'check_index', 'argv', 'exit_code', 'stdout_tail', 'stderr_tail'}
          or diagnostic.get('stage') != 'command' or diagnostic.get('code') != 'ValidationCommandError'
          or type(diagnostic.get('check_index')) is not int or diagnostic.get('check_index') != len(checks) - 1 or diagnostic.get('argv') != checks[-1]['executed_argv']
          or diagnostic.get('exit_code') != checks[-1]['exit_code']
          or any(type(diagnostic.get(key)) is not str or len(diagnostic[key].encode()) > 16000 for key in ('stdout_tail', 'stderr_tail'))
          or checks[-1]['output_tail'] != backend_output_tail(diagnostic['stdout_tail'], diagnostic['stderr_tail'])):
        raise ValueError('backend failure is not an actual source-bound command diagnostic')


def write_backend_check_report(root: Path, task: dict, *, source_sha256: dict, checks: list, diagnostic) -> dict:
    """Persist one actual worker-owned observation; this never grants acceptance."""
    root = Path(root).resolve(); semantic = backend_task_semantics_sha256(task)
    if source_sha256 != backend_source_hashes(root, task):
        raise ValueError('backend sources changed before producer report persistence')
    report = {'schema': BACKEND_REPORT_SCHEMA, 'task_id': task['task_id'], 'task_semantics_sha256': semantic,
              'source_sha256': source_sha256, 'original_checks': task['checks'], 'checks': checks,
              'outcome': 'passed' if diagnostic is None else 'failed', 'diagnostic': diagnostic,
              'observed_at': time.time(), 'producer_pid': os.getpid(),
              'producer_birth': Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19],
              'work_complete': False, 'completion_authority': False}
    _backend_check_records(task, report)
    raw = _backend_json(report) + b'\n'
    if len(raw) > 131072:
        raise ValueError('backend producer report exceeds its bound')
    relative = BACKEND_RUNTIME + '/tasks/' + task['task_id'] + '/backend-checks/attempt-' + str(uuid.uuid4()) + '/report.json'
    path = _backend_path(root, relative); path.parent.mkdir(parents=True, mode=0o700, exist_ok=False)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_DIRECTORY)
    try: os.fsync(directory)
    finally: os.close(directory)
    return {'schema': BACKEND_REFERENCE_SCHEMA, 'path': relative, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def load_backend_check_report(root: Path, task: dict, reference: dict) -> dict:
    root = Path(root).resolve(); semantic = backend_task_semantics_sha256(task)
    if (type(reference) is not dict or set(reference) != {'schema', 'path', 'sha256', 'bytes'}
            or reference['schema'] != BACKEND_REFERENCE_SCHEMA or type(reference['bytes']) is not int
            or not 0 < reference['bytes'] <= 131072 or type(reference['sha256']) is not str
            or re.fullmatch('[0-9a-f]{64}', reference['sha256']) is None):
        raise ValueError('invalid backend producer report reference')
    prefix = BACKEND_RUNTIME + '/tasks/' + task['task_id'] + '/backend-checks/'
    relative = reference.get('path')
    if type(relative) is not str or not relative.startswith(prefix):
        raise ValueError('backend producer report escaped its task namespace')
    suffix = Path(relative).relative_to(prefix)
    if (len(suffix.parts) != 2 or suffix.name != 'report.json' or not suffix.parts[0].startswith('attempt-')
            or str(uuid.UUID(suffix.parts[0][8:])) != suffix.parts[0][8:]):
        raise ValueError('backend producer report has no canonical owned attempt')
    path = _backend_path(root, relative); raw = _backend_bytes(path, 131072, private=True)
    if len(raw) != reference['bytes'] or hashlib.sha256(raw).hexdigest() != reference['sha256']:
        raise ValueError('backend producer report changed from its admitted bytes')
    def pairs(rows):
        value = {}
        for key, item in rows:
            if key in value: raise ValueError('duplicate backend producer report key')
            value[key] = item
        return value
    report = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite backend report value')))
    fields = {'schema', 'task_id', 'task_semantics_sha256', 'source_sha256', 'original_checks', 'checks',
              'outcome', 'diagnostic', 'observed_at', 'producer_pid', 'producer_birth', 'work_complete', 'completion_authority'}
    if (type(report) is not dict or set(report) != fields or report.get('schema') != BACKEND_REPORT_SCHEMA
            or report.get('task_id') != task['task_id'] or report.get('task_semantics_sha256') != semantic
            or report.get('source_sha256') != backend_source_hashes(root, task)
            or report.get('work_complete') is not False or report.get('completion_authority') is not False
            or type(report.get('observed_at')) not in {int, float} or not math.isfinite(report['observed_at']) or report['observed_at'] <= 0
            or type(report.get('producer_pid')) is not int or report['producer_pid'] <= 0
            or type(report.get('producer_birth')) is not str or not report['producer_birth'].isdigit()):
        raise ValueError('backend producer report is stale or outside its task/source policy')
    _backend_check_records(task, report)
    return {'report': report, 'original': {key: reference[key] for key in ('path', 'sha256', 'bytes')}}


def backend_check_model_context(loaded: dict) -> dict:
    """Project actual observations once, retaining the complete immutable report."""
    report = loaded['report']; projection = {'schema': BACKEND_REPORT_SCHEMA, 'task_id': report['task_id'],
        'original': loaded['original'], 'outcome': report['outcome'], 'original_checks': report['original_checks'],
        'source_identity': {'sha256': hashlib.sha256(_backend_json(report['source_sha256'])).hexdigest(),
                            'source_count': len(report['source_sha256'])}, 'checks': [], 'diagnostic': report['diagnostic'],
        'projection_only': True, 'work_complete': False, 'completion_authority': False,
        'instruction': 'These original checks actually ran in this worker under its lease. Passing prechecks are context only: still return a fresh genuine repair-mode pass with no edits if no fix is needed; original checks rerun after the model and the independent validator still decides completion. A failed command is diagnostic context, not a fabricated workflow failure.'}
    for row in report['checks']:
        selected = {key: row[key] for key in ('index', 'declared_argv', 'executed_argv', 'exit_code')}
        if report['outcome'] == 'passed': selected['output_tail'] = row['output_tail'][-2048:]
        projection['checks'].append(selected)
    if projection['diagnostic'] is not None:
        projection['diagnostic'] = dict(projection['diagnostic'])
        for name in ('stdout_tail', 'stderr_tail'):
            raw = projection['diagnostic'][name].encode()[-6144:]
            projection['diagnostic'][name] = raw.decode(errors='ignore')
    if len(_backend_json(projection)) > 16384:
        raise ValueError('backend producer model context exceeds its bound')
    return projection
