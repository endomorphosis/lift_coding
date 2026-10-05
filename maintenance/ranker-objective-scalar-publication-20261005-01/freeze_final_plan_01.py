"""Assemble the final objective-scalar plan from externally pinned quiet evidence.

File-only: no imports of project/helpers, codec, classifier, native, metadata,
model, Git or network jobs. This is not the selection freezer or package builder.
All new outputs are exclusive creates; a failed preparation remains reviewable.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

W=Path('/home/barberb/lift_coding')
S=Path(__file__).resolve().parent
R=W/'maintenance/ranker-objective-scalar-publication-root-20261005-01'
Q=W/'qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01'
P6=W/'qualification/codebase_ir/ranker-objective-ir-source-plan-20261005-01'
PARENT='fae2e38dc882929edb2bcd2226560f0da3dfcd9e'
HELD={}
MAX=32*1024**2
PROFILE={'raw_population_max':268435456,'raw_member_sum_per_shard_max':14680064,
    'per_file_max':14680064,'complete_decoded_tar_max':16777216,'compressed_shard_max':16777216,
    'aggregate_decoded_work_max':1073741824,'wall_seconds':180,'members_max':10000,'depth_max':6,
    'shards_max':64,'zstd_args':['-T1','-3'],'duplicate_verification_decoder_invocations':0,
    'member_readback_profile':'same_first_decoded_tar_and_member_streams@1','native_qualification_limits_changed':False}
NATIVE_BOUNDS={'timeout_seconds':20,'cpu_seconds':20,'max_input_bytes':262144,'max_output_bytes':65536,'max_workspace_bytes':16777216}
SOURCE_PLAN_PINS={'source-plan.json':'f0e712a1b78ba1a728f5f4a41a8d8f66540017ae86418e23f4bd3c40f6cce690',
    'source-bindings.json':'5f76eed1e9b025c8e7bb61d23e368a4740b01f329c40472f0c77f2f909bd5c16',
    'ir-interface.json':'53a6ba907b4ac64d79f88a97fb9b987a54d0b2efeb930cef798c249d483a6cd0',
    'extract_bindings_01.py':'e9888ea64ad2c9523207ca3488b5869d0ac2dfecca07d73d17825c78f90a40e8'}
NATIVE={'lean-objective-scalar-01':(5,'57ac502ebc37df08ae73b7fec69280b2dcb1a2453895ab573869d826d613bd5e'),
    'lean-objective-generated-01':(9,'4bcc8424739067b6e31382f594bd0c17e7e3e800d117bd08b2e38de302177041')}
PEERS={
    'candidate_source':('ranker-objective-scalar-independent-source-review@1','passed_source_only','outstanding_source_issues'),
    'prepared_native_inputs':('ranker-objective-scalar-prepared-input-source-review@1','passed_file_only','outstanding_source_issues'),
    'semantic_native':('ranker-objective-scalar-independent-semantic-native-review@1','passed_file_only_actual_receipt_review','outstanding_review_issues'),
    'metadata_source_initial':('ranker-objective-scalar-metadata-independent-source-review@1','passed_source_only','outstanding_source_issues'),
    'metadata_builder_patch':('ranker-objective-scalar-metadata-builder-patch-independent-source-review@1','passed_source_only','outstanding_source_issues'),
    'publication_source':('ranker-objective-scalar-publication-independent-source-review@1','passed_source_only','outstanding_source_issues'),
}


def need(value,message):
    if value is not True:raise ValueError(message)


def wire(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


def read(path):
    path=Path(path).absolute()
    need(path.resolve(strict=True)==path and not path.is_symlink(),'canonical input')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        first=os.fstat(fd);need(stat.S_ISREG(first.st_mode) and first.st_size<=MAX,'bounded regular input')
        blocks=[];total=0
        while block:=os.read(fd,1024**2):
            total+=len(block);need(total<=MAX,'input exceeded bound');blocks.append(block)
        raw=b''.join(blocks)
        keys=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        sign=lambda info:tuple(getattr(info,key) for key in keys)
        need(sign(first)==sign(os.fstat(fd))==sign(path.lstat()) and len(raw)==first.st_size,'input changed')
    finally:os.close(fd)
    binding={'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    if str(path) in HELD:need(HELD[str(path)]==binding,'previous input changed')
    HELD[str(path)]=binding
    return raw,binding


def pin(path):return read(path)[1]


def descriptor(row):
    need(type(row) is dict and set(row)=={'path','bytes','sha256'} and type(row['path']) is str and
        type(row['bytes']) is int and 0<=row['bytes']<=MAX and type(row['sha256']) is str and
        re.fullmatch('[0-9a-f]{64}',row['sha256']) is not None,'exact bounded input descriptor')
    return Path(row['path'])


def document(row):
    raw,binding=read(descriptor(row));need(binding==row,'same-buffer externally pinned input')
    return json.loads(raw)


def save(path,raw):
    with path.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return pin(path)


def save_json(path,value):return save(path,wire(value)+b'\n')


def count(body,key,expected):
    need(type(body.get(key)) is int and body[key]==expected,'exact integer '+key)


def census(root):
    leaves=[]
    def visit(path):
        info=path.lstat();need(path.resolve(strict=True)==path and not stat.S_ISLNK(info.st_mode),'no aliases in owned census')
        if stat.S_ISDIR(info.st_mode):
            for child in sorted(path.iterdir(),key=lambda item:os.fsencode(item.name)):visit(child)
        else:
            need(stat.S_ISREG(info.st_mode) and info.st_size<=PROFILE['per_file_max'],'bounded owned evidence leaf')
            leaves.append(pin(path))
    visit(root)
    return sorted(leaves,key=lambda row:os.fsencode(row['path']))


def main():
    need(__debug__,'optimized Python refused')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True,type=Path)
    parser.add_argument('--expected-request-sha256',required=True)
    a=parser.parse_args()
    need(a.request==R/'freeze-final-plan-request-01.json' and re.fullmatch('[0-9a-f]{64}',a.expected_request_sha256) is not None,
        'fixed externally pinned final request')
    raw,request_pin=read(a.request);need(request_pin['sha256']==a.expected_request_sha256,'independent final request pin')
    request=json.loads(raw)
    need(type(request) is dict and set(request)=={'schema','file_seal','qualified_review','sealed_regular_files',
        'sealed_regular_bytes','peer_reviews','closure_producer','prior_publication_closure','extra_provenance'} and
        request['schema']=='ranker-objective-scalar-final-plan-request@1','closed final request schema')
    need(type(request['sealed_regular_files']) is int and 0<request['sealed_regular_files']<=10000 and
        type(request['sealed_regular_bytes']) is int and 0<request['sealed_regular_bytes']<=PROFILE['raw_population_max'],
        'external bounded sealed count and bytes')
    required_sources={'SOURCE_API.md','build_package.py','review_package.py','freeze_inputs.py','freeze_final_plan_01.py'}
    need({path.name for path in S.iterdir()}==required_sources and all((S/name).is_file() for name in required_sources),
        'fresh preparation namespace containing only reviewed sources')
    source_pins=[pin(S/name) for name in sorted(required_sources)]
    need(descriptor(request['file_seal'])==Q/'file-only-seal-01.json' and descriptor(request['qualified_review'])==Q/'qualified-review-01.json',
        'fixed final candidate seal and review')
    seal,qualified=document(request['file_seal']),document(request['qualified_review'])
    need(seal['schema']=='ranker-objective-scalar-file-only-seal@1' and seal['scope_root']==str(Q) and
        seal['review']==request['qualified_review'] and seal.get('fixture_symlinks',[])==[] and
        seal.get('excluded_dependency_roots',[])==[] and seal.get('excluded_dependency_subtrees',[])==[],
        'complete final no-alias seal without denominator exclusions')
    count(seal,'regular_file_count',request['sealed_regular_files']);count(seal,'regular_file_bytes',request['sealed_regular_bytes'])
    need(type(seal['files']) is list and len(seal['files'])==request['sealed_regular_files'] and
        len({row['path'] for row in seal['files']})==len(seal['files']) and
        sum(row['bytes'] for row in seal['files'])==request['sealed_regular_bytes'] and
        hashlib.sha256(wire(seal['files'])).hexdigest()==seal['file_inventory_sha256'],'exact complete seal population')
    before=census(Q)
    need(before==sorted([*seal['files'],request['file_seal']],key=lambda row:os.fsencode(row['path'])),
        'entire owned root equals final seal plus seal self-file')
    need(qualified['schema']=='ranker-objective-scalar-closed-qualification@1' and qualified['status']=='passed' and
        qualified['producer']==request['closure_producer'],'qualified closure producer join')
    for key,value in (('native_lean_calls',2),('qualified_positive_native_lean_checks',2),('inconclusive_native_lean_checks_retained',0),
        ('qualified_theorem_queries',14),('pure_test_cases',98),('metadata_payloads',4458),('metadata_family_count',32),
        ('additive_metadata_payloads',18),('unchanged_vector_rows',375),('unchanged_contract_rows',2),
        ('new_mathematical_projection_domain_contract_rows',0),('strict_advisory_cache_entries_added',0)):
        count(qualified,key,value)
    need(all(qualified[key] is True for key in ('accepted_scalar_compiler_partial_semantic_preservation_proved',
        'emitted_stable_loss_exact_real_projection_proved','emitted_stable_factor_exact_real_projection_proved',
        'emitted_stable_loss_equals_realPairLoss_proved','emitted_stable_factor_equals_realLogisticP_proved',
        'prior4440_payloads_preserved_exactly_as_prefixes','vectors_payloads_unchanged','contracts_payloads_unchanged',
        'all_owned_leases_drained','native_proof_and_metadata_limits_unchanged')),'closed narrow scalar and metadata facts')
    need(all(qualified[key] is False for key in ('proof_authority','execution_authority','completion_authority','planner_activation',
        'host_parser_correctness_theorem_proved','python_ranker_source_equivalence_proved','objective_to_IR_translation_proved',
        'computed_gradient_source_equivalence_proved','feature_preparation_to_IR_translation_proved','full_training_loop_to_IR_translation_proved',
        'CPython_math_fsum_semantics_proved','binary64_error_bound_proved','native_Float_optimizer_convergence_proved',
        'global_autoencoder_convergence_proved','whole_codebase_IR_semantic_preservation_proved',
        'atomic_whole_source_snapshot_claimed','historical_execution_origin_proved')),'source/numeric/full-task/authority frontiers')
    need(qualified['full_task_satisfaction']=='unknown' and qualified['all32_governing_RPI_exits']=='OPEN' and
        qualified['official_benchmark_score'] is None,'task frontier')
    for key in ('new_autoencoder_fits','new_public_fits','new_gradient_evaluations','new_optimizer_updates',
        'new_ranker_training_trace_replays','new_feature_preparations'):count(qualified,key,0)
    docs={'file_seal':request['file_seal'],'qualified_review':request['qualified_review'],
        'metadata_readback':qualified['native_metadata_readback'],'open_obligations':qualified['open_obligations'],
        'source_IR':pin(Q/'evidence/compile-source-objective-01/objective-slices.json')}
    need({path.parent.name for path in (Q/'evidence').glob('*/check-result.json')}==set(NATIVE),'all actual native attempts retained')
    native=[]
    for mode,(queries,sha) in NATIVE.items():
        binding=pin(Q/'evidence'/mode/'check-result.json');need(binding['sha256']==sha,'actual accepted check pin')
        check=document(binding);role=mode.replace('-','_');native.append(role);docs[role]=binding
        need(check['status']=='passed' and type(check['native_invocations']) is int and check['native_invocations']==1 and
            wire(check['native_bounds'])==wire(NATIVE_BOUNDS) and len(check['theorem_axiom_output'])==queries,
            'actual unchanged-cap native check/query census')
    peers=request['peer_reviews']
    need(type(peers) is list and 6<=len(peers)<=16 and len({peer['role'] for peer in peers})==len(peers),
        'complete unique bounded peer-review roles')
    need(set(PEERS)<={peer['role'] for peer in peers} and
        len({peer['receipt']['path'] for peer in peers})==len(peers),
        'all required distinct source/prepared/native/metadata/patch/publication peer reviews')
    captures=[('final_plan_request',request_pin),('qualification_closure_producer',request['closure_producer'])]
    for peer in peers:
        need(type(peer) is dict and set(peer)=={'role','receipt','producer','expected_status','issue_field'} and
            re.fullmatch('[a-z][a-z0-9_]{0,63}',peer['role']) is not None and type(peer['expected_status']) is str and
            peer['expected_status'].startswith('passed') and type(peer['issue_field']) is str,'closed peer review binding')
        body=document(peer['receipt']);need(body['status']==peer['expected_status'] and body[peer['issue_field']]==[],
            'independent peer review passed without issues')
        if peer['role'] in PEERS:
            need((body['schema'],peer['expected_status'],peer['issue_field'])==PEERS[peer['role']],
                'fixed required peer role, schema, status and issue-field mapping')
        need(any(body.get(key)==peer['producer'] for key in ('review_source','reviewer','producer')),'peer receipt binds reviewer producer')
        need(all(body[key] is False for key in ('proof_authority','execution_authority','completion_authority','planner_activation')),
            'peer review cannot grant authority')
        docs['peer_'+peer['role']]=peer['receipt']
        captures.extend([(peer['role']+'_receipt',peer['receipt']),(peer['role']+'_producer',peer['producer'])])
    peer_bindings={peer['receipt']['path']:peer['receipt'] for peer in peers}
    need(all(row==peer_bindings.get(row['path']) for row in qualified['independent_reviews']),
        'every qualified independent review is captured with its exact descriptor')
    prior=document(request['prior_publication_closure'])
    need(prior['status']=='PUBLISHED_AND_VERIFIED' and prior['huggingface']['commit']==PARENT and
        prior['github']['commit']=='a6712457a8616c2d22100b3b0cd950986b891e64' and
        prior['all_nine_fresh_gitlinks_preserved'] is True and
        all(prior[key] is False for key in ('proof_authority','execution_authority','completion_authority','planner_activation')),
        'prior completed Git/HF combined publication closure')
    captures.extend([('prior_combined_publication_closure',request['prior_publication_closure']),('prior_combined_closure_producer',prior['producer'])])
    source_plan=census(P6)
    need({Path(row['path']).name for row in source_plan}==set(SOURCE_PLAN_PINS) and
        all(row['sha256']==SOURCE_PLAN_PINS[Path(row['path']).name] for row in source_plan),'whole immutable source-plan population')
    captures.extend([('retained_source_plan',row) for row in source_plan])
    for name in ('prepare_hf_plan_01.py','prepare_invocation_01.py','scan_final_upload_01.py','review_hf_readback_01.py'):
        captures.append(('publication_root_source',pin(R/name)))
    extras=request['extra_provenance']
    need(type(extras) is list and len(extras)<=24,'bounded explicit extra review/history provenance')
    captures.extend([('extra_provenance',row) for row in extras])
    unique={}
    for role,row in captures:
        path=descriptor(row)
        need(path.is_relative_to(W) and path.suffix in ('.json','.py','.md','.lean') and pin(path)==row,
            'exact bounded public source/receipt provenance')
        if row['path'] in unique:need(unique[row['path']][1]==row,'capture descriptor conflict')
        else:unique[row['path']]=(role,row)
    need(len(unique)+len(source_pins)+3<=100,'final explicit-addition cap before any output')
    bodies={name:document(row) for name,row in docs.items()}
    facts=[{'document':name,'pointer':'/'+key.replace('~','~0').replace('/','~1'),'equals':value}
        for name,body in bodies.items() for key,value in body.items()]
    need(0<len(facts)<=5000,'bounded exact observed-fact policy')
    need(census(Q)==before and census(P6)==source_plan and all(pin(path)==row for path,row in list(HELD.items())),
        'all source/census/document pins unchanged before final-plan preparation')
    directory=S/'captured-provenance';directory.mkdir(mode=0o700)
    mapping=[]
    for index,(path,(role,row)) in enumerate(sorted(unique.items())):
        raw,binding=read(path);need(binding==row,'capture source drift')
        target=directory/('%03d-%s-%s'%(index,role,Path(path).name))
        captured=save(target,raw);need(captured['sha256']==row['sha256'] and captured['bytes']==row['bytes'],'byte-exact provenance copy')
        mapping.append({'role':role,'original':row,'captured':captured,'byte_exact_clone':True})
    provenance=save_json(directory/'provenance-map.json',{'schema':'ranker-objective-scalar-publication-provenance-map@1',
        'request':request_pin,'copies':mapping,'copies_are_source_or_receipt_history_not_new_qualification':True})
    policy=save_json(S/'required-facts.json',facts)
    additions=sorted([*source_pins,provenance,policy,*[row['captured'] for row in mapping],request['file_seal']],key=lambda row:row['path'])
    need(len(additions)<=100 and len({row['path'] for row in additions})==len(additions),'exact bounded final additions')
    need(census(Q)==before and census(P6)==source_plan and all(pin(path)==row for path,row in list(HELD.items())),
        'all sources, captures and sealed census unchanged before writing final plan')
    plan={'schema':'ranker-objective-scalar-publication-plan@1','status':'frozen_final_plan','scope_root':str(Q),'source_plan_root':str(P6),
        'source_and_artifacts_quiet':True,'source_plan_quiet':True,'seal_schema':seal['schema'],'review_schema':qualified['schema'],
        'documents':docs,'semantic_policy':policy,'native_checks':native,'explicit_additions':additions,'excluded_dependency_subtrees':[],
        'publication_profile':PROFILE,'old_HF_bundle_reuploaded':False,'prior_HF_commit':PARENT,'provenance_map':provenance,
        'final_plan_request':request_pin,'final_plan_producer':pin(Path(__file__).resolve()),
        'external_dependencies':{'manifest_scope':'all two complete actual native environment profiles','raw_bodies_published':False,
            'prior_source_slice_namespace':'releases/20261004-terminal-codebase-ir-evidence-v1/successor-ranker-source-slices-v1',
            'source_plan_role':'retained source planning history; only actual native evidence grants narrow mathematical qualification'}}
    result=save_json(S/'plan.json',plan)
    print(json.dumps({'plan':result,'facts':len(facts),'explicit_additions':len(additions),'provenance_copies':len(mapping),
        'native_qualification_jobs':0,'codec_calls':0,'metadata_jobs':0,'remote_mutations':0}))


if __name__=='__main__':main()
