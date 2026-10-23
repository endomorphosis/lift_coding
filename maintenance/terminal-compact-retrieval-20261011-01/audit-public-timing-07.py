"""Frozen replay timing of a fresh provider-free public fixture, without keys.

This reuses only the public native capsule, signed nominations and generated
receipts from attempt06. That attempt's source pin changed during integration,
so its timing is retained as rejected. The updated representation header is
regenerated here with the production API, under a new fixture receipt filename.
No private signing key, provider prompt/output, verifier, solution or auth read.
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
PRIVATE = EVIDENCE / 'audit-public-private-fixture-06'
AUDIT = CHECKOUT / 'benchmarks/agent_supervisor/container_coding/terminal_context_audit.py'
SOURCE = Path('/home/barberb/lift_coding/maintenance/terminal-frontier-runtime-20261011-01/production-quota-host-01/bottle.py')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

pins = [AUDIT, CHECKOUT / 'benchmarks/agent_supervisor/container_coding/test_terminal_context_audit.py',
        CHECKOUT / 'ipfs_accelerate_py/agent_supervisor/runtime/compact_code_retrieval.py',
        CHECKOUT / 'ipfs_accelerate_py/agent_supervisor/runtime/verified_code_retrieval_projection.py',
        CHECKOUT / 'ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py',
        CHECKOUT / 'ipfs_accelerate_py/agent_supervisor/runtime/router_public_instruction.py']
before = {str(path.relative_to(CHECKOUT)): {'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size} for path in pins}
report = {'schema':'terminal-full-public-audit-frozen-timing@1','provider_calls':0,
    'private_keys_or_auth_examined':False,'raw_provider_prompts_exported':False,
    'target_code_executed':False,'emitted_decoder_executed':False,
    'scope':'provider-free owner historical audit timing; not actual worker decoder execution',
    'fixture_origin':'fresh public native objects from retained attempt06; source changed then, frozen replay here',
    'before':before,'stages':{},'cold_imports':[],'collections':[]}

def timed(name, action):
    start = time.monotonic()
    result = action()
    report['stages'][name] = time.monotonic()-start
    print(json.dumps({'stage':name,'seconds':report['stages'][name]}),flush=True)
    return result

for name, expression in [
    ('audit','from benchmarks.agent_supervisor.container_coding import terminal_context_audit'),
    ('router_and_suppression','from ipfs_accelerate_py.agent_supervisor.runtime import router_implementation_runner, supervisor_meta_index'),
    ('public_intent_loader','from ipfs_accelerate_py.agent_supervisor.runtime import router_public_instruction'),
    ('native_retrieval_loader','from ipfs_accelerate_py.agent_supervisor.runtime import code_retrieval_context'),
]:
    code = 'import time,json; started=time.monotonic(); '+expression+'; print(json.dumps({"module_seconds":time.monotonic()-started}))'
    start=time.monotonic()
    child=subprocess.run([sys.executable,'-B','-P','-c',code],cwd=CHECKOUT,check=True,capture_output=True,text=True,timeout=20)
    report['cold_imports'].append({'name':name,'process_seconds':time.monotonic()-start,
        'module_seconds':json.loads(child.stdout.strip().splitlines()[-1])['module_seconds']})

from benchmarks.agent_supervisor.container_coding import terminal_context_audit as audit
from ipfs_accelerate_py.agent_supervisor.context.context_compiler import render_context_capsule
from ipfs_accelerate_py.agent_supervisor.runtime import compact_code_retrieval as codec
from ipfs_accelerate_py.agent_supervisor.runtime import semantic_router_translation as semantic
from ipfs_accelerate_py.agent_supervisor.runtime import doctor_residual_context as residual
from ipfs_accelerate_py.agent_supervisor.runtime import router_public_instruction as public
from ipfs_accelerate_py.agent_supervisor.runtime import verified_code_retrieval_projection as verified
from ipfs_accelerate_py.agent_supervisor.runtime.router_implementation_runner import render_model_prompt
from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata

locations=json.loads((PRIVATE/'fixture-locations.json').read_bytes())
state=Path(locations['state']); root=Path(locations['repository']); workspace_root=Path(locations['workspace_root'])
expected=json.loads((state/'context-result.json').read_bytes()); prepared=json.loads((state/'prepared.json').read_bytes())
receipt=json.loads((PRIVATE/'fixture-receipt.json').read_bytes())
compact=json.loads((PRIVATE/'fixture-compact-receipt.json').read_bytes())
assert expected['metadata']['Code retrieval sha256'] == compact['code_retrieval_projection']['native_verification']['observed_artifact_sha256']
assert prepared['manifest']['payload']['sources']['bottle.py']['sha256'] == sha(SOURCE.read_bytes())
assert len(SOURCE.read_bytes()) == 175565
assert sha(SOURCE.read_bytes()) == '761756ce31753e526c48d28ccbca13a5d2493b16fe37aff3e1e4d2efaf3a2bba'
meta=Path(os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'])
lake=Path(os.environ['IPFS_ACCELERATE_META_INDEX_DUCKLAKE'])
assert not meta.exists() and not lake.exists()
with public_replay_without_metadata():
    native_observed, native=timed('capsule_inventory_native_render',lambda:audit._capsule(
        (state/'launch/offline-base-context-capsule.json').read_bytes(),expected=expected,prepared=prepared))
    assert native_observed['all_context_checks_passed'] is True
    old=timed('historical_semantic_encoder',lambda:semantic.replay_semantic_router_prompt_for_audit(prompt=native,repository=root))
    bindings=timed('native_semantic_producer_only',lambda:audit._native_semantic_bindings(prompt=native,repository=root))
    assert bindings == {key:old.receipt[key] for key in audit.SEMANTIC_BINDINGS}
    residual_text, residual_observed=timed('historical_typed_residual',lambda:residual.load_doctor_residual_advisory(
        artifact=Path(receipt['doctor_residual_context']['artifact']),expected_sha256=receipt['doctor_residual_context']['artifact_sha256'],
        repository=root,task_cid=receipt['doctor_residual_context']['task_cid'],prompt=native,require_current_source=False))
    public_text, public_observed=timed('historical_signed_public_compact_intent',lambda:public.load_public_instruction(
        artifact=Path(receipt['public_instruction']['artifact']),expected_sha256=receipt['public_instruction']['artifact_sha256'],
        repository=root,task_cid=receipt['public_instruction']['task_cid'],prompt=native,require_current_source=False,
        requirements_transport='compact'))
    for field in ('context_cid','manifest_cid','source_sha256','source_bytes','block_sha256','block_bytes','intent_requirements','intent_requirements_projection'):
        assert public_observed[field] == receipt['public_instruction'][field]
    source=verified.extract_verified_public_instruction_source(public_text,receipt['public_instruction'])
    projection=compact['code_retrieval_projection']
    timed('historical_native_code_full_census_query_ast',lambda:audit._historical_code_native(
        rendered=native,projection=projection,repository=root,prepared=prepared,expected=expected))
    projected, pure=timed('pure_code_codec_projection',lambda:codec.project_code_retrieval_prompt(
        native,source,decoder_command=projection['decoder_command']))
    assert pure == {key:value for key,value in projection.items() if key not in {'native_verification','decoder_command'}}
    router=projected+residual_text+public_text
    model, advisory=render_model_prompt(prompt=router,purpose='coding',workspace=Path(compact['workspace']),
        code_retrieval_projected=projection['selected_transport']=='compact')
    compact={**compact,'model_prompt_sha256':sha(model.encode()),'model_prompt_bytes':len(model.encode()),
        'workspace_advisory_sha256':sha(advisory.encode()),'workspace_advisory_bytes':len(advisory.encode())}
    output=PRIVATE/'fixture-compact-receipt-current-header.json'
    assert not output.exists()
    output.write_bytes(json.dumps(compact,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
    projection_summary=audit.validate_code_retrieval_projection_receipt(compact)
    for mode,row in [('expanded',receipt),('compact',compact)]:
        observed=timed('warm_complete_'+mode,lambda:audit.audit_terminal_context(state=state,receipts=[row],workspace_root=workspace_root))
        assert observed['all_observed_coding_inputs_verified'] is True, observed
        report[mode+'_warm']={'status':observed['status'],'read_errors':observed['read_errors'],
            'all_model_checks':all(observed['matches'][0]['model_input_checks'].values()),
            'native_prompt_bytes':row['native_prompt_bytes'],'model_prompt_bytes':row['model_prompt_bytes'],
            'actual_intent_transport':row['public_instruction']['intent_requirements_projection']['transport']}

for mode,row in [('expanded',receipt),('compact',compact)]:
    for seconds in (3.,10.):
        start=time.monotonic()
        observed=audit.collect_terminal_context_audit(state=state,receipts=[row],workspace_root=workspace_root,timeout_seconds=seconds)
        report['collections'].append({'code_retrieval_codec':mode,'budget_seconds':seconds,'seconds':time.monotonic()-start,
            'status':observed['status'],'reason':observed['reason'],'read_errors':observed['read_errors'],
            'exact_model_input_verified':observed['all_observed_coding_inputs_verified']})
report['fixture']={'public_source_bytes':175565,'public_source_sha256':sha(SOURCE.read_bytes()),
    'literal_instruction_bytes':3873,'literal_instruction_sha256':sha(source.encode()),
    'required_requirements':len(receipt['public_instruction']['intent_requirements']['requirement_ids']),
    'permitted_requirements_excluded':2,'native_rows':426,'native_hits':5,'typed_residual_bytes':len(residual_text.encode()),
    'compact_intent_public_block_bytes':len(public_text.encode()),'code_projection':projection_summary,
    'current_source_superseded':True,'allocated_workspace_removed':True}
assert not Path(receipt['workspace']).exists()
assert sha((root/'bottle.py').read_bytes()) != sha(SOURCE.read_bytes())
assert not meta.exists() and not lake.exists()
report['configured_metadata_db_or_lake_created']=False
report['after']={str(path.relative_to(CHECKOUT)):{'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size} for path in pins}
assert report['before'] == report['after']
(EVIDENCE/'audit-public-timing-07.json').write_bytes(json.dumps(report,sort_keys=True,indent=2).encode()+b'\n')
print(json.dumps(report,sort_keys=True),flush=True)
