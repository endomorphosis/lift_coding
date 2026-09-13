"""Reduce retained signed-client pilot terminals; never dispatch or rescore."""
import sys
sys.dont_write_bytecode = True
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

OP = Path(__file__).resolve().parent.parent
ACTIVATION = '4757277bc5ba71c780478c6b74e7b636e4de847db95becd10ac06652a82962eb'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path, bindings, expected=None):
    path = Path(path)
    assert path.is_file() and not path.is_symlink(), str(path)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert expected is None or digest == expected, str(path)
    assert str(path) not in bindings or bindings[str(path)] == digest
    bindings[str(path)] = digest
    return json.loads(raw)


def write(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())



def original_terminal_path(private, disposition):
    """Select only the signed protocol-defined original, never an arbitrary path."""
    if disposition is None:
        return private / 'result.json'
    names = {'candidate_rejected': 'proposal_result.json',
             'known_proposal_failure': 'result.json',
             'known_scorer_failure': 'result.json'}
    name = names[disposition['classification']]
    assert disposition['original_filename'] == name, 'Disposition original filename differs'
    path = private / name
    digest = sha(path)
    assert disposition['original_receipt_sha256'] == digest
    assert disposition['binding']['original_receipt_sha256'] == digest
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args()
    bindings = {str(Path(__file__).resolve()): sha(__file__)}
    a = read(OP / 'activation.private.json', bindings, ACTIVATION)
    batch = read(a['batch']['path'], bindings, a['batch']['sha256'])
    assert len(a['ordered_cells']) == 24 and len(set(a['ordered_cells'])) == 24
    assert a['ordered_cells'] == batch['planned_cells'] == batch['enabled_cells']
    rows = []
    pending_seen = False
    for n, cell in enumerate(a['ordered_cells'], 1):
        meta = a['amendments'][cell]
        amendment = read(meta['path'], bindings, meta['sha256'])
        row = dict(number=n, cell_id=cell, unit=meta['unit'], arm=meta['arm'],
                   repetition=meta['repetition'], cache='local_cold')
        terminal_path = OP / f'cell{n:03}_terminal.private.json'
        private = Path(a['private_root']) / cell
        if not terminal_path.exists():
            pending_seen = True
            assert args.allow_partial, f'Cell {n} has no verified terminal'
            row.update(terminal=False, useful_completion=None,
                       outcome='prepared_nonterminal' if private.exists() else 'unissued_pending')
            rows.append(row)
            continue
        assert not pending_seen, 'Non-prefix terminal sequence'
        terminal = read(terminal_path, bindings)
        assert terminal['terminal_verified'] is True and terminal['cell_id'] == cell
        assert terminal['batch_sha256'] == a['batch']['sha256']
        execution = read(terminal['client_execution']['path'], bindings,
                         terminal['client_execution']['sha256'])
        client = read(terminal['client_result']['path'], bindings,
                      terminal['client_result']['sha256'])
        assert execution['success'] is True and execution['cleanup_exit_code'] == 0
        assert client['terminal'] is True and len(client['results']) == 1
        assert client['batch_sha256'] == a['batch']['sha256']
        result = client['results'][0]
        assert result['cell_id'] == cell
        verified = result['result']['host_verified']
        assert verified['signature_and_scope_verified'] is True
        assert (verified.get('terminal_failure') is True
                or verified.get('admitted_historical_pilot') is True)
        scalar = terminal['cold_scalar_result']
        assert scalar == result['result']['cold_scalar_result']
        disposition = None
        if terminal['terminal_failure']:
            disposition = read(private / 'disposition.json', bindings,
                               scalar['failure_disposition_sha256'])['receipt']
        original_path = original_terminal_path(private, disposition)
        original = read(original_path, bindings)
        body = original['receipt']
        assert body['cell_id'] == cell and body['batch_sha256'] == a['batch']['sha256']
        assert body['amendment_sha256'] == meta['sha256']
        assert body['unit'] == meta['unit'] and body['arm'] == meta['arm']
        assert body['repetition'] == meta['repetition'] and body['cache'] == 'local_cold'
        assert body['final_scientific_run'] is False
        if 'human_annotation' in body:
            assert body['human_annotation'] is False
        assert body['provider_termination']['termination_proven'] is True
        proposer = read(private / 'http_proposer/result.json', bindings,
                        body['proposal_result_sha256'])
        cleanup = read(private / 'http_proposer/cleanup.json', bindings,
                       body['provider_termination']['cleanup_sha256'])
        assert cleanup['returncode'] == 0
        assert cleanup['container'] == body['provider_termination']['container_id']
        provider = proposer['provider']
        assert provider['attempted_posts'] == 1
        grant = read(private / 'grant.json', bindings, body['grant_sha256'])
        assert grant['batch_binding']['cell_id'] == cell
        assert grant['batch_binding']['sha256'] == a['batch']['sha256']
        assert grant['profile'] == body['profile']
        assert grant['request_binding'] == body['request_binding']
        assert scalar['human_annotation'] is False
        if terminal['terminal_failure']:
            assert disposition['binding']['cell_id'] == cell
            assert disposition['success_credit'] is False and disposition['retry_allowed'] is False
            outcome = ('proposal_child_deadline' if provider.get('absolute_timeout') is True else
                       'candidate_parser_failure' if proposer.get('parse_error') else
                       disposition['classification'])
            useful = False
        else:
            assert scalar['cold_full_validation'] is True
            useful = scalar['candidate_valid'] is True
            outcome = 'full_cold_pass' if useful else body['scorer']['scorer']['classification']
        for name in ('operator_review.json', 'operator_disposition.json'):
            if (private / name).exists():
                read(private / name, bindings)
        row.update(terminal=True, outcome=outcome, useful_completion=useful,
                   original_receipt_filename=original_path.name,
                   actual_provider_posts=provider['attempted_posts'],
                   provider_status=provider.get('status'), http_status=provider.get('http_status'),
                   served_model=provider.get('served_model'), served_revision=provider.get('served_revision'),
                   response_bytes=provider.get('response_bytes'), parse_error=proposer.get('parse_error'),
                   gateway_proposal_elapsed_seconds=body['elapsed_seconds'],
                   http_wrapper_elapsed_seconds=proposer['elapsed_seconds'],
                   provider_child_elapsed_seconds=provider.get('elapsed_seconds'),
                   gateway_score_elapsed_seconds=body.get('score_elapsed_seconds'),
                   gateway_score_elapsed_scope=body.get('score_elapsed_seconds_scope'),
                   actual_cold_scored=scalar['cold_full_validation'],
                   visible_passed=scalar.get('visible_passed'), visible_collected=scalar.get('visible_collected'),
                   hidden_passed=scalar.get('hidden_passed'), hidden_collected=scalar.get('hidden_collected'),
                   usage=provider.get('usage'), settled_provider_cost=proposer['settled_provider_cost'],
                   unknown_external_charge=body.get('unknown_external_charge'),
                   signed_terminal_path=str(terminal_path), signed_terminal_sha256=sha(terminal_path))
        rows.append(row)
    terminal_rows = [r for r in rows if r['terminal']]
    groups = []
    for unit in sorted({r['unit'] for r in rows}):
        for arm in ('A', 'B'):
            group = [r for r in rows if r['unit'] == unit and r['arm'] == arm]
            assert len(group) == 3
            groups.append(dict(unit=unit, arm=arm, planned=3,
                               terminal=sum(r['terminal'] for r in group),
                               useful=sum(r.get('useful_completion') is True for r in group),
                               outcomes=dict(collections.Counter(r['outcome'] for r in group))))
    usage_names = ('prompt_tokens', 'completion_tokens', 'total_tokens', 'cost_in_usd_ticks')
    observed_usage = {name: {'known_sum': sum(r['usage'].get(name, 0) for r in terminal_rows
                                            if isinstance(r['usage'], dict) and name in r['usage']),
                             'observed_cells': sum(isinstance(r['usage'], dict) and name in r['usage']
                                                   for r in terminal_rows)} for name in usage_names}
    summary = dict(schema='ns028-pilot-retained-evidence-analysis/v1',
                   analyzed_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                   complete=len(terminal_rows) == 24, planned_cells=24,
                   terminal_cells=len(terminal_rows), unissued_or_nonterminal=24-len(terminal_rows),
                   actual_provider_posts=sum(r['actual_provider_posts'] for r in terminal_rows),
                   actual_cold_scores=sum(r['actual_cold_scored'] for r in terminal_rows),
                   outcomes=dict(collections.Counter(r['outcome'] for r in rows)),
                   useful_completions=sum(r['useful_completion'] for r in terminal_rows),
                   observed_api_usage=observed_usage,
                   gateway_proposal_elapsed_sum_seconds=sum(r['gateway_proposal_elapsed_seconds'] for r in terminal_rows),
                   gateway_score_elapsed_known_sum_seconds=sum(r['gateway_score_elapsed_seconds'] for r in terminal_rows
                                                               if r['gateway_score_elapsed_seconds'] is not None),
                   statistical_scope='Descriptive developmental pilot:4 independent historical families, A/B paired,3 nested repetitions. No24-independent-repository or final inference.',
                   cost_scope='API usage/ticks are reported observations, not settled charges. Missing measurements remain null; observed sums are not complete cost. Child, HTTP wrapper and gateway durations are nested and are not added together. Shared historical context preparation is charged once outside this reducer. Prior6 protocol failures plus1 diagnostic and all setup/metadata/authoring costs remain separate retained accounting.',
                   verification_scope='Hashes of retained actual typed-client verification and signed host evidence are rechecked. This reducer does not rerun cryptographic verification, native analysis, model, scorer or any effect.',
                   final_admitted=False, native_task_completed=False, new_provider_calls=0,
                   new_scorer_calls=0, batch_sha256=a['batch']['sha256'], groups=groups, rows=rows)
    args.output.mkdir(mode=0o700)
    write(args.output / 'analysis.private.json', summary)
    write(args.output / 'bindings.private.json', bindings)
    print(json.dumps({'analysis': str(args.output / 'analysis.private.json'),
                      'sha256': sha(args.output / 'analysis.private.json'),
                      'bindings_sha256': sha(args.output / 'bindings.private.json'),
                      'complete': summary['complete'], 'terminal_cells': len(terminal_rows),
                      'outcomes': summary['outcomes']}))


if __name__ == '__main__':
    main()
