import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

EVIDENCE=Path(__file__).parent
CHECKOUT=Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
baseline=json.loads((EVIDENCE/'baseline.json').read_text())
rows=baseline['files']
new_names=[
 'ipfs_accelerate_py/agent_supervisor/runtime/compact_code_retrieval.py',
 'ipfs_accelerate_py/agent_supervisor/runtime/verified_code_retrieval_projection.py',
 'test/api/test_compact_code_retrieval.py',
 'test/api/test_verified_code_retrieval_projection.py',
 'benchmarks/agent_supervisor/container_coding/test_terminal_retrieval_codec.py',
 'benchmarks/agent_supervisor/container_coding/test_terminal_retrieval_codec_comparison.py',
 'benchmarks/agent_supervisor/container_coding/test_terminal_context_audit_budget.py',
]
sha=lambda data:hashlib.sha256(data).hexdigest()
changes=[]
parts=[]
for name in sorted({row['path'] for row in rows}|set(new_names)):
 old_path=EVIDENCE/'baseline'/name
 before=old_path.read_bytes() if old_path.exists() else b''
 after=(CHECKOUT/name).read_bytes()
 if before==after:continue
 if name.endswith('.py'): ast.parse(after,filename=name)
 if old_path.exists():
  pin=next(row for row in rows if row['path']==name)
  assert len(before)==pin['bytes'] and sha(before)==pin['sha256']
 else:
  assert name in new_names
 changes.append({'path':name,'new_file':not old_path.exists(),'before_bytes':len(before),
  'before_sha256':sha(before) if old_path.exists() else None,'after_bytes':len(after),'after_sha256':sha(after)})
 parts.extend(difflib.unified_diff(before.decode().splitlines(keepends=True),after.decode().splitlines(keepends=True),
  fromfile='a/'+name if old_path.exists() else '/dev/null',tofile='b/'+name))
patch=''.join(parts).encode()
(EVIDENCE/'changes-final.patch').write_bytes(patch)
with tempfile.TemporaryDirectory(prefix='public-patch-application-',dir=EVIDENCE) as directory:
 root=Path(directory)
 for row in rows:
  target=root/row['path'];target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes((EVIDENCE/'baseline'/row['path']).read_bytes())
 subprocess.run(['git','init','-q',str(root)],check=True,capture_output=True)
 subprocess.run(['git','-C',str(root),'apply','--check',str(EVIDENCE/'changes-final.patch')],check=True,capture_output=True)
 subprocess.run(['git','-C',str(root),'apply',str(EVIDENCE/'changes-final.patch')],check=True,capture_output=True)
 assert all((root/row['path']).read_bytes()==(CHECKOUT/row['path']).read_bytes() for row in changes)
receipt={'schema':'terminal-compact-retrieval-source-delta@1','checkout':str(CHECKOUT),
 'patch_basis':'Exact captured beginning-of-turn files; preexisting dirty changes excluded.',
 'files':changes,'patch_bytes':len(patch),'patch_sha256':sha(patch),
 'all_changed_python_syntax_checked':True,'patch_applies_cleanly_to_captured_baseline':True,
 'applied_changed_bytes_match_checkout':True,'original_dirty_checkout_or_git_index_mutated':False}
(EVIDENCE/'source-manifest-final.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'changed_files':len(changes),'patch_sha256':sha(patch),'patch_applies':True}))
