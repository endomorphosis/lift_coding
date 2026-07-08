# external/meta-wearables-dat-android to external/ipfs_datasets

Task: HAO-738
Goal: VAIOS-G710
Packet: goal_packet/interoperability/external/6595cbbfadb9

This objective validation repair covers the interface contract external/meta-wearables-dat-android external/ipfs_datasets. The Android DAT
producer envelope from HAO-739 can be projected into dataset records for display
widget feedback, training samples, and audit trails, while the embedded
`external/ipfs_datasets/.tools/ipfs_kit_py` descriptors provide bucket VFS and
deprecation schema evidence for the datasets side.

Runtime proof:

- `external/meta-wearables-dat-android/python/meta_wearables_dat_android/ipfs_kit_handoff.py`
  normalizes wearable dataset samples.
- `external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json`
  exposes the deprecation report schema used by the shared VFS tool surface.
- `external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md`
  and the bucket demos prove dataset bucket semantics are present.
- `tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop.py`
  checks the handoff projection and required descriptor files.

Validation:

```bash
python -m pytest tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop.py -q
```
