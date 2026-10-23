#!/usr/bin/env python3
"""Fresh native Bottle retrieval/metadata fixture; no provider or target import."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
H = Path('/home/barberb/lift_coding/maintenance/terminal-context-budget-20261011-01')
I = Path('/home/barberb/lift_coding/maintenance/terminal-source-inspector-20261011-01')
SOURCE_SHA = '761756ce31753e526c48d28ccbca13a5d2493b16fe37aff3e1e4d2efaf3a2bba'
INSTRUCTION_SHA = '89b1abdf0af19399f720233b5cdf6b2e8e0ff7b6e3fe3e2a3af0d4d298a8641a'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    if output.exists() or output.resolve(strict=False) != output or output.parent != I:
        raise ValueError('new canonical stage-contained output required')
    source_path = H / 'public-source/bottle.py'
    instruction_path = C / 'benchmarks/agent_supervisor/container_coding/fixtures/public-bottle-instruction.md'
    raw = source_path.read_bytes()
    instruction = instruction_path.read_bytes()
    if source_path.is_symlink() or instruction_path.is_symlink() or sha(raw) != SOURCE_SHA or sha(instruction) != INSTRUCTION_SHA:
        raise ValueError('exact nominated public source/instruction required')
    output.mkdir(mode=0o755)
    repository = output / 'repository'
    repository.mkdir(mode=0o755)
    (repository / 'bottle.py').write_bytes(raw)
    (output / 'instruction.txt').write_bytes(instruction)
    sys.path.insert(0, str(C))
    import duckdb
    from benchmarks.agent_supervisor.container_coding.vector_index_preflight import qualify
    from ipfs_accelerate_py.agent_supervisor.analysis.code_symbol_vector_index import (
        CodeVectorIndexSnapshot, CodeVectorSearchResult)
    from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata
    from ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_context import (
        load_code_retrieval_context, prepare_code_retrieval_context)
    from ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_frontier import prepare_code_retrieval_frontier
    start = time.monotonic()
    # Suppress ambient metadata-owner activation. The explicit production
    # preflight still constructs only its own fresh output-local catalog/lake.
    with public_replay_without_metadata():
        indexed = qualify(repository, output / 'vectors', ['bottle.py'], instruction.decode('utf-8'))
        with duckdb.connect(str(output / 'vectors/vectors.duckdb'), read_only=True,
                config={'threads': 1, 'enable_external_access': False,
                        'autoload_known_extensions': False, 'autoinstall_known_extensions': False}) as db:
            rows = db.execute('SELECT payload FROM snapshots WHERE id=?', [indexed['index_id']]).fetchmany(2)
            if len(rows) != 1:
                raise ValueError('one exact fresh native index required')
            snapshot = CodeVectorIndexSnapshot.from_dict(json.loads(rows[0][0]))
        result = CodeVectorSearchResult.from_dict(indexed['hits'])
        task_id = 'PUBLIC-BOTTLE-INSPECTOR-001'
        task_cid = 'task:public-bottle-source-inspection-preview:' + INSTRUCTION_SHA
        prepared = prepare_code_retrieval_context(repository=repository, task_id=task_id,
            query_text=instruction.decode('utf-8'), snapshot=snapshot, result=result,
            output=repository / 'retrieval.json')
        native_text = load_code_retrieval_context(repository=repository, task_id=task_id,
            artifact='retrieval.json', expected_sha256=prepared['sha256'])
        frontier = prepare_code_retrieval_frontier(repository=repository, task_cid=task_cid,
            task_id=task_id, task_revision='sha256:' + SOURCE_SHA,
            repository_id='repo:public-bottle-inspection-preview:' + SOURCE_SHA,
            tree_id=snapshot.tree_id, source_artifact='retrieval.json',
            source_sha256=prepared['sha256'], output=repository / 'frontier')
    native = json.loads(native_text)
    assert native['status'] == 'current' and len(native['hits']) == 5
    assert native['query_text'].encode() == instruction and native['source_sha256'] == {'bottle.py': SOURCE_SHA}
    (output / 'native-retrieval-context.json').write_text(native_text)
    witness_paths = [repository / 'bottle.py', repository / 'retrieval.json',
        repository / frontier['metadata']['Code retrieval frontier artifact'],
        repository / frontier['metadata']['Code retrieval frontier artifact'].replace('frontier.json', 'manifest.duckdb'),
        output / 'vectors/vectors.duckdb', output / 'vectors/metadata.duckdb',
        output / 'vectors/metadata-lake/metadata.ducklake']
    payload = json.loads((repository / 'retrieval.json').read_bytes())
    if 'snapshot_ref' in payload:
        witness_paths.append(repository / payload['snapshot_ref']['path'])
    # Protect this newly authored public capture before source inspection;
    # these permissions do not authenticate an owner or grant proof authority.
    for directory in [output, repository, repository / 'frontier']:
        directory.chmod(0o755)
    for path in witness_paths:
        path.chmod(0o644)
    pins = []
    for path in witness_paths:
        st = path.lstat()
        if path.is_symlink() or not path.is_file():
            raise ValueError('regular fixture output required')
        value = path.read_bytes()
        pins.append({'path': str(path), 'bytes': len(value), 'sha256': sha(value),
            'witness': {key: getattr(st, key) for key in
                ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')}})
    producers = []
    for name in ['benchmarks/agent_supervisor/container_coding/vector_index_preflight.py',
        'ipfs_accelerate_py/agent_supervisor/runtime/code_retrieval_context.py',
        'ipfs_accelerate_py/agent_supervisor/runtime/code_retrieval_frontier.py',
        'ipfs_accelerate_py/agent_supervisor/analysis/code_symbol_vector_index.py',
        'ipfs_accelerate_py/agent_supervisor/runtime/supervisor_meta_index.py']:
        value = (C / name).read_bytes()
        producers.append({'path': str(C / name), 'bytes': len(value), 'sha256': sha(value)})
    summary = {'schema': 'public-bottle-native-source-inspector-fixture@1',
        'repository': str(repository), 'instruction_sha256': INSTRUCTION_SHA,
        'source_sha256': SOURCE_SHA, 'native_index_id': snapshot.index_id,
        'native_symbols': len(snapshot.rows), 'native_fact_rows_replayed': indexed['native_fact_rows_replayed'],
        'native_query_id': result.query.query_id, 'native_result_id': result.result_id,
        'task_id': task_id, 'task_cid': task_cid, 'task_scope': 'fresh public qualification fixture; not signed live benchmark admission',
        'source_artifact': 'retrieval.json', 'source_artifact_sha256': prepared['sha256'],
        'frontier_artifact': frontier['metadata']['Code retrieval frontier artifact'],
        'frontier_artifact_sha256': frontier['metadata']['Code retrieval frontier sha256'],
        'frontier_selected_transport': frontier['selected_transport'],
        'public_capture_repository_and_inspector_input_permissions': 'directories0755/files0644; observed policy protection, not immutable owner custody',
        'native_retrieval_bytes': len(native_text.encode()), 'hits': native['hits'],
        'vectors': 'production lexical TF-IDF over qualified names; no learned embeddings',
        'fresh_ducklake_projection': indexed['ducklake'], 'pins': pins, 'producer_pins': producers,
        'provider_calls': 0, 'target_module_imports': 0, 'training_steps': 0, 'prover_invocations': 0,
        'source_semantics_verified': False, 'task_completion': False, 'proof_authority': False,
        'execution_authority': False, 'completion_authority': False,
        'seconds': time.monotonic() - start}
    assert source_path.read_bytes() == raw and instruction_path.read_bytes() == instruction
    (output / 'summary.json').write_bytes(encoded(summary))
    print(json.dumps({'output': str(output), 'native_symbols': len(snapshot.rows),
        'hit_symbols': [hit['symbol'] for hit in native['hits']], 'ducklake': indexed['ducklake'],
        'frontier_selected_transport': frontier['selected_transport'], 'seconds': summary['seconds']}, sort_keys=True))


if __name__ == '__main__':
    main()
