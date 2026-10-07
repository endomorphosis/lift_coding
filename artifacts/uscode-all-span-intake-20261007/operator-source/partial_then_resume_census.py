"""Commit a partial census, then exec a fresh CLI process at a different batch size."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--arguments-file', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source_root.resolve()))
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.uscode_source_census import run_source_census
    options = json.loads(args.arguments_file.read_bytes())
    partial = run_source_census(**options, max_batches=4, section_batch_size=4)
    output = Path(options['output_directory'])
    with (output / 'partial-report.json').open('x') as stream:
        json.dump(partial, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    if partial['complete_source_scan'] or partial['statistics']['next_section'] != 16:
        raise ValueError('actual partial census did not commit the expected first sixteen sections')
    command = [sys.executable, str(args.source_root / 'scripts/ops/legal_ir/census_uscode_sources.py')]
    for key, value in options.items():
        if value is None or value is False:
            continue
        command.append('--' + key.replace('_', '-'))
        if value is not True:
            command.append(str(value))
    command.extend(['--section-batch-size', '16'])
    print(json.dumps(dict(event='exec_fresh_cli_resume', next_section=16,
                         original_batch_size=4, resume_batch_size=16)), flush=True)
    # Exec retains the owned PID, birth and process-group identity while
    # rebuilding all Python/module/DuckDB state in a fresh process image.
    os.execv(sys.executable, command)


if __name__ == '__main__':
    main()
