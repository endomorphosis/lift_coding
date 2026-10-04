"""Bind final prose while preserving the already validated numerical replay."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path('/home/barberb/lift_coding')
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
OUTPUT = CAMPAIGN / 'decoder-replay-02'


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def bind(path):
    path = Path(path)
    value = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(value), sha256=hashlib.sha256(value).hexdigest())


def main():
    assert not OUTPUT.exists()
    predecessor_path = CAMPAIGN / 'decoder-replay-01/validation.json'
    predecessor_binding = bind(predecessor_path)
    assert predecessor_binding['sha256'] == 'ba3ee457a4405c60d2921bbe0572b4face6c05f7565f755e8cc599d5cd84c4bf'
    previous = json.loads(predecessor_path.read_bytes())
    payload = {key: value for key, value in previous.items() if key != 'content_sha256'}
    assert hashlib.sha256(raw(payload)).hexdigest() == previous['content_sha256']
    for reference in (previous['checked_file_bindings'] + [previous['runner_binding'],
                       previous['span_report_binding'], previous['sidecar_report_binding']]
                      + previous['predecessor_validation_bindings']):
        assert bind(reference['path']) == reference
    documents = [ROOT / 'implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md',
                 CAMPAIGN / 'decoder-replay-report.md']
    links = []
    for document in documents:
        for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', document.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            resolved = (document.parent / target.split('#')[0]).resolve()
            assert resolved.is_file() or resolved == OUTPUT / 'validation.json'
            links.append(dict(document=str(document), target=target, resolved=str(resolved)))
    checkout = ROOT / '.worktrees/alignment-decoder-768-20261003'
    assert subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain=v1',
                                   '--untracked-files=normal'], text=True).strip() == ''
    result = dict(schema='alignment-decoder-replay-documentation-validation/v1', status='passed_unqualified',
                  runner_binding=bind(__file__), numerical_validation_binding=predecessor_binding,
                  numerical_evidence_preserved=True, unchanged_checked_file_count=len(previous['checked_file_bindings']),
                  documentation_bindings=[bind(path) for path in documents], local_link_checks=links,
                  correction_scope='clarify_saved_BOS_rows_vs_probe_rows_and_configured_output_cap;update_validation_link',
                  independent_readonly_audits=[
                      dict(agent='/root/decoder_checkout_audit', scope='source_span_bindings_control_arithmetic_private_reloads',
                           status='passed', new_model_execution=False),
                      dict(agent='/root/autoencoder_inventory', scope='sidecar_bindings_stdlib_binary_digests_source_joins_geometry_generations',
                           status='passed', new_model_execution=False)],
                  model_execution=False, training_execution=False, proof_execution=False,
                  complete_dependency_manifest=False, independent_semantic_review_completed=False,
                  checkpoint_promoted=False, qualified=False, proof_authority=False,
                  source_fidelity_established=False)
    result['content_sha256'] = hashlib.sha256(raw(result)).hexdigest()
    OUTPUT.mkdir()
    path = OUTPUT / 'validation.json'
    with path.open('xb') as stream:
        stream.write(raw(result) + b'\n')
    assert all(Path(item['resolved']).is_file() for item in links)
    print(json.dumps(dict(validation=bind(path), unchanged_file_count=result['unchanged_checked_file_count'],
                         local_links=len(links)), indent=2))


if __name__ == '__main__':
    main()
