"""File-only producer for one fresh bounded typed-prefix native batch.

Preserves the previous complete environment, registers the actually qualified
container module and chunks, and captures exact reviewed per-check sources.
No compiler, scheduler, metadata, training or tests are invoked.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
COMMON = (22214, '40ed16e8f7bb3d7c7db1a7b6c2de9660d50db073c9ce318614d61e3be84451e0')
CHECKER = {'path':str(ROOT.with_name('ranker-real-curvature-20261005-01')/'preparation/lean-original-descent-01-producer/bounded_analytic_checker.py'),
           'bytes':29086,'sha256':'04015267ed110533a7406c0b39c38b88a974a1d80259fd5755a99ef908a8a8b4'}
RETENTION = {'path':str(ROOT.with_name('ranker-real-curvature-20261005-01')/'preparation/lean-original-descent-01-producer/RetainLeanProof.py'),
             'bytes':5828,'sha256':'ccdf7df547844ac5d39cc077c8a14194fd06f7bb51838d80ffa9d7f349999e66'}


def helpers():
    path = ROOT/'prefix_file_helpers_01.py'
    if len(COMMON) != 2 or path.resolve(strict=True) != path or path.is_symlink():
        raise ValueError('externally reviewed canonical helper required')
    with path.open('rb') as stream: raw = stream.read(COMMON[0]+1)
    if len(raw) != COMMON[0] or hashlib.sha256(raw).hexdigest() != COMMON[1]:
        raise ValueError('reviewed helper bytes differ')
    ns = {'__file__':str(path),'__name__':'held_prefix_preparation_file_helpers'}
    exec(compile(raw,str(path),'exec'),ns)
    ns['exact']({'path':str(path),'bytes':COMMON[0],'sha256':COMMON[1]})
    return ns


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-producer-sha256',required=True)
    args = parser.parse_args()
    if not __debug__ or re.fullmatch('[0-9a-f]{64}',args.expected_producer_sha256) is None:
        raise ValueError('unoptimized reviewed producer pin required')
    h = helpers()
    need,pin = h['need'],h['pin']
    own = pin(Path(__file__).resolve())
    need(own['sha256'] == args.expected_producer_sha256,'reviewed producer differs')
    h['core_source_gate']()
    rows,inherited,seal = h['complete_guard_union']()
    def guards():
        found = {}
        for role,cwd in (('root',h['WORKSPACE']),('child',h['WORKSPACE']/'external/ipfs_accelerate')):
            wanted = inherited['original_checkout_guards'][role]
            head = subprocess.check_output(['git','-c','core.fsmonitor=false','-C',str(cwd),'rev-parse','HEAD'],text=True,timeout=30).strip()
            index = pin(wanted['index']['path'])
            need(head == wanted['head'] and index == wanted['index'],'original checkout changed')
            found[role] = {'head':head,'index':index}
        return found
    before = guards()
    request = dict(inherited)
    request.update(schema='terminal-ranker-objective-prefix-kernel-request@1',strict_old_inputs=rows,
        prior_container_request=h['BASE_REQUEST'],prior_container_seal=h['Q6_SEAL'],
        independent_core_source_review=h['SOURCE_GATE'],original_checkout_guards=before,
        exact_native_mode=h['MODE'],exact_theorem_names=list(h['QUERIES']),strict_guard_count=len(rows),
        new_proof_scope='Four actual source-bound typed mixed projections; eight concrete compilation/evaluation queries only',
        candidate_compiled=False,candidate_native_qualified=False,actual_new_native_jobs=0,
        actual_new_model_jobs=0,actual_new_test_cases=0,actual_new_metadata_jobs=0,
        actual_new_source_function_executions=0,preparation_status='file_only_prepared_native_execution_pending',
        generic_typed_prefix_semantic_preservation_proved=False,actual_emitted_prefix_compiled=False,
        objective_source_equivalence_proved=False,gradient_source_equivalence_proved=False,
        full_source_runtime_equivalence=False,binary64_error_bound_proved=False,
        native_Float_optimizer_convergence_proved=False,global_autoencoder_convergence_proved=False,
        full_task_satisfaction='unknown',official_benchmark_score=None,**h['AUTHORITY'])
    h['validate_guard_union'](request)
    source_raw,source_pin = h['fixed'](ROOT/'math/ObjectivePrefixProjections.lean',h['CORE_PINS']['math/ObjectivePrefixProjections.lean'],True)
    need(re.findall(rb'^import ([A-Za-z0-9_.]+)\s*$',source_raw,re.M) == [b'ObjectivePrefixIR'],
         'one exact qualified direct import required')
    base = h['document'](h['BASE_PROFILE'])
    need(len(base['files']) == base['external_file_count'] == 20119
         and base['native_per_file_capture_bytes_unchanged'] == 65536
         and base['root_reconstructed_external_module_aggregate_max_bytes'] == 3997696,
         'unchanged complete prior native environment required')
    extended,container = h['extended_base'](base)
    imports = [h['qualified_module'](name,extended) for name in ('ObjectiveScalarIR','RealStableFactor','TypedNumericSlice','ObjectiveContainerCore','ObjectivePrefixIR')]
    executable = pin(Path(sys.executable).resolve(strict=True))
    need(executable['bytes'] == 7845032 and executable['sha256'] == '1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f',
         'exact existing Python executable required')
    for row in (CHECKER,RETENTION): h['exact'](row)
    preparation = ROOT/'preparation'
    preparation.mkdir(exist_ok=True)
    (ROOT/'evidence').mkdir(exist_ok=True)
    request_pin = h['write'](preparation/'request-v1.json',request)
    destination = preparation/(h['MODE']+'-producer')
    destination.mkdir()
    files = {row['path']:row for row in extended['files']}
    sources = []
    for original in (source_pin,CHECKER,RETENTION,own,{'path':str(ROOT/'prefix_file_helpers_01.py'),'bytes':COMMON[0],'sha256':COMMON[1]}):
        raw = h['exact'](original,True)
        captured = destination/Path(original['path']).name
        with captured.open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        captured.chmod(0o444)
        held = pin(captured)
        need((held['bytes'],held['sha256']) == (original['bytes'],original['sha256']) and held['path'] not in files,
             'unique exact new held capture required')
        sources.append({'original':original,'captured':held})
        files[held['path']] = held
    need(executable['path'] in files and files[executable['path']] == executable,'Python already in unchanged closure required')
    profile = dict(extended)
    profile.update(selected_proof_sources=[sources[0]['captured']],profile_parent=h['BASE_PROFILE'],
        qualified_container_import=container,per_check_sources=sources,files=[files[p] for p in sorted(files)],
        external_file_count=len(files),external_file_bytes=sum(row['bytes'] for row in files.values()))
    profile_pin = h['write'](destination/'environment-manifest.json',profile)
    Path(profile_pin['path']).chmod(0o444)
    spec = {'schema':'ranker-objective-prefix-kernel-native-check-specification@1','mode':h['MODE'],
        'source':sources[0]['captured'],'environment_manifest':profile_pin,'expected_success':True,
        'theorem_names':list(h['QUERIES']),'freeze_producer':sources[3]['captured'],
        'checker_wrapper':sources[1]['captured'],'retention_helper':sources[2]['captured'],
        'file_helpers':sources[4]['captured'],'python_executable':executable,
        'independent_core_source_review':h['SOURCE_GATE'],'qualified_imports':imports,
        'profile_parent':h['BASE_PROFILE'],'source_capture_scope':'individual held-byte copies; no atomic live or loader-open claim'}
    spec_pin = h['write'](preparation/(h['MODE']+'-check-specification.json'),spec)
    Path(spec_pin['path']).chmod(0o444)
    h['verify_held']()
    need(guards() == before,'original checkout changed during preparation')
    print(json.dumps({'status':'prepared_file_only_native_execution_pending','request':request_pin,
        'specification':spec_pin,'profile':profile_pin,'strict_inputs':len(rows),
        'environment_files':len(files),'native_jobs':0,'target_imports':0}))


if __name__ == '__main__': main()
