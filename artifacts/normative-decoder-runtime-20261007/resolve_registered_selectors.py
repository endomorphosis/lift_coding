"""Read the genuine persisted catalog without constructing ModelManager."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/barberb/lift_coding')
ACCELERATE = ROOT / '.worktrees/normative-checkpoint-availability-accelerate-20261006'
STORE = ROOT / 'external/ipfs_accelerate/model_manager.duckdb'
sys.path.insert(0, str(ACCELERATE))


def pin(path):
    p = Path(path).resolve(strict=True)
    data = p.read_bytes()
    return {'path': str(p), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def witness():
    s = STORE.stat()
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def main():
    from ipfs_accelerate_py.model_catalog.sources import ir_persistent
    assert Path(ir_persistent.__file__).resolve() == ACCELERATE / 'ipfs_accelerate_py/model_catalog/sources/ir_persistent.py'
    relative = 'ipfs_accelerate_py/model_catalog/sources/ir_persistent.py'
    # The captured current parent uses108931f9; this frozen reader is byte-identical.
    current = subprocess.check_output(['git', 'show', '108931f98f9b270267ec7185850a835cad670513:' + relative], cwd=ACCELERATE)
    assert current == Path(ir_persistent.__file__).read_bytes()
    preflight_path = HERE / 'preflight-final/original-assets-preflight.json'
    preflight = json.loads(preflight_path.read_text())
    before = witness()
    source = ir_persistent.IRPersistentCatalogSource(path=STORE, source='normative-runtime-preparation.persisted')
    catalog = source.load()
    resolutions = []
    for state in preflight['selected_states']:
        resolution = catalog.resolve_ir_binding(state['model_manager_selector'])
        assert not any(resolution['authority'].values())
        declaration = resolution['selected_binding']['declaration']
        assert declaration['original_checkpoint_pin'] == state['original_checkpoint_pin']
        assert declaration['runtime_ready'] is declaration['teacher_qualified'] is declaration['proof_authority'] is False
        resolutions.append(resolution)
    assert witness() == before
    result = dict(schema='normative-cached-runtime-real-registered-selector-resolution/v1',
        completed=True, observed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        script_pin=pin(__file__), preflight_pin=pin(preflight_path), reader_pin=pin(ir_persistent.__file__),
        reader_source_matches_current_parent_component=True, selected_store=str(STORE),
        catalog_revision=catalog.revision, binding_snapshot_revision=catalog.binding_snapshot_revision,
        exact_resolutions=resolutions, database_file_witness_unchanged=True,
        model_manager_constructed=False, model_loaded=False, database_writes=False,
        source_bytes_or_Hub_authentication_performed=False, runtime_admitted=False,
        teacher_qualified=False, proof_authority=False, external_running_service_refreshed=False)
    destination = HERE / 'registered-selector-resolution.json'
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'completed': True, 'resolved_states': len(resolutions), 'receipt': pin(destination)}))


if __name__ == '__main__':
    main()
