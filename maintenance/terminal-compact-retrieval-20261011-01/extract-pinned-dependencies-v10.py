"""Extract only verified, regular v10 public dependency sources into fresh evidence."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import time

EVIDENCE = Path('/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01')
ARCHIVE = EVIDENCE / 'runtime-archive-v10/runtime.tar.gz'
MANIFEST = EVIDENCE / 'runtime-archive-v10/manifest.json'
DESTINATION = EVIDENCE / 'pinned-dependencies-v10'
EXPECTED_ARCHIVE_SHA256 = 'eee6600da4a5a9432fcfd4ff8b40162d604f0d632741efdbdbc80624da9b915d'
EXPECTED_MANIFEST_SHA256 = 'cd7bb7704895ec07367de31b6d1bbc769d4a3f53c1441b4f832f58f415701cd4'

def need(condition, reason):
    if not condition:
        raise ValueError(reason)

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def identity(path):
    value = path.lstat()
    need(stat.S_ISREG(value.st_mode) and not path.is_symlink(), 'regular immutable archive input required')
    return tuple(getattr(value, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mode', 'st_mtime_ns', 'st_ctime_ns'))

def canonical(name):
    need(type(name) is str and 0 < len(name.encode()) <= 4096, 'bounded archive relative name required')
    value = PurePosixPath(name)
    need(not value.is_absolute() and str(value) == name and name != '.' and '..' not in value.parts
         and not any(character in name for character in ('\0', '\r', '\n')), 'noncanonical archive relative name')
    return value

started = time.monotonic()
os.umask(0o022)
archive_before, manifest_before = identity(ARCHIVE), identity(MANIFEST)
need(digest(ARCHIVE) == EXPECTED_ARCHIVE_SHA256, 'v10 whole archive digest differs before extraction')
manifest_raw = MANIFEST.read_bytes()
need(hashlib.sha256(manifest_raw).hexdigest() == EXPECTED_MANIFEST_SHA256, 'v10 manifest digest differs')
manifest = json.loads(manifest_raw)
need(manifest['archive_sha256'] == EXPECTED_ARCHIVE_SHA256 and manifest['credentials_in_archive'] is False
     and manifest['task_inputs_in_archive'] is False, 'public archive safety and identity claims differ')
inventory = {}
parents = set()
for row in manifest['files']:
    need(type(row) is dict and set(row) == {'path', 'sha256', 'bytes', 'mode'}, 'exact manifest record required')
    name = canonical(row['path'])
    need(row['path'] not in inventory and type(row['bytes']) is int and row['bytes'] >= 0
         and type(row['mode']) is int and row['mode'] in (0o644, 0o755)
         and type(row['sha256']) is str and re.fullmatch('[a-f0-9]{64}', row['sha256']), 'manifest duplicate or invalid bound')
    inventory[row['path']] = row
    parents.update(str(parent) for parent in name.parents if str(parent) != '.')
selected = {name: row for name, row in inventory.items() if PurePosixPath(name).parts[0] in ('datasets', 'kit')}
need(selected and any(name.startswith('datasets/') for name in selected)
     and any(name.startswith('kit/') for name in selected), 'complete dependency populations required')
DESTINATION.mkdir(mode=0o755, exist_ok=False)
seen, extracted = set(), []
header_count = 0
with tarfile.open(ARCHIVE, mode='r|gz') as archive:
    for member in archive:
        name = str(canonical(member.name))
        header_count += 1
        need(not member.issym() and not member.islnk(), 'archive links refused')
        if member.isdir():
            need(name in parents and member.mode == 0o755, 'unknown or nonpublic archive directory')
            continue
        need(member.isfile() and name in inventory and name not in seen, 'unexpected archive type, member or duplicate')
        expected = inventory[name]
        need(member.size == expected['bytes'] and member.mode == expected['mode'], 'archive header differs from exact inventory')
        seen.add(name)
        if name not in selected:
            continue
        target = DESTINATION.joinpath(*PurePosixPath(name).parts)
        target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        source = archive.extractfile(member)
        need(source is not None, 'regular dependency body required')
        hasher, count = hashlib.sha256(), 0
        with source, target.open('xb') as destination:
            while raw := source.read(1024 * 1024):
                count += len(raw)
                need(count <= expected['bytes'], 'dependency body exceeds inventory byte bound')
                destination.write(raw)
                hasher.update(raw)
            destination.flush()
            os.fchmod(destination.fileno(), expected['mode'])
        need(count == expected['bytes'] and hasher.hexdigest() == expected['sha256'], 'dependency body differs from exact inventory')
        extracted.append(dict(expected))
need(seen == set(inventory), 'whole archive regular-file census differs from manifest')
need({row['path'] for row in extracted} == set(selected), 'dependency extraction omitted an inventory member')
for row in extracted:
    target = DESTINATION / row['path']
    info = target.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == row['mode']
         and info.st_size == row['bytes'] and digest(target) == row['sha256'], 'independent extracted file reread differs')
for directory in (DESTINATION, *(path for path in DESTINATION.rglob('*') if path.is_dir())):
    need(not directory.is_symlink() and stat.S_IMODE(directory.lstat().st_mode) == 0o755, 'snapshot directory mode differs')
need(identity(ARCHIVE) == archive_before and digest(ARCHIVE) == EXPECTED_ARCHIVE_SHA256
     and identity(ARCHIVE) == archive_before, 'v10 archive changed during extraction')
need(identity(MANIFEST) == manifest_before and MANIFEST.read_bytes() == manifest_raw, 'v10 manifest changed during extraction')
counts = {}
for prefix in ('datasets', 'kit'):
    rows = [row for row in extracted if row['path'].startswith(prefix + '/')]
    counts[prefix] = {'root': str(DESTINATION / prefix), 'files': len(rows), 'bytes': sum(row['bytes'] for row in rows),
                      'files_0644': sum(row['mode'] == 0o644 for row in rows),
                      'files_0755': sum(row['mode'] == 0o755 for row in rows)}
receipt = {'schema': 'terminal-pinned-public-dependency-snapshot@1', 'archive': str(ARCHIVE),
    'archive_sha256_before': EXPECTED_ARCHIVE_SHA256, 'archive_sha256_after': EXPECTED_ARCHIVE_SHA256,
    'manifest': str(MANIFEST), 'manifest_sha256': EXPECTED_MANIFEST_SHA256,
    'extractor_sha256': digest(Path(__file__)), 'destination': str(DESTINATION),
    'all_archive_headers_inspected': True, 'archive_header_count': header_count,
    'archive_regular_file_count': len(seen), 'archive_inventory_census_verified': True,
    'links_and_special_files_refused': True, 'only_datasets_and_kit_bodies_extracted': True,
    'every_extracted_sha256_bytes_and_original_mode_verified_twice': True,
    'directories_mode': 0o755, 'source_modes_preserved': True, 'credentials_in_source_archive': False,
    'task_inputs_in_source_archive': False, 'live_dependencies_modified': False,
    'archive_and_manifest_unchanged': True, 'provider_calls': 0, 'counts': counts,
    'files': sorted(extracted, key=lambda row: row['path']), 'elapsed_seconds': time.monotonic() - started}
with (DESTINATION / 'snapshot-receipt.json').open('x') as stream:
    stream.write(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps({key: value for key, value in receipt.items() if key != 'files'}, indent=2, sort_keys=True))
