"""Clone the stopped diagnostic generation, then exercise a bounded exact resume."""
import argparse
import json
from pathlib import Path
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--arguments-file', type=Path, required=True)
    parser.add_argument('--stopped-generation', type=Path, required=True)
    args = parser.parse_args()
    options = json.loads(args.arguments_file.read_bytes())
    destination = Path(options['output_directory'])
    destination.mkdir(exist_ok=False)
    if (args.stopped_generation / 'census.duckdb.wal').exists():
        raise ValueError('stopped generation still has an unreconciled WAL')
    for name in ['manifest.json', 'census.duckdb']:
        source = args.stopped_generation / name
        if source.is_symlink() or not source.is_file():
            raise ValueError('stopped generation inputs must be regular files')
        shutil.copyfile(source, destination / name)
    sys.path.insert(0, str(args.source_root.resolve()))
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.uscode_source_census import run_source_census
    report = run_source_census(**options)
    print(json.dumps(dict(event='bounded_stopped_generation_resume',
                         complete_source_scan=report['complete_source_scan'],
                         statistics=report['statistics'])), flush=True)


if __name__ == '__main__':
    main()
