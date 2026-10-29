"""Avoid repeated paid visual reviews of an unchanged, exhausted failed phase.

This is an admission fence only. Changed source is eligible for the original
workflow and review; no repair spend is refunded and no task is completed here.
The independent phase budget remains authoritative and is never edited here.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

SCHEMA = 'swissknife.exhausted-visual-review-source-fence.v1'


class UnchangedExhaustedVisualReview(ValueError):
    code = 'unchanged_exhausted_visual_review'


def _stable(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _source_contract(root, profile, task):
    from swissknife_visual_functional_phase_budget import _path, _read
    # Board progress and unrelated task metadata cannot buy another review.
    excluded = {profile.get('todoPath'), profile.get('objectivePath'), profile.get('taskSpecPath')}
    names = set(task.get('execution_inputs', []) + task.get('context_paths', []) + task.get('edit_paths', []))
    names.update(p for p in (profile.get('appContractPath'), 'config/swissknife_visual_functional_supervisor.json',
                           'config/swissknife_visual_functional_payload_fixtures.json') if p)
    sources = {}
    for name in sorted(names - excluded):
        path = _path(root, name)
        if path.exists():
            if not path.is_file():
                raise ValueError('review source closure must name regular files')
            sources[name] = hashlib.sha256(_read(root, name, 16 * 1024 * 1024)).hexdigest()
        else:
            sources[name] = None
    task_contract = {k: v for k, v in task.items() if k not in {'status'}}
    return _stable({'task': task_contract, 'sources': sources})


def _path(root, task):
    from swissknife_visual_functional_phase_budget import directory
    return directory(root, task) / 'exhausted-visual-review-source-fence.json'


def _phase(root, task):
    from swissknife_visual_functional_phase_budget import _journal, LIMIT
    with _journal(root, task) as (_, value):
        if value is None or value['state'] != 'exhausted' or value['spent'] < LIMIT:
            return None
        return {'spent': value['spent'], 'history_sha256': _stable(value['history'])}


def assert_recheck_allowed(root: Path, profile: dict, task: dict) -> None:
    from swissknife_visual_functional_phase_budget import _read, _review, PhaseBudgetError
    phase = _phase(root, task)
    if phase is None:
        return
    path = _path(root, task)
    if not path.exists() and not path.is_symlink():
        return  # Prior versions have no new evidence fence; qualify once.
    value = json.loads(_read(root, path))
    if (type(value) is not dict or set(value) != {'schema', 'task_id', 'phase', 'spent', 'history_sha256',
            'source_contract', 'failed_review', 'completion_authority', 'work_complete'}
            or value.get('schema') != SCHEMA or value.get('task_id') != task['task_id']
            or value.get('phase') != 'final_visual_review'
            or type(value.get('spent')) is not int
            or any(type(value.get(k)) is not str or not re.fullmatch('[0-9a-f]{64}', value[k])
                   for k in ('history_sha256', 'source_contract'))
            or value.get('completion_authority') is not False or value.get('work_complete') is not False):
        raise PhaseBudgetError('exhausted visual review source fence is malformed')
    _review(root, task, value['failed_review'])
    if phase != {k: value[k] for k in phase}:
        raise PhaseBudgetError('exhausted visual review fence does not match preserved phase history')
    if value['source_contract'] == _source_contract(root, profile, task):
        raise UnchangedExhaustedVisualReview(
            task['task_id'] + ': unchanged final visual failure with exhausted repair admissions; '
            'wait for scoped remediation, then run original workflow, visual review, and validator')


def remember_exhaustion(root: Path, profile: dict, task: dict, phase_record: dict) -> None:
    from swissknife_visual_functional_phase_budget import _review, _validate, _save, LIMIT
    _validate(phase_record, task)
    if phase_record['state'] != 'exhausted' or phase_record['spent'] < LIMIT:
        raise ValueError('cannot fence a non-exhausted phase')
    reference = phase_record['gap_request']['failed_review']
    _review(root, task, reference)
    phase = _phase(root, task)
    expected = {'spent': phase_record['spent'], 'history_sha256': _stable(phase_record['history'])}
    if phase != expected:
        raise ValueError('phase history changed before its source fence was recorded')
    value = {'schema': SCHEMA, 'task_id': task['task_id'], 'phase': 'final_visual_review',
             **expected, 'source_contract': _source_contract(root, profile, task),
             'failed_review': reference, 'work_complete': False, 'completion_authority': False}
    _save(_path(root, task), value)
