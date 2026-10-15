"""Seal explicitly named public artifacts; never scan private fixture/model state."""
import hashlib
import json
from pathlib import Path
G=Path(__file__).parent
names=[
 'change-scope.json','baseline-manifest.json','prior-evidence-baseline.json','source-manifest.json','changes.patch',
 'validation-summary.json','codec-delivery-validation.json','legacy-codec-replay-final.json',
 'control-wire-final-validation.json','runner-wire-review.json','materialized-probe-independent-review.json',
 'source-patch-independent-review.json','source-runtime-independent-review.json',
 'probe-adaptation-review.json','owned-validation-review.json','unit-audit-comparison-03/receipt.json',
 'codec-delivery-validation-01.xml','codec-delivery-followup-01.xml','runner-validation-01.xml',
 'runner-validation-02.xml','control-wire-frozen-tests.xml','unit-audit-comparison-03/tests.xml',
 'unit-audit-comparison-01/receipt.json','unit-audit-focused-02/receipt.json',
 'build-pinned-runtime-v14.py','verify-runtime-delta.py','prepare-source-review.py','summarize-validation.py','summarize-result.py',
 'materialized-worker-probe.py','installed-full-audit-probe.py','qualify-installed-runtime.py',
 'runtime-archive-v14/manifest.json','runtime-archive-verification-v14.json','runtime-delta.json',
 'installed-qualification-01/qualification.json','installed-qualification-independent-review.json',
 'next-work.json','result-summary.json','seal-evidence.py']

def sha(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
source=json.loads((G/'source-manifest.json').read_text())
checkout=Path(source['checkout'])
for row in source['files']:
 path=checkout/row['path'];assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
prior=json.loads((G/'prior-evidence-baseline.json').read_text())
for row in prior['files']:
 path=Path(row['path']);assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
records=[]
for name in names:
 path=G/name
 assert path.is_file() and not path.is_symlink(),name
 records.append({'path':name,'sha256':sha(path),'bytes':path.stat().st_size})
receipt={'schema':'materialized-wire-public-evidence-manifest@1',
 'enumeration':'Explicit public allowlist; no recursive file hashing or private fixture/database/model-transcript scanning.',
 'files':records,'all_19_source_hashes_match':True,'prior_91_explicit_public_artifacts_preserved':True,
 'provider_model_calls_in_this_stage':0,'whole_repository_test_pass_claimed':False,
 'original_dirty_checkout_or_git_index_mutated_by_this_work':False,
 'github_or_huggingface_publication_performed':False,
 'raw_model_rollouts_hidden_verifier_content_credentials_private_keys_and_databases_excluded':True,
 'token_savings_or_general_semantic_equivalence_convergence_claimed':False}
(G/'evidence-manifest.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'sealed_public_files':len(records),'prior_artifacts_preserved':len(prior['files']),
 'source_files_verified':len(source['files']), 'evidence_manifest_sha256':sha(G/'evidence-manifest.json')}),flush=True)
