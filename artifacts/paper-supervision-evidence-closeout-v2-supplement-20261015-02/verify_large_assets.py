"""Hash three named retained assets; inspect manifest schema without extraction.

No weights load, inference, archive execution/extraction, package import or network.
The output directory is this new supplement. Existing outputs are never replaced.
"""
import hashlib
import json
import os
import time
from pathlib import Path
from audit_io import ROOT, OUT, AUTH, Reader, write_json

ASSETS = [
    ('T1 runtime archive', ROOT/'artifacts/supervisor-portable-codex-worker-fix-20261014-01/runtime-campaign/runtime/runtime.tar.gz',
     'f89c7ace1f4387bcb020f223758609dac607c8e6258c208189bbd8dec2f652f8'),
    ('Intent development backend', ROOT/'artifacts/intent-ir-roundtrip-20260929/training-03/model/candidate.json',
     '699bf438f5340b23eb86fb78d77991a42fa91d8b84cbc8a0ae3e42799382d86d'),
]

def main():
    results = []
    consumed = 0
    for name, p, expected in ASSETS:
        assert p.is_relative_to(ROOT) and p.resolve() == p and p.is_file()
        before = p.stat()
        assert before.st_size <= AUTH['limits']['stream_file_bytes']
        assert consumed + before.st_size <= AUTH['limits']['total_stream_bytes']
        digest = hashlib.sha256()
        count = 0
        start = time.monotonic()
        with p.open('rb') as f:
            while block := f.read(1024*1024):
                count += len(block)
                consumed += len(block)
                if count > AUTH['limits']['stream_file_bytes'] or consumed > AUTH['limits']['total_stream_bytes']:
                    raise ValueError('Streaming read bound exceeded')
                digest.update(block)
        after = p.stat()
        stable = (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) == (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
        results.append({'asset':name,'path':str(p),'bytes':count,'sha256':digest.hexdigest(),'expected_sha256':expected,
                        'matches_reported_identity':digest.hexdigest()==expected,'stable_during_read':stable,
                        'inspection_seconds':time.monotonic()-start,'signature_verification':'not_performed',
                        'scope':'byte identity only; no source semantics, model qualification or runtime consumption inferred'})
    r = Reader('integration')
    p = ROOT/'artifacts/supervisor-portable-codex-worker-fix-20261014-01/runtime-campaign/runtime/manifest.json'
    manifest = r.json(p,'original_runtime_manifest')
    # Save top-level schema only. A later bounded projection selects declared pins.
    structure = {k:{'type':type(v).__name__,'count':len(v) if isinstance(v,(dict,list)) else None}
                 for k,v in manifest.items()}
    result = {'schema':'paper-supplement-large-asset-byte-check@1','results':results,'stream_bytes':consumed,
              'all_matched':all(x['matches_reported_identity'] and x['stable_during_read'] for x in results),
              'manifest_path':str(p),'manifest_sha256':r.seen[str(p)]['sha256'],
              'manifest_structure':structure,'archives_extracted':False,'models_loaded':False,'behavioral_execution':False}
    write_json('audit/large_asset_verification.json',result)
    print(json.dumps({'all_matched':result['all_matched'],'stream_bytes':consumed,
                      'assets':[{'asset':x['asset'],'bytes':x['bytes'],'matches':x['matches_reported_identity']} for x in results],
                      'manifest_structure':structure}))

if __name__=='__main__':
    os.umask(0o077)
    main()
