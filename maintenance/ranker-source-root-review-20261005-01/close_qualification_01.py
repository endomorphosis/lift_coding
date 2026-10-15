"""File-only closure of the quiet typed source-slice evidence. No prover or fit calls."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

WORKSPACE = Path('/home/barberb/lift_coding')
Q = WORKSPACE / 'qualification/codebase_ir/ranker-source-semantics-20261005-01'
PRIOR = Q.with_name('ranker-real-convergence-20261005-01')
HELD = {}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def read(path):
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode), 'regular input required')
        pieces = []
        while block := os.read(fd, 1024**2):
            pieces.append(block)
        raw = b''.join(pieces)
        fields = ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        sign = lambda value: tuple(getattr(value, key) for key in fields)
        need(sign(first) == sign(os.fstat(fd)) == sign(path.lstat()) and len(raw) == first.st_size, 'input changed')
    finally:
        os.close(fd)
    HELD[str(path)] = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    return raw


def pin(path):
    read(path)
    return HELD[str(Path(path).absolute())]


def document(binding):
    need(type(binding) is dict and set(binding) == {'path','bytes','sha256'}, 'exact descriptor required')
    raw = read(binding['path'])
    need(HELD[binding['path']] == binding, 'external binding differs')
    return json.loads(raw)


def load(path):
    return json.loads(read(path))


def save(path, value):
    with path.open('xb') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode()+b'\n')
        stream.flush(); os.fsync(stream.fileno())


def inventory():
    leaves = []
    for directory, directories, files in os.walk(Q, followlinks=False):
        need(all(not (Path(directory)/name).is_symlink() for name in directories), 'directory symlink refused')
        for name in files:
            if Path(directory)/name != Q/'file-only-seal-01.json':
                leaves.append(pin(Path(directory)/name))
    return sorted(leaves, key=lambda row: os.fsencode(row['path']))


def guards():
    baseline = load(WORKSPACE/'maintenance/ranker-curvature-private-git-preparation-20261005-01/original-checkout-state-01.json')
    result = {}
    for name, old in baseline['original_checkouts'].items():
        head = subprocess.check_output(['git','-C',old['path'],'rev-parse','HEAD'], env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')).decode().strip()
        index = pin(old['index_path'])
        need(head == old['head'] and index['bytes'] == old['index_bytes'] and index['sha256'] == old['index_sha256'], 'original checkout changed')
        result[name] = {'head':head,'index':index}
    return result


def main():
    need(__debug__, 'optimized Python refused')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    plan_raw = read(args.plan)
    need(hashlib.sha256(plan_raw).hexdigest() == args.plan_sha256, 'independent final plan pin differs')
    plan_pin = pin(args.plan); plan = json.loads(plan_raw)
    need(plan['schema'] == 'ranker-source-slices-closure-plan@1' and plan['scope_root'] == str(Q), 'closure scope')
    need(plan['source_and_artifacts_quiet'] is True, 'quiet closure required')
    need(not (Q/'qualified-review-01.json').exists() and not (Q/'file-only-seal-01.json').exists(), 'fresh closure required')
    first = inventory(); original_guards = guards()
    prior_seal = pin(PRIOR/'file-only-seal-01.json')
    need(prior_seal['sha256'] == '6ee7b5d675777e8cc9744c9072ee7f885cb8fc47a9204c1a40d9724632012648', 'prior seal pin')
    prior = load(prior_seal['path'])
    need(len(prior['files']) == 378, 'prior population')
    need(all(pin(row['path']) == row for row in prior['files']), 'prior leaf changed')
    request = load(Q/'preparation/request-v3.json')
    need(pin(Q/'preparation/request-v3.json')['sha256'] == '4858034f642fcedd31d7b243d65156eade84332e8401578df12e0c8f30c30861', 'owned request changed')
    need(len(request['strict_old_inputs']) == 1808 and len(request['protected_live_sources']) == 4, 'guard census')
    need(all(pin(row['path']) == row for row in request['strict_old_inputs']+request['protected_live_sources']), 'inherited/live source changed')
    reviews = []; semantic_reviews = []
    for item in plan['independent_reviews']:
        review = document(item['receipt'])
        need(review['status'] == item['expected_status'], 'independent review status')
        need(review[item['issue_field']] == [], 'unresolved independent issues')
        reviews.append(item['receipt'])
        if review.get('schema') == 'ranker-source-slices-independent-semantic-native-file-review@1':
            semantic_reviews.append(review)
    need(len(reviews) >= 3 and len(semantic_reviews) == 1, 'compiler, harness and exact semantic review required')
    semantic = semantic_reviews[0]
    need(semantic['documents']['request'] == pin(Q/'preparation/request-v3.json'), 'semantic request join')
    need(semantic['documents']['compiler_v2'] == pin(Q/'source-v2/typed_slice_compiler.py') and semantic['documents']['tests_v2'] == pin(Q/'source-v2/test_typed_slice_compiler.py'), 'semantic final compiler/test join')
    need(semantic['documents']['slices_v2'] == pin(Q/'evidence/compile-source-02/source-slices.json') and semantic['documents']['generated_v2'] == pin(Q/'evidence/compile-source-02/GeneratedNumericSlices.lean'), 'semantic emitted source join')
    build_receipt = document(plan['metadata_build_receipt'])
    need(build_receipt['status'] == 'passed', 'metadata builder gate')
    checks=[]; accepted=[]; failed=[]; queries=0
    for path in sorted((Q/'evidence').glob('*/check-result.json')):
        check=load(path); owned=load(path.parent/'closed.json'); outer=load(path.parent.with_name(path.parent.name+'-closed.json'))
        need(check['native_invocations'] == check['native_lean_invocations'] == 1, 'exact native invocation')
        need(owned['cleanup_errors'] == outer['cleanup_errors'] == [], 'native cleanup')
        need(check['native_bounds'] == {'timeout_seconds':20,'cpu_seconds':20,'max_input_bytes':262144,'max_output_bytes':65536,'max_workspace_bytes':16777216}, 'native bounds')
        row={'mode':path.parent.name,'qualification':pin(path),'source':check['source'],'environment_manifest':check['environment_manifest'],'status':check['status'],'owned_closed':pin(path.parent/'closed.json'),'outer_closed':pin(path.parent.with_name(path.parent.name+'-closed.json'))}
        need(pin(check['source']['path']) == check['source'], 'native source pin'); document(check['environment_manifest'])
        if check['status'] == 'passed':
            need(check['matches_expectation'] is True and check['expected_success'] is True and check['native_lean_returncode'] == 0, 'kernel result')
            need(check['axiom_report_error'] is None and check['post_call_binding_error'] is None and check['artifact_anomalies'] == [], 'native binding')
            need(check['reconstruction_validation']['status'] == 'passed' and check['workspace_cleaned'] is True, 'retention')
            need(all(item['complete'] is True for item in check['compiled_artifacts']), 'complete module bodies')
            for artifact in check['compiled_artifacts']+check['retained_chunk_artifacts']:
                need(pin(artifact['path']) == {key:artifact[key] for key in ('path','bytes','sha256')}, 'retained object/chunk changed')
            need(all(set(query['axioms']) <= {'propext','Classical.choice','Quot.sound'} for query in check['theorem_axiom_output']), 'forbidden axiom')
            need(len({query['theorem'] for query in check['theorem_axiom_output']}) == len(check['theorem_axiom_output']), 'duplicate query')
            queries += len(check['theorem_axiom_output']); accepted.append(row)
        else:
            need(path.parent.name == 'lean-typed-scalar-01' and check['status'] == 'inconclusive' and check['matches_expectation'] is False, 'retained failure scope')
            failed.append(row)
        checks.append(row)
    need(len(checks)==3 and len(accepted)==2 and len(failed)==1 and queries==21, 'qualified native census')
    need({row['mode']: row['qualification'] for row in checks} == {row['mode']: row['check'] for row in semantic['native_attempts']}, 'semantic actual native receipt joins')
    need({row['mode'] for row in accepted} == {'lean-typed-scalar-02','lean-generated-slices-01'}, 'qualified modules')
    metadata_path=Q/'evidence/metadata-source-slices-01/metadata-readback.json'
    metadata=load(metadata_path)
    need(metadata['status']=='passed' and metadata['metadata_row_count']==4440 and metadata['metadata_family_count']==32, 'metadata census')
    need(metadata['fresh_process_readback_verified'] is True and metadata['all_payload_rows_read_back_exactly'] is True, 'native fresh readback')
    old_rows=document(request['prior_metadata_inputs']); new_rows=load(Q/'evidence/metadata-source-slices-01/metadata-inputs.json')
    need(len(new_rows)==32 and set(new_rows)==set(old_rows) and sum(map(len,old_rows.values()))==4417 and sum(map(len,new_rows.values()))==4440, 'payload census')
    need(all(wire(new_rows[family][:len(values)])==wire(values) for family,values in old_rows.items()), 'prior canonical prefix drift')
    need(wire(new_rows['vectors'])==wire(old_rows['vectors']) and len(new_rows['vectors'])==375, 'vector drift')
    domains=new_rows['contracts'][len(old_rows['contracts']):]
    need(len(domains)==2 and all(row['record_kind']=='mathematical_projection_domain' and row['runtime_enforced'] is False and row['python_source_contract_proved'] is False for row in domains), 'projection domain scope')
    for family,values in new_rows.items():
        exported=[json.loads(line)['payload'] for line in (Q/'evidence/metadata-source-slices-01/metadata/exports'/f'{family}.jsonl').read_bytes().splitlines()]
        need(wire(exported)==wire(values), 'complete export drift '+family)
    phases=[]
    for path in sorted((Q/'evidence').glob('*/closed.json')):
        phase=load(path); outer=load(path.parent.with_name(path.parent.name+'-closed.json'))
        need(phase['cleanup_errors']==outer['cleanup_errors']==[], 'phase cleanup')
        need(phase['final_resource_state']['active_lease_count']==phase['final_resource_state']['waiting_request_count']==0, 'lease drain')
        need(all(phase[key]==0 for key in ('fit_calls','autoencoder_fit_calls','gradient_evaluations','optimizer_updates','native_preparation_calls')), 'unauthorized ranker execution')
        if path.parent.name!='lean-typed-scalar-01':
            need(phase['status']=='passed' and outer['returncode']==0 and outer['primary_error'] is None, 'owned phase failed')
        phases.append(pin(path))
    need(len(phases)==8, 'all owned phase census')
    for mode in ('pure-tests-source-01','pure-tests-source-02'):
        phase=load(Q/'evidence'/mode/'closed.json')
        need(phase['selected_test_count']==137 and phase['pytest_returncode']==0 and phase['native_runner_calls_refused']==phase['direct_process_calls_refused']==0, 'pure controls')
    need(first==inventory() and guards()==original_guards, 'quiet inventory/live guards changed')
    need(all(pin(path)==row for path,row in list(HELD.items())), 'held input changed before closure')
    result={'schema':'ranker-source-slices-closed-qualification@1','status':'passed','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producer':pin(Path(__file__).resolve()),'closure_plan':plan_pin,'prior_convergence_seal':prior_seal,'independent_reviews':reviews,'metadata_build_receipt':plan['metadata_build_receipt'],'native_checks':checks,'native_lean_calls':3,'qualified_positive_native_lean_checks':2,'inconclusive_native_lean_checks_retained':1,'qualified_theorem_queries':21,'owned_phase_count':8,'phases':phases,'pure_test_cases_per_compiler_version':137,'all_owned_leases_drained':True,'new_autoencoder_fits':0,'new_public_fits':0,'new_gradient_evaluations':0,'new_optimizer_updates':0,'new_ranker_training_trace_replays':0,'new_feature_preparations':0,'typed_scalar_compiler_semantic_preservation_proved':True,'emitted_dot_exact_real_projection_proved':True,'emitted_update_exact_real_projection_proved':True,'supplied_mathematical_gradient_update_joins_original_exact_real_step':True,'prior_original_exact_real_model_weights_and_objective_convergence_preserved':True,'native_metadata_readback':pin(metadata_path),'metadata_family_count':32,'metadata_payloads':4440,'prior4417_payloads_preserved_exactly_as_prefixes':True,'additive_metadata_payloads':23,'new_mathematical_projection_domain_contract_rows':2,'projection_domains_runtime_enforced':False,'vectors_payloads_unchanged':True,'strict_advisory_cache_entries_added':0,'native_proof_and_metadata_limits_unchanged':True,'original_checkout_guards':original_guards,'all_prior378_regular_leaves_unchanged':True,'open_obligations':pin(Q/'source-model-obligations-01.json'),'host_parser_correctness_theorem_proved':False,'python_ranker_source_equivalence_proved':False,'objective_to_IR_translation_proved':False,'feature_preparation_to_IR_translation_proved':False,'full_training_loop_to_IR_translation_proved':False,'CPython_math_fsum_semantics_proved':False,'binary64_error_bound_proved':False,'native_Float_optimizer_convergence_proved':False,'global_autoencoder_convergence_proved':False,'whole_codebase_IR_semantic_preservation_proved':False,'full_task_satisfaction':'unknown','all32_governing_RPI_exits':'OPEN','official_benchmark_score':None,'atomic_whole_source_snapshot_claimed':False,'historical_execution_origin_proved':False,'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False}
    review_path=Q/'qualified-review-01.json';save(review_path,result)
    leaves=inventory()
    seal={'schema':'ranker-source-slices-file-only-seal@1','status':'sealed_quiet_regular_file_scope','scope_root':str(Q),'review':pin(review_path),'files':leaves,'regular_file_count':len(leaves),'regular_file_bytes':sum(row['bytes'] for row in leaves),'file_inventory_sha256':hashlib.sha256(wire(leaves)).hexdigest(),'fixture_symlinks':[],'excluded_dependency_roots':[],'raw_external_dependency_bodies_in_scope':False,'stat_atime_in_identity':False,'model_training_calls':0,'prover_calls':0,'remote_mutations':0,'proof_authority':False}
    need(leaves==inventory(), 'final quiet inventory changed')
    save(Q/'file-only-seal-01.json',seal)
    print(json.dumps({'review':pin(review_path),'seal':pin(Q/'file-only-seal-01.json'),'regular_files':len(leaves),'regular_bytes':seal['regular_file_bytes']}))


if __name__=='__main__':main()
