"""Project verified file commitments; do not infer a live imported module forest."""
import json
import os
from collections import Counter
from pathlib import Path
from audit_io import ROOT, OUT, Reader, write_json, write_jsonl

def main():
    r=Reader('integration')
    root=ROOT/'artifacts/supervisor-portable-codex-worker-fix-20261014-01/runtime-campaign'
    manifest=r.json(root/'runtime/manifest.json','original_runtime_manifest')
    freeze=r.json(root/'released-source-freeze.json','retained_source_freeze')
    check=json.loads((OUT/'audit/runtime_member_verification.json').read_text())
    assert check['all_declared_file_bytes_verified']
    files={x['path']:x for x in manifest['files']}
    bindings=[]
    for group in ['overlay_sources','root_released_overlay_sha256','selected_and_deadline_sources']:
        for path,pin in freeze[group].items():
            expected=pin['sha256'] if isinstance(pin,dict) else pin
            found=files.get(path)
            bindings.append({'group':group,'path':path,'expected_sha256':expected,
                             'archive_member_sha256':found['sha256'] if found else None,
                             'matches':found is not None and expected==found['sha256']})
    write_jsonl('private/runtime_source_files.jsonl',[
        {'path':x['path'],'bytes':x['bytes'],'sha256':x['sha256'],'declared_mode':x['mode'],
         'regular_member_bytes_verified':True,'runtime_import_observed':None} for x in manifest['files']])
    summary={'schema':'paper-runtime-source-forest-byte-projection@1',
             'archive_sha256':manifest['archive_sha256'],'manifest_sha256':r.seen[str(root/'runtime/manifest.json')]['sha256'],
             'released_source_freeze_sha256':r.seen[str(root/'released-source-freeze.json')]['sha256'],
             'file_count':len(files),'uncompressed_regular_file_bytes':sum(x['bytes'] for x in files.values()),
             'root_counts':dict(Counter(p.split('/')[0] for p in files)),
             'source_file_index':'private/runtime_source_files.jsonl','selected_pin_joins':bindings,
             'all_selected_pin_joins_match':all(x['matches'] for x in bindings),
             'runtime_python_version':manifest['runtime_python_version'],'codex_version':manifest['codex_version'],
             'native_codex_target':manifest['codex_native_runtime']['target'],
             'native_codex_manifest_sha256':manifest['codex_native_runtime']['manifest_sha256'],
             'embedding_model_snapshot_revision':manifest['model_snapshot_revision'],
             'security_checkpoint_manifest_field':manifest['security_checkpoint'],
             'security_initializer_manifest_field':manifest['security_initializer'],
             'canonical_cve_training_manifest_field':manifest['canonical_cve_training'],
             'task_inputs_in_archive_reported':manifest['task_inputs_in_archive'],
             'credentials_in_archive_reported':manifest['credentials_in_archive'],
             'credential_content_scan_performed':False,
             'complete_import_closure_claimed_by_freeze':freeze['complete_import_closure_claimed'],
             'actual_live_loaded_module_origins':None,'executed_git_forest':None,
             'limitations':['Archive and manifest bytes self-consistently verified; no execution or import replay.',
                            'Manifest checkpoint null fields do not prove absence of separately mounted runtime assets.',
                            'Current source heads are not substituted for archived files or historical workers.',
                            'No archive link is followed and no files extracted; header modes/links are not execution truth.',
                            'Archive credential/task flags are reported metadata, not a fresh sensitive-content scan.']}
    write_json('runtime_source_forest.json',summary)
    write_json('workstreams/integration_gap_updates.json',{'updates':[
        {'prior_gap':2,'status':'partially_closed','resolved':['Runtime archive exact SHA256 independently verified','All27911declared regular member size/SHA256 values verified','Runtime manifest and selected source freeze recovered and joined'],
         'remaining':['Actual live worker import origins and execution trace closure','Executed Git source forest where not retained'],
         'evidence':['audit/large_asset_verification.json','audit/runtime_member_verification.json','runtime_source_forest.json']},
        {'prior_gap':25,'status':'closed','resolved':['Retained Intent development candidate exact bytes now hash-match original descriptor'],
         'does_not_resolve':['semantic qualification','384Dhead identity','Terminal-Bench inference consumption'],
         'evidence':['audit/large_asset_verification.json']}
    ]})
    print(json.dumps({'files':len(files),'selected_pins':len(bindings),'all_selected_pins_match':summary['all_selected_pin_joins_match']}))

if __name__=='__main__':
    os.umask(0o077);main()
