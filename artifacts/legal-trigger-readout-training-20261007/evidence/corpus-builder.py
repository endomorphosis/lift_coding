#!/usr/bin/env python3
"""Fresh authored occurrence-copy bank for a bounded trigger-readout experiment.

The earlier renderer/anagram implementation is an explicit immutable source
input. New occupation, action, object and condition identities are independently
authored here. They are engineering premises, not reviewed statutory targets.
Only the new isolated checkout supplies pure scope-transport validation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re
import sys

sys.dont_write_bytecode = True
SEED = 24603
OLD = Path('/home/barberb/lift_coding/artifacts/legal-next-training-20261007-01')
OLD_BUILDER_SHA = 'ef654d25b51ea5addc5e91448664aee9c1c470335f7a7097c5d464747d2d6631'
COUNTS = {'train': 512, 'selection': 64, 'final': 64}
FACETS = ('actor', 'action', 'object', 'condition')
LEXICONS = {
    'train': {
        'actors': (
            'juniper librarian', 'acacia dispatcher', 'cypress accountant', 'larch botanist',
            'sequoia geologist', 'spruce pharmacist', 'palm chemist', 'beech optician',
            'poplar architect', 'ginkgo historian', 'mulberry translator', 'sycamore engineer',
            'chestnut researcher', 'baobab statistician', 'tamarind technician', 'églantier editor',
        ),
        'actions': (
            ('assess', 'assessing'), ('dispatch', 'dispatching'), ('verify', 'verifying'),
            ('retain', 'retaining'), ('release', 'releasing'),
            ('systematically measure', 'systematically measuring'),
            ('promptly transmit', 'promptly transmitting'), ('deliberately revise', 'deliberately revising'),
        ),
        'objects': (
            'mulberry application', 'juniper agenda', 'cypress account', 'larch budget',
            'sequoia invoice', 'spruce license', 'palm permit', 'beech allocation',
            'poplar report', 'ginkgo statement', 'sycamore resolution', 'chestnut amendment',
            'baobab proposal', 'tamarind request', 'acacia contract', 'églantier agreement',
        ),
        'conditions': (
            'approval arrives', 'consent persists', 'funding clears', 'signature matches',
            'quota suffices', 'licence expires', 'échéance approaches', 'coverage extends',
        ),
        'exception': 'supplementary authorization applies',
    },
    'selection': {
        'actors': (
            'dolomite mechanic', 'fluorite carpenter', 'garnet musician', 'zircon photographer',
            'spinel illustrator', 'pyrite designer', 'selenite artisan', 'chalk physician',
            'basalt nurse', 'limestone dentist', 'mica hygienist', 'andesite therapist',
            'calcite nutritionist', 'pumice radiologist', 'serpentine paramedic', 'éphémère anesthetist',
        ),
        'actions': (
            ('forward', 'forwarding'), ('collect', 'collecting'), ('resolve', 'resolving'),
            ('record', 'recording'), ('approve', 'approving'),
            ('thoroughly screen', 'thoroughly screening'),
            ('politely acknowledge', 'politely acknowledging'), ('evenly distribute', 'evenly distributing'),
        ),
        'objects': (
            'dolomite log', 'fluorite tally', 'garnet inventory', 'zircon catalogue',
            'spinel checklist', 'pyrite directory', 'selenite database', 'chalk file',
            'basalt document', 'limestone dossier', 'mica archive', 'andesite analysis',
            'calcite survey', 'pumice specification', 'serpentine blueprint', 'éphémère protocol',
        ),
        'conditions': (
            'eligibility continues', 'payment succeeds', 'authorization ends', 'registration renews',
            'notice returns', 'objection subsides', 'vérité holds', 'mandate activates',
        ),
        'exception': 'auxiliary dispensation applies',
    },
    'final': {
        'actors': (
            'pimento professor', 'sienna lecturer', 'vervain tutor', 'nutmeg pedagogue',
            'hops instructor', 'clover educator', 'nettle trainer', 'sorrel dean',
            'fennel principal', 'oregano rector', 'thyme provost', 'rosemary chancellor',
            'marjoram fellow', 'bay sage', 'sumac docent', 'étoile scholar',
        ),
        'actions': (
            ('authorize', 'authorizing'), ('withdraw', 'withdrawing'), ('reject', 'rejecting'),
            ('amend', 'amending'), ('cancel', 'canceling'),
            ('visibly mark', 'visibly marking'), ('firmly endorse', 'firmly endorsing'),
            ('directly summarize', 'directly summarizing'),
        ),
        'objects': (
            'aubergine digest', 'chartreuse thesis', 'ferruginous study', 'mauve audit',
            'olive finding', 'khaki assessment', 'magenta judgment', 'burgundy opinion',
            'tawny testimony', 'scarlet evidence', 'russet exhibit', 'ecru syllabus',
            'viridian curriculum', 'tansy lesson', 'amaranth evaluation', 'étoile decision',
        ),
        'conditions': (
            'petition matures', 'validation completes', 'audience assembles', 'sanction lapses',
            'appeal concludes', 'dispatch ceases', 'succès emerges', 'consensus develops',
        ),
        'exception': 'additional exemption applies',
    },
}
FILES = tuple(f'{s}-{r}.json' for s in COUNTS for r in ('inputs', 'references')) + (
    'corpus-protocol.json', 'corpus-manifest.json',
)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def normal(text):
    return ' '.join(text.casefold().split())


def earlier_builder():
    path = OLD / 'corpus-builder.py'
    require(sha(path) == OLD_BUILDER_SHA, 'immutable earlier corpus renderer changed')
    spec = importlib.util.spec_from_file_location('_trigger_readout_prior_authored_renderer', path)
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    return owner


def declared_values(inventory):
    return {
        'actor': set(inventory['actors']),
        'action': {a for pair in inventory['actions'] for a in pair},
        'object': set(inventory['objects']) | set(inventory['actors']),
        'condition': set(inventory['conditions']),
    }


def semantic_heads(inventory):
    """Declared identity vocabulary, not a source-text parser or target builder."""
    return {
        'actor': {a.split()[-1] for a in inventory['actors']},
        'action': {a.split()[-1] for pair in inventory['actions'] for a in pair},
        'object': {a.split()[-1] for a in (*inventory['objects'], *inventory['actors'])},
        'condition': {a.split()[-1] for a in inventory['conditions']},
    }


def earlier_inventory(base):
    sources, groups = set(), set()
    observed = {f: set() for f in FACETS}
    for split in COUNTS:
        inputs = read(OLD / f'{split}-inputs.json')
        references = read(OLD / f'{split}-references.json')
        by_id = {row['id']: row for row in inputs}
        require(len(inputs) == len(references) == 2 * COUNTS[split], 'complete earlier split required')
        for row in inputs:
            sources.add(normal(row['source_text']))
            groups.add(row['source_group'])
        for ref in references:
            if ref['supported']:
                text = by_id[ref['id']]['source_text']
                for facet in FACETS:
                    span = ref['prediction']['spans'][facet]
                    if span is not None:
                        observed[facet].add(normal(text[slice(*span)]))
    declared = {f: set() for f in FACETS}
    heads = {f: set() for f in FACETS}
    for old in base.LEXICONS.values():
        for facet, values in declared_values(old).items():
            declared[facet].update(map(normal, values))
        for facet, values in semantic_heads(old).items():
            heads[facet].update(map(normal, values))
    require(len(sources) == 1280 and len(groups) == 640, 'earlier complete1280sources/640groups required')
    return {'sources': sources, 'groups': groups, 'observed_facets': observed,
            'declared_facets': declared, 'semantic_heads': heads}


def assignment(row, template, count):
    # TRAIN has a complete64-row factorial for four nullable cells, four finite
    # aliases and four negative categories per template. Small evaluation splits
    # preserve each marginal rather than claiming an impossible full factorial.
    if count == 512:
        obj = (row + template) % 2 == 0
        cond = (row // 2 + template // 2) % 2 == 0
        alias = (row // 4 + template) % 4
        negative = (row // 16 + template) % 4
    else:
        obj = (row + template) % 2 == 0
        cond = (row // 2 + template // 2) % 2 == 0
        alias = (row + template) % 4
        negative = (row // 2 + template) % 4
    return obj, cond, alias, negative


def build_corpus(datasets_root, seed=SEED):
    require(type(seed) is int and seed == SEED, 'fixed fresh corpus seed required')
    base = earlier_builder()
    prior = earlier_inventory(base)
    scope = base._scope_owner(datasets_root)
    inventories = {s: declared_values(v) for s, v in LEXICONS.items()}
    for split, inventory in LEXICONS.items():
        for facet, values in inventories[split].items():
            fresh = {normal(v) for v in values}
            require(not fresh & (prior['observed_facets'][facet] | prior['declared_facets'][facet]),
                    'fresh facet identity overlaps earlier vocabulary: ' + facet)
            require(not {normal(v) for v in semantic_heads(inventory)[facet]} & prior['semantic_heads'][facet],
                    'prefix-only identity replacement is forbidden: ' + facet)
    for left in COUNTS:
        for right in COUNTS:
            if left >= right:
                continue
            for facet in FACETS:
                require(not {normal(x) for x in inventories[left][facet]} &
                        {normal(x) for x in inventories[right][facet]}, 'fresh split facet overlap: ' + facet)
                require(not semantic_heads(LEXICONS[left])[facet] & semantic_heads(LEXICONS[right])[facet],
                        'fresh split semantic-head overlap: ' + facet)
    corpus, seen, seen_groups = {}, set(), set()
    for split, count in COUNTS.items():
        inventory = LEXICONS[split]
        inputs, references = [], []
        for index in range(count):
            t, row = index % 8, index // 8
            actor = inventory['actors'][(row + 3 * t) % 16]
            action, gerund = inventory['actions'][(row // 16 + t) % 8]
            modality = ('O', 'P', 'F')[(row + 2 * t) % 3]
            has_object, has_condition, alias, category_index = assignment(row, t, count)
            repeated = has_object and (row // 4 + t) % 3 == 0
            obj = (actor if repeated else inventory['objects'][(row * 5 + t) % 16]) if has_object else None
            condition = inventory['conditions'][(row * 7 + t) % 8] if has_condition else None
            caller = ('rule', 'statement')[(row // 3 + t) % 2]
            text, spans = base.construct(base.TEMPLATES[t], actor=actor, action=action,
                gerund=gerund, obj=obj, condition=condition, modality=modality, trigger_variant=alias)
            source_sha = base.text_sha(text)
            identity = 'source:' + source_sha
            group = 'trigger-group:' + digest({'version': 'fresh-trigger-readout-20261007/v1',
                'split': split, 'ordinal': index, 'positive_source_sha256': source_sha})
            require(group not in seen_groups and group not in prior['groups'], 'source parent overlap')
            seen_groups.add(group)
            prediction = {'schema': scope.PREDICTION_SCHEMA,
                'interpretation_profile': scope.INTERPRETATION_PROFILE,
                'modality': modality, 'spans': spans,
                'condition_attachment': caller if has_condition else None}
            validated = scope.propose_scope_from_spans(text, prediction, expected_source_sha256=source_sha)
            require(validated['masks'] == base.ZERO_MASKS and validated['formal_output'] is None
                    and validated['source_semantics_verified'] is False, 'transport acquired authority')
            common = {'source_group': group, 'template': base.TEMPLATES[t], 'condition_attachment': caller}
            positive = {'id': identity, 'source_text': text, 'source_sha256': source_sha, **common}
            ref = {'id': identity, 'source_group': group, 'source_sha256': source_sha, 'supported': True,
                'prediction': prediction, 'parent_source_id': identity,
                'repeated_actor_object_occurrences': repeated,
                'reference_origin': 'fresh_authored_engineering_construction',
                'natural_source_semantics_verified': False, 'independent_legal_review': False,
                'admission_masks': dict(base.ZERO_MASKS)}
            category = base.NEGATIVE_CATEGORIES[category_index]
            negative_text = base.unsupported_source(text, spans, category, actor=actor,
                action=action, exception=inventory['exception'], split=split)
            negative_sha = base.text_sha(negative_text)
            negative_id = 'source:' + negative_sha
            negative = {'id': negative_id, 'source_text': negative_text,
                'source_sha256': negative_sha, **common}
            negative_ref = {'id': negative_id, 'source_group': group, 'source_sha256': negative_sha,
                'supported': False, 'prediction': None, 'unsupported_category': category,
                'parent_source_id': identity,
                'reference_origin': 'fresh_authored_outside_single_rule_engineering_profile',
                'legally_false_claimed': False, 'natural_source_semantics_verified': False,
                'independent_legal_review': False, 'admission_masks': dict(base.ZERO_MASKS)}
            for candidate in (positive, negative):
                normalized = normal(candidate['source_text'])
                require(normalized not in seen and normalized not in prior['sources'], 'fresh source overlap')
                seen.add(normalized)
            if category == 'modal_misspelling':
                require(len(text.encode()) == len(negative_text.encode()) and
                    Counter(text.encode()) == Counter(negative_text.encode()), 'anagram byte inventory drift')
            inputs.extend((positive, negative))
            references.extend((ref, negative_ref))
        order = list(range(len(inputs)))
        random.Random(seed + list(COUNTS).index(split)).shuffle(order)
        corpus[split] = {'inputs': [inputs[i] for i in order], 'references': [references[i] for i in order]}
    require(len(seen) == 1280 and len(seen_groups) == 640, 'complete unique fresh corpus required')
    return corpus


def training_batches(train_inputs, train_references, seed=SEED, updates=240):
    require(type(seed) is int and seed == SEED and type(updates) is int and updates == 240,
            'fixed fresh balanced240-update schedule required')
    refs = {r['id']: r for r in train_references}
    require(len(refs) == len(train_inputs) == 1024 and set(refs) == {r['id'] for r in train_inputs},
            'complete fresh train reference join required')
    pools = {flag: [r['id'] for r in train_inputs if refs[r['id']]['supported'] is flag] for flag in (True, False)}
    require(all(len(v) == 512 for v in pools.values()), 'complete512+512fresh train required')
    rng, cursor, result = random.Random(seed), {True: 512, False: 512}, []
    for _ in range(updates):
        batch = []
        for flag in (True, False):
            if cursor[flag] == 512:
                rng.shuffle(pools[flag]); cursor[flag] = 0
            batch.extend(pools[flag][cursor[flag]:cursor[flag] + 8]); cursor[flag] += 8
        rng.shuffle(batch); result.append(batch)
    return result


def statistics(values):
    ins = {r['id']: r for r in values['inputs']}
    positive = [r for r in values['references'] if r['supported']]
    negative = [r for r in values['references'] if not r['supported']]
    trigger = lambda r: ins[r['id']]['source_text'][slice(*r['prediction']['spans']['modality'])]
    cell = lambda r: ('object' if r['prediction']['spans']['object'] is not None else 'no_object') + '|' + (
        'condition' if r['prediction']['spans']['condition'] is not None else 'no_condition')
    count = lambda values: dict(sorted(Counter(values).items()))
    tokens = lambda s: re.findall(r'\w+|[^\w\s]', s, flags=re.UNICODE)
    return {'input_rows': len(ins), 'positive_rows': len(positive), 'negative_rows': len(negative),
        'source_groups': len({r['source_group'] for r in values['inputs']}),
        'unique_normalized_sources': len({normal(r['source_text']) for r in values['inputs']}),
        'modalities': count(r['prediction']['modality'] for r in positive),
        'modal_trigger_aliases': count(trigger(r) for r in positive),
        'templates': count(ins[r['id']]['template'] for r in positive),
        'nullable_cells': count(cell(r) for r in positive),
        'template_modality_alias_nullable_cells': count('|'.join((ins[r['id']]['template'],
            r['prediction']['modality'], trigger(r), cell(r))) for r in positive),
        'negative_categories': count(r['unsupported_category'] for r in negative),
        'repeated_actor_object_occurrences': sum(r['repeated_actor_object_occurrences'] for r in positive),
        'unicode_positive_sources': sum(any(ord(c) > 127 for c in ins[r['id']]['source_text']) for r in positive),
        'caller_attachments': count(r['condition_attachment'] for r in values['inputs']),
        'positive_scope_transport_validations': len(positive),
        'maximum_source_tokens': max(len(tokens(r['source_text'])) for r in values['inputs']),
        'maximum_token_UTF8_bytes': max(len(t.encode()) for r in values['inputs'] for t in tokens(r['source_text'])),
        'maximum_source_UTF8_bytes': max(len(r['source_text'].encode()) for r in values['inputs'])}


def write_corpus(output, datasets_root, seed=SEED):
    output = Path(output).resolve()
    require(output.is_dir() and not any((output / n).exists() for n in FILES), 'fresh immutable artifact names required')
    base = earlier_builder()
    corpus = build_corpus(datasets_root, seed)
    batches = training_batches(corpus['train']['inputs'], corpus['train']['references'], seed)
    old_inputs = [OLD / 'corpus-builder.py'] + [OLD / f'{s}-{r}.json' for s in COUNTS for r in ('inputs', 'references')]
    old_bindings = [{'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in old_inputs]
    plan = {'schema': 'fresh-trigger-readout-authored-corpus-protocol/v1', 'seed': seed,
        'scope': 'Fresh raw-source single-rule five-facet engineering copy targets; no statutory semantic gold.',
        'comparison_owner': 'Root numerical runner defines the separately reviewed matched global versus learned-trigger readout; no model initialized or owner selected by corpus construction.',
        'split_supported_counts': dict(COUNTS), 'split_unsupported_counts': dict(COUNTS),
        'templates': list(base.TEMPLATES), 'finite_modal_aliases': base.FINITE_TRIGGERS,
        'infinitive_modal_aliases': base.INF_TRIGGERS, 'gerund_modal_aliases': base.NOM_TRIGGERS,
        'shared_grammar': 'All eight templates, O/P/F classes, operator alias vocabulary and rendering semantics deliberately shared with earlier pilot; new source strings/facet identities do not establish new syntax or reviewed-law generalization.',
        'negative_categories': list(base.NEGATIVE_CATEGORIES),
        'anagrams': 'Change one preannotated operator word; TRAIN rotateleft1, selection rotateleft2, finalreverse. Preserve token order/spaces/UTF8length/per-tokenbyte multiset. Distinct permutations by split. Unsupported means outside authored profile, not legally false.',
        'caller_attachment': 'Explicit rule|statement caller premise inherited by each positive/negative pair, never learned. Copy to output only when a predicted condition is present; otherwise null.',
        'fresh_exclusion': 'All1280 earlier source strings and640groups, all observed earlier facet strings and full declared earlier facet vocabularies, plus semantic-role/object/action/condition-head vocabulary are excluded. New splits also have disjoint normalized facet values and declared semantic heads; no prefix-only replacement of an old identity.',
        'old_source_bindings': old_bindings, 'fresh_declared_lexicons': LEXICONS,
        'balance': '512TRAINpositives:64/template and16/nullablecell/template; finite aliases and negative categories16/template.64evaluationpositives:8/template,2/nullablecell/template; finite aliases and negative categories2/template. O/P/F as close as integer counts permit. Complete joint count ledgers retained in manifest.',
        'optimizer_steps_per_arm': 240, 'batch_size': 16, 'positive_per_batch': 8, 'negative_per_batch': 8,
        'row_presentations_per_arm': 3840, 'training_schedule_sha256': digest(batches),
        'selection_steps': [0, 120, 240],
        'selection_score_descending': ['positive_raw_modality_exact', 'positive_exact_count', '-completed_updates'],
        'support_threshold': 0.5, 'source_chars_max': 8192, 'source_tokens_max': 96,
        'token_UTF8_bytes_max': 64,
        'output_profile': 'Single-rule predicted source-occurrence structure; no autoregressive formula-token output or512-token decoding budget.',
        'source_features': 'Raw source UTF8 only. Inputid/group/template/digest/callermetadata and reference labels are never learned byte/token features. No parser, source search, anchor repair, truncation or target lookup.',
        'unsupported_reference_contract': 'supported=false,prediction=null; no negative modality/class/span/optional-presence target.',
        'final_reference_barrier': 'Author construction and mechanical transport validation use all640 positive references. The root numerical runner must durably freeze both selections/checkpoints before parsing fresh final-references.json, and durably save both final prediction panels before scoring. This is not an authors-blind final-label claim.',
        'law_source_semantics_verified': False, 'independent_legal_review': False,
        'legal_gold': False, 'admission_masks': dict(base.ZERO_MASKS),
        'numerical_model_encoder_optimizer_prover_calls': 0,
        'source_builder': {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__))}}
    artifacts = {}
    def save(name, value):
        data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        p = output / name
        with p.open('xb') as stream:
            stream.write(data)
        artifacts[name] = {'path': str(p), 'sha256': hashlib.sha256(data).hexdigest(),
                           'bytes': len(data), 'canonical_sha256': digest(value)}
    for split, values in corpus.items():
        for role in ('inputs', 'references'):
            save(f'{split}-{role}.json', values[role])
    save('corpus-protocol.json', plan)
    owners = [Path(datasets_root) / 'ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_span_proposal.py',
              Path(datasets_root) / 'ipfs_datasets_py/logic/legal_ir/canonical_statement_scope.py']
    manifest = {'schema': 'fresh-trigger-readout-authored-corpus-manifest/v1', 'complete': True,
        'seed': seed, 'artifacts': dict(artifacts), 'statistics': {s: statistics(v) for s, v in corpus.items()},
        'construction_source': plan['source_builder'], 'versioned_old_source_inputs': old_bindings,
        'proposal_owner_bindings': [{'path': str(p.resolve()), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in owners],
        'training_schedule_sha256': digest(batches), 'source_rows': 1280, 'source_parent_groups': 640,
        'distinct_train_sources_presented': len({s for b in batches for s in b}),
        'old_sources_normalized_overlap': 0, 'old_source_groups_overlap': 0,
        'old_observed_and_declared_facet_overlap': dict.fromkeys(FACETS, 0),
        'old_declared_identity_head_overlap': dict.fromkeys(FACETS, 0),
        'fresh_split_facet_and_identity_head_overlap': dict.fromkeys(FACETS, 0),
        'same_text_duplicated_for_caller_profiles': False,
        'positive_scope_transport_validations': 640, 'all_admission_masks0': True,
        'semantic_source_review_or_legal_gold': False, 'training_or_proof_admission': False,
        'numerical_model_encoder_optimizer_prover_calls': 0}
    save('corpus-manifest.json', manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--datasets-root', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=SEED)
    args = parser.parse_args()
    result = write_corpus(args.output, args.datasets_root, args.seed)
    print(json.dumps({'complete': result['complete'], 'sources': result['source_rows'],
        'groups': result['source_parent_groups'], 'schedule': result['training_schedule_sha256']}, indent=2))


if __name__ == '__main__':
    main()
