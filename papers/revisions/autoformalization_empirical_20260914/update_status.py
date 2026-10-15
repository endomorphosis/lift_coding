#!/usr/bin/env python3
"""Report empirical progress from durable observations, never task counts alone."""
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def count(path):
    if not path.is_file():
        return 0
    with path.open() as stream:
        return sum(bool(line.strip()) for line in stream)

def main():
    encoder = ROOT / 'autoencoder/final/source_embeddings.jsonl.receipt.json'
    status = {
        'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scientific_protocol_frozen': (ROOT / 'FINAL_PROTOCOL_FREEZE.json').exists(),
        'source_encoding_complete': encoder.exists() and json.loads(encoder.read_text())['count'] == 1913,
        'native_arm_terminal_rows': {arm: count(ROOT / f'pipeline/final_{arm}.jsonl') for arm in ['B', 'C', 'T5']},
        'native_arm_planned_each': 1913,
        'natural_model_terminal_rows': count(ROOT / 'assistance/natural_model/results.jsonl'),
        'natural_model_planned': 100,
        'projection_source_rows': sum(count(ROOT / f'autoencoder/final/worker{worker}/T0.predictions.jsonl') for worker in [0, 1]),
        'projection_source_rows_planned': 1913,
        'autoencoder_summary_complete': (ROOT / 'autoencoder/final/summary.json').exists(),
        'guidance_summary_complete': (ROOT / 'guidance/final_join/summary.json').exists(),
        'constructed_proof_summary_complete': (ROOT / 'assistance/summary.json').exists(),
        'citations_verified': (ROOT / 'citation_verification.md').exists(),
        'measured_tables_generated': (ROOT / 'editable/results/table_generation.json').exists(),
        'final_pdf_validated': (ROOT / 'paper_build_validation.json').exists() and (ROOT / 'paper_visual_review.json').exists(),
        'supplement_reproduction_complete': (ROOT / 'supplement_reproduction.json').exists(),
        'delivered': (ROOT / 'delivery_receipt.json').exists(),
        'independent_human_semantic_fidelity_measured': False,
    }
    (ROOT / 'STATUS.json').write_text(json.dumps(status, indent=2) + '\n')
    mark = lambda yes: '[x]' if yes else '[ ]'
    lines = ['# Empirical completion tasks', '', f"Observed at {status['observed_at']}. Counts come from saved observations, not the historical supervisor completion total.", '',
             '- [x] Recover and verify original learned checkpoints and native runtime.',
             f"- {mark(status['scientific_protocol_frozen'])} Freeze scientific profiles before final-source access.",
             f"- {mark(status['source_encoding_complete'])} Encode all 1,913 complete source documents with the fixed MiniLM windowing procedure."]
    for arm, done in status['native_arm_terminal_rows'].items():
        lines.append(f'- {mark(done == 1913)} Execute native {arm}: {done:,}/1,913 terminal observations, including failures.')
    lines += [f"- {mark(status['natural_model_terminal_rows'] == 100)} Execute direct-model formalization: {status['natural_model_terminal_rows']}/100 attempts; preserve one-attempt failures.",
              f"- {mark(status['autoencoder_summary_complete'])} Finish all source-conditioned projections and T1/T3 derivations, score them, and calculate component uncertainty ({status['projection_source_rows']:,}/1,913 source rows emitted so far).",
              f"- {mark(status['guidance_summary_complete'])} Execute all 5,739 learned check-order off/on/rollback source/seed pairs.",
              f"- {mark(status['constructed_proof_summary_complete'])} Complete the 64-goal native proof study and separate post-hoc policy sensitivity.",
              f"- {mark(status['citations_verified'])} Verify the original references and model-asset citations against primary sources.",
              f"- {mark(status['measured_tables_generated'])} Generate all paper tables from complete measured summaries.",
              f"- {mark(status['final_pdf_validated'])} Build and visually inspect the anonymous PDF within nine actual main pages.",
              f"- {mark(status['supplement_reproduction_complete'])} Package and reproduce all metrics/tables from a fresh anonymous ZIP extraction.",
              f"- {mark(status['delivered'])} Deliver the matching PDF, supplement, editable sources, checksums, and revised status documentation.", '',
              'Independent legal-semantic fidelity and general natural-source proof transfer remain unmeasured research questions. The current paper makes no measured claim for them. The qualified learned consumer orders structural checks; it does not implement the historical proposed canonical-semantic mutation adapter.', '',
              'These are empirical revision tasks. They do not manufacture new completion receipts in the historical supervisor database.']
    (ROOT / 'EMPIRICAL_TODO.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(status))

if __name__ == '__main__':
    main()
