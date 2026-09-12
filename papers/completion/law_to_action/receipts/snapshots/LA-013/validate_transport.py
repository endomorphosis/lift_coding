#!/usr/bin/python3.12
"""Validate LA-013 transport parity outputs against sealed-environment facts."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("qualify_transport.py")
sys.argv = [str(SCRIPT), "validate"]
runpy.run_path(str(SCRIPT), run_name="__main__")
