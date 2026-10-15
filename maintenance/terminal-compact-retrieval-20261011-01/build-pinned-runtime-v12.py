"""Build and independently join every packaged file to its declared digest."""
import hashlib
import json
from pathlib import Path
import tarfile
import time
from benchmarks.agent_supervisor.container_coding.terminal_deployment import build_runtime_archive

EVIDENCE = Path(__file__).parent
ASSETS = Path('/home/barberb/lift_coding/maintenance/terminal-frontier-runtime-20261011-01')
CHECKOUT = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
SOURCE_ROOTS = {'source': CHECKOUT, 'datasets': EVIDENCE / 'pinned-dependencies-v10/datasets',
                'kit': EVIDENCE / 'pinned-dependencies-v10/kit'}
started = time.monotonic()
manifest = build_runtime_archive(output=EVIDENCE / 'runtime-archive-v12', source=SOURCE_ROOTS['source'],
    datasets=SOURCE_ROOTS['datasets'], kit=SOURCE_ROOTS['kit'],
    extension_dir=ASSETS / 'pinned-assets-v8/extensions',
    lean_toolchain=ASSETS / 'pinned-assets-v8/toolchains/lean',
    codex_native_dir=ASSETS / 'native-codex-arm64-bin-02')
records = {r['path']: r for r in manifest['files']}
assert len(records) == len(manifest['files'])
seen = set()
with tarfile.open(EVIDENCE / 'runtime-archive-v12/runtime.tar.gz', 'r:gz') as archive:
    for entry in archive:
        assert entry.name not in seen and entry.name in records and entry.isfile()
        seen.add(entry.name)
        row = records[entry.name]
        assert entry.size == row['bytes'] and entry.mode == row['mode'] and entry.uid == entry.gid == 0
        with archive.extractfile(entry) as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256']
        prefix, relative = entry.name.split('/', 1) if '/' in entry.name else (None, None)
        if prefix in SOURCE_ROOTS:
            path = SOURCE_ROOTS[prefix] / relative
            assert not path.is_symlink() and path.stat().st_size == row['bytes']
            with path.open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256']
assert seen == set(records)
receipt = {'schema': 'terminal-runtime-archive-file-verification@1', 'archive_sha256': manifest['archive_sha256'],
    'files_verified': len(seen), 'total_uncompressed_bytes': sum(r['bytes'] for r in records.values()),
    'all_archive_entries_match_inventory': True, 'all_packaged_source_matches_checkout_after_build': True,
    'credentials_in_archive': manifest['credentials_in_archive'], 'task_inputs_in_archive': manifest['task_inputs_in_archive'],
    'elapsed_seconds': time.monotonic() - started}
(EVIDENCE / 'runtime-archive-verification-v12.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt), flush=True)
