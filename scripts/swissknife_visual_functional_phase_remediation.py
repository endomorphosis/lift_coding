"""Finite phase remediation admission; original acceptance/history stay authoritative.

Native plan revisions operate on an owned metadata projection, never on the live
board. The separate CAS publisher rolls forward its exact before/after bytes and
refuses foreign changes. A derived task may make one paid source proposal; it
cannot create another child, refund the original phase, or complete its parent.
"""
from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import time
import math

SCHEMA = 'swissknife.phase-remediation.v1'
KIND = 'scoped-remediation'
PHASE = 'final_visual_review'
MAX_ORIGINALS = 45
FINAL_SCHEMA = 'swissknife.final-remediation.v1'
FINAL_MODE = 'final-review'
FINAL_IDS = frozenset('SVF-'+str(i) for i in range(1001,1046))
_PHASE_MODE = ContextVar('svf_finite_phase_mode', default=None)
ORIGINAL_APPS = {'SVF-113': 'image-viewer', 'SVF-123': 'notes', 'SVF-133': 'accelerate-panel', 'SVF-143': 'terminal', 'SVF-153': 'vibecode', 'SVF-163': 'music-studio-unified', 'SVF-173': 'ai-chat', 'SVF-183': 'file-manager', 'SVF-193': 'task-manager', 'SVF-203': 'todo', 'SVF-213': 'model-browser', 'SVF-223': 'huggingface', 'SVF-233': 'openrouter', 'SVF-243': 'ipfs-explorer', 'SVF-253': 'device-manager', 'SVF-263': 'settings', 'SVF-273': 'mcp-control', 'SVF-283': 'api-keys', 'SVF-293': 'github', 'SVF-303': 'oauth-login', 'SVF-313': 'cron', 'SVF-323': 'navi', 'SVF-333': 'p2p-network', 'SVF-343': 'p2p-chat-unified', 'SVF-353': 'neural-network-designer', 'SVF-363': 'training-manager', 'SVF-373': 'calculator', 'SVF-383': 'clock', 'SVF-393': 'calendar', 'SVF-403': 'peertube', 'SVF-413': 'friends-list', 'SVF-423': 'media-player', 'SVF-433': 'system-monitor', 'SVF-443': 'neural-photoshop', 'SVF-453': 'cinema', 'SVF-463': 'strudel', 'SVF-473': 'strudel-ai-daw', 'SVF-483': 'music-studio', 'SVF-493': 'p2p-chat', 'SVF-503': 'datasets-browser', 'SVF-513': 'idl-explorer', 'SVF-523': 'glasses-preview', 'SVF-533': 'orb-auto-ui', 'SVF-543': 'mcp-plus-plus', 'SVF-553': 'agent-supervisor'}
MAX_PLAN_BYTES = 8 * 1024 * 1024
WORKER = 'scripts/swissknife_visual_functional_worker.py'

class RemediationRefusal(ValueError):
    code = 'phase_remediation_refused'


def need(value, text):
    if not value:
        raise RemediationRefusal(text)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(wire(value)).hexdigest()


def physical(root, name):
    root = Path(root)
    need(root.is_absolute() and root.resolve() == root, 'checkout root must be physical')
    need(type(name) is str and name and not Path(name).is_absolute()
         and all(p not in ('', '.', '..') for p in name.split('/')), 'invalid relative remediation path')
    target = root / name
    need(target.resolve() == target, 'remediation symlink or escape refused')
    return target


def read(root, name, limit=MAX_PLAN_BYTES, *, allow_empty=False):
    target = physical(root, name)
    fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and (0 <= before.st_size if allow_empty else 0 < before.st_size) and before.st_size <= limit, 'unbounded/nonregular remediation input')
        raw = stream.read(limit + 1); after = os.fstat(stream.fileno())
    ident = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    need(len(raw) == before.st_size and ident(before) == ident(after) == ident(target.lstat()), 'remediation input changed')
    return raw


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate remediation JSON key'); result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda x: need(False, 'nonfinite remediation JSON'))


def ref(root, name):
    raw = read(root, name)
    return {'path': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def check_ref(root, value):
    need(type(value) is dict and set(value) == {'path', 'sha256', 'bytes'}, 'invalid remediation reference')
    raw = read(root, value['path'])
    need(hashlib.sha256(raw).hexdigest() == value['sha256'] and len(raw) == value['bytes'], 'remediation evidence changed')
    return raw


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)


def atomic(root, name, raw, *, exclusive=False):
    path = physical(root, name); path.parent.mkdir(parents=True, exist_ok=True)
    physical(root, name)
    if exclusive:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    else:
        fd, temporary = tempfile.mkstemp(prefix='.phase-remediation-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
    sync_dir(path.parent)


def immutable(root, name, raw):
    target = physical(root, name)
    if target.exists():
        need(read(root, name) == raw, 'immutable prepared artifact changed')
    else:
        atomic(root, name, raw, exclusive=True)



def final_policy_enabled(profile):
    value = profile.get('finalRemediation')
    if value is None: return False
    expected = {'schema': FINAL_SCHEMA, 'enabled': True, 'max_finals': 45,
                'max_children_per_final': 1, 'max_paid_assessments': 1,
                'max_paid_proposals': 1, 'child_timeout_seconds': 3600}
    extra = value.get('max_paid_producer_repairs', None) if type(value) is dict else None
    clean = {k:v for k,v in value.items() if k not in {'max_paid_producer_repairs','producer_repair_timeout_seconds'}} if type(value) is dict else {}
    need(type(value) is dict and type(value.get('enabled')) is bool
         and ('max_paid_producer_repairs' not in value or type(extra) is int and extra == 1)
         and ('producer_repair_timeout_seconds' not in value or type(value['producer_repair_timeout_seconds']) is int and value['producer_repair_timeout_seconds']==900)
         and wire({**clean, 'enabled': True}) == wire(expected), 'final remediation opt-in policy expanded')
    return value['enabled']


def policy_enabled(profile):
    value = profile.get('phaseRemediation')
    legacy = False
    if value is not None:
        expected = {'schema':SCHEMA,'enabled':True,'max_originals':45,'max_children_per_phase':1,
                    'max_paid_assessments':1,'max_paid_proposals':1,'child_timeout_seconds':3600}
        need(type(value) is dict and type(value.get('enabled')) is bool
             and wire({**value,'enabled':True}) == wire(expected), 'phase remediation opt-in policy expanded')
        legacy = value['enabled']
    final = final_policy_enabled(profile)
    return final if _PHASE_MODE.get() == FINAL_MODE else legacy if _PHASE_MODE.get() == 'original' else legacy or final


def pending_publications(root, profile):
    directory = physical(root, base(profile)+'/admissions')
    if not directory.exists(): return []
    need(directory.is_dir(), 'invalid remediation admission directory')
    children = list(directory.iterdir()); need(len(children) <= MAX_ORIGINALS, 'finite admission directory bound')
    result = []
    for child in sorted(children):
        name = str(child.relative_to(root)); physical(root, name)
        need(child.is_dir() and re.fullmatch('[0-9a-f]{64}', child.name), 'foreign admission directory')
        if (child/'intent.json').exists() and not (child/'commit.json').exists(): result.append(name)
    return result


def assert_controller_pins(root, profile):
    from svf_backends.foundation_service_ownership import _registration
    cfg = _registration(Path(root))
    required = (__file_name(), WORKER, 'scripts/swissknife_visual_functional_supervisor.py',
                'scripts/swissknife_visual_functional_llm.py',
                'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/lane_resume.py')
    need(all(cfg['protected_sha256'].get(name) == ref(root,name)['sha256'] for name in required),
         'remediation controller is not pinned by the registered owner')


def recover_pending(root, profile, *, ensure_authority):
    """Startup convergence only; never constructs/adopts a new plan or budget."""
    pending = pending_publications(root, profile)
    if not pending: return {'state':'idle','recovered':0}
    assert_controller_pins(root, profile)
    no_hold_or_activity(root, profile)
    with locked(root, profile):
        for directory in pending:
            _recover_intent(root, profile, directory, ensure_authority=ensure_authority)
    return {'state':'recovered','recovered':len(pending)}


def base(profile):
    return profile['runtimeRoot'] + ('/state/final-phase-remediation' if _PHASE_MODE.get() == FINAL_MODE else '/state/phase-remediation')


@contextmanager
def locked(root, profile):
    name = base(profile) + '/admission.lock'; path = physical(root, name)
    path.parent.mkdir(parents=True, exist_ok=True); physical(root, name)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e: raise RemediationRefusal('remediation admission busy') from e
        yield
    finally: os.close(fd)


def originals(spec):
    if _PHASE_MODE.get() == FINAL_MODE: return finals(spec)
    tasks = [t for t in spec['tasks'] if t.get('kind') == 'verify' and t.get('app_id')]
    need({t['task_id']:t['app_id'] for t in tasks} == ORIGINAL_APPS
         and len(tasks) == MAX_ORIGINALS and len({t['task_id'] for t in tasks}) == MAX_ORIGINALS
         and len({t['app_id'] for t in tasks}) == MAX_ORIGINALS
         and all(re.fullmatch(r'SVF-[0-9]+', t['task_id']) for t in tasks), 'original verification allowlist changed')
    return {t['task_id']: t for t in tasks}


def gap_key(profile, task):
    return digest({'campaign': profile['runtimeRoot'], 'task_id': task['task_id'], 'phase': PHASE})


def child_id(task):
    if _PHASE_MODE.get() == FINAL_MODE:
        need(task.get('kind') == 'final-app-verify' and task['task_id'] in FINAL_IDS, 'derived/final task cannot grow recursive children')
        return 'SVF-FINAL-R' + task['task_id'][4:]
    need(re.fullmatch(r'SVF-[0-9]+', task['task_id']), 'derived tasks cannot grow remediation children')
    return 'SVF-PHASE-R' + task['task_id'][4:]



def _validate_current_failed_phase(root, profile, task, review_path):
    from swissknife_visual_functional_worker import ROOT, validate_workflow
    from swissknife_visual_functional_final_coverage import binding, review_join
    need(Path(ROOT) == Path(root), 'workflow validator must use this physical checkout')
    report = Path(review_path).parent / 'workflow.json'
    need(parse(read(root, str(report.relative_to(root)))).get('schema') == 'swissknife.visual-functional-workflow.v2',
         'new remediation requires genuine current independent V2 failure evidence')
    validated = validate_workflow(profile, task, report)
    need(validated is not None, 'failed phase lacks independently validated current V2 producer')
    return review_join(root, profile, task, binding(task, validated), Path(review_path), require_pass=False)


def qualify_gap(root, profile, task):
    """Pure reads only; never touches the phase journal lock or its spend."""
    if _PHASE_MODE.get() == FINAL_MODE: return qualify_final_gap(root, profile, task)
    from swissknife_visual_functional_phase_budget import _validate, _review, LIMIT
    from swissknife_visual_functional_review_recheck import SCHEMA as FENCE_SCHEMA, _source_contract, _stable
    need(task.get('kind') == 'verify' and re.fullmatch(r'SVF-[0-9]+', task['task_id']), 'not an original verification gap')
    directory = profile['runtimeRoot'] + '/tasks/' + task['task_id']
    phase_name = directory + '/required-phase-repair-budget.json'
    fence_name = directory + '/exhausted-visual-review-source-fence.json'
    phase = _validate(parse(read(root, phase_name)), task)
    need(phase['state'] == 'exhausted' and phase['spent'] >= LIMIT, 'phase is not exhausted')
    fence = parse(read(root, fence_name))
    need(fence.get('schema') == FENCE_SCHEMA and fence.get('task_id') == task['task_id']
         and fence.get('phase') == PHASE and type(fence.get('spent')) is int
         and fence['spent'] == phase['spent'] and fence.get('history_sha256') == _stable(phase['history'])
         and fence.get('failed_review') == phase['gap_request']['failed_review']
         and fence.get('completion_authority') is False and fence.get('work_complete') is False,
         'gap/fence/history identity differs')
    review = _review(root, task, fence['failed_review'])
    current = _source_contract(root, profile, task)
    need(fence.get('source_contract') == current, 'stale gap: allow normal original verification before remediation')
    _validate_current_failed_phase(root, profile, task, physical(root, fence['failed_review']['path']))
    return {'key': gap_key(profile, task), 'phase': ref(root, phase_name), 'fence': ref(root, fence_name),
            'failed_review': fence['failed_review'], 'source_contract': current,
            'history_sha256': _stable(phase['history']), 'spent': phase['spent'],
            'review_invocation_id': review['invocation_id']}


def blocks(text):
    parts = re.split(r'(?=^## SVF-)', text, flags=re.M)
    result = {}
    for part in parts[1:]:
        match = re.match(r'## (SVF-[A-Z0-9-]+)(?:\s|$)', part)
        need(match and match[1] not in result, 'invalid/duplicate board block')
        result[match[1]] = part
    return result


def member_spans(text, start=0):
    decoder = json.JSONDecoder(); cursor = start
    while text[cursor].isspace(): cursor += 1
    need(text[cursor] == '{', 'expected object'); cursor += 1; result = {}
    while True:
        while text[cursor].isspace() or text[cursor] == ',': cursor += 1
        if text[cursor] == '}': return result
        key, cursor = decoder.raw_decode(text, cursor)
        while text[cursor].isspace(): cursor += 1
        need(text[cursor] == ':', 'invalid object separator'); cursor += 1
        while text[cursor].isspace(): cursor += 1
        value_start = cursor; _, cursor = decoder.raw_decode(text, cursor)
        need(key not in result, 'duplicate object member'); result[key] = (value_start, cursor)


def task_spans(text):
    start, end = member_spans(text)['tasks']; cursor = start + 1; decoder = json.JSONDecoder(); rows = {}
    while True:
        while text[cursor].isspace() or text[cursor] == ',': cursor += 1
        if text[cursor] == ']': return rows, cursor
        value, after = decoder.raw_decode(text, cursor)
        need(value['task_id'] not in rows, 'duplicate canonical task')
        rows[value['task_id']] = (cursor, after); cursor = after


def child_task(profile, original, gap):
    identity = child_id(original); app = original['app_id']
    scenario = 'swissknife/test/e2e/functional-workflows/' + app + '.json'
    scope_owner = gap['source_task'] if _PHASE_MODE.get() == FINAL_MODE else original
    allowed = [p for p in scope_owner.get('edit_paths', []) if p == scenario
               or p == 'swissknife/web/js/main-simple.js'
               or p == 'swissknife/web/js/apps/' + app + '.js'
               or p == 'swissknife/web/css/' + app + '.css']
    if _PHASE_MODE.get() == FINAL_MODE:
        allowed = list(gap['source_scope'])
        need(scope_owner.get('kind') == 'verify' and scope_owner.get('app_id') == app
             and scope_owner['task_id'] == original['original_verify_task'], 'final source basis differs')
    need(allowed and set(allowed) <= set(scope_owner['edit_paths']), 'no declared application/scenario remediation scope')
    directory = profile['runtimeRoot'] + '/tasks/' + identity
    result = {'task_id': identity, 'stable_task_id': identity, 'title': 'One scoped source remediation for ' + original['task_id'],
              'kind': KIND, 'status': 'ready', 'goal_id': original['goal_id'], 'app_id': app,
              'dependencies': list(original.get('dependencies', [])), 'priority': 'P0', 'edit_paths': allowed,
              'checks': [], 'outputs': [directory + '/receipt.json'], 'predicted_files': [directory + '/receipt.json', *allowed],
              'execution_command': ['python3', WORKER, '--task-id', identity],
              'execution_validation': ['python3', WORKER, '--validate', '--task-id', identity],
              'timeout_seconds': 3600, 'resource_class': 'cpu-browser',
              'acceptance': 'At most one source proposal and one stale-evidence assessment, exact checked application and fresh original independent V2 functional producer with source-only validation. An obsolete gap needs a positive genuine refresh; functional-only pass is insufficient. Original acceptance remains downstream.',
              'context_paths': list(original.get('context_paths', [])),
              'execution_inputs': list(dict.fromkeys([*original.get('execution_inputs', []), __file_name(), gap['failed_review']['path']])),
              'phase_remediation': {'schema': SCHEMA, 'gap': gap, 'original_task': original,
                                    'max_paid_proposals': 1, 'max_paid_assessments': 1, 'allow_recovery': False, 'allow_children': False}}
    if _PHASE_MODE.get() == FINAL_MODE:
        result['phase_remediation']['mode'] = FINAL_MODE
        result['title'] = 'One bounded source remediation for final review ' + original['task_id']
        result['acceptance'] = 'One bounded source proposal and at most one stale-gap assessment; exact app/scenario CAS application and fresh independent functional producer. The final readonly task must separately pass its genuine current two-viewport review. No original task or prior spend is reopened or refunded.'
    if original.get('subgoal_id'): result['subgoal_id'] = original['subgoal_id']
    return result


def __file_name():
    return 'scripts/swissknife_visual_functional_phase_remediation.py'


def render_child(task):
    values = [('Status', 'ready'), ('Priority', 'P0'), ('Track', KIND), ('Goal id', task['goal_id']),
              ('Depends on', ', '.join(task['dependencies']) or 'none'),
              ('Deterministic command', ' '.join(task['execution_command'])),
              ('Validation', ' '.join(task['execution_validation'])),
              ('Resource class', task['resource_class']), ('Implementation timeout seconds', str(task['timeout_seconds'])),
              ('Predicted files', ', '.join(task['predicted_files'])), ('Execution inputs', ', '.join(task['execution_inputs'])),
              ('Conflict policy', 'Edit only the declared application/scenario under the campaign lease; no recovery or child task authority.'),
              ('Acceptance', task['acceptance'])]
    return '## ' + task['task_id'] + ' ' + task['title'] + '\n\n' + ''.join('- '+k+': '+v+'\n' for k,v in values)



def source_writer_deferrals(root, profile, spec, board, original):
    """Only independent ready writers can defer a gap; descendants cannot."""
    records = blocks(board); statuses = {}
    for identity, block in records.items():
        match = re.search(r'^- Status: ([^\n]+)', block, re.M)
        statuses[identity] = match[1].strip().lower() if match else ''
    descendants = {original['task_id']}
    while True:
        updated = descendants | {t['task_id'] for t in spec['tasks'] if descendants & set(t.get('dependencies', []))}
        if updated == descendants: break
        descendants = updated
    closure = set(original.get('execution_inputs', []) + original.get('context_paths', []) + original.get('edit_paths', []))
    candidates = [t for t in spec['tasks'] if t['task_id'] not in descendants
        and statuses.get(t['task_id']) in {'ready', 'pending'}
        and all(statuses.get(d) in {'completed', 'complete', 'done'} for d in t.get('dependencies', []))
        and t.get('kind') in {'implementation', 'repair', 'backend-repair', 'verify', KIND}
        and closure & set(t.get('edit_paths', []))]
    if not candidates: return []
    # Existing native read-only health recognizes a current exhausted semantic
    # contract. An exhausted recovery ledger cannot be an eligible writer.
    from ipfs_accelerate_py.agent_supervisor.rescue import lane_resume, semantic_recovery
    attempts = physical(root, profile['runtimeRoot'] + '/state/lane_resume_attempts.json')
    health = lane_resume.lane_execution_health(repo_root=Path(root), todo_path=physical(root, profile['todoPath']),
        task_header_prefix='## SVF-', attempt_path=attempts)
    exhausted = {row['task_id'] for row in health.get('pending_failures', [])
                 if row.get('current_contract_qualified') and row.get('exhausted')}
    result = []
    for task in candidates:
        if task['kind'] == KIND and not child_can_still_write(root, profile, task):
            continue
        if task['kind'] == 'verify':
            try:
                qualify_gap(root, profile, task)
            except (ValueError, OSError, KeyError):
                pass
            else:
                continue  # It will refuse before browser/model, so cannot write.
        if task['task_id'] in exhausted:
            limit = task.get('semantic_recovery_limit', 0) if task.get('semantic_recovery_command') else 0
            recovery = semantic_recovery.summary(attempts, task['task_id'])
            if recovery.get('spent', 0) >= limit:
                continue
        result.append(task['task_id'])
    return result


def propose(root, profile, task_id):
    spec_raw = read(root, profile['taskSpecPath']); board_raw = read(root, profile['todoPath'])
    spec = parse(spec_raw); original = originals(spec).get(task_id)
    need(original is not None, 'gap task is not an admitted original')
    board = board_raw.decode(); old_blocks = blocks(board)
    need(task_id in old_blocks and re.search(r'^- Status: (ready|pending|blocked)\s*$', old_blocks[task_id], re.M),
         'parent must be unclaimed pending/blocked; completed history cannot be amended')
    gap = qualify_gap(root, profile, original)
    waits = source_writer_deferrals(root, profile, spec, board, original)
    need(not waits, 'defer gap for independently eligible source writers: ' + ','.join(waits))
    child = child_task(profile, original, gap)
    need(child['task_id'] not in {t['task_id'] for t in spec['tasks']} and child['task_id'] not in old_blocks,
         'remediation child already exists; never create another identity')
    spans, closing = task_spans(spec_raw.decode()); text = spec_raw.decode(); start, end = spans[task_id]
    dependency_start, dependency_end = member_spans(text[start:end])['dependencies']
    dependencies = [*original.get('dependencies', []), child['task_id']]
    inserts = [(start+dependency_start, start+dependency_end, json.dumps(dependencies)),
               (closing, closing, ',\n' + '\n'.join('    '+line for line in json.dumps(child, indent=2, ensure_ascii=False, allow_nan=False).splitlines()) + '\n  ')]
    after_spec = text
    for a,b,value in sorted(inserts, reverse=True): after_spec = after_spec[:a]+value+after_spec[b:]
    parent_block = old_blocks[task_id]
    new_block, n = re.subn(r'^- Depends on:.*$', '- Depends on: '+', '.join(dependencies), parent_block, flags=re.M)
    need(n == 1 and board.count(parent_block) == 1, 'parent dependency line is ambiguous')
    after_board = board.replace(parent_block, new_block, 1)
    need(after_board.endswith('\n'), 'canonical board needs a final newline before additive publication')
    after_board += render_child(child)
    next_spec = parse(after_spec.encode()); indexed = {t['task_id']:t for t in next_spec['tasks']}
    need(len(indexed) == len(spec['tasks'])+1 and indexed[task_id] == {**original, 'dependencies': dependencies}, 'nondependency parent amendment')
    for old in spec['tasks']:
        if old['task_id'] != task_id: need(indexed[old['task_id']] == old, 'unrelated canonical task was changed')
    next_blocks = blocks(after_board)
    for identity, block in old_blocks.items():
        if identity != task_id: need(next_blocks[identity] == block, 'existing Markdown history changed')
    from swissknife_visual_functional_worker import validate_dag
    validate_dag(next_spec['tasks'])
    need(read(root, profile['taskSpecPath']) == spec_raw and read(root, profile['todoPath']) == board_raw, 'canonical inputs changed while preparing plan')
    return {'schema': SCHEMA, 'key': gap['key'], 'parent': task_id, 'child': child, 'gap': gap,
            'before': {name: {'path': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
                       for name, raw in ((profile['taskSpecPath'], spec_raw), (profile['todoPath'], board_raw))},
            'after': {profile['taskSpecPath']: after_spec, profile['todoPath']: after_board},
            'original_task': original, 'work_complete': False, 'completion_authority': False}


def plan_summary(plan):
    return {'schema': SCHEMA, 'key': plan['key'], 'parent': plan['parent'], 'child': plan['child']['task_id'],
            'before': plan['before'], 'after_sha256': {p:hashlib.sha256(s.encode()).hexdigest() for p,s in plan['after'].items()},
            'gap': plan['gap'], 'original_acceptance_deadlines_unchanged': True,
            'new_paid_proposal_limit': 1, 'new_paid_assessment_limit': 1, 'completion_authority': False}


def native_prepare(root, profile, plan, directory, *, lease_id):
    """Real public SDK revision semantics on private metadata only, not live history."""
    from ipfs_accelerate_py.agent_supervisor.planning.plan_revision_contracts import (
        CompletionAuthority, DeltaEffectClass, LifecycleState, MergeStrategyKind, PlanAuthorityRoots,
        PlanCompletionRule, PlanConflictContract, PlanDelta, PlanDeltaItem, PlanDeltaOperation,
        PlanLeaseContract, PlanMergeStrategy, PlanOrigin, PlanPopulationDigest, PlanProviderContract,
        PlanResourceContract, PlanRetryContract, PlanRevision, PlanWorktreeContract, PopulationKind,
        plan_revision_cid,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.plan_revision_store import PlanRevisionStore, PlanRevisionApplyRequest
    cid = plan_revision_cid
    summary = plan_summary(plan); before_spec = parse(check_ref(root, plan['before'][profile['taskSpecPath']]))
    completed = [name for name, body in blocks(check_ref(root, plan['before'][profile['todoPath']]).decode()).items()
                 if re.search(r'^- Status: (completed|complete|done)\s*$', body, re.M)]
    tasks = [cid({'logical_task': t['task_id']}) for t in before_spec['tasks']]
    goals = [cid({'logical_goal': g.get('goal_id') or g.get('goal_cid') or digest(g)}) for g in before_spec.get('goals', [])]
    parent_cid = cid({'logical_task': plan['parent']}); child_cid = cid({'logical_task': plan['child']['task_id']})
    owned = physical(root, directory); owned.mkdir(parents=True, exist_ok=True)
    projection_path = owned/'native-metadata-projection.json'
    base_record = {'schema': SCHEMA, 'metadata_only': True, 'execution_history_authority': False,
                   'source_before': plan['before'], 'tasks': tasks, 'source_completed_labels': completed}
    next_record = {**base_record, 'closed_amendment': summary, 'tasks': [*tasks, child_cid]}
    before_root, after_root = cid(base_record), cid(next_record)
    root_fields = ('repository_root_cid', 'dirty_worktree_root', 'task_source_revision', 'policy_root', 'intent_ir_root',
                   'legal_ir_root', 'security_ir_root', 'program_root', 'capability_catalog_root',
                   'provider_catalog_root', 'usage_policy_root', 'configuration_root')
    roots = PlanAuthorityRoots(repository_id='campaign:' + digest(profile['runtimeRoot']),
        task_source_id='task-source:prepared-phase-metadata',
        **{key: cid({'kind': key, 'admission': summary}) for key in root_fields})
    pop = lambda kind, values=(): PlanPopulationDigest(kind=kind, member_cids=tuple(sorted(values)))
    defaults = dict(roots=roots, request_cid=cid({'request': summary}), scan_receipt_cid=cid({'before': plan['before']}),
        query_plan_cid=cid({'query': 'one closed original-phase gap'}), evidence_bundle_cid=cid(plan['gap']),
        admission_receipt_cid=cid({'policy': 'one per original phase', 'gap': plan['key']}),
        execution_plan_cid=cid({'after': summary['after_sha256']}), goal_population=pop(PopulationKind.RETAINED, goals),
        task_population=pop(PopulationKind.RETAINED, tasks), added_population=pop(PopulationKind.ADDED, tasks),
        superseded_population=pop(PopulationKind.SUPERSEDED), retained_population=pop(PopulationKind.RETAINED),
        deferred_population=pop(PopulationKind.DEFERRED), claimed_population=pop(PopulationKind.CLAIMED),
        completed_population=pop(PopulationKind.COMPLETED, [cid({'logical_task': t}) for t in completed]),
        blocked_population=pop(PopulationKind.BLOCKED), resource_contract=PlanResourceContract(),
        provider_contract=PlanProviderContract(), lease_contract=PlanLeaseContract(), retry_contract=PlanRetryContract(),
        worktree_contract=PlanWorktreeContract(), merge_strategy=PlanMergeStrategy(kind=MergeStrategyKind.SERIAL),
        conflict_contract=PlanConflictContract(predicted_files=tuple(sorted(plan['after']))),
        completion_rule=PlanCompletionRule(authority=CompletionAuthority.VALIDATION_GATE),
        validation_dag=(), event_cursor=cid({'cursor': plan['before']}))
    first = PlanRevision(plan_root_cid=before_root, semantic_revision=1, parent_plan_root='',
                         origin=PlanOrigin.CREATE, delta_cid='', **defaults)
    effects = ('append-one-scoped-remediation', 'amend-pending-parent-dependency-only')
    items = (
        PlanDeltaItem(item_key='add:' + plan['child']['task_id'], operation=PlanDeltaOperation.ADD_TASK,
            target_cid='', expected_target_lifecycle=LifecycleState.PROPOSED, expected_target_spec_revision='',
            before_digest='', after_record_cid=cid(plan['child']), effect_class=DeltaEffectClass.MATERIALIZABLE_NOW,
            rationale='One finite source-only remediation dependency.', expected_effects=(effects[0],)),
        PlanDeltaItem(item_key='dependency:' + plan['parent'], operation=PlanDeltaOperation.REWIRE_UNSTARTED_DEPENDENCY,
            target_cid=parent_cid, expected_target_lifecycle=LifecycleState.UNSTARTED,
            expected_target_spec_revision=cid(plan['original_task']), before_digest=cid(plan['original_task']),
            after_record_cid=cid({**plan['original_task'], 'dependencies': [*plan['original_task'].get('dependencies', []), plan['child']['task_id']]}),
            effect_class=DeltaEffectClass.MATERIALIZABLE_NOW, rationale='Original acceptance/deadline/history unchanged.',
            expected_effects=(effects[1],)),
    )
    delta = PlanDelta(base_plan_root=before_root, base_plan_revision=1, request_cid=defaults['request_cid'], roots=roots,
        items=items, expected_effects=effects, deferred_item_keys=(), claimed_population_digest=cid([]),
        accepted_population_digest=cid(completed), scan_receipt_cid=defaults['scan_receipt_cid'],
        evidence_bundle_cid=defaults['evidence_bundle_cid'], admission_receipt_cid=defaults['admission_receipt_cid'])
    second_values = {**defaults, 'task_population': pop(PopulationKind.RETAINED, [*tasks, child_cid]),
                     'added_population': pop(PopulationKind.ADDED, [child_cid]), 'retained_population': pop(PopulationKind.RETAINED, tasks)}
    second = PlanRevision(plan_root_cid=after_root, semantic_revision=2, parent_plan_root=before_root,
                          origin=PlanOrigin.STEER, delta_cid=delta.delta_cid, **second_values)
    class PreparedMetadataProjection:
        path = projection_path
        def apply_plan_revision(self, *, revision, origin, **unused):
            record = base_record if str(origin).endswith('create') else next_record
            need(revision.plan_root_cid == cid(record), 'native prepared projection identity differs')
            atomic(root, str(self.path.relative_to(root)), wire(record) + b'\n')
            return {'projection_cid': cid(record)}
        def plan_revision_projection_cid(self):
            return cid(parse(read(root, str(self.path.relative_to(root)))))
    projection = PreparedMetadataProjection()
    store = PlanRevisionStore(owned/'native-revisions')
    one = store.apply_authorized(PlanRevisionApplyRequest(revision=first, observed_roots=roots,
        idempotency_key=plan['key'] + ':base', expected_effects=('capture-metadata-base',),
        markdown_source=projection, repository_tree_id=roots.dirty_worktree_root,
        fencing_token=1, lease_id=lease_id))
    two = store.apply_authorized(PlanRevisionApplyRequest(revision=second, observed_roots=roots,
        idempotency_key=plan['key'] + ':amend', expected_effects=effects, delta=delta,
        markdown_source=projection, repository_tree_id=roots.dirty_worktree_root,
        fencing_token=1, lease_id=lease_id, expected_active_plan_root=before_root,
        expected_active_revision_cid=first.revision_cid, base_event_cursor=one.event_cursor,
        records={'closed_campaign_amendment': summary}))
    need(two.committed or two.state.value == 'replayed', 'native closed metadata revision did not commit')
    receipt = {'schema': SCHEMA, 'metadata_only': True, 'execution_history_authority': False,
               'native_receipt': two.to_dict(), 'delta': delta.to_dict(), 'plan_summary': summary}
    name = directory + '/native-metadata-admission.json'
    if physical(root, name).exists():
        prior = parse(read(root, name)); need(prior['delta'] == receipt['delta'], 'native admission replay differs')
        return ref(root, name)
    atomic(root, name, wire(receipt) + b'\n', exclusive=True)
    return ref(root, name)


def _admission_directory(profile, key):
    need(re.fullmatch('[0-9a-f]{64}', key), 'invalid phase gap key')
    return base(profile) + '/admissions/' + key


def _verify_plan(root, profile, plan):
    need(plan.get('schema') == SCHEMA and plan.get('completion_authority') is False
         and plan.get('work_complete') is False, 'invalid phase remediation plan')
    original = plan['original_task']; need(plan['key'] == gap_key(profile, original), 'plan key differs')
    need(plan['child'] == child_task(profile, original, plan['gap']), 'child metadata authority expanded')
    current_spec = parse(check_ref(root, plan['before'][profile['taskSpecPath']]))
    expected = next(t for t in current_spec['tasks'] if t['task_id'] == plan['parent'])
    need(expected == original and qualify_gap(root, profile, original) == plan['gap'], 'gap/source changed before admission')
    # Recompute the exact literal amendment; callers cannot supply arbitrary plan bodies.
    recomputed = propose(root, profile, plan['parent'])
    need(wire(recomputed) == wire(plan), 'canonical plan amendment was changed')



def assert_no_hold(root, profile):
    root = Path(root); runtime = physical(root, profile['runtimeRoot'])
    for directory in (root, runtime, runtime/'state', runtime/'watchdog'):
        for name in ('HOLD', 'OPERATOR_STOP', 'watchdog.disabled', 'hold', 'operator.hold'):
            target = directory/name
            need(not target.exists() and not target.is_symlink(), 'operator/foreign HOLD prevents admission')


def authority_fence(root, profile, callback):
    assert_no_hold(root, profile)
    return callback()


def authenticate_intent(root, profile, directory, intent):
    """Close restart recovery over the exact natively authorized two-file plan."""
    need(intent.get('schema') == SCHEMA and intent.get('completion_authority') is False
         and intent.get('work_complete') is False, 'invalid remediation intent authority')
    original=intent['original_task'];gap=intent['gap'];child=child_task(profile,original,gap)
    need((_final_app_map(parse(read(root, profile['taskSpecPath']))).get(original['task_id']) if _PHASE_MODE.get() == FINAL_MODE else ORIGINAL_APPS.get(original['task_id'])) == original['app_id']
         and intent['key'] == gap_key(profile,original) == gap['key']
         and directory == _admission_directory(profile,intent['key'])
         and intent['child'] == child['task_id'] and intent['child_sha256'] == digest(child), 'restart child identity expanded')
    rows=intent['files']; checkpoint=base(profile)+'/last-admission-projection.json'
    need(type(rows) is list and len(rows)==3
         and {row['path'] for row in rows} == {profile['taskSpecPath'],profile['todoPath'],checkpoint}, 'restart canonical file authority expanded')
    after={}
    for row in rows:
        blob=row['after_blob'];need(physical(root,blob['path']).parent == physical(root,directory), 'restart blob escaped admission')
        raw=check_ref(root,blob)
        need(hashlib.sha256(raw).hexdigest() == row['after_sha256'], 'restart after bytes differ')
        if row['path'] != checkpoint:after[row['path']]=raw.decode('utf-8')
    summary=intent['plan_summary']
    reconstructed={'schema':SCHEMA,'key':intent['key'],'parent':original['task_id'],'child':child,'gap':gap,
        'before':summary['before'],'after':after,'original_task':original,'work_complete':False,'completion_authority':False}
    need(digest(reconstructed)==intent['plan_sha256'] and wire(summary)==wire(plan_summary(reconstructed)), 'restart retained plan identity differs')
    need(all(row['before_sha256']==summary['before'][row['path']]['sha256'] for row in rows if row['path']!=checkpoint), 'restart before identity differs')
    native=parse(check_ref(root,intent['native_admission']))
    need(native.get('schema')==SCHEMA and native.get('metadata_only') is True and native.get('execution_history_authority') is False
         and wire(native.get('plan_summary'))==wire(summary), 'restart lacks closed native metadata authority')
    from ipfs_accelerate_py.agent_supervisor.planning.plan_revision_contracts import PlanDelta
    receipt=native['native_receipt']
    need(receipt.get('state') in {'committed','replayed'} and receipt.get('delta_cid')==PlanDelta.from_dict(native['delta']).delta_cid, 'native revision is not committed')
    cas=directory+'/native-revisions/cas/'+receipt['receipt_cid']
    stored=parse(read(root,cas))
    # Native public API persists the committed authorization independently of
    # our publisher. Replay flags may differ, but its identity/effects may not.
    payload=stored.get('payload',{})
    need(stored.get('cid')==receipt['receipt_cid'] and payload.get('state') in {'committed','replayed'}
         and all(wire(payload.get(key))==wire(receipt.get(key)) for key in
             ('receipt_cid','intent_cid','revision_cid','plan_root_cid','delta_cid','expected_effects','observed_effects')),
         'native authorization receipt differs from its immutable CAS')
    return intent


def _recover_intent(root, profile, directory, *, ensure_authority, fault=lambda point: None):
    intent_name = directory + '/intent.json'; commit_name = directory + '/commit.json'
    if physical(root, commit_name).exists():
        commit = parse(read(root, commit_name)); check_ref(root, commit['intent'])
        return {'state': 'committed', 'child': commit['child'], 'replayed': True}
    intent = authenticate_intent(root,profile,directory,parse(read(root,intent_name)))
    # No restoration: any foreign source/board progress is preserved and refused.
    for item in intent['files']:
        current = physical(root, item['path'])
        observed = hashlib.sha256(read(root, item['path'])).hexdigest() if current.exists() else None
        need(observed in {item['before_sha256'], item['after_sha256']}, 'foreign canonical drift during pending admission')
        check_ref(root, item['after_blob'])
    for item in intent['files']:
        authority_fence(root, profile, ensure_authority)
        current = physical(root, item['path'])
        observed = hashlib.sha256(read(root, item['path'])).hexdigest() if current.exists() else None
        need(observed in {item['before_sha256'], item['after_sha256']}, 'canonical CAS contention')
        if observed != item['after_sha256']:
            atomic(root, item['path'], check_ref(root, item['after_blob']))
        fault('after:' + item['path'])
    authority_fence(root, profile, ensure_authority)
    need(all(ref(root, item['path'])['sha256'] == item['after_sha256'] for item in intent['files']), 'canonical projection changed before commit')
    native = parse(check_ref(root, intent['native_admission']))
    need(native.get('metadata_only') is True and native.get('execution_history_authority') is False,
         'native projection cannot own prior execution history')
    commit = {'schema': SCHEMA, 'intent': ref(root, intent_name), 'child': intent['child'],
              'key': intent['key'], 'native_admission': intent['native_admission'],
              'files': [ref(root, item['path']) for item in intent['files']],
              'work_complete': False, 'completion_authority': False}
    fault('before_commit')
    authority_fence(root, profile, ensure_authority)
    atomic(root, commit_name, wire(commit) + b'\n', exclusive=True)
    return {'state': 'committed', 'child': intent['child'], 'replayed': False}


def publish(root, profile, plan, *, ensure_authority, fault=lambda point: None):
    """One native metadata admission plus CAS publication, never task completion."""
    need(policy_enabled(profile), 'phase remediation is not opted in')
    with locked(root, profile):
        authority_fence(root, profile, ensure_authority); directory = _admission_directory(profile, plan['key'])
        intent_name = directory + '/intent.json'
        if physical(root, intent_name).exists():
            intent = parse(read(root, intent_name)); need(intent['plan_sha256'] == digest(plan), 'duplicate gap has different plan identity')
            return _recover_intent(root, profile, directory, ensure_authority=ensure_authority, fault=fault)
        _verify_plan(root, profile, plan)
        existing = physical(root, base(profile) + '/admissions')
        need(not existing.exists() or (len(list(existing.iterdir())) < MAX_ORIGINALS or physical(root, directory).exists()) and len(list(existing.iterdir())) <= MAX_ORIGINALS, 'finite campaign child limit exhausted')
        authority = authority_fence(root, profile, ensure_authority); need(type(authority) is dict and authority.get('lease_id'), 'physical campaign lease is required')
        native = native_prepare(root, profile, plan, directory, lease_id=authority['lease_id'])
        # Native rollback is confined to its private metadata projection above.
        authority_fence(root, profile, ensure_authority); _verify_plan(root, profile, plan)
        files = []
        for index, (name, text) in enumerate(plan['after'].items()):
            blob = directory + '/after-' + str(index) + '.txt'
            immutable(root, blob, text.encode())
            files.append({'path': name, 'before_sha256': plan['before'][name]['sha256'],
                          'after_sha256': hashlib.sha256(text.encode()).hexdigest(), 'after_blob': ref(root, blob)})
        checkpoint_name = base(profile) + '/last-admission-projection.json'
        checkpoint = {'schema': SCHEMA, 'key': plan['key'], 'canonical_after_sha256': {v['path']:v['after_sha256'] for v in files},
                      'purpose': 'Admission checkpoint, not live board-progress authority.', 'completion_authority': False}
        checkpoint_blob = directory + '/after-hashes.json'
        immutable(root, checkpoint_blob, wire(checkpoint) + b'\n')
        checkpoint_path = physical(root, checkpoint_name)
        files.append({'path': checkpoint_name, 'before_sha256': ref(root, checkpoint_name)['sha256'] if checkpoint_path.exists() else None,
                      'after_sha256': ref(root, checkpoint_blob)['sha256'], 'after_blob': ref(root, checkpoint_blob)})
        for role in ('phase', 'fence'):
            immutable(root, directory + '/original-' + role + '.json', check_ref(root, plan['gap'][role]))
        intent = {'schema': SCHEMA, 'key': plan['key'], 'child': plan['child']['task_id'], 'child_sha256': digest(plan['child']),
                  'plan_sha256': digest(plan), 'plan_summary': plan_summary(plan), 'original_task': plan['original_task'],
                  'gap': plan['gap'], 'files': files, 'native_admission': native,
                  'work_complete': False, 'completion_authority': False}
        atomic(root, intent_name, wire(intent) + b'\n', exclusive=True)
        fault('after_intent')
        return _recover_intent(root, profile, directory, ensure_authority=ensure_authority, fault=fault)


def child_contract(root, profile, spec, task):
    need(task.get('kind') == KIND and not {'semantic_recovery_command', 'recovery_edit_paths'} & set(task),
         'scoped child cannot acquire recovery/recursive authority')
    policy = task.get('phase_remediation', {}); original = policy.get('original_task', {})
    need(policy.get('schema') == SCHEMA and policy.get('max_paid_proposals') == 1
         and type(policy.get('max_paid_proposals')) is int
         and policy.get('max_paid_assessments') == 1 and type(policy.get('max_paid_assessments')) is int
         and policy.get('allow_children') is False and policy.get('allow_recovery') is False
         and task['task_id'] == child_id(original), 'invalid finite child policy')
    current_spec = parse(read(root, profile['taskSpecPath']))
    need(wire(current_spec) == wire(spec), 'canonical task source changed at child admission')
    need(next((item for item in current_spec['tasks'] if item['task_id'] == task['task_id']), None) == task, 'child is not the current canonical task')
    parent = originals(spec).get(original['task_id'])
    need(parent is not None and parent == {**original, 'dependencies': [*original.get('dependencies', []), task['task_id']]},
         'original acceptance/commands/deadlines changed beyond dependency amendment')
    need(task == child_task(profile, original, policy['gap']), 'child task scope changed')
    directory = _admission_directory(profile, policy['gap']['key'])
    commit = parse(read(root, directory + '/commit.json')); intent = parse(check_ref(root, commit['intent']))
    need(commit.get('schema') == SCHEMA and commit.get('child') == task['task_id'] and intent.get('child_sha256') == digest(task),
         'child lacks its exact committed admission')
    check_ref(root, intent['native_admission'])
    if _PHASE_MODE.get() == FINAL_MODE:
        saved = parse(read(root, directory + '/original-phase.json'))
        board = blocks(read(root, profile['todoPath']).decode())
        completed = task['task_id'] in board and re.search(r'^- Status: completed\s*$', board[task['task_id']], re.M)
        if completed:
            current = _validate_saved_final_failure(root, profile, original, saved)
            retained = read(root, directory + '/original-phase.json')
            need(retained == read(root, directory + '/original-fence.json')
                 and hashlib.sha256(retained).hexdigest() == policy['gap']['fence']['sha256'],
                 'completed child saved final fence changed')
        else:
            current = validate_final_failure(root, profile, original, current=False)
            need(ref(root, policy['gap']['fence']['path']) == policy['gap']['fence'], 'pending final failure was rebound')
        need(wire(saved) == wire(current) and current['failed_review'] == policy['gap']['failed_review'],
             'retained final failure was rebound')
        basis, scope = final_source_basis(root, profile, original, spec)
        need(basis == policy['gap']['source_task'] and scope == policy['gap']['source_scope'], 'final source authority changed')
    else:
        from swissknife_visual_functional_phase_budget import _validate, _review
        saved = _validate(parse(read(root, directory + '/original-phase.json')), original)
        current = _validate(parse(read(root, policy['gap']['phase']['path'])), original)
        need(saved['spent'] == current['spent'] == policy['gap']['spent']
             and digest(saved['history']) == digest(current['history']), 'original six-spend history changed')
        _review(root, original, policy['gap']['failed_review'])
    return original, parent, intent


def payment_path(profile, task):
    return profile['runtimeRoot'] + '/tasks/' + task['task_id'] + '/phase-remediation-payments.json'


def payments(root, profile, task):
    name = payment_path(profile, task); claims = []
    for role in ('assessment', 'proposal'):
        claim_name = name + '.' + role + '.claim.json'
        if physical(root, claim_name).exists():
            claim = parse(read(root, claim_name, 65536))
            need(claim.get('role') == role and claim.get('task_id') == task['task_id']
                 and claim.get('completion_authority') is False and claim.get('state') == 'admitted',
                 'immutable payment claim malformed')
            claims.append({key:value for key,value in claim.items() if key != 'task_id'})
    if not physical(root, name).exists():
        return {'schema': SCHEMA, 'task_id': task['task_id'], 'limits': {'assessment': 1, 'proposal': 1},
                'spent': {role:sum(row['role'] == role for row in claims) for role in ('assessment','proposal')},
                'history': claims, 'closed': False, 'completion_authority': False}
    value = parse(read(root, name, 65536))
    need(type(value) is dict and value.get('schema') == SCHEMA and value.get('task_id') == task['task_id']
         and wire(value.get('limits')) == wire({'assessment': 1, 'proposal': 1}) and value.get('completion_authority') is False
         and type(value.get('closed')) is bool and type(value.get('history')) is list and len(value['history']) <= 2
         and set(value.get('spent', {})) == {'assessment', 'proposal'}
         and all(type(x) is int and x in {0, 1} for x in value['spent'].values()), 'single-call journal malformed')
    for role in ('assessment', 'proposal'):
        rows = [item for item in value['history'] if item.get('role') == role]
        originals = [item for item in claims if item['role'] == role]
        need(len(rows) == value['spent'][role] == len(originals), 'payment claim/history/spend mismatch')
        if rows:
            need(all(rows[0].get(key) == originals[0][key] for key in ('admission_id','role','source_contract','provider_admission','deadline_at_ms')),
                 'payment admission identity changed')
    return value


def close_payments(root, profile, task):
    with locked(root, profile):
        value = payments(root, profile, task)
        need(value['history'] and all(row['state'] == 'returned' for row in value['history']), 'unfinished/failed payment cannot close a child')
        value['closed'] = True
        atomic(root, payment_path(profile, task), wire(value) + b'\n')



def child_can_still_write(root, profile, task):
    paid = payments(root, profile, task)
    if paid['closed']: return False
    directory = profile['runtimeRoot']+'/tasks/'+task['task_id']
    if paid['spent']['proposal'] == 1:
        output = directory+'/proposal.json'
        if not physical(root, output).exists(): return False
        from swissknife_visual_functional_llm import validate_model_receipt
        try:
            proposal = parse(read(root, output))
            validate_model_receipt(root, proposal, task_id=task['task_id'], mode='repair', predicted_files=task['edit_paths'])
        except (ValueError, OSError, KeyError, TypeError): return False
        if proposal['response']['decision'] != 'needs_changes' or not proposal['response']['edits']: return False
        intent_name = directory+'/application-intent.json'
        if physical(root, intent_name).exists():
            intent = parse(read(root, intent_name))
            actual = {name: hashlib.sha256(read(root, name, 250000)).hexdigest() if physical(root, name).exists() else None
                      for name in task['edit_paths']}
            if actual == intent['after']: return False
        return True  # A retained positive proposal may still need one exact application.
    original = task['phase_remediation']['original_task']
    stale = source_contract(root, profile, original) != task['phase_remediation']['gap']['source_contract']
    if not stale or paid['spent']['assessment'] == 0: return True
    name = assessment_path(profile, task)
    if physical(root, name).exists():
        value = parse(read(root, name))
        return value.get('decision') != 'pass' and value.get('source_contract') == source_contract(root, profile, original)
    packet_name = directory+'/assessment-intent.json'
    if physical(root, packet_name).exists():
        packet = parse(read(root, packet_name)); report = physical(root, packet['workflow']['path'])
        return (report.parent/'visual-review.json').exists()
    return False  # A consumed unknown refresh cannot pay again or write source.


def source_contract(root, profile, original):
    from swissknife_visual_functional_review_recheck import _source_contract
    return _source_contract(root, profile, original)



def remaining_seconds(root, profile, task):
    name = profile['runtimeRoot']+'/tasks/'+task['task_id']+'/execution-deadline.json'
    now = int(time.time()*1000)
    candidates = [now + 3600*1000]
    for owner in (profile.get('bounds', {}), task['phase_remediation']['original_task'], task):
        for key in ('deadline_at_ms', 'expires_at_ms', 'absolute_expiry_ms'):
            if key in owner:
                value = owner[key]
                need(type(value) is int and value > 0, 'invalid absolute task/campaign expiry')
                candidates.append(value)
    raw = os.environ.get('SVF_CAMPAIGN_DEADLINE_AT_MS')
    if raw:
        need(raw.isdecimal(), 'invalid inherited campaign deadline')
        candidates.append(int(raw))
    from ipfs_accelerate_py.agent_supervisor.rescue.lane_resume import execution_progress_snapshot
    progress = execution_progress_snapshot(physical(root, profile['runtimeRoot']+'/state/lane_resume_attempts.json'), task['task_id'])
    if progress.get('state') in {'running', 'produced'} and type(progress.get('started_at_ms')) is int:
        candidates.append(progress['started_at_ms'] + task['timeout_seconds']*1000)
    with locked(root, profile):
        if physical(root, name).exists():
            value = parse(read(root, name, 65536))
            need(value.get('schema') == SCHEMA and value.get('task_id') == task['task_id']
                 and type(value.get('deadline_at_ms')) is int, 'child deadline malformed')
            deadline = min(value['deadline_at_ms'], *candidates)
            if deadline < value['deadline_at_ms']:
                atomic(root, name, wire({**value,'deadline_at_ms':deadline})+b'\n')
        else:
            existing = payments(root, profile, task)
            claims = [row.get('deadline_at_ms') for row in existing['history']]
            need(all(type(value) is int for value in claims), 'claimed child lost its immutable deadline')
            deadline = min([*candidates, *claims])
            atomic(root, name, wire({'schema':SCHEMA,'task_id':task['task_id'],
                'deadline_at_ms':deadline,'envelope_seconds':3600,'completion_authority':False})+b'\n', exclusive=True)
    need(deadline > now, 'finite child absolute deadline exhausted')
    return max(0, (deadline-now)//1000)


def validate_admission(root, profile, task, role, admission):
    import uuid
    keys = {'schema','output_path','invocation_id','task_id','mode','provider','model','attempt_receipt_path',
            'source_contract_sha256','prompt_sha256','router_source_sha256','input_files','screenshots',
            'timeout_seconds','model_context_bytes','max_output_tokens','max_turns'}
    need(type(admission) is dict and set(admission) == keys
         and admission['schema'] == 'swissknife.visual-functional-provider-admission.v1', 'actual provider admission metadata required')
    identity = uuid.UUID(admission['invocation_id'])
    need(str(identity) == admission['invocation_id'] and identity.version == 4
         and admission['provider'] == 'grok_cli' and admission['model'] == 'grok-4.7', 'payment route/invocation differs')
    expected_task = task['task_id'] if role in {'proposal','producer_repair'} else task['phase_remediation']['original_task']['task_id']
    need(admission['task_id'] == expected_task and admission['mode'] == ('repair' if role in {'proposal','producer_repair'} else 'review'), 'payment role/task/mode differs')
    directory = physical(root, profile['runtimeRoot']+'/tasks/'+expected_task)
    output = physical(root, admission['output_path'])
    need(output.is_relative_to(directory) and output.name == ('producer-repair-proposal.json' if role == 'producer_repair' else 'proposal.json' if role == 'proposal' else 'visual-review.json'), 'payment output escaped its role')
    if role in {'proposal','producer_repair'}: need(output.parent == directory, 'proposal output path differs')
    archive = physical(root, admission['attempt_receipt_path'])
    need(archive == output.parent/'model-invocations'/(output.stem+'-'+str(identity)+'.json'), 'payment immutable receipt path differs')
    need(all(type(admission[key]) is str and re.fullmatch('[0-9a-f]{64}',admission[key]) for key in
             ('source_contract_sha256','prompt_sha256','router_source_sha256')), 'payment invocation hashes missing')
    need(type(admission['timeout_seconds']) is int and 0 < admission['timeout_seconds'] <= 600
         and all(type(admission[key]) is int and admission[key] > 0 for key in ('model_context_bytes','max_output_tokens','max_turns')),
         'payment call bounds expanded')
    for group, limit in (('input_files',64),('screenshots',16)):
        need(type(admission[group]) is list and len(admission[group]) <= limit, 'payment input bound')
        for record in admission[group]:
            need(type(record) is dict and type(record.get('size_bytes')) is int, 'payment input record malformed')
            raw = read(root, record['path'], 16777216)
            need(len(raw) == record['size_bytes'] and hashlib.sha256(raw).hexdigest() == record['sha256'], 'payment input changed')
    if role == 'assessment': need(len(admission['screenshots']) == 2, 'assessment requires both exact original viewports')
    return admission


def admit_payment(root, profile, spec, task, role, admission):
    """Only the real compiler callback may issue the irreversible one-call claim."""
    need(policy_enabled(profile) and role in {'assessment','proposal'}, 'unknown/disabled child payment role')
    validate_admission(root,profile,task,role,admission)
    remaining = remaining_seconds(root,profile,task)
    need(remaining >= admission['timeout_seconds'] + 5, 'finite child deadline cannot contain this provider call')
    original, parent, _ = child_contract(root, profile, spec, task)
    current = source_contract(root, profile, original); stale = current != task['phase_remediation']['gap']['source_contract']
    if role == 'assessment': need(stale, 'readonly refresh is reserved for stale evidence')
    elif stale:
        assessment = load_assessment(root, profile, spec, task)
        need(assessment is not None and assessment['decision'] != 'pass', 'stale evidence requires current genuine negative assessment')
    assert_no_hold(root,profile)
    with locked(root, profile):
        value = payments(root, profile, task)
        need(value['closed'] is False, 'child payment outcome is already closed')
        need(value['spent'][role] == 0, 'finite ' + role + ' allowance exhausted; no refund or new identity')
        identity = admission['invocation_id']; value['spent'][role] = 1
        deadline = parse(read(root, profile['runtimeRoot']+'/tasks/'+task['task_id']+'/execution-deadline.json'))['deadline_at_ms']
        row = {'admission_id':identity,'role':role,'state':'admitted','source_contract':current,
               'provider_admission':admission,'deadline_at_ms':deadline,'completion_authority':False}
        atomic(root, payment_path(profile, task)+'.'+role+'.claim.json', wire({**row,'task_id':task['task_id']})+b'\n', exclusive=True)
        value['history'].append(row)
        atomic(root, payment_path(profile, task), wire(value)+b'\n')
        return identity


def payment_receipt(root, row, receipt):
    value = parse(check_ref(root,receipt)); admission = row['provider_admission']
    need(all(wire(value.get(key)) == wire(admission[key]) for key in admission
             if key not in {'schema','output_path'}), 'payment receipt is not its exact admitted invocation')
    need(receipt['path'] in {admission['output_path'],admission['attempt_receipt_path']}, 'payment receipt escaped immutable invocation')
    return value


def finish_payment(root, profile, task, identity, *, receipt=None, error_type=None):
    with locked(root, profile):
        value = payments(root, profile, task)
        rows = [row for row in value['history'] if row['admission_id'] == identity]
        need(len(rows) == 1 and rows[0]['state'] == 'admitted', 'payment admission unknown or already finished')
        if receipt is not None: payment_receipt(root,rows[0],receipt)
        rows[0]['state'] = 'failed' if error_type else 'returned'
        if receipt is not None: rows[0]['receipt'] = receipt
        if error_type: rows[0]['error_type'] = str(error_type)[:80]
        atomic(root, payment_path(profile, task), wire(value)+b'\n')


def recover_payment(root, profile, task, role, output):
    """Replay one exact archived invocation, never scan or dispatch a second call."""
    calls = payments(root,profile,task)
    if calls['spent'][role] == 0: return False
    row = next(row for row in calls['history'] if row['role'] == role)
    admission = row['provider_admission']
    need(str(Path(output).relative_to(root)) == admission['output_path'], 'payment replay output differs')
    if row['state'] == 'failed': raise RemediationRefusal('single '+role+' already failed; no retry/refund')
    archive = admission['attempt_receipt_path']
    need(physical(root,archive).exists(), 'single '+role+' has no retained exact invocation outcome; wait or inspect')
    value = payment_receipt(root,row,ref(root,archive))
    need(value.get('success') is True, 'single '+role+' retained a failed native call; no retry')
    from swissknife_visual_functional_llm import validate_model_receipt
    validate_model_receipt(root,value,task_id=admission['task_id'],mode=admission['mode'],
                           require_visual=role=='assessment',predicted_files=task['edit_paths'] if role=='proposal' else [])
    target = admission['output_path']
    if physical(root,target).exists(): need(parse(read(root,target)) == value, 'payment output differs from exact invocation')
    else: atomic(root,target,read(root,archive),exclusive=True)
    if row['state'] == 'admitted': finish_payment(root,profile,task,row['admission_id'],receipt=ref(root,target))
    else: need(row.get('receipt') == ref(root,target), 'returned payment receipt changed')
    return True


def assessment_path(profile, task):
    return profile['runtimeRoot'] + '/tasks/' + task['task_id'] + '/stale-evidence-assessment.json'


def record_assessment(root, profile, spec, task, report, review):
    original, parent, _ = child_contract(root, profile, spec, task)
    from swissknife_visual_functional_worker import validate_workflow
    from swissknife_visual_functional_final_coverage import binding, review_join
    validated = validate_workflow(profile, parent, Path(report))
    need(validated is not None, 'assessment requires independent V2 producer')
    raw = parse(read(root, str(Path(review).relative_to(root))))
    joined = review_join(root, profile, parent, binding(parent, validated), Path(review),
                         require_pass=raw['response']['decision'] == 'pass')
    calls = payments(root, profile, task)
    need(calls['spent']['assessment'] == 1 and any(row['role'] == 'assessment'
         and row['state'] == 'returned' and row.get('receipt', {}).get('sha256') == ref(root, str(Path(review).relative_to(root)))['sha256']
         for row in calls['history']), 'assessment has no consumed genuine payment admission')
    value = {'schema': SCHEMA, 'child': task['task_id'], 'original_task_id': original['task_id'],
             'workflow': ref(root, str(Path(report).relative_to(root))), 'review': ref(root, str(Path(review).relative_to(root))),
             'review_join': joined, 'evidence': binding(parent, validated), 'source_contract': source_contract(root, profile, original),
             'decision': raw['response']['decision'], 'completion_authority': False}
    atomic(root, assessment_path(profile, task), wire(value) + b'\n', exclusive=True)
    return value


def load_assessment(root, profile, spec, task, *, current=True):
    name = assessment_path(profile, task)
    if not physical(root, name).exists(): return None
    value = parse(read(root, name))
    need(value.get('schema') == SCHEMA and value.get('child') == task['task_id']
         and value.get('completion_authority') is False, 'assessment identity changed')
    original, parent, _ = child_contract(root, profile, spec, task)
    if current:
        need(value.get('source_contract') == source_contract(root, profile, original), 'assessment source is stale')
    from swissknife_visual_functional_worker import validate_workflow
    from swissknife_visual_functional_final_coverage import binding, review_join
    report = physical(root, value['workflow']['path']); review = physical(root, value['review']['path'])
    check_ref(root, value['workflow']); check_ref(root, value['review'])
    expected = value['evidence']
    if current:
        validated = validate_workflow(profile, parent, report)
        need(expected == binding(parent, validated), 'assessment functional evidence changed')
    need(value['review_join'] == review_join(root, profile, parent, expected, review, require_pass=value['decision'] == 'pass'),
         'assessment is detached from original task/report/review')
    return value


def no_hold_or_activity(root, profile):
    """Observe only; no process signaling, launching, or control commands."""
    root = Path(root); assert_no_hold(root, profile)
    controller_groups = None
    def groups(name):
        raw = name.read_bytes()
        need(0 < len(raw) <= 65536, 'activity cgroup identity is unavailable')
        result = {}
        for line in raw.decode().splitlines():
            fields = line.split(':', 2)
            need(len(fields) == 3 and fields[0].isdigit() and fields[2].startswith('/')
                 and '..' not in fields[2].split('/'), 'activity cgroup identity is malformed')
            key = (fields[0], fields[1]); need(key not in result, 'activity cgroup identity is ambiguous')
            result[key] = fields[2].rstrip('/') or '/'
        need(result, 'activity cgroup identity is unavailable')
        return result
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid(): continue
        try:
            if process.stat().st_uid != os.getuid(): continue
            argv = [x.decode(errors='replace') for x in (process/'cmdline').read_bytes().split(b'\0') if x]
            active = any('grok' in Path(x).name.lower() or 'chrom' in Path(x).name.lower()
                         or x.endswith('/'+WORKER) or x == WORKER for x in argv[:4])
            if not active: continue
            if controller_groups is None:
                try: controller_groups = groups(Path('/proc/self/cgroup'))
                except (FileNotFoundError, ProcessLookupError, PermissionError):
                    raise RemediationRefusal('current supervisor cgroup identity is unavailable') from None
            candidate_groups = groups(process/'cgroup')
            need(set(candidate_groups) == set(controller_groups), 'activity cgroup identity cannot be compared')
            if not all(candidate_groups[key] == own or candidate_groups[key].startswith(own.rstrip('/') + '/')
                       for key, own in controller_groups.items()): continue
            cwd = (process/'cwd').resolve()
            if cwd == root or any(str(root) in x for x in argv):
                raise RemediationRefusal('active campaign worker/browser/model prevents admission')
        except (FileNotFoundError, ProcessLookupError): continue
        except PermissionError:
            raise RemediationRefusal('activity admission cannot inspect possible active process pid=' + process.name) from None


def between_cycles(root, profile, *, ensure_authority):
    """Opt-in safe-boundary adapter. No claimed/running command may call it."""
    if not policy_enabled(profile): return {'state':'idle','disabled':True}
    no_hold_or_activity(root, profile); ensure_authority()
    store = physical(root, base(profile)+'/admissions')
    if store.exists():
        need(store.is_dir() and len(list(store.iterdir())) <= MAX_ORIGINALS, 'admission directory bound')
        for directory in sorted(store.iterdir()):
            if (directory/'intent.json').exists() and not (directory/'commit.json').exists():
                with locked(root, profile):
                    return _recover_intent(root, profile, str(directory.relative_to(root)), ensure_authority=ensure_authority)
    spec = parse(read(root, profile['taskSpecPath'])); eligible = originals(spec)
    refusals = []
    for identity, task in eligible.items():
        if child_id(task) in {t['task_id'] for t in spec['tasks']}: continue
        journal = physical(root, profile['runtimeRoot']+'/tasks/'+identity+('/failed-final-review-source-fence.json' if _PHASE_MODE.get() == FINAL_MODE else '/required-phase-repair-budget.json'))
        if not journal.exists(): continue
        try:
            phase = parse(read(root, str(journal.relative_to(root))))
            if _PHASE_MODE.get() != FINAL_MODE and phase.get('state') != 'exhausted': continue
            plan = propose(root, profile, identity)
        except (ValueError, OSError, KeyError, TypeError) as error:
            refusals.append({'task_id':identity,'reason':' '.join(str(error).split())[:240],
                             'completion_authority':False})
            continue
        return publish(root, profile, plan, ensure_authority=ensure_authority)
    if refusals:
        atomic(root, base(profile)+'/gap-refusals.json', wire({'schema':SCHEMA,'scope_refusals':refusals,
            'observation_only':True,'completion_authority':False})+b'\n')
    return {'state': 'idle', 'completion_authority': False}



def checked_application(root, profile, task, application, proposal):
    need(set(application.get('before', {})) == set(application.get('after', {})) == set(task['edit_paths'])
         and set(application.get('original_sources', {})) == set(task['edit_paths']), 'application source closure differs')
    original_bytes = {}
    for name, record in application['original_sources'].items():
        target = physical(root, record['path'])
        need(target.is_relative_to(physical(root, profile['runtimeRoot']+'/tasks/'+task['task_id'])), 'original source escaped child')
        raw = read(root, record['path'], 250000, allow_empty=True)
        need(len(raw) == record['bytes'] and hashlib.sha256(raw).hexdigest() == record['sha256']
             and (hashlib.sha256(raw).hexdigest() if raw else None) == application['before'][name], 'original source was rebound')
        original_bytes[name] = raw
    if proposal['response']['edits']:
        from swissknife_visual_functional_recovery import proposal_after
        expected = proposal_after(root, proposal, task['edit_paths'], application['before'], original_bytes)
    else: expected = application['before']
    need(expected == application['after'], 'application is not the exact native proposal')
    return expected


def recoverable_owned_source(root, profile, task_id, name):
    """Pure preflight predicate for an authenticated own interrupted application."""
    spec = parse(read(root,profile['taskSpecPath']))
    task = next((t for t in spec['tasks'] if t['task_id'] == task_id),None)
    if task is None or task.get('kind') != KIND or name not in task['edit_paths']: return False
    child_contract(root,profile,spec,task)
    directory = profile['runtimeRoot']+'/tasks/'+task_id
    packet = directory+'/application-intent.json'
    if not physical(root,packet).exists(): return False
    application = parse(read(root,packet))
    proposal = parse(check_ref(root,application['proposal']))
    from swissknife_visual_functional_llm import validate_model_receipt
    validate_model_receipt(root,proposal,task_id=task_id,mode='repair',predicted_files=task['edit_paths'])
    need(proposal['response']['decision'] == 'needs_changes' and proposal['response']['edits'], 'interrupted source proposal is not a real change')
    paid = payments(root,profile,task)
    need(any(row['role']=='proposal' and row['state']=='returned' and row.get('receipt')==application['proposal']
             for row in paid['history']), 'interrupted source has no exact paid proposal')
    checked_application(root,profile,task,application,proposal)
    ledger = parse(read(root,profile['runtimeRoot']+'/owned-source-hashes.json'))
    for path in task['edit_paths']:
        actual = hashlib.sha256(read(root,path,250000)).hexdigest() if physical(root,path).exists() else None
        need(actual in {application['before'][path],application['after'][path]}
             and ledger.get(path) in {application['before'][path],application['after'][path]}, 'foreign interrupted source/ledger drift')
    return True


def execute_child(root, profile_path, profile, spec, task, *, model, workflow, validate_workflow,
                  apply_edits, ensure_lease, check_owned, remember_owned):
    """No retry loop: one refresh and one proposal at most, then source proof."""
    need(policy_enabled(profile), 'phase remediation is not opted in')
    original, parent, _ = child_contract(root, profile, spec, task)
    original_workflow = workflow
    def workflow(profile, parent, directory):
        remaining = remaining_seconds(root, profile, task)
        need(remaining > 0, 'no child time remains for original producer')
        return original_workflow(profile, parent, directory, timeout_seconds=min(1200, remaining))
    directory = profile['runtimeRoot'] + '/tasks/' + task['task_id']
    physical(root, directory).mkdir(parents=True, exist_ok=True)
    prior_proposal = physical(root, directory + '/proposal.json').exists()
    if not prior_proposal: check_owned(profile, task['edit_paths'])
    assessment = load_assessment(root, profile, spec, task, current=not prior_proposal)
    stale = source_contract(root, profile, original) != task['phase_remediation']['gap']['source_contract']
    if stale and assessment is None and not prior_proposal:
        refresh_intent = directory + '/assessment-intent.json'
        if physical(root, refresh_intent).exists():
            packet = parse(read(root, refresh_intent))
            report = physical(root, packet['workflow']['path']); check_ref(root, packet['workflow'])
            checks = packet['checks']; validated = validate_workflow(profile, parent, report)
        else:
            need(payments(root, profile, task)['spent']['assessment'] == 0, 'assessment outcome unknown; cannot dispatch again')
            files, checks = workflow(profile, parent, physical(root, profile['runtimeRoot']+'/tasks/'+parent['task_id']+'/verification'))
            report = files[0]; validated = validate_workflow(profile, parent, report)
            need(validated is not None, 'refresh requires fresh original V2 producer')
            packet = {'schema': SCHEMA, 'workflow': ref(root, str(report.relative_to(root))), 'checks': checks,
                      'source_contract': source_contract(root, profile, original)}
            atomic(root, refresh_intent, wire(packet)+b'\n', exclusive=True)
        review = report.parent/'visual-review.json'
        recover_payment(root,profile,task,'assessment',review)
        if not review.exists():
            need(payments(root, profile, task)['spent']['assessment'] == 0, 'refresh already spent without retained outcome')
            model(profile_path, parent, 'review', [profile['appContractPath'], str(report.relative_to(root))],
                  [image['path'] for image in validated['images']], review, remediation_payment=(task, 'assessment'))
        assessment = record_assessment(root, profile, spec, task, report, review)
    proposal = None; application = None
    obsolete = assessment is not None and assessment['decision'] == 'pass'
    if not obsolete:
        output_name = directory + '/proposal.json'; output = physical(root, output_name)
        recover_payment(root,profile,task,'proposal',output)
        if not output.exists():
            need(payments(root, profile, task)['spent']['proposal'] == 0, 'proposal outcome unknown; cannot dispatch again')
            failed_review = assessment['review'] if assessment else task['phase_remediation']['gap']['failed_review']
            model(profile_path, task, 'repair', [failed_review['path'], *task['edit_paths']], [], output,
                  remediation_payment=(task, 'proposal'))
        from swissknife_visual_functional_llm import validate_model_receipt
        proposal = parse(read(root, output_name))
        validate_model_receipt(root, proposal, task_id=task['task_id'], mode='repair', predicted_files=task['edit_paths'])
        need(proposal['response']['decision'] == 'needs_changes' and proposal['response']['edits'],
             'unchanged proposal cannot complete source remediation without positive visual refresh')
        paid = payments(root, profile, task)
        need(paid['spent']['proposal'] == 1 and any(row['role']=='proposal' and row['state']=='returned'
             and row.get('receipt') == ref(root, output_name) for row in paid['history']),
             'native proposal lacks its immutable single-call admission/outcome')
        application_name = directory + '/application.json'
        intent_name = directory + '/application-intent.json'
        if physical(root, intent_name).exists():
            application = parse(read(root, intent_name)); check_ref(root, application['proposal'])
            need(application['proposal'] == ref(root, output_name), 'application was rebound to another proposal')
        else:
            ensure_lease(profile); check_owned(profile, task['edit_paths'])
            before = {}; originals_bytes = {}; retained = {}
            for index, name in enumerate(task['edit_paths']):
                raw = read(root, name, 250000) if physical(root, name).exists() else b''
                before[name] = hashlib.sha256(raw).hexdigest() if raw else None; originals_bytes[name] = raw
                saved = directory + '/original-source-' + str(index) + '.txt'
                # Empty new-file sources are valid edit baselines, not proof artifacts.
                atomic(root, saved, raw, exclusive=True)
                retained[name] = {'path': saved, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
            if proposal['response']['edits']:
                from swissknife_visual_functional_recovery import proposal_after
                expected = proposal_after(root, proposal, task['edit_paths'], before, originals_bytes)
            else:
                expected = before
            application = {'schema': SCHEMA, 'proposal': ref(root, output_name), 'before': before,
                           'after': expected, 'original_sources': retained, 'completion_authority': False}
            atomic(root, intent_name, wire(application)+b'\n', exclusive=True)
        actual = {name: hashlib.sha256(read(root, name, 250000)).hexdigest() if physical(root, name).exists() else None for name in task['edit_paths']}
        checked_application(root, profile, task, application, proposal)
        need(all(actual[name] in {application['before'][name], application['after'][name]} for name in task['edit_paths']),
             'foreign app drift during source remediation')
        pending = [name for name in task['edit_paths'] if actual[name] != application['after'][name]]
        ledger_name = profile['runtimeRoot'] + '/owned-source-hashes.json'
        if physical(root, ledger_name).exists():
            ledger = parse(read(root, ledger_name))
            need(all(ledger.get(name) in {application['before'][name], application['after'][name]}
                     for name in task['edit_paths']), 'foreign ownership ledger drift before source replay')
        ensure_lease(profile)
        if pending:
            check_owned(profile, pending)
            remaining_edits = [edit for edit in proposal['response']['edits'] if edit['path'] in pending]
            apply_edits(root, remaining_edits, pending, lease_check=lambda:ensure_lease(profile))
        after = {name: hashlib.sha256(read(root, name, 250000)).hexdigest() if physical(root, name).exists() else None for name in task['edit_paths']}
        need(after == application['after'], 'application differs from exact retained native proposal')
        # Recover only exact authenticated own source bytes, never broad dirty adoption.
        ledger_name = profile['runtimeRoot'] + '/owned-source-hashes.json'
        if physical(root, ledger_name).exists():
            ledger = parse(read(root, ledger_name))
            need(all(ledger.get(name) in {application['before'][name], after[name]}
                     for name in task['edit_paths']), 'foreign ownership ledger drift')
        changed = [name for name in task['edit_paths'] if application['before'][name] != after[name]]
        if changed: remember_owned(profile, changed)
        atomic(root, application_name, wire(application)+b'\n')
    # This is a fresh source-only producer, never the original positive review.
    files, checks = workflow(profile, parent, physical(root, profile['runtimeRoot']+'/tasks/'+parent['task_id']+'/verification'))
    report = files[0]; validated = validate_workflow(profile, parent, report)
    need(validated is not None, 'source-only child requires fresh independent V2 workflow')
    if obsolete:
        # A functional pass alone was never enough: load_assessment proves the
        # already consumed, current positive native original-task Grok join.
        need(load_assessment(root, profile, spec, task)['decision'] == 'pass', 'obsolete child lacks positive native refresh')
    close_payments(root, profile, task)
    value = {'schema': SCHEMA, 'task_id': task['task_id'], 'scope': 'source_remediation_only',
             'original_task_id': parent['task_id'], 'original_task_sha256': digest(parent),
             'workflow': ref(root, str(report.relative_to(root))), 'workflow_checks': checks,
             'proposal': ref(root, directory+'/proposal.json') if proposal else None,
             'application': ref(root, directory+'/application.json') if application else None,
             'assessment': ref(root, assessment_path(profile, task)) if assessment else None,
             'obsolete_gap': obsolete, 'payments': ref(root, payment_path(profile, task)),
             'completion_authority': False, 'work_complete': False}
    name = directory + '/source-only-result.json'
    atomic(root, name, wire(value)+b'\n')
    return [physical(root, name), *([physical(root, directory+'/proposal.json')] if proposal else [])], checks, {
        'source_only_remediation': ref(root, name), 'original_acceptance_downstream': True,
        'paid_limits': {'assessment': 1, 'proposal': 1}}


def validate_child_result(root, profile, spec, task, receipt, *, validate_workflow):
    original, parent, _ = child_contract(root, profile, spec, task)
    value = parse(check_ref(root, receipt['detail']['source_only_remediation']))
    need(value.get('schema') == SCHEMA and value.get('task_id') == task['task_id']
         and value.get('scope') == 'source_remediation_only' and value.get('original_task_id') == parent['task_id']
         and value.get('original_task_sha256') == digest(parent)
         and value.get('work_complete') is False and value.get('completion_authority') is False,
         'child result cannot grant original completion')
    report = physical(root, value['workflow']['path']); check_ref(root, value['workflow'])
    need(validate_workflow(profile, parent, report) is not None, 'child lacks independently validated current original V2 producer')
    need(receipt.get('checks') == value['workflow_checks'] and len(receipt['checks']) == 1
         and type(receipt['checks'][0].get('exit_code')) is int and receipt['checks'][0]['exit_code'] == 0
         and receipt['checks'][0].get('argv') == ['node','swissknife/scripts/run-visual-functional-workflow.mjs',
             '--app',parent['app_id'],'--contracts',profile['appContractPath'],'--output-dir',str(report.parent),'--independent-viewports'],
         'child did not retain its fresh original producer command')
    paid = payments(root, profile, task)
    need(paid['closed'] is True and check_ref(root, value['payments']) == read(root, payment_path(profile, task)), 'child payment outcome is not sealed')
    if value['obsolete_gap']:
        assessment = load_assessment(root, profile, spec, task)
        need(assessment is not None and assessment['decision'] == 'pass' and value['proposal'] is None
             and paid['spent']['assessment'] == 1 and paid['spent']['proposal'] == 0,
             'obsolete child requires positive native refresh, never producer flags alone')
    else:
        need(paid['spent']['proposal'] == 1 and value['proposal'] is not None and value['application'] is not None,
             'source remediation lacks its single paid proposal')
        from swissknife_visual_functional_llm import validate_model_receipt
        proposal = parse(check_ref(root, value['proposal']))
        validate_model_receipt(root, proposal, task_id=task['task_id'], mode='repair', predicted_files=task['edit_paths'])
        need(proposal['response']['decision'] == 'needs_changes' and proposal['response']['edits'], 'child source proposal lacks required native source edits')
        application = parse(check_ref(root, value['application']))
        need(application['proposal'] == value['proposal'], 'application model identity differs')
        checked_application(root, profile, task, application, proposal)
        need(all((hashlib.sha256(read(root, name, 250000)).hexdigest() if physical(root, name).exists() else None) == value
                 for name, value in application['after'].items()), 'child applied source changed')
    return value


@contextmanager
def _mode(mode):
    token = _PHASE_MODE.set(mode)
    try: yield
    finally: _PHASE_MODE.reset(token)


def _task_mode(task):
    policy = task.get('phase_remediation', {})
    if task.get('kind') == 'final-app-verify' or policy.get('mode') == FINAL_MODE:
        return FINAL_MODE
    need('mode' not in policy, 'unknown finite child mode')
    return 'original'


def finals(spec):
    verify = {t['task_id']:t['app_id'] for t in spec['tasks'] if t.get('kind') == 'verify' and t.get('app_id')}
    need(verify == ORIGINAL_APPS, 'original source allowlist changed')
    tasks = [t for t in spec['tasks'] if t.get('kind') == 'final-app-verify']
    need(len(tasks) == 45 and {t['task_id'] for t in tasks} == FINAL_IDS
         and {t.get('app_id') for t in tasks} == set(ORIGINAL_APPS.values()), 'finite final45 allowlist changed')
    for task in tasks:
        need(task.get('checks') == [] and task.get('edit_paths') == []
             and not {'semantic_recovery_command','recovery_edit_paths'} & set(task)
             and verify.get(task.get('original_verify_task')) == task.get('app_id')
             and set(verify) | {'SVF-043','SVF-044'} <= set(task.get('dependencies', [])), 'final readonly/acceptance authority changed')
    return {t['task_id']:t for t in tasks}


def _final_app_map(spec):
    return {identity:task['app_id'] for identity,task in finals(spec).items()}


def final_source_basis(root, profile, task, spec=None):
    spec = spec or parse(read(root, profile['taskSpecPath']))
    need(task['task_id'] in finals(spec), 'final is outside finite allowlist')
    basis = next((t for t in spec['tasks'] if t['task_id'] == task['original_verify_task']), None)
    need(basis is not None and basis.get('kind') == 'verify' and basis.get('app_id') == task['app_id'], 'same-app original source scope is missing')
    app = next((a for a in parse(read(root, profile['appContractPath']))['apps'] if a['app_id'] == task['app_id']), None)
    need(app is not None, 'canonical app source contract missing')
    scenario = 'swissknife/test/e2e/functional-workflows/' + task['app_id'] + '.json'
    canonical = {'swissknife/' + name for name in app['source_paths']} | {scenario}
    registration = parse(read(root, 'config/swissknife_visual_functional_foundation_owners.json'))
    protected = set(registration['protected_sha256'])
    allowed = [name for name in basis.get('edit_paths', []) if name in canonical and name not in protected
               and (name == scenario or name.startswith('swissknife/web/js/apps/') or name.startswith('swissknife/web/css/'))]
    need(allowed and len(allowed) == len(set(allowed))
         and all(name == scenario or not {'test','tests','fixtures','.git'}.intersection(Path(name).parts) for name in allowed),
         'final child has no bounded nonprotected app/scenario scope')
    return basis, allowed


def validate_final_failure(root, profile, task, *, current=True):
    from swissknife_visual_functional_final_coverage import FAILURE_SCHEMA, task_identity, review_join, _review_identity
    need(task.get('kind') == 'final-app-verify' and task['task_id'] in FINAL_IDS, 'not an allowed final review')
    name = profile['runtimeRoot'] + '/tasks/' + task['task_id'] + '/failed-final-review-source-fence.json'
    value = parse(read(root, name))
    need(type(value) is dict and set(value) == {'schema','task_id','app_id','task_contract','identity','evidence','failed_review','work_complete','completion_authority'}
         and value['schema'] == FAILURE_SCHEMA and value['task_id'] == task['task_id'] and value['app_id'] == task['app_id']
         and value['work_complete'] is False and value['completion_authority'] is False
         and value['task_contract'] == {k:v for k,v in task.items() if k != 'status'}
         and value['identity']['task_semantics_sha256'] == task_identity(task), 'genuine final failed-review fence differs')
    review_path = physical(root, value['failed_review']['path']); check_ref(root, value['failed_review'])
    need(review_path.is_relative_to(physical(root, profile['runtimeRoot']+'/tasks/'+task['task_id']+'/verification')), 'failed final review escaped owner')
    review = parse(read(root, value['failed_review']['path']))
    need(review.get('task_id') == task['task_id'] and review.get('mode') == 'review'
         and review.get('provider') == 'grok_cli' and review.get('model') == 'grok-4.7'
         and review.get('success') is True and review.get('response',{}).get('decision') == 'needs_changes', 'real negative pinned final review required')
    review_join(root, profile, task, value['evidence'], review_path, require_pass=False)
    if current:
        need(value['identity'] == _review_identity(root, profile, task), 'stale final gap: rerun fresh readonly verification first')
        _validate_current_failed_phase(root, profile, task, review_path)
    return value


def qualify_final_gap(root, profile, task):
    need(final_policy_enabled(profile), 'final remediation is not explicitly opted in')
    fence = validate_final_failure(root, profile, task)
    basis, scope = final_source_basis(root, profile, task)
    name = profile['runtimeRoot']+'/tasks/'+task['task_id']+'/failed-final-review-source-fence.json'
    review = parse(check_ref(root, fence['failed_review']))
    return {'key':gap_key(profile, task), 'mode':FINAL_MODE, 'phase':ref(root,name), 'fence':ref(root,name),
            'failed_review':fence['failed_review'], 'source_contract':source_contract(root,profile,task),
            'review_invocation_id':review['invocation_id'], 'source_task':basis, 'source_scope':scope}


def _task_scoped(function, index):
    argument_name = function.__code__.co_varnames[index]
    @wraps(function)
    def call(*args, **kwargs):
        task = args[index] if len(args) > index else kwargs[argument_name]
        with _mode(_task_mode(task)): return function(*args, **kwargs)
    return call


for _name, _index in {'child_id':0, 'child_task':1, 'qualify_gap':2, 'payment_path':1, 'payments':2,
    'close_payments':2, 'child_can_still_write':2, 'remaining_seconds':2, 'validate_admission':2,
    'admit_payment':3, 'finish_payment':2, 'recover_payment':2, 'record_assessment':3,
    'load_assessment':3, 'child_contract':3, 'checked_application':2, 'execute_child':4,
    'validate_child_result':3}.items():
    globals()[_name] = _task_scoped(globals()[_name], _index)

_propose_one = propose
@wraps(_propose_one)
def propose(root, profile, task_id):
    with _mode(FINAL_MODE if task_id in FINAL_IDS else 'original'):
        return _propose_one(root, profile, task_id)

_publish_one = publish
@wraps(_publish_one)
def publish(root, profile, plan, **kwargs):
    with _mode(_task_mode(plan['child'])): return _publish_one(root, profile, plan, **kwargs)

_pending_one = pending_publications
def pending_publications(root, profile):
    if _PHASE_MODE.get() is not None: return _pending_one(root, profile)
    result = []
    for mode in ('original', FINAL_MODE):
        with _mode(mode): result.extend(_pending_one(root, profile))
    return result

_recover_one = recover_pending
def recover_pending(root, profile, **kwargs):
    if _PHASE_MODE.get() is not None: return _recover_one(root, profile, **kwargs)
    results = []
    for mode in ('original', FINAL_MODE):
        with _mode(mode): results.append(_recover_one(root, profile, **kwargs))
    return {'state':'recovered' if any(r['recovered'] for r in results) else 'idle',
            'recovered':sum(r['recovered'] for r in results)}

_between_one = between_cycles
def between_cycles(root, profile, **kwargs):
    if not final_policy_enabled(profile):
        with _mode('original'): return _between_one(root, profile, **kwargs)
    for mode in ('original', FINAL_MODE):
        with _mode(mode):
            if not policy_enabled(profile): continue
            result = _between_one(root, profile, **kwargs)
        if result.get('state') != 'idle': return result
    return {'state':'idle','completion_authority':False}

_owned_one = recoverable_owned_source
@wraps(_owned_one)
def recoverable_owned_source(root, profile, task_id, name):
    mode = FINAL_MODE if task_id in {'SVF-FINAL-R'+str(i) for i in range(1001,1046)} else 'original'
    with _mode(mode): return _owned_one(root, profile, task_id, name)


FEEDBACK_SCHEMA = 'swissknife.producer-feedback.v1'

def _feedback_directory(profile, task):
    return profile['runtimeRoot']+'/tasks/'+task['task_id']

def producer_feedback_enabled(profile, task=None):
    enabled = final_policy_enabled(profile) and profile['finalRemediation'].get('max_paid_producer_repairs', 0) == 1 and profile['finalRemediation'].get('producer_repair_timeout_seconds') == 900
    if task is not None:
        enabled = enabled and task.get('kind') == KIND and task.get('phase_remediation', {}).get('mode') == FINAL_MODE
    return enabled

def _current_sources(root, task):
    return {name:hashlib.sha256(read(root,name,250000)).hexdigest() if physical(root,name).exists() else None for name in task['edit_paths']}

def _producer_check(profile, parent, check):
    keys = {'argv','exit_code','stdout_sha256','stderr_sha256','stdout_bytes','stderr_bytes','output_tail'}
    need(type(check) is dict and set(check) == keys and type(check['exit_code']) is int
         and check['exit_code'] not in {0,75}, 'real nonzero producer check required')
    argv = check['argv']
    need(type(argv) is list and len(argv) == 9 and argv[:6] == ['node','swissknife/scripts/run-visual-functional-workflow.mjs','--app',parent['app_id'],'--contracts',profile['appContractPath']]
         and argv[6] == '--output-dir' and argv[8] == '--independent-viewports', 'foreign producer argv')
    need(all(type(check[k]) is str and re.fullmatch('[0-9a-f]{64}',check[k]) for k in ('stdout_sha256','stderr_sha256'))
         and all(type(check[k]) is int and check[k] >= 0 for k in ('stdout_bytes','stderr_bytes'))
         and type(check['output_tail']) is str and len(check['output_tail']) <= 16000, 'producer output identity malformed')
    return argv[7]

def validate_producer_feedback(root, profile, spec, task, packet_ref=None, *, current=True):
    need(producer_feedback_enabled(profile,task), 'producer feedback is not explicitly opted in')
    original,parent,_ = child_contract(root,profile,spec,task)
    directory = _feedback_directory(profile,task)
    wanted = directory+'/producer-feedback.json'
    packet_ref = packet_ref or ref(root,wanted)
    need(packet_ref['path'] == wanted, 'feedback packet escaped child')
    value = parse(check_ref(root,packet_ref))
    need(set(value) == {'schema','task_id','initial_proposal','initial_application','failure_record','producer_check','source_after','context','producer_phase','completion_authority'}
         and value['schema'] == FEEDBACK_SCHEMA and value['task_id'] == task['task_id'] and value['completion_authority'] is False,
         'producer feedback packet malformed')
    need(value['initial_proposal'] == ref(root,directory+'/proposal.json') and value['initial_application'] == ref(root,directory+'/application.json'), 'initial proposal/application rebound')
    proposal = parse(check_ref(root,value['initial_proposal'])); application = parse(check_ref(root,value['initial_application']))
    checked_application(root,profile,task,application,proposal)
    need(application['proposal'] == value['initial_proposal'] and value['source_after'] == application['after']
         and set(value['source_after']) == set(task['edit_paths']), 'feedback applied source differs')
    paid = payments(root,profile,task)
    need(paid['spent']['proposal'] == 1 and any(row['role']=='proposal' and row['state']=='returned' and row.get('receipt')==value['initial_proposal'] for row in paid['history']), 'feedback lacks the original charged proposal')
    raw_attempt = Path(_producer_check(profile,parent,value['producer_check']))
    need(raw_attempt.is_absolute() and raw_attempt.is_relative_to(Path(root)), 'producer output directory escaped root')
    attempt = physical(root,str(raw_attempt.relative_to(root)))
    need(attempt.is_relative_to(physical(root,profile['runtimeRoot']+'/tasks/'+parent['task_id']+'/verification')), 'producer attempt escaped parent')
    record = parse(check_ref(root,value['failure_record']))
    if record.get('schema') == 'swissknife.visual-functional-execution-failure.v1':
        need(record.get('task_id') == parent['task_id'] and record.get('stage') == 'workflow', 'foreign execution failure')
        record = parse(check_ref(root,record['driver_failure']))
    need(record.get('schema') == 'swissknife.visual-functional-workflow-failure.v1' and record.get('app_id') == parent['app_id']
         and record.get('work_complete') is False and record.get('completion_authority') is False
         and type(record.get('source_sha256')) is dict and all(record['source_sha256'].get(k)==v for k,v in value['source_after'].items()),
         'foreign/stale applied-source producer failure')
    need(value['producer_phase']==ref(root,_supplement_path(profile,task)), 'feedback supplemental clock identity changed')
    need(type(value['context']) is dict, 'worker-validated producer context required')
    if current: need(_current_sources(root,task) == value['source_after'], 'feedback source changed since producer failure')
    return value

def producer_repair_payments(root, profile, task):
    directory = _feedback_directory(profile,task)
    name = directory+'/producer-repair-payments.json'
    claim_name = name+'.claim.json'
    claim = parse(read(root,claim_name,65536)) if physical(root,claim_name).exists() else None
    empty = {'schema':FEEDBACK_SCHEMA,'task_id':task['task_id'],'limit':1,'spent':0,'history':[],
             'closed':False,'completion_authority':False}
    if claim is not None:
        need(claim.get('role') == 'producer_repair' and claim.get('task_id') == task['task_id'] and claim.get('state') == 'admitted'
             and claim.get('completion_authority') is False, 'feedback payment claim malformed')
    value = parse(read(root,name,65536)) if physical(root,name).exists() else {**empty,'spent':int(claim is not None),'history':[{k:v for k,v in claim.items() if k!='task_id'}] if claim else []}
    need(type(value) is dict and set(value)==set(empty) and value['schema']==FEEDBACK_SCHEMA and value['task_id']==task['task_id']
         and type(value['limit']) is int and value['limit']==1 and type(value['spent']) is int and value['spent'] in {0,1}
         and type(value['closed']) is bool and value['completion_authority'] is False and type(value['history']) is list
         and len(value['history'])==value['spent']==int(claim is not None), 'feedback payment journal malformed')
    if claim:
        row=value['history'][0]
        need(all(row.get(k)==v for k,v in claim.items() if k not in {'task_id','state'})
             and row.get('state') in {'admitted','returned','failed'}, 'feedback payment identity changed')
    return value

_initial_admit_payment = admit_payment
def admit_payment(root,profile,spec,task,role,admission):
    if role != 'producer_repair': return _initial_admit_payment(root,profile,spec,task,role,admission)
    with _mode(_task_mode(task)):
        packet=validate_producer_feedback(root,profile,spec,task)
        validate_admission(root,profile,task,role,admission)
        need(producer_repair_remaining_seconds(root,profile,task) >= admission['timeout_seconds']+5, 'feedback exceeds its supplemental absolute deadline')
        assert_no_hold(root,profile)
        with locked(root,profile):
            value=producer_repair_payments(root,profile,task)
            need(value['spent']==0 and not value['closed'], 'producer repair allowance already consumed; no refund or new identity')
            phase=_supplement(root,profile,task);deadline=phase['deadline_at_ms']
            row={'admission_id':admission['invocation_id'],'role':role,'state':'admitted','source_contract':source_contract(root,profile,task['phase_remediation']['original_task']),
                 'provider_admission':admission,'deadline_at_ms':deadline,'feedback':ref(root,_feedback_directory(profile,task)+'/producer-feedback.json'),
                 'original_deadline':phase['original_deadline'],'original_deadline_at_ms':phase['original_deadline_at_ms'],
                 'supplemental_phase':ref(root,_supplement_path(profile,task)),'supplemental_policy_sha256':phase['policy_sha256'],'completion_authority':False}
            atomic(root,_feedback_directory(profile,task)+'/producer-repair-payments.json.claim.json',wire({**row,'task_id':task['task_id']})+b'\n',exclusive=True)
            value.update(spent=1,history=[row]);atomic(root,_feedback_directory(profile,task)+'/producer-repair-payments.json',wire(value)+b'\n')
            return row['admission_id']

_initial_finish_payment = finish_payment
def finish_payment(root,profile,task,identity,*,receipt=None,error_type=None):
    value=producer_repair_payments(root,profile,task)
    if not value['history'] or value['history'][0]['admission_id'] != identity:
        return _initial_finish_payment(root,profile,task,identity,receipt=receipt,error_type=error_type)
    with locked(root,profile):
        value=producer_repair_payments(root,profile,task);row=value['history'][0]
        need(row['state']=='admitted','feedback payment already finished')
        if receipt is not None: payment_receipt(root,row,receipt);row['receipt']=receipt
        row['state']='failed' if error_type else 'returned'
        if error_type:row['error_type']=str(error_type)[:80]
        atomic(root,_feedback_directory(profile,task)+'/producer-repair-payments.json',wire(value)+b'\n')

_initial_recover_payment = recover_payment
def recover_payment(root,profile,task,role,output):
    if role != 'producer_repair':return _initial_recover_payment(root,profile,task,role,output)
    value=producer_repair_payments(root,profile,task)
    if value['spent']==0:return False
    row=value['history'][0];admission=row['provider_admission']
    need(str(Path(output).relative_to(root))==admission['output_path'],'feedback output rebound')
    need(row['state']!='failed','producer repair already failed; no retry/refund')
    archive=admission['attempt_receipt_path'];need(physical(root,archive).exists(),'feedback paid outcome unknown; never redispatch')
    receipt=payment_receipt(root,row,ref(root,archive));need(receipt.get('success') is True,'feedback native call failed')
    from swissknife_visual_functional_llm import validate_model_receipt
    validate_model_receipt(root,receipt,task_id=task['task_id'],mode='repair',predicted_files=task['edit_paths'])
    if physical(root,admission['output_path']).exists():need(parse(read(root,admission['output_path']))==receipt,'feedback output changed')
    else:atomic(root,admission['output_path'],read(root,archive),exclusive=True)
    if row['state']=='admitted':finish_payment(root,profile,task,row['admission_id'],receipt=ref(root,admission['output_path']))
    return True

def _prepare_producer_feedback(root,profile,spec,task,context_builder,trigger):
    need(callable(context_builder),'trusted worker producer failure context callback required')
    directory=_feedback_directory(profile,task);packet_name=directory+'/producer-feedback.json'
    if physical(root,packet_name).exists():return validate_producer_feedback(root,profile,spec,task,current=False)
    _,parent,_=child_contract(root,profile,spec,task)
    application=parse(check_ref(root,trigger['initial_application']))
    need(_current_sources(root,task)==application['after'],'foreign source before feedback capture')
    context=context_builder(profile,task,parent,trigger['initial_application'],trigger['failure_record'],trigger['producer_check'])
    need(_current_sources(root,task)==application['after'],'source changed during feedback context capture')
    packet={**trigger,'schema':FEEDBACK_SCHEMA,'task_id':task['task_id'],'source_after':application['after'],'context':context,
            'producer_phase':ref(root,_supplement_path(profile,task)),'completion_authority':False}
    atomic(root,packet_name,wire(packet)+b'\n',exclusive=True)
    return validate_producer_feedback(root,profile,spec,task)

def _feedback_application(root,profile,task,packet,proposal,ensure_lease,check_owned,apply_edits,remember_owned):
    directory=_feedback_directory(profile,task);intent=directory+'/producer-repair-application-intent.json';output=directory+'/producer-repair-proposal.json'
    if physical(root,intent).exists():application=parse(read(root,intent))
    else:
        ensure_lease(profile);check_owned(profile,task['edit_paths']);before=_current_sources(root,task)
        need(before==packet['source_after'],'foreign source before producer repair')
        retained={};raws={}
        for index,name in enumerate(task['edit_paths']):
            raw=read(root,name,250000) if physical(root,name).exists() else b'';raws[name]=raw;saved=directory+'/producer-repair-source-'+str(index)+'.txt'
            if physical(root,saved).exists():need(read(root,saved,250000,allow_empty=True)==raw,'feedback original source rebound')
            else:atomic(root,saved,raw,exclusive=True)
            retained[name]={'path':saved,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        from swissknife_visual_functional_recovery import proposal_after
        after=proposal_after(root,proposal,task['edit_paths'],before,raws)
        application={'schema':FEEDBACK_SCHEMA,'proposal':ref(root,output),'feedback':ref(root,directory+'/producer-feedback.json'),
                     'before':before,'after':after,'original_sources':retained,'completion_authority':False}
        atomic(root,intent,wire(application)+b'\n',exclusive=True)
    need(application['proposal']==ref(root,output) and application['feedback']==ref(root,directory+'/producer-feedback.json')
         and application['before']==packet['source_after'],'feedback application chain rebound')
    checked_application(root,profile,task,application,proposal)
    actual=_current_sources(root,task)
    need(all(actual[n] in {application['before'][n],application['after'][n]} for n in task['edit_paths']),'foreign source during producer repair replay')
    ledger_name=profile['runtimeRoot']+'/owned-source-hashes.json'
    if physical(root,ledger_name).exists():
        ledger=parse(read(root,ledger_name));need(all(ledger.get(n)in{application['before'][n],application['after'][n]}for n in task['edit_paths']),'foreign ownership ledger during feedback')
    pending=[n for n in task['edit_paths']if actual[n]!=application['after'][n]]
    ensure_lease(profile)
    if pending:
        check_owned(profile,pending);apply_edits(root,[e for e in proposal['response']['edits']if e['path']in pending],pending,lease_check=lambda:ensure_lease(profile))
    need(_current_sources(root,task)==application['after'],'producer repair application incomplete')
    changed=[n for n in task['edit_paths']if application['before'][n]!=application['after'][n]]
    if changed:remember_owned(profile,changed)
    atomic(root,directory+'/producer-repair-application.json',wire(application)+b'\n')
    return application

def _execute_producer_feedback(root,profile_path,profile,spec,task,packet,*,model,workflow,validate_workflow,apply_edits,ensure_lease,check_owned,remember_owned,**unused):
    directory=_feedback_directory(profile,task);failed=directory+'/producer-repair-failed.json'
    producer_repair_remaining_seconds(root,profile,task)
    need(not physical(root,failed).exists(),'corrected producer already failed; bounded feedback exhausted')
    output=physical(root,directory+'/producer-repair-proposal.json');recover_payment(root,profile,task,'producer_repair',output)
    if not output.exists():
        need(producer_repair_payments(root,profile,task)['spent']==0,'feedback outcome unknown; no redispatch')
        validate_producer_feedback(root,profile,spec,task)
        model(profile_path,task,'repair',[directory+'/producer-feedback.json',*task['edit_paths']],[],output,
              remediation_payment=(task,'producer_repair'),producer_failure=ref(root,directory+'/producer-feedback.json'))
    proposal=parse(read(root,str(output.relative_to(root))))
    from swissknife_visual_functional_llm import validate_model_receipt
    validate_model_receipt(root,proposal,task_id=task['task_id'],mode='repair',predicted_files=task['edit_paths'])
    need(proposal['response']['decision']=='needs_changes' and proposal['response']['edits'],'feedback requires real scoped native source edits')
    paid=producer_repair_payments(root,profile,task)
    need(paid['spent']==1 and paid['history'][0]['state']=='returned' and paid['history'][0].get('receipt')==ref(root,str(output.relative_to(root)))
         and paid['history'][0].get('feedback')==ref(root,directory+'/producer-feedback.json'),'feedback lacks exact charged returned proposal/packet')
    application=_feedback_application(root,profile,task,packet,proposal,ensure_lease,check_owned,apply_edits,remember_owned)
    _,parent,_=child_contract(root,profile,spec,task)
    try:
        remaining=producer_repair_remaining_seconds(root,profile,task);need(remaining>0,'feedback supplemental deadline exhausted')
        files,checks=workflow(profile,parent,physical(root,profile['runtimeRoot']+'/tasks/'+parent['task_id']+'/verification'),timeout_seconds=min(1200,remaining))
        report=files[0];need(validate_workflow(profile,parent,report)is not None,'corrected source still lacks fresh independent V2 producer')
    except Exception as error:
        if getattr(error,'producer_failure_record',None) is not None:
            atomic(root,failed,wire({'schema':FEEDBACK_SCHEMA,'application':ref(root,directory+'/producer-repair-application.json'),
                'failure_record':error.producer_failure_record,'producer_check':error.producer_check,'completion_authority':False})+b'\n',exclusive=True)
        raise
    with locked(root,profile):
        paid=producer_repair_payments(root,profile,task);need(paid['history'][0]['state']=='returned','feedback payment unfinished');paid['closed']=True
        atomic(root,directory+'/producer-repair-payments.json',wire(paid)+b'\n')
    _supplement(root,profile,task)  # Original 1/0 journal remains byte-exact.
    result={'schema':SCHEMA,'task_id':task['task_id'],'scope':'source_remediation_only','original_task_id':parent['task_id'],'original_task_sha256':digest(parent),
        'workflow':ref(root,str(report.relative_to(root))),'workflow_checks':checks,'proposal':packet['initial_proposal'],'application':packet['initial_application'],
        'assessment':None,'obsolete_gap':False,'payments':ref(root,payment_path(profile,task)),
        'producer_phase':ref(root,_supplement_path(profile,task)),
        'producer_repair':{'feedback':ref(root,directory+'/producer-feedback.json'),'proposal':ref(root,str(output.relative_to(root))),
            'application':ref(root,directory+'/producer-repair-application.json'),'payments':ref(root,directory+'/producer-repair-payments.json')},
        'completion_authority':False,'work_complete':False}
    name=directory+'/source-only-result.json';atomic(root,name,wire(result)+b'\n')
    _close_supplemental_result(root,profile,task,ref(root,name),result)
    return [physical(root,name),output],checks,{'source_only_remediation':ref(root,name),'original_acceptance_downstream':True,
        'paid_limits':{'assessment':1,'proposal':1,'producer_repair':1}}

_initial_execute_child = execute_child
def execute_child(root,profile_path,profile,spec,task,*,producer_failure_context=None,**kwargs):
    with _mode(_task_mode(task)):
        if not producer_feedback_enabled(profile,task):return _initial_execute_child(root,profile_path,profile,spec,task,**kwargs)
        directory=_feedback_directory(profile,task);packet=directory+'/producer-feedback.json';intent=directory+'/producer-feedback-intent.json'
        result_name=directory+'/source-only-result.json'
        if physical(root,result_name).exists():
            value=parse(read(root,result_name))
            if value.get('producer_phase')is not None:
                synthetic={'detail':{'source_only_remediation':ref(root,result_name)},'checks':value['workflow_checks']}
                if not physical(root,directory+'/producer-repair-phase-result.json').exists():
                    report=physical(root,value['workflow']['path']);check_ref(root,value['workflow'])
                    need(kwargs['validate_workflow'](profile,child_contract(root,profile,spec,task)[1],report)is not None,'retained supplemental result is not current')
                    _close_supplemental_result(root,profile,task,ref(root,result_name),value)
                validate_supplemental_result(root,profile,spec,task,synthetic,validate_workflow=kwargs['validate_workflow'])
                files=[physical(root,result_name)]
                if value.get('producer_repair'):files.append(physical(root,value['producer_repair']['proposal']['path']))
                return files,value['workflow_checks'],{'source_only_remediation':ref(root,result_name),'original_acceptance_downstream':True,'paid_limits':{'assessment':1,'proposal':1,'producer_repair':1}}
        if physical(root,packet).exists():
            producer_repair_remaining_seconds(root,profile,task)
            return _execute_producer_feedback(root,profile_path,profile,spec,task,validate_producer_feedback(root,profile,spec,task,current=False),**kwargs)
        if physical(root,intent).exists():
            trigger=parse(read(root,intent));producer_repair_remaining_seconds(root,profile,task)
            value=_prepare_producer_feedback(root,profile,spec,task,producer_failure_context,trigger)
            return _execute_producer_feedback(root,profile_path,profile,spec,task,value,**kwargs)
        if physical(root,_supplement_path(profile,task)).exists():
            return _probe_supplement(root,profile_path,profile,spec,task,producer_failure_context,**kwargs)
        if physical(root,directory+'/application.json').exists():
            retained=_find_retained_trigger(root,profile,spec,task)
            if retained is not None:
                _start_producer_supplement(root,profile,spec,task,retained)
                return _probe_supplement(root,profile_path,profile,spec,task,producer_failure_context,**kwargs)
        try:return _initial_execute_child(root,profile_path,profile,spec,task,**kwargs)
        except Exception as error:
            if getattr(error,'producer_failure_record',None)is None or getattr(error,'producer_check',None)is None:raise
            need(physical(root,directory+'/application.json').exists(),'feedback requires an applied initial proposal')
            _producer_check(profile,child_contract(root,profile,spec,task)[1],error.producer_check)
            _start_producer_supplement(root,profile,spec,task,error.producer_failure_record)
            trigger={'initial_proposal':ref(root,directory+'/proposal.json'),'initial_application':ref(root,directory+'/application.json'),
                'failure_record':error.producer_failure_record,'producer_check':error.producer_check}
            atomic(root,intent,wire(trigger)+b'\n',exclusive=True)
            value=_prepare_producer_feedback(root,profile,spec,task,producer_failure_context,trigger)
            return _execute_producer_feedback(root,profile_path,profile,spec,task,value,**kwargs)


_initial_child_can_still_write = child_can_still_write
def child_can_still_write(root,profile,task):
    if producer_feedback_enabled(profile,task):
        directory=_feedback_directory(profile,task)
        if physical(root,_supplement_path(profile,task)).exists():
            try:producer_repair_remaining_seconds(root,profile,task)
            except (ValueError,OSError,KeyError,TypeError):return False
        if not physical(root,directory+'/producer-feedback.json').exists():
            try:
                if physical(root,_supplement_path(profile,task)).exists():
                    producer_repair_remaining_seconds(root,profile,task)
                    return not physical(root,directory+'/producer-repair-probe.json').exists()
                if physical(root,directory+'/application.json').exists():
                    return _find_retained_trigger(root,profile,parse(read(root,profile['taskSpecPath'])),task)is not None
            except (ValueError,OSError,KeyError,TypeError):return False
        if physical(root,directory+'/producer-feedback.json').exists():
            if physical(root,directory+'/source-only-result.json').exists() or physical(root,directory+'/producer-repair-failed.json').exists():return False
            paid=producer_repair_payments(root,profile,task)
            if paid['spent']==0:
                try: validate_producer_feedback(root,profile,parse(read(root,profile['taskSpecPath'])),task)
                except (ValueError,OSError,KeyError,TypeError): return False
                return True
            output=directory+'/producer-repair-proposal.json'
            if not physical(root,output).exists() or paid['history'][0]['state']!='returned':return False
            try:
                from swissknife_visual_functional_llm import validate_model_receipt
                proposal=parse(read(root,output))
                validate_model_receipt(root,proposal,task_id=task['task_id'],mode='repair',predicted_files=task['edit_paths'])
                if proposal['response']['decision']!='needs_changes' or not proposal['response']['edits']:return False
                if paid['history'][0].get('receipt')!=ref(root,output) or paid['history'][0].get('feedback')!=ref(root,directory+'/producer-feedback.json'):return False
                packet=validate_producer_feedback(root,profile,parse(read(root,profile['taskSpecPath'])),task,current=False)
                intent=directory+'/producer-repair-application-intent.json'
                if physical(root,intent).exists():
                    application=parse(read(root,intent));checked_application(root,profile,task,application,proposal)
                    if application['before']!=packet['source_after']:return False
                    actual=_current_sources(root,task)
                    return actual!=application['after'] and all(actual[n]in{application['before'][n],application['after'][n]}for n in task['edit_paths'])
                return _current_sources(root,task)==packet['source_after']
            except (ValueError,OSError,KeyError,TypeError):return False
    return _initial_child_can_still_write(root,profile,task)

def _source_result(root,profile,spec,task,receipt):
    original,parent,_=child_contract(root,profile,spec,task)
    value=parse(check_ref(root,receipt['detail']['source_only_remediation']))
    need(value.get('schema')==SCHEMA and value.get('task_id')==task['task_id']
         and value.get('scope')=='source_remediation_only' and value.get('original_task_id')==parent['task_id']
         and value.get('original_task_sha256')==digest(parent) and value.get('work_complete')is False
         and value.get('completion_authority')is False,'child cannot grant parent acceptance')
    return parent,value

def _workflow_check(profile,parent,report,checks):
    need(type(checks)is list and len(checks)==1 and type(checks[0].get('exit_code'))is int and checks[0]['exit_code']==0
         and checks[0].get('argv')==['node','swissknife/scripts/run-visual-functional-workflow.mjs','--app',parent['app_id'],
             '--contracts',profile['appContractPath'],'--output-dir',str(report.parent),'--independent-viewports'],
         'source-only producer command changed')

def _feedback_result_chain(root,profile,spec,task,receipt):
    parent,value=_source_result(root,profile,spec,task,receipt)
    repair=value.get('producer_repair')
    need(type(repair)is dict and set(repair)=={'feedback','proposal','application','payments'},'feedback result chain missing')
    packet=validate_producer_feedback(root,profile,spec,task,repair['feedback'],current=False)
    need(value['proposal']==packet['initial_proposal'] and value['application']==packet['initial_application']
         and value.get('obsolete_gap')is False,'initial result provenance rebound')
    old=payments(root,profile,task)
    need(value.get('producer_phase')==ref(root,_supplement_path(profile,task)) and old['spent']['proposal']==1
         and check_ref(root,value['payments'])==check_ref(root,_supplement(root,profile,task)['original_payments_snapshot']),
         'original charged payment changed')
    from swissknife_visual_functional_llm import validate_model_receipt
    proposal=parse(check_ref(root,repair['proposal']))
    validate_model_receipt(root,proposal,task_id=task['task_id'],mode='repair',predicted_files=task['edit_paths'])
    need(proposal['response']['decision']=='needs_changes' and proposal['response']['edits'],'feedback did not return real edits')
    application=parse(check_ref(root,repair['application']))
    need(application['feedback']==repair['feedback'] and application['proposal']==repair['proposal']
         and application['before']==packet['source_after'],'feedback application lost initial-after join')
    checked_application(root,profile,task,application,proposal)
    need(_current_sources(root,task)==application['after'],'feedback applied source changed')
    paid=producer_repair_payments(root,profile,task)
    need(paid['spent']==1 and paid['closed']is True and paid['history'][0]['state']=='returned'
         and paid['history'][0].get('receipt')==repair['proposal'] and paid['history'][0].get('feedback')==repair['feedback']
         and check_ref(root,repair['payments'])==read(root,_feedback_directory(profile,task)+'/producer-repair-payments.json'),
         'feedback payment proof incomplete')
    return parent,value,application

_initial_validate_child_result = validate_child_result
def validate_child_result(root,profile,spec,task,receipt,*,validate_workflow):
    with _mode(_task_mode(task)):
        value=parse(check_ref(root,receipt['detail']['source_only_remediation']))
        if value.get('producer_phase')is not None:
            return validate_supplemental_result(root,profile,spec,task,receipt,validate_workflow=validate_workflow)
        if value.get('producer_repair')is not None:
            parent,value,application=_feedback_result_chain(root,profile,spec,task,receipt)
            report=physical(root,value['workflow']['path']);check_ref(root,value['workflow'])
            need(validate_workflow(profile,parent,report)is not None,'feedback result lacks fresh current independent producer')
            need(receipt.get('checks')==value['workflow_checks'],'feedback receipt checks rebound')
            _workflow_check(profile,parent,report,value['workflow_checks'])
            return value
        annex=_feedback_directory(profile,task)+'/controller-requalification.json'
        if physical(root,annex).exists():
            validate_controller_requalification(root,profile,spec,task,receipt,validate_workflow=validate_workflow)
            return value
        return _initial_validate_child_result(root,profile,spec,task,receipt,validate_workflow=validate_workflow)

_initial_recoverable_source = recoverable_owned_source
def recoverable_owned_source(root,profile,task_id,name):
    spec=parse(read(root,profile['taskSpecPath']));task=next((x for x in spec['tasks']if x['task_id']==task_id),None)
    if task is not None and producer_feedback_enabled(profile,task):
        directory=_feedback_directory(profile,task);intent=directory+'/producer-repair-application-intent.json'
        if physical(root,intent).exists() and name in task['edit_paths']:
            with _mode(_task_mode(task)):
                packet=validate_producer_feedback(root,profile,spec,task,current=False)
                application=parse(read(root,intent));proposal=parse(check_ref(root,application['proposal']))
                need(application['before']==packet['source_after'] and application['feedback']==ref(root,directory+'/producer-feedback.json'),
                     'replayed feedback source chain changed')
                checked_application(root,profile,task,application,proposal)
                paid=producer_repair_payments(root,profile,task)
                need(paid['spent']==1 and paid['history'][0]['state']=='returned'
                     and paid['history'][0].get('receipt')==application['proposal'] and paid['history'][0].get('feedback')==application['feedback'],'replay lacks charged feedback proposal/packet')
                actual=_current_sources(root,task)
                need(all(actual[n]in{application['before'][n],application['after'][n]}for n in task['edit_paths']),
                     'foreign source during feedback recovery')
                return True
    return _initial_recoverable_source(root,profile,task_id,name)


CONTROLLER_ANNEX_SCHEMA = 'swissknife.controller-requalification.v1'
REQUALIFIABLE_CONTROLLERS = frozenset({'scripts/swissknife_visual_functional_worker.py',
    'scripts/swissknife_visual_functional_phase_remediation.py','scripts/swissknife_visual_functional_llm.py',
    'config/swissknife_visual_functional_supervisor.json'})

def _canonical_completed_child(root,profile,spec,task,receipt):
    need(task.get('kind')==KIND and task.get('phase_remediation',{}).get('mode')==FINAL_MODE,
         'controller annex requires an admitted final source-only child')
    child_contract(root,profile,spec,task)
    board=blocks(read(root,profile['todoPath']).decode())
    need(task['task_id']in board and re.search(r'^- Status: completed\s*$',board[task['task_id']],re.M),
         'controller annex requires an already completed child')
    name=_feedback_directory(profile,task)+'/receipt.json'
    raw=read(root,name);actual=parse(raw)
    if type(receipt)is dict and 'path'in receipt and 'sha256'in receipt:
        need(receipt['path']==name and check_ref(root,receipt)==raw,'annex canonical receipt reference changed')
    else:need(wire(actual)==wire(receipt),'annex is not the canonical completed receipt')
    need(actual.get('schema')=='swissknife.visual-functional-task.v1' and actual.get('kind')==KIND
         and actual.get('task_id')==task['task_id'] and actual.get('task_spec_sha256')==digest(task)
         and actual.get('completion_authority')is False and actual.get('work_complete')is False,
         'completed receipt is not the exact source-only child')
    return actual,ref(root,name)

def _historical_controller_chain(root,profile,spec,task,receipt):
    receipt,receipt_ref=_canonical_completed_child(root,profile,spec,task,receipt)
    parent,value=_source_result(root,profile,spec,task,receipt)
    if value.get('keyboard_confirmation_normalization')is not None:
        parent,value,application=_keyboard_normalization_result_chain(root,profile,spec,task,receipt)
        need(_current_sources(root,task)==application['after'],'normalized completed child app/scenario changed')
        effective=value['keyboard_confirmation_normalization']['application']
        payment_refs=[value['payments'],value['producer_repair']['payments']]
    elif value.get('producer_repair')is not None:
        parent,value,application=_feedback_result_chain(root,profile,spec,task,receipt)
        effective=value['producer_repair']['application']
        payment_refs=[value['payments'],value['producer_repair']['payments']]
    else:
        need(value.get('obsolete_gap')is False and value.get('proposal')is not None and value.get('application')is not None,
             'controller annex requires a real applied source proposal')
        from swissknife_visual_functional_llm import validate_model_receipt
        proposal=parse(check_ref(root,value['proposal']))
        validate_model_receipt(root,proposal,task_id=task['task_id'],mode='repair',predicted_files=task['edit_paths'])
        need(proposal['response']['decision']=='needs_changes' and proposal['response']['edits'],'historical source proposal lacks edits')
        application=parse(check_ref(root,value['application']))
        need(application['proposal']==value['proposal'],'historical application proposal rebound')
        checked_application(root,profile,task,application,proposal)
        need(_current_sources(root,task)==application['after'],'completed child app/scenario changed')
        effective=value['application'];payment_refs=[value['payments']]
    paid=payments(root,profile,task)
    need((paid['closed']is True or value.get('producer_phase')is not None or value.get('retained_proposal_phase')is not None or value.get('keyboard_confirmation_normalization')is not None) and paid['spent']['proposal']==1
         and check_ref(root,value['payments'])==read(root,payment_path(profile,task)),
         'completed child payment is not its closed immutable outcome')
    if value.get('producer_phase')is not None:
        _supplemental_closure(root,profile,task,receipt['detail']['source_only_remediation'],value)
    if value.get('retained_proposal_phase')is not None:
        _validate_retained_resume_closure(root,profile,task,receipt['detail']['source_only_remediation'],value)
    report=physical(root,value['workflow']['path']);raw=check_ref(root,value['workflow']);old=parse(raw)
    need(report.is_relative_to(physical(root,profile['runtimeRoot']+'/tasks/'+parent['task_id']+'/verification')),
         'historical workflow escaped its parent')
    need(old.get('schema')=='swissknife.visual-functional-workflow.v2' and old.get('app_id')==parent['app_id']
         and old.get('passed')is True and old.get('actual_desktop')is True and type(old.get('source_sha256'))is dict,
         'completed historical V2 report malformed')
    need(receipt.get('checks')==value['workflow_checks'],'historical receipt command rebound')
    _workflow_check(profile,parent,report,value['workflow_checks'])
    sources=old['source_sha256']
    need(all(sources.get(name)==want for name,want in application['after'].items()),'historical report did not observe effective app/scenario')
    changes={}
    for name,want in sources.items():
        current=hashlib.sha256(read(root,name,16777216)).hexdigest()
        if current!=want:
            need(name in REQUALIFIABLE_CONTROLLERS,'non-controller historical source changed: '+name)
            changes[name]={'before':want,'after':current}
    need(changes,'controller annex cannot replace a current historical report')
    views=old.get('viewport_reports')
    need(type(views)is list and len(views)==2 and [v.get('name')for v in views]==['desktop','mobile'],
         'historical independent viewport references missing')
    from swissknife_visual_functional_final_coverage import CHILD_SCHEMA
    sessions=[]
    for entry in views:
        child=parse(check_ref(root,entry['report']))
        need(child.get('schema')==CHILD_SCHEMA and child.get('app_id')==parent['app_id']
             and child.get('source_sha256')==sources and type(child.get('session_id'))is str and child['session_id'],
             'historical child closure changed')
        sessions.append(child['session_id'])
        for item in child.get('artifacts',[]):_check_proof_artifact(root,item)
    need(len(set(sessions))==2,'historical viewports reuse a session')
    for item in old.get('artifacts',[]):_check_proof_artifact(root,item)
    for item in receipt.get('artifacts',[]):_check_proof_artifact(root,item)
    chain={'receipt':receipt_ref,'result':receipt['detail']['source_only_remediation'],'old_workflow':value['workflow'],
           'effective_application':effective,'payments':payment_refs,'source_after':application['after'],'controller_changes':changes}
    return parent,value,chain

def record_controller_requalification(root,profile,spec,task,receipt,report,checks,*,validate_workflow):
    """Operator-only data API; caller supplies the owned maintenance lease fence.

    The old completed receipt and its source/application/payment records are
    read only. This exclusive annex has no task-status or acceptance authority.
    """
    with _mode(_task_mode(task)):
        parent,value,chain=_historical_controller_chain(root,profile,spec,task,receipt)
        report=Path(report)
        if report.is_absolute():
            need(report.is_relative_to(Path(root)),'fresh annex report escaped root');report=physical(root,str(report.relative_to(root)))
        else:report=physical(root,str(report))
        need(report.is_relative_to(physical(root,profile['runtimeRoot']+'/tasks/'+parent['task_id']+'/verification'))
             and str(report.relative_to(root))!=value['workflow']['path'],'annex needs a distinct fresh parent workflow')
        _workflow_check(profile,parent,report,checks)
        need(validate_workflow(profile,parent,report)is not None,'annex lacks strict current independent two-view producer')
        after=_historical_controller_chain(root,profile,spec,task,receipt)[2]
        need(chain==after,'completed source chain changed during unpaid requalification')
        packet={'schema':CONTROLLER_ANNEX_SCHEMA,'task_id':task['task_id'],**chain,
            'workflow':ref(root,str(report.relative_to(root))),'workflow_checks':checks,
            'unpaid_current_source_requalification':True,'work_complete':False,'completion_authority':False}
        name=_feedback_directory(profile,task)+'/controller-requalification.json'
        atomic(root,name,wire(packet)+b'\n',exclusive=True)
        validate_controller_requalification(root,profile,spec,task,receipt,validate_workflow=validate_workflow)
        return ref(root,name)

def validate_controller_requalification(root,profile,spec,task,receipt,*,validate_workflow):
    with _mode(_task_mode(task)):
        parent,value,chain=_historical_controller_chain(root,profile,spec,task,receipt)
        name=_feedback_directory(profile,task)+'/controller-requalification.json';annex=parse(read(root,name))
        need(type(annex)is dict and set(annex)=={'schema','task_id',*chain,'workflow','workflow_checks',
            'unpaid_current_source_requalification','work_complete','completion_authority'}
             and annex['schema']==CONTROLLER_ANNEX_SCHEMA and annex['task_id']==task['task_id']
             and all(annex.get(k)==v for k,v in chain.items()) and annex['unpaid_current_source_requalification']is True
             and annex['completion_authority']is False and annex['work_complete']is False,'controller annex chain rebound')
        report=physical(root,annex['workflow']['path']);check_ref(root,annex['workflow'])
        need(annex['workflow']!=chain['old_workflow'],'controller annex rebound the old report')
        _workflow_check(profile,parent,report,annex['workflow_checks'])
        need(validate_workflow(profile,parent,report)is not None,'controller annex no longer has strict current source qualification')
        return annex


SUPPLEMENT_SCHEMA = 'swissknife.producer-repair-phase.v1'

def _supplement_path(profile,task):
    return _feedback_directory(profile,task)+'/producer-repair-phase.json'

def _supplement(root,profile,task):
    value=parse(read(root,_supplement_path(profile,task),131072))
    need(value.get('schema')==SUPPLEMENT_SCHEMA and value.get('task_id')==task['task_id']
         and value.get('completion_authority')is False and value.get('work_complete')is False
         and type(value.get('created_at_ms'))is int and type(value.get('deadline_at_ms'))is int
         and type(value.get('timeout_seconds'))is int and value['timeout_seconds']==900 and value['deadline_at_ms']==value['created_at_ms']+900000
         and value.get('policy_sha256')==digest(value.get('policy'))
         and value['policy'].get('max_paid_producer_repairs')==1
         and value['policy'].get('producer_repair_timeout_seconds')==900,
         'supplemental phase deadline/policy malformed')
    directory=_feedback_directory(profile,task)
    need(value['initial_proposal']==ref(root,directory+'/proposal.json')
         and value['initial_application']==ref(root,directory+'/application.json'), 'supplement original source authority changed')
    application=parse(check_ref(root,value['initial_application']))
    need(value['source_after']==application['after'],'supplement initial-after witness changed')
    check_ref(root,value['retained_failure'])
    need(check_ref(root,value['original_payments'])==check_ref(root,value['original_payments_snapshot']),
         'original proposal/assessment payment bytes changed')
    deadline=parse(check_ref(root,value['original_deadline']))
    need(deadline['deadline_at_ms']==value['original_deadline_at_ms'],'original deadline changed')
    phase_ref=ref(root,_supplement_path(profile,task))
    claim_name=directory+'/producer-repair-payments.json.claim.json'
    if physical(root,claim_name).exists():
        claim=parse(read(root,claim_name,65536))
        need(claim.get('supplemental_phase')==phase_ref and claim.get('deadline_at_ms')==value['deadline_at_ms']
             and claim.get('original_deadline')==value['original_deadline']
             and claim.get('original_deadline_at_ms')==value['original_deadline_at_ms']
             and claim.get('supplemental_policy_sha256')==value['policy_sha256'],'claimed supplemental clock was renewed/rebound')
    probe_name=directory+'/producer-repair-probe.json'
    if physical(root,probe_name).exists():need(parse(read(root,probe_name)).get('phase')==phase_ref,'admitted supplemental probe clock changed')
    packet_name=directory+'/producer-feedback.json'
    if physical(root,packet_name).exists():need(parse(read(root,packet_name)).get('producer_phase')==phase_ref,'grounded feedback clock changed')
    return value

def producer_repair_remaining_seconds(root,profile,task):
    """Only the separately authorized phase clock; never renew/create it here."""
    need(producer_feedback_enabled(profile,task),'supplemental producer repair not explicitly opted in')
    phase=_supplement(root,profile,task)
    need(phase['policy_sha256']==digest(profile['finalRemediation']),'supplemental policy changed; no renewed credit')
    remaining=(phase['deadline_at_ms']-int(time.time()*1000))//1000
    need(remaining>0,'supplemental producer repair deadline exhausted; no renewal')
    return remaining

def _retained_producer_trigger(root,profile,spec,task,failure_ref):
    _,parent,_=child_contract(root,profile,spec,task)
    directory=_feedback_directory(profile,task);application=parse(read(root,directory+'/application.json'))
    proposal=parse(read(root,directory+'/proposal.json'));checked_application(root,profile,task,application,proposal)
    need(_current_sources(root,task)==application['after'],'retained producer trigger no longer matches applied initial source')
    paid=payments(root,profile,task)
    need(paid['spent']['proposal']==1 and any(row['role']=='proposal'and row['state']=='returned'
         and row.get('receipt')==ref(root,directory+'/proposal.json')for row in paid['history']), 'supplement lacks original charged proposal')
    record=parse(check_ref(root,failure_ref));record_path=physical(root,failure_ref['path'])
    if record.get('schema')=='swissknife.visual-functional-execution-failure.v1':
        archive=physical(root,profile['runtimeRoot']+'/tasks/'+parent['task_id']+'/execution-failures')
        need(record_path.parent==archive and re.fullmatch('[0-9a-f]{32}\\.json',record_path.name)
             and record.get('task_id')==parent['task_id'] and record.get('stage')=='workflow'
             and record.get('error',{}).get('code')=='ValidationCommandError'
             and record.get('work_complete')is False and record.get('completion_authority')is False,
             'supplement needs immutable real checked failure, not HOLD/resource/latest')
        code=re.match(r'command exit ([0-9]+):',record['error'].get('message',''))
        need(code and int(code.group(1))not in {0,75},'resource/success cannot start a supplemental phase')
        driver_ref=record.get('driver_failure');need(type(driver_ref)is dict,'retained failure has no source witness')
        driver=parse(check_ref(root,driver_ref));driver_path=physical(root,driver_ref['path'])
    else:
        # Portable tests explicitly author this trusted-worker boundary; the
        # real worker supplies the immutable archived execution record above.
        driver=record;driver_path=record_path
    expected=physical(root,profile['runtimeRoot']+'/tasks/'+parent['task_id']+'/verification')
    need(driver_path.is_relative_to(expected) and driver_path.name=='failure.json'
         and driver.get('schema')=='swissknife.visual-functional-workflow-failure.v1'
         and driver.get('app_id')==parent['app_id'] and driver.get('work_complete')is False
         and driver.get('completion_authority')is False and type(driver.get('source_sha256'))is dict,
         'retained producer failure escaped original source task')
    need(all(driver['source_sha256'].get(n)==v for n,v in application['after'].items()),'retained failure has foreign app/scenario bytes')
    drift={}
    for name,want in driver['source_sha256'].items():
        current=hashlib.sha256(read(root,name,16777216)).hexdigest()
        if current!=want:
            need(name in REQUALIFIABLE_CONTROLLERS,'retained failure has unrelated stale source')
            drift[name]={'before':want,'after':current}
    return application,drift

def _start_producer_supplement(root,profile,spec,task,failure_ref):
    need(producer_feedback_enabled(profile,task),'producer repair phase is not explicitly opted in')
    name=_supplement_path(profile,task)
    if physical(root,name).exists():return _supplement(root,profile,task)
    application,drift=_retained_producer_trigger(root,profile,spec,task,failure_ref)
    assert_no_hold(root,profile)
    directory=_feedback_directory(profile,task);old_pay=read(root,payment_path(profile,task),65536)
    saved=directory+'/producer-repair-original-payments.json'
    if physical(root,saved).exists():need(read(root,saved,65536)==old_pay,'original payment snapshot changed')
    else:atomic(root,saved,old_pay,exclusive=True)
    old_deadline=directory+'/execution-deadline.json';old=parse(read(root,old_deadline))
    now=int(time.time()*1000)
    value={'schema':SUPPLEMENT_SCHEMA,'task_id':task['task_id'],'created_at_ms':now,'deadline_at_ms':now+900000,
        'timeout_seconds':900,'policy':profile['finalRemediation'],'policy_sha256':digest(profile['finalRemediation']),
        'initial_proposal':ref(root,directory+'/proposal.json'),'initial_application':ref(root,directory+'/application.json'),
        'source_after':application['after'],'retained_failure':failure_ref,'controller_drift':drift,
        'original_payments':ref(root,payment_path(profile,task)),'original_payments_snapshot':ref(root,saved),
        'original_deadline':ref(root,old_deadline),'original_deadline_at_ms':old['deadline_at_ms'],
        'completion_authority':False,'work_complete':False}
    atomic(root,name,wire(value)+b'\n',exclusive=True)
    return value

def _find_retained_trigger(root,profile,spec,task):
    _,parent,_=child_contract(root,profile,spec,task)
    directory=physical(root,profile['runtimeRoot']+'/tasks/'+parent['task_id']+'/execution-failures')
    if not directory.exists():return None
    entries=list(directory.iterdir());need(len(entries)<=128,'retained producer failure census expanded')
    candidates=[]
    for path in entries:
        if not path.is_file()or not re.fullmatch('[0-9a-f]{32}\\.json',path.name):continue
        reference=ref(root,str(path.relative_to(root)))
        try: _retained_producer_trigger(root,profile,spec,task,reference)
        except (ValueError,OSError,KeyError,TypeError):continue
        candidates.append(reference)
    return sorted(candidates,key=lambda x:x['path'])[-1]if candidates else None

def _probe_supplement(root,profile_path,profile,spec,task,context_builder,**kwargs):
    directory=_feedback_directory(profile,task);claim=directory+'/producer-repair-probe.json'
    need(not physical(root,claim).exists(),'supplemental probe already admitted with unknown outcome; no repeated unchanged producer')
    _,parent,_=child_contract(root,profile,spec,task);remaining=producer_repair_remaining_seconds(root,profile,task)
    kwargs['ensure_lease'](profile)
    need(_current_sources(root,task)==_supplement(root,profile,task)['source_after'],'foreign source before unpaid supplemental probe')
    atomic(root,claim,wire({'schema':SUPPLEMENT_SCHEMA,'task_id':task['task_id'],'phase':ref(root,_supplement_path(profile,task)),
        'work_complete':False,'completion_authority':False})+b'\n',exclusive=True)
    try:
        files,checks=kwargs['workflow'](profile,parent,physical(root,profile['runtimeRoot']+'/tasks/'+parent['task_id']+'/verification'),timeout_seconds=min(1200,remaining))
        report=files[0];need(kwargs['validate_workflow'](profile,parent,report)is not None,'unpaid probe lacks current independent V2 proof')
    except Exception as error:
        if getattr(error,'producer_failure_record',None)is None or getattr(error,'producer_check',None)is None:raise
        trigger={'initial_proposal':ref(root,directory+'/proposal.json'),'initial_application':ref(root,directory+'/application.json'),
            'failure_record':error.producer_failure_record,'producer_check':error.producer_check}
        atomic(root,directory+'/producer-feedback-intent.json',wire(trigger)+b'\n',exclusive=True)
        packet=_prepare_producer_feedback(root,profile,spec,task,context_builder,trigger)
        return _execute_producer_feedback(root,profile_path,profile,spec,task,packet,**kwargs)
    phase=_supplement(root,profile,task)
    value={'schema':SCHEMA,'task_id':task['task_id'],'scope':'source_remediation_only','original_task_id':parent['task_id'],
        'original_task_sha256':digest(parent),'workflow':ref(root,str(report.relative_to(root))),'workflow_checks':checks,
        'proposal':phase['initial_proposal'],'application':phase['initial_application'],'assessment':None,'obsolete_gap':False,
        'payments':phase['original_payments'],'producer_phase':ref(root,_supplement_path(profile,task)),
        'probe_only':True,'completion_authority':False,'work_complete':False}
    name=directory+'/source-only-result.json';atomic(root,name,wire(value)+b'\n')
    _close_supplemental_result(root,profile,task,ref(root,name),value)
    return [physical(root,name)],checks,{'source_only_remediation':ref(root,name),'original_acceptance_downstream':True,
        'paid_limits':{'assessment':1,'proposal':1,'producer_repair':1}}

def _close_supplemental_result(root,profile,task,result_ref,value):
    phase=_supplement(root,profile,task);paid=producer_repair_payments(root,profile,task)
    need(value.get('producer_phase')==ref(root,_supplement_path(profile,task)),'result lacks its supplemental phase')
    packet={'schema':SUPPLEMENT_SCHEMA,'task_id':task['task_id'],'phase':value['producer_phase'],
        'result':result_ref,'workflow':value['workflow'],'producer_repair_spent':paid['spent'],
        'closed':True,'work_complete':False,'completion_authority':False}
    name=_feedback_directory(profile,task)+'/producer-repair-phase-result.json'
    if physical(root,name).exists():need(wire(parse(read(root,name)))==wire(packet),'supplemental closure rebound')
    else:atomic(root,name,wire(packet)+b'\n',exclusive=True)
    return packet

def _supplemental_closure(root,profile,task,result_ref,value):
    phase=_supplement(root,profile,task)
    need(value.get('producer_phase')==ref(root,_supplement_path(profile,task))
         and value['payments']==phase['original_payments'],'supplemental original payment/phase lineage differs')
    closed=parse(read(root,_feedback_directory(profile,task)+'/producer-repair-phase-result.json'))
    paid=producer_repair_payments(root,profile,task)
    expected={'schema':SUPPLEMENT_SCHEMA,'task_id':task['task_id'],'phase':value['producer_phase'],
        'result':result_ref,'workflow':value['workflow'],'producer_repair_spent':paid['spent'],
        'closed':True,'work_complete':False,'completion_authority':False}
    need(wire(closed)==wire(expected),'supplemental result closure differs')
    return closed

def validate_supplemental_result(root,profile,spec,task,receipt,*,validate_workflow):
    parent,value=_source_result(root,profile,spec,task,receipt)
    _supplemental_closure(root,profile,task,receipt['detail']['source_only_remediation'],value)
    if value.get('producer_repair')is not None:
        parent,value,application=_feedback_result_chain(root,profile,spec,task,receipt)
    else:
        phase=_supplement(root,profile,task)
        need(value.get('probe_only')is True and value.get('obsolete_gap')is False
             and value['proposal']==phase['initial_proposal'] and value['application']==phase['initial_application']
             and _current_sources(root,task)==phase['source_after'] and producer_repair_payments(root,profile,task)['spent']==0,
             'unpaid supplemental result changed its source/model lineage')
        proposal=parse(check_ref(root,value['proposal']));application=parse(check_ref(root,value['application']))
        checked_application(root,profile,task,application,proposal)
    report=physical(root,value['workflow']['path']);check_ref(root,value['workflow'])
    _workflow_check(profile,parent,report,value['workflow_checks'])
    need(receipt.get('checks')==value['workflow_checks'] and validate_workflow(profile,parent,report)is not None,
         'supplemental result lacks current independent two-view producer')
    return value


# Historical Playwright archives are binary artifacts, not JSON/model inputs.
# Their separate streaming bound must not broaden read()/check_ref() limits.
MAX_PROOF_ZIP_BYTES = 64 * 1024 * 1024


def _check_proof_artifact(root, value):
    need(type(value) is dict and set(value) == {'path', 'sha256', 'bytes'},
         'invalid retained proof artifact reference')
    name = value['path']
    if not (type(name) is str and name.endswith('.zip')):
        check_ref(root, value)
        return value
    need(type(value['bytes']) is int and 0 < value['bytes'] <= MAX_PROOF_ZIP_BYTES
         and type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']),
         'retained ZIP artifact exceeds its separate bound')
    target = physical(root, name)
    fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_size == value['bytes']
             and 0 < before.st_size <= MAX_PROOF_ZIP_BYTES,
             'unbounded/nonregular retained ZIP artifact')
        total = 0
        checksum = hashlib.sha256()
        first = True
        while True:
            part = stream.read(128 * 1024)
            if not part:
                break
            if first:
                need(part[:4] in (b'PK\x03\x04', b'PK\x05\x06'), 'retained ZIP signature differs')
                first = False
            total += len(part)
            need(total <= before.st_size, 'retained ZIP artifact grew')
            checksum.update(part)
        after = os.fstat(stream.fileno())
    identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    need(total == value['bytes'] and checksum.hexdigest() == value['sha256']
         and identity(before) == identity(after) == identity(target.lstat()),
         'retained ZIP proof artifact changed')
    return value


CONTROLLER_ANNEX_V2_SCHEMA = 'swissknife.controller-requalification.v2'
_legacy_controller_annex_validator = validate_controller_requalification


def controller_requalification_identity(root):
    sources = {name: hashlib.sha256(read(root, name)).hexdigest()
               for name in sorted(REQUALIFIABLE_CONTROLLERS)}
    return {'controller_sha256': sources, 'key': digest(sources)}


def controller_requalification_path(profile, task, identity):
    need(type(identity) is dict and set(identity) == {'controller_sha256', 'key'}
         and type(identity['controller_sha256']) is dict
         and set(identity['controller_sha256']) == REQUALIFIABLE_CONTROLLERS
         and all(type(value) is str and re.fullmatch('[0-9a-f]{64}', value)
                 for value in identity['controller_sha256'].values())
         and identity['key'] == digest(identity['controller_sha256']),
         'versioned controller annex identity differs')
    return _feedback_directory(profile, task) + '/controller-requalifications/' + identity['key'] + '.json'


def record_controller_requalification(root, profile, spec, task, receipt, report, checks, *, validate_workflow):
    """Append one annex per exact current controller tuple; old annexes stay immutable."""
    with _mode(_task_mode(task)):
        parent, value, chain = _historical_controller_chain(root, profile, spec, task, receipt)
        identity = controller_requalification_identity(root)
        report = Path(report)
        if report.is_absolute():
            need(report.is_relative_to(Path(root)), 'fresh annex report escaped root')
            report = physical(root, str(report.relative_to(root)))
        else:
            report = physical(root, str(report))
        need(report.is_relative_to(physical(root, profile['runtimeRoot'] + '/tasks/' + parent['task_id'] + '/verification'))
             and str(report.relative_to(root)) != value['workflow']['path'],
             'annex needs a distinct fresh parent workflow')
        _workflow_check(profile, parent, report, checks)
        need(validate_workflow(profile, parent, report) is not None,
             'annex lacks strict current independent two-view producer')
        need(wire(chain) == wire(_historical_controller_chain(root, profile, spec, task, receipt)[2])
             and wire(identity) == wire(controller_requalification_identity(root)),
             'completed source/controller chain changed during unpaid requalification')
        packet = {'schema': CONTROLLER_ANNEX_V2_SCHEMA, 'task_id': task['task_id'], **chain,
                  'controller_identity': identity, 'workflow': ref(root, str(report.relative_to(root))),
                  'workflow_checks': checks, 'unpaid_current_source_requalification': True,
                  'work_complete': False, 'completion_authority': False}
        name = controller_requalification_path(profile, task, identity)
        atomic(root, name, wire(packet) + b'\n', exclusive=True)
        validate_controller_requalification(root, profile, spec, task, receipt, validate_workflow=validate_workflow)
        return ref(root, name)


def validate_controller_requalification(root, profile, spec, task, receipt, *, validate_workflow):
    with _mode(_task_mode(task)):
        identity = controller_requalification_identity(root)
        name = controller_requalification_path(profile, task, identity)
        if not physical(root, name).exists():
            # Legacy R38's one fixed annex remains readable only when every
            # original source/controller join is still current; never rebind it.
            return _legacy_controller_annex_validator(root, profile, spec, task, receipt,
                                                       validate_workflow=validate_workflow)
        parent, value, chain = _historical_controller_chain(root, profile, spec, task, receipt)
        annex = parse(read(root, name))
        need(type(annex) is dict and set(annex) == {'schema', 'task_id', *chain,
             'controller_identity', 'workflow', 'workflow_checks', 'unpaid_current_source_requalification',
             'work_complete', 'completion_authority'}
             and annex['schema'] == CONTROLLER_ANNEX_V2_SCHEMA and annex['task_id'] == task['task_id']
             and wire(annex['controller_identity']) == wire(identity)
             and all(wire(annex.get(key)) == wire(value) for key, value in chain.items())
             and annex['unpaid_current_source_requalification'] is True
             and annex['completion_authority'] is False and annex['work_complete'] is False,
             'versioned controller annex chain rebound')
        report = physical(root, annex['workflow']['path'])
        check_ref(root, annex['workflow'])
        need(annex['workflow'] != chain['old_workflow'], 'controller annex rebound the old report')
        _workflow_check(profile, parent, report, annex['workflow_checks'])
        need(validate_workflow(profile, parent, report) is not None,
             'controller annex no longer has strict current source qualification')
        return annex


def _validate_retained_resume_closure(root, profile, task, result_ref, value, *, create=False):
    phase = _resume_phase(root, profile, task)
    phase_ref = ref(root, _resume_name(profile, task))
    claim_name = _resume_name(profile, task, 'producer-claim.json')
    claim = parse(read(root, claim_name))
    need(value.get('retained_proposal_phase') == phase_ref and value.get('proposal') == phase['proposal']
         and value.get('payments') == phase['payments'] and value.get('obsolete_gap') is False
         and claim == {'schema': RESUME_SCHEMA, 'task_id': task['task_id'], 'phase': phase_ref,
                       'deadline_at_ms': phase['deadline_at_ms'], 'application': value['application'],
                       'max_paid_calls': 0, 'completion_authority': False},
         'unpaid resumed producer/result lineage changed')
    expected = {'schema': RESUME_SCHEMA, 'task_id': task['task_id'], 'phase': phase_ref,
                'producer_claim': ref(root, claim_name), 'result': result_ref, 'workflow': value['workflow'],
                'paid_calls': 0, 'closed': True, 'work_complete': False, 'completion_authority': False}
    name = _resume_name(profile, task, 'result.json')
    if create and not physical(root, name).exists():
        atomic(root, name, wire(expected) + b'\n', exclusive=True)
    need(wire(parse(read(root, name))) == wire(expected), 'retained-proposal resume closure changed')
    return expected


def validate_retained_proposal_resume(root, profile, spec, task, receipt, *, validate_workflow, close=False):
    parent, value = _source_result(root, profile, spec, task, receipt)
    phase = _resume_phase(root, profile, task)
    proposal = parse(check_ref(root, phase['proposal']))
    application = parse(check_ref(root, value['application']))
    need(application['proposal'] == phase['proposal'], 'resumed application proposal changed')
    checked_application(root, profile, task, application, proposal)
    need(_current_sources(root, task) == application['after'], 'resumed applied source changed')
    paid = payments(root, profile, task)
    need(paid['spent']['proposal'] == 1 and paid['closed'] is False,
         'unpaid resume changed original paid/closed state')
    report = physical(root, value['workflow']['path'])
    check_ref(root, value['workflow'])
    _workflow_check(profile, parent, report, value['workflow_checks'])
    need(receipt.get('checks') == value['workflow_checks'] and validate_workflow(profile, parent, report) is not None,
         'retained proposal resume lacks a strict current producer')
    _validate_retained_resume_closure(root, profile, task, receipt['detail']['source_only_remediation'], value, create=close)
    return value


_r38_execute_child = execute_child
_r38_validate_child_result = validate_child_result
_r38_child_can_still_write = child_can_still_write


def execute_child(root, profile_path, profile, spec, task, *, producer_failure_context=None, **kwargs):
    with _mode(_task_mode(task)):
        directory = _feedback_directory(profile, task)
        result_name = directory + '/source-only-result.json'
        if physical(root, result_name).exists():
            value = parse(read(root, result_name))
            if value.get('retained_proposal_phase') is not None:
                synthetic = {'detail': {'source_only_remediation': ref(root, result_name)}, 'checks': value['workflow_checks']}
                validate_retained_proposal_resume(root, profile, spec, task, synthetic,
                                                  validate_workflow=kwargs['validate_workflow'], close=True)
                return [physical(root, result_name), physical(root, value['proposal']['path'])], value['workflow_checks'], {
                    'source_only_remediation': ref(root, result_name), 'original_acceptance_downstream': True,
                    'paid_limits': {'assessment': 1, 'proposal': 1}, 'retained_resume_paid_calls': 0}
        # An already grounded producer phase owns its separate new paid allowance.
        if retained_proposal_resume_enabled(profile, task) and not physical(root, _supplement_path(profile, task)).exists():
            phase_name = _resume_name(profile, task)
            deadline_name = directory + '/execution-deadline.json'
            if physical(root, phase_name).exists() or (physical(root, deadline_name).exists()
                    and physical(root, directory + '/proposal.json').exists()
                    and parse(read(root, deadline_name)).get('deadline_at_ms', 0) <= int(time.time() * 1000)):
                return execute_retained_proposal_resume(root, profile_path, profile, spec, task,
                    producer_failure_context=producer_failure_context, **kwargs)
        return _r38_execute_child(root, profile_path, profile, spec, task,
                                  producer_failure_context=producer_failure_context, **kwargs)


def validate_child_result(root, profile, spec, task, receipt, *, validate_workflow):
    value = parse(check_ref(root, receipt['detail']['source_only_remediation']))
    if value.get('retained_proposal_phase') is not None:
        return validate_retained_proposal_resume(root, profile, spec, task, receipt, validate_workflow=validate_workflow)
    if task.get('phase_remediation', {}).get('mode') == FINAL_MODE:
        directory = _feedback_directory(profile, task) + '/controller-requalifications'
        if physical(root, directory).exists():
            identity = controller_requalification_identity(root)
            if physical(root, controller_requalification_path(profile, task, identity)).exists():
                validate_controller_requalification(root, profile, spec, task, receipt, validate_workflow=validate_workflow)
                return value
    return _r38_validate_child_result(root, profile, spec, task, receipt, validate_workflow=validate_workflow)


def child_can_still_write(root, profile, task):
    if retained_proposal_resume_enabled(profile, task):
        directory = _feedback_directory(profile, task)
        if physical(root, _resume_name(profile, task)).exists() and not physical(root, _supplement_path(profile, task)).exists():
            try:
                retained_proposal_resume_remaining_seconds(root, profile, task)
                if physical(root, _resume_name(profile, task, 'producer-claim.json')).exists():
                    return False
                proposal = parse(read(root, directory + '/proposal.json'))
                from swissknife_visual_functional_llm import validate_model_receipt
                validate_model_receipt(root, proposal, task_id=task['task_id'], mode='repair', predicted_files=task['edit_paths'])
                intent = directory + '/application-intent.json'
                return not physical(root, intent).exists() or _current_sources(root, task) != parse(read(root, intent))['after']
            except (ValueError, OSError, KeyError, TypeError):
                return False
    return _r38_child_can_still_write(root, profile, task)


RESUME_SCHEMA = 'swissknife.retained-proposal-resume.v1'


def retained_proposal_resume_enabled(profile, task=None):
    value = profile.get('retainedProposalResume')
    if value is None:
        return False
    expected = {'schema': RESUME_SCHEMA, 'enabled': True, 'max_finals': 45,
                'max_resumes_per_child': 1, 'max_paid_calls': 0, 'timeout_seconds': 900}
    need(type(value) is dict and type(value.get('enabled')) is bool
         and wire({**value, 'enabled': True}) == wire(expected), 'retained-proposal resume opt-in expanded')
    return value['enabled'] and (task is None or task.get('phase_remediation', {}).get('mode') == FINAL_MODE)


def _resume_name(profile, task, tail='phase.json'):
    return _feedback_directory(profile, task) + '/retained-proposal-resume-' + tail


def _retained_paid_proposal(root, profile, spec, task):
    need(retained_proposal_resume_enabled(profile, task), 'retained-proposal resume is not explicitly opted in')
    child_contract(root, profile, spec, task)
    directory = _feedback_directory(profile, task)
    need(not physical(root, directory + '/receipt.json').exists(), 'completed child cannot resume a queued proposal')
    old_deadline = ref(root, directory + '/execution-deadline.json')
    deadline = parse(check_ref(root, old_deadline))
    need(type(deadline.get('deadline_at_ms')) is int and deadline['deadline_at_ms'] <= int(time.time() * 1000),
         'retained-proposal resume requires an expired original deadline')
    paid = payments(root, profile, task)
    proposal_ref = ref(root, directory + '/proposal.json')
    from swissknife_visual_functional_llm import validate_model_receipt
    proposal = parse(check_ref(root, proposal_ref))
    validate_model_receipt(root, proposal, task_id=task['task_id'], mode='repair', predicted_files=task['edit_paths'])
    need(proposal['response']['decision'] == 'needs_changes' and proposal['response']['edits']
         and paid['spent']['proposal'] == 1 and paid['closed'] is False,
         'resume requires a returned paid source proposal, not new credit')
    rows = [row for row in paid['history'] if row['role'] == 'proposal']
    need(len(rows) == 1 and rows[0]['state'] == 'returned' and rows[0].get('receipt') == proposal_ref,
         'retained proposal outcome is unknown or differs from its single paid call')
    payment_receipt(root, rows[0], proposal_ref)
    return proposal, {'proposal': proposal_ref, 'payments': ref(root, payment_path(profile, task)),
                      'original_deadline': old_deadline, 'original_deadline_at_ms': deadline['deadline_at_ms']}


def _resume_phase(root, profile, task):
    name = _resume_name(profile, task)
    phase = parse(read(root, name))
    anchor = parse(read(root, _resume_name(profile, task, 'start.json')))
    need(type(phase) is dict and phase.get('schema') == RESUME_SCHEMA and phase.get('task_id') == task['task_id']
         and phase.get('task_sha256') == digest(task) and phase.get('policy') == profile.get('retainedProposalResume')
         and phase.get('policy_sha256') == digest(profile['retainedProposalResume'])
         and type(phase.get('created_at_ms')) is int and type(phase.get('deadline_at_ms')) is int
         and phase['deadline_at_ms'] == phase['created_at_ms'] + 900000
         and phase.get('max_paid_calls') == 0 and type(phase['max_paid_calls']) is int,
         'retained-proposal resume phase malformed or renewed')
    need(anchor == {'schema': RESUME_SCHEMA, 'task_id': task['task_id'], 'phase': ref(root, name),
                    'deadline_at_ms': phase['deadline_at_ms'], 'max_paid_calls': 0,
                    'completion_authority': False}, 'retained-proposal resume clock anchor changed')
    for key in ('proposal', 'payments', 'original_deadline'):
        check_ref(root, phase[key])
    need(phase['payments'] == ref(root, payment_path(profile, task))
         and phase['original_deadline'] == ref(root, _feedback_directory(profile, task) + '/execution-deadline.json'),
         'original paid journal/deadline changed during unpaid resume')
    spec = parse(read(root, profile['taskSpecPath']))
    child_contract(root, profile, spec, task)
    paid = payments(root, profile, task)
    proposal = parse(check_ref(root, phase['proposal']))
    from swissknife_visual_functional_llm import validate_model_receipt
    validate_model_receipt(root, proposal, task_id=task['task_id'], mode='repair', predicted_files=task['edit_paths'])
    rows = [row for row in paid['history'] if row['role'] == 'proposal']
    need(paid['spent']['proposal'] == 1 and paid['closed'] is False and len(rows) == 1
         and rows[0]['state'] == 'returned' and rows[0].get('receipt') == phase['proposal']
         and phase['original_deadline_at_ms'] == parse(check_ref(root, phase['original_deadline']))['deadline_at_ms']
         and phase['original_deadline_at_ms'] <= phase['created_at_ms'],
         'unpaid resume lost its genuinely returned expired original paid proposal')
    payment_receipt(root, rows[0], phase['proposal'])
    return phase


def retained_proposal_resume_remaining_seconds(root, profile, task):
    need(retained_proposal_resume_enabled(profile, task), 'retained-proposal resume disabled')
    phase = _resume_phase(root, profile, task)
    remaining = (phase['deadline_at_ms'] - int(time.time() * 1000)) // 1000
    need(remaining > 0, 'retained-proposal resume absolute deadline exhausted')
    return remaining


def _start_retained_proposal_resume(root, profile, spec, task):
    name = _resume_name(profile, task)
    if physical(root, name).exists():
        retained_proposal_resume_remaining_seconds(root, profile, task)
        return _resume_phase(root, profile, task)
    directory = _feedback_directory(profile, task)
    need(not physical(root, directory + '/source-only-result.json').exists(), 'source-only result already exists')
    proposal, lineage = _retained_paid_proposal(root, profile, spec, task)
    before = {edit['path']: edit['before_sha256'] for edit in proposal['response']['edits']}
    current = _current_sources(root, task)
    application = directory + '/application-intent.json'
    if physical(root, application).exists():
        saved = parse(read(root, application))
        need(saved['proposal'] == lineage['proposal'], 'retained application proposal changed')
        checked_application(root, profile, task, saved, proposal)
        need(all(current[name] in {saved['before'][name], saved['after'][name]} for name in task['edit_paths']),
             'foreign source drift before retained application resume')
    else:
        need(all(current[name] == want for name, want in before.items()),
             'retained proposal source before hashes no longer match')
    assert_no_hold(root, profile)
    now = int(time.time() * 1000)
    phase = {'schema': RESUME_SCHEMA, 'task_id': task['task_id'], 'task_sha256': digest(task),
             'policy': profile['retainedProposalResume'], 'policy_sha256': digest(profile['retainedProposalResume']),
             **lineage, 'source_at_start': current, 'created_at_ms': now, 'deadline_at_ms': now + 900000,
             'max_paid_calls': 0, 'completion_authority': False, 'work_complete': False}
    atomic(root, name, wire(phase) + b'\n', exclusive=True)
    anchor = {'schema': RESUME_SCHEMA, 'task_id': task['task_id'], 'phase': ref(root, name),
              'deadline_at_ms': phase['deadline_at_ms'], 'max_paid_calls': 0, 'completion_authority': False}
    atomic(root, _resume_name(profile, task, 'start.json'), wire(anchor) + b'\n', exclusive=True)
    return _resume_phase(root, profile, task)


def _apply_retained_proposal(root, profile, task, proposal, phase, *, apply_edits, ensure_lease, check_owned, remember_owned):
    directory = _feedback_directory(profile, task)
    intent_name = directory + '/application-intent.json'
    if physical(root, intent_name).exists():
        application = parse(read(root, intent_name))
        need(application['proposal'] == phase['proposal'], 'retained application proposal rebound')
    else:
        ensure_lease(profile); check_owned(profile, task['edit_paths'])
        before, original_bytes, retained = {}, {}, {}
        for index, name in enumerate(task['edit_paths']):
            raw = read(root, name, 250000) if physical(root, name).exists() else b''
            before[name] = hashlib.sha256(raw).hexdigest() if raw else None
            original_bytes[name] = raw
            saved = directory + '/original-source-' + str(index) + '.txt'
            immutable(root, saved, raw)
            retained[name] = {'path': saved, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        from swissknife_visual_functional_recovery import proposal_after
        application = {'schema': SCHEMA, 'proposal': phase['proposal'], 'before': before,
                       'after': proposal_after(root, proposal, task['edit_paths'], before, original_bytes),
                       'original_sources': retained, 'completion_authority': False}
        atomic(root, intent_name, wire(application) + b'\n', exclusive=True)
    checked_application(root, profile, task, application, proposal)
    current = _current_sources(root, task)
    need(all(current[name] in {application['before'][name], application['after'][name]} for name in task['edit_paths']),
         'foreign source drift during retained proposal application')
    ledger_name = profile['runtimeRoot'] + '/owned-source-hashes.json'
    ledger = parse(read(root, ledger_name))
    need(all(ledger.get(name) in {application['before'][name], application['after'][name]} for name in task['edit_paths']),
         'foreign ledger drift during retained proposal application')
    pending = [name for name in task['edit_paths'] if current[name] != application['after'][name]]
    retained_proposal_resume_remaining_seconds(root, profile, task)
    ensure_lease(profile)
    if pending:
        check_owned(profile, pending)
        apply_edits(root, [edit for edit in proposal['response']['edits'] if edit['path'] in pending], pending,
                    lease_check=lambda: ensure_lease(profile))
    need(_current_sources(root, task) == application['after'], 'retained application output differs from exact paid proposal')
    changed = [name for name in task['edit_paths'] if application['before'][name] != application['after'][name]]
    if changed:
        remember_owned(profile, changed)
    atomic(root, directory + '/application.json', wire(application) + b'\n')
    _resume_phase(root, profile, task)
    return application


def execute_retained_proposal_resume(root, profile_path, profile, spec, task, *, producer_failure_context=None, **kwargs):
    with _mode(FINAL_MODE):
        phase = _start_retained_proposal_resume(root, profile, spec, task)
        _, parent, _ = child_contract(root, profile, spec, task)
        claim_name = _resume_name(profile, task, 'producer-claim.json')
        need(not physical(root, claim_name).exists(), 'unpaid resumed producer outcome unknown; never rerun unchanged source')
        proposal = parse(check_ref(root, phase['proposal']))
        application = _apply_retained_proposal(root, profile, task, proposal, phase,
            **{key: kwargs[key] for key in ('apply_edits', 'ensure_lease', 'check_owned', 'remember_owned')})
        claim = {'schema': RESUME_SCHEMA, 'task_id': task['task_id'], 'phase': ref(root, _resume_name(profile, task)),
                 'deadline_at_ms': phase['deadline_at_ms'],
                 'application': ref(root, _feedback_directory(profile, task) + '/application.json'),
                 'max_paid_calls': 0, 'completion_authority': False}
        atomic(root, claim_name, wire(claim) + b'\n', exclusive=True)
        remaining = retained_proposal_resume_remaining_seconds(root, profile, task)
        try:
            files, checks = kwargs['workflow'](profile, parent,
                physical(root, profile['runtimeRoot'] + '/tasks/' + parent['task_id'] + '/verification'),
                timeout_seconds=min(1200, remaining))
        except Exception as error:
            if getattr(error, 'producer_failure_record', None) is None or getattr(error, 'producer_check', None) is None:
                raise
            trigger = {'initial_proposal': phase['proposal'], 'initial_application': claim['application'],
                       'failure_record': error.producer_failure_record, 'producer_check': error.producer_check}
            atomic(root, _resume_name(profile, task, 'producer-failed.json'), wire(trigger) + b'\n', exclusive=True)
            if not producer_feedback_enabled(profile, task):
                raise
            _producer_check(profile, parent, error.producer_check)
            _start_producer_supplement(root, profile, spec, task, error.producer_failure_record)
            atomic(root, _feedback_directory(profile, task) + '/producer-feedback-intent.json', wire(trigger) + b'\n', exclusive=True)
            packet = _prepare_producer_feedback(root, profile, spec, task, producer_failure_context, trigger)
            return _execute_producer_feedback(root, profile_path, profile, spec, task, packet, **kwargs)
        report = files[0]
        need(kwargs['validate_workflow'](profile, parent, report) is not None,
             'unpaid retained proposal resume lacks strict current two-view producer')
        _workflow_check(profile, parent, report, checks)
        _resume_phase(root, profile, task)
        result = {'schema': SCHEMA, 'task_id': task['task_id'], 'scope': 'source_remediation_only',
                  'original_task_id': parent['task_id'], 'original_task_sha256': digest(parent),
                  'workflow': ref(root, str(report.relative_to(root))), 'workflow_checks': checks,
                  'proposal': phase['proposal'], 'application': claim['application'], 'payments': phase['payments'],
                  'assessment': None, 'obsolete_gap': False, 'retained_proposal_phase': ref(root, _resume_name(profile, task)),
                  'work_complete': False, 'completion_authority': False}
        name = _feedback_directory(profile, task) + '/source-only-result.json'
        atomic(root, name, wire(result) + b'\n', exclusive=True)
        closure = {'schema': RESUME_SCHEMA, 'task_id': task['task_id'], 'phase': result['retained_proposal_phase'],
                   'producer_claim': ref(root, claim_name), 'result': ref(root, name), 'workflow': result['workflow'],
                   'paid_calls': 0, 'closed': True, 'work_complete': False, 'completion_authority': False}
        atomic(root, _resume_name(profile, task, 'result.json'), wire(closure) + b'\n', exclusive=True)
        return [physical(root, name), physical(root, phase['proposal']['path'])], checks, {
            'source_only_remediation': ref(root, name), 'original_acceptance_downstream': True,
            'paid_limits': {'assessment': 1, 'proposal': 1}, 'retained_resume_paid_calls': 0}



def _validate_saved_final_failure(root, profile, original, value):
    from swissknife_visual_functional_final_coverage import FAILURE_SCHEMA, task_identity, review_join
    need(type(value) is dict and set(value) == {'schema', 'task_id', 'app_id', 'task_contract',
         'identity', 'evidence', 'failed_review', 'work_complete', 'completion_authority'}
         and value['schema'] == FAILURE_SCHEMA and value['task_id'] == original['task_id']
         and value['app_id'] == original['app_id'] and value['work_complete'] is False
         and value['completion_authority'] is False
         and value['task_contract'] == {key: data for key, data in original.items() if key != 'status'}
         and value['identity']['task_semantics_sha256'] == task_identity(original),
         'completed child historical final fence identity changed')
    review = parse(check_ref(root, value['failed_review']))
    need(review.get('success') is True and review.get('task_id') == original['task_id']
         and review.get('mode') == 'review' and review.get('provider') == 'grok_cli'
         and review.get('model') == 'grok-4.7' and review.get('response', {}).get('decision') == 'needs_changes',
         'completed child historical review is not its genuine negative')
    review_join(root, profile, original, value['evidence'], physical(root, value['failed_review']['path']), require_pass=False)
    return value


KEYBOARD_NORMALIZATION_SCHEMA = 'swissknife.keyboard-confirmation-normalization.v1'
KEYBOARD_RESULT_ERROR = 'keyboard actions need their own subsequent observed semantic result'


def keyboard_confirmation_normalization_enabled(profile, task=None):
    value = profile.get('keyboardConfirmationNormalization')
    if value is None:
        return False
    expected = {'schema': KEYBOARD_NORMALIZATION_SCHEMA, 'enabled': True,
                'max_normalizations_per_child': 1, 'max_paid_calls': 0, 'timeout_seconds': 900}
    need(type(value) is dict and type(value.get('enabled')) is bool
         and wire({**value, 'enabled': True}) == wire(expected), 'keyboard normalization opt-in expanded')
    return value['enabled'] and (task is None or task.get('phase_remediation', {}).get('mode') == FINAL_MODE)


def _keyboard_name(profile, task, tail):
    return _feedback_directory(profile, task) + '/keyboard-confirmation-normalization-' + tail


def normalize_keyboard_confirmations(scenario):
    """Replace only the intervening real confirmation click in an exact key sequence."""
    need(type(scenario) is dict and scenario.get('schema') == 'swissknife.visual-functional-scenario.v1'
         and type(scenario.get('phases')) is dict, 'keyboard normalization needs an exact supported scenario')
    result = parse(wire(scenario))
    bindings = {row['binding_id'] for row in scenario.get('backend_bindings', [])
                if type(row) is dict and row.get('consent') == 'ui_required'}
    changes = []
    for phase, steps in scenario['phases'].items():
        need(type(steps) is list and all(type(step) is dict for step in steps), 'keyboard phase is not a bounded step list')
        for index, step in enumerate(steps):
            if index < 2 or set(step) != {'op', 'selector'} or step['op'] != 'click':
                continue
            match = re.fullmatch(r'\[data-gateway-confirm="([A-Za-z0-9_.:-]+)"\]', step['selector'])
            if match is None or match.group(1) not in bindings:
                continue
            key, wait = steps[index - 2:index]
            if not (key.get('op') == 'press' and key.get('key') == 'Enter'
                    and type(key.get('selector')) is str and key['selector'] != step['selector']
                    and wait.get('op') == 'wait_for' and wait.get('selector') == step['selector']
                    and wait.get('state') == 'visible'):
                continue
            following = steps[index + 1:]
            semantic = next((later for later in following if later.get('requirement_id')), None)
            if semantic is None or semantic.get('op') != 'assert':
                continue
            semantic_index = next(i for i, later in enumerate(following) if later is semantic)
            if any(later.get('op') not in {'assert', 'capture', 'wait_ms', 'wait_for'} for later in following[:semantic_index]):
                continue
            replacement = {'op': 'press', 'selector': step['selector'], 'key': 'Enter'}
            result['phases'][phase][index] = replacement
            changes.append({'phase': phase, 'step_index': index, 'before': step, 'after': replacement})
    need(changes, 'no exact keyboard/visible-confirmation/semantic sequence to normalize')
    # This inverse also protects unknown scalar, native-binding and assertion fields.
    inverse = parse(wire(result))
    for row in changes:
        inverse['phases'][row['phase']][row['step_index']] = row['before']
    need(wire(inverse) == wire(scenario), 'keyboard normalization changed unrelated scenario data')
    return result, changes


def _keyboard_normalization_trigger(root, profile, spec, task, *, current=True):
    need(keyboard_confirmation_normalization_enabled(profile, task), 'keyboard normalization is not explicitly opted in')
    _, parent, _ = child_contract(root, profile, spec, task)
    directory = _feedback_directory(profile, task)
    if current:
        need(not physical(root, directory + '/receipt.json').exists(), 'completed child cannot acquire keyboard normalization')
    marker_ref = ref(root, directory + '/producer-repair-failed.json')
    marker = parse(check_ref(root, marker_ref))
    need(marker.get('schema') == FEEDBACK_SCHEMA and marker.get('completion_authority') is False,
         'normalization needs the retained failed corrected producer marker')
    packet = validate_producer_feedback(root, profile, spec, task, current=False)
    proposal_ref = ref(root, directory + '/producer-repair-proposal.json')
    application_ref = ref(root, directory + '/producer-repair-application.json')
    need(marker.get('application') == application_ref, 'keyboard failure is not the exact paid feedback application')
    from swissknife_visual_functional_llm import validate_model_receipt
    proposal = parse(check_ref(root, proposal_ref))
    validate_model_receipt(root, proposal, task_id=task['task_id'], mode='repair', predicted_files=task['edit_paths'])
    need(proposal['response']['decision'] == 'needs_changes' and proposal['response']['edits'],
         'normalization needs a genuine returned paid correction')
    application = parse(check_ref(root, application_ref))
    need(application['proposal'] == proposal_ref and application['feedback'] == ref(root, directory + '/producer-feedback.json')
         and application['before'] == packet['source_after'], 'paid keyboard correction source chain changed')
    checked_application(root, profile, task, application, proposal)
    paid = producer_repair_payments(root, profile, task)
    need(paid['spent'] == 1 and len(paid['history']) == 1 and paid['history'][0]['state'] == 'returned'
         and paid['history'][0].get('receipt') == proposal_ref, 'keyboard correction paid outcome is unknown')
    payment_receipt(root, paid['history'][0], proposal_ref)
    record_ref = marker.get('failure_record')
    record = parse(check_ref(root, record_ref))
    archive = physical(root, profile['runtimeRoot'] + '/tasks/' + parent['task_id'] + '/execution-failures')
    record_path = physical(root, record_ref['path'])
    need(record_path.parent == archive and re.fullmatch('[0-9a-f]{32}\\.json', record_path.name)
         and record.get('schema') == 'swissknife.visual-functional-execution-failure.v1'
         and record.get('task_id') == parent['task_id'] and record.get('stage') == 'workflow'
         and record.get('error', {}).get('code') == 'ValidationCommandError',
         'normalization requires a real immutable checked producer failure')
    attempt = Path(_producer_check(profile, parent, marker['producer_check']))
    need(attempt.is_absolute() and attempt.is_relative_to(Path(root)), 'keyboard producer attempt escaped root')
    driver_ref = record.get('driver_failure')
    driver = parse(check_ref(root, driver_ref))
    need(physical(root, driver_ref['path']).is_relative_to(attempt)
         and driver.get('schema') == 'swissknife.visual-functional-workflow-failure.v1'
         and driver.get('app_id') == parent['app_id'] and driver.get('actual_desktop') is True
         and driver.get('error', {}).get('code') == 'MISSING_POSTCONDITION'
         and driver.get('error', {}).get('message') == KEYBOARD_RESULT_ERROR
         and type(driver.get('source_sha256')) is dict
         and all(driver['source_sha256'].get(name) == want for name, want in application['after'].items()),
         'not the exact current keyboard-result producer failure')
    need(record['error']['message'] == 'command exit ' + str(marker['producer_check']['exit_code']) + ': ' + marker['producer_check']['output_tail'],
         'keyboard failure output differs from its trusted checked command')
    if current:
        need(_current_sources(root, task) == application['after'], 'keyboard failure product source is stale')
    for name, old in driver['source_sha256'].items():
        if name in application['after']:
            continue
        now = hashlib.sha256(read(root, name, 16777216)).hexdigest()
        need(now == old or name in REQUALIFIABLE_CONTROLLERS, 'keyboard failure has unrelated stale source: ' + name)
    scenario = 'swissknife/test/e2e/functional-workflows/' + task['app_id'] + '.json'
    need(scenario in task['edit_paths'], 'keyboard normalization scenario is outside declared source scope')
    return {'marker': marker_ref, 'failure_record': record_ref, 'driver_failure': driver_ref,
            'feedback': ref(root, directory + '/producer-feedback.json'), 'proposal': proposal_ref,
            'application': application_ref, 'producer_payments': ref(root, directory + '/producer-repair-payments.json'),
            'original_payments': ref(root, payment_path(profile, task)),
            'original_deadline': ref(root, directory + '/execution-deadline.json'),
            'source_before': application['after'], 'scenario': scenario}


def _keyboard_phase(root, profile, task):
    name = _keyboard_name(profile, task, 'phase.json')
    phase = parse(read(root, name))
    need(phase.get('schema') == KEYBOARD_NORMALIZATION_SCHEMA and phase.get('task_id') == task['task_id']
         and phase.get('task_sha256') == digest(task) and phase.get('policy') == profile.get('keyboardConfirmationNormalization')
         and phase.get('policy_sha256') == digest(profile['keyboardConfirmationNormalization'])
         and type(phase.get('created_at_ms')) is int and type(phase.get('deadline_at_ms')) is int
         and phase['deadline_at_ms'] == phase['created_at_ms'] + 900000
         and phase.get('max_paid_calls') == 0 and type(phase['max_paid_calls']) is int,
         'keyboard normalization phase/clock changed')
    anchor = parse(read(root, _keyboard_name(profile, task, 'start.json')))
    need(anchor == {'schema': KEYBOARD_NORMALIZATION_SCHEMA, 'task_id': task['task_id'],
                    'phase': ref(root, name), 'deadline_at_ms': phase['deadline_at_ms'], 'completion_authority': False},
         'keyboard normalization clock was renewed/rebound')
    for key in ('marker', 'failure_record', 'driver_failure', 'feedback', 'proposal', 'application',
                'producer_payments', 'original_payments', 'original_deadline'):
        check_ref(root, phase['lineage'][key])
    before = check_ref(root, phase['scenario_before'])
    after = check_ref(root, phase['scenario_after'])
    candidate, changes = normalize_keyboard_confirmations(parse(before))
    scenario = phase['lineage']['scenario']
    need(after == (json.dumps(candidate, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
         and wire(changes) == wire(phase['changes']) and phase['source_before'] == phase['lineage']['source_before']
         and phase['source_after'] == {**phase['source_before'], scenario: hashlib.sha256(after).hexdigest()}
         and hashlib.sha256(before).hexdigest() == phase['source_before'][scenario],
         'keyboard normalization changed more than its exact allowed scenario rows')
    spec = parse(read(root, profile['taskSpecPath']))
    need(wire(phase['lineage']) == wire(_keyboard_normalization_trigger(root, profile, spec, task, current=False)),
         'keyboard normalization lost its genuine immutable paid producer failure')
    return phase


def keyboard_normalization_remaining_seconds(root, profile, task):
    need(keyboard_confirmation_normalization_enabled(profile, task), 'keyboard normalization disabled')
    remaining = (_keyboard_phase(root, profile, task)['deadline_at_ms'] - int(time.time() * 1000)) // 1000
    need(remaining > 0, 'keyboard normalization absolute deadline exhausted; no renewal')
    return remaining


def _start_keyboard_confirmation_normalization(root, profile, spec, task):
    name = _keyboard_name(profile, task, 'phase.json')
    if physical(root, name).exists():
        keyboard_normalization_remaining_seconds(root, profile, task)
        return _keyboard_phase(root, profile, task)
    lineage = _keyboard_normalization_trigger(root, profile, spec, task)
    need(not physical(root, _feedback_directory(profile, task) + '/source-only-result.json').exists(),
         'existing source-only result cannot acquire normalization')
    raw = read(root, lineage['scenario'], 250000)
    candidate, changes = normalize_keyboard_confirmations(parse(raw))
    normalized = (json.dumps(candidate, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    assert_no_hold(root, profile)
    before_name = _keyboard_name(profile, task, 'scenario-before.json')
    after_name = _keyboard_name(profile, task, 'scenario-after.json')
    immutable(root, before_name, raw)
    immutable(root, after_name, normalized)
    now = int(time.time() * 1000)
    phase = {'schema': KEYBOARD_NORMALIZATION_SCHEMA, 'task_id': task['task_id'], 'task_sha256': digest(task),
             'policy': profile['keyboardConfirmationNormalization'], 'policy_sha256': digest(profile['keyboardConfirmationNormalization']),
             'lineage': lineage, 'scenario_before': ref(root, before_name), 'scenario_after': ref(root, after_name),
             'source_before': lineage['source_before'],
             'source_after': {**lineage['source_before'], lineage['scenario']: hashlib.sha256(normalized).hexdigest()},
             'changes': changes, 'created_at_ms': now, 'deadline_at_ms': now + 900000,
             'max_paid_calls': 0, 'work_complete': False, 'completion_authority': False}
    atomic(root, name, wire(phase) + b'\n', exclusive=True)
    anchor = {'schema': KEYBOARD_NORMALIZATION_SCHEMA, 'task_id': task['task_id'],
              'phase': ref(root, name), 'deadline_at_ms': phase['deadline_at_ms'], 'completion_authority': False}
    atomic(root, _keyboard_name(profile, task, 'start.json'), wire(anchor) + b'\n', exclusive=True)
    return _keyboard_phase(root, profile, task)


def _keyboard_application(root, profile, task, phase, *, apply_edits, ensure_lease, check_owned, remember_owned):
    current = _current_sources(root, task)
    need(all(current[name] in {phase['source_before'][name], phase['source_after'][name]} for name in task['edit_paths']),
         'foreign product source during keyboard normalization')
    scenario = phase['lineage']['scenario']
    before, after = check_ref(root, phase['scenario_before']), check_ref(root, phase['scenario_after'])
    ledger = parse(read(root, profile['runtimeRoot'] + '/owned-source-hashes.json'))
    need(all(ledger.get(name) in {phase['source_before'][name], phase['source_after'][name]} for name in task['edit_paths']),
         'foreign owned ledger during keyboard normalization')
    keyboard_normalization_remaining_seconds(root, profile, task)
    ensure_lease(profile)
    if current[scenario] != phase['source_after'][scenario]:
        check_owned(profile, [scenario])
        edit = {'path': scenario, 'before_sha256': phase['source_before'][scenario],
                'old': before.decode(), 'new': after.decode()}
        apply_edits(root, [edit], [scenario], lease_check=lambda: ensure_lease(profile))
    need(_current_sources(root, task) == phase['source_after'], 'keyboard normalization CAS output differs')
    remember_owned(profile, [scenario])
    application = {'schema': KEYBOARD_NORMALIZATION_SCHEMA, 'task_id': task['task_id'],
                   'phase': ref(root, _keyboard_name(profile, task, 'phase.json')),
                   'paid_application': phase['lineage']['application'], 'before': phase['source_before'],
                   'after': phase['source_after'], 'changes': phase['changes'],
                   'paid_calls': 0, 'work_complete': False, 'completion_authority': False}
    name = _keyboard_name(profile, task, 'application.json')
    immutable(root, name, wire(application) + b'\n')
    _keyboard_phase(root, profile, task)
    return ref(root, name)


def execute_keyboard_confirmation_normalization(root, profile_path, profile, spec, task, **kwargs):
    with _mode(FINAL_MODE):
        phase = _start_keyboard_confirmation_normalization(root, profile, spec, task)
        _, parent, _ = child_contract(root, profile, spec, task)
        claim_name = _keyboard_name(profile, task, 'producer-claim.json')
        need(not physical(root, claim_name).exists(), 'normalized producer outcome unknown; never rerun unchanged source')
        application = _keyboard_application(root, profile, task, phase,
            **{key: kwargs[key] for key in ('apply_edits', 'ensure_lease', 'check_owned', 'remember_owned')})
        claim = {'schema': KEYBOARD_NORMALIZATION_SCHEMA, 'task_id': task['task_id'],
                 'phase': ref(root, _keyboard_name(profile, task, 'phase.json')),
                 'deadline_at_ms': phase['deadline_at_ms'], 'application': application,
                 'max_paid_calls': 0, 'completion_authority': False}
        atomic(root, claim_name, wire(claim) + b'\n', exclusive=True)
        try:
            files, checks = kwargs['workflow'](profile, parent,
                physical(root, profile['runtimeRoot'] + '/tasks/' + parent['task_id'] + '/verification'),
                timeout_seconds=min(1200, keyboard_normalization_remaining_seconds(root, profile, task)))
        except Exception as error:
            packet = {'schema': KEYBOARD_NORMALIZATION_SCHEMA, 'task_id': task['task_id'],
                      'producer_claim': ref(root, claim_name), 'error_type': type(error).__name__,
                      'completion_authority': False}
            if getattr(error, 'producer_failure_record', None) is not None:
                packet['failure_record'] = error.producer_failure_record
            immutable(root, _keyboard_name(profile, task, 'failed.json'), wire(packet) + b'\n')
            raise
        report = files[0]
        need(kwargs['validate_workflow'](profile, parent, report) is not None, 'normalization lacks strict current independent producer')
        _workflow_check(profile, parent, report, checks)
        _keyboard_phase(root, profile, task)
        lineage = phase['lineage']
        feedback = parse(check_ref(root, lineage['feedback']))
        result = {'schema': SCHEMA, 'task_id': task['task_id'], 'scope': 'source_remediation_only',
                  'original_task_id': parent['task_id'], 'original_task_sha256': digest(parent),
                  'workflow': ref(root, str(report.relative_to(root))), 'workflow_checks': checks,
                  'proposal': feedback['initial_proposal'], 'application': feedback['initial_application'],
                  'payments': lineage['original_payments'], 'assessment': None, 'obsolete_gap': False,
                  'producer_repair': {key: lineage[key] for key in ('feedback', 'proposal', 'application')},
                  'keyboard_confirmation_normalization': {'phase': ref(root, _keyboard_name(profile, task, 'phase.json')),
                                                        'application': application},
                  'work_complete': False, 'completion_authority': False}
        result['producer_repair']['payments'] = lineage['producer_payments']
        name = _feedback_directory(profile, task) + '/source-only-result.json'
        atomic(root, name, wire(result) + b'\n', exclusive=True)
        _keyboard_normalization_closure(root, profile, task, ref(root, name), result, create=True)
        return [physical(root, name), physical(root, lineage['proposal']['path'])], checks, {
            'source_only_remediation': ref(root, name), 'original_acceptance_downstream': True,
            'paid_limits': {'assessment': 1, 'proposal': 1, 'producer_repair': 1}, 'normalization_paid_calls': 0}


def _keyboard_normalization_closure(root, profile, task, result_ref, result, *, create=False):
    phase = _keyboard_phase(root, profile, task)
    claim_name = _keyboard_name(profile, task, 'producer-claim.json')
    claim = parse(read(root, claim_name))
    repair = result['keyboard_confirmation_normalization']
    need(claim == {'schema': KEYBOARD_NORMALIZATION_SCHEMA, 'task_id': task['task_id'],
                   'phase': ref(root, _keyboard_name(profile, task, 'phase.json')),
                   'deadline_at_ms': phase['deadline_at_ms'], 'application': repair['application'],
                   'max_paid_calls': 0, 'completion_authority': False},
         'normalized producer claim/deadline/application changed')
    expected = {'schema': KEYBOARD_NORMALIZATION_SCHEMA, 'task_id': task['task_id'],
                'phase': repair['phase'], 'producer_claim': ref(root, claim_name),
                'result': result_ref, 'workflow': result['workflow'], 'paid_calls': 0,
                'closed': True, 'work_complete': False, 'completion_authority': False}
    name = _keyboard_name(profile, task, 'result.json')
    if create and not physical(root, name).exists():
        atomic(root, name, wire(expected) + b'\n', exclusive=True)
    need(wire(parse(read(root, name))) == wire(expected), 'keyboard normalization closure changed')
    return expected


def _keyboard_normalization_result_chain(root, profile, spec, task, receipt, *, close=False):
    parent, value = _source_result(root, profile, spec, task, receipt)
    phase = _keyboard_phase(root, profile, task)
    lineage = _keyboard_normalization_trigger(root, profile, spec, task, current=False)
    need(wire(lineage) == wire(phase['lineage']), 'normalized historical paid/failure chain changed')
    feedback = parse(check_ref(root, lineage['feedback']))
    repair = value.get('keyboard_confirmation_normalization')
    need(type(repair) is dict and set(repair) == {'phase', 'application'}
         and repair['phase'] == ref(root, _keyboard_name(profile, task, 'phase.json'))
         and repair['application'] == ref(root, _keyboard_name(profile, task, 'application.json'))
         and value['proposal'] == feedback['initial_proposal'] and value['application'] == feedback['initial_application']
         and value['payments'] == lineage['original_payments'] and value.get('obsolete_gap') is False
         and value.get('producer_repair') == {'feedback': lineage['feedback'], 'proposal': lineage['proposal'],
                                            'application': lineage['application'], 'payments': lineage['producer_payments']},
         'normalization result rebound the immutable paid application')
    application = parse(check_ref(root, repair['application']))
    expected = {'schema': KEYBOARD_NORMALIZATION_SCHEMA, 'task_id': task['task_id'], 'phase': repair['phase'],
                'paid_application': lineage['application'], 'before': phase['source_before'], 'after': phase['source_after'],
                'changes': phase['changes'], 'paid_calls': 0, 'work_complete': False, 'completion_authority': False}
    need(wire(application) == wire(expected), 'normalization application is not the exact separately authorized SC transform')
    if not close:
        _keyboard_normalization_closure(root, profile, task, receipt['detail']['source_only_remediation'], value)
    return parent, value, application


def validate_keyboard_normalization_result(root, profile, spec, task, receipt, *, validate_workflow, close=False):
    parent, value, application = _keyboard_normalization_result_chain(root, profile, spec, task, receipt, close=close)
    need(_current_sources(root, task) == application['after'], 'normalized current source no longer matches its CAS')
    report = physical(root, value['workflow']['path'])
    check_ref(root, value['workflow'])
    _workflow_check(profile, parent, report, value['workflow_checks'])
    need(receipt.get('checks') == value['workflow_checks'] and validate_workflow(profile, parent, report) is not None,
         'normalization result lacks strict current independent producer')
    _keyboard_normalization_closure(root, profile, task, receipt['detail']['source_only_remediation'], value, create=close)
    return value


_before_keyboard_execute_child = execute_child
_before_keyboard_validate_child_result = validate_child_result
_before_keyboard_child_can_still_write = child_can_still_write
_before_keyboard_recoverable_owned_source = recoverable_owned_source


def execute_child(root, profile_path, profile, spec, task, *, producer_failure_context=None, **kwargs):
    with _mode(_task_mode(task)):
        result_name = _feedback_directory(profile, task) + '/source-only-result.json'
        if physical(root, result_name).exists():
            value = parse(read(root, result_name))
            if value.get('keyboard_confirmation_normalization') is not None:
                synthetic = {'detail': {'source_only_remediation': ref(root, result_name)}, 'checks': value['workflow_checks']}
                validate_keyboard_normalization_result(root, profile, spec, task, synthetic,
                                                       validate_workflow=kwargs['validate_workflow'], close=True)
                return [physical(root, result_name), physical(root, value['producer_repair']['proposal']['path'])], value['workflow_checks'], {
                    'source_only_remediation': ref(root, result_name), 'original_acceptance_downstream': True,
                    'paid_limits': {'assessment': 1, 'proposal': 1, 'producer_repair': 1}, 'normalization_paid_calls': 0}
        if keyboard_confirmation_normalization_enabled(profile, task):
            directory = _feedback_directory(profile, task)
            if physical(root, _keyboard_name(profile, task, 'phase.json')).exists() or physical(root, directory + '/producer-repair-failed.json').exists():
                return execute_keyboard_confirmation_normalization(root, profile_path, profile, spec, task, **kwargs)
        return _before_keyboard_execute_child(root, profile_path, profile, spec, task,
                                               producer_failure_context=producer_failure_context, **kwargs)


def validate_child_result(root, profile, spec, task, receipt, *, validate_workflow):
    value = parse(check_ref(root, receipt['detail']['source_only_remediation']))
    if value.get('keyboard_confirmation_normalization') is not None:
        return validate_keyboard_normalization_result(root, profile, spec, task, receipt, validate_workflow=validate_workflow)
    return _before_keyboard_validate_child_result(root, profile, spec, task, receipt, validate_workflow=validate_workflow)


def child_can_still_write(root, profile, task):
    if keyboard_confirmation_normalization_enabled(profile, task):
        phase_name = _keyboard_name(profile, task, 'phase.json')
        if physical(root, phase_name).exists():
            try:
                keyboard_normalization_remaining_seconds(root, profile, task)
                if physical(root, _keyboard_name(profile, task, 'producer-claim.json')).exists():
                    return False
                phase = _keyboard_phase(root, profile, task)
                return _current_sources(root, task) != phase['source_after']
            except (ValueError, OSError, KeyError, TypeError):
                return False
        marker = _feedback_directory(profile, task) + '/producer-repair-failed.json'
        if physical(root, marker).exists():
            try:
                spec = parse(read(root, profile['taskSpecPath']))
                lineage = _keyboard_normalization_trigger(root, profile, spec, task)
                normalize_keyboard_confirmations(parse(read(root, lineage['scenario'], 250000)))
                return True
            except (ValueError, OSError, KeyError, TypeError):
                return False
    return _before_keyboard_child_can_still_write(root, profile, task)


def recoverable_owned_source(root, profile, task_id, name):
    spec = parse(read(root, profile['taskSpecPath']))
    task = next((item for item in spec['tasks'] if item['task_id'] == task_id), None)
    if (task is not None and keyboard_confirmation_normalization_enabled(profile, task)
            and physical(root, _keyboard_name(profile, task, 'phase.json')).exists()):
        phase = _keyboard_phase(root, profile, task)
        if name == phase['lineage']['scenario']:
            child_contract(root, profile, spec, task)
            actual = _current_sources(root, task)
            ledger = parse(read(root, profile['runtimeRoot'] + '/owned-source-hashes.json'))
            need(all(actual[path] in {phase['source_before'][path], phase['source_after'][path]}
                     and ledger.get(path) in {phase['source_before'][path], phase['source_after'][path]}
                     for path in task['edit_paths']), 'foreign source/ledger drift in own normalization CAS')
            return True
    return _before_keyboard_recoverable_owned_source(root, profile, task_id, name)

