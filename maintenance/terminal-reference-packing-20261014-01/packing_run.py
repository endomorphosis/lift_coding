"""Current public source -> native context -> exact reference packing controls."""
import argparse
import json
from pathlib import Path
import resource
import time
import traceback
from packing_io import ROOT, FALSE, inputs, read, write, wire, sha, pin
from capsule_run import source_repository, check_lease

POLICY = {'schema': 'terminal-reference-packing-policy@1', 'sources': 5, 'tasks': 4,
 'source_total_bytes': 15788, 'context_input_tokens_max': 20000,
 'full_instruction_bytes_required': True, 'all_task_sources_required': True,
 'unresolved_requirements_retained': True, 'source_body_execution': False,
 'outer_wall_seconds': 300, 'native_shared_memory_mb': 1024,
 'optimizer_candidate_evaluations_per_packet_max': 64,
 'provider_usage': None, 'worker_delivery': 'unexecuted; local counterfactual only', **FALSE}

def restore_variant(name, text, original):
    from benchmarks.agent_supervisor.container_coding.terminal_semantic_context_transport import (
        decode_context_packet, canonical_context_packet)
    from reference_codec import decode_reference_packet
    from nested_context import restore_context_strings
    if name == 'native_dictionary':
        restored = canonical_context_packet(decode_context_packet(text))
    elif name == 'reference_original':
        restored = canonical_context_packet(decode_reference_packet(text,
            expected_packet_sha256=sha(original.encode('utf-8'))))
    elif name == 'reference_lifted':
        restored = restore_context_strings(decode_reference_packet(text))
    else:
        raise ValueError('unknown closed packing variant')
    if restored != original:
        raise ValueError('complete original native context differs after expansion')
    return restored

def pack_projection(projection, instruction, descriptor):
    from benchmarks.agent_supervisor.container_coding.terminal_semantic_context_transport import encode_context_packet
    from reference_codec import optimize_reference_packet
    from nested_context import lift_context_strings, validate_source_complete
    from token_cost_review import load_tokenizer
    rendered = projection['rendered']
    document = lift_context_strings(rendered)
    validation = validate_source_complete(rendered=rendered, doc=document,
        instruction_bytes=instruction, source_views=projection['source_views'])
    original = optimize_reference_packet(json.loads(rendered), descriptor)
    lifted = optimize_reference_packet(document, descriptor)
    variants = {
        'native_dictionary': {'wire': encode_context_packet(json.loads(rendered)), 'diagnostics': None},
        'reference_original': {'wire': original['text'], 'diagnostics': original['diagnostics']},
        'reference_lifted': {'wire': lifted['text'], 'diagnostics': lifted['diagnostics']},
    }
    tokenizer, _ = load_tokenizer(descriptor)
    for name, value in variants.items():
        restore_variant(name, value['wire'], rendered)
        value.update({'whole_wire_local_bpe_tokens': len(tokenizer.encode(value['wire'])),
            'wire_bytes': len(value['wire'].encode('utf-8')),
            'original_context_sha256': sha(rendered.encode('utf-8')),
            'exact_original_context_restored': True, **FALSE})
    return {'schema': 'terminal-source-complete-reference-packing@1',
        'task_id': projection['task_id'], 'validation': validation,
        'nested_document': document, 'variants': variants, **FALSE}

def build_contexts(*, output, structural, corpus, instructions, native, metadata, tokenizer, descriptor, lease):
    from native_structural_ir import _owner
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_accelerate_py.agent_supervisor.planning.structural_codebase_context import run_with_structural_codebase_context
    from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as metadata_api
    from packing_metadata import select_task_rows
    from context_projection import compile_task_context, task_capsule_summaries
    head = CodebaseHead.from_dict(structural['head'])
    metadata_api.validate_codebase_ir_metadata(output=output/'metadata', expected=metadata['native_metadata'], fresh_process=False)
    def build(context):
        materials = context.to_plan_create_materials()
        tasks = []
        for task in corpus['tasks']:
            check_lease(lease)
            sources, codecs = select_task_rows(metadata_output=output/'metadata', native_metadata=metadata['native_metadata'],
                task=task, head=context.head.to_dict())
            projection = compile_task_context(task=task, instruction=instructions[task['task_id']],
                head=context.head.to_dict(), source_rows=sources, codec_rows=codecs,
                capsule_summaries=task_capsule_summaries(native['capsules'], set(sources)),
                tokenizer=tokenizer, arm='raw')
            packing = pack_projection(projection, instructions[task['task_id']], descriptor)
            tasks.append({'task_id': task['task_id'], 'projection': projection, 'packing': packing})
        return {'tasks': tasks, 'native_structural_context': context.to_dict(),
            'native_plan_materials': {'scan': materials.scan, 'extra': materials.extra,
                'current_facts_count': len(materials.current_facts), 'current_roots': None},
            'native_context_compiler_exercised': True, 'native_plan_create_service_activated': False,
            'source_views_selected_through_actual_duckdb': True,
            'data_not_published_inside_observation': True, **FALSE}
    with _owner(output/'structural', existing=True) as (index, _):
        result = run_with_structural_codebase_context(index, output/'source-repository', build,
            repository_id=head.repository_id, expected_head=head, parent_lease=lease,
            admission_timeout_seconds=20, timeout_seconds=120, memory_mb=256)
    metadata_api.validate_codebase_ir_metadata(output=output/'metadata', expected=metadata['native_metadata'], fresh_process=False)
    return result

def measure_contexts(contexts, descriptor):
    from packing_costs import evaluate_packing_costs
    results = []
    for task in contexts['tasks']:
        rendered = task['projection']['rendered']
        for name, variant in sorted(task['packing']['variants'].items()):
            # The actual codecs restore first. No source-expansion differential
            # is added: both arms already preserve the original raw sources.
            restore_variant(name, variant['wire'], rendered)
            followups = ('Continue planning using every required source and unresolved instruction.',
                'Check the remaining obligations against the same complete source context.')
            for scenario, turns, retry in [('one_turn', (), False),
                    ('three_turn_history', followups, False),
                    ('three_turn_history_retry', followups, True)]:
                report = evaluate_packing_costs(task_id=task['task_id'], original_rendered=rendered,
                    encoded_wire=variant['wire'], candidate_name=name,
                    codec_kind={'native_dictionary':'native', 'reference_original':'reference',
                        'reference_lifted':'reference-lifted'}[name],
                    restore=lambda text: restore_variant(name, text, rendered),
                    script_name='one_turn' if scenario=='one_turn' else 'three_turn_history',
                    followup_instructions=turns, retry_last=retry, tokenizer_descriptor=descriptor)
                results.append({'task_id': task['task_id'], 'variant': name, 'scenario': scenario, 'measurement': report})
    return {'schema': 'terminal-reference-packing-cost-scripts@1', 'pairs': results,
        'counterfactual': True, 'provider_usage': None, 'actual_provider_invocations': 0, **FALSE}

FILES = ['policy.json', 'corpus-manifest.json', 'lineage.json', 'structural-report.json', 'native-capsules.json',
    'codec-views.json', 'tokenizer.json', 'metadata-report.json', 'contexts.json', 'costs.json']

def run(output):
    resource.setrlimit(resource.RLIMIT_CPU, (240, 240))
    resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32*1024**2, 32*1024**2))
    if output.resolve() != output or output.parent != ROOT or output.exists():
        raise ValueError('exclusive owned experiment required')
    output.mkdir(mode=0o700)
    write(output/'policy.json', POLICY)
    started = time.monotonic()
    corpus, bodies, instructions, lineage = inputs()
    write(output/'corpus-manifest.json', corpus); write(output/'lineage.json', lineage)
    repository = source_repository(output, bodies)
    for task in corpus['tasks']:
        directory = output/'instructions'/task['task_id']; directory.mkdir(parents=True)
        with (directory/'instruction.md').open('xb') as stream: stream.write(instructions[task['task_id']])
    from native_structural_ir import prepare_structural_ir, _scheduler, verify_structural_ir
    structural = prepare_structural_ir(repository=repository, output=output/'structural',
        repository_id='terminal-reference-packing-20261014-01:'+output.name,
        expected_sources={p: sha(raw) for p, raw in bodies.items()})
    write(output/'structural-report.json', structural)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from native_capsules import build_native_capsules
    from capsule_codec import build_capsule_codec
    from token_cost_review import load_tokenizer
    from packing_metadata import build_records
    from metadata_projections import hydrate_and_verify_records
    with _scheduler().acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=1024, child_process_slots=1,
            timeout=30, request_id='terminal-reference-packing:context-cost') as lease:
        check_lease(lease)
        native = build_native_capsules(CodebaseIRManifest.from_dict(structural['manifest']), CodebaseHead.from_dict(structural['head']))
        write(output/'native-capsules.json', native)
        codecs = {s['path']: {arm: build_capsule_codec(bodies[s['path']], s['path'], s['source_cid'],
            structural['head'], aliases=arm=='aliased') for arm in ['minified', 'aliased']} for s in structural['sources']}
        write(output/'codec-views.json', codecs)
        tokenizer, descriptor = load_tokenizer(); write(output/'tokenizer.json', descriptor)
        records = build_records(structural=structural, bodies=bodies, instructions=instructions, corpus=corpus,
            native=native, codecs=codecs, lineage=lineage)
        with lease.acquire_child(lane=ResourceLane.PERSISTENCE, cpu_slots=1, memory_mb=256, child_process_slots=1,
                timeout=20, request_id='terminal-reference-packing:metadata') as child:
            check_lease(child)
            metadata = hydrate_and_verify_records(records=records, output=output/'metadata',
                source_snapshot={'schema': 'terminal-reference-packing-snapshot@1', 'head': structural['head'],
                    'native_capsule_set_id': native['capsule_set_id'], 'codec_views_sha256': sha(wire(codecs)),
                    'instructions': {key: sha(value) for key, value in instructions.items()}})
        write(output/'metadata-report.json', metadata)
        contexts = build_contexts(output=output, structural=structural, corpus=corpus, instructions=instructions,
            native=native, metadata=metadata, tokenizer=tokenizer, descriptor=descriptor, lease=lease)
        # Publish derived candidates only after the genuine owner exit check.
        write(output/'contexts.json', contexts)
        costs = measure_contexts(contexts, descriptor); write(output/'costs.json', costs)
    verify_structural_ir(repository=repository, output=output/'structural', expected=structural)
    if inputs()[3] != lineage: raise ValueError('selected sealed public inputs changed')
    artifacts = [{'relative_path': name, **{k: v for k, v in pin(output/name).items() if k != 'path'}} for name in sorted(FILES)]
    result = {'schema': 'terminal-reference-packing-experiment@1', 'completed': True, 'policy': POLICY,
        'native_head': structural['head'], 'source_count': 5, 'task_count': 4,
        'native_capsule_inventory': native['complete_inventory'], 'metadata_original_record_counts': metadata['family_counts'],
        'context_compilations': 4, 'exact_context_variant_roundtrips': 12, 'local_script_pairs': len(costs['pairs']),
        'artifact_pins': artifacts, 'provider_invocations': 0, 'new_optimizer_updates': 0, 'new_prover_invocations': 0,
        'source_body_execution': False, 'planning_requirements_all_unresolved': True,
        'seconds': time.monotonic()-started, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, **FALSE}
    write(output/'result.json', result)
    print(json.dumps({'completed': True, 'seconds': result['seconds'], 'pairs': len(costs['pairs']), 'provider_invocations': 0}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True); args = parser.parse_args()
    try: run(Path(args.output))
    except BaseException as error:
        output = Path(args.output)
        if output.is_dir() and not (output/'failure.json').exists():
            write(output/'failure.json', {'class': type(error).__name__, 'message': str(error), **FALSE})
        traceback.print_exc(); raise
