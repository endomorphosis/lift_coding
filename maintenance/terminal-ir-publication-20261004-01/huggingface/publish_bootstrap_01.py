from pathlib import Path
import hashlib,io,json,time
from huggingface_hub import HfApi,CommitOperationAdd
ROOT=Path('/home/barberb/lift_coding');OUT=Path(__file__).resolve().parent/'bootstrap-01';OUT.mkdir(exist_ok=False)
repo='Publicus/codebase-ir-proof-index';prefix='releases/20261004-terminal-codebase-ir-evidence-v1'
sealroot=ROOT/'artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-requirement-grounding-20261004-01/final-retention-01'
expected={'seal.json':'57cc54ea656ddb991cf9d3b0b72605c843f053b784f88ad0b3fa9da3404d5c1e','verification/readback.json':'46fd3fc73d2505fe11afb770ef982332bf1f350333e36a1a01ed4560d11364a1','verification/final-closure.json':'072b462746e6c6dcd23fb08de712b755c74576b41e57c203b017c31f550082d1'}
files={};bindings=[]
for name,digest in expected.items():
 path=sealroot/name;raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
 remote=prefix+'/latest-grounding-retention/'+name;files[remote]=raw;bindings.append({'path':remote,'bytes':len(raw),'sha256':digest})
card='''---
pretty_name: CodebaseIR repository proof evidence
tags:
- codebase-ir
- terminal-bench
- symbolic-planning
- lean
- proof-cache
---
# CodebaseIR repository proof evidence

This dataset retains repository scans, source snapshots, AST/KG/vector metadata, formalization candidates, scoped Lean checks, training receipts and proof-cache research evidence for the IPFS agent supervisor.

The release is indexed under `releases/20261004-terminal-codebase-ir-evidence-v1`. The bootstrap includes sealed requirement-grounding manifests. Bulk archive preparation is in progress; its final content-addressed manifest will state captured paths, source drift, exclusions and qualification limits.

A compiled finite model is evidence for its stated model and assumptions. It does not establish whole-source equivalence, full Terminal Bench task satisfaction, global autoencoder convergence or permission for supervisor execution. Existing production activation criteria remain open.

Source licenses and provenance remain associated with their original repositories and captured files. No new blanket license or model activation is asserted here.
'''
files['README.md']=card.encode()
status={'schema':'terminal-ir-publication-status@1','status':'sealed_grounding_bootstrap_published_bulk_preparing','release_prefix':prefix,'github':{'ipfs_accelerate':'a601b87e9e6bceb42f925cb085203ea337d204a5','ipfs_datasets':'a3e7ea91cfbbf2e68d68b1362e0a22690cb09d97','ipfs_kit':'8ac00bb1974b1378e12091d546d8425af34049e0','JevOps':'9af1ebb6a4245ce2b4e673ac277e4988da4d5caa'},'sealed_proof_manifests':bindings,'whole_source_equivalence_proved':False,'full_task_satisfaction_proved':False,'model_convergence_proved':False,'activation_criteria_open':32,'bulk_archive_publication_complete':False}
files[prefix+'/publication-status.json']=(json.dumps(status,sort_keys=True,indent=2)+'\n').encode()
api=HfApi();started=time.monotonic();api.create_repo(repo_id=repo,repo_type='dataset',private=False,exist_ok=True)
info=api.repo_info(repo_id=repo,repo_type='dataset');parent=info.sha
# This first-write path must never silently overwrite an existing different release.
existing={r.path for r in api.list_repo_tree(repo,repo_type='dataset',revision=parent,recursive=True)}
for name in files:
 assert name not in existing, 'bootstrap path unexpectedly already exists: '+name
commit=api.create_commit(repo_id=repo,repo_type='dataset',parent_commit=parent,commit_message='Publish sealed CodebaseIR proof provenance and archive status',operations=[CommitOperationAdd(path_in_repo=name,path_or_fileobj=io.BytesIO(raw)) for name,raw in sorted(files.items())])
verified=[]
from huggingface_hub import hf_hub_download
for name,raw in sorted(files.items()):
 remote=Path(hf_hub_download(repo_id=repo,repo_type='dataset',filename=name,revision=commit.oid));got=remote.read_bytes();assert got==raw
 verified.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
receipt={'schema':'terminal-ir-hf-bootstrap-publication@1','repo_id':repo,'repo_type':'dataset','parent':parent,'commit':commit.oid,'commit_url':commit.commit_url,'files':verified,'readback_verified':True,'bulk_archive_complete':False,'elapsed_seconds':time.monotonic()-started}
(OUT/'closed.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
