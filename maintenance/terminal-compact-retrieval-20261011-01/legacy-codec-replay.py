"""Compare explicit v1 replay with the exact qualified v12 new-file patch."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

E = Path('/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01')
PATH = 'ipfs_accelerate_py/agent_supervisor/runtime/compact_code_retrieval.py'
OLD_SHA = '1b97477ea0dd09e1d3f930b009f849dc9973936108c443ca71d2a4b0dafe8882'
started = time.monotonic()
patch = (E/'changes.patch').read_bytes()
lines = patch.decode().splitlines(True)
positions = [i for i, line in enumerate(lines) if line == '+++ b/'+PATH+'\n']
assert len(positions) == 1
start = positions[0]
assert lines[start-1] == '--- /dev/null\n' and lines[start+1] == '@@ -0,0 +1,371 @@\n'
end = next((i for i in range(start+2,len(lines)) if lines[i].startswith('--- ')),len(lines))
body = lines[start+2:end]
assert len(body) == 371 and all(line.startswith('+') for line in body)
old_bytes = ''.join(line[1:] for line in body).encode()
assert hashlib.sha256(old_bytes).hexdigest() == OLD_SHA
old_path = E/'legacy-codec-v12.py'
with old_path.open('xb') as stream: stream.write(old_bytes)
name = 'ipfs_accelerate_py.agent_supervisor.runtime.legacy_compact_code_retrieval_v12'
spec = importlib.util.spec_from_file_location(name,old_path)
old = importlib.util.module_from_spec(spec)
sys.modules[name] = old
spec.loader.exec_module(old)
from ipfs_accelerate_py.agent_supervisor.runtime import compact_code_retrieval as new
from ipfs_accelerate_py.agent_supervisor.runtime.verified_code_retrieval_projection import decoder_command_prefix
from test.api.test_compact_code_retrieval import native_case
fixture = E/'legacy-codec-replay-fixture'
fixture.mkdir(mode=0o755)
os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB'] = str(fixture/'fresh-metadata.duckdb')
os.environ.pop('IPFS_ACCELERATE_META_INDEX_DUCKLAKE',None)
os.environ['IPFS_ACCELERATE_AGENT_SEAL_DB_PATH'] = str(fixture/'fresh-seal.duckdb')
prompt,source,context,index = native_case(fixture)
source_path = fixture/'literal-public-source.md'
source_path.write_bytes(source.encode())
source_path.chmod(0o444)
sha = lambda value: hashlib.sha256(value.encode() if isinstance(value,str) else value).hexdigest()
canonical = lambda value: json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
prefix = decoder_command_prefix(repository=fixture,source_path=source_path.name,
    source_sha256=sha(source),native_prompt_sha256=sha(prompt))
checks = []
for command in (None,prefix):
    old_packet = old.encode_code_retrieval_prompt(prompt,source)
    new_packet = new.encode_code_retrieval_prompt(prompt,source)
    old_rendered = old.render_code_retrieval_prompt(old_packet,decoder_command=command)
    new_rendered = new.render_code_retrieval_prompt(new_packet,decoder_command=command,guidance_version=1)
    old_selected,old_receipt = old.project_code_retrieval_prompt(prompt,source,decoder_command=command)
    new_selected,new_receipt = new.project_code_retrieval_prompt(prompt,source,decoder_command=command,guidance_version=1)
    old_parsed = old.parse_code_retrieval_prompt(old_rendered,decoder_command=command)
    new_parsed = new.parse_code_retrieval_prompt(new_rendered,decoder_command=command,guidance_version=1)
    equal = {'packet_bytes':canonical(old_packet).encode()==canonical(new_packet).encode(),
        'rendered_bytes':old_rendered.encode()==new_rendered.encode(),
        'projected_bytes':old_selected.encode()==new_selected.encode(),
        'receipt_bytes':canonical(old_receipt).encode()==canonical(new_receipt).encode(),
        'parsed_packet_bytes':canonical(old_parsed).encode()==canonical(new_parsed).encode(),
        'exact_native_decode':old.decode_code_retrieval_prompt(old_parsed,source)==new.decode_code_retrieval_prompt(new_parsed,source)==prompt}
    assert all(equal.values()),equal
    checks.append({'decoder_prefix_present':command is not None,'checks':equal,
        'legacy_schema':old_receipt['schema'],'rendered_bytes':len(old_rendered.encode()),
        'rendered_sha256':sha(old_rendered),'projected_sha256':sha(old_selected),
        'receipt_sha256':sha(canonical(old_receipt)),'selected_transport':old_receipt['selected_transport']})
receipt = {'schema':'terminal-independent-v12-codec-legacy-replay@1','patch':str(E/'changes.patch'),
    'patch_sha256':sha(patch),'extracted_module':str(old_path),'extracted_module_sha256':sha(old_bytes),
    'expected_qualified_v12_module_sha256':OLD_SHA,'full_new_file_patch_reconstructed':True,
    'current_module_sha256':sha(Path(new.__file__).read_bytes()),'checks':checks,
    'all_old_and_explicit_v1_bytes_equal':True,'native_five_hit_fixture':True,
    'native_code_hit_count':len(context['hits']),'native_prompt_sha256':sha(prompt),
    'literal_source_sha256':sha(source),'provider_calls':0,'new_live_archive_modified':False,
    'repository_files_modified':False,'signed_native_admission_claimed':False,
    'scope':'Exact extracted qualified v12 code compared with current explicit-v1 render/project/parse/decode over one genuine native AST/vector/five-hit fixture; no provider or hidden task content read.',
    'seconds':time.monotonic()-started}
with (E/'legacy-codec-replay.json').open('x') as stream: stream.write(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,indent=2,sort_keys=True))
