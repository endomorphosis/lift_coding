"""Prepare a byte-pinned objective-scalar successor upload. File-only.

Final seal/review and population values come from external reviewed arguments.
This producer performs no classifier, codec, native, model or remote operation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

W=Path('/home/barberb/lift_coding')
R=Path(__file__).resolve().parent
S=W/'maintenance/ranker-objective-scalar-publication-20261005-01'
P=W/'maintenance/ranker-objective-scalar-publication-package-20261005-01'
Q=W/'qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01'
PARENT='fae2e38dc882929edb2bcd2226560f0da3dfcd9e'
PREFIX='releases/20261004-terminal-codebase-ir-evidence-v1'
NS=PREFIX+'/successor-ranker-objective-scalar-v1'
HELD={}


def need(value,message):
    if value is not True:raise ValueError(message)


def read(path):
    path=Path(path).absolute()
    need(path.resolve(strict=True)==path and not path.is_symlink(),'canonical input')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size<=32*1024**2,'bounded regular input')
        blocks=[];total=0
        while block:=os.read(fd,1024**2):
            total+=len(block);need(total<=32*1024**2,'input exceeded bound');blocks.append(block)
        raw=b''.join(blocks)
        keys=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        signature=lambda info:tuple(getattr(info,key) for key in keys)
        need(signature(before)==signature(os.fstat(fd))==signature(path.lstat()) and len(raw)==before.st_size,'input changed')
    finally:os.close(fd)
    return raw


def read_bound(path,expected=None):
    raw=read(path)
    binding={'path':str(Path(path).absolute()),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    if expected is not None:need(binding==expected,'exact same-buffer descriptor')
    if binding['path'] in HELD:need(HELD[binding['path']]==binding,'previous input changed')
    HELD[binding['path']]=binding
    return raw,binding


def pin(path):return read_bound(path)[1]


def load_bound(path,sha=None):
    raw,binding=read_bound(path)
    if sha is not None:need(binding['sha256']==sha,'independent document pin')
    return json.loads(raw),binding


def count(document,key,expected):
    need(type(document.get(key)) is int and document[key]==expected,'exact integer '+key)


def save(path,raw):
    with path.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return pin(path)


def encoded(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def main():
    need(__debug__,'optimized Python refused')
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','manifest','package-review','qualification','seal','closed-inputs'):
        parser.add_argument('--expected-'+name+'-sha256',required=True)
    for name in ('sealed-files','sealed-bytes','selected-files','selected-bytes'):
        parser.add_argument('--expected-'+name,required=True,type=int)
    a=parser.parse_args()
    need(all(re.fullmatch('[0-9a-f]{64}',getattr(a,'expected_'+name.replace('-','_')+'_sha256')) is not None
        for name in ('baseline','manifest','package-review','qualification','seal','closed-inputs')),'independent lowercase SHA256 pins')
    need(0<a.expected_sealed_files<=a.expected_selected_files<=10000 and
        0<a.expected_sealed_bytes<=a.expected_selected_bytes<=256*1024**2,'bounded external population values')
    own=pin(Path(__file__).resolve())
    baseline,baseline_pin=load_bound(R/'HF-parent-preflight-01.json',a.expected_baseline_sha256)
    need(baseline['status']=='passed' and baseline['parent_commit']==PARENT and baseline['namespace']==NS and
        baseline['namespace_unoccupied'] is True,'exact unoccupied parent baseline')
    count(baseline,'complete_regular_file_count',331);count(baseline,'prior_immutable_files',329)
    need(type(baseline['files']) is dict and len(baseline['files'])==331,'whole prior tree census')
    need(all(pin(row['path'])==row for row in baseline['mutable_pointer_source_pins']),'prior mutable body drift')
    frozen,frozen_pin=load_bound(S/'closed-inputs.json',a.expected_closed_inputs_sha256)
    need(frozen['schema']=='ranker-objective-scalar-publication-closed-inputs@1','exact input closure')
    final_plan,final_plan_pin=load_bound(S/'plan.json');selection,selection_pin=load_bound(S/'final-selection.json')
    need(frozen['plan']==final_plan_pin and frozen['final_selection']==selection_pin and
        final_plan['schema']=='ranker-objective-scalar-publication-plan@1' and final_plan['status']=='frozen_final_plan' and
        final_plan['source_and_artifacts_quiet'] is True and final_plan['source_plan_quiet'] is True and
        selection['schema']=='ranker-objective-scalar-publication-final-selection@1','closure joins quiet plan and selection')
    need(len(selection['files'])==a.expected_selected_files and sum(row['bytes'] for row in selection['files'])==a.expected_selected_bytes,
        'external complete selection count and bytes')
    manifest,manifest_pin=load_bound(P/'package/manifest.json',a.expected_manifest_sha256)
    package_closed,package_closed_pin=load_bound(P/'closed.json')
    review,review_pin=load_bound(S/'package-review-01.json',a.expected_package_review_sha256)
    need(manifest['schema']=='ranker-objective-scalar-frozen-evidence-package@1' and
        manifest['closed_inputs']==frozen_pin and manifest['plan']==final_plan_pin and manifest['final_selection']==selection_pin,
        'manifest joins exact frozen input population')
    need(package_closed['status']=='passed_local_frozen_package' and package_closed['manifest']==manifest_pin and
        package_closed['candidate_hits']==0 and package_closed['source_drift_count']==0 and package_closed['cleanup_errors']==[],
        'successful package closure')
    need(review['schema']=='ranker-objective-scalar-full-decoded-member-file-only-review@1' and review['status']=='passed' and
        review['package_closure']==package_closed_pin and review['manifest']==manifest_pin and review['closed_inputs']==frozen_pin and
        review['reviewer']==pin(S/'review_package.py') and review['publication_profile']==frozen['publication_profile'],
        'decoded review joins exact package, frozen selection and executed reviewer')
    for document,key,value in ((manifest,'file_count',a.expected_selected_files),(manifest,'original_file_bytes',a.expected_selected_bytes),
        (manifest,'sealed_regular_file_count',a.expected_sealed_files),(manifest,'sealed_regular_file_bytes',a.expected_sealed_bytes),
        (review,'selected_files_verified_before_after',a.expected_selected_files),(review,'decoded_members_verified',a.expected_selected_files),
        (review,'sealed_file_count_rehashed',a.expected_sealed_files),(review,'sealed_file_bytes_rehashed',a.expected_sealed_bytes),
        (manifest,'native_attempt_count_fact_gated',2),(review,'native_attempt_denominator_verified',2)):
        count(document,key,value)
    need(manifest['all_sealed_regular_files_retained'] is True and manifest['all_failed_attempts_retained'] is True and
        manifest['scan_hits']==[] and manifest['raw_external_dependency_bodies_published'] is False and
        manifest['full_objects_and_chunks_retained'] is True and manifest['old_HF_bundle_reuploaded'] is False,
        'complete scanned evidence and no dependency or old archive bodies')
    qual,qual_pin=load_bound(Q/'qualified-review-01.json',a.expected_qualification_sha256)
    seal,seal_pin=load_bound(Q/'file-only-seal-01.json',a.expected_seal_sha256)
    need(qual['schema']=='ranker-objective-scalar-closed-qualification@1' and qual['status']=='passed' and
        seal['schema']=='ranker-objective-scalar-file-only-seal@1' and seal['scope_root']==str(Q) and seal['review']==qual_pin and
        final_plan['documents']['file_seal']==seal_pin and final_plan['documents']['qualified_review']==qual_pin,
        'externally pinned final seal and qualified review joins')
    count(seal,'regular_file_count',a.expected_sealed_files);count(seal,'regular_file_bytes',a.expected_sealed_bytes)
    need(len(seal['files'])==a.expected_sealed_files and sum(row['bytes'] for row in seal['files'])==a.expected_sealed_bytes,
        'whole externally pinned owned census')
    for key,value in (('native_lean_calls',2),('qualified_positive_native_lean_checks',2),('inconclusive_native_lean_checks_retained',0),
        ('qualified_theorem_queries',14),('pure_test_cases',98),('metadata_payloads',4458),('metadata_family_count',32),
        ('additive_metadata_payloads',18),('unchanged_vector_rows',375),('unchanged_contract_rows',2),
        ('new_mathematical_projection_domain_contract_rows',0),('strict_advisory_cache_entries_added',0)):
        count(qual,key,value)
    need(all(qual[key] is True for key in ('accepted_scalar_compiler_partial_semantic_preservation_proved',
        'emitted_stable_loss_exact_real_projection_proved','emitted_stable_factor_exact_real_projection_proved',
        'emitted_stable_loss_equals_realPairLoss_proved','emitted_stable_factor_equals_realLogisticP_proved',
        'prior4440_payloads_preserved_exactly_as_prefixes','vectors_payloads_unchanged','contracts_payloads_unchanged',
        'all_owned_leases_drained','native_proof_and_metadata_limits_unchanged')),'actual narrow scalar and metadata claims')
    need(all(qual[key] is False for key in ('proof_authority','execution_authority','completion_authority','planner_activation',
        'host_parser_correctness_theorem_proved','python_ranker_source_equivalence_proved','objective_to_IR_translation_proved',
        'computed_gradient_source_equivalence_proved','feature_preparation_to_IR_translation_proved','full_training_loop_to_IR_translation_proved',
        'CPython_math_fsum_semantics_proved','binary64_error_bound_proved','native_Float_optimizer_convergence_proved',
        'global_autoencoder_convergence_proved','whole_codebase_IR_semantic_preservation_proved',
        'atomic_whole_source_snapshot_claimed','historical_execution_origin_proved')),'open source, numeric and authority frontiers')
    for key in ('new_autoencoder_fits','new_public_fits','new_gradient_evaluations','new_optimizer_updates',
        'new_ranker_training_trace_replays','new_feature_preparations'):count(qual,key,0)
    need(qual['all32_governing_RPI_exits']=='OPEN' and qual['full_task_satisfaction']=='unknown' and
        qual['official_benchmark_score'] is None,'task frontier')
    prior_by_name={Path(row['path']).name:row for row in baseline['mutable_pointer_source_pins']}
    need(set(prior_by_name)=={'prior-HF-README-01.md','prior-HF-publication-status-01.json'},'exact two prior mutable bodies')
    card=read_bound(R/'prior-HF-README-01.md',prior_by_name['prior-HF-README-01.md'])[0]+b'''\n\n## Exact-real objective scalar leaves\n\nTwo accepted Lean modules provide 14 theorem queries for a partial typed scalar\ncompiler and the pinned stable-loss and sign-split logistic-factor expressions.\nTheir emitted literal trees evaluate to the earlier exact-real realPairLoss and\nrealLogisticP definitions. Only standard Lean axioms are admitted. The host\ncompiler passed 98 pure controls with native tools and subprocesses blocked;\nsource parsing and rendering used two AST parses and executed no ranker source.\nBoth actual native attempts, complete compiled objects, chunks, environment\nprofiles, preparation records and independent reviews are retained. No ranker\nimport, fit, feature preparation, gradient evaluation, optimizer update or\ntraining trace replay occurred in this increment.\n\nDuckDB/DuckLake hydration and fresh-process readback verify 4,458 payloads in the\nsame 32 families. All preceding 4,440 payloads are exact canonical prefixes. All\n375 vectors and both existing mathematical projection-domain contracts are\nunchanged. The 18 additions contain scalar AST/IR and source records, two accepted\nmodules, two actual attempt records and KG links. No runtime contract, strict\ncache admission or operational authority is added.\n\nHost-parser correctness, the enclosing Python objective loops and list reductions,\ncomputed-gradient translation, Python source equivalence, binary64/libm/fsum\nrefinement, feature preparation, full training, whole-codebase IR preservation,\ngeneral autoencoder convergence and Terminal Bench task satisfaction remain\nopen. All 32 RPI exits remain OPEN, all authority flags remain false, and no\nbenchmark score is claimed. The complete sealed increment and planning history\nare retained in releases/20261004-terminal-codebase-ir-evidence-v1/successor-ranker-objective-scalar-v1.\nAll prior immutable evidence is preserved; prior large archives, raw external\ndependency bodies, SDK logs and caches are not reuploaded.\n'''
    new_card=save(R/'HF-README-02.md',card)
    status,status_pin=load_bound(R/'prior-HF-publication-status-01.json',prior_by_name['prior-HF-publication-status-01.json']['sha256'])
    need(status_pin==prior_by_name['prior-HF-publication-status-01.json'],'prior status same-buffer join')
    status['status']='PUBLISHED_PRIOR_EVIDENCE_WITH_OBJECTIVE_SCALAR_SUCCESSOR'
    status['ranker_objective_scalar_qualification']={'qualified_review':qual_pin,'file_seal':seal_pin,'package_manifest':manifest_pin,
        'decoded_package_review':review_pin,'namespace':NS,'native_attempts':2,'accepted_modules':2,'retained_inconclusive_attempts':0,
        'qualified_theorem_queries':14,'pure_test_cases':98,'metadata_payloads':4458,'metadata_families':32,'unchanged_prior_payloads':4440,
        'unchanged_vectors':375,'unchanged_projection_domain_contracts':2,'new_projection_domain_contracts':0,
        'new_training_calls':0,'exact_real_stable_loss_and_factor_leaf_projection_proved':True,
        'host_parser_correctness_proved':False,'python_source_equivalence_proved':False,'full_objective_translation_proved':False,
        'computed_gradient_translation_proved':False,'binary64_refinement_proved':False,'whole_IR_preservation_proved':False,
        'general_autoencoder_convergence_proved':False,'full_task_satisfaction':'unknown','all32_governing_RPI_exits':'OPEN',
        'official_benchmark_score':None,'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False}
    new_status=save(R/'HF-publication-status-02.json',encoded(status))
    files=[]
    def add(path,remote):files.append({'local':pin(path),'remote':remote})
    for path in sorted((P/'package').iterdir()):
        need(path.is_file() and not path.is_symlink(),'regular package leaf');add(path,NS+'/package/'+path.name)
    for path in sorted(S.rglob('*')):
        need(not path.is_symlink(),'no publication source aliases')
        if path.is_file():
            need(path.suffix!='.log' and not any(part in ('__pycache__','download-cache','private-staging') for part in path.relative_to(S).parts),
                'no SDK logs or private caches');add(path,NS+'/publication/'+str(path.relative_to(S)))
    for name in ('qualified-review-01.json','file-only-seal-01.json','source-model-obligations-01.json'):
        add(Q/name,NS+'/qualification/'+name)
    for name in ('prepare_hf_plan_01.py','prepare_invocation_01.py','scan_final_upload_01.py','review_hf_readback_01.py','HF-parent-preflight-01.json'):
        add(R/name,NS+'/publication-root/'+name)
    # The executed producer and failed file-only attempt remain immutable history.
    attempt,attempt_pin=load_bound(R/'hf-preparation-attempt-01.json')
    need(attempt['schema']=='ranker-objective-scalar-HF-file-preparation-attempt@1' and
        attempt['status']=='failed_before_frozen_upload_plan' and attempt['exit_code']==1 and
        attempt['hf_plan_created'] is False and attempt['remote_mutations']==0 and
        attempt['producer']==pin(R/'prepare_hf_plan_01.py') and
        attempt['archive_decoded_member_review']==review_pin,'retained preplan failure joins old producer and reviewed archive')
    need(type(attempt['partial_outputs']) is list and len(attempt['partial_outputs'])==2 and
        {row['path'] for row in attempt['partial_outputs']}==
        {str(R/'HF-README-01.md'),str(R/'HF-publication-status-01.json')},'exact retained partial output paths')
    for row in attempt['partial_outputs']:
        need(pin(row['path'])==row,'failed-attempt partial output changed')
        add(Path(row['path']),NS+'/publication-root/failed-prepare-01/'+Path(row['path']).name)
    peer_root=W/'maintenance/ranker-objective-scalar-HF-plan-patch-review-20261005-01'
    peer,peer_pin=load_bound(peer_root/'review-receipt.json')
    need(peer['schema']=='ranker-objective-scalar-HF-plan-independent-patch-review@1' and
        peer['status']=='passed_source_only' and peer['findings']==[] and
        peer['corrected_producer']==own and peer['reviewer']==pin(peer_root/'review_source.py'),
        'independent exact corrected-producer patch review')
    for path in (R/'prepare_hf_plan_02.py',R/'hf-preparation-attempt-01.json',
        peer_root/'review_source.py',peer_root/'review-receipt.json'):
        add(path,NS+'/publication-root/prepare-02-provenance/'+path.name)
    files.extend([{'local':new_card,'remote':'README.md'},{'local':new_status,'remote':PREFIX+'/publication-status.json'}])
    need(0<len(files)<=100 and len({row['remote'] for row in files})==len(files),'bounded unique upload population')
    need(all(row['remote'] in ('README.md',PREFIX+'/publication-status.json') or row['remote'].startswith(NS+'/') for row in files),
        'only two mutable pointers and the new immutable namespace')
    need(all(row['remote'] not in baseline['files'] for row in files if row['remote'].startswith(NS+'/')),'namespace occupied')
    need(pin(Path(__file__).resolve())==own,'plan producer changed')
    plan={'schema':'terminal-ir-successor-evidence-publication-plan@1','repo_id':'Publicus/codebase-ir-proof-index',
        'expected_parent_commit':PARENT,'immutable_namespace':NS,'files':files,
        'scope':'Partial exact-real scalar compiler and emitted stable-loss/sign-split-factor leaves only; host parser and whole objective open',
        'old_immutable_files_preserved':True,'large_prior_archive_reupload':False}
    need(all(pin(path)==binding for path,binding in list(HELD.items())),'parsed and selected inputs changed before plan closure')
    binding=save(R/'hf-plan-01.json',encoded(plan))
    print(json.dumps({'plan':binding,'files':len(files),'bytes':sum(row['local']['bytes'] for row in files)}))


if __name__=='__main__':main()
