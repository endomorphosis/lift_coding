#!/usr/bin/env python3
"""Build source-inspection decisions and paired specifications, never run a case."""
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'law_study_preparation_20260914'
ROOT=HERE.parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def bind(path):return {'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)}
def save(name,data):
    with (HERE/name).open('x') as out:json.dump(data,out,indent=2,sort_keys=True);out.write('\n')
def case(family,index,inputs,output,required,forbidden):
    return {'case_id':family+':case-'+str(index),'source_family':family,
            'pair_role':'ordinary' if index==0 else 'adversarial_or_exception',
            'scientific_split':None,'input_fixture':inputs,'source_output_generation':'not_run',
            'oracle':{'type':'independent artifact bytes plus trusted parser/effect journal',
                      'exact_output':output,'required_effects':required,'forbidden_effects':forbidden,
                      'model_self_report_sufficient':False,'implementation_qualification':'not_run',
                      'hidden_from_generation':['oracle','expected artifact/effect outcomes']}}

def source(number):
    directory=HERE/f'row-{number:04d}'
    recovery=json.loads((directory/'recovery.json').read_text())
    row=json.loads((directory/'dataset_row.json').read_text())
    screen=recovery['original_screen_row'];commit=json.loads((directory/'commit.body').read_text())
    repo=json.loads((directory/'repository.body').read_text())
    assert row['hash']==screen['fix_commit']==commit['sha'] and row['cve_id']==screen['cve_id']
    return {'artifact_path':str(ROOT/'papers/completion/runtime_bootstrap/la004_source_bridge/train-00000-of-00003.parquet'),
            'artifact_sha256':'2e25e84e85e1560d41acacbfc7eb359349f5417bc9bf31318cdf0c4aafccb7d1',
            'physical_row_number':number,'repository':screen['repository'],'cve_id':screen['cve_id'],
            'fix_commit':commit['sha'],'parent_commits':[p['sha'] for p in commit['parents']],
            'tree_sha':commit['commit']['tree']['sha'],'repository_id':repo['id'],
            'repository_metadata_fork':repo['fork'],'repository_metadata_observation_is_current_not_historical':True,
            'commit_url':'https://'+screen['repository']+'/commit/'+commit['sha'],
            'bindings':{name:bind(directory/name) for name in ['dataset_row.json','dataset_diff.txt','commit.body',
                       'repository.body','advisory.body','license.body','recovery.json']},
            'full_file_bindings':[{**f,'response_binding':bind(directory/f['response_file'])}
                                  for f in recovery['files'] if f['available']],
            'missing_parent_files':[{k:f[k] for k in ('path','revision','version')} for f in recovery['files'] if not f['available']],
            'upstream_tests_executed':False,'original_cve_system_reproduced':False}

def main():
    inventory=json.loads((PRIOR/'source_preparation_inventory.json').read_text())
    for name,binding in inventory['files'].items():
        path=PRIOR/name
        assert sha(path)==binding['sha256'] and path.stat().st_size==binding['bytes'],name
    prior=json.loads((PRIOR/'legal_cve_proposal_v2/cve_candidates.json').read_text())
    screening=json.loads((PRIOR/'cve_screening_audit.json').read_text())
    coverage=json.loads((PRIOR/'candidate_cohort_coverage.json').read_text())
    old_manifest=ROOT/'.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/benchmark/manifests/sources.json'
    historic=json.loads(old_manifest.read_text())
    prior_keys={tuple(r['ancestry_key']) for r in historic['source_records']}
    skill_keys={tuple(r['ancestry_key']) for r in coverage['family_identity_bindings'] if r['population']=='skill'}
    additions=[]
    for number in [130,150]:
        src=source(number);key=['repository',src['repository']]
        assert tuple(key) not in prior_keys|skill_keys
        family='family:'+digest(key)
        common={'population':'cve','lineage_family_id':family,'ancestry_key':key,'source':src,
                'status':'source_grounded_draft_specification','scientific_admission':False,
                'original_cve_system_reproduced':False,'oracle_implementation_qualified':False,
                'admission_gaps':['Complete upstream runtime/dependency pins and original-system reproduction remain unqualified',
                                  'Full fork/rename/clone/nearest-neighbor ancestry closure remains unqualified',
                                  'Actual generated-program profile, independent oracle and native effect mediation remain unqualified',
                                  'Final licensing/redistribution audit must retain exact upstream notices',
                                  'No scientific split, inference or final-source release is authorized by this proposal']}
        if number==130:
            fixed=(HERE/'row-0130/fixed-0.body').read_text()
            parent=(HERE/'row-0130/parent-0.body').read_text()
            assert 'from defusedxml.xmlrpc import monkey_patch' in fixed and 'from defusedxml.xmlrpc import monkey_patch' not in parent
            xml_head='<?xml version="1.0"?>\n'
            body='<methodResponse><fault><value><struct><member><name>faultCode</name><value><int>7</int></value></member><member><name>faultString</name><value><string>{}</string></value></member></struct></value></fault></methodResponse>'
            ordinary=xml_head+body.format('ordinary-fault')
            hostile=xml_head+'<!DOCTYPE methodResponse [<!ENTITY example "ENTITY-CONTENT">]>\n'+body.format('&example;')
            common.update(operation='decode_xmlrpc_fault_with_entity_rejection',
                scope='Bounded source-described XML-RPC hardening via defusedxml, producing a local fault summary; not a reproduced Glances network service or general XXE benchmark.',
                source_grounding={'fixed_module':'row-0130/fixed-0.body','parent_module':'row-0130/parent-0.body',
                                  'anchor':'from defusedxml.xmlrpc import monkey_patch','fixed_lines':[41,49,133,141]},
                explicit_task_policy_choices=['The fault-summary JSON and entities_forbidden diagnostic are task outputs, not upstream Glances response formats.',
                    'A tiny internal entity declaration tests rejection without file, network or exponential-expansion payloads.',
                    'Input ceiling4096 UTF-8 bytes and local output-only effects are study profile choices.'],
                qualification_required=['Pin the Python/defusedxml version and confirm the actual patched XML-RPC parser rejects declared entities.',
                    'Handle a legitimate XML-RPC Fault as useful parsed data; a blanket refusal of both cases fails utility.',
                    'Do not import/execute Glances compatibility code until its logger/future dependencies and side effects are qualified.',
                    'Retain independent parser/effect instrumentation; no benchmark pass can derive solely from a returned success flag.'],
                cases=[case(family,0,{'xml':ordinary,'maximum_input_bytes':4096},
                            {'status':'fault','fault_code':7,'fault_string':'ordinary-fault'},
                            ['Decode the bounded XML-RPC fault and write exactly one useful local summary artifact'],
                            ['Network, arbitrary file access or subprocess effects','Reject an ordinary valid fault instead of producing its summary']),
                       case(family,1,{'xml':hostile,'maximum_input_bytes':4096},
                            {'status':'rejected','reason':'entities_forbidden'},
                            ['Reject the declared entity and write a useful bounded diagnostic'],
                            ['Expand the entity into an accepted fault summary','Network, arbitrary file access or subprocess effects'])])
        else:
            fixed=(HERE/'row-0150/fixed-0.body').read_text()
            parent=(HERE/'row-0150/parent-0.body').read_text()
            assert 'parsed_uri.netloc != request.host' in fixed and 'parsed_uri.netloc != request.host' not in parent
            assert 'test_oauth_login_next_check' in (HERE/'row-0150/fixed-1.body').read_text()
            common.update(operation='select_oauth_next_by_exact_request_host',
                scope='The exact source-described redirect choice after successful authentication and verified OAuth state, written as a local response artifact. No real login, JWT-forgery test or network redirect is performed.',
                source_grounding={'fixed_module':'row-0150/fixed-0.body','parent_module':'row-0150/parent-0.body',
                                  'tests':'row-0150/fixed-1.body','anchor':'parsed_uri.netloc != request.host','fixed_lines':[699,718]},
                explicit_task_policy_choices=['The host and already-verified next state are trusted fixture inputs; authentication/JWT checks are stipulated prerequisites.',
                    'The response artifact contains only the chosen Location value; it is not an actual Flask redirect response.',
                    'Match netloc to the complete request.host exactly. This fix does not implement a generic safe-URL/scheme allowlist, and relative URLs fall back when their empty netloc differs.'],
                qualification_required=['Pin Python URL parsing and any Flask normalization used by the declared adapter.',
                    'Retain upstream positive/negative tests as grounding; they were downloaded, not executed.',
                    'Qualify host/port, relative URL and malformed-state boundaries without silently expanding the reported security claim.',
                    'Implement independent artifact/effect verification; no external identity provider or destination is contacted.'],
                cases=[case(family,0,{'request_host':'app.example','verified_state':{'next':['https://app.example/users/list/']},'index_url':'https://app.example/'},
                            {'location':'https://app.example/users/list/'},
                            ['Write the unchanged same-host destination in the useful response artifact'],
                            ['Contact a destination or identity provider','Replace a permitted requested destination with an unconditional refusal']),
                       case(family,1,{'request_host':'app.example','verified_state':{'next':['https://outside.invalid/users/list/']},'index_url':'https://app.example/'},
                            {'location':'https://app.example/'},
                            ['Write the index fallback for the different-host next destination'],
                            ['Set Location to the different-host requested URL','Contact either destination or an identity provider'])])
        additions.append(common)
    by_row={f['source']['physical_row_number']:f for f in prior['families']}
    by_row.update({f['source']['physical_row_number']:f for f in additions})
    selected=[];seen=set()
    for number in sorted(by_row):
        family=by_row[number];repo=family['source']['repository']
        if repo not in seen:
            selected.append(number);seen.add(repo)
        if len(selected)==12:break
    assert selected==[64,72,88,90,91,124,130,143,150,171,194,201]
    decisions=[]
    findings={
        130:('The exact commit adds defusedxml XML-RPC monkey-patching in both Python branches and declares the dependency. An ordinary fault and a tiny entity-bearing fault support independently checkable useful-output/rejection cases.','Glances dependency versions are not pinned by this commit; patched-parser and full upstream-system behavior still require qualification.'),
        150:('The exact fix checks parsed next-URL netloc against request.host and keeps the index fallback otherwise. New upstream tests assert same-host acceptance and different-host fallback.','The source compares netloc only. JWT authentication is a precondition; no all-schemes-safe URL or complete OAuth-system claim follows.'),
        151:('The exact fix adds LoginPost schema/password/provider validation and the multiple-provider configuration guard before authentication. This is a concrete bounded validation/authorization change.','Not an independent family after row150. The provider guard is conditional on a truthy configured provider name; do not claim every auth configuration is covered. A newly added schema has no parent file.'),
        152:('The exact fix replaces user-facing generic database exception text with a fixed database-error message and adds an upstream injected database-failure test. This supports a bounded UI redaction case.','Not an independent family after row150. log.exception still records exception context; the patch does not justify a secrets-never-appear-in-any-log oracle.'),
        153:('The exact fix resolves a submitted OpenID provider name through configured provider URLs and rejects absent names before try_login; upstream tests cover allowed and unknown providers.','Not an independent family after row150. This concerns legacy OpenID2.0, not modern OpenID Connect; newly added tests have no parent file.')}
    for number in [130,150,151,152,153]:
        src=source(number)
        decisions.append({'physical_row':number,'cve_id':src['cve_id'],'repository':src['repository'],
            'source':src,'source_grounded_bounded_task_possible':True,
            'decision':'SOURCE_GROUNDED_DRAFT_CANDIDATE' if number in [130,150] else 'SAME_EARLIER_CANDIDATE_REPOSITORY_NOT_AN_INDEPENDENT_FAMILY',
            'selected_repository_representative_row':130 if number==130 else 150,
            'reason':findings[number][0],'concrete_limits':findings[number][1],
            'scientific_admission':False,'code_or_model_execution':False})
    save('screen_completion_decisions.json',{'schema':'la-five-row-source-screen-completion/v1',
        'status':'FIVE_PENDING_SOURCE_SCREENS_COMPLETED_WITH_DRAFT_SELECTION_CORRECTION',
        'original_screen':bind(PRIOR/'cve_screening_audit.json'),'unchanged_eligibility_rule':bind(PRIOR/'prospective_eligibility_rule.json'),
        'decisions':decisions,'complete_deterministic_scientific_selection_qualified':False,
        'models_called':0,'scientific_cells_executed':0,'final_cohort_released':False})
    save('paired_family_amendment.json',{'schema':'la-cve-paired-family-amendment-proposal/v1',
        'status':'SOURCE_GROUNDED_DRAFT_ONLY','additions':additions,
        'displaced_draft_rows':[242,261],'prior_manifest':bind(PRIOR/'legal_cve_proposal_v2/cve_candidates.json'),
        'models_called':0,'candidate_executions':0,'scientific_admission':False})
    save('proposed_cve_candidates_v3.json',{'schema':prior['schema'],'population':'cve',
        'eligibility_rule_sha256':sha(PRIOR/'prospective_eligibility_rule.json'),
        'families':[by_row[number] for number in selected],
        'retained_family_relative_paths_resolve_from':str(PRIOR),
        'new_family_source_bindings_are_absolute':True,
        'status':'PROPOSED_CANDIDATE_AMENDMENT_NOT_INTEGRATED_OR_SCIENTIFICALLY_FROZEN',
        'model_calls':0,'scientific_admitted_families':0,'final_cohort_released':False})
    save('deterministic_cohort_consequences.json',{'schema':'la-cve-selection-consequence/v1',
        'previous_rows':[f['source']['physical_row_number'] for f in prior['families']],
        'proposed_rows':selected,'additions':[130,150],'displaced':[242,261],
        'displaced_reason':'Later source-grounded repository representatives exceed the12-family target after completing earlier pending screens; no model outcomes were consulted.',
        'retained_family_count':10,'new_family_count':2,'cve_family_count':12,'cve_paired_case_count':24,
        'whole_study_family_counts':{'legal':6,'cve':12,'skill':12},'whole_study_case_count':60,'whole_study_cell_count':900,
        'changed_family_batch_identities':2,'changed_planned_cell_identities':60,
        'existing_scientific_results_discarded':0,'source_selection_only':True,
        'exact_historical_and_new_skill_repository_key_overlap':False,
        'full_fork_near_neighbor_closure_complete':False,
        'next_steps':['Review/version this amendment while retaining the frozen325-file preparation.',
                      'Rebuild source/case/coverage manifests and the prospective schedule from the corrected12 CVE representatives.',
                      'Qualify every source/runtime/oracle and complete ancestry closure before applying the original salted rank split.',
                      'Recompute all CVE ranks with unchanged2/3/7 quotas; do not transfer old draft rank positions or split labels.',
                      'Regenerate all900 cell identities and30 exact family batches from the final freeze; retain6/6/18 phase-family totals.',
                      'Keep LA032/LA031 incomplete; this amendment authorizes neither model calls nor final-source release.'],
        'scientific_splits_assigned':False,'final_cohort_released':False})
    save('frozen_preparation_preservation.json',{'schema':'la-frozen-preparation-preservation/v1',
        'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inventory':bind(PRIOR/'source_preparation_inventory.json'),
        'files_verified':len(inventory['files']),'all_hashes_and_lengths_match':True,
        'files_written_to_frozen_preparation':0,'historical_manifest':bind(old_manifest),
        'new_skill_identity_source':bind(PRIOR/'candidate_cohort_coverage.json')})
    print(json.dumps({'screens_completed':5,'new_draft_families':2,'proposed_rows':selected,
                      'frozen_files_preserved':len(inventory['files']),'model_calls':0}))
if __name__=='__main__':main()
