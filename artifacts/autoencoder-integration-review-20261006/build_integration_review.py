"""Seal reviewed source/evidence only; no model, proof, fetch or publication."""
import hashlib,json,tarfile,xml.etree.ElementTree as ET
from pathlib import Path
import subprocess
R=Path(__file__).resolve().parent;W=R.parents[1];P=W/'external/ipfs_datasets'
def require(ok,msg):
 if not ok:raise ValueError(msg)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def info(path):
 p=Path(path);raw=p.read_bytes();return {'bytes':len(raw),'sha256':sha(raw)}
def read(p):return json.loads(Path(p).read_bytes())
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def git(repo,*args):return subprocess.check_output(['git','-c','core.hooksPath=/dev/null','-C',str(repo),*args])
def main_preimage(repo,parent,path):
 raw=git(repo,'--literal-pathspecs','ls-tree',parent,'--',path)
 if not raw:return None
 return sha(git(repo,'show',parent+':'+path))
def main():
 expectedP='5171a632c6b9f0ecb2939d29d2ad74992cbfeb11';expectedW='3b0162bebe0b7a09727081cb8c5f5c15378caba1'
 independent=['findings/progress-final-review-r3.json','findings/progress-doc-fact-review-r3.json','findings/additive-wrapper-and-raw-compile-source-audit.json','findings/effective-tree-owner-source-audit.json']
 bound={}
 def bind(path):bound[str(Path(path).resolve())]=info(path)
 for name in independent:
  value=read(R/name);require(not value.get('findings'),'independent findings unresolved')
  for check in value.get('checks',[]):
   if isinstance(check,dict):require(check.get('passed') is True,'independent check failed')
  for item in value.get('sources',[]):
   require(info(item['path'])=={k:item[k] for k in ('bytes','sha256')},'reviewed source changed')
   bind(item['path'])
  for key in ('documentation_review','source_review','read_only_owner_review'):
   if key in value:
    item=value[key];require(info(item['path'])=={k:item[k] for k in ('bytes','sha256')},'independent child review changed')
  bind(R/name)
 candidateP=read(R/'branches/combined-owned-source-scope.json');require(len(candidateP['paths'])==31,'restored source scope count')
 pathsP=[x['path'] for x in candidateP['paths']]
 for x in candidateP['paths']:require(info(P/x['path'])=={k:x[k] for k in ('bytes','sha256')},'restored source bytes changed')
 pathsP+=['docs/autoencoders/four_width_training.md','docs/autoencoders/README.md','docs/autoencoders/progress_integration.md']
 recovery=read(R/'pipeline/recovery-candidates.json')
 pathsW=[]
 for group in ('historical_recovery','uncommitted_publication_recovery','owned_recovery_documentation'):
  for item in recovery[group]:
   require(info(W/item['path'])=={'bytes':item['source_bytes'],'sha256':item['source_sha256']},'recovery bytes changed')
   pathsW.append(item['path'])
 for item in recovery['owned_current_source_repairs']:
  require(info(W/item['path'])=={'bytes':item['source_bytes_after'],'sha256':item['source_sha256_after']},'raw compile source repair changed')
  pathsW.append(item['path'])
 pathsW+=['scripts/review_autoencoder_progress.py','tests/test_review_autoencoder_progress.py','implementation_plan/docs/58-autoencoder-progress-integration-2026-10-06.md']
 tests=[]
 for root,filename,count in [(R/'branches','profile-canonical-tests-r1.xml',129),(R/'branches','ir-wrapper-canonical-tests-r1.xml',774),(R/'branches','checkpoint-hub-existing-tests-r1.xml',25),(R,'canonical-semantic-gates.xml',17),(R,'progress-tool-tests.xml',9)]:
  p=root/filename;x=ET.parse(p).getroot();s=[x] if x.tag=='testsuite' else list(x)
  require(sum(int(a.attrib['tests']) for a in s)==count,'test count differs')
  require(all(int(a.get(k,'0'))==0 for a in s for k in ('failures','errors','skipped')),'targeted tests unsuccessful')
  tests.append({'path':str(p.relative_to(W)),'tests':count,**info(p)});bind(p)
 require(read(R/'pipeline/raw-lean-probe-tests-r2.json')['test_count']==13 and read(R/'pipeline/raw-lean-probe-tests-r2.json')['exit_code']==0,'raw compile mocked tests failed')
 require(all(x['exit_code']==0 for x in read(R/'pipeline/main-overlay-validation.json')['results']),'historical replay failed')
 require(read(R/'pipeline/source-evidence-review.json')['pure_test_counts']['accounting']==30,'historical test count')
 require(read(R/'pipeline/source-evidence-review.json')['pure_test_counts']['all_weights']==22,'publication pure test count')
 for path in pathsP:bind(P/path)
 for path in pathsW:bind(W/path)
 for n in ('branches/combined-owned-source-scope.json','branches/test-receipts.json','pipeline/recovery-candidates.json','pipeline/source-evidence-review.json','pipeline/main-overlay-validation.json','pipeline/raw-lean-probe-tests-r2.json'):bind(R/n)
 initial=read(R/'workspace-initial-inventory.json');pi=read(R/'datasets-initial-inventory.json')
 summary=dict(schema='cross-agent-autoencoder-integration-summary/v1',date='2026-10-06',reviewed_remote_heads={'workspace':expectedW,'datasets':expectedP},inventory={'workspace_refs':len(initial['refs']),'workspace_worktrees':len(initial['worktrees']),'datasets_refs':len(pi['refs']),'datasets_worktrees':len(pi['worktrees'])},findings_matrix=info(R/'findings/evidence-matrix.json'),datasets_recovered_paths=31,datasets_documentation_paths=3,workspace_historical_recovery_paths=23,workspace_publication_recovery_paths=12,workspace_recovered_evidence_bytes=recovery['historical_total_bytes']+recovery['uncommitted_total_bytes'],validation={'pytest_tests':tests,'additional_mocked_probe_tests':13,'historical_accounting_tests':30,'publication_pure_tests':22,'table_hash_replays':3,'total_targeted_unique_tests':1019},remaining_owner_review='Retained snapshot.py ancestor-witness/physical-byte changes require a separate owner comparison; current implementation preserved. Broad semantic corpus/family qualification remains open.',model_training_executed=False,model_forward_executed=False,encoder_executed=False,weights_downloaded=False,Hub_transfer_executed=False,lake_executed=False,qualification_granted=False,checkpoint_promoted=False,constitution_formalized=False)
 save(R/'review-summary.json',summary);bind(R/'review-summary.json')
 # Keep all bounded review attempts, including failures, without bundling source
 # mirrors, external model assets, giant unrelated worktree status or caches.
 archive_inputs=[]
 for folder in ('branches','pipeline','findings'):
  archive_inputs.extend(p for p in (R/folder).iterdir() if p.is_file())
 rootnames=['datasets-fetched-refs.json','workspace-fetched-refs.json','documentation-preimages.json','our-published-progress-preservation.json','canonical-semantic-gates.log','canonical-semantic-gates.xml','progress-tool-tests.log','progress-tool-tests.xml','retained-paraphrase-check.json','missing-source-before-recovery.json','publish_integration.py','build_integration_review.py','review-summary.json']
 archive_inputs.extend(R/x for x in rootnames)
 require(sum(p.stat().st_size for p in archive_inputs)<40_000_000,'bounded review archive exceeded40MB')
 members={str(p.relative_to(R)):info(p) for p in archive_inputs}
 archive=R/'review-evidence.tar.gz';require(not archive.exists(),'fresh archive required')
 with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
  for name in sorted(members):
   p=R/name;require(info(p)==members[name],'review artifact changed while archiving');item=tarfile.TarInfo(name);item.size=members[name]['bytes'];item.mode=0o644;item.mtime=0
   with p.open('rb') as stream:tar.addfile(item,stream)
 with tarfile.open(archive,'r:gz') as tar:
  require({m.name for m in tar.getmembers()}==set(members),'archive member inventory mismatch')
  for m in tar.getmembers():require(m.isfile() and info_bytes(tar.extractfile(m).read())==members[m.name],'archive member bytes mismatch')
 require(all(info(R/name)==value for name,value in members.items()),'review inputs changed during archive')
 save(R/'review-evidence-manifest.json',dict(schema='bounded-autoencoder-integration-review-archive/v1',archive=info(archive),members=members,original_private_artifacts_preserved=True,excluded=['giant unrelated workspace status','private isolated source mirrors','caches','external weights and binaries'],models_or_native_proofs_executed=False))
 readiness=dict(schema='root-saved-review-integration-readiness/v1',passed=True,findings=[],artifacts=bound,independent_review_used=True,qualification_granted=False,semantic_fidelity_measured_this_review=False)
 save(R/'publication-review.json',readiness)
 public=['review-summary.json','review-evidence.tar.gz','review-evidence-manifest.json','findings/README.md','findings/evidence-matrix.json','findings/published-scalars.json','findings/duplicate-publications.json','branches/branch-review-summary.json','branches/branch-review-summary.md','branches/combined-owned-source-scope.json','pipeline/recovery-candidates.json','pipeline/integration-review.json','publication-review.json','publish_integration.py','build_integration_review.py']
 pathsW += [str((R/x).relative_to(W)) for x in public]
 def selection(repo,parent,paths):
  require(len(paths)==len(set(paths)),'duplicate selection')
  return {'parent':parent,'files':{path:{**info(repo/path),'parent_sha256':main_preimage(repo,parent,path),'mode':'100644'} for path in sorted(paths)}}
 scope=dict(schema='reviewed-autoencoder-integration-publication/v1',passed=True,reviewed=True,required_reviews=['publication-review.json','pipeline/publisher-code-independent-review.json','pipeline/publication-scope-independent-review.json'],datasets=selection(P,expectedP,pathsP),workspace=selection(W,expectedW,pathsW),new_model_or_training_runs=0,new_weights_downloaded=0,only_gitlink_updated='external/ipfs_datasets')
 save(R/'publication-scope.json',scope)
 print(json.dumps({'datasets_paths':len(pathsP),'workspace_paths':len(pathsW),'archive_bytes':archive.stat().st_size,'unique_targeted_tests':1019,'ready_for_exact_scope_independent_review':True}))
def info_bytes(raw):return {'bytes':len(raw),'sha256':sha(raw)}
if __name__=='__main__':main()
