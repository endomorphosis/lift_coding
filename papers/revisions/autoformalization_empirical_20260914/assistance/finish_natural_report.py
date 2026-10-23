#!/usr/bin/env python3
"""Render paper-ready natural-arm facts from all frozen terminal attempts."""
import collections
import datetime
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    rows = [json.loads(line) for line in (HERE / 'natural_model/results.jsonl').read_text().splitlines()]
    sources = [json.loads(line) for line in (HERE.parent / 'pipeline/final_a100.sources.jsonl').read_text().splitlines()]
    summary = json.loads((HERE / 'natural_summary.json').read_text())
    assert summary['attempted'] == len(rows) == len({row['record_id'] for row in rows}) == 100
    valid = [row for row in rows if row['status'] == 'measured' and all(check['passed'] for check in row.get('checks', {}).values())]
    errors = collections.Counter(row.get('error', '') for row in rows if row['status'] != 'measured')
    failed_checks = collections.Counter(name for row in rows for name, check in row.get('checks', {}).items() if not check['passed'])
    server_log = (HERE / 'natural_job_01.log').read_text()
    ready = re.search(r'"event": "server_ready", "elapsed_seconds": ([0-9.]+)', server_log)
    cpu_rows = [json.loads(line) for line in (HERE / 'warm_cpu_observations.jsonl').read_text().splitlines()]
    lifecycle = [json.loads(line) for line in (HERE / 'warm_lifecycle.jsonl').read_text().splitlines()]
    completed = [row for row in lifecycle if row['event'] == 'all100_complete_same_model']
    cleanup = [row for row in lifecycle if row['event'] == 'warm_cleanup']
    assert completed and cleanup and cleanup[-1]['completed'] == 100 and cleanup[-1]['port8080closed'] and not cleanup[-1]['server_alive']
    start = datetime.datetime.fromisoformat('2026-09-14T08:09:46+00:00')
    end = datetime.datetime.fromisoformat(cleanup[-1]['at'])
    numbers = dict(schema='direct-model-natural100-paper-ready/v1', summary=summary,
                   error_counts=dict(errors), failed_native_check_counts=dict(failed_checks),
                   valid_formula_family_counts=dict(sum((collections.Counter(row.get('family_counts', {})) for row in valid), collections.Counter())),
                   source_unit_family_counts=dict(collections.Counter(row['family'] for row in sources)),
                   source_prefix_truncated_records=sum(row['source_truncated'] for row in rows),
                   evaluated_source_characters=sum(row['evaluated_chars'] for row in rows),
                   failed_request_record_wall_seconds=sum(row['wall_seconds'] for row in rows if row['status'] == 'request_failed'),
                   model_startup_seconds=float(ready.group(1)) if ready else None,
                   natural_model_instances=1, reloads_between_natural_batches=0,
                   wall_seconds_unit_start_through_cleanup=(end - start).total_seconds(),
                   last_observed_server_CPU_seconds=cpu_rows[-1]['server_cpu_seconds'],
                   user_requested_hard_wall_seconds=10000, per_request_timeout_seconds=60,
                   model=dict(name='Leanstral 1.5 119B A6B', quantization='Frosty40 NVFP4 GGUF', weight_sha256='4668fd2a6d2764de250489852230e96238eb5c0d7495866eb3b9c6c4fac5c7da', temperature=0, seed=20260914, output_token_limit=2048),
                   results_sha256=hashlib.sha256((HERE / 'natural_model/results.jsonl').read_bytes()).hexdigest(),
                   no_independent_semantic_fidelity_or_native_proof_claim=True)
    (HERE / 'natural_paper_ready_numbers.json').write_text(json.dumps(numbers, indent=2) + '\n')
    text = f'''The frozen direct-model arm completed all 100 planned natural-source attempts with one Leanstral 1.5 NVFP4 model instance. {summary['responses']} requests returned a response body; {summary['statuses'].get('request_failed', 0)} failed requests remain in the denominator. {summary['formats_accepted']} responses passed the exact output schema. The same native registry/type and source-span checks used for the compiler arms accepted {summary['structural_and_provenance_pass']}/100 documents: {summary['nonempty_eligible']} were nonempty and {summary['empty_valid']} were empty. The eligible nonempty documents contained {summary['formula_count']} formulas. There were {summary['exact_nonempty_cycles']} exact nonempty source-withheld cycles, with {summary['cycles_measured']} cycles measured in total.

These are structural coverage and consistency measurements. They do not establish legal semantic fidelity, support of each formula by its cited span, or native theorem validity. For example, the retained output for cfr:37:102.30:2024 assigns obligation to a source opening that says the USPTO may disclose a record; its spans all point to characters 0–100. The frozen checks accept in-range spans and registered structure, so this qualitative example illustrates a limitation rather than a new annotated accuracy estimate. No scoring, prompt or output repair was introduced after observing it.

Returned requests consumed {summary['inference_wall_seconds']:.3f} seconds in total and reported {summary['prompt_tokens']} prompt tokens and {summary['completion_tokens']} completion tokens. The total per-record wall time was {summary['total_record_wall_seconds']:.3f} seconds, including {numbers['failed_request_record_wall_seconds']:.3f} seconds for failed requests plus structural/cycle processing. Token usage is unavailable for a timed-out request; it has not been fabricated. Model startup took {numbers['model_startup_seconds']:.3f} seconds. The same loaded model was retained across all natural client batches; total time from transient-unit start through cleanup was {numbers['wall_seconds_unit_start_through_cleanup']:.3f} seconds.

The total wall bound was changed prospectively for active work from the historical 900-second launch to 10000 seconds at the user's request. The model, sample, prompt, 2048-token output limit, 60-second request limit and one-attempt policy remained unchanged. The final cleanup confirms that the model process exited and port 8080 closed; the permanent service remained masked. The historical wrapper's obsolete deadline may report a cleanup timeout after its watchdog is resumed. The authoritative scientific completion evidence is the 100 unique terminal records, warm-controller completion event and verified cleanup.

The exact terminal rows and raw request/response files are in `natural_model/`. `natural_provenance_audit.json` checks the frozen source input, request parameters, hashes and unedited model semantic fields. `natural_paper_ready_numbers.json` records counts, failures and costs for table generation. The portable natural supplement reproduces these recorded counts without another model call.
'''
    (HERE / 'NATURAL_RESULTS.md').write_text(text)
    print(json.dumps(numbers, indent=2))


if __name__ == '__main__':
    main()
