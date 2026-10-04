"""Capture changed source in a private index; original checkout stays intact."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time

ROOT=Path('/home/barberb/lift_coding')
OUT=Path(__file__).resolve().parent
MAX_SOURCE=8*1024*1024
BULK_SUFFIXES={'.gz','.zip','.tgz','.xz','.zst','.tar','.sqlite','.db','.duckdb','.parquet','.arrow',
    '.npy','.npz','.pt','.pth','.safetensors','.ckpt','.bin','.blob','.raw','.pack','.idx','.log','.jsonl',
    '.nc','.so','.a','.o','.pyc','.olean','.ai','.mp4','.wav','.mp3','.onnx','.gguf'}
SECRET_RE=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|hf_[A-Za-z0-9]{30,}|xai-[A-Za-z0-9]{35,}|sk-ant-api[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')


def save(name,value):
    with (OUT/name).open('x') as stream:
        json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n')
def binding(path):
    raw=path.read_bytes();return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def run(args,env=None,accepted=(0,),timeout=300):
    started=time.monotonic()
    process=subprocess.run(['git','-c','gc.auto=0','-c','maintenance.auto=false',*args],cwd=ROOT,
        capture_output=True,env={**os.environ,'GIT_TERMINAL_PROMPT':'0',**(env or {})},timeout=timeout)
    with (OUT/'operations.jsonl').open('ab') as stream:
        stream.write(json.dumps({'args':args,'returncode':process.returncode,'elapsed_seconds':time.monotonic()-started,
            'stdout_bytes':len(process.stdout),'stderr_bytes':len(process.stderr),
            'stdout_sha256':hashlib.sha256(process.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(process.stderr).hexdigest()}).encode()+b'\n')
    assert process.returncode in accepted,(args[:2],process.returncode)
    return process.stdout
def signature(info):return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def main():
    started=time.monotonic();inventory=json.loads((OUT/'inventory.json').read_bytes())
    head=run(['rev-parse','HEAD']).decode().strip();assert head==inventory['head']
    index_path=Path(run(['rev-parse','--git-path','index']).decode().strip())
    if not index_path.is_absolute():index_path=ROOT/index_path
    original_index=binding(index_path)
    selected=[];bulk=[];local_only=[];secrets=[];unstable=[]
    for row in inventory['paths']:
        name=row['path'];parts=Path(name).parts;path=ROOT/name;basename=path.name.lower()
        if row['type']=='directory':continue
        if '.git' in parts or 'node_modules' in parts or '__pycache__' in parts:
            local_only.append({'path':name,'reason':'Git administration or dependency cache'});continue
        if name.startswith('maintenance/terminal-ir-publication-20261004-01/'):
            local_only.append({'path':name,'reason':'Publication bookkeeping is committed separately after closure'});continue
        if basename in {'token','stored_tokens','credentials','credentials.json','secrets.json','id_rsa','id_ed25519'} or (basename.startswith('.env') and not any(v in basename for v in ('example','sample','template'))) or path.suffix.lower() in {'.pem','.key','.p12','.pfx'}:
            local_only.append({'path':name,'reason':'Credential/key filename; original retained locally'});continue
        if row['type']=='file' and (row['bytes']>MAX_SOURCE or path.suffix.lower() in BULK_SUFFIXES):
            bulk.append(row);continue
        if row['type']=='other':local_only.append({'path':name,'reason':'Nonregular node metadata belongs to artifact index'});continue
        if row['type']=='deleted':selected.append({'path':name,'type':'deleted'});continue
        before=path.lstat()
        if row['type']=='link':
            raw=os.fsencode(os.readlink(path));mode='120000'
        else:
            fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(fd,'rb') as stream:
                info=os.fstat(stream.fileno());assert stat.S_ISREG(info.st_mode)
                raw=stream.read(MAX_SOURCE+1);after_fd=os.fstat(stream.fileno())
            if len(raw)>MAX_SOURCE or signature(info)!=signature(after_fd) or signature(before)!=signature(info):
                unstable.append({'path':name,'reason':'Changed during read; no source byte claim'});continue
            mode='100755' if before.st_mode&0o111 else '100644'
            if SECRET_RE.search(raw):
                secrets.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'reason':'Credential-shaped material; no matched value retained'});continue
        if signature(before)!=signature(path.lstat()):
            unstable.append({'path':name,'reason':'Path changed during read'});continue
        selected.append({'path':name,'type':row['type'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mode':mode})
        if len(selected)%20000==0:print(json.dumps({'selected':len(selected),'bulk':len(bulk),'flagged':len(secrets)}),flush=True)
    save('selection.json',{'head':head,'original_index':original_index,'selected':selected,'huggingface_bulk':bulk,
        'local_only':local_only,'credential_flags':secrets,'unstable_reads':unstable,
        'scope':'Per-file stable changed/untracked source observation; no globally atomic checkout claim. Large/generated data are separately archived to Hugging Face.'})
    assert not unstable,'Source changed during capture; retain attempt and resolve before staging'
    index=OUT/'private-index';assert not index.exists()
    env={'GIT_INDEX_FILE':str(index)}
    run(['read-tree',head],env=env)
    pathspec=OUT/'selected-paths.nul'
    with pathspec.open('xb') as stream:
        stream.write(b''.join(b':(literal)'+os.fsencode(row['path'])+b'\0' for row in selected))
    run(['add','-A','--pathspec-from-file='+str(pathspec),'--pathspec-file-nul'],env=env,timeout=600)
    assert binding(index_path)==original_index and run(['rev-parse','HEAD']).decode().strip()==head
    tree=run(['write-tree'],env=env).decode().strip()
    manifest=binding(OUT/'selection.json')
    save('snapshot-tree.json',{'tree':tree,'parent_HEAD':head,'selection':manifest,'original_index_unchanged':True,
        'selected_files':len(selected),'selected_bytes':sum(row.get('bytes',0) for row in selected),
        'bulk_files_for_HuggingFace':len(bulk),'bulk_bytes':sum(row['bytes'] for row in bulk),
        'credential_flags':len(secrets),'elapsed_seconds':time.monotonic()-started,'published':False})
    print(json.dumps({'tree':tree,'selected_files':len(selected),'bulk_files':len(bulk),'credential_flags':len(secrets),'elapsed_seconds':time.monotonic()-started}))


if __name__=='__main__':main()
