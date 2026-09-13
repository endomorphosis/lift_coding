# Measured operator costs

{
  "actual_group_cpu_seconds": 1608.817478,
  "all_segment_raw_result_bindings": [
    {
      "path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/actual_operator_run_v1/result.json",
      "sha256": "316c200458b1455f0fde3dce1b40c0bbe69cc0e76030846ab481cb68ffad452c"
    },
    {
      "path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/actual_operator_continuation_v1/result.json",
      "sha256": "dc08dc0204d9bbb99cccf51bbd2549ea980beaaea6baddcc1377c7aab79c6745"
    },
    {
      "path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/actual_operator_continuation_v2/result.json",
      "sha256": "10ac98602f7305e1f8d9332288186623923cdb3fed9213876ab42dff2b1dbc34"
    },
    {
      "path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/actual_operator_startup_recovery_v3/result.json",
      "sha256": "d3736ee70e4e10df75d236b71ca7612d4e3aa773f9a9f45caaea572f8eab281d"
    },
    {
      "path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/actual_operator_startup625_recovery_v1/result.json",
      "sha256": "5c4fe89376b2ec0b3e765d4aa8ddcfab5de06837dbbb035a8bb0b38304e6e279"
    }
  ],
  "cell_host_wall_including_cleanup_seconds_sum": 2686.8702189085307,
  "counting_rule": "Each of 902 host attempts has its final parent CPU counted once: 900 scientific cells plus the undispatched 591 and 625 startups. No startup refund or duplicate scientific row. Parent samples are cumulative. Cell/segment/host clocks overlap and are not added. Preparation, earlier failed diagnostic runs, qualification and authoring costs remain separately bound histories.",
  "failed_startup_group_cpu_seconds": 0.118787,
  "infrastructure_startups": [
    {
      "attempt_id": null,
      "cell_host_wall_including_cleanup_seconds": 7.872266196995042,
      "cleanup_proven": true,
      "cost_counted_once": true,
      "group_cpu_seconds": 0.057819,
      "group_peak_memory_bytes": 6475776,
      "group_system_seconds": 0.025918,
      "group_user_seconds": 0.0319,
      "host_attempt_path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/actual_operator_continuation_v2/cells/0591/host/result.json",
      "host_result_sha256": "d56aa30d615e494f1c0d2edfdbf1669e9745878b51d7cf38028558dec9645406",
      "index": 591,
      "original_host_admitted": false,
      "original_termination_proven": false,
      "record_kind": "infrastructure_startup",
      "scheduled_scientific_attempt_id": "104759:A3:family:ebdcafa63e90d6e25c5fc28a35b5ecf8385c2c72f971bce552ed13f4203e0d04:case-0",
      "scientific_dispatch_not_reached": true,
      "scientific_outcome": null,
      "whole_cell_wall_to_group_exit_seconds": null
    },
    {
      "attempt_id": null,
      "cell_host_wall_including_cleanup_seconds": 8.79665912000928,
      "cleanup_proven": true,
      "cost_counted_once": true,
      "group_cpu_seconds": 0.060968,
      "group_peak_memory_bytes": 6995968,
      "group_system_seconds": 0.027132,
      "group_user_seconds": 0.033835,
      "host_attempt_path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/actual_operator_startup_recovery_v3/cells/0625/host/result.json",
      "host_result_sha256": "6253c97a1ec8dd69b56ecad11a2e8f1c459300fa1f58c12714e7085d820674c9",
      "index": 625,
      "original_host_admitted": false,
      "original_termination_proven": false,
      "record_kind": "infrastructure_startup",
      "scheduled_scientific_attempt_id": "104761:A2:family:47e697640b656d1165774b9f33decc9af78738cf25b45c8502b90cfe3e824629:case-1",
      "scientific_dispatch_not_reached": true,
      "scientific_outcome": null,
      "whole_cell_wall_to_group_exit_seconds": null
    }
  ],
  "operator_pause_wall_seconds_by_recovery_index": {
    "591": 2335.7108575609745,
    "625": 840.292727435939
  },
  "original_diagnostic_cpu_reason": "Not measured with the required process-group boundary; no imputed cost.",
  "original_diagnostic_cpu_seconds": null,
  "original_diagnostic_history": {
    "path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/preservation.private.json",
    "sha256": "1a08bad62b3032ae47182cffe604e199412c99888c779fcad3f59bbfe39196a8"
  },
  "pause_scope": "Separate operator/usage-interruption gap; not counted as active container wall. The 591 and 625 budgets are explicitly amended cumulative active allowances, not continuous original absolute 20s.",
  "recovered591_cumulative_active_wall_seconds": 11.766051943064667,
  "recovered591_cumulative_group_cpu_seconds": 1.482855,
  "recovered625_cumulative_active_wall_seconds": 19.793533246032894,
  "recovered625_cumulative_group_cpu_seconds": 1.400841,
  "schema": "la029-complete-cost-accounting/v1",
  "scientific_cell_group_cpu_seconds": 1608.698691,
  "segment_host_observations": [
    {
      "host_controller_cpu_seconds": 37.850814688,
      "host_controller_wall_seconds": 1123.4182278279914,
      "path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/actual_operator_run_v1/result.json",
      "segment": 0
    },
    {
      "host_controller_cpu_seconds": 8.20200896,
      "host_controller_wall_seconds": 239.8077705539763,
      "path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/actual_operator_continuation_v1/result.json",
      "segment": 1
    },
    {
      "host_controller_cpu_seconds": 4.017975551999999,
      "host_controller_wall_seconds": 120.53347974002827,
      "path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/actual_operator_continuation_v2/result.json",
      "segment": 2
    },
    {
      "host_controller_cpu_seconds": 4.08890832,
      "host_controller_wall_seconds": 121.402770339977,
      "path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/actual_operator_startup_recovery_v3/result.json",
      "segment": 3
    },
    {
      "host_controller_cpu_seconds": 36.890027216,
      "host_controller_wall_seconds": 1099.297824564972,
      "path": "/home/barberb/lift_coding/papers/completion/runtime_bootstrap/unblock_20260912/la015_fixed_action_recovery_v1/actual_operator_startup625_recovery_v1/result.json",
      "segment": 4
    }
  ]
}
