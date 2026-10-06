"""Prepare exact new package paths and a bounded workspace publication scope."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

R = Path(__file__).resolve().parent
W = R.parents[1]
P = W / 'external/ipfs_datasets'
EVIDENCE = 'docs/autoencoders/evidence/reconstruction-gap-followup-20261006'
GUIDE = 'docs/autoencoders/reconstruction_gap_followup_20261006.md'
REVIEWS = (
    'diagnosis/diagnosis-readiness.json',
    'qualifier-review/independent-preflight-review.json',
    'train-observation/independent-runner-readiness.json',
    'train-observation/actual-result-independent-review.json',
    'guardian/terminal-resource-independent-review.json',
    'pipeline/publisher-independent-review.json',
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def record(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=sha(raw))


def git(repo, *args):
    return subprocess.check_output(['git', '-c', 'gc.auto=0', '-C', str(repo), *args])


def main():
    if (R / 'publication-scope.json').exists():
        raise ValueError('sealed scope is immutable')
    archive = json.loads((R / 'retention-manifest.json').read_bytes())
    if archive.get('passed') is not True or archive.get('findings'):
        raise ValueError('clean completed archive required')
    archive_path = W / archive['archive']['path']
    if record(archive_path) != {k: archive['archive'][k] for k in ('bytes', 'sha256')}:
        raise ValueError('archive changed')
    review_bindings = {}
    for relative in REVIEWS:
        path = R / relative
        reviewed = json.loads(path.read_bytes())
        if reviewed.get('passed') is not True or reviewed.get('findings'):
            raise ValueError('clean completed review required: ' + relative)
        review_bindings[str(path.relative_to(W))] = record(path)
    source = R / 'documentation/reconstruction_gap_followup_20261006.md'
    freeze = json.loads((R / 'documentation/documentation-freeze.json').read_bytes())
    # The authored guide remains untouched. Only final publication wording is
    # added to a separate final guide after the actual reviews/archive complete.
    if freeze.get('passed') is not True or freeze.get('findings'):
        raise ValueError('clean authored documentation freeze required')
    wanted = freeze['artifacts'][str(source)]
    if record(source) != {k: wanted[k] for k in ('bytes', 'sha256')}:
        raise ValueError('authored guide changed after freeze')
    text = source.read_text()
    old = ('Complete new observation traces and byte-pinned input closure remain in an immutable '
           'workspace archive; compact publication awaits independent numerical and resource reviews and the archive seal.')
    new = ('Complete new observation traces and byte-pinned input closure are retained in the '
           '[immutable workspace archive](https://github.com/endomorphosis/lift_coding/blob/main/'
           + archive['archive']['path'] + '). The [evidence index](evidence/reconstruction-gap-followup-20261006/'
           'evidence-index.json) binds the completed independent numerical, representability and resource reviews '
           'to that archive. Publication uses exact scopes and preserves the newer checkpoint-registration and '
           'worker-custody contributions.')
    if text.count(old) != 1:
        raise ValueError('exact final documentation transition required')
    text = text.replace(old, new)
    text += ('\nMeasurement settings: bridge names `[]`, prover flag false, metric disk cache false, '
             'one CPU worker, batch size 8, CUDA disabled, and warm source-vector caches. '
             'This is a frozen historical neural replay, with no canonical compiler/decompiler/parser calls '
             'and no bridge-on legal-IR throughput claim.\n')
    text += ('\nThe newer [grouped support-boundary continuation](grouped_support_boundary_training.md) '
             'and [source occurrence proposal boundary](../../ipfs_datasets_py/logic/formalization/autoencoder/'
             'legal_scope_span_proposal.py) are preserved alongside this work on main. The matched grouped '
             'study improves unsupported-profile refusal with a small positive-reconstruction tradeoff; its '
             'raw-source architecture and authored cohort are distinct from the native 384D/768D comparison. '
             'The occurrence adapter transports explicit predicted anchors and attachment declarations, '
             'but is untrained and retains unreviewed meaning, unavailable context and zero admission masks. '
             'Those proposals remain ineligible here until their context and source review are resolved. '
             'Future qualifier preparation should reuse that boundary and the existing statement-scope '
             'and review-intake owners, preserving every unresolved field.\n')
    text += ('\nThe compact TRAIN summary retains its author-time pending-resource-review marker. '
             'The evidence index binds the subsequently completed independent reviews and their exact artifacts.\n')
    final_guide = R / 'documentation/final-publication-guide.md'
    with final_guide.open('x') as stream:
        stream.write(text)
    selected = {
        'ipfs_datasets_py/logic/legal_ir/canonical_qualifier_training_preflight.py':
            ('58ebc41a4ea1f93d3497108ebd54ea3611bc652b5d74284214b13bb74a535489', 14908),
        'tests/unit/logic/legal_ir/test_canonical_qualifier_training_preflight.py':
            ('57563f10077d8f978c66b5f0554cc618d34949b32455a1a1270438693129f913', 16352),
    }
    for relative, (wanted_sha, wanted_bytes) in selected.items():
        if record(P / relative) != dict(sha256=wanted_sha, bytes=wanted_bytes):
            raise ValueError('frozen qualifier source changed: ' + relative)
    copies = {GUIDE: final_guide}
    for path in sorted((R / 'documentation/evidence').glob('*.json')):
        copies[EVIDENCE + '/' + path.name] = path
    if len(copies) != 6:
        raise ValueError('one guide and five exact compact evidence records required')
    for relative, source_path in copies.items():
        target = P / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(source_path.read_bytes())
    index = dict(schema='reconstruction-gap-followup-evidence-index/v1', passed=True, findings=[],
                 archive=archive['archive'], archive_entries=len(archive['entries']),
                 archive_uncompressed_bytes=archive['source_bytes'],
                 compact_files={name: record(P / name) for name in copies},
                 independent_reviews=review_bindings,
                 complete_TRAIN_observation=dict(endpoints=4, paragraphs_per_endpoint=96,
                     rules_per_endpoint=360, scalar_sites_per_endpoint=1440,
                     scalar_sites_total=5760, full32_distributions_total=17280),
                 qualification=False, training_executed_by_observation=False,
                 encoder_executed_by_observation=False, lake_executed=False,
                 formalized=False, Constitution_formalized=False,
                 independent_semantic_holdout=False, convergence_proven=False,
                 checkpoint_promoted_by_observation=False)
    save(P / EVIDENCE / 'evidence-index.json', index)
    package_paths = [*selected, *copies, EVIDENCE + '/evidence-index.json']
    final_binding = dict(schema='final-publication-documentation-bindings/v1', passed=True, findings=[],
                         authored_guide=record(source), final_guide=record(final_guide),
                         final_wording_changes=['completed review and immutable archive links',
                                                'explicit measurement settings and frozen numerical scope'],
                         frozen_source_and_compact_values_changed=False,
                         artifacts={str(P / relative): record(P / relative) for relative in package_paths})
    save(R / 'pipeline/final-documentation-bindings.json', final_binding)
    workspace_paths = ['README.md', 'initial-state.json', 'retain_evidence.py',
                       'retention-manifest.json', 'reconstruction-gap-evidence.tar.gz',
                       'prepare_publication.py', 'publish_integration.py', 'publisher_review_tests.py',
                       'pipeline/post-observation-pinned-state.json',
                       'pipeline/publisher-adaptation.diff', 'pipeline/publisher-streaming-adaptation.json',
                       'pipeline/publisher-synthetic-validation.json', 'pipeline/publisher-independent-review.json',
                       'pipeline/final-documentation-bindings.json']
    workspace_paths += [str(path.relative_to(R)) for path in sorted((R / 'documentation').rglob('*'))
                        if path.is_file()]
    scope = dict(schema='reconstruction-gap-exact-main-publication-scope/v1', passed=True, reviewed=True,
                 required_reviews=['pipeline/publication-scope-independent-review.json', *REVIEWS,
                                   'pipeline/final-documentation-bindings.json'])
    for label, repo, paths in (('datasets', P, package_paths),
                               ('workspace', W, [str((R / relative).relative_to(W)) for relative in workspace_paths])):
        git(repo, 'fetch', '--no-tags', 'origin', 'main')
        parent = git(repo, 'rev-parse', 'origin/main').decode().strip()
        files = {}
        for relative in paths:
            if git(repo, '--literal-pathspecs', 'ls-tree', '-z', parent, '--', relative):
                raise ValueError('all-new scoped path already exists on main: ' + relative)
            files[relative] = dict(record(repo / relative), parent_sha256=None, mode='100644')
        scope[label] = dict(parent=parent, files=files)
    save(R / 'publication-scope.json', scope)
    print(json.dumps(dict(package_paths=len(package_paths), workspace_paths=len(workspace_paths),
                          package_parent=scope['datasets']['parent'], workspace_parent=scope['workspace']['parent'])))


if __name__ == '__main__':
    main()
