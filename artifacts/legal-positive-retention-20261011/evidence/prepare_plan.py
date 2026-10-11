"""Bind one matched objective experiment without constructing any model."""
from pathlib import Path
from hashlib import sha256
import json,sys
F=Path(__file__).resolve().parent;D=F/'datasets';C=F/'corpus';P=F.parent/'legal-support-gate-20261007-01'
sys.path.insert(0,str(D))
from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_retention_gate as head
from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_retention_selection as policy
def pin(path):
 path=Path(path).resolve();raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=sha256(raw).hexdigest())
prior=json.loads((P/'experiment-plan.json').read_text())
manifest=json.loads((C/'corpus-manifest.json').read_text())
protocol=json.loads((C/'corpus-protocol.json').read_text())
plan=dict(schema='support-retention-objective-matched-plan/v1',
 candidate_source_main='a1b5c73e5b687d8bd6c3b3051788860fd6e2f07a',
 seed=24606,arms=['bce','positive_margin'],hidden=32,feature_width=97,
 feature_bundle='same frozen contextual64 plus donor ordered Conv3 mean/max/log-length33',
 pooling='predicted_trigger interval coverage in both arms',
 trainable_parameters={k:3169 for k in ('bce','positive_margin')},capacity_matched=True,
 same_seeded_gate_tensors=True,same_data_and_optimizer_call_budget=True,
 updates_per_arm=240,batch_size=16,positive_per_batch=8,negative_per_batch=8,
 actual_encoded_batch_size=16,learning_rate=.003,weight_decay=0.0,gradient_clip=5.0,
 support_threshold=.5,selection_steps=[0,120,240],
 source_profile='fresh-support-retention-20261011/v1',
 objectives=dict(bce='mean support BCE over all16 paired source records',
 positive_margin='same support BCE plus lambda1 mean squared relu(clamp(detached frozen-parent support logit,0,1)-candidate support logit) over supported TRAIN rows whose actual frozen parent emits a proposal'),
 retention_lambda=dict(bce=0.0,positive_margin=1.0),retention_floor_clamp=[0.0,1.0],
 retention_empty_mask='exact scalarzero',retention_is_soft_training_penalty=True,
 teacher_origin='online shared frozen-parent tensor pass decoded on each TRAIN row; source bytes and explicit caller attachment; no cached external teacher or reference pointers',
 shared_parent_tensor_paths_per_step=1,additional_parent_model_forwards_per_step=0,
 teacher_decode_rows_per_step=16,teacher_labels_at_inference=False,
 fitting_reference_fields=['supported boolean only'],
 action_class_presence_pointer_losses_or_updates=False,
 selection_eligibility=[
 'negative_emitted_proposal_count <= measuredstep0 baseline',
 'positive_exact_count >= measuredstep0 baseline',
 'positive_emitted_proposal_count >= measuredstep0 baseline',
 'positive_learned_refusal_count <= measuredstep0 baseline',
 'all baseline exact positive IDs retained',
 'all baseline emitted positive IDs retained',
 'no new negative emitted IDs'],
 baseline_positive_emission_and_whole_must_be_nonzero_before_fitting=True,
 selection_rank=['-negative_emitted_proposal_count','positive_exact_count','negative_learned_refusal_count','-actual_updates'],
 fallback='measured exact coldstep0 checkpoint',selected_fitted_gain_requires='removed baseline negative emission or gained wholepositive success, not a rank tie',
 selection_constraints_case_and_aggregate=True,per_case_preservation_guaranteed_on_final=False,
 fresh_final_constraints_guaranteed=False,retention_selection_or_fitting=False,
 actual_optimizer_calls_across_arms=480,support_updates=480,action_updates=0,class_updates=0,
 encoded_source_presentations_per_arm=3840,positive_support_presentations_per_arm=1920,
 negative_support_presentations_per_arm=1920,ignored_negative_records=0,
 actual_parent_pairs_per_step=8,negative_parent_pairs_per_category_per_step=2,
 parent_checkpoint=pin(F/'parent-checkpoint.json'),parent_selected_steps=120,
 parent_selected_action_steps=120,parent_Adam_continued=False,
 all_parent_tensors_modes_flags_configs_and_old_Adam_bytes_frozen=True,new_gate_Adam_fresh=True,
 builder=pin(F/'corpus-builder.py'),corpus_protocol=pin(C/'corpus-protocol.json'),
 corpus_manifest=pin(C/'corpus-manifest.json'),schedule_file=pin(C/'training-schedule.json'),
 schedule_canonical_sha256=manifest['training_schedule_sha256'],
 runner=pin(F/'run_retention_experiment.py'),selection_policy=pin(Path(policy.__file__)),
 scorer=prior['scorer'],producer_pins=head.producer_pins(),
 inputs={s:pin(C/(s+'-inputs.json')) for s in ('train','selection','final')},
 references={s:pin(C/(s+'-references.json')) for s in ('train','selection','final')},
 retention=prior['retention'],
 numerical_barrier='Both choices and selectedcheckpointhashes fsynced before parsing freshfinal or anyretention refs; all15 parent/selected outputs over5cohorts fsynced before anyevaluation-referencejoin',
 source_inputs_only_at_inference=True,inference_targets_training_helpers_parser_optimizer_denied=True,
 structural_ceiling='measure TRAIN/selection prefit; finalonly after locked output/referencebarrier',
 construction_labels_authors_blind=False,legal_gold=False,source_only=True,latent_conditioned=False,
 condition_attachment='explicit caller premise copied only if predicted condition nonempty',
 law_semantics_verified=False,formal_output=None,admission_masks='all fivezero',
 Lake_or_native_lowering_run=False,default_promotion=False,
 one_seed_preliminary_engineering_study=True)
old_results=P/'release/results'
plan['retention']['earlier_support_gate']=dict(inputs=pin(P/'final-inputs.json'),
 references=pin(P/'final-references.json'),archived_parent_predictions=pin(old_results/'parent-fresh_final-predictions.json'),
 role='fourth exposed postfit retention only')
assert plan['parent_checkpoint']['sha256']=='48559399bb22de0fe68908919d225d391880a38f4fab659026d526e19ffc9155'
assert protocol['source_profile']==plan['source_profile'] and '^2' in protocol['objectives']['retention']
assert plan['schedule_canonical_sha256']=='fd8cf0b032ec07a45131358450d49b1b6c09932cad7faaf7cdc2ced5ec82696f'
p=F/'experiment-plan.json'
with p.open('x') as out:json.dump(plan,out,indent=2);out.write('\n')
print(json.dumps(dict(plan=pin(p),models_constructed=0,optimizer_steps=0)))
