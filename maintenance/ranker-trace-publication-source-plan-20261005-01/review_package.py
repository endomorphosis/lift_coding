"""Independent file-only selected population and complete decoded-member review.

Only Python standard library and the pinned system zstd binary are used. This
performs no project imports, model replay, fit, SQL/storage or Lean invocation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import tarfile
import tempfile
import time

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = WORKSPACE / 'maintenance/ranker-trace-publication-source-plan-20261005-01'
QUALIFIER = WORKSPACE / 'qualification/codebase_ir/ranker-trace-authentication-20261005-01'
SCOPES = [QUALIFIER, WORKSPACE / 'qualification/codebase_ir/ranker-trace-authentication-source-review-20261005-01',
          WORKSPACE / 'qualification/codebase_ir/ranker-convergence-obligations-20261005-01']
LOCKS = {str(QUALIFIER / p) for p in ('evidence/actual-01/resources.json.lock',
    'evidence/lean-02/resources.json.lock', 'evidence/metadata-01/resources.json.lock',
    'evidence/tests-01/resources.json.lock', 'evidence/metadata-01/metadata/owner.lock',
    'evidence/metadata-01/metadata/lake/owner.lock')}
BLOCK = 1024 * 1024
FILE_MAX, RAW_MAX, DECODE_MAX, SHARD_MAX = 16 * BLOCK, 64 * BLOCK, 512 * BLOCK, 256 * BLOCK
POLICY_SHA = '256f52449c65b8c7e477349af63d1dad6cbc24b73949fd957a6b63499ce47833'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode() + b'\n'


def signature(info):
    return {key:getattr(info, 'st_' + key) for key in
        ('dev','ino','mode','nlink','uid','gid','size','mtime_ns','ctime_ns')}


def read_regular(path, maximum=FILE_MAX):
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular path required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, 'regular file bound differs')
        raw, total = [], 0
        while block := os.read(fd, BLOCK):
            total += len(block)
            need(total <= maximum, 'regular file growth exceeds bound')
            raw.append(block)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()), 'file stat changed')
        need(total == before.st_size, 'file bytes differ')
        return b''.join(raw), signature(before)
    finally:
        os.close(fd)


def pin(path, maximum=FILE_MAX):
    raw, _ = read_regular(path, maximum)
    return {'path':str(path), 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


def body(descriptor, maximum=FILE_MAX):
    path = Path(descriptor['path'])
    need(pin(path, maximum) == descriptor, 'descriptor pin changed')
    return json.loads(read_regular(path, maximum)[0])


def pointer(value, path):
    for key in path.strip('/').split('/') if path else []:
        key = key.replace('~1','/').replace('~0','~')
        value = value[int(key)] if isinstance(value,list) else value[key]
    return value


def inventory(extra):
    files, exclusions, directories = [], [], []
    def visit(path):
        info = path.lstat()
        need(path.resolve(strict=True) == path, 'inventory path resolution changed')
        if stat.S_ISDIR(info.st_mode):
            need(path.name != '__pycache__', 'undeclared bytecode directory')
            directories.append({'path':str(path),'stat':signature(info)})
            for child in sorted(path.iterdir(),key=lambda p:os.fsencode(p.name)):
                visit(child)
        elif path.name.endswith('.lock'):
            exclusions.append({'path':str(path), 'kind':'transient_lock',
                'reason':'closed_runtime_lock_not_durable_evidence', 'stat':signature(info)})
        else:
            need(stat.S_ISREG(info.st_mode), 'unexpected inventory node')
            files.append(path)
    for scope in SCOPES:
        visit(scope)
    for path in extra:
        visit(path)
    return sorted(files,key=lambda p:os.fsencode(str(p.relative_to(WORKSPACE)))), exclusions, directories


def verify_inputs(closure, selected, manifest):
    documents = {name:body(descriptor) for name,descriptor in closure['documents'].items()}
    facts = json.loads(read_regular(ROOT / 'required-facts.json')[0])
    need(pin(ROOT / 'required-facts.json')['sha256'] == POLICY_SHA and len(facts) == 202,
         'fixed policy changed')
    need(wire(closure['required_facts']) == wire(facts), 'closed policy changed')
    for fact in facts:
        need(wire(pointer(documents[fact['document']],fact['pointer'])) == wire(fact['equals']),
             'observed semantic fact changed')
    seal = documents['file_seal']
    need(seal['review'] == closure['documents']['qualified_review'], 'seal review differs')
    need(len(seal['files']) == 203 and len({p['path'] for p in seal['files']}) == 203, '203 unique seals required')
    need(hashlib.sha256(wire(seal['files'])[:-1]).hexdigest() == seal['file_inventory_sha256'],
         'compact no-newline seal inventory digest differs')
    for descriptor in seal['files']:
        need(Path(descriptor['path']).is_relative_to(QUALIFIER) and pin(Path(descriptor['path'])) == descriptor,
             'sealed leaf changed')
        if descriptor['path'] in LOCKS:
            need(descriptor['bytes'] == 0, 'sealed ephemeral lock is nonempty')
    additions = closure['explicit_additions']
    for descriptor in additions:
        need(pin(Path(descriptor['path'])) == descriptor, 'explicit addition changed')
    extra = [Path(p['path']) for p in additions if not any(Path(p['path']).is_relative_to(s) for s in SCOPES)]
    files, exclusions, directories = inventory(extra)
    expected = ({p['path'] for p in seal['files']} - LOCKS) | {p['path'] for p in additions}
    need({str(p) for p in files} == expected and len(files) == len(expected), 'sealed selected population differs')
    actual = [{**pin(p), 'stat':signature(p.lstat())} for p in files]
    need(actual == selected['files'] and exclusions == selected['exclusions'] and directories == selected['directories'],
         'selected inventory/hash/stat differs')
    need({p['path'] for p in exclusions} == LOCKS and len(exclusions) == 6, 'exact lock exclusions required')
    need(len(manifest['files']) == len(actual) and manifest['file_count'] == len(actual), 'manifest population differs')
    for row, source in zip(manifest['files'], actual):
        need({k:row[k] for k in ('source_path','bytes','sha256')} ==
             {'source_path':source['path'],'bytes':source['bytes'],'sha256':source['sha256']}, 'manifest source pin differs')
        need(row['source_stat'] == source['stat'] and row['path'] == str(Path(source['path']).relative_to(WORKSPACE))
             and row['member'] == row['path'] and row['scan_hits'] == [], 'manifest selected identity differs')
    need(sum(p['bytes'] for p in actual) == manifest['original_file_bytes'] <= RAW_MAX, 'raw population bound differs')
    for descriptor in manifest['helper_pins'].values():
        need(pin(Path(descriptor['path'])) == descriptor, 'executed helper changed')
    need(pin(Path(manifest['builder']['path'])) == manifest['builder'], 'executed builder changed')
    need(pin(Path(manifest['codec']['path'])) == manifest['codec'], 'codec changed')
    return len(files)


def decode(shard, codec, temporary, deadline, remaining):
    """Stream with concurrent wall and output bounds; never extract to a path."""
    child = subprocess.Popen([str(codec),'--quiet','-d','--stdout',str(shard)],
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
    selector, count, digest = selectors.DefaultSelector(), 0, hashlib.sha256()
    selector.register(child.stdout,selectors.EVENT_READ)
    try:
        while True:
            seconds = deadline-time.monotonic()
            need(seconds > 0, 'file-only review wall bound exceeded')
            events = selector.select(min(seconds,1))
            if not events:
                continue
            block = os.read(child.stdout.fileno(),BLOCK)
            if not block:
                break
            count += len(block)
            need(count <= FILE_MAX and count <= remaining, 'file-only decoded work/container bound exceeded')
            digest.update(block)
            temporary.write(block)
        need(child.wait(timeout=max(0.01,deadline-time.monotonic())) == 0, 'pinned zstd decode failed')
        temporary.seek(0)
        return count,digest.hexdigest()
    finally:
        selector.close()
        child.stdout.close()
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGKILL)
            child.wait()


def review(args):
    deadline = time.monotonic()+180
    own_pin = pin(Path(__file__).resolve())
    manifest_pin, closure_pin = pin(args.manifest), pin(args.closed_inputs)
    need(manifest_pin['sha256'] == args.expected_manifest_sha256 and
         closure_pin['sha256'] == args.expected_closed_inputs_sha256, 'independent expected pins differ')
    manifest, closure = body(manifest_pin), body(closure_pin)
    selected = body(closure['final_selection'])
    need(manifest['schema'] == 'ranker-trace-frozen-evidence-package@1' and
         manifest['status'] == 'closed_scanned_local_package_not_uploaded', 'successful classified package required')
    need(closure['schema'] == 'ranker-trace-publication-closed-inputs@1' and closure['source_and_artifacts_quiet'] is True,
         'closed input schema differs')
    need(manifest['closed_inputs'] == closure_pin and manifest['final_selection'] == closure['final_selection'],
         'manifest closure join differs')
    package_closed = args.manifest.parent.parent / 'closed.json'
    closed_pin = pin(package_closed)
    closed = body(closed_pin)
    need(closed['status'] == 'passed_local_frozen_package' and closed['manifest'] == manifest_pin and
         closed['cleanup_errors'] == [] and not (args.manifest.parent.parent/'private-staging').exists(),
         'package must be closed and private staging removed')
    count = verify_inputs(closure,selected,manifest)
    profile = manifest['publication_decode_profile']
    need((profile['raw_population_max'],profile['per_file_max'],profile['per_decoded_container_max'],
         profile['compressed_shard_max'],profile['aggregate_decoded_work_max'],profile['wall_seconds']) ==
         (RAW_MAX,FILE_MAX,FILE_MAX,SHARD_MAX,DECODE_MAX,180), 'publication profile differs')
    need(manifest['scan_hits'] == [] and manifest['exact_available_cached_credential_veto'] is True and
         manifest['bounded_complete_PEM_classifier_veto'] is True, 'classifier closure required')
    rows, actual_decode, offset, reviews = manifest['files'], 0, 0, []
    for index, descriptor in enumerate(manifest['data_shards']):
        need(time.monotonic() < deadline, 'review wall bound exceeded')
        archive_name = 'data-%06d.tar.zst' % index
        shard = args.manifest.parent / archive_name
        need(descriptor['path'] == str(shard) and descriptor['archive'] == archive_name and
             pin(shard,SHARD_MAX) == {k:descriptor[k] for k in ('path','bytes','sha256')}, 'compressed shard pin differs')
        group = rows[offset:offset+descriptor['members']]
        need(len(group) == descriptor['members'] and all(row['archive'] == archive_name for row in group),
             'ordered shard assignment differs')
        with tempfile.TemporaryFile() as temporary:
            size,digest = decode(shard,Path(manifest['codec']['path']),temporary,deadline,DECODE_MAX-actual_decode)
            actual_decode += size
            need(size == descriptor['decoded_tar_bytes'] <= FILE_MAX and digest == descriptor['decoded_tar_sha256'],
                 'complete decoded tar differs')
            with tarfile.open(fileobj=temporary,mode='r:') as archive:
                members = archive.getmembers()
                need(len(members) == len(group), 'decoded member count differs')
                for member,row in zip(members,group):
                    need(time.monotonic() < deadline, 'review wall bound exceeded')
                    need(member.isfile() and not member.issym() and not member.islnk() and
                         member.name == row['member'] and member.size == row['bytes'] and
                         member.mode == 0o644 and member.uid == member.gid == member.mtime == 0,
                         'complete member identity differs')
                    digest,counted = hashlib.sha256(),0
                    with archive.extractfile(member) as stream:
                        while block := stream.read(BLOCK):
                            counted += len(block)
                            need(counted <= FILE_MAX and time.monotonic() < deadline, 'member/work bound exceeded')
                            digest.update(block)
                    need(counted == row['bytes'] and digest.hexdigest() == row['sha256'], 'decoded member bytes differ')
        reviews.append({'archive':archive_name,'decoded_tar_bytes':size,'members_verified':len(group)})
        offset += len(group)
    need(offset == len(rows), 'all selected members must be verified')
    need(manifest['actual_aggregate_decoded_work_bytes'] <= DECODE_MAX and
         manifest['actual_verification_decode_bytes'] == actual_decode and
         manifest['actual_recursive_classifier_decoded_bytes']+actual_decode == manifest['actual_aggregate_decoded_work_bytes'],
         'classifier and manual decoded-work accounting differs')
    verify_inputs(closure,selected,manifest)
    need(pin(args.manifest) == manifest_pin and pin(args.closed_inputs) == closure_pin and
         pin(package_closed) == closed_pin and pin(Path(__file__).resolve()) == own_pin, 'reviewed input drift')
    need(not args.output.exists() and args.output.parent.is_dir(), 'new review receipt required')
    receipt = {'schema':'ranker-trace-full-decoded-member-file-only-review@1','status':'passed',
        'manifest':manifest_pin,'closed_inputs':closure_pin,'package_closure':closed_pin,'reviewer':own_pin,
        'selected_files_verified_before_after':count,'sealed_leaves_verified_before_after':203,
        'sealed_excluded_lock_bindings_verified_before_after':6,'decoded_members_verified':offset,
        'decoded_tar_shards':reviews,'actual_file_only_review_decoded_bytes':actual_decode,
        'file_only_review_decode_work_max':DECODE_MAX,'publication_container_max':FILE_MAX,
        'exact_202_semantic_outcome_facts_verified':True,'first_inconclusive_lean_attempt_retained':True,
        'new_native_jobs':0,'project_imports':0,'new_fits':0,'new_sql_or_lean_calls':0,'remote_mutations':0,
        'full_task_satisfaction':'unknown','whole_source_runtime_equivalence_proved':False,
        'asymptotic_optimizer_convergence_proved':False,'all32_governing_RPI_exits':'OPEN',
        'proof_authority':False,'execution_authority':False,'completion_authority':False}
    with args.output.open('xb') as stream:
        stream.write(wire(receipt));stream.flush();os.fsync(stream.fileno())
    return pin(args.output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True,type=Path)
    parser.add_argument('--expected-manifest-sha256',required=True)
    parser.add_argument('--closed-inputs',required=True,type=Path)
    parser.add_argument('--expected-closed-inputs-sha256',required=True)
    parser.add_argument('--output',required=True,type=Path)
    print(json.dumps(review(parser.parse_args()),sort_keys=True))
