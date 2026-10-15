"""Provider-free installed-runtime qualification of public retrieval frontiers.

Run owner mode as installed supervisor UID1000. It creates only a new passive
public source fixture, an allocated Git worktree, and NEW synthetic owner state.
The existing validation-worker bootstrap runs this same pinned script as
UID1001; worker mode executes the exact emitted expansion CLI. No target module,
provider, model, verifier, or owner credential is imported or read.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shlex
import socket
import stat
import subprocess
import sys
import time
import uuid

ROOT = Path('/opt/ipfs-supervisor')
APP = Path('/app')
MAX_FILE = 256 * 1024 * 1024
SCHEMA = 'terminal-installed-frontier-worker-probe@1'
NAMES = (
    'ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_frontier',
    'ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_context',
    'ipfs_accelerate_py.agent_supervisor.context.database_context',
    'ipfs_accelerate_py.agent_supervisor.analysis.code_symbol_vector_index',
    'ipfs_accelerate_py.agent_supervisor.analysis.program_ast_adapters',
    'ipfs_accelerate_py.agent_supervisor.analysis.analysis_ast_index',
    'ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index',
    'ipfs_accelerate_py.agent_supervisor.runtime.compact_code_retrieval',
    'ipfs_accelerate_py.agent_supervisor.runtime.verified_code_retrieval_projection',
    'ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_wire_delivery',
    'ipfs_accelerate_py.agent_supervisor.runtime.router_implementation_runner',
    'ipfs_accelerate_py.agent_supervisor.runtime.candidate_execution',
    'ipfs_accelerate_py.agent_supervisor.runtime.container_worker_boundary',
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def persistent(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def pin(path, maximum=MAX_FILE, *, root_protected=False):
    path = Path(path).absolute()
    resolved = path.resolve(strict=True)
    need(stat.S_ISREG(resolved.stat().st_mode), 'bounded regular input required')
    if root_protected:
        need(resolved.is_relative_to(ROOT), 'installed producer escaped runtime root')
        for member in (resolved, *resolved.parents):
            info = member.stat()
            need(info.st_uid == 0 and not info.st_mode & 0o022, 'installed producer is not root protected')
    before = resolved.stat()
    with resolved.open('rb') as stream:
        raw = stream.read(maximum + 1)
    need(len(raw) <= maximum and persistent(before) == persistent(resolved.stat()), 'input changed or exceeded bound')
    return {'path': str(path), 'resolved_path': str(resolved), 'bytes': len(raw), 'sha256': sha(raw),
            'uid': before.st_uid, 'gid': before.st_gid, 'mode': stat.S_IMODE(before.st_mode)}


def inventory(root):
    root = Path(root)
    need(root.resolve(strict=True) == root.absolute(), 'witness root must be canonical')
    records = {}
    for path in sorted(root.rglob('*')):
        need(not path.is_symlink(), 'witness refuses symlinks')
        if path.is_file():
            info = path.stat()
            records[path.relative_to(root).as_posix()] = {'sha256': pin(path)['sha256'],
                'bytes': info.st_size, 'dev': info.st_dev, 'inode': info.st_ino,
                'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid,
                'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns, 'nlink': info.st_nlink}
    return records


def write_new(path, raw, mode=0o644):
    with Path(path).open('xb') as stream:
        stream.write(raw)
    Path(path).chmod(mode)


@contextmanager
def no_parent_network():
    original, original_ex = socket.socket.connect, socket.socket.connect_ex
    def refuse(*args, **kwargs):
        raise AssertionError('qualification process cannot open a network connection')
    socket.socket.connect = socket.socket.connect_ex = refuse
    try:
        yield
    finally:
        socket.socket.connect, socket.socket.connect_ex = original, original_ex


def heavy_source():
    sections = []
    for number in range(20):
        lines = [f'def operation_{number:02d}_qualified_public_lookup_and_validation(service, payload):']
        lines += [f'    value_{call} = service.resolve_public_namespace_{call:02d}_for_request(payload)' for call in range(8)]
        lines.append('    return (' + ', '.join(f'value_{call}' for call in range(8)) + ')')
        sections.append('\n'.join(lines))
    return '\n\n'.join(sections) + '\n'


def modules_and_pins():
    modules = {name: importlib.import_module(name) for name in NAMES}
    return modules, {name: pin(module.__file__, root_protected=True) for name, module in modules.items()}


def runtime_provenance(arguments, producers):
    manifest_pin = pin(arguments.runtime_manifest, 16 * 1024 * 1024, root_protected=True)
    need(manifest_pin['sha256'] == arguments.runtime_manifest_sha256, 'runtime manifest digest differs')
    manifest = json.loads(Path(arguments.runtime_manifest).read_bytes())
    need(manifest['schema'] == 'terminal-supervisor-runtime-archive@1'
         and manifest['archive_sha256'] == arguments.archive_sha256
         and manifest['runtime_python_version'] == '3.12.12'
         and manifest['codex_version'] == '0.158.0', 'runtime archive provenance differs')
    need(sys.version.split()[0] == manifest['runtime_python_version'], 'installed Python version differs')
    entries = {row['path']: row for row in manifest['files']}
    for name, observed in producers.items():
        relative = Path(observed['resolved_path']).relative_to(ROOT).as_posix()
        expected = entries.get(relative)
        need(expected is not None and expected['sha256'] == observed['sha256']
             and expected['bytes'] == observed['bytes'], 'installed source differs from archive: ' + name)
    import duckdb
    native = importlib.util.find_spec('_duckdb')
    libraries = {'duckdb_python': pin(duckdb.__file__, root_protected=True)}
    if native is not None and native.origin:
        libraries['duckdb_native'] = pin(native.origin, root_protected=True)
    expected_duckdb = [item.split('==', 1)[1] for item in manifest['base_requirements'] if item.startswith('duckdb==')]
    need(expected_duckdb == [importlib.metadata.version('duckdb')], 'installed DuckDB version differs')
    with duckdb.connect(':memory:', config={'threads': 1, 'autoload_known_extensions': False,
            'autoinstall_known_extensions': False}) as connection:
        platform = connection.execute('PRAGMA platform').fetchone()[0]
    cached_extensions = {}
    for extension in ('ducklake', 'httpfs', 'quack'):
        asset = ROOT / 'extensions' / (extension + '.duckdb_extension')
        observed = pin(asset, root_protected=True)
        expected = entries.get(asset.relative_to(ROOT).as_posix())
        need(expected is not None and expected['bytes'] == observed['bytes']
             and expected['sha256'] == observed['sha256'], 'runtime extension differs from archive')
        libraries['archive_extension_' + extension] = observed
        cached = ROOT / 'home/.duckdb/extensions' / ('v' + duckdb.__version__) / platform / asset.name
        cached_extensions[extension] = pin(cached)
        need(cached_extensions[extension]['sha256'] == observed['sha256'], 'owner installed extension cache differs from archive')
    return {'runtime_manifest': manifest_pin, 'archive_sha256': arguments.archive_sha256,
        'python_version': sys.version.split()[0], 'python_executable': pin(sys.executable, root_protected=True),
        'duckdb_version': importlib.metadata.version('duckdb'), 'duckdb_platform': platform,
        'libraries': libraries, 'owner_extension_cache_pins': cached_extensions,
        'library_integrity_scope': 'Observed installed owner/worker-identical file hashes and pinned version; source hashes independently checked against archive manifest.'}


def deny_open(path, flags):
    try:
        descriptor = os.open(path, flags)
    except PermissionError:
        return True
    else:
        os.close(descriptor)
        raise ValueError('worker can open private or immutable material')


def worker(arguments):
    need(os.getuid() == os.geteuid() == 1001, 'actual installed worker UID required')
    request_path = Path(arguments.request).absolute()
    need(request_path.resolve(strict=True) == request_path and request_path.is_relative_to(APP), 'public request outside scope')
    raw = request_path.read_bytes()
    need(len(raw) <= 262144 and sha(raw) == arguments.request_sha256, 'public worker request digest differs')
    request = json.loads(raw)
    need(request['schema'] == SCHEMA and request['worker_uid'] == 1001, 'worker request schema differs')
    modules, producers = modules_and_pins()
    need(producers == request['producer_pins'], 'worker installed source differs from owner')
    need(pin(sys.executable, root_protected=True) == request['provenance']['python_executable'], 'worker interpreter differs')
    for library, expected in request['provenance']['libraries'].items():
        need(pin(expected['path'], root_protected=True) == expected, 'worker installed library differs: ' + library)
    boundary_path = ROOT / 'container-boundary.json'
    boundary = modules[NAMES[-1]].verify_container_worker_boundary(
        artifact=boundary_path, expected_sha256=pin(boundary_path)['sha256'],
        workspace=Path.cwd(), purpose='validation')
    private_denials = []
    for path in request['private_files']:
        for flags, name in ((os.O_RDONLY, 'read'), (os.O_WRONLY, 'write-open')):
            need(deny_open(path, flags), 'private access was not denied')
            private_denials.append({'path': path, 'operation': name, 'denied': True})
    for path in request['private_roots']:
        need(all(not os.access(path, mode) for mode in (os.R_OK, os.W_OK, os.X_OK)), 'owner private root accessible')
    marker = Path.cwd() / '.git'
    need(deny_open(marker, os.O_WRONLY), 'owner worktree marker writable')
    try:
        marker.unlink()
    except PermissionError:
        pass
    else:
        raise ValueError('worker can unlink owner worktree marker')
    # No inherited import path or owner environment reaches the actual CLI.
    env = {'HOME': str(ROOT / 'worker-home'), 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
           'PYTHONDONTWRITEBYTECODE': '1', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
           'IPFS_ACCELERATE_META_INDEX_DUCKDB': request['metadata_path'],
           'IPFS_ACCELERATE_META_INDEX_DUCKLAKE': request['lake_path']}
    need('PYTHONPATH' not in env, 'worker CLI inherited an import path')
    public_root = Path(request['public_root'])
    before = inventory(public_root)
    database_before = pin(request['metadata_path'])
    lake_before = inventory(request['lake_path'])
    for path in request['readonly_public_files']:
        need(deny_open(path, os.O_WRONLY), 'worker can mutate public native cache')
    recovered = []
    cli_records = []
    for handle in request['handles']:
        command = [*request['command_prefix'], '--handle', handle,
                   '--question', 'Which exact deferred public-source candidate should be inspected?']
        completed = subprocess.run(command, env=env, cwd=Path.cwd(), capture_output=True, timeout=45)
        need(completed.returncode == 0, 'emitted worker expansion CLI failed')
        need(len(completed.stdout) <= 65536 and len(completed.stderr) <= 65536, 'worker CLI output exceeds bound')
        response = json.loads(completed.stdout)
        need(response['manifest_cid'] == request['manifest_cid'] and response['task_cid'] == request['task_cid'], 'worker expansion binding differs')
        recovered.append(response['hit'])
        cli_records.append({'handle': handle, 'returncode': completed.returncode,
            'stdout_sha256': sha(completed.stdout), 'stderr_sha256': sha(completed.stderr),
            'stdout_bytes': len(completed.stdout), 'stderr_bytes': len(completed.stderr)})
    need(sha(canonical(recovered)) == request['deferred_hits_sha256'] and len(recovered) == 18, 'worker did not recover exact deferred native hits')
    need(inventory(public_root) == before and pin(request['metadata_path']) == database_before
         and inventory(request['lake_path']) == lake_before, 'worker CLI mutated public/cache/metadata witnesses')
    need(modules_and_pins()[1] == producers, 'installed worker producer changed during reads')
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    return {'schema': SCHEMA, 'role': 'worker', 'uid': os.getuid(), 'euid': os.geteuid(),
        'gid': os.getgid(), 'groups': os.getgroups(), 'workspace': str(Path.cwd()),
        'boundary': boundary, 'capabilities': {key: status[key].strip() for key in ('CapEff', 'CapPrm', 'CapAmb')},
        'no_new_privileges': status['NoNewPrivs'].strip() == '1', 'private_denials': private_denials,
        'owner_private_roots_inaccessible': True, 'owner_marker_write_unlink_denied': True,
        'owner_auth_file_present': request['owner_auth_file_present'],
        'inherited_pythonpath_used': False, 'actual_emitted_cli_invocations': cli_records,
        'exact_deferred_native_hits_recovered': 18, 'deferred_hits_sha256': sha(canonical(recovered)),
        'public_cache_metadata_lake_unchanged': True, 'producer_pins': producers,
        'provider_calls': 0, 'target_code_imported': False, 'proof_authority': False, 'completion_authority': False}


def optional_production_probe(arguments, directory, modules):
    if arguments.public_code is None:
        return None
    from benchmarks.agent_supervisor.container_coding import vector_index_preflight as qualifier
    from ipfs_accelerate_py.agent_supervisor.analysis.code_symbol_vector_index import CodeVectorIndexSnapshot, CodeVectorSearchResult
    code = Path(arguments.public_code).read_bytes()
    instruction = Path(arguments.public_instruction).read_bytes()
    need(len(code) == 175565 and sha(code) == '761756ce31753e526c48d28ccbca13a5d2493b16fe37aff3e1e4d2efaf3a2bba', 'reviewed public Bottle source differs')
    need(len(instruction) == 3873 and sha(instruction) == '89b1abdf0af19399f720233b5cdf6b2e8e0ff7b6e3fe3e2a3af0d4d298a8641a', 'reviewed public instruction differs')
    qualifier_pin = pin(qualifier.__file__, root_protected=True)
    manifest = json.loads(Path(arguments.runtime_manifest).read_bytes())
    relative = Path(qualifier_pin['resolved_path']).relative_to(ROOT).as_posix()
    expected = next((item for item in manifest['files'] if item['path'] == relative), None)
    need(expected is not None and expected['sha256'] == qualifier_pin['sha256']
         and expected['bytes'] == qualifier_pin['bytes'], 'production qualifier differs from archive')
    directory.mkdir()
    previous_metadata = os.environ.get('IPFS_ACCELERATE_META_INDEX_DUCKDB')
    previous_lake = os.environ.get('IPFS_ACCELERATE_META_INDEX_DUCKLAKE')
    os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = str(directory / 'fresh-production-metadata.duckdb')
    os.environ.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE', None)
    write_new(directory / 'bottle.py', code)
    qualified = qualifier.qualify(directory, directory / 'production-vectors', ['bottle.py'], instruction.decode())
    import duckdb
    with duckdb.connect(str(directory / 'production-vectors/vectors.duckdb'), read_only=True, config={'threads': 1}) as connection:
        snapshot = CodeVectorIndexSnapshot.from_dict(json.loads(connection.execute('SELECT payload FROM snapshots WHERE id=?', [qualified['index_id']]).fetchone()[0]))
    result = CodeVectorSearchResult.from_dict(qualified['hits'])
    need(result.query.max_results == 5 and len(result.hits) == 5, 'production query quota changed')
    context = modules[NAMES[1]].prepare_code_retrieval_context(repository=directory, task_id='PRODUCTION-QUOTA-001',
        query_text=instruction.decode(), snapshot=snapshot, result=result, output=directory / 'retrieval.json')
    full = modules[NAMES[1]].load_code_retrieval_context(repository=directory, artifact='retrieval.json',
        expected_sha256=context['sha256'], task_id='PRODUCTION-QUOTA-001')
    prepared = modules[NAMES[0]].prepare_code_retrieval_frontier(repository=directory,
        task_cid='task:production-quota-public-probe', task_id='PRODUCTION-QUOTA-001', task_revision='revision:public-instruction',
        repository_id='repo:production-quota-public-probe', tree_id=snapshot.tree_id,
        source_artifact='retrieval.json', source_sha256=context['sha256'], output=directory / 'frontier')
    args = {'repository': directory, 'artifact': prepared['metadata']['Code retrieval frontier artifact'],
        'expected_sha256': prepared['metadata']['Code retrieval frontier sha256'], 'task_id': 'PRODUCTION-QUOTA-001'}
    selected = modules[NAMES[0]].load_code_retrieval_frontier(**args)
    spec = json.loads((directory / args['artifact']).read_bytes())
    with duckdb.connect(str(directory / spec['store_path']), read_only=True, config={'threads': 1}) as connection:
        body = connection.execute('SELECT body_json FROM context_manifests WHERE manifest_cid=?', [spec['manifest_cid']]).fetchone()[0]
    manifest = modules[NAMES[2]].manifest_from_dict(json.loads(body))
    before = inventory(directory)
    recovered = [modules[NAMES[0]].expand_code_retrieval_frontier(**args, handle=member.expansion_handle,
        question='Inspect an additional exact production-quota native candidate.')['hit'] for member in manifest.omitted_members()]
    full_body = json.loads(full)
    need(recovered == full_body['hits'][2:] and inventory(directory) == before, 'production deferred hit replay or custody differs')
    need(sha((directory / 'bottle.py').read_bytes()) == sha(code), 'public source changed')
    need(pin(qualifier.__file__, root_protected=True) == qualifier_pin, 'production qualifier changed')
    receipt = {'schema': 'terminal-production-quota-frontier-probe@1', 'retrieval_model': qualified['model'],
        'production_lexical_query_max_results': 5, 'complete_hit_count': 5, 'included_hit_count': prepared['included_hit_count'],
        'omitted_hit_count': prepared['omitted_hit_count'], 'selected_transport': prepared['selected_transport'],
        'full_context_bytes': len(full.encode()), 'frontier_context_bytes': prepared['frontier_bytes'],
        'selected_context_bytes': len(selected.encode()), 'source_sha256': sha(code), 'instruction_sha256': sha(instruction),
        'query_text_sha256': sha(instruction), 'native_index_id': snapshot.index_id,
        'native_query_id': result.query.query_id, 'native_result_id': result.result_id,
        'complete_native_hits_sha256': sha(canonical(full_body['hits'])), 'deferred_native_hits_sha256': sha(canonical(recovered)),
        'native_facts_source_and_deferred_hits_unchanged': True, 'native_fact_rows_replayed': qualified['native_fact_rows_replayed'],
        'ducklake_projection_status': qualified['ducklake']['status'], 'provider_calls': 0,
        'producer': qualifier_pin,
        'scope': 'Actual production lexical qualifier/max5 over copied public Bottle and literal instruction; authored task labels, no signed IntentIR admission or learned-provider evaluation.'}
    if previous_metadata is None:
        os.environ.pop('IPFS_ACCELERATE_META_INDEX_DUCKDB', None)
    else:
        os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = previous_metadata
    if previous_lake is None:
        os.environ.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE', None)
    else:
        os.environ['IPFS_ACCELERATE_META_INDEX_DUCKLAKE'] = previous_lake
    return receipt


def owner(arguments):
    need(os.getuid() == os.geteuid() == 1000, 'installed supervisor owner UID required')
    need(re.fullmatch('[a-z0-9-]{1,48}', arguments.name) is not None, 'bounded probe name required')
    need(bool(arguments.public_code) == bool(arguments.public_instruction), 'both optional public inputs required')
    os.umask(0o022)
    public = APP / ('.' + arguments.name)
    need(not public.exists(), 'fresh public qualification namespace required')
    public.mkdir(mode=0o755)
    private = ROOT / 'state' / arguments.name
    private.mkdir(mode=0o700)
    write_new(private / 'synthetic-key', b'synthetic-noncredential-private-control\n', 0o600)
    metadata_path = private / 'fresh-metadata.duckdb'
    os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = str(metadata_path)
    os.environ.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE', None)
    modules, producers = modules_and_pins()
    provenance = runtime_provenance(arguments, producers)
    import duckdb
    owner_database = private / 'synthetic-owner.duckdb'
    with duckdb.connect(str(owner_database), config={'threads': 1}) as connection:
        connection.execute('CREATE TABLE synthetic_private_owner_probe(value INTEGER)')
        connection.execute('INSERT INTO synthetic_private_owner_probe VALUES (1)')
    owner_database.chmod(0o600)
    source_path = public / 'fixture.py'
    source = heavy_source()
    write_new(source_path, source.encode())
    relative = source_path.relative_to(APP).as_posix()
    ast = modules[NAMES[4]].build_program_evidence_index({relative: source}).ast_index
    snapshot = modules[NAMES[3]].build_code_symbol_vector_index(ast,
        forest_id='forest:passive-runtime-probe', tree_id='tree:passive-runtime-probe', coverage_id=ast.index_id,
        dimensions=2, model_id='deterministic-passive-qualification', model_revision='1',
        configuration_id='passive:2d', vectors=lambda row: (1.0, 0.0))
    result = snapshot.search((1.0, 0.0), max_results=20)
    context = modules[NAMES[1]].prepare_code_retrieval_context(repository=APP, task_id='RUNTIME-FRONTIER-001',
        query_text='public lookup and validation', snapshot=snapshot, result=result, output=public / 'retrieval.json')
    source_artifact = (public / 'retrieval.json').relative_to(APP).as_posix()
    full = modules[NAMES[1]].load_code_retrieval_context(repository=APP, artifact=source_artifact,
        expected_sha256=context['sha256'], task_id='RUNTIME-FRONTIER-001')
    prepared = modules[NAMES[0]].prepare_code_retrieval_frontier(repository=APP,
        task_cid='task:installed-runtime-frontier-probe', task_id='RUNTIME-FRONTIER-001', task_revision='revision:passive-public-fixture',
        repository_id='repo:installed-runtime-passive-probe', tree_id=snapshot.tree_id,
        source_artifact=source_artifact, source_sha256=context['sha256'], output=public / 'frontier')
    args = {'repository': APP, 'artifact': prepared['metadata']['Code retrieval frontier artifact'],
            'expected_sha256': prepared['metadata']['Code retrieval frontier sha256'], 'task_id': 'RUNTIME-FRONTIER-001'}
    packet = json.loads(modules[NAMES[0]].load_code_retrieval_frontier(**args))
    full_body = json.loads(full)
    need(prepared['selected_transport'] == 'frontier' and packet['retrieval'] == {**full_body, 'hits': full_body['hits'][:2]}, 'passive native selected pair differs')
    need(len(packet['frontier']['expansion_handles']) == 18, 'complete passive frontier census differs')
    # Public metadata must be readable and immutable to the worker, while its
    # configured owner metadata target remains inaccessible. Replay must not
    # activate that target or a configured DuckLake metadata owner.
    lake = private / 'configured-lake'
    lake.mkdir(mode=0o700)
    write_new(lake / 'synthetic-catalog-custody', b'public qualification sentinel\n', 0o600)
    public_metadata = public / 'public-metadata.duckdb'
    write_new(public_metadata, metadata_path.read_bytes())
    public_lake = public / 'configured-public-lake'
    public_lake.mkdir(mode=0o755)
    write_new(public_lake / 'metadata-custody.json', canonical({'scope': 'public configured-lake directory witness; no extension invoked during worker replay'}))
    owner_auth = ROOT / 'codex-auth/auth.json'
    private_files = [str(private / 'synthetic-key'), str(owner_database), str(metadata_path)]
    if owner_auth.exists():
        private_files.append(str(owner_auth))
    request = {'schema': SCHEMA, 'worker_uid': 1001, 'public_root': str(public),
        'task_cid': packet['task_cid'], 'manifest_cid': prepared['manifest_cid'],
        'handles': packet['frontier']['expansion_handles'], 'command_prefix': shlex.split(packet['expansion']['command_prefix']),
        'deferred_hits_sha256': sha(canonical(full_body['hits'][2:])), 'producer_pins': producers,
        'provenance': provenance, 'private_files': private_files,
        'private_roots': [str(ROOT / name) for name in ('state', 'home', 'codex-auth')],
        'owner_auth_file_present': owner_auth.exists(), 'metadata_path': str(public_metadata), 'lake_path': str(public_lake),
        'readonly_public_files': [str(source_path), str(public / 'retrieval.json'),
            str(public / 'frontier/frontier.json'), str(public / 'frontier/manifest.duckdb'), str(public_metadata)]}
    request_path = public / 'worker-request.json'
    raw = canonical(request)
    write_new(request_path, raw, 0o444)
    for path in public.rglob('*'):
        if path.is_file():
            path.chmod(0o444)
        elif path.is_dir():
            path.chmod(0o755)
    public_before, private_before = inventory(public), inventory(private)
    candidate = ROOT / 'worktrees' / arguments.name
    git_env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0',
        'GIT_CONFIG_COUNT': '2', 'GIT_CONFIG_KEY_0': 'core.hooksPath', 'GIT_CONFIG_VALUE_0': '/dev/null',
        'GIT_CONFIG_KEY_1': 'core.fsmonitor', 'GIT_CONFIG_VALUE_1': 'false'}
    subprocess.run(['git', '-c', 'safe.directory=' + str(APP), '-C', str(APP), 'worktree', 'add',
                    '--detach', str(candidate), 'HEAD'], env=git_env, check=True, capture_output=True, timeout=30)
    (candidate / '.git').chmod(0o440)
    binding = modules[NAMES[-2]].bind_candidate_runner([str(ROOT / 'bin/validation-worker')])
    completed = modules[NAMES[-2]].run_candidate(binding, [sys.executable, '-P', str(Path(__file__).absolute()),
        '--worker', '--request', str(request_path), '--request-sha256', sha(raw)],
        cwd=candidate, timeout=300, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode:
        frames = [line.strip()[:512] for line in completed.stderr.decode(errors='replace').splitlines()
                  if line.lstrip().startswith('File ')][:16]
        raise ValueError('installed worker failed: ' + json.dumps({'returncode': completed.returncode,
            'stdout_sha256': sha(completed.stdout), 'stderr_sha256': sha(completed.stderr),
            'public_traceback_frames': frames}, sort_keys=True))
    need(len(completed.stdout) <= 262144 and len(completed.stderr) <= 65536, 'qualification receipt exceeds bound')
    worker_receipt = json.loads(completed.stdout)
    need(worker_receipt['uid'] == worker_receipt['euid'] == 1001
         and worker_receipt['exact_deferred_native_hits_recovered'] == 18, 'real restricted worker evidence differs')
    need(inventory(public) == public_before and inventory(private) == private_before, 'worker mutated owner/public witnesses')
    optional = optional_production_probe(arguments, public.with_name(public.name + '-production'), modules)
    need(inventory(private) == private_before, 'separate production probe mutated private worker-qualification witnesses')
    need(modules_and_pins()[1] == producers, 'installed owner producers changed during qualification')
    need(all(pin(info['path']) == info for info in provenance['owner_extension_cache_pins'].values()),
         'installed owner extension cache changed during qualification')
    return {'schema': SCHEMA, 'qualified': True, 'role': 'owner', 'uid': os.getuid(), 'euid': os.geteuid(),
        'probe_script': pin(__file__, root_protected=True), 'provenance': provenance,
        'passive_public_fixture': {'source_sha256': sha(source.encode()), 'source_bytes': len(source.encode()),
            'native_symbol_count': len(snapshot.rows), 'native_query_max_results': 20, 'complete_hit_count': 20,
            'selected_hit_count': 2, 'deferred_hit_count': 18, 'full_context_bytes': len(full.encode()),
            'frontier_context_bytes': prepared['frontier_bytes'], 'selected_transport': prepared['selected_transport'],
            'complete_native_hits_sha256': sha(canonical(full_body['hits'])), 'manifest_cid': prepared['manifest_cid'],
            'scope': 'Authored passive source AST/local-vector serialization and worker reachability; target code never imported.'},
        'worker': worker_receipt, 'public_cache_and_synthetic_private_witnesses_unchanged': True,
        'production_quota_probe': optional, 'provider_calls': 0, 'target_code_imported': False,
        'owner_credentials_read': False, 'signed_plan_admission_claimed': False,
        'training_or_proving_performed': False, 'benchmark_success_claimed': False,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False}



_original_production_probe = optional_production_probe


def compact_worker(request_path, request_sha256):
    from ipfs_accelerate_py.agent_supervisor.runtime import compact_code_retrieval as codec
    from ipfs_accelerate_py.agent_supervisor.runtime import verified_code_retrieval_projection as verified
    need(os.getuid() == os.geteuid() == 1001, 'actual restricted codec worker required')
    request_path = Path(request_path).absolute()
    need(request_path.resolve(strict=True) == request_path and request_path.is_relative_to(APP)
         and not os.access(request_path, os.W_OK), 'protected public worker request required')
    raw = codec._read_file(request_path, 262144, source=True)
    need(len(raw) <= 262144 and sha(raw) == request_sha256, 'protected worker request differs')
    request = json.loads(raw)
    modules, producer_pins = modules_and_pins()
    need(producer_pins == request['producer_pins'], 'compact worker installed source differs from owner')
    need(pin(sys.executable, root_protected=True) == request['python_executable'], 'compact worker interpreter differs')
    manifest_path = Path(request['runtime_manifest'])
    manifest_pin = pin(manifest_path, 16 * 1024 * 1024, root_protected=True)
    need(manifest_pin['sha256'] == request['runtime_manifest_sha256'], 'compact worker runtime manifest differs')
    manifest = json.loads(manifest_path.read_bytes())
    need(manifest['schema'] == 'terminal-supervisor-runtime-archive@1'
         and manifest['archive_sha256'] == request['runtime_archive_sha256'], 'compact worker archive identity differs')
    entries = {row['path']: row for row in manifest['files']}
    for observed in producer_pins.values():
        relative = Path(observed['resolved_path']).relative_to(ROOT).as_posix()
        expected = entries.get(relative)
        need(expected is not None and expected['sha256'] == observed['sha256']
             and expected['bytes'] == observed['bytes'], 'compact worker producer differs from current archive')
    boundary_path = ROOT/'container-boundary.json'
    boundary = modules[NAMES[-1]].verify_container_worker_boundary(
        artifact=boundary_path, expected_sha256=pin(boundary_path)['sha256'],
        workspace=Path.cwd(), purpose='validation')
    root = Path(request['repository'])
    need(root.is_absolute() and root.resolve(strict=True) == root and root.is_relative_to(APP)
         and not os.access(root, os.W_OK), 'read-only public source root required')
    verified._relative(request['source_path'])
    source = codec._read_file(root / request['source_path'], codec.MAX_SOURCE_BYTES, source=True).decode('utf-8')
    wire_path = Path(request['wire'])
    need(wire_path.is_absolute() and wire_path.resolve(strict=True) == wire_path
         and wire_path.is_relative_to(root) and not os.access(wire_path, os.W_OK), 'bounded read-only public wire required')
    wire = codec._read_file(wire_path, codec.MAX_WIRE_BYTES)
    need(len(wire) <= codec.MAX_WIRE_BYTES and sha(wire) == request['wire_sha256'], 'independent wire pin differs')
    packet = json.loads(wire)
    need(type(request['guidance_version']) is int and request['guidance_version'] == 2,
         'current emitted decoder guidance required')
    rendered = request['guidance'] + '\n' + wire.decode('utf-8')
    need(len(rendered.encode()) == request['selected_prompt_bytes']
         and sha(rendered.encode()) == request['selected_prompt_sha256'], 'exact emitted rendering differs')
    need(codec.parse_code_retrieval_prompt(rendered, decoder_command=request['decoder_command'],
         guidance_version=2) == packet, 'current exact emitted guidance or wire differs')
    native = codec.decode_code_retrieval_prompt(packet, source)
    need(sha(native.encode()) == request['native_prompt_sha256'], 'independent native pin differs')
    os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = request['inaccessible_metadata_path']
    os.environ['IPFS_ACCELERATE_META_INDEX_DUCKLAKE'] = request['inaccessible_lake_path']
    before = inventory(root)
    replay = verified.verify_code_retrieval_prompt(prompt=native, repository=root, source_text=source)
    marker = ' Read-only exact decoder command: '
    need(request['guidance'].count(marker) == 1, 'single complete advertised decoder command required')
    command = request['guidance'].split(marker, 1)[1]
    need(len(command.encode()) <= 16384 and not any(char in command for char in ('\0','\r','\n')),
         'bounded single-line advertised decoder command required')
    environment = {'SUPERVISOR_CODE_RETRIEVAL_WIRE': str(wire_path)}
    result = subprocess.run(['/bin/sh', '-c', command], env=environment,
        cwd=Path.cwd(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    need(result.returncode == 0 and result.stdout == native.encode(), 'actual emitted decoder CLI did not recover exact native capsule')
    need(replay['code_hit_count'] == 5 and replay['metadata_owner_suppressed'] is True, 'complete five native hits required')
    need(inventory(root) == before, 'worker modified public native cache or source')
    for private in (ROOT/'state', ROOT/'home', ROOT/'codex-auth'):
        need(all(not os.access(private, mode) for mode in (os.R_OK, os.W_OK, os.X_OK)), 'owner root accessible to codec worker')
    need(modules_and_pins()[1] == producer_pins, 'compact worker producer changed during replay')
    return {'schema': 'terminal-installed-compact-retrieval-worker@2', 'qualified': True,
        'uid': os.getuid(), 'euid': os.geteuid(), 'native_prompt_sha256': sha(native.encode()),
        'exact_decoder_native_roundtrip': True, 'native_query_replayed_from_current_public_code': True,
        'complete_native_hits': replay['code_hit_count'], 'public_cache_source_witnesses_unchanged': True,
        'metadata_owner_suppressed': replay['metadata_owner_suppressed'], 'owner_roots_inaccessible': True,
        'wire_sha256': sha(wire), 'wire_bytes': len(wire), 'provider_calls': 0,
        'guidance_version': 2, 'exact_advertised_command_executed': True,
        'wire_arguments_manually_appended': False, 'shell_executable': '/bin/sh',
        'command_sha256': sha(command.encode()), 'command_bytes': len(command.encode()),
        'shell_environment_keys': sorted(environment), 'runtime_archive_sha256': request['runtime_archive_sha256'],
        'producer_pins': producer_pins, 'boundary': boundary,
        'signed_intent_admission_claimed': False, 'proof_authority': False, 'completion_authority': False}


def optional_production_probe(arguments, directory, modules):
    original = _original_production_probe(arguments, directory, modules)
    if original is None:
        return None
    previous_metadata = os.environ.get('IPFS_ACCELERATE_META_INDEX_DUCKDB')
    previous_lake = os.environ.get('IPFS_ACCELERATE_META_INDEX_DUCKLAKE')
    os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = str(directory/'fresh-codec-metadata.duckdb')
    os.environ.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE', None)
    try:
        return _compact_production_probe(arguments, directory, modules, original)
    finally:
        for key, value in (('IPFS_ACCELERATE_META_INDEX_DUCKDB',previous_metadata),('IPFS_ACCELERATE_META_INDEX_DUCKLAKE',previous_lake)):
            if value is None: os.environ.pop(key,None)
            else: os.environ[key]=value


def _compact_production_probe(arguments, directory, modules, original):
    from ipfs_accelerate_py.agent_supervisor.runtime import compact_code_retrieval as codec
    from ipfs_accelerate_py.agent_supervisor.runtime import verified_code_retrieval_projection as verified
    from ipfs_accelerate_py.agent_supervisor.runtime.semantic_context_runtime import prepare_semantic_context, load_semantic_worker_context
    from ipfs_accelerate_py.agent_supervisor.context.context_compiler import build_text_context_references, compile_context_capsule, render_context_capsule
    from ipfs_accelerate_py.agent_supervisor.context.context_contracts import ContextBudget
    source = Path(arguments.public_instruction).read_bytes()
    write_new(directory/'public-instruction.md', source, 0o444)
    semantic = prepare_semantic_context(repository=directory, task_id='PRODUCTION-QUOTA-001',
        paths=['bottle.py', 'public-instruction.md'], output=directory/'semantic',
        required_raw_paths=['public-instruction.md'], objective='Inspect exact native code context', max_symbols=1024, worker_query=source.decode(), worker_max_bytes=32768)
    # Use the exact native worker projection, with all producer declarations.
    semantic_text = load_semantic_worker_context(repository=directory,
        artifact='semantic/worker-context.json',
        expected_sha256=semantic['worker_payload_sha256'], task_id='PRODUCTION-QUOTA-001')
    retrieval_raw = (directory/'retrieval.json').read_bytes()
    full = modules[NAMES[1]].load_code_retrieval_context(repository=directory, artifact='retrieval.json',
        expected_sha256=sha(retrieval_raw), task_id='PRODUCTION-QUOTA-001')
    binding = dict(repository_id='repository:installed-public-codec-probe', tree_id='tree:installed-public-codec-probe',
        objective_id='PRODUCTION-QUOTA-001', objective_revision='revision:public-instruction',
        policy_id='policy:passive-public-probe', policy_revision='revision:1',
        caller='supervisor:installed-codec-probe', stage='implementation')
    refs = (*build_text_context_references(semantic_text, reference_prefix='semantic', kind='semantic-context',
        path='semantic/worker-context.json', repository_id=binding['repository_id'], tree_id=binding['tree_id'],
        required=True, chunk_bytes=6144), *build_text_context_references(full, reference_prefix='code', kind='code-retrieval-context',
        path='retrieval.json', repository_id=binding['repository_id'], tree_id=binding['tree_id'], required=True, chunk_bytes=6144))
    compiled = compile_context_capsule(**binding, budget=ContextBudget(max_input_tokens=65000,max_items=64,max_item_bytes=16384,max_serialized_bytes=256000),
        goal={'objective':'Inspect exact native code context'}, authority={'mode':'candidate_only','completion_authority':False},
        scope={'allowed_paths':['bottle.py']}, acceptance={'criteria':['exact native reconstruction']}, evidence=refs)
    native = render_context_capsule(compiled.capsule)
    decoder = verified.decoder_command_prefix(repository=directory,source_path='public-instruction.md',source_sha256=sha(source),native_prompt_sha256=sha(native.encode()))
    selected, projection = verified.project_verified_code_retrieval_prompt(prompt=native,repository=directory,source_text=source.decode(),decoder_command=decoder)
    need(projection['schema']=='supervisor-code-retrieval-prompt-projection@2'
         and type(projection['guidance_version']) is int and projection['guidance_version']==2
         and projection['selected_transport']=='compact', 'current complete installed projection should be smaller')
    packet = codec.parse_code_retrieval_prompt(selected, decoder_command=decoder, guidance_version=2)
    guidance, emitted_wire = selected.rsplit('\n', 1)
    wire = canonical(packet)
    need(emitted_wire.encode() == wire, 'advertised current wire differs from saved packet')
    write_new(directory/'compact-wire.json', wire, 0o444)
    request = {'repository':str(directory),'source_path':'public-instruction.md', 'wire':str(directory/'compact-wire.json'),
        'wire_sha256':sha(wire),'native_prompt_sha256':sha(native.encode()),'decoder_command':decoder,
        'guidance':guidance,'guidance_version':2,'selected_prompt_sha256':sha(selected.encode()),
        'selected_prompt_bytes':len(selected.encode()),'producer_pins':modules_and_pins()[1],
        'python_executable':pin(sys.executable,root_protected=True),
        'runtime_manifest':str(arguments.runtime_manifest),'runtime_manifest_sha256':arguments.runtime_manifest_sha256,
        'runtime_archive_sha256':arguments.archive_sha256,
        'inaccessible_metadata_path':str(ROOT/'state'/arguments.name/'fresh-metadata.duckdb'),
        'inaccessible_lake_path':str(ROOT/'state'/arguments.name/'configured-lake')}
    request_raw = canonical(request)
    request_path = directory/'compact-worker-request.json'
    write_new(request_path, request_raw, 0o444)
    for path in directory.rglob('*'):
        if path.is_file(): path.chmod(0o444)
        elif path.is_dir(): path.chmod(0o755)
    directory.chmod(0o755)
    before = inventory(directory)
    candidate = ROOT/'worktrees'/arguments.name
    binding = modules[NAMES[-2]].bind_candidate_runner([str(ROOT/'bin/validation-worker')])
    completed = modules[NAMES[-2]].run_candidate(binding,[sys.executable,'-P',str(Path(__file__).absolute()),
        '--compact-worker',str(request_path),'--compact-request-sha256',sha(request_raw)],cwd=candidate,timeout=120,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if completed.returncode:
        frames=[line.strip()[:512] for line in completed.stderr.decode(errors='replace').splitlines() if line.lstrip().startswith('File ')][:16]
        raise ValueError('installed compact worker failed: '+json.dumps({'returncode':completed.returncode,
            'stdout_sha256':sha(completed.stdout),'stderr_sha256':sha(completed.stderr),'public_traceback_frames':frames}))
    worker_receipt = json.loads(completed.stdout)
    need(worker_receipt['qualified'] and worker_receipt['guidance_version']==2
         and worker_receipt['exact_advertised_command_executed'] is True
         and worker_receipt['wire_arguments_manually_appended'] is False
         and worker_receipt['shell_environment_keys']==['SUPERVISOR_CODE_RETRIEVAL_WIRE']
         and inventory(directory)==before,'installed codec cache custody or exact advertised command differs')
    materialized_result = modules[NAMES[-2]].run_candidate(binding,
        [sys.executable, '-P', str(Path(__file__).absolute()), '--materialized-worker', str(request_path),
         '--compact-request-sha256', sha(request_raw)], cwd=candidate, timeout=120,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if materialized_result.returncode:
        frames=[line.strip()[:512] for line in materialized_result.stderr.decode(errors='replace').splitlines()
            if line.lstrip().startswith('File ')][:16]
        raise ValueError('installed materialized worker failed: '+json.dumps({
            'returncode':materialized_result.returncode, 'stdout_sha256':sha(materialized_result.stdout),
            'stderr_sha256':sha(materialized_result.stderr), 'public_traceback_frames':frames}))
    materialized_receipt = json.loads(materialized_result.stdout)
    need(materialized_receipt['qualified'] and inventory(directory)==before,
         'installed materialized wire probe or public custody differs')
    for module in (codec,verified):
        observed = pin(module.__file__,root_protected=True)
        relative = Path(observed['resolved_path']).relative_to(ROOT).as_posix()
        expected = next(row for row in json.loads(Path(arguments.runtime_manifest).read_bytes())['files'] if row['path']==relative)
        need(expected['sha256']==observed['sha256'] and expected['bytes']==observed['bytes'],'installed codec source differs from pinned archive')
    return {**original,'compact_code_retrieval':{'schema':'terminal-installed-production-codec-probe@1',
        'qualified':True,'projection':projection,'worker':worker_receipt,
        'materialized_worker':materialized_receipt,
        'complete_five_native_hits_retained':True,'provider_calls':0,
        'scope':'Exact protected public Bottle AST/native lexical max5, semantic source declarations and installed restricted decoder. Synthetic task labels; no signed IntentIR admission, model fit, task proof or benchmark reward.'}}


def materialized_worker(request_path, request_sha256):
    """Actual UID1001 uses a fresh wire outside candidate Git, then detects mutation."""
    from ipfs_accelerate_py.agent_supervisor.runtime import compact_code_retrieval as codec
    from ipfs_accelerate_py.agent_supervisor.runtime import verified_code_retrieval_projection as verified
    from ipfs_accelerate_py.agent_supervisor.runtime import code_retrieval_wire_delivery as delivery
    legacy = compact_worker(request_path, request_sha256)
    request = json.loads(codec._read_file(Path(request_path), 262144, source=True))
    repository = Path(request['repository'])
    source = codec._read_file(repository / request['source_path'], codec.MAX_SOURCE_BYTES, source=True).decode()
    packet = json.loads(codec._read_file(Path(request['wire']), codec.MAX_WIRE_BYTES))
    native = codec.decode_code_retrieval_prompt(packet, source)
    root = delivery.DEFAULT_DELIVERY_ROOT
    need(root == ROOT/'worker-home/context-wires' and root.stat().st_uid == 1001
         and stat.S_IMODE(root.stat().st_mode) == 0o700, 'fixed worker-owned delivery root required')
    before = inventory(repository)
    census = lambda: subprocess.check_output(['/usr/bin/git', 'status', '--porcelain=v1', '--untracked-files=all'])
    candidate_before = census()
    def select(invocation):
        path = delivery.planned_wire_path(packet, invocation_id=invocation)
        selected, projection = verified.project_verified_code_retrieval_prompt(prompt=native,
            repository=repository, source_text=source, decoder_command=request['decoder_command'],
            guidance_version=3, delivered_wire_path=str(path))
        need(projection['selected_transport']=='compact' and projection['guidance_version']==3
             and projection['wire_delivery']['materialized'] is False,
             'pure projection must retain planned delivery without claiming existing file')
        handle = delivery.materialize_verified_code_retrieval_wire(packet, source_text=source,
            expected_wire_sha256=projection['wire_sha256'], expected_wire_bytes=projection['wire_bytes'],
            expected_source_sha256=sha(source.encode()),
            expected_native_sha256=request['native_prompt_sha256'], invocation_id=invocation)
        need(handle.receipt==dict(projection['wire_delivery'], materialized=True), 'delivery pins differ')
        guidance, inline_wire = selected.rsplit('\n',1)
        need(inline_wire.encode()==Path(handle.receipt['path']).read_bytes(), 'inline/file wire mismatch')
        command = guidance.split(' Read-only exact decoder command: ',1)[1]
        need('--wire ' in command and '--expected-wire-sha256 ' in command
             and 'SUPERVISOR_CODE_RETRIEVAL_WIRE' not in command,
             'complete pinned command cannot require inherited tool variable')
        return handle, selected, projection, command
    handle, selected, projection, command = select(uuid.uuid4().hex)
    try:
        need(handle.verify() is True, 'fresh pre-command witness required')
        result = subprocess.run(['/bin/sh','-c',command], env={}, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
        need(result.returncode==0 and result.stdout==native.encode(), 'exact v3 emitted command did not decode')
        need(handle.verify() is True and census()==candidate_before, 'worker wire or candidate Git changed')
        actual_receipt = dict(handle.receipt)
    finally:
        cleanup = handle.cleanup()
    need(cleanup=='removed' and not Path(actual_receipt['path']).exists(), 'exact fresh wire cleanup required')
    negative, _, _, negative_command = select(uuid.uuid4().hex)
    negative_path = Path(negative.receipt['path'])
    original = negative_path.read_bytes()
    original_inode = (negative_path.stat().st_dev, negative_path.stat().st_ino)
    negative_path.chmod(0o600)
    negative_path.write_bytes(b'['+original[1:])
    rejected = subprocess.run(['/bin/sh','-c',negative_command], env={}, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    need(rejected.returncode!=0, 'same-UID wire hash mutation was accepted')
    negative_path.write_bytes(original)
    negative_path.chmod(0o400)
    restored_refused = False
    try:
        negative.verify()
    except ValueError:
        restored_refused = True
    need(restored_refused and negative.cleanup()=='failed' and negative_path.exists(),
         'write-and-restore must invalidate witness and preserve modified target')
    need((negative_path.stat().st_dev,negative_path.stat().st_ino)==original_inode
         and negative_path.read_bytes()==original, 'negative fixture cleanup scope differs')
    negative_path.unlink()
    negative_path.parent.rmdir()
    need(inventory(repository)==before and census()==candidate_before, 'public/candidate code changed')
    need(all(not os.access(ROOT/name,mode) for name in ('state','home','codex-auth')
             for mode in (os.R_OK,os.W_OK,os.X_OK)), 'each owner root R/W/X denial required')
    return {'schema':'terminal-installed-materialized-retrieval-worker@1', 'qualified':True,
        'uid':os.getuid(), 'euid':os.geteuid(), 'guidance_version':3,
        'wire_delivery':actual_receipt, 'exact_advertised_command_executed':True,
        'wire_arguments_manually_appended':False, 'shell_environment_keys':[],
        'exact_decoder_native_roundtrip':True, 'complete_native_hits':legacy['complete_native_hits'],
        'native_prompt_sha256':sha(native.encode()), 'selected_prompt_sha256':sha(selected.encode()),
        'selected_prompt_bytes':len(selected.encode()), 'candidate_git_census_unchanged':True,
        'public_cache_source_witnesses_unchanged':True, 'owner_roots_individually_inaccessible':True,
        'same_uid_wire_hash_mutation_refused':True, 'same_uid_write_restore_witness_refused':True,
        'exact_positive_wire_cleanup':cleanup, 'negative_fixture_removed_after_preservation_observed':True,
        'runtime_archive_sha256':request['runtime_archive_sha256'], 'producer_pins':legacy['producer_pins'],
        'provider_calls':0, 'signed_intent_admission_claimed':False, 'owner_custody':False,
        'proof_authority':False, 'completion_authority':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--request', type=Path)
    parser.add_argument('--request-sha256')
    parser.add_argument('--name', default='frontier-public-probe-01')
    parser.add_argument('--runtime-manifest', type=Path)
    parser.add_argument('--runtime-manifest-sha256')
    parser.add_argument('--archive-sha256')
    parser.add_argument('--public-code', type=Path)
    parser.add_argument('--public-instruction', type=Path)
    args = parser.parse_args()
    for value in (args.request_sha256,) if args.worker else (args.runtime_manifest_sha256, args.archive_sha256):
        need(type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None, 'exact pinned SHA256 required')
    started = time.monotonic()
    with no_parent_network():
        result = worker(args) if args.worker else owner(args)
    result['elapsed_seconds'] = time.monotonic() - started
    print(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False), flush=True)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--materialized-worker']:
        p=argparse.ArgumentParser();p.add_argument('--materialized-worker',type=Path,required=True);p.add_argument('--compact-request-sha256',required=True)
        a=p.parse_args();print(json.dumps(materialized_worker(a.materialized_worker,a.compact_request_sha256),sort_keys=True),flush=True)
    elif sys.argv[1:2] == ['--compact-worker']:
        p=argparse.ArgumentParser();p.add_argument('--compact-worker',type=Path,required=True);p.add_argument('--compact-request-sha256',required=True)
        a=p.parse_args();print(json.dumps(compact_worker(a.compact_worker,a.compact_request_sha256),sort_keys=True),flush=True)
    else:
        main()
