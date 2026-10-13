"""Copy reviewed merge evidence; keep private owner artifacts outside publication."""
import hashlib,json,shutil
from pathlib import Path
R=Path(__file__).resolve().parent
OUT=Path('/home/barberb/lift_coding/.worktrees/supervisor-comparison-publication-20261011/artifacts/numerical-loop-publication-20261013')
paths=['merge-input-review.json','merge-final-independent-review.json','merge-docker-evidence-audit.json','release_merge_docker.py','copy_merge_evidence.py']
paths+=json.loads((R/'merge-docker-evidence-audit.json').read_bytes())['publishable_subset']
for folder in ['merge-tests-01','merge-custody-01','merge-documentation-01']:
    paths += [folder+'/'+n for n in ['command.json','stdout','stderr','exit.json','junit.xml','result.json','gates.stdout','gates.stderr'] if (R/folder/n).is_file()]
files={}
for name in sorted(set(paths)):
    src,dst=R/name,OUT/name;assert src.is_file() and not src.is_symlink()
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    raw=dst.read_bytes();assert raw==src.read_bytes();files[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
result=dict(schema='numerical-loop-merge-publication-manifest@1',files=files,raw_bytes_unchanged=True,private_owner_state_included=False)
(OUT/'merge-evidence-manifest.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({'copied_files':len(files),'bytes':sum(v['bytes'] for v in files.values())}))
