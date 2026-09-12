"""Worker-side fixed request and signed result transport. No execution authority."""
from pathlib import Path
import argparse,base64,hashlib,json,os,stat,subprocess,tempfile

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def read(p):
    assert p.is_absolute() and p.resolve()==p,'noncanonical handoff path'
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        s=os.fstat(fd);assert stat.S_ISREG(s.st_mode)and s.st_size<=1048576,'invalid handoff file'
        return os.read(fd,1048577)
    finally:os.close(fd)
def load(p):return json.loads(read(p))
def write(p,data):
    assert p.parent.resolve()==p.parent
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
    try:
        with os.fdopen(fd,'wb',closefd=False)as f:f.write(data);f.flush();os.fsync(fd)
    finally:os.close(fd)
    fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def offer(queue,expected):
    raw=read(queue/'offer.json');assert sha(raw)==expected,'untrusted offer'
    x=json.loads(raw);assert sha(read(queue/'public.pem'))==x['public_key_sha256'],'public key changed'
    assert set(x['request'])=={'schema','grant_sha256','grant_id','request_id','unit','arm','amendment_sha256'}
    assert x['request']['schema']=='operator-development-request/v1'
    return x
def submit(queue,expected):
    x=offer(queue,expected);payload=canonical(x['request']);p=queue/'request.json'
    if p.exists():assert read(p)==payload,'different request already submitted'
    else:write(p,payload)
    return {'status':'waiting_for_operator_execution','request_sha256':sha(payload),'provider_invoked_by_client':False}
def result(queue,expected):
    x=offer(queue,expected);r=load(queue/'response.json');body=r['receipt'];request=x['request']
    assert r['public_key_sha256']==x['public_key_sha256'],'response signing key changed'
    with tempfile.TemporaryDirectory(prefix='development-receipt-')as d:
        p=Path(d);write(p/'body',canonical(body));write(p/'sig',base64.b64decode(r['signature'],validate=True))
        subprocess.run(['openssl','pkeyutl','-verify','-pubin','-rawin','-inkey',str(queue/'public.pem'),'-in',str(p/'body'),'-sigfile',str(p/'sig')],check=True,capture_output=True)
    assert body['schema']=='operator-development-receipt/v1'
    assert all(body[k]==request[k]for k in ('grant_id','grant_sha256','unit','arm','amendment_sha256')),'response belongs to another grant'
    assert body['request_sha256']==sha(canonical(request))and body['profile']==x['profile']and body['source_sha256']==x['source_sha256'],'response scope differs'
    assert body['final_scientific_run']is False and body['historical_population_admitted']is False
    return {'signature_and_scope_verified':True,'receipt':body}
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['submit','result']);p.add_argument('--queue',type=Path,required=True);p.add_argument('--offer-sha256',required=True);a=p.parse_args()
    print(json.dumps((submit if a.action=='submit'else result)(a.queue.resolve(),a.offer_sha256),sort_keys=True))
if __name__=='__main__':main()
