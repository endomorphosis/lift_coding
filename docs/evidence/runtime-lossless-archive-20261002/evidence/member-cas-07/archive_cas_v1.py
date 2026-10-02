"""Bounded archival recipe. Reads original archives; never extracts or edits them."""
from __future__ import annotations
import argparse,fcntl,gzip,hashlib,io,json,os,pathlib,resource,sys,tarfile,time,zlib

BLOCK=1024**2
MAX_TAR=4*1024**3
MAX_BODY=512*BLOCK
MAX_RECIPE=64*BLOCK
MAX_LINE=65536
MAX_MEMBERS=60000
MAX_STAGE=5*1024**3
MAX_APPARENT=4*1024**3
SCHEMA='raw-tar-member-cas-gzip@1'

def require(value,message):
    if not value:raise ValueError(message)

def digest_file(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(BLOCK),b''):digest.update(chunk)
    return digest.hexdigest()

def regular(path):
    require(path.is_file() and not path.is_symlink(),'regular nonsymlink file required')
    st=path.stat();return (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)

def safe_digest(value):
    require(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value),'closed digest')
    return value

def gzip_parts(path):
    with path.open('rb') as stream:
        first=stream.read(10)
        require(first[:4]==b'\x1f\x8b\x08\x08','only one gzip member with FNAME flag supported')
        header=bytearray(first)
        while len(header)==10 or header[-1]!=0:
            c=stream.read(1);require(c and len(header)<4096,'bounded gzip filename');header+=c
        stream.seek(-8,2);trailer=stream.read(8)
    return bytes(header),trailer

def inventory(root):
    apparent=allocated=files=0
    for current,dirs,names in os.walk(root,followlinks=False):
        p=pathlib.Path(current);require(not p.is_symlink(),'staging symlink refused')
        allocated+=p.stat().st_blocks*512
        for d in dirs:require(not (p/d).is_symlink(),'staging directory symlink refused')
        for name in names:
            path=p/name;regular(path);st=path.stat()
            apparent+=st.st_size;allocated+=st.st_blocks*512;files+=1
    require(apparent<=MAX_APPARENT and allocated<=MAX_STAGE and files<=MAX_MEMBERS,'staging bound exceeded')
    return dict(apparent_bytes=apparent,allocated_bytes=allocated,file_count=files)

class Store:
    def __init__(self,root):
        self.root=pathlib.Path(root).resolve();self.root.mkdir(exist_ok=True)
        require(not pathlib.Path(root).is_symlink(),'staging root symlink')
        self.blobs=self.root/'blobs';self.blobs.mkdir(exist_ok=True)
        self.recipes=self.root/'recipes';self.recipes.mkdir(exist_ok=True)
        self.lock=(self.root/'archive.lock').open('a+b')
        try:
            fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.initial=inventory(self.root);self.bytes=self.initial['apparent_bytes'];self.new_bytes=0
        except BaseException:
            self.lock.close();raise

    def close(self):
        fcntl.flock(self.lock,fcntl.LOCK_UN);self.lock.close()

    def write(self,stream,data):
        require(self.bytes+len(data)<=MAX_APPARENT,'staging write ceiling')
        stream.write(data);self.bytes+=len(data);self.new_bytes+=len(data)

    def blob(self,digest):return self.blobs/(safe_digest(digest)+'.zlib')

    def retain_body(self,stream,size,expected=None):
        require(type(size) is int and 0<size<=MAX_BODY,'bounded member body')
        expected=safe_digest(expected) if expected is not None else None
        skip=expected is not None and self.blob(expected).is_file()
        tmp=self.root/'body.partial';require(not tmp.exists(),'unfinished body refused')
        output=None if skip else tmp.open('xb')
        compressor=None if skip else zlib.compressobj(1)
        h=hashlib.sha256();remaining=size
        try:
            while remaining:
                data=stream.read(min(BLOCK,remaining));require(data,'truncated body')
                h.update(data);remaining-=len(data)
                if compressor is not None:self.write(output,compressor.compress(data))
            if compressor is not None:
                self.write(output,compressor.flush());output.flush();os.fsync(output.fileno());output.close();output=None
            digest=h.hexdigest()
            if expected is not None:require(digest==expected,'manifest body digest differs')
            if skip:return digest,False
            destination=self.blob(digest)
            if destination.exists():
                regular(destination);self.bytes-=tmp.stat().st_size;tmp.unlink();return digest,False
            os.link(tmp,destination);tmp.unlink();return digest,True
        finally:
            if output is not None:output.close()

    def read_body(self,digest,size):
        path=self.blob(digest);regular(path);decoder=zlib.decompressobj();h=hashlib.sha256();total=0
        with path.open('rb') as stream:
            for raw in iter(lambda:stream.read(BLOCK),b''):
                pending=raw
                while pending:
                    data=decoder.decompress(pending,min(BLOCK,size-total+1));pending=decoder.unconsumed_tail
                    require(not decoder.unused_data,'CAS trailing data')
                    total+=len(data);require(total<=size,'CAS body exceeds recipe')
                    h.update(data);yield data
        require(decoder.eof and total==size and h.hexdigest()==digest,'CAS digest or length differs')

def parse_pax(raw):
    result={};offset=0
    while offset<len(raw):
        space=raw.find(b' ',offset);require(space>=offset,'bad PAX record')
        length=int(raw[offset:space]);require(length>space-offset+1 and offset+length<=len(raw),'bad PAX length')
        row=raw[space+1:offset+length];require(row.endswith(b'\n') and b'=' in row,'bad PAX assignment')
        key,value=row[:-1].split(b'=',1);result[key.decode()]=value.decode('utf-8','surrogateescape');offset+=length
    return result

def capture(*,archive,manifest,store,slug):
    require(slug and all(c.isalnum() or c in '-_' for c in slug),'closed recipe slug')
    before=regular(archive);manifest_identity=regular(manifest)
    require(manifest_identity[2]<=16*BLOCK,'bounded source manifest')
    model=json.loads(manifest.read_bytes());expected_archive=safe_digest(model['archive_sha256'])
    require(digest_file(archive)==expected_archive,'source archive/manifest mismatch')
    expected={r['path']:r for r in model['files']};require(len(expected)==len(model['files']),'duplicate manifest paths')
    header,trailer=gzip_parts(archive);path=store.recipes/(slug+'.jsonl');require(not path.exists(),'recipe already exists')
    first=dict(schema=SCHEMA,kind='header',archive_sha256=expected_archive,archive_bytes=before[2],
        gzip_header_hex=header.hex(),gzip_trailer_hex=trailer.hex(),manifest_sha256=digest_file(manifest),
        source_archive=str(archive),source_manifest=str(manifest),zlib_runtime=zlib.ZLIB_RUNTIME_VERSION,
        zlib_compile=zlib.ZLIB_VERSION,python=sys.version,deflate_level=1,deflate_wbits=-15,deflate_mem_level=8,deflate_strategy=0)
    tar_hash=hashlib.sha256();tar_bytes=0;members=0;new_blobs=0;global_pax={};next_pax={};next_long_name=None
    def account(data):
        nonlocal tar_bytes
        tar_hash.update(data);tar_bytes+=len(data);require(tar_bytes<=MAX_TAR,'decoded archive bound')
        return data
    class Accounted:
        def __init__(self,stream):self.stream=stream
        def read(self,count):return account(self.stream.read(count))
    def line(stream,row):
        raw=(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n').encode()
        require(len(raw)<=MAX_LINE and stream.tell()+len(raw)<=MAX_RECIPE,'recipe bounds')
        store.write(stream,raw)
    with path.open('xb') as recipe, gzip.open(archive,'rb') as compressed:
        stream=Accounted(compressed);line(recipe,first)
        while True:
            raw=stream.read(512);require(len(raw)==512,'truncated tar header')
            if raw==bytes(512):
                zeros=512
                while True:
                    tail=stream.read(BLOCK)
                    if not tail:break
                    require(not tail.strip(b'\0'),'nonzero trailing tar records unsupported');zeros+=len(tail)
                require(zeros>=1024 and zeros%512==0,'tar termination records')
                line(recipe,dict(kind='end',zero_bytes=zeros,tar_bytes=tar_bytes,tar_sha256=tar_hash.hexdigest(),members=members));break
            info=tarfile.TarInfo.frombuf(raw,'utf-8','surrogateescape')
            require(0<=info.size<=MAX_BODY,'bounded tar header size')
            members+=1;require(members<=MAX_MEMBERS,'member count bound')
            body=None;name=next_long_name or next_pax.get('path') or global_pax.get('path') or info.name
            if info.size:
                if info.type in (tarfile.XHDTYPE,tarfile.XGLTYPE,tarfile.GNUTYPE_LONGNAME,tarfile.GNUTYPE_LONGLINK):
                    require(info.size<=BLOCK,'bounded metadata body');data=stream.read(info.size);require(len(data)==info.size,'metadata length')
                    body,created=store.retain_body(io.BytesIO(data),info.size)
                    if info.type==tarfile.XHDTYPE:next_pax=parse_pax(data)
                    elif info.type==tarfile.XGLTYPE:global_pax.update(parse_pax(data))
                    elif info.type==tarfile.GNUTYPE_LONGNAME:next_long_name=data.rstrip(b'\0').decode('utf-8','surrogateescape')
                else:
                    record=expected.get(name)
                    predicted=record['sha256'] if record is not None and record['bytes']==info.size else None
                    body,created=store.retain_body(stream,info.size,predicted)
                new_blobs+=int(created)
            padding=stream.read((-info.size)%512);require(len(padding)==(-info.size)%512,'truncated body padding')
            line(recipe,dict(kind='member',header_hex=raw.hex(),body_bytes=info.size,body_sha256=body,padding_hex=padding.hex()))
            if info.type not in (tarfile.XHDTYPE,tarfile.XGLTYPE,tarfile.GNUTYPE_LONGNAME,tarfile.GNUTYPE_LONGLINK):next_pax={};next_long_name=None
            if members%1000==0:inventory(store.root)
        recipe.flush();os.fsync(recipe.fileno())
    require(regular(archive)==before and regular(manifest)==manifest_identity,'original changed during capture')
    usage=inventory(store.root)
    return dict(recipe=str(path),recipe_sha256=digest_file(path),archive_sha256=expected_archive,
        source_identity_unchanged=True,decoded_tar_bytes=tar_bytes,members=members,new_blobs=new_blobs,staging=usage)

def reconstruct(*,recipe,store):
    before=regular(recipe);require(before[2]<=MAX_RECIPE,'recipe maximum')
    total=tar_bytes=0;tar_hash=hashlib.sha256();gzip_hash=hashlib.sha256();compressor=zlib.compressobj(1,zlib.DEFLATED,-15)
    members=0;ended=False;first=None
    def emit(data):
        nonlocal tar_bytes,total
        tar_bytes+=len(data);require(tar_bytes<=MAX_TAR,'replay tar bound');tar_hash.update(data)
        raw=compressor.compress(data);gzip_hash.update(raw);total+=len(raw)
    with recipe.open('rb') as stream:
        for ordinal,raw in enumerate(stream):
            require(len(raw)<=MAX_LINE,'recipe line bound');row=json.loads(raw)
            if ordinal==0:
                first=row;require(row['schema']==SCHEMA and row['kind']=='header','closed recipe header')
                require(row['zlib_runtime']==zlib.ZLIB_RUNTIME_VERSION and row['deflate_level']==1 and row['deflate_wbits']==-15 and row['deflate_mem_level']==8 and row['deflate_strategy']==0,'pinned deflate profile')
                header=bytes.fromhex(row['gzip_header_hex']);require(len(header)<=4096,'gzip header bound')
                gzip_hash.update(header);total+=len(header);continue
            require(not ended,'rows after termination')
            if row['kind']=='member':
                members+=1;require(members<=MAX_MEMBERS,'replay member count')
                header=bytes.fromhex(row['header_hex']);require(len(header)==512,'exact tar header')
                info=tarfile.TarInfo.frombuf(header,'utf-8','surrogateescape');size=row['body_bytes']
                require(type(size) is int and 0<=size<=MAX_BODY and info.size==size,'tar header/body size join')
                emit(header)
                if size:
                    for data in store.read_body(safe_digest(row['body_sha256']),size):emit(data)
                else:require(row['body_sha256'] is None,'zero body cannot have blob')
                pad=bytes.fromhex(row['padding_hex']);require(len(pad)==(-size)%512,'exact padding size');emit(pad)
            elif row['kind']=='end':
                count=row['zero_bytes'];require(type(count) is int and 1024<=count<=MAX_TAR and count%512==0,'termination size')
                while count:
                    data=bytes(min(BLOCK,count));emit(data);count-=len(data)
                require(tar_bytes==row['tar_bytes'] and tar_hash.hexdigest()==row['tar_sha256'] and members==row['members'],'complete tar digest/population join')
                ended=True
            else:raise ValueError('unknown recipe row')
    require(first is not None and ended,'complete recipe required')
    raw=compressor.flush();gzip_hash.update(raw);total+=len(raw)
    trailer=bytes.fromhex(first['gzip_trailer_hex']);require(len(trailer)==8,'gzip trailer size');gzip_hash.update(trailer);total+=8
    require(total==first['archive_bytes'] and gzip_hash.hexdigest()==first['archive_sha256'],'original gzip hash/length mismatch')
    require(regular(recipe)==before,'recipe changed during replay')
    return dict(exact=True,archive_sha256=gzip_hash.hexdigest(),archive_bytes=total,tar_sha256=tar_hash.hexdigest(),
        tar_bytes=tar_bytes,members=members,recipe_sha256=digest_file(recipe),original_archive_read_during_replay=False,
        expanded_tar_or_gzip_written=False,zlib_runtime=zlib.ZLIB_RUNTIME_VERSION)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=pathlib.Path);parser.add_argument('--manifest',type=pathlib.Path)
    parser.add_argument('--store',required=True,type=pathlib.Path);parser.add_argument('--slug');parser.add_argument('--recipe',type=pathlib.Path)
    parser.add_argument('--result',required=True,type=pathlib.Path);args=parser.parse_args();started=time.monotonic();store=None
    result=dict(schema='native-runtime-member-cas-qualification@1',qualified=False,originals_modified=False)
    try:
        store=Store(args.store)
        if args.recipe is None:
            step=time.monotonic();result['capture']=capture(archive=args.archive,manifest=args.manifest,store=store,slug=args.slug);result['capture_seconds']=time.monotonic()-step
            recipe=pathlib.Path(result['capture']['recipe'])
        else:recipe=args.recipe
        step=time.monotonic();result['reconstruction']=reconstruct(recipe=recipe,store=store);result['reconstruction_seconds']=time.monotonic()-step
        result['staging']=inventory(store.root);result['qualified']=True
    except BaseException as error:result['error']={'type':type(error).__name__,'message':str(error)}
    finally:
        if store is not None:store.close()
        usage=resource.getrusage(resource.RUSAGE_SELF);result.update(seconds=time.monotonic()-started,peak_rss_bytes=usage.ru_maxrss*1024,
            cpu_user_seconds=usage.ru_utime,cpu_system_seconds=usage.ru_stime)
        args.result.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({k:result.get(k) for k in ('qualified','seconds','peak_rss_bytes','error')}),flush=True)
    return 0 if result['qualified'] else 1

if __name__=='__main__':sys.exit(main())
