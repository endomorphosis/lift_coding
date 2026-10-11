"""Authenticate both contributed merge trees and live-main preservation."""
from pathlib import Path
from hashlib import sha256
import json,subprocess
F=Path(__file__).resolve().parent
def git(root,*args):return subprocess.check_output(['git',*args],cwd=root)
def verify(label,root,binding_name,pr_name):
 b=json.loads((F/binding_name).read_text());pr=json.loads((F/pr_name).read_text());assert pr['state']=='MERGED'
 merge=pr['mergeCommit']['oid'];ref='refs/remotes/legal-decoder-progress-20261011-01/main'
 subprocess.run(['git','-c','gc.auto=0','fetch','--no-tags','--no-write-fetch-head','--no-auto-maintenance','origin','main:'+ref],cwd=root,check=True)
 live=git(root,'rev-parse',ref).decode().strip();subprocess.run(['git','merge-base','--is-ancestor',merge,live],cwd=root,check=True)
 parent=git(root,'rev-parse',merge+'^1').decode().strip()
 expected=set(b['paths'])|({'external/ipfs_datasets'} if label=='workspace' else set())
 assert set(git(root,'diff','--name-only',parent,merge).decode().splitlines())==expected
 for rev in (merge,live):
  for path,record in b['paths'].items():
   raw=git(root,'show',rev+':'+path);assert len(raw)==record['bytes'] and sha256(raw).hexdigest()==record['sha256'],(rev,path)
 if label=='workspace':
  def links(rev):return {line.split('\t')[1]:line.split()[2] for line in git(root,'ls-tree','-r',rev).decode().splitlines() if line.startswith('160000 ')}
  actual=links(merge);assert actual['external/ipfs_datasets']==b['source_merge_gitlink']
  assert {p:h for p,h in actual.items() if p!='external/ipfs_datasets'}==b['other_gitlinks']
 v=dict(schema='support-retention-'+label+'-merged-preservation/v1',passed=True,findings=[],
   contributed_merge=merge,merge_first_parent=parent,live_main=live,merge_ancestor_of_live_main=True,
   only_owned_paths_changed_from_actual_first_parent=True,all_contributions_byte_exact_on_merge_and_live_main=True,
   unrelated_first_parent_tree_entries_preserved=True,paths=b['paths'])
 (F/(label+'-merged-preservation.json')).write_text(json.dumps(v,indent=2)+'\n')
 print(json.dumps(dict(repo=label,merge=merge,live=live,files=len(b['paths']),passed=True)))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['datasets','workspace'],required=True);a=p.parse_args()
 verify(a.phase,F/('datasets' if a.phase=='datasets' else 'workspace'),
  'source-contribution-binding.json' if a.phase=='datasets' else 'workspace-contribution-binding.json',
  'datasets-pr-merged.json' if a.phase=='datasets' else 'workspace-pr-merged.json')
