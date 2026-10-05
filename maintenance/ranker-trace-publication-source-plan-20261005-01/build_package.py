"""Package exact closed finite-ranker evidence locally; no Git, upload or native jobs.

The externally pinned closed-inputs descriptor binds the final selected inventory,
including this executed builder. The fixed policy binds actual observed outcomes.
The publication-only decoder profile does not alter solver or metadata bounds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import types

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = WORKSPACE / 'maintenance/ranker-trace-publication-source-plan-20261005-01'
HF = WORKSPACE / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
QUALIFIER = WORKSPACE / 'qualification/codebase_ir/ranker-trace-authentication-20261005-01'
ROOT_AUDIT = WORKSPACE / 'maintenance/ranker-trace-publication-root-20261005-01'
SCOPES = [QUALIFIER, WORKSPACE / 'qualification/codebase_ir/ranker-trace-authentication-source-review-20261005-01',
          WORKSPACE / 'qualification/codebase_ir/ranker-convergence-obligations-20261005-01']
SOURCE_PINS = {
    'external/ipfs_accelerate/benchmarks/agent_supervisor/container_coding/terminal_codebase_ranker_trace_authentication.py':
        'd89e83376367b3114cca967797677e0982a27cab78797ebfca0d7a1c1807c364',
    'external/ipfs_accelerate/test/api/test_terminal_codebase_ranker_trace_authentication.py':
        '5e5d1791233b279654b2e616866e7b73d5028c6cf64d5b0f805b29a07e56092d',
}
HELPERS = {
    'reader': (HF / 'successor-source-model-package-03/build_package.py',
               '8c8eab266a053115cdf0ea11a8aea5323611c2ab049ec1541383831618e385ce'),
    'archive': (HF / 'build_evidence_archive_02.py',
                'f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036'),
    'classifier': (HF / 'classify_and_prepare_public_archive_07.py',
                   'dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8'),
}
DOCUMENT_PATHS = {
    'qualified_review': QUALIFIER / 'file-only-review-01.json',
    'file_seal': QUALIFIER / 'file-only-seal-01.json',
    'source_review': SCOPES[1] / 'review.json',
    'obligations_review': SCOPES[2] / 'review.json',
    'native_authentication': QUALIFIER / 'evidence/actual-01/authentication-result.json',
    'metadata_readback': QUALIFIER / 'evidence/metadata-01/metadata-readback.json',
    'source_snapshot': QUALIFIER / 'evidence/metadata-01/source-snapshot.json',
    'positive_lean_check': QUALIFIER / 'evidence/lean-02/lean-finite_native_observation_order-check.json',
    'negative_lean_check': QUALIFIER / 'evidence/lean-02/lean-false_reversed_observation_chain-check.json',
    'inconclusive_lean_check': QUALIFIER / 'evidence/actual-01/lean-finite_native_observation_order-check.json',
    'finite_mapping': QUALIFIER / 'evidence/lean-02/finite-objective-mapping.json',
    'tests_closure': QUALIFIER / 'evidence/tests-01/closed.json',
    'root_join': ROOT_AUDIT / 'independent-qualified-join-01.json',
}
# The closure descriptor supplies the exact reviewed pins for these new files.
# Nothing discovered in a later walk may enlarge this list.
ADDITION_PATHS = [QUALIFIER / 'file-only-seal-01.json', SCOPES[1] / 'review.json',
    SCOPES[2] / 'review.json', ROOT / 'build_package.py', ROOT / 'review_package.py',
    ROOT / 'plan.json', ROOT / 'required-facts.json',
    ROOT_AUDIT / 'verify_closed_qualification.py', ROOT_AUDIT / 'independent-qualified-join-01.json',
    *[WORKSPACE / p for p in SOURCE_PINS]]
LOCK_RELATIVES = ('evidence/actual-01/resources.json.lock', 'evidence/lean-02/resources.json.lock',
    'evidence/metadata-01/resources.json.lock', 'evidence/tests-01/resources.json.lock',
    'evidence/metadata-01/metadata/owner.lock', 'evidence/metadata-01/metadata/lake/owner.lock')
BLOCK = 1024 * 1024
FILE_MAX = 16 * BLOCK
TOTAL_MAX = 64 * BLOCK
DECODE_MAX = 512 * BLOCK
SHARD_MAX = 256 * BLOCK
POLICY_SHA256 = '256f52449c65b8c7e477349af63d1dad6cbc24b73949fd957a6b63499ce47833'
FIXED_CRITICAL_SHA256 = {
    'qualified_review': 'd1809dca6471ba8640f03805d6ed1ef557a7879887664de9ec712abac90c0e8f',
    'file_seal': '8ea31286ffda2a5f08b4820bcc6ccf9ee05f133b96018132378f8c96ec16f438',
    'root_join': '2850d5e7598e84b1696faa447cb45da92f897b6764ae97a03f457912758ad712',
}


def load_source(path, expected, name):
    if path.resolve(strict=True) != path or path.is_symlink():
        raise ValueError('canonical frozen helper required')
    raw = path.read_bytes()
    if len(raw) > FILE_MAX or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('frozen helper source pin changed')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def pointer(value, path):
    for field in path.strip('/').split('/') if path else []:
        field = field.replace('~1', '/').replace('~0', '~')
        value = value[int(field)] if isinstance(value, list) else value[field]
    return value


def check_closed_inputs(reader, path, expected):
    binding = reader.pin(path)
    if binding['sha256'] != expected:
        raise ValueError('independent closed-inputs manifest pin changed')
    body = json.loads(reader.read_regular(path)[0])
    if (body.get('schema') != 'ranker-trace-publication-closed-inputs@1' or
            body.get('source_and_artifacts_quiet') is not True or
            body.get('scopes') != [str(p) for p in SCOPES] or body.get('source_pins') != SOURCE_PINS):
        raise ValueError('exact closed quiet scopes and new source pins required')
    if set(body.get('documents', {})) != set(DOCUMENT_PATHS):
        raise ValueError('complete exact closed document bindings required')
    documents = {}
    for name, selected in DOCUMENT_PATHS.items():
        descriptor = body['documents'][name]
        if descriptor.get('path') != str(selected) or reader.pin(selected) != descriptor:
            raise ValueError('closed document pin changed')
        if name in FIXED_CRITICAL_SHA256 and descriptor['sha256'] != FIXED_CRITICAL_SHA256[name]:
            raise ValueError('fixed qualification closure pin changed')
        documents[name] = json.loads(reader.read_regular(selected)[0])
    policy_path = ROOT / 'required-facts.json'
    if reader.pin(policy_path)['sha256'] != POLICY_SHA256:
        raise ValueError('fixed semantic outcome policy changed')
    facts = json.loads(reader.read_regular(policy_path)[0])
    if reader.wire(body.get('required_facts')) != reader.wire(facts) or len(facts) != 202:
        raise ValueError('exact observed semantic policy required')
    for fact in facts:
        if reader.wire(pointer(documents[fact['document']], fact['pointer'])) != reader.wire(fact['equals']):
            raise ValueError('closed qualification fact differs')
    if len(documents['metadata_readback']['family_counts']) != 29:
        raise ValueError('exact observed 29-family readback required')
    auth = documents['native_authentication']
    if len(auth['authenticated_states']) != 129 or len(documents['finite_mapping']['loss_units']) != 129:
        raise ValueError('all authenticated states and exact observed units required')
    if documents['file_seal']['review'] != body['documents']['qualified_review']:
        raise ValueError('seal must bind the final qualified review')
    additions = body.get('explicit_additions', [])
    if {p['path'] for p in additions} != {str(p) for p in ADDITION_PATHS} or len(additions) != len(ADDITION_PATHS):
        raise ValueError('only fixed explicit additional new files permitted')
    for descriptor in additions:
        if reader.pin(Path(descriptor['path'])) != descriptor:
            raise ValueError('explicit additional file pin changed')
    for relative, expected_source in SOURCE_PINS.items():
        if reader.pin(WORKSPACE / relative)['sha256'] != expected_source:
            raise ValueError('qualified new source changed')
    return body, binding, documents


def verify_seal(reader, body, documents, files, exclusions):
    """Rehash all 203 sealed leaves, including the six excluded zero-byte locks."""
    sealed = documents['file_seal']['files']
    if len(sealed) != 203 or len({p['path'] for p in sealed}) != 203:
        raise ValueError('exact unique 203-file seal required')
    if hashlib.sha256(json.dumps(sealed, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest() != documents['file_seal']['file_inventory_sha256']:
        raise ValueError('seal inventory digest changed')
    locks = {str(QUALIFIER / p) for p in LOCK_RELATIVES}
    for descriptor in sealed:
        path = Path(descriptor['path'])
        if not path.is_relative_to(QUALIFIER) or reader.pin(path) != descriptor:
            raise ValueError('sealed file changed')
        if str(path) in locks and descriptor['bytes'] != 0:
            raise ValueError('declared ephemeral locks must remain empty')
    if {p['path'] for p in exclusions} != locks or any(p['kind'] != 'transient_lock' for p in exclusions):
        raise ValueError('only six exact sealed ephemeral locks may be excluded')
    expected_files = ({p['path'] for p in sealed} - locks) | {p['path'] for p in body['explicit_additions']}
    if {str(p) for p in files} != expected_files or len(files) != len(expected_files):
        raise ValueError('selected population differs from seal plus fixed additions')
    return {'sealed_file_count_rehashed': 203, 'sealed_lock_bindings_rehashed': 6,
            'sealed_durable_leaves_selected': 197, 'explicit_additions': len(body['explicit_additions'])}


def verify_final_selection(reader, body, files, exclusions, directories):
    # External closed-inputs SHA256 pins this descriptor, so the selected builder
    # can be included without a circular self-digest or a later unbound walk.
    descriptor = body['final_selection']
    if Path(descriptor['path']) != ROOT / 'final-selection.json' or reader.pin(Path(descriptor['path'])) != descriptor:
        raise ValueError('final independently reviewed selection manifest changed')
    selected = json.loads(reader.read_regular(Path(descriptor['path']))[0])
    actual = [{**reader.pin(path), 'stat': reader.signature(path.lstat())} for path in files]
    if (selected.get('schema') != 'ranker-trace-publication-final-selection@1' or
            selected.get('files') != actual or selected.get('exclusions') != exclusions or
            selected.get('directories') != directories):
        raise ValueError('durable inventory/exclusions/stats differ from final selected population')
    return selected


def tar_item(row):
    item = tarfile.TarInfo(row['path'])
    item.size, item.mode = row['bytes'], 0o644
    item.uid = item.gid = item.mtime = 0
    item.uname = item.gname = ''
    return item


def split_shards(rows):
    """Account exact GNU long-name headers and complete tar record padding."""
    groups, current, count = [], [], 0
    for row in rows:
        needed = len(tar_item(row).tobuf(format=tarfile.GNU_FORMAT)) + ((row['bytes'] + 511) // 512) * 512
        complete = lambda n: ((n + 1024 + tarfile.RECORDSIZE - 1) // tarfile.RECORDSIZE) * tarfile.RECORDSIZE
        if complete(needed) > FILE_MAX:
            raise ValueError('one member cannot fit unchanged decoded-container bound')
        if current and complete(count + needed) > FILE_MAX:
            groups.append(current)
            current, count = [], 0
        current.append(row)
        count += needed
    if current:
        groups.append(current)
    return groups


def readback(inspection, shard, tar_pin, rows):
    verification_bytes = 0
    with shard.open('rb') as encoded, tempfile.TemporaryFile(dir=inspection.temporary) as decoded:
        inspection.zstd(encoded, decoded)
        decoded.seek(0)
        digest = hashlib.sha256()
        while block := decoded.read(BLOCK):
            verification_bytes += len(block)
            # Classifier.zstd.copy enforces per-container bounds but does not
            # charge its output. Explicitly include this extra verification pass.
            inspection.budget.charge(len(block), verification_bytes)
            digest.update(block)
        if verification_bytes != tar_pin['bytes'] or digest.hexdigest() != tar_pin['sha256']:
            raise ValueError('full decoded tar bytes differ')
        decoded.seek(0)
        with tarfile.open(fileobj=decoded, mode='r:') as archive:
            members = archive.getmembers()
            if len(members) != len(rows):
                raise ValueError('decoded member population differs')
            for row, member in zip(rows, members):
                inspection.budget.check()
                if (not member.isfile() or member.name != row['path'] or member.size != row['bytes'] or
                        member.mode != 0o644 or member.uid != 0 or member.gid != 0 or member.mtime != 0):
                    raise ValueError('decoded member identity differs')
                digest, count = hashlib.sha256(), 0
                with archive.extractfile(member) as stream:
                    while block := stream.read(BLOCK):
                        count += len(block)
                        digest.update(block)
                        inspection.budget.check()
                if count != row['bytes'] or digest.hexdigest() != row['sha256']:
                    raise ValueError('decoded member bytes differ')
    return verification_bytes


def build(args):
    reader = load_source(*HELPERS['reader'], 'ranker_trace_frozen_reader')
    builder_pin = reader.pin(Path(__file__).resolve())
    body, closure_pin, documents = check_closed_inputs(reader, args.closed_inputs, args.expected_closed_inputs_sha256)
    output = args.output
    if (not output.is_absolute() or output.resolve() != output or output.exists() or
            not output.parent.is_dir() or not output.is_relative_to(WORKSPACE / 'maintenance')):
        raise ValueError('new canonical maintenance package directory required')
    reader.SCOPES = SCOPES
    reader.SOURCE_FILES = [p for p in ADDITION_PATHS if not any(p.is_relative_to(scope) for scope in SCOPES)]
    files, exclusions, directories = reader.inventory()
    verify_final_selection(reader, body, files, exclusions, directories)
    seal_before = verify_seal(reader, body, documents, files, exclusions)
    archive = load_source(*HELPERS['archive'], 'ranker_trace_frozen_archive')
    classifier = load_source(*HELPERS['classifier'], 'ranker_trace_frozen_classifier')
    scanner = archive.Scanner()
    scanner.patterns = [(name, pattern) for name, pattern in archive.PATTERNS if name != 'private_key_pem']
    budget = classifier.Budget(seconds=180, decoded_bytes=DECODE_MAX, container_bytes=FILE_MAX, members=10000, depth=6)
    output.mkdir(mode=0o700)
    args.owned_output = True
    staging, public = output / 'private-staging', output / 'package'
    staging.mkdir(mode=0o700)
    public.mkdir(mode=0o700)
    reader.write(output / 'started.json', {'schema':'ranker-trace-local-package-attempt@1',
        'closed_inputs':closure_pin, 'builder':builder_pin, 'status':'started', 'remote_mutations':0})
    rows, sources, total = [], {}, 0
    for index, source in enumerate(files):
        budget.check()
        raw, signature = reader.read_regular(source)
        total += len(raw)
        if total > TOTAL_MAX:
            raise ValueError('selected increment exceeds unchanged raw population bound')
        target = staging / ('file-%06d' % index)
        with target.open('xb') as stream:
            stream.write(raw)
        inspection = classifier.Classifier(scanner, budget, staging)
        with target.open('rb') as stream:
            inspection.inspect(stream)
        if inspection.hits:
            raise ValueError('credential-pattern or exact cached-value veto refused export')
        name = str(source.relative_to(WORKSPACE))
        rows.append({'path':name, 'source_path':str(source), 'bytes':len(raw),
            'sha256':hashlib.sha256(raw).hexdigest(), 'source_stat':signature,
            'scan_counts':dict(inspection.counts), 'scan_hits':[]})
        sources[name] = target
    zstd, shards, manual_bytes = Path('/usr/bin/zstd'), [], 0
    zstd_pin = reader.pin(zstd)
    for index, group in enumerate(split_shards(rows)):
        budget.check()
        tarpath = staging / ('data-%06d.tar' % index)
        with tarfile.open(tarpath, 'w', format=tarfile.GNU_FORMAT) as sink:
            for row in group:
                with sources[row['path']].open('rb') as stream:
                    sink.addfile(tar_item(row), stream)
        tar_pin = reader.pin(tarpath)
        if tar_pin['bytes'] > FILE_MAX:
            raise ValueError('complete decoded tar exceeds unchanged 16 MiB container bound')
        shard = public / ('data-%06d.tar.zst' % index)
        with shard.open('xb') as stream:
            subprocess.run([str(zstd), '-T1', '-3', '--quiet', '--stdout', str(tarpath)],
                           stdout=stream, stderr=subprocess.PIPE, check=True, timeout=60)
        if shard.stat().st_size > SHARD_MAX or reader.pin(zstd) != zstd_pin:
            raise ValueError('compressed shard/tool pin differs')
        inspection = classifier.Classifier(scanner, budget, staging)
        with shard.open('rb') as stream:
            inspection.inspect(stream)
        if inspection.hits:
            raise ValueError('recursive compressed-shard veto refused export')
        manual_bytes += readback(inspection, shard, tar_pin, group)
        shards.append({**reader.pin(shard), 'archive':shard.name,
            'decoded_tar_bytes':tar_pin['bytes'], 'decoded_tar_sha256':tar_pin['sha256'],
            'members':len(group), 'scan_counts':dict(inspection.counts), 'scan_hits':[],
            'decoded_per_file_readback_verified':True})
        for row in group:
            row.update(archive=shard.name, member=row['path'])
    if reader.inventory() != (files, exclusions, directories):
        raise ValueError('selected population or stat changed during packaging')
    verify_final_selection(reader, body, files, exclusions, directories)
    seal_after = verify_seal(reader, body, documents, files, exclusions)
    if check_closed_inputs(reader, args.closed_inputs, args.expected_closed_inputs_sha256) != (body, closure_pin, documents):
        raise ValueError('closed qualification inputs changed')
    for path, expected in HELPERS.values():
        if reader.pin(path)['sha256'] != expected:
            raise ValueError('frozen helper source changed during packaging')
    if reader.pin(Path(__file__).resolve()) != builder_pin or reader.pin(zstd) != zstd_pin:
        raise ValueError('executed builder or codec source changed')
    manifest = {'schema':'ranker-trace-frozen-evidence-package@1',
        'status':'closed_scanned_local_package_not_uploaded', 'closed_inputs':closure_pin,
        'final_selection':body['final_selection'], 'semantic_policy':reader.pin(ROOT / 'required-facts.json'),
        'files':rows, 'file_count':len(rows), 'original_file_bytes':total, 'data_shards':shards,
        'exclusions':exclusions, 'scope_roots':[str(p) for p in SCOPES], 'explicit_additions':body['explicit_additions'],
        'seal_binding_before':seal_before, 'seal_binding_after':seal_after,
        'helper_pins':{k:reader.pin(v[0]) for k,v in HELPERS.items()}, 'builder':builder_pin, 'codec':zstd_pin,
        'publication_decode_profile':{'raw_population_max':TOTAL_MAX, 'per_file_max':FILE_MAX,
            'per_decoded_container_max':FILE_MAX, 'compressed_shard_max':SHARD_MAX,
            'aggregate_decoded_work_max':DECODE_MAX, 'wall_seconds':180, 'members_max':10000, 'depth_max':6,
            'authority':'explicit root authorization for publication-only decoded work; native solver and metadata bounds unchanged'},
        'actual_aggregate_decoded_work_bytes':budget.decoded, 'actual_verification_decode_bytes':manual_bytes,
        'actual_recursive_classifier_decoded_bytes':budget.decoded-manual_bytes, 'actual_recursive_members':budget.members,
        'exact_available_cached_credential_veto':True, 'bounded_complete_PEM_classifier_veto':True,
        'scan_hits':[], 'universal_secret_free_claim':False,
        'old_sealed_evidence_references_not_copied':True, 'source_atomic':False,
        'whole_source_runtime_equivalence_proved':False, 'full_task_satisfaction_proved':False,
        'asymptotic_optimizer_convergence_proved':False, 'global_autoencoder_convergence_proved':False,
        'all32_governing_RPI_exits':'OPEN', 'proof_authority':False,
        'execution_authority':False, 'completion_authority':False, 'remote_mutations':0,
        'new_qualification_jobs':0, 'first_inconclusive_lean_attempt_retained':True}
    manifest_pin = reader.write(public / 'manifest.json', manifest)
    for source in staging.iterdir():
        source.unlink()
    staging.rmdir()
    reader.write(output / 'closed.json', {'schema':'ranker-trace-local-package-attempt@1',
        'status':'passed_local_frozen_package', 'manifest':manifest_pin,
        'source_drift_count':0, 'candidate_hits':0, 'public_upload_performed':False,
        'remote_mutations':0, 'new_qualification_jobs':0, 'cleanup_errors':[]})
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
        # A failed attempt remains private and cannot satisfy the passed receipt.
        if getattr(args, 'owned_output', False) and args.output.is_dir() and not (args.output / 'closed.json').exists():
            raw = (json.dumps({'schema':'ranker-trace-local-package-attempt@1',
                'status':'failed_partial_local_evidence_retained', 'error_type':type(error).__name__,
                'public_upload_performed':False, 'remote_mutations':0, 'cleanup_errors':[]},sort_keys=True)+'\n').encode()
            with (args.output / 'closed.json').open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        raise
    print(json.dumps(result, sort_keys=True))
