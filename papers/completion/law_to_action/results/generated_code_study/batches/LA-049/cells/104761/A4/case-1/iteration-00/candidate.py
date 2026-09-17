function run(payload) {
  const config = {
    "environment": {
      "source": "ngssc.json",
      "target": "environment.ts"
    },
    "build": {
      "source": "ngssc.json",
      "target": "ngssc.json"
    }
  };

  emit_allowed(payload, config);
}