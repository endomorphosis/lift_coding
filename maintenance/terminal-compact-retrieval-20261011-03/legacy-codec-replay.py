"""Independent historical public-fixture replay; exports hashes and booleans only."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time

G = Path('/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-03')
E = Path('/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01')
ROOT = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
sha = lambda raw: hashlib.sha256(raw).hexdigest()
started = time.monotonic()
from ipfs_accelerate_py.agent_supervisor.runtime import compact_code_retrieval as current
from ipfs_accelerate_py.agent_supervisor.runtime import supervisor_meta_index as metadata
from ipfs_accelerate_py.agent_supervisor.runtime.verified_code_retrieval_projection import decoder_command_prefix
from test.api.test_compact_code_retrieval import native_case

old_paths = [(1, E / 'legacy-codec-v12.py', json.loads((E / 'legacy-codec-replay.json').read_bytes())['expected_qualified_v12_module_sha256']),
             (2, G / 'baseline/ipfs_accelerate_py/agent_supervisor/runtime/compact_code_retrieval.py', '4d78a279ce3dea88ddcc90a1003a7a6a54142a68c33b6989f4678d51a895e15f')]
old_modules = []
for version, path, expected in old_paths:
    raw = path.read_bytes()
    assert sha(raw) == expected
    spec = importlib.util.spec_from_file_location(current.__package__ + '.qualified_legacy_' + str(version), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    old_modules.append((version, module, {'path': str(path), 'sha256': sha(raw), 'bytes': len(raw)}))
owned = [ROOT / 'ipfs_accelerate_py/agent_supervisor/runtime' / name for name in
         ('compact_code_retrieval.py', 'verified_code_retrieval_projection.py', 'code_retrieval_wire_delivery.py')]
pins = {str(path): sha(path.read_bytes()) for path in owned}
checks = []
prior_env = {name: os.environ.get(name) for name in (metadata.ENV_DUCKDB, metadata.ENV_DUCKLAKE, 'IPFS_ACCELERATE_AGENT_SEAL_DB_PATH')}
try:
    with tempfile.TemporaryDirectory(prefix='legacy-public-fixture-', dir=G) as folder:
        repository = Path(folder)
        repository.chmod(0o755)
        os.environ[metadata.ENV_DUCKDB] = str(repository / 'fresh-metadata.duckdb')
        os.environ.pop(metadata.ENV_DUCKLAKE, None)
        os.environ['IPFS_ACCELERATE_AGENT_SEAL_DB_PATH'] = str(repository / 'fresh-seal.duckdb')
        prompt, source, native, _ = native_case(repository)
        source_path = repository / 'instruction.md'
        source_path.write_bytes(source.encode()); source_path.chmod(0o444)
        prefix = decoder_command_prefix(repository=repository, source_path=source_path.name,
            source_sha256=sha(source.encode()), native_prompt_sha256=sha(prompt.encode()))
        for version, old, old_ref in old_modules:
            for label, command in [('none', None), ('actual_trusted_decoder_prefix', prefix)]:
                old_packet = old.encode_code_retrieval_prompt(prompt, source)
                new_packet = current.encode_code_retrieval_prompt(prompt, source)
                old_kwargs = {"decoder_command": command, **({"guidance_version": version} if version == 2 else {})}
                old_render = old.render_code_retrieval_prompt(old_packet, **old_kwargs)
                new_render = current.render_code_retrieval_prompt(new_packet, decoder_command=command, guidance_version=version)
                old_project = old.project_code_retrieval_prompt(prompt, source, **old_kwargs)
                new_project = current.project_code_retrieval_prompt(prompt, source, decoder_command=command, guidance_version=version)
                flags = {
                    'packet_equal': old_packet == new_packet,
                    'render_utf8_equal': old_render.encode() == new_render.encode(),
                    'parse_equal': old.parse_code_retrieval_prompt(old_render, **old_kwargs) == current.parse_code_retrieval_prompt(new_render, decoder_command=command, guidance_version=version),
                    'project_utf8_equal': old_project[0].encode() == new_project[0].encode(),
                    'closed_receipt_equal': old_project[1] == new_project[1],
                    'decode_exact_equal': old.decode_code_retrieval_prompt(old_packet, source).encode() == current.decode_code_retrieval_prompt(new_packet, source).encode() == prompt.encode(),
                }
                assert all(flags.values())
                if version == 2:
                    assert current.render_code_retrieval_prompt(new_packet, decoder_command=command) == old_render
                    assert current.project_code_retrieval_prompt(prompt, source, decoder_command=command) == old_project
                checks.append({'guidance_version': version, 'command_scope': label, 'previous_source': old_ref,
                    **flags, 'render_sha256': sha(new_render.encode()), 'selected_sha256': sha(new_project[0].encode()),
                    'receipt_sha256': sha(json.dumps(new_project[1], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())})
        fixture = {'genuine_native_ast_vector_five_hit_fixture': True, 'native_code_hit_count': len(native['hits']),
            'native_prompt_sha256': sha(prompt.encode()), 'literal_source_sha256': sha(source.encode()),
            'signed_native_admission_claimed': False}
finally:
    for name, value in prior_env.items():
        if value is None: os.environ.pop(name, None)
        else: os.environ[name] = value
assert all(sha(path.read_bytes()) == pins[str(path)] for path in owned)
result = {'schema': 'legacy-codec-materialized-guidance-replay@1', 'scope': 'Qualified original v12 source v1 and captured v13 source v2 compared independently with current explicit legacy modes and default v2; public authored fixture, no providers/raw transcripts/private or hidden inputs.',
    'checks': checks, 'all_byte_and_receipt_equal': all(all(row[k] for k in ('packet_equal', 'render_utf8_equal', 'parse_equal', 'project_utf8_equal', 'closed_receipt_equal', 'decode_exact_equal')) for row in checks),
    'fixture': fixture, 'source_pins': pins, 'source_pins_unchanged': True, 'provider_calls': 0,
    'old_evidence_modified': False, 'runtime_archive_modified': False, 'seconds': time.monotonic() - started}
with (G / 'legacy-codec-replay-final.json').open('x') as out:
    json.dump(result, out, indent=2, sort_keys=True); out.write('\n')
print(json.dumps({'checks': len(checks), 'all_byte_and_receipt_equal': result['all_byte_and_receipt_equal'], 'native_code_hit_count': fixture['native_code_hit_count']}))
