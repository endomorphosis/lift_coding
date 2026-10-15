"""Verify explicit source delta and unchanged pinned runtime dependencies."""
import hashlib
import json
from pathlib import Path
G=Path(__file__).parent
F=G.parent/'terminal-compact-retrieval-20261011-02'
old=json.loads((F/'runtime-archive-v13/manifest.json').read_text())
new=json.loads((G/'runtime-archive-v14/manifest.json').read_text())
a={r['path']:r for r in old['files']};b={r['path']:r for r in new['files']}
removed=sorted(a.keys()-b.keys());added=sorted(b.keys()-a.keys())
changed=sorted(k for k in a.keys()&b.keys() if a[k]!=b[k])
assert not removed
source=json.loads((G/'source-manifest.json').read_text())
allowed={'source/'+r['path'] for r in source['files']}
assert set(added+changed)<=allowed
assert added==['source/ipfs_accelerate_py/agent_supervisor/runtime/code_retrieval_wire_delivery.py']
unchanged_dependencies=[k for k in a if not k.startswith('source/')]
assert all(a[k]==b[k] for k in unchanged_dependencies)
assert old['credentials_in_archive'] is False and new['credentials_in_archive'] is False
assert old['task_inputs_in_archive'] is False and new['task_inputs_in_archive'] is False
receipt={'schema':'materialized-wire-runtime-delta@1','base_archive_sha256':old['archive_sha256'],
 'archive_sha256':new['archive_sha256'], 'manifest_sha256':hashlib.sha256((G/'runtime-archive-v14/manifest.json').read_bytes()).hexdigest(),
 'changed_entries':changed,'added_entries':added,'removed_entries':removed,
 'unchanged_dependency_entries':len(unchanged_dependencies),'all_non_source_entries_byte_mode_identical':True,
 'all_runtime_changes_join_captured_source_patch':True,'credentials_in_archive':False,'task_inputs_in_archive':False}
(G/'runtime-delta.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt),flush=True)
