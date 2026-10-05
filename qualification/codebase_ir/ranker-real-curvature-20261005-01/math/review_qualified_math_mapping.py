"""File-only map of already completed analytic proof checks; no prover calls.

Only standard-library file reads and a new JSON review output occur. The exact
numeric Lean source is independently reconstructed in memory from the existing
qualified numeric binding; no norms, binding values or source files are generated.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path('/home/barberb/lift_coding/qualification/codebase_ir/ranker-real-curvature-20261005-01')
OUTPUT = ROOT / 'math/qualified-proof-mapping-01.json'
MAX_FILE = 16 * 1024**2
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}
MODULE_ROLES = {
    'LogisticCoefficient': 'Real logistic p in (0,1), coefficient in [0,1/4], sharp c(0)=1/4.',
    'CoordinateGeometry': 'Explicit Euclidean coordinate sum of squares, nonnegativity and finite Cauchy-Schwarz.',
    'LogisticCurvature': 'Bounds for stated candidate Q; this module alone does not identify an objective derivative.',
    'OriginalNumericCurvature': 'Exact Rat literal matrix norm/shape/parameter/safe-step arithmetic.',
    'ScalarSoftplus': 'Actual log/exp real scalar derivatives and stable real source-shape loss equality.',
    'DirectionalObjective': 'Actual second derivative of the real objective along every affine line equals Q.',
    'RealGradient': 'Finite sum interchange identifies the coordinate gradient with first directional derivative at zero.',
    'RealDescent': 'Actual derivatives and curvature yield Taylor upper bound and exact-real safe-step decrease.',
    'OriginalRealProfile': 'Actual Rat/List to Fin4xFin80 Real coordinate/norm/L/eta join, without an alignment premise.',
    'OriginalRealDescent': 'Original mu/eta/coordinates instantiate the exact-real safe-step decrease.',
}


def need(condition, message):
    if condition is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def read(path):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular file required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_FILE, 'bounded regular file required')
        blocks, total = [], 0
        while block := os.read(fd, 1024**2):
            total += len(block)
            need(total <= MAX_FILE, 'file grew beyond fixed read bound')
            blocks.append(block)
        signature = lambda info: tuple(getattr(info, 'st_' + key) for key in
            ('dev', 'ino', 'mode', 'nlink', 'uid', 'gid', 'size', 'mtime_ns', 'ctime_ns'))
        need(total == before.st_size and signature(before) == signature(os.fstat(fd)) == signature(path.lstat()), 'file drift during read')
        return b''.join(blocks)
    finally:
        os.close(fd)


def pin(path):
    path = Path(path)
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def bound(row):
    expected = {key: row[key] for key in ('path', 'bytes', 'sha256')}
    need(pin(row['path']) == expected, 'independent retained descriptor differs')
    return expected


def expected_numeric_source(body, numeric_raw_sha):
    def rat(value):
        need(set(value) == {'numerator', 'denominator'} and
             re.fullmatch('-?(0|[1-9][0-9]*)', value['numerator']) is not None and
             re.fullmatch('[1-9][0-9]*', value['denominator']) is not None, 'canonical exact rational numeral strings required')
        numerator, denominator = value['numerator'], value['denominator']
        return '(' + numerator + ' : Rat)' if denominator == '1' else '((' + numerator + ' : Rat) / ' + denominator + ')'
    rows = body['pair_difference_coordinates_exact']
    need(len(rows) == 4 and all(len(row) == 80 for row in rows), 'all original4x80 coordinates required')
    matrix = '[' + ',\n  '.join('[' + ', '.join(rat(value) for value in row) + ']' for row in rows) + ']'
    norms = '[' + ', '.join(rat(value) for value in body['pair_squared_norms_exact']) + ']'
    return f'''import Std
/- Exact Rat statements for all 320 embedded stored binary64 coordinates.
Numeric binding complete file SHA256: {numeric_raw_sha}
This does not formalize Python Float conversion or prove Float/libm errors. -/
set_option maxRecDepth 8192
namespace OriginalRankerCurvatureArithmetic
noncomputable def differences : List (List Rat) := {matrix}
noncomputable def squaredNorms : List Rat := {norms}
noncomputable def mu : Rat := {rat(body['native_mu_exact'])}
noncomputable def eta : Rat := {rat(body['native_eta_exact'])}
noncomputable def maxSquaredNorm : Rat := {rat(body['maximum_pair_squared_norm_exact'])}
noncomputable def meanL : Rat := {rat(body['mean_curvature_L_exact'])}
noncomputable def conservativeL : Rat := {rat(body['conservative_curvature_L_exact'])}
def squaredNorm (row : List Rat) : Rat := row.foldl (fun acc x => acc + x*x) 0
theorem original_norms_exact : differences.map squaredNorm = squaredNorms := by
  decide +kernel
theorem original_shape : differences.length = 4 ∧ differences.all (fun row => row.length == 80) = true := by
  decide +kernel
theorem original_positive_scalars : 0 < mu ∧ 0 < eta := by
  decide +kernel
theorem original_mean_bound : meanL = mu + squaredNorms.foldl (fun acc x => acc+x) 0 / 16 := by
  decide +kernel
theorem original_conservative_bound : conservativeL = mu + maxSquaredNorm / 4 ∧
    squaredNorms.all (fun value => decide (value ≤ maxSquaredNorm)) = true := by
  decide +kernel
theorem original_safe_steps : eta * meanL ≤ 1 ∧ eta * conservativeL ≤ 1 := by
  decide +kernel
end OriginalRankerCurvatureArithmetic
'''.encode()


def main():
    own = pin(Path(__file__).resolve())
    plan_path = ROOT / 'math/proof-plan.json'
    plan_pin, plan = pin(plan_path), json.loads(read(plan_path))
    numeric_path = ROOT / 'evidence/numeric-01/numeric-binding.json'
    numeric_pin, numeric_raw = pin(numeric_path), read(numeric_path)
    numeric = json.loads(numeric_raw)
    need(hashlib.sha256(wire({key: value for key, value in numeric.items() if key != 'numeric_binding_sha256'})).hexdigest() ==
         numeric['numeric_binding_sha256'], 'numeric canonical self digest differs')
    need(numeric['corpus_sha256'] == 'sha256:d4aa22b9a7bfe796c31adbcf78f9b72987549a85117b8f08534f5a06c032a3df' and
         numeric['difference_vectors_sha256'] == 'e8504c6e8004a2f2878bc79aae0af54c9541bff82df8cde670b48bdf7da03ac6' and
         numeric['pair_count'] == 4 and numeric['dimension'] == 80, 'actual original profile required')
    mapping_path = ROOT / 'math/numeric-source-mapping.json'
    mapping_pin, mapping = pin(mapping_path), json.loads(read(mapping_path))
    expected = expected_numeric_source(numeric, numeric_pin['sha256'])
    numeric_source = pin(ROOT / 'math/OriginalNumericCurvature.lean')
    need(read(numeric_source['path']) == expected and hashlib.sha256(expected).hexdigest() == numeric_source['sha256'] and
         mapping['source_sha256'] == numeric_source['sha256'] and mapping['numeric_binding_raw_sha256'] == numeric_pin['sha256'] and
         mapping['numeric_binding_sha256'] == numeric['numeric_binding_sha256'] and mapping['matrix_coordinates'] == 320,
         'all320 literal source coordinates/norms/scalars and complete source bytes must match existing numeric binding')
    paths = sorted((ROOT / 'evidence').glob('lean-*/check-result.json'))
    receipts = [(pin(path), json.loads(read(path))) for path in paths]
    positive = [(binding, body) for binding, body in receipts if body.get('status') == 'passed' and body.get('expected_success') is True]
    negative = [(binding, body) for binding, body in receipts if body.get('status') == 'rejected' and body.get('expected_success') is False]
    inconclusive = [(binding, body) for binding, body in receipts if body.get('status') == 'inconclusive']
    need(len(receipts) == 19 and len(positive) == 10 and len(negative) == 1 and len(inconclusive) == 8 and
         all(type(body.get('native_invocations')) is int and body['native_invocations'] == 1 for _, body in receipts), 'actual19-call census required')
    modules = {}
    for receipt, check in positive:
        need(check['returncode'] == 0 and check['matches_expectation'] is True and check['output_truncated'] is False and
             check['artifact_anomalies'] == [] and check['axiom_report_error'] is None and
             check['direct_imports_and_implicit_Init_in_frozen_registry'] is True and check['workspace_cleaned'] is True,
             'actual fully qualified native positive required')
        module = Path(check['source']['path']).stem
        need(module in MODULE_ROLES and module not in modules, 'unique actual module required')
        source = bound(check['source'])
        current = pin(ROOT / 'math' / (module + '.lean'))
        need((source['bytes'], source['sha256']) == (current['bytes'], current['sha256']), 'current source differs from checked source')
        augmented = bound(check['augmented_source'])
        objects = []
        for row in check['compiled_artifacts']:
            need(row['complete'] is True, 'complete raw module object required')
            objects.append(bound(row))
        need(objects and Path(objects[0]['path']).name == module + '.olean', 'complete module main required')
        queried = check['theorem_axiom_output']
        need(queried and all(set(row['axioms']) <= ALLOWED_AXIOMS and row['report_occurrences'] > 0 for row in queried), 'standard-only actual axiom registry required')
        retained = None
        if check['schema'].endswith('@2'):
            need(check['reconstruction_validation_error'] is None and check['reconstruction_validation']['status'] == 'passed' and
                 check['reconstruction_validation']['manifest_complete'] is True and check['reconstruction_validation']['exact_chunk_population'] is True,
                 'actual complete bounded-chunk readback required')
            retained = {'manifest': bound(check['retention_manifest']),
                'chunks': [bound(row) for row in check['retained_chunk_artifacts']],
                'profile': check['retention_profile'], 'profile_sha256': check['retention_profile_sha256'],
                'validation': check['reconstruction_validation']}
        env_pin = bound(check['environment_manifest'])
        env = json.loads(read(env_pin['path']))
        need(env['mathlib_revision'] == '5ed2965256430c3649e86755f9576b54eca72435', 'fixed official Mathlib revision required')
        owned_path = Path(receipt['path']).parent / 'closed.json'
        owned = json.loads(read(owned_path))
        need(owned['root_release_returned'] is True and owned['cleanup_errors'] == [] and owned['primary_error'] is None and
             owned['final_resource_state']['active_lease_count'] == 0 and owned['old348_protected4_prior203_unchanged'] is True,
             'actual root closure/drain/old-guard receipts required')
        lines = read(current['path']).decode().splitlines()
        declarations = [{'name': match.group(2), 'line': number} for number, line in enumerate(lines, 1)
            if (match := re.match(r'^(?:(?:noncomputable) )?(def|theorem) ([A-Za-z0-9_]+)', line))]
        modules[module] = {'role': MODULE_ROLES[module], 'source': current, 'checked_source': source,
            'augmented_checked_source': augmented, 'native_receipt': receipt, 'native_elapsed_seconds': check['native_elapsed_seconds'],
            'owned_closure': pin(owned_path), 'environment_manifest': env_pin, 'native_bounds': check['native_bounds'],
            'compiled_artifacts': objects, 'retention': retained, 'queried_axioms': queried,
            'source_declaration_line_roles': declarations, 'registered_local_imports': env.get('local_checked_modules', [])}
    need(set(modules) == set(MODULE_ROLES), 'all ten qualified module stages required')
    for module, row in modules.items():
        for local in row['registered_local_imports']:
            target = modules[local['module']]
            need(local['qualification'] == target['native_receipt'] and local['environment'] == target['environment_manifest'],
                 'fresh checked import module must bind the same complete source/receipt/environment chain')
    neg_pin, neg = negative[0]
    need(neg['returncode'] == 1 and neg['matches_expectation'] is True and neg['output_truncated'] is False and
         re.search(r'proposition\s+False\s+is false', neg['stdout']) is not None and neg['compiled_artifacts'] == [],
         'genuine closed False rejection required')
    history = []
    for binding, check in receipts:
        history.append({'receipt': binding, 'status': check['status'], 'returncode': check['returncode'],
            'matches_expectation': check['matches_expectation'], 'source': bound(check['source']),
            'retained_complete_compiled_objects': len([row for row in check['compiled_artifacts'] if row.get('complete') is True]),
            'diagnostic_stdout_sha256': hashlib.sha256(check['stdout'].encode()).hexdigest(),
            'reconstruction_validation_error': check.get('reconstruction_validation_error'),
            'owned_closure': pin(Path(binding['path']).parent / 'closed.json')})
    native_qualified_claims = {
        'coefficient_bounds_and_sharpness': True, 'candidate_quadratic_bounds': True,
        'actual_real_scalar_derivative': True, 'actual_real_second_directional_identity': True,
        'coordinate_first_directional_gradient_identity': True, 'real_Taylor_upper_and_safe_one_step_descent': True,
        'original_Rat_literal_and_finite_shape_norm_parameter_facts': True,
        'original_Rat_to_Real_coordinate_norm_L_step_join': True, 'original_exact_real_safe_one_step_descent': True,
    }
    result = {'schema': 'terminal-ranker-real-curvature-qualified-proof-mapping@1', 'status': 'passed_file_only_actual_qualified_mathematical_mapping',
        'review_source': own, 'source_proposal_snapshot': plan_pin, 'file_only_review': True,
        'new_native_Lean_or_solver_calls_here': 0, 'new_training_or_replay_calls_here': 0, 'new_norm_folds_or_numeric_bindings_here': 0,
        'source_and_artifact_pins_rehashed_here': True, 'dependency_bodies_rehashed_here': False,
        'scope': 'Actual root-qualified Lean mathematical statements under pinned declared dependencies, with explicit original matrix/parameter join.',
        'original_profile': plan['original_profile_binding'], 'numeric_binding': numeric_pin,
        'numeric_source_generator': pin(ROOT / 'generate_numeric_lean.py'), 'numeric_source_mapping': mapping_pin,
        'independent_numeric_literal_join': {'full_expected_source_regenerated_in_memory': True,
            'all320_coordinate_literal_strings_match': True, 'all4_norm_literal_strings_match': True,
            'mu_eta_maxNorm_meanL_conservativeL_literal_strings_match': True,
            'complete_source_bytes_and_SHA256_match': True, 'matrix_coordinates': 320,
            'expected_source_bytes': len(expected), 'expected_source_sha256': hashlib.sha256(expected).hexdigest(),
            'no_norm_recomputation_no_new_binding_no_generated_source_write': True,
            'formal_Float_to_Rat_conversion_proved': False},
        'qualified_mathematical_claims': native_qualified_claims, 'qualified_modules': modules,
        'actual_Lean_call_census': {'calls': 19, 'qualified_positive': 10, 'genuine_false_rejection': 1, 'inconclusive': 8},
        'genuine_false_control': {'receipt': neg_pin, 'source': bound(neg['source']), 'queried_counterexample_axioms': neg['theorem_axiom_output'],
            'precise_scope': 'Sharp c(0)=1/4 refutes an eighth cap; separate intentional False statement is genuinely rejected by decide +kernel. This is not a global-convergence false control.'},
        'all_native_attempt_history': history, 'all_failed_attempt_receipts_retained': True,
        'retained_failures': {'source_elaboration': ['lean-curvature-01', 'lean-curvature-02', 'lean-softplus-01', 'lean-directional-01'],
            'unchanged64KiB_single_file_truncation': ['lean-curvature-03', 'lean-coefficient-01'],
            'MappingProxy_retention_manifest_interface_failure': ['lean-coefficient-02'],
            'root_wrong_query_namespace': ['lean-original-profile-01'],
            'MappingProxy_regression_control': pin(ROOT / 'evidence/pure-tests-mappingproxy-01/closed.json')},
        'mathematical_statements': plan['statements'],
        'scope_limits': {'full_Frechet_operator_Hessian_proved': False, 'gradient_Lipschitz_operator_theorem_proved': False,
            'mu_strong_convexity_definition_theorem_proved': False, 'gradient_map_contraction_proved': False,
            'minimizer_existence_uniqueness_or_global_real_iteration_convergence_proved': False,
            'binary64_fsum_libm_uniform_error_or_error_floor_proved': False,
            'historical_execution_pin_origin_or_heldout_outcomes_proved': False,
            'original_matrix_alignment_is_a_premise': False,
            'candidate_Q_alone_is_treated_as_actual_derivative': False,
            'one_step_real_decrease_is_treated_as_native_or_global_convergence': False},
        'python_ranker_source_equivalence_proved': False, 'whole_source_runtime_equivalence_proved': False,
        'binary64_error_bound_proved': False, 'global_optimizer_convergence_proved': False,
        'global_autoencoder_convergence_proved': False, 'full_source_satisfaction': False, 'full_task_satisfaction': 'unknown',
        'all32_governing_RPI_exits': 'OPEN', 'official_benchmark_score': None,
        'proof_authority': False, 'formalization_authority': False, 'execution_authority': False,
        'completion_authority': False, 'mutation_authority': False, 'omission_authority': False, 'planner_activation': False,
        'source_snapshot_atomic_claimed': False, 'network_calls_here': 0, 'git_calls_here': 0, 'uploads_here': 0}
    # Read the key exact inputs again before writing a new independent review leaf.
    need(pin(Path(__file__).resolve()) == own and pin(plan_path) == plan_pin and pin(numeric_path) == numeric_pin and
         pin(mapping_path) == mapping_pin, 'key mapping inputs changed')
    for binding, _ in receipts:
        need(pin(binding['path']) == binding, 'retained checker receipt changed')
    for row in modules.values():
        need(pin(row['source']['path']) == row['source'] and pin(row['owned_closure']['path']) == row['owned_closure'], 'source/closure drift')
        for obj in row['compiled_artifacts']:
            bound(obj)
    with OUTPUT.open('xb') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode() + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(pin(OUTPUT), sort_keys=True))


if __name__ == '__main__':
    main()
