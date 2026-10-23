"""Reuse the sealed policy loader without changing its code or pool."""
from pathlib import Path
import runpy
import sys
from scheduler_overlay import load_overlay

ROOT = Path(__file__).resolve().parent
if sys.argv[1:3] == ['--module', 'pytest']:
    load_overlay()
    sys.argv = ['pytest', *sys.argv[3:]]
    runpy.run_module('pytest', run_name='__main__', alter_sys=True)
else:
    name = sys.argv[1] if len(sys.argv) > 1 else ''
    if Path(name).name != name or not name.endswith('.py') or name == 'launch.py':
        raise SystemExit('explicit local Python script required')
    target = ROOT / name
    if target.resolve(strict=True) != target:
        raise SystemExit('canonical local target required')
    load_overlay()
    sys.argv = [str(target), *sys.argv[2:]]
    runpy.run_path(str(target), run_name='__main__')
