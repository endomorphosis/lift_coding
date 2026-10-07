"""Predeclared count floors for the fresh support-gate selection panel.

These constraints protect aggregate selection counts, not individual cases or
exposed retention cohorts. Paired whole losses/gains and negative emission
changes must be reported separately. The actual measured step-zero checkpoint
is always the fallback; prior/final references never enter this helper.
"""


def _validate(summary):
    if type(summary) is not dict:
        raise ValueError('ordinary selection summary required')
    keys = ('positive_count', 'negative_count', 'positive_exact_count',
            'positive_emitted_proposal_count', 'positive_learned_refusal_count',
            'negative_learned_refusal_count', 'negative_emitted_proposal_count')
    if any(type(summary.get(key)) is not int or summary[key] < 0 for key in keys):
        raise ValueError('nonnegative ordinary integer selection counts required')
    if summary['positive_count'] < 1 or summary['negative_count'] < 1:
        raise ValueError('selection requires both positive and negative records')
    if not (summary['positive_exact_count'] <= summary['positive_emitted_proposal_count']
            <= summary['positive_count']
            and summary['positive_emitted_proposal_count'] + summary['positive_learned_refusal_count']
            <= summary['positive_count']
            and summary['negative_learned_refusal_count'] + summary['negative_emitted_proposal_count']
            <= summary['negative_count']):
        raise ValueError('selection count bounds differ')
    for field, count, emitted, refused in (
        ('positive_structural_block_count', 'positive_count',
         'positive_emitted_proposal_count', 'positive_learned_refusal_count'),
        ('negative_incidental_block_count', 'negative_count',
         'negative_emitted_proposal_count', 'negative_learned_refusal_count'),
    ):
        if field in summary:
            if (type(summary[field]) is not int or summary[field] < 0
                    or summary[emitted] + summary[refused] + summary[field] != summary[count]):
                raise ValueError('selection status partition differs')
    if 'case_count' in summary and (type(summary['case_count']) is not int
            or summary['case_count'] != summary['positive_count'] + summary['negative_count']):
        raise ValueError('selection total count differs')


def _steps(steps):
    if type(steps) is not int or not 0 <= steps <= 10_000_000:
        raise ValueError('bounded ordinary integer update count required')


def eligible(summary, baseline):
    _validate(summary)
    _validate(baseline)
    if (baseline['positive_emitted_proposal_count'] < 1
            or baseline['positive_exact_count'] < 1):
        raise ValueError('nonzero baseline positive emission and whole exactness required before fitting')
    if (summary['positive_count'], summary['negative_count']) != (
            baseline['positive_count'], baseline['negative_count']):
        raise ValueError('selection cohort denominators differ')
    return (summary['negative_emitted_proposal_count'] <= baseline['negative_emitted_proposal_count']
            and summary['positive_exact_count'] >= baseline['positive_exact_count']
            and summary['positive_emitted_proposal_count'] >= baseline['positive_emitted_proposal_count']
            and summary['positive_learned_refusal_count'] <= baseline['positive_learned_refusal_count'])


def rank(summary, steps):
    _validate(summary)
    _steps(steps)
    return (-summary['negative_emitted_proposal_count'], summary['positive_exact_count'],
            summary['negative_learned_refusal_count'], -steps)


def select(candidates, baseline):
    if type(candidates) is not list or not candidates:
        raise ValueError('measured step-zero fallback must be first')
    previous = -1
    for row in candidates:
        if type(row) is not dict or 'completed_updates' not in row or 'summary' not in row:
            raise ValueError('ordinary candidate update and summary required')
        _steps(row['completed_updates'])
        if row['completed_updates'] <= previous:
            raise ValueError('candidate updates must be distinct and increasing')
        previous = row['completed_updates']
    if candidates[0]['completed_updates'] != 0:
        raise ValueError('measured step-zero fallback must be first')
    if candidates[0]['summary'] != baseline:
        raise ValueError('step-zero fallback must equal the measured baseline summary')
    allowed = [row for row in candidates if eligible(row['summary'], baseline)]
    return max(allowed, key=lambda row: rank(row['summary'], row['completed_updates']))
