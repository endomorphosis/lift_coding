#!/usr/bin/python3.12
"""Validate LA-012 durable consumption outputs against sealed-environment facts."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("durable_consumption.py")
sys.argv = [str(SCRIPT), "validate"]
runpy.run_path(str(SCRIPT), run_name="__main__")
