"""Versioned private authored candidates, original-target lineage, stdlib only.

No semantic parser, numerical owner, encoder, model or training admission is used.
Every original row, candidate and rejected wording revision remains accounted for.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import re
from types import SimpleNamespace

WORKSPACE = Path('/home/barberb/lift_coding')
OWNER_ROOT = WORKSPACE / 'artifacts/autoencoder-balanced-wording-20261007/candidates'
B = WORKSPACE / 'external/ipfs_datasets/workspace/test-logs'
E = B / 'decoder-normative-wording-r2-20261006/preparation-r1/results'
ORIGINAL_BANK = B / 'decoder-training-paraphrases-r4-20261004/preparation-r1/results/original-training-bank-used.json'
CODEC = WORKSPACE / 'artifacts/autoencoder-wording-fit-20261006/development/codec.json'
SEALED_DEV = WORKSPACE / 'artifacts/autoencoder-wording-fit-20261006/development'
V3 = B / 'decoder-fresh-normative-style-r2-20261004/preparation-r1/results'
NEXT_PLAN = WORKSPACE / 'artifacts/autoencoder-next-reconstruction-gap-20261006/documentation/evidence/next-training-plan.json'
FACETS = {'actor', 'action', 'object', 'modality', 'conditions', 'exceptions', 'temporal'}
MODALITIES = ('O', 'P', 'F')
GERUNDS = {'approve': 'approving', 'deliver': 'delivering', 'examine': 'examining',
           'preserve': 'preserving', 'publish': 'publishing'}
FAMILIES = ('dummy_subject_deontic_infinitive_v1', 'possessive_gerund_deontic_subject_v1')
TEMPLATES = FAMILIES
SEED = 20261006  # Exact E paragraph packing; source rendition changes, grouping does not.
SCHEMA = 'balanced-wording-training-sources/v1'
SOURCE_SCHEMA = SCHEMA
REJECTED_FAMILY = 'gerund_actor_final_for_v0'
ACTORS = {'notary', 'registrar', 'secretary', 'treasurer', 'trustee'}
OBJECTS = {'archive', 'notice'}
EXPECTED_PRIOR = {'composition64': 64, 'exposed_r6': 48, 'exposed_r8': 48, 'exposed_v3': 48,
                  'original_train_bank': 180, 'paragraph_train': 48, 'paragraph_validation': 48,
                  'prospective_development_sources': 60, 'r4_training_paraphrases': 48,
                  'raw_canary': 30, 'raw_test': 60, 'raw_train': 180, 'raw_validation': 60}
FALSE = dict.fromkeys(('train_eligible', 'training_admitted', 'source_semantics_verified', 'proof_authority',
                      'qualified', 'admitted', 'formalized', 'roundtrip_ok', 'training_executed',
                      'models_executed', 'encoders_executed', 'downloads_performed', 'Lake_executed',
                      'Constitution_formalized', 'independent_human_review_authenticated',
                      'reviewed_natural_law_gold', 'fresh_holdout'), False)
CANDIDATE_SCHEMA = 'balanced-authored-wording-candidates/v1'
REQUIRED_PRIOR_COUNTS = {**EXPECTED_PRIOR, 'current_normative_train': 48}
REQUIRED_PRIOR_DATASETS = tuple(REQUIRED_PRIOR_COUNTS)
VOCABULARY = ['<pad>', '<bos>', '<eos>', '"F"', '"O"', '"P"', '"action"',
    '"actor"', '"approve"', '"archive"', '"conditions"', '"deliver"', '"examine"',
    '"exceptions"', '"modality"', '"notary"', '"notice"', '"object"', '"preserve"',
    '"publish"', '"registrar"', '"rules"', '"secretary"', '"temporal"',
    '"treasurer"', '"trustee"', ',', ':', '[', ']', '{', '}']
TOKEN = re.compile(r'"(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"|[{}\[\],:]')
SHA = re.compile(r'[0-9a-f]{64}\Z')
TRANSPORT_FALSE = {**FALSE, **dict.fromkeys(('source_alignment_reviewed', 'source_semantics_reviewed',
    'independent_human_review', 'encoder_executed', 'embedding_inference_executed', 'lake_executed',
    'checkpoint_promoted', 'historical_linguistic_teacher_modified', 'training_allowed', 'selection_allowed',
    'holdout_evaluated', 'fresh_holdout_claimed', 'evaluation_scored', 'encoder_context_increased'), False)}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def source_digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def normalized(text):
    return ' '.join(text.casefold().split())


def decode_original_target(ids, vocabulary):
    if type(ids) is not list or len(ids) != 40 or ids[0] != 1 or ids[-1] != 2:
        raise ValueError('exact original40-token BOS1/EOS2 target required')
    if any(type(i) is not int or not 0 <= i < 32 for i in ids):
        raise ValueError('original32-value token IDs required')
    try:
        target = json.loads(''.join(vocabulary[i] for i in ids[1:-1]))
    except (TypeError, ValueError, IndexError) as error:
        raise ValueError('original target tokens do not decode') from error
    if type(target) is not dict or set(target) != {'rules'} or type(target['rules']) is not list or len(target['rules']) != 1:
        raise ValueError('one exact original rule required')
    rule = target['rules'][0]
    if type(rule) is not dict or set(rule) != FACETS:
        raise ValueError('complete original seven-facet rule required')
    if rule['actor'] not in ACTORS or rule['action'] not in GERUNDS or rule['object'] not in OBJECTS or rule['modality'] not in MODALITIES:
        raise ValueError('unexpected original lexical identity')
    if any(rule[name] != [] for name in ('conditions', 'exceptions', 'temporal')):
        raise ValueError('nonempty qualifiers cannot enter normative32V candidate lane')
    return target


def original_identities(bank, vocabulary):
    if type(bank) is not list or len(bank) != 180 or vocabulary != VOCABULARY:
        raise ValueError('complete original180 source bank and32-token codec required')
    identities, ids, sources = {}, set(), set()
    for index, row in enumerate(bank):
        if type(row) is not dict or set(row) != {'id', 'source_text', 'target_ids'}:
            raise ValueError('closed saved original-bank row required')
        if type(row['id']) is not str or not 0 < len(row['id']) <= 1024 or row['id'] in ids or type(row['source_text']) is not str or not row['source_text'].strip() or '\n\n' in row['source_text'] or len(row['source_text'].encode('utf-8')) > 32768 or normalized(row['source_text']) in sources:
            raise ValueError('original IDs/sources must remain unique')
        ids.add(row['id']); sources.add(normalized(row['source_text']))
        target = decode_original_target(row['target_ids'], vocabulary)
        rule_sha = digest(target['rules'][0])
        record = identities.setdefault(rule_sha, {'original_rule_sha256': rule_sha, 'target': target,
            'target_ids': list(row['target_ids']), 'target_sha256': digest(target), 'target_ids_sha256': digest(row['target_ids']),
            'original_bank_first_index': index, 'original_train_sources': []})
        if record['target'] != target or record['target_ids'] != row['target_ids']:
            raise ValueError('same-rule original token aliases differ')
        record['original_train_sources'].append({'id': row['id'], 'source_sha256': source_digest(row['source_text']),
            'target_sha256': digest(target), 'target_ids_sha256': digest(row['target_ids'])})
    if len(identities) != 90 or any(len(x['original_train_sources']) != 2 for x in identities.values()):
        raise ValueError('exact90 identities with two original aliases each required')
    groups = {}
    for record in identities.values():
        rule = record['target']['rules'][0]
        groups.setdefault((rule['actor'], rule['action'], rule['object']), set()).add(rule['modality'])
    if len(groups) != 30 or any(value != set(MODALITIES) for value in groups.values()):
        raise ValueError('complete30 original actor/action/object groups with all O/P/F required')
    return sorted(identities.values(), key=lambda x: x['original_bank_first_index'])


def _require(value, message):
    if not value:
        raise ValueError(message)


def _codec(codec):
    _require(type(codec) is dict and set(codec) == {'schema', 'target_vocabulary'}
             and codec['schema'] == 'typed-json-lexical/v1' and codec['target_vocabulary'] == VOCABULARY,
             'exact unchanged32-value lexical codec required')


def _rules(target, validate_rule):
    _require(callable(validate_rule) and type(target) is dict and set(target) == {'rules'}
             and type(target['rules']) is list and 1 <= len(target['rules']) <= 8,
             'one through eight exact rules and supplied syntax validator required')
    for rule in target['rules']:
        sentence(TEMPLATES[0], rule)  # Strict complete lexical/empty-qualifier check, no prose parser.
        supplied = {'rules': [deepcopy(rule)]}
        before = canonical(supplied)
        answer = validate_rule(supplied)
        _require(canonical(supplied) == before and type(answer) is dict and answer.get('valid') is True
                 and ('canonical_ir' not in answer or canonical(answer['canonical_ir']) == before),
                 'supplied syntax validator failed, mutated or normalized target')


def _encode(target, codec):
    _codec(codec)
    wire = canonical(target).decode('utf-8')
    tokens = TOKEN.findall(wire)
    _require(''.join(tokens) == wire and all(token in VOCABULARY for token in tokens),
             'complete target cannot be encoded without changing original vocabulary')
    ids = [1] + [VOCABULARY.index(token) for token in tokens] + [2]
    _require(len(ids) <= 512 and json.loads(''.join(VOCABULARY[i] for i in ids[1:-1])) == target,
             'target lost fields or exceeds fixed512 output cap')
    return ids


def sentence(template, rule):
    _require(type(rule) is dict and set(rule) == FACETS
             and all(type(rule[key]) is list and not rule[key] for key in ('conditions', 'exceptions', 'temporal')),
             'complete unchanged seven-facet empty-qualifier rule required; no dropped facet')
    _require(template in TEMPLATES and all(type(rule[name]) is str for name in ('actor', 'action', 'object', 'modality'))
             and rule['actor'] in ACTORS and rule['action'] in GERUNDS and rule['object'] in OBJECTS and rule['modality'] in MODALITIES,
             'closed original lexical inventory and declared current template required')
    return render(rule, template)


# Existing native preparation needs only these pure base contracts; no inherited
# package or numerical owner is imported. The names retain existing call shapes.
text_sha = source_digest
base = SimpleNamespace(text_sha=text_sha, digest=digest, raw=canonical, _normal=normalized,
                       _codec=_codec, _encode=_encode, _rules=_rules, _require=_require,
                       _SHA=SHA, _RULE_KEYS=FACETS, ACTORS=tuple(sorted(ACTORS)),
                       ACTIONS=tuple(GERUNDS), OBJECTS=tuple(sorted(OBJECTS)), MODALITIES=MODALITIES)


def _prior_inventory(inventories, training_bank):
    _require(type(inventories) is dict and set(REQUIRED_PRIOR_DATASETS) <= set(inventories)
             and 1 <= len(inventories) <= 32,
             'complete original E inventories and current normative TRAIN required')
    _require(all(len(inventories[name]) == count for name, count in REQUIRED_PRIOR_COUNTS.items()),
             'complete prior source row counts differ; no partial exclusion bank')
    expected = {row['id']: row['source_text'] for row in training_bank}
    _require({row['id']: row['source_text'] for row in inventories['original_train_bank']} == expected,
             'original TRAIN provenance inventory differs from saved bank')
    forbidden, literals, prior_ids, reports, total_bytes = set(), set(), {}, {}, 0
    for name, rows in inventories.items():
        _require(type(name) is str and name and type(rows) is list and 1 <= len(rows) <= 256,
                 'bounded named nonempty prior inventory required')
        ids, normals, shas = set(), set(), set()
        for row in rows:
            _require(type(row) is dict and set(row) == {'id', 'source_text'}
                     and type(row['id']) is str and 0 < len(row['id']) <= 1024
                     and type(row['source_text']) is str and row['source_text'].strip()
                     and len(row['source_text'].encode('utf-8')) <= 32768,
                     'closed bounded explicit prior source required; no target fields')
            text = row['source_text']; pieces = text.split('\n\n')
            _require(all(piece.strip() for piece in pieces) and row['id'] not in ids
                     and (row['id'] not in prior_ids or prior_ids[row['id']] == text),
                     'empty source clause, duplicate ID or conflicting prior ID')
            ids.add(row['id']); prior_ids[row['id']] = text
            normals.update(normalized(value) for value in (text, *pieces))
            shas.update(text_sha(value) for value in (text, *pieces))
            total_bytes += len(text.encode('utf-8'))
            _require(total_bytes <= 16 * 1024**2, 'prior inventory exceeds16MiB bound')
        forbidden.update(normals); literals.update(shas)
        reports[name] = {'rows': len(rows), 'source_rows_sha256': digest(rows),
                         'normalized_paragraph_and_clause_count': len(normals), 'literal_sha256_count': len(shas)}
    return forbidden, literals, set(prior_ids), reports


def _stratum_rules(rules, ordinal):
    groups = {}
    for key, rule in rules.items():
        group = tuple(rule[name] for name in ('actor', 'action', 'object'))
        modalities = groups.setdefault(group, {})
        _require(rule['modality'] not in modalities, 'duplicate original content-group modality')
        modalities[rule['modality']] = key
    _require(len(groups) == 30 and all(set(value) == set(MODALITIES) for value in groups.values()),
             'complete30 original O/P/F content groups required')
    rng = random.Random(SEED + ordinal)
    ordered = sorted(groups); rng.shuffle(ordered)
    variants = {}
    for group in ordered:
        keys = [groups[group][modality] for modality in MODALITIES]
        rng.shuffle(keys); variants[group] = keys
    return [variants[group][round_] for round_ in range(3) for group in ordered]


def build(*, training_bank, prior_sources_by_dataset, codec, sealed_recipe_sha256,
          validate_rule, seed=SEED):
    """Compatible source-only48/180 fixture build; supplied seal is no authority.

    Each original meaning has one source rendition in each of two template slots.
    Any collision refuses the entire transport build; authored candidate/rejection
    ledgers are stored separately and never reduced to an easy surviving subset.
    """
    _require(type(seed) is int and seed == SEED, 'fixed original E packing seed20261006 required')
    _require(type(sealed_recipe_sha256) is str and SHA.fullmatch(sealed_recipe_sha256),
             'explicit sealed recipe SHA256 required')
    _codec(codec)
    identities = original_identities(training_bank, codec['target_vocabulary'])
    rules = {record['original_rule_sha256']: record['target']['rules'][0] for record in identities}
    derivations = {record['original_rule_sha256']: record['original_train_sources'] for record in identities}
    for record in identities:
        _rules(record['target'], validate_rule)
        _require(_encode(record['target'], codec) == record['target_ids'], 'original target IDs changed')
    for field, wanted in {'actor': dict.fromkeys(ACTORS, 18), 'action': dict.fromkeys(GERUNDS, 18),
                          'object': dict.fromkeys(OBJECTS, 45), 'modality': dict.fromkeys(MODALITIES, 30)}.items():
        _require(Counter(rule[field] for rule in rules.values()) == wanted, 'complete original field balance differs: ' + field)
    forbidden, old_literals, old_ids, inventory = _prior_inventory(prior_sources_by_dataset, training_bank)
    rows, references, clause_references, pairing = [], [], [], []
    used_clauses, used_paragraphs, clause_shas, paragraph_shas = set(), set(), set(), set()
    for template_slot, template in enumerate(TEMPLATES):
        members = []
        for key in _stratum_rules(rules, template_slot):
            text = sentence(template, rules[key]); normal = normalized(text); literal = text_sha(text)
            _require(normal not in forbidden and literal not in old_literals
                     and normal not in used_clauses and literal not in clause_shas,
                     'candidate clause overlaps prior/generated source; whole transport build refused')
            used_clauses.add(normal); clause_shas.add(literal); members.append((key, text))
        cursor = 0
        for count in (1, 2, 4, 8):
            for index in range(6):
                selected = members[cursor:cursor + count]; cursor += count
                text = '\n\n'.join(value for _, value in selected)
                literal = text_sha(text); normal = normalized(text)
                paragraph_id = 'balanced-training-v1:' + literal
                _require(normal not in forbidden and literal not in old_literals
                         and normal not in used_paragraphs and literal not in paragraph_shas
                         and paragraph_id not in old_ids,
                         'candidate paragraph/source-parent overlaps prior; whole transport build refused')
                used_paragraphs.add(normal); paragraph_shas.add(literal)
                target = {'rules': [deepcopy(rules[key]) for key, _ in selected]}
                _require(len({tuple(rule[name] for name in ('actor', 'action', 'object')) for rule in target['rules']}) == count,
                         'paragraph repeats a conflicting original content group')
                _rules(target, validate_rule); ids = _encode(target, codec)
                clause_ids, paragraph_derivations = [], []
                for slot, (key, value) in enumerate(selected):
                    clause_id = 'balanced-training-clause-v1:' + text_sha(value)
                    _require(clause_id not in old_ids, 'candidate clause ID overlaps prior provenance')
                    clause_ids.append(clause_id)
                    single = {'rules': [deepcopy(rules[key])]}; single_ids = _encode(single, codec)
                    derivation = {'rule_sha256': key, 'original_train_sources': deepcopy(derivations[key])}
                    paragraph_derivations.append(deepcopy(derivation))
                    clause_references.append({'id': clause_id, 'source_text': value, 'source_sha256': text_sha(value),
                        'split': 'train_augmentation', 'template': template, 'modality_stratum': rules[key]['modality'],
                        'parent_paragraph_id': paragraph_id, 'slot': slot, 'target': single, 'target_ids': single_ids,
                        'target_sha256': digest(single), 'target_ids_sha256': digest(single_ids), 'original_rule_sha256': key,
                        'derivations': [derivation], 'reference_origin': 'authored_rendering_of_original_TRAIN_rules', **TRANSPORT_FALSE})
                    pairing.append({'pairing_key': key + ':template-slot:' + str(template_slot), 'template_slot': template_slot,
                        'template': template, 'original_rule_sha256': key, 'modality': rules[key]['modality'],
                        'clause_id': clause_id, 'source_sha256': text_sha(value), 'parent_paragraph_id': paragraph_id,
                        'paragraph_source_sha256': literal, 'slot': slot, 'target_ids_sha256': digest(single_ids)})
                rows.append({'id': paragraph_id, 'source_text': text})
                references.append({'id': paragraph_id, 'source_text': text, 'source_sha256': literal, 'split': 'train_augmentation',
                    'template': template, 'clause_count': count, 'index_within_template_length': index,
                    'clause_ids': clause_ids, 'target': target, 'target_ids': ids, 'target_sha256': digest(target),
                    'target_ids_sha256': digest(ids), 'derivations': paragraph_derivations,
                    'reference_origin': 'authored_rendering_of_original_TRAIN_rules', **TRANSPORT_FALSE})
        _require(cursor == len(members) == 90, 'complete no-replacement original meaning census required')
    _require(len(rows) == len(references) == 48 and len(clause_references) == len(pairing) == 180
             and len({x['pairing_key'] for x in pairing}) == 180
             and Counter(x['clause_count'] for x in references) == {1: 12, 2: 12, 4: 12, 8: 12}
             and Counter((x['template'], x['modality_stratum']) for x in clause_references)
                 == {(template, modality): 30 for template in TEMPLATES for modality in MODALITIES},
             'complete48/180 and six balanced30-clause strata required')
    unique_sources = set(text_sha(row['source_text']) for row in rows) | clause_shas
    _require(len(unique_sources) == 216, 'complete216 unique native source strings required')
    templates = {template: [sentence(template, rules[key]) for key in sorted(rules)] for template in TEMPLATES}
    receipt = {'schema': SOURCE_SCHEMA, 'complete': True, 'role': 'train_augmentation', 'seed': seed,
        'sealed_recipe_sha256': sealed_recipe_sha256, 'lifecycle_seal_verified': False,
        'original_train_bank_sha256': digest(training_bank), 'original_train_sources': 180, 'unique_original_train_rules': 90,
        'source_rows_sha256': digest(rows), 'references_sha256': digest(references),
        'clause_references_sha256': digest(clause_references), 'pairing_census_sha256': digest(pairing),
        'codec_sha256': digest(codec), 'vocabulary_size': 32, 'source_paragraphs': 48, 'unique_clauses': 180,
        'clause_occurrences': 180, 'single_clause_paragraph_aliases': 12, 'unique_source_strings': 216,
        'templates': list(TEMPLATES), 'gerunds': deepcopy(GERUNDS), 'rendered_templates_sha256': digest(templates),
        'prior_inventory': inventory, 'required_prior_datasets': list(REQUIRED_PRIOR_DATASETS),
        'required_prior_row_counts': deepcopy(REQUIRED_PRIOR_COUNTS), 'prior_sources_sha256': digest(prior_sources_by_dataset),
        'prior_inventory_completeness_verified': False, 'source_rows_contain_targets': False,
        'original_target_roles_preserved': True, 'empty_qualifier_compatibility_verified': True,
        'provenance': 'authored_rendering_of_original_TRAIN_rules',
        'exclusion_policy': 'literal SHA256 and casefolded whitespace-normalized paragraphs/clauses plus source/parent IDs',
        'separation_claim': 'operational source-string/ID exclusion only; meanings intentionally reused, no independent semantic holdout',
        'paragraph_content_groups_unique': True,
        'packing_policy': 'exact original E three-round shuffled30-content-group order and O/P/F variants, seed20261006',
        'evaluation_labels_used': False, 'context_tokens': 512, 'decoder_output_tokens': 512, 'temperature': 0, **TRANSPORT_FALSE}
    receipt['receipt_sha256'] = digest(receipt)
    return {'source_rows': rows, 'references': references, 'clause_references': clause_references,
            'receipt': receipt, 'pairing_census': pairing}


def render(rule, family):
    actor, action, obj, modality = (rule[name] for name in ('actor', 'action', 'object', 'modality'))
    gerund = GERUNDS[action]
    if family == FAMILIES[0]:
        predicate = {'O': 'mandatory', 'P': 'permissible', 'F': 'forbidden'}[modality]
        return f'It is {predicate} for the {actor} to {action} the {obj}.'
    predicate = {'O': 'mandatory', 'P': 'permitted', 'F': 'forbidden'}[modality]
    if family == FAMILIES[1]:
        return f"The {actor}'s {gerund} the {obj} is {predicate}."
    if family == REJECTED_FAMILY:
        return f'{gerund.capitalize()} the {obj} is {predicate} for the {actor}.'
    raise ValueError('unknown authored wording family; no fallback renderer')


def candidate(record, family, index):
    rule = record['target']['rules'][0]
    text = render(rule, family)
    result = {**FALSE, 'id': 'balanced-wording-candidate-v1:' + source_digest(text), 'source_text': text,
        'source_sha256': source_digest(text), 'normalized_source_sha256': source_digest(normalized(text)),
        'split': 'candidate_train_augmentation', 'template': family, 'template_family': family,
        'stratum': family + ':' + rule['modality'], 'modality': rule['modality'],
        'source_group': {'template_family': family, 'actor': rule['actor'], 'action': rule['action'], 'object': rule['object']},
        'original_target_meaning_previously_exposed': True,
        'original_actor_action_object_group': [rule['actor'], rule['action'], rule['object']],
        'original_bank_first_index': record['original_bank_first_index'], 'index_within_family': index,
        'original_rule_sha256': record['original_rule_sha256'], 'target': record['target'],
        'target_ids': record['target_ids'], 'target_sha256': record['target_sha256'],
        'target_ids_sha256': record['target_ids_sha256'], 'original_train_sources': record['original_train_sources'],
        'label_provenance': 'authored fixture rendering of unchanged saved original TRAIN target IDs; not natural-law translation',
        'authored_pair_review_status': 'pending_complete_independent_fixture_review',
        'source_formal_alignment_reviewed': False, 'pair_semantic_authority': False,
        'context': {'role': 'none_required', 'text': '', 'bindings': {}, 'sha256': source_digest('')},
        'automatic_transport_or_training_admission': False,
    }
    return result


def build_candidates(identities):
    current = [candidate(record, family, i) for family in FAMILIES for i, record in enumerate(identities)]
    rejected = []
    for index, record in enumerate(identities):
        row = candidate(record, REJECTED_FAMILY, index)
        replacement = candidate(record, FAMILIES[1], index)
        row.update(candidate_status='rejected_wording_draft_retained',
                   rejection_reason='Actor-final for-phrase can identify a beneficiary/affected party instead of the action agent.',
                   revision_source='Independent reviewer requested explicit agency; possessive gerund subject replaces actor-final for-phrase.',
                   replaced_by_candidate_id=replacement['id'])
        rejected.append(row)
    for row in current:
        row['candidate_status'] = 'proposed_pending_independent_fixture_review'
    return current, rejected


def expanded_sources(rows):
    result = []
    for row in rows:
        text = row['source_text']
        if type(text) is not str or not text.strip():
            raise ValueError('explicit nonempty prior source required')
        result.append({'id': row['id'], 'kind': 'whole_source', 'source_text': text})
        if '\n\n' in text:
            result.extend({'id': row['id'] + ':clause:' + str(i), 'kind': 'clause', 'source_text': part}
                          for i, part in enumerate(text.split('\n\n')))
    return result


def overlaps(rows, inventories):
    reports = {}
    retained = []
    for name, prior in inventories.items():
        strings = expanded_sources(prior)
        literals, normals = {}, {}
        for row in strings:
            literals.setdefault(row['source_text'], []).append({'id': row['id'], 'kind': row['kind']})
            normals.setdefault(normalized(row['source_text']), []).append({'id': row['id'], 'kind': row['kind']})
        hits = []
        for row in rows:
            literal_hits = literals.get(row['source_text'], [])
            normal_hits = normals.get(normalized(row['source_text']), [])
            if literal_hits or normal_hits:
                hit = {'candidate_id': row['id'], 'candidate_status': row['candidate_status'],
                       'source_sha256': row['source_sha256'], 'literal_matches': literal_hits, 'normalized_matches': normal_hits}
                hits.append(hit); retained.append({'prior_bank': name, **hit})
        reports[name] = {'rows': len(prior), 'expanded_whole_source_and_clause_occurrences': len(strings),
                         'unique_literal_sources': len(literals), 'unique_normalized_sources': len(normals),
                         'source_rows_sha256': digest(prior), 'literal_overlap_candidates': sum(bool(x['literal_matches']) for x in hits),
                         'normalized_overlap_candidates': sum(bool(x['normalized_matches']) for x in hits), 'overlaps': hits}
    return reports, retained


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=OWNER_ROOT / 'results/draft-r1')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if not out.is_relative_to(OWNER_ROOT.resolve()) or out.exists():
        raise ValueError('new, private-owned candidate output directory required; no overwrites')
    bindings = {}

    def read(path):
        data = path.read_bytes()
        bindings[str(path)] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        return json.loads(data)

    plan = read(NEXT_PLAN)
    assert plan['new_fitting_approved_by_this_plan'] is False
    bank = read(ORIGINAL_BANK)
    codec = read(CODEC)
    identities = original_identities(bank, codec['target_vocabulary'])
    receipt = read(E / 'training-corpus-receipt.json')
    assert digest(bank) == receipt['original_train_bank_sha256']
    assert GERUNDS == receipt['gerunds'] and receipt['unique_original_train_rules'] == 90
    # Independently cross-check original IDs/hashes against E's completed TRAIN derivations.
    e_refs = read(E / 'training-references.json')
    derivations = {}
    for reference in e_refs:
        for derivation, rule in zip(reference['derivations'], reference['target']['rules'], strict=True):
            assert derivation['rule_sha256'] == digest(rule)
            expected = {row['id']: row for row in derivation['original_train_sources']}
            if digest(rule) in derivations:
                assert expected == derivations[digest(rule)]
            derivations[digest(rule)] = expected
    assert set(derivations) == {x['original_rule_sha256'] for x in identities}
    for identity in identities:
        assert {row['id']: row for row in identity['original_train_sources']} == derivations[identity['original_rule_sha256']]
    prior = read(E / 'prior-source-inventories.json')
    assert set(prior) == set(EXPECTED_PRIOR) and {k: len(v) for k, v in prior.items()} == EXPECTED_PRIOR
    for name, rows in prior.items():
        assert digest(rows) == receipt['prior_inventory'][name]['source_rows_sha256']
    current_normative = read(E / 'source-rows.json')
    sealed60 = read(SEALED_DEV / 'source-rows.json')
    sealed_receipt = read(SEALED_DEV / 'development-corpus-receipt.json')
    v3_sources = read(V3 / 'source-rows.json')
    v3_receipt = read(V3 / 'holdout-receipt.json')
    assert len(current_normative) == 48 and len(sealed60) == 60 and len(v3_sources) == 48
    assert prior['prospective_development_sources'] == sealed60 and prior['exposed_v3'] == v3_sources
    prior['current_normative_train'] = current_normative
    prior['sealed60_development_primary'] = sealed60
    prior['exposed_v3_primary'] = v3_sources
    candidates, rejected = build_candidates(identities)
    assert len(candidates) == 180 and len(rejected) == 90
    assert Counter(row['stratum'] for row in candidates) == Counter({family + ':' + modality: 30 for family in FAMILIES for modality in MODALITIES})
    assert len({row['source_text'] for row in candidates}) == len({normalized(row['source_text']) for row in candidates}) == 180
    inventory, overlap_rows = overlaps(candidates + rejected, prior)
    candidate_overlap_ids = {row['candidate_id'] for row in overlap_rows if row['candidate_status'] == 'proposed_pending_independent_fixture_review'}
    for row in candidates:
        row['source_overlap_found_in_declared_prior_banks'] = row['id'] in candidate_overlap_ids
        row['source_overlap_check_scope'] = 'byte-pinned declared16 inventories, including whole sources and newline-separated clauses; not all historical language'
    actor_actions = sorted({(x['target']['rules'][0]['actor'], x['target']['rules'][0]['action']) for x in identities})
    assert actor_actions == [tuple(x) for x in sealed_receipt['original_train_actor_action_groups']]
    sealed_group_overlap = sorted(set(actor_actions) & {tuple(x) for x in sealed_receipt['validation_actor_action_groups']})
    assert not sealed_group_overlap
    exposure = {'schema': 'balanced-wording-source-overlap-and-exposure/v1', **FALSE,
        'checked_prior_banks': inventory, 'checked_prior_bank_count': len(prior),
        'all_proposed_pairs_retained': True, 'all_rejected_drafts_retained': True,
        'candidate_literal_or_normalized_overlap_count': len(candidate_overlap_ids), 'overlap_records': overlap_rows,
        'prior_inventory_completeness_scope': 'All13 complete E prior inventories plus current normative TRAIN and explicit primary sealed60/v3 aliases; external unrelated corpora not claimed.',
        'normalization': 'casefold and whitespace collapse only; whole paragraphs and exact newline-separated clauses; no punctuation stripping or semantic normalization',
        'original_meaning_exposure': {'original180_sources': 180, 'unique_original_rules': 90, 'original_target_rule_occurrences_in_new_bank': 180,
            'each_original_meaning_rendered_once_per_new_family': True, 'target_meaning_novelty_claimed': False,
            'original_actor_action_pairs': [list(x) for x in actor_actions], 'original_actor_action_object_groups': 30},
        'sealed60_actor_action_group_overlap': sealed_group_overlap,
        'exposed_v3_source_family_metadata': v3_receipt['family_roles'],
        'sealed60_source_families': sealed_receipt['templates'],
        'candidate_source_families': list(FAMILIES),
        'source_family_ID_overlap_with_v3_evaluation_or_sealed60': sorted(set(FAMILIES) & (set(v3_receipt['family_roles']['evaluation']) | set(sealed_receipt['templates']))),
        'construction_related_exposure': 'The dummy-subject infinitive is related to the previously exposed expletive_infinitival construction; a new family ID or literal cue does not establish syntactic novelty.',
        'source_group_definition': 'Reporting-only group: named authored family plus original actor/action/object identity. New family IDs do not establish independent source groups or exclude shared content meanings.',
        'operative_exclusion_policy': 'Exact and casefolded whitespace-normalized source strings plus source/clause/paragraph provenance IDs. Original semantic/content groups intentionally overlap; template/content grouping is reporting metadata, not an admission or novelty test.',
        'v3_targets_parsed_or_used_to_construct_candidates': False,
        'v3_semantic_meaning_group_overlap_computed': False,
        'semantic_group_limit': 'No semantic targets are reconstructed from v3 sources. Candidate targets derive exclusively from the saved original180 target IDs; v3 source/template metadata is exclusion evidence only.',
        'input_bindings': bindings}
    target_owner = {'schema': 'original90-target-identity-ledger/v1', **FALSE,
        'original180_bank_binding': {'path': str(ORIGINAL_BANK), **bindings[str(ORIGINAL_BANK)]},
        'original180_bank_canonical_sha256': digest(bank), 'codec_binding': {'path': str(CODEC), **bindings[str(CODEC)]},
        'codec_canonical_sha256': digest(codec), 'decoder_vocabulary_size': 32, 'original_rows': 180, 'unique_original_rules': 90,
        'E_derivation_identity_crosscheck_complete': True, 'rules': identities}
    bank_payload = {'schema': CANDIDATE_SCHEMA, **FALSE, 'status': 'draft_after_initial_independent_wording_suggestions_pending_complete_review',
        'candidate_count': 180, 'original_unique_rules': 90, 'families': list(FAMILIES),
        'stratum_counts': dict(Counter(row['stratum'] for row in candidates)), 'candidates': candidates,
        'candidate_source_rows_sha256': digest([{'id': x['id'], 'source_text': x['source_text']} for x in candidates]),
        'candidate_pairs_sha256': digest(candidates), 'original_bank_canonical_sha256': digest(bank),
        'original_target_owner': 'original90-target-identities.json', 'versioned_renderers': 'source/build_balanced_wording_candidates.py',
        'schema_frozen': False, 'source_and_results_frozen': False}
    rejection_payload = {'schema': 'balanced-wording-rejected-drafts/v1', **FALSE,
        'rejected_draft_count': 90, 'rejected_family': REJECTED_FAMILY, 'all_records_retained': True,
        'rejection_is_wording_review_not_performance_selection': True, 'rejected_drafts': rejected}
    summary = {'schema': 'balanced-wording-author-candidate-check/v1', 'passed': True, 'findings': [], **FALSE,
        'candidate_count': 180, 'retained_rejected_drafts': 90, 'total_authored_pair_records_retained': 270,
        'stratum_counts': bank_payload['stratum_counts'], 'unique_original_rules': 90, 'original_alias_rows': 180,
        'original90_target_ids_actor_action_object_modality_empty_qualifiers_preserved': True,
        'all_180_candidate_target_ids_equal_saved_original_aliases': True, 'no_heuristic_gerund_stemming': True,
        'gerund_map': GERUNDS, 'original_actor_vocabulary': sorted(ACTORS), 'original_object_vocabulary': sorted(OBJECTS),
        'literal_normalized_candidate_overlap_count': len(candidate_overlap_ids),
        'overlaps_refuse_future_fit_but_are_not_removed': True, 'schema_or_source_freeze_performed': False,
        'full_independent_fixture_review_pending': True, 'no_feature_mode_or_optimizer_owner_selected': True,
        'context_tokens': 512, 'decoder_output_tokens': 512,
        'actual_encoder_tokens_measured': False, 'saved_target_id_length': 40,
        'target_formation': 'Decode pinned original target IDs by concatenating saved vocabulary tokens between original BOS1/EOS2, then preserve exact original IDs; no re-encoding or v3 targets.',
        'deliver_notice_prohibition_candidates': [{'id': x['id'], 'source_text': x['source_text'], 'original_rule_sha256': x['original_rule_sha256'], 'original_train_sources': x['original_train_sources']}
            for x in candidates if x['target']['rules'][0]['action'] == 'deliver' and x['target']['rules'][0]['object'] == 'notice' and x['modality'] == 'F'],
        'input_bindings': bindings}
    preview_recipe = {'schema': 'balanced-wording-private-packing-preview/v1', **FALSE,
        'status': 'draft_for_complete_independent_review_no_lifecycle_seal_claim',
        'source_builder_binding': {'path': str(Path(__file__).resolve()),
            'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'bytes': Path(__file__).stat().st_size},
        'candidate_pairs_sha256': bank_payload['candidate_pairs_sha256'], 'templates': list(TEMPLATES),
        'source_schema': SOURCE_SCHEMA, 'seed': SEED, 'paragraph_counts_by_length': {'1': 12, '2': 12, '4': 12, '8': 12},
        'packing_unchanged_from_original_E': True, 'target_meanings_unchanged': True,
        'source_input_fields': ['id', 'source_text'], 'no_feature_mode_or_optimizer_owner_selected': True,
        'input_bindings': deepcopy(bindings)}

    def syntax_only(target):
        return {'valid': True, 'canonical_ir': deepcopy(target)}

    payload = build(training_bank=bank, prior_sources_by_dataset=prior, codec=codec,
                    sealed_recipe_sha256=digest(preview_recipe), validate_rule=syntax_only)
    assert payload['receipt']['unique_source_strings'] == 216
    assert [x['target_ids'] for x in payload['references']] == [x['target_ids'] for x in e_refs]
    assert [x['clause_count'] for x in payload['references']] == [x['clause_count'] for x in e_refs]
    control_clauses = read(E / 'clause-training-references.json')
    control_templates = receipt['templates']
    control_by_pair = {}
    for row in control_clauses:
        slot = control_templates.index(row['template'])
        key = row['original_rule_sha256'] + ':template-slot:' + str(slot)
        assert key not in control_by_pair
        control_by_pair[key] = row
    paired = []
    for row in payload['pairing_census']:
        control = control_by_pair[row['pairing_key']]
        assert row['target_ids_sha256'] == control['target_ids_sha256']
        paired.append({**row, 'candidate_id': 'balanced-wording-candidate-v1:' + row['source_sha256'],
            'control_template': control['template'], 'control_clause_id': control['id'],
            'control_source_sha256': control['source_sha256'], 'control_parent_paragraph_id': control['parent_paragraph_id'],
            'control_slot': control['slot']})
        assert row['slot'] == control['slot']
    assert len(paired) == len(control_by_pair) == 180
    prior_ids = {row['id'] for rows in prior.values() for row in rows}
    assert not ({x['id'] for x in payload['source_rows']} | {x['id'] for x in payload['clause_references']}) & prior_ids
    summary.update(source_only_paragraphs=48, clause_references=180, native_unique_sources=216,
        exact_original_E_paragraph_target_ids_and_rule_order_preserved=True,
        complete_control_treatment_pairing_keys=180, new_source_and_parent_ids_disjoint_from_prior=True,
        compatible_pure_build_and_sentence_APIs=True, preview_recipe_digest_is_admission=False)
    out.mkdir(parents=True)
    for name, value in [('original90-target-identities.json', target_owner), ('candidate-bank.json', bank_payload),
                        ('rejected-drafts.json', rejection_payload), ('overlap-and-exposure.json', exposure), ('author-check.json', summary),
                        ('private-packing-preview-recipe.json', preview_recipe), ('source-rows.json', payload['source_rows']),
                        ('references.json', payload['references']), ('clause-references.json', payload['clause_references']),
                        ('source-receipt.json', payload['receipt']), ('pairing-census.json', payload['pairing_census']),
                        ('prior-source-inventories.json', prior),
                        ('control-treatment-pairing-census.json', {'schema': 'balanced-wording-control-treatment-pairing/v1', **FALSE,
                            'pairs': paired, 'pairing_count': 180, 'pairing_by_original_rule_and_template_slot_not_source_hash': True,
                            'target_ids_identical_for_each_pair': True, 'candidate_paragraph_targets_and_order_match_original_E': True,
                            'control_clause_references_binding': {'path': str(E / 'clause-training-references.json'), **bindings[str(E / 'clause-training-references.json')]},
                            'treatment_census_sha256': digest(payload['pairing_census']), 'pairs_sha256': digest(paired)})]:
        (out / name).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'output_dir': str(out), 'candidates': len(candidates), 'rejected_drafts_retained': len(rejected),
                      'strata': bank_payload['stratum_counts'], 'overlap_count': len(candidate_overlap_ids),
                      'source_only_paragraphs': 48, 'native_unique_sources': 216, 'paired_clause_keys': 180, 'schema_frozen': False}, sort_keys=True))


if __name__ == '__main__':
    main()
