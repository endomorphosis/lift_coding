"""Fetch only the immutable, bounded original queue needed for source census."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

REPOSITORY = 'justicedao/uscode-autoformal-span-cache'
REVISION = '765176c6db79ba65c1697c21dead43666350b730'
QUEUE_PATH = 'autoformal/uscode/resume-checkpoint.parquet'
QUEUE_BYTES = 52_701_179
QUEUE_SHA = '7707c001d650876717651a38e442d1522c5bdab6c792539414973922af1c1d03'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    destination = args.output / 'resume-checkpoint.parquet'
    url = f'https://huggingface.co/datasets/{REPOSITORY}/resolve/{REVISION}/{QUEUE_PATH}'
    started = time.monotonic()
    digest = hashlib.sha256()
    received = 0
    with urllib.request.urlopen(url, timeout=30) as response, destination.open('xb') as stream:
        declared = response.headers.get('Content-Length')
        if declared is not None and int(declared) != QUEUE_BYTES:
            raise ValueError('immutable queue Content-Length differs')
        while chunk := response.read(1024 * 1024):
            received += len(chunk)
            if received > QUEUE_BYTES or time.monotonic() - started > 180:
                raise ValueError('immutable queue exceeded byte or elapsed-time bound')
            digest.update(chunk)
            stream.write(chunk)
        stream.flush()
        os.fsync(stream.fileno())
    if received != QUEUE_BYTES or digest.hexdigest() != QUEUE_SHA:
        raise ValueError('immutable queue byte identity differs')
    record = dict(schema='uscode-source-census-input-download/v1', repository_id=REPOSITORY,
                  revision=REVISION, path_in_repo=QUEUE_PATH, path=str(destination.resolve()),
                  bytes=received, sha256=digest.hexdigest(), verified=True,
                  elapsed_seconds=round(time.monotonic() - started, 3),
                  models_executed=False, training_executed=False, proof_authority=False)
    with (args.output / 'input-receipt.json').open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
