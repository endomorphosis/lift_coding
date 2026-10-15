#!/usr/bin/env python3
"""Render measured tables only after every fixed empirical population is complete."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEEDS = (104729, 130363, 155921)

def read(root, name):
    return json.loads((root / name).read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def n(value):
    return f"{value:,}"

def table(caption, label, columns, header, rows):
    return ("\\begin{table}[t]\n\\centering\\small\n"
            + "\\caption{" + caption + "}\n\\label{" + label + "}\n"
            + "\\begin{tabular}{" + columns + "}\\toprule\n"
            + " & ".join(header) + "\\\\\\midrule\n"
            + "".join("\\midrule\n" if row is None else " & ".join(map(str, row)) + "\\\\\n" for row in rows)
            + "\\bottomrule\n\\end{tabular}\n\\end{table}\n")

def generate(root, output):
    inputs = {
        'pipeline': 'pipeline/summary.json',
        'ae': 'autoencoder/final/summary.json',
        'guidance': 'guidance/final_join/summary.json',
        'natural': 'assistance/natural_summary.json',
        'proof': 'assistance/summary.json',
        'proof_cost': 'assistance/paper_ready_numbers.json',
        'encoder': 'autoencoder/final/source_embeddings.jsonl.receipt.json',
    }
    data = {key: read(root, path) for key, path in inputs.items()}
    p, ae, g, a, proof = [data[k] for k in ('pipeline', 'ae', 'guidance', 'natural', 'proof')]
    assert p['population']['units'] == ae['cohort_records'] == 1913
    assert a['attempted'] == a['planned'] == 100
    assert proof['model_calls'] == proof['planned_new_goals'] == 64
    counts = g['pooled_descriptive']['counts']
    assert counts['records'] == 1913 * 3
    assert counts['learned_consumptions'] == counts['outcomes_unchanged'] == counts['rollback_passed'] == 5739
    assert counts['actual_check_calls'] == 34434 and counts.get('check_execution_errors', 0) == 0
    for seed in SEEDS:
        assert g['seed_reports'][str(seed)]['counts']['records'] == 1913
    arms = {row['arm']: row for row in ae['table']}
    assert all(row['records'] == 1913 for row in arms.values())
    cold = arms['T0']
    trained = [arms[f'T2-{seed}'] for seed in SEEDS]
    learned_cos = statistics.mean(row['mean_cosine'] for row in trained)
    seed_spread = max(row['mean_cosine'] for row in trained) - min(row['mean_cosine'] for row in trained)
    spread_mantissa, spread_exponent = f'{seed_spread:.1e}'.split('e')
    spread_tex = rf'${spread_mantissa}\times 10^{{{int(spread_exponent)}}}$'
    mean = arms['TRAIN mean supplement']
    output.mkdir(parents=True, exist_ok=True)
    text = {}
    text['empirical_numbers.tex'] = (
        f"\\newcommand{{\\AEColdCosine}}{{{cold['mean_cosine']:.3f}}}\n"
        f"\\newcommand{{\\AETrainedCosine}}{{{learned_cos:.3f}}}\n"
        f"\\newcommand{{\\AETrainingMeanCosine}}{{{mean['mean_cosine']:.3f}}}\n")

    rows = []
    b = p['B']
    rows.append(['Native B', '1913', b['compile_success'], b['nonempty_compiled'], b['roundtrip_exact'], r'\textemdash'])
    for key, title in [('C', 'Native C'), ('T5', 'Repaired C (T5)')]:
        x = p[key]
        rows.append([title, 1913, x['schema_and_provenance_pass'], x['nonempty_eligible'], x['cycle_exact_nonempty'], x['cycle_statuses'].get('timeout', 0)])
    rows += [None, ['Direct model A', 100, a['structural_and_provenance_pass'], a['nonempty_eligible'], a['exact_nonempty_cycles'], a['cycle_statuses'].get('timeout', 0)]]
    x = p['matched_a100_C']
    rows.append(['Native C, same subset', 100, x['schema_and_provenance_pass'], x['nonempty_eligible'], x['cycle_exact_nonempty'], x['cycle_statuses'].get('timeout', 0)])
    text['empirical_pipeline.tex'] = table(
        'Native representation and reconstruction outcomes. A and C share structural checks on the 100-source subset. B uses its stricter native deontic contract; its whole-call timeouts cannot be assigned to a cycle phase. Counts are not source-semantic accuracy.',
        'tab:pipeline-results', 'lrrrrr', ['Method', 'Units', 'IR passes', 'Nonempty', 'Exact cycle', 'Cycle timeout'], rows)
    c = p['C']
    text['empirical_pipeline_discussion.tex'] = (
        f"Native C produces {n(c['nonempty_eligible'])} nonempty checked representations, including "
        f"{n(c['deontic_nonempty'])} units containing a deontic formula. Its {n(c['formula_count'])} "
        f"formulas span the registered logical families. Nonempty coverage alone cannot distinguish useful "
        f"formalization from spurious output. Only {n(c['cycle_exact_nonempty'])} "
        f"units reproduce their semantic-field multiset exactly; {n(c['cycle_statuses'].get('timeout', 0))} "
        "cycle attempts time out. A completed initial compilation is retained when a later cycle times out. "
        f"The source-prefix limit truncates {n(p['population']['prefix_truncated_units'])} of 1,913 inputs.\n\n"
        f"B records {n(b['compile_success'])} successful initial compilations. Its full pipeline returns "
        f"{n(b['native_statuses'].get('success', 0))} successes, {n(b['native_statuses'].get('abstained', 0))} abstentions, "
        f"{n(b['native_statuses'].get('failed', 0))} native failures, and {n(b['statuses'].get('timeout', 0))} whole-call timeouts. "
        "Its strict vocabulary and abstention contract differ from C's richer output contract, so these counts "
        "are operational coverage under different interfaces, not a ranking of semantic accuracy.\n\n"
        f"On the matched 100-unit subset, A yields {a['formats_accepted']} accepted-format responses, "
        f"{a['structural_and_provenance_pass']} passing both checks, and {a['nonempty_eligible']} nonempty checked IRs; "
        f"{a['empty_valid']} passing IRs are empty. There are {a['statuses'].get('response_rejected', 0)} format rejections "
        f"and {a['statuses'].get('request_failed', 0)} request timeouts. "
        f"C yields {p['matched_a100_C']['nonempty_eligible']} nonempty checked IRs on those same sources. "
        "Structural passage remains weaker than faithful interpretation. In one retained A output, the source's "
        "permission that the USPTO may disclose a record becomes an obligation, and the cited span covers a heading. "
        "This post-hoc example illustrates a check's limitation; it is not an annotated error-rate estimate.\n")

    memory = [arms[f'T1-{seed}'] for seed in SEEDS]
    memory_hits = sum(row['sample_memory_hits'] for row in memory)
    memory_same = all(row['mean_cosine'] == cold['mean_cosine'] and row['mean_mse'] == cold['mean_mse'] for row in memory)
    rows = [['T0 fixed cold projection', 'fixed', f"{cold['mean_cosine']:.4f}", f"{cold['mean_mse']:.6f}"]]
    rows.append(['T1 sample memory', 'three seeds', f"{statistics.mean(row['mean_cosine'] for row in memory):.4f}", f"{statistics.mean(row['mean_mse'] for row in memory):.6f}"])
    rows += [['T2 shared parameters', seed, f"{row['mean_cosine']:.4f}", f"{row['mean_mse']:.6f}"] for seed, row in zip(SEEDS, trained)]
    rows += [['T3 isolated proof heads', 'tied to T2', 'same as T2', 'same as T2'],
             ['Training-mean control', 'supplemental', f"{mean['mean_cosine']:.4f}", f"{mean['mean_mse']:.6f}"],
             ['Identity-copy control', 'analytic', '1.0000', '0.000000']]
    text['empirical_learning.tex'] = table(
        'Source-conditioned embedding reconstruction on 1,913 held-out units. T3 reuses exactly tied decoder values. The decoder has no demonstrated compression bottleneck; identity copying is exact by construction. The supplemental constant mean uses only 69 training vectors.',
        'tab:training-results', 'llrr', ['Condition', 'Seed', 'Mean cosine', 'Mean MSE'], rows)
    boot = ae['T2_minus_T0_primary_component_bootstrap']['metrics']
    co, ms = boot['cosine'], boot['mse']
    comparison = 'exceeds' if mean['mean_cosine'] > learned_cos else 'falls below'
    r = p['repair']
    repair_interval = r['changed_units_interval']['interval95']
    assert r['both_compiled'] == 1913, 'Separate one-sided compilation failures before reporting paired field changes'
    text['empirical_learning_discussion.tex'] = (
        f"The seed-averaged T2--T0 cosine difference is {co['point']:+.4f} "
        f"(component-bootstrap 95\\% interval [{co['ci95'][0]:+.4f}, {co['ci95'][1]:+.4f}]); "
        f"the MSE difference is {ms['point']:+.6f} "
        f"([{ms['ci95'][0]:+.6f}, {ms['ci95'][1]:+.6f}]). "
        f"The constant training-mean cosine {comparison} the learned projection's seed average "
        f"({mean['mean_cosine']:.4f} versus {learned_cos:.4f}). "
        f"The range of mean cosine across the three stored seeds is {spread_tex}. "
        "The cold-baseline difference alone therefore does not establish a strong representation-learning result. "
        f"T1 records {memory_hits} memory hits in {n(ae['actual_T1_memory_lookups'])} native lookups. "
        + ("Its unseen-source scores equal T0 exactly. " if memory_same else "Its scores include native cold fallback on memory misses. ")
        + "Protected-state equality establishes decoder isolation; reused T3 scores do not measure an additional gain from proof feedback.\n\n"
        f"Across {n(counts['records'])} source--seed pairs, T4 consumes learned state "
        f"{n(counts.get('learned_consumptions', 0))} times and changes check order in "
        f"{n(counts.get('order_changes', 0))} pairs. Outcomes remain unchanged in "
        f"{n(counts.get('outcomes_unchanged', 0))} pairs, with "
        f"{n(counts.get('rollback_passed', 0))} successful rollbacks and "
        f"{n(counts.get('actual_check_calls', 0))} actual check calls. "
        "This verifies consumption of the learned prior and preserves the acceptance contract; it does not "
        "demonstrate better semantic interpretation or fewer required checks.\n\n"
        f"T5 changes canonical semantic fields on {n(r['changed_units'])}/1,913 units "
        f"(component-bootstrap 95\\% interval for the changed fraction "
        f"[{100*repair_interval[0]:.1f}\\%, {100*repair_interval[1]:.1f}\\%]). "
        f"Within pairs with equal formula counts, it changes predicate fields outside the conditional-normative family on {n(r['units_with_governing_predicate_changes'])} units; it "
        f"increases explicit exception roles on {n(r['units_with_more_exception_roles'])}. "
        f"There are {n(r['schema_provenance_regressions'])} regressions in the frozen schema/provenance checks. "
        f"Cycle timeouts are {n(p['T5']['cycle_statuses'].get('timeout', 0))} with the patch and "
        f"{n(p['C']['cycle_statuses'].get('timeout', 0))} without it under concurrent execution; "
        "the patch does not improve exact-cycle coverage. "
        "These paired effects show execution of the patch; independent judgments would be needed to quantify "
        "whether each changed interpretation is correct.\n")

    rows = []
    for key, title in [('baseline', 'Fixed native tactics'), ('hammer', 'SMT-guided reconstruction'), ('model', 'Leanstral, primary policy')]:
        x = proof['arms'][key]
        rows.append([title, f"{x['valid_native_accepted']}/32", f"{x['invalid_native_accepted']}/32", x['statuses'].get('unsupported', 0)])
    interval = proof['model_minus_baseline_valid_family_bootstrap']
    text['empirical_assistance.tex'] = table(
        'Native acceptance on 64 constructed goals (32 valid, 32 invalid). Every method attempted the same fixed declarations.',
        'tab:assistance-results', 'lrrr', ['Method', 'Valid accepted', 'Invalid accepted', 'Unsupported'], rows)
    text['empirical_assistance.tex'] += (
        f"Leanstral's valid-goal acceptance differs from the baseline by {100*interval['point']:.1f} percentage "
        f"points (2,000 family-bootstrap draws; 95\\% interval "
        f"[{100*interval['percentile95'][0]:.1f}, {100*interval['percentile95'][1]:.1f}]).\n")

    encoder = data['encoder']
    execution = ae['joint_source_preparation_and_T0_T2_execution']
    rows = [['Native B, complete cohort', f"{p['B']['sum_record_wall_seconds']:.1f}", 'sum of record intervals'],
            ['Native C, complete cohort', f"{p['C']['sum_record_wall_seconds']:.1f}", 'sum of record intervals'],
            ['Repaired C, complete cohort', f"{p['T5']['sum_record_wall_seconds']:.1f}", 'sum of record intervals'],
            ['Leanstral, 64 proof calls', f"{proof['model_wall_seconds']:.1f}", 'inference requests'],
            ['Direct model A, all 100 units', f"{a['total_record_wall_seconds']:.1f}", 'sum of record intervals'],
            [f"A, {a['responses']} returned responses", f"{a['inference_wall_seconds']:.1f}", 'returned API response intervals'],
            ['Learned check-order replay', f"{g['wall_seconds']:.1f}", 'whole replay job'],
            ['Full-document MiniLM encoding', f"{encoder['wall_seconds']:.1f}", 'whole encoder job'],
            ['Projection worker 1, four arms', f"{execution['worker_wall_seconds'][0]:.1f}", 'worker including preparation'],
            ['Projection worker 2, four arms', f"{execution['worker_wall_seconds'][1]:.1f}", 'worker including preparation']]
    text['empirical_execution.tex'] = table(
        'Measured execution costs. Concurrent per-record intervals are sums, not end-to-end elapsed time or CPU time. Model request intervals exclude model loading. These scopes must not be added to enclosing job intervals.',
        'tab:execution-costs', 'lrl', ['Stage', 'Seconds', 'Scope'], rows)
    text['empirical_execution.tex'] += (
        f"The {a['responses']} returned natural-source responses account for {n(a['prompt_tokens'])} prompt and {n(a['completion_tokens'])} "
        f"completion tokens; {a['attempted']-a['responses']} failed requests have no returned token-usage report. "
        "Their observed failure wall time is included in the all-record total. "
        f"The 64 proof calls use {n(proof['model_prompt_tokens'])} and "
        f"{n(proof['model_completion_tokens'])}, respectively. Five separate serving-qualification calls use "
        f"{data['proof_cost']['qualification_inference_seconds']:.3f} request seconds and are excluded from those denominators. "
        "A failed chat-template qualification consumed 295.152 seconds of model loading and no model requests. "
        "The corrected proof job loaded in 281.246 seconds. The natural-source job loaded in 275.883 seconds, "
        "then kept that model warm across client batches under a 10,000-second wall limit. "
        "Historical launch arguments show an earlier 900-second envelope; retained runtime-override records "
        "identify the superseding limit without relabeling the original log.\n\n"
        "The host is an NVIDIA GB10 with 20 logical CPU threads and approximately 128 GB of unified memory. "
        "Compiler jobs use bounded worker pools; each worker has a 4 GiB virtual-address limit. "
        "The Python runtime is 3.12.3, spaCy 3.8.14 with en\\_core\\_web\\_sm 3.8.0, and NumPy 1.26.4. "
        "Exact runtime, model, source, code, and observation hashes are retained in the supplement. "
        f"Full-document encoding covers {n(encoder['windows'])} windows and {n(encoder['tokens'])} tokens, "
        f"using {encoder['cpu_seconds']:.1f} process-CPU seconds. The two projection workers use "
        f"{execution['cpu_seconds']:.1f} process-CPU seconds in total, including all four independently "
        "computed arms and shared source-feature preparation. Concurrent worker wall intervals are not summed "
        "as end-to-end elapsed time.\n")
    for name, body in text.items():
        (output / name).write_text(body)
    receipt = {'schema': 'measured-paper-table-generation/v1',
               'inputs_sha256': {path: sha(root / path) for path in inputs.values()},
               'generator_sha256': sha(Path(__file__)),
               'outputs_sha256': {name: sha(output / name) for name in text},
               'complete_denominators': {'sources': 1913, 'direct_model_sources': 100, 'guidance_source_seed_pairs': 5739, 'constructed_proof_goals': 64}}
    (output / 'table_generation.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt['complete_denominators']))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    generate(args.root, args.output or args.root / 'editable/results')
