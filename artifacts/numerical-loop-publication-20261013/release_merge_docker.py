"""Pin the merged owner/source-policy dependencies for a fresh offline replay."""
import hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent
P=Path('/home/barberb/lift_coding/.worktrees/supervisor-comparison-contracts-20261011')
previous='65cf6a24650213a4607d935a66513c53b3582a87';merged='e1c410bcbd7651c31fca84beb82e3ef2fe9ac836'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip()==merged
old=json.loads((R/'docker-release-03.json').read_bytes());paths=set(old['source_bindings'])
changed=subprocess.check_output(['git','diff','--name-only',previous,merged],cwd=P,text=True).splitlines()
added=[p for p in changed if p.endswith('.py') and not p.startswith(('docs/','test/')) and not Path(p).name.startswith('test_')]
paths.update(str(P/p) for p in added)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
result={**old,'schema':'numerical-loop-merge-offline-docker-release@1','source_bindings':{p:sha(p) for p in sorted(paths)},'previous_qualified_revision':previous,'merged_revision':merged,'additional_changed_runtime_dependencies':added}
assert all(sha(p)==v for p,v in result['runner_bindings'].items())
with (R/'docker-release-04.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({'source_bindings':len(paths),'profile':result['profile'],'head':merged}))
