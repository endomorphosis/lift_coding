"""Copied-policy custody tests never open actual shared scheduler state."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import scheduler_overlay as subject


def _authored_pin(tmp_path):
    body = b"# Authored module data; never executes\n"
    source, retained = tmp_path / "public.py", tmp_path / "retained.py"
    source.write_bytes(body)
    retained.write_bytes(body)
    return {"public_source": str(source), "retained_source": str(retained),
            "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}, body


def _child(script):
    return subprocess.run([sys.executable, "-B", "-c", script],
        cwd=subject.ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=30)


def test_retained_and_public_source_replay_exact(tmp_path):
    pin, body = _authored_pin(tmp_path)
    assert subject._verify_source(pin) == body


@pytest.mark.parametrize("member", ["public_source", "retained_source"])
def test_source_drift_refuses_refresh(tmp_path, member):
    pin, body = _authored_pin(tmp_path)
    Path(pin[member]).write_bytes(body + b"# changed\n")
    with pytest.raises(subject.PolicyOverlayError, match="drift"):
        subject._verify_source(pin)
    assert Path(pin["retained_source"]).read_bytes() == (body + b"# changed\n" if member == "retained_source" else body)


def test_wrong_hash_or_byte_count_refuses(tmp_path):
    pin, _ = _authored_pin(tmp_path)
    for changed in (dict(pin, sha256="0" * 64), dict(pin, bytes=pin["bytes"] + 1)):
        with pytest.raises(subject.PolicyOverlayError, match="drift"):
            subject._verify_source(changed)


def test_symlink_and_hardlink_source_refuse(tmp_path):
    pin, body = _authored_pin(tmp_path)
    symbolic = tmp_path / "symbolic.py"
    symbolic.symlink_to(pin["public_source"])
    with pytest.raises(subject.PolicyOverlayError, match="canonical"):
        subject._verify_source(dict(pin, public_source=str(symbolic)))
    linked = tmp_path / "linked.py"
    os.link(pin["public_source"], linked)
    with pytest.raises(subject.PolicyOverlayError, match="single-link"):
        subject._verify_source(pin)


def test_oversized_policy_source_refuses_before_read(tmp_path):
    path = tmp_path / "large.py"
    path.write_bytes(b"#" * (512 * 1024 + 1))
    with pytest.raises(subject.PolicyOverlayError, match="bounded"):
        subject._read(path)


@pytest.mark.parametrize("modules", [[], [{"module": subject.ORDER[1]}, {"module": subject.ORDER[0]}],
    [{"module": subject.ORDER[0]}, {"module": subject.ORDER[0]}],
    [{"module": subject.ORDER[0]}, {"module": subject.ORDER[1]}, {"module": "extra"}]])
def test_missing_wrong_order_duplicate_or_extra_policy_modules_refuse(modules):
    with pytest.raises(subject.PolicyOverlayError, match="collector"):
        subject._validate_order(modules)


def test_fresh_isolated_runtime_uses_copied_matching_real_collector():
    result = _child("""
import inspect,json
from pathlib import Path
from scheduler_overlay import load_overlay
loaded=load_overlay()
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceSchedulerConfig,GlobalResourceScheduler
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.proof_resource_safety import collect_proof_host_resources
config=ResourceSchedulerConfig.for_proof_host()
host=collect_proof_host_resources()
assert config.proof_resource_sampler is collect_proof_host_resources
assert config.proof_safety_enabled is True and config.proof_recovery_enabled is False
assert config.proof_resource_profile is None
assert host.cpu_slots > 0 and host.total_memory_mb > 0
assert Path(inspect.getfile(GlobalResourceScheduler)).parent.name == 'native-policy-overlay-01'
assert Path(inspect.getfile(collect_proof_host_resources)).parent.name == 'native-policy-overlay-01'
print(json.dumps({'copied':True,'native_real_collector':True,'state_opened':loaded['shared_scheduler_state_opened']}))
""")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"copied": True, "native_real_collector": True, "state_opened": False}


@pytest.mark.parametrize("prior", [
    "import ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler",
    "import ipfs_datasets_py.optimizers.logic_theorem_optimizer.proof_resource_safety",
    "import importlib; p=importlib.import_module('ipfs_datasets_py.optimizers.logic_theorem_optimizer'); p.resource_scheduler=object()",
    "import importlib; p=importlib.import_module('ipfs_datasets_py.optimizers.logic_theorem_optimizer'); p.proof_resource_safety=object()",
])
def test_cached_original_module_or_package_attribute_refuses(prior):
    result = _child(prior + "\nfrom scheduler_overlay import load_overlay,PolicyOverlayError\n"
        "try:\n load_overlay()\nexcept PolicyOverlayError:\n print('refused')\nelse:\n raise AssertionError('mixed import identity accepted')\n")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "refused"


def test_already_loaded_overlay_cannot_be_replaced():
    result = _child("from scheduler_overlay import load_overlay,PolicyOverlayError\nload_overlay()\n"
        "try:\n load_overlay()\nexcept PolicyOverlayError:\n print('refused')\nelse:\n raise AssertionError('reload accepted')\n")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "refused"
