"""Inspect by default. Apply the exact reviewed patch only on matching preimages.
No stage/commit/reset; any NS027 overlap requires a new narrow reviewed rebase.
"""
import argparse,hashlib,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def inspect(root):
 m=json.loads((HERE/'integration_manifest.json').read_text());buffers={};drift=[]
 for rel,f in m['files'].items():
  path=root/rel
  if path.resolve()!=path or sha(path.read_bytes())!=f['before_sha256']:drift.append(rel)
  candidate=HERE/f['candidate'];raw=candidate.read_bytes()
  if candidate.resolve()!=candidate or sha(raw)!=f['sha256']:raise ValueError('candidate changed: '+rel)
  buffers[rel]=raw
 return m,buffers,drift
def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args();root=a.repo.resolve();m,buffers,drift=inspect(root)
 if drift:raise SystemExit('Refusing stale preimages; preserve NS027 and rebase only reviewed hooks: '+', '.join(drift))
 profile=root/'papers/completion/neurosymbolic_supervision/experiments/production_profile.json';body=json.loads(profile.read_text());template=json.loads((HERE/'pilot_profile.template.json').read_text())
 if body.get('pilot_host_handoff')not in (None,template):raise SystemExit('Existing pilot profile differs; do not overwrite activation')
 if a.apply:
  # Source edits only. Each file has a same-directory atomic replacement.
  if inspect(root)[2]:raise SystemExit('Source changed before writes')
  body['pilot_host_handoff']=template;buffers[str(profile.relative_to(root))]=(json.dumps(body,indent=2)+'\n').encode()
  for rel,raw in buffers.items():
   path=root/rel;tmp=path.with_name(path.name+'.ns028-new')
   fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
   with os.fdopen(fd,'wb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
   os.chmod(tmp,path.stat().st_mode&0o777);os.replace(tmp,path)
 print(json.dumps({'schema':'ns028-deferred-integration/v1','applied':a.apply,'files':list(buffers),'activation':False,'grants_created':0,'provider_calls':0}))
if __name__=='__main__':main()
