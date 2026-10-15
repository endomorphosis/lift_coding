"""Offline matched-input measurement over captured public Bottle source.

The cached public tokenizer asset is verified before use. No downloads,
provider calls, owner state, hidden verifier, training, or proving are used.
Run with the isolated checkout and dependency roots on PYTHONPATH.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import importlib.metadata
import importlib.util
import inspect
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import time

CHECKOUT = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
DEFAULT_CODE = Path('/home/barberb/lift_coding/maintenance/terminal-coding-transport-20261011-01/pilot/coding-identifiers-01/jobs/supervisor-full-identifiers-fix-code-vulnerability/fix-code-vulnerability__NW2EqdA/agent/public-output-evidence/before/bottle.py')
INSTRUCTION = CHECKOUT / 'benchmarks/agent_supervisor/container_coding/fixtures/public-bottle-instruction.md'
TEST = CHECKOUT / 'test/api/semantic_state/test_code_retrieval_frontier.py'
NAMES = (
    'ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_frontier',
    'ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_context',
    'ipfs_accelerate_py.agent_supervisor.context.database_context',
    'ipfs_accelerate_py.agent_supervisor.analysis.program_ast_adapters',
    'ipfs_accelerate_py.agent_supervisor.analysis.code_symbol_vector_index',
    'ipfs_accelerate_py.agent_supervisor.analysis.analysis_ast_index',
    'ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index',
)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def capture(path, maximum=8 * 1024 * 1024):
    path = Path(path).absolute()
    if path.resolve(strict=True) != path or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('measurement input must be a canonical regular file')
    before = path.stat()
    with path.open('rb') as stream:
        raw = stream.read(maximum + 1)
    after = path.stat()
    persistent = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_uid,
        value.st_gid, value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if persistent(before) != persistent(after) or len(raw) > maximum:
        raise ValueError('measurement input changed or exceeded its bound')
    return raw, {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def write(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)


@contextmanager
def offline():
    original_run = subprocess.run
    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex
    probes = []
    def run(argv, *args, **kwargs):
        if (type(argv) not in (list, tuple) or not argv or kwargs.get('shell')
                or not (Path(argv[0]).name == 'git' or list(argv) == [sys.executable, '--version'])):
            raise AssertionError('offline measurement permits only Git and exact interpreter version probes')
        probes.append([str(value) for value in argv])
        return original_run(argv, *args, **kwargs)
    def connect(*args, **kwargs):
        raise AssertionError('offline measurement refuses network connections')
    subprocess.run, socket.socket.connect, socket.socket.connect_ex = run, connect, connect
    try:
        yield probes
    finally:
        subprocess.run, socket.socket.connect, socket.socket.connect_ex = original_run, original_connect, original_connect_ex


def tokenizer(cache):
    """Require the previous verified asset; absence never initiates a download."""
    import tiktoken
    from tiktoken_ext import openai_public
    definition = inspect.getsource(openai_public.o200k_base)
    url = re.search(r'"(https://openaipublic\.blob\.core\.windows\.net/encodings/o200k_base\.tiktoken)"', definition).group(1)
    expected = re.search(r'expected_hash="([0-9a-f]{64})"', definition).group(1)
    cache = Path(cache).absolute()
    if cache.resolve(strict=True) != cache:
        raise ValueError('canonical existing tokenizer cache required')
    raw, pin = capture(cache / hashlib.sha1(url.encode()).hexdigest())
    if sha(raw) != expected:
        raise ValueError('cached tokenizer asset differs from official integrity pin')
    os.environ['TIKTOKEN_CACHE_DIR'] = str(cache)
    encoding = tiktoken.get_encoding('o200k_base')
    return encoding, {'schema': 'terminal-local-tokenizer-provenance@1', 'encoding': encoding.name,
        'tiktoken_version': importlib.metadata.version('tiktoken'), 'vocabulary_size': encoding.n_vocab,
        'asset': pin, 'official_expected_sha256': expected,
        'official_definition': capture(openai_public.__file__)[1], 'asset_downloaded': False,
        'scope': 'LOCAL representation counts; not provider cumulative usage or an asserted configured-model tokenizer'}


def metric(raw, encoding):
    return {'bytes': len(raw), 'sha256': sha(raw),
            'LOCAL_o200k_base_tokens': len(encoding.encode(raw.decode(), disallowed_special=()))}


def comparison(before, after, encoding):
    full, selected = metric(before, encoding), metric(after, encoding)
    return {'full': full, 'selected': selected,
            'saved_bytes': full['bytes'] - selected['bytes'],
            'byte_reduction_percent': 100 * (full['bytes'] - selected['bytes']) / full['bytes'],
            'saved_LOCAL_tokens': full['LOCAL_o200k_base_tokens'] - selected['LOCAL_o200k_base_tokens'],
            'LOCAL_token_reduction_percent': 100 * (full['LOCAL_o200k_base_tokens'] - selected['LOCAL_o200k_base_tokens']) / full['LOCAL_o200k_base_tokens']}


def breakdown(value, encoding):
    fields = {key: metric(wire(key) + b':' + wire(item), encoding) for key, item in value.items()}
    punctuation = 2 + max(0, len(fields) - 1)
    assert sum(item['bytes'] for item in fields.values()) + punctuation == len(wire(value))
    return {'fields': fields, 'object_punctuation_bytes': punctuation,
            'bytes_additive': True, 'tokens_additive': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--tokenizer-cache', required=True, type=Path)
    parser.add_argument('--public-code', default=DEFAULT_CODE, type=Path)
    args = parser.parse_args()
    output = args.output.absolute()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = str(output / 'fresh-meta.duckdb')
    os.environ['IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB'] = str(output / 'fresh-seal.duckdb')
    os.environ.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE', None)
    started = time.monotonic()
    with offline() as probes:
        encoding, token_provenance = tokenizer(args.tokenizer_cache)
        modules = {name: importlib.import_module(name) for name in NAMES}
        fixture_spec = importlib.util.spec_from_file_location('offline_frontier_fixture', TEST)
        fixture = importlib.util.module_from_spec(fixture_spec)
        fixture_spec.loader.exec_module(fixture)
        before = {name: capture(module.__file__)[1] for name, module in modules.items()}
        before['qualification_fixture'] = capture(TEST)[1]
        for name, module in modules.items():
            write(output / (name + '.py'), capture(module.__file__)[0])
        write(output / 'qualification-fixture.py', capture(TEST)[0])
        write(output / 'measurement-driver.py', capture(__file__)[0])
        code_raw, code_pin = capture(args.public_code, 2_000_000)
        instruction_raw, instruction_pin = capture(INSTRUCTION, 8192)
        if sha(code_raw) != '761756ce31753e526c48d28ccbca13a5d2493b16fe37aff3e1e4d2efaf3a2bba':
            raise ValueError('captured public Bottle source differs from reviewed input')
        if sha(instruction_raw) != '89b1abdf0af19399f720233b5cdf6b2e8e0ff7b6e3fe3e2a3af0d4d298a8641a':
            raise ValueError('full public instruction differs from reviewed input')
        write(output / 'public-bottle-before.py', code_raw)
        write(output / 'public-bottle-instruction.md', instruction_raw)
        case = fixture.build_native_fixture(output / 'fresh-native-fixture', source=code_raw.decode(),
                                            source_name='bottle.py', max_results=20,
                                            query_text=instruction_raw.decode())
        frontier = modules[NAMES[0]]
        prepared = frontier.prepare_code_retrieval_frontier(**case['frontier_args'])
        reader = fixture.reader_args(case, prepared)
        selected_text = frontier.load_code_retrieval_frontier(**reader)
        selected = json.loads(selected_text)
        full = case['full']
        projected = selected.get('retrieval', selected)
        assert {k: v for k, v in projected.items() if k != 'hits'} == {k: v for k, v in full.items() if k != 'hits'}
        assert projected['hits'] == full['hits'][:len(projected['hits'])]
        assert len(projected['hits']) == prepared['included_hit_count'] if prepared['selected_transport'] == 'frontier' else projected['hits'] == full['hits']
        assert all(projected[key] is False for key in ('semantic_authority', 'execution_authority', 'completion_authority'))
        artifact, spec, database, manifest_body = fixture.read_stored_manifest(case, prepared)
        manifest = modules[NAMES[2]].manifest_from_dict(manifest_body)
        db_before = capture(database, 64_000_000)[1]
        files_before = fixture.file_inventory(case['repository'])
        metadata_before = capture(output / 'fresh-meta.duckdb', 64_000_000)[1]
        lake = output / 'configured-public-lake'
        lake.mkdir()
        write(lake / 'metadata-custody.json', wire({'scope': 'Configured public-lake directory witness; no DuckLake extension loaded.'}))
        os.environ['IPFS_ACCELERATE_META_INDEX_DUCKLAKE'] = str(lake)
        lake_before = fixture.file_inventory(lake)
        assert frontier.load_code_retrieval_frontier(**reader) == selected_text
        recovered = []
        for member in manifest.omitted_members():
            response = frontier.expand_code_retrieval_frontier(**reader, handle=member.expansion_handle,
                question='Which additional exact public-source candidate should be inspected?')
            recovered.append(response)
        assert [item['hit'] for item in recovered] == full['hits'][prepared['included_hit_count']:]
        assert capture(database, 64_000_000)[1] == db_before
        assert fixture.file_inventory(case['repository']) == files_before
        assert capture(output / 'fresh-meta.duckdb', 64_000_000)[1] == metadata_before
        assert fixture.file_inventory(lake) == lake_before
        full_wrapper = instruction_raw + b'\n\nCode retrieval context:\n' + case['full_text'].encode() + b'\n'
        selected_wrapper = instruction_raw + b'\n\nCode retrieval context:\n' + selected_text.encode() + b'\n'
        assert full_wrapper.count(instruction_raw) == selected_wrapper.count(instruction_raw) == 1
        assert projected['query_text'] == full['query_text'] == instruction_raw.decode()
        # The public instruction appears once literally in the wrapper and
        # once losslessly JSON-encoded as query_text in each matched input.
        stages = {'retrieval_appendix': comparison(case['full_text'].encode(), selected_text.encode(), encoding),
                  'literal_public_instruction_plus_appendix': comparison(full_wrapper, selected_wrapper, encoding)}
        artifacts = {'full-retrieval-context.json': case['full_text'].encode(),
                     'selected-retrieval-context.json': selected_text.encode(),
                     'full-public-input-fragment.txt': full_wrapper,
                     'selected-public-input-fragment.txt': selected_wrapper,
                     'complete-native-manifest.json': wire(manifest_body),
                     'expansion-responses.json': wire(recovered), 'frontier-preparation.json': wire(prepared),
                     'tokenizer.json': wire(token_provenance)}
        artifact_pins = {}
        for name, raw in artifacts.items():
            write(output / name, raw)
            artifact_pins[name] = metric(raw, encoding)
        after = {name: capture(module.__file__)[1] for name, module in modules.items()}
        after['qualification_fixture'] = capture(TEST)[1]
        if before != after:
            raise AssertionError('selected producer source changed during measurement')
    result = {'schema': 'terminal-public-code-frontier-local-measurement@1',
        'scope': 'Exact captured public Bottle source, native AST index, complete deterministic local vector index, actual max20 native query replay and persisted DuckDB frontier. Measures serialization only.',
        'public_instruction': instruction_pin, 'public_code': code_pin,
        'native_bindings': {'ast_index_id': case['index'].ast_index_id, 'index_id': case['index'].index_id,
            'query_id': case['result'].query.query_id, 'result_id': case['result'].result_id,
            'native_symbol_population': len(case['index'].rows), 'complete_retrieval_hit_count': len(full['hits']),
            'task_id': full['task_id'], 'task_cid': spec['task_cid'], 'task_revision': spec['task_revision'],
            'manifest_cid': manifest.manifest_cid, 'included_hit_count': prepared['included_hit_count'],
            'omitted_hit_count': prepared['omitted_hit_count'], 'selected_transport': prepared['selected_transport']},
        'preservation': {'native_header_exact': True, 'selected_hit_dicts_exact': True,
            'all_deferred_hit_dicts_recovered_exactly': True, 'complete_manifest_census_retained': True,
            'public_literal_wrapper_exact': True, 'native_query_text_exact_public_instruction': True,
            'expansion_repository_file_witness_unchanged': True, 'expansion_database_unchanged': True,
            'expansion_database_before_after': db_before},
        'public_replay_metadata_custody': {'fresh_metadata_duckdb_before_after': metadata_before,
            'configured_lake_directory_witness_before_after': lake_before,
            'unchanged': True, 'ducklake_extension_loaded': False,
            'scope': 'Actual existing fresh native metadata DuckDB and configured public-lake directory sentinel; not a hydrated DuckLake engine experiment.'},
        'stages': stages, 'field_breakdown': {'full': breakdown(full, encoding),
                                             'selected': breakdown(selected, encoding)},
        'tokenizer': token_provenance, 'artifact_pins': artifact_pins,
        'producer_pins_before': before, 'producer_pins_after': after,
        'subprocess_probes': probes, 'elapsed_seconds': time.monotonic() - started,
        'claims': {'provider_calls': 0, 'network_calls': 0, 'provider_usage_measured': False,
            'embedding_quality_measured': False, 'learned_embeddings': False,
            'source_behavior_proven': False, 'benchmark_success_measured': False,
            'original_indexes_used': False, 'owner_signing_keys_used': False},
        'limitations': ['LOCAL o200k_base counts are representation measurements, not provider totals or the asserted configured-model tokenizer.',
            'Deterministic vector equality/tie ordering is a serialization fixture, not intent relevance or a learned embedding model.',
            'Native AST/query replay proves source freshness and nominations, not code behavior, contract satisfaction, proof correctness, convergence or benchmark success.',
            'The captured public source has historical capture provenance; no hidden verifier, solution or after-code was read.',
            'The input fragment excludes the remaining production context capsule, provider system/tools, workspace advisory and other retrieval families.',
            'This measurement retains native query_text exactly, including its encoded instruction, and separately retains the same literal public instruction wrapper.']}
    write(output / 'measurement.json', json.dumps(result, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n')
    print(json.dumps({'measurement': str(output / 'measurement.json'), 'stages': stages,
                      'native_bindings': result['native_bindings']}, sort_keys=True))


if __name__ == '__main__':
    main()
