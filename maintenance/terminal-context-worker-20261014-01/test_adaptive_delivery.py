"""Exact offline full-message selection; authored data, no worker/provider runs."""
from copy import deepcopy
import json

import pytest

import adaptive_delivery as subject


@pytest.fixture(scope='module')
def tokenizer():
    from token_cost_review import load_tokenizer
    return load_tokenizer()


@pytest.fixture(scope='module')
def codec_cases():
    from reference_codec import _envelope, canonical_packet_bytes, decode_reference_packet
    repeated = 'baguqeerabf5d6ac7e8f90213456789abcdef0123456789abcdef0123456789abcdef'
    large = {'schema': 'authored-delivery-data@1', 'bindings': [repeated] * 48,
             'opaque_source': "  This is authored non-executable source-looking text. λ🙂\n\t  "}
    tiny = {'authored': 'small'}
    def case(value, table):
        original = canonical_packet_bytes(value).decode('utf-8')
        packed = _envelope(value, original.encode('utf-8'), table)
        def restore(text):
            return canonical_packet_bytes(decode_reference_packet(text)).decode('utf-8')
        return {'original_rendered': original, 'packed_wire': packed, 'restore': restore}
    return {'cheaper': case(large, [repeated]), 'larger': case(tiny, [])}


def messages(original):
    return [{'message_id': 'system', 'role': 'system', 'content': '  Preserve all source and instruction bytes.\n'},
            {'message_id': 'past', 'role': 'assistant', 'content': '\tPrior authored history λ🙂 <|endoftext|>\n  '},
            {'message_id': 'context', 'role': 'user', 'content': original},
            {'message_id': 'followup', 'role': 'user', 'content': 'Continue with every unresolved requirement.\t '}]


def select(case, *, supplied_messages=None, **kwargs):
    options = dict(case, messages=messages(case['original_rendered']) if supplied_messages is None else supplied_messages,
                   context_message_id='context', max_input_tokens=100_000,
                   history_required_ids=('system', 'past'))
    options.update(kwargs)
    return subject.select_delivery(**options)


def test_real_reference_codec_selection_counts_complete_roles_history_and_framing(codec_cases, tokenizer):
    from token_cost_review import serialize_messages
    encoder, descriptor = tokenizer
    case = codec_cases['cheaper']
    supplied = messages(case['original_rendered']); before = deepcopy(supplied)
    report = select(case, supplied_messages=supplied, tokenizer_descriptor=descriptor)
    assert report['selected_form'] == 'packed'
    assert report['packed_strictly_cheaper_complete_input'] is True
    assert report['adaptive_local_nonregression_checked'] is True
    assert supplied == before
    for index, item in enumerate(report['selected_messages']):
        if item['message_id'] == 'context':
            assert item == {**before[index], 'content': case['packed_wire']}
        else:
            assert item == before[index]
    expected = serialize_messages(report['selected_messages'])['payload']
    assert report['serialized_payload'] == expected
    assert report['input_tokens'] == len(encoder.encode(expected))
    assert report['payload_sha256'] == subject._sha(expected.encode('utf-8'))
    assert report['payload_bytes'] == len(expected.encode('utf-8'))
    assert report['expanded_full_message_cost']['input_tokens'] == len(encoder.encode(serialize_messages(before)['payload']))
    assert report['input_tokens'] > len(encoder.encode(case['packed_wire']))
    assert report['packed_restores_complete_original'] is True
    assert report['required_history_ids_present'] is True
    assert report['every_other_message_bytes_roles_ids_unchanged'] is True
    assert report['message_ids_are_local_manifest_only'] is True
    assert all(report[key] is False for key in subject.CLAIMS)
    assert report['provider_usage'] is None and report['provider_invocations'] == 0
    # No selection trace, costs or authority receipt is inserted in model text.
    assert report['selected_messages'][2]['content'] == case['packed_wire']


def test_adaptive_falls_back_when_complete_packed_envelope_costs_more(codec_cases):
    case = codec_cases['larger']
    report = select(case)
    assert report['selected_form'] == 'expanded'
    assert report['packed_full_message_cost']['input_tokens'] > report['expanded_full_message_cost']['input_tokens']
    assert report['selected_messages'] == messages(case['original_rendered'])
    assert report['signed_local_input_token_difference'] == 0
    assert report['selected_local_tokens_not_greater_than_expanded'] is True


def test_equal_full_input_cost_keeps_exact_expanded_context():
    original = '{"authored":"identical literal control"}'
    case = {'original_rendered': original, 'packed_wire': original, 'restore': lambda text: text}
    report = select(case)
    assert report['selected_form'] == 'expanded'
    assert report['packed_full_message_cost']['input_tokens'] == report['expanded_full_message_cost']['input_tokens']
    assert report['packed_strictly_cheaper_complete_input'] is False


def test_only_cheaper_candidate_can_fit_and_budget_is_final_whole_input(codec_cases):
    case = codec_cases['cheaper']
    measured = select(case)
    budget = measured['packed_full_message_cost']['input_tokens']
    assert budget < measured['expanded_full_message_cost']['input_tokens']
    report = select(case, max_input_tokens=budget)
    assert report['selected_form'] == 'packed'
    assert report['input_tokens'] == budget
    assert report['final_complete_input_within_budget'] is True
    assert report['expanded_full_message_cost']['within_input_token_budget'] is False
    with pytest.raises(subject.DeliveryBudgetError, match='final complete serialized'):
        select(case, max_input_tokens=budget-1)
    # Counting just the context would incorrectly admit this whole conversation.
    from token_cost_review import load_tokenizer
    encoder, _ = load_tokenizer()
    with pytest.raises(subject.DeliveryBudgetError):
        select(case, max_input_tokens=len(encoder.encode(case['packed_wire'])))


def test_forced_forms_keep_explicit_budget_without_adaptive_guarantee(codec_cases):
    larger = codec_cases['larger']
    forced = select(larger, delivery_mode='packed')
    assert forced['selected_form'] == 'packed'
    assert forced['adaptive_local_nonregression_checked'] is False
    assert forced['selected_local_tokens_not_greater_than_expanded'] is False
    assert forced['signed_local_input_token_difference'] < 0
    raw = select(larger, delivery_mode='expanded')
    assert raw['selected_form'] == 'expanded'
    assert raw['adaptive_local_nonregression_checked'] is False
    with pytest.raises(subject.DeliveryBudgetError):
        select(larger, delivery_mode='packed', max_input_tokens=raw['input_tokens'])
    cheaper = codec_cases['cheaper']
    packed = select(cheaper)
    with pytest.raises(subject.DeliveryBudgetError):
        select(cheaper, delivery_mode='expanded', max_input_tokens=packed['input_tokens'])


def test_explicit_routing_guidance_is_in_packed_message_and_can_reverse_decision(codec_cases):
    from token_cost_review import load_tokenizer, serialize_messages
    case = codec_cases['cheaper']
    guidance = 'Explicit authored routing instructions charged in this message. ' * 500
    report = select(case, routing_guidance=guidance)
    assert report['selected_form'] == 'expanded'
    packed_messages = messages(case['original_rendered'])
    packed_messages[2]['content'] = guidance + '\n' + case['packed_wire']
    expected = serialize_messages(packed_messages)['payload']
    encoder, _ = load_tokenizer()
    assert report['packed_full_message_cost']['serialized_payload'] == expected
    assert report['packed_full_message_cost']['input_tokens'] == len(encoder.encode(expected))
    assert report['routing_guidance'] == {'text': guidance, 'separator': '\n', 'bytes': len(guidance.encode()),
        'included_in_packed_message': True, 'charged_in_complete_packed_input': True}


def test_context_history_substitution_is_explicit_and_does_not_attest_session_state(codec_cases):
    report = select(codec_cases['cheaper'], history_required_ids=('system', 'past', 'context'))
    assert report['designated_context_is_required_history'] is True
    assert report['context_substitution_authorized_by_caller_only'] is True
    assert report['required_noncontext_history_bytes_unchanged'] is True
    assert report['prior_delivery_state_checked'] is False
    assert report['live_session_history_immutability_verified'] is False


@pytest.mark.parametrize('mode', ['adaptive', 'expanded', 'packed'])
@pytest.mark.parametrize('damage', ['wrong_bytes', 'bytes_result', 'raises', 'mutates_other', 'duplicates_id'])
def test_actual_restore_is_checked_before_every_form_choice(codec_cases, mode, damage):
    case = dict(codec_cases['larger'])
    supplied = messages(case['original_rendered'])
    if damage == 'wrong_bytes': case['restore'] = lambda _text: case['original_rendered'] + ' '
    elif damage == 'bytes_result': case['restore'] = lambda _text: case['original_rendered'].encode()
    elif damage == 'raises':
        def refusal(_text): raise ValueError('authored decoder refusal')
        case['restore'] = refusal
    else:
        def mutation(_text):
            if damage == 'mutates_other': supplied[0]['content'] += ' changed'
            else: supplied[1]['message_id'] = supplied[0]['message_id']
            return case['original_rendered']
        case['restore'] = mutation
    with pytest.raises(subject.AdaptiveDeliveryError):
        select(case, supplied_messages=supplied, delivery_mode=mode)


@pytest.mark.parametrize('damage', ['no_messages', 'too_many_messages', 'missing_id', 'extra_field', 'duplicate_id',
    'wrong_context_content', 'missing_context', 'bad_role', 'float_content', 'cycle_content', 'tuple_messages',
    'list_history', 'missing_history', 'duplicate_history', 'nontext_history', 'too_many_history',
    'float_budget', 'bool_budget', 'zero_budget', 'negative_budget', 'bad_mode', 'surrogate_text',
    'oversize_guidance', 'no_restore'])
def test_exact_message_scope_and_budget_types_refuse_before_decoder(codec_cases, damage):
    case = dict(codec_cases['larger'])
    supplied = messages(case['original_rendered'])
    kwargs = {}
    called = False
    def never(_text):
        nonlocal called
        called = True
        pytest.fail('invalid message scope must refuse before codec callback')
    case['restore'] = never
    if damage == 'no_messages': supplied = []
    elif damage == 'too_many_messages': supplied += [{'message_id': str(i), 'role': 'user', 'content': 'x'} for i in range(29)]
    elif damage == 'missing_id': supplied[0].pop('message_id')
    elif damage == 'extra_field': supplied[0]['provider_usage'] = 1.0
    elif damage == 'duplicate_id': supplied[1]['message_id'] = supplied[0]['message_id']
    elif damage == 'wrong_context_content': supplied[2]['content'] += ' changed'
    elif damage == 'missing_context': kwargs['context_message_id'] = 'unseen'
    elif damage == 'bad_role': supplied[0]['role'] = 'administrator'
    elif damage == 'float_content': supplied[0]['content'] = 1.0
    elif damage == 'cycle_content': supplied[0]['content'] = supplied
    elif damage == 'tuple_messages': supplied = tuple(supplied)
    elif damage == 'list_history': kwargs['history_required_ids'] = ['system']
    elif damage == 'missing_history': kwargs['history_required_ids'] = ('missing',)
    elif damage == 'duplicate_history': kwargs['history_required_ids'] = ('past', 'past')
    elif damage == 'nontext_history': kwargs['history_required_ids'] = ([],)
    elif damage == 'too_many_history': kwargs['history_required_ids'] = tuple(str(i) for i in range(33))
    elif damage == 'float_budget': kwargs['max_input_tokens'] = 1000.0
    elif damage == 'bool_budget': kwargs['max_input_tokens'] = True
    elif damage == 'zero_budget': kwargs['max_input_tokens'] = 0
    elif damage == 'negative_budget': kwargs['max_input_tokens'] = -1
    elif damage == 'bad_mode': kwargs['delivery_mode'] = 'truncate-history'
    elif damage == 'surrogate_text': supplied[0]['content'] = '\ud800'
    elif damage == 'oversize_guidance': kwargs['routing_guidance'] = 'x' * (subject.MAX_GUIDANCE_BYTES + 1)
    elif damage == 'no_restore': case['restore'] = None
    with pytest.raises(subject.AdaptiveDeliveryError):
        select(case, supplied_messages=supplied, **kwargs)
    assert called is False


def test_complete_serialized_byte_cap_includes_json_escape_and_framing():
    original = '\x00' * 90_000
    case = {'original_rendered': original, 'packed_wire': original, 'restore': lambda text: text}
    with pytest.raises(subject.AdaptiveDeliveryError, match='measurement refused'):
        select(case, supplied_messages=[{'message_id': 'context', 'role': 'user', 'content': original}],
               history_required_ids=())


def test_exact_32_message_bound_retains_all_other_history(codec_cases):
    case = codec_cases['cheaper']
    supplied = messages(case['original_rendered'])
    supplied += [{'message_id': 'history-' + str(i), 'role': 'tool', 'content': '  Authored history ' + str(i) + '\n'}
                 for i in range(28)]
    report = select(case, supplied_messages=supplied, history_required_ids=tuple(row['message_id'] for row in supplied))
    assert len(report['selected_messages']) == 32
    assert [row['message_id'] for row in report['selected_messages']] == [row['message_id'] for row in supplied]
    assert all(a == b for a, b in zip(report['selected_messages'], supplied) if a['message_id'] != 'context')


def test_tokenizer_descriptor_and_ledger_source_substitution_refuse(codec_cases, tokenizer, monkeypatch):
    _, descriptor = tokenizer
    tampered = deepcopy(descriptor); tampered['provider_tokenizer_equivalence_established'] = True
    with pytest.raises(ValueError, match='descriptor'):
        select(codec_cases['larger'], tokenizer_descriptor=tampered)
    monkeypatch.setattr(subject, 'LEDGER_SHA256', '0' * 64)
    with pytest.raises(subject.AdaptiveDeliveryError, match='ledger source changed'):
        select(codec_cases['larger'])
