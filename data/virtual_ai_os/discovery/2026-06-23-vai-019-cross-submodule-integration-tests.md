# VAI-019 Cross-Submodule Integration Tests

## Cross-Submodule Harness Evidence

```json
{
  "task_id": "VAI-019",
  "evidence_id": "vai-019-cross-submodule-integration",
  "requires_physical_devices": false,
  "scenarios": [
    {
      "scenario_id": "desktop-dataset-discovery",
      "component_ids": [
        "swissknife",
        "hallucinate_app",
        "ipfs_datasets_py"
      ],
      "capability_id": "dataset_discovery",
      "runtime_surface": "swissknife_orb",
      "placement_target": "endomorphosis/swissknife",
      "compute_placement": "desktop_peer"
    },
    {
      "scenario_id": "local-ipfs-pin-receipt",
      "component_ids": [
        "hallucinate_app",
        "ipfs_kit_py"
      ],
      "capability_id": "ipfs_pin",
      "runtime_surface": "direct_adapter",
      "placement_target": "endomorphosis/ipfs_kit_py",
      "compute_placement": "local"
    }
  ]
}
```

The integration harness derives per-component checkout roots and
`validation_artifacts` from `handsfree.virtual_ai_os_components` at test time.
This keeps the discovery packet stable while the executable coverage proves the
selected routes are bound to checked-out component repositories.
