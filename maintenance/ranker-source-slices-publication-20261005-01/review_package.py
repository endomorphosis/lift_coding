"""Read and independently verify every decoded member of the sealed local package.

This file-only review does not run qualifications, import project code, change
source files, modify Git, or contact a remote. Frozen reader/classifier/member
verification sources are reused; population and pin joins are checked here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tarfile
import tempfile
import time
import types

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = WORKSPACE / 'maintenance/ranker-source-slices-publication-20261005-01'
QUALIFIER = WORKSPACE / 'qualification/codebase_ir/ranker-source-semantics-20261005-01'
SOURCE_PLAN = WORKSPACE / 'qualification/codebase_ir/ranker-source-semantics-source-plan-20261005-01'
HF = WORKSPACE / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
BLOCK, RAW_MAX, MEMBER_MAX, TAR_MAX, DECODE_MAX = 1024**2, 256*1024**2, 14*1024**2, 16*1024**2, 1024**3
PROFILE = {'raw_population_max': RAW_MAX, 'raw_member_sum_per_shard_max': MEMBER_MAX, 'per_file_max': MEMBER_MAX,
    'complete_decoded_tar_max': TAR_MAX, 'compressed_shard_max': TAR_MAX, 'aggregate_decoded_work_max': DECODE_MAX,
    'wall_seconds': 180, 'members_max': 10000, 'depth_max': 6, 'shards_max': 64, 'zstd_args': ['-T1', '-3'],
    'duplicate_verification_decoder_invocations': 0, 'member_readback_profile': 'same_first_decoded_tar_and_member_streams@1',
    'native_qualification_limits_changed': False}
HELPERS = {
    'archive': (HF / 'build_evidence_archive_02.py', 'f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036'),
    'classifier': (HF / 'classify_and_prepare_public_archive_07.py', 'dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8'),
    'member_verifier': (WORKSPACE / 'maintenance/ranker-curvature-publication-source-plan-20261005-01/build_package.py', '4e14c08fc6d680e5fcbf755f649284f750353b73b42dd08b926398f4c43c9a93'),
}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def signature(info):
    return {key: getattr(info, 'st_' + key) for key in ('dev', 'ino', 'mode', 'nlink', 'uid', 'gid', 'size', 'mtime_ns', 'ctime_ns')}


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= TAR_MAX, 'bounded regular input required')
        parts, total = [], 0
        while block := os.read(fd, BLOCK):
            total += len(block)
            need(total <= TAR_MAX, 'input grew beyond bound')
            parts.append(block)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and total == before.st_size, 'input changed during read')
        return b''.join(parts)
    finally:
        os.close(fd)


def pin(path):
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def descriptor(row):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and type(row['path']) is str and type(row['bytes']) is int and
        0 <= row['bytes'] <= TAR_MAX and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None, 'exact bounded descriptor required')
    path = Path(row['path'])
    need(pin(path) == row, 'descriptor bytes differ')
    return path


def document(row):
    path = descriptor(row)
    raw = read(path)
    need(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], 'parsed document bytes differ from descriptor')
    return json.loads(raw)


def pointer(value, path):
    need(type(path) is str and (not path or path.startswith('/')), 'JSON pointer required')
    for part in path[1:].split('/') if path else []:
        key = part.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if type(value) is list else value[key]
    return value


def load(name):
    path, expected = HELPERS[name]
    raw = read(path)
    need(hashlib.sha256(raw).hexdigest() == expected, 'frozen review helper source differs')
    module = types.ModuleType('held_convergence_package_review_' + name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def population(plan, documents):
    seal = documents['file_seal']
    sealed = seal['files']
    need(len(sealed) == len({row['path'] for row in sealed}) == seal['regular_file_count'] and
        sum(row['bytes'] for row in sealed) == seal['regular_file_bytes'] <= RAW_MAX and
        hashlib.sha256(wire(sealed)).hexdigest() == seal['file_inventory_sha256'] and seal.get('fixture_symlinks', []) == [], 'complete exact no-alias regular seal required')
    excluded = {Path(name) for name in plan['excluded_dependency_subtrees']}
    need(plan['excluded_dependency_subtrees'] == seal.get('excluded_dependency_subtrees', []) and all(path.is_relative_to(QUALIFIER) and path != QUALIFIER for path in excluded), 'only sealed dependency exclusions required')
    found, exclusions, directories = [], [], []
    def visit(path):
        info = path.lstat()
        need(not stat.S_ISLNK(info.st_mode) and path.resolve(strict=True) == path, 'undeclared symlink/referral refused')
        if path in excluded:
            need(stat.S_ISDIR(info.st_mode), 'excluded dependency directory required')
            exclusions.append({'path': str(path), 'kind': 'external_dependency_subtree', 'stat': signature(info)})
        elif stat.S_ISDIR(info.st_mode):
            directories.append({'path': str(path), 'stat': signature(info)})
            for child in sorted(path.iterdir(), key=lambda item: os.fsencode(item.name)):
                visit(child)
        else:
            need(stat.S_ISREG(info.st_mode) and info.st_size <= MEMBER_MAX, 'bounded owned regular evidence required')
            found.append(path)
    visit(QUALIFIER)
    seal_path = descriptor(plan['documents']['file_seal'])
    need({str(path) for path in found} == {row['path'] for row in sealed} | {str(seal_path)}, 'Q3 census must retain every sealed regular leaf and seal self-file')
    for row in sealed:
        path = descriptor(row)
        need(path.is_relative_to(QUALIFIER) and not any(path.is_relative_to(root) for root in excluded), 'sealed file left owned scope')
    visit(SOURCE_PLAN)
    required = {str(ROOT / name) for name in ('build_package.py', 'review_package.py', 'freeze_inputs.py', 'required-facts.json')} | {str(seal_path)}
    need(required <= {row['path'] for row in plan['explicit_additions']}, 'all executed publication sources and seal self-file required')
    for row in plan['explicit_additions']:
        path = descriptor(row)
        need((path.is_relative_to(ROOT) or path.is_relative_to(QUALIFIER)) and path.name not in ('plan.json', 'closed-inputs.json', 'final-selection.json'), 'owned non-self-referential addition required')
        if path not in found:
            visit(path)
    need(len(found) == len(set(found)) <= 10000, 'unique complete regular population required')
    rows = [{**pin(path), 'stat': signature(path.lstat())} for path in sorted(found, key=lambda path: os.fsencode(str(path.relative_to(WORKSPACE))))]
    need(sum(row['bytes'] for row in rows) <= RAW_MAX, 'full selected population exceeds fixed raw cap')
    return rows, exclusions, directories


def review(args):
    started = time.monotonic()
    own = pin(Path(__file__).resolve())
    closure_raw = read(args.closed_inputs)
    closure_pin = {'path': str(args.closed_inputs), 'bytes': len(closure_raw), 'sha256': hashlib.sha256(closure_raw).hexdigest()}
    need(args.closed_inputs == ROOT / 'closed-inputs.json' and closure_pin['sha256'] == args.expected_closed_inputs_sha256, 'externally pinned fixed closure required')
    closure = json.loads(closure_raw)
    need(closure['schema'] == 'ranker-source-slices-publication-closed-inputs@1' and closure['publication_profile'] == PROFILE, 'exact closure schema/profile required')
    plan = document(closure['plan'])
    need(descriptor(closure['plan']) == ROOT / 'plan.json' and plan.get('schema') == 'ranker-source-slices-publication-plan@1' and
        plan.get('status') == 'frozen_final_plan' and plan.get('source_and_artifacts_quiet') is True and plan.get('source_plan_quiet') is True and
        plan.get('scope_root') == str(QUALIFIER) and plan.get('source_plan_root') == str(SOURCE_PLAN) and plan.get('publication_profile') == PROFILE, 'root-frozen quiet owned plan required')
    documents = {name: document(row) for name, row in plan['documents'].items()}
    seal, qualified = documents['file_seal'], documents['qualified_review']
    need(seal['schema'] == plan['seal_schema'] and qualified['schema'] == plan['review_schema'] and qualified['status'] == 'passed' and
        seal['review'] == plan['documents']['qualified_review'], 'sealed final passed qualification review required')
    need(all(qualified.get(key) is False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')) and
        qualified.get('full_task_satisfaction') == 'unknown' and qualified.get('all32_governing_RPI_exits') == 'OPEN', 'qualification cannot grant operational/full-task authority')
    need(descriptor(plan['semantic_policy']) == ROOT / 'required-facts.json', 'fixed semantic policy required')
    facts = document(plan['semantic_policy'])
    need(type(facts) is list and 0 < len(facts) <= 5000, 'nonempty explicit observed-fact policy required')
    keys = set()
    for fact in facts:
        need(set(fact) == {'document', 'pointer', 'equals'} and fact['document'] in documents, 'exact semantic fact required')
        key = (fact['document'], fact['pointer'])
        need(key not in keys and wire(pointer(documents[fact['document']], fact['pointer'])) == wire(fact['equals']), 'duplicate or mismatched semantic fact')
        keys.add(key)
    attempts = {row['path'] for row in seal['files'] if Path(row['path']).name == 'check-result.json'}
    need({plan['documents'][name]['path'] for name in plan['native_checks']} == attempts and len(plan['native_checks']) == len(attempts) and
        all((name, '/status') in keys for name in plan['native_checks']), 'complete fact-gated native attempt denominator required')
    rows, exclusions, directories = population(plan, documents)
    selection = document(closure['final_selection'])
    need(descriptor(closure['final_selection']) == ROOT / 'final-selection.json' and selection['files'] == rows and selection['exclusions'] == exclusions and
        selection['directories'] == directories, 'exact full frozen selection required')
    manifest_raw = read(args.manifest)
    manifest_pin = {'path': str(args.manifest), 'bytes': len(manifest_raw), 'sha256': hashlib.sha256(manifest_raw).hexdigest()}
    need(manifest_pin['sha256'] == args.expected_manifest_sha256 and args.manifest.parent.name == 'package' and
        args.manifest.parent.parent.parent == WORKSPACE / 'maintenance' and args.manifest.parent.parent.name.startswith('ranker-source-slices-publication-package-'), 'owned externally pinned package manifest required')
    manifest = json.loads(manifest_raw)
    need(manifest['schema'] == 'ranker-source-slices-frozen-evidence-package@1' and manifest['status'] == 'closed_scanned_local_package_not_uploaded' and
        manifest['closed_inputs'] == closure_pin and manifest['plan'] == closure['plan'] and manifest['final_selection'] == closure['final_selection'] and
        manifest['semantic_policy'] == plan['semantic_policy'] and manifest['publication_profile'] == PROFILE, 'manifest closure/profile joins differ')
    expected = [{key: row[key] for key in ('path', 'bytes', 'sha256', 'stat')} for row in rows]
    observed = [{'path': row['source_path'], 'bytes': row['bytes'], 'sha256': row['sha256'], 'stat': row['source_stat']} for row in manifest['files']]
    need(observed == expected and manifest['file_count'] == len(rows) and manifest['original_file_bytes'] == sum(row['bytes'] for row in rows) and
        manifest['exclusions'] == exclusions and manifest['scan_hits'] == [] and manifest['semantic_fact_count_verified'] == len(facts), 'every complete manifest member must match frozen selection')
    builder_path = descriptor(manifest['builder'])
    need(builder_path == ROOT / 'build_package.py' and manifest['builder']['sha256'] == args.expected_builder_sha256, 'externally pinned executed builder required')
    for name, (path, expected_sha) in HELPERS.items():
        need(manifest['helper_pins'][name] == pin(path) and pin(path)['sha256'] == expected_sha, 'executed frozen classifier/helper pin differs')
    need(descriptor(manifest['codec']) == Path('/usr/bin/zstd'), 'executed codec pin differs')
    archive, classifier, verifier = load('archive'), load('classifier'), load('member_verifier')
    scanner = archive.Scanner()
    scanner.patterns = [(name, pattern) for name, pattern in archive.PATTERNS if name != 'private_key_pem']
    need(time.monotonic() - started < 180, 'review wall budget exceeded before decode')
    budget = classifier.Budget(seconds=180-(time.monotonic()-started), decoded_bytes=DECODE_MAX, container_bytes=TAR_MAX, members=10000, depth=6)
    shards, counts, verified_members = manifest['data_shards'], [], 0
    need(0 < len(shards) <= PROFILE['shards_max'] and len({row['archive'] for row in shards}) == len(shards), 'unique bounded archive population required')
    assigned = []
    with tempfile.TemporaryDirectory(prefix='convergence-package-review-', dir=ROOT) as temporary:
        for index, shard in enumerate(shards):
            budget.check()
            need(shard['archive'] == 'data-%06d.tar.zst' % index and shard['path'] == str(args.manifest.parent / shard['archive']) and
                pin(Path(shard['path'])) == {key: shard[key] for key in ('path', 'bytes', 'sha256')}, 'exact compressed shard pin required')
            members = [row for row in manifest['files'] if row['archive'] == shard['archive']]
            need(len(members) == shard['members'] and members and sum(row['bytes'] for row in members) == shard['raw_member_bytes'] <= MEMBER_MAX and
                0 < shard['decoded_tar_bytes'] <= TAR_MAX and shard['bytes'] <= TAR_MAX, 'complete member count/raw/decoded shard bounds required')
            for row in members:
                need(row['path'] == row['member'] == str(Path(row['source_path']).relative_to(WORKSPACE)) and row['scan_hits'] == [], 'exact member name and scanned source binding required')
            assigned.extend(members)
            tar_pin = {'bytes': shard['decoded_tar_bytes'], 'sha256': shard['decoded_tar_sha256']}
            inspection = verifier.inspect_complete_shard(classifier, scanner, budget, Path(temporary), Path(shard['path']), tar_pin, members)
            verified_members += len(members)
            counts.append({'archive': shard['archive'], 'decoded_tar_bytes': inspection.decoded_tar_bytes,
                'decoded_member_bytes': inspection.decoded_member_bytes, 'members_verified': len(members)})
    need(assigned == manifest['files'] and verified_members == len(rows), 'every member exactly once in complete shard order required')
    package_closed_path = args.manifest.parent.parent / 'closed.json'
    package_closed = json.loads(read(package_closed_path))
    need(package_closed['status'] == 'passed_local_frozen_package' and package_closed['manifest'] == manifest_pin and package_closed['candidate_hits'] == 0 and
        package_closed['source_drift_count'] == 0 and package_closed['cleanup_errors'] == [], 'successful local package closure required')
    need(population(plan, documents) == (rows, exclusions, directories), 'complete source population/stat changed during decoded review')
    for row in [closure_pin, closure['plan'], closure['final_selection'], plan['semantic_policy'], manifest_pin, manifest['builder'], manifest['codec'], *plan['documents'].values(), *manifest['helper_pins'].values()]:
        descriptor(row)
    need(pin(Path(__file__).resolve()) == own, 'executed reviewer changed')
    budget.check()
    need(args.output == ROOT / 'package-review-01.json' and not args.output.exists(), 'fresh fixed reviewer receipt required')
    result = {'schema': 'ranker-source-slices-full-decoded-member-file-only-review@1', 'status': 'passed', 'reviewer': own, 'manifest': manifest_pin,
        'package_closure': pin(package_closed_path), 'closed_inputs': closure_pin, 'selected_files_verified_before_after': len(rows), 'decoded_members_verified': verified_members,
        'decoded_tar_shards': counts, 'actual_file_only_review_decoded_bytes': budget.decoded, 'actual_outer_shard_codec_decoder_invocations': len(shards),
        'publication_profile': PROFILE, 'sealed_file_count_rehashed': seal['regular_file_count'], 'sealed_file_bytes_rehashed': seal['regular_file_bytes'],
        'native_attempt_denominator_verified': len(attempts), 'semantic_fact_count_verified': len(facts), 'exact_frozen_semantic_outcome_facts_verified': True,
        'all_failed_attempts_retained': True, 'zero_byte_locks_retained': True, 'full_objects_and_chunks_retained': True, 'raw_external_dependency_bodies_published': False,
        'old_HF_bundle_reuploaded': False, 'source_atomic': False, 'project_imports': 0, 'new_native_qualification_jobs': 0, 'new_public_fits': 0, 'remote_mutations': 0,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False, 'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN'}
    with args.output.open('xb') as stream:
        stream.write(wire(result) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return pin(args.output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--closed-inputs', required=True, type=Path)
    parser.add_argument('--expected-closed-inputs-sha256', required=True)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--expected-builder-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(review(args), sort_keys=True))
