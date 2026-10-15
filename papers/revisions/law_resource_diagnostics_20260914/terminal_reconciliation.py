"""Narrow ENODEV reconciliation from independently retained terminal evidence.

This returns a resource-accounting decision, never candidate/task admission.
All inputs must come from the trusted host observer, not the candidate.
"""
import errno
from pathlib import Path
import re

from cgroup_observation import LEAF_FIELDS, retained_parent_check


def reconcile_enodev(detail, last_leaf, parent_before, parent_final, terminal, *,
                     container_id, parent_path, leaf_path):
    if not re.fullmatch(r'[0-9a-f]{64}', container_id):
        raise ValueError('Exact Docker container identity required')
    parent, leaf = Path(parent_path), Path(leaf_path)
    if not parent.is_absolute() or leaf.parent != parent or leaf.name != 'docker-' + container_id + '.scope':
        raise ValueError('Expected Docker leaf is outside its retained parent')
    if terminal['Id'] != container_id or terminal['HostConfig']['CgroupParent'] != parent.name:
        raise ValueError('Terminal container or parent identity differs')
    state = terminal['State']
    if state['Running'] is not False or state['Pid'] != 0 or state['ExitCode'] != 0 or state['OOMKilled']:
        raise ValueError('Successful whole-container termination is unproven')
    path = Path(detail['path'])
    if detail['directory'] != str(leaf) or path.parent != leaf or path.name not in LEAF_FIELDS:
        raise ValueError('Read failure belongs to another controller or leaf')
    if detail['errno'] != errno.ENODEV or detail['operation'] not in (
            'read_controller_file', 'read_preopened_controller_file_after_terminal_exit'):
        raise ValueError('This version reconciles only the reproduced ENODEV read condition')
    if detail['current_path_identity'] != {'error_type': 'FileNotFoundError', 'errno': errno.ENOENT}:
        raise ValueError('Leaf removal is not established; replacement and access failures remain fatal')
    if detail['initial_identity'] != detail['open_directory_identity'] or detail['initial_identity'] != last_leaf['identity']:
        raise ValueError('Previously sampled and held leaf identities differ')
    if not last_leaf['observed_monotonic'] <= detail['observed_monotonic'] <= parent_final['observed_monotonic']:
        raise ValueError('Fresh parent accounting after the failed read is required')
    if parent_final['observed_monotonic'] < parent_before['observed_monotonic']:
        raise ValueError('Parent observation order regressed')
    checks = retained_parent_check(parent_before, parent_final)
    if (parent_final['cpu_usage_seconds'] < last_leaf['cpu_usage_seconds']
            or int(parent_final['memory.peak']) < int(last_leaf['memory.peak'])):
        raise ValueError('Final parent accounting does not cover the sampled leaf costs')
    for counter, forbidden in (('memory.events', ('max', 'oom', 'oom_kill')),
                               ('pids.events', ('max',))):
        events = dict(line.split() for line in parent_final[counter].splitlines())
        if any(int(events.get(key, 0)) for key in forbidden):
            raise ValueError('Resource-limit events are present')
    return {'decision': 'use_verified_retained_parent_accounting_after_leaf_removal',
            'parent_checks': checks, 'failed_leaf_read_retained': detail,
            'descendant_cpu_seconds': parent_final['cpu_usage_seconds'],
            'descendant_memory_peak_bytes': int(parent_final['memory.peak']),
            'candidate_admission': False, 'scientific_completion': False,
            'caller_still_must_verify': ['exact image/labels/mounts and running leaf resource limits',
                                       'complete attempt wall/CPU limits and cleanup',
                                       'native authorization, effect and independent utility evidence']}
