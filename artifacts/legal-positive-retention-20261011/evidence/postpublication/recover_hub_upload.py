"""Append the unchanged release in small, individually parent-guarded commits."""
from pathlib import Path
from hashlib import sha1, sha256
import importlib.util, json, os, sys

F = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_frozen_release_publisher', F/'publish_release.py')
pub = importlib.util.module_from_spec(spec); spec.loader.exec_module(pub)
assert sha256((F/'publish_release.py').read_bytes()).hexdigest() == '74a56756d0dfa48a000a972e645b4970cb2ef05b8dda27a6e4ed3f4596be8424'

def event(value):
    with (F/'hub-upload-batch-events.jsonl').open('a') as out:
        out.write(json.dumps(value,sort_keys=True,allow_nan=False)+'\n');out.flush();os.fsync(out.fileno())

def main():
    from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download
    stage = F/'release'; mirror = F/'hub-readback'
    assert not mirror.exists()
    for name in ('hub-upload-commit.json','hub-readback-verification.json','hub-all-checkpoint-downloads.json',
                 'hub-upload-batch-proposal.json','hub-upload-batch-events.jsonl','hub-upload-batch-recovery.json'):
        assert not (F/name).exists(), 'resolve any prior fallback outcome before retry'
    failure = pub.read_json(F/'hub-upload-error.json')
    reconciliation = pub.read_json(F/'hub-upload-reconciliation.json')
    original = pub.read_json(F/'hub-upload-parent.json')
    assert failure['parent_commit'] == original['revision']
    assert reconciliation['remote_head_unchanged'] is True
    assert reconciliation['remote_head'] == original['revision']
    assert reconciliation['new_prefix_file_count'] == 0 and reconciliation['prior_changed_paths'] == []
    manifest, files, roles = pub.verify_local(stage)
    assert len(files)==311 and files['release-manifest.json']['sha256']=='17f4b9bd7fa2bb34365c19ba10bdf6b0014f14c7a2512f96ed9729cd25418c61'
    api=HfApi(); before=pub.observe(api)
    assert before==original, 'remote changed after failure reconciliation'
    assert not any(p.startswith(pub.PREFIX+'/') for p in before['files'])
    batches=[]; batch=[]; size=0
    for name in sorted(n for n in files if n!='release-manifest.json'):
        if batch and size+files[name]['bytes']>4_000_000:
            batches.append(batch);batch=[];size=0
        batch.append(name);size+=files[name]['bytes']
    if batch:batches.append(batch)
    batches.append(['release-manifest.json'])
    assert sorted(n for b in batches for n in b)==sorted(files)
    proposal=dict(schema='positive-retention-parent-guarded-batch-proposal/v1',
        repo=pub.REPO,prefix=pub.PREFIX,original_parent=before['revision'],
        recovered_initial_failure_sha256=sha256((F/'hub-upload-error.json').read_bytes()).hexdigest(),
        reconciliation_sha256=sha256((F/'hub-upload-reconciliation.json').read_bytes()).hexdigest(),
        helper_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        release_manifest_sha256=files['release-manifest.json']['sha256'],
        raw_batch_byte_target=4_000_000,oversize_files_single_batch=True,
        batches=batches,manifest_last=True,files=files,overwrite_or_delete_allowed=False)
    pub.write(F/'hub-upload-batch-proposal.json',proposal)
    with (F/'hub-upload-batch-events.jsonl').open('x') as out:out.flush();os.fsync(out.fileno())
    pub.sync_directory(F)
    expected_head=before['revision']; completed=[]
    for index, names in enumerate(batches):
        live=pub.observe(api)
        assert live['revision']==expected_head, 'concurrent main update; reconcile before any continuation'
        assert all(live['files'].get(p)==v for p,v in before['files'].items()), 'prior file identity changed'
        assert all(pub.PREFIX+'/'+n not in live['files'] for n in names), 'target already exists'
        assert pub.verify_local(stage)[1]==files
        event(dict(stage='before_commit',batch=index,parent=expected_head,paths=names,
                   raw_bytes=sum(files[n]['bytes'] for n in names)))
        try:
            commit=api.create_commit(repo_id=pub.REPO,repo_type='model',
                operations=[CommitOperationAdd(path_in_repo=pub.PREFIX+'/'+n,path_or_fileobj=str(stage/n)) for n in names],
                parent_commit=expected_head,commit_message=f'Append retention research artifacts {index+1}/{len(batches)}')
        except Exception as error:
            event(dict(stage='uncertain_commit_error',batch=index,parent=expected_head,error_type=type(error).__name__,
                       automatic_retry=False,required_next_action='Reconcile actual remote paths/head against this journal; do not rerun blindly.'))
            print(json.dumps(dict(status='uncertain',batch=index,error_type=type(error).__name__)))
            return 1
        event(dict(stage='after_commit',batch=index,parent=expected_head,revision=commit.oid,paths=names))
        completed.append(dict(batch=index,parent=expected_head,revision=commit.oid,paths=names))
        expected_head=commit.oid
        print(json.dumps(dict(batch=index+1,batches=len(batches),revision=expected_head)),flush=True)
    revision=expected_head; after=pub.observe(api,revision)
    assert after['revision']==revision
    changed=[p for p,v in before['files'].items() if after['files'].get(p)!=v]
    assert changed==[], 'batch recovery requires every prior identity unchanged'
    assert set(after['files'])-set(before['files'])=={pub.PREFIX+'/'+n for n in files}
    published=[]
    for n, expected in sorted(files.items()):
        raw=(stage/n).read_bytes();assert pub.pin(raw)==expected
        identity=after['files'][pub.PREFIX+'/'+n];assert identity['size']==len(raw)
        if identity['lfs_sha256']:assert identity['lfs_sha256']==expected['sha256']
        else:assert identity['blob_id']==sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        published.append(dict(path=pub.PREFIX+'/'+n,**expected,git_or_LFS_identity_verified=True))
    pub.write(F/'hub-upload-commit.json',dict(repo=pub.REPO,prefix=pub.PREFIX,parent=before['revision'],
        revision=revision,url=f'https://huggingface.co/{pub.REPO}/commit/{revision}',
        publication_transport='parent-guarded small batches after reconciled no-change TLS failure',
        batch_commits=completed))
    downloaded={}; records=[]
    for n in sorted(roles):
        remote=Path(hf_hub_download(pub.REPO,pub.PREFIX+'/'+n,revision=revision,cache_dir=str(F/'hub-download-cache')))
        raw=remote.read_bytes();assert raw==(stage/n).read_bytes() and pub.pin(raw)==files[n]
        downloaded[n]=raw;records.append(dict(path=n,**files[n],downloaded_bytes_exact=True,checkpoint_role=roles[n]['role']))
    for n,raw in downloaded.items():pub.write_bytes(mirror/'all-checkpoints'/n.removeprefix('checkpoints/'),raw)
    for arm in pub.ARMS:pub.write_bytes(mirror/arm/'checkpoint.json',downloaded['checkpoints/'+arm+'/checkpoint.json'])
    pub.write(F/'hub-all-checkpoint-downloads.json',dict(schema='positive-retention-all-Hub-checkpoints/v1',
        passed=True,repo=pub.REPO,prefix=pub.PREFIX,revision=revision,original_states=6,selected_aliases=2,
        checkpoint_files=8,model_restores=0,model_forwards=0,optimizer_updates=0,files=records))
    pub.write(F/'hub-readback-verification.json',dict(schema='positive-retention-Hub-readback/v1',passed=True,
        repo=pub.REPO,prefix=pub.PREFIX,parent=before['revision'],revision=revision,
        prior_file_count=len(before['files']),prior_file_identities_preserved=True,allowed_changed_prior_paths=[],
        gitattributes_append_only=False,all_new_git_or_LFS_identities_verified=True,new_file_count=len(published),
        all_eight_checkpoints_downloaded_byte_exact=True,both_selected_aliases_downloaded_byte_exact=True,
        selected_alias_mirror=str(mirror),files=published,default_or_ModelManager_promotion=False,model_restores=0,model_forwards=0))
    pub.write(F/'hub-upload-batch-recovery.json',dict(schema='positive-retention-parent-guarded-batch-recovery/v1',
        passed=True,findings=[],original_failure_preserved=True,reconciliation_proved_remote_unchanged=True,
        initial_prefix_absent=True,parent_guard_every_batch=True,no_target_overwrites_or_deletions=True,
        original_parent=before['revision'],final_revision=revision,batch_count=len(completed),batch_commits=completed,
        every_prior_identity_preserved=True,all311_new_identities_verified=True,all8_checkpoint_downloads_exact=True,
        proposal_sha256=sha256((F/'hub-upload-batch-proposal.json').read_bytes()).hexdigest(),
        event_journal_sha256=sha256((F/'hub-upload-batch-events.jsonl').read_bytes()).hexdigest()))
    print(json.dumps(dict(status='completed',revision=revision,new_files=311,batches=len(completed))),flush=True)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
