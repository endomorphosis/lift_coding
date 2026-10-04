"""Publishable derivatives; flagged raw content remains in local capture only."""
from pathlib import Path
import hashlib
import json
import os
import runpy
import time

BASE = Path('/home/barberb/lift_coding/maintenance/terminal-ir-publication-20261004-01/datasets')
RAW = BASE / 'nested-patches-02'
OUT = BASE / 'public-nested-variants-01'

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + '\n')

def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def main():
    started = time.monotonic()
    OUT.mkdir(mode=0o700)
    (OUT / 'objects').mkdir()
    patterns = runpy.run_path(str(BASE / 'capture_nested_variants_02.py'))['REGEXES']
    summary = json.loads((RAW / 'summary.json').read_text())
    flagged = {Path(row['object_path']).name: row for row in summary['secret_findings'] if row.get('object_path')}
    mapping = {}
    quarantine = []
    for shard in (RAW / 'objects').iterdir():
        if not shard.is_dir():
            continue
        for source in shard.iterdir():
            rawsha = source.name
            if rawsha in flagged:
                data = source.read_bytes()
                try:
                    data.decode('utf-8')
                    text = b'\0' not in data
                except UnicodeDecodeError:
                    text = False
                if not text:
                    mapping[rawsha] = {'raw_sha256': rawsha, 'public_content': None, 'policy': 'quarantined_binary_raw_local_only'}
                    quarantine.append(dict(mapping[rawsha], raw_path=str(source)))
                    continue
                for kind, pattern in patterns:
                    data = pattern.sub(lambda m: ('[REDACTED_' + kind.upper() + '_SHA256_' + hashlib.sha256(m.group()).hexdigest() + ']').encode(), data)
                if any(pattern.search(data) for _, pattern in patterns):
                    raise RuntimeError('redacted derivative still matches scoped credential pattern')
                publicsha = hashlib.sha256(data).hexdigest()
                target = OUT / 'objects' / publicsha[:2] / publicsha
                target.parent.mkdir(exist_ok=True)
                if not target.exists():
                    target.write_bytes(data)
                item = {'raw_sha256': rawsha, 'public_sha256': publicsha, 'public_content': str(target.relative_to(OUT)), 'public_bytes': len(data), 'policy': 'redacted_review_derivative_not_exact_original', 'raw_policy': 'LOCAL_ONLY_QUARANTINE'}
                mapping[rawsha] = item
                quarantine.append(dict(item, raw_path=str(source)))
            else:
                target = OUT / 'objects' / rawsha[:2] / rawsha
                target.parent.mkdir(exist_ok=True)
                os.link(source, target)
                mapping[rawsha] = {'raw_sha256': rawsha, 'public_sha256': rawsha, 'public_content': str(target.relative_to(OUT)), 'public_bytes': source.stat().st_size, 'policy': 'exact_original_unflagged_by_scoped_pattern_scan'}
    repositories = []
    for row in summary['repositories']:
        original = Path(row['manifest']['path'])
        manifest = json.loads(original.read_text())
        folder = OUT / original.parent.name
        folder.mkdir()
        for patch in manifest.get('patches', []):
            source = Path(patch['public_derivative']['path'])
            target = folder / source.name
            os.link(source, target)
            patch['public_derivative'] = dict(pin(target), relative_path=str(target.relative_to(OUT)))
            patch['raw_policy'] = 'LOCAL_ONLY; excluded from publication regardless of flags'
        for entry in manifest.get('files', []):
            if entry.get('kind') == 'regular':
                entry['public_representation'] = mapping[entry['sha256']]
                entry['raw_object_policy'] = 'LOCAL_ONLY; publication uses public_representation only'
        dump(folder / 'manifest.json', manifest)
        repositories.append({'id': row['id'], 'relative': row['relative'], 'manifest': pin(folder / 'manifest.json'), 'manifest_relative_path': str((folder / 'manifest.json').relative_to(OUT)), 'counts': row['counts']})
    objects = [path for shard in (OUT / 'objects').iterdir() for path in shard.iterdir()]
    result = {'schema': 'nested-git-public-review-derivatives@1', 'status': 'prepared', 'repositories': repositories, 'repository_count': len(repositories), 'public_unique_object_count': len(objects), 'public_unique_object_bytes': sum(path.stat().st_size for path in objects), 'quarantined_raw_unique_count': len(quarantine), 'quarantined_raw_unique_bytes': sum(Path(x['raw_path']).stat().st_size for x in quarantine), 'quarantine': quarantine, 'raw_capture_summary_pin': pin(RAW / 'summary.json'), 'scope': 'all89 dirty declared variants preserved; raw suspicious objects/patches LOCAL ONLY; text redaction changes bytes and is review-only; scan is scoped to named credential patterns, not whole-tree or arbitrary archive-content assurance; ignored files/.git internal state outside this Git-variant capture', 'actual_outer_elapsed_seconds': time.monotonic() - started}
    dump(OUT / 'summary.json', result)
    dump(BASE / 'raw-quarantine-01.json', {'schema': 'nested-git-raw-publication-quarantine@1', 'raw_namespace': str(RAW), 'never_upload_namespaces': [str(RAW), str(BASE / 'nested-patches')], 'raw_unique_objects': quarantine, 'public_namespace': str(OUT), 'scope': result['scope']})
    print(json.dumps({key: result[key] for key in ['status', 'repository_count', 'public_unique_object_count', 'public_unique_object_bytes', 'quarantined_raw_unique_count', 'quarantined_raw_unique_bytes', 'actual_outer_elapsed_seconds']}))

if __name__ == '__main__':
    main()
