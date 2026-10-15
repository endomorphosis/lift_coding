"""Prepare an exact reviewed container-language module without native calls.

Each module freezes a fresh request/profile/specification. Only actually closed
prior stages may supply imports. Existing environment bodies remain unchanged.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import json

ROOT=Path(__file__).resolve().parent
COMMON = (20510, '694d198c493d2bb95e9452ca5bbbf2098710769695f707e5c098f585d3d35e34')
CHECKER={'path':str(ROOT.with_name('ranker-real-curvature-20261005-01')/'preparation/lean-original-descent-01-producer/bounded_analytic_checker.py'),
 'bytes':29086,'sha256':'04015267ed110533a7406c0b39c38b88a974a1d80259fd5755a99ef908a8a8b4'}
RETENTION={'path':str(ROOT.with_name('ranker-real-curvature-20261005-01')/'preparation/lean-original-descent-01-producer/RetainLeanProof.py'),
 'bytes':5828,'sha256':'ccdf7df547844ac5d39cc077c8a14194fd06f7bb51838d80ffa9d7f349999e66'}


def helpers():
    p=ROOT/'language_file_helpers_01.py'
    if len(COMMON)!=2 or p.resolve(strict=True)!=p or p.is_symlink():raise ValueError('reviewed canonical helper required')
    with p.open('rb') as stream:raw=stream.read(COMMON[0]+1)
    if len(raw)!=COMMON[0] or hashlib.sha256(raw).hexdigest()!=COMMON[1]:raise ValueError('reviewed helper differs')
    ns={'__file__':str(p),'__name__':'held_language_batch_file_helpers'}
    exec(compile(raw,str(p),'exec'),ns)
    ns['exact']({'path':str(p),'bytes':COMMON[0],'sha256':COMMON[1]})
    return ns


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',required=True);ap.add_argument('--plan',required=True,type=Path)
    ap.add_argument('--expected-plan-sha256',required=True);ap.add_argument('--expected-source-sha256',required=True)
    a=ap.parse_args()
    if not __debug__ or any(re.fullmatch('[0-9a-f]{64}',s) is None for s in (a.expected_plan_sha256,a.expected_source_sha256)):
        raise ValueError('unoptimized external source/plan pins required')
    h=helpers();need=h['need'];own=h['pin'](Path(__file__).resolve())
    need(own['sha256']==a.expected_source_sha256,'reviewed preparation source differs')
    chosen=h['module'](a.mode)
    need(chosen['qualification_root']==str(ROOT),
         'only exact fresh owned relay module allowed; old OriginalRealConvergenceV2 evidence is context only')
    h['source_gate'](a.mode)
    pp=h['pin'](a.plan);need(pp['sha256']==a.expected_plan_sha256,'reviewed preparation plan differs')
    plan=h['document'](pp)
    need(set(plan)=={'schema','mode','imports','tooling_source_review'}
         and plan['schema']=='ranker-container-language-batch-plan@1' and plan['mode']==a.mode,
         'closed exact reviewed preparation plan required')
    gate=h['document'](plan['tooling_source_review'])
    helper_pin={'path':str(ROOT/'language_file_helpers_01.py'),'bytes':COMMON[0],'sha256':COMMON[1]}
    runner_pin=h['pin'](ROOT/'run_language_batch_01.py')
    need(gate['status']=='passed_source_only' and gate['findings']==[]
         and gate['reviewed_sources']==[helper_pin,own,runner_pin]
         and all(gate[k] is False for k in h['AUTHORITY']), 'exact file/native tooling source review required')
    expected_dependencies=chosen['prior_modes']
    need([r['mode'] for r in plan['imports']]==expected_dependencies,'exact dependency-prefix batch list required')
    rows,inherited=h['complete_guard_union']()
    def guards():
        found={}
        for role,cwd in (('root',h['WORKSPACE']),('child',h['WORKSPACE']/'external/ipfs_accelerate')):
            wanted=inherited['original_checkout_guards'][role]
            head=subprocess.check_output(['git','-c','core.fsmonitor=false','-C',str(cwd),'rev-parse','HEAD'],text=True,timeout=30).strip()
            index=h['pin'](wanted['index']['path'])
            need(head==wanted['head'] and index==wanted['index'],'original checkout changed')
            found[role]={'head':head,'index':index}
        return found
    before=guards()
    raw=h['exact'](chosen['source'],True)
    need(re.findall(rb'^import ([A-Za-z0-9_.]+)\s*$',raw,re.M)==[n.encode() for n in chosen['direct_imports']],
         'exact reviewed direct imports required')
    base=h['document'](h['BASE_PROFILE'])
    need(len(base['files'])==base['external_file_count']==20184
         and base['native_per_file_capture_bytes_unchanged']==65536
         and base['root_reconstructed_external_module_aggregate_max_bytes']==3997696,
         'complete unchanged previously qualified environment required')
    extended,joined=h['import_extension'](base,plan['imports'])
    imports=[h['qualified_module'](n,extended) for n in h['BASE_IMPORT_NAMES']]
    imports+=joined
    executable=h['pin'](Path(sys.executable).resolve(strict=True))
    need(executable['bytes']==7845032 and executable['sha256']=='1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f',
         'exact Python executable required')
    preparation=ROOT/'preparation';preparation.mkdir(exist_ok=True);(ROOT/'evidence').mkdir(exist_ok=True)
    destination=preparation/(a.mode+'-producer');destination.mkdir()
    sources=[];files={r['path']:r for r in extended['files']}
    for original in (chosen['source'],CHECKER,RETENTION,own,helper_pin):
        body=h['exact'](original,True);p=destination/Path(original['path']).name
        with p.open('xb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
        p.chmod(0o444);held=h['pin'](p)
        need((held['bytes'],held['sha256'])==(original['bytes'],original['sha256']) and held['path'] not in files,
             'unique exact held capture required')
        sources.append({'original':original,'captured':held});files[held['path']]=held
    need(files.get(executable['path'])==executable,'exact Python already in closure required')
    profile=dict(extended)
    profile.update(selected_proof_sources=[sources[0]['captured']],profile_parent=h['BASE_PROFILE'],
        per_check_sources=sources,files=[files[p] for p in sorted(files)],external_file_count=len(files),
        external_file_bytes=sum(r['bytes'] for r in files.values()))
    profile_pin=h['write'](destination/'environment-manifest.json',profile);Path(profile_pin['path']).chmod(0o444)
    request=dict(inherited)
    request.update(schema='terminal-ranker-container-language-request@1',strict_old_inputs=rows,
        prior_language_context_request=h['PRIOR_REQUEST'],prior_language_context_seal=h['PRIOR_SEAL'],
        independent_core_source_review=h['SOURCE_GATE'],original_checkout_guards=before,
        exact_native_mode=a.mode,exact_theorem_names=chosen['queries'],strict_guard_count=len(rows),
        preparation_plan=pp,staged_import_inputs=plan['imports'],candidate_compiled=False,candidate_native_qualified=False,
        actual_new_native_jobs=0,actual_new_model_jobs=0,actual_new_test_cases=0,actual_new_metadata_jobs=0,
        actual_new_source_function_executions=0,full_task_satisfaction='unknown',official_benchmark_score=None,
        complete_original_prefix_emitted=True,whole_objective_semantics_proved=False,
        whole_gradient_semantics_proved=False,native_Float_optimizer_convergence_proved=False,
        global_autoencoder_convergence_proved=False,strict_cache_admission=False,**h['AUTHORITY'])
    request.update(new_proof_scope='Exact unchanged fixed-model convergence three-query module under a fresh modern owned qualification envelope',
        corpus_scope='Byte-identical historical OriginalRealConvergenceV2; exact baseline supplies genuine RealMinimumGrowth and RealGapContraction only',
        actual_emitted_prefix_compiled=True,generated_prefix_preservation_proved=True,
        actual_margins_eval_success_proved=True,
        actual_objective_and_computed_gradient_equivalence_proved=False,
        prior_generic_container_language_qualified=True,prior_generic_source_container_success_qualified=True,
        prior_failed_margins_native_attempts=4,prior_failed_margins_qualified_queries=0,
        modern_owned_relay_admitted=False,historical_owned_schema_reclassified=False,
        current_stage_new_native_modes=h['MODE_ORDER'],current_stage_expected_qualified_queries=3)
    h['validate_guard_union'](request)
    req_pin=h['write'](preparation/(a.mode+'-request.json'),request)
    spec={'schema':'ranker-container-language-native-specification@1','mode':a.mode,'selected_module':chosen,
        'source':sources[0]['captured'],'environment_manifest':profile_pin,'expected_success':True,
        'theorem_names':chosen['queries'],'freeze_producer':sources[3]['captured'],'checker_wrapper':sources[1]['captured'],
        'retention_helper':sources[2]['captured'],'file_helpers':sources[4]['captured'],'python_executable':executable,
        'independent_core_source_review':h['SOURCE_GATE'],'qualified_imports':imports,'profile_parent':h['BASE_PROFILE'],
        'preparation_plan':pp,'staged_import_inputs':plan['imports'],
        'source_capture_scope':'individual held-byte copies; no atomic live or loader-open claim'}
    spec_pin=h['write'](preparation/(a.mode+'-check-specification.json'),spec);Path(spec_pin['path']).chmod(0o444)
    h['verify_held']();need(guards()==before,'original checkout changed during preparation')
    print(json.dumps({'status':'prepared_file_only','request':req_pin,'specification':spec_pin,'profile':profile_pin,
        'mode':a.mode,'strict_guards':len(rows),'environment_files':len(files),'native_jobs':0}))


if __name__=='__main__':main()
