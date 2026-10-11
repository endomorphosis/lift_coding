#!/usr/bin/env python3
"""Fresh authored support-retention occurrence-copy bank and exact paired schedule.

The earlier renderer/anagram implementation is an explicit immutable source
input. New actor, action, object and condition identities are independently
authored here. They are engineering premises, not reviewed statutory targets.
Only the new isolated checkout supplies pure scope-transport validation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import re
import sys
import unicodedata

sys.dont_write_bytecode = True
SEED = 24606
SOURCE_PROFILE = "fresh-support-retention-20261011/v1"
SOURCE_COMMIT = "a1b5c73e5b687d8bd6c3b3051788860fd6e2f07a"
OLD = Path('/home/barberb/lift_coding/artifacts/legal-next-training-20261007-01')
OLD_BUILDER_SHA = 'ef654d25b51ea5addc5e91448664aee9c1c470335f7a7097c5d464747d2d6631'
PREVIOUS = Path('/home/barberb/lift_coding/artifacts/legal-trigger-readout-20261007-01')
PREVIOUS_BUILDER_SHA = '881abc31455551c953ebe23f2a24bb6bde5df09a85e1c6455945a1a5ffd56e74'
THIRD = Path('/home/barberb/lift_coding/artifacts/legal-support-action-20261007-01')
THIRD_BUILDER_SHA = '54616dca4e9edc0d5c1f2362544de0da5b87ad57b4b7af75480b4e455be56e7e'
PRIOR_MANIFEST_SHAS = {OLD: '5c87b0ef62c3fa7846f2000ae99caa3438c85c2cf1e80809380cf97e600d2f32',
    PREVIOUS: '22a551395a410e4b3fe79155f554a2ee05c7b2eec6631d7836079d7ec9c0a7d1',
    THIRD: 'eda62b5e15083adba9184ec5ecdcf01a530df21914344e3bfb7d36ed0cc7cec0'}
FOURTH = Path('/home/barberb/lift_coding/artifacts/legal-support-gate-20261007-01')
FOURTH_BUILDER_SHA = 'ae83a8ae139301411ffbe3aeb6f5b2a06e9fab509ca83c6f835919c387cbdf73'
PRIOR_MANIFEST_SHAS[FOURTH] = '7a841522be4e481be886be65b3bdaf85092e24cd2c2cb0202e7eb91ee5b0c959'
COUNTS = {'train': 512, 'selection': 64, 'final': 64}
FACETS = ('actor', 'action', 'object', 'condition')
LEXICONS = {'train': {'actors': ['kyanite weevil',
                      'rutile cicada',
                      'apatite locust',
                      'iolite mantis',
                      'tanzanite hornet',
                      'peridot moth',
                      'chrysoprase beetle',
                      'carnelian firefly',
                      'sodalite dragonfly',
                      'aventurine termite',
                      'sphene lacewing',
                      'prehnite katydid',
                      'larimar ladybird',
                      'charoite aphid',
                      'sunstone cricket',
                      'héliotrope earwig'],
           'objects': ['kyanite sundial',
                       'rutile anvil',
                       'apatite retort',
                       'iolite crucible',
                       'tanzanite spatula',
                       'peridot pipette',
                       'chrysoprase burette',
                       'carnelian mortar',
                       'sodalite pestle',
                       'aventurine sieve',
                       'sphene ladle',
                       'prehnite colander',
                       'larimar decanter',
                       'charoite flask',
                       'sunstone alembic',
                       'héliotrope thimble'],
           'actions': [['grind', 'grinding'],
                       ['buff', 'buffing'],
                       ['temper', 'tempering'],
                       ['anneal', 'annealing'],
                       ['glaze', 'glazing'],
                       ['lightly hone', 'lightly honing'],
                       ['delicately etch', 'delicately etching'],
                       ['rigorously abrade', 'rigorously abrading']],
           'conditions': ['geyser gushes',
                          'estuary surges',
                          'lagoon ripples',
                          'delta floods',
                          'inlet ebbs',
                          'strait churns',
                          'bayou meanders',
                          'fjord foams'],
           'exception': 'forbearance nullifies'},
 'selection': {'actors': ['europa alpaca',
                          'io llama',
                          'titania bison',
                          'rhea buffalo',
                          'iapetus gazelle',
                          'enceladus impala',
                          'mimas ibex',
                          'tethys antelope',
                          'dione zebra',
                          'triton giraffe',
                          'nereid rhinoceros',
                          'phobos hippopotamus',
                          'deimos walrus',
                          'callísto otter',
                          'ganymede badger',
                          'prospero chinchilla'],
               'objects': ['europa caliper',
                           'io micrometer',
                           'titania protractor',
                           'rhea sextant',
                           'iapetus tachometer',
                           'enceladus dynamometer',
                           'mimas barometer',
                           'tethys thermometer',
                           'dione hydrometer',
                           'triton pyrometer',
                           'nereid voltmeter',
                           'phobos ammeter',
                           'deimos galvanometer',
                           'callísto spectrometer',
                           'ganymede viscometer',
                           'prospero sphygmomanometer'],
               'actions': [['calibrate', 'calibrating'],
                           ['lubricate', 'lubricating'],
                           ['couple', 'coupling'],
                           ['detach', 'detaching'],
                           ['unfasten', 'unfastening'],
                           ['loosely crimp', 'loosely crimping'],
                           ['tightly cinch', 'tightly cinching'],
                           ['cautiously bevel', 'cautiously beveling']],
               'conditions': ['monsoon abates',
                              'cyclone looms',
                              'hurricane veers',
                              'typhoon recedes',
                              'whirlwind eddies',
                              'breeze wafts',
                              'duststorm dissipates',
                              'snowstorm intensifies'],
               'exception': 'interdiction invalidates'},
 'final': {'actors': ['amanita goby',
                      'boletus guppy',
                      'chanterelle loach',
                      'morel minnow',
                      'shiitake carp',
                      'enoki tench',
                      'maitake roach',
                      'porcini dace',
                      'russula perch',
                      'lactarius trout',
                      'ganoderma salmon',
                      'pleurotus flounder',
                      'morchella halibut',
                      'tricholoma turbot',
                      'coprinus haddock',
                      'piñon anchovy'],
           'objects': ['amanita cufflink',
                       'boletus epaulet',
                       'chanterelle gaiter',
                       'morel spats',
                       'shiitake beret',
                       'enoki fedora',
                       'maitake bonnet',
                       'porcini sombrero',
                       'russula poncho',
                       'lactarius parka',
                       'ganoderma anorak',
                       'pleurotus doublet',
                       'morchella jerkin',
                       'tricholoma bolero',
                       'coprinus tabard',
                       'piñon tunic'],
           'actions': [['button', 'buttoning'],
                       ['lace', 'lacing'],
                       ['zip', 'zipping'],
                       ['baste', 'basting'],
                       ['ruffle', 'ruffling'],
                       ['elegantly smock', 'elegantly smocking'],
                       ['stylishly fringe', 'stylishly fringing'],
                       ['tastefully emboss', 'tastefully embossing']],
           'conditions': ['magma wells',
                          'lava oozes',
                          'fumarole vents',
                          'caldera seethes',
                          'crater smolders',
                          'fissure widens',
                          'fault slips',
                          'plateau uplifts'],
           'exception': 'proviso rescinds'}}
FILES = tuple(f'{s}-{r}.json' for s in COUNTS for r in ('inputs', 'references')) + (
    'corpus-protocol.json', 'training-schedule.json', 'corpus-manifest.json',
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
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def earlier_builder():
    # Load only the pinned authored builder; its earlier_builder pins ef654d too.
    path = PREVIOUS / 'corpus-builder.py'
    require(sha(path) == PREVIOUS_BUILDER_SHA, 'immutable prior freshness builder changed')
    spec = importlib.util.spec_from_file_location('_support_action_prior_fresh_builder', path)
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    base = owner.earlier_builder()
    require(sha(OLD / 'corpus-builder.py') == OLD_BUILDER_SHA, 'immutable original renderer changed')
    return base


def previous_builder():
    path = PREVIOUS / 'corpus-builder.py'
    require(sha(path) == PREVIOUS_BUILDER_SHA, 'immutable prior freshness builder changed')
    spec = importlib.util.spec_from_file_location('_support_action_prior_inventory_builder', path)
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    return owner



def third_builder():
    path = THIRD / 'corpus-builder.py'
    require(sha(path) == THIRD_BUILDER_SHA, 'immutable support/action source builder changed')
    spec = importlib.util.spec_from_file_location('_support_gate_prior_bank_builder', path)
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    return owner


def fourth_builder():
    path = FOURTH / 'corpus-builder.py'
    require(sha(path) == FOURTH_BUILDER_SHA, 'immutable support-gate builder changed')
    spec = importlib.util.spec_from_file_location('_retention_pinned_support_gate_builder', path)
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    return owner


def prior_source_bindings():
    records = []
    for root, expected in PRIOR_MANIFEST_SHAS.items():
        manifest_path = root / 'corpus-manifest.json'
        require(sha(manifest_path) == expected, 'pinned prior manifest changed')
        manifest = read(manifest_path)
        for split in COUNTS:
            for role in ('inputs', 'references'):
                path = root / f'{split}-{role}.json'
                record = manifest['artifacts'][path.name]
                require(sha(path) == record['sha256'] and path.stat().st_size == record['bytes'],
                        'pinned prior split artifact changed: ' + str(path))
        protocol_path = root / 'corpus-protocol.json'
        require(sha(protocol_path) == manifest['artifacts'][protocol_path.name]['sha256'],
                'pinned prior protocol changed')
        review_name = 'independent-corpus-selector-review.json' if root == THIRD else 'independent-corpus-review.json'
        paths = [root / 'corpus-builder.py', manifest_path, protocol_path, root / review_name]
        paths += [root / f'{split}-{role}.json' for split in COUNTS for role in ('inputs', 'references')]
        records.extend({'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in paths)
    return records


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


def content_words(inventory):
    values = set().union(*declared_values(inventory).values()) | {inventory['exception']}
    return {word for value in values for word in normal(value).split()}


def earlier_inventory(base):
    prior_source_bindings()
    previous = previous_builder()
    sources, groups = set(), set()
    observed = {f: set() for f in FACETS}
    declared = {f: set() for f in FACETS}
    heads = {f: set() for f in FACETS}
    words = set()
    for root, owner in ((OLD, base), (PREVIOUS, previous), (THIRD, third_builder()), (FOURTH, fourth_builder())):
        root_sources, root_groups = set(), set()
        for split in COUNTS:
            inputs = read(root / f'{split}-inputs.json')
            references = read(root / f'{split}-references.json')
            by_id = {row['id']: row for row in inputs}
            require(len(inputs) == len(references) == len(by_id) == 2 * COUNTS[split],
                    'complete unique prior split required')
            require(set(by_id) == {row['id'] for row in references}, 'prior reference join differs')
            for row in inputs:
                root_sources.add(normal(row['source_text']))
                root_groups.add(row['source_group'])
            for ref in references:
                if ref['supported']:
                    text = by_id[ref['id']]['source_text']
                    for facet in FACETS:
                        span = ref['prediction']['spans'][facet]
                        if span is not None:
                            observed[facet].add(normal(text[slice(*span)]))
        require(len(root_sources) == 1280 and len(root_groups) == 640, 'complete prior bank required')
        sources.update(root_sources); groups.update(root_groups)
        for inventory in owner.LEXICONS.values():
            for facet, values in declared_values(inventory).items():
                declared[facet].update(map(normal, values))
            for facet, values in semantic_heads(inventory).items():
                heads[facet].update(map(normal, values))
            words.update(content_words(inventory))
    require(len(sources) == 5120 and len(groups) == 2560, 'complete union of all four earlier banks required')
    return {'sources': sources, 'groups': groups, 'observed_facets': observed,
            'declared_facets': declared, 'semantic_heads': heads, 'content_words': words}


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
    require(not any(n == 'torch' or n.startswith('torch.') for n in sys.modules), 'no Torch in corpus process')
    require(Path(datasets_root).resolve() == Path(__file__).resolve().parent / 'datasets',
            'only owned isolated source checkout may validate transport')
    import subprocess
    current = subprocess.check_output(['git', '-C', str(datasets_root), 'rev-parse', 'HEAD'], text=True).strip()
    require(current == SOURCE_COMMIT, 'isolated proposal source revision changed')
    base = earlier_builder()
    prior = earlier_inventory(base)
    scope = base._scope_owner(datasets_root)
    inventories = {s: declared_values(v) for s, v in LEXICONS.items()}
    for split, inventory in LEXICONS.items():
        require(not content_words(inventory) & prior['content_words'],
                'fresh declared content word overlaps any prior bank: ' + split)
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
            require(not content_words(LEXICONS[left]) & content_words(LEXICONS[right]),
                    'fresh split content words overlap')
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
            action, gerund = inventory['actions'][(3 * row + t + t // 2 + row // 8) % 8]
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
            group = 'support-retention-group:' + digest({'version': SOURCE_PROFILE,
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
                'repeated_actor_object_occurrences': repeated, 'declared_action_lemma': action,
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
    require(not any(n == 'torch' or n.startswith('torch.') for n in sys.modules), 'corpus imported Torch')
    return corpus


def training_batches(train_inputs, train_references, seed=SEED, updates=240):
    """One pair per parent group; each batch has two groups per negative category.

    The shuffled 128-group category pools cycle only after full consumption. The
    supported source and its actual corresponding unsupported source always
    appear together. Labels/categories/IDs determine the schedule only, never
    numerical source features. No independent positive/negative sampler exists.
    """
    require(type(seed) is int and seed == SEED and type(updates) is int and updates == 240,
            'fixed fresh paired240-update schedule required')
    refs = {r['id']: r for r in train_references}
    rows = {r['id']: r for r in train_inputs}
    require(len(refs) == len(rows) == len(train_inputs) == 1024 and set(refs) == set(rows),
            'complete fresh train reference join required')
    by_group = {}
    for row in train_inputs:
        group = row['source_group']
        require(refs[row['id']]['source_group'] == group, 'input/reference source group mismatch')
        by_group.setdefault(group, []).append(row['id'])
    require(len(by_group) == 512, 'exactly512parentgroups required')
    base = earlier_builder()
    pools = {category: [] for category in base.NEGATIVE_CATEGORIES}
    pairs = {}
    for group, ids in sorted(by_group.items()):
        require(len(ids) == 2, 'one positive/negative pair per group required')
        positive = [i for i in ids if refs[i]['supported'] is True]
        negative = [i for i in ids if refs[i]['supported'] is False]
        require(len(positive) == len(negative) == 1, 'paired boolean labels required')
        p, n = positive[0], negative[0]
        require(refs[p]['parent_source_id'] == p == refs[n]['parent_source_id'],
                'negative must be paired to its actual authored positive source')
        category = refs[n]['unsupported_category']
        require(category in pools, 'unknown negative category')
        pairs[group] = (p, n)
        pools[category].append(group)
    require(all(len(groups) == 128 for groups in pools.values()), '128groups/category required')
    rng, cursors, batches = random.Random(seed), dict.fromkeys(pools, 128), []
    for _ in range(updates):
        groups = []
        for category in base.NEGATIVE_CATEGORIES:
            if cursors[category] == 128:
                rng.shuffle(pools[category]); cursors[category] = 0
            groups.extend(pools[category][cursors[category]:cursors[category] + 2])
            cursors[category] += 2
        require(len(set(groups)) == 8, 'eight distinct actual parent groups required')
        rng.shuffle(groups)
        batch = [source for group in groups for source in pairs[group]]
        require(len(set(batch)) == 16, 'sixteen unique paired input records required')
        batches.append(batch)
    audit = schedule_audit(train_inputs, train_references, batches)
    require(audit['valid'] and audit['group_presentation_count'] == 1920 and
            audit['source_presentation_count'] == 3840, 'complete paired exposure schedule required')
    return batches


def schedule_audit(train_inputs, train_references, batches):
    """Pure source/group exposure accounting; no model, feature or fitting call."""
    refs = {r['id']: r for r in train_references}
    rows = {r['id']: r for r in train_inputs}
    require(len(refs) == len(rows) == 1024, 'complete train source tables required')
    source_exposures, group_exposures = Counter(), Counter()
    batch_checks, batch_groups = [], []
    base = earlier_builder()
    expected_categories = set(base.NEGATIVE_CATEGORIES)
    for step, ids in enumerate(batches, 1):
        require(len(ids) == len(set(ids)) == 16 and set(ids) <= set(rows), 'bounded unique batch required')
        by_group = {}
        for source in ids:
            source_exposures[source] += 1
            by_group.setdefault(rows[source]['source_group'], []).append(source)
        require(len(by_group) == 8, 'eightpairedgroups/batch required')
        negatives = Counter()
        for group, sources in by_group.items():
            positive = [i for i in sources if refs[i]['supported'] is True]
            negative = [i for i in sources if refs[i]['supported'] is False]
            require(len(positive) == len(negative) == 1 and len(sources) == 2,
                    'every batch group must have its positive and negative')
            require(refs[negative[0]]['parent_source_id'] == positive[0], 'actual parent pairing required')
            negatives[refs[negative[0]]['unsupported_category']] += 1
            group_exposures[group] += 1
        require(set(negatives) == expected_categories and set(negatives.values()) == {2},
                'exactlytwoactualgroups/category/batch required')
        batch_groups.append(list(by_group))
        batch_checks.append({'step': step, 'sources': 16, 'groups': 8,
            'positive_sources': 8, 'negative_sources': 8,
            'negative_category_groups': dict(sorted(negatives.items()))})
    require(len(batches) == 240 and set(source_exposures) == set(rows), 'complete240step source exposure required')
    require(set(group_exposures) == {row['source_group'] for row in train_inputs}, 'all512groups required')
    for group in group_exposures:
        source_counts = {source_exposures[row['id']] for row in train_inputs if row['source_group'] == group}
        require(source_counts == {group_exposures[group]}, 'paired source/group exposures must match')
    count = lambda values: dict(sorted(Counter(values).items()))
    checkpoints = {}
    for step in (64, 120, 128, 192, 240):
        exposures = Counter(source for batch in batches[:step] for source in batch)
        groups = Counter(group for batch in batch_groups[:step] for group in batch)
        checkpoints[str(step)] = {'distinct_sources': len(exposures), 'distinct_groups': len(groups),
            'source_presentation_count': sum(exposures.values()), 'group_presentation_count': sum(groups.values()),
            'source_exposure_histogram': count(exposures.values()), 'group_exposure_histogram': count(groups.values())}
    require(checkpoints['64']['source_exposure_histogram'] == {1: 1024}, 'firstcycle must visit every source once')
    require(count(source_exposures.values()) == {3: 256, 4: 768}, '240step source exposure histogram changed')
    require(count(group_exposures.values()) == {3: 128, 4: 384}, '240step group exposure histogram changed')
    return {'schema': 'paired-support-retention-schedule-audit/v1', 'valid': True,
        'updates': 240, 'batch_size': 16, 'seed': SEED, 'source_profile': SOURCE_PROFILE,
        'source_presentation_count': sum(source_exposures.values()),
        'group_presentation_count': sum(group_exposures.values()),
        'distinct_sources': len(source_exposures), 'distinct_groups': len(group_exposures),
        'source_exposure_histogram': count(source_exposures.values()),
        'group_exposure_histogram': count(group_exposures.values()),
        'source_exposure_counts': dict(sorted(source_exposures.items())),
        'group_exposure_counts': dict(sorted(group_exposures.items())),
        'checkpoints': checkpoints, 'per_batch_checks': batch_checks,
        'batches': batches, 'batch_groups': batch_groups,
        'each_group_always_has_actual_positive_and_negative': True,
        'separate_positive_negative_samplers': False,
        'four_category_pools_of_128groups_cycle_after_full_consumption': True,
        'training_schedule_sha256': digest(batches)}


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
        'declared_action_lemmas_by_template': {t: count(r['declared_action_lemma'] for r in positive
            if ins[r['id']]['template'] == t) for t in sorted({row['template'] for row in values['inputs']})},
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
    old_bindings = prior_source_bindings()
    plan = {'schema': 'fresh-support-retention-authored-corpus-protocol/v1',
        'source_profile': SOURCE_PROFILE, 'seed': seed,
        'scope': 'Fresh raw-source single-rule five-facet authored engineering construction; no statutory semantic gold. Unicode half-open anchors are captured during the pinned renderer construction before negative mutations. No parser, span search, model or semantic reviewer creates these labels.',
        'comparison_owner': 'Separately reviewed root runner compares the same predicted-trigger97-to32-to1 Tanh gate (3169parameters), seeded identically over frozen contextual64 plus ordered-byte33 features. Only objective differs: support BCE versus support BCE plus lambda1 online frozen-parent positive margin hinge. Parent architecture/class/presence/allfivepointers remain frozen. Corpus construction initializes no model.',
        'frozen_parent_checkpoint_sha256': '48559399bb22de0fe68908919d225d391880a38f4fab659026d526e19ffc9155',
        'objectives': {'control': 'binary support BCE over all16 actual paired source records',
            'retention': 'same BCE plus lambda1 mean relu(clamp(parent_support_logit,0,1)-candidate_support_logit) over actual frozen-parent-emitted supported TRAIN sources only',
            'lambda': 1, 'margin_floor_logit_clamp': [0, 1],
            'teacher_emission_mask': 'Online actual frozen-parent proposal emission, requiring its learned support and structural emission; labels only restrict to supported TRAIN. Reuse the same parent forward/features/logit/pointers; count additional parent decodes separately, with no extra parent forwards.',
            'gold_spans_or_modalities_in_fitting': False},
        'split_supported_counts': dict(COUNTS), 'split_unsupported_counts': dict(COUNTS),
        'templates': list(base.TEMPLATES), 'finite_modal_aliases': base.FINITE_TRIGGERS,
        'infinitive_modal_aliases': base.INF_TRIGGERS, 'gerund_modal_aliases': base.NOM_TRIGGERS,
        'shared_grammar': 'All8templates, O/P/F classes, finite/infinitive/gerund modal aliases, construction semantics and negative categories deliberately shared with ALL FOUR exposed earlier banks. Novel strings and content identities do not establish novel syntax or fresh reviewed legal meaning.',
        'negative_categories': list(base.NEGATIVE_CATEGORIES),
        'anagrams': 'Pinned token-local modality anagrams: TRAINrotateleft1, selectionrotateleft2, finalreverse. Preserve whitespace, token order, UTF8length and byte multisets. Permutations differ by split within the new bank; the same patterns exist in earlier exposed banks, so there is no globally unseen-pattern claim.',
        'caller_attachment': 'Explicit rule|statement caller premise, identical within each positive/negative pair, never learned. Only copy to output when predicted condition is present, otherwise null.',
        'fresh_exclusion': 'Exclude the union of5120normalizedsources/2560groups from ALL FOUR old banks, including observed/declared facet values, semantic heads and declared content words. New TRAIN/selection/final declared content words, facet values and semantic heads are mutually disjoint under NFKC-casefold-whitespace normalization; no prefix-only old identity replacement.',
        'old_source_bindings': old_bindings, 'fresh_declared_lexicons': LEXICONS,
        'balance': 'TRAIN512positives:64/template;16/nullablecell/template and16finitealias/category per template. Selection/final64positives:8/template;2/nullablecell/template and2finitealias/category per template. Every template uses all8actionlemmas,8eachTRAIN/1eachevaluation. O/P/F are as close as integer counts permit. Exact joint, Unicode, repeated-mention and nullable ledgers remain in manifest.',
        'optimizer_steps_per_arm': 240, 'batch_size': 16, 'positive_per_batch': 8, 'negative_per_batch': 8,
        'parent_groups_per_batch': 8, 'groups_per_negative_category_per_batch': 2,
        'paired_schedule': 'Four128-group category pools cycle after full consumption. Each batch takes2actualparentgroups/category; each selected group contributes its original positive+corresponding negative. Group order is shuffled; there are no separate positive/negative random samplers. Both arms must use identical IDs/order and actual commit accounting.',
        'scheduled_input_records_per_arm': 3840, 'scheduled_group_presentations_per_arm': 1920,
        'training_schedule_sha256': digest(batches), 'training_schedule_file': 'training-schedule.json',
        'selection_steps': [0,120,240], 'selection_positive_count':64, 'selection_negative_count':64,
        'selection_paired_group_count':64,
        'selection_score_owner': 'Root experiment-plan/selector separately defines paired positive retention plus baseline negative-emission and aggregate success/emission/refusal floors; no final references choose checkpoints.',
        'support_threshold':0.5, 'source_chars_max':8192, 'source_tokens_max':96, 'token_UTF8_bytes_max':64,
        'source_features': 'Raw source UTF8 only; no ID/group/template/category/reference/declaredlemma metadata enters numerical features. No parser, lexical oracle, source search, anchor repair, target lookup or truncation.',
        'output_profile':'Single-rule predicted source-occurrence proposal; null formal output and zero admission masks.',
        'unsupported_reference_contract':'supported=false,prediction=null; no negative modality/class/span/presence target; unsupported means outside the authored profile, not legally false.',
        'fitting_reference_contract':'Only supportedboolean labels are fitting supervision. All16 sources are encoded; actual frozen-parent TRAIN emission/logit supplies the optional online margin. Positive spans/modality/optionalpresence/actionlemma/negativecategory are construction/scoring/fairness/schedule audit fields, never numerical loss targets.',
        'final_reference_barrier':'This author construction and mechanical transport process sees all640positive references. Both arm selections/checkpoints must be durable before the runner parses any new final or earlier retention references. All source-only parent+bothselectedarm panels on newfinal and ALL FOUR oldfinals must be durable/fsynced before any evaluation reference joins. This is a numerical barrier, not an authors-blind label or independent-gold claim.',
        'retention_policy':'Four exposed old final128-case cohorts,512oldretentioncases total. Keep all sources/paired groups/whole gains/losses/refusal/negative emissions/frozen signatures. Oldfinal labels remain outside fitting and selection; they are exposed postfit retention.',
        'law_source_semantics_verified':False, 'independent_legal_review':False, 'legal_gold':False,
        'admission_masks':dict(base.ZERO_MASKS), 'numerical_model_encoder_optimizer_prover_calls':0,
        'isolated_transport_source_commit':SOURCE_COMMIT,
        'source_builder':{'path':str(Path(__file__).resolve()),'sha256':sha(Path(__file__))}}
    artifacts = {}
    def save(name, value):
        data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        p = output / name
        with p.open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
        artifacts[name] = {'path': str(p), 'sha256': hashlib.sha256(data).hexdigest(),
                           'bytes': len(data), 'canonical_sha256': digest(value)}
    for split, values in corpus.items():
        for role in ('inputs', 'references'):
            save(f'{split}-{role}.json', values[role])
    save('corpus-protocol.json', plan)
    save('training-schedule.json', schedule_audit(corpus['train']['inputs'], corpus['train']['references'], batches))
    owners = [Path(datasets_root) / 'ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_span_proposal.py',
              Path(datasets_root) / 'ipfs_datasets_py/logic/legal_ir/canonical_statement_scope.py']
    manifest = {'schema': 'fresh-support-retention-authored-corpus-manifest/v1', 'complete': True,
        'seed': seed, 'source_profile': SOURCE_PROFILE, 'artifacts': dict(artifacts), 'statistics': {s: statistics(v) for s, v in corpus.items()},
        'construction_source': plan['source_builder'], 'versioned_old_source_inputs': old_bindings,
        'proposal_owner_bindings': [{'path': str(p.resolve()), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in owners],
        'training_schedule_sha256': digest(batches), 'source_rows': 1280, 'source_parent_groups': 640,
        'distinct_train_sources_presented': len({s for b in batches for s in b}),
        'prior_union_source_count': 5120, 'prior_union_group_count': 2560, 'old_sources_normalized_overlap': 0, 'old_source_groups_overlap': 0,
        'old_observed_and_declared_facet_overlap': dict.fromkeys(FACETS, 0),
        'old_declared_identity_head_overlap': dict.fromkeys(FACETS, 0),
        'fresh_split_facet_and_identity_head_overlap': dict.fromkeys(FACETS, 0),
        'old_declared_content_word_overlap': 0, 'fresh_split_declared_content_word_overlap': 0,
        'same_text_duplicated_for_caller_profiles': False,
        'positive_scope_transport_validations': 640, 'all_admission_masks0': True,
        'paired_schedule_audit': {k:v for k,v in schedule_audit(corpus['train']['inputs'],corpus['train']['references'],batches).items() if k not in ('batches','batch_groups','per_batch_checks','source_exposure_counts','group_exposure_counts')},
        'prior_exclusion_inventory_counts': {k:len(v) if isinstance(v,set) else {f:len(x) for f,x in v.items()} for k,v in earlier_inventory(base).items()},
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
