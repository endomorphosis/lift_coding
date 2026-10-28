"""Finite phase remediation admission; original acceptance/history stay authoritative.

Native plan revisions operate on an owned metadata projection, never on the live
board. The separate CAS publisher rolls forward its exact before/after bytes and
refuses foreign changes. A derived task may make one paid source proposal; it
cannot create another child, refund the original phase, or complete its parent.
"""
from __future__ import annotations
from contextlib import contextmanager
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



def policy_enabled(profile):
    value = profile.get('phaseRemediation')
    if value is None: return False
    expected = {'schema':SCHEMA,'enabled':True,'max_originals':45,'max_children_per_phase':1,
                'max_paid_assessments':1,'max_paid_proposals':1,'child_timeout_seconds':3600}
    need(type(value) is dict and type(value.get('enabled')) is bool
         and wire({**value,'enabled':True}) == wire(expected), 'phase remediation opt-in policy expanded')
    return value['enabled']


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
    return profile['runtimeRoot'] + '/state/phase-remediation'


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
    tasks = [t for t in spec['tasks'] if t.get('kind') == 'verify' and t.get('app_id')]
    need({t['task_id']:t['app_id'] for t in tasks} == ORIGINAL_APPS
         and len(tasks) == MAX_ORIGINALS and len({t['task_id'] for t in tasks}) == MAX_ORIGINALS
         and len({t['app_id'] for t in tasks}) == MAX_ORIGINALS
         and all(re.fullmatch(r'SVF-[0-9]+', t['task_id']) for t in tasks), 'original verification allowlist changed')
    return {t['task_id']: t for t in tasks}


def gap_key(profile, task):
    return digest({'campaign': profile['runtimeRoot'], 'task_id': task['task_id'], 'phase': PHASE})


def child_id(task):
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
    allowed = [p for p in original.get('edit_paths', []) if p == scenario
               or p == 'swissknife/web/js/main-simple.js'
               or p == 'swissknife/web/js/apps/' + app + '.js'
               or p == 'swissknife/web/css/' + app + '.css']
    need(allowed and set(allowed) <= set(original['edit_paths']), 'no declared application/scenario remediation scope')
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
    need(ORIGINAL_APPS.get(original['task_id']) == original['app_id']
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
    expected_task = task['task_id'] if role == 'proposal' else task['phase_remediation']['original_task']['task_id']
    need(admission['task_id'] == expected_task and admission['mode'] == ('repair' if role == 'proposal' else 'review'), 'payment role/task/mode differs')
    directory = physical(root, profile['runtimeRoot']+'/tasks/'+expected_task)
    output = physical(root, admission['output_path'])
    need(output.is_relative_to(directory) and output.name == ('proposal.json' if role == 'proposal' else 'visual-review.json'), 'payment output escaped its role')
    if role == 'proposal': need(output.parent == directory, 'proposal output path differs')
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
        journal = physical(root, profile['runtimeRoot']+'/tasks/'+identity+'/required-phase-repair-budget.json')
        if not journal.exists(): continue
        try:
            phase = parse(read(root, str(journal.relative_to(root))))
            if phase.get('state') != 'exhausted': continue
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
