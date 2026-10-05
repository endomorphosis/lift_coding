"""Freeze observed source-slice facts and the complete sealed publication scope."""
import hashlib
import json
from pathlib import Path

W=Path('/home/barberb/lift_coding')
S=Path(__file__).resolve().parent
Q=W/'qualification/codebase_ir/ranker-source-semantics-20261005-01'
P5=W/'qualification/codebase_ir/ranker-source-semantics-source-plan-20261005-01'
REVIEW=W/'maintenance/ranker-source-slices-publication-source-review-20261005-01/review-receipt.json'


def pin(path):
    assert path.resolve(strict=True)==path and not path.is_symlink()
    raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def save(path,value):
    with path.open('x') as f:json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')


def main():
    if not __debug__:raise RuntimeError("optimized Python refused")
    seal=pin(Q/'file-only-seal-01.json');qualified=pin(Q/'qualified-review-01.json')
    assert seal['sha256']=='21a459ac9bfcf399132943708e32445c93cb66fa0fab8fb2878beeb01dcf8b65'
    assert qualified['sha256']=='39c403afd19b5972a28281813c23fdd13eddea1c32fa63747b4dd3258b07e550'
    review_raw=REVIEW.read_bytes()
    assert hashlib.sha256(review_raw).hexdigest()=='fbfef37641d60af2e94439b53faa71a5dcfbcbfb35ea632ca9882f84561f4257'
    source_review=json.loads(review_raw)
    assert source_review['status']=='passed_source_only' and source_review.get('issues', [])==[]
    # Preserve the independently generated source review under the selected owned root.
    raw=REVIEW.read_bytes()
    with (S/'source-review-01.json').open('xb') as f:f.write(raw)
    docs={'file_seal':seal,'qualified_review':qualified,
          'metadata_readback':pin(Q/'evidence/metadata-source-slices-01/metadata-readback.json'),
          'source_IR':pin(Q/'evidence/compile-source-02/source-slices.json'),
          'open_obligations':pin(Q/'source-model-obligations-01.json'),
          'semantic_review':pin(W/'maintenance/ranker-source-semantic-native-review-20261005-01/review-receipt.json')}
    native=[]
    for p in sorted((Q/'evidence').glob('*/check-result.json')):
        name=p.parent.name.replace('-','_');native.append(name);docs[name]=pin(p)
    facts=[]
    def add(role,pointer,equals):facts.append({'document':role,'pointer':pointer,'equals':equals})
    for name,binding in docs.items():
        body=json.loads(Path(binding['path']).read_bytes())
        assert pin(Path(binding['path']))==binding
        if name=='qualified_review':
            for key,value in body.items():add(name,'/'+key.replace('~','~0').replace('/','~1'),value)
        elif name in native:
            for key in ('status','native_invocations','native_lean_invocations','native_lean_returncode','expected_success','matches_expectation','native_bounds','proof_authority','execution_authority','completion_authority','planner_activation','full_task_satisfaction','official_benchmark_score','python_ranker_source_equivalence_proved','binary64_error_bound_proved','optimizer_convergence_proved','theorem_axiom_output','source','augmented_source','environment_manifest','compiled_artifacts','retained_chunk_artifacts','reconstruction_validation'):
                add(name,'/'+key,body[key])
        elif name=='metadata_readback':
            for key in ('status','metadata_family_count','metadata_row_count','additive_payload_rows','fresh_process_readback_verified','all_payload_rows_read_back_exactly','prior4417_payload_rows_preserved_exactly_as_prefixes','prior_contract_payloads_preserved_and_vectors_unchanged','new_mathematical_projection_domain_contract_rows','strict_advisory_cache_entries_added_in_this_phase','proof_authority','execution_authority','completion_authority','planner_activation','full_task_satisfaction','source_runtime_equivalence_proved','global_autoencoder_convergence_proved'):
                add(name,'/'+key,body[key])
        elif name=='semantic_review':
            add(name,'/status',body['status']);add(name,'/outstanding_issues',[]);add(name,'/census',body['census'])
        elif name=='source_IR':
            for key in ('schema','status','source','dimension','dot','update','scope'):
                if key in body:add(name,'/'+key,body[key])
        elif name=='open_obligations':
            add(name,'/all32_governing_RPI_exits','OPEN');add(name,'/obligations',body['obligations'])
    save(S/'required-facts.json',facts)
    additions=[pin(p) for p in sorted(S.rglob('*')) if p.is_file() and p.name!='plan.json']+[seal]
    assert len(additions)<=100
    profile={'raw_population_max':268435456,'raw_member_sum_per_shard_max':14680064,'per_file_max':14680064,'complete_decoded_tar_max':16777216,'compressed_shard_max':16777216,'aggregate_decoded_work_max':1073741824,'wall_seconds':180,'members_max':10000,'depth_max':6,'shards_max':64,'zstd_args':['-T1','-3'],'duplicate_verification_decoder_invocations':0,'member_readback_profile':'same_first_decoded_tar_and_member_streams@1','native_qualification_limits_changed':False}
    plan={'schema':'ranker-source-slices-publication-plan@1','status':'frozen_final_plan','scope_root':str(Q),'source_plan_root':str(P5),'source_and_artifacts_quiet':True,'source_plan_quiet':True,'seal_schema':'ranker-source-slices-file-only-seal@1','review_schema':'ranker-source-slices-closed-qualification@1','documents':docs,'semantic_policy':pin(S/'required-facts.json'),'native_checks':native,'explicit_additions':additions,'excluded_dependency_subtrees':[],'publication_profile':profile,'old_HF_bundle_reuploaded':False,'prior_HF_commit':'d6b6e333f3b1bcfe9028a8ca5ac3be6b12256e8a','external_dependencies':{'manifest_scope':'all three complete actual native environment manifests','raw_bodies_published':False,'prior_convergence_namespace':'releases/20261004-terminal-codebase-ir-evidence-v1/successor-ranker-convergence-v1','next_objective_plan_role':'captured unimplemented, unqualified proposal only'}}
    save(S/'plan.json',plan)
    print(json.dumps({'plan':pin(S/'plan.json'),'facts':len(facts),'explicit_additions':len(additions)}))


if __name__=='__main__':main()
