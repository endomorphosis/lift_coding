"""pytest configuration for HandsFree tests."""

import sys
from pathlib import Path

# Add src directory to path so tests can import handsfree
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))
