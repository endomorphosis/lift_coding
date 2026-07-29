from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"


def test_lift_bootstrap_prefers_checked_out_ipfs_accelerate(tmp_path, monkeypatch):
    shadow_root = tmp_path / "shadow"
    shadow_package = shadow_root / "ipfs_accelerate_py"
    shadow_package.mkdir(parents=True)
    (shadow_package / "__init__.py").write_text("SHADOW_PACKAGE = True\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(shadow_root))
    for module_name in list(sys.modules):
        if module_name == "ipfs_accelerate_py" or module_name.startswith("ipfs_accelerate_py."):
            monkeypatch.delitem(sys.modules, module_name, raising=False)
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))

    from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate

    bootstrap = bootstrap_ipfs_accelerate(
        SCRIPTS_DIR / "virtual_ai_os_todo_supervisor.py",
        include_script_dir=True,
    )
    module = importlib.import_module("ipfs_accelerate_py")

    assert bootstrap.package_root == IPFS_ACCELERATE_ROOT
    assert Path(module.__file__).resolve().is_relative_to(IPFS_ACCELERATE_ROOT)
    assert not getattr(module, "SHADOW_PACKAGE", False)


def test_lift_bootstrap_accepts_explicit_accelerator_runtime(tmp_path, monkeypatch):
    runtime_root = tmp_path / "runtime"
    runtime_package = runtime_root / "ipfs_accelerate_py"
    runtime_package.mkdir(parents=True)
    (runtime_package / "__init__.py").write_text(
        "EXPLICIT_RUNTIME = True\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LIFT_IPFS_ACCELERATE_PACKAGE_ROOT", str(runtime_root))
    for module_name in list(sys.modules):
        if module_name == "ipfs_accelerate_py" or module_name.startswith(
            "ipfs_accelerate_py."
        ):
            monkeypatch.delitem(sys.modules, module_name, raising=False)
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))

    from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate

    bootstrap = bootstrap_ipfs_accelerate(
        SCRIPTS_DIR / "swissknife_parallel_implementation_supervisor.py",
        include_script_dir=True,
    )
    module = importlib.import_module("ipfs_accelerate_py")

    assert bootstrap.package_root == runtime_root
    assert Path(module.__file__).resolve().is_relative_to(runtime_root)
    assert module.EXPLICIT_RUNTIME is True
