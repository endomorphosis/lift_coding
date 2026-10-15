"""Stream retained tar members and compare manifest hashes without extraction.

Bound: 5 GiB regular member bytes, 2 GiB compressed read, 50,000 headers, 90s.
Never follows archive links, loads models or executes any archived code.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
import time
from collections import Counter
from audit_io import ROOT, OUT, Reader, write_json

ARCHIVE = ROOT/'artifacts/supervisor-portable-codex-worker-fix-20261014-01/runtime-campaign/runtime/runtime.tar.gz'
MANIFEST = ARCHIVE.parent/'manifest.json'

class BoundedCompressedReader:
    def __init__(self, file):self.file=file;self.bytes=0
    def read(self, size=-1):
        if size < 0:raise ValueError('Unbounded compressed read disallowed')
        data=self.file.read(size);self.bytes+=len(data)
        if self.bytes>2*1024**3:raise ValueError('Compressed byte bound exceeded')
        return data

def main():
    reader=Reader('integration');manifest=reader.json(MANIFEST,'original_runtime_manifest')
    declared={x['path']:x for x in manifest['files']}
    if len(declared)!=len(manifest['files']):raise ValueError('Duplicate manifest paths')
    verified=[];mismatches=[];undeclared=[];seen=set();kinds=Counter();member_bytes=0;headers=0
    start=time.monotonic();before=ARCHIVE.stat();error=None;compressed=0
    try:
        with ARCHIVE.open('rb') as f:
            stream=BoundedCompressedReader(f)
            with tarfile.open(fileobj=stream,mode='r|gz') as tar:
                for member in tar:
                    headers+=1
                    if headers>50000 or time.monotonic()-start>90:raise ValueError('Header/time bound exceeded')
                    name=member.name.removeprefix('./')
                    path=PurePosixPath(name)
                    if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe archive member path')
                    kind='file' if member.isfile() else 'directory' if member.isdir() else 'link_or_other'
                    kinds[kind]+=1
                    if not member.isfile():
                        if name in declared:mismatches.append({'path':name,'kind':'declared_regular_file_is_not_regular'})
                        continue
                    if name in seen:raise ValueError('Duplicate regular archive member')
                    seen.add(name)
                    if member_bytes+member.size>5*1024**3:raise ValueError('Uncompressed byte bound exceeded')
                    digest=hashlib.sha256();count=0
                    body=tar.extractfile(member)
                    while block:=body.read(1024*1024):
                        count+=len(block);member_bytes+=len(block);digest.update(block)
                        if time.monotonic()-start>90:raise ValueError('Time bound exceeded')
                    reported=declared.get(name)
                    actual={'path':name,'bytes':count,'sha256':digest.hexdigest(),'mode':member.mode}
                    if reported is None:undeclared.append(actual)
                    elif count!=reported['bytes'] or actual['sha256']!=reported['sha256']:
                        mismatches.append({'path':name,'actual':actual,'declared':reported})
                    else:verified.append(name)
            compressed=stream.bytes
    except (OSError,ValueError,tarfile.TarError) as exc:
        error={'type':type(exc).__name__,'reason':str(exc)}
    after=ARCHIVE.stat();stable=(before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns)
    missing=sorted(set(declared)-seen)
    result={'schema':'retained-runtime-member-hash-audit@1','archive_path':str(ARCHIVE),
            'manifest_path':str(MANIFEST),'manifest_sha256':reader.seen[str(MANIFEST)]['sha256'],
            'archive_sha256_reported':manifest['archive_sha256'],'archive_byte_hash_verification':'audit/large_asset_verification.json',
            'declared_files':len(declared),'verified_files':len(verified),'headers':headers,'member_types':dict(kinds),
            'regular_member_bytes':member_bytes,'compressed_bytes_read':compressed,'inspection_seconds':time.monotonic()-start,
            'stable_during_read':stable,'error':error,'missing_declared_files':missing,'mismatches':mismatches,
            'undeclared_regular_files':undeclared,'all_declared_file_bytes_verified':not error and stable and not missing and not mismatches,
            'archive_has_only_declared_regular_files':not error and not undeclared,
            'verified_roots':dict(Counter(n.split('/')[0] for n in verified)),
            'no_extraction_or_execution':True,'links_followed':False,
            'runtime_consumption_or_full_import_closure_proven':False,'signature_verification':'not_performed'}
    write_json('audit/runtime_member_verification.json',result)
    print(json.dumps({k:result[k] for k in ['declared_files','verified_files','regular_member_bytes','compressed_bytes_read','all_declared_file_bytes_verified','archive_has_only_declared_regular_files','error','inspection_seconds']}))

if __name__=='__main__':
    os.umask(0o077);main()
