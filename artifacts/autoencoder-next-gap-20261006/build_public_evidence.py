"""Bundle bounded diagnostic evidence, never model assets or checkpoints."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import tarfile

R = Path(__file__).resolve().parent
W = R.parents[1]
P = W / 'external/ipfs_datasets'
B = P / 'workspace/test-logs'
RUN = B / 'decoder-paraphrase-modality-margins-r2-20261006'
FIRST = B / 'decoder-paraphrase-modality-margins-20261006'
PUBLIC = P / 'docs/implementation/reports/evidence/decoder-paraphrase-modality-margins-20261006'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    summary = read(RUN / 'diagnostic-r1/results/summary.json')
    resource = read(RUN / 'diagnostic-r1/resources-final.json')
    guardian = read(RUN / 'guardian-exit.json')
    audit = read(R / 'diagnosis/independent-numerical-audit.json')
    assert summary['complete'] is True and resource['status'] == 'released'
    assert guardian['returncode'] == read(RUN / 'diagnostic-r1/child-exit.json')['returncode'] == 0
    assert audit['passed'] is True and not audit['findings']
    old_summary = read(B / 'decoder-paraphrase-modality-styles-20261004/evaluation-r1/results/summary.json')
    panels = []
    for panel in summary['panels']:
        archived = [x for x in old_summary['panels'] if x['dimension'] == panel['dimension']
                    and x['arm'] == panel['arm'] and x['role'] == 'selected']
        assert len(archived) == 1 and archived[0]['state_ref'] == panel['state_ref']
        panels.append(dict(panel, exact_paragraphs=archived[0]['ordered_exact'],
                           sample_count=48, rule_count=180,
                           generation_seconds_per_paragraph=panel['generation_seconds'] / 48))
    PUBLIC.mkdir(parents=True, exist_ok=False)
    results = dict(schema='published-paraphrase-modality-diagnostic/v1', complete=True,
        panels=panels, independent_check_count=audit['check_count'],
        independent_float32_coordinates_checked=2880 * 32,
        maximum_component_metric_absolute_difference=audit['maximum_component_metric_absolute_difference'],
        all_archived_predictions_exact=True, decoder_states_executed=4,
        driver_elapsed_seconds=summary['elapsed_seconds'], guardian_elapsed_seconds=guardian['wrapper_elapsed_seconds'],
        retained_attempt_bytes=resource['record']['final_attempt_bytes'], resources_released=True,
        charged_bytes_at_finalization=resource['record']['final_accounting']['charged_bytes'],
        storage_cap_bytes=resource['storage_limit_bytes'], reservation_storage_bytes=100000000,
        reservation_memory_mb=1536, comparison_scope='previously_exposed_authored_v3; four selected states',
        recipe=summary['recipe'], formal_status=summary['formal_status'],
        legal_ir_bridge_evaluation_executed=False, legal_ir_target_count=None,
        training_executed=False, encoder_executed=False, downloads_performed=False,
        qualified=False, admitted=False, checkpoint_promoted=False, fresh_holdout=False,
        convergence_proven=False, formalized=False, roundtrip_ok=False, lake_executed=False,
        compiler_output_executed=False, protected_teacher_modified=False,
        next_training_recipe_status='specified_only; not_executed',
        new_decoder_loss_or_predictions_improved=False)
    save(PUBLIC / 'results.json', results)
    sources = {}

    def retain(path):
        path = Path(path)
        assert path.is_file() and not path.is_symlink()
        assert path.suffix in ('.py', '.md', '.json', '.jsonl', '.xml', '.log')
        raw = path.read_bytes()
        assert len(raw) < 5000000, path
        sources[path.relative_to(W).as_posix()] = (path, raw)

    for folder in ('diagnosis', 'data', 'runner_review'):
        for path in sorted((R / folder).glob('*')):
            if path.is_file():
                retain(path)
    for path in sorted(RUN.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            retain(path)
    for name in ('diagnostic-manifest.json', 'diagnostic-plan.json', 'superseded-preparation.json'):
        retain(FIRST / name)
    for path in (R / 'initial-git-and-protected-checkpoint.json', R / 'build_public_evidence.py',
                 P / 'scripts/ops/autoencoder/diagnose_paraphrase_modality_margins.py',
                 P / 'tests/unit/logic/formalization/autoencoder/test_paraphrase_modality_margins.py',
                 P / 'docs/autoencoders/paraphrase_modality_diagnostics.md', PUBLIC / 'results.json'):
        retain(path)
    assert sum(len(raw) for _, raw in sources.values()) < 25000000
    archive = R / 'review-evidence.tar.gz'
    with archive.open('xb') as output:
        with gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode='w|') as tar:
                for name, (_, raw) in sorted(sources.items()):
                    entry = tarfile.TarInfo(name)
                    entry.size = len(raw)
                    entry.mode = 0o644
                    tar.addfile(entry, io.BytesIO(raw))
    assert archive.stat().st_size < 10000000
    members = {name: dict(bytes=len(raw), sha256=digest(raw)) for name, (_, raw) in sorted(sources.items())}
    manifest = dict(schema='published-paraphrase-modality-evidence-manifest/v1',
        archive_path=archive.relative_to(W).as_posix(), archive_repository='workspace origin/main',
        archive_sha256=digest(archive.read_bytes()), archive_bytes=archive.stat().st_size,
        member_count=len(members), members=members,
        final_input_manifest_sha256=digest((RUN / 'diagnostic-manifest.json').read_bytes()),
        final_plan_sha256=digest((RUN / 'diagnostic-plan.json').read_bytes()),
        input_count=1178, frozen_extension_count=11, source_runner_tests=73,
        model_assets_bundled=False, private_checkpoint_tensors_bundled=False,
        predecessor_source_trees_bundled=False, local_saved_dependencies_required=True,
        provenance_scope='authenticated historical numerical producers; not current compiler',
        first_preparation_seal_preserved=True, first_preparation_launched=False,
        training_executed=False, checkpoint_promoted=False, admitted=False)
    save(PUBLIC / 'manifest.json', manifest)
    save(R / 'evidence-bundle-receipt.json', dict(passed=True, findings=[],
        archive_sha256=manifest['archive_sha256'], archive_bytes=manifest['archive_bytes'],
        member_count=len(members), archive_scope='bounded JSON/source evidence; no weights'))
    print(json.dumps(dict(members=len(members), archive_bytes=archive.stat().st_size,
                          archive_sha256=manifest['archive_sha256'])))


if __name__ == '__main__':
    main()
