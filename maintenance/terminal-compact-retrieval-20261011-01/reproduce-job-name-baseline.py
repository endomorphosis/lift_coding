import importlib.util
from pathlib import Path
import sys
import pytest
import benchmarks.agent_supervisor.container_coding as package
name='benchmarks.agent_supervisor.container_coding.full_supervisor_benchmark'
path=Path(__file__).parent/'baseline/benchmarks/agent_supervisor/container_coding/full_supervisor_benchmark.py'
spec=importlib.util.spec_from_file_location(name,path)
module=importlib.util.module_from_spec(spec)
sys.modules[name]=module
spec.loader.exec_module(module)
package.full_supervisor_benchmark=module
raise SystemExit(pytest.main(['test/api/test_terminal_intent_benchmark_config.py::test_old_config_calls_retain_default_arm_without_contract','-p','no:cacheprovider','-o','addopts=','-o','log_cli=false','--color=no','--tb=short','-q','--junitxml='+str(Path(__file__).with_name('job-name-baseline.xml'))]))
