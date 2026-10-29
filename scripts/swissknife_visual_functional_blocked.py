"""Source-bound negative proposal cache; never grants execution or acceptance.

API: build_scope(root, task=..., route=profile['llm'], edit_hashes=...,
readonly_hashes=..., failure=load_execution_failure(...)) returns an immutable
JSON-compatible identity. Call raise_if_blocked(root, cache_dir, scope) immediately
before a paid repair. After validating a blocked/no-edits model result, call
remember_blocked(root, cache_dir, scope, receipt_path). Cache misses return None; malformed existing entries fail closed;
CachedBlockedRepair is a real failed proposal, NOT a resource refusal/exit75.

Readonly dependency hashes independently fence the worker's projected source
context; when present in the model receipt they must agree. Editable target
hashes must always occur in the receipt.
Use stable original source/dependency paths in readonly_hashes, never generated
model-input contexts, progress or receipt files. Failure UUIDs/clocks/correlations
are normalized separately. No TTL can authorize another identical paid request.
The original producer may independently retry under its existing finite policy.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

SCHEMA = 'swissknife.blocked-repair-cache.v1'
FAILURE_SCHEMA = 'swissknife.visual-functional-execution-failure.v1'
MAX_ENTRIES = 64
MAX_RECEIPT_BYTES = 3 * 1024 * 1024
HEX = re.compile(r'[0-9a-f]{64}')
PROPOSAL_METADATA = frozenset({
    'config/swissknife_visual_functional_tasks.json',
    'implementation_plan/docs/53-swissknife-visual-functional-mcplusplus.todo.md',
    'implementation_plan/docs/53-swissknife-visual-functional-mcplusplus.objectives.md',
})
RUNTIME = 'data/agent_supervisor/swissknife_visual_functional/'
VOLATILE = {'created_at', 'received_at', 'updated_at', 'timestamp', 'pid', 'correlation_id',
            'receipt_id', 'receipt_refs', 'event_dag_refs', 'receipt_cid', 'event_cid', 'artifacts',
            'original', 'source_sha256', 'scenario_sha256', 'started_at_ms', 'finished_at_ms'}


class BlockedCacheError(ValueError):
    pass


class CachedBlockedRepair(RuntimeError):
    code = 'cached_model_decline'

    def __init__(self, record):
        self.record = record
        self.fingerprint = record['fingerprint']
        self.reason = record['response']['summary']
        self.findings = record['response']['findings']
        super().__init__('unchanged scoped repair remains blocked: ' + self.reason)


def _require(value, message):
    if not value:
        raise BlockedCacheError(message)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _path(root, raw):
    root = Path(root).resolve()
    p = Path(raw)
    if p.is_absolute():
        try: p = p.relative_to(root)
        except ValueError as exc: raise BlockedCacheError('path escapes checkout') from exc
    _require(p.parts and '..' not in p.parts and '.' not in p.parts, 'invalid cache/source path')
    current = root
    for part in p.parts:
        current /= part
        if current.is_symlink():
            raise BlockedCacheError('symlink cache/source path refused')
    return current


def _hash(root, name):
    path = _path(root, name)
    if not path.exists(): return None
    info = path.stat()
    _require(stat.S_ISREG(info.st_mode) and info.st_size <= 4 * 1024 * 1024, 'unbounded source file')
    return _sha(path.read_bytes())


def _sources(root, values):
    _require(type(values) is dict and len(values) <= 256, 'invalid source hash map')
    result = {}
    for name, expected in values.items():
        _require(type(name) is str and (expected is None or type(expected) is str and HEX.fullmatch(expected)), 'invalid source identity')
        relative = _path(root, name).relative_to(Path(root).resolve()).as_posix()
        _require(_hash(root, relative) == expected, 'source changed since negative admission')
        result[relative] = expected
    return dict(sorted(result.items()))


def _native_reason(value, depth=0):
    if depth > 8 or not isinstance(value, dict):
        return None
    fields = {'error','error_type','code','type','message','reason','status','outcome','success','ok','isError'}
    result = {k:v for k,v in value.items() if k in fields and (v is None or type(v) in {str,bool,int,float})}
    if isinstance(value.get('error'), dict):
        result['error'] = _native_reason(value['error'], depth+1)
    for key in ('result','response','owner_error'):
        if isinstance(value.get(key), dict): result[key] = _native_reason(value[key], depth+1)
    if isinstance(value.get('content'), list):
        result['content'] = [{'json':_native_reason(item['json'],depth+1)} for item in value['content'][:8]
                             if isinstance(item,dict) and isinstance(item.get('json'),dict)]
    return result


def _stable_failure(failure):
    """Only concrete assertion/backend fields participate, never proof labels."""
    volatile_values = set()
    def collect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in VOLATILE and key not in {'artifacts','source_sha256','original'}:
                    if isinstance(item, str): volatile_values.add(item)
                    elif isinstance(item, list): volatile_values.update(x for x in item if isinstance(x, str))
                collect(item)
        elif isinstance(value, list):
            for item in value: collect(item)
    collect(failure)
    def clean(value, depth=0):
        _require(depth <= 20, 'failure nesting exceeds bound')
        if isinstance(value, dict):
            return {k: clean(v, depth+1) for k,v in sorted(value.items()) if k not in VOLATILE and k not in {'receipt','persistence'}}
        if isinstance(value, list): return [clean(v, depth+1) for v in value[:32]]
        if isinstance(value, str):
            text=value
            for item in sorted(volatile_values, key=len, reverse=True):
                if len(item) >= 8: text=text.replace(item, '<volatile>')
            text=re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '<uuid>', text)
            text=re.sub(r'(verification/attempt-|model-inputs/)[A-Za-z0-9_-]+', r'\1<attempt>', text)
            return text
        _require(value is None or type(value) in {bool,int,float}, 'invalid failure value')
        return value
    diagnostic=failure.get('diagnostic') or {}
    result={'stage':failure.get('stage'),'error':failure.get('error'),
            'phase':diagnostic.get('phase'),'step':diagnostic.get('step'),'assertion':diagnostic.get('error')}
    owners=[]
    for item in diagnostic.get('retained_observations', []):
        observation=item.get('observation', {})
        for row in observation.get('records', []):
            response=row.get('response') or {}
            owners.append({'binding_id':row.get('binding_id'),'tool_id':row.get('tool_id'),
                           'error':row.get('error'),'outcome':response.get('outcome'),
                           'result':_native_reason(response.get('result'))})
    if owners: result['owner_failures']=owners
    if failure.get('visual_review'): result['visual_review']=failure['visual_review'].get('response')
    value=clean(result)
    _require(len(_json(value).encode()) <= 49152, 'concrete failure exceeds cache bound')
    return value


def build_scope(root, *, task, route, edit_hashes, readonly_hashes, failure):
    """Hash current source and normalized actual failure without granting authority."""
    root=Path(root).resolve()
    _require(type(task) is dict and re.fullmatch(r'SVF-[A-Z0-9-]{1,64}', str(task.get('task_id',''))), 'invalid task')
    _require(type(route) is dict and route.get('provider')=='grok_cli' and route.get('model')=='grok-4.7', 'wrong pinned route')
    _require(route.get('allowLocalFallback',route.get('allow_local_fallback')) is False
             and route.get('allowCrossProviderFallback',route.get('allow_cross_provider_fallback')) is False, 'fallback route refused')
    _require(not any(re.search(r'api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|secret|password|credential', k, re.I) for k in route), 'private route values refused')
    edits=_sources(root,edit_hashes);readonly=_sources(root,readonly_hashes)
    _require(edits and set(edits)==set(task.get('edit_paths',[])), 'cache edit scope differs from task')
    _require(not set(edits)&set(readonly), 'duplicate edit/readonly identity')
    f=failure.get('failure',failure) if type(failure) is dict else None
    _require(type(f) is dict and f.get('schema')==FAILURE_SCHEMA and f.get('task_id')==task['task_id']
             and type(f.get('source_sha256')) is dict and f.get('completion_authority') is False
             and f.get('work_complete') is False, 'failure is not current task/source bound')
    failure_sources=_sources(root,f['source_sha256'])
    _require(set(edits)<=set(failure_sources) and all(failure_sources[k]==v for k,v in edits.items())
             and all(k in edits or readonly.get(k)==v for k,v in failure_sources.items()), 'failure scope sources differ')
    _require(type(f.get('error')) is dict and f['error'].get('code') not in {None,'browser_contention'}, 'not a concrete semantic failure')
    fields=('task_id','kind','app_id','acceptance','edit_paths','checks','dependencies','llm_limits','conflict_policy')
    identity={'task':{k:task[k] for k in fields if k in task},'route':route,
              'edit_hashes':edits,'readonly_hashes':readonly,'failure':_stable_failure(f)}
    _require(len(_json(identity).encode()) <= 98304, 'negative scope exceeds bound')
    return {'schema':SCHEMA,'fingerprint':_sha(_json(identity).encode()),'identity':identity}


def build_proposal_scope(root, *, task, route, edit_hashes, readonly_hashes):
    """Fence an initial backend repair, without inventing a producer failure.

    The task's semantic policy and declared source paths replace a workflow
    failure in this identity. Whole-board status, generated attempt contexts,
    receipts and progress cannot renew an otherwise identical paid request.
    A current successful blocked/no-edits native receipt is still mandatory
    before remember_blocked() can create a negative entry.
    """
    root = Path(root).resolve()
    _require(type(task) is dict and task.get('kind') == 'backend-repair'
             and re.fullmatch(r'SVF-[A-Z0-9-]{1,64}', str(task.get('task_id', ''))),
             'initial negative proposal scope requires a backend-repair task')
    _require(type(route) is dict and route.get('provider') == 'grok_cli'
             and route.get('model') == 'grok-4.7', 'wrong pinned route')
    _require(route.get('allowLocalFallback', route.get('allow_local_fallback')) is False
             and route.get('allowCrossProviderFallback', route.get('allow_cross_provider_fallback')) is False,
             'fallback route refused')
    _require(not any(re.search(r'api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|secret|password|credential', k, re.I)
                     for k in route), 'private route values refused')
    edits = _sources(root, edit_hashes)
    _require(edits and set(edits) == set(task.get('edit_paths', []))
             and not set(edits) & PROPOSAL_METADATA, 'cache edit scope differs from backend task')
    _require(type(readonly_hashes) is dict and len(readonly_hashes) <= 256, 'invalid source hash map')
    def stable_path(name):
        _require(type(name) is str, 'invalid source identity')
        relative = _path(root, name).relative_to(root).as_posix()
        return relative, (relative not in PROPOSAL_METADATA and
                          (not relative.startswith(RUNTIME) or relative.startswith(RUNTIME + 'backends/fixtures/')))
    readonly_inputs = {}
    for name, expected in readonly_hashes.items():
        _require(expected is None or type(expected) is str and HEX.fullmatch(expected), 'invalid source identity')
        relative, stable = stable_path(name)
        if stable:
            _require(relative not in readonly_inputs, 'duplicate normalized readonly identity')
            readonly_inputs[relative] = expected
    readonly = _sources(root, readonly_inputs)
    _require(readonly and not set(edits) & set(readonly), 'backend readonly closure is empty or overlaps edits')
    for field in ('context_paths', 'execution_inputs'):
        names = task.get(field, [])
        _require(type(names) is list and len(names) <= 256, 'invalid declared backend context')
        for name in names:
            relative, stable = stable_path(name)
            _require(not relative.startswith(RUNTIME) or stable,
                     'generated runtime paths cannot be declared backend source context')
            _require(not stable or relative in edits or relative in readonly,
                     'backend negative scope omits a declared source dependency')
    fields = ('task_id', 'kind', 'app_id', 'acceptance', 'edit_paths', 'checks',
              'dependencies', 'llm_limits', 'conflict_policy', 'context_paths',
              'execution_inputs', 'semantic_recovery_inputs', 'timeout_seconds')
    identity = {'task': {key: task[key] for key in fields if key in task},
                'route': route, 'edit_hashes': edits, 'readonly_hashes': readonly,
                'proposal': {'mode': 'repair', 'reason': 'backend_model_decline'}}
    _require(len(_json(identity).encode()) <= 98304, 'negative scope exceeds bound')
    return {'schema': SCHEMA, 'fingerprint': _sha(_json(identity).encode()), 'identity': identity}


def _producer_text_identity(text):
    """Hash semantic command diagnostics without retaining raw command output."""
    text = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '<uuid>', text)
    text = re.sub(r'\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?', '<time>', text)
    volatile = ('pid|parent_pid|producer_pid|process_group_id|start_ticks|producer_birth|'
                'duration_seconds|elapsed_seconds|observed_at|started_at_ms|finished_at_ms|'
                'nonce|challenge|capture_id|invocation_id|request_id|response_id|correlation_id|operation_id|'
                'request_sha256|response_sha256|capture_sha256|wire_request_sha256|wire_response_sha256|'
                'request_bytes|response_bytes')
    text = re.sub(r'([\"\'](?:' + volatile + r')[\"\']\s*:\s*)(?:[\"\'][^\"\'\n]*[\"\']|\d+(?:\.\d+)?)',
                  lambda match: match.group(1) + '"<volatile>"', text)
    text = re.sub(r'((?:"--challenge"|\'--challenge\'|--challenge)\s*(?:,\s*)?[\"\']?)[0-9a-f]{32}(?=[\"\'\s,\]])',
                  lambda match: match.group(1) + '<challenge>', text)
    text = re.sub(r'(foundation-call-witness/(?:kit-pubsub|accelerate-supervisor)/)[0-9a-f]{32}',
                  lambda match: match.group(1) + '<invocation>', text)
    text = re.sub(r'((?:attempt-|model-inputs/(?:proposal|repair)-[0-9]+-))[0-9a-f]{32}',
                  lambda match: match.group(1) + '<attempt>', text)
    references = r'(?:capture|failure_artifact)'
    text = re.sub(r'("' + references + r'"\s*:\s*\{[^{}]{0,1024}"sha256"\s*:\s*)"[0-9a-f]{64}"',
                  lambda match: match.group(1) + '"<reference-hash>"', text)
    text = re.sub(r'("' + references + r'"\s*:\s*\{[^{}]{0,1024}"bytes"\s*:\s*)[0-9]+',
                  lambda match: match.group(1) + '"<reference-bytes>"', text)
    text = re.sub(r'\bin\s+\d+(?:\.\d+)?s\b', 'in <duration>s', text)
    return _sha(text.encode())


def _producer_identity(root, task, reference, source_identity):
    from swissknife_visual_functional_native_context import load_backend_check_report
    try:
        loaded = load_backend_check_report(root, task, reference)
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as error:
        raise BlockedCacheError('actual backend producer report is invalid; no paid retry admitted') from error
    report = loaded['report']
    sources = {**source_identity['edit_hashes'], **source_identity['readonly_hashes']}
    _require(all(name in sources and sources[name] == digest
                 for name, digest in report['source_sha256'].items()),
             'producer source closure differs from negative admission')
    def argv(value, declared):
        result = list(value)
        if Path(declared[0]).name in {'python', 'python3'}:
            # The report loader already verifies the actual Python binary;
            # equivalent executable aliases do not change command semantics.
            result[0] = 'python3'
        return result
    checks = [{'index': row['index'], 'declared_argv': row['declared_argv'],
               'executed_argv': argv(row['executed_argv'], row['declared_argv']), 'exit_code': row['exit_code']}
              for row in report['checks']]
    diagnostic = report['diagnostic']
    if diagnostic is not None:
        diagnostic = {**{name: diagnostic[name] for name in ('stage', 'code', 'check_index', 'exit_code')},
                      'argv': argv(diagnostic['argv'], report['original_checks'][diagnostic['check_index']]),
                      'stdout_identity_sha256': _producer_text_identity(diagnostic['stdout_tail']),
                      'stderr_identity_sha256': _producer_text_identity(diagnostic['stderr_tail'])}
    return {'schema': 'swissknife.backend-producer-identity.v1',
            'task_semantics_sha256': report['task_semantics_sha256'],
            'original_edit_paths': list(task['edit_paths']),
            'source_identity_sha256': _sha(_json(report['source_sha256']).encode()),
            'outcome': report['outcome'], 'original_checks': report['original_checks'],
            'checks': checks, 'diagnostic': diagnostic}


def build_producer_scope(root, *, task, route, edit_hashes, readonly_hashes, producer, producer_task=None):
    """Fence real original check observations, without granting task acceptance."""
    scope = build_proposal_scope(root, task=task, route=route, edit_hashes=edit_hashes,
                                 readonly_hashes=readonly_hashes)
    identity = scope['identity']
    original = task if producer_task is None else producer_task
    fields = ('task_id', 'kind', 'app_id', 'acceptance', 'edit_paths', 'checks',
              'dependencies', 'llm_limits', 'conflict_policy', 'context_paths',
              'execution_inputs', 'semantic_recovery_inputs', 'timeout_seconds')
    _require(type(original) is dict and type(original.get('edit_paths')) is list
             and len(original['edit_paths']) <= 128 and all(type(name) is str for name in original['edit_paths'])
             and len(original['edit_paths']) == len(set(original['edit_paths']))
             and set(identity['edit_hashes']) <= set(original['edit_paths'])
             and {key: original[key] for key in fields if key != 'edit_paths' and key in original}
                 == {key: task[key] for key in fields if key != 'edit_paths' and key in task},
             'producer task differs from the original policy or expands recovery edits')
    identity['proposal'] = {'mode': 'repair', 'reason': 'backend_checked_model_decline'}
    identity['producer'] = _producer_identity(root, original, producer, identity)
    _require(len(_json(identity).encode()) <= 98304, 'negative scope exceeds bound')
    scope['fingerprint'] = _sha(_json(identity).encode())
    # This integrity reference is deliberately outside the stable key: a fresh
    # actual run with identical observations cannot renew paid eligibility.
    scope['producer_reference'] = dict(producer)
    return scope


def _fence(root, scope):
    _require(type(scope) is dict and scope.get('schema')==SCHEMA and type(scope.get('identity')) is dict
             and scope.get('fingerprint')==_sha(_json(scope['identity']).encode()), 'negative identity changed')
    identity=scope['identity']
    _sources(root,identity['edit_hashes']);_sources(root,identity['readonly_hashes'])
    if 'producer' in identity:
        original = {**identity['task'], 'edit_paths': identity['producer'].get('original_edit_paths')}
        _require('producer_reference' in scope and _producer_identity(root, original,
                     scope['producer_reference'], identity) == identity['producer'],
                 'actual producer report changed from negative admission')
    else:
        _require('producer_reference' not in scope, 'unexpected producer reference')
    return identity


def _directory(root, directory, identity):
    path=_path(root,directory)
    prefix=Path(root).resolve()/'data/agent_supervisor/swissknife_visual_functional/tasks'/identity['task']['task_id']
    _require(path.is_relative_to(prefix) and path!=prefix, 'cache escaped its task runtime')
    for parent in (path, *path.parents):
        if parent == Path(root).resolve(): break
        _require(not parent.exists() or parent.is_dir(), 'cache directory state is malformed')
    return path


def _proposal_context(root, receipt, identity):
    """Match the historical admitted task body; its UUID is never a scope key."""
    if 'proposal' not in identity:
        return None
    prefix = Path(RUNTIME) / 'tasks' / identity['task']['task_id'] / 'model-inputs'
    matches = []
    for item in receipt.get('input_files', []):
        if not isinstance(item, dict) or not isinstance(item.get('path'), str):
            continue
        path = _path(root, item['path'])
        relative = path.relative_to(Path(root).resolve())
        if relative.is_relative_to(prefix):
            suffix = relative.relative_to(prefix)
            if len(suffix.parts) == 2 and suffix.name == 'context.json':
                matches.append((path, item))
    _require(len(matches) == 1, 'blocked backend receipt lacks one admitted task context')
    path, reference = matches[0]
    raw = _read(path, 1024 * 1024)
    _require(type(reference.get('sha256')) is str and _sha(raw) == reference['sha256'],
             'blocked backend context changed from its admitted bytes')
    if 'size_bytes' in reference:
        _require(type(reference['size_bytes']) is int and len(raw) == reference['size_bytes'],
                 'blocked backend context byte count differs')
    context = json.loads(raw)
    observed = context.get('task') if type(context) is dict else None
    _require(type(observed) is dict, 'blocked backend context has no semantic task body')
    fields = ('task_id', 'kind', 'app_id', 'acceptance', 'edit_paths', 'checks',
              'dependencies', 'llm_limits', 'conflict_policy')
    _require(all(observed.get(key) == identity['task'].get(key) for key in fields),
             'blocked backend receipt describes another task policy')
    _require(context.get('proposal_scope_fingerprint') == _sha(_json(identity).encode()),
             'blocked backend context lacks its admitted source/context fingerprint')
    if 'producer' in identity:
        _require(context.get('producer_identity_sha256') == _sha(_json(identity['producer']).encode()),
                 'blocked backend context does not bind its actual producer identity')
    return {'path': path.relative_to(Path(root).resolve()).as_posix(),
            'sha256': _sha(raw), 'size_bytes': len(raw)}


def _validate(root, receipt, identity):
    from swissknife_visual_functional_llm import validate_model_receipt, safe_rejected_response
    validate_model_receipt(root,receipt,task_id=identity['task']['task_id'],mode='repair',predicted_files=list(identity['edit_hashes']))
    response=receipt['response']
    _require(response.get('decision')=='blocked' and response.get('edits')==[]
             and safe_rejected_response(response) and len(_json(response).encode())<=32768, 'only safe bounded blocked/no-edits results may be cached')
    recorded={v['path']:v.get('sha256') for v in receipt.get('input_files',[]) if isinstance(v,dict)}
    _require(all(name in recorded and recorded[name]==value for name,value in identity['edit_hashes'].items()), 'blocked receipt omits admitted edit hashes')
    _require(all(name not in recorded or recorded[name]==value for name,value in identity['readonly_hashes'].items()), 'blocked receipt readonly hashes conflict')
    if 'proposal' in identity:
        _proposal_context(root, receipt, identity)
        if identity['route'].get('repairReadPolicy') == 'inline_only':
            _require(receipt.get('native_read_file_denied') is True
                     and receipt['native_observation']['native_grok_progress']['tool_name_counts'].get('read_file') == 0,
                     'blocked backend receipt violated its inline-only policy')
    return response


def _read(path, limit):
    _require(path.is_file() and not path.is_symlink() and path.stat().st_size<=limit,'invalid bounded cache artifact')
    return path.read_bytes()


def _immutable(path,data):
    try:
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    except FileExistsError:
        _require(_read(path,len(data))==data,'immutable cache artifact conflict')
        return
    with os.fdopen(fd,'wb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    descriptor=os.open(path.parent,os.O_DIRECTORY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)


def remember_blocked(root, directory, scope, receipt_path):
    """Retain only sanitized validated receipt fields; provider logs never enter."""
    identity=_fence(root,scope);directory=_directory(root,directory,identity)
    original=_path(root,receipt_path);raw=_read(original,MAX_RECEIPT_BYTES);receipt=json.loads(raw)
    response=_validate(root,receipt,identity)
    # Keep just the fields consumed by the independent receipt validator.
    names=('schema','task_id','mode','provider','model','temperature','success','allow_local_fallback',
        'allow_cross_provider_fallback','disable_model_retry','edits_applied','work_complete','completion_authority',
        'effective_route','source_contract_sha256','prompt_sha256','router_source_sha256','output_sha256',
        'response_sha256','native_read_file_denied','screenshots','response')
    safe={k:receipt[k] for k in names if k in receipt}
    native=receipt['native_observation'];progress=native['native_grok_progress']
    safe['native_observation']={k:native[k] for k in ('exit_code','native_grok_reason_code','native_grok_error_observed','timed_out') if k in native}
    safe['native_observation']['native_grok_progress']={k:progress[k] for k in ('response_usable','tool_name_counts') if k in progress}
    safe['effective_route']={k:receipt['effective_route'][k] for k in ('effective_provider_name','effective_model_name')}
    recorded={v['path']:v.get('sha256') for v in receipt.get('input_files',[]) if isinstance(v,dict) and isinstance(v.get('path'),str)}
    safe['input_files']=[{'path':name,'sha256':value} for name,value in {**identity['edit_hashes'],**identity['readonly_hashes']}.items() if name in recorded]
    context_reference = _proposal_context(root, receipt, identity)
    if context_reference is not None:
        safe['input_files'].append(context_reference)
    _validate(root,safe,identity);_fence(root,scope)
    directory.mkdir(parents=True,exist_ok=True);_directory(root,directory,identity)
    if (directory/(scope['fingerprint']+'.json')).exists():
        return _lookup(root,directory,scope)
    _require(len(list(directory.glob('*.json'))) < MAX_ENTRIES*2,'negative cache capacity reached')
    copy=directory/(scope['fingerprint']+'.receipt.json');data=(_json(safe)+'\n').encode();_immutable(copy,data)
    record={**scope,'receipt':{'path':copy.relative_to(Path(root).resolve()).as_posix(),'sha256':_sha(data)},
        'original_receipt':{'path':original.relative_to(Path(root).resolve()).as_posix(),'sha256':_sha(raw)},
        'response':response,'completion_authority':False,'work_complete':False}
    _immutable(directory/(scope['fingerprint']+'.json'),(_json(record)+'\n').encode())
    return record


def _lookup(root,directory,scope):
    identity=_fence(root,scope);directory=_directory(root,directory,identity)
    path=directory/(scope['fingerprint']+'.json')
    _require(not path.is_symlink(),'symlink negative index refused')
    if not path.exists():
        copy=directory/(scope['fingerprint']+'.receipt.json')
        _require(not copy.exists() and not copy.is_symlink(),
                 'orphan negative receipt requires verified cache repair; no paid retry admitted')
        return None
    value=json.loads(_read(path,196608))
    expected={'schema','fingerprint','identity','receipt','original_receipt','response','completion_authority','work_complete'}
    if 'producer' in identity: expected.add('producer_reference')
    _require(set(value)==expected
             and value.get('schema')==SCHEMA and value.get('identity')==identity and value.get('fingerprint')==scope['fingerprint']
             and value.get('completion_authority') is False and value.get('work_complete') is False,'cached identity mismatch')
    if 'producer' in identity: _fence(root,value)
    copy=_path(root,value['receipt']['path'])
    _require(copy.parent==directory and copy.name==scope['fingerprint']+'.receipt.json','receipt escaped negative cache')
    raw=_read(copy,131072);_require(_sha(raw)==value['receipt']['sha256'],'negative receipt changed')
    response=_validate(root,json.loads(raw),identity)
    _require(response==value['response'],'cached reason differs from validated receipt')
    return value


def raise_if_blocked(root, directory, scope):
    """A missing entry permits work; a valid negative or malformed identity blocks paid retry."""
    try: value=_lookup(root,directory,scope)
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:
        raise BlockedCacheError('negative cache identity or artifact is invalid; no paid retry admitted') from exc
    if value is not None: raise CachedBlockedRepair(value)
    return None
