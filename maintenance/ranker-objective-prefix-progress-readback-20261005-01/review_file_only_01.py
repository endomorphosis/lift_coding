"""File-only join of ordinary host controls, unqualified IR and sealed native evidence.
No candidate/helper/ranker import, compiler call, pytest, Lean or metadata job.
"""
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
W=Path('/home/barberb/lift_coding')
ROOT=Path(__file__).resolve().parent
HELD={}
AUTH=('proof_authority','execution_authority','completion_authority','planner_activation')
def pin(path):
    path=Path(path);assert path.resolve(strict=True)==path and not path.is_symlink()
    before=path.stat();raw=path.read_bytes();after=path.stat()
    assert len(raw)==before.st_size<=16*1024**2
    assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
    row={'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    assert str(path) not in HELD or HELD[str(path)]==row
    HELD[str(path)]=row;return raw,row
def exact(row):
    raw,actual=pin(row['path']);assert actual=={k:row[k] for k in ('path','bytes','sha256')};return raw
def parse(raw):
    def unique(items):
        body={}
        for key,val in items:assert key not in body;body[key]=val
        return body
    def bad(value):raise ValueError('nonfinite JSON')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=bad)
def doc(row):return parse(exact(row))
def pathdoc(path):
    raw,row=pin(path);return parse(raw),row
def false(body):assert all(body[k] is False for k in AUTH)
def sealed(root,count,bytecount):
    seal,p=pathdoc(root/'file-only-seal-01.json')
    assert seal['scope_root']==str(root) and seal['regular_file_count']==len(seal['files'])==count
    assert sum(row['bytes'] for row in seal['files'])==seal['regular_file_bytes']==bytecount
    assert len({row['path'] for row in seal['files']})==count and seal['fixture_symlinks']==seal['excluded_dependency_roots']==[]
    wire=json.dumps(seal['files'],sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
    assert hashlib.sha256(wire).hexdigest()==seal['file_inventory_sha256']
    physical=list(root.rglob('*'));assert not any(p.is_symlink() for p in physical)
    assert all(p.is_file() or p.is_dir() for p in physical)
    assert {str(p) for p in physical if p.is_file()}=={row['path'] for row in seal['files']}|{str(root/'file-only-seal-01.json')}
    for row in seal['files']:exact(row)
    false(seal);review=doc(seal['review']);false(review)
    return {'seal':p,'review':seal['review'],'regular_files':count,'regular_bytes':bytecount,'inventory':seal['file_inventory_sha256']},review
def guards(wanted):
    result={}
    for role,cwd in (('root',W),('child',W/'external/ipfs_accelerate')):
        head=subprocess.check_output(['git','-c','core.fsmonitor=false','-C',str(cwd),'rev-parse','HEAD'],timeout=10,text=True).strip()
        index=pin(wanted[role]['index']['path'])[1];assert head==wanted[role]['head'] and index==wanted[role]['index']
        result[role]={'head':head,'index':index}
    return result
def main():
    controls,controlpin=pathdoc(W/'maintenance/ranker-objective-prefix-controls-20261005-01/run-01/closed.json')
    assert controlpin['bytes']==3787 and controlpin['sha256']=='69445c990bcf7bcf6bc614cbbc68320249bc022c743f9e306da1b1dfdcf38505'
    false(controls);assert controls['status']=='passed' and controls['pytest_returncode']==0 and controls['cleanup_errors']==[] and controls['primary_error'] is None
    assert controls['test_groups_passed']==20 and controls['qualified_native_queries']==controls['native_jobs']==0
    assert controls['strict_guards_verified_before_after']==2421 and controls['protected_live_sources']==4 and controls['all_historical_and_candidate_inputs_unchanged'] is True
    assert controls['ordinary_pytest_job'] is True and controls['supervisor_lease_claimed'] is False
    plan=doc(controls['plan']);gate=doc(controls['candidate_source_review']);runnergate=doc(controls['runner_source_review'])
    false(gate);false(runnergate);assert gate['findings']==runnergate['findings']==[]
    assert plan['candidate_pins']==gate['candidate_pins'] and plan['candidate_source_review']==controls['candidate_source_review']
    for row in plan['candidate_pins']:exact(row)
    assert len(plan['candidate_pins'])==4
    exact(controls['producer'])
    for pair in controls['captured_test_sources']:
        a=exact(pair['captured']);b=exact(pair['original']);assert a==b
    stdout=exact(controls['stdout']).decode();assert '20 passed' in stdout
    report=ET.fromstring(exact(controls['junit']));cases=report.findall('.//testcase');suites=report.findall('.//testsuite')
    assert len(cases)==20 and len(suites)==1 and suites[0].get('tests')=='20'
    assert all(suites[0].get(k)=='0' for k in ('failures','errors','skipped')) and all(not list(c) for c in cases)
    assert len({c.get('name') for c in cases})==20 and {c.get('name','')[5:7] for c in cases}=={f'{i:02d}' for i in range(1,21)}
    before_heads=guards(controls['original_checkout_guards'])
    q=W/'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-02';v1=q.with_name('ranker-objective-container-core-candidate-20261005-01')
    before_v2,proof=sealed(q,34,11290575);before_v1,failed=sealed(v1,29,10856773)
    assert proof['status']=='passed' and proof['qualified_native_checks']==1 and proof['qualified_theorem_queries']==4 and proof['prior_failed_native_attempts']==1 and proof['prior_failed_qualified_queries']==0
    assert proof['request']==plan['native_guard_request'] and proof['prior_failed_seal']==before_v1['seal']
    assert failed['native_attempts']==1 and failed['qualified_native_checks']==failed['qualified_theorem_queries']==0
    request=doc(plan['native_guard_request']);strict={r['path']:r for r in request['strict_old_inputs']};live={r['path']:r for r in request['protected_live_sources']}
    assert len(strict)==2421 and len(live)==4 and all(strict[path]==row for path,row in live.items())
    check=doc(proof['check_result']);owned=doc(proof['owned_closed']);outer=doc(proof['outer_closed'])
    assert check['status']=='passed' and check['native_invocations']==check['native_lean_invocations']==1 and check['native_lean_returncode']==0
    assert owned['status']=='passed' and outer['returncode']==0 and owned['cleanup_errors']==outer['cleanup_errors']==[]
    assert owned['final_resource_state']['active_lease_count']==owned['final_resource_state']['waiting_request_count']==0
    assert [r['theorem'] for r in check['theorem_axiom_output']]==proof['queried_theorems'] and len(check['theorem_axiom_output'])==4
    assert all(r['report_occurrences']==2 and set(r['axioms'])<={'Classical.choice','Quot.sound','propext'} for r in check['theorem_axiom_output'])
    native=exact(proof['whole_native_object']);chunks=b''.join(exact(row) for row in proof['ordered_native_chunks'])
    assert native==chunks and len(native)==202632 and len(proof['ordered_native_chunks'])==4
    manifest=doc(proof['retention_manifest']);assert manifest==check['retention_manifest_body'] and manifest['aggregate_raw_object_bytes']==202632
    assert manifest['objects'][0]['chunks']==[row['name'] for row in manifest['chunks']]
    hostroot=W/'qualification/codebase_ir/ranker-objective-prefix-host-result-20261005-01'
    materialization,materialpin=pathdoc(hostroot/'materialization-receipt.json');artifact=doc(materialization['output']);false(materialization);false(artifact)
    assert {p.name for p in hostroot.iterdir()}=={'materialization-receipt.json','objective-prefix-draft.json'}
    assert materialization['status']=='passed_host_JSON_materialization_only' and materialization['host_controls']==controlpin and materialization['control_plan']==controls['plan']
    assert materialization['source_AST_parse_calls_observed']==2 and materialization['same_source_buffer_reextracted'] is True
    assert materialization['compiler'] in plan['candidate_pins'] and materialization['original_source']==plan['original_source'] and materialization['bindings']==plan['bindings']
    exact(materialization['producer']);exact(materialization['compiler']);exact(plan['original_source']);exact(plan['bindings'])
    assert artifact['schema']=='ranker-objective-container-pinned-prefix-draft@1' and artifact['status']=='DRAFT_JSON_UNQUALIFIED_UNCOMPILED'
    assert artifact['accepted_numeric_statements']==materialization['accepted_numeric_statements']==5 and len(artifact['assignments'])==5
    assert artifact['checked_context_statements']==materialization['checked_context_statements']==7
    assert len(artifact['checked_bindings'])==materialization['checked_bindings']==17
    assert artifact['shape']=={'rows':4,'columns':80,'weights':80} and artifact['admission']['coordinates_checked']==0
    assert artifact['source']=={k:plan['original_source'][k] for k in ('bytes','sha256')} and artifact['P7_bindings']=={k:plan['bindings'][k] for k in ('bytes','sha256')}
    for key,val in artifact.items():
        if key.endswith('_proved') or key.endswith('_authority') or key in ('kernel_checked','theorem_qualified','strict_cache_admission','typed_Lean_SourcePrefix_exists'):assert val is False
    for key in ('native_queries','new_tests','model_training_calls','original_ranker_import_or_execution_calls','metadata_hydration_calls'):assert materialization[key]==0
    assert artifact['new_native_jobs']==artifact['new_training_jobs']==artifact['source_function_execution_calls']==0
    assert artifact['full_task_satisfaction']==materialization['full_task_satisfaction']=='unknown' and artifact['all32_governing_RPI_exits']=='OPEN'
    stack=[artifact['tree']];nodecount=0;ratios=0
    while stack:
        node=stack.pop();nodecount+=1;assert nodecount<=10000
        if type(node) is dict:
            if node.get('kind')=='scalarLiteral':
                ratio=node['ratio'];assert set(ratio)=={'numerator','denominator'}
                assert re.fullmatch('-?(0|[1-9][0-9]*)',ratio['numerator']) and re.fullmatch('[1-9][0-9]*',ratio['denominator'])
                n,d=int(ratio['numerator']),int(ratio['denominator']);assert math.gcd(abs(n),d)==1;ratios+=1
            stack.extend(node.values())
        elif type(node) is list:stack.extend(node)
    assert artifact['L2_exact_ratio']=={'numerator':'5764607523034235','denominator':'576460752303423488'}
    names=[];node=artifact['tree']
    while node['kind']=='letBind':names.append(node['binder']);node=node['body']
    assert names==['margins','data','regularizer','factors','gradient'] and node['kind']=='prefixRecord'
    assert [r['name'] for r in node['fields']]==names and artifact['context_only_suffix']==['nonfinite_guard','return_tuple']
    after_v2,_=sealed(q,34,11290575);after_v1,_=sealed(v1,29,10856773);after_heads=guards(controls['original_checkout_guards'])
    assert before_v2==after_v2 and before_v1==after_v1 and before_heads==after_heads
    for row in list(HELD.values()):exact(row)
    own=pin(Path(__file__).resolve())[1]
    result={'schema':'ranker-objective-prefix-independent-actual-progress-readback@1','status':'passed_file_only_actual_host_controls_and_unqualified_prefix_join',
      'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producer':own,'findings':[],
      'host_controls':controlpin,'host_stdout':controls['stdout'],'host_JUnit':controls['junit'],'control_plan':controls['plan'],
      'candidate_source_review':controls['candidate_source_review'],'runner_source_review':controls['runner_source_review'],'candidate_pins':plan['candidate_pins'],
      'host_materialization':materialpin,'host_prefix':materialization['output'],'materializer_source':materialization['producer'],
      'host_control_groups_passed':20,'host_failures_errors_skips':0,'numeric_statements_emitted':5,'context_statements_checked':7,'source_bindings_checked':17,
      'host_shape_specification':artifact['shape'],'host_input_coordinates_supplied':0,'host_materialization_source_AST_parses_observed_by_producer':2,
      'JSON_tree_nodes_observed':nodecount,'canonical_rational_literal_nodes_observed':ratios,'L2_exact_binary_ratio':artifact['L2_exact_ratio'],
      'qualified_native_attempts':1,'qualified_native_queries':4,'retained_native_whole_bytes':202632,'retained_native_ordered_chunks':4,
      'prior_failed_native_attempts':1,'prior_failed_qualified_queries':0,'native_evidence':before_v2,'prior_failed_evidence':before_v1,
      'full_native_and_failed_scopes_unchanged_before_after':True,'original_checkout_guards_before':before_heads,'original_checkout_guards_after':after_heads,
      'all_original_HEAD_and_index_guards_unchanged':True,'observed_control_guard_count':2421,'protected_live_cohort_count':4,'protected_live_paths_overlap_strict_exactly':True,
      'whole_20119_dependency_closure_rehashed_by_this_audit':False,'candidate_or_helper_imports_compiler_or_renderer_calls':0,
      'pytest_native_model_metadata_codec_or_publication_jobs_by_this_audit':0,'new_kernel_queries_for_host_prefix':0,'typed_Lean_SourcePrefix_exists':False,
      'kernel_semantic_equivalence_proved':False,'full_source_runtime_equivalence':False,'full_objective_semantics_proved':False,'full_gradient_semantics_proved':False,
      'Python_Float_semantics_proved':False,'CPython_math_fsum_semantics_proved':False,'host_parser_correctness_theorem_proved':False,
      'optimizer_source_convergence_proved':False,'global_autoencoder_convergence_proved':False,'cache_admission':False,
      'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,
      'full_task_satisfaction':'unknown','all32_governing_RPI_exits':'OPEN','official_benchmark_score':None}
    out=ROOT/'review-receipt.json';raw=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
    with out.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'status':result['status'],'receipt':pin(out)[1],'producer':own,'distinct_file_bodies_read':len(HELD)}))
if __name__=='__main__':main()
