#!/usr/bin/env python3
"""Paired authored CLI byte measurements; no model or benchmark task calls."""
from __future__ import annotations

import argparse
import ast
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
BASELINE_COMMIT = '540c253f29c089368ccfb4657a5de0e27df8d20f'
RELATIVE = 'ipfs_accelerate_py/agent_supervisor/runtime/tool_output_artifact.py'
OUTPUT = Path(__file__).with_name('authored-wire-comparison.json')


def git(*args):
    return subprocess.run(['git', '-C', str(SOURCE), *args], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15).stdout


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def function_bodies(source):
    return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(source).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-commit')
    options = parser.parse_args()
    commit = git('rev-parse', 'HEAD').decode().strip()
    helper_path = SOURCE / RELATIVE
    source_bytes = helper_path.read_bytes()
    committed = source_bytes == git('show', commit + ':' + RELATIVE)
    if options.expected_commit and (commit != options.expected_commit or not committed):
        raise ValueError('final source or helper commit binding differs')
    baseline_bodies = function_bodies(git('show', BASELINE_COMMIT + ':' + RELATIVE))
    current_bodies = function_bodies(source_bytes)
    unchanged = {name: current_bodies[name] == baseline_bodies[name]
                 for name in ('run', 'read', '_write_receipt', '_preview')}
    if not all(unchanged.values()):
        raise ValueError('default run/read/receipt behavior changed')
    spec = importlib.util.spec_from_file_location('authored_wire_comparison_helper', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)

    fixtures = [dict(name='ascii_stdout_' + str(size), stdout=b'x' * size, stderr=b'',
                     stdout_expression='b"x"*' + str(size), stderr_expression='b""', preview_bytes=2048)
                for size in (0, 128, 1024, 4096, 16384, 65536)]
    fixtures.extend([
        dict(name='both_streams_ascii', stdout=b'x' * 4096, stderr=b'y' * 4096,
             stdout_expression='b"x"*4096', stderr_expression='b"y"*4096', preview_bytes=2048),
        dict(name='control_and_json_escapes', stdout=(b'\x00\n\r\t"\\' * 683)[:4096], stderr=b'',
             stdout_expression='(b\'\\x00\\n\\r\\t"\\\\\'*683)[:4096]', stderr_expression='b""', preview_bytes=2048),
        dict(name='valid_utf8_fully_shown', stdout=('☃💡\n' * 20).encode(), stderr=b'',
             stdout_expression=repr(('☃💡\n' * 20).encode()), stderr_expression='b""', preview_bytes=2048),
        dict(name='utf8_preview_codepoint_split', stdout='💡'.encode() * 20, stderr=b'',
             stdout_expression=repr('💡'.encode()) + '*20', stderr_expression='b""', preview_bytes=12),
        dict(name='binary_fully_shown', stdout=bytes(range(256)), stderr=b'',
             stdout_expression='bytes(range(256))', stderr_expression='b""', preview_bytes=2048),
        dict(name='binary_omitted', stdout=bytes(range(256)) * 32, stderr=b'',
             stdout_expression='bytes(range(256))*32', stderr_expression='b""', preview_bytes=2048),
    ])
    rows = []

    def measure(fixture, response_format):
        with tempfile.TemporaryDirectory(prefix='authored-wire-comparison-') as directory:
            store = Path(directory) / 'store'
            identity = helper.create_store(store)['store_identity']
            row = None
            try:
                script = ('import sys; sys.stdout.buffer.write(' + fixture['stdout_expression'] + '); '
                          'sys.stdout.buffer.flush(); sys.stderr.buffer.write(' + fixture['stderr_expression'] + '); '
                          'sys.stderr.buffer.flush()')
                command = [sys.executable, str(helper_path), 'run', '--store', str(store),
                    '--timeout', '5', '--preview-bytes', str(fixture['preview_bytes']),
                    '--response-format', response_format, '--', sys.executable, '-c', script]
                process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    check=True, timeout=15)
                actual = json.loads(process.stdout)
                receipt = json.loads(next(store.glob('capture-*.json')).read_bytes())
                if (process.stderr or not actual['complete'] or not actual['cleanup_complete']
                        or actual['exit_code'] != 0 or receipt['schema'] != 'tool-output-artifact-capture@1'):
                    raise ValueError('authored capture did not complete as expected')
                # Recreate only the display fields excluded from the persisted
                # v1 receipt, using this authored fixture's known exact bytes.
                internal = copy.deepcopy(receipt)
                for name in ('stdout', 'stderr'):
                    raw = fixture[name]
                    digest = hashlib.sha256(raw).hexdigest()
                    stream = receipt['streams'][name]
                    if (stream['bytes'] != len(raw) or stream['sha256'] != digest
                            or (store / (digest + '.bin')).read_bytes() != raw):
                        raise ValueError('retained exact bytes differ from authored input')
                    limit = (fixture['preview_bytes'] + (name == 'stdout')) // 2
                    internal['streams'][name].update(helper._preview(raw[:limit], raw[-limit:] if limit else b'', len(raw), limit))
                before = {path.name: path.read_bytes() for path in store.iterdir()}
                before_internal = canonical(internal)
                expected = helper.format_response(internal, response_format)
                if canonical(expected) + b'\n' != process.stdout:
                    raise ValueError('actual CLI bytes differ from pure projection')
                if (canonical(internal) != before_internal
                        or {path.name: path.read_bytes() for path in store.iterdir()} != before):
                    raise ValueError('formatting mutated internal result or artifacts')
                raw_bytes = len(fixture['stdout']) + len(fixture['stderr'])
                row = {
                    'response_schema': actual['schema'],
                    'cli_json_bytes_including_newline': len(process.stdout),
                    'cli_json_minus_raw_bytes': len(process.stdout) - raw_bytes,
                    'capture_complete': actual['complete'],
                    'process_cleanup_complete': actual['cleanup_complete'],
                    'retained_bytes': actual['retained_bytes'],
                    'preview_payload_bytes': sum(s['preview_bytes'] for s in receipt['streams'].values()),
                    'omitted_bytes': sum(s['omitted_bytes'] for s in receipt['streams'].values()),
                    'exact_retained_data_verified': True,
                    'cli_matches_pure_projection': True,
                    'formatting_preserved_internal_result_and_store_bytes': True,
                    'persisted_capture_schema': receipt['schema'],
                }
                if fixture['name'] == 'ascii_stdout_4096':
                    digest = receipt['streams']['stdout']['sha256']
                    replay = subprocess.run([sys.executable, str(helper_path), 'read', '--store', str(store),
                        '--sha256', digest, '--offset', '1024', '--length', '1024',
                        '--response-format', response_format], check=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
                    page = json.loads(replay.stdout)
                    raw_page = (page['text'].encode() if page.get('text') is not None
                                else base64.b64decode(page['data_base64']))
                    if (raw_page != b'x' * 1024 or replay.stderr
                            or page['offset'] != 1024 or page['length'] != 1024):
                        raise ValueError('authored replay bytes differ')
                    row['read_1024_byte_middle_page'] = {
                        'schema': page['schema'], 'raw_page_bytes': len(raw_page),
                        'cli_json_bytes_including_newline': len(replay.stdout),
                        'text_representation_present': 'text' in page,
                        'base64_representation_present': 'data_base64' in page,
                        'capture_plus_read_cli_bytes': len(process.stdout) + len(replay.stdout),
                        'capture_plus_read_minus_original_raw_bytes': len(process.stdout) + len(replay.stdout) - raw_bytes,
                        'exact_bytes_verified': True,
                    }
                summary = helper.summarize_store(store)
                row['usage'] = {key: summary[key] for key in ('capture_count', 'complete_capture_count',
                    'incomplete_capture_count', 'read_count', 'read_bytes', 'artifact_count', 'store_bytes')}
                normalized_receipt = dict(receipt)
                normalized_receipt.pop('capture_id')
            finally:
                cleanup = helper.remove_store(store, expected_identity=identity)
                if row is not None:
                    row['store_removed'] = cleanup['removed'] and not store.exists()
            return row, normalized_receipt

    for fixture in fixtures:
        legacy, legacy_receipt = measure(fixture, 'legacy')
        compact, compact_receipt = measure(fixture, 'compact')
        if canonical(legacy_receipt) != canonical(compact_receipt):
            raise ValueError('persisted v1 receipts differ beyond per-run capture ID')
        rows.append({
            'case': fixture['name'],
            'authored_stdout_bytes': len(fixture['stdout']),
            'authored_stderr_bytes': len(fixture['stderr']),
            'preview_option_bytes': fixture['preview_bytes'],
            'legacy': legacy, 'compact': compact,
            'compact_minus_legacy_cli_json_bytes': compact['cli_json_bytes_including_newline'] - legacy['cli_json_bytes_including_newline'],
            'compact_to_legacy_cli_json_byte_ratio': compact['cli_json_bytes_including_newline'] / legacy['cli_json_bytes_including_newline'],
            'persisted_capture_receipts_equal_except_unique_capture_id': True,
        })

    report = {
        'schema': 'terminal-authored-tool-output-wire-comparison@1',
        'source_commit': commit,
        'helper_sha256': hashlib.sha256(source_bytes).hexdigest(),
        'helper_path': RELATIVE,
        'helper_matches_source_commit': committed,
        'qualification_phase': 'final_source_binding' if options.expected_commit else 'preliminary_local_source',
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'baseline_default_behavior_commit': BASELINE_COMMIT,
        'default_behavior_functions_ast_unchanged': unchanged,
        'provider_calls': 0, 'native_task_calls': 0, 'source_modified_by_benchmark': False,
        'raw_content_exported': False, 'token_measurement_performed': False,
        'causal_live_token_difference_attribution': False,
        'measurement_scope': 'Actual helper CLI stdout JSON bytes including newline, before native tool transport wrapping.',
        'fixture_count': len(rows), 'capture_count': 2 * len(rows), 'read_count': 2,
        'rows': rows,
        'all_captures_complete': all(row[mode]['capture_complete'] for row in rows for mode in ('legacy', 'compact')),
        'all_cleanup_complete': all(row[mode]['process_cleanup_complete'] and row[mode]['store_removed'] for row in rows for mode in ('legacy', 'compact')),
        'limitations': [
            'JSON representation bytes are not model tokens or billing units; the results do not explain live token differences causally.',
            'Native tool wrappers, invocation arguments, and advisory input costs are outside this measurement.',
            'The 2048-byte preview option is split between streams, so stdout-only previews use at most 1024 bytes.',
            'Compact output reduces redundant representations and metadata; semantic utility and official task success require separate qualification.',
            'UTF-8 fragments splitting a code point use exact base64. Printable ASCII break-even sizes do not generalize to binary or escape-heavy text.',
            'Run IDs necessarily differ across paired real executions; persisted receipt equality excludes only capture_id.',
            'No provider, native benchmark task, external-pressure injection, or stress workload was invoked.'
        ],
    }
    OUTPUT.write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'report': str(OUTPUT), 'capture_count': report['capture_count'],
        'all_cleanup_complete': report['all_cleanup_complete'], 'helper_matches_source_commit': committed,
        'qualification_phase': report['qualification_phase']}))


if __name__ == '__main__':
    main()
