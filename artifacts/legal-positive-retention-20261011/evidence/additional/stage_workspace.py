"""Stage the owned report/archive and actual source merge gitlink only."""
from pathlib import Path
from hashlib import sha256
import json,subprocess
F=Path(__file__).resolve().parent; W=F/'workspace'; A=W/'artifacts/legal-positive-retention-20261011'
report='implementation_plan/docs/71-positive-retention-objective-training-2026-10-11.md'
def git(*args):return subprocess.check_output(['git',*args],cwd=W)
assert git('diff','--cached','--name-only')==b''
base=git('rev-parse','HEAD').decode().strip()
pr=json.loads((F/'datasets-pr-merged.json').read_text());assert pr['state']=='MERGED'
merge=pr['mergeCommit']['oid'];assert json.loads((F/'hub-publication-review.json').read_text())['passed']
manifest=json.loads((A/'retention-manifest.json').read_text())
for p,pin in manifest['local_files'].items():
 raw=(A/p).read_bytes();assert len(raw)==pin['bytes'] and sha256(raw).hexdigest()==pin['sha256']
paths=[report,*[str(p.relative_to(W)) for p in sorted(A.rglob('*')) if p.is_file()]]
assert all(not p.is_symlink() for p in A.rglob('*'))
def links(revision):
 return {line.split('\t')[1]:line.split()[2] for line in git('ls-tree','-r',revision).decode().splitlines() if line.startswith('160000 ')}
before=links(base);assert len(before)==9
subprocess.run(['git','add','-f','--',*paths],cwd=W,check=True)
subprocess.run(['git','update-index','--cacheinfo','160000',merge,'external/ipfs_datasets'],cwd=W,check=True)
assert set(git('diff','--cached','--name-only').decode().splitlines())==set(paths)|{'external/ipfs_datasets'}
subprocess.run(['git','diff','--cached','--check'],cwd=W,check=True)
records={}
for p in paths:
 raw=(W/p).read_bytes();records[p]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
v=dict(schema='support-retention-workspace-contribution-binding/v1',base=base,source_merge_gitlink=merge,
 paths=records,other_gitlinks={p:h for p,h in before.items() if p!='external/ipfs_datasets'},
 only_owned_report_archive_and_source_gitlink_staged=True,weights_copied_to_Git=False,
 hub_revision=manifest['hub_revision'],published_files_mapped=manifest['released_file_count'])
(F/'workspace-contribution-binding.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(dict(regular_files=len(paths),source_merge_gitlink=merge,other_gitlinks_preserved=8)))
