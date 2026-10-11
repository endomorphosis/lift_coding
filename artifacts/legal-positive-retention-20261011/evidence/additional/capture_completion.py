"""Capture completion evidence and protect canonical checkout HEAD/index identities."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,subprocess
F=Path(__file__).resolve().parent
C=Path('/home/barberb/lift_coding')
def load(n):return json.loads((F/n).read_text())
def pin(n):
 p=F/n;b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha256(b).hexdigest())
original=load('intake.json')['canonical'];canonical={}
for label,root in [('workspace',C),('datasets',C/'external/ipfs_datasets')]:
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
 index=Path(subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-path','index'],cwd=root,text=True).strip())
 record=dict(head=head,index_sha256=sha256(index.read_bytes()).hexdigest())
 assert record=={k:original[label][k] for k in record}
 canonical[label]=record
reviews=['source-staged-review.json','workspace-staged-review.json','model-selector-review.json','independent-corpus-review.json','protocol-review.json','results-resource-review.json','publication-preflight-review.json','hub-recovery-source-review.json','hub-publication-review.json','archive-source-review.json','report-generator-review.json','datasets-merged-preservation.json','workspace-merged-preservation.json']
for name in reviews:
 d=load(name)
 if name=='model-selector-review.json':
  assert d['verdict']=='pass_static_model_and_selector_review_with_bound_primary_test_receipts' and d['findings']==[]
 else:assert d['passed'] is True
for name in ['datasets-pr-merged.json','workspace-pr-merged.json']:assert load(name)['state']=='MERGED'
assert load('selected-checkpoint-replay.json')['complete_outputs_exact']==1280
assert load('hub-checkpoint-replay.json')['complete_outputs_exact']==1280
assert load('hub-upload-batch-recovery.json')['passed'] is True
assert load('workspace-archive-build.json')['raw_checkpoint_files_copied']==0
receipt_names=reviews+['validation.json','hub-upload-commit.json','hub-readback-verification.json','hub-all-checkpoint-downloads.json','hub-checkpoint-replay.json','selected-checkpoint-replay.json','hub-upload-error.json','hub-upload-reconciliation.json','hub-upload-batch-recovery.json','datasets-pr-merged.json','workspace-pr-merged.json','datasets-hosted-ci.json','workspace-hosted-ci.json','workspace-archive-build.json','source-contribution-binding.json','workspace-contribution-binding.json','workspace-latest-integration.json']
v=dict(schema='support-retention-integrated-completion/v1',observed_at_utc=datetime.now(timezone.utc).isoformat(),passed=True,findings=[],canonical_HEAD_and_index_unchanged=True,canonical=canonical,source_PR=load('datasets-pr-merged.json')['url'],workspace_PR=load('workspace-pr-merged.json')['url'],Hub_revision=load('hub-upload-commit.json')['revision'],current_local_tests=179,actual_optimizer_updates=480,encoded_source_presentations=7680,selected_updates={'bce':0,'positive_margin':0},selected_fitted_gain=False,selected_local_complete_outputs_exact=1280,selected_Hub_complete_outputs_exact=1280,formal_output=None,admission_masks='all five zero',default_promotion=False,source_only=True,latent_conditioned=False,legal_gold=False,native_runtime_qualified=False,remaining_work=['authentic native 8D/384D/768D conditioning beyond the fixed native assay','independently reviewed US Code source-context targets','broader logic-family reconstruction and lake build legal','fresh excluded-case support experiment with fixed selection policy'],evidence=[pin(n) for n in receipt_names],hosted_CI={label:{k:load(label+'-hosted-ci.json')[k] for k in ['availability','claim_passed']} for label in ['datasets','workspace']})
p=F/'completion.json'
with p.open('x') as h:json.dump(v,h,indent=2);h.write('\n')
print(json.dumps({k:v[k] for k in ['passed','source_PR','workspace_PR','Hub_revision','canonical_HEAD_and_index_unchanged','hosted_CI']}))
