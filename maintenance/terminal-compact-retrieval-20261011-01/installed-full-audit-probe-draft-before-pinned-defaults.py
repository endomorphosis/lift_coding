"""Installed owner-only public audit qualification; no provider or target imports.

Only fresh copied public inputs live under /app/.runtime/<nonce>. Signing,
control and audit state stay in /opt/ipfs-supervisor/state/<nonce>. Underlying
native profile code signs with fresh fixture keys; this script never examines,
hashes, copies, exports or prints any private key or provider auth bytes.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import time

ROOT = Path('/opt/ipfs-supervisor')
APP = Path('/app')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runtime-manifest', type=Path, required=True)
parser.add_argument('--runtime-manifest-sha256', required=True)
parser.add_argument('--public-code', type=Path, default=APP/'bottle.py')
parser.add_argument('--public-instruction', type=Path, required=True)
parser.add_argument('--name', default='full-public-audit-01')
arguments = parser.parse_args()
ORIGINAL_STDOUT = sys.stdout
class SuppressedPublicStdout:
    encoding = 'utf-8'
    def __init__(self):
        self.bytes = 0
        self.digest = hashlib.sha256()
    def write(self, text):
        raw = text.encode('utf-8')
        self.bytes += len(raw)
        if self.bytes > 1024*1024:
            raise ValueError('qualification stdout budget exceeded')
        self.digest.update(raw)
        return len(text)
    def flush(self):
        pass
    def isatty(self):
        return False
SUPPRESSED_STDOUT = SuppressedPublicStdout()
sys.stdout = SUPPRESSED_STDOUT
if os.getuid() != 1000 or os.geteuid() != 1000:
    raise ValueError('installed supervisor owner UID required')
if re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', arguments.name) is None:
    raise ValueError('bounded fresh qualification name required')
os.umask(0o022)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['PYTHONPATH'] = ':'.join(str(ROOT/part) for part in ('source','datasets','kit'))
sys.path[:0] = os.environ['PYTHONPATH'].split(':')
os.environ['GIT_CONFIG_NOSYSTEM'] = '1'
os.environ['GIT_CONFIG_GLOBAL'] = '/dev/null'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
canonical_bytes = canonical

def protected_read(path, maximum, *, installed=False):
    path = Path(path).absolute()
    if path.resolve(strict=True) != path:
        raise ValueError('canonical qualification input required')
    if any(path.is_relative_to(ROOT/part) for part in ('state','home','codex-auth')):
        raise ValueError('private existing owner input refused')
    descriptor = os.open(path, os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
    with os.fdopen(descriptor,'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<before.st_size<=maximum or stat.S_IMODE(before.st_mode)&0o022 or installed and before.st_uid!=0:
            raise ValueError('bounded protected public qualification input required')
        raw=stream.read(maximum+1)
        after=os.fstat(stream.fileno())
    identity=lambda info:(info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
    if len(raw)>maximum or identity(before)!=identity(after) or identity(after)!=identity(path.lstat()):
        raise ValueError('qualification input changed during read')
    return raw

manifest_raw=protected_read(arguments.runtime_manifest,16*1024*1024,installed=True)
if re.fullmatch('[a-f0-9]{64}',arguments.runtime_manifest_sha256) is None or sha(manifest_raw)!=arguments.runtime_manifest_sha256:
    raise ValueError('independent installed manifest pin differs')
MANIFEST=json.loads(manifest_raw)
MANIFEST_FILES={row['path']:row for row in MANIFEST['files']}
PUBLIC_CODE=arguments.public_code.absolute()
if PUBLIC_CODE!=APP/'bottle.py':
    raise ValueError('only original public Bottle input permitted')
SOURCE_BYTES=protected_read(arguments.public_instruction,32768,installed=True)
if len(SOURCE_BYTES)!=3873 or sha(SOURCE_BYTES)!='89b1abdf0af19399f720233b5cdf6b2e8e0ff7b6e3fe3e2a3af0d4d298a8641a':
    raise ValueError('reviewed public instruction differs')
CHECKOUT=ROOT/'source'
AUDIT=CHECKOUT/'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py'
private=ROOT/'state'/arguments.name
private.mkdir(mode=0o700,exist_ok=False)
private.chmod(0o700)
public_parent=APP/'.runtime'
public_parent.mkdir(mode=0o755,exist_ok=True)
if public_parent.is_symlink() or not public_parent.is_dir() or stat.S_IMODE(public_parent.stat().st_mode)&0o022:
    raise ValueError('protected public fixture parent required')
PUBLIC_REPOSITORY=public_parent/arguments.name
if PUBLIC_REPOSITORY.exists():
    raise ValueError('new public fixture repository required')

def pin_module(name):
    module=importlib.import_module(name)
    path=Path(module.__file__).absolute()
    raw=protected_read(path,2*1024*1024,installed=True)
    relative=path.relative_to(ROOT).as_posix()
    expected=MANIFEST_FILES.get(relative)
    if expected is None or expected['bytes']!=len(raw) or expected['sha256']!=sha(raw):
        raise ValueError('installed producer differs from archive')
    return {'module':name,'path':relative,'bytes':len(raw),'sha256':sha(raw)}

PRODUCER_NAMES=[
 'benchmarks.agent_supervisor.container_coding.terminal_context_audit',
 'benchmarks.agent_supervisor.container_coding.terminal_indexed_preparation',
 'benchmarks.agent_supervisor.container_coding.terminal_public_intent_contract',
 'benchmarks.agent_supervisor.container_coding.vector_index_preflight',
 'ipfs_accelerate_py.agent_supervisor.runtime.compact_code_retrieval',
 'ipfs_accelerate_py.agent_supervisor.runtime.verified_code_retrieval_projection',
 'ipfs_accelerate_py.agent_supervisor.runtime.router_implementation_runner',
 'ipfs_accelerate_py.agent_supervisor.runtime.router_public_instruction',
 'ipfs_accelerate_py.agent_supervisor.runtime.semantic_router_translation',
 'ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_context',
 'ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index',
 'ipfs_accelerate_py.agent_supervisor.analysis.code_symbol_vector_index',
]
producer_before=[pin_module(name) for name in PRODUCER_NAMES]
from benchmarks.agent_supervisor.container_coding.terminal_deployment import INPUT_SNAPSHOT

def original_inputs():
    return json.loads(subprocess.run([sys.executable,'-I','-c',INPUT_SNAPSHOT],check=True,capture_output=True,timeout=15).stdout)
original_before=original_inputs()

# Block Python network routes; bundled native DuckDB extensions use local
# installed assets. This is not an operating-system network tracing claim.
def refuse_network(*args,**kwargs):
    raise PermissionError('provider-free qualification forbids Python network routes')
socket.socket.connect=refuse_network
socket.socket.connect_ex=refuse_network

report={'schema':'terminal-installed-full-public-audit-probe@1','qualified':False,
    'reviewer_provider_calls':0,'target_module_imported':False,'private_keys_or_auth_examined':False,
    'raw_provider_prompts_exported':False,'source_before':sha(protected_read(AUDIT,2*1024*1024,installed=True)),
    'stages':{},'collections':[],'archive_sha256':MANIFEST['archive_sha256'],
    'runtime_manifest_sha256':sha(manifest_raw),'python':sys.version,'python_executable':sys.executable,
    'script_sha256':sha(protected_read(Path(__file__),2*1024*1024,installed=True)),
    'fixture_origin':{'public_original':'/app/bottle.py','literal_public_instruction_sha256':sha(SOURCE_BYTES),
        'public_fixture_repository':str(PUBLIC_REPOSITORY),'fresh_private_owner_fixture':str(private),
        'authored_interpretation_and_coverage':True,'no_natural_language_equivalence_or_program_proof_claim':True},
    'embedded_builder_origin':{'source_helper_path': 'benchmarks/agent_supervisor/container_coding/test_terminal_compact_intent_experiment.py', 'source_helper_sha256': '2f3b2ae044aaba6cdb7a176c87508f4e1d9eabcfb885b10c0bf1f0dc2df98cec', 'host_timing_template': 'audit-public-timing-06.py', 'host_timing_template_sha256': 'aa5ea3a22f9b52267cd6c0656ba37b474bfa08539122ce76961388d231f534cc', 'adaptations': ['public repository created at its final /app/.runtime/<name> path from the outset; signed identities are never relocated', 'original public instruction is passed as independently pinned bytes instead of reading an excluded test fixture file', 'private state/keys stay under ROOT/state/<name>; no script key inspection/export', 'actual selected compact code rendering passes code_retrieval_projected=True', 'fresh copied public Bottle publication successor is committed; allocated fixture worktree is removed before historical audits']},
}

def timed(label,action):
    started=time.monotonic();result=action();report['stages'][label]=time.monotonic()-started
    return result


def build_public_case(directory, *, bottle_source=None):
    """Build actual scanner/planner/admission/context objects in fresh state."""
    from benchmarks.agent_supervisor.container_coding import terminal_indexed_preparation as prep
    from benchmarks.agent_supervisor.container_coding.terminal_public_intent_contract import (
        PUBLIC_INSTRUCTION_SHA256, build_terminal_public_intent_profile,
    )
    from ipfs_accelerate_py.agent_supervisor.planning.intent_symbolic_planning import build_intent_symbolic_plan
    from ipfs_accelerate_py.agent_supervisor.prompt.intent_plan_coverage import check_intent_plan_coverage
    from ipfs_accelerate_py.agent_supervisor.runtime import local_planning_admission as local
    from ipfs_accelerate_py.agent_supervisor.runtime.intent_requirement_context import build_task_intent_context

    directory = Path(directory).absolute()
    directory.mkdir(parents=True, exist_ok=False)
    root = PUBLIC_REPOSITORY
    root.mkdir(mode=0o755)
    root.chmod(0o755)
    if bottle_source is not None and (type(bottle_source) is not bytes or not 1 <= len(bottle_source) <= 262144):
        raise ValueError("bounded captured public Bottle bytes required")
    original = bottle_source if bottle_source is not None else b"def application():\n    return 'authored fixture, no solution'\n"
    (root / "bottle.py").write_bytes(original)
    for args in (("init", "-q"), ("add", "."), ("-c", "user.name=Offline public fixture", "-c",
        "user.email=offline@example.invalid", "commit", "-qm", "Offline public repository fixture")):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    source = SOURCE_BYTES
    assert len(source) == 3873 and hashlib.sha256(source).hexdigest() == PUBLIC_INSTRUCTION_SHA256
    text = source.decode("utf-8")
    instruction = directory / "public-instruction.md"
    instruction.write_bytes(source)
    profile = build_terminal_public_intent_profile(source_text=text)
    contract_path = directory / "authored-reviewed-contract.json"
    contract_path.write_bytes(canonical_bytes(profile["contract"]))
    prepared = prep.prepare(repository=root, instruction=instruction, state=directory / "state",
        disable_intent_autoencoder=True, enable_source_unit_autoencoder=False,
        intent_requirement_contract=contract_path)
    if prepared["planning_strategy"] != "intent_symbolic" or prepared["request"]["planning_policy"]["allow_model"] is not False:
        raise AssertionError("public fixture must select the actual model-free symbolic path")
    planned = build_intent_symbolic_plan(profile["contract"], manifest=prepared["manifest"])
    coverage = check_intent_plan_coverage(profile["contract"], graph=planned["graph"],
        bindings=planned["requirement_bindings"])
    assert coverage == planned["coverage"] and coverage["accepted"] is True
    admission = local.admit_local_benchmark_plan(graph=planned["graph"], manifest=prepared["manifest"],
        requirement_bindings=planned["requirement_bindings"])
    local.verify_local_benchmark_admission(admission)
    task = planned["graph"].tasks[0]
    checked_coverage = admission["receipt"]["payload"]["requirement_coverage"]
    assert checked_coverage == coverage
    context = build_task_intent_context(contract=profile["contract"], graph=planned["graph"],
        coverage=checked_coverage, task_cid=task.task_cid)
    assert (root / "bottle.py").read_bytes() == original and not (root / "report.jsonl").exists()
    return dict(directory=directory, repository=root, source=source, source_text=text,
        profile=profile, prepared=prepared, planned=planned, admission=admission,
        coverage=checked_coverage, task=task, context=context,
        code_fixture_scope="captured public before/bottle.py" if bottle_source is not None else "authored tiny repository")

from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata
from benchmarks.agent_supervisor.container_coding import vector_index_preflight as vector
from benchmarks.agent_supervisor.container_coding import terminal_context_audit as audit
from ipfs_accelerate_py.agent_supervisor.runtime import local_planning_admission as local
from ipfs_accelerate_py.agent_supervisor.runtime import semantic_router_translation as semantic
from ipfs_accelerate_py.agent_supervisor.runtime import router_public_instruction as instruction
from ipfs_accelerate_py.agent_supervisor.runtime import doctor_residual_context as residual
from ipfs_accelerate_py.agent_supervisor.runtime.supervised_task_context import prepare_supervised_task_context
from ipfs_accelerate_py.agent_supervisor.analysis.code_symbol_vector_index import CodeVectorIndexSnapshot, CodeVectorSearchResult
from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository
from ipfs_accelerate_py.agent_supervisor.runtime.deterministic_doctor_runtime import DeterministicDoctorRuntime
from ipfs_accelerate_py.agent_supervisor.validation.deterministic_doctor_policy import DeterministicDoctorPolicy
from ipfs_accelerate_py.agent_supervisor.analysis.deterministic_doctor_contracts import DoctorMode
from ipfs_accelerate_py.agent_supervisor.runtime.doctor_task_workflow import prepare_doctor_task_repair, execute_doctor_task_repair
from ipfs_accelerate_py.agent_supervisor.runtime.code_retrieval_context import load_code_retrieval_context
from ipfs_accelerate_py.agent_supervisor.context.context_compiler import ContextCompiler, build_text_context_references, render_context_capsule
from ipfs_accelerate_py.agent_supervisor.context.context_contracts import ContextBudget
from ipfs_accelerate_py.agent_supervisor.semantic_state.intent_world_snapshot import load_intent_world_context, minify_intent_world_worker_context
from ipfs_accelerate_py.agent_supervisor.runtime.router_implementation_runner import render_model_prompt
from ipfs_accelerate_py.agent_supervisor.runtime import verified_code_retrieval_projection as retrieval_codec


code = protected_read(PUBLIC_CODE,262144)
assert len(code) == 175565 and sha(code) == '761756ce31753e526c48d28ccbca13a5d2493b16fe37aff3e1e4d2efaf3a2bba'
with public_replay_without_metadata():
    case = timed('public_native_symbolic_case', lambda: build_public_case(private / 'case', bottle_source=code))
    root, state, task = case['repository'], case['directory'] / 'state', case['task']
    assert case['planned']['receipt']['provider_calls']==0
    assert case['coverage']['semantic_alignment_verified'] is False
    indexed = timed('native_lexical_full_index_max5', lambda: vector.qualify(root, private / 'fresh-vectors', ['bottle.py'], case['source_text']))
    import duckdb
    with duckdb.connect(str(private / 'fresh-vectors/vectors.duckdb'), read_only=True, config={'threads': 1}) as connection:
        snapshot = CodeVectorIndexSnapshot.from_dict(json.loads(connection.execute('SELECT payload FROM snapshots WHERE id=?', [indexed['index_id']]).fetchone()[0]))
    result = CodeVectorSearchResult.from_dict(indexed['hits'])
    with IntentRepository(state / 'intent.duckdb') as intent:
        local.materialize_local_benchmark_plan(admission=case['admission'], intent=intent)
        context = timed('native_full_semantic_world_retrieval', lambda: prepare_supervised_task_context(
            repository=root, intent=intent, task_cid=task.task_cid, paths=case['prepared']['worker_inputs'],
            required_raw_paths=['.supervisor-instruction.md', '.supervisor-public-smoke.py'],
            output=root / '.runtime/audit-context', code_vector_snapshot=snapshot, code_vector_result=result,
            code_query_text=case['source_text'], semantic_max_symbols=1024,
            semantic_worker_query=case['source_text'], semantic_worker_max_bytes=32768))
        runtime = DeterministicDoctorRuntime(checkout_root=root, index_root=private / 'fresh-doctor-index',
            policy=DeterministicDoctorPolicy(enabled=True, default_mode=DoctorMode.SANDBOX_AUTO))
        candidate_ref = 'refs/heads/doctor/offline-audit-fixture'
        subprocess.run(['git', '-C', str(root), 'update-ref', candidate_ref, case['prepared']['manifest']['payload']['baseline_commit']], check=True, capture_output=True)
        doctor = timed('native_generic_doctor_prepare', lambda: prepare_doctor_task_repair(runtime=runtime,
            intent=intent, admission=case['admission'], task_cid=task.task_cid,
            state_root=private / 'fresh-doctor-workflow', solver_executable=Path('/unavailable/z3'),
            kernel_executable=Path('/unavailable/lean'), candidate_ref=candidate_ref))
        doctor_result = timed('native_generic_doctor_residual', lambda: execute_doctor_task_repair(doctor))
        assert doctor_result['status'] == 'residual'
        (root / '.runtime').chmod(0o755)
        doctor_context = residual.prepare_doctor_residual_context(prepared=doctor, result=doctor_result)
    selected_instruction = instruction.prepare_public_instruction_context(repository=root,
        admission=case['admission'], task_cid=task.task_cid, source_path='.supervisor-instruction.md',
        expected_source_sha256=sha(case['source']))
    metadata = context['metadata']
    payloads = [('semantic-context', metadata['Semantic context artifact'], (root / metadata['Semantic context artifact']).read_text()),
                ('intent-world-context', metadata['World context artifact'], json.dumps(minify_intent_world_worker_context(load_intent_world_context(artifact=root / metadata['World context artifact'], expected_sha256=metadata['World context sha256'], task_id=task.task_key, repository_id=metadata['World context repository'])), sort_keys=True, separators=(',', ':'), ensure_ascii=False)),
                ('code-retrieval-context', metadata['Code retrieval artifact'], load_code_retrieval_context(
                    repository=root, task_id=task.task_key, artifact=metadata['Code retrieval artifact'],
                    expected_sha256=metadata['Code retrieval sha256']))]
    refs = []
    for number, (kind, path, text) in enumerate(payloads):
        refs.extend(build_text_context_references(text, reference_prefix=f'public-context-{number}',
            kind=kind, path=path, repository_id=context['repository_id'], tree_id=context['semantic']['scope_cid'],
            required=True, chunk_bytes=6144))
    compiled = ContextCompiler(ContextBudget(max_input_tokens=32768, max_items=64, max_item_bytes=16384,
        max_serialized_bytes=262144)).compile(repository_id=context['repository_id'], tree_id=context['semantic']['scope_cid'],
        objective_id=task.task_key, objective_revision='sha256:public-fixture', policy_id='policy:public-fixture',
        policy_revision='sha256:public-fixture', caller='supervisor:offline-public-fixture', stage='implementation',
        goal={'id':task.task_key,'objective':task.objective}, authority={'mode':'candidate_only','completion_authority':False},
        scope={'allowed_paths':[item.path for item in task.outputs]}, acceptance={'criteria':[item.criterion for item in task.acceptance]}, evidence=refs)
    native = render_context_capsule(compiled.capsule)
    workspace_root = private / 'allocated-worktrees'; workspace_root.mkdir()
    workspace = workspace_root / 'coding'
    subprocess.run(['git','-C',str(root),'worktree','add','--detach','-q',str(workspace)],check=True,capture_output=True)
    encoded = timed('current_source_semantic_encoding_fixture_receipt', lambda: semantic.encode_semantic_router_prompt(prompt=native, repository=root))
    neutral = {'schema':'semantic-router-source-verification@1','freshness_checked':True,
               **{key:encoded.receipt[key] for key in audit.SEMANTIC_BINDINGS}}
    residual_text, residual_receipt = residual.load_doctor_residual_advisory(artifact=Path(doctor_context['artifact']),
        expected_sha256=doctor_context['sha256'], repository=root, task_cid=task.task_cid, prompt=native, workspace=workspace)
    public_text, public_receipt = instruction.load_public_instruction(artifact=Path(selected_instruction['artifact']),
        expected_sha256=selected_instruction['sha256'], repository=root, task_cid=task.task_cid, prompt=native,
        workspace=workspace, requirements_transport='compact')
    root.chmod(0o755)
    # Only known public replay paths are protected; no private key directory is
    # walked, hashed or exported. These are fresh fixture inputs, never owner DBs.
    for path in [metadata['Semantic context artifact'], metadata['Code retrieval artifact']]:
        target = root / path
        target.chmod(0o644)
        for directory in target.parents:
            if directory == root:
                break
            directory.chmod(0o755)
    code_artifact = json.loads((root / metadata['Code retrieval artifact']).read_bytes())
    if code_artifact.get('schema') == 'supervisor-code-retrieval-artifact@2':
        snapshot_path = root / code_artifact['snapshot_ref']['path']
        snapshot_path.chmod(0o644)
        for directory in snapshot_path.parents:
            if directory == root:
                break
            directory.chmod(0o755)
    for path in case['prepared']['worker_inputs']:
        (root / path).chmod(0o444)
    source_text = retrieval_codec.extract_verified_public_instruction_source(public_text, public_receipt)
    decoder = retrieval_codec.decoder_command_prefix(repository=root, source_path=public_receipt['source_path'], source_sha256=public_receipt['source_sha256'], native_prompt_sha256=sha(native.encode()))
    compact_native, code_projection = timed('current_native_code_projection', lambda: retrieval_codec.project_verified_code_retrieval_prompt(prompt=native, repository=root, source_text=source_text, decoder_command=decoder))
    assert code_projection['selected_transport'] == 'compact'
    router_prompt = native + residual_text + public_text
    model, advisory = render_model_prompt(prompt=router_prompt, purpose='coding', workspace=workspace)
    receipt = {'schema':'router-implementation-invocation@1','phase':'coding','purpose':'coding','invocation_id':'offline-public-audit',
        'workspace':str(workspace),'prompt_sha256':sha(native.encode()),'prompt_bytes':len(native.encode()),
        'native_prompt_sha256':sha(native.encode()),'native_prompt_bytes':len(native.encode()),
        'router_prompt_sha256':sha(router_prompt.encode()),'router_prompt_bytes':len(router_prompt.encode()),
        'model_prompt_sha256':sha(model.encode()),'model_prompt_bytes':len(model.encode()),
        'workspace_advisory_sha256':sha(advisory.encode()),'workspace_advisory_bytes':len(advisory.encode()),
        'semantic_transport':'native','semantic_translation':None,'semantic_context_verification':neutral,
        'doctor_residual_context':residual_receipt,'public_instruction':public_receipt,
        'code_retrieval_codec':'expanded','code_retrieval_projection':None}
    compact_router = compact_native + residual_text + public_text
    compact_model, compact_advisory = render_model_prompt(prompt=compact_router, purpose='coding', workspace=workspace, code_retrieval_projected=(code_projection['selected_transport']=='compact'))
    compact_receipt = {**receipt,'invocation_id':'offline-public-audit-compact',
        'router_prompt_sha256':sha(compact_router.encode()),'router_prompt_bytes':len(compact_router.encode()),
        'model_prompt_sha256':sha(compact_model.encode()),'model_prompt_bytes':len(compact_model.encode()),
        'workspace_advisory_sha256':sha(compact_advisory.encode()),'workspace_advisory_bytes':len(compact_advisory.encode()),
        'code_retrieval_codec':'compact','code_retrieval_projection':code_projection}
    audit.validate_code_retrieval_projection_receipt(compact_receipt)
    audit_state = private / 'audit-state'; audit_state.mkdir(); (audit_state / 'launch').mkdir()
    (audit_state / 'launch/offline-base-context-capsule.json').write_text(compiled.capsule.to_json())
    expected = {'task_cid':task.task_cid,'semantic_root_cid':context['semantic_root_cid'],
                'world_snapshot_cid':context['world_snapshot_cid'],'index_id':snapshot.index_id, 'metadata':context['metadata']}
    (audit_state / 'prepared.json').write_bytes(canonical(case['prepared']))
    (audit_state / 'context-result.json').write_bytes(canonical(expected))
    # This is a fixture-only receipt containing hashes and public nominations,
    # never the model task prompt or any actual provider output.
    (private / 'fixture-receipt.json').write_bytes(canonical(receipt))
    (private / 'fixture-compact-receipt.json').write_bytes(canonical(compact_receipt))
    (private / 'fixture-locations.json').write_bytes(canonical({'state':str(audit_state),
        'workspace_root':str(workspace_root),'repository':str(root)}))
    (root / 'bottle.py').chmod(0o644)
    (root / 'bottle.py').write_bytes(code + b'\n# Authored publication successor for historical audit qualification.\n')
    subprocess.run(['git','-C',str(root),'-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','add','bottle.py'],check=True,capture_output=True)
    subprocess.run(['git','-C',str(root),'-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','user.name=Installed public audit fixture','-c','user.email=offline@example.invalid','commit','-qm','Authored historical audit successor'],check=True,capture_output=True)
    subprocess.run(['git','-C',str(root),'worktree','remove','--force',str(workspace)],check=True,capture_output=True)

report['fixture'] = {'source_bytes':len(code),'source_sha256':sha(code),'public_instruction_bytes':len(case['source']),
    'public_instruction_sha256':sha(case['source']),'required_requirements':len(case['context']['requirement_ids']),
    'permitted_requirements_excluded':sum(row['modality']=='permitted' for row in case['profile']['ledger']['requirements']),'native_symbols':len(snapshot.rows),'native_query_hits':len(result.hits),
    'typed_residual_status':doctor_result['status'],'native_prompt_bytes':len(native.encode()),
    'residual_bytes':len(residual_text.encode()),'public_block_bytes':len(public_text.encode()),
    'model_prompt_bytes':len(model.encode()),'compact_code_model_prompt_bytes':len(compact_model.encode()),
    'code_projection':audit.validate_code_retrieval_projection_receipt(compact_receipt), 'actual_intent_transport':public_receipt['intent_requirements_projection']['transport'],
    'current_fixture_source_superseded':True,'allocated_workspace_removed':True}
parsed = audit._receipt(receipt, workspace_root)
with public_replay_without_metadata():
    timed('capsule_inventory_native_render', lambda: audit._capsule((audit_state / 'launch/offline-base-context-capsule.json').read_bytes(), expected=expected, prepared=case['prepared']))
    timed('historical_semantic_encoder_suppressed', lambda: semantic.replay_semantic_router_prompt_for_audit(prompt=native, repository=root))
    parts = semantic._prompt_parts(native)
    timed('historical_semantic_producer_verification_only_suppressed', lambda: semantic._verified_semantic(root,
        artifact=parts[5], text=parts[4], task_id=parts[0]['objective_id'], current=False))
    timed('historical_doctor_residual_suppressed', lambda: residual.load_doctor_residual_advisory(
        artifact=Path(residual_receipt['artifact']), expected_sha256=residual_receipt['artifact_sha256'],
        repository=root, task_cid=task.task_cid, prompt=native, require_current_source=False))
    timed('historical_public_compact_intent_suppressed', lambda: instruction.load_public_instruction(
        artifact=Path(public_receipt['artifact']), expected_sha256=public_receipt['artifact_sha256'],
        repository=root, task_cid=task.task_cid, prompt=native, require_current_source=False, requirements_transport='compact'))
    direct = timed('direct_full_audit_suppressed', lambda: audit.audit_terminal_context(state=audit_state,
        receipts=[receipt], workspace_root=workspace_root))
    report['direct_suppressed_status'] = direct['status']
    report['direct_suppressed_read_errors'] = direct['read_errors']
    compact_direct = timed('direct_full_compact_code_audit_suppressed', lambda: audit.audit_terminal_context(state=audit_state, receipts=[compact_receipt], workspace_root=workspace_root))
    report['compact_direct_status'] = compact_direct['status']
    report['compact_direct_read_errors'] = compact_direct['read_errors']
    assert direct['all_observed_coding_inputs_verified'] is True
    assert compact_direct['all_observed_coding_inputs_verified'] is True
for mode, row in [('expanded', receipt), ('compact', compact_receipt)]:
    for seconds in (3.,10.):
        started = time.monotonic()
        observed = audit.collect_terminal_context_audit(state=audit_state,receipts=[row],workspace_root=workspace_root,timeout_seconds=seconds)
        report['collections'].append({'code_retrieval_codec':mode,'budget_seconds':seconds,'seconds':time.monotonic()-started,
            'status':observed['status'],'reason':observed['reason'],'read_errors':observed['read_errors'],
            'all_observed_coding_inputs_verified':observed.get('all_observed_coding_inputs_verified') is True})


report['source_after']=sha(protected_read(AUDIT,2*1024*1024,installed=True))
report['producers_before']=producer_before
report['producers_after']=[pin_module(name) for name in PRODUCER_NAMES]
report['installed_producer_pins_unchanged']=report['producers_before']==report['producers_after']
original_after=original_inputs()
report['original_tracked_task_inputs_preserved']=(original_before['files']==original_after['files'] and original_before['head']==original_after['head'] and original_before['report_exists']==original_after['report_exists'])
report['original_tracked_input_count']=len(original_before['files'])
report['original_task_head']=original_before['head']
report['original_public_code_sha256']=sha(protected_read(PUBLIC_CODE,262144))
report['new_public_fixture_head']=subprocess.run(['git','-C',str(PUBLIC_REPOSITORY),'rev-parse','HEAD'],check=True,capture_output=True,text=True,timeout=10).stdout.strip()
report['fixture_original_baseline']=case['prepared']['manifest']['payload']['baseline_commit']
report['fixture_publication_changed_head']=report['new_public_fixture_head']!=report['fixture_original_baseline']
report['fixture']['required_requirements_exactly17']=report['fixture']['required_requirements']==17
report['fixture']['permitted_requirements_excluded_exactly2']=report['fixture']['permitted_requirements_excluded']==2
report['cold_audit_10_seconds_verified_both_modes']=all(row['status']=='verified' and row['all_observed_coding_inputs_verified'] is True for row in report['collections'] if row['budget_seconds']==10.)
report['cold_audit_3_second_outcomes_recorded_without_budget_change']=True
report['scope']='Installed owner-only genuine symbolic17required+2permission plan/admission over public Bottle426symbols/native lexical max5; typed Doctor residual, compact IntentIR, original/compact code inputs, historical audited original Git blobs after fresh public-copy publication/worktree removal. Authored source interpretation; no task proof, model fit, target import, provider call or benchmark reward.'
report['qualified']=(report['source_before']==report['source_after'] and report['installed_producer_pins_unchanged'] and report['original_tracked_task_inputs_preserved'] and report['fixture_publication_changed_head'] and report['fixture']['required_requirements_exactly17'] and report['fixture']['permitted_requirements_excluded_exactly2'] and report['fixture']['native_symbols']==426 and report['fixture']['native_query_hits']==5 and report['direct_suppressed_status']=='verified' and report['compact_direct_status']=='verified' and report['cold_audit_10_seconds_verified_both_modes'])
report['actual_compact_code_transport']=code_projection['selected_transport']
report['suppressed_public_library_stdout_bytes']=SUPPRESSED_STDOUT.bytes
report['suppressed_public_library_stdout_sha256']=SUPPRESSED_STDOUT.digest.hexdigest()
if not report['qualified']:
    ORIGINAL_STDOUT.write(json.dumps(report,sort_keys=True,ensure_ascii=True)+'\n')
    ORIGINAL_STDOUT.flush()
    raise ValueError('installed full public audit qualification failed; preserved fresh fixture and curated outcomes')
raw=json.dumps(report,sort_keys=True,indent=2).encode()+b'\n'
with (private/'curated-audit-receipt.json').open('xb') as stream:
    stream.write(raw)
os.chmod(private/'curated-audit-receipt.json',0o600)
ORIGINAL_STDOUT.write(json.dumps(report,sort_keys=True,ensure_ascii=True)+'\n')
ORIGINAL_STDOUT.flush()
