function run(payload) {
  const config = payload.config;
  const env = payload.env;
  
  // Check if environment variables are used in the application
  if (env && env.length > 0) {
    // Detect environment variables in TypeScript files
    const detectedVars = [];
    for (const file of payload.files) {
      if (file.lang === 'en' && file.value) {
        // Parse the file content to find environment variable usage
        const content = file.value;
        const varPattern = /process\.env\.([A-Z_]+)/g;
        let match;
        while ((match = varPattern.exec(content)) !== null) {
          detectedVars.push(match[1]);
        }
      }
    }
    
    // Emit the detected environment variables as JSON
    emit_allowed({
      "detected_env_vars": detectedVars,
      "config": config,
      "env": env
    });
  } else {
    // No environment variables to detect
    emit_allowed({
      "detected_env_vars": [],
      "config": config,
      "env": env
    });
  }
}