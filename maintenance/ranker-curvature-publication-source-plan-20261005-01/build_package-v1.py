"""Package externally sealed real-ranker proof evidence locally.

No work occurs on import. A root-owned final seal and exact observed fact policy
must be externally pinned before this source can run. Mathlib/cache dependency
bodies remain outside publication; their exact profile manifests are retained.
This publication-only profile changes no native proof or metadata limit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile
import tempfile
import types

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = WORKSPACE / 'maintenance/ranker-curvature-publication-source-plan-20261005-01'
QUALIFIER = WORKSPACE / 'qualification/codebase_ir/ranker-real-curvature-20261005-01'
HF = WORKSPACE / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
EXTERNAL_SUBTREES = (QUALIFIER / 'environment/mathlib4', QUALIFIER / 'environment/cache')
HELPERS = {
    'reader': (HF / 'successor-source-model-package-03/build_package.py',
               '8c8eab266a053115cdf0ea11a8aea5323611c2ab049ec1541383831618e385ce'),
    'archive': (HF / 'build_evidence_archive_02.py',
                'f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036'),
    'classifier': (HF / 'classify_and_prepare_public_archive_07.py',
                   'dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8'),
}
BLOCK, FILE_MAX, TOTAL_MAX, DECODE_MAX, SHARD_MAX = 1024**2, 16 * 1024**2, 320 * 1024**2, 1024**3, 256 * 1024**2
MATHLIB_REVISION = '5ed2965256430c3649e86755f9576b54eca72435'
REQUIRED_THEOREMS = {
    'RankerRealCurvature.realLogisticCoeff_bounds', 'RankerRealCurvature.realLogisticCoeff_zero',
    'RankerRealCurvature.dot_sq_le', 'OriginalRankerCurvatureArithmetic.original_norms_exact',
    'OriginalRankerCurvatureArithmetic.original_safe_steps', 'RankerRealCurvature.candidateHessianQuad_bounds',
    'RankerRealCurvature.secondDeriv_realPairLoss', 'RankerRealCurvature.secondDeriv_realObjectiveLine',
    'RankerRealCurvature.actual_secondDirectional_bounds', 'RankerRealCurvature.lineFirstDerivative_zero_eq_dot_gradient',
    'RankerRealCurvature.realGradientStep_safe_descent', 'RankerRealCurvature.originalReal_norms_exact',
    'RankerRealCurvature.originalReal_meanL_exact', 'RankerRealCurvature.originalReal_eta_le_inverse_meanL',
    'RankerRealCurvature.originalReal_actual_secondDirectional_bounds', 'RankerRealCurvature.originalReal_safe_descent',
}
SOURCE_AUTHORED_EXTRA_AXIOM_QUERY = 'RankerRealCurvature.originalReal_meanL_exact'
PROFILE = {'raw_population_max': TOTAL_MAX, 'per_file_max': FILE_MAX,
    'per_decoded_container_max': FILE_MAX, 'compressed_shard_max': SHARD_MAX,
    'aggregate_decoded_work_max': DECODE_MAX, 'wall_seconds': 180,
    'members_max': 10000, 'depth_max': 6, 'zstd_arguments': ['-T1', '-3'],
    'member_readback_profile': 'same_first_decoded_tar_and_member_streams@1',
    'duplicate_verification_decoder_invocations': 0,
    'authorization_scope': 'explicit root publication-only320MiB raw/1GiB decoded; native limits unchanged',
    'authorization_reason': 'root measured277398309 bytes/1212 owned leaves; retain all failures and22 complete dependency profiles'}
BOUNDARIES = {'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN',
    'python_ranker_source_equivalence_proved': False, 'binary64_error_bound_proved': False,
    'historical_execution_origin_proved': False, 'global_optimizer_convergence_proved': False,
    'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
    'planner_activation': False, 'official_benchmark_score': None, 'all_failed_attempts_retained': True,
    'new_public_fits': 0, 'new_ranker_training_trace_replays': 0}


def need(condition, message):
    if condition is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def descriptor(value):
    need(type(value) is dict and set(value) == {'path', 'bytes', 'sha256'} and
         type(value['path']) is str and type(value['bytes']) is int and 0 <= value['bytes'] <= FILE_MAX and
         type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']) is not None,
         'exact bounded file descriptor required')
    path = Path(value['path'])
    need(path.is_absolute() and path.resolve(strict=True) == path, 'canonical pinned input required')
    return path


def load_source(path, expected, name):
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical frozen helper required')
    raw = path.read_bytes()
    need(len(raw) <= FILE_MAX and hashlib.sha256(raw).hexdigest() == expected, 'frozen helper source differs')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def pointer(value, path):
    need(type(path) is str and (path == '' or path.startswith('/')), 'JSON pointer required')
    for field in path.strip('/').split('/') if path else []:
        field = field.replace('~1', '/').replace('~0', '~')
        value = value[int(field)] if isinstance(value, list) else value[field]
    return value


def allowed_addition(path):
    if path.is_relative_to(QUALIFIER):
        return not any(path.is_relative_to(root) for root in EXTERNAL_SUBTREES)
    relative = path.relative_to(WORKSPACE)
    return len(relative.parts) >= 3 and (
        relative.parts[0] == 'maintenance' and relative.parts[1].startswith('ranker-curvature-') or
        relative.parts[:2] == ('qualification', 'codebase_ir') and relative.parts[2].startswith('ranker-real-curvature-'))


def validate_semantics(closure, documents, read_pin):
    """Bind complete actual checks and advisory joins; never invoke a prover."""
    review = documents['qualified_review']
    need(review.get('schema') == 'ranker-real-curvature-closed-qualification-review@1' and
         review.get('status') == 'passed', 'exact final qualified review schema/status required')
    roles = closure.get('semantic_roles')
    required = {'positive_native_checks', 'negative_native_checks', 'original_numeric_binding',
                'qualified_cache_acceptances', 'native_metadata_readback', 'failure_and_call_accounting'}
    need(type(roles) is dict and set(roles) == required, 'complete fixed actual semantic roles required')
    names = []
    for key in ('positive_native_checks', 'negative_native_checks', 'qualified_cache_acceptances'):
        need(type(roles[key]) is list and 0 < len(roles[key]) <= 64 and len(set(roles[key])) == len(roles[key]),
             'nonempty unique actual positive/false-control/cache roles required')
        names.extend(roles[key])
    for key in ('original_numeric_binding', 'native_metadata_readback', 'failure_and_call_accounting'):
        need(type(roles[key]) is str, 'exact actual document role required')
        names.append(roles[key])
    gated = {fact['document'] for fact in closure['required_facts']}
    need(all(type(name) is str and name in documents and name in gated for name in names),
         'every actual semantic role must be pinned and explicitly fact-gated')
    native, source_authored_extra_queries = {}, set()
    bounds = {'timeout_seconds': 20, 'cpu_seconds': 20, 'max_input_bytes': 262144,
              'max_output_bytes': 65536, 'max_workspace_bytes': 16777216}
    for name in [*roles['positive_native_checks'], *roles['negative_native_checks']]:
        check = documents[name]
        need(check.get('schema') in ('ranker-real-curvature-bounded-analytic-lean-check@1',
                                    'ranker-real-curvature-bounded-analytic-lean-check@2') and
             wire(check.get('native_bounds')) == wire(bounds) and type(check.get('native_invocations')) is int and
             check['native_invocations'] == 1 and check.get('workspace_cleaned') is True and
             all(check.get(key) is False for key in ('timed_out', 'cancelled', 'unavailable', 'resource_exhausted',
                 'output_truncated', 'workspace_limit_exceeded')) and check.get('artifact_anomalies') == [] and
             check.get('axiom_report_error') is None and check.get('post_call_binding_error') is None and
             check.get('receipt_retention_overflow', False) is False, 'clean actual native check and unchanged caps required')
        need(all(check.get(key) is True for key in ('proof_source_in_frozen_per_job_environment',
                 'direct_imports_and_implicit_Init_in_frozen_registry', 'root_lease_owned_by_caller',
                 'outer120s_and_frozen_project_import_guard_owned_by_caller')) and
             check.get('environment_actual_runtime_open_trace_claimed') is False, 'actual frozen source/import/admission guards required')
        need(all(check.get(key) is False for key in ('proof_authority', 'execution_authority', 'completion_authority',
                 'planner_activation', 'python_ranker_source_equivalence_proved', 'binary64_error_bound_proved',
                 'historical_execution_origin_proved', 'optimizer_convergence_proved')) and
             check.get('full_task_satisfaction') == 'unknown' and check.get('all32_governing_RPI_exits') == 'OPEN' and
             check.get('official_benchmark_score') is None, 'native check cannot grant source/Float/global/task/operational authority')
        for field in ('source', 'augmented_source', 'environment_manifest'):
            row = check[field]
            need(read_pin(descriptor(row)) == row, 'actual checked source/profile pin differs')
        if name in roles['negative_native_checks']:
            need(check.get('status') == 'rejected' and check.get('expected_success') is False and
                 check.get('matches_expectation') is True and type(check.get('returncode')) is int and check['returncode'] != 0 and
                 type(check.get('stdout')) is str and check['stdout'].count('error:') == 1 and check.get('stderr') == '' and
                 'Tactic `decide` proved that the proposition' in check['stdout'] and
                 re.search(r'proposition\s+False\s+is false', check['stdout']) is not None,
                 'genuine kernel decide-false control required; generic failures cannot qualify')
            continue
        need(check.get('status') == 'passed' and check.get('expected_success') is True and check.get('matches_expectation') is True and
             type(check.get('returncode')) is int and check['returncode'] == 0, 'actual positive kernel check required')
        registry = check.get('theorem_axiom_output')
        need(type(registry) is list and 0 < len(registry) <= 256 and
             len({row['theorem'] for row in registry}) == len(registry), 'complete unique theorem query registry required')
        for row in registry:
            need(type(row.get('theorem')) is str and type(row.get('axioms')) is list and
                 len(set(row['axioms'])) == len(row['axioms']) and set(row['axioms']) <= {'propext', 'Classical.choice', 'Quot.sound'} and
                 type(row.get('report_occurrences')) is int and row['report_occurrences'] > 0,
                 'actual standard-only queried theorem axioms required')
        # This declared theorem was printed by the actual frozen Lean source,
        # outside the checker's parsed fixed registry. Verify its actual output
        # separately; do not claim it was an appended checker registry query.
        label = re.escape("'" + SOURCE_AUTHORED_EXTRA_AXIOM_QUERY + "'")
        nonempty = re.findall(label + r' depends on axioms: \[([^\]]*)\]', check['stdout'])
        empty = len(re.findall(label + r' does not depend on any axioms', check['stdout']))
        if nonempty or empty:
            reports = [[item.strip() for item in report.split(',') if item.strip()] for report in nonempty] + [[]] * empty
            need(all(report == reports[0] for report in reports) and len(set(reports[0])) == len(reports[0]) and
                 set(reports[0]) <= {'propext', 'Classical.choice', 'Quot.sound'},
                 'additional actual source-authored axiom report must be consistent and standard-only')
            source_authored_extra_queries.add(SOURCE_AUTHORED_EXTRA_AXIOM_QUERY)
        objects = check.get('compiled_artifacts')
        stem = Path(check['augmented_source']['path']).stem
        allowed = [stem + suffix for suffix in ('.olean', '.olean.private', '.olean.server', '.ir')]
        need(type(objects) is list and 0 < len(objects) <= 4 and Path(objects[0]['path']).name == allowed[0] and
             len({row['path'] for row in objects}) == len(objects), 'complete actual main object and companions required')
        for row in objects:
            base = {key: row[key] for key in ('path', 'bytes', 'sha256')}
            maximum = 3997696 if check['schema'].endswith('@2') else 65536
            need(row.get('complete') is True and type(row['bytes']) is int and 0 < row['bytes'] <= maximum and
                 Path(row['path']).name in allowed and read_pin(descriptor(base)) == base,
                 'complete actual raw compiled object binding required')
        if check['schema'].endswith('@2'):
            need(check.get('retention_format') == 'bounded_lean_chunks@1' and check.get('reconstruction_validation_error') is None and
                 check.get('reconstruction_validation', {}).get('status') == 'passed' and
                 check['reconstruction_validation'].get('manifest_complete') is True and
                 check['reconstruction_validation'].get('exact_chunk_population') is True and
                 type(check.get('native_lean_invocations')) is int and check['native_lean_invocations'] == 1 and
                 type(check.get('native_lean_returncode')) is int and check['native_lean_returncode'] == 0,
                 'actual complete bounded-chunk reconstruction required')
        check_pin = hashlib.sha256(wire(check)).hexdigest()
        need(check_pin not in native, 'one actual positive receipt cannot be counted through duplicate aliases')
        native[check_pin] = (check, {row['theorem'] for row in registry})
    need(REQUIRED_THEOREMS <= set().union(*(queried for _, queried in native.values())) | source_authored_extra_queries,
         'complete actual coefficient/geometry/numeric/derivative/gradient/original-real-descent theorem chain required')
    numeric = documents[roles['original_numeric_binding']]
    need(numeric.get('schema') == 'terminal-ranker-original-real-curvature-numeric-binding@1' and
         numeric.get('status') == 'exact_original_profile_candidate_curvature_constants' and numeric.get('dimension') == 80 and
         numeric.get('pair_count') == 4 and numeric.get('corpus_sha256') == 'sha256:d4aa22b9a7bfe796c31adbcf78f9b72987549a85117b8f08534f5a06c032a3df' and
         all(numeric.get(key) is True for key in ('exact_positive_eta', 'exact_positive_mu', 'exact_eta_times_conservative_L_le_one',
             'exact_eta_times_mean_L_le_one', 'candidate_curvature_numeric_inequalities_checked', 'prior_trace_receipt_consumed_passively')) and
         numeric.get('prior_trace_replayed_or_revalidated_here') is False, 'exact original Rat-to-Real numeric binding required')
    numeric_pin = hashlib.sha256(wire(numeric)).hexdigest()
    cache_keys = set()
    for name in roles['qualified_cache_acceptances']:
        entry = documents[name]
        need(entry.get('schema') == 'terminal-ranker-real-curvature-proof-cache-entry@2' and
             entry.get('status') == 'qualified_advisory_real_model_theorem' and entry.get('native_check_sha256') in native,
             'actual admitted exact-dimension advisory theorem cache entry required')
        need(type(entry.get('cache_key_sha256')) is str and re.fullmatch('[0-9a-f]{64}', entry['cache_key_sha256']) is not None and
             entry['cache_key_sha256'] not in cache_keys, 'one cache entry cannot be counted through duplicate aliases')
        cache_keys.add(entry['cache_key_sha256'])
        check, queried = native[entry['native_check_sha256']]
        dimensions, theorem_row = entry['cache_dimensions'], entry['theorem_row']
        need(dimensions.get('theorem') in queried and dimensions.get('proof_source_sha256') == check['source']['sha256'] and
             dimensions.get('environment_manifest_sha256') == check['environment_manifest']['sha256'] and
             dimensions.get('numeric_binding_sha256') == numeric_pin and
             dimensions.get('corpus_sha256') == numeric['corpus_sha256'] and
             dimensions.get('feature_profile_sha256') == numeric['feature_profile_sha256'] and
             dimensions.get('difference_vectors_sha256') == numeric['difference_vectors_sha256'] and
             theorem_row.get('theorem') == dimensions['theorem'] and theorem_row.get('advisory_only') is True and
             theorem_row.get('status') == 'kernel_real_statement_bound' and
             type(entry.get('native_prover_calls_here')) is int and entry['native_prover_calls_here'] == 0 and
             entry.get('external_pin_origin_authenticated_here') is False,
             'cache theorem/source/environment/original numeric canonical bindings differ')
        for row in (entry, theorem_row):
            need(all(row.get(key) is False for key in ('proof_authority', 'execution_authority', 'completion_authority',
                     'planner_activation', 'semantic_alignment_verified', 'source_semantics_verified',
                     'whole_source_runtime_equivalence_proved', 'binary64_error_bound_proved', 'global_optimizer_convergence_proved')) and
                 row.get('full_task_satisfaction') == 'unknown' and row.get('all32_governing_RPI_exits') == 'OPEN' and
                 row.get('official_benchmark_score') is None, 'cache entries remain strictly advisory and grant no source/Float/global/task authority')
    need(any(documents[name]['cache_dimensions']['theorem'] == 'RankerRealCurvature.originalReal_safe_descent'
             for name in roles['qualified_cache_acceptances']), 'original exact-real safe-descent theorem cache binding required')
    readback = documents[roles['native_metadata_readback']]
    need(type(readback.get('fresh_process_readback')) is dict and readback['fresh_process_readback'].get('verified') is True,
         'actual fresh-process metadata readback dictionary verified true required')
    accounting = documents[roles['failure_and_call_accounting']]
    need(type(accounting.get('native_lean_calls')) is int and accounting['native_lean_calls'] > 0 and
         accounting.get('all_failed_attempts_retained') is True, 'exact actual proof-call accounting and retained failures required')
    return {'positive_native_checks': len(roles['positive_native_checks']), 'genuine_negative_native_checks': len(roles['negative_native_checks']),
            'qualified_advisory_cache_entries': len(roles['qualified_cache_acceptances']), 'actual_native_lean_calls': accounting['native_lean_calls'],
            'additional_source_authored_axiom_queries_verified_separately': sorted(source_authored_extra_queries),
            'additional_source_authored_queries_claimed_as_checker_parsed_registry': False}


def inventory(reader, additions, locks):
    """Never descend into the two explicitly excluded external dependencies."""
    files, exclusions, directories = [], [], []
    def visit(path):
        info = path.lstat()
        need(path.resolve(strict=True) == path and not stat.S_ISLNK(info.st_mode), 'inventory symlink/referral refused')
        if path in EXTERNAL_SUBTREES:
            need(stat.S_ISDIR(info.st_mode), 'external dependency subtree must be a directory')
            exclusions.append({'path': str(path), 'kind': 'external_dependency_subtree',
                'reason': 'exact retained dependency profiles and official source revision; raw bodies not published',
                'stat': reader.signature(info)})
        elif stat.S_ISDIR(info.st_mode):
            directories.append({'path': str(path), 'stat': reader.signature(info)})
            for child in sorted(path.iterdir(), key=lambda p: os.fsencode(p.name)):
                visit(child)
        elif str(path) in locks:
            need(stat.S_ISREG(info.st_mode) and info.st_size == 0, 'explicit sealed runtime lock must be empty')
            exclusions.append({'path': str(path), 'kind': 'transient_lock',
                'reason': 'exact sealed closed-runtime zero-byte lock', 'stat': reader.signature(info)})
        else:
            need(stat.S_ISREG(info.st_mode), 'unsupported selected node')
            files.append(path)
    visit(QUALIFIER)
    for row in additions:
        path = Path(row['path'])
        if not path.is_relative_to(QUALIFIER):
            visit(path)
    need(len(files) <= 10000 and len(set(files)) == len(files), 'unique bounded selected population required')
    return sorted(files, key=lambda p: os.fsencode(str(p.relative_to(WORKSPACE)))), exclusions, directories


def check_closed_inputs(reader, path, expected):
    need(type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected) is not None,
         'independent lowercase closed-inputs SHA256 required')
    binding = reader.pin(path)
    need(binding['sha256'] == expected, 'externally pinned closed inputs differ')
    body = json.loads(reader.read_regular(path)[0])
    need(body.get('schema') == 'ranker-curvature-publication-closed-inputs@1' and
         body.get('source_and_artifacts_quiet') is True and body.get('scope_root') == str(QUALIFIER) and
         body.get('excluded_dependency_subtrees') == [str(p) for p in EXTERNAL_SUBTREES] and
         wire(body.get('publication_profile')) == wire(PROFILE), 'exact quiet owned scope and publication profile required')
    docs = body.get('documents')
    need(type(docs) is dict and {'file_seal', 'qualified_review'} <= set(docs) and len(docs) <= 1000,
         'sealed qualification and final review documents required')
    documents = {}
    for name, row in docs.items():
        selected = descriptor(row)
        need(allowed_addition(selected) and reader.pin(selected) == row, 'closed owned document pin differs')
        documents[name] = json.loads(reader.read_regular(selected)[0])
    policy_path = descriptor(body['semantic_policy'])
    need(policy_path == ROOT / 'required-facts.json' and reader.pin(policy_path) == body['semantic_policy'],
         'exact root-frozen observed policy required')
    facts = json.loads(reader.read_regular(policy_path)[0])
    need(type(facts) is list and 0 < len(facts) <= 10000 and wire(facts) == wire(body.get('required_facts')),
         'exact nonempty observed semantic policy required')
    required_boundary_facts = []
    for key, value in BOUNDARIES.items():
        fact = {'document': 'qualified_review', 'pointer': '/' + key, 'equals': value}
        required_boundary_facts.append(wire(fact))
    need(all(fact in [wire(row) for row in facts] for fact in required_boundary_facts),
         'all source/Float/global/task/origin/authority and retained-failure boundaries required')
    for fact in facts:
        need(type(fact) is dict and set(fact) == {'document', 'pointer', 'equals'} and fact['document'] in documents,
             'exact declared observed fact required')
        need(wire(pointer(documents[fact['document']], fact['pointer'])) == wire(fact['equals']),
             'actual qualification outcome differs from frozen policy')
    validate_semantics(body, documents, reader.pin)
    additions = body.get('explicit_additions')
    need(type(additions) is list and len(additions) <= 1000 and len({row['path'] for row in additions}) == len(additions),
         'unique fixed explicit additions required')
    additions_by_path = {}
    for row in additions:
        selected = descriptor(row)
        need(allowed_addition(selected) and reader.pin(selected) == row, 'explicit new addition pin differs')
        additions_by_path[str(selected)] = row
    for selected in (ROOT / 'build_package.py', ROOT / 'review_package.py', ROOT / 'freeze_inputs.py',
                     ROOT / 'publication-profile-authorization.json', ROOT / 'plan.json', policy_path):
        need(additions_by_path.get(str(selected)) == reader.pin(selected), 'all final publication sources/plan/policy selected')
    dependencies = body.get('external_dependencies')
    need(type(dependencies) is dict and dependencies.get('mathlib_revision') == MATHLIB_REVISION and
         dependencies.get('official_repository') == 'https://github.com/leanprover-community/mathlib4' and
         dependencies.get('raw_dependency_bodies_published') is False and
         type(dependencies.get('environment_manifests')) is list and len(dependencies['environment_manifests']) > 0 and
         type(dependencies.get('reproduction_notes')) is str and len(dependencies['reproduction_notes']) > 0,
         'exact dependency profile/reproduction declaration required')
    for row in dependencies['environment_manifests']:
        selected = descriptor(row)
        need(selected.is_relative_to(QUALIFIER) and not any(selected.is_relative_to(root) for root in EXTERNAL_SUBTREES)
             and reader.pin(selected) == row, 'retained exact dependency profile differs')
    need(documents['file_seal']['review'] == docs['qualified_review'], 'seal must bind final qualified review')
    return body, binding, documents


def verify_seal(reader, body, documents, files, exclusions):
    sealed = documents['file_seal']['files']
    count, total = body.get('expected_sealed_file_count'), body.get('expected_sealed_file_bytes')
    need(type(count) is int and 0 < count <= 10000 and type(total) is int and 0 <= total <= TOTAL_MAX and
         type(sealed) is list and len(sealed) == len({row['path'] for row in sealed}) == count and
         sum(row['bytes'] for row in sealed) == total, 'exact final seal count and bytes required')
    need(hashlib.sha256(wire(sealed)).hexdigest() == documents['file_seal']['file_inventory_sha256'],
         'canonical ASCII no-newline seal inventory digest differs')
    locks = body.get('excluded_zero_byte_locks')
    need(type(locks) is list and len(set(locks)) == len(locks) and all(type(p) is str for p in locks),
         'exact declared zero-byte lock paths required')
    lock_set = set(locks)
    sealed_by_path = {}
    for row in sealed:
        selected = descriptor(row)
        need(selected.is_relative_to(QUALIFIER) and not any(selected.is_relative_to(root) for root in EXTERNAL_SUBTREES)
             and reader.pin(selected) == row, 'sealed owned leaf changed')
        need(str(selected) not in lock_set or row['bytes'] == 0, 'sealed runtime lock changed')
        sealed_by_path[str(selected)] = row
    need(lock_set <= set(sealed_by_path), 'all excluded locks must remain sealed')
    expected_excluded = {str(root): 'external_dependency_subtree' for root in EXTERNAL_SUBTREES}
    expected_excluded.update({p: 'transient_lock' for p in lock_set})
    need(len(exclusions) == len(expected_excluded) and {p['path']: p['kind'] for p in exclusions} == expected_excluded,
         'only exact two dependency roots and sealed zero-byte locks excluded')
    additions = body['explicit_additions']
    expected = (set(sealed_by_path) - lock_set) | {row['path'] for row in additions}
    need({str(p) for p in files} == expected and len(files) == len(expected),
         'full owned seal plus fixed additions required; failed attempts cannot disappear')
    selected_pins = {str(p): reader.pin(p) for p in files}
    for row in body['documents'].values():
        need(selected_pins.get(row['path']) == row, 'every qualification outcome document must be selected')
    for row in body['external_dependencies']['environment_manifests']:
        need(selected_pins.get(row['path']) == row, 'exact dependency profile manifests must be selected')
    return {'sealed_file_count_rehashed': count, 'sealed_file_bytes_rehashed': total,
            'sealed_lock_bindings_rehashed': len(lock_set), 'sealed_durable_leaves_selected': count - len(lock_set),
            'explicit_additions': len(additions), 'semantic_fact_count_verified': len(body['required_facts'])}


def verify_final_selection(reader, body, files, exclusions, directories):
    selected_path = descriptor(body['final_selection'])
    need(selected_path == ROOT / 'final-selection.json' and reader.pin(selected_path) == body['final_selection'],
         'externally frozen final selection differs')
    selected = json.loads(reader.read_regular(selected_path)[0])
    actual = [{**reader.pin(path), 'stat': reader.signature(path.lstat())} for path in files]
    need(selected.get('schema') == 'ranker-curvature-publication-final-selection@1' and
         selected.get('files') == actual and selected.get('exclusions') == exclusions and selected.get('directories') == directories,
         'full selected inventory/hash/stat/exclusions differ')
    return selected


def reader_controls(reader, output):
    control = output / 'reader-control'
    control.mkdir(mode=0o700)
    regular, link = control / 'regular.bin', control / 'link.bin'
    regular.write_bytes(b'bounded frozen reader control\n')
    link.symlink_to(regular)
    positive = reader.read_regular(regular)[0] == b'bounded frozen reader control\n'
    rejected = False
    try:
        reader.read_regular(link)
    except (AssertionError, ValueError, OSError):
        rejected = True
    need(positive and rejected, 'frozen regular-reader positive/symlink false controls must pass')
    link.unlink()
    regular.unlink()
    control.rmdir()
    return {'regular_positive_exact_bytes': True, 'symlink_negative_genuinely_refused': True,
            'control_population': 2, 'cleanup_verified': True, 'native_proof_jobs': 0}


def tar_item(row):
    item = tarfile.TarInfo(row['path'])
    item.size, item.mode = row['bytes'], 0o644
    item.uid = item.gid = item.mtime = 0
    item.uname = item.gname = ''
    return item


def split_shards(rows):
    groups, current, count = [], [], 0
    complete = lambda n: ((n + 1024 + tarfile.RECORDSIZE - 1) // tarfile.RECORDSIZE) * tarfile.RECORDSIZE
    for row in rows:
        needed = len(tar_item(row).tobuf(format=tarfile.GNU_FORMAT)) + ((row['bytes'] + 511) // 512) * 512
        need(complete(needed) <= FILE_MAX, 'one member cannot fit complete decoded16MiB tar')
        if current and complete(count + needed) > FILE_MAX:
            groups.append(current)
            current, count = [], 0
        current.append(row)
        count += needed
    if current:
        groups.append(current)
    return groups


def inspect_complete_shard(classifier, scanner, budget, staging, shard, tar_pin, rows):
    """Verify hashes inside the frozen classifier's first decoded traversal.

    Its existing recursive scan still charges every first decoded tar byte and
    every decoded member byte. Hashing piggybacks on those same stream reads;
    no second decoder, omitted member, or decoded-budget exemption is used.
    Only the outer, expected tar dispatch is extended with exact identities.
    All member/nested-container scans retain the pinned classifier algorithm.
    """
    class MemberRead:
        def __init__(self, stream):
            self.stream, self.digest, self.count = stream, hashlib.sha256(), 0
        def read(self, size):
            block = self.stream.read(size)
            self.count += len(block)
            need(self.count <= FILE_MAX, 'complete member byte bound exceeded')
            self.digest.update(block)
            return block

    class CompleteShardClassifier(classifier.Classifier):
        tar_verified = False
        decoded_tar_bytes = 0
        decoded_member_bytes = 0
        def inspect(self, stream, depth=0, already_decoded=False):
            if depth != 1 or already_decoded is not True:
                return super().inspect(stream, depth, already_decoded)
            need(not self.tar_verified, 'one first outer decoded tar required')
            self.budget.check()
            need(depth <= self.budget.depth_max, 'recursive classifier depth bound exceeded')
            stream.seek(0)
            prefix = stream.read(512)
            stream.seek(0)
            need(self.format(prefix) == 'tar', 'first outer decoded body must be the expected GNU tar')
            tail, count, digest = b'', 0, hashlib.sha256()
            while block := stream.read(BLOCK):
                count += len(block)
                self.budget.charge(len(block), count)
                self.hits.update(self.hits_in(tail + block))
                tail = (tail + block)[-65536:]
                digest.update(block)
            need(count == tar_pin['bytes'] <= FILE_MAX and digest.hexdigest() == tar_pin['sha256'],
                 'complete first decoded tar bytes differ')
            self.counts['streams'] += 1
            self.counts['raw_stream_bytes'] += count
            self.counts['containers'] += 1
            stream.seek(0)
            index, member_bytes = 0, 0
            with tarfile.open(fileobj=classifier.BoundedParserReads(stream), mode='r:') as archive:
                for member in archive:
                    self.budget.member()
                    self.hits.update(self.hits_in(os.fsencode(member.name)))
                    need(index < len(rows), 'unexpected additional decoded tar member')
                    row = rows[index]
                    need(member.isfile() and not member.issym() and not member.islnk() and member.name == row['path'] and
                         member.size == row['bytes'] and member.mode == 0o644 and
                         member.uid == member.gid == member.mtime == 0 and member.uname == member.gname == '',
                         'complete first decoded member identity differs')
                    source = archive.extractfile(member)
                    need(source is not None, 'complete decoded member body absent')
                    with source, tempfile.TemporaryFile(dir=self.temporary) as payload:
                        observed = MemberRead(source)
                        self.copy(observed, payload)
                        need(observed.count == row['bytes'] and observed.digest.hexdigest() == row['sha256'],
                             'complete first decoded member bytes differ')
                        member_bytes += observed.count
                        payload.seek(0)
                        super().inspect(payload, depth + 1, True)
                    index += 1
            need(index == len(rows), 'all expected first decoded members required')
            self.tar_verified, self.decoded_tar_bytes, self.decoded_member_bytes = True, count, member_bytes

    inspection = CompleteShardClassifier(scanner, budget, staging)
    with shard.open('rb') as stream:
        inspection.inspect(stream)
    need(inspection.tar_verified and not inspection.hits, 'complete first-spool member verification/credential veto required')
    return inspection


def build(args):
    need(__debug__, 'frozen reader assertions must remain enabled')
    reader = load_source(*HELPERS['reader'], 'ranker_curvature_frozen_reader')
    builder_pin = reader.pin(Path(__file__).resolve())
    body, closure_pin, documents = check_closed_inputs(reader, args.closed_inputs, args.expected_closed_inputs_sha256)
    output = args.output
    need(output.is_absolute() and output.resolve() == output and not output.exists() and
         output.parent.is_dir() and output.is_relative_to(WORKSPACE / 'maintenance') and
         output.name.startswith('ranker-curvature-publication-package-'), 'new owned curvature maintenance output required')
    files, exclusions, directories = inventory(reader, body['explicit_additions'], body['excluded_zero_byte_locks'])
    verify_final_selection(reader, body, files, exclusions, directories)
    seal_before = verify_seal(reader, body, documents, files, exclusions)
    archive = load_source(*HELPERS['archive'], 'ranker_curvature_frozen_archive')
    classifier = load_source(*HELPERS['classifier'], 'ranker_curvature_frozen_classifier')
    scanner = archive.Scanner()
    scanner.patterns = [(name, pattern) for name, pattern in archive.PATTERNS if name != 'private_key_pem']
    budget = classifier.Budget(seconds=180, decoded_bytes=DECODE_MAX, container_bytes=FILE_MAX, members=10000, depth=6)
    output.mkdir(mode=0o700)
    args.owned_output = True
    reader.write(output / 'started.json', {'schema': 'ranker-curvature-local-package-attempt@1',
        'closed_inputs': closure_pin, 'builder': builder_pin, 'status': 'started', 'remote_mutations': 0})
    controls = reader_controls(reader, output)
    staging, public = output / 'private-staging', output / 'package'
    staging.mkdir(mode=0o700)
    public.mkdir(mode=0o700)
    rows, sources, total = [], {}, 0
    for index, source in enumerate(files):
        budget.check()
        raw, signature = reader.read_regular(source)
        total += len(raw)
        need(total <= TOTAL_MAX, 'explicit publication-only320MiB raw population exceeded')
        target = staging / ('file-%06d' % index)
        with target.open('xb') as stream:
            stream.write(raw)
        inspection = classifier.Classifier(scanner, budget, staging)
        with target.open('rb') as stream:
            inspection.inspect(stream)
        need(not inspection.hits, 'credential-pattern or exact cached-value veto refused export')
        name = str(source.relative_to(WORKSPACE))
        rows.append({'path': name, 'source_path': str(source), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(), 'source_stat': signature,
            'scan_counts': dict(inspection.counts), 'scan_hits': []})
        sources[name] = target
    zstd, shards, first_tar_bytes, first_member_bytes = Path('/usr/bin/zstd'), [], 0, 0
    zstd_pin = reader.pin(zstd)
    for index, group in enumerate(split_shards(rows)):
        budget.check()
        tarpath = staging / ('data-%06d.tar' % index)
        with tarfile.open(tarpath, 'w', format=tarfile.GNU_FORMAT) as sink:
            for row in group:
                with sources[row['path']].open('rb') as stream:
                    sink.addfile(tar_item(row), stream)
        tar_pin = reader.pin(tarpath)
        need(tar_pin['bytes'] <= FILE_MAX, 'complete decoded tar exceeds16MiB container')
        shard = public / ('data-%06d.tar.zst' % index)
        with shard.open('xb') as stream:
            subprocess.run([str(zstd), '-T1', '-3', '--quiet', '--stdout', str(tarpath)],
                           stdout=stream, stderr=subprocess.PIPE, check=True, timeout=60)
        need(shard.stat().st_size <= SHARD_MAX and reader.pin(zstd) == zstd_pin, 'compressed shard/tool pin differs')
        inspection = inspect_complete_shard(classifier, scanner, budget, staging, shard, tar_pin, group)
        first_tar_bytes += inspection.decoded_tar_bytes
        first_member_bytes += inspection.decoded_member_bytes
        shards.append({**reader.pin(shard), 'archive': shard.name, 'decoded_tar_bytes': tar_pin['bytes'],
            'decoded_tar_sha256': tar_pin['sha256'], 'members': len(group), 'scan_counts': dict(inspection.counts),
            'scan_hits': [], 'decoded_per_file_readback_verified': True})
        for row in group:
            row.update(archive=shard.name, member=row['path'])
    need(inventory(reader, body['explicit_additions'], body['excluded_zero_byte_locks']) ==
         (files, exclusions, directories), 'full selected population/stat changed during packaging')
    verify_final_selection(reader, body, files, exclusions, directories)
    seal_after = verify_seal(reader, body, documents, files, exclusions)
    need(check_closed_inputs(reader, args.closed_inputs, args.expected_closed_inputs_sha256) ==
         (body, closure_pin, documents), 'closed qualification inputs changed during packaging')
    for path, expected in HELPERS.values():
        need(reader.pin(path)['sha256'] == expected, 'frozen helper changed during packaging')
    need(reader.pin(Path(__file__).resolve()) == builder_pin and reader.pin(zstd) == zstd_pin,
         'executed builder/codec changed')
    budget.check()
    manifest = {'schema': 'ranker-curvature-frozen-evidence-package@1',
        'status': 'closed_scanned_local_package_not_uploaded', 'closed_inputs': closure_pin,
        'final_selection': body['final_selection'], 'semantic_policy': body['semantic_policy'],
        'files': rows, 'file_count': len(rows), 'original_file_bytes': total, 'data_shards': shards,
        'exclusions': exclusions, 'scope_root': str(QUALIFIER), 'explicit_additions': body['explicit_additions'],
        'seal_binding_before': seal_before, 'seal_binding_after': seal_after,
        'helper_pins': {key: reader.pin(value[0]) for key, value in HELPERS.items()}, 'builder': builder_pin, 'codec': zstd_pin,
        'semantic_role_validation': validate_semantics(body, documents, reader.pin),
        'publication_decode_profile': dict(PROFILE), 'frozen_reader_controls': controls,
        'external_dependencies': body['external_dependencies'],
        'actual_aggregate_decoded_work_bytes': budget.decoded, 'actual_verification_decode_bytes': 0,
        'actual_recursive_classifier_decoded_bytes': budget.decoded, 'actual_recursive_members': budget.members,
        'actual_first_decoded_tar_readback_bytes': first_tar_bytes,
        'actual_first_decoded_member_readback_bytes': first_member_bytes,
        'actual_duplicate_verification_decoder_invocations': 0,
        'actual_outer_shard_codec_encode_invocations': len(shards),
        'actual_first_outer_shard_codec_decode_invocations': len(shards),
        'exact_available_cached_credential_veto': True, 'bounded_complete_PEM_classifier_veto': True,
        'scan_hits': [], 'universal_secret_free_claim': False, 'source_atomic': False,
        'old_sealed_source_helpers_and_evidence_modified': False, 'raw_mathlib_and_cache_bodies_published': False,
        'intended_remote_namespace': 'successor-ranker-curvature-v1',
        'remote_parent_verified_here': False, 'public_upload_performed': False,
        'whole_source_runtime_equivalence_proved': False, 'asymptotic_optimizer_convergence_proved': False,
        'new_qualification_jobs': 0, 'remote_mutations': 0, **BOUNDARIES}
    manifest_pin = reader.write(public / 'manifest.json', manifest)
    for source in staging.iterdir():
        source.unlink()
    staging.rmdir()
    budget.check()
    reader.write(output / 'closed.json', {'schema': 'ranker-curvature-local-package-attempt@1',
        'status': 'passed_local_frozen_package', 'manifest': manifest_pin, 'source_drift_count': 0,
        'candidate_hits': 0, 'public_upload_performed': False, 'remote_mutations': 0,
        'new_qualification_jobs': 0, 'cleanup_errors': []})
    return manifest_pin


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--closed-inputs', required=True, type=Path)
    parser.add_argument('--expected-closed-inputs-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = build(args)
    except BaseException as error:
        try:
            if getattr(args, 'owned_output', False) and args.output.is_dir() and not (args.output / 'closed.json').exists():
                raw = (json.dumps({'schema': 'ranker-curvature-local-package-attempt@1',
                    'status': 'failed_partial_local_evidence_retained', 'error_type': type(error).__name__,
                    'public_upload_performed': False, 'remote_mutations': 0, 'cleanup_attempted': False,
                    'cleanup_errors': None, 'private_partial_evidence_retained': True}, sort_keys=True) + '\n').encode()
                with (args.output / 'closed.json').open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
        except BaseException as receipt_error:
            error.add_note('Preserving the package failure receipt also failed: ' + type(receipt_error).__name__)
        raise
    print(json.dumps(result, sort_keys=True))
