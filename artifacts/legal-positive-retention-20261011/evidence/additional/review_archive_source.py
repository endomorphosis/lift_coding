"""Root data-only review of the frozen archive helper and recovered publication guard."""
from pathlib import Path
from hashlib import sha256
import ast,json,importlib.util
F=Path(__file__).resolve().parent
p=F/'prepare_workspace_archive.py';raw=p.read_bytes()
build=json.loads((F/'archive-helper-build.json').read_text());pin=dict(path=str(p),bytes=len(raw),sha256=sha256(raw).hexdigest());assert build['helper']==pin
allowed={'__future__','argparse','hashlib','json','os','pathlib','re','urllib.parse'}
tree=ast.parse(raw);imports={n.module if isinstance(n,ast.ImportFrom) else a.name for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom)) for a in (n.names if isinstance(n,ast.Import) else [None])};assert imports<=allowed
spec=importlib.util.spec_from_file_location('retention_archive_read_only_review',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
manifest_path=F/'release/release-manifest.json';manifest=m.read_json(manifest_path)
declared={name:{k:record[k] for k in ['bytes','sha256']} for name,record in manifest['files'].items()};declared['release-manifest.json']=m.byte_pin(manifest_path.read_bytes())
weights={'inputs/parent-checkpoint.json'}|{'checkpoints/'+arm+'/checkpoint-'+str(step)+'.json' for arm in ['bce','positive_margin'] for step in [0,120,240]}|{'checkpoints/'+arm+'/checkpoint.json' for arm in ['bce','positive_margin']}
accepted=[];denied=[]
for name in sorted(declared):
 try:b=m.checked_copy_bytes(F/'release'/name)
 except ValueError:
  assert name in weights;denied.append(name)
 else:
  assert name not in weights and m.byte_pin(b)==declared[name];accepted.append(name)
assert len(accepted)==302 and len(denied)==9
commit=m.read_json(F/'hub-upload-commit.json');pub=m.read_json(F/'hub-publication-review.json')
recovery=m.require_recovered_error(F,declared,manifest_path,commit,pub);assert recovery['original_error_preserved_and_resolved']
supplements=set(m.EXTRA_REQUIRED)|set(m.RECOVERY_FILES)|{'hub-upload-parent.json','hub-upload-proposal.json','hub-upload-commit.json','hub-readback-verification.json','hub-all-checkpoint-downloads.json','hub-checkpoint-replay.json','hub-publication-review.json','report-generator-review.json','source-staged-review.json','source-contribution-binding.json','datasets-pr-merged.json','datasets-merged-preservation.json','datasets-hosted-ci.json','stage_source.py','stage_workspace.py','capture_hosted_ci.py','verify_merged_contributions.py','capture_completion.py'}
for name in sorted(supplements):m.checked_copy_bytes(F/name)
old=F/'archive-source-review.json';archive=F/'archive-source-review-draft-02.json';assert not archive.exists();archive.write_bytes(old.read_bytes())
v=dict(schema='support-retention-workspace-archiver-source-review/v1',passed=True,findings=[],reviewer='root; independent of helper author',helper=pin,manifest_sha256=sha256(manifest_path.read_bytes()).hexdigest(),guard_nonweight_payloads_accepted=len(accepted),guard_raw_containers_denied=len(denied),supplementary_guard_payloads_accepted=len(supplements),manifest_self_separately_bound=True,metadata_only_schema_not_treated_as_rawweights=True,recovered_error_authenticated=recovery,controls=['all311 published files fully mapped','9 raw containers Hub only;302 nonweights local','results/resource/preflight/publication/local+Hub1280 replay required','all original/release/Hub byte bindings','safe isolated bounded paths, symlink/credential/privateledger denial','supplement authentication before new archive creation','no Git/Hub/numerical calls','completed30commit60event recovery and original failure byte-bound to independent actual publication review'],helper_imported_for_data_only_copy_guard=True,archiver_prepare_or_main_executed=False,models_or_tests_or_Git_or_Hub_executed_by_reviewer=False,archive_execution_pending=True)
old.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(dict(passed=True,helper=pin,nonweights=len(accepted),weights_denied=len(denied),supplements=len(supplements))))
