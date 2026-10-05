#!/usr/bin/env python3
"""File-only review: JSON, source text, hashes, and byte joins; no artifact imports."""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
Q2 = ROOT / 'qualification/codebase_ir/ranker-real-curvature-20261005-01'
Q3 = ROOT / 'qualification/codebase_ir/ranker-real-convergence-20261005-01'
OUT = ROOT / 'maintenance/ranker-convergence-math-review-20261005-01'
JOBS = {
    'lean-strong-lower-01': ('RealStrongLower', 'passed', 6),
    'lean-pl-01': ('RealPL', 'passed', 5),
    'lean-stable-factor-01': ('RealStableFactor', 'passed', 2),
    'lean-gap-01': ('RealGapContraction', 'passed', 6),
    'lean-minimizer-01': ('RealMinimizer', 'inconclusive', 0),
    'lean-minimizer-02': ('RealMinimizerV2', 'passed', 9),
    'lean-growth-01': ('RealMinimumGrowth', 'passed', 8),
    'lean-original-convergence-01': ('OriginalRealConvergence', 'inconclusive', 0),
    'lean-original-convergence-02': ('OriginalRealConvergenceV2', 'passed', 3),
}
ALLOWED = {'propext', 'Classical.choice', 'Quot.sound'}
NATIVE_BOUNDS = {'cpu_seconds': 20, 'timeout_seconds': 20,
                 'max_input_bytes': 262144, 'max_output_bytes': 65536,
                 'max_workspace_bytes': 16777216}
issues = []
file_hashes = {}
pin_references = 0
joined_objects = []
queried = []
attempts = []
module_graph = {}


def require(condition, message):
    if not condition:
        issues.append(message)


def digest_file(path):
    path = Path(path)
    key = str(path)
    if key not in file_hashes:
        digest = hashlib.sha256()
        size = 0
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1048576), b''):
                size += len(block)
                digest.update(block)
        file_hashes[key] = {'path': key, 'bytes': size, 'sha256': digest.hexdigest()}
    return file_hashes[key]


def verify_pin(pin, context):
    global pin_references
    pin_references += 1
    actual = digest_file(pin['path'])
    require(actual['bytes'] == pin['bytes'] and actual['sha256'] == pin['sha256'],
            f'{context}: pin mismatch: {pin["path"]}')


def walk_pins(value, context):
    if isinstance(value, dict):
        if {'path', 'bytes', 'sha256'} <= value.keys():
            verify_pin(value, context)
        for child in value.values():
            walk_pins(child, context)
    elif isinstance(value, list):
        for child in value:
            walk_pins(child, context)


def read_json(path):
    digest_file(path)
    return json.loads(Path(path).read_bytes())


def source_without_comments(text):
    return re.sub(r'/\-.*?\-/|--[^\n]*', '', text, flags=re.S)


def imports(text):
    return re.findall(r'^import\s+(\S+)', text, flags=re.M)


def review_job(job, module, wanted_status, query_count):
    check_path = Q3 / f'evidence/{job}/check-result.json'
    spec_path = Q3 / f'preparation/{job}-check-specification.json'
    inv_path = Q3 / f'preparation/{job}-invocation.json'
    closed_path = Q3 / f'evidence/{job}/closed.json'
    outer_path = Q3 / f'evidence/{job}-closed.json'
    check, spec, inv, closed, outer = map(read_json,
                                        [check_path, spec_path, inv_path, closed_path, outer_path])
    for body in [check, spec, inv, closed, outer]:
        walk_pins(body, job)
    require(check['status'] == wanted_status, f'{job}: status')
    require(check['native_invocations'] == check['native_lean_invocations'] == 1,
            f'{job}: native call census')
    require(check['native_bounds'] == NATIVE_BOUNDS, f'{job}: unchanged native caps')
    require(check['post_call_binding_error'] is None, f'{job}: post-call binding')
    require(check['proof_authority'] is False and closed['proof_authority'] is False,
            f'{job}: proof authority remains false')
    require(check['workspace_cleaned'] is True and not closed['cleanup_errors']
            and not outer['cleanup_errors'], f'{job}: native cleanup')
    require(closed['root_release_returned'] is True, f'{job}: root lease released')
    state = closed['final_resource_state']
    for name in ['active_lease_count', 'active_child_lease_count', 'active_root_lease_count',
                 'allocated_child_process_slots', 'waiting_request_count']:
        require(state[name] == 0, f'{job}: {name} drained')
    require(all(v == 0 for v in state['allocated'].values()), f'{job}: allocated resources drained')
    require(check['native_elapsed_seconds'] < 20, f'{job}: native elapsed bound')
    require(check['source'] == spec['source'] and check['environment_manifest'] == spec['environment_manifest'],
            f'{job}: specification/source/environment join')
    require(check['source']['path'].endswith(f'/{module}.lean'), f'{job}: module filename')
    env = read_json(check['environment_manifest']['path'])
    walk_pins(env, f'{job}: frozen environment')
    require(env['mathlib_revision'] == '5ed2965256430c3649e86755f9576b54eca72435',
            f'{job}: Mathlib revision')
    require(Path(env['mathlib_toolchain']['path']).read_text().strip() == 'leanprover/lean4:v4.34.0',
            f'{job}: Lean toolchain')
    require(env['proof_authority'] is False, f'{job}: environment proof authority')
    require(env['actual_runtime_file_opens_traced'] is False and env['atomic_source_snapshot_claimed'] is False,
            f'{job}: declaration/runtime-open scope remains honest')
    for item in env['per_check_sources']:
        require(item['captured']['sha256'] == item['original']['sha256']
                and item['captured']['bytes'] == item['original']['bytes'],
                f'{job}: exact held producer copy')
    registered = {item['module'] for item in env['source_import_modules']}
    registered |= {item['module'] for item in env['local_checked_modules']}
    direct = imports(Path(check['source']['path']).read_text())
    require(set(direct) <= registered, f'{job}: direct imports in frozen registry')
    require(check['direct_imports_and_implicit_Init_in_frozen_registry'] is True,
            f'{job}: implicit Init in frozen registry')
    dependency_rows = []
    for item in env['local_checked_modules']:
        dependency = read_json(item['qualification']['path'])
        require(dependency['status'] == 'passed' and dependency['matches_expectation'] is True,
                f'{job}: dependency {item["module"]} qualified')
        require(dependency['environment_manifest'] == item['environment'],
                f'{job}: dependency {item["module"]} environment join')
        imported = next((x for x in env['source_import_modules'] if x['module'] == item['module']), None)
        require(imported is not None, f'{job}: dependency import record {item["module"]}')
        if imported is not None:
            require(imported['source'] == dependency['augmented_source'],
                    f'{job}: dependency {item["module"]} exact checked source')
            expected_objects = {(x['path'], x['bytes'], x['sha256'])
                                for x in dependency['compiled_artifacts']}
            actual_objects = {(x['path'], x['bytes'], x['sha256']) for x in imported['compiled']}
            require(expected_objects == actual_objects,
                    f'{job}: dependency {item["module"]} complete compiled-object join')
        dependency_rows.append(item['module'])
    module_graph[module] = [name for name in direct if name in dependency_rows]
    profile = check['retention_profile']
    require(profile['native_cpu_seconds'] == profile['native_wall_seconds'] == 20
            and profile['native_per_file_capture_bytes'] == profile['chunk_bytes'] == 65536
            and profile['native_workspace_bytes'] == 16777216
            and profile['native_max_source_bytes'] == 262144
            and profile['compression'] == 'none', f'{job}: retention/native caps')
    profile_hash = hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    require(profile_hash == check['retention_profile_sha256'], f'{job}: retention profile digest')
    row = {'job': job, 'module': module, 'status': check['status'],
           'receipt': digest_file(check_path), 'source': check['source'],
           'environment': check['environment_manifest'], 'specification': digest_file(spec_path),
           'closure': digest_file(closed_path), 'outer_closure': digest_file(outer_path),
           'native_elapsed_seconds': check['native_elapsed_seconds'],
           'declared_environment_file_count': len(env['files']),
           'registered_local_modules': dependency_rows, 'source_direct_imports': direct,
           'qualified_query_count': len(check['theorem_axiom_output'])}
    if wanted_status == 'passed':
        require(check['native_lean_returncode'] == check['returncode'] == outer['returncode'] == 0,
                f'{job}: successful return codes')
        require(check['matches_expectation'] is True and check['output_truncated'] is False
                and check['reconstruction_validation_error'] is None
                and check['axiom_report_error'] is None, f'{job}: accepted native receipt')
        require(check['reconstruction_validation']['status'] == 'passed'
                and check['reconstruction_validation']['manifest_complete'] is True
                and check['reconstruction_validation']['exact_chunk_population'] is True,
                f'{job}: complete retained reconstruction')
        require(len(check['theorem_axiom_output']) == query_count, f'{job}: query count')
        require([x['theorem'] for x in check['theorem_axiom_output']] == spec['theorem_names'],
                f'{job}: exact specified query registry')
        for query in check['theorem_axiom_output']:
            require(set(query['axioms']) == ALLOWED and query['report_occurrences'] == 2,
                    f'{job}: allowed standard theorem axioms')
            queried.append({'module': module, **query})
        clean_source = source_without_comments(Path(check['source']['path']).read_text())
        require(not re.search(r'\b(sorry|admit|axiom|unsafe|native_decide)\b', clean_source),
                f'{job}: explicit proof bypass or custom axiom')
        manifest_path = Path(check['retention_manifest']['path'])
        manifest = read_json(manifest_path)
        require(manifest == check['retention_manifest_body'] and manifest['status'] == 'complete',
                f'{job}: retention manifest body join')
        require(manifest['retention_profile_sha256'] == profile_hash
                and manifest['native_lean_returncode'] == 0, f'{job}: manifest profile/native join')
        listed_chunks = [x['name'] for x in manifest['chunks']]
        require(listed_chunks == [f'LeanProofChunk{i:03d}.bin' for i in range(len(listed_chunks))],
                f'{job}: consecutive chunk names')
        require(set(listed_chunks) == {x.name for x in manifest_path.parent.glob('LeanProofChunk*.bin')},
                f'{job}: exact chunk population')
        chunks = {}
        for chunk in manifest['chunks']:
            path = manifest_path.parent / chunk['name']
            verify_pin({'path': str(path), 'bytes': chunk['bytes'], 'sha256': chunk['sha256']}, job)
            require(chunk['bytes'] <= 65536, f'{job}: chunk capture cap')
            chunks[chunk['name']] = path.read_bytes()
        consumed = []
        total = 0
        for obj in manifest['objects']:
            body = b''.join(chunks[name] for name in obj['chunks'])
            consumed.extend(obj['chunks'])
            object_hash = hashlib.sha256(body).hexdigest()
            require(len(body) == obj['bytes'] and object_hash == obj['sha256'],
                    f'{job}: in-memory reconstructed object')
            path = manifest_path.parent / obj['name']
            require(path.read_bytes() == body, f'{job}: retained object equals complete chunk body')
            verify_pin({'path': str(path), 'bytes': obj['bytes'], 'sha256': obj['sha256']}, job)
            total += len(body)
            joined_objects.append({'job': job, 'name': obj['name'], 'bytes': len(body),
                                   'sha256': object_hash, 'chunks': len(obj['chunks']),
                                   'joined_in_memory_only': True})
        require(consumed == listed_chunks and total == manifest['aggregate_raw_object_bytes'],
                f'{job}: exact object/chunk aggregate')
        require(total <= profile['max_raw_object_bytes'] and len(chunks) <= profile['max_chunk_files'],
                f'{job}: aggregate bounded retention')
        row['retained_object_bytes'] = total
        row['retained_chunk_count'] = len(chunks)
    else:
        require(check['native_lean_returncode'] == check['returncode'] == outer['returncode'] == 1
                and check['matches_expectation'] is False, f'{job}: retained inconclusive result')
        require(check['compiled_artifacts'] == [] and check['theorem_axiom_output'] == [],
                f'{job}: failed attempt not counted as proof')
        require('sorryAx' in check['stdout'], f'{job}: incomplete theorem diagnosis retained')
        row['retained_failure_diagnostic'] = check['stdout'].splitlines()[:8]
    attempts.append(row)


def main():
    observed_jobs = {p.parent.name for p in (Q3 / 'evidence').glob('*/check-result.json')}
    require(observed_jobs == set(JOBS), 'exact nine-attempt native census')
    for job, values in JOBS.items():
        review_job(job, *values)
    require(len(queried) == 39, 'exact 39 qualified theorem-query entries')
    final = read_json(Q3 / 'evidence/lean-original-convergence-02/check-result.json')
    final_text = source_without_comments(Path(final['source']['path']).read_text())
    require(re.search(r'theorem\s+originalReal_model_converges\s*:\s*∃!', final_text) is not None,
            'final model theorem has no minimizer/contraction/convergence argument')
    require('∀ w0 : Fin 80 → ℝ' in final_text and 'Tendsto (originalRealIterate w0)' in final_text,
            'final theorem quantifies every original real initial vector')
    require('originalReal_exists_unique_global_minimizer' in final_text,
            'final existence/uniqueness supplied by an independently checked theorem')
    require('RealMinimizer' not in module_graph.get('RealMinimumGrowth', [])
            and 'OriginalRealConvergence' not in module_graph.get('OriginalRealConvergenceV2', []),
            'failed modules absent from actual mathematical dependencies')
    seal_path = Q2 / 'file-only-seal-01.json'
    seal = read_json(seal_path)
    for pin in seal['files']:
        verify_pin(pin, 'prior Q2 sealed regular files')
    require(len(seal['files']) == seal['regular_file_count']
            and sum(x['bytes'] for x in seal['files']) == seal['regular_file_bytes'],
            'prior Q2 complete sealed file census')
    for link in seal['fixture_symlinks']:
        target = os.readlink(link['path'])
        body = target.encode()
        require(target == link['target'] and len(body) == link['bytes']
                and hashlib.sha256(body).hexdigest() == link['sha256'],
                f'prior Q2 no-follow fixture alias: {link["path"]}')
    audit_path = Q2 / 'proof-cache/final-numeric-coordinate-source-audit-01.json'
    original_audit = read_json(audit_path)
    walk_pins(original_audit, 'prior original numeric/profile/descent semantic joins')
    require(original_audit['status'] == 'exact_original_numeric_and_real_profile_dependency_joins_verified_file_only',
            'prior original numeric/profile join status retained')
    require(all(x['all_320_coordinates_exact'] and x['four_norms_exact']
                and x['mu_eta_maxNorm_meanL_conservativeL_exact']
                for x in original_audit['coordinate_source_matches']),
            'prior original 320-coordinate/exact-scalar bindings retained')
    report = {
        'schema': 'ranker-original-real-convergence-independent-file-review@1',
        'status': 'passed_file_only_review' if not issues else 'failed_file_only_review',
        'review_source': digest_file(Path(__file__).resolve()),
        'review_work': {'Lean_calls': 0, 'native_checks': 0, 'artifact_imports': 0,
                        'decoder_classifier_training_fit_replay_solver_test_jobs': 0,
                        'Q2_or_Q3_writes': 0, 'Git_or_HF_operations': 0,
                        'method': 'source/JSON reads, existing pin hashes, byte joins in memory only'},
        'native_census': {'calls': 9, 'passed': 7, 'inconclusive_retained': 2,
                          'qualified_theorem_query_entries': len(queried)},
        'attempts': attempts, 'qualified_queries': queried,
        'module_direct_dependency_graph': module_graph,
        'complete_retained_objects_joined_in_memory': joined_objects,
        'pin_review': {'references_checked': pin_references, 'unique_regular_files_hashed': len(file_hashes),
                       'unique_regular_file_bytes_hashed': sum(x['bytes'] for x in file_hashes.values()),
                       'all_declared_environment_file_pins_rehashed': True,
                       'actual_runtime_file_open_trace_claimed': False,
                       'atomic_live_source_snapshot_claimed': False},
        'prior_Q2_preservation': {'seal': digest_file(seal_path), 'regular_files': len(seal['files']),
                                 'regular_bytes': seal['regular_file_bytes'],
                                 'no_follow_fixture_aliases': len(seal['fixture_symlinks']),
                                 'semantic_data_join_audit': digest_file(audit_path),
                                 'original_320_coordinates_and_exact_mu_eta_bindings_retained': True},
        'mathematical_review': {
            'actual_objective': 'F(w)=originalRealMu/2*Σ_j(w_j)^2+1/4*Σ_i log(1+exp(-dot(w,originalRealDifferences_i)))',
            'actual_fixed_dimensions': {'pairs': 4, 'coordinates': 80},
            'parameter_source': 'Exact Q2 original literal Rat coordinates and scalars, cast to Real; closed finite indexing/norm/mean joins are qualified conclusions, not alignment premises.',
            'native_scalar_literals': original_audit['native_scalar_literals'],
            'noncircular_chain': ['actual scalar and line derivatives', 'derived lower Taylor inequality',
                                 'nonnegative regularizer lower bound and continuity',
                                 'bounded actual sublevel and actual global minimizer existence',
                                 'scalar Fermat stationarity, quadratic growth and actual uniqueness',
                                 'sum-of-squares PL domination', 'original safe descent plus PL gives gap contraction',
                                 'actual recursive iteration and derived geometric rate',
                                 'gap squeeze and coordinate-square/sqrt limits',
                                 'Pi Tendsto plus actual unique minimizer removes all minimum/convergence premises from final theorem'],
            'final_theorem': 'RankerRealCurvature.originalReal_model_converges',
            'final_theorem_has_no_minimum_contraction_or_convergence_premise': True,
            'conclusion': 'A unique global minimizer of this fixed original exact-real objective exists; every initial Fin 80 real vector has exact-real iterates and objective values tending to that minimizer/value.',
            'stable_source_branch_result': 'RealStableFactor proves exact-real stable probability/coordinate-gradient branch identities; binary64 execution is outside that conclusion.',
            'topology_norm_check': 'All analytic bounds use the explicit sum of coordinate squares. Compactness uses a finite-Pi coordinate box and proper function-space topology; no equality with the default function norm is assumed.',
            'retained_failures': {'RealMinimizer': 'Log-continuity nonzero goal failed to normalize its Pi/composition expression; RealMinimizerV2 supplies the explicit positive 1+exp(-margin) expression.',
                                  'OriginalRealConvergence': 'Coordinate-square nonnegativity had an unresolved AddLeftMono typeclass; V2 annotates Fin 80 and its actual squared coordinate expression.'}},
        'metadata_and_scope': {'proof_authority': False,
                               'all_native_environment_checker_and_owned_closure_proof_authority_fields_false': True,
                               'inherited_optimizer_convergence_proved_false_explanation': 'The native receipt keeps broad pipeline authority/scope fields false. Specific qualified Lean queries establish only the named fixed original exact-real theorem; no global pipeline flag is promoted.',
                               'Python_binary64_source_runtime_equivalence_proved': False,
                               'autoencoder_equivalence_or_convergence_proved': False,
                               'arbitrary_IR_or_general_task_satisfaction_proved': False,
                               'Float_libm_fsum_error_bound_or_execution_origin_proved': False},
        'issues': issues,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT / 'review-receipt.json'
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': report['status'], 'issues': issues, 'receipt': str(destination),
                      'native_census': report['native_census'], 'pin_review': report['pin_review'],
                      'joined_object_count': len(joined_objects)}))
    return 0 if not issues else 1


if __name__ == '__main__':
    sys.exit(main())
