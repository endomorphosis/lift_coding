"""Fixed synthetic profile-boundary data; no law-cache labels become gold."""
from collections import Counter
from hashlib import sha256
import itertools
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
OLD = OUT.parent / 'legal-grouped-head-v2-20261006/authored-span-v2-corpus.json'
PARENT = OUT.parent / 'legal-grouped-head-v2-20261006/run-02/epoch-003/checkpoint.json'


def digest(value):
    return sha256(value).hexdigest()


def write(name, value):
    path = OUT / name
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return {'path': str(path), 'sha256': digest(path.read_bytes()), 'bytes': path.stat().st_size}


def typo(word, excluded, nonce):
    values = sorted({''.join(p) for p in itertools.permutations(word)})
    values = [v for v in values if v not in excluded and v != word]
    if not values:
        values = [word[:i] + word[i] + word[i:] for i in range(len(word))]
        values = sorted(set(values) - excluded)
    assert values
    result = values[nonce % len(values)]
    assert result != word
    return result


def edit_modal(source, span, kind, changed_word):
    start, end = span
    old = source[start:end]
    assert old in ('shall', 'must', 'may', 'shall not', 'must not', 'is permitted to')
    if kind == 'missing_modal_local':
        assert source[end:end + 1] == ' '
        return source[:start] + source[end + 1:]
    word = 'permitted' if old == 'is permitted to' else old.split()[0]
    return source[:start] + old.replace(word, changed_word, 1) + source[end:]


original = json.loads(OLD.read_text())
assert digest(PARENT.read_bytes()) == 'efd7f7e71159592672769c7f580112917381e9a854f021a72f8de1613d299b95'
old_sources = {r['input']['source_text'] for r in original['rows']}
old_words = {w.casefold() for g in original['source_groups'] for m in g.get('members', [])
             for w in (m['actor'] + ' ' + m['action']).split()}
old_corruptions = {w.casefold() for table in original['corruption_strings_by_split'].values()
                   for value in table.values() for w in value.split()}
excluded = old_words | old_corruptions | {'shall', 'must', 'may', 'permitted'}
corruptions = {}
for split, nonce in [('train', 0), ('selection', 1), ('final', 2)]:
    corruptions[split] = {}
    for word in ('shall', 'must', 'may', 'permitted'):
        value = typo(word, excluded, nonce)
        corruptions[split][word] = value
        excluded.add(value)

train = [r for r in original['rows'] if r['split'] == 'train']
groups = {g['source_group_id']: g for g in original['source_groups'] if g['split'] == 'train' and g['supported']}
local_negatives = []
for index, row in enumerate(r for r in train if r['supported']):
    group = groups[row['source_group_id']]
    members = group['members']
    position_label = ('first', 'middle', 'last')[index % 3]
    position = {'first': 0, 'middle': len(members) // 2, 'last': len(members) - 1}[position_label]
    member = members[position]
    word = 'permitted' if member['modal_text'] == 'is permitted to' else member['modal_text'].split()[0]
    for kind in ('missing_modal_local', 'misspelled_modal_local'):
        source = edit_modal(group['source_text'], member['modal_span'], kind, corruptions['train'][word])
        identity = 'boundary-train-' + digest((source + '\0' + row['input']['modal_scope']).encode())
        local_negatives.append({'case_id': identity, 'source_group_id': identity,
            'parent_source_group_id': row['source_group_id'], 'split': 'train',
            'input': {'source_text': source, 'modal_scope': row['input']['modal_scope']},
            'supported': False, 'target_spans': [], 'target_request': None,
            'negative_category': kind, 'edited_member_index': position,
            'position_label': position_label, 'edited_modal_span': member['modal_span'],
            'source_semantics_reviewed': False})

colors = 'smaragdine xanthic griseous aeruginous porphyrous luteous albescent fuscous testaceous incarnadine flavescent violaceous piceous prasinous fulvous ferruginous'.split()
roles = 'palimpsestkeeper tessellationkeeper quirekeeper codicilkeeper fasciclekeeper colophonkeeper scrollwarden tabletwarden foliowarden slipwarden chartwarden cahierkeeper albumkeeper repertorist registerwarden volumewarden'.split()
verbs = 'emboss perforate fold staple bind tint etch trim pleat crimp ruffle notch punch crease tack buff suture glaze sand deburr chisel gild baste stitch weave braid lacquer anodize vitrify inlay bevel lacinate burnish cure sieve strain temper anneal solder'.split()
objects = 'vellum parchment cyanotype linocut woodcut intaglio etching watermark filigree frieze cameo basrelief tapestry colophon palimpsest foliolet codex quarto octavo quilt sampler aquatint mezzotint linoleum rubbing wainscot plaque panel'.split()
verbs = [v for v in verbs if v not in old_words][:16]
objects = [v for v in objects if v not in old_words][:16]
assert len(verbs) == len(objects) == 16
assert not (set(colors + roles + verbs + objects) & old_words)
modals = {'O': ('shall', 'must'), 'P': ('may', 'is permitted to'), 'F': ('shall not', 'must not')}
fresh = {}
source_sets = {}
for split, offset in [('selection', 0), ('final', 8)]:
    rows = []
    actors = [colors[offset + i].title() + ' ' + roles[offset + i].title() for i in range(8)]
    actions = [v + ' the ' + o for v, o in zip(verbs[offset:offset + 8], objects[offset:offset + 8])]
    for index in range(38):
        mixed = index >= 26
        count = 2 + index % 7
        source, members = '', []
        previous_actor = previous_actor_span = None
        common_modality = ('O', 'P', 'F')[(index // 7) % 3]
        for slot in range(count):
            if slot:
                source += ' or '
            explicit = slot == 0 or (mixed and slot % 2 == 1) or (not mixed and index % 3 == 1 and slot % 2 == 1)
            if explicit:
                actor = actors[(index * 3 + (slot if mixed else 0)) % 8]
                source += 'The ' if slot == 0 else 'the '
                actor_span = [len(source), len(source) + len(actor)]
                source += actor + ' '
                previous_actor, previous_actor_span = actor, actor_span
            else:
                actor, actor_span = previous_actor, previous_actor_span.copy()
            modality = ('O', 'P', 'F')[(index + slot) % 3] if mixed and index % 2 else common_modality
            modal = modals[modality][(index + slot + (split == 'final')) % 2]
            modal_span = [len(source), len(source) + len(modal)]
            source += modal + ' '
            action = actions[(index * 3 + slot * 5 + index // 8) % 8]
            action_span = [len(source), len(source) + len(action)]
            source += action
            members.append({'actor': actor, 'actor_span': actor_span.copy(), 'action': action,
                            'action_span': action_span, 'modality': modality, 'modal_text': modal, 'modal_span': modal_span})
        source += '.'
        group = 'fresh-boundary-' + digest(source.encode())
        assert source not in old_sources
        scopes = ['disjunction_of_norms'] if mixed else ['modal_over_actions', 'disjunction_of_norms']
        for scope_index, scope in enumerate(scopes):
            request = {'schema': 'legal-coordination-decode-request/v1', 'modal_scope': scope,
                'connective': 'inclusive_or', 'binding_profile': 'universal_actor_predicate',
                'members': [{'actor': m['actor'].casefold(), 'action': m['action'], 'modality': m['modality']} for m in members]}
            positive = {'case_id': group + '-' + scope, 'source_group_id': group,
                'parent_source_group_id': group, 'split': split, 'input': {'source_text': source, 'modal_scope': scope},
                'supported': True, 'target_spans': [{k: m[k] for k in ('actor_span', 'action_span', 'modality')} for m in members],
                'target_request': request, 'negative_category': None, 'source_semantics_reviewed': False}
            rows.append(positive)
            position_label = ('first', 'middle', 'last')[(index + scope_index) % 3]
            position = {'first': 0, 'middle': count // 2, 'last': count - 1}[position_label]
            member = members[position]
            kind = 'missing_modal_local' if (index + scope_index) % 2 == 0 else 'misspelled_modal_local'
            word = 'permitted' if member['modal_text'] == 'is permitted to' else member['modal_text'].split()[0]
            changed = edit_modal(source, member['modal_span'], kind, corruptions[split][word])
            negative_id = 'fresh-boundary-negative-' + digest((changed + '\0' + scope).encode())
            rows.append({'case_id': negative_id, 'source_group_id': negative_id, 'parent_source_group_id': group,
                'split': split, 'input': {'source_text': changed, 'modal_scope': scope}, 'supported': False,
                'target_spans': [], 'target_request': None, 'negative_category': kind,
                'position_label': position_label, 'edited_member_index': position, 'source_semantics_reviewed': False})
    assert len(rows) == 128 and sum(r['supported'] for r in rows) == 64
    assert len({r['case_id'] for r in rows}) == 128
    source_sets[split] = {r['input']['source_text'] for r in rows}
    assert source_sets[split].isdisjoint(old_sources)
    fresh[split] = rows
assert source_sets['selection'].isdisjoint(source_sets['final'])
training_sources = {r['input']['source_text'] for r in train + local_negatives}
assert all(values.isdisjoint(training_sources) for values in source_sets.values())
train_ref = write('training-corpus.json', {'original_rows': train, 'targeted_negatives': local_negatives,
    'original_corpus_sha256': digest(OLD.read_bytes()), 'targeted_position_counts': dict(Counter(r['position_label'] for r in local_negatives))})
selection_ref = write('selection-reference.json', {'rows': fresh['selection'], 'legal_gold': False})
final_ref = write('final-reference.json', {'rows': fresh['final'], 'legal_gold': False})
write('final-inputs.json', {'rows': [{'case_id': r['case_id'], 'input': r['input']} for r in fresh['final']]})
write('experiment-plan.json', {'schema': 'grouped-boundary-matched-continuation-plan/v1',
    'parent_checkpoint': {'path': str(PARENT), 'sha256': digest(PARENT.read_bytes()), 'steps': 480},
    'training_corpus': train_ref, 'selection_reference': selection_ref, 'sealed_final_reference': final_ref,
    'arms': ['original_negatives', 'position_local_negatives'], 'updates_per_arm': 200,
    'batch_size': 16, 'positive_per_batch': 8, 'negative_per_batch': 8,
    'targeted_arm_original_negatives_per_batch': 4, 'targeted_arm_local_negatives_per_batch': 4,
    'learning_rate': 0.0005, 'batch_order_seed': 24601, 'support_threshold': 0.5,
    'selection_updates': [0, 100, 200],
    'selection_score': ['mixed_exact_count', '-negative_emitted_request_count', 'positive_exact_count', '-additional_updates'],
    'source_sets_disjoint_from_parent_corpus_and_between_new_splits': True,
    'new_source_parent_groups_per_evaluation_split': 38,
    'evaluation_positive_rows_per_split': 64, 'evaluation_negative_rows_per_split': 64,
    'negative_meaning': 'outside narrow repeated-modal coordination profile; not legally false',
    'legal_gold': False, 'source_semantics_reviewed': False, 'latent_conditioned': False,
    'fresh_references_fixed_before_training': True, 'corruptions': corruptions,
    'runner_sha256': digest(Path(__file__).read_bytes())})
print(json.dumps({'status': 'fixed_before_training', 'train_original_rows': len(train),
    'targeted_negatives': len(local_negatives), 'new_selection_rows': 128, 'new_final_rows': 128}))
