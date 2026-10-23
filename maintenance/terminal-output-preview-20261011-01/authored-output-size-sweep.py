#!/usr/bin/env python3
"""Measure frozen helper representation bytes with authored local output only."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
COMMIT = '540c253f29c089368ccfb4657a5de0e27df8d20f'
RELATIVE = 'ipfs_accelerate_py/agent_supervisor/runtime/tool_output_artifact.py'
OUTPUT = Path(__file__).with_name('authored-output-size-sweep.json')


def git(*args):
    return subprocess.run(['git', '-C', str(SOURCE), *args], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15).stdout


def main():
    if git('rev-parse', 'HEAD').decode().strip() != COMMIT:
        raise ValueError('frozen source commit differs')
    helper_path = SOURCE / RELATIVE
    source_bytes = helper_path.read_bytes()
    if source_bytes != git('show', COMMIT + ':' + RELATIVE):
        raise ValueError('helper differs from frozen commit')
    spec = importlib.util.spec_from_file_location('authored_output_sweep_helper', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    records = []

    def measure(size, *, role='size_sweep', read_page=False):
        with tempfile.TemporaryDirectory(prefix='authored-output-size-sweep-') as directory:
            store = Path(directory) / 'store'
            identity = helper.create_store(store)['store_identity']
            row = None
            try:
                command = [sys.executable, str(helper_path), 'run', '--store', str(store),
                    '--timeout', '5', '--preview-bytes', '2048', '--', sys.executable, '-c',
                    'import sys; sys.stdout.buffer.write(b"x"*' + str(size) + '); sys.stdout.buffer.flush()']
                process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    check=True, timeout=15)
                capture = json.loads(process.stdout)
                streams = capture['streams']
                expected_hash = hashlib.sha256(b'x' * size).hexdigest()
                if (not capture['complete'] or not capture['cleanup_complete'] or capture['exit_code'] != 0
                        or capture['observed_bytes'] != size or capture['retained_bytes'] != size
                        or streams['stdout']['sha256'] != expected_hash or streams['stderr']['bytes'] != 0
                        or process.stderr):
                    raise ValueError('authored capture differs from expected bytes')
                preview_bytes = sum(item['preview_bytes'] for item in streams.values())
                response_bytes = len(process.stdout)
                row = {
                    'role': role,
                    'authored_stdout_bytes': size,
                    'authored_stderr_bytes': 0,
                    'capture_complete': capture['complete'],
                    'command_exit_code': capture['exit_code'],
                    'process_cleanup_complete': capture['cleanup_complete'],
                    'cli_stdout_json_bytes_including_newline': response_bytes,
                    'cli_stderr_bytes': len(process.stderr),
                    'retained_raw_bytes': capture['retained_bytes'],
                    'preview_payload_bytes': preview_bytes,
                    'omitted_raw_bytes': sum(item['omitted_bytes'] for item in streams.values()),
                    'json_envelope_bytes_excluding_authored_preview_characters': response_bytes - preview_bytes,
                    'cli_response_minus_raw_bytes': response_bytes - size,
                    'cli_response_to_raw_byte_ratio': response_bytes / size if size else None,
                    'cli_response_smaller_than_raw': response_bytes < size,
                }
                if read_page:
                    read_process = subprocess.run([sys.executable, str(helper_path), 'read',
                        '--store', str(store), '--sha256', streams['stdout']['sha256'],
                        '--offset', '1024', '--length', '1024'], check=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
                    page = json.loads(read_process.stdout)
                    import base64
                    if (page['offset'] != 1024 or page['length'] != 1024
                            or base64.b64decode(page['data_base64']) != b'x' * 1024
                            or page['text'] != 'x' * 1024 or read_process.stderr):
                        raise ValueError('authored replay differs')
                    row['bounded_read'] = {
                        'offset': page['offset'], 'raw_page_bytes': page['length'],
                        'cli_stdout_json_bytes_including_newline': len(read_process.stdout),
                        'text_field_bytes': len(page['text'].encode()),
                        'base64_field_ascii_bytes': len(page['data_base64']),
                        'capture_plus_read_cli_bytes': response_bytes + len(read_process.stdout),
                        'capture_plus_read_minus_original_raw_bytes': response_bytes + len(read_process.stdout) - size,
                        'exact_bytes_verified': True,
                    }
                summary = helper.summarize_store(store)
                row['helper_usage_observation'] = {key: summary[key] for key in
                    ('capture_count', 'complete_capture_count', 'incomplete_capture_count',
                     'read_count', 'read_bytes', 'store_bytes', 'artifact_count')}
            finally:
                cleanup = helper.remove_store(store, expected_identity=identity)
                if row is not None:
                    row['store_cleanup_complete'] = cleanup['removed'] and not store.exists()
            records.append(row)
            return row

    for size in (0, 128, 1024, 1536, 1792, 2048, 4096, 16384, 65536):
        measure(size, read_page=size == 4096)

    # With repeated printable ASCII, all preview characters occupy one JSON
    # byte. Find and confirm the local representation fixed point empirically.
    candidate = next(row for row in records if row['authored_stdout_bytes'] == 4096)[
        'cli_stdout_json_bytes_including_newline']
    equality = None
    for _ in range(4):
        row = measure(candidate, role='break_even_search')
        if row['cli_response_minus_raw_bytes'] == 0:
            equality = candidate
            break
        candidate = row['cli_stdout_json_bytes_including_newline']
    if equality is None:
        raise ValueError('bounded break-even search did not converge')
    below = measure(equality - 1, role='break_even_confirmation')
    above = measure(equality + 1, role='break_even_confirmation')
    if not (below['cli_response_minus_raw_bytes'] > 0 and above['cli_response_minus_raw_bytes'] < 0):
        raise ValueError('neighboring byte break-even confirmation failed')

    result = {
        'schema': 'terminal-authored-tool-output-representation-sweep@1',
        'source_commit': COMMIT,
        'helper_path': RELATIVE,
        'helper_sha256': hashlib.sha256(source_bytes).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'preview_option_bytes': 2048,
        'authored_output_kind': 'Repeated printable ASCII x on stdout; empty stderr.',
        'measurement_scope': 'Actual helper CLI stdout JSON bytes including its trailing newline, before native tool transport wrapping.',
        'provider_calls': 0,
        'source_modified': False,
        'raw_content_exported': False,
        'token_measurement_performed': False,
        'causal_live_token_difference_attribution': False,
        'rows': records,
        'confirmed_printable_ascii_byte_break_even': {
            'raw_bytes_equal_to_cli_response_bytes': equality,
            'first_neighbor_with_smaller_cli_response_bytes': equality + 1,
            'scope': 'This fixed helper version, successful command, stdout-only printable ASCII, empty stderr, 2048-byte preview option; independently confirmed adjacent sizes.'},
        'all_captures_complete': all(row['capture_complete'] for row in records),
        'all_process_cleanups_complete': all(row['process_cleanup_complete'] for row in records),
        'all_stores_removed': all(row['store_cleanup_complete'] for row in records),
        'limitations': [
            'Representation bytes are not model tokens, billing units, or a causal explanation of the live ABBA token difference.',
            'The native tool response wrapper and the advisory/input/tool-call bytes are outside this measurement.',
            'The fixed preview budget is split between stdout and stderr; with empty stderr, stdout previews use at most 1024 raw bytes.',
            'JSON metadata can outweigh reduction of small outputs. Escape-heavy text or binary bytes can change the break-even point.',
            'A valid UTF-8 retrieval page carries both readable text and exact base64, plus metadata; this duplicates representation bytes.',
            'Capture plus retrieval costs depend on how many pages the agent actually requests.',
            'The authored repeated-character fixture isolates representation overhead and does not establish semantic utility or task success.',
            'Only small authored command executions were used; no external resource pressure was injected.'
        ],
    }
    OUTPUT.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'report': str(OUTPUT), 'capture_count': len(records),
        'break_even_raw_bytes': equality, 'all_stores_removed': result['all_stores_removed']}))


if __name__ == '__main__':
    main()
