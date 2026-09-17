function run(payload) {
  const config = payload.config;
  const tsFiles = payload.ts_files;
  
  // Check if we have configuration and TypeScript files
  if (!config || !tsFiles || tsFiles.length === 0) {
    return;
  }
  
  // Process each TypeScript file to detect environment variables
  tsFiles.forEach(file => {
    const filePath = file.path;
    const fileContent = file.content;
    
    // Find all environment variable references in the file
    const envVarRegex = /process\.env\.\w+/g;
    const matches = fileContent.match(envVarRegex);
    
    if (matches) {
      // Extract unique environment variable names
      const uniqueEnvVars = [...new Set(matches.map(match => match.split('.')[2]))];
      
      // Update the configuration with detected environment variables
      config.environment_variables = uniqueEnvVars;
    }
  });
  
  // Emit the updated configuration
  emit_allowed({
    "config": config,
    "ts_files": tsFiles
  });
}