#!/usr/bin/env python3
"""Assemble the anonymous measured-evidence ZIP after all component exports exist."""
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'supplement_staging'
TABLE_INPUTS = (
    'pipeline/summary.json', 'autoencoder/final/summary.json',
    'guidance/final_join/summary.json', 'assistance/natural_summary.json',
    'assistance/summary.json', 'assistance/paper_ready_numbers.json',
    'autoencoder/final/source_embeddings.jsonl.receipt.json')
PROTOCOLS = (
    'FINAL_PROTOCOL_FREEZE.json', 'runtime_manifest.json', 'citation_verification.md', 'original_programme_crosswalk.json',
    'freeze_drift_review.json', 'post_execution_freeze_review.json', 'infrastructure_amendment_review.json',
    'pipeline/final_release.json', 'autoencoder/scientific_profile.json',
    'autoencoder/cache_execution_amendment.json',
    'autoencoder/training_mean_baseline.freeze.json',
    'autoencoder/mean_metadata_amendment.json',
    'guidance/collector_binding_addendum.json')
SUMMARY_LINKS = {
    'pipeline/summary.json': 'pipeline/summary.json',
    'autoencoder/final/summary.json': 'autoencoder/summary.json',
    'guidance/final_join/summary.json': 'guidance/summary.json',
    'assistance/natural_summary.json': 'natural/natural_summary.json',
    'assistance/summary.json': 'proof/summary.json',
    'autoencoder/final/source_embeddings.jsonl.receipt.json': 'autoencoder/provenance/source_embeddings.receipt.json',
}

def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()

def publish_text(src, dst, custody):
    # Preserve all numeric values and identify path-only transformations.
    raw = src.read_text()
    body = raw.replace('/home/barberb/lift_coding', '/ANONYMOUS_RESEARCH_ROOT').replace('/home/barberb', '/ANONYMOUS_HOME')
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(body)
    custody.append({'path': str(dst.relative_to(TARGET)), 'original_sha256': sha(src),
                    'published_sha256': sha(dst), 'transformation': 'none' if raw == body else 'private host root markers only'})

def main():
    for component, verifier in [('pipeline', 'reproduce.py'), ('autoencoder', 'reproduce.py'),
                                ('guidance', 'reproduce_guidance.py'), ('natural', 'verify_counts.py'),
                                ('proof', 'verify_proofs.py')]:
        assert (TARGET / component / verifier).is_file(), (component, verifier)
    assert json.loads((ROOT / 'assistance/natural_summary.json').read_text())['attempted'] == 100
    assert json.loads((ROOT / 'autoencoder/final/summary.json').read_text())['cohort_records'] == 1913
    custody = []
    for name in TABLE_INPUTS:
        if name in SUMMARY_LINKS:
            assert json.loads((ROOT / name).read_text()) == json.loads((TARGET / SUMMARY_LINKS[name]).read_text()), ('Table source and verified component differ', name)
        publish_text(ROOT / name, TARGET / 'table_inputs' / name, custody)
    (TARGET / 'TABLE_COMPONENT_LINKS.json').write_text(json.dumps(SUMMARY_LINKS, indent=2) + '\n')
    for name in PROTOCOLS:
        publish_text(ROOT / name, TARGET / 'protocols' / name, custody)
    for name in ['generate_paper_tables.py']:
        publish_text(ROOT / name, TARGET / name, custody)
    for path in sorted((ROOT / 'editable/results').glob('*')):
        if path.suffix in ('.tex', '.json'):
            publish_text(path, TARGET / 'published_tables' / path.name, custody)
    (TARGET / 'ROOT_CUSTODY.json').write_text(json.dumps(custody, indent=2) + '\n')
    license_dir = TARGET / 'licenses'
    license_dir.mkdir(exist_ok=True)
    shutil.copyfile(ROOT.parents[2] / 'external/ipfs_datasets/LICENSE', license_dir / 'ipfs_datasets_AGPL-3.0.txt')
    root_indexes = {TARGET / 'MANIFEST.json', TARGET / 'SHA256SUMS'}
    paths = sorted(p for p in TARGET.rglob('*') if p.is_file()
                   and '__pycache__' not in p.parts and p not in root_indexes)
    private = [str(p.relative_to(TARGET)) for p in paths if b'/home/barberb' in p.read_bytes() or b'barberb@' in p.read_bytes()]
    assert not private, ('Private host identity in anonymous payload', private)
    manifest = {'schema': 'anonymous-autoformalization-empirical-supplement/v1',
                'files': [{'path': str(p.relative_to(TARGET)), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in paths],
                'complete_denominators': {'native_units_each_B_C_T5': 1913, 'direct_model_sources': 100,
                                          'learned_source_seed_pairs': 5739, 'constructed_proof_goals': 64},
                'fresh_inference_fully_packaged': False,
                'omissions': ['multi-gigabyte adaptive parameter arrays and sample-memory files',
                              'pretrained language and embedding model weights', 'complete external compiler/serving runtime'],
                'supported_reproduction': 'per-unit metric aggregation, paired intervals, reported tables, optional native replay of the twelve admitted model proofs'}
    (TARGET / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    paths.append(TARGET / 'MANIFEST.json')
    (TARGET / 'SHA256SUMS').write_text(''.join(f"{sha(p)}  {p.relative_to(TARGET)}\n" for p in sorted(paths)))
    paths.append(TARGET / 'SHA256SUMS')
    archive = ROOT / 'supplement.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=7) as bundle:
        for path in sorted(paths):
            info = zipfile.ZipInfo(str(path.relative_to(TARGET)), date_time=(2026, 9, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=7)
    assert archive.stat().st_size < 100_000_000, archive.stat().st_size
    report = {'archive_sha256': sha(archive), 'archive_bytes': archive.stat().st_size,
              'files': len(paths), 'uncompressed_bytes': sum(p.stat().st_size for p in paths),
              'private_host_identity_scan_passed': True, 'zip_member_names_relative': True}
    (ROOT / 'supplement_build_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
