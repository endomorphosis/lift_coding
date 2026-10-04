#!/usr/bin/env python3
"""Bounded saved native768 sidecar replay on source-only authored inputs.

This runner does not read the historical paragraph corpus, targets, evaluation
panels, or optimizer receipts. Saved checkpoint metadata supplies its original
training normalization; source-only native vectors are reused without encoding.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

WORKSPACE = Path('/home/barberb/lift_coding')
CAMPAIGN = WORKSPACE / 'artifacts/autoformalization-alignment-20261003'
CHECKOUT = WORKSPACE / '.worktrees/alignment-decoder-768-20261003'
BASE = '64bc5734dc82db72e955f2e809b770127e9b6cfc'
DEPENDENCY = WORKSPACE / 'artifacts/legal-ir-inference-speed-review/audit/baseline_tree'
FROZEN = WORKSPACE / 'external/ipfs_datasets/workspace/test-logs/decoder-generated-field-training-r2-20261003/experiment-source'
STATES = FROZEN.parent / 'training-r1/results/768-generated-fields-every2-2718'
AUTO = 'ipfs_datasets_py/logic/formalization/autoencoder/'
PREFIX = 'ipfs_datasets_py.logic.formalization.autoencoder.'
OUTPUT = CAMPAIGN / 'sidecar-replay-01'
MAX_RSS = 2 * 1024**3
EXPECTED = {
    'inputs': (CAMPAIGN / 'richer-embedding-01/embedding_inputs.json', '072b5e7479499bd232715ec72bfe157c0dafb80c0bb9c140423c867c9f751f99'),
    'native768': (CAMPAIGN / 'richer-embedding-01/native768_embeddings.json', 'd169295841e14829d896a81b48630d39f85537380df8e581b7440671ac49d2a9'),
    'donor': (WORKSPACE / 'artifacts/source-reconstruction-v2-20261001/run-01/legal_ir/raw_ce-1729-checkpoint.json', '6e3f4d731d798aa2732afc37bd74fec34da3267a323844975d2dab78f59f9c61'),
    'training_manifest': (FROZEN.parent / 'training-manifest.json', '41b31d2085e70bab9b666e08c9e7edd50cbe6911d64a92ef97aa0b87f36630b5'),
    'initial': (STATES / 'initial-state.json', 'e803914449287fcda4c0525b03dbaf731bba80ffc416429f510ec8e968610e1a'),
    'selected': (STATES / 'selected-state.json', 'b23f1db1169e37e235d297475bcbd7f2676ce3442158515481d4375e17df66d7'),
    'last-attempt': (STATES / 'last-attempt-state.json', '7367e01a2b7f5274258010541d9e80cb446c22a6149f33de2d29b5530ae2db4a'),
}
HELPERS = (
    'decoder_distillation_experiment', 'decoder_distillation_experiment_v2',
    'dimension_native_decoder_experiment', 'source_value_decoder_experiment',
    'decoder_cardinality_experiment', 'projected_source_decoder_experiment',
    'shared_slot_source_decoder_experiment', 'clause_source_decoder_experiment',
    'action_factorized_clause_decoder_experiment', 'ordered_clause_recurrent_decoder_experiment',
    'clause_source_context', 'long_span_count_exposure_training',
)
FALSE = dict(qualified=False, admitted=False, proof_authority=False,
    source_semantics_verified=False, source_fidelity_established=False,
    formalized=False, roundtrip_ok=False, checkpoint_promoted=False,
    lake_executed=False, optimizer_step_executed=False, training_executed=False,
    encoder_executed=False, downloads_performed=False, reference_tokens_passed=False,
    historical_corpus_read=False, historical_predictions_reproduced=False,
    production_runtime_compatible=False, optimizer_resumable=False,
    declared_assumptions_delivered=False, learned_vector_reconstruction=False)


def require(value, message):
    if not value:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def binding(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def read_pinned(path, expected):
    pin = binding(path)
    require(pin['sha256'] == expected, 'input file changed: ' + str(path))
    require(pin['bytes'] <= 8 * 1024**2, 'bounded metadata/state input required')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError('nonfinite JSON value: ' + value)

    return json.loads(path.read_bytes(), object_pairs_hook=unique,
                      parse_constant=nonfinite), pin


def load_script(relative, name, pins):
    require(binding(CHECKOUT / relative)['sha256'] == pins[relative], 'script pin changed')
    spec = importlib.util.spec_from_file_location(name, CHECKOUT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rss_guard(deadline):
    require(time.monotonic() < deadline, 'bounded replay wall deadline exceeded')
    require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 <= MAX_RSS,
            'observed process peak RSS exceeds 2 GiB')


def save(path, value):
    with path.open('xb') as stream:
        stream.write(raw(value) + b'\n')
    return binding(path)


def package_bindings():
    results = {}
    for name, module in list(sys.modules.items()):
        if name != 'ipfs_datasets_py' and not name.startswith('ipfs_datasets_py.'):
            continue
        filename = getattr(module, '__file__', None)
        if filename is None:
            continue
        path = Path(filename).resolve()
        require(path.suffix == '.py' and path.is_file(), 'unbound package module')
        require(path.is_relative_to(DEPENDENCY) or path.is_relative_to(CHECKOUT),
                'package module loaded from another source tree: ' + str(path))
        results[name] = binding(path)
    return results


def run():
    started = time.monotonic()
    deadline = started + 240
    require(not OUTPUT.exists(), 'fresh sidecar output directory required')
    require(subprocess.check_output(['git', '-C', str(CHECKOUT), 'rev-parse', 'HEAD'],
                                   text=True).strip() == BASE, 'decoder checkout HEAD differs')
    require(not subprocess.check_output(['git', '-C', str(CHECKOUT), 'status', '--porcelain=v1',
                                        '--untracked-files=normal'], text=True).strip(),
            'decoder source checkout must be clean')
    values, inputs = {}, {}
    for key, (path, sha) in EXPECTED.items():
        values[key], inputs[key] = read_pinned(path, sha)
    manifest = values['training_manifest']
    pins = manifest['extensions']
    helper_bindings = {}
    for name in HELPERS:
        relative = AUTO + name + '.py'
        current, frozen = binding(CHECKOUT / relative), binding(FROZEN / relative)
        require(current['sha256'] == frozen['sha256'] == pins[relative],
                'historical helper pin differs: ' + name)
        helper_bindings[name] = dict(current=current, frozen=frozen)
    for relative in ('scripts/ops/autoencoder/benchmark_long_span_decoder.py',
                     'scripts/ops/autoencoder/benchmark_clause_context_source_training.py'):
        current, frozen = binding(CHECKOUT / relative), binding(FROZEN / relative)
        require(current['sha256'] == frozen['sha256'] == pins[relative], 'script pin differs')
        helper_bindings[relative] = dict(current=current, frozen=frozen)
    source_inputs, lane = values['inputs'], values['native768']
    for item in (source_inputs, lane):
        require(item['payload_sha256'] == digest({k: v for k, v in item.items() if k != 'payload_sha256'}),
                'saved native input payload differs')
    require(lane['status'] == 'produced' and lane['dimension'] == 768
            and lane['input_recipe'] == 'exact_source_only'
            and lane['input_manifest_sha256'] == source_inputs['payload_sha256']
            and lane['backend_evidence']['execution_kind'] == 'observed_native'
            and lane['context_semantics_applied'] is False, 'observed source-only native768 lane required')
    require(len(source_inputs['rows']) == len(lane['receipts']) == 34, 'exact authored panel coverage required')
    receipts = {row['id']: row for row in lane['receipts']}
    require(len(receipts) == 34, 'unique native receipt IDs required')
    rows, cache, text_lookup = [], [], {}
    for source in source_inputs['rows']:
        receipt = receipts[source['id']]
        require(source['context_applied'] is False and receipt['context_applied'] is False
                and receipt['status'] == 'embedded'
                and receipt['source_sha256'] == source['source_sha256']
                == hashlib.sha256(source['source_text'].encode()).hexdigest()
                and receipt['input_sha256'] == source['input_sha256'], 'source/vector identity differs')
        vector = receipt['embedding']
        require(type(vector) is list and len(vector) == 768
                and all(type(x) in (int, float) and math.isfinite(x) for x in vector)
                and receipt['embedding_sha256'] == digest(vector)
                and abs(math.fsum(x*x for x in vector) - 1.) <= 1e-4, 'normalized native vector differs')
        require('\n\n' not in source['source_text'], 'new clause vectors required for multi-clause source')
        row = dict(id=source['id'], source_text=source['source_text'], input=vector)
        rows.append(row)
        if row['source_text'] in text_lookup:
            require(text_lookup[row['source_text']] == vector, 'identical source has different native vectors')
        else:
            text_lookup[row['source_text']] = vector
            cache.append(row)
    require(len(cache) == 33, 'expected exact-text cache deduplication differs')
    donor = values['donor']
    numerical_relative = 'ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_latent_formula.py'
    require(binding(DEPENDENCY / numerical_relative)['sha256']
            == donor['implementation']['numerical']['files']['modal_latent_formula.py'],
            'donor numerical source differs')
    # Parent package/dependency imports remain in the preserved donor tree;
    # only these versioned experimental leaf owners resolve from the clean base.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(DEPENDENCY))
    package = importlib.import_module(PREFIX.rstrip('.'))
    package.__path__.insert(0, str(CHECKOUT / AUTO))
    owners = {name: importlib.import_module(PREFIX + name) for name in HELPERS}
    for name, owner in owners.items():
        require(Path(owner.__file__).resolve() == (CHECKOUT / AUTO / (name + '.py')).resolve(),
                'wrong numerical helper owner')
    long_runner = load_script('scripts/ops/autoencoder/benchmark_long_span_decoder.py',
                              '_sidecar_private_donor', pins)
    restore_runner = load_script('scripts/ops/autoencoder/benchmark_clause_context_source_training.py',
                                 '_sidecar_restore', pins)
    import torch
    torch.set_num_threads(1)
    require(torch.get_default_dtype() == torch.float32, 'CPU float32 defaults required')
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import modal_latent_formula as numerical
    core = owners['decoder_distillation_experiment']
    # Distinct inference identities intentionally share one source in this panel.
    # The owner's split builder forbids duplicate normalized paragraphs; build
    # each inference packet separately and retain its normal per-row validator.
    contexts = {}
    for row in rows:
        source_row = {k: row[k] for k in ('id', 'source_text')}
        contexts.update(owners['clause_source_context'].build_source_contexts([source_row], cache))
    input_context_digest = core.digest(contexts)
    before_rng = torch.get_rng_state().clone()
    models, restorations = {}, {}
    with torch.random.fork_rng(devices=[]):
        teacher = long_runner.private_teacher(donor, numerical, core)
        teacher_digest = core.tensor_digest(teacher)
        for role in ('initial', 'selected', 'last-attempt'):
            saved = values[role]
            require(saved['schema'] == 'private-native-dimension-source-state/v1'
                    and saved['dimension'] == 768 and saved['role'] == role
                    and saved['selected'] is (role == 'selected')
                    and saved['optimizer_resumable'] is False
                    and saved['weights_sha256'] == core.digest(saved['model_state']), 'saved state identity differs')
            require(saved['codec'] == donor['codec'], 'original token codec required')
            require(all(saved[key] is False for key in ('qualified', 'admitted', 'proof_authority',
                    'source_semantics_verified', 'formalized', 'roundtrip_ok', 'checkpoint_promoted',
                    'lake_executed', 'convergence_proven', 'fresh_holdout')), 'saved authority differs')
            architecture = saved['architecture']
            native, receipt = owners['dimension_native_decoder_experiment'].bind_dimension_native_body(
                teacher.body, dimension=768, source_seed=1729)
            require(receipt == saved['initializer_receipt'], 'native initializer receipt differs')
            model = owners['decoder_distillation_experiment_v2'].bind_persistent_model(
                native, dimension=768, conditioning='every_step')
            model = owners['projected_source_decoder_experiment'].bind_projected_source_model(
                model, codec=saved['codec'], normalization_receipt=architecture['normalization'],
                count_prior_receipt=architecture['count_prior'], guide_boundary=True, scalar_guidance=True)
            model = owners['clause_source_decoder_experiment'].bind_clause_source_model(
                model, head_seed=2718, clause_normalization_receipt=architecture['clause_normalization'])
            model = owners['action_factorized_clause_decoder_experiment'].bind_action_factorized_clause_model(
                model, codec=saved['codec'])
            model = owners['ordered_clause_recurrent_decoder_experiment'].bind_ordered_clause_recurrent_model(
                model, codec=saved['codec'])
            require(model.describe() == architecture, 'complete original architecture differs')
            typed = restore_runner.restored_tensors(dict(numerical=numerical), saved['model_state'], model.state_dict())
            prefix = 'body.body.body.'
            raw_slice = {name[len(prefix):]: tensor for name, tensor in typed.items() if name.startswith(prefix)}
            owners['dimension_native_decoder_experiment'].validate_restored_state(native, receipt, raw_slice)
            model.load_state_dict(typed, strict=True)
            require(core.tensor_digest(model) == saved['tensor_sha256'], 'binary restored tensor digest differs')
            model.eval()
            for parameter in model.parameters():
                parameter.requires_grad_(False)
                parameter.grad = None
            models[role] = model
            restorations[role] = dict(state=inputs[role], tensor_sha256=core.tensor_digest(model),
                model_state_sha256=saved['weights_sha256'], tensor_count=len(typed),
                parameter_count=sum(p.numel() for p in model.parameters()), strict_restore_passed=True,
                architecture_equal=True, initializer_equal=True, selected=saved['selected'])
            rss_guard(deadline)
        require(core.tensor_digest(teacher) == teacher_digest, 'private donor changed')
    require(torch.equal(before_rng, torch.get_rng_state()), 'restoration changed global torch RNG')
    storage = {role: {tensor.untyped_storage().data_ptr() for tensor in model.state_dict().values()}
               for role, model in models.items()}
    require(all(not storage[a] & storage[b] for a, b in (('initial', 'selected'),
            ('initial', 'last-attempt'), ('selected', 'last-attempt'))), 'restored models share storage')
    before_sources = package_bindings()
    assay, generated = {}, {}
    forward_calls = generation_calls = 0
    size = len(donor['codec']['target_vocabulary'])
    probe = None
    with torch.inference_mode():
        for role, model in models.items():
            saved, outputs = values[role], []
            for offset in range(0, len(rows), 8):
                rss_guard(deadline)
                part = rows[offset:offset+8]
                transform = saved['input_transform']
                data = (torch.tensor([r['input'] for r in part], dtype=torch.float32)
                        - torch.tensor(transform['mean'], dtype=torch.float32)) / transform['scale']
                kw = core._source_context_kwargs(torch, part, contexts, transform)
                bos = torch.ones((len(part), 1), dtype=torch.long)
                projected, logits = model(data, bos, **kw)
                scalars, counts = model.source_value_logits(projected, **kw), model.count_logits(projected)
                require(torch.equal(projected, data), 'frozen native identity projection differs')
                require(tuple(logits.shape) == (len(part), 1, size)
                        and tuple(scalars.shape) == (len(part), 8, 4, size)
                        and tuple(counts.shape) == (len(part), owners['projected_source_decoder_experiment'].MAX_COUNTS)
                        and all(bool(torch.isfinite(t).all()) for t in (logits, scalars, counts)),
                        'numeric forward geometry/finiteness differs')
                forward_calls += 1
                for index, row in enumerate(part):
                    outputs.append(dict(id=row['id'], source_sha256=hashlib.sha256(row['source_text'].encode()).hexdigest(),
                        embedding_sha256=core.digest(row['input']), projected_sha256=core.digest(projected[index].tolist()),
                        bos_next_logits=logits[index, 0].tolist(), source_scalar_logits=scalars[index].tolist(),
                        source_count_logits=counts[index].tolist()))
                if role == 'initial' and offset == 0:
                    probe = (data.clone(), bos.clone(), kw, logits.clone())
            require(core.tensor_digest(model) == restorations[role]['tensor_sha256'], 'forward changed saved state')
            assay[role] = dict(schema='saved-sidecar-source-only-forward/v1', role=role, rows=outputs,
                explicit_prefix='one_BOS_token_only', input_dimension=768, vocabulary_size=size,
                original_input_transform_retained=True, frozen_projection_bitwise_identity=True,
                finite_output_geometry_verified=True, source_contexts_sha256=input_context_digest, **FALSE)
        data, bos, kw, expected_logits = probe
        _, observed = models['initial'](data, bos, **kw)
        forward_calls += 1
        require(torch.equal(observed, expected_logits), 'A/B/A numerical replay differs')
        require(assay['initial']['rows'] == assay['selected']['rows'], 'initial and epoch-0 selected outputs differ')
        for role, model in models.items():
            role_started = time.monotonic()
            role_deadline = min(deadline, role_started + 20.)
            outputs, complete = [], True
            for offset in range(0, len(rows), 8):
                rss_guard(deadline)
                part, transform = rows[offset:offset+8], values[role]['input_transform']
                data = (torch.tensor([r['input'] for r in part], dtype=torch.float32)
                        - torch.tensor(transform['mean'], dtype=torch.float32)) / transform['scale']
                kw = core._source_context_kwargs(torch, part, contexts, transform)
                observed = core._greedy(torch, model, data, 512, size, role_deadline, **kw)
                generation_calls += 1
                if observed is None:
                    complete = False
                    break
                projected, token_rows, statuses = observed
                require(torch.equal(projected, data), 'generation changed identity projection')
                for row, token_ids, status in zip(part, token_rows, statuses):
                    token_text = ''.join(donor['codec']['target_vocabulary'][token] for token in token_ids)
                    parsed = None
                    if status == 'eos':
                        try:
                            parsed = json.loads(token_text)
                        except ValueError:
                            pass
                    outputs.append(dict(id=row['id'], token_ids=token_ids, token_text=token_text,
                        generation_status=status, json_parse_valid=parsed is not None,
                        parsed_json=parsed, native_shape_checked=False))
            require(core.tensor_digest(model) == restorations[role]['tensor_sha256'], 'generation changed saved state')
            generated[role] = dict(schema='saved-sidecar-source-only-generation/v1', role=role,
                status='produced' if complete else 'timeout', expected_rows=34, completed_rows=len(outputs),
                predictions=outputs, output_limit=512, generation_temperature=0, batch_size=8,
                per_role_wall_limit_seconds=20., elapsed_seconds=time.monotonic()-role_started,
                source_contexts_sha256=input_context_digest, syntax_scope='JSON_parse_only', **FALSE)
    require(torch.equal(before_rng, torch.get_rng_state()), 'forward replay changed global torch RNG')
    after_sources = package_bindings()
    require(before_sources == after_sources, 'loaded source inventory changed during replay')
    for pin in inputs.values():
        require(binding(Path(pin['path'])) == pin, 'retained input file changed during replay')
    for pair in helper_bindings.values():
        require(all(binding(Path(pin['path'])) == pin for pin in pair.values()), 'helper changed during replay')
    rss_guard(deadline)
    vocab = donor['codec']['target_vocabulary']
    symbols = set()
    for token in vocab:
        try:
            value = json.loads(token)
        except ValueError:
            continue
        if isinstance(value, str):
            symbols.add(value)
    OUTPUT.mkdir()
    artifacts = {}
    for role in ('initial', 'selected', 'last-attempt'):
        artifacts[role+'-forward'] = save(OUTPUT / (role+'-forward.json'), assay[role])
        artifacts[role+'-generation'] = save(OUTPUT / (role+'-generation.json'), generated[role])
    report = dict(schema='native768-sidecar-bounded-replay/v1',
        status='restored_numeric_forward_passed', decoder_arm='768-generated-fields-every2-2718',
        source_checkout=dict(path=str(CHECKOUT), commit=BASE), dependency_tree=str(DEPENDENCY),
        inputs=inputs, helper_bindings=helper_bindings, loaded_package_sources=after_sources,
        runner=binding(Path(__file__)), restorations=restorations, artifacts=artifacts,
        numerical=dict(rows_per_state=34, source_input_width=768, saved_model_tensors=32,
            actual_bos_forward_calls=forward_calls, greedy_batch_calls=generation_calls,
            models_disjoint_storage=True, initial_selected_outputs_bitwise_equal=True,
            ABA_bos_logits_bitwise_equal=True, saved_binary_hashes_reproduced=True,
            private_teacher_preserved=True, global_torch_rng_preserved=True),
        source_context=dict(policy='per_inference_row_literal_blank_line_clauses/exact_text_native768_cache',
            single_clause_rows=34, unique_cache_sources=33, source_contexts_sha256=input_context_digest,
            declared_assumptions_applied=False, inference_references_read=False),
        generation={role: dict(status=item['status'], completed_rows=item['completed_rows'],
            eos_rows=sum(p['generation_status']=='eos' for p in item['predictions']),
            json_parse_valid_rows=sum(p['json_parse_valid'] for p in item['predictions']))
            for role, item in generated.items()},
        support=dict(output_vocabulary_size=size, max_rule_slots=8,
            named_diagnostic_symbol_representability={s: s in symbols for s in ('clerk','custodian','case_file')},
            matched_richer_panel_semantics_not_admitted=True,
            unsupported_target_policy='separate_codec_admission_needed_before_fidelity_scoring'),
        resources=dict(cpu_threads=torch.get_num_threads(), dtype='float32', device='cpu',
            CPU_soft_seconds=120, CPU_hard_seconds=130, outer_wall_seconds=300,
            cooperative_wall_seconds=240, measured_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            RSS_maximum_bytes=MAX_RSS, RSS_enforcement='RLIMIT_RSS_and_peak_check_at_model_and_batch_boundaries',
            elapsed_seconds=time.monotonic()-started, torch_version=torch.__version__),
        scope='saved_private_state_restoration_and_source_only_development_execution;no_semantic_or_proof_admission',
        **FALSE)
    report['content_sha256'] = digest(report)
    receipt = save(OUTPUT / 'report.json', report)
    print(json.dumps(dict(report=receipt, numerical=report['numerical'], generation=report['generation'],
                         resources=report['resources']), sort_keys=True))


if __name__ == '__main__':
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    sys.dont_write_bytecode = True
    resource.setrlimit(resource.RLIMIT_CPU, (120, 130))
    resource.setrlimit(resource.RLIMIT_RSS, (MAX_RSS, MAX_RSS))
    with contextlib.redirect_stdout(sys.stderr):
        run()
