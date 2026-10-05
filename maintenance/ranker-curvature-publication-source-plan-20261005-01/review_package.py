"""Independent complete file/member review of the curvature publication package.

This source imports only the standard library. Its sole child is the separately
pinned system zstd decoder. It performs no project, solver, model, fit, SQL,
dependency setup, Git, or remote call. Inputs require independent SHA256 pins.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import tarfile
import tempfile
import time

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = WORKSPACE / 'maintenance/ranker-curvature-publication-source-plan-20261005-01'
QUALIFIER = WORKSPACE / 'qualification/codebase_ir/ranker-real-curvature-20261005-01'
EXTERNAL_SUBTREES = (QUALIFIER / 'environment/mathlib4', QUALIFIER / 'environment/cache')
BLOCK, FILE_MAX, RAW_MAX, DECODE_MAX, SHARD_MAX = 1024**2, 16 * 1024**2, 320 * 1024**2, 1024**3, 256 * 1024**2
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
PROFILE = {'raw_population_max': RAW_MAX, 'per_file_max': FILE_MAX,
    'per_decoded_container_max': FILE_MAX, 'compressed_shard_max': SHARD_MAX,
    'aggregate_decoded_work_max': DECODE_MAX, 'wall_seconds': 180,
    'members_max': 10000, 'depth_max': 6, 'zstd_arguments': ['-T1', '-3'],
    'member_readback_profile': 'same_first_decoded_tar_and_member_streams@1',
    'duplicate_verification_decoder_invocations': 0,
    'authorization_scope': 'explicit root publication-only320MiB raw/1GiB decoded; native limits unchanged',
    'authorization_reason': 'final root seal273066128 bytes/1080 regular leaves exceeds256MiB; retain all failures and22 complete dependency profiles'}
BOUNDARIES = {'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN',
    'python_ranker_source_equivalence_proved': False, 'binary64_error_bound_proved': False,
    'historical_execution_origin_proved': False, 'global_optimizer_convergence_proved': False,
    'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
    'planner_activation': False, 'official_benchmark_score': None, 'all_failed_attempts_retained': True,
    'new_public_fits': 0, 'new_ranker_training_trace_replays': 0}
HF = WORKSPACE / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
HELPERS = {
    'reader': (HF / 'successor-source-model-package-03/build_package.py', '8c8eab266a053115cdf0ea11a8aea5323611c2ab049ec1541383831618e385ce'),
    'archive': (HF / 'build_evidence_archive_02.py', 'f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036'),
    'classifier': (HF / 'classify_and_prepare_public_archive_07.py', 'dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8'),
}


def need(condition, message):
    if condition is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def signature(info):
    return {key: getattr(info, 'st_' + key) for key in ('dev', 'ino', 'mode', 'nlink', 'uid', 'gid', 'size', 'mtime_ns', 'ctime_ns')}


def read_regular(path, maximum=FILE_MAX):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, 'regular bounded input required')
        blocks, total = [], 0
        while block := os.read(fd, BLOCK):
            total += len(block)
            need(total <= maximum, 'input grew beyond fixed bound')
            blocks.append(block)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and total == before.st_size,
             'input bytes/stat changed during read')
        return b''.join(blocks), signature(before)
    finally:
        os.close(fd)


def pin(path, maximum=FILE_MAX):
    raw, _ = read_regular(path, maximum)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def body(row):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and type(row['path']) is str and
         type(row['bytes']) is int and 0 <= row['bytes'] <= FILE_MAX and type(row['sha256']) is str and
         re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None, 'exact bounded input descriptor required')
    path = Path(row['path'])
    need(pin(path) == row, 'input descriptor differs')
    return json.loads(read_regular(path)[0])


def descriptor(row):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and type(row['path']) is str and
         type(row['bytes']) is int and 0 <= row['bytes'] <= FILE_MAX and type(row['sha256']) is str and
         re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None, 'exact bounded file descriptor required')
    path = Path(row['path'])
    need(path.is_absolute() and path.resolve(strict=True) == path, 'canonical pinned input required')
    return path


def pointer(value, path):
    need(type(path) is str and (path == '' or path.startswith('/')), 'JSON pointer required')
    for key in path.strip('/').split('/') if path else []:
        key = key.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def allowed_addition(path):
    if path.is_relative_to(QUALIFIER):
        return not any(path.is_relative_to(root) for root in EXTERNAL_SUBTREES)
    relative = path.relative_to(WORKSPACE)
    return len(relative.parts) >= 3 and (relative.parts[0] == 'maintenance' and relative.parts[1].startswith('ranker-curvature-') or
        relative.parts[:2] == ('qualification', 'codebase_ir') and relative.parts[2].startswith('ranker-real-curvature-'))


def fixture_alias(path, row):
    """Bind a pytest convenience link without following or omitting its body."""
    need(type(row) is dict and set(row) == {'path', 'target', 'bytes', 'sha256', 'stat'} and
         row['path'] == str(path) and type(row['target']) is str and type(row['bytes']) is int and
         0 < row['bytes'] <= 4096 and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None and
         type(row['stat']) is list and len(row['stat']) == 7 and all(type(value) is int for value in row['stat']),
         'exact sealed fixture symlink binding required')
    relative = path.relative_to(QUALIFIER)
    need(len(relative.parts) == 4 and relative.parts[0] == 'evidence' and relative.parts[1].startswith('pure-tests') and
         relative.parts[2] == 'fixtures' and relative.parts[3].endswith('current') and
         path.parent.resolve(strict=True) == path.parent, 'only direct pytest fixture convenience aliases permitted')
    seven = lambda info: [getattr(info, 'st_' + key) for key in ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')]
    before = path.lstat()
    need(stat.S_ISLNK(before.st_mode) and seven(before) == row['stat'], 'sealed symlink stat differs')
    literal = os.readlink(path)
    raw = literal.encode('utf-8')
    need(literal == row['target'] and len(raw) == row['bytes'] == before.st_size and
         hashlib.sha256(raw).hexdigest() == row['sha256'], 'literal sealed readlink bytes differ')
    target = Path(literal) if Path(literal).is_absolute() else path.parent / literal
    need(target.parent == path.parent and target.resolve(strict=True) == target and
         stat.S_ISDIR(target.lstat().st_mode) and not target.is_symlink(), 'fixture alias must name one real canonical sibling directory')
    need(os.readlink(path) == literal and seven(path.lstat()) == row['stat'], 'fixture alias changed during read')
    return {'path': str(path), 'kind': 'transient_fixture_symlink', 'reason': 'sealed literal pytest convenience alias; real sibling bodies selected once',
            'target': literal, 'bytes': len(raw), 'sha256': row['sha256'], 'stat': row['stat']}



def inventory(additions, locks, fixture_symlinks):
    files, exclusions, directories = [], [], []
    need(type(fixture_symlinks) is list and len(fixture_symlinks) <= 1000, 'bounded exact fixture alias population required')
    aliases = {row['path']: row for row in fixture_symlinks}
    need(len(aliases) == len(fixture_symlinks), 'unique sealed fixture aliases required')
    def visit(path):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            need(str(path) in aliases, 'undeclared symlink refused without traversal')
            exclusions.append(fixture_alias(path, aliases[str(path)]))
            return
        need(path.resolve(strict=True) == path and not stat.S_ISLNK(info.st_mode), 'inventory symlink/referral refused')
        if path in EXTERNAL_SUBTREES:
            need(stat.S_ISDIR(info.st_mode), 'external dependency directory required')
            exclusions.append({'path': str(path), 'kind': 'external_dependency_subtree',
                'reason': 'exact retained dependency profiles and official source revision; raw bodies not published', 'stat': signature(info)})
        elif stat.S_ISDIR(info.st_mode):
            directories.append({'path': str(path), 'stat': signature(info)})
            for child in sorted(path.iterdir(), key=lambda p: os.fsencode(p.name)):
                visit(child)
        elif str(path) in locks:
            need(stat.S_ISREG(info.st_mode) and info.st_size == 0, 'sealed explicit runtime lock must be empty')
            exclusions.append({'path': str(path), 'kind': 'transient_lock',
                'reason': 'exact sealed closed-runtime zero-byte lock', 'stat': signature(info)})
        else:
            need(stat.S_ISREG(info.st_mode), 'unsupported owned node')
            files.append(path)
    visit(QUALIFIER)
    for row in additions:
        selected = Path(row['path'])
        if not selected.is_relative_to(QUALIFIER):
            visit(selected)
    need(len(files) <= 10000 and len(set(files)) == len(files), 'unique bounded selected files required')
    return sorted(files, key=lambda p: os.fsencode(str(p.relative_to(WORKSPACE)))), exclusions, directories


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






def verify_inputs(closure, selected, manifest):
    need(closure.get('schema') == 'ranker-curvature-publication-closed-inputs@1' and
         closure.get('source_and_artifacts_quiet') is True and closure.get('scope_root') == str(QUALIFIER) and
         closure.get('excluded_dependency_subtrees') == [str(p) for p in EXTERNAL_SUBTREES] and
         wire(closure.get('publication_profile')) == wire(PROFILE), 'exact quiet curvature inputs/profile required')
    need(type(closure.get('documents')) is dict and {'file_seal', 'qualified_review'} <= set(closure['documents'])
         and len(closure['documents']) <= 1000, 'complete sealed qualification documents required')
    documents = {}
    for name, row in closure['documents'].items():
        need(allowed_addition(Path(row['path'])), 'document outside new owned namespace')
        documents[name] = body(row)
    policy = closure['semantic_policy']
    need(policy['path'] == str(ROOT / 'required-facts.json'), 'root-frozen observed policy required')
    facts = body(policy)
    need(type(facts) is list and 0 < len(facts) <= 10000 and wire(facts) == wire(closure.get('required_facts')),
         'exact nonempty semantic fact policy required')
    encoded_facts = [wire(fact) for fact in facts]
    for key, value in BOUNDARIES.items():
        need(wire({'document': 'qualified_review', 'pointer': '/' + key, 'equals': value}) in encoded_facts,
             'all source/Float/global/task/origin/authority/retained-failure boundaries required')
    for fact in facts:
        need(type(fact) is dict and set(fact) == {'document', 'pointer', 'equals'} and fact['document'] in documents,
             'exact declared actual outcome fact required')
        need(wire(pointer(documents[fact['document']], fact['pointer'])) == wire(fact['equals']), 'actual observed semantic fact differs')
    need(manifest.get('semantic_role_validation') == validate_semantics(closure, documents, pin),
         'actual semantic role/check/source-print accounting differs')
    seal = documents['file_seal']
    count, total = closure.get('expected_sealed_file_count'), closure.get('expected_sealed_file_bytes')
    need(type(count) is int and 0 < count <= 10000 and type(total) is int and 0 <= total <= RAW_MAX and
         type(seal.get('files')) is list and len(seal['files']) == len({row['path'] for row in seal['files']}) == count and
         sum(row['bytes'] for row in seal['files']) == total and seal['review'] == closure['documents']['qualified_review'],
         'exact final sealed population and review binding required')
    need(hashlib.sha256(wire(seal['files'])).hexdigest() == seal['file_inventory_sha256'], 'compact no-newline seal digest differs')
    locks = closure.get('excluded_zero_byte_locks')
    need(type(locks) is list and len(set(locks)) == len(locks) and
         all(type(p) is str and Path(p).name.endswith('.lock') for p in locks), 'exact lock exclusions required')
    sealed_paths = set()
    for row in seal['files']:
        path = Path(row['path'])
        need(path.is_relative_to(QUALIFIER) and not any(path.is_relative_to(root) for root in EXTERNAL_SUBTREES) and
             pin(path) == row and (str(path) not in locks or row['bytes'] == 0), 'sealed owned leaf changed')
        sealed_paths.add(str(path))
    need(set(locks) <= sealed_paths, 'all excluded locks must remain sealed')
    additions = closure.get('explicit_additions')
    need(type(additions) is list and len(additions) <= 1000 and len({row['path'] for row in additions}) == len(additions),
         'unique fixed new additions required')
    for row in additions:
        need(allowed_addition(Path(row['path'])) and pin(Path(row['path'])) == row, 'explicit new addition changed')
    by_addition = {row['path']: row for row in additions}
    for path in (ROOT / 'build_package.py', ROOT / 'review_package.py', ROOT / 'freeze_inputs.py',
                 ROOT / 'publication-profile-authorization.json', ROOT / 'plan.json', ROOT / 'required-facts.json'):
        need(by_addition.get(str(path)) == pin(path), 'publication tools/plan/policy must be selected')
    dependencies = closure.get('external_dependencies')
    need(type(dependencies) is dict and dependencies.get('mathlib_revision') == '5ed2965256430c3649e86755f9576b54eca72435' and
         dependencies.get('official_repository') == 'https://github.com/leanprover-community/mathlib4' and
         dependencies.get('raw_dependency_bodies_published') is False and
         type(dependencies.get('environment_manifests')) is list and len(dependencies['environment_manifests']) > 0 and
         type(dependencies.get('reproduction_notes')) is str and len(dependencies['reproduction_notes']) > 0,
         'exact retained environment/reproduction declaration required')
    aliases = closure.get('excluded_fixture_symlinks')
    need(type(aliases) is list and wire(aliases) == wire(seal.get('fixture_symlinks')) and
         hashlib.sha256(wire(aliases)).hexdigest() == seal.get('fixture_symlink_inventory_sha256'), 'exact sealed fixture alias inventory required')
    for row in aliases:
        fixture_alias(Path(row['path']), row)
    files, exclusions, directories = inventory(additions, locks, aliases)
    expected = (sealed_paths - set(locks)) | set(by_addition)
    need({str(p) for p in files} == expected and len(files) == len(expected), 'full seal plus exact additions required')
    expected_exclusions = {str(root): 'external_dependency_subtree' for root in EXTERNAL_SUBTREES}
    expected_exclusions.update({path: 'transient_lock' for path in locks})
    expected_exclusions.update({row['path']: 'transient_fixture_symlink' for row in aliases})
    need(len(exclusions) == len(expected_exclusions) and {row['path']: row['kind'] for row in exclusions} == expected_exclusions,
         'only exact dependency subtrees and sealed runtime locks excluded')
    actual = [{**pin(path), 'stat': signature(path.lstat())} for path in files]
    need(selected.get('schema') == 'ranker-curvature-publication-final-selection@1' and selected.get('files') == actual and
         selected.get('exclusions') == exclusions and selected.get('directories') == directories, 'frozen selected inventory/hash/stat differs')
    by_selected = {row['path']: {key: row[key] for key in ('path', 'bytes', 'sha256')} for row in actual}
    for row in [*closure['documents'].values(), *dependencies['environment_manifests']]:
        need(by_selected.get(row['path']) == row, 'all qualification documents and exact environment profiles must be selected')
    need(manifest.get('scope_root') == str(QUALIFIER) and manifest.get('exclusions') == exclusions and
         manifest.get('explicit_additions') == additions and wire(manifest.get('external_dependencies')) == wire(dependencies),
         'manifest qualification/dependency scope differs')
    need(type(manifest.get('files')) is list and len(manifest['files']) == len(actual) == manifest.get('file_count'), 'manifest population differs')
    for row, source in zip(manifest['files'], actual):
        need({key: row[key] for key in ('source_path', 'bytes', 'sha256')} ==
             {'source_path': source['path'], 'bytes': source['bytes'], 'sha256': source['sha256']} and
             row['source_stat'] == source['stat'] and row['path'] == str(Path(source['path']).relative_to(WORKSPACE)) and
             row['member'] == row['path'] and row['scan_hits'] == [], 'manifest source/member pin differs')
    need(sum(row['bytes'] for row in actual) == manifest['original_file_bytes'] <= RAW_MAX, 'publication raw population bound differs')
    for key, (path, expected_sha) in HELPERS.items():
        need(manifest.get('helper_pins', {}).get(key) == pin(path) and pin(path)['sha256'] == expected_sha, 'fixed executed helper changed')
    need(set(manifest['helper_pins']) == set(HELPERS) and pin(ROOT / 'build_package.py') == manifest['builder'] and
         manifest['codec']['path'] == '/usr/bin/zstd' and pin(Path('/usr/bin/zstd')) == manifest['codec'], 'builder/codec source changed')
    binding = {'sealed_file_count_rehashed': count, 'sealed_file_bytes_rehashed': total,
               'sealed_lock_bindings_rehashed': len(locks), 'sealed_durable_leaves_selected': count - len(locks),
               'sealed_fixture_symlink_bindings_rehashed': len(aliases),
               'explicit_additions': len(additions), 'semantic_fact_count_verified': len(facts)}
    need(manifest.get('seal_binding_before') == binding == manifest.get('seal_binding_after'), 'before/after seal/fact accounting differs')
    return len(files), binding


def decode(shard, codec, temporary, deadline, remaining):
    child = subprocess.Popen([str(codec), '--quiet', '-d', '--stdout', str(shard)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
    selector, count, digest = selectors.DefaultSelector(), 0, hashlib.sha256()
    selector.register(child.stdout, selectors.EVENT_READ)
    try:
        while True:
            seconds = deadline - time.monotonic()
            need(seconds > 0, 'file-only review wall bound exceeded')
            events = selector.select(min(seconds, 1))
            if not events:
                continue
            block = os.read(child.stdout.fileno(), BLOCK)
            if not block:
                break
            count += len(block)
            need(count <= FILE_MAX and count <= remaining, 'decoded work/container bound exceeded')
            digest.update(block)
            temporary.write(block)
        need(child.wait(timeout=max(0.01, deadline - time.monotonic())) == 0, 'pinned decoder failed')
        temporary.seek(0)
        return count, digest.hexdigest()
    finally:
        selector.close()
        child.stdout.close()
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()


def review(args):
    deadline = time.monotonic() + 180
    own_pin, manifest_pin, closure_pin = pin(Path(__file__).resolve()), pin(args.manifest), pin(args.closed_inputs)
    need(type(args.expected_manifest_sha256) is str and re.fullmatch('[0-9a-f]{64}', args.expected_manifest_sha256) is not None and
         type(args.expected_closed_inputs_sha256) is str and re.fullmatch('[0-9a-f]{64}', args.expected_closed_inputs_sha256) is not None and
         manifest_pin['sha256'] == args.expected_manifest_sha256 and closure_pin['sha256'] == args.expected_closed_inputs_sha256,
         'independent exact expected pins differ')
    manifest, closure = body(manifest_pin), body(closure_pin)
    selected = body(closure['final_selection'])
    need(manifest.get('schema') == 'ranker-curvature-frozen-evidence-package@1' and
         manifest.get('status') == 'closed_scanned_local_package_not_uploaded' and
         manifest.get('closed_inputs') == closure_pin and manifest.get('final_selection') == closure['final_selection'] and
         manifest.get('semantic_policy') == closure['semantic_policy'], 'successful exact package closure join required')
    package_closed = args.manifest.parent.parent / 'closed.json'
    closed_pin = pin(package_closed)
    closed = body(closed_pin)
    need(closed.get('schema') == 'ranker-curvature-local-package-attempt@1' and closed.get('status') == 'passed_local_frozen_package' and
         closed.get('manifest') == manifest_pin and closed.get('cleanup_errors') == [] and
         not (args.manifest.parent.parent / 'private-staging').exists(), 'closed package and complete staging cleanup required')
    count, seal_binding = verify_inputs(closure, selected, manifest)
    need(wire(manifest.get('publication_decode_profile')) == wire(PROFILE), 'exact publication-only profile required')
    for key, value in BOUNDARIES.items():
        need(wire(manifest.get(key)) == wire(value), 'manifest authority/task/source/Float/global boundary differs')
    need(manifest.get('frozen_reader_controls') == {'regular_positive_exact_bytes': True,
         'symlink_negative_genuinely_refused': True, 'control_population': 2, 'cleanup_verified': True, 'native_proof_jobs': 0},
         'frozen reader control pair closure required')
    need(manifest.get('scan_hits') == [] and manifest.get('exact_available_cached_credential_veto') is True and
         manifest.get('bounded_complete_PEM_classifier_veto') is True and manifest.get('universal_secret_free_claim') is False and
         manifest.get('raw_mathlib_and_cache_bodies_published') is False and manifest.get('remote_mutations') == 0 and
         manifest.get('new_qualification_jobs') == 0, 'classified local-only publication closure required')
    rows, actual_decode, offset, reviews = manifest['files'], 0, 0, []
    need(type(manifest.get('data_shards')) is list and 0 < len(manifest['data_shards']) <= 1000, 'bounded shard population required')
    for index, row in enumerate(manifest['data_shards']):
        need(time.monotonic() < deadline, 'review wall bound exceeded')
        name = 'data-%06d.tar.zst' % index
        shard = args.manifest.parent / name
        need(row['path'] == str(shard) and row['archive'] == name and pin(shard, SHARD_MAX) ==
             {key: row[key] for key in ('path', 'bytes', 'sha256')} and type(row['members']) is int and 0 < row['members'] <= 10000 and
             row['scan_hits'] == [] and row['decoded_per_file_readback_verified'] is True, 'compressed shard pin/accounting differs')
        group = rows[offset:offset + row['members']]
        need(len(group) == row['members'] and all(source['archive'] == name for source in group), 'ordered complete shard assignment differs')
        with tempfile.TemporaryFile() as temporary:
            size, digest = decode(shard, Path(manifest['codec']['path']), temporary, deadline, DECODE_MAX - actual_decode)
            actual_decode += size
            need(size == row['decoded_tar_bytes'] <= FILE_MAX and digest == row['decoded_tar_sha256'], 'complete decoded tar differs')
            with tarfile.open(fileobj=temporary, mode='r:') as archive:
                members = archive.getmembers()
                need(len(members) == len(group), 'complete decoded member count differs')
                for member, source in zip(members, group):
                    need(time.monotonic() < deadline and member.isfile() and not member.issym() and not member.islnk() and
                         member.name == source['member'] and member.size == source['bytes'] and member.mode == 0o644 and
                         member.uid == member.gid == member.mtime == 0 and member.uname == member.gname == '', 'member identity differs')
                    digest, counted = hashlib.sha256(), 0
                    with archive.extractfile(member) as stream:
                        while block := stream.read(BLOCK):
                            counted += len(block)
                            need(counted <= FILE_MAX and time.monotonic() < deadline, 'member work bound exceeded')
                            digest.update(block)
                    need(counted == source['bytes'] and digest.hexdigest() == source['sha256'], 'complete member bytes differ')
        reviews.append({'archive': name, 'decoded_tar_bytes': size, 'members_verified': len(group)})
        offset += len(group)
    need(offset == len(rows), 'every selected member must be decoded and verified')
    need(type(manifest.get('actual_outer_shard_codec_encode_invocations')) is int and
         type(manifest.get('actual_first_outer_shard_codec_decode_invocations')) is int and
         manifest['actual_outer_shard_codec_encode_invocations'] == len(reviews) == manifest['actual_first_outer_shard_codec_decode_invocations'],
         'actual outer-shard codec invocation accounting differs')
    for key in ('actual_aggregate_decoded_work_bytes', 'actual_verification_decode_bytes', 'actual_recursive_classifier_decoded_bytes'):
        need(type(manifest.get(key)) is int and 0 <= manifest[key] <= DECODE_MAX, 'exact bounded decoded work accounting required')
    need(manifest['actual_verification_decode_bytes'] == 0 and
         manifest['actual_recursive_classifier_decoded_bytes'] == manifest['actual_aggregate_decoded_work_bytes'] and
         manifest.get('actual_first_decoded_tar_readback_bytes') == actual_decode and
         manifest.get('actual_first_decoded_member_readback_bytes') == manifest['original_file_bytes'] and
         type(manifest.get('actual_duplicate_verification_decoder_invocations')) is int and
         manifest['actual_duplicate_verification_decoder_invocations'] == 0 and
         manifest['actual_aggregate_decoded_work_bytes'] >= actual_decode + manifest['original_file_bytes'],
         'first-decoded-spool and complete member/work accounting differs')
    need(verify_inputs(closure, selected, manifest) == (count, seal_binding), 'full post-review closure accounting changed')
    need(pin(args.manifest) == manifest_pin and pin(args.closed_inputs) == closure_pin and pin(package_closed) == closed_pin and
         pin(Path(__file__).resolve()) == own_pin, 'reviewed manifest/closure/source drift')
    need(time.monotonic() < deadline, 'complete final review must remain within180s wall')
    need(args.output.is_absolute() and args.output.resolve() == args.output and not args.output.exists() and
         args.output.parent.is_dir() and args.output.is_relative_to(WORKSPACE / 'maintenance'), 'new owned review receipt required')
    result = {'schema': 'ranker-curvature-full-decoded-member-file-only-review@1', 'status': 'passed',
        'manifest': manifest_pin, 'closed_inputs': closure_pin, 'package_closure': closed_pin, 'reviewer': own_pin,
        'selected_files_verified_before_after': count, 'seal_binding_verified_before_after': seal_binding,
        'decoded_members_verified': offset, 'decoded_tar_shards': reviews,
        'actual_file_only_review_decoded_bytes': actual_decode, 'file_only_review_decode_work_max': DECODE_MAX,
        'publication_container_max': FILE_MAX, 'exact_frozen_semantic_outcome_facts_verified': True,
        'excluded_dependency_subtrees': [str(path) for path in EXTERNAL_SUBTREES],
        'raw_mathlib_and_cache_bodies_published': False, 'new_native_qualification_jobs': 0,
        'actual_outer_shard_codec_decoder_invocations': len(reviews), 'project_imports': 0,
        'new_sql_or_lean_calls': 0, 'remote_mutations': 0, 'source_atomic': False, **BOUNDARIES}
    with args.output.open('xb') as stream:
        stream.write(wire(result) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return pin(args.output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--closed-inputs', required=True, type=Path)
    parser.add_argument('--expected-closed-inputs-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    print(json.dumps(review(parser.parse_args()), sort_keys=True))
