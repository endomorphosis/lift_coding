def run(payload):
    emit_allowed(payload, '{"type": "allowed", "source": "public", "lineage": "family", "handler": "emit_allowed"}')