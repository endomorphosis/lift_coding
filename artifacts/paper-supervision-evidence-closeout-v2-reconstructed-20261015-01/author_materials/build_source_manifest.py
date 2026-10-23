"""Copy and bind one retained manuscript snapshot into a new reconstruction.

Standard library only. Existing input files remain untouched. Each destination
file is opened exclusively; this is not a manuscript build or a supervisor.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
BASE = ROOT / 'papers/revisions/neurosymbolic_system_scope_20260914/build/increment-016'
PACKAGE = Path(__file__).absolute().parent.parent
os.umask(0o077)

def read(path, maximum=2 * 1024 * 1024):
    if path.resolve() != path or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError('Unsafe or oversized source: ' + str(path))
    return path.read_bytes()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write(relative, raw):
    dest = PACKAGE / relative
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with dest.open('xb') as stream:
        stream.write(raw)
    return {'path': str(relative), 'bytes': len(raw), 'sha256': sha(raw)}

original_manifest = read(BASE / 'source_manifest.json')
if sha(original_manifest) != '2f774bd2b3b32b868e3ff72775cbfbbf205921ca387267f7d6c51e61c2390f8b':
    raise ValueError('Retained source manifest changed')
manifest = json.loads(original_manifest)
if len(manifest) != 29:
    raise ValueError('Unexpected snapshot membership')
pending = []
for relative, expected in sorted(manifest.items()):
    fragment = Path(relative)
    if fragment.is_absolute() or '..' in fragment.parts:
        raise ValueError('Unsafe manifest path')
    source = BASE / 'source_snapshot' / fragment
    raw = read(source)
    if sha(raw) != expected:
        raise ValueError('Source digest mismatch: ' + relative)
    pending.append((source, Path('source_reference/source_snapshot') / fragment, raw))

for original, destination in (
    ('main.pdf', 'main.pdf'), ('paper.txt', 'paper.txt'),
    ('source_manifest.json', 'source_manifest.original.json'),
    ('verification.json', 'verification.original.json'),
):
    source = BASE / original
    raw = read(source)
    if original == 'main.pdf' and sha(raw) != '51a72d60c7dcb23faa17918091fe172f6cbacf8f25df10e94d1b4071dce05ce7':
        raise ValueError('Selected PDF changed')
    pending.append((source, Path('source_reference') / destination, raw))

# Validate the complete source set before creating any copied members.
copies = []
for source, destination, raw in pending:
    item = write(destination, raw)
    item['original_path'] = str(source)
    item['copy_is_byte_identical'] = True
    copies.append(item)

result = {
    'schema': 'reconstructed-paper-source-manifest@1',
    'created_at_utc': datetime.now(timezone.utc).isoformat(),
    'title': 'Proof-Carrying Neurosymbolic Supervision: State, Reasoning, and Evidence Reuse',
    'package_kind': 'new_authorized_local_reconstruction',
    'authorization': {'user_reply': 'just make one',
        'context': 'Reply to request for the missing supplied v2 revision package path.'},
    'selected_working_base': str(BASE),
    'selection_basis': 'Explicit working-base choice among retained exact-title 37-page candidates, not proof of supplied-PDF identity.',
    'relation_to_supplied_37_page_pdf': 'unresolved_original_bytes_and_hash_unavailable',
    'original_supplied_v2_package_recovered': False,
    'snapshot_members_verified': len(manifest),
    'pdf_sha256': '51a72d60c7dcb23faa17918091fe172f6cbacf8f25df10e94d1b4071dce05ce7',
    'retained_source_manifest_sha256': sha(original_manifest),
    'abstract_source_sha256': manifest['fragments/abstract.tex'],
    'header_source_sha256': manifest['header.tex'],
    'other_37_page_candidate': {
        'name': 'increment-015',
        'pdf_sha256_observed_in_prior_intake': '4d1d770f607b41d34491a920ec443519889dbd8ae77d661e67faf87630fca9bb',
        'not_used_for_reconstruction': True,
    },
    'adjacent_verification_scope': 'Retained historical metadata, not a fresh build, signature check or experiment authentication.',
    'runtime_source_forest': None,
    'snapshot_is_experiment_runtime_evidence': False,
    'original_manuscripts_or_reports_modified': False,
    'source_files': copies,
    'private_provenance': True,
    'anonymous_release_ready': False,
}
write(Path('author_materials/source_manifest.json'),
      (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
print(json.dumps({'snapshot_members_verified': len(manifest),
                  'byte_identical_copies': len(copies),
                  'supplied_pdf_identity_established': False}))
