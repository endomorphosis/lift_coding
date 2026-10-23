"""Root file-only readback of prepared language inputs; no native/project calls."""
import argparse,datetime,hashlib,json
from pathlib import Path

def pin(path):
    path=Path(path).resolve(strict=True)
    digest=hashlib.sha256();size=0
    with path.open('rb') as stream:
        while part:=stream.read(1024*1024):size+=len(part);digest.update(part)
    return {'path':str(path),'bytes':size,'sha256':digest.hexdigest()}

def main():
    if not __debug__: raise RuntimeError("unoptimized root input review required")
    ap=argparse.ArgumentParser();ap.add_argument('--driver',type=Path,required=True)
    ap.add_argument('--driver-sha256',required=True);ap.add_argument('--request-sha256',required=True)
    ap.add_argument('--specification-sha256',required=True);ap.add_argument('--mode',required=True)
    ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    driver=pin(a.driver);assert driver['sha256']==a.driver_sha256
    raw=a.driver.read_bytes()
    assert len(raw)==driver['bytes'] and hashlib.sha256(raw).hexdigest()==driver['sha256']
    ns={'__name__':'held_root_file_only_language_input_review','__file__':driver['path']}
    exec(compile(raw,driver['path'],'exec'),ns)
    ns['MODE']=a.mode;ns['validate_mode'](a.mode);f=ns['files']()
    root=Path(driver['path']).parent
    request_pin=pin(root/'preparation'/(a.mode+'-request.json'))
    spec_pin=pin(root/'preparation'/(a.mode+'-check-specification.json'))
    assert request_pin['sha256']==a.request_sha256 and spec_pin['sha256']==a.specification_sha256
    request=f['document'](request_pin);ns['validate_request'](f,request)
    spec=ns['validate_specification'](f,spec_pin)
    profile=f['document'](spec['environment_manifest'])
    # All declared transitive executable/library bodies, including large ones,
    # are streamed, so the review is about bytes rather than manifest fields.
    total=0
    for row in profile['files']:
        assert pin(row['path'])==row;total+=row['bytes']
    before=ns['checkout_guards'](f,request);f['verify_held']()
    assert ns['checkout_guards'](f,request)==before and pin(a.driver)==driver
    receipt={'schema':'ranker-container-language-root-input-review@1',
      'status':'passed_file_only','findings':[],'mode':a.mode,'driver':driver,
      'request':request_pin,'specification':spec_pin,'environment_manifest':spec['environment_manifest'],
      'environment_bodies_read':len(profile['files']),'environment_bytes_read':total,
      'strict_guards_verified':len(request['strict_old_inputs']),'protected_live_sources_verified':4,
      'original_checkout_guards':before,'all_input_bodies_equal_before_after':True,
      'native_calls':0,'target_imports':0,'test_calls':0,'model_calls':0,'metadata_calls':0,
      'authority_scope':'file-only input review, no proof qualification',
      'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),**f['AUTHORITY']}
    result=f['write'](a.output,receipt)
    print(json.dumps({'status':receipt['status'],'receipt':result,'native_calls':0,
      'environment_bodies_read':len(profile['files'])}))
if __name__=='__main__':main()
