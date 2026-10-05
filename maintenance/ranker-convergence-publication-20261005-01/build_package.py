"""Package the complete externally sealed convergence increment locally.

No work occurs on import. A quiet final plan and its independent SHA256 are
required. Every sealed regular leaf, failure, full object and chunk is retained.
Native qualifications, Git operations and remote publication are absent.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile
import time
import types

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = WORKSPACE / 'maintenance/ranker-convergence-publication-20261005-01'
QUALIFIER = WORKSPACE / 'qualification/codebase_ir/ranker-real-convergence-20261005-01'
SOURCE_PLAN = WORKSPACE / 'qualification/codebase_ir/ranker-real-convergence-source-plan-20261005-01'
HF = WORKSPACE / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
HELPERS = {
    'reader': (HF / 'successor-source-model-package-03/build_package.py', '8c8eab266a053115cdf0ea11a8aea5323611c2ab049ec1541383831618e385ce'),
    'archive': (HF / 'build_evidence_archive_02.py', 'f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036'),
    'classifier': (HF / 'classify_and_prepare_public_archive_07.py', 'dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8'),
    'member_verifier': (WORKSPACE / 'maintenance/ranker-curvature-publication-source-plan-20261005-01/build_package.py', '4e14c08fc6d680e5fcbf755f649284f750353b73b42dd08b926398f4c43c9a93'),
}
BLOCK = 1024**2
RAW_MAX = 256 * BLOCK
MEMBER_MAX = 14 * BLOCK
TAR_MAX = 16 * BLOCK
DECODE_MAX = 1024**3
PROFILE = {
    'raw_population_max': RAW_MAX, 'raw_member_sum_per_shard_max': MEMBER_MAX,
    'per_file_max': MEMBER_MAX, 'complete_decoded_tar_max': TAR_MAX,
    'compressed_shard_max': TAR_MAX, 'aggregate_decoded_work_max': DECODE_MAX,
    'wall_seconds': 180, 'members_max': 10000, 'depth_max': 6,
    'shards_max': 64, 'zstd_args': ['-T1', '-3'],
    'duplicate_verification_decoder_invocations': 0,
    'member_readback_profile': 'same_first_decoded_tar_and_member_streams@1',
    'native_qualification_limits_changed': False,
}
NATIVE_BOUNDS = {'timeout_seconds': 20, 'cpu_seconds': 20, 'max_input_bytes': 262144,
    'max_output_bytes': 65536, 'max_workspace_bytes': 16777216}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def load_source(name):
    path, expected = HELPERS[name]
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical helper source required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= TAR_MAX, 'bounded helper source required')
        raw = b''
        while block := os.read(fd, BLOCK):
            raw += block
            need(len(raw) <= TAR_MAX, 'helper grew beyond bound')
        signature = lambda info: tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and len(raw) == before.st_size, 'helper changed during read')
    finally:
        os.close(fd)
    need(hashlib.sha256(raw).hexdigest() == expected, 'frozen helper source differs')
    module = types.ModuleType('held_convergence_publication_' + name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def descriptor(row):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and type(row['path']) is str and
        type(row['bytes']) is int and 0 <= row['bytes'] <= TAR_MAX and type(row['sha256']) is str and
        re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None, 'exact bounded descriptor required')
    path = Path(row['path'])
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical descriptor required')
    return path


def read_document(reader, row):
    path = descriptor(row)
    raw, _ = reader.read_regular(path)
    need(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], 'parsed pinned document changed')
    return json.loads(raw)


def pointer(value, path):
    need(type(path) is str and (path == '' or path.startswith('/')), 'JSON pointer required')
    for part in path[1:].split('/') if path else []:
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if type(value) is list else value[part]
    return value


def check_plan(reader, path, expected):
    need(path == ROOT / 'plan.json' and re.fullmatch('[0-9a-f]{64}', expected or '') is not None,
        'fixed final plan and independent lowercase SHA256 required')
    raw, _ = reader.read_regular(path)
    plan_pin = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    need(plan_pin['sha256'] == expected, 'externally pinned plan differs')
    plan = json.loads(raw)
    need(plan.get('schema') == 'ranker-convergence-publication-plan@1' and plan.get('status') == 'frozen_final_plan' and
        plan.get('source_and_artifacts_quiet') is True and plan.get('source_plan_quiet') is True,
        'root-frozen quiet final inputs required; active candidate plans cannot execute')
    need(plan.get('scope_root') == str(QUALIFIER) and plan.get('source_plan_root') == str(SOURCE_PLAN) and
        wire(plan.get('publication_profile')) == wire(PROFILE), 'fixed owned roots and unchanged publication caps required')
    docs = plan.get('documents')
    need(type(docs) is dict and {'file_seal', 'qualified_review'} <= set(docs) and 2 <= len(docs) <= 256,
        'complete pinned final seal, review and semantic documents required')
    documents = {name: read_document(reader, row) for name, row in docs.items()}
    seal, review = documents['file_seal'], documents['qualified_review']
    need(descriptor(docs['file_seal']).is_relative_to(QUALIFIER) and descriptor(docs['qualified_review']).is_relative_to(QUALIFIER),
        'new convergence final seal and review required')
    need(type(plan.get('seal_schema')) is str and seal.get('schema') == plan['seal_schema'] and
        type(plan.get('review_schema')) is str and review.get('schema') == plan['review_schema'] and review.get('status') == 'passed',
        'exact final seal/review schemas and passed review required')
    need(seal.get('review') == docs['qualified_review'], 'final seal must bind qualified review')
    need(seal.get('fixture_symlinks', []) == [], 'this no-alias plan refuses undeclared fixture symlinks')
    exclusions = plan.get('excluded_dependency_subtrees')
    need(type(exclusions) is list and exclusions == seal.get('excluded_dependency_subtrees', []) and
        len(exclusions) == len(set(exclusions)) <= 8 and all(type(name) is str and Path(name).is_relative_to(QUALIFIER) and
            Path(name) != QUALIFIER for name in exclusions), 'only exact sealed dependency subtree exclusions permitted')
    need(all(review.get(key) is False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')) and
        review.get('full_task_satisfaction') == 'unknown' and review.get('all32_governing_RPI_exits') == 'OPEN',
        'review cannot grant full-task or operational authority')
    policy = plan.get('semantic_policy')
    need(descriptor(policy) == ROOT / 'required-facts.json', 'fixed observed-fact policy required')
    facts = read_document(reader, policy)
    need(type(facts) is list and 0 < len(facts) <= 5000, 'nonempty exact observed-fact policy required')
    seen = set()
    for fact in facts:
        need(type(fact) is dict and set(fact) == {'document', 'pointer', 'equals'} and fact['document'] in documents,
            'exact document/pointer/equals fact required')
        key = (fact['document'], fact['pointer'])
        need(key not in seen, 'duplicate fact pointer refused')
        seen.add(key)
        need(wire(pointer(documents[fact['document']], fact['pointer'])) == wire(fact['equals']), 'observed fact differs')
    native_roles = plan.get('native_checks')
    need(type(native_roles) is list and 0 < len(native_roles) <= 64 and len(native_roles) == len(set(native_roles)),
        'complete unique actual native check roles required')
    all_checks = {row['path'] for row in seal.get('files', []) if Path(row['path']).name == 'check-result.json'}
    need({docs[name]['path'] for name in native_roles if name in docs} == all_checks and len(native_roles) == len(all_checks),
        'every sealed native attempt, including failures, must be fact-gated')
    clean_false = ('timed_out', 'cancelled', 'unavailable', 'resource_exhausted', 'output_truncated', 'workspace_limit_exceeded')
    for name in native_roles:
        check = documents[name]
        need((name, '/status') in seen and wire(check.get('native_bounds')) == wire(NATIVE_BOUNDS) and check.get('native_invocations') == 1,
            'actual native status facts and unchanged native bounds required')
        if check['status'] != 'passed':
            need(check['status'] in ('inconclusive', 'rejected'), 'unknown native status refused')
            continue
        need(check.get('returncode') == 0 and check.get('expected_success') is True and check.get('matches_expectation') is True and
            check.get('workspace_cleaned') is True and all(check.get(key) is False for key in clean_false) and
            check.get('artifact_anomalies') == [] and check.get('axiom_report_error') is None and
            check.get('post_call_binding_error') is None and check.get('reconstruction_validation_error') is None and
            check.get('receipt_retention_overflow', False) is False, 'clean actual positive native result required')
        need(all(check.get(key) is True for key in ('proof_source_in_frozen_per_job_environment',
            'direct_imports_and_implicit_Init_in_frozen_registry', 'root_lease_owned_by_caller',
            'outer120s_and_frozen_project_import_guard_owned_by_caller')), 'actual frozen native admission bindings required')
        queries = check.get('theorem_axiom_output')
        need(type(queries) is list and 0 < len(queries) <= 256 and len({row['theorem'] for row in queries}) == len(queries) and
            all(type(row.get('axioms')) is list and set(row['axioms']) <= {'propext', 'Classical.choice', 'Quot.sound'} for row in queries),
            'complete actual theorem queries with only standard axioms required')
        for field in ('source', 'augmented_source', 'environment_manifest'):
            need(reader.pin(descriptor(check[field])) == check[field], 'actual positive native source/profile pin changed')
        artifacts = check.get('compiled_artifacts')
        chunks = check.get('retained_chunk_artifacts')
        need(type(artifacts) is list and artifacts and type(chunks) is list and chunks and
            check.get('reconstruction_validation', {}).get('status') == 'passed', 'complete retained full objects and chunks required')
        for row in [*artifacts, *chunks]:
            bound = {key: row[key] for key in ('path', 'bytes', 'sha256')}
            need(row.get('complete') is True and reader.pin(descriptor(bound)) == bound and bound['path'] in {item['path'] for item in seal['files']},
                'every complete native object and chunk must remain sealed and selected')
    for name in ('qualified_review', *native_roles):
        need(any(key[0] == name for key in seen), 'all qualification roles must be explicitly fact-gated')
    additions = plan.get('explicit_additions')
    need(type(additions) is list and 1 <= len(additions) <= 100 and len(additions) == len({row['path'] for row in additions}),
        'unique bounded final explicit additions required')
    required = {str(ROOT / name) for name in ('build_package.py', 'review_package.py', 'freeze_inputs.py', 'required-facts.json')}
    required.add(docs['file_seal']['path'])
    need(required <= {row['path'] for row in additions}, 'all executed publication sources, policy and seal self-file required')
    for row in additions:
        path = descriptor(row)
        need((path.is_relative_to(ROOT) or path.is_relative_to(QUALIFIER)) and path != ROOT / 'plan.json' and
            path.name not in ('closed-inputs.json', 'final-selection.json') and reader.pin(path) == row,
            'exact new public tool/policy/seal additions; self-referential plan outputs refused')
    need(plan.get('old_HF_bundle_reuploaded') is False and plan.get('prior_HF_commit') == '8b7b8c896749e0ca3884114cedbed782a88f4702',
        'prior curvature bundle is referenced and preserved')
    return plan, plan_pin, documents, facts


def inventory(reader, plan, documents):
    seal = documents['file_seal']
    sealed = seal.get('files')
    need(type(sealed) is list and 0 < len(sealed) <= 10000 and len(sealed) == len({row['path'] for row in sealed}), 'complete unique final regular seal required')
    count, total = len(sealed), sum(row['bytes'] for row in sealed)
    need(seal.get('regular_file_count') == count and seal.get('regular_file_bytes') == total and total <= RAW_MAX and
        hashlib.sha256(wire(sealed)).hexdigest() == seal.get('file_inventory_sha256'), 'exact seal count, bytes and canonical inventory digest required')
    excluded = {Path(name) for name in plan['excluded_dependency_subtrees']}
    found, exclusions, directories = [], [], []
    def visit(path):
        info = path.lstat()
        if path in excluded:
            need(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode) and path.resolve(strict=True) == path, 'canonical sealed dependency directory required')
            exclusions.append({'path': str(path), 'kind': 'external_dependency_subtree', 'stat': reader.signature(info)})
            return
        need(not stat.S_ISLNK(info.st_mode) and path.resolve(strict=True) == path, 'unexpected symlink/referral refused without traversal')
        if stat.S_ISDIR(info.st_mode):
            directories.append({'path': str(path), 'stat': reader.signature(info)})
            for child in sorted(path.iterdir(), key=lambda item: os.fsencode(item.name)):
                visit(child)
        else:
            need(stat.S_ISREG(info.st_mode) and info.st_size <= MEMBER_MAX, 'bounded owned regular evidence required')
            found.append(path)
    visit(QUALIFIER)
    seal_path = descriptor(plan['documents']['file_seal'])
    need({str(path) for path in found} == {row['path'] for row in sealed} | {str(seal_path)},
        'all owned regular evidence must equal full seal plus externally pinned seal self-file')
    for row in sealed:
        path = descriptor(row)
        need(path.is_relative_to(QUALIFIER) and not any(path.is_relative_to(root) for root in excluded) and reader.pin(path) == row,
            'sealed regular leaf changed or left owned scope')
    visit(SOURCE_PLAN)
    for row in plan['explicit_additions']:
        path = descriptor(row)
        if path not in found:
            visit(path)
    need(len(found) == len(set(found)) <= 10000, 'unique complete selected population required')
    files = sorted(found, key=lambda path: os.fsencode(str(path.relative_to(WORKSPACE))))
    rows = [{**reader.pin(path), 'stat': reader.signature(path.lstat())} for path in files]
    need(sum(row['bytes'] for row in rows) <= RAW_MAX, 'full selected raw population exceeds fixed 256MiB cap')
    return rows, exclusions, directories


def check_closed(reader, path, expected):
    need(path == ROOT / 'closed-inputs.json' and re.fullmatch('[0-9a-f]{64}', expected or '') is not None, 'fixed externally pinned closed inputs required')
    raw, _ = reader.read_regular(path)
    closure_pin = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    need(closure_pin['sha256'] == expected, 'closed-inputs pin differs')
    closure = json.loads(raw)
    need(closure.get('schema') == 'ranker-convergence-publication-closed-inputs@1', 'exact closed-input schema required')
    plan, plan_pin, documents, facts = check_plan(reader, descriptor(closure['plan']), closure['plan']['sha256'])
    need(plan_pin == closure['plan'] and closure.get('publication_profile') == PROFILE, 'final plan/profile differs from closure')
    selected = read_document(reader, closure['final_selection'])
    need(descriptor(closure['final_selection']) == ROOT / 'final-selection.json' and selected.get('schema') == 'ranker-convergence-publication-final-selection@1', 'fixed complete final selection required')
    rows, exclusions, directories = inventory(reader, plan, documents)
    need(selected.get('files') == rows and selected.get('exclusions') == exclusions and selected.get('directories') == directories, 'full frozen selection/stat inventory changed')
    return closure, closure_pin, plan, documents, rows, exclusions, directories


def tar_item(row):
    item = tarfile.TarInfo(row['path'])
    item.size, item.mode = row['bytes'], 0o644
    item.uid = item.gid = item.mtime = 0
    item.uname = item.gname = ''
    return item


def split_shards(rows):
    groups, current, raw_bytes, encoded_bytes = [], [], 0, 0
    complete = lambda n: ((n + 1024 + tarfile.RECORDSIZE - 1) // tarfile.RECORDSIZE) * tarfile.RECORDSIZE
    for row in rows:
        needed = len(tar_item(row).tobuf(format=tarfile.GNU_FORMAT)) + ((row['bytes'] + 511) // 512) * 512
        need(row['bytes'] <= MEMBER_MAX and complete(needed) <= TAR_MAX, 'single member cannot fit fixed complete tar bounds')
        if current and (raw_bytes + row['bytes'] > MEMBER_MAX or complete(encoded_bytes + needed) > TAR_MAX):
            groups.append(current)
            current, raw_bytes, encoded_bytes = [], 0, 0
        current.append(row)
        raw_bytes += row['bytes']
        encoded_bytes += needed
    if current:
        groups.append(current)
    need(0 < len(groups) <= PROFILE['shards_max'], 'bounded nonempty shard population required')
    return groups


def build(args):
    need(__debug__, 'pinned reader assertions must remain enabled')
    deadline = time.monotonic() + PROFILE['wall_seconds']
    reader = load_source('reader')
    own_pin = reader.pin(Path(__file__).resolve())
    closed = check_closed(reader, args.closed_inputs, args.expected_closed_inputs_sha256)
    closure, closure_pin, plan, documents, selected, exclusions, directories = closed
    output = args.output
    need(output.is_absolute() and output.resolve() == output and not output.exists() and output.parent.is_dir() and
        output.parent == WORKSPACE / 'maintenance' and output.name.startswith('ranker-convergence-publication-package-'), 'fresh owned local package output required')
    archive, classifier, verifier = load_source('archive'), load_source('classifier'), load_source('member_verifier')
    scanner = archive.Scanner()
    scanner.patterns = [(name, pattern) for name, pattern in archive.PATTERNS if name != 'private_key_pem']
    need(time.monotonic() < deadline, 'publication wall budget exceeded before package creation')
    budget = classifier.Budget(seconds=deadline-time.monotonic(), decoded_bytes=DECODE_MAX, container_bytes=TAR_MAX, members=10000, depth=6)
    output.mkdir(mode=0o700)
    args.owned_output = True
    reader.write(output / 'started.json', {'schema': 'ranker-convergence-local-package-attempt@1', 'status': 'started', 'closed_inputs': closure_pin, 'builder': own_pin, 'publication_profile': PROFILE, 'remote_mutations': 0, 'native_qualification_jobs': 0})
    staging, public = output / 'private-staging', output / 'package'
    staging.mkdir(mode=0o700)
    public.mkdir(mode=0o700)
    rows, sources = [], {}
    for index, original in enumerate(selected):
        budget.check()
        source = descriptor({key: original[key] for key in ('path', 'bytes', 'sha256')})
        raw, signature = reader.read_regular(source)
        need(len(raw) == original['bytes'] and hashlib.sha256(raw).hexdigest() == original['sha256'] and signature == original['stat'], 'selected source/stat drifted')
        target = staging / ('file-%06d' % index)
        with target.open('xb') as stream:
            stream.write(raw)
        inspection = classifier.Classifier(scanner, budget, staging)
        with target.open('rb') as stream:
            inspection.inspect(stream)
        need(not inspection.hits, 'credential-pattern or exact cached-value veto refused export')
        name = str(source.relative_to(WORKSPACE))
        rows.append({'path': name, 'source_path': str(source), 'bytes': len(raw), 'sha256': original['sha256'], 'source_stat': signature, 'scan_counts': dict(inspection.counts), 'scan_hits': []})
        sources[name] = target
    codec = Path('/usr/bin/zstd')
    codec_pin = reader.pin(codec)
    shards, decoded_tars, decoded_members = [], 0, 0
    for index, group in enumerate(split_shards(rows)):
        budget.check()
        tarpath = staging / ('data-%06d.tar' % index)
        with tarfile.open(tarpath, 'w', format=tarfile.GNU_FORMAT) as sink:
            for row in group:
                with sources[row['path']].open('rb') as stream:
                    sink.addfile(tar_item(row), stream)
        tar_pin = reader.pin(tarpath)
        need(tar_pin['bytes'] <= TAR_MAX and sum(row['bytes'] for row in group) <= MEMBER_MAX, 'actual complete tar/member sum exceeded fixed bounds')
        shard = public / ('data-%06d.tar.zst' % index)
        budget.check()
        with shard.open('xb') as stream:
            subprocess.run([str(codec), '-T1', '-3', '--quiet', '--stdout', str(tarpath)], stdout=stream, stderr=subprocess.PIPE,
                check=True, timeout=min(60, max(0.001, budget.deadline-time.monotonic())))
        budget.check()
        need(shard.stat().st_size <= TAR_MAX and reader.pin(codec) == codec_pin, 'compressed shard or codec pin differs')
        inspection = verifier.inspect_complete_shard(classifier, scanner, budget, staging, shard, tar_pin, group)
        decoded_tars += inspection.decoded_tar_bytes
        decoded_members += inspection.decoded_member_bytes
        shards.append({**reader.pin(shard), 'archive': shard.name, 'decoded_tar_bytes': tar_pin['bytes'], 'decoded_tar_sha256': tar_pin['sha256'],
            'raw_member_bytes': sum(row['bytes'] for row in group), 'members': len(group), 'scan_counts': dict(inspection.counts), 'scan_hits': [], 'decoded_per_file_readback_verified': True})
        for row in group:
            row.update(archive=shard.name, member=row['path'])
    need(check_closed(reader, args.closed_inputs, args.expected_closed_inputs_sha256) == closed, 'full closed population/semantic facts changed during build')
    need(reader.pin(Path(__file__).resolve()) == own_pin and reader.pin(codec) == codec_pin, 'executed builder or codec changed')
    for path, expected in HELPERS.values():
        need(reader.pin(path)['sha256'] == expected, 'frozen helper changed during packaging')
    budget.check()
    manifest = {'schema': 'ranker-convergence-frozen-evidence-package@1', 'status': 'closed_scanned_local_package_not_uploaded', 'closed_inputs': closure_pin,
        'plan': closure['plan'], 'final_selection': closure['final_selection'], 'semantic_policy': plan['semantic_policy'], 'files': rows, 'file_count': len(rows),
        'original_file_bytes': sum(row['bytes'] for row in rows), 'data_shards': shards, 'exclusions': exclusions, 'publication_profile': PROFILE,
        'sealed_regular_file_count': documents['file_seal']['regular_file_count'], 'sealed_regular_file_bytes': documents['file_seal']['regular_file_bytes'],
        'all_sealed_regular_files_retained': True, 'all_failed_attempts_retained': True, 'zero_byte_locks_retained': True, 'full_objects_and_chunks_retained': True,
        'source_plan_population_role': 'retained source drafts and plans; qualification follows explicit actual native receipts only',
        'semantic_fact_count_verified': len(read_document(reader, plan['semantic_policy'])), 'native_attempt_count_fact_gated': len(plan['native_checks']),
        'builder': own_pin, 'codec': codec_pin, 'helper_pins': {name: reader.pin(path) for name, (path, _) in HELPERS.items()},
        'actual_aggregate_decoded_work_bytes': budget.decoded, 'actual_recursive_members': budget.members, 'actual_first_decoded_tar_readback_bytes': decoded_tars,
        'actual_first_decoded_member_readback_bytes': decoded_members, 'actual_outer_shard_codec_encode_invocations': len(shards), 'actual_first_outer_shard_codec_decode_invocations': len(shards),
        'actual_duplicate_verification_decoder_invocations': 0, 'exact_available_cached_credential_veto': True, 'bounded_complete_PEM_classifier_veto': True,
        'scan_hits': [], 'universal_secret_free_claim': False, 'source_atomic': False, 'raw_external_dependency_bodies_published': False,
        'old_HF_bundle_reuploaded': False, 'prior_HF_commit': plan['prior_HF_commit'], 'external_dependencies': plan.get('external_dependencies', {}),
        'remote_parent_verified_here': False, 'public_upload_performed': False, 'remote_mutations': 0, 'new_native_qualification_jobs': 0,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False, 'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN'}
    manifest_pin = reader.write(public / 'manifest.json', manifest)
    for path in staging.iterdir():
        path.unlink()
    staging.rmdir()
    budget.check()
    reader.write(output / 'closed.json', {'schema': 'ranker-convergence-local-package-attempt@1', 'status': 'passed_local_frozen_package', 'manifest': manifest_pin,
        'candidate_hits': 0, 'source_drift_count': 0, 'public_upload_performed': False, 'remote_mutations': 0, 'native_qualification_jobs': 0, 'cleanup_errors': []})
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
        if getattr(args, 'owned_output', False) and not (args.output / 'closed.json').exists():
            raw = wire({'schema': 'ranker-convergence-local-package-attempt@1', 'status': 'failed_partial_local_evidence_retained',
                'error_type': type(error).__name__, 'private_partial_evidence_retained': True, 'cleanup_attempted': False, 'public_upload_performed': False, 'remote_mutations': 0}) + b'\n'
            with (args.output / 'closed.json').open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        raise
    print(json.dumps(result, sort_keys=True))
