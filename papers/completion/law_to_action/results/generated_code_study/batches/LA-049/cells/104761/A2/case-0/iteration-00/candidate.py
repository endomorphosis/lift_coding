function run(payload) {
  const config = payload.config;
  const env = payload.env;
  
  // Check if environment variables are used in the application
  if (env && Object.keys(env).length > 0) {
    // Detect environment variables in TypeScript files
    emit_allowed({
      "environment_variables": env,
      "detected_in_ts_files": true,
      "source_files": payload.source_files
    });
  }
  
  // If no environment variables are detected, emit a warning
  if (!env || Object.keys(env).length === 0) {
    emit_allowed({
      "warning": "No environment variables detected in TypeScript files",
      "source_files": payload.source_files
    });
  }
}