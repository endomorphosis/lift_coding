#!/usr/bin/env python3
"""Read-only verification of retained no-model cgroup diagnostic evidence."""
import hashlib
import json
from pathlib import Path
import subprocess

from cgroup_observation import retained_parent_check
from qualify_observation import exact_absence, owned

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def main():
    manifest = read(HERE / 'kernel_probe_inventory.json')
    for relative, binding in manifest['files'].items():
        path = HERE / relative
        assert path.resolve().is_relative_to(HERE) and not path.is_symlink()
        assert path.stat().st_size == binding['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding['sha256'], relative
    cpu_total = 0
    for version in ('v1', 'v2'):
        root = HERE / ('kernel_probe_' + version)
        result = read(root / 'qualification.json')
        assert result['model_calls'] == result['scientific_cases_executed'] == 0
        assert result['historical_LA030_failure_cause_proven'] is False
        for name, digest in result['sources'].items():
            assert hashlib.sha256((root / 'source' / name).read_bytes()).hexdigest() == digest
            if version == 'v2':
                assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest
        created, terminal = read(root / 'created.json'), read(root / 'terminal.json')
        cid = created['Id']
        for data in (created, terminal):
            owned(data, cid, result['name'], result['label'], Path(result['parent']).name)
        assert not terminal['State']['Running'] and terminal['State']['Pid'] == 0
        assert terminal['State']['ExitCode'] == 0 and not terminal['State']['OOMKilled']
        before, after = read(root / 'parent_before.json'), read(root / 'parent_after.json')
        retained_parent_check(before, after)
        probe = read(root / 'stale_descriptor_probe.json')
        detail = probe['detail']
        assert probe['status'] == 'kernel_read_failed' and detail['errno'] == 19
        assert detail['operation'] == 'read_preopened_controller_file_after_terminal_exit'
        assert detail['path'].endswith('/cpu.stat')
        assert detail['initial_identity'] == detail['open_directory_identity']
        assert detail['current_path_identity']['errno'] == 2
        assert Path(detail['directory']).parent == Path(result['parent'])
        observations = read(root / 'leaf_poll_observations.json')
        assert len(observations['samples']) == result['ordinary_poll_samples']
        assert len(observations['errors']) == result['ordinary_poll_errors'] == 0
        if version == 'v1':
            assert result['status'] == 'FAILED' and result['cleanup_error_type'] == 'AssertionError'
            reconciled = read(root / 'cleanup_reconciliation.json')
            absence, final = reconciled['inspect'], reconciled['final_parent']
            assert reconciled['exact_container_absent']
        else:
            assert result['status'] == 'PASS_FOR_DIAGNOSTICS_ONLY'
            assert result['exact_container_cleanup_proven']
            absence, final = read(root / 'absent_result.json'), read(root / 'parent_after_cleanup.json')
        actual = subprocess.CompletedProcess([], absence['returncode'],
                                             absence['stdout'].encode(), absence['stderr'].encode())
        assert exact_absence(actual, cid)
        retained_parent_check(before, final)
        assert final['cpu_usage_seconds'] <= 20 and int(final['memory.peak']) <= 2147483648
        cpu_total += final['cpu_usage_seconds']
    print(json.dumps({'status': 'PASS_FOR_RETAINED_DIAGNOSTICS_ONLY', 'artifact_hashes': len(manifest['files']),
                      'actual_constructed_container_executions': 2, 'model_calls': 0,
                      'scientific_cases_executed': 0, 'reproduced_stale_controller_read_errno': 19,
                      'descendant_cpu_seconds_across_both_probes': round(cpu_total, 6),
                      'historical_LA030_failure_cause_proven': False,
                      'automatic_leaf_failure_admission': False}))


if __name__ == '__main__':
    main()
