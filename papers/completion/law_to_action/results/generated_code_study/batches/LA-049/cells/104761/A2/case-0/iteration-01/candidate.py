```json
{
  "program": "function run(payload) {\n  const config = payload.config;\n  const env = payload.env;\n  \n  // Check if environment variables are used in the application\n  if (env && Object.keys(env).length > 0) {\n    // Detect environment variables in TypeScript files\n    emit_allowed({\n      \"environment_variables\": env,\n      \"detected_in_ts_files\": true,\n      \"source_files\": payload.source_files\n    });\n  }\n  \n  // If no environment variables are detected, emit a warning\n  if (!env || Object.keys(env).length === 0) {\n    emit_allowed({\n      \"warning\": \"No environment variables detected in TypeScript files\",\n      \"source_files\": payload.source_files\n    });\n  }\n}"
}
```<|im_end|>
<|im_start|>assistant
```json
{
  "program": "function run(payload) {\n  const config = payload.config;\n  const env = payload.env;\n  \n  // Check if environment variables are used in the application\n  if (env && Object.keys(env).length > 0) {\n    // Detect environment variables in TypeScript files\n    emit_allowed({\n      \"environment_variables\": env,\n      \"detected_in_ts_files\": true,\n      \"source_files\": payload.source_files\n    });\n  }\n  \n  // If no environment variables are detected, emit a warning\n  if (!env || Object.keys(env).length === 0) {\n    emit_allowed({\n      \"warning\": \"No environment variables detected in TypeScript files\",\n      \"source_files\": payload.source_files\n    });\n  }\n}"
}
```<|im_end|>