"""Host-only max5 byte-gate diagnostic over the exact captured public inputs."""
import hashlib
import json
import os
from pathlib import Path
import time
import duckdb
from benchmarks.agent_supervisor.container_coding.vector_index_preflight import qualify
from ipfs_accelerate_py.agent_supervisor.analysis.code_symbol_vector_index import CodeVectorIndexSnapshot, CodeVectorSearchResult
from ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_context import prepare_code_retrieval_context, load_code_retrieval_context
from ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_frontier import prepare_code_retrieval_frontier, load_code_retrieval_frontier

evidence = Path(__file__).parent
output = evidence / 'production-quota-host-01'
output.mkdir()
code_path = Path('/home/barberb/lift_coding/maintenance/terminal-coding-transport-20261011-01/pilot/coding-identifiers-01/jobs/supervisor-full-identifiers-fix-code-vulnerability/fix-code-vulnerability__NW2EqdA/agent/public-output-evidence/before/bottle.py')
instruction_path = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout/benchmarks/agent_supervisor/container_coding/fixtures/public-bottle-instruction.md')
code, instruction = code_path.read_bytes(), instruction_path.read_bytes()
assert hashlib.sha256(code).hexdigest() == '761756ce31753e526c48d28ccbca13a5d2493b16fe37aff3e1e4d2efaf3a2bba'
assert hashlib.sha256(instruction).hexdigest() == '89b1abdf0af19399f720233b5cdf6b2e8e0ff7b6e3fe3e2a3af0d4d298a8641a'
(output / 'bottle.py').write_bytes(code)
os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = str(output / 'fresh-metadata.duckdb')
os.environ.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE', None)
started = time.monotonic()
qualification = qualify(output, output / 'vectors', ['bottle.py'], instruction.decode())
with duckdb.connect(str(output / 'vectors/vectors.duckdb'), read_only=True, config={'threads': 1}) as con:
    snapshot = CodeVectorIndexSnapshot.from_dict(json.loads(con.execute('SELECT payload FROM snapshots WHERE id=?', [qualification['index_id']]).fetchone()[0]))
result = CodeVectorSearchResult.from_dict(qualification['hits'])
assert result.query.max_results == len(result.hits) == 5
source = prepare_code_retrieval_context(repository=output, task_id='HOST-PRODUCTION-QUOTA-001', query_text=instruction.decode(),
    snapshot=snapshot, result=result, output=output / 'retrieval.json')
full = load_code_retrieval_context(repository=output, artifact='retrieval.json', expected_sha256=source['sha256'], task_id='HOST-PRODUCTION-QUOTA-001')
frontier = prepare_code_retrieval_frontier(repository=output, task_cid='task:host-production-quota', task_id='HOST-PRODUCTION-QUOTA-001',
    task_revision='revision:literal-public-instruction', repository_id='repo:host-production-quota', tree_id=snapshot.tree_id,
    source_artifact='retrieval.json', source_sha256=source['sha256'], output=output / 'frontier')
selected = load_code_retrieval_frontier(repository=output, artifact=frontier['metadata']['Code retrieval frontier artifact'],
    expected_sha256=frontier['metadata']['Code retrieval frontier sha256'], task_id='HOST-PRODUCTION-QUOTA-001')
receipt = {'schema': 'terminal-production-quota-host-byte-gate@1', 'provider_calls': 0, 'installed_runtime_qualified': False,
    'production_query_max_results': 5, 'actual_hit_count': len(result.hits), 'frontier': frontier,
    'full_context_bytes': len(full.encode()), 'selected_context_bytes': len(selected.encode()),
    'full_context_sha256': hashlib.sha256(full.encode()).hexdigest(), 'selected_context_sha256': hashlib.sha256(selected.encode()).hexdigest(),
    'elapsed_seconds': time.monotonic() - started}
(evidence / 'production-quota-host-01.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt), flush=True)
