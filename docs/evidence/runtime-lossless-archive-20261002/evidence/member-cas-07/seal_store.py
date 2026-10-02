"""Final private/durable archival barrier; never removes original archives."""
from pathlib import Path
import argparse,hashlib,json,os,stat,time,zlib
import archive_cas as cas

def _verify_blob(path,digest,size):
    """Hash compressed and decoded bytes from the same stable descriptor."""
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        before=os.fstat(fd);cas.private_file(path)
        compressed=hashlib.sha256();decoded=hashlib.sha256();decoder=zlib.decompressobj();raw_bytes=total=0
        for raw in iter(lambda:os.read(fd,cas.BLOCK),b''):
            compressed.update(raw);raw_bytes+=len(raw);pending=raw
            while pending:
                data=decoder.decompress(pending,min(cas.BLOCK,size-total+1));pending=decoder.unconsumed_tail
                cas.require(not decoder.unused_data,'CAS trailing data')
                total+=len(data);cas.require(total<=size,'CAS decoded body bound');decoded.update(data)
        after=os.fstat(fd)
        identity=lambda v:(v.st_dev,v.st_ino,v.st_size,v.st_mtime_ns,v.st_ctime_ns)
        cas.require(identity(before)==identity(after) and raw_bytes==before.st_size,'CAS changed during same-descriptor verification')
        cas.require(decoder.eof and total==size and decoded.hexdigest()==digest,'CAS decoded content differs')
        return compressed.hexdigest()
    finally:os.close(fd)

def seal_store(root,accepted,expected_files=None):
    started=time.monotonic();store=cas.Store(root)
    try:
        cas.require(not (root/'SEALED.json').exists(),'store already sealed')
        cas.require(type(accepted) is list and 0<len(accepted)<=64,'bounded independent accepted archive population required')
        names=set();bindings=[];referenced={};expected=dict(expected_files or {})
        for row in accepted:
            slug=row['slug'];cas.require(slug not in names and all(c.isalnum() or c in '-_' for c in slug),'unique closed archive slug');names.add(slug)
            recipe=store.recipes/(slug+'.jsonl');cas.private_file(recipe)
            cas.require(recipe.stat().st_size<=cas.MAX_RECIPE,'accepted recipe size bound')
            expected['recipes/'+slug+'.jsonl']=cas.safe_digest(row['recipe_sha256'])
            recipe_digest=hashlib.sha256()
            with recipe.open('rb') as stream:
                first=stream.readline(cas.MAX_LINE+1);cas.require(len(first)<=cas.MAX_LINE,'recipe first-line bound');recipe_digest.update(first);header=json.loads(first)
                cas.require(header['archive_sha256']==cas.safe_digest(row['archive_sha256']) and header['archive_bytes']==row['archive_bytes'],'accepted original archive binding differs')
                for raw in iter(lambda:stream.readline(cas.MAX_LINE+1),b''):
                    cas.require(len(raw)<=cas.MAX_LINE,'recipe line bound')
                    recipe_digest.update(raw)
                    part=json.loads(raw)
                    if part['kind']=='member' and part['body_bytes']:
                        digest=cas.safe_digest(part['body_sha256']);size=part['body_bytes']
                        cas.require(digest not in referenced or referenced[digest]==size,'inconsistent shared body length');referenced[digest]=size
            cas.require(recipe_digest.hexdigest()==row['recipe_sha256'],'accepted recipe changed')
            source_manifest=root/'manifests'/(slug+'.json');cas.private_file(source_manifest)
            cas.require(source_manifest.stat().st_size<=16*cas.BLOCK,'accepted source manifest size bound')
            manifest_bytes=source_manifest.read_bytes();expected['manifests/'+slug+'.json']=cas.safe_digest(row['manifest_sha256'])
            cas.require(hashlib.sha256(manifest_bytes).hexdigest()==row['manifest_sha256'],'preserved original manifest changed')
            cas.require(json.loads(manifest_bytes)['archive_sha256']==row['archive_sha256'],'manifest original hash differs')
            cas.private_file(root/'codec/deflate1')
            cas.require('codec/deflate1' not in expected or expected['codec/deflate1']==row['codec_sha256'],'one consistent codec binding required')
            expected['codec/deflate1']=cas.safe_digest(row['codec_sha256'])
            cas.require(cas.digest_file(root/'codec/deflate1')==cas.safe_digest(row['codec_sha256']),'accepted standalone codec changed')
            bindings.append(dict(row))
        for digest,size in referenced.items():
            expected['blobs/'+digest+'.zlib']=_verify_blob(store.blob(digest),digest,size)
        root_fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            root_identity=os.fstat(root_fd);files=[];directories=[]
            for current,dirs,names,descriptor in os.fwalk('.',topdown=False,follow_symlinks=False,dir_fd=root_fd):
                info=os.fstat(descriptor)
                cas.require(info.st_uid==os.getuid() and not(info.st_mode&0o022),'private owned retained directory required')
                for name in dirs:
                    item=os.stat(name,dir_fd=descriptor,follow_symlinks=False);cas.require(stat.S_ISDIR(item.st_mode),'retained symlink refused')
                for name in sorted(names):
                    fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=descriptor)
                    try:
                        before=os.fstat(fd);cas.require(stat.S_ISREG(before.st_mode) and before.st_uid==os.getuid() and not(before.st_mode&0o022) and before.st_nlink==1,'private owned retained file required')
                        h=hashlib.sha256();size=0
                        for chunk in iter(lambda:os.read(fd,cas.BLOCK),b''):h.update(chunk);size+=len(chunk)
                        after=os.fstat(fd);cas.require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) and size==before.st_size,'file changed during durable seal')
                        relative=(Path(current)/name).as_posix().removeprefix('./')
                        if relative in expected:cas.require(h.hexdigest()==expected[relative],'final durable file differs from accepted/verified content: '+relative)
                        mode=0o600 if relative=='archive.lock' else 0o500 if relative=='codec/deflate1' else 0o400
                        os.fchmod(fd,mode);os.fsync(fd)
                        files.append(dict(path=relative,sha256=h.hexdigest(),bytes=size,mode=oct(mode)))
                    finally:os.close(fd)
                os.fsync(descriptor)
                directories.append(current)
            cas.require(set(expected).issubset({row['path'] for row in files}),'accepted/verified file missing from final durable population')
            body=dict(schema='durable-private-runtime-archive-store@1',archives=bindings,files=sorted(files,key=lambda v:v['path']),
                directories=sorted(directories),referenced_body_count=len(referenced),all_referenced_bodies_freshly_hash_verified=True,
                original_archives_removed=False,codec_mode='retained Linux ARM64 static zlib1.3; no dynamic loader dependency',
                originals_activity_authorization='separate immediately refreshed activity/stat decision required',seconds=time.monotonic()-started)
            encoded=(json.dumps(body,sort_keys=True,indent=2)+'\n').encode();cas.require(len(encoded)<16*cas.BLOCK,'seal manifest bound')
            fd=os.open('SEALED.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400,dir_fd=root_fd)
            with os.fdopen(fd,'wb') as stream:stream.write(encoded);stream.flush();os.fsync(stream.fileno())
            for current,dirs,names,descriptor in os.fwalk('.',topdown=False,follow_symlinks=False,dir_fd=root_fd):os.fchmod(descriptor,0o500);os.fsync(descriptor)
            observed=root.stat();cas.require((observed.st_dev,observed.st_ino)==(root_identity.st_dev,root_identity.st_ino),'store root replaced during seal')
            parent=root.parent
            while True:
                fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:os.fsync(fd)
                finally:os.close(fd)
                if parent==parent.parent:break
                parent=parent.parent
            return dict(qualified=True,seal_path=str(root/'SEALED.json'),seal_sha256=hashlib.sha256(encoded).hexdigest(),
                archive_count=len(bindings),referenced_body_count=len(referenced),file_count=len(files),staging=cas.inventory(root),
                seconds=time.monotonic()-started,original_archives_removed=False)
        finally:os.close(root_fd)
    finally:store.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--store',type=Path,required=True);parser.add_argument('--accepted',type=Path,required=True);parser.add_argument('--result',type=Path,required=True);args=parser.parse_args()
    try:result=seal_store(args.store,json.loads(args.accepted.read_bytes()))
    except BaseException as error:result=dict(qualified=False,error=dict(type=type(error).__name__,message=str(error)),original_archives_removed=False)
    args.result.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result),flush=True)
