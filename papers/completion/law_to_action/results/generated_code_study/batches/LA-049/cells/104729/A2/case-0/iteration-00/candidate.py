function run(payload) {
  const ts = payload.ts;
  const config = payload.config;
  
  // Check if ts file exists
  if (!ts) {
    emit_allowed(payload);
    return;
  }
  
  // Check if config file exists
  if (!config) {
    emit_allowed(payload);
    return;
  }
  
  // Check if ts contains environment variable detection
  if (!ts.includes('environment')) {
    emit_allowed(payload);
    return;
  }
  
  // Check if config contains sibling final label
  if (!config.includes('final')) {
    emit_allowed(payload);
    return;
  }
  
  // If all checks pass, emit the source-relative JSON record
  emit_allowed({
    ts: ts,
    config: config,
    source: 'CVE-2023-28444',
    kind: 'permitted_public_source',
    locator: {
      cve_id: 'CVE-2023-28444',
      cwe_id: 'CWE-200',
      fix_commit: 'd701f51260637a84ede278e248934e0437a7ff86',
      language: 'TypeScript',
      repository: 'github.com/kyubisation/angular-server-side-configuration'
    }
  });
}