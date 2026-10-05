"""Tiny real archive controls; synthetic bytes, no native/model/prover jobs."""
import ast,hashlib,json,os
from pathlib import Path
import subprocess,sys,time,io,tarfile,lzma,gzip,zipfile,re

ROOT=Path('/home/barberb/lift_coding/maintenance/terminal-ir-publication-20261004-01/huggingface')
BUILDER=ROOT/'build_evidence_archive_02.py'
DECODER=ROOT/'classify_and_prepare_public_archive_07.py'

def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):
 with p.open('xb') as f:f.write((json.dumps(v,sort_keys=True,indent=2)+'\n').encode())
def run_child(argv,root,label):
 start=time.monotonic()
 with (root/(label+'.stdout.log')).open('xb') as out,(root/(label+'.stderr.log')).open('xb') as err:
  child=subprocess.run(argv,stdout=out,stderr=err,timeout=90,check=False)
 result={'argv':argv,'returncode':child.returncode,'elapsed_seconds':time.monotonic()-start};save(root/(label+'.closed.json'),result)
 if child.returncode:raise AssertionError(label+' child failure')
 return result

def main():
 root=ROOT/'decoder-controls-05';root.mkdir(exist_ok=False);start=time.monotonic();state={'status':'running','scope':'SYNTHETIC_ARCHIVE_CONTROL_ONLY','model_jobs':0,'prover_jobs':0,'native_SQL_jobs':0,'HF_mutations':0}
 save(root/'started.json',state)
 try:
  sources=root/'sources';sources.mkdir();(sources/'clean.txt').write_bytes('alive Ω\n'.encode())
  # These deliberately generated pattern strings are inert scanner controls,
  # not valid credentials, cryptographic key material or public fixture proof.
  gh=b'ghp_'+b'A'*36;hf=b'hf_'+b'B'*36
  (sources/'raw-format-control.txt').write_bytes(gh+b'\n')
  pem='-----BEGIN PRIVATE KEY-----\nQUFBQQ==\n-----END PRIVATE KEY-----'
  (sources/'escaped-format-control.json').write_text(json.dumps({'synthetic_key_shape':pem}))
  with zipfile.ZipFile(sources/'clean.zip','x') as z:z.writestr('hello.txt','public control bytes')
  tar=io.BytesIO()
  with tarfile.open(fileobj=tar,mode='w') as z:
   info=tarfile.TarInfo('inert-token-shape.txt');info.size=len(hf);z.addfile(info,io.BytesIO(hf))
  (sources/'nested-format-control.tar.gz').write_bytes(gzip.compress(tar.getvalue()))
  clean_tar=io.BytesIO()
  with tarfile.open(fileobj=clean_tar,mode='w') as z:
   body=b'contiguous split control';info=tarfile.TarInfo('split.txt');info.size=len(body);z.addfile(info,io.BytesIO(body))
  split=lzma.compress(clean_tar.getvalue());cut=len(split)//2
  (sources/'clean.tar.xz.part-001').write_bytes(split[:cut]);(sources/'clean.tar.xz.part-002').write_bytes(split[cut:])
  os.symlink('clean.txt',sources/'clean-link');os.mkfifo(sources/'metadata-only-fifo')
  # Additional observed-hit/provenance ordering and three-context controls.
  bad_container=b'Rar!'+gh+b'\n'
  bad_fixture=b'7z\xbc\xaf\x27\x1c'+pem.encode()
  (sources/'declared-container-provenance.rar').write_bytes(bad_container)
  (sources/'declared-fixture-with-parse-refusal.7z').write_bytes(bad_fixture)
  for name,body in [('a-unsafe',gh),('m-safe',b'benign one'),('z-safe',b'benign two')]:
   packed=io.BytesIO()
   with tarfile.open(fileobj=packed,mode='w') as archive:
    info=tarfile.TarInfo('body.txt');info.size=len(body);archive.addfile(info,io.BytesIO(body))
   encoded=gzip.compress(packed.getvalue(),mtime=0)
   (sources/(name+'.tar.gz.part-001')).write_bytes(encoded[:10])
   (sources/(name+'.tar.gz.part-002')).write_bytes(encoded[10:])
  missing=clean_tar.getvalue();cut=(len(missing)-1024)//2
  (sources/'missing-terminal.tar.part-001').write_bytes(missing[:cut])
  (sources/'missing-terminal.tar.part-002').write_bytes(missing[cut:-1024])
  missing_tail={'path':'missing-terminal.tar.part-003','bytes':1024,'sha256':hashlib.sha256(missing[-1024:]).hexdigest()}
  (sources/'approved-fixture-in-unsafe.bin.part-001').write_bytes(pem.encode())
  (sources/'approved-fixture-in-unsafe.bin.part-002').write_bytes(gh)
  restored_pem='-----BEGIN PRIVATE KEY-----\nQkJCQg==\n-----END PRIVATE KEY-----'
  (sources/'approved-inert-fixture.pem').write_bytes(restored_pem.encode())
  part_records=[]
  for path in sources.iterdir():
   if re.search(r'\.part-\d+$',path.name):
    b=path.read_bytes();part_records.append({'path':path.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
  part_records.append(missing_tail)
  save(root/'split-preservation.json',{'schema':'synthetic-split-preservation@1','files':part_records,'scope':'authored controls; intentionally absent terminal part is not genuine preserved source'})
  groups=[]
  for prefix in sorted({re.sub(r'\d+$','',row['path']) for row in part_records}):
   rows=sorted([row for row in part_records if row['path'].startswith(prefix)],key=lambda row:int(re.search(r'\d+$',row['path']).group()))
   groups.append({'namespace':'synthetic_controls','path_prefix':prefix,'ordered_parts':rows,'source_manifest':pin(root/'split-preservation.json'),'expected_source_schema':'synthetic-split-preservation@1','source_manifest_field':'files'})

  scopes={'schema':'terminal-ir-publication-scopes@1','destination':{'repo_id':'SYNTHETIC_CONTROL_NO_REMOTE','repo_type':'dataset'},'recursive_roots':[{'namespace':'synthetic_controls','root':str(sources)}],'selection_manifests':[],'strict_pinned_inputs':[pin(sources/'clean.txt')],'selected_sealed_and_external_pins_complete':True}
  save(root/'scopes.json',scopes);save(root/'approvals.json',{'schema':'terminal-ir-publication-classification-approvals@1','public_fixture_files':[{'file_sha256':hashlib.sha256(restored_pem.encode()).hexdigest(),'approved_match_sha256':[hashlib.sha256(restored_pem.encode()).hexdigest()],'classification':'published_public_fixture','provenance_ref':'SYNTHETIC_DECLARATION_NOT_ACTUAL_PUBLISHED_PROVENANCE'},{'file_sha256':hashlib.sha256(pem.encode()).hexdigest(),'approved_match_sha256':[hashlib.sha256(pem.encode()).hexdigest()],'classification':'published_public_fixture','provenance_ref':'SYNTHETIC_DECLARATION_NOT_ACTUAL_PUBLISHED_PROVENANCE'},{'file_sha256':hashlib.sha256(bad_fixture).hexdigest(),'approved_match_sha256':[hashlib.sha256(pem.encode()).hexdigest()],'classification':'published_public_fixture','provenance_ref':'SYNTHETIC_DECLARATION_NOT_ACTUAL_PUBLISHED_PROVENANCE'}],'public_container_provenance':[{'file_sha256':hashlib.sha256(bad_container).hexdigest(),'provenance_ref':'SYNTHETIC_DECLARATION_NOT_ACTUAL_PUBLISHED_PROVENANCE'}],'split_groups':groups,'scope':'synthetic controls only; no authentic public-provenance declarations'})
  save(root/'source-pins.json',{'builder':pin(BUILDER),'decoder':pin(DECODER),'control_driver':pin(Path(__file__))})
  run_child([sys.executable,str(BUILDER),'--scopes',str(root/'scopes.json'),'--output',str(root/'build'),'--expected-script-sha256',pin(BUILDER)['sha256'],'--expected-scopes-sha256',pin(root/'scopes.json')['sha256'],'--wall-seconds','90'],root,'builder')
  manifest=root/'build/public/archive-manifest.json'
  run_child([sys.executable,str(DECODER),'--build',str(root/'build'),'--helper',str(BUILDER),'--approvals',str(root/'approvals.json'),'--output',str(root/'derivative'),'--expected-archive-manifest-sha256',pin(manifest)['sha256'],'--expected-helper-sha256',pin(BUILDER)['sha256'],'--expected-approvals-sha256',pin(root/'approvals.json')['sha256'],'--wall-seconds','90'],root,'decoder')
  report=json.loads((root/'derivative/public/archive-manifest.json').read_bytes())
  assert report['unresolved_unique_files']>=2,report['classification_counts']
  assert report['upload_qualified'] is False
  assert report['forbidden_unique_chunks']>=3,report['classification_counts']
  assert report['rewritten_original_shards']==1
  assert any(item['status']=='scanned_split_archive_no_named_candidates' for item in report['group_results'])
  states=[]
  for item in report['path_manifest_shards']:
   raw=subprocess.run(['/usr/bin/zstd','-d','--quiet','--stdout',item['path']],capture_output=True,check=True).stdout
   states.extend(json.loads(line) for line in raw.splitlines())
  bypath={r['path']:r for r in states}
  for name in ['raw-format-control.txt','escaped-format-control.json','nested-format-control.tar.gz']:
   assert bypath[name]['public_original_bytes_included'] is False and 'chunks' not in bypath[name]
  assert bypath['metadata-only-fifo']['status']=='captured_special_metadata_only'
  assert bypath['clean-link']['target']=='clean.txt'
  assert bypath['clean.txt']['public_original_bytes_included'] is True
  assert bypath['approved-inert-fixture.pem']['public_original_bytes_included'] is True
  assert bypath['approved-inert-fixture.pem']['public_classification']['status']=='approved_exact_public_fixture'
  restored=False
  assert bypath['declared-container-provenance.rar']['public_original_bytes_included'] is False
  assert bypath['declared-container-provenance.rar']['public_classification']['candidate_hits']
  refused= bypath['declared-fixture-with-parse-refusal.7z']['public_classification']
  assert refused['status'].startswith('unresolved') and refused['decoded_scan_complete'] is False
  for name in ['a-unsafe','m-safe','z-safe']:
   assert bypath[name+'.tar.gz.part-001']['public_original_bytes_included'] is False
  assert bypath['z-safe.tar.gz.part-001']['public_classification']['split_group_denial']
  assert bypath['missing-terminal.tar.part-001']['public_classification']['status']=='unresolved_split_archive_manifest_population'
  assert bypath['approved-fixture-in-unsafe.bin.part-001']['public_original_bytes_included'] is False
  assert bypath['approved-fixture-in-unsafe.bin.part-001']['public_classification']['split_group_denial']=='quarantined_decoded_split_archive'

  # A denied chunk must be physically absent, not only absent from path JSON.
  for item in report['data_shards']:
   raw=subprocess.run(['/usr/bin/zstd','-d','--quiet','--stdout',item['source_path']],capture_output=True,check=True).stdout
   with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:
    for member in archive:
     encoded=archive.extractfile(member).read()
     body=subprocess.run(['/usr/bin/zstd','-d','--quiet','--stdout'],input=encoded,capture_output=True,check=True).stdout
     assert gh not in body and hf not in body
     if b'BEGIN PRIVATE KEY' in body:assert body==restored_pem.encode();restored=True
  assert restored
  state.update({'status':'PASS','checks':['real full-file raw credential exclusion','escaped JSON PEM detection','gzip/tar member detection','complete multipart group supersedes individual parse refusal','physical affected-shard rewrite','safe-file preservation','symlink text preservation','FIFO metadata only','observed token beats declared container provenance','fixture approval does not erase parse refusal','three shared-part contexts retain first denial','expected terminal part absence refuses','approved standalone fixture cannot override unsafe complete group','exact standalone approved fixture restored into new chunk/index/shard'],'classification_report':pin(root/'derivative/public/archive-manifest.json'),'originals_modified':False,'synthetic_credentials_are_valid':False,'native_qualification':False})
 except BaseException as e:state.update({'status':'FAIL','error_type':type(e).__name__});raise
 finally:state['elapsed_seconds']=time.monotonic()-start;save(root/'closed.json',state)
 print(json.dumps({'status':state['status'],'elapsed_seconds':state['elapsed_seconds']}))

if __name__=='__main__':main()
