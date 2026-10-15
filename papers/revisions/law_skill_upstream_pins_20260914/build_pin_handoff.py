#!/usr/bin/env python3
"""Bind recovered immutable candidate sources and explicitly limited lineage evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'law_study_preparation_20260914'
ROOT=HERE.parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def bind(path):return {'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)}
def save(name,data):
    with (HERE/name).open('x') as out:json.dump(data,out,indent=2,sort_keys=True);out.write('\n')
def check(binding):
    path=Path(binding['path']);assert sha(path)==binding['sha256'] and path.stat().st_size==binding['bytes'],path
def main():
    original=json.loads((PRIOR/'skill_candidates_v1/source_manifest.json').read_text())
    initial=json.loads((HERE/'recovery_summary.json').read_text())
    completion=json.loads((HERE/'authenticated_completion_v1/recovery_summary.json').read_text())
    merged={r['family']['task_key']:r for r in initial['families']}
    for r in completion['families']:
        assert merged[r['family']['task_key']]['blocking_fetch_failures']
        merged[r['family']['task_key']]=r
    assert len(merged)==12
    families=[]
    for old in original['families']:
        r=merged[old['task_key']];assert not r['blocking_fetch_failures'] and r['family']==old
        row=json.loads(Path(r['source_row']['path']).read_text())
        check(r['source_row'])
        cutoff=datetime.datetime.fromisoformat(r['recorded_original_fetch_at'].replace('Z','+00:00'))
        commit=r['candidate_commit']
        assert datetime.datetime.fromisoformat(commit['committer_date'].replace('Z','+00:00'))<=cutoff
        assert re.fullmatch('[0-9a-f]{40}',commit['sha']) and len(r['files'])==2
        readme=next(f for f in r['files'] if f['kind']=='readme')
        license_file=next(f for f in r['files'] if f['kind']=='license')
        directory=Path(readme['response_binding']['path']).parent
        tree=json.loads((directory/'root-tree.body').read_text())
        assert tree['sha']==commit['tree_sha'] and not tree.get('truncated')
        blobs={f['path']:f['sha'] for f in tree['tree'] if f['type']=='blob'}
        for f in r['files']:
            assert f['available'] and f['revision']==commit['sha'];check(f['response_binding'])
            raw=Path(f['response_binding']['path']).read_bytes()
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blobs[f['path']]==f['git_blob_id']
        text=Path(license_file['response_binding']['path']).read_text()
        if 'Permission is hereby granted, free of charge' in text and 'THE SOFTWARE IS PROVIDED "AS IS"' in text:
            classification='MIT'
        elif 'Apache License' in text and 'Version 2.0, January 2004' in text:
            classification='Apache-2.0'
        else:raise AssertionError('License text requires manual classification: '+old['task_key'])
        generated=re.search(r'^license_spdx: "([^"]+)"$',row['metadata_yaml'],re.M).group(1)
        api_license=(r['repository_identity'].get('license') or {}).get('spdx_id')
        family={
            'family_id':old['family_id'],'task_key':old['task_key'],'skill_id':old['skill_id'],
            'pinned_generated_procedure_binding':{'source_row':r['source_row'],
                                                 'procedure':bind(PRIOR/'skill_candidates_v1'/old['procedure_path'])},
            'declared_repository':old['repository'],'resolved_repository':'github.com/'+r['repository_identity']['full_name'].lower(),
            'repository_identity':r['repository_identity'],'candidate_upstream_commit':commit,
            'candidate_pin_selection':r['candidate_pin_selection'],
            'recorded_original_fetch_at':r['recorded_original_fetch_at'],
            'original_source_capture_proven':False,'original_branch_identity_proven':False,
            'primary_files':r['files'],'exact_commit_license_text_classification':classification,
            'generated_metadata_license':generated,'current_api_license':api_license,
            'current_api_license_differs_from_pinned_text':api_license!=classification,
            'license_document_and_git_blob_binding_verified':True,
            'all_source_redistribution_obligations_reviewed':False,
            'fork_metadata':{'current_api_fork':r['repository_identity']['fork'],
                             'parent_and_source':r['fork_parent_and_source'],
                             'complete_historical_fork_clone_audit':False},
            'source_bindings':{name:bind(directory/name) for name in ['repository.body','historical-commit-list.body',
                                                                    'root-tree.body','recovery.json']},
            'scientific_admission':False,'upstream_program_build_or_tests_executed':False,
            'source_relative_oracle_equivalence_qualified':False,
        }
        families.append(family)
    by_key={f['task_key']:f for f in families}
    metadata_dir=HERE/'declared_lineage_metadata'
    django=json.loads((metadata_dir/'django_declared_base.body').read_text())
    scheb=json.loads((metadata_dir/'scheb_declared_successor.body').read_text())
    modsecurity=json.loads((metadata_dir/'modsecurity_declared_legacy_namespace.body').read_text())
    assert modsecurity['id']==by_key['modsecurity_config']['repository_identity']['id']
    edges=[
        {'from_repository':by_key['django_refresh']['resolved_repository'],
         'to_repository':'github.com/'+django['full_name'].lower(),
         'observed_link':'github.com/getblimp/django-rest-framework-jwt',
         'kind':'explicit_primary_readme_based_on_derivation','lineage_merge_required_for_new_cohort':True,
         'claim_limit':'README declaration plus resolved repository identity; copied-code overlap not yet measured.',
         'metadata_binding':bind(metadata_dir/'django_declared_base.body')},
        {'from_repository':by_key['backup_code']['resolved_repository'],
         'to_repository':'github.com/'+scheb['full_name'].lower(),
         'kind':'explicit_primary_readme_successor_project','lineage_merge_required_for_new_cohort':True,
         'claim_limit':'Conservative same-lineage treatment of the explicitly named successor; complete source history not reconstructed.',
         'metadata_binding':bind(metadata_dir/'scheb_declared_successor.body')},
        {'from_repository':'github.com/spiderlabs/modsecurity-nginx',
         'to_repository':by_key['modsecurity_config']['resolved_repository'],
         'kind':'legacy_namespace_resolves_to_same_repository_id','repository_id':modsecurity['id'],
         'lineage_merge_required_for_new_cohort':True,
         'metadata_binding':bind(metadata_dir/'modsecurity_declared_legacy_namespace.body')},
    ]
    old_manifest=ROOT/'.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/benchmark/manifests/sources.json'
    historical=json.loads(old_manifest.read_text())
    historical_keys={r['ancestry_key'][1].lower() for r in historical['source_records'] if r['ancestry_key'][0]=='repository'}
    cve_path=HERE.parent/'law_cve_screen_completion_20260914/proposed_cve_candidates_v3.json'
    cve=json.loads(cve_path.read_text());cve_keys={r['source']['repository'].lower() for r in cve['families']}
    source_nodes={f['resolved_repository'] for f in families}|{e[k] for e in edges for k in ['from_repository','to_repository']}
    overlap=sorted(source_nodes&(historical_keys|cve_keys));assert not overlap
    preserved=json.loads((PRIOR/'source_preparation_inventory.json').read_text())
    for name,entry in preserved['files'].items():check({'path':str(PRIOR/name),**entry})
    report={'schema':'skill-upstream-historical-candidate-pins-proposal/v1','status':'TWELVE_IMMUTABLE_CANDIDATE_PINS_AND_LICENSE_DOCUMENTS_RECOVERED',
        'original_skill_manifest':bind(PRIOR/'skill_candidates_v1/source_manifest.json'),
        'families':families,'family_order_and_procedure_contracts_unchanged':True,
        'declared_lineage_edges':edges,'known_lineage_node_overlap_with_old_study_or_corrected_CVE':overlap,
        'historical_identity_source':bind(old_manifest),'corrected_cve_identity_source':bind(cve_path),
        'full_historical_fork_clone_nearest_neighbor_closure':False,
        'original_source_capture_verified':False,'scientific_admission':False,
        'model_calls':0,'upstream_code_executed':False,'native_mutations':0,
        'original_frozen_files_verified_unchanged':len(preserved['files']),
        'next_requirements':['Review adoption of these historical candidate revisions as explicit source pins; exact original generated-source captures remain unavailable.',
            'Retain pinned license notices and source-version-specific terms; do not substitute current API labels.',
            'Carry the three declared lineage relationships into exclusion/split closure and inspect code similarity before claiming complete independence.',
            'Qualify actual upstream task behavior and source-to-oracle adaptation, complete execution profiles and native effect/resource evidence.',
            'Keep scientific splits/final release/model execution disabled until the prospective full-study gate passes.']}
    save('upstream_pin_proposal.json',report)
    save('verification.json',{'schema':'skill-source-pin-binding-verification/v1','checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_IMMUTABLE_CANDIDATE_SOURCE_BINDINGS_ONLY','candidate_commits':12,'primary_readme_files':12,'license_documents':12,
        'all_primary_file_git_blob_ids_verified':True,'all_commit_dates_before_recorded_original_fetch':True,
        'current_api_fork_flags_false':all(not f['repository_identity']['fork'] for f in families),
        'declared_lineage_edges':3,'known_old_or_corrected_CVE_lineage_overlap':overlap,
        'license_metadata_discrepancies':[f['task_key'] for f in families if f['current_api_license_differs_from_pinned_text']],
        'frozen_preparation_files_preserved':len(preserved['files']),
        'original_capture_or_full_ancestry_proven':False,'scientific_admission_or_results_verified':False,
        'model_calls':0,'upstream_code_executed':False,'proposal':bind(HERE/'upstream_pin_proposal.json'),
        'builder':bind(Path(__file__).resolve())})
    print(json.dumps({'families':12,'exact_readme_and_license_files':24,'declared_lineage_edges':3,
                      'license_metadata_discrepancies':['current_user'],'original_frozen_files_preserved':325,
                      'scientific_admission':False,'model_calls':0}))
if __name__=='__main__':main()
