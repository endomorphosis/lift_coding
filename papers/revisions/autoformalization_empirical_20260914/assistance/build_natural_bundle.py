#!/usr/bin/env python3
"""Package the completed natural arm, retaining original and public byte hashes."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
ROOT = HERE.parents[3]
DEST = EXPERIMENT / 'supplement_staging/natural'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    summary = json.loads((HERE / 'natural_summary.json').read_text())
    audit = json.loads((HERE / 'natural_provenance_audit.json').read_text())
    lifecycle = [json.loads(line) for line in (HERE / 'warm_lifecycle.jsonl').read_text().splitlines()]
    assert summary['attempted'] == audit['terminal_attempts'] == 100 and audit['passed']
    assert any(row['event'] == 'warm_cleanup' and row['completed'] == 100 and row['port8080closed'] and not row['server_alive'] for row in lifecycle)
    if DEST.exists():
        raise RuntimeError('Refuse to overwrite an existing final natural bundle')
    DEST.mkdir(parents=True)
    entries = []

    def copy(source, relative, scientific=False):
        before = source.read_bytes()
        after = before
        if scientific:
            assert b'/home/barberb' not in before, relative
        else:
            after = after.replace(str(ROOT).encode(), b'<WORKSPACE>').replace(b'/home/barberb', b'<HOME>').replace(b'/run/user/1000', b'/run/user/<UID>')
        target = DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(after)
        origin = str(source.relative_to(EXPERIMENT)) if source.is_relative_to(EXPERIMENT) else str(source.relative_to(ROOT))
        entries.append(dict(bundle_path=str(relative), original_artifact=origin, original_sha256=sha(before), bundle_sha256=sha(after), transformation='byte-identical' if before == after else 'host-path redaction in receipt/source only'))

    copy(EXPERIMENT / 'pipeline/final_a100.sources.jsonl', 'sources.jsonl', True)
    copy(HERE / 'natural_model/results.jsonl', 'results.jsonl', True)
    for folder in sorted((HERE / 'natural_model').glob('record-*')):
        for source in sorted(folder.glob('*.json')):
            copy(source, Path('records') / folder.name / source.name, True)
    for job in sorted((HERE / 'natural_model').glob('job-*')):
        for source in sorted(job.glob('*.json')):
            copy(source, Path('serving_checks') / job.name / source.name)
    for name in ['natural_summary.json', 'natural_provenance_audit.json', 'frozen_natural_protocol.json', 'frozen_natural_protocol_before_context_guard.json', 'frozen_natural_protocol_before_batch_envelope.json', 'leanstral_v15.jinja', 'LIVE_RUNTIME_STATUS.json', 'LIVE_RUNTIME_STATUS.md', 'warm_lifecycle.jsonl', 'warm_cpu_observations.jsonl', 'natural_resource_01.jsonl', 'natural_job_01.log', 'natural_server_01.log', 'NATURAL_RESULTS.md', 'natural_paper_ready_numbers.json']:
        copy(HERE / name, name)
    copy(EXPERIMENT / 'FINAL_PROTOCOL_FREEZE.json', 'FINAL_PROTOCOL_FREEZE.json')
    copy(EXPERIMENT / 'supplement_staging/proof/MODEL_IDENTITY.json', 'MODEL_IDENTITY.json')
    for name in ['run_natural_a.py', 'run_natural_a_before_context_guard.py', 'run_natural_a_before_batch_envelope.py', 'run_natural_workload.py', 'launch_natural_warm.py', 'continue_natural_warm_running_snapshot.py', 'audit_natural_records.py', 'REPRODUCE_WARM_WORKLOAD.md']:
        copy(HERE / name, Path('source') / name)
    copy(ROOT / 'scripts/run_leanstral_ephemeral.py', 'source/run_leanstral_ephemeral.py')
    copy(HERE / 'verify_natural_bundle.py', 'verify_counts.py', True)
    readme = '''This bundle contains all 100 prespecified direct-model natural autoformalization attempts, including malformed responses, abstentions, and request timeouts. The public legal sources, requests, returned response bodies, assembled intermediate representations, and terminal records are retained byte for byte. A missing response file denotes a request that failed before a complete body was received; it is not an omitted successful response.

Run `python3 verify_counts.py` with Python 3.9 or later to verify every manifest hash, exact frozen 100-source input, source and request binding, unchanged returned semantic fields, and all reported counts and costs. This requires no model, solver, network, or third-party Python packages. It audits the recorded native-check outcomes; it does not reexecute the complete compiler or establish legal semantic fidelity. The frozen client and serving configuration are included as source records. Repeating inference also requires the separately identified model weights and original compiler/checker dependencies; these are not bundled.

The sample is the 100 source units with the smallest SHA256("AF20260914-A100:" + normalized_full_unit_sha) in the final held-out source pool. The model receives only the normalized first 4096 raw source characters. Input hashes retain both the complete unit and the evaluated prefix. No compiler outputs or autoencoder predictions enter the prompt. Source-family strata are obtained from the source manifest's `family` field by record ID; the per-attempt `source_family` metadata is null because the original client looked for a differently named optional field. This does not affect source text, prompts or scoring. Output is limited to 8 formula objects and 2048 tokens, with deterministic temperature 0, seed 20260914, one attempt per source and a 60-second request timeout. Only complete, stop-terminated exact-schema JSON is eligible; invalid outputs are not repaired or retried.

`natural_summary.json` distinguishes complete responses, accepted output format, valid typed structure and in-range source spans, nonempty eligible documents, empty valid documents, and exact nonempty source-withheld cycles. Structural acceptance and valid span bounds do not demonstrate that the cited text entails the generated formula. The source-withheld cycle uses the unpatched native compiler and measures consistency, not independent semantic fidelity. No human accuracy or native proof rate is inferred from these natural outputs. The separate constructed proof study is in the sibling `proof` bundle.

`inference_wall_seconds` sums request wall time only for requests with a returned body; the failed request's elapsed time remains included in `total_record_wall_seconds`, together with structural and cycle processing. Output token counts cover returned API usage; a timed-out server generation cannot be assigned an invented token count. Model loading and infrastructure wall time are recorded separately.

The resource envelope was amended while the original model was loaded: the historical launch recorded 900 seconds, then the user requested one warm model and a 10000-second total wall bound. The verified live systemd override superseded the original wall limit without changing prompts, sample, token budgets, scoring or model identity. The same server is retained across natural client batches and shut down after completion. Resource receipts preserve this chronology, including the inherited process CPU cap. The permanent service was not unmasked.

`MANIFEST.json` provides both original and bundled SHA256 hashes. Only identifying local host paths in receipts, lifecycle records and documentary source are replaced with <WORKSPACE>, <HOME>, or <UID>; scientific request/response/result bytes and source text are unchanged. The manifest does not claim a hash of itself. `MODEL_IDENTITY.json` distinguishes the actual Leanstral 1.5 NVFP4 weights from ancestor 2603 lineage metadata.
'''
    (DEST / 'README.md').write_text(readme)
    entries.append(dict(bundle_path='README.md', original_artifact='generated documentation', original_sha256=None, bundle_sha256=sha(readme.encode()), transformation='new documentation, no scientific data changed'))
    manifest = dict(schema='anonymous-direct-model-natural100-bundle/v1', planned=100, terminal_attempts=100, model_calls=100, independent_semantic_fidelity_measured=False, redaction_policy='Exact scientific bytes retained; only local host paths in receipts/documentary source anonymized, with original and bundled hashes.', files=entries)
    (DEST / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    size = sum(path.stat().st_size for path in DEST.rglob('*') if path.is_file())
    assert size < 20_000_000, size
    print(json.dumps(dict(bundle=str(DEST), files=len(entries) + 1, bytes=size)))


if __name__ == '__main__':
    main()
