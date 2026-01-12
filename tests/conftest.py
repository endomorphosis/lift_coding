"""pytest configuration for HandsFree tests."""

import sys
from pathlib import Path

# Add src directory to path so tests can import handsfree
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))
https://github.com/endomorphosis/lift_coding/pull/7/conflict?name=tests%252Ftest_api_contract.py&base_oid=b603712130ac9524db64e9129c436438fc4cf319&head_oid=21bb8df094a5bc78647c35e1e2fb61ed0e32113b