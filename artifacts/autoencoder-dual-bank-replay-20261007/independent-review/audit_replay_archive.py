"""Stream an explicitly completed archive; stdlib only, no extraction."""
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile

W = Path('/home/barberb/lift_coding')
R = W / 'artifacts/autoencoder-dual-bank-replay-20261007'
RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-dual-bank-replay-20261007'
SOURCE_CAP = 512_000_000
ARCHIVE_CAP = 100_000_000
MEMBER_CAP = 4096
CHECKS = []
ARTIFACTS = {}


def check(ok, message):
    CHECKS.append(dict(check=message, passed=bool(ok)))
    if not ok:
        raise ValueError(message)


def identity(value):
    return [value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns]


def file_binding(path):
    path = Path(path)
    before = path.lstat()
    check(stat.S_ISREG(before.st_mode), 'Regular nonsymbolic source: ' + str(path))
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        check(identity(os.fstat(stream.fileno())) == identity(before), 'Exact opened descriptor identity')
        for chunk in iter(lambda: stream.read(1048576), b''):
            size += len(chunk)
            h.update(chunk)
        check(identity(os.fstat(stream.fileno())) == identity(before), 'Source descriptor immutable during audit')
    check(identity(path.lstat()) == identity(before) and size == before.st_size, 'Source pathname/bytes immutable')
    result = dict(bytes=size, sha256=h.hexdigest())
    ARTIFACTS[str(path)] = result
    return result


def expected_source(member):
    parts = PurePosixPath(member).parts
    check(bool(parts) and '/'.join(parts) == member and not member.startswith('/') and '\\' not in member
        and all(p not in ('', '.', '..') for p in parts), 'Safe archive member path')
    roots = {'owned-run': RUN, 'review-and-source': R}
    check(parts[0] in roots and len(parts) > 1, 'Declared archive root prefix')
    root = roots[parts[0]]
    path = root.joinpath(*parts[1:])
    check(path.resolve().is_relative_to(root.resolve()), 'Source stays within declared owner root')
    return path


def main():
    manifest_path = R / 'publication/replay-evidence-manifest.json'
    manifest_binding = file_binding(manifest_path)
    manifest = json.loads(manifest_path.read_bytes())
    archive = R / 'publication/replay-evidence.tar.gz'
    check(manifest['archive']['path'] == str(archive), 'Exact actual archive location')
    archive_binding = file_binding(archive)
    check(archive_binding == {k: manifest['archive'][k] for k in ('bytes','sha256')}, 'Archive bytes/authenticated SHA')
    check(archive_binding['bytes'] <= ARCHIVE_CAP, 'Compressed archive byte cap')
    check(manifest['limits'] == dict(source_bytes=SOURCE_CAP, compressed_bytes=ARCHIVE_CAP, members=MEMBER_CAP),
        'Exact declared archive limits')
    members = manifest['members']
    check(len(members) == manifest['member_count'] <= MEMBER_CAP, 'Exact bounded member denominator')
    check(sum(x['bytes'] for x in members.values()) == manifest['source_bytes'] <= SOURCE_CAP, 'Exact bounded source bytes')
    seen = []
    streamed_bytes = 0
    with archive.open('rb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='rb') as compressed:
            with tarfile.open(fileobj=compressed, mode='r|') as tar:
                for info in tar:
                    check(info.name in members and info.name not in seen, 'Declared unique archive member')
                    record = members[info.name]
                    source = expected_source(info.name)
                    check(record['path'] == str(source), 'Exact source/member mapping')
                    check(info.isreg() and not info.issym() and not info.islnk() and not info.sparse,
                        'Regular nonsymbolic nonsparse archive member')
                    check(info.uid == info.gid == info.mtime == 0 and info.mode == 0o644
                        and info.uname == info.gname == '', 'Deterministic metadata')
                    check(info.size == record['bytes'] and 0 <= info.size <= SOURCE_CAP, 'Exact bounded member size')
                    h = hashlib.sha256(); size = 0
                    stream = tar.extractfile(info)
                    check(stream is not None, 'Regular member body is readable without extraction')
                    with stream:
                        for chunk in iter(lambda: stream.read(1048576), b''):
                            size += len(chunk); streamed_bytes += len(chunk); h.update(chunk)
                            check(streamed_bytes <= SOURCE_CAP, 'Streaming decompressed source byte cap')
                    check(size == record['bytes'] and h.hexdigest() == record['sha256'], 'Every streamed body SHA/byte count')
                    check(file_binding(source) == {k:record[k] for k in ('bytes','sha256')}, 'Every member equals retained current source bytes')
                    check(identity(source.lstat()) == record['source_identity'], 'Every member source identity retained from creation')
                    seen.append(info.name)
            tail_bytes = 0
            for chunk in iter(lambda: compressed.read(1048576), b''):
                tail_bytes += len(chunk)
                check(tail_bytes <= 1048576 and not any(chunk), 'Bounded zero tar trailer and verified gzip CRC')
    check(seen == sorted(members), 'Exact count/order/coverage of all manifest members')
    check(streamed_bytes == manifest['source_bytes'], 'Exact streamed source-byte sum')
    excluded = manifest['excluded_checkpoint_bodies']
    actual_states = sorted(RUN.glob('training-384-r1/results/dual-bank-retention-ce/*-state.json'))
    check(len(excluded) == len(actual_states) == 3
        and {x['path'] for x in excluded} == {str(p) for p in actual_states}, 'Only three actual checkpoint tensor bodies excluded')
    for record in excluded:
        check(record['member'] not in members and record['member'].startswith('owned-run/'), 'Checkpoint bodies absent from archive')
        check(file_binding(record['path']) == {k:record[k] for k in ('bytes','sha256')}, 'Excluded checkpoint metadata byte reference remains exact')
    check('review-and-source/initial-state.json' in members, 'Initial Git/workspace custody receipt is retained')
    check(all(not p.startswith('review-and-source/publication/') and not p.startswith('review-and-source/pipeline/')
        and '__pycache__' not in PurePosixPath(p).parts and not p.endswith(('.pyc','.index')) for p in members),
        'Self-archive/publication/pipeline/cache indexes excluded')
    for phase in ('preflight-384-r1','training-384-r1','evaluation-r1'):
        for relative in (phase+'-guardian-exit.json',phase+'/resources-final.json',phase+'/results/summary.json'):
            check('owned-run/'+relative in members, 'Completed phase terminal/resource/results entry coverage: '+relative)
        terminal=json.loads((RUN/(phase+'-guardian-exit.json')).read_bytes())
        resource=json.loads((RUN/(phase+'/resources-final.json')).read_bytes())
        summary=json.loads((RUN/(phase+'/results/summary.json')).read_bytes())
        check(terminal['returncode']==0 and resource['status']=='released' and summary['complete'] is True,
            'Every actual phase is completed and its owned lease released')
    for name in ('actual-preflight-384-r1-independent-review.json','actual-training-384-r1-independent-review.json',
        'actual-evaluation-r1-independent-review.json','postfit-comparison-independent-review.json',
        'documentation-and-archive-source-independent-review.json'):
        check('review-and-source/independent-review/'+name in members, 'Actual independent review retained: '+name)
    check(all(manifest[k] is False for k in ('checkpoint_promoted','qualified','admitted','proof_authority','Constitution_formalized')),
        'Archive grants no model/promotion/proof authority')
    check('not vector-free' in manifest['retained_vector_policy'], 'Retained observations honestly disclose vector content')
    source_binding = file_binding(Path(__file__).resolve())
    report=dict(schema='dual-bank-replay-actual-archive-independent-review/v1',passed=True,findings=[],
        archive=manifest['archive'],manifest=dict(path=str(manifest_path),**manifest_binding),
        auditor=dict(path=str(Path(__file__).resolve()),**source_binding),checks=CHECKS,artifacts=ARTIFACTS,
        members_streamed=len(seen),source_bytes_streamed=streamed_bytes,excluded_actual_checkpoint_bodies=3,
        gzip_crc_and_archive_order_verified=True,all_declared_members_equal_current_frozen_sources=True,
        limits=manifest['limits'],qualification_or_model_authority_granted=False,
        cached_or_normalized_observation_vectors_retained=True,raw_historical_model_cache_closure_retained_elsewhere=True,
        model_or_encoder_or_numerical_owner_execution=False,archive_extraction=False,resource_or_git_or_remote_mutation=False,
        qualified=False,admitted=False,proof_authority=False,checkpoint_promoted=False,Constitution_formalized=False)
    destination=R/'independent-review/actual-archive-independent-review.json'
    with destination.open('x') as stream:
        json.dump(report,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(passed=True,path=str(destination),checks=len(CHECKS),bindings=len(ARTIFACTS),
        bytes=destination.stat().st_size,sha256=hashlib.sha256(destination.read_bytes()).hexdigest())))


if __name__=='__main__':
    main()
