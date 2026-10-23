#!/usr/bin/env python3
"""Independent authored byte probes; no providers, hidden tests, or source edits."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
HELPER = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011/ipfs_accelerate_py/agent_supervisor/runtime/tool_output_artifact.py')
spec = importlib.util.spec_from_file_location('independent_helper_review', HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
checks, rows = [], []


def check(name, condition):
    checks.append({'check': name, 'passed': bool(condition)})


def encode(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True,
                      separators=(',', ':')).encode('ascii') + b'\n'


def exact(value):
    assert ('text' in value) != ('data_base64' in value)
    if 'text' in value:
        return value['text'].encode('utf-8')
    return base64.b64decode(value['data_base64'], validate=True)


def preview(value, expected, budget):
    shown = min(len(expected), budget)
    assert value['bytes'] == len(expected)
    assert value['omitted_bytes'] == len(expected) - shown
    if not value['omitted_bytes']:
        assert exact(value) == expected
        assert 'sha256' not in value
        return
    first, last = (budget + 1) // 2, budget // 2
    if 'head_text' in value:
        assert 'head_base64' not in value and 'tail_base64' not in value
        parts = value['head_text'].encode(), value['tail_text'].encode()
    else:
        assert 'head_text' not in value and 'tail_text' not in value
        parts = (base64.b64decode(value['head_base64'], validate=True),
                 base64.b64decode(value['tail_base64'], validate=True))
    assert parts == (expected[:first], expected[-last:] if last else b'')
    assert value['sha256'] == hashlib.sha256(expected).hexdigest()


fixtures = [
    ('empty', b'', b'', 2048),
    ('controls', b'\r\n\0\x1b[31m"\\\t', b'\r\n', 2048),
    ('replacement_is_literal', '\ufffd'.encode(), b'', 2048),
    ('no_unicode_normalization', 'e\u0301\u00e9\U0001f4a1'.encode(), b'', 2048),
    ('binary', bytes(range(256)), b'\x80\xff', 2048),
    ('split_unicode', '\U0001f4a1'.encode() * 20, b'', 12),
    ('zero_preview', b'abc', b'def', 0),
    ('odd_preview', b'abcdefghij', b'0123456789', 7),
    ('maximum_escaped_preview', b'\0' * 9000, b'\1' * 9000, 8192),
    ('maximum_binary_preview', b'\xff' * 9000, b'\xfe' * 9000, 8192),
]

with tempfile.TemporaryDirectory(prefix='compact-independent-review-') as temporary:
    parent = Path(temporary)
    for name, stdout, stderr, budget in fixtures:
        store = parent / name
        identity = helper.create_store(store)['store_identity']
        out_expr = f'{stdout[:1]!r}*{len(stdout)}' if stdout and len(set(stdout)) == 1 else repr(stdout)
        err_expr = f'{stderr[:1]!r}*{len(stderr)}' if stderr and len(set(stderr)) == 1 else repr(stderr)
        script = f'import os; os.write(1,{out_expr}); os.write(2,{err_expr})'
        original = helper.run(store=store, argv=[sys.executable, '-c', script], timeout=3,
                              preview_bytes=budget)
        before = copy.deepcopy(original)
        files = {p.name: p.read_bytes() for p in store.iterdir()}
        projected = helper.format_response(original, 'compact')
        try:
            preview(projected['streams']['stdout'], stdout, (budget + 1) // 2)
            preview(projected['streams']['stderr'], stderr, budget // 2)
            check(name + '.exact_preview', True)
        except AssertionError:
            check(name + '.exact_preview', False)
        check(name + '.capture_flags', projected['complete'] is True
              and projected['cleanup_complete'] is True and projected['exit_code'] == 0
              and projected['observed_bytes'] == projected['retained_bytes'] == len(stdout) + len(stderr)
              and projected['proof_authority'] is projected['completion_authority'] is False)
        check(name + '.pure_projection', original == before
              and helper.format_response(original) is original
              and helper.format_response(original, 'legacy') is original
              and files == {p.name: p.read_bytes() for p in store.iterdir()})
        check(name + '.serialized_bound', len(encode(projected)) <= 6 * 8192 + 2048)
        check(name + '.less_than_legacy_for_fixture', len(encode(projected)) < len(encode(original)))
        for stream_name, data in [('stdout', stdout), ('stderr', stderr)]:
            digest = original['streams'][stream_name]['sha256']
            for offset, length in [(0, 8192), (min(1, len(data)), 1), (len(data), 1)]:
                page = helper.read(store=store, sha256=digest, offset=offset, length=length)
                before_page = copy.deepcopy(page)
                compact_page = helper.format_response(page, 'compact')
                check(name + '.' + stream_name + f'.page_{offset}_{length}',
                      exact(compact_page) == data[offset:offset + length]
                      and compact_page['next_offset'] == offset + min(length, len(data) - offset)
                      and compact_page['eof'] is (offset + length >= len(data))
                      and page == before_page
                      and len(encode(compact_page)) < len(encode(page)))
        rows.append({'fixture': name, 'raw_bytes': len(stdout) + len(stderr),
                     'preview_budget_bytes': budget, 'legacy_json_bytes': len(encode(original)),
                     'compact_json_bytes': len(encode(projected))})
        check(name + '.cleanup', helper.remove_store(store, expected_identity=identity)['removed'])

    for name, script, timeout, exit_code, reason in [
            ('nonzero_exit', 'import sys; print("failure"); sys.exit(7)', 3, 7, None),
            ('timeout', 'import os,time; os.write(1,b"x"*100); time.sleep(20)', .1, None, 'timeout')]:
        store = parent / name
        identity = helper.create_store(store)['store_identity']
        result = helper.run(store=store, argv=[sys.executable, '-c', script], timeout=timeout, preview_bytes=8)
        compact = helper.format_response(result, 'compact')
        check(name + '.visibility', compact['termination_reason'] == reason
              and compact['cleanup_complete'] is True
              and (compact['exit_code'] == exit_code if exit_code is not None else compact['complete'] is False)
              and (reason is None or compact['retained_bytes'] == 0))
        check(name + '.no_incomplete_replay', reason is None or all('sha256' not in s for s in compact['streams'].values()))
        check(name + '.cleanup', helper.remove_store(store, expected_identity=identity)['removed'])

    store = parent / 'malformed'
    identity = helper.create_store(store)['store_identity']
    result = helper.run(store=store, argv=[sys.executable, '-c', 'print("bytes")'], timeout=3)
    mutated = copy.deepcopy(result)
    mutated['streams']['stdout']['bytes'] += 1
    try:
        helper.format_response(mutated, 'compact')
        check('inconsistent_capture_census_rejected', False)
    except ValueError:
        check('inconsistent_capture_census_rejected', True)
    page = helper.read(store=store, sha256=result['streams']['stdout']['sha256'])
    page['length'] += 1
    try:
        helper.format_response(page, 'compact')
        check('inconsistent_page_census_rejected', False)
    except ValueError:
        check('inconsistent_page_census_rejected', True)
    marker = parent / 'must-not-exist'
    command = [sys.executable, str(HELPER), 'run', '--store', str(store),
               '--response-format', 'unsupported', '--', sys.executable, '-c',
               f'open({str(marker)!r},"w").write("unsafe")']
    rejected = subprocess.run(command, capture_output=True, timeout=5)
    check('invalid_format_cannot_spawn', rejected.returncode == 2 and not marker.exists())
    helper.remove_store(store, expected_identity=identity)

report = {'schema': 'independent-compact-output-probes@1', 'helper_sha256': hashlib.sha256(HELPER.read_bytes()).hexdigest(),
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'all_checks_passed': all(c['passed'] for c in checks), 'check_count': len(checks),
          'checks': checks, 'fixtures': rows, 'provider_calls': 0, 'token_measurement_performed': False,
          'raw_output_exported': False, 'claims_general_token_savings': False}
(ROOT / 'independent-compact-probes.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: report[k] for k in ('all_checks_passed', 'check_count', 'helper_sha256')}))
if not report['all_checks_passed']:
    print(json.dumps([c for c in checks if not c['passed']]))
    raise SystemExit(1)
