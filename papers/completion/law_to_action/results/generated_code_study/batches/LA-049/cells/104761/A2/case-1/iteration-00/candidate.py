async function run(payload) {
  const config = payload.config;
  const env = config.env;
  
  // Detect environment variables used in TypeScript files
  const tsFiles = payload.ts_files || [];
  const detectedEnvVars = [];
  
  for (const file of tsFiles) {
    const filePath = file.path;
    const fileContent = file.content;
    
    // Extract environment variable names from TypeScript files
    const envVarMatches = fileContent.match(/process\.env\.\w+/g) || [];
    for (const match of envVarMatches) {
      const varName = match.split('.').pop();
      if (!detectedEnvVars.includes(varName)) {
        detectedEnvVars.push(varName);
      }
    }
  }
  
  // Write detected environment variables to ngssc.json file
  if (detectedEnvVars.length > 0) {
    const jsonContent = JSON.stringify({ environmentVariables: detectedEnvVars }, null, 2);
    await emit_allowed({
      file: {
        path: 'ngssc.json',
        content: jsonContent
      }
    });
  }
}