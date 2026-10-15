#!/usr/bin/env python3
"""Read-only source/selection binding checks, not a scientific execution verifier."""
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'law_study_preparation_20260914'
def sha(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()
def checked(binding):
    path=Path(binding['path'])
    assert path.stat().st_size==binding['bytes'] and sha(path)==binding['sha256'],str(path)
def main():
    decisions=json.loads((HERE/'screen_completion_decisions.json').read_text())
    proposal=json.loads((HERE/'paired_family_amendment.json').read_text())
    candidate=json.loads((HERE/'proposed_cve_candidates_v3.json').read_text())
    consequences=json.loads((HERE/'deterministic_cohort_consequences.json').read_text())
    inventory=json.loads((PRIOR/'source_preparation_inventory.json').read_text())
    for name,binding in inventory['files'].items():
        checked({'path':str(PRIOR/name),**binding})
    checked(decisions['original_screen']);checked(decisions['unchanged_eligibility_rule'])
    assert [d['physical_row'] for d in decisions['decisions']]==[130,150,151,152,153]
    for decision in decisions['decisions']:
        src=decision['source'];directory=HERE/f'row-{decision["physical_row"]:04d}'
        for binding in src['bindings'].values():checked(binding)
        commit=json.loads((directory/'commit.body').read_text())
        assert commit['sha']==src['fix_commit'] and [p['sha'] for p in commit['parents']]==src['parent_commits']
        assert len(src['parent_commits'])==1
        files={f['filename']:f for f in commit['files']}
        for full in src['full_file_bindings']:
            checked(full['response_binding'])
            if full['version']=='fixed':
                raw=Path(full['response_binding']['path']).read_bytes()
                git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                assert git_blob==files[full['path']]['sha']
        for missing in src['missing_parent_files']:
            assert missing['version']=='parent' and files[missing['path']]['status']=='added'
        advisory=json.loads((directory/'advisory.body').read_text())
        assert any(a['cve_id']==src['cve_id'] for a in advisory)
        assert decision['source_grounded_bounded_task_possible'] and not decision['scientific_admission']
    source=Path(decisions['decisions'][0]['source']['artifact_path'])
    assert sha(source)==decisions['decisions'][0]['source']['artifact_sha256']
    families=candidate['families'];rows=[f['source']['physical_row_number'] for f in families]
    assert rows==[64,72,88,90,91,124,130,143,150,171,194,201]
    assert len({f['source']['repository'] for f in families})==12
    assert consequences['proposed_rows']==rows and consequences['displaced']==[242,261]
    previous=json.loads((PRIOR/'legal_cve_proposal_v2/cve_candidates.json').read_text())
    prior_by_row={f['source']['physical_row_number']:f for f in previous['families']}
    assert all(f==prior_by_row[f['source']['physical_row_number']] for f in families if f['source']['physical_row_number'] not in [130,150])
    assert len(proposal['additions'])==2 and all(len(f['cases'])==2 for f in proposal['additions'])
    assert sum(len(f['cases']) for f in families)==24
    assert all(not f['scientific_admission'] and all(c['scientific_split'] is None and c['source_output_generation']=='not_run' for c in f['cases']) for f in families)
    assert not candidate['final_cohort_released'] and not consequences['scientific_splits_assigned']
    assert decisions['models_called']==decisions['scientific_cells_executed']==0
    assert consequences['whole_study_cell_count']==900
    updated=json.loads((HERE/'updated_cve_screening_audit.json').read_text())
    assert len(updated['rows'])==262
    assert not any(r['status']=='ADDITIONAL_ROW_REQUIRING_SCREEN_COMPLETION' for r in updated['rows'])
    selected=[r['physical_row'] for r in updated['rows'] if r['status']=='SOURCE_GROUNDED_DRAFT_CANDIDATE']
    assert selected==rows
    assert updated['counts']==dict(Counter(r['status'] for r in updated['rows']))
    print(json.dumps({'status':'PASS_SOURCE_BINDINGS_AND_DRAFT_SELECTION_ONLY','five_screens_completed':True,
                      'all_fixed_full_files_match_exact_commit_git_blob_ids':True,
                      'missing_parent_files_are_proven_newly_added':True,'original_artifact_sha256_passed':True,
                      'frozen_preparation_files_preserved':len(inventory['files']),
                      'selected_rows':rows,'cve_family_count':12,'cve_case_count':24,
                      'scientific_execution_or_admission_verified':False,'model_calls':0},indent=2))
if __name__=='__main__':main()
