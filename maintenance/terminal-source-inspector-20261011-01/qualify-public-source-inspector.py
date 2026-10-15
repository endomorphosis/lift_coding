#!/usr/bin/env python3
"""Exercise exact CLI against fresh native public Bottle retrieval, provider-free."""
from __future__ import annotations
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time

C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
E = Path('/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01/pinned-dependencies-v10')
I = Path('/home/barberb/lift_coding/maintenance/terminal-source-inspector-20261011-01')
CACHE = Path('/home/barberb/lift_coding/maintenance/terminal-compact-context-20261011-01/tokenizer-cache')
TOKEN_ASSET = CACHE / 'fb374d419588a4632f3f557e76b4b70aebbca790'
TOKEN_SHA = '446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d'
MODULE = 'ipfs_accelerate_py.agent_supervisor.runtime.code_source_inspection'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fixture = args.fixture.resolve(strict=True)
    output = args.output.absolute()
    if not fixture.is_relative_to(I) or output.exists() or output.resolve(strict=False) != output or output.parent != I:
        raise ValueError('canonical stage-contained input and new output required')
    summary_raw = (fixture / 'summary.json').read_bytes()
    summary = json.loads(summary_raw)
    repository = Path(summary['repository'])
    source_raw = (repository / 'bottle.py').read_bytes()
    if sha(source_raw) != summary['source_sha256'] or sha(TOKEN_ASSET.read_bytes()) != TOKEN_SHA:
        raise ValueError('exact public source and pinned offline tokenizer required')
    source = source_raw.decode('utf-8')
    original_lines = list(io.StringIO(source).readlines())
    offsets = [0]
    for line in original_lines:
        offsets.append(offsets[-1] + len(line.encode('utf-8')))
    definitions = {}
    class Visitor(ast.NodeVisitor):
        scope = []
        def definition(self, node):
            name = '.'.join([*self.scope, node.name])
            definitions.setdefault(name, []).append(node)
            self.scope.append(node.name); self.generic_visit(node); self.scope.pop()
        visit_ClassDef = definition
        visit_FunctionDef = definition
        visit_AsyncFunctionDef = definition
    Visitor().visit(ast.parse(source))
    output.mkdir()
    cwd = output / 'empty-working-directory'; cwd.mkdir()
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(map(str, [C, E / 'datasets', E / 'kit']))
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    sentinel = output / 'unrelated-metadata-owner-must-stay-unopened.duckdb'
    env['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = str(sentinel)
    env.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE', None)
    os.environ['TIKTOKEN_CACHE_DIR'] = str(CACHE)
    import importlib.metadata
    import tiktoken
    tokenizer = tiktoken.get_encoding('o200k_base')
    count = lambda text: len(tokenizer.encode(text, disallowed_special=()))
    sys.path.insert(0, str(C))
    from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata
    from ipfs_accelerate_py.agent_supervisor.analysis.program_ast_adapters import build_program_evidence_index
    from ipfs_accelerate_py.agent_supervisor.analysis.code_symbol_vector_index import (
        CodeVectorIndexSnapshot, resolve_code_symbol_ast_facts)
    payload = json.loads((repository / summary['source_artifact']).read_bytes())
    snapshot_data = payload.get('snapshot')
    if snapshot_data is None:
        snapshot_data = json.loads((repository / payload['snapshot_ref']['path']).read_bytes())
    snapshot = CodeVectorIndexSnapshot.from_dict(snapshot_data)
    with public_replay_without_metadata():
        evidence = build_program_evidence_index({'bottle.py': source})
    indexed = next(row for row in evidence.ast_index.path_records if row.path == 'bottle.py')
    rows = {row.row_id: row for row in snapshot.rows}
    producer_paths = [C / 'ipfs_accelerate_py/agent_supervisor/runtime/code_source_inspection.py',
        C / 'test/api/test_code_source_inspection.py', Path(__file__)]
    producer_pins = [{'path': str(path), 'bytes': path.stat().st_size,
                      'sha256': sha(path.read_bytes())} for path in producer_paths]

    def command(row_id, question, mode, maximum, continuation=None, **overrides):
        options = dict(repository=str(repository), artifact=summary['frontier_artifact'],
            expected_sha256=summary['frontier_artifact_sha256'], task_id=summary['task_id'],
            task_cid=summary['task_cid'], source_artifact=summary['source_artifact'],
            source_sha256=summary['source_artifact_sha256'], row_id=row_id, question=question,
            mode=mode, max_bytes=str(maximum))
        if continuation is not None: options['continuation'] = continuation
        options.update(overrides)
        argv = [sys.executable, '-P', '-m', MODULE]
        for key, value in options.items(): argv.extend(['--' + key.replace('_', '-'), str(value)])
        return argv

    calls, cases = [], []
    def invoke(label, argv, maximum, *, refused=False):
        start = time.monotonic()
        run = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=60)
        seconds = time.monotonic() - start
        row = {'label': label, 'returncode': run.returncode, 'seconds': seconds,
               'stdout_bytes': len(run.stdout), 'stderr_bytes': len(run.stderr)}
        if refused:
            assert run.returncode == 2 and not run.stdout
            error = json.loads(run.stderr)
            assert error['schema'] == 'supervisor-code-source-inspection-error@1' and len(run.stderr) <= 512
            row['bounded_refusal'] = error
        else:
            assert run.returncode == 0 and not run.stderr and len(run.stdout) <= maximum
            response = json.loads(run.stdout)
            assert encoded(response) == run.stdout
            assert response['schema'] == 'supervisor-code-source-inspection@1'
            assert all(response[key] is False for key in ['source_authentication_claimed',
                'immutable_custody_claimed', 'module_resolution_verified', 'dynamic_resolution_verified',
                'semantic_authority', 'proof_authority', 'execution_authority', 'completion_authority'])
            assert response['native_result_replayed'] and response['source_freshness_verified'] and response['selected_definition_unique']
            row['local_tokens'] = count(run.stdout.decode('utf-8')); row['sha256'] = sha(run.stdout)
            (output / (label + '.json')).write_bytes(run.stdout)
        calls.append(row)
        print(json.dumps({'completed': label, 'returncode': run.returncode,
                          'seconds': round(seconds, 3), 'stdout_bytes': len(run.stdout)}, sort_keys=True), flush=True)
        return None if refused else response

    hits = {hit['symbol']: hit for hit in summary['hits']}
    assert len(summary['hits']) == len(hits) == len({hit['row_id'] for hit in summary['hits']}) == 5
    requests = [('small-decorated-source', 'bottle.BaseRequest.app', 'source', 8192),
                ('large-source', 'bottle.static_file', 'source', 6144),
                ('native-facts', 'bottle.static_file', 'facts', 8192)]
    start = time.monotonic()
    first_partial = None
    for name, symbol, mode, maximum in requests:
        hit = hits[symbol]; node = definitions[rows[hit['row_id']].symbol][0]
        first = min([node.lineno, *[d.lineno for d in node.decorator_list]])
        expected = source_raw[offsets[first-1]:offsets[node.end_lineno]] if mode == 'source' else encoded(resolve_code_symbol_ast_facts(indexed, rows[hit['row_id']]))
        question = 'Show the exact nominated ' + mode + ' evidence for this public task.'
        joined, continuation, page_count = [], None, 0
        response_bytes = local_tokens = 0
        while page_count < 16:
            label = name + '-page-' + str(page_count + 1)
            response = invoke(label, command(hit['row_id'], question, mode, maximum, continuation), maximum)
            binding = response['bindings']
            assert binding['row_id'] == hit['row_id'] and binding['symbol'] == symbol
            assert binding['source_sha256'] == summary['source_sha256']
            assert binding['task_cid'] == summary['task_cid'] and binding['query_id'] == summary['native_query_id']
            assert binding['result_id'] == summary['native_result_id'] and binding['index_id'] == summary['native_index_id']
            part = response['content_text'].encode('utf-8')
            begin = sum(map(len, joined)); end = begin + len(part)
            assert response['content_sha256'] == sha(expected) and response['content_bytes'] == len(expected)
            assert response['page_offset'] == begin and response['page_end'] == end
            assert response['page_bytes'] == len(part) and response['page_sha256'] == sha(part)
            assert part == expected[begin:end] and response['remaining_bytes'] == len(expected) - end
            if mode == 'source':
                span = binding['source_span']; page = response['page_source_span']
                assert span['line_start'] == first and span['line_end'] == node.end_lineno
                assert span['sha256'] == sha(expected) and span['byte_start'] == offsets[first-1]
                assert page['byte_start'] == span['byte_start'] + begin and page['byte_end'] == span['byte_start'] + end
            joined.append(part); page_count += 1
            response_bytes += calls[-1]['stdout_bytes']; local_tokens += calls[-1]['local_tokens']
            if not response['complete'] and first_partial is None:
                first_partial = (hit['row_id'], question, mode, maximum, response['continuation'])
            continuation = response['continuation']
            if response['complete']:
                assert continuation is None; break
            assert continuation and end > begin
        else:
            raise ValueError('public qualification exceeded page limit')
        assert b''.join(joined) == expected
        cases.append({'case': name, 'symbol': symbol, 'mode': mode, 'byte_cap': maximum,
            'pages': page_count, 'content_bytes': len(expected), 'content_sha256': sha(expected),
            'complete_cli_output_bytes': response_bytes,
            'sum_independent_local_tool_output_tokens': local_tokens,
            'exact_reconstruction_verified': True})
    if first_partial is None:
        raise ValueError('public continuation control was not exercised')
    row_id, question, mode, maximum, handle = first_partial
    invoke('wrong-continuation-question', command(row_id, question + ' changed', mode, maximum, handle), maximum, refused=True)
    invoke('wrong-continuation-mode', command(row_id, question, 'facts' if mode == 'source' else 'source', maximum, handle), maximum, refused=True)
    invoke('wrong-continuation-budget', command(row_id, question, mode, maximum+1, handle), maximum+1, refused=True)
    target = next(row for row in snapshot.rows if row.symbol == 'HeaderDict')
    assert target.row_id not in {hit['row_id'] for hit in summary['hits']}
    invoke('non-nominated-header-symbol', command(target.row_id, question, 'source', 8192), 8192, refused=True)
    invoke('foreign-task', command(row_id, question, mode, maximum, task_cid='task:foreign-public-control'), maximum, refused=True)
    invoke('wrong-source-artifact-pin', command(row_id, question, mode, maximum, source_sha256='0'*64), maximum, refused=True)
    assert not sentinel.exists()
    for pin in summary['pins']:
        path = Path(pin['path']); raw = path.read_bytes(); st = path.lstat()
        assert len(raw) == pin['bytes'] and sha(raw) == pin['sha256']
        assert all(getattr(st, key) == value for key, value in pin['witness'].items())
    for pin in producer_pins:
        raw = Path(pin['path']).read_bytes(); assert len(raw) == pin['bytes'] and sha(raw) == pin['sha256']
    assert (fixture / 'summary.json').read_bytes() == summary_raw
    receipt = {'schema': 'public-bottle-code-source-inspector-cli-qualification@1',
        'qualified': True, 'fixture_summary': {'path': str(fixture / 'summary.json'), 'sha256': sha(summary_raw)},
        'producer_pins': producer_pins, 'cases': cases, 'calls': calls,
        'full_source_local_tokens': count(source), 'full_source_bytes': len(source_raw),
        'literal_query_hits': list(hits), 'literal_query_result_hit_count': 5,
        'inspected_nominated_symbol_count': 2, 'header_targets_nominated': False,
        'fresh_ducklake_projection': summary['fresh_ducklake_projection'],
        'source_and_original_fixture_bytes_and_witnesses_unchanged': True,
        'unrelated_metadata_owner_activated': False, 'provider_calls': 0,
        'target_module_imports': 0, 'training_steps': 0, 'prover_invocations': 0,
        'complete_cli_wire_byte_caps_verified': True, 'seconds': time.monotonic()-start,
        'local_tokenizer': {'encoding': 'o200k_base', 'version': importlib.metadata.version('tiktoken'),
            'asset_sha256': TOKEN_SHA, 'scope': 'Independent LOCAL complete tool-output representation counts, not native provider usage or model-turn attribution.'},
        'installed_runtime_archive_qualified': False, 'coding_prompt_integration': False,
        'task_reward_evaluated': False, 'provider_total_token_reduction_established': False,
        'source_semantic_equivalence_proved': False, 'task_satisfaction_proved': False,
        'model_convergence_proved': False,
        'limitations': ['Two symbols from the exact five-hit production literal-query result were inspected; that result does not nominate the authored header targets.',
            'Each page replays current native inputs; summed tool-output representations and latency must be assessed before any live promotion.',
            'Fresh local native metadata/projection is not signed task admission, complete repository semantics or proof authority.',
            'CLI qualified from a separate working directory on the host; no deployed worker/runtime or provider trial occurred.']}
    (output / 'qualification.json').write_bytes(encoded(receipt))
    print(json.dumps({'qualified': True, 'output': str(output), 'cases': len(cases),
        'calls': len(calls), 'provider_calls': 0, 'seconds': receipt['seconds']}, sort_keys=True))


if __name__ == '__main__':
    main()
