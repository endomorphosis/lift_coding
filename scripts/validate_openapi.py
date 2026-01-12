from __future__ import annotations

import sys
from pathlib import Path

import yaml
from openapi_spec_validator import validate_spec


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_openapi.py <path-to-openapi.yaml>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate_spec(data)
    print(f"ok: OpenAPI spec is valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
