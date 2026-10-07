"""Declared selection floors; exposed prior cohorts never enter this policy."""


def _validate(summary):
    keys = ('positive_count', 'negative_count', 'positive_exact_count',
            'positive_emitted_proposal_count', 'positive_learned_refusal_count',
            'negative_learned_refusal_count', 'negative_emitted_proposal_count')
    if any(type(summary.get(key)) is not int or summary[key] < 0 for key in keys):
        raise ValueError('nonnegative integer selection counts required')
    if not (summary['positive_exact_count'] <= summary['positive_emitted_proposal_count']
            <= summary['positive_count']
            and summary['positive_emitted_proposal_count'] + summary['positive_learned_refusal_count']
            <= summary['positive_count']
            and summary['negative_learned_refusal_count'] + summary['negative_emitted_proposal_count']
            <= summary['negative_count']):
        raise ValueError('selection count bounds differ')


def eligible(summary, baseline):
    _validate(summary)
    _validate(baseline)
    if baseline['positive_emitted_proposal_count'] < 1:
        raise ValueError('a nonzero baseline positive-emission floor is required before fitting')
    if (summary['positive_count'], summary['negative_count']) != (baseline['positive_count'], baseline['negative_count']):
        raise ValueError('selection cohort denominators differ')
    return (summary['positive_emitted_proposal_count'] >= baseline['positive_emitted_proposal_count']
            and summary['positive_learned_refusal_count'] <= baseline['positive_learned_refusal_count']
            and summary['positive_exact_count'] >= baseline['positive_exact_count'])


def rank(summary, steps):
    _validate(summary)
    if type(steps) is not int or steps < 0:
        raise ValueError('actual nonnegative update count required')
    return (summary['positive_exact_count'] + summary['negative_learned_refusal_count'],
            -summary['negative_emitted_proposal_count'], summary['positive_exact_count'], -steps)


def select(candidates, baseline):
    if not candidates or candidates[0]['completed_updates'] != 0:
        raise ValueError('the measured step-zero fallback must be first')
    if candidates[0]['summary'] != baseline:
        raise ValueError('step-zero fallback must equal the measured baseline summary')
    allowed = [row for row in candidates if eligible(row['summary'], baseline)]
    return max(allowed, key=lambda row: rank(row['summary'], row['completed_updates']))
