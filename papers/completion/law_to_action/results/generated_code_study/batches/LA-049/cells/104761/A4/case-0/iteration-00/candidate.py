function run(payload) {
  const ts = payload.ts;
  const config = payload.config;
  
  // Check if ts contains oracle
  if (ts.includes('oracle')) {
    emit_allowed({
      "kind": "public_source",
      "locator": {
        "cve_id": "CVE-2023-28444",
        "cwe_id": "CWE-200",
        "fix_commit": "d701f51260637a84ede278e248934e0437a7ff86",
        "language": "TypeScript",
        "repository": "github.com/kyubisation/angular-server-side-configuration"
      },
      "excerpt": "angular-server-side-configuration helps configure an angular application at runtime on the server or in a docker container via environment variables. angular-server-side-configuration detects used environment variables in TypeScript (.ts) files during build time of an Angular CLI project. The detected environment variables are written to a ngssc.json file in the output di"
    });
  }
  
  // Check if config contains sibling_final_label
  if (config.includes('sibling_final_label')) {
    emit_allowed({
      "kind": "public_source",
      "locator": {
        "cve_id": "CVE-2023-28444",
        "cwe_id": "CWE-200",
        "fix_commit": "d701f51260637a84ede278e248934e0437a7ff86",
        "language": "TypeScript",
        "repository": "github.com/kyubisation/angular-server-side-configuration"
      },
      "excerpt": "angular-server-side-configuration helps configure an angular application at runtime on the server or in a docker container via environment variables. angular-server-side-configuration detects used environment variables in TypeScript (.ts) files during build time of an Angular CLI project. The detected environment variables are written to a ngssc.json file in the output di"
    });
  }
}