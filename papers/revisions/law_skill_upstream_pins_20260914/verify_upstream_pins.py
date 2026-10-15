#!/usr/bin/env python3
"""Read-only verification of historical candidate source pins, not scientific results."""
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'law_study_preparation_20260914'
def check(binding):
    path=Path(binding['path']);raw=path.read_bytes()
    assert len(raw)==binding['bytes'] and hashlib.sha256(raw).hexdigest()==binding['sha256'],str(path)
    return raw
def main():
    report=json.loads((HERE/'upstream_pin_proposal.json').read_text())
    initial=json.loads(check(report['original_skill_manifest']))
    assert len(report['families'])==len(initial['families'])==12
    assert [f['skill_id'] for f in report['families']]==[f['skill_id'] for f in initial['families']]
    assert len({f['resolved_repository'] for f in report['families']})==12
    files=0
    for family in report['families']:
        for binding in family['pinned_generated_procedure_binding'].values():check(binding)
        for binding in family['source_bindings'].values():check(binding)
        commit=family['candidate_upstream_commit']
        listing=json.loads(check(family['source_bindings']['historical-commit-list.body']))
        assert len(listing)==1 and listing[0]['sha']==commit['sha']
        assert listing[0]['commit']['tree']['sha']==commit['tree_sha']
        assert datetime.datetime.fromisoformat(commit['committer_date'].replace('Z','+00:00'))<=datetime.datetime.fromisoformat(family['recorded_original_fetch_at'].replace('Z','+00:00'))
        tree=json.loads(check(family['source_bindings']['root-tree.body']))
        assert tree['sha']==commit['tree_sha'] and not tree.get('truncated')
        blobs={f['path']:f['sha'] for f in tree['tree'] if f['type']=='blob'}
        assert {f['kind'] for f in family['primary_files']}=={'readme','license'}
        for source in family['primary_files']:
            raw=check(source['response_binding'])
            assert source['revision']==commit['sha']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blobs[source['path']]==source['git_blob_id']
            files+=1
        assert not family['original_source_capture_proven'] and not family['scientific_admission']
    for edge in report['declared_lineage_edges']:check(edge['metadata_binding'])
    assert len(report['declared_lineage_edges'])==3
    assert not report['known_lineage_node_overlap_with_old_study_or_corrected_CVE']
    check(report['historical_identity_source']);check(report['corrected_cve_identity_source'])
    inventory=json.loads((PRIOR/'source_preparation_inventory.json').read_text())
    for name,binding in inventory['files'].items():check({'path':str(PRIOR/name),**binding})
    assert not report['scientific_admission'] and report['model_calls']==report['native_mutations']==0
    assert not report['upstream_code_executed'] and not report['full_historical_fork_clone_nearest_neighbor_closure']
    print(json.dumps({'status':'PASS_CANDIDATE_SOURCE_PIN_BINDINGS_ONLY','families':12,
        'exact_primary_files':files,'declared_lineage_edges':3,'frozen_files_preserved':len(inventory['files']),
        'scientific_admission_or_original_capture_proven':False,'model_calls':0},indent=2))
if __name__=='__main__':main()
