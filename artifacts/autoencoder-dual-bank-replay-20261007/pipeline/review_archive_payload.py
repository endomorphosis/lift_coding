"""Read back immutable completed evidence; never rebuild or execute models."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import tarfile

W = Path('/home/barberb/lift_coding')
R = W / 'artifacts/autoencoder-dual-bank-replay-20261007'
RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-dual-bank-replay-20261007'
A = {}
CHECKS = []


def pin(path, wanted=None):
    path = Path(path).resolve(); before = path.stat(); size = 0; h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block); size += len(block)
    after = path.stat(); identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if not stat.S_ISREG(before.st_mode) or identity(before) != identity(after) or size != before.st_size:
        raise ValueError('artifact changed during readback: ' + str(path))
    record = dict(sha256=h.hexdigest(), bytes=size)
    if wanted is not None and record['sha256'] != wanted: raise ValueError('artifact SHA differs: ' + str(path))
    A[str(path)] = record; return record


def read(path, wanted=None):
    pin(path, wanted); return json.loads(Path(path).read_bytes())


def check(name, ok, details=None):
    if not ok: raise ValueError(name)
    CHECKS.append(dict(name=name, passed=True, details=details))


def eligible(prefix, root):
    result = {}
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.is_symlink(): continue
        rel = path.relative_to(root)
        if root == R and rel.parts[0] in ('publication', 'pipeline'): continue
        if '__pycache__' in rel.parts or path.suffix in ('.pyc', '.index'): continue
        result[prefix + '/' + rel.as_posix()] = path
    return result


def main():
    manifest_path = R / 'publication/replay-evidence-manifest.json'
    manifest = read(manifest_path)
    archive = R / 'publication/replay-evidence.tar.gz'
    archive_binding = pin(archive, '0b732781a178533a918cf3174759c09a98de92781d77ae63d7166bd0de65220f')
    check('exact-final-compressed-archive-binding', manifest['archive'] == dict(path=str(archive), **archive_binding)
          and archive_binding['bytes'] == 62752730, archive_binding)
    check('finite-declared-limits-and-full-member-census', manifest['limits'] == dict(source_bytes=512000000,
          compressed_bytes=100000000, members=4096) and manifest['member_count'] == len(manifest['members']) == 247
          and manifest['source_bytes'] == sum(v['bytes'] for v in manifest['members'].values()) == 204736335
          and archive_binding['bytes'] <= manifest['limits']['compressed_bytes'],
          dict(members=247, source_bytes=204736335))
    roots = {'owned-run': RUN, 'review-and-source': R}
    expected = {**eligible('owned-run', RUN), **eligible('review-and-source', R)}
    expected_excluded = {name: path for name, path in expected.items()
                         if name.startswith('owned-run/') and path.name.endswith('-state.json')}
    # Later root-only publication-scope files are metadata created after the
    # archive snapshot; they do not replace full immutable owned phase files.
    later_metadata = {'review-and-source/publication-scope.json',
        'review-and-source/independent-review/actual-evaluation-r1-independent-review.json.gz',
        'review-and-source/independent-review/actual-preflight-384-r1-independent-review.json.gz',
        'review-and-source/independent-review/actual-training-384-r1-independent-review.json.gz',
        'review-and-source/independent-review/postfit-comparison-independent-review.json.gz',
        'review-and-source/independent-review/archive-auditor-pure-tests.log',
        'review-and-source/independent-review/audit_replay_archive.py',
        'review-and-source/independent-review/compact-auditor-source-results-freeze.json',
        'review-and-source/independent-review/test_archive_auditor_contracts.py'}
    retained_expected = {name: path for name, path in expected.items()
                         if name not in expected_excluded and name not in later_metadata}
    check('all-current-owned-phase-and-frozen-source-files-retained', set(manifest['members']) == set(retained_expected),
          dict(owned_run_members=sum(n.startswith('owned-run/') for n in manifest['members']),
               review_source_members=sum(n.startswith('review-and-source/') for n in manifest['members'])))
    declared_excluded = {record['member']: record for record in manifest['excluded_checkpoint_bodies']}
    check('exact-three-real-checkpoint-bodies-excluded', len(declared_excluded) == len(expected_excluded) == 3
          and set(declared_excluded) == set(expected_excluded), sorted(declared_excluded))
    for name, record in declared_excluded.items():
        body = pin(record['path'], record['sha256'])
        check('excluded-state:' + name, Path(record['path']) == expected_excluded[name]
              and body['bytes'] == record['bytes'] and name not in manifest['members'], body)
    custody_name = 'review-and-source/initial-state.json'
    check('root-initial-Git-custody-is-retained-not-treated-as-weights', custody_name in manifest['members']
          and manifest['members'][custody_name]['bytes'] == 851, manifest['members'].get(custody_name))
    observed = set(); total = 0
    with tarfile.open(archive, mode='r|gz') as tar:
        for member in tar:
            name = member.name; parts = PurePosixPath(name).parts
            check('safe-unique-regular-tar-member:' + name, member.isfile() and name not in observed
                  and name in manifest['members'] and not PurePosixPath(name).is_absolute()
                  and '..' not in parts and parts[0] in roots
                  and member.uid == member.gid == member.mtime == 0 and member.mode == 0o644)
            observed.add(name); record = manifest['members'][name]
            source = roots[parts[0]] / Path(*parts[1:])
            check('exact-source-and-size-binding:' + name, str(source) == record['path'] and member.size == record['bytes'])
            source_binding = pin(source, record['sha256'])
            before = source.stat()
            check('source-stat-identity:' + name, source_binding['bytes'] == record['bytes']
                  and list((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns))
                  == record['source_identity'])
            stream = tar.extractfile(member); h = hashlib.sha256(); size = 0
            if stream is None: raise ValueError('regular payload stream missing')
            for block in iter(lambda: stream.read(1048576), b''):
                h.update(block); size += len(block)
            check('actual-tar-payload-sha:' + name, h.hexdigest() == record['sha256'] and size == record['bytes'])
            total += size
    check('all-member-payloads-read-and-exact-total', observed == set(manifest['members']) and total == manifest['source_bytes'],
          dict(actual_members=len(observed), actual_source_bytes=total))
    for phase in ('preflight-384-r1', 'training-384-r1', 'evaluation-r1'):
        outer = read(RUN / (phase + '-guardian-exit.json'))
        child = read(RUN / phase / 'child-exit.json')
        resources = read(RUN / phase / 'resources-final.json')
        check('completed-owned-phase:' + phase, outer['returncode'] == child['returncode'] == 0
              and child['leader_reaped'] is True and resources['status'] == 'released'
              and resources['record']['last_usage']['group_rss']['live_processes'] == 0)
    comparison = read(R / 'postfit-comparison.json')
    check('comparison-and-nonpromotion-authority-retained', comparison['complete'] is True
          and manifest['all_phase_outputs_complete'] is True
          and all(manifest[k] is False for k in ('checkpoint_promoted', 'qualified', 'admitted',
                                                'proof_authority', 'Constitution_formalized')))
    mechanics = read(R / 'pipeline/publisher-mechanics-independent-review-r2.json',
                     '9c2bfe35eb196d47b7109a14effc1355ef23a24d54e00515f7ab42fc7854535a')
    check('current-source-mechanics-binding', mechanics['passed'] is True and mechanics['findings'] == []
          and pin(R / 'build_evidence_archive.py')['sha256'] == mechanics['artifacts'][str(R / 'build_evidence_archive.py')]['sha256'])
    pin(Path(__file__).resolve())
    for path, record in list(A.items()):
        if pin(path, record['sha256']) != record: raise ValueError('artifact changed after payload audit')
    result = dict(schema='dual-bank-replay-actual-evidence-archive-independent-review/v1', passed=True, findings=[],
                  checks=CHECKS, artifacts=A, archive=dict(path=str(archive), **archive_binding),
                  complete_actual_tar_payload_readback=True, member_count=len(observed),
                  source_bytes=total, excluded_checkpoint_bodies=3, root_initial_state_git_custody_retained=True,
                  vector_bearing_observations_retained=True, archive_is_vector_free=False,
                  explicit_post_snapshot_publication_or_auditor_metadata=sorted(set(expected) & later_metadata),
                  all_owned_RUN_phase_files_retained=True,
                  deterministic_metadata_verified=True, tar_extraction_to_filesystem_performed=False,
                  archive_builder_or_model_or_Git_executed=False, source_modified_by_review=False,
                  final_publication_scope_review_required=True, qualified=False, admitted=False,
                  proof_authority=False, Lake_executed=False, Constitution_formalized=False, checkpoint_promoted=False)
    target = R / 'pipeline/actual-archive-independent-review.json'
    with target.open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2); stream.write('\n')
    print(json.dumps(dict(path=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                         bytes=target.stat().st_size, checks=len(CHECKS), bindings=len(A), members=len(observed))))


if __name__ == '__main__': main()
