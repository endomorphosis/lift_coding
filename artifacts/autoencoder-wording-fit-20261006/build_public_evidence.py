"""Publish bounded source/fit/observation evidence without private model tensors."""
from pathlib import Path
import gzip
import hashlib
import json
import tarfile

R=Path(__file__).resolve().parent;W=R.parents[1];P=W/'external/ipfs_datasets'
RUN=P/'workspace/test-logs/decoder-normative-wording-r2-20261006'
PUBLIC=P/'docs/implementation/reports/evidence/decoder-normative-wording-20261006'

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for data in iter(lambda:stream.read(1048576),b''):h.update(data)
 return h.hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def save(path,value):
 with path.open('x')as stream:json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')

def main():
 summary=read(RUN/'evaluation-r1/results/summary.json')
 audit=read(R/'review/development_results_audit.json');fit_audit=read(R/'review/fit_audit.json')
 assert summary['complete']is True and len(summary['panels'])==8
 for a in (audit,fit_audit):assert a['passed']is True and not a['findings']
 phases={}
 for attempt in ('preparation-r1','preflight-384-r1','preflight-768-r1','training-384-r1','training-768-r1','evaluation-r1'):
  final=read(RUN/attempt/'resources-final.json');outer=read(RUN/(attempt+'-guardian-exit.json'))
  assert final['status']=='released'and outer['returncode']==read(RUN/attempt/'child-exit.json')['returncode']==0
  driver=read(RUN/attempt/'results/summary.json')
  phases[attempt]=dict(driver_seconds=driver['elapsed_seconds'],guardian_seconds=outer['elapsed_seconds'],
   retained_attempt_bytes=final['record']['final_attempt_bytes'],cap_bytes=final['storage_limit_bytes'],
   charged_campaign_bytes=final['record']['final_accounting']['charged_bytes'],released=True)
 panels=[dict(x,sample_count=60,generation_seconds_per_span=x['generation_seconds']/60)for x in summary['panels']]
 training={}
 for dimension in (384,768):
  comparison=read(RUN/f'training-{dimension}-r1/results/summary.json')
  training[str(dimension)]=[read(item['summary_path'])for item in comparison['runs']]
  assert all(x['budget_completed']for x in training[str(dimension)])
  assert [x for x in training[str(dimension)]if x['arm']=='normative-wording-zero'][0]['zero_arm_archived_replay_verified']is True
 PUBLIC.mkdir(parents=True,exist_ok=False)
 results=dict(schema='published-normative-wording-training-comparison/v1',complete=True,panels=panels,
  training=training,phase_wall_times=phases,recipe=summary['recipe'],
  native_source_vectors_per_width=276,new_training_clause_count=180,development_source_count=60,
  native_preparation_audit=read(R/'review/native_preparation_audit.json'),fit_audit=fit_audit,development_audit=audit,
  training_executed=True,local_native_encoders_executed=True,weights_downloaded=False,
  source_head_observed_in_same_greedy_pass=True,all_predictions_fsynced_before_reference_load=True,
  input_reconstruction_mse_measured=False,original_development_meanings_previously_exposed=True,
  comparison_is_width_only_ablation=False,composition64_prior_vector_comparison_complete=False,
  bridge_names=[],legal_ir_evaluate_provers=False,metric_disk_cache=False,workers_per_width=1,
  training_cache_scope='warm authenticated native vectors',native_preparation_page_cache_state='uncontrolled',
  legal_ir_bridge_evaluation_executed=False,legal_ir_target_count=None,
  encoder_context_tokens=512,decoder_output_limit_tokens=512,temperature=0,
  native_encoder_weights_updated=False,historical_8d_teacher_modified=False,model_4096d_trained=False,
  current_compiler_executed=False,logic_family_projections_executed=False,lake_executed=False,
  qualified=False,admitted=False,checkpoint_promoted=False,fresh_holdout=False,convergence_proven=False,
  formalized=False,roundtrip_ok=False)
 save(PUBLIC/'results.json',results)
 members={}
 def retain(path):
  path=Path(path)
  assert path.is_file()and not path.is_symlink(),path
  assert path.suffix in('.py','.md','.json','.jsonl','.xml','.log','.txt'),path
  assert not path.name.endswith('-state.json'),path
  assert path.stat().st_size<50000000,path
  name=path.relative_to(W).as_posix()
  record=dict(bytes=path.stat().st_size,sha256=sha(path))
  assert name not in members or members[name]==record
  members[name]=record
 for folder in('review','development','pipeline'):
  for path in sorted((R/folder).rglob('*')):
   if path.is_file()and '__pycache__'not in path.parts and path.name!='review_publication.py' and path.suffix in('.py','.md','.json','.jsonl','.xml','.log','.txt'):
    retain(path)
 for path in sorted(RUN.rglob('*')):
  if path.is_file()and '__pycache__'not in path.parts and path.suffix in('.py','.md','.json','.jsonl','.xml','.log','.txt')and not path.name.endswith('-state.json') and not ('results'in path.parts and path.name in {'source-inventory.json','training-rows.json','source-contexts.json','paraphrase-bank.json'}) and not (path.name.startswith('evaluation-') and path.name not in {'evaluation-training.json','evaluation-validation.json'}):
   retain(path)
 first=RUN.parent/'decoder-normative-wording-20261006'
 for name in('preparation-seal-failure.json','seal_preparation.py'):
  if(first/name).is_file():retain(first/name)
 for path in(R/'initial-git-and-protected-checkpoint.json',R/'build_public_evidence.py',PUBLIC/'results.json',P/'docs/autoencoders/normative_wording_training.md'):
  retain(path)
 assert sum(x['bytes']for x in members.values())<300000000
 archive=R/'review-evidence.tar.gz'
 with archive.open('xb')as output:
  with gzip.GzipFile(filename='',mode='wb',fileobj=output,mtime=0)as gz:
   with tarfile.open(fileobj=gz,mode='w|')as tar:
    for name,item in sorted(members.items()):
     path=W/name;assert sha(path)==item['sha256']and path.stat().st_size==item['bytes']
     entry=tarfile.TarInfo(name);entry.size=item['bytes'];entry.mode=0o644
     with path.open('rb')as stream:tar.addfile(entry,stream)
 assert archive.stat().st_size<75000000
 manifest=dict(schema='published-normative-wording-evidence-manifest/v1',complete=True,
  archive_repository='workspace origin/main',archive_path=archive.relative_to(W).as_posix(),
  archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),member_count=len(members),members=members,
  preparation_manifest_sha256=sha(RUN/'preparation-manifest.json'),training_manifest_sha256=sha(RUN/'training-manifest.json'),
  evaluation_manifest_sha256=sha(RUN/'evaluation-manifest.json'),private_checkpoint_tensors_bundled=False,publication_reviewer_bundled_separately=True,
  model_assets_bundled=False,predecessor_source_trees_bundled=False,local_authenticated_dependencies_required=True,
  first_preparation_seal_failure_preserved=True,first_preparation_launched=False,
  duplicated_training_input_envelopes_bundled=False,duplicated_training_input_envelopes_bound_by_manifest=True,
  original_control_panel_bodies_bundled=False,original_control_panel_digests_and_compact_metrics_bundled=True,
  source_provenance_scope='explicit authenticated historical numerical closure;not current compiler benchmark',
  qualified=False,admitted=False,checkpoint_promoted=False)
 save(PUBLIC/'manifest.json',manifest)
 save(R/'evidence-bundle-receipt.json',dict(passed=True,findings=[],archive_sha256=manifest['archive_sha256'],
  archive_bytes=manifest['archive_bytes'],member_count=len(members),private_checkpoint_tensors_bundled=False))
 print(json.dumps(dict(members=len(members),archive_bytes=archive.stat().st_size,archive_sha256=manifest['archive_sha256'])))

if __name__=='__main__':main()
