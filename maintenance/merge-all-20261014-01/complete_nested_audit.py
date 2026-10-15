import json, os, subprocess, configparser, collections, datetime, gzip
from pathlib import Path
ROOT='/home/barberb/lift_coding'; OUT=ROOT+'/maintenance/merge-all-20261014-01/nested-repository-audit.json'
d=json.load(open(OUT)); prim=d['primary_comparison_targets']; cache={}
def git(g,*a,ok=False):
 p=subprocess.run(['git','--git-dir='+g,'--work-tree='+ROOT,*a],cwd='/tmp',text=True,capture_output=True,timeout=25)
 if p.returncode and not ok: raise RuntimeError(p.stderr[:800])
 return p

def contained(g,s,b):
 key=(g,s,b)
 if key not in cache: cache[key]=git(g,'merge-base','--is-ancestor',s,b,ok=True).returncode==0
 return cache[key]
def cfg(g):
 c=configparser.ConfigParser(interpolation=None,strict=False); c.read(g+'/config'); return c

def origin(c):
 u=c.get('remote "origin"','url',fallback=''); u=u.removeprefix('https://').removeprefix('http://').removeprefix('git@').replace('github.com:','github.com/'); return u.removesuffix('.git')

def inspect(g):
 c=cfg(g); row={'git_dir':g,'origin':origin(c)}
 refs=[]
 for line in git(g,'for-each-ref','--format=%(refname)%09%(objectname)%09%(upstream:short)%09%(committerdate:iso8601)%09%(subject)','refs/heads','refs/remotes/origin/main','refs/remotes/origin/master','refs/remotes/origin/HEAD').stdout.splitlines():
  vals=line.split('\t',4); refs.append(dict(zip(('ref','sha','upstream','date','subject'),vals)))
 baseline=next((r for n in ('main','master','HEAD') for r in refs if r['ref']=='refs/remotes/origin/'+n),None); row['cached_default']=baseline
 groups={}
 for r in refs:
  if r['ref'].startswith('refs/heads/'):groups.setdefault(r['sha'],{'sha':r['sha'],'branches':[],'worktrees':[]})['branches'].append(r)
 worktrees=[]; w={}
 for line in git(g,'worktree','list','--porcelain').stdout.splitlines()+['']:
  if not line:
   if w:worktrees.append(w);w={}
  else:
   k,_,v=line.partition(' ');w[k]=v
 for w in worktrees:
  if w.get('HEAD'):groups.setdefault(w['HEAD'],{'sha':w['HEAD'],'branches':[],'worktrees':[]})['worktrees'].append(w)
 for h in groups.values():
  s=h['sha']; h['contained_in_cached_origin']=bool(baseline and contained(g,s,baseline['sha'])); h['primary_comparison']=None
  p=prim.get(row['origin'])
  if not h['contained_in_cached_origin'] and p:
   if git(p['git_dir'],'cat-file','-e',s+'^{commit}',ok=True).returncode==0:
    h['primary_comparison']={'basis':'head object already present in primary repository','target':p['candidate'],'contained':contained(p['git_dir'],s,p['candidate'])}
   elif git(g,'cat-file','-e',p['candidate']+'^{commit}',ok=True).returncode==0:
    h['primary_comparison']={'basis':'candidate object already present in nested repository','target':p['candidate'],'contained':contained(g,s,p['candidate'])}
  if h['contained_in_cached_origin']:h['classification']='contained_in_cached_origin'
  elif (h.get('primary_comparison') or {}).get('contained'):h['classification']='represented_in_primary_candidate'
  elif not h['branches']:h['classification']='detached_dependency_pin_not_assumed_new_work'
  else:h['classification']='ahead_or_diverged_from_cached_origin'
 row['heads']=list(groups.values()); return row
fixed=0
for idx,r in enumerate(d['repositories']):
 g=r['git_dir']
 if r.get('error'):
  try:r=inspect(g);d['repositories'][idx]=r;fixed+=1
  except Exception as e:r['retry_error']=str(e)
 c=cfg(g);cw=c.get('core','worktree',fallback=None);r['configured_core_worktree']=cw;r['configured_worktree_resolved']=os.path.normpath(os.path.join(g,cw)) if cw else None
 r['metadata_command_worktree_override']=ROOT
 if (idx+1)%100==0:print('metadata checked',idx+1,flush=True)
# Read only history tree hashes; no blob materialization.
history={}
for o,p in prim.items():
 hm=collections.defaultdict(list)
 for line in git(p['git_dir'],'log','--format=%H %T',p['candidate']).stdout.splitlines():
  s,t=line.split();hm[t].append(s)
 history[o]=hm
# Same-origin smaller repo cached default history is also useful for archive equivalence.
for r in d['repositories']:
 o=r.get('origin');b=r.get('cached_default')
 if o and o not in history and b:
  hm=collections.defaultdict(list)
  for line in git(r['git_dir'],'log','--format=%H %T',b['sha']).stdout.splitlines():
   s,t=line.split();hm[t].append(s)
  history[o]=hm
outstanding=[]; errors=[]
for r in d['repositories']:
 if r.get('error'):errors.append({'git_dir':r['git_dir'],'error':r.get('retry_error',r['error'])});continue
 g=r['git_dir'];o=r['origin'];b=r.get('cached_default');p=prim.get(o)
 for h in r['heads']:
  if h['classification']!='ahead_or_diverged_from_cached_origin':continue
  s=h['sha']; meta=git(g,'show','-s','--format=%T%n%ci%n%s',s).stdout.splitlines();t=meta[0];h['tree']=t;h['date']=meta[1];h['subject']=meta[2]
  base=git(g,'merge-base',s,b['sha'],ok=True).stdout.strip() if b else ''
  h['merge_base']=base or None
  raw=git(g,'diff-tree','-r','--raw','--no-renames',base or s+'^',s,ok=True).stdout.splitlines()
  changes=[]
  for line in raw:
   if not line.startswith(':') or '\t' not in line:continue
   modes,path=line.split('\t',1);oldmode,newmode,oldblob,newblob,status=modes[1:].split();changes.append({'path':path,'old_mode':oldmode,'new_mode':newmode,'old_blob':oldblob,'new_blob':newblob,'status':status})
  h['material_changes']=changes;h['changed_path_count']=len(changes)
  equiv=history.get(o,{}).get(t,[])
  if equiv:
   h['audit_disposition']='tree_equivalent_to_published_history';h['equivalent_published_commits']=equiv[:3]
  elif t=='4b825dc642cb6eb9a060e54bf8d69288fbee4904b':h['audit_disposition']='empty_tree_retained_snapshot_do_not_merge'
  elif not changes:h['audit_disposition']='history_only_no_source_delta'
  elif all(x['old_mode'] in ('160000','000000') and x['new_mode'] in ('160000','000000') for x in changes):h['audit_disposition']='historical_gitlink_only_update_no_source_delta'
  elif s.startswith('4b9767c092f3'):h['audit_disposition']='active_post_cutoff_work_preserved'
  elif any(x['ref'].startswith('refs/heads/publication/wip-20261004/') for x in h.get('branches',[])):h['audit_disposition']='retained_source_snapshot_requires_review'
  else:h['audit_disposition']='local_source_delta_requires_review'
  # Compare changed path final blobs against known primary frozen candidate; hash only.
  if p and h['audit_disposition'] not in ('tree_equivalent_to_published_history','historical_gitlink_only_update_no_source_delta','history_only_no_source_delta'):
   match=0;delta=[]
   for ch in changes:
    if ch['new_mode']=='160000':continue
    cur=git(p['git_dir'],'ls-tree',p['candidate'],'--',ch['path']).stdout.strip();cb=cur.split()[2] if cur else None
    if (cb or '0'*40)==ch['new_blob']:match+=1
    else:delta.append({'path':ch['path'],'branch_blob':ch['new_blob'],'candidate_blob':cb})
   h['changed_paths_already_equal_primary']=match;h['changed_paths_differing_primary']=delta
   if match and not delta:h['audit_disposition']='all_changed_source_blobs_equal_primary_candidate'
  outstanding.append({'git_dir':g,'origin':o,**h})
summary={'repositories':len(d['repositories']),'read_errors':len(errors),'broken_worktree_metadata_reads_recovered':fixed,'local_branch_refs':sum(len(h.get('branches',[])) for r in d['repositories'] for h in r.get('heads',[])),'registered_worktree_records':sum(len(h.get('worktrees',[])) for r in d['repositories'] for h in r.get('heads',[])),'distinct_origin_head_pairs':len({(r.get('origin'),h['sha']) for r in d['repositories'] for h in r.get('heads',[])}),'classification_counts':dict(collections.Counter(h['classification'] for r in d['repositories'] for h in r.get('heads',[]))),'outstanding_disposition_counts':dict(collections.Counter(h['audit_disposition'] for h in outstanding))}
d['summary']=summary;d['completed_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();d['notes']+=['Explicit --work-tree override repairs broken core.worktree metadata access without editing Git config.','Registered worktree paths from git worktree list include the artificial main-worktree override; configured_worktree_resolved records the original source path.','No fetches, merges, pushes, tests, ref changes, or source changes were performed.']
with gzip.open(OUT+'.full.json.gz','wt') as f:json.dump(d,f)
compact=[]
for r in d['repositories']:
 compact.append({k:v for k,v in r.items() if k!='heads'}|{'local_branch_ref_count':sum(len(h.get('branches',[])) for h in r.get('heads',[])),'worktree_record_count':sum(len(h.get('worktrees',[])) for h in r.get('heads',[])),'distinct_head_count':len(r.get('heads',[])),'classification_counts':dict(collections.Counter(h['classification'] for h in r.get('heads',[])))})
for h in outstanding:
 h['branch_count']=len(h.get('branches',[]));h['branch_refs']=[x['ref'] for x in h.pop('branches',[])][:8];h['worktree_count']=len(h.get('worktrees',[]));h['worktree_paths']=[x.get('worktree') for x in h.pop('worktrees',[])][:4]
 h.pop('material_changed_paths',None);h.pop('tip_metadata',None)
 # Avoid repeated huge path details; full exact evidence remains compressed.
 if len(h.get('material_changes',[]))>15:h['material_changes_sample']=h.pop('material_changes')[:15]
 if len(h.get('changed_paths_differing_primary',[]))>15:h['changed_paths_differing_primary_count']=len(h['changed_paths_differing_primary']);h['changed_paths_differing_primary_sample']=h.pop('changed_paths_differing_primary')[:15]
final={k:v for k,v in d.items() if k!='repositories'};final.update(repositories=compact,outstanding_heads=outstanding,errors=errors,full_evidence_gzip=OUT+'.full.json.gz')
json.dump(final,open(OUT,'w'),indent=2);print(json.dumps(summary),flush=True)
