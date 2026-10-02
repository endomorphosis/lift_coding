"""Authorized reversible archival of the 15 exactly qualified runtime bundles."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,stat,subprocess,time,uuid
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler,ResourceLane
import archive_cas as cas

ROOT=Path(__file__).resolve().parent

def activity(directories):
    matched=[];denied={};seen=0
    needles=[str(p) for p in directories]
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name)==os.getpid():continue
        try:uid=process.stat().st_uid
        except FileNotFoundError:continue
        seen+=1
        for kind in ('cmdline','cwd','fd','maps'):
            try:
                if kind=='cmdline':values=[process.joinpath(kind).read_bytes().replace(b'\0',b' ').decode(errors='replace')]
                elif kind=='cwd':values=[os.readlink(process/kind)]
                elif kind=='fd':
                    values=[]
                    for path in (process/kind).iterdir():
                        try:values.append(os.readlink(path))
                        except FileNotFoundError:pass
                else:values=(process/kind).read_text(errors='replace').splitlines()
                for value in values:
                    for needle in needles:
                        if needle in value:matched.append(dict(pid=int(process.name),uid=uid,kind=kind,candidate=needle))
            except FileNotFoundError:pass
            except PermissionError:denied[str(uid)]=denied.get(str(uid),0)+1
    listed=subprocess.run(['docker','ps','-aq'],capture_output=True,text=True,timeout=15)
    cas.require(listed.returncode==0,'Docker container census unavailable')
    ids=listed.stdout.split();overlaps=[]
    for cid in ids:
        raw=subprocess.run(['docker','inspect',cid,'--format','{{json .Mounts}}'],capture_output=True,text=True,timeout=15)
        cas.require(raw.returncode==0,'Docker mount census unavailable')
        for mount in json.loads(raw.stdout):
            source=mount.get('Source')
            if not source:continue
            path=Path(source).resolve()
            for target in directories:
                if target==path or target.is_relative_to(path) or path.is_relative_to(target):overlaps.append(dict(container=cid,source=str(path),candidate=str(target)))
    return dict(at=datetime.now(timezone.utc).isoformat(),observed_process_matches=matched,processes_seen=seen,
        denied_field_count_by_uid=denied,global_inactivity_proved=False,docker_container_count=len(ids),docker_overlap=overlaps)

def archive_one(record,reference,check):
    original=Path(record['original_archive']);directory=original.parent
    cas.require(directory.resolve()==directory,'canonical original directory required')
    dirfd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fd=None;pending=None
    prior=os.fstat(dirfd);original_mode=stat.S_IMODE(prior.st_mode)
    result=dict(original_path=str(original),archive_sha256=record['sha256'],bytes=record['bytes'])
    try:
        cas.require(prior.st_uid==os.getuid(),'original directory must be task-owned')
        os.fchmod(dirfd,0o700)
        fd=os.open(original.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=dirfd);before=os.fstat(fd)
        expected=(record['device'],record['inode'],record['bytes'],record['mtime_ns'],record['uid'],record['gid'],int(record['mode'],8))
        observed=lambda row:(row.st_dev,row.st_ino,row.st_size,row.st_mtime_ns,row.st_uid,row.st_gid,stat.S_IMODE(row.st_mode))
        cas.require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and observed(before)==expected,'original identity no longer matches qualified archive')
        digest=hashlib.sha256();size=0
        for block in iter(lambda:os.read(fd,cas.BLOCK),b''):check();digest.update(block);size+=len(block)
        after=os.fstat(fd)
        cas.require(observed(after)==expected and before.st_ctime_ns==after.st_ctime_ns and size==record['bytes'] and digest.hexdigest()==record['sha256'],'original changed or exact hash differs')
        check();named=os.stat(original.name,dir_fd=dirfd,follow_symlinks=False)
        cas.require(observed(named)==expected and named.st_nlink==1,'original name changed before archival')
        visible=directory.stat();cas.require((visible.st_dev,visible.st_ino)==(prior.st_dev,prior.st_ino),'original directory path changed')
        sidecar=original.name+'.cas.json';pending='.'+sidecar+'.'+uuid.uuid4().hex+'.pending'
        payload=(json.dumps(reference,sort_keys=True,indent=2)+'\n').encode()
        output=os.open(pending,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=dirfd)
        with os.fdopen(output,'wb') as stream:stream.write(payload);stream.flush();os.fsync(stream.fileno())
        os.link(pending,sidecar,src_dir_fd=dirfd,dst_dir_fd=dirfd,follow_symlinks=False);os.unlink(pending,dir_fd=dirfd);pending=None;os.fsync(dirfd)
        check();current=os.stat(original.name,dir_fd=dirfd,follow_symlinks=False)
        cas.require(observed(current)==expected and current.st_ctime_ns==after.st_ctime_ns and current.st_nlink==1,'original changed after durable restore reference')
        os.unlink(original.name,dir_fd=dirfd);os.fsync(dirfd)
        result.update(archived=True,sidecar=str(directory/sidecar),sidecar_sha256=hashlib.sha256(payload).hexdigest(),
            original_allocated_bytes=current.st_blocks*512,original_identity=record,directory_original_mode=oct(original_mode),
            reference_durable_before_original_unlink=True)
        return result
    finally:
        if pending is not None:
            try:os.unlink(pending,dir_fd=dirfd)
            except FileNotFoundError:pass
        if fd is not None:os.close(fd)
        os.fchmod(dirfd,original_mode);os.fsync(dirfd);os.close(dirfd)

def main():
    report=dict(schema='qualified-runtime-archive-replacement@1',qualified=False,original_archive_bytes_preserved_in_sealed_cas=False,archived=[])
    lease=None;started=time.monotonic()
    try:
        qualification=json.loads((ROOT/'complete-qualification.json').read_bytes());envelope=json.loads((ROOT/'finish-envelope.json').read_bytes())
        cas.require(qualification['qualified'] and qualification['archive_count']==15 and envelope['qualified'] and envelope['reaped'] and envelope['native_admission']['released'],'complete native durable qualification required')
        store=ROOT/'store';seal=store/'SEALED.json';seal_sha=qualification['seal']['seal_sha256']
        cas.require(cas.digest_file(seal)==seal_sha,'externally qualified seal hash mismatch')
        sealed=json.loads(seal.read_bytes());files={row['path']:row for row in sealed['files']};accepted={row['slug']:row for row in sealed['archives']}
        for name in ('codec/deflate1','restore/archive_cas.py','archive-index.json'):
            cas.private_file(store/name);cas.require(cas.digest_file(store/name)==files[name]['sha256'],'sealed restoration dependency changed')
        report['original_archive_bytes_preserved_in_sealed_cas']=True
        authority=ROOT.parent/'activity-review-final15.json';authority_sha=cas.digest_file(authority);audit=json.loads(authority.read_bytes())
        cas.require(len(audit['bundles'])==15 and not audit['findings']['observable_reference_matches'] and audit['findings']['docker_overlap_count']==0,'independent activity review has an observed reference')
        scheduler=get_global_resource_scheduler();lease=scheduler.acquire(ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=512,child_process_slots=1,timeout=30,request_id='runtime-exact-archive-replacement-01')
        deadline=time.monotonic()+300
        def check():
            if lease.cancelled or time.monotonic()>=deadline:raise TimeoutError('archival native cancellation/deadline')
        report['native_admission']=dict(lease_id=lease.lease_id,cpu_slots=1,memory_mb=512,child_process_slots=1)
        report['fresh_activity']=activity([Path(row['original_archive']).parent for row in qualification['archives']])
        cas.require(not report['fresh_activity']['observed_process_matches'] and not report['fresh_activity']['docker_overlap'],'fresh observable activity blocks archival')
        disk=shutil.disk_usage(ROOT);report['disk_before']=dict(total=disk.total,used=disk.used,free=disk.free,used_percent_excluding_reserved=100*disk.used/(disk.used+disk.free))
        report['independent_activity_report']=dict(path=str(authority),sha256=authority_sha,visibility_gaps_preserved=True)
        for original in qualification['archives']:
            check();binding=accepted[original['slug']];recipe=store/'recipes'/(original['slug']+'.jsonl')
            cas.require(cas.digest_file(recipe)==binding['recipe_sha256'],'sealed recipe changed')
            cas.require(cas.digest_file(Path(binding['source_manifest']))==binding['manifest_sha256'],'original manifest changed')
            reference=dict(schema='runtime-archive-lossless-cas-reference@1',original=original,
                store=str(store),seal_sha256=seal_sha,recipe=str(recipe),recipe_sha256=binding['recipe_sha256'],
                codec=str(store/'codec/deflate1'),codec_sha256=binding['codec_sha256'],
                restorer=str(store/'restore/archive_cas.py'),restorer_sha256=files['restore/archive_cas.py']['sha256'],
                archive_sha256=binding['archive_sha256'],archive_bytes=binding['archive_bytes'],
                original_manifest_sha256=binding['manifest_sha256'],activity_report_sha256=authority_sha,
                instructions=str(store/'RESTORE.md'),created_at=datetime.now(timezone.utc).isoformat(),
                note='Exact original bytes are retained in the sealed shared store; restore to a fresh private destination before reuse.')
            report['archived'].append(archive_one(original,reference,check))
            (ROOT/'replacement-result.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        report['qualified']=len(report['archived'])==15
    except BaseException as error:report['error']=dict(type=type(error).__name__,message=str(error))
    finally:
        if lease is not None:lease.release();report['native_admission']['released']=lease.released
        disk=shutil.disk_usage(ROOT);report['disk_after']=dict(total=disk.total,used=disk.used,free=disk.free,used_percent_excluding_reserved=100*disk.used/(disk.used+disk.free))
        report['unlinked_original_allocated_bytes']=sum(row['original_allocated_bytes'] for row in report['archived'])
        if 'disk_before' in report:report['observed_free_bytes_increase']=disk.free-report['disk_before']['free']
        report['seconds']=time.monotonic()-started
        (ROOT/'replacement-result.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        print(json.dumps({k:report.get(k) for k in ('qualified','seconds','unlinked_original_allocated_bytes','observed_free_bytes_increase','disk_after','error')}),flush=True)

if __name__=='__main__':main()
