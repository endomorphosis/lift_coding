#!/usr/bin/env python3
"""Publish the complete paired scheduler receipts with explicit byte custody."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
DEST = EXPERIMENT / 'supplement_staging/guidance'
SEEDS = (104729, 130363, 155921)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    summary = json.loads((HERE / 'final_join/summary.json').read_text())
    assert summary['split'] == 'final'
    assert summary['pooled_descriptive']['counts']['records'] == 5739
    assert summary['pooled_descriptive']['counts']['actual_check_calls'] == 34434
    assert all(summary['seed_reports'][str(seed)]['counts']['records'] == 1913 for seed in SEEDS)
    assert (DEST / 'reproduce_guidance.py').is_file()
    assert not (DEST / 'MANIFEST.json').exists(), 'Refuse to overwrite a finalized bundle'
    entries = []

    def copy(source, relative, scientific=False):
        raw = source.read_bytes()
        public = raw
        if scientific:
            assert b'/home/barberb' not in raw, relative
        else:
            public = raw.replace(b'/home/barberb/lift_coding', b'<WORKSPACE>').replace(b'/home/barberb', b'<LOCAL_HOME>')
        target = DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(public)
        entries.append(dict(bundle_path=str(relative), original_artifact=str(source.relative_to(EXPERIMENT)),
                            original_sha256=sha(raw), bundle_sha256=sha(public),
                            transformation='byte-identical' if raw == public else 'host-path redaction in documentary receipt only'))

    for name in ['summary.json', 'derived_inputs.json'] + [f'paired_seed{seed}.jsonl' for seed in SEEDS]:
        copy(HERE / 'final_join' / name, name, scientific=True)
    copy(HERE / 'final_join/head_distribution_audit.json', 'head_distribution_audit.json', scientific=True)
    for name in ['learned_route.py', 'structural_checks.py', 'evaluate_guidance.py', 'audit_final_heads.py']:
        copy(HERE / name, Path('source') / name)
    for name in ['qualification.json', 'qualified_replays.json', 'engineering_review_autoencoder.json',
                 'collector_engineering_review.json', 'collector_binding_addendum.json', 'final_join_inputs.json']:
        copy(HERE / name, Path('qualification') / name)
    for seed in SEEDS:
        for source in sorted((HERE / f'qualification_v5_seed{seed}').glob('*.json')):
            copy(source, Path('qualification') / f'seed{seed}' / source.name)
    readme = '''This bundle contains the full learned-check scheduling experiment: 1,913 native C source candidates at each of three retained T3 seeds, with paired off/on/rollback executions and 34,434 actual structural check calls. All source–seed pairs remain in the denominator, including empty candidates and check failures. `summary.json` is byte-identical to the original final collector result, and all paired observations are retained unchanged.

Run `python reproduce_guidance.py --output reproduced_guidance.json` with Python 3.9 or later. The standard-library-only script verifies manifest hashes, unique complete populations, per-callback result digests, unchanged candidate/checker identities, both required check calls, eligibility, learned ordering and rollback. It recomputes every per-seed and pooled count and timing summary and requires exact equality with the published result. It does not invoke models, the native compiler, or native checks again. Fresh inference additionally requires the omitted original checkpoints and runtime. Existing output reports are never overwritten.

The frozen baseline runs modal_well_formedness followed by provenance_preservation. T4 ranks these two required checks using the actual T3 obligation_family categorical probabilities from the fixed frame_logic context. Every required check runs in every condition; there is no early acceptance, skipped check, semantic-field rewriting or replacement of native proof trust. Off/on/rollback use isolated copies of the identical candidate and unchanged checker callbacks. The two checks establish registered typed structure and source-span binding, not that the legal source entails the representation and not Lean kernel proof acceptance. Empty valid representations are separate from nonempty eligible coverage.

`head_distribution_audit.json` describes the already emitted native T3 heads across all sources and fixed contexts. Constant learned priors can change the scheduling order, but they do not discriminate source-specific correctness. A singleton categorical vocabulary yields probability one by construction; this is not calibrated confidence in proof truth or semantic fidelity. T3 decoder values are tied to T2 and these consumed head outputs are not counted as independent decoder runs. The historical proposed adapter that would alter canonical semantic fields was not implemented.

Off, on and rollback execute in the same fixed condition order. Timing differences are descriptive replay costs, not a speedup estimate. Source–seed pairs reuse the same 1,913 sources and are not 5,739 independent natural documents. `source/` contains the exact frozen scheduler, structural checker and collector code for inspection; those scripts rely on the original external runtime for fresh execution. `qualification/` includes the frozen admission evidence, CID-backed qualification, independently reviewed code bindings, and constructed canary outcomes, separate from final natural measurements.

The source-only predictor binds full-source and parser-prefix hashes separately. The scheduler consumes the first-4096-character parser hash for comparison with native C; the collector verifies full-source identity as well. The source texts and native C outputs are available in the sibling pipeline bundle. `MANIFEST.json` records each original and published SHA256, including any local-host-path redaction in documentary receipts. Scientific summary, paired observation and head-audit bytes are unchanged. Original artifact hashes remain distinct from published hashes; no frozen scientific identifier is silently recomputed.
'''
    (DEST / 'README.md').write_text(readme)
    for name in ['README.md', 'reproduce_guidance.py']:
        entries.append(dict(bundle_path=name, original_artifact='generated portable documentation/code', original_sha256=None,
                            bundle_sha256=sha((DEST / name).read_bytes()), transformation='new reproduction support; no scientific observation changed'))
    manifest = dict(schema='anonymous-learned-check-scheduling-bundle/v1', source_records=1913,
                    source_seed_pairs=5739, actual_check_calls=34434, new_model_calls_in_reproduction=0,
                    new_native_check_calls_in_reproduction=0, files=entries)
    (DEST / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(files=len(entries) + 1, manifest_sha256=sha((DEST / 'MANIFEST.json').read_bytes()))))


if __name__ == '__main__':
    main()
