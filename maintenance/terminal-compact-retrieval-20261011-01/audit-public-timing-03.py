"""Provider-free historical audit timing over approved public Bottle inputs.

Fresh native fixture state may contain its own private signing keys. This script
never reads, hashes, prints, copies or exports those keys or any owner auth.
Only public native artifacts and scalar timing/input identities are inspected.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

EVIDENCE = Path(__file__).parent
CHECKOUT = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
PUBLIC_CODE = Path('/home/barberb/lift_coding/maintenance/terminal-frontier-runtime-20261011-01/production-quota-host-01/bottle.py')
AUDIT = CHECKOUT / 'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py'
private = EVIDENCE / 'audit-public-private-fixture-03'
private.mkdir(mode=0o700, exist_ok=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


report = {'schema': 'terminal-full-public-audit-timing@1', 'reviewer_provider_calls': 0,
          'target_module_imported': False, 'private_keys_or_auth_examined': False,
          'raw_provider_prompts_exported': False, 'source_before': sha(AUDIT.read_bytes()),
          'stages': {}, 'collections': []}


def timed(label, action):
    started = time.monotonic()
    result = action()
    report['stages'][label] = time.monotonic() - started
    print(json.dumps({'stage': label, 'seconds': report['stages'][label]}), flush=True)
    return result


from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata
from benchmarks.agent_supervisor.container_coding import test_terminal_compact_intent_experiment as public_fixture
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

code = PUBLIC_CODE.read_bytes()
assert len(code) == 175565 and sha(code) == '761756ce31753e526c48d28ccbca13a5d2493b16fe37aff3e1e4d2efaf3a2bba'
with public_replay_without_metadata():
    case = timed('public_native_symbolic_case', lambda: public_fixture.build_public_case(private / 'case', bottle_source=code))
    root, state, task = case['repository'], case['directory'] / 'state', case['task']
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
            required=True, chunk_bytes=16384))
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
    router_prompt = native + residual_text + public_text
    model, advisory = render_model_prompt(prompt=router_prompt, purpose='coding', workspace=workspace)
    receipt = {'schema':'router-implementation-invocation@1','phase':'coding','purpose':'coding','invocation_id':'offline-public-audit',
        'workspace':str(workspace),'prompt_sha256':sha(native.encode()),'prompt_bytes':len(native.encode()),
        'native_prompt_sha256':sha(native.encode()),'native_prompt_bytes':len(native.encode()),
        'router_prompt_sha256':sha(router_prompt.encode()),'router_prompt_bytes':len(router_prompt.encode()),
        'model_prompt_sha256':sha(model.encode()),'model_prompt_bytes':len(model.encode()),
        'workspace_advisory_sha256':sha(advisory.encode()),'workspace_advisory_bytes':len(advisory.encode()),
        'semantic_transport':'native','semantic_translation':None,'semantic_context_verification':neutral,
        'doctor_residual_context':residual_receipt,'public_instruction':public_receipt}
    audit_state = private / 'audit-state'; audit_state.mkdir(); (audit_state / 'launch').mkdir()
    (audit_state / 'launch/offline-base-context-capsule.json').write_text(compiled.capsule.to_json())
    expected = {'task_cid':task.task_cid,'semantic_root_cid':context['semantic_root_cid'],
                'world_snapshot_cid':context['world_snapshot_cid'],'index_id':snapshot.index_id}
    (audit_state / 'prepared.json').write_bytes(canonical(case['prepared']))
    (audit_state / 'context-result.json').write_bytes(canonical(expected))
    # This is a fixture-only receipt containing hashes and public nominations,
    # never the model task prompt or any actual provider output.
    (private / 'fixture-receipt.json').write_bytes(canonical(receipt))
    (private / 'fixture-locations.json').write_bytes(canonical({'state':str(audit_state),
        'workspace_root':str(workspace_root),'repository':str(root)}))
    (root / 'bottle.py').write_bytes(code + b'\n# Authored publication successor for historical audit qualification.\n')
    subprocess.run(['git','-C',str(root),'worktree','remove','--force',str(workspace)],check=True,capture_output=True)

report['fixture'] = {'source_bytes':len(code),'source_sha256':sha(code),'public_instruction_bytes':len(case['source']),
    'public_instruction_sha256':sha(case['source']),'required_requirements':len(case['context']['requirement_ids']),
    'permitted_requirements_excluded':2,'native_symbols':len(snapshot.rows),'native_query_hits':len(result.hits),
    'typed_residual_status':doctor_result['status'],'native_prompt_bytes':len(native.encode()),
    'residual_bytes':len(residual_text.encode()),'public_block_bytes':len(public_text.encode()),
    'model_prompt_bytes':len(model.encode()),'actual_intent_transport':public_receipt['intent_requirements_projection']['transport'],
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
for seconds in (3.,10.):
    started = time.monotonic()
    observed = audit.collect_terminal_context_audit(state=audit_state,receipts=[receipt],workspace_root=workspace_root,timeout_seconds=seconds)
    report['collections'].append({'budget_seconds':seconds,'seconds':time.monotonic()-started,
        'status':observed['status'],'reason':observed['reason'],'read_errors':observed['read_errors']})
report['source_after'] = sha(AUDIT.read_bytes())
assert report['source_before'] == report['source_after']
assert PUBLIC_CODE.read_bytes() == code
(EVIDENCE / 'audit-public-timing-03.json').write_bytes(json.dumps(report,sort_keys=True,indent=2).encode()+b'\n')
print(json.dumps(report,sort_keys=True),flush=True)
