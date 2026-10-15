"""Curate final scalar qualification results and limits."""
import hashlib,json
from pathlib import Path
G=Path(__file__).parent
q=json.loads((G/'installed-qualification-01/qualification.json').read_text())
v=json.loads((G/'validation-summary.json').read_text())
s=json.loads((G/'source-manifest.json').read_text())
a=q['full_public_installed_audit'];f=a['fixture']
c=q['retrieval_probe']['production_quota_probe']['compact_code_retrieval']
w=c['materialized_worker']
assert q['qualified'] and q['qualification_container_removed'] and q['provider_calls']==0
assert all(c['all_observed_coding_inputs_verified']is True for c in a['collections'])
review=G/'installed-qualification-independent-review.json'
assert review.is_file(), 'Independent installed review must finish before final result.'
result={'schema':'materialized-code-retrieval-final-result@1',
 'implemented_control':'code_retrieval_wire_delivery=inline|materialized',
 'default_codec':'expanded','default_wire_delivery':'inline',
 'implemented_behavior':[
  'Verified compact wire is written outside candidate Git before provider dispatch; full command uses independent wire/source/native pins and no inherited variable.',
  'Versions1/2 remain byteexact; version3 keeps canonical inlinepacket and complete sizegate.',
  'Original file and directory witnesses detect sameUID mutation; exact unchanged artifacts cleaned, changed artifacts preserved with failedcleanup status.',
  'Zero-call preparation refusals are retained separately from actual provider invocations, with unknown usage and conservative wholetrial accounting.',
  'Historical replay reconstructs complete input without livewire or candidate checkout; comparison separates delivery controls and retains failures.'],
 'source_files_changed':len(s['files']),'source_patch_sha256':s['patch_sha256'],
 'runtime_archive_sha256':q['archive_sha256'],'runtime_manifest_sha256':q['runtime_manifest_sha256'],
 'unique_focused_passing_tests':v['unique_passing_cases'],'selected_junit_records':v['selected_junit_records'],
 'whole_repository_test_pass_claimed':False,
 'installed_qualification':{'qualified':True,'seconds':q['elapsed_seconds'],'container_removed':True,
  'actual_worker_uid':w['uid'],'actual_worker_euid':w['euid'],'guidance_version':w['guidance_version'],
  'exact_advertised_command_executed':w['exact_advertised_command_executed'],
  'shell_environment_keys':w['shell_environment_keys'],'complete_native_hits':w['complete_native_hits'],
  'same_uid_hash_mutation_refused':w['same_uid_wire_hash_mutation_refused'],
  'same_uid_write_restore_witness_refused':w['same_uid_write_restore_witness_refused'],
  'owner_roots_R_W_X_denied_individually':w['owner_roots_individually_inaccessible'],
  'candidate_git_census_unchanged':w['candidate_git_census_unchanged'],
  'public_source_cache_unchanged':w['public_cache_source_witnesses_unchanged'],
  'positive_cleanup':w['exact_positive_wire_cleanup'],
  'original_tracked_task_inputs_preserved':q['original_tracked_task_inputs_preserved'],
  'historical_cases':[{k:c[k] for k in ('case','code_retrieval_codec','status','all_observed_coding_inputs_verified','seconds')} for c in a['collections']],
  'genuine_context_result_metadata_absent':f['genuine_context_result_metadata_absent'],
  'context_bytes_copied_without_modification':f['expected_context_bytes_copied_without_modification'],
  'historical_v3_delivery_descriptor_is_authored_fixture_not_physical_delivery':f['materialized_descriptor_authored_without_live_delivery'],
  'historical_wire_live_path_not_required':f['materialized_wire_live_path_never_required_by_historical_replay'],
  'native_bundle_negative_controls':a['native_bundle_negative_controls']},
 'byte_observations_not_provider_tokens':{
  'worker_native_prompt_bytes':c['projection']['native_prompt_bytes'],
  'worker_inline_v2_selected_prompt_bytes':c['projection']['selected_prompt_bytes'],
  'worker_materialized_v3_selected_prompt_bytes':w['selected_prompt_bytes'],
  'v3_additional_bytes_over_v2':w['selected_prompt_bytes']-c['projection']['selected_prompt_bytes'],
  'full_fixture_expanded_model_prompt_bytes':f['model_prompt_bytes'],
  'full_fixture_inline_v2_model_prompt_bytes':f['compact_code_model_prompt_bytes'],
  'full_fixture_materialized_v3_model_prompt_bytes':f['materialized_v3_model_prompt_bytes']},
 'independent_installed_review_sha256':hashlib.sha256(review.read_bytes()).hexdigest(),
 'live_model_provider_calls':0,'new_model_fit_or_prover_jobs':0,
 'official_verifier_or_task_reward_run_in_this_stage':False,
 'total_token_savings_established':False,'cause_of_prior_extra_tokens_established':False,
 'arbitrary_source_to_model_semantic_equivalence_proved':False,'formal_model_convergence_proved':False,
 'owner_immutable_wire_custody_claimed':False,'proof_or_publication_or_completion_authority_granted':False,
 'prior_v12_failure_and_v13_metadata_refresh_unknown_preserved':True,
 'github_or_huggingface_publication_performed':False,
 'source_checkout':s['checkout'],'reviewable_patch':'changes.patch','next_work':'next-work.json'}
(G/'result-summary.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({'qualified':True,'unique_tests':v['unique_passing_cases'],'historical_cases':len(a['collections']),
 'actual_worker_uid':w['uid'],'provider_calls':0,'total_token_savings_established':False}),flush=True)
