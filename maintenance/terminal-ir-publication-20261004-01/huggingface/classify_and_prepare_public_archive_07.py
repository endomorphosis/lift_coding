"""Bounded local credential/container classification and physical public derivative.

Consumes only a closed local archive snapshot. No network/upload API is present.
Original files, original shards and previous receipts are never modified.
"""
from __future__ import annotations
import argparse
import bz2
import collections
import ctypes
import gzip
import hashlib
import importlib.util
import io
import json
import lzma
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import tarfile
import tempfile
import time
import zipfile

BLOCK = 1024**2
PEM = re.compile(rb'-----BEGIN ((?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?)PRIVATE KEY-----[ \t]{0,64}(?:\r?\n|\\n)(?:[A-Za-z0-9+/=,: \t-]{1,128}(?:\r?\n|\\n)){1,256}-----END \1PRIVATE KEY-----')
SCHEMA = 'terminal-ir-public-archive-classification@1'


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def sha(value): return hashlib.sha256(value).hexdigest()


def save(path, value):
    with path.open('xb') as stream:
        stream.write(wire(value) + b'\n'); stream.flush(); os.fsync(stream.fileno())


def pin(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW); digest = hashlib.sha256(); count = 0
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode): raise ValueError('regular input required')
        while block := os.read(fd, BLOCK): digest.update(block); count += len(block)
        after = os.fstat(fd)
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) != (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns): raise ValueError('input changed during read')
    finally: os.close(fd)
    return {'path': str(path), 'bytes': count, 'sha256': digest.hexdigest()}


class Refusal(ValueError): pass


class BoundedParserReads:
    """Refuse large parser metadata allocations; ordinary payloads stream."""
    def __init__(self, stream): self.stream=stream
    def read(self, count=-1):
        if count<0:
            here=self.stream.tell();self.stream.seek(0,2);count=self.stream.tell()-here;self.stream.seek(here)
        if count>8*1024**2:raise Refusal('parser_metadata_read_budget')
        return self.stream.read(count)
    def seek(self,*args):return self.stream.seek(*args)
    def tell(self):return self.stream.tell()
    def seekable(self):return True
    def __getattr__(self,name):return getattr(self.stream,name)


class Budget:
    def __init__(self, seconds, decoded_bytes, container_bytes, members, depth):
        self.deadline = time.monotonic() + seconds
        self.total_max, self.container_max, self.members_max, self.depth_max = decoded_bytes,container_bytes,members,depth
        self.decoded = 0; self.members = 0
    def check(self):
        if time.monotonic() >= self.deadline: raise Refusal('wall_budget')
    def member(self):
        self.check(); self.members += 1
        if self.members > self.members_max: raise Refusal('member_budget')
    def charge(self, count, own_count):
        self.check(); self.decoded += count
        if self.decoded > self.total_max or own_count > self.container_max: raise Refusal('decoded_byte_budget')


class SourceChunks:
    """At most three <=252MiB raw tar caches; compressed/raw chunk pins checked."""
    def __init__(self, build, manifest, db, private, budget, api):
        self.build,self.db,self.private,self.budget,self.api = build,db,private,budget,api
        self.archives = {item['archive']:item for item in manifest['data_shards']}
        self.cache = collections.OrderedDict()
        if pin(Path(manifest['zstd_library']['path']))!=manifest['zstd_library'] or pin(Path(manifest['zstd_executable']['path']))!=manifest['zstd_executable']:raise Refusal('compression_tool_pin')
        lib = ctypes.CDLL(manifest['zstd_library']['path'])
        lib.ZSTD_decompress.argtypes = [ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t]
        lib.ZSTD_decompress.restype = ctypes.c_size_t
        lib.ZSTD_isError.argtypes = [ctypes.c_size_t]; lib.ZSTD_isError.restype = ctypes.c_uint
        self.lib = lib
    def tar(self, name):
        self.budget.check()
        if name in self.cache:
            self.cache.move_to_end(name); return self.cache[name][1]
        binding = self.archives[name]; origin = self.build/'public'/name
        if pin(origin) != binding_subset(binding): raise Refusal('archive_pin')
        if len(self.cache) == 3:
            _,(path,archive) = self.cache.popitem(last=False); archive.close(); path.unlink()
        target = self.private/(name+'.tar-cache'); child = None
        try:
            with target.open('xb') as output:
                child = subprocess.Popen(['/usr/bin/zstd','--quiet','-d','--stdout',str(origin)],stdout=output,stderr=subprocess.PIPE,start_new_session=True)
                _,errors = child.communicate(timeout=min(300,max(1,self.budget.deadline-time.monotonic())))
            if child.returncode or target.stat().st_size != binding['tar_bytes'] or target.stat().st_size > 252*1024**2: raise Refusal('archive_decode')
            archive = tarfile.open(target,'r:'); self.cache[name]=(target,archive); return archive
        except BaseException:
            if child is not None and child.poll() is None: os.killpg(child.pid,9); child.wait()
            target.unlink(missing_ok=True); raise
    def raw(self, item):
        row = self.db.execute('SELECT raw_bytes,location FROM chunks WHERE sha256=?',(item['sha256'],)).fetchone()
        if row is None: raise Refusal('missing_snapshot_chunk')
        raw_count,encoded = row; location = json.loads(encoded)
        if item['bytes'] != raw_count: raise Refusal('chunk_length')
        member = self.tar(location['archive']).extractfile(location['member'])
        if member is None: raise Refusal('chunk_member')
        compressed = member.read(9*1024**2+1)
        if len(compressed) != location['stored_bytes'] or sha(compressed) != location['stored_sha256']: raise Refusal('stored_chunk_pin')
        output=ctypes.create_string_buffer(max(1,raw_count)); source=ctypes.create_string_buffer(compressed)
        count=self.lib.ZSTD_decompress(output,raw_count,source,len(compressed))
        if self.lib.ZSTD_isError(count) or count != raw_count: raise Refusal('raw_chunk_decode')
        raw=output.raw[:count]
        if sha(raw) != item['sha256']: raise Refusal('raw_chunk_pin')
        return raw
    def close(self):
        for path,archive in self.cache.values(): archive.close(); path.unlink(missing_ok=True)
        self.cache.clear()


def binding_subset(value): return {key:value[key] for key in ('path','bytes','sha256')}


class Classifier:
    def __init__(self, scanner, budget, temporary):
        self.scanner,self.budget,self.temporary=scanner,budget,temporary
        self.counts=collections.Counter(); self.hits=set(); self.scope_events=[]
    def hits_in(self, block):
        return {(name,sha(m.group())) for name,pattern in self.scanner.patterns for m in pattern.finditer(block)} | {('exact_available_credential',sha(token)) for token in self.scanner.known if token in block} | {('complete_private_key_pem_or_escaped',sha(m.group())) for m in PEM.finditer(block)}
    def inspect(self, stream, depth=0, already_decoded=False):
        self.budget.check()
        if depth > self.budget.depth_max: raise Refusal('depth_budget')
        stream.seek(0); prefix=stream.read(512); stream.seek(0)
        fmt=self.format(prefix); tail=b''; count=0
        spool=stream if fmt else None
        try:
            while block:=stream.read(BLOCK):
                self.budget.check(); count+=len(block)
                if already_decoded: self.budget.charge(len(block),count)
                self.hits.update(self.hits_in(tail+block)); tail=(tail+block)[-65536:]
                if spool and not already_decoded and count>4*1024**3: raise Refusal('seekable_container_budget')
            self.counts['streams']+=1; self.counts['raw_stream_bytes']+=count
            if not fmt: return
            self.counts['containers']+=1; spool.seek(0)
            if fmt=='tar':
                with tarfile.open(fileobj=BoundedParserReads(spool),mode='r:') as archive:
                    for item in archive:
                        self.budget.member(); self.hits.update(self.hits_in(os.fsencode(item.name)))
                        if item.issym() or item.islnk(): self.hits.update(self.hits_in(os.fsencode(item.linkname)))
                        if item.isfile():
                            body=archive.extractfile(item)
                            if body is None: raise Refusal('tar_member')
                            with tempfile.TemporaryFile(dir=self.temporary) as payload:
                                self.copy(body,payload); payload.seek(0); self.inspect(payload,depth+1,True)
            elif fmt=='zip':
                with zipfile.ZipFile(BoundedParserReads(spool)) as archive:
                    for item in archive.infolist():
                        self.budget.member(); self.hits.update(self.hits_in(os.fsencode(item.filename)))
                        if item.flag_bits&1: raise Refusal('encrypted_zip')
                        if item.is_dir(): continue
                        with archive.open(item) as body,tempfile.TemporaryFile(dir=self.temporary) as payload:
                            self.copy(body,payload); payload.seek(0); self.inspect(payload,depth+1,True)
            else:
                with tempfile.TemporaryFile(dir=self.temporary) as payload:
                    if fmt=='zstd': self.zstd(spool,payload)
                    else:
                        constructor={'gzip':gzip.GzipFile,'xz':lzma.LZMAFile,'bzip2':bz2.BZ2File}.get(fmt)
                        if constructor is None: raise Refusal('unsupported_container_'+fmt)
                        with (constructor(fileobj=spool,mode='rb') if fmt=='gzip' else constructor(spool,'rb')) as decoded: self.copy(decoded,payload)
                    payload.seek(0); self.inspect(payload,depth+1,True)
        finally:
            pass  # Caller owns the pinned seekable payload; no second full copy.
    @staticmethod
    def format(prefix):
        for name,magic in [('gzip',b'\x1f\x8b'),('zip',b'PK\x03\x04'),('xz',b'\xfd7zXZ\x00'),('zstd',b'\x28\xb5\x2f\xfd'),('bzip2',b'BZh'),('7zip',b'7z\xbc\xaf\x27\x1c'),('rar',b'Rar!')]:
            if prefix.startswith(magic): return name
        return 'tar' if len(prefix)>262 and prefix[257:262]==b'ustar' else None
    def copy(self, source, target):
        count=0
        while block:=source.read(BLOCK):
            self.budget.check(); count+=len(block)
            if count>self.budget.container_max: raise Refusal('container_decode_budget')
            target.write(block)
    def zstd(self, source, target):
        fd,path=tempfile.mkstemp(dir=self.temporary,prefix='zstd-'); os.close(fd); path=Path(path); child=None
        try:
            source.seek(0)
            with path.open('wb') as encoded: shutil.copyfileobj(source,encoded,BLOCK)
            child=subprocess.Popen(['/usr/bin/zstd','--quiet','-d','--stdout',str(path)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
            self.copy(child.stdout,target); child.stdout.close()
            if child.wait(timeout=max(1,self.budget.deadline-time.monotonic())): raise Refusal('zstd_container_decode')
        finally:
            if child is not None and child.poll() is None: os.killpg(child.pid,9); child.wait()
            path.unlink(missing_ok=True)


def raw_file(record, source, chunks, temporary, budget):
    payload=tempfile.TemporaryFile(dir=temporary); digest=hashlib.sha256(); count=0
    try:
        if record['status']=='quarantined_credential_candidate':
            fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW)
            try:
                before=os.fstat(fd)
                if not stat.S_ISREG(before.st_mode): raise Refusal('quarantine_source_type')
                while block:=os.read(fd,BLOCK): budget.check(); digest.update(block); count+=len(block); payload.write(block)
                after=os.fstat(fd)
                if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns): raise Refusal('quarantine_source_changed')
            finally: os.close(fd)
        else:
            for item in record['chunks']:
                budget.check(); block=chunks.raw(item); digest.update(block); count+=len(block); payload.write(block)
        if count!=record['bytes'] or digest.hexdigest()!=record['full_sha256']: raise Refusal('full_file_snapshot_pin')
        payload.seek(0); return payload
    except BaseException: payload.close(); raise


def load_helper(path, expected):
    binding=pin(path)
    if binding['sha256']!=expected: raise ValueError('helper pin')
    spec=importlib.util.spec_from_file_location('frozen_local_archive_api',path); api=importlib.util.module_from_spec(spec); spec.loader.exec_module(api)
    return api,binding


def run(args,output,state):
    api,helper=load_helper(args.helper,args.expected_helper_sha256)
    manifestpath=args.build/'public/archive-manifest.json'; manifestpin=pin(manifestpath)
    if manifestpin['sha256']!=args.expected_archive_manifest_sha256: raise ValueError('archive manifest pin')
    manifest=json.loads(manifestpath.read_bytes()); closed=json.loads((args.build/'closed.json').read_bytes())
    if closed['status']!='prepared_local_shards_requires_root_review' or manifest['status']!='prepared_local_shards_requires_root_review': raise ValueError('closed successful local build required')
    approvals=json.loads(args.approvals.read_bytes()); approvalpin=pin(args.approvals)
    if approvalpin['sha256']!=args.expected_approvals_sha256 or approvals['schema']!='terminal-ir-publication-classification-approvals@1': raise ValueError('approval pin/schema')
    allow={item['file_sha256']:item for item in approvals.get('public_fixture_files',[])}
    approved_containers={item['file_sha256']:item for item in approvals.get('public_container_provenance',[])}
    budget=Budget(args.wall_seconds,args.decoded_bytes,args.container_bytes,args.member_limit,args.depth_limit)
    private=output/'private';private.mkdir(); public=output/'public';public.mkdir()
    db=sqlite3.connect('file:'+str(args.build/'private/path-index.sqlite')+'?mode=ro',uri=True)
    work=sqlite3.connect(private/'classification.sqlite');work.execute('CREATE TABLE files(sha256 TEXT PRIMARY KEY,record TEXT,source TEXT,result TEXT)');work.execute('CREATE TABLE forbidden(sha256 TEXT PRIMARY KEY)')
    scanner=api.Scanner();scanner.patterns=[(name,pattern) for name,pattern in api.PATTERNS if name!='private_key_pem']; chunks=SourceChunks(args.build,manifest,db,private,budget,api)
    scanned=0; regular_paths=0;captured_regular_paths=0; result_counts=collections.Counter(); grouping={}
    try:
        path_digest=hashlib.sha256();node_count=0
        for encoded,private_encoded,namespace,relative in db.execute('SELECT public_record,private_record,namespace,relative_path FROM nodes ORDER BY namespace,relative_path'):
            budget.check();path_digest.update(encoded.encode('ascii')+b'\n');node_count+=1
            public_record=json.loads(encoded);private_record=json.loads(private_encoded)
            if private_record['namespace']!=namespace or private_record['path']!=relative:raise Refusal('private_path_identity')
            if public_record.get('path',relative)!=relative or public_record.get('namespace')!=namespace:raise Refusal('public_path_identity')
            if 'path_sha256' in public_record and public_record['path_sha256']!=sha(os.fsencode(relative)):raise Refusal('redacted_path_identity')
            for field in ('full_sha256','bytes','chunks'):
                if field in public_record and public_record[field]!=private_record.get(field):raise Refusal('private_public_file_binding')
        if path_digest.hexdigest()!=manifest['path_jsonl_sha256'] or node_count!=manifest['node_count']:raise Refusal('original_path_index_root')
        chunk_digest=hashlib.sha256();chunk_count=0;raw_count=0
        for digest,size,location in db.execute('SELECT sha256,raw_bytes,location FROM chunks ORDER BY sha256'):
            budget.check();chunk_digest.update(wire({'sha256':digest,'raw_bytes':size,**json.loads(location)})+b'\n');chunk_count+=1;raw_count+=size
        if chunk_digest.hexdigest()!=manifest['chunk_jsonl_sha256'] or chunk_count!=manifest['unique_chunks'] or raw_count!=manifest['unique_raw_chunk_bytes']:raise Refusal('original_chunk_index_root')
        for source,encoded in db.execute('SELECT source,private_record FROM nodes'):
            budget.check(); record=json.loads(encoded)
            if record.get('node_type')=='regular':regular_paths+=1
            if record.get('node_type')!='regular' or 'full_sha256' not in record: continue
            captured_regular_paths+=1
            work.execute('INSERT OR IGNORE INTO files VALUES (?,?,?,NULL)',(record['full_sha256'],encoded,source))
            if re.search(r'\.part-\d+$',record['path']):
                group=(record['namespace'],re.sub(r'\d+$','',record['path']))
                grouping.setdefault(group,[]).append((int(re.search(r'\d+$',record['path']).group()),record,source))
        work.commit()
        # First chunk/archive ordering keeps the bounded raw-tar cache useful.
        for file_sha,encoded,source in work.execute('SELECT sha256,record,source FROM files ORDER BY rowid'):
            budget.check(); record=json.loads(encoded); classifier=Classifier(scanner,budget,private); error=None
            try:
                with raw_file(record,Path(source),chunks,private,budget) as payload: classifier.inspect(payload)
            except Exception as problem:
                error=str(problem) if isinstance(problem,Refusal) else type(problem).__name__
            hits=[{'pattern':name,'match_sha256':value} for name,value in sorted(classifier.hits)]
            status='unresolved_container_or_read' if error else 'quarantined_credential_candidate' if hits else 'scanned_no_named_candidates'
            approval=allow.get(file_sha)
            if not error and hits and approval and not any(item['pattern']=='exact_available_credential' for item in hits):
                if set(item['match_sha256'] for item in hits)<=set(approval['approved_match_sha256']) and approval.get('classification')=='published_public_fixture' and approval.get('provenance_ref'):
                    status='approved_exact_public_fixture'
            if error and not hits and file_sha in approved_containers and approved_containers[file_sha].get('provenance_ref'):
                status='approved_exact_public_container_provenance'
            result={'file_sha256':file_sha,'status':status,'candidate_hits':hits,'error':error,'scanner_stream_counts':dict(classifier.counts),'decoded_scan_complete':error is None,'approval':approval if status=='approved_exact_public_fixture' else approved_containers.get(file_sha) if status=='approved_exact_public_container_provenance' else None}
            work.execute('UPDATE files SET result=? WHERE sha256=?',(wire(result).decode(),file_sha));scanned+=1;result_counts[status]+=1
            if scanned%1000==0:work.commit();print(json.dumps({'classified_unique_files':scanned,'status_counts':dict(result_counts),'decoded_bytes':budget.decoded}),flush=True)
        # Multipart archives are decoded as exact contiguous ordered raw snapshots.
        group_results=[]
        for (namespace,name),parts in sorted(grouping.items()):
            unique={number:(record,source) for number,record,source in parts}; ordered=sorted(unique)
            declaration=next((item for item in approvals.get('split_groups',[]) if item['namespace']==namespace and item['path_prefix']==name),None)
            lineage_ok=False
            if declaration:
                source_manifest=declaration['source_manifest'];source_path=Path(source_manifest['path'])
                if pin(source_path)!=source_manifest:raise Refusal('split_preservation_manifest_pin')
                source_doc=json.loads(source_path.read_bytes())
                if source_doc['schema']!=declaration['expected_source_schema']:raise Refusal('split_preservation_manifest_schema')
                all_declared=[{key:item[key] for key in ('path','sha256','bytes')} for item in source_doc[declaration['source_manifest_field']] if item['path'].startswith(name) and re.search(r'\.part-\d+$',item['path'])]
                all_declared.sort(key=lambda item:int(re.search(r'\d+$',item['path']).group()))
                expected_parts=declaration['ordered_parts']
                actual_parts=[{'path':unique[number][0]['path'],'sha256':unique[number][0]['full_sha256'],'bytes':unique[number][0]['bytes']} for number in ordered]
                lineage_ok=all_declared==expected_parts==actual_parts
            if not declaration:result={'status':'unresolved_split_archive_missing_explicit_lineage'}
            elif not lineage_ok:result={'status':'unresolved_split_archive_manifest_population'}
            elif ordered!=list(range(min(ordered),max(ordered)+1)) or min(ordered) not in (0,1): result={'status':'unresolved_split_archive_sequence'}
            else:
                classifier=Classifier(scanner,budget,private); error=None
                try:
                    with tempfile.TemporaryFile(dir=private) as whole:
                        total=0
                        for number in ordered:
                            record,source=unique[number]
                            with raw_file(record,Path(source),chunks,private,budget) as payload:
                                while block:=payload.read(BLOCK):
                                    total+=len(block)
                                    if total>4*1024**3:raise Refusal('split_seekable_budget')
                                    whole.write(block)
                        whole.seek(0); classifier.inspect(whole)
                except Exception as problem:error=str(problem) if isinstance(problem,Refusal) else type(problem).__name__
                hits=[{'pattern':a,'match_sha256':b} for a,b in sorted(classifier.hits)]
                result={'status':'unresolved_split_archive' if error else 'quarantined_decoded_split_archive' if hits else 'scanned_split_archive_no_named_candidates','error':error,'candidate_hits':hits,'parts':[unique[n][0]['full_sha256'] for n in ordered]}
            result.update({'namespace':namespace,'group_path_sha256':sha(os.fsencode(name))});group_results.append(result)
            for record,source in unique.values():
                old=json.loads(work.execute('SELECT result FROM files WHERE sha256=?',(record['full_sha256'],)).fetchone()[0])
                old['individual_part_status_before_group']=old['status'];old['individual_part_error_before_group']=old.get('error');previous_group=old.get('split_group');old.setdefault('split_group_results',[]).append(result);old['split_group']=result
                previous_denial=next((item['status'] for item in old['split_group_results'] if not item['status'].startswith('scanned_')),None) or old.get('split_group_denial') or (old['status'] if old.get('candidate_hits') and old['status'] not in ('scanned_no_named_candidates','approved_exact_public_fixture','approved_exact_public_container_provenance') else None)
                old['split_group_denial']=previous_denial
                context_safe=result['status'].startswith('scanned_') and previous_denial is None
                if context_safe:old['error']=None
                old['status']='scanned_no_named_candidates' if context_safe else (previous_denial or result['status'])
                old['decoded_scan_complete']=context_safe
                work.execute('UPDATE files SET result=? WHERE sha256=?',(wire(old).decode(),record['full_sha256']))
        work.commit()
        # Conservative closure: no byte chunk originating in an excluded file can
        # remain public merely because another path references the same chunk.
        again=True; closure_rounds=0
        while again:
            again=False;closure_rounds+=1
            for file_sha,encoded,result in work.execute('SELECT sha256,record,result FROM files'):
                record=json.loads(encoded); classified=json.loads(result)
                safe=classified['status'] in ('scanned_no_named_candidates','approved_exact_public_fixture','approved_exact_public_container_provenance')
                shared=any(work.execute('SELECT 1 FROM forbidden WHERE sha256=?',(c['sha256'],)).fetchone() for c in record['chunks']) if safe else False
                if shared:
                    classified['status']='quarantined_shared_chunk_closure';work.execute('UPDATE files SET result=? WHERE sha256=?',(wire(classified).decode(),file_sha));safe=False
                if not safe:
                    for item in record['chunks']:
                        if work.execute('INSERT OR IGNORE INTO forbidden VALUES (?)',(item['sha256'],)).rowcount:again=True
            work.commit()
        forbidden={row[0] for row in work.execute('SELECT sha256 FROM forbidden')}
        # Preserve every path's identity/classification. Excluded paths have no
        # reconstruction references and are explicitly not byte-complete public.
        def paths():
            for encoded,private_encoded in db.execute('SELECT public_record,private_record FROM nodes ORDER BY namespace,relative_path'):
                record=json.loads(encoded); file_sha=record.get('full_sha256')
                if file_sha:
                    row=work.execute('SELECT result FROM files WHERE sha256=?',(file_sha,)).fetchone();result=json.loads(row[0]) if row else None
                    record['public_classification']=result
                    if result and result['status'] not in ('scanned_no_named_candidates','approved_exact_public_fixture','approved_exact_public_container_provenance'):
                        record.pop('chunks',None);record['public_original_bytes_included']=False;record['status']='public_quarantined_'+result['status']
                    else:
                        record['public_original_bytes_included']=True
                        if 'chunks' not in record:record['chunks']=json.loads(private_encoded).get('chunks',[])
                yield wire(record).decode()
        data=[];rewritten=0;known_chunks=set();new_locations={}
        for name,binding in chunks.archives.items():
            budget.check(); archive=chunks.tar(name);members=archive.getmembers()
            affected=any(Path(member.name).stem in forbidden for member in members)
            if not affected:data.append({**binding,'source_path':str(args.build/'public'/name),'derivative_rewritten':False});continue
            raw=public/(name+'.partial');tar=tarfile.open(raw,'x',format=tarfile.USTAR_FORMAT)
            try:
                for member in members:
                    digest=Path(member.name).stem
                    if digest in forbidden:continue
                    body=archive.extractfile(member)
                    if body is None:raise Refusal('derivative_member')
                    tar.addfile(member,body)
            finally:tar.close()
            result=api.compress_file(raw,public/name,'/usr/bin/zstd',budget.deadline,256*1024**2);result.update({'archive':name,'source_path':str(public/name),'derivative_rewritten':True,'tar_bytes':raw.stat().st_size});raw.unlink();data.append(result);rewritten+=1
        # Approved exact-public fixture contents initially quarantined by the raw
        # builder must be genuinely restored from their exact retained snapshot.
        append=api.Shards(public,'/usr/bin/zstd',budget.deadline);append.number=len(data)
        encoder=api.Zstd(Path(manifest['zstd_library']['path']))
        for file_sha,encoded,source,result in work.execute('SELECT sha256,record,source,result FROM files'):
            classification=json.loads(result);record=json.loads(encoded)
            if classification['status'] not in ('approved_exact_public_fixture','approved_exact_public_container_provenance'):continue
            if record['status']!='quarantined_credential_candidate':continue
            with raw_file(record,Path(source),chunks,private,budget) as payload:
                for item in record['chunks']:
                    block=payload.read(item['bytes'])
                    if sha(block)!=item['sha256']:raise Refusal('approved_fixture_chunk_pin')
                    if item['sha256'] in forbidden or item['sha256'] in new_locations:continue
                    existing=db.execute('SELECT 1 FROM chunks WHERE sha256=?',(item['sha256'],)).fetchone()
                    if existing:continue
                    compressed=encoder.compress(block);temporary=private/(item['sha256']+'.restore');temporary.write_bytes(compressed)
                    location=append.append(item['sha256'],temporary,len(compressed),sha(compressed));temporary.unlink()
                    new_locations[item['sha256']]={'raw_bytes':len(block),**location}
        append.finish();data.extend({**item,'source_path':item['path'],'derivative_rewritten':True} for item in append.finished)
        def index():
            for digest,size,location in db.execute('SELECT sha256,raw_bytes,location FROM chunks ORDER BY sha256'):
                if digest not in forbidden:yield wire({'sha256':digest,'raw_bytes':size,**json.loads(location)}).decode()
            for digest,location in sorted(new_locations.items()):yield wire({'sha256':digest,**location}).decode()
        for file_sha,encoded,result in work.execute('SELECT sha256,record,result FROM files'):
            classification=json.loads(result);record=json.loads(encoded)
            if classification['status'] not in ('scanned_no_named_candidates','approved_exact_public_fixture','approved_exact_public_container_provenance'):continue
            if sum(item['bytes'] for item in record['chunks'])!=record['bytes']:raise Refusal('public_file_chunk_length')
            for item in record['chunks']:
                if item['sha256'] in forbidden or (item['sha256'] not in new_locations and db.execute('SELECT 1 FROM chunks WHERE sha256=?',(item['sha256'],)).fetchone() is None):raise Refusal('public_file_chunk_missing')
        path_shards,path_root=api.jsonl_shards(paths(),public,'paths','/usr/bin/zstd',budget.deadline)
        chunk_shards,chunk_root=api.jsonl_shards(index(),public,'chunks','/usr/bin/zstd',budget.deadline)
        states=collections.Counter(json.loads(row[0])['status'] for row in work.execute('SELECT result FROM files'))
        unresolved=sum(count for status,count in states.items() if status.startswith('unresolved'))
        for binding in manifest['source_scope_declarations']['strict_pinned_inputs']:
            if pin(Path(binding['path']))!=binding:raise Refusal('strict_original_pin_changed')
        for field in ('zstd_library','zstd_executable'):
            if pin(Path(manifest[field]['path']))!=manifest[field]:raise Refusal('compression_tool_final_pin')
        if pin(manifestpath)!=manifestpin or pin(args.helper)!=helper or pin(args.approvals)!=approvalpin:raise Refusal('classification_input_drift')
        state.update({'status':'closed_public_derivative_requires_root_classification_review','input_archive_manifest':manifestpin,'helper':helper,'approvals':approvalpin,'unique_files_classified':scanned,'classification_counts':dict(states),'group_results':group_results,'forbidden_unique_chunks':len(forbidden),'shared_chunk_closure_rounds':closure_rounds,'rewritten_original_shards':rewritten,'data_shards':data,'path_manifest_shards':path_shards,'path_jsonl_sha256':path_root,'chunk_index_shards':chunk_shards,'chunk_jsonl_sha256':chunk_root,'actual_decoded_bytes':budget.decoded,'actual_archive_members':budget.members,'original_regular_file_paths':regular_paths,'captured_regular_snapshot_paths':captured_regular_paths,'publication_administration_or_other_regular_metadata_only_paths':regular_paths-captured_regular_paths,'original_selected_nodes_preserved_as_path_metadata':manifest['node_count'],'original_raw_bytes_all_published':not forbidden and manifest['unresolved_source_nodes']==0 and regular_paths==captured_regular_paths,'unresolved_unique_files':unresolved,'source_enumeration_errors':manifest['first_enumeration_errors']+manifest['final_enumeration_errors'],'upload_qualified':unresolved==0 and manifest['unresolved_source_nodes']==0 and not manifest['first_enumeration_errors'] and not manifest['final_enumeration_errors'],'universal_secret_free_claim':False,'model_training_calls':0,'prover_calls':0,'remote_mutations':0,'proof_authority':False,'source_atomic':False,'source_open_scope':'Final file O_NOFOLLOW plus parent resolution and file stat consistency; not an atomic openat-chain containment proof','root_public_provenance_adjudication_independently_proved_by_reader':False,'PEM_profile':'Matching actual/escaped newline blocks: header whitespace <=64 bytes, body <=256 lines each <=128 chars, total match <34KiB; 64KiB overlap guarantees this bounded profile. Exotic larger encodings outside this profile are not universally qualified.'})
        save(public/'archive-manifest.json',state)
        with (private/'file-classifications.jsonl').open('xb') as stream:
            for row in work.execute('SELECT result FROM files ORDER BY sha256'):stream.write(row[0].encode()+b'\n')
    finally:chunks.close();work.commit();work.close();db.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','helper','approvals','output'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('archive-manifest','helper','approvals'):p.add_argument('--expected-'+name+'-sha256',required=True)
    p.add_argument('--wall-seconds',type=float,default=7200);p.add_argument('--decoded-bytes',type=int,default=128*1024**3)
    p.add_argument('--container-bytes',type=int,default=16*1024**3);p.add_argument('--member-limit',type=int,default=1000000);p.add_argument('--depth-limit',type=int,default=4)
    args=p.parse_args();start=time.monotonic();output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    state={'schema':SCHEMA,'status':'running','started_wall_time':time.time(),'primary_error_type':None,'budget':{'wall_seconds':args.wall_seconds,'decoded_bytes':args.decoded_bytes,'container_bytes':args.container_bytes,'members':args.member_limit,'depth':args.depth_limit}}
    save(output/'invocation.json',{'script':pin(Path(__file__).resolve()),'argv':{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()}});save(output/'started.json',state)
    try:run(args,output,state)
    except BaseException as problem:state.update({'status':'failed_classification_preserved','primary_error_type':type(problem).__name__});raise
    finally:state['elapsed_seconds']=time.monotonic()-start;save(output/'closed.json',state)
    print(json.dumps({'status':state['status'],'upload_qualified':state['upload_qualified'],'unique_files':state['unique_files_classified'],'forbidden_chunks':state['forbidden_unique_chunks']}))


if __name__=='__main__':main()
