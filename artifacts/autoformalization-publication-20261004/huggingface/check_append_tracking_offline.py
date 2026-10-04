"""Check scoped tracking additions without network, model or repository writes."""

import hashlib
import json
from pathlib import Path


def main():
    directory = Path(__file__).resolve().parent
    source = directory / 'publish_append_release_v2.py'
    data = source.read_bytes()
    namespace = {'__file__': str(source), '__name__': '_offline_selected_tracking'}
    exec(compile(data, str(source), 'exec'), namespace)
    validate = namespace['validate_tracking_delta']
    before = b'*.bin filter=lfs diff=lfs merge=lfs -text\n'
    rule = 'releases/fixture/selected.json filter=lfs diff=lfs merge=lfs -text'
    line = (rule + '\n').encode()
    assert validate(before, before + line, {rule}) == [rule]
    checks = ['exact_old_bytes_plus_selected_LFS_rule']
    for name, after, allowed in (
        ('changed_existing_bytes', b'*.py filter=lfs\n' + line, {rule}),
        ('unselected_new_path', before + b'other.json filter=lfs diff=lfs merge=lfs -text\n', {rule}),
        ('broad_glob_rule', before + b'*.json filter=lfs diff=lfs merge=lfs -text\n', {rule}),
        ('duplicate_rule', before + line + line, {rule}),
        ('incomplete_trailing_line', before + line[:-1], {rule}),
        ('non_LFS_selected_rule', before + line, set()),
    ):
        try:
            validate(before, after, allowed)
        except ValueError:
            checks.append(name + '_rejected')
        else:
            raise AssertionError('unselected tracking delta accepted')
    assert source.read_bytes() == data
    result = {'schema': 'HF-selected-tracking-delta-offline-check/v1', 'checks': checks,
        'status': 'passed', 'publisher_source': {'path': str(source), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()},
        'network_calls': 0, 'model_calls': 0, 'training_executed': False, 'repository_mutations': 0}
    print(json.dumps({'fixture': namespace['save'](directory / 'append_tracking_fixture_v2.json', result), 'checks': len(checks)}))


if __name__ == '__main__':
    main()
