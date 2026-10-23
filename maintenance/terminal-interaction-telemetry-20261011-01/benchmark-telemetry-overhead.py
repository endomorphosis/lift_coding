#!/usr/bin/env python3
"""Authored local parser qualification; no native/provider transcripts are read.

All wall times are measured with tracemalloc enabled and are not estimates of
provider/model latency. Fixture creation is streamed outside measured regions.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
import types

SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
OLD_REVISION = 'fbe0681bc'
RELATIVE = 'ipfs_accelerate_py/agent_supervisor/runtime/codex_usage_receipt.py'
HELPER = 'ipfs_accelerate_py/agent_supervisor/runtime/codex_interaction_telemetry.py'
THREAD = 'authored-telemetry-benchmark-123456'
MEMORY_LIMIT = 512 * 1024 * 1024


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def memory_observation(stage):
    wanted = {'VmPeak', 'VmSize', 'VmHWM', 'VmRSS'}
    values = {}
    for line in Path('/proc/self/status').read_text().splitlines():
        key, _, value = line.partition(':')
        if key in wanted:
            values[key + '_bytes'] = int(value.split()[0]) * 1024
    return {'stage': stage, 'proc_status': values,
        'rusage_self_maxrss_linux_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_fixture(folder, *, pairs, padding_records):
    home = folder / 'authored-home'
    workspace = folder / 'authored-workspace'
    workspace.mkdir(parents=True)
    path = home / 'sessions/2026/10/11' / ('rollout-' + THREAD + '.jsonl')
    path.parent.mkdir(parents=True)
    count = 0
    with path.open('w', encoding='utf-8') as stream:
        def emit(row):
            nonlocal count
            stream.write(json.dumps(row, separators=(',', ':'), ensure_ascii=False) + '\n')
            count += 1
        emit({'type': 'session_meta', 'payload': {'id': THREAD, 'cwd': str(workspace)}})
        emit({'type': 'event_msg', 'payload': {'type': 'task_started'}})
        for index in range(pairs):
            emit({'type': 'response_item', 'payload': {
                'type': 'function_call', 'call_id': 'authored-call-' + str(index),
                'name': 'exec_command', 'arguments': '{"cmd":"printf authored-fixture"}'}})
            emit({'type': 'response_item', 'payload': {
                'type': 'function_call_output', 'call_id': 'authored-call-' + str(index),
                'output': 'Authored bounded tool output. ' * 8}})
            emit({'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {
                'total_token_usage': {'input_tokens': (index + 1) * 20,
                    'cached_input_tokens': (index + 1) * 5,
                    'cache_write_input_tokens': 0,
                    'output_tokens': (index + 1) * 2,
                    'reasoning_output_tokens': index + 1,
                    'total_tokens': (index + 1) * 22}}}})
        # Closed synthetic event marker carries no tool/usage semantics. It
        # crosses only the telemetry processing cap, not the file-reader cap.
        for _ in range(padding_records):
            emit({'type': 'event_msg', 'payload': {'type': 'authored_fixture_tick'}})
        emit({'type': 'event_msg', 'payload': {'type': 'task_complete'}})
    size = path.stat().st_size
    assert size < 32_000_000
    return home, workspace, {'bytes': size, 'records_including_session_meta': count,
        'tool_pairs': pairs, 'padding_records': padding_records,
        'sha256': digest(path.read_bytes())}


def measured(function, *, home, workspace, repeats):
    samples = []
    receipt = None
    for _ in range(repeats):
        gc.collect()
        tracemalloc.start()
        started = time.perf_counter()
        try:
            receipt = function(home=home, thread_id=THREAD, workspace=workspace)
            wall = time.perf_counter() - started
            current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert type(receipt) is dict
        samples.append({'wall_seconds_with_tracemalloc': wall,
            'python_traced_peak_bytes': peak, 'python_traced_retained_bytes': current})
    encoded = json.dumps(receipt, separators=(',', ':'), sort_keys=True).encode()
    telemetry = receipt.get('interaction_telemetry')
    summary = {'samples': samples,
        'median_wall_seconds_with_tracemalloc': statistics.median(
            item['wall_seconds_with_tracemalloc'] for item in samples),
        'max_python_traced_peak_bytes': max(item['python_traced_peak_bytes'] for item in samples),
        'serialized_receipt_bytes': len(encoded),
        'serialized_telemetry_bytes': (len(json.dumps(telemetry, separators=(',', ':'),
            sort_keys=True).encode()) if telemetry is not None else 0)}
    if telemetry is not None:
        summary['telemetry_bounds'] = {key: telemetry[key] for key in (
            'observed_records', 'record_limit_exceeded', 'observed_tool_call_events',
            'observed_tool_output_events', 'omitted_tool_events', 'observed_token_checkpoints',
            'omitted_token_observations', 'tool_observations_complete',
            'token_observations_complete')}
        summary['telemetry_bounds']['retained_tool_pairs'] = len(telemetry['tool_pairs'])
        summary['telemetry_bounds']['retained_token_observations'] = len(telemetry['token_observations'])
    return receipt, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('overhead.json'))
    args = parser.parse_args()
    memory_observations = [memory_observation('before_source_retrieval')]
    old_head = subprocess.check_output(['git', 'rev-parse', OLD_REVISION], cwd=SOURCE,
                                     text=True).strip()
    old_source = subprocess.check_output(['git', 'show', f'{old_head}:{RELATIVE}'], cwd=SOURCE)
    source_pins = {name: digest((SOURCE / name).read_bytes()) for name in (RELATIVE, HELPER)}
    current_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE,
                                         text=True).strip()
    source_matches_head = all(subprocess.check_output(
        ['git', 'show', f'{current_head}:{name}'], cwd=SOURCE) == (SOURCE / name).read_bytes()
        for name in source_pins)
    assert source_matches_head, 'Qualification requires committed active producer contents'
    # Git maps the repository's packfile virtually; constrain only the parser
    # process after source retrieval, not unrelated Git packfile address space.
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    memory_observations.append(memory_observation('parser_limit_installed'))
    results = []
    with tempfile.TemporaryDirectory(prefix='authored-telemetry-overhead-') as temporary:
        temporary = Path(temporary)
        old_path = temporary / 'old_receipt.py'
        old_path.write_bytes(old_source)
        old_path.chmod(0o600)
        old = load_module('authored_old_receipt', old_path)
        # Import only the two reviewed pure modules, avoiding package startup
        # side effects, discovery, provider state, and optional dependencies.
        package = types.ModuleType('authored_active_runtime')
        package.__path__ = [str((SOURCE / RELATIVE).parent)]
        sys.modules[package.__name__] = package
        new = load_module('authored_active_runtime.codex_usage_receipt', SOURCE / RELATIVE)
        cases = [('normal_10_pairs', 10, 0, 3),
                 ('larger_1000_pairs', 1000, 0, 3),
                 ('record_capped_100005', 10, 99972, 1)]
        for name, pairs, padding, repeats in cases:
            home, workspace, fixture = write_fixture(temporary / name, pairs=pairs,
                                                      padding_records=padding)
            old_receipt, old_stats = measured(old.recover_codex_usage, home=home,
                                              workspace=workspace, repeats=repeats)
            new_receipt, new_stats = measured(new.recover_codex_usage, home=home,
                                              workspace=workspace, repeats=repeats)
            keys = ('schema', 'thread_id', 'rollout_sha256', 'usage', 'usage_available',
                'observed_token_count_records', 'task_complete_observed',
                'billing_total_verified', 'cache_included_in_input', 'dollar_cost')
            same = all(old_receipt[key] == new_receipt[key] for key in keys)
            assert same, 'Healthy native aggregate contract changed'
            assert new_receipt['task_complete_observed'] is True
            assert new_receipt['usage']['total_tokens'] == pairs * 22
            assert new_stats['serialized_telemetry_bytes'] < 250_000
            if name.startswith('record_capped'):
                assert fixture['records_including_session_meta'] > 100_000
                assert new_stats['telemetry_bounds']['record_limit_exceeded'] is True
            results.append({'case': name, 'fixture': fixture, 'repeats_per_variant': repeats,
                'old': old_stats, 'new': new_stats,
                'native_aggregate_unchanged': same,
                'compared_native_contract_fields': list(keys),
                'measured_wall_ratio_new_to_old': new_stats['median_wall_seconds_with_tracemalloc'] /
                    old_stats['median_wall_seconds_with_tracemalloc'],
                'measured_peak_ratio_new_to_old': new_stats['max_python_traced_peak_bytes'] /
                    old_stats['max_python_traced_peak_bytes']})
            print(json.dumps({'case': name, 'native_aggregate_unchanged': same,
                'old_median_instrumented_seconds': old_stats['median_wall_seconds_with_tracemalloc'],
                'new_median_instrumented_seconds': new_stats['median_wall_seconds_with_tracemalloc'],
                'new_peak_python_bytes': new_stats['max_python_traced_peak_bytes']}, sort_keys=True),
                flush=True)
            memory_observations.append(memory_observation(name))
    assert all(digest((SOURCE / name).read_bytes()) == value for name, value in source_pins.items()), \
        'Source changed during local qualification; rerun against frozen content'
    final_process_memory = memory_observations[-1]['proc_status']
    assert final_process_memory['VmPeak_bytes'] <= MEMORY_LIMIT
    report = {'schema': 'authored-codex-telemetry-parser-overhead@1',
        'qualified': True, 'old_source_commit': old_head, 'active_source_head_at_start': current_head,
        'active_producer_contents_match_source_head': source_matches_head,
        'active_producer_contents_unchanged_during_qualification': True,
        'active_source_content_sha256': source_pins, 'old_receipt_source_sha256': digest(old_source),
        'authored_fixtures_only': True, 'real_provider_files_read': False,
        'raw_transcripts_retained': False, 'provider_calls': 0,
        'process_address_space_limit_bytes': MEMORY_LIMIT,
        'process_lifetime_rusage_maxrss_reported_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'proc_vm_hwm_bytes_after_measurements': final_process_memory['VmHWM_bytes'],
        'proc_vm_peak_bytes_after_measurements': final_process_memory['VmPeak_bytes'],
        'memory_observations': memory_observations,
        'cases': results, 'notes': [
            'Local parser recovery only; this does not measure model or end-to-end benchmark performance.',
            'All function wall samples include tracemalloc instrumentation; compare only as instrumented parser measurements.',
            'Python traced allocation peak excludes untracked native allocations; a separate 512MiB process address-space ceiling was enforced.',
            'The address-space ceiling is installed after Git source retrieval and before fixture generation, imports, and all parser measurements.',
            'rusage maxrss already reported a larger value before source retrieval and did not increase during this run; its prior provenance is unresolved and it is not a measurement-interval RSS claim. Linux /proc/self/status supplies current process VmHWM/VmPeak separately.',
            'The old parser runs first in each authored case; filesystem cache and allocator reuse are uncontrolled.',
            'New parser includes conservative completion validation as well as telemetry, so overhead is not attributed solely to telemetry.',
            'Truncation limits telemetry detail while the full bounded rollout still supplies unchanged healthy aggregate usage.',
            'Authored temporary fixtures and old source module are deleted after qualification.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
