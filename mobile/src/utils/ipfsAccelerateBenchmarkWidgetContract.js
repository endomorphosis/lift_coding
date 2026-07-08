export const BENCHMARK_WIDGET_ACTION_CONTRACT =
  'handsfree.meta-glasses/ipfs-accelerate-benchmark-widget-action@0.1.0';

export const BENCHMARK_WIDGET_ACTION_IDS = [
  'mobile_render_performance_benchmark_widget',
  'mobile_update_performance_benchmark_widget',
  'mobile_clear_performance_benchmark_widget',
  'mobile_refresh_performance_benchmark_metrics',
];

export const BENCHMARK_WIDGET_ORB_OPERATION_BY_ACTION_ID = {
  mobile_render_performance_benchmark_widget: 'render_performance_benchmark_widget',
  mobile_update_performance_benchmark_widget: 'update_performance_benchmark_widget',
  mobile_clear_performance_benchmark_widget: 'clear_performance_benchmark_widget',
  mobile_refresh_performance_benchmark_metrics: 'refresh_performance_benchmark_metrics',
};

export const BENCHMARK_WIDGET_DAT_METHOD_BY_ACTION_ID = {
  mobile_render_performance_benchmark_widget: 'renderPerformanceBenchmarkWidget',
  mobile_update_performance_benchmark_widget: 'updatePerformanceBenchmarkWidget',
  mobile_clear_performance_benchmark_widget: 'clearPerformanceBenchmarkWidget',
  mobile_refresh_performance_benchmark_metrics: 'refreshPerformanceBenchmarkMetrics',
};

export const BENCHMARK_WIDGET_TIME_SERIES_TABLE_BY_ACTION_ID = {
  mobile_render_performance_benchmark_widget: 'performance_baselines',
  mobile_update_performance_benchmark_widget: 'performance_trends',
  mobile_clear_performance_benchmark_widget: 'regression_notifications',
  mobile_refresh_performance_benchmark_metrics: 'performance_regressions',
};

export const IPFS_ACCELERATE_BENCHMARK_WIDGET_ACTION_CONTRACT = {
  contract: BENCHMARK_WIDGET_ACTION_CONTRACT,
  producer: 'external/ipfs_accelerate',
  consumer: 'mobile',
  interface_contract: 'interface contract mobile external/ipfs_accelerate',
  goal_id: 'VAIOS-G719',
  objective_validation_repair: 'VAI-672 repairs the VAIOS-G719 objective validation repair',
  action_ids: BENCHMARK_WIDGET_ACTION_IDS,
  operation_by_action_id: BENCHMARK_WIDGET_ORB_OPERATION_BY_ACTION_ID,
  dat_method_by_action_id: BENCHMARK_WIDGET_DAT_METHOD_BY_ACTION_ID,
  time_series_table_by_action_id: BENCHMARK_WIDGET_TIME_SERIES_TABLE_BY_ACTION_ID,
  schema_refs: {
    time_series_schema: 'external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql',
    benchmark_schema_script:
      'external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py',
    check_database_schema:
      'external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py',
    check_db_schema: 'external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py',
  },
};

const BENCHMARK_WIDGET_ACTION_ID_SET = new Set(BENCHMARK_WIDGET_ACTION_IDS);

export function isBenchmarkWidgetActionId(actionId) {
  return BENCHMARK_WIDGET_ACTION_ID_SET.has(actionId);
}
