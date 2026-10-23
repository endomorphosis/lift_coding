"""Bounded ordinary host materialization, separate from all native phases.

Rejoins exact reviewed decoder/test/fixture bodies and complete sealed proof
scopes. Ranker bytes are AST data; no source ranker or training is executed.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import resource
import subprocess

W = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
HELPER = W/'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-02/container_core_file_helpers_01.py'


def need(value, message):
    if value is not True: raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU,(20,20))
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(1024**2,1024**2))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    raw = HELPER.read_bytes()
    need(len(raw)==17601 and hashlib.sha256(raw).hexdigest()=='815bec62dd2c8de4073b389dbdf62827c4a639d4f6a3e08e5e79ef83ccffff3a','immutable stdlib reader differs')
    h = {'__file__':str(HELPER),'__name__':'held_prefix_materialization_file_helpers'}
    exec(compile(raw,str(HELPER),'exec'),h)
    own=h['pin'](Path(__file__).resolve());need(own['sha256']==args.source_sha256,'reviewed materializer differs')
    pp=h['pin'](ROOT/'plan-01.json');need(pp['sha256']==args.plan_sha256,'materialization plan differs')
    plan=h['document'](pp)
    need(set(plan)=={'schema','producer_review','host_control_plan','host_control_receipt','kernel_seal','output_root'}
         and plan['schema']=='ranker-objective-prefix-decoder-materialization-plan@1','closed materialization plan required')
    gate=h['document'](plan['producer_review']);need(gate['status']=='passed_source_only' and gate['findings']==[] and gate['reviewed_source']==own,'exact materializer gate required')
    control=h['document'](plan['host_control_receipt']);need(control['status']=='passed' and control['test_groups_passed']==20
         and control['pytest_returncode']==0 and control['cleanup_errors']==[] and control['plan']==plan['host_control_plan'],'actual20hostcontrols required')
    inputs=h['document'](plan['host_control_plan']);request=h['document'](inputs['native_guard_request'])
    h['validate_guard_union'](request)
    candidate={Path(r['path']).name:r for r in inputs['candidate_pins']}
    kernel=h['document'](plan['kernel_seal'])
    need(kernel['qualified_theorem_queries']==6 and kernel['qualified_native_checks']==1
         and kernel['regular_file_count']==len(kernel['files'])==75,'actual6kernelqueries sealed required')
    kernel_review=h['document'](kernel['review'])
    kernel_request=h['document'](kernel_review['request'])
    need(len(kernel_request['strict_old_inputs'])==2512 and kernel_review['status']=='passed',
         'actual complete qualified kernel guard context required')
    def verify():
        h['validate_guard_union'](request)
        for row in [*request['strict_old_inputs'],*request['protected_live_sources'],*inputs['candidate_pins'],
                    *kernel_request['strict_old_inputs'],*kernel_request['protected_live_sources'],
                    *kernel['files'],plan['kernel_seal'],plan['host_control_receipt'],plan['host_control_plan']]:h['exact'](row)
        physical=list(Path(kernel['scope_root']).rglob('*'))
        need(not any(p.is_symlink() for p in physical)
             and {str(p) for p in physical if p.is_file()}=={r['path'] for r in kernel['files']}|{plan['kernel_seal']['path']},'complete quiet kernel census differs')
        for role,cwd in (('root',W),('child',W/'external/ipfs_accelerate')):
            expected=request['original_checkout_guards'][role]
            head=subprocess.check_output(['git','-c','core.fsmonitor=false','-C',str(cwd),'rev-parse','HEAD'],text=True,timeout=10).strip()
            need(head==expected['head'] and h['pin'](expected['index']['path'])==expected['index'],'original checkout changed')
    verify()
    buffers=[h['exact'](inputs[role],True) for role in ('draft','original_source','bindings','materialization_receipt','qualified_host_compiler')]
    decoder=candidate['objective_prefix_decoder.py'];ns={'__name__':'held_source_bound_prefix_decoder'}
    exec(compile(h['exact'](decoder,True),decoder['path'],'exec'),ns)
    calls=[];original_parse=ast.parse
    def counted_parse(*a,**kw):
        calls.append(1);return original_parse(*a,**kw)
    ast.parse=counted_parse
    try:
        decoded=ns['decode_source_bound_prefix'](*buffers)
        emitted=ns['emit_source_bound_supported_projections'](*buffers)
    finally:ast.parse=original_parse
    need(len(calls)==6 and emitted['projection_count']==4 and emitted['complete_original_prefix_emitted'] is False,
         'exact decoder/emitter AST work and narrow projections required')
    out=Path(plan['output_root']);need(out==W/'qualification/codebase_ir/ranker-objective-prefix-decoder-host-result-20261006-01','fixed fresh output scope required');out.mkdir()
    decoded_pin=h['write'](out/'decoded-prefix.json',decoded)
    lean=emitted.pop('text');raw=lean.encode();need(len(raw)==emitted['text_utf8_bytes'] and hashlib.sha256(raw).hexdigest()==emitted['text_sha256'],'exact emitted Lean source join required')
    path=out/'ObjectivePrefixProjections.lean'
    with path.open('xb') as stream:stream.write(raw)
    lean_pin=h['pin'](path)
    verify();h['verify_held']()
    receipt={'schema':'ranker-objective-prefix-decoder-host-materialization@1','status':'passed_host_only',
        'producer':own,'plan':pp,'host_controls':plan['host_control_receipt'],'decoder':decoder,'inputs':{k:inputs[k] for k in ('draft','original_source','bindings','materialization_receipt','qualified_host_compiler')},
        'decoded_prefix':decoded_pin,'emitted_source':lean_pin,'emission':emitted,'source_AST_parse_calls_observed':len(calls),
        'source_binding_records_rejoined_per_decode':17,'context_statements_rejoined_per_decode':7,'numeric_assignments_decoded':5,
        'actual_numeric_coordinates_supplied':0,'native_jobs':0,'test_jobs':0,'model_jobs':0,'metadata_jobs':0,'original_ranker_execution_calls':0,
        'guards_same':True,'kernel_checked':False,'complete_original_prefix_emitted':False,'strict_cache_admission':False,
        'full_task_satisfaction':'unknown','all32_governing_RPI_exits':'OPEN',**{k:False for k in ('proof_authority','execution_authority','completion_authority','planner_activation')}}
    result=h['write'](out/'materialization-receipt.json',receipt)
    print(json.dumps({'status':receipt['status'],'receipt':result,'projections':4,'AST_parses':6,'native_jobs':0}))


if __name__=='__main__':main()
