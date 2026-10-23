#!/usr/bin/env python3
"""Package exact completed native observations and portable metric reproduction."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = ('final.sources.jsonl', 'final_a100.sources.jsonl', 'final_metadata.json',
         'final_C.jsonl', 'final_T5.jsonl', 'final_B.jsonl', 'summary.json',
         'repair_pairs.jsonl', 'aggregate_pipeline.py', 'constructed.sources.jsonl',
         'constructed_c_v2.jsonl', 'constructed_t5_v2.jsonl',
         'selection_c_v1.jsonl', 'selection_t5_v1.jsonl', 'pool_qualification_c.jsonl')

def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()

def main():
    source = ROOT / 'pipeline'
    target = ROOT / 'supplement_staging/pipeline'
    summary = json.loads((source / 'summary.json').read_text())
    assert summary['population']['units'] == 1913
    target.mkdir(parents=True, exist_ok=True)
    records = []
    for name in FILES:
        src, dst = source / name, target / name
        if b'/home/barberb' in src.read_bytes():
            raise ValueError(f'Private path in scientific payload: {name}')
        shutil.copyfile(src, dst)
        records.append({'path': name, 'original_sha256': sha(src), 'published_sha256': sha(dst), 'transformation': 'none'})
    inspection = target / 'inspection_code'
    inspection.mkdir(exist_ok=True)
    # These drivers retain their scientific implementation but their host root is
    # replaced by an explicit relocation marker. They are inspection copies, not
    # the portable reproduction entry point and not a shipped full runtime.
    driver_paths = [source / 'native_c.py', source / 'run_corpus.py', source / 'release_final.py',
                    ROOT / 'guidance/native_b.py']
    for src in driver_paths:
        body = src.read_text().replace('/home/barberb/lift_coding', '/ANONYMOUS_RESEARCH_ROOT').replace('/home/barberb', '/ANONYMOUS_HOME')
        dst = inspection / src.name
        dst.write_text(body)
        records.append({'path': str(dst.relative_to(target)), 'original_sha256': sha(src), 'published_sha256': sha(dst), 'transformation': 'host root markers only; inspection copy'})
    (target / 'CUSTODY.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps({'pipeline_payload_files': len(records), 'bytes': sum(p.stat().st_size for p in target.rglob('*') if p.is_file())}))

if __name__ == '__main__':
    main()
