import pytest
from selection_policy import eligible, rank, select


def summary(**changes):
    values = dict(positive_count=64, negative_count=64, positive_exact_count=3,
        positive_emitted_proposal_count=20, positive_learned_refusal_count=20,
        negative_learned_refusal_count=60, negative_emitted_proposal_count=4)
    values.update(changes)
    return values


def candidate(steps, value):
    return dict(completed_updates=steps, summary=value)


def test_reject_all_larger_utility_does_not_displace_usable_baseline():
    base = summary()
    reject = summary(positive_exact_count=0, positive_emitted_proposal_count=0,
        positive_learned_refusal_count=64, negative_learned_refusal_count=64,
        negative_emitted_proposal_count=0)
    assert rank(reject, 120) > rank(base, 0)
    assert not eligible(reject, base)
    assert select([candidate(0, base), candidate(120, reject)], base)['completed_updates'] == 0


def test_coverage_and_exactness_floors_each_reject_apparent_gain():
    base = summary()
    for bad in (summary(positive_emitted_proposal_count=19, negative_learned_refusal_count=64, negative_emitted_proposal_count=0),
                summary(positive_learned_refusal_count=21, negative_learned_refusal_count=64, negative_emitted_proposal_count=0),
                summary(positive_exact_count=2, negative_learned_refusal_count=64, negative_emitted_proposal_count=0)):
        assert rank(bad, 120) > rank(base, 0)
        assert not eligible(bad, base)


def test_genuine_eligible_gain_and_earlier_tie_are_selected():
    base = summary()
    gain = summary(positive_exact_count=5, positive_emitted_proposal_count=22,
        positive_learned_refusal_count=18, negative_learned_refusal_count=62,
        negative_emitted_proposal_count=2)
    chosen = select([candidate(0, base), candidate(120, gain), candidate(240, gain)], base)
    assert chosen['completed_updates'] == 120


@pytest.mark.parametrize('change', [dict(positive_count=True), dict(positive_exact_count=21),
    dict(negative_emitted_proposal_count=5), dict(positive_learned_refusal_count=45)])
def test_invalid_counts_fail_closed(change):
    with pytest.raises(ValueError):
        eligible(summary(**change), summary())


def test_missing_positive_baseline_and_changed_denominators_fail_closed():
    with pytest.raises(ValueError):
        eligible(summary(), summary(positive_exact_count=0, positive_emitted_proposal_count=0))
    with pytest.raises(ValueError):
        eligible(summary(positive_count=63), summary())
